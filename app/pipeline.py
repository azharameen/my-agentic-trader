"""
Shared pipeline orchestration.

Drives the LangGraph trading pipeline and surfaces any resulting proposal to
Telegram. Used by BOTH the CLI (`app.main scan` / `run`) and the Telegram bot
(`/scan` / `/run` commands) so the two entry points behave identically.

This module is deliberately free of any web framework — the only "transport"
is the Telegram Bot API (outbound HTTPS), so the whole system runs as a single
long-polling process with no inbound ports.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from app import (
    corporate_events,
    graph,
    monitor,
    news,
    observability,
    outbox,
    regime,
    screener,
    telegram_bot,
)
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Guards against overlapping /scan runs (double downloads, duplicate proposals).
_scan_lock = threading.Lock()


class ScanInProgressError(RuntimeError):
    """Raised when a universe scan is requested while one is already running."""


def _notify_closed_trades(closed: list[dict]) -> None:
    if not closed:
        return
    lines = ["\U0001F4CA *Position monitor closed the following trade(s):*", ""]
    for trade in closed:
        lines.append(
            f"\u2022 *{trade['symbol']}* [{trade.get('mistake_category', '?')}] "
            f"exit \u20b9{trade.get('exit_price', 0):,.2f} | P&L \u20b9{trade.get('realized_pnl', 0):+,.2f}"
        )
    telegram_bot.notify_text(get_settings().TELEGRAM_CHAT_ID, "\n".join(lines))


def process_symbol(
    symbol: str,
    news_headlines: Optional[list[str]] = None,
    snapshot: Optional[dict] = None,
    events: Optional[list[corporate_events.CorporateEvent]] = None,
) -> dict:
    """Run one symbol through the graph and push any proposal to Telegram.

    Fetches real RSS headlines when the caller doesn't already have them, and
    forwards a pre-computed technical snapshot (if given) so the graph's
    screener node doesn't re-download the same OHLCV history.

    Returns the final graph state (or the interrupt state if paused at
    `human_approval`).
    """
    symbol = screener.canonical_symbol(symbol)
    started = time.perf_counter()
    with observability.span("pipeline.process_symbol", symbol=symbol):
        logger.info("Processing %s ...", symbol)
        try:
            if news_headlines is None:
                news_headlines = news.fetch_headlines(symbol)
            state = graph.run_symbol(symbol, news_headlines, snapshot=snapshot, events=events)
        except Exception as exc:  # noqa: BLE001 - one bad symbol must not kill a scan
            logger.exception("Failed to process %s", symbol)
            return {
                "execution_details": {"status": "ERROR", "error": str(exc)},
                "timing": {"process_symbol_seconds": round(time.perf_counter() - started, 3)},
            }

    interrupts = state.get("__interrupt__") if isinstance(state, dict) else None
    if interrupts:
        payload = interrupts[0].value
        logger.info("Graph paused at human_approval for %s; pushing to Telegram.", symbol)
        recipient = get_settings().TELEGRAM_CHAT_ID
        outbox.enqueue("TRADE_PROPOSAL", recipient, payload)
        outbox.deliver_pending(telegram_bot.send_proposal_to_chat)
        observability.event("proposal.created", symbol=symbol)
    else:
        logger.info("Thread for %s completed: %s", symbol, state.get("execution_details"))
    if isinstance(state, dict):
        state["timing"] = {
            **state.get("timing", {}),
            "process_symbol_seconds": round(time.perf_counter() - started, 3),
        }
    return state


def run_universe_scan(
    universe_symbols: list[str],
    regime_assessment: regime.RegimeAssessment | None = None,
) -> list[str]:
    """Check open positions, scan the universe, and run each qualifier through the graph.

    Returns the list of symbols that produced a proposal (paused at
    `human_approval`). Raises `ScanInProgressError` if a scan is already
    running (guards against overlapping `/scan` invocations).
    """
    if not _scan_lock.acquire(blocking=False):
        raise ScanInProgressError("A universe scan is already running.")

    try:
        scan_started = time.perf_counter()
        with observability.span("pipeline.run_universe_scan", symbol_count=len(universe_symbols)):
            outbox.deliver_pending(telegram_bot.send_proposal_to_chat)
            closed = monitor.check_open_trades()
            _notify_closed_trades(closed)

            if regime_assessment is not None and not regime_assessment.allow_new_entries:
                logger.warning("Scan blocked by market regime: %s", regime_assessment.reasons)
                return []

            logger.info("Scanning universe (%d symbols)...", len(universe_symbols))
            events = corporate_events.fetch_events()
            qualifiers = screener.scan_nifty_universe(universe_symbols)
            logger.info("%d symbols qualified for analysis.", len(qualifiers))

            proposed: list[str] = []
            rejected: dict[str, int] = {}
            for row in qualifiers:
                try:
                    headlines = news.fetch_headlines(row["symbol"])
                    state = process_symbol(
                        row["symbol"],
                        news_headlines=headlines,
                        snapshot=row,
                        events=events,
                    )
                except Exception:  # noqa: BLE001 - continue the rest of the universe
                    logger.exception("Universe scan failed for %s", row["symbol"])
                    continue
                if isinstance(state, dict) and state.get("__interrupt__"):
                    proposed.append(row["symbol"])
                elif isinstance(state, dict):
                    reason = state.get("rejection_reason") or state.get("execution_details", {}).get("reason", "ERROR")
                    rejected[reason] = rejected.get(reason, 0) + 1
            logger.info(
                "Scan timing: symbols=%d qualifiers=%d proposed=%d rejected=%s duration_seconds=%.3f",
                len(universe_symbols), len(qualifiers), len(proposed), rejected,
                time.perf_counter() - scan_started,
            )
            return proposed
    finally:
        _scan_lock.release()
