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
from typing import Optional

from config.settings import get_settings
from app import graph, screener, telegram_bot

logger = logging.getLogger(__name__)


def process_symbol(symbol: str, news_headlines: Optional[list[str]] = None) -> dict:
    """Run one symbol through the graph and push any proposal to Telegram.

    Returns the final graph state (or the interrupt state if paused at
    `human_approval`).
    """
    logger.info("Processing %s ...", symbol)
    state = graph.run_symbol(symbol, news_headlines)

    interrupts = state.get("__interrupt__") if isinstance(state, dict) else None
    if interrupts:
        payload = interrupts[0].value
        logger.info("Graph paused at human_approval for %s; pushing to Telegram.", symbol)
        telegram_bot._send_proposal_to_chat(get_settings().TELEGRAM_CHAT_ID, payload)
    else:
        logger.info("Thread for %s completed: %s", symbol, state.get("execution_details"))
    return state


def run_universe_scan(universe: list[str]) -> list[str]:
    """Scan the universe and run each qualifier through the graph.

    Returns the list of symbols that produced a proposal (paused at
    `human_approval`).
    """
    logger.info("Scanning universe (%d symbols)...", len(universe))
    qualifiers = screener.scan_nifty_universe(universe)
    logger.info("%d symbols qualified for analysis.", len(qualifiers))

    proposed: list[str] = []
    for row in qualifiers:
        state = process_symbol(row["symbol"])
        if isinstance(state, dict) and state.get("__interrupt__"):
            proposed.append(row["symbol"])
    return proposed
