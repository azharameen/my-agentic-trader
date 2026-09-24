"""Reusable Groww portfolio sync helpers.

This module is the single path for scheduled syncs and on-demand refreshes.
It normalizes live Groww holdings, positions, and margin into TrAId's DB.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app import db, groww_client

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _holdings_from_positions(
    client: groww_client.GrowwClient,
) -> list[groww_client.GrowwHolding]:
    """Use cash positions when Groww denies or omits settled holdings."""
    positions = client.get_positions()
    return [
        groww_client.GrowwHolding(
            symbol=position.symbol,
            quantity=position.quantity,
            avg_price=position.buy_price,
            current_price=position.current_price,
            invested_amount=round(position.buy_price * position.quantity, 2),
            current_value=round(position.current_price * position.quantity, 2),
            pnl=position.pnl,
            pnl_pct=round(
                (position.pnl / (position.buy_price * position.quantity)) * 100.0,
                2,
            )
            if position.buy_price > 0 and position.quantity > 0
            else 0.0,
        )
        for position in positions
        if position.quantity > 0
    ]


def _sync_holdings(
    client: groww_client.GrowwClient, user_id: str, synced_at: str
) -> dict[str, Any]:
    holdings = client.get_holdings()
    if not holdings:
        holdings = _holdings_from_positions(client)
    if not holdings:
        if not client.portfolio_access_error:
            db.init_all_tables()
            db.execute(
                """
                UPDATE user_positions SET status = 'INACTIVE', synced_last_synced_at = %s
                WHERE user_id = %s AND source = 'GROWW_SYNC' AND status = 'ACTIVE';
                """,
                (synced_at, user_id),
            )
        return {"holdings_found": 0, "synced_count": 0, "updated_count": 0, "closed_count": 0}

    db.init_all_tables()
    existing_rows = db.fetchall(
        """
        SELECT * FROM user_positions
        WHERE user_id = %s AND symbol IS NOT NULL
          AND source IN ('GROWW_SYNC', 'BASKET', 'MANUAL')
          AND status IN ('ACTIVE', 'PENDING_CONFIRMATION')
        ORDER BY CASE source WHEN 'BASKET' THEN 0 WHEN 'MANUAL' THEN 1 ELSE 2 END;
        """,
        (user_id,),
    )
    existing_by_symbol: dict[str, dict[str, Any]] = {}
    for row in existing_rows:
        existing_by_symbol.setdefault(row["symbol"], row)
    seen_symbols: set[str] = set()
    synced_count = 0
    updated_count = 0

    portfolio_row = db.fetchone(
        "SELECT portfolio_id FROM user_portfolios WHERE user_id = %s AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1;",
        (user_id,),
    )
    portfolio_id = portfolio_row["portfolio_id"] if portfolio_row else f"groww-sync-{user_id}"

    if not portfolio_row:
        db.execute(
            """
            INSERT INTO user_portfolios (
                portfolio_id, user_id, created_at, initial_capital,
                allocated_capital, cash_balance, risk_vibe, status
            ) VALUES (%s, %s, %s, 0, 0, 0, 'BALANCED', 'ACTIVE')
            ON CONFLICT (portfolio_id) DO NOTHING;
            """,
            (portfolio_id, user_id, synced_at),
        )

    for holding in holdings:
        seen_symbols.add(holding.symbol)
        entry_price = holding.avg_price if holding.avg_price > 0 else holding.current_price
        current_price = holding.current_price or entry_price
        invested_amount = holding.invested_amount or round(entry_price * holding.quantity, 2)
        current_value = holding.current_value or round(current_price * holding.quantity, 2)
        pnl = holding.pnl if holding.pnl else round(current_value - invested_amount, 2)
        pnl_pct = (
            holding.pnl_pct
            if holding.pnl_pct
            else round((pnl / invested_amount) * 100.0, 2)
            if invested_amount > 0
            else 0.0
        )

        existing = existing_by_symbol.get(holding.symbol)
        company_name = holding.company_name or (existing.get("company_name") if existing else None) or holding.symbol
        isin = holding.isin or (existing.get("isin") if existing else None) or ""
        investment_source = (
            "PLANNED_THEN_GROWW"
            if existing and existing.get("source") == "BASKET"
            else "MANUAL_THEN_GROWW"
            if existing and existing.get("source") == "MANUAL"
            else "GROWW_DIRECT"
        )
        plan_status = "BOUGHT" if existing and existing.get("source") == "BASKET" else "NONE"
        target_price = float(existing.get("target_price") or entry_price * 1.08) if existing else entry_price * 1.08
        stop_loss_price = float(existing.get("stop_loss_price") or entry_price * 0.94) if existing else entry_price * 0.94
        if existing:
            db.execute(
                """
                UPDATE user_positions SET
                    portfolio_id = %s,
                    shares = %s,
                    suggested_price = %s,
                    entry_price = %s,
                    current_price = %s,
                    target_price = %s,
                    stop_loss_price = %s,
                    status = 'ACTIVE',
                    filled_at = %s,
                    highest_price = %s,
                    trailing_stop = %s,
                    broker_name = %s,
                    sector = %s,
                    company_name = %s,
                    isin = %s,
                    source = 'GROWW_SYNC',
                    investment_source = %s,
                    plan_status = %s,
                    synced_current_price = %s,
                    synced_invested_amount = %s,
                    synced_current_value = %s,
                    synced_pnl = %s,
                    synced_pnl_pct = %s,
                    synced_last_synced_at = %s
                WHERE position_id = %s;
                """,
                (
                    portfolio_id,
                    holding.quantity,
                    entry_price,
                    entry_price,
                    current_price,
                    round(target_price, 2),
                    round(stop_loss_price, 2),
                    synced_at,
                    current_price,
                    round(stop_loss_price, 2),
                    "Groww",
                    "Diversified",
                    company_name,
                    isin,
                    investment_source,
                    plan_status,
                    current_price,
                    invested_amount,
                    current_value,
                    pnl,
                    pnl_pct,
                    synced_at,
                    existing["position_id"],
                ),
            )
            db.execute(
                """
                UPDATE user_positions SET status = 'INACTIVE', synced_last_synced_at = %s
                WHERE user_id = %s AND symbol = %s AND position_id <> %s
                  AND source IN ('GROWW_SYNC', 'BASKET', 'MANUAL');
                """,
                (synced_at, user_id, holding.symbol, existing["position_id"]),
            )
            updated_count += 1
        else:
            db.execute(
                """
                INSERT INTO user_positions (
                    position_id, portfolio_id, user_id, symbol, shares,
                    suggested_price, entry_price, current_price,
                    target_price, stop_loss_price, status, created_at, filled_at,
                    highest_price, trailing_stop, broker_name, sector, source,
                    company_name, isin, investment_source, plan_status,
                    synced_current_price, synced_invested_amount, synced_current_value,
                    synced_pnl, synced_pnl_pct, synced_last_synced_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE',
                    %s, %s, %s, %s, %s, %s, 'GROWW_SYNC',
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                );
                """,
                (
                    f"groww-{holding.symbol}",
                    portfolio_id,
                    user_id,
                    holding.symbol,
                    holding.quantity,
                    entry_price,
                    entry_price,
                    current_price,
                    round(entry_price * 1.08, 2),
                    round(entry_price * 0.94, 2),
                    synced_at,
                    synced_at,
                    current_price,
                    round(entry_price * 0.94, 2),
                    "Groww",
                    "Diversified",
                    company_name,
                    isin,
                    "GROWW_DIRECT",
                    "NONE",
                    current_price,
                    invested_amount,
                    current_value,
                    pnl,
                    pnl_pct,
                    synced_at,
                ),
            )
            synced_count += 1

    closed_count = 0
    for symbol, row in existing_by_symbol.items():
        if row.get("source") == "GROWW_SYNC" and symbol not in seen_symbols:
            db.execute(
                "UPDATE user_positions SET status = 'INACTIVE', synced_last_synced_at = %s WHERE position_id = %s;",
                (synced_at, row["position_id"]),
            )
            closed_count += 1

    return {
        "holdings_found": len(holdings),
        "synced_count": synced_count,
        "updated_count": updated_count,
        "closed_count": closed_count,
    }


def sync_groww_portfolio(user_id: str = "default_user") -> dict[str, Any]:
    """Fetch Groww portfolio data and persist it into TrAId's DB."""
    client = groww_client.get_groww_client()
    if not client.is_configured():
        return {"status": "SKIPPED", "reason": "Groww is not configured"}

    db.init_all_tables()
    synced_at = _now()
    client.clear_portfolio_access_error()
    run_id = f"groww-sync-{uuid.uuid4().hex[:12]}"
    db.execute(
        """
        INSERT INTO groww_sync_runs (
            run_id, user_id, started_at, status
        ) VALUES (%s, %s, %s, %s);
        """,
        (run_id, user_id, synced_at, "RUNNING"),
    )
    result: dict[str, Any] = {
        "status": "OK",
        "message": "Groww portfolio sync completed.",
        "synced_at": synced_at,
        "user_id": user_id,
        "run_id": run_id,
    }

    holdings_result = _sync_holdings(client, user_id=user_id, synced_at=synced_at)
    result.update(holdings_result)
    if client.portfolio_access_error:
        result["error"] = client.portfolio_access_error
        result["status"] = "PARTIAL"
        result["message"] = (
            "Groww access token is valid, but portfolio reads were denied. Check API permissions in Groww Developer Console."
        )

    try:
        margin = client.get_user_margin()
        db.execute(
            """
            UPDATE user_portfolios
            SET cash_balance = %s,
                allocated_capital = COALESCE(allocated_capital, 0),
                status = 'ACTIVE'
            WHERE user_id = %s;
            """,
            (margin.available_cash, user_id),
        )
        result["available_cash"] = margin.available_cash
        result["total_margin"] = margin.total_margin
        result["last_synced_at"] = synced_at
    except Exception as exc:  # noqa: BLE001
        logger.warning("Groww margin sync failed: %s", exc)
        result["available_cash"] = None
        result["total_margin"] = None

    try:
        positions = client.get_positions()
        result["positions_found"] = len(positions)
        if client.portfolio_access_error:
            result["error"] = client.portfolio_access_error
            result["status"] = "PARTIAL"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Groww positions sync failed: %s", exc)
        result["positions_found"] = 0

    db.execute(
        """
        UPDATE groww_sync_runs
        SET finished_at = %s,
            status = %s,
            holdings_found = %s,
            synced_count = %s,
            updated_count = %s,
            closed_count = %s,
            positions_found = %s,
            available_cash = %s,
            total_margin = %s,
            error = %s
        WHERE run_id = %s;
        """,
        (
            _now(),
            result["status"],
            int(result.get("holdings_found") or 0),
            int(result.get("synced_count") or 0),
            int(result.get("updated_count") or 0),
            int(result.get("closed_count") or 0),
            int(result.get("positions_found") or 0),
            result.get("available_cash"),
            result.get("total_margin"),
            result.get("error"),
            run_id,
        ),
    )

    try:
        from app import events

        events.broadcast_event("COMMAND_CENTER_TICK", result)
    except Exception:  # noqa: BLE001
        logger.debug("Failed to broadcast command center tick after Groww sync")

    return result
