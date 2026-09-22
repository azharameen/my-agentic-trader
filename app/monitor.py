"""
Position monitor — auto-closes OPEN_PAPER trades on stop/target breach with dynamic ATR trailing stops (ADR-028).

Runs once at the start of every `/scan` (see `pipeline.run_universe_scan`).
Without this, `trade_audit_log` rows stay `OPEN_PAPER` forever and the
realized P&L column never populates, so there is no way to measure whether
the strategy actually works.
"""

from __future__ import annotations

import logging

from app import broker, db, executor, risk, screener
from config.settings import get_settings

logger = logging.getLogger(__name__)


def check_open_trades() -> list[dict]:
    """Evaluate open paper trades, ratchet dynamic trailing stops, and close on exit signals.

    Returns the list of trades closed during this check (merged trade +
    close-result dicts), for a Telegram summary. A symbol with no fetchable
    snapshot is skipped this round rather than failing the whole check.
    """
    closed: list[dict] = []
    open_trades = [t for t in executor.fetch_all_trades() if t["status"] == "OPEN_PAPER"]

    for trade in open_trades:
        symbol = trade["symbol"]
        snap = screener.get_symbol_snapshot(symbol)
        if snap is None:
            logger.warning("Position monitor: no snapshot for %s; skipping this round.", symbol)
            continue

        price = snap["daily_close"]
        atr = snap.get("atr") or 10.0
        entry_price = float(trade.get("fill_price") or trade.get("entry_price") or price)
        hard_stop = float(trade.get("hard_stop") or (entry_price * 0.95))
        prev_highest = float(trade.get("highest_price") or entry_price)
        prev_trailing_stop = float(trade.get("trailing_stop") or trade.get("soft_stop") or hard_stop)

        # Update highest price reached since entry
        new_highest = max(prev_highest, price)

        # Calculate new dynamic trailing stop
        new_trailing_stop, stop_mode = risk.calculate_trailing_stop(
            entry_price=entry_price,
            hard_stop=hard_stop,
            highest_price=new_highest,
            current_price=price,
            atr=atr,
            previous_trailing_stop=prev_trailing_stop,
        )

        # Update trade_audit_log with ratcheted levels
        try:
            db.execute(
                """
                UPDATE trade_audit_log
                SET highest_price = %s, trailing_stop = %s
                WHERE trade_id = %s
                """,
                (new_highest, new_trailing_stop, trade["trade_id"]),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not update trailing stop for %s: %s", trade["trade_id"], exc)

        category = None
        if price <= hard_stop:
            category = "STOPPED_OUT"
        elif price <= new_trailing_stop and new_trailing_stop > hard_stop:
            category = "TRAILING_STOP_HIT" if stop_mode == "ATR_TRAILING" else "BREAK_EVEN_STOP_HIT"
        elif price >= trade["target_price"]:
            category = "TARGET_HIT"

        if category is not None:
            result = broker.get_broker(get_settings().TRADING_MODE).close_trade(
                trade["trade_id"], exit_price=price, mistake_category=category
            )
            closed.append({**trade, **result, "mistake_category": category})

    if closed:
        logger.info(
            "Position monitor closed %d trade(s): %s",
            len(closed),
            [f"{c['symbol']} ({c.get('mistake_category')})" for c in closed],
        )
    return closed

