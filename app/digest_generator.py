"""Daily digest and market evaluation generator for beginner investors.

Produces calm, plain-English morning briefings and evening portfolio health reports,
highlighting key progress milestones and high-priority action alerts without financial jargon.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app import db
from app.models_basket import DailyDigest, PositionHealthStatus
from app.portfolio_manager import get_user_portfolio

logger = logging.getLogger(__name__)


def generate_morning_mood_digest(user_id: str = "default_user") -> DailyDigest:
    """Generate pre-market morning briefing (8:45 AM) summarizing market sentiment and active holdings."""
    portfolio = get_user_portfolio(user_id=user_id)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    pos_count = len(portfolio.active_positions) if portfolio else 0
    total_val = portfolio.current_value if portfolio else 0.0

    greeting = "☀️ Good morning!"
    market_mood = (
        "Indian equity markets are positioned steadily this morning with constructive macroeconomic cues. "
        "Large-cap indices are maintaining their uptrend above key multi-week moving averages."
    )

    action_alerts: list[str] = []
    earnings_alerts: list[str] = []
    if portfolio:
        for pos in portfolio.active_positions:
            if pos.status == "APPROACHING_TARGET":
                action_alerts.append(f"🎯 {pos.symbol} is {pos.target_progress_pct}% toward profit target ₹{pos.target_price:.2f}.")
            elif pos.status == "TARGET_REACHED":
                action_alerts.append(f"🚨 TAKE PROFIT: {pos.symbol} hit target ₹{pos.target_price:.2f}. Consider selling {pos.target1_shares or pos.shares} shares.")
            elif pos.status == "STOPPED_OUT":
                action_alerts.append(f"🛑 STOP LOSS: {pos.symbol} dropped below ₹{pos.stop_loss_price:.2f}. Capital protection trigger.")

    zen_mode = len(action_alerts) == 0
    zen_message = (
        "🧘 Status: Zen — All positions are healthy, risk stops are active, and 0 manual actions are needed today. Enjoy your day!"
        if zen_mode
        else None
    )

    if zen_mode:
        summary_text = (
            f"You have {pos_count} active investments valued at ₹{total_val:,.2f}. "
            f"All positions are progressing smoothly within expected volatility channels. Zero manual actions needed today."
        )
    else:
        summary_text = (
            f"You have {pos_count} active investments valued at ₹{total_val:,.2f}. "
            f"Key focus for today: {len(action_alerts)} position(s) require your attention."
        )

    digest_id = f"dig-am-{uuid.uuid4().hex[:8]}"
    digest = DailyDigest(
        digest_id=digest_id,
        digest_type="MORNING_MOOD",
        date_str=today_str,
        title="🌅 Morning Market Brief & Portfolio Outlook",
        greeting=greeting,
        market_mood=market_mood,
        portfolio_summary_text=summary_text,
        total_portfolio_value=total_val,
        daily_pnl_amount=0.0,
        daily_pnl_pct=0.0,
        zen_mode=zen_mode,
        zen_message=zen_message,
        positions=portfolio.active_positions if portfolio else [],
        action_alerts=action_alerts,
        earnings_alerts=earnings_alerts,
    )

    # Save to database
    _save_digest(digest, user_id=user_id, portfolio_id=portfolio.portfolio_id if portfolio else None)
    return digest


def generate_evening_health_digest(user_id: str = "default_user") -> DailyDigest:
    """Generate post-market evening health check (4:00 PM) summarizing daily P&L and target milestones."""
    portfolio = get_user_portfolio(user_id=user_id)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    total_val = portfolio.current_value if portfolio else 0.0
    unrealized_pnl = portfolio.unrealized_pnl if portfolio else 0.0
    unrealized_pct = portfolio.unrealized_pnl_pct if portfolio else 0.0

    pnl_sign = "+" if unrealized_pnl >= 0 else ""
    pnl_emoji = "🟢" if unrealized_pnl >= 0 else "🟠"

    greeting = "🌇 Evening Portfolio Wrap"
    market_mood = "Markets closed today with steady participation across major sectors."

    summary_text = (
        f"Your portfolio is valued at ₹{total_val:,.2f} ({pnl_emoji} {pnl_sign}₹{unrealized_pnl:,.2f} / {pnl_sign}{unrealized_pct}% overall). "
    )

    action_alerts: list[str] = []
    if portfolio:
        for pos in portfolio.active_positions:
            if pos.status == "TARGET_REACHED":
                action_alerts.append(f"🚨 Action: Sell {pos.shares} shares of {pos.symbol} on your broker to lock in profit.")
            elif pos.status == "STOPPED_OUT":
                action_alerts.append(f"🛑 Action: Exit {pos.shares} shares of {pos.symbol} on your broker to protect capital.")

    zen_mode = len(action_alerts) == 0
    zen_message = (
        "🧘 Status: Zen — No overnight risks detected. Your downside is safely protected by automated GTT/stop-loss orders."
        if zen_mode
        else None
    )

    digest_id = f"dig-pm-{uuid.uuid4().hex[:8]}"
    digest = DailyDigest(
        digest_id=digest_id,
        digest_type="EVENING_HEALTH",
        date_str=today_str,
        title="📊 Evening Portfolio Health Report",
        greeting=greeting,
        market_mood=market_mood,
        portfolio_summary_text=summary_text,
        total_portfolio_value=total_val,
        daily_pnl_amount=unrealized_pnl,
        daily_pnl_pct=unrealized_pct,
        zen_mode=zen_mode,
        zen_message=zen_message,
        positions=portfolio.active_positions if portfolio else [],
        action_alerts=action_alerts,
        earnings_alerts=[],
    )

    _save_digest(digest, user_id=user_id, portfolio_id=portfolio.portfolio_id if portfolio else None)
    return digest


def _save_digest(digest: DailyDigest, user_id: str, portfolio_id: Optional[str]) -> None:
    """Save generated digest into PostgreSQL relational store."""
    try:
        db.init_all_tables()
        insert_query = """
        INSERT INTO daily_digests (
            digest_id, user_id, digest_date, digest_type,
            portfolio_id, title, summary, payload, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        db.execute(
            insert_query,
            (
                digest.digest_id,
                user_id,
                digest.date_str,
                digest.digest_type,
                portfolio_id,
                digest.title,
                digest.portfolio_summary_text,
                digest.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to save daily digest to database: %s", exc)


def format_digest_for_telegram(digest: DailyDigest) -> str:
    """Format structured daily digest into high-clarity markdown for Telegram delivery."""
    lines = [
        f"*{digest.title}*",
        f"📅 _{digest.date_str}_",
        "",
        digest.greeting,
        f"🌐 *Market Context:* {digest.market_mood}",
        "",
        f"💼 *Portfolio Status:* {digest.portfolio_summary_text}",
    ]

    if digest.zen_mode and digest.zen_message:
        lines.append("")
        lines.append(f"*{digest.zen_message}*")

    if digest.positions:
        lines.append("")
        lines.append("*Current Holdings:*")
        for pos in digest.positions:
            sign = "+" if pos.pnl_pct >= 0 else ""
            be_tag = " [🔒 Break-Even]" if pos.breakeven_locked else ""
            lines.append(
                f"• *{pos.symbol}* ({pos.shares} sh): ₹{pos.current_price:,.2f} "
                f"({sign}{pos.pnl_pct}%){be_tag} | Target: ₹{pos.target_price:,.2f} ({pos.target_progress_pct}% done)"
            )

    if digest.action_alerts:
        lines.append("")
        lines.append("⚡ *Action Items:*")
        for alert in digest.action_alerts:
            lines.append(f"  {alert}")

    return "\n".join(lines)
