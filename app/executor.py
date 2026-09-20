"""
Execution & audit layer (ADR-023).

Handles:
  * Schema initialization and PostgreSQL connection pooling.
  * Paper-trading fill simulation with realistic slippage (0.05%).
  * Appending every decision state to the `trade_audit_log` table for
    post-mortem analysis.

In `PAPER_TRADING` mode fills are simulated locally. In `LIVE` mode this module
refuses to route orders until a real broker adapter is wired in.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app import db
from app.risk import calculate_delivery_costs
from app.state import TradeProposal
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Realistic slippage applied to paper fills (0.05%).
SLIPPAGE_PCT = 0.0005


def init_db() -> None:
    """Create the audit schema and relational tables if they do not already exist.

    Safe to call repeatedly (idempotent). Called on application boot.
    """
    db.init_all_tables()
    logger.info("Database initialized successfully.")


def get_current_capital() -> float:
    """Configured base capital plus realized P&L from closed paper trades.

    Used for position sizing so `RISK_PER_TRADE_PCT` tracks actual equity as
    it accrues, instead of always sizing off the static config baseline.
    """
    settings = get_settings()
    row = db.fetchone(
        "SELECT COALESCE(SUM(realized_pnl), 0) AS total FROM trade_audit_log WHERE status = %s",
        ("CLOSED",),
    )
    realized = row["total"] if row and row.get("total") is not None else 0.0
    return settings.PORTFOLIO_CAPITAL + float(realized)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_open_trade(
    proposal: TradeProposal,
    rsi: float,
    ema_200: float,
    atr: float,
    thesis: str,
    human_decision: str,
    news_headlines: Optional[list[str]] = None,
    evidence_snapshot_id: Optional[str] = None,
    strategy_name: Optional[str] = None,
    market_regime: Optional[str] = None,
    catalyst_type: Optional[str] = None,
    source_set: Optional[list[str]] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    cache_hits: Optional[list[str]] = None,
) -> dict:
    """Simulate a paper fill and persist an OPEN_PAPER trade row.

    The fill price applies slippage against the entry (buys fill slightly
    higher than the quoted entry). Returns the full record dict including the
    generated `trade_id` and `fill_price`.
    """
    settings = get_settings()
    if settings.TRADING_MODE == "LIVE":
        raise RuntimeError(
            "LIVE order routing is not implemented. Set TRADING_MODE=PAPER_TRADING."
        )

    trade_id = uuid.uuid4().hex
    fill_price = round(proposal.entry_price * (1.0 + SLIPPAGE_PCT), 2)
    headlines_json = json.dumps(news_headlines or [])

    db.execute(
        """
        INSERT INTO trade_audit_log (
            trade_id, timestamp, symbol, entry_price, soft_stop, hard_stop,
            target_price, quantity, rsi, ema_200, atr, thesis, headlines_used,
            human_decision, fill_price, status, evidence_snapshot_id, strategy_name,
            market_regime, catalyst_type, source_set, llm_provider, llm_model, cache_hits
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            trade_id,
            _now_iso(),
            proposal.symbol,
            proposal.entry_price,
            proposal.soft_stop,
            proposal.hard_stop,
            proposal.target_price,
            proposal.quantity,
            rsi,
            ema_200,
            atr,
            thesis,
            headlines_json,
            human_decision,
            fill_price,
            "OPEN_PAPER",
            evidence_snapshot_id,
            strategy_name,
            market_regime,
            catalyst_type,
            json.dumps(source_set or []),
            llm_provider,
            llm_model,
            json.dumps(cache_hits or []),
        ),
    )

    logger.info(
        "PAPER FILL %s %s qty=%d fill=%.2f (slippage %.4f%%)",
        trade_id, proposal.symbol, proposal.quantity, fill_price, SLIPPAGE_PCT * 100,
    )
    return {
        "trade_id": trade_id,
        "symbol": proposal.symbol,
        "fill_price": fill_price,
        "quantity": proposal.quantity,
        "status": "OPEN_PAPER",
        "slippage_pct": SLIPPAGE_PCT * 100,
    }


def close_trade(
    trade_id: str,
    exit_price: float,
    mistake_category: Optional[str] = None,
) -> dict:
    """Close an open paper trade, computing realized P&L.

    Realized P&L = (exit_price - fill_price) * quantity. The row is updated to
    `CLOSED`. Returns the updated record.
    """
    row = db.fetchone(
        "SELECT status, fill_price, quantity, exit_price, realized_pnl FROM trade_audit_log WHERE trade_id = %s",
        (trade_id,),
    )
    if row is None:
        raise ValueError(f"Unknown trade_id: {trade_id}")

    if row["status"] == "CLOSED":
        return {
            "trade_id": trade_id,
            "exit_price": row["exit_price"],
            "realized_pnl": row["realized_pnl"],
            "status": "CLOSED",
        }

    fill_price = row["fill_price"]
    quantity = row["quantity"]
    gross_pnl = round((exit_price - fill_price) * quantity, 2)
    costs = calculate_delivery_costs(
        buy_value=fill_price * quantity,
        sell_value=exit_price * quantity,
    )
    realized_pnl = round(gross_pnl - costs.total, 2)

    db.execute(
        """
        UPDATE trade_audit_log
        SET status = 'CLOSED', exit_price = %s, realized_pnl = %s,
            gross_pnl = %s, transaction_costs = %s, mistake_category = %s
        WHERE trade_id = %s
        """,
        (exit_price, realized_pnl, gross_pnl, costs.model_dump_json(), mistake_category, trade_id),
    )

    logger.info(
        "CLOSED %s exit=%.2f pnl=%.2f mistake=%s",
        trade_id, exit_price, realized_pnl, mistake_category,
    )
    return {
        "trade_id": trade_id,
        "exit_price": exit_price,
        "realized_pnl": realized_pnl,
        "gross_pnl": gross_pnl,
        "transaction_costs": costs.model_dump(),
        "status": "CLOSED",
    }


def fetch_all_trades() -> list[dict]:
    """Return every audit row as a list of dicts (for the dashboard)."""
    return db.fetchall("SELECT * FROM trade_audit_log ORDER BY timestamp DESC")
