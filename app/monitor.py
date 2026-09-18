"""
Position monitor — auto-closes OPEN_PAPER trades on stop/target breach.

Runs once at the start of every `/scan` (see `pipeline.run_universe_scan`).
Without this, `trade_audit_log` rows stay `OPEN_PAPER` forever and the
realized P&L column never populates, so there is no way to measure whether
the strategy actually works.
"""

from __future__ import annotations

import logging

from app import broker, executor, screener
from config.settings import get_settings

logger = logging.getLogger(__name__)


def check_open_trades() -> list[dict]:
    """Close any OPEN_PAPER trade whose current price has hit its hard stop or target.

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
        category = None
        if price <= trade["hard_stop"]:
            category = "STOPPED_OUT"
        elif price >= trade["target_price"]:
            category = "TARGET_HIT"

        if category is not None:
            result = broker.get_broker(get_settings().TRADING_MODE).close_trade(
                trade["trade_id"], exit_price=price, mistake_category=category
            )
            closed.append({**trade, **result, "mistake_category": category})

    if closed:
        logger.info("Position monitor closed %d trade(s): %s",
                    len(closed), [c["symbol"] for c in closed])
    return closed
