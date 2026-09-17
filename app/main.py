"""
Application entry point, CLI triggers and scheduler.

Responsibilities:
  * Initialize the audit database on boot (idempotent schema creation).
  * Provide a CLI to run a single symbol through the graph (for testing).
  * Provide a daily end-of-day scheduler that scans the NIFTY 100 universe,
    runs each qualifying symbol through the graph, and pushes any paused
    proposal to Telegram for human approval.
  * Start the Telegram long-polling bot in a background thread so the HITL
    approval channel is always listening.

Run modes:
    python -m app.main scan                 # one-shot universe scan + proposals
    python -m app.main run RELIANCE         # run a single symbol through graph
    python -m app.main serve                # start scheduler + telegram bot
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
from typing import Optional

from config.settings import get_settings
from app import executor, pipeline, telegram_bot

# A representative NIFTY 100 universe. In production this would be loaded from
# the official NSE NIFTY 100 constituent list; kept inline for the scaffold.
NIFTY_100_UNIVERSE: list[str] = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL",
    "ITC", "LT", "KOTAKBANK", "AXISBANK", "HINDUNILVR", "MARUTI", "SUNPHARMA",
    "TITAN", "BAJFINANCE", "ASIANPAINT", "WIPRO", "ULTRACEMCO", "NTPC",
    "POWERGRID", "TATAMOTORS", "TATASTEEL", "ADANIENT", "ADANIPORTS", "COALINDIA",
    "HCLTECH", "TATAPOWER", "M&M", "ONGC", "NOC", "JSWSTEEL", "BAJAJFINSV",
    "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP", "BRITANNIA", "EICHERMOT",
    "HINDALCO", "GRASIM", "HEROMOTOCO", "INDUSINDBK", "BAJAJ-AUTO", "SBILIFE",
    "HDFCLIFE", "TORNTPHARM", "PIDILITIND", "SIEMENS", "LTIM", "TECHM",
    "PFC", "RECLTD", "BEL", "HAL", "IRCTC", "VODAFONEIDEA", "TRENT",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
# The Telegram bot's httpx client logs every long-poll getUpdates at INFO,
# which is pure noise (each call is a held-open wait, not a heartbeat).
# Silence it; the LLM client logs under "httpx2" and stays visible.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("main")


def _start_telegram_in_background() -> None:
    """Run the blocking Telegram bot on a daemon thread."""
    thread = threading.Thread(target=telegram_bot.start_bot, name="telegram-bot", daemon=True)
    thread.start()
    logger.info("Telegram bot thread started.")


def cmd_scan(_args: argparse.Namespace) -> None:
    """One-shot: scan the universe and run each qualifier through the graph."""
    pipeline.run_universe_scan(NIFTY_100_UNIVERSE)


def cmd_run(args: argparse.Namespace) -> None:
    """Run a single symbol through the graph (for testing / manual review)."""
    pipeline.process_symbol(args.symbol.upper())


def cmd_serve(_args: argparse.Namespace) -> None:
    """Start the daily scheduler and the Telegram bot (long-running)."""
    _start_telegram_in_background()
    logger.info("Scheduler ready. Use `scan` for a manual run; daily EOD job is a no-op stub in the scaffold.")
    # Keep the process alive so the Telegram bot keeps polling.
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NIFTY 100 Swing Trading Assistant")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scan", help="Scan the universe and generate proposals")
    run_p = sub.add_parser("run", help="Run a single symbol through the graph")
    run_p.add_argument("symbol", help="NSE symbol, e.g. RELIANCE")
    sub.add_parser("serve", help="Start scheduler + Telegram bot")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    settings = get_settings()
    logger.info("TRADING_MODE=%s CAPITAL=%.2f RISK=%.1f%%",
                settings.TRADING_MODE, settings.PORTFOLIO_CAPITAL,
                settings.RISK_PER_TRADE_PCT * 100)

    # Auto-create the audit schema on boot.
    executor.init_db()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "serve":
        cmd_serve(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
