"""Portfolio manager and execution recorder for beginner-assisted manual trading.

Manages user portfolio lifecycle: saving proposed baskets, confirming batch executions
with slippage checks, tracking real-time position health, and handling capital recycling.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app import db, market_data
from app.basket_generator import generate_strategy_basket
from app.models_basket import (
    BatchExecutionRequest,
    PortfolioSummary,
    PositionHealthStatus,
    StrategyBasket,
)

logger = logging.getLogger(__name__)


def create_user_portfolio_from_basket(
    basket: StrategyBasket, user_id: str = "default_user"
) -> str:
    """Initialize a portfolio record from a newly approved strategy basket."""
    db.init_all_tables()

    insert_query = """
    INSERT INTO user_portfolios (
        portfolio_id, user_id, created_at, initial_capital,
        allocated_capital, cash_balance, risk_vibe, status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (portfolio_id) DO UPDATE SET
        allocated_capital = EXCLUDED.allocated_capital,
        cash_balance = EXCLUDED.cash_balance,
        status = EXCLUDED.status;
    """
    db.execute(
        insert_query,
        (
            basket.basket_id,
            user_id,
            basket.created_at,
            basket.total_capital,
            basket.allocated_capital,
            basket.cash_reserve,
            basket.risk_vibe.value,
            "PENDING_CONFIRMATION",
        ),
    )

    # Insert pending positions with 2-tranche parameters
    for alloc in basket.allocations:
        pos_id = f"pos-{uuid.uuid4().hex[:8]}"
        pos_query = """
        INSERT INTO user_positions (
            position_id, portfolio_id, user_id, symbol, shares,
            suggested_price, entry_price, target_price, stop_loss_price,
            target2_price, target1_shares, target2_shares,
            holding_period, status, created_at, layman_rationale, sector,
            source, investment_source, plan_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'BASKET', 'PLANNED', 'PLANNED');
        """
        db.execute(
            pos_query,
            (
                pos_id,
                basket.basket_id,
                user_id,
                alloc.symbol,
                alloc.shares,
                alloc.suggested_entry_price,
                alloc.suggested_entry_price,  # Default to suggested entry price until confirmed
                alloc.target1_price or alloc.target_price,
                alloc.stop_loss_price,
                alloc.target2_price,
                alloc.target1_shares,
                alloc.target2_shares,
                alloc.holding_period,
                "PENDING_CONFIRMATION",
                basket.created_at,
                alloc.layman_rationale,
                alloc.sector,
            ),
        )

    return basket.basket_id


def confirm_batch_execution(request: BatchExecutionRequest) -> PortfolioSummary:
    """Confirm user execution on broker, calibrating actual filled prices and logging slippage."""
    db.init_all_tables()
    now_utc = datetime.now(timezone.utc).isoformat()

    total_actual_invested = 0.0

    for item in request.confirmations:
        # Check existing position
        row = db.fetchone(
            "SELECT * FROM user_positions WHERE portfolio_id = %s AND symbol = %s;",
            (request.basket_id, item.symbol),
        )
        if not row:
            continue

        suggested = float(row["suggested_price"])
        actual = float(item.executed_price)
        shares = int(item.shares)
        total_actual_invested += actual * shares

        slippage_pct = round(((actual - suggested) / suggested) * 100.0, 2)
        if abs(slippage_pct) > 1.5:
            logger.info(
                "Slippage detected on %s: suggested=₹%.2f, filled=₹%.2f (%.2f%%)",
                item.symbol, suggested, actual, slippage_pct
            )

        # Update position with confirmed execution
        update_pos = """
        UPDATE user_positions SET
            shares = %s,
            entry_price = %s,
            status = 'ACTIVE',
            filled_at = %s,
            highest_price = %s,
            trailing_stop = %s,
            broker_name = %s,
            source = 'BASKET',
            investment_source = 'PLANNED',
            plan_status = 'BOUGHT'
        WHERE position_id = %s;
        """
        db.execute(
            update_pos,
            (
                shares,
                actual,
                now_utc,
                actual,
                row["stop_loss_price"],
                item.broker_name or "Broker",
                row["position_id"],
            ),
        )

    # Update portfolio status and cash balance
    port_row = db.fetchone(
        "SELECT * FROM user_portfolios WHERE portfolio_id = %s;",
        (request.basket_id,),
    )
    if port_row:
        initial_cap = float(port_row["initial_capital"])
        new_cash = max(0.0, initial_cap - total_actual_invested)
        uid = request.user_id or port_row.get("user_id") or "default_user"
        db.execute(
            """
            UPDATE user_portfolios SET
                allocated_capital = %s,
                cash_balance = %s,
                status = 'ACTIVE',
                user_id = %s
            WHERE portfolio_id = %s;
            """,
            (round(total_actual_invested, 2), round(new_cash, 2), uid, request.basket_id),
        )
        db.execute(
            "UPDATE user_positions SET user_id = %s WHERE portfolio_id = %s;",
            (uid, request.basket_id),
        )

    return get_user_portfolio(user_id=request.user_id, portfolio_id=request.basket_id)


def get_user_portfolio(
    user_id: str = "default_user", portfolio_id: Optional[str] = None
) -> Optional[PortfolioSummary]:
    """Retrieve active user portfolio with live price evaluations, P&L, 2-tranche progress, and tax breakdowns."""
    db.init_all_tables()

    if portfolio_id:
        port_row = db.fetchone(
            "SELECT * FROM user_portfolios WHERE portfolio_id = %s;",
            (portfolio_id,),
        )
    else:
        port_row = db.fetchone(
            "SELECT * FROM user_portfolios WHERE user_id = %s AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1;",
            (user_id,),
        )

    if not port_row:
        return None

    pid = port_row["portfolio_id"]
    positions_rows = db.fetchall(
        "SELECT * FROM user_positions WHERE portfolio_id = %s AND status = 'ACTIVE';",
        (pid,),
    )

    active_positions: list[PositionHealthStatus] = []
    total_current_value = 0.0
    total_invested = 0.0
    total_net_pnl = 0.0

    for pos in positions_rows:
        pos_id = pos["position_id"]
        sym = pos["symbol"]
        shares = int(pos["shares"])
        entry = float(pos["entry_price"])
        target1 = float(pos["target_price"])
        target2 = float(pos.get("target2_price") or target1 * 1.08)
        stop_loss = float(pos["stop_loss_price"])
        t1_shares = int(pos.get("target1_shares") or max(1, shares // 2))
        t2_shares = int(pos.get("target2_shares") or max(0, shares - t1_shares))
        tranche1_exited = bool(pos.get("tranche1_exited", False))
        breakeven_locked = bool(pos.get("breakeven_locked", False))

        # Fetch latest price
        try:
            hist = market_data.load_price_history(sym, period="5d")
            current_price = float(hist["Close"].iloc[-1]) if not hist.empty else entry
        except Exception:  # noqa: BLE001
            current_price = entry

        # Dynamic Break-even Ratchet: If price >= +4% above entry, lock trailing stop at Break-Even (Entry Price)
        if current_price >= entry * 1.04 and not breakeven_locked:
            breakeven_locked = True
            stop_loss = max(stop_loss, entry)
            db.execute(
                "UPDATE user_positions SET breakeven_locked = TRUE, trailing_stop = %s WHERE position_id = %s;",
                (entry, pos_id),
            )
        elif breakeven_locked:
            stop_loss = max(stop_loss, entry)

        current_val = current_price * shares
        invested_val = entry * shares
        pnl_amt = current_val - invested_val
        pnl_pct = round(((current_price - entry) / entry) * 100.0, 2) if entry > 0 else 0.0

        # Tax & statutory charges breakdown (0.1% STT/brokerage + 20% STCG on profits)
        estimated_charges = round((invested_val + current_val) * 0.001, 2)
        estimated_stcg_tax = round(max(0.0, pnl_amt) * 0.20, 2)
        estimated_net_pnl = round(pnl_amt - estimated_charges - (estimated_stcg_tax if pnl_amt > 0 else 0.0), 2)
        total_net_pnl += estimated_net_pnl

        # Calculate progress towards target 1
        total_target_distance = max(0.01, target1 - entry)
        current_advance = max(0.0, current_price - entry)
        progress_pct = min(100.0, round((current_advance / total_target_distance) * 100.0, 1))

        # GTT Trigger prices
        gtt_stop_trig = round(stop_loss, 2)
        gtt_t1_trig = round(target1, 2)
        gtt_t2_trig = round(target2, 2)

        # Status & Action Recommendation
        status = "ON_TRACK"
        action_req = False
        rec_action = "HOLD - Trend is healthy. Relax and let agents monitor."

        if current_price >= target2:
            status = "TARGET_REACHED"
            action_req = True
            rec_action = f"SELL all remaining {shares} shares of {sym} to capture full runner target (+{pnl_pct}%)"
        elif current_price >= target1 and not tranche1_exited:
            status = "TARGET_REACHED"
            action_req = True
            rec_action = f"SELL {t1_shares} shares (Tranche 1) on broker to lock in profit. Trailing stop ratcheted to ₹{entry:.2f}."
        elif current_price <= stop_loss:
            status = "STOPPED_OUT"
            action_req = True
            rec_action = f"EXIT {shares} shares of {sym} on broker to protect capital (Stop Loss hit)"
        elif progress_pct >= 70.0:
            status = "APPROACHING_TARGET"
            rec_action = f"Approaching Target 1 ({progress_pct}% complete). Prepare to take profit."

        total_current_value += current_val
        total_invested += invested_val

        active_positions.append(
            PositionHealthStatus(
                position_id=pos_id,
                symbol=sym,
                shares=shares,
                entry_price=round(entry, 2),
                current_price=round(current_price, 2),
                pnl_amount=round(pnl_amt, 2),
                pnl_pct=pnl_pct,
                target_price=round(target1, 2),
                stop_loss_price=round(stop_loss, 2),
                target_progress_pct=progress_pct,
                status=status,
                action_required=action_req,
                recommended_action=rec_action,
                holding_period=pos.get("holding_period") or "2-4 Weeks",
                target1_price=round(target1, 2),
                target1_shares=t1_shares,
                target2_price=round(target2, 2),
                target2_shares=t2_shares,
                breakeven_locked=breakeven_locked,
                tranche1_exited=tranche1_exited,
                gtt_stop_trigger=gtt_stop_trig,
                gtt_target1_trigger=gtt_t1_trig,
                gtt_target2_trigger=gtt_t2_trig,
                estimated_charges=estimated_charges,
                estimated_stcg_tax=estimated_stcg_tax,
                estimated_net_pnl=estimated_net_pnl,
            )
        )

    unrealized_pnl = total_current_value - total_invested
    unrealized_pct = (
        round((unrealized_pnl / total_invested) * 100.0, 2) if total_invested > 0 else 0.0
    )
    cash = float(port_row["cash_balance"])

    return PortfolioSummary(
        portfolio_id=pid,
        user_id=user_id,
        initial_capital=float(port_row["initial_capital"]),
        invested_capital=round(total_invested, 2),
        current_value=round(total_current_value + cash, 2),
        unrealized_pnl=round(unrealized_pnl, 2),
        unrealized_pnl_pct=unrealized_pct,
        cash_balance=round(cash, 2),
        total_net_pnl=round(total_net_pnl, 2),
        active_positions=active_positions,
    )
