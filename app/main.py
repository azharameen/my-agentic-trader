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
import signal
import sys
import threading
from typing import Any, Optional

from app import evaluation, executor, maintenance, observability, pipeline, telegram_bot, universe
from config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
# The Telegram bot's httpx client logs every long-poll getUpdates at INFO,
# which is pure noise (each call is a held-open wait, not a heartbeat).
# Silence it; the LLM client logs under "httpx2" and stays visible.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("main")


def _start_telegram_in_background() -> threading.Thread:
    """Run the blocking Telegram bot on a daemon thread."""
    thread = threading.Thread(target=telegram_bot.start_bot, name="telegram-bot", daemon=True)
    thread.start()
    logger.info("Telegram bot thread started.")
    return thread


def cmd_scan(_args: argparse.Namespace) -> None:
    """One-shot: scan the universe and run each qualifier through the graph."""
    pipeline.run_universe_scan(universe.get_universe())


def cmd_run(args: argparse.Namespace) -> None:
    """Run a single symbol through the graph (for testing / manual review)."""
    pipeline.process_symbol(args.symbol.upper())


def cmd_refresh_universe(_args: argparse.Namespace) -> None:
    """Force a live refresh of the NIFTY 100 universe and report the diff."""
    old = universe.get_universe()
    new = universe.get_universe(force_refresh=True)
    delta = universe.diff_universe(old, new)
    logger.info("Universe refreshed: %d symbols. Added=%s Removed=%s",
                len(new), delta["added"], delta["removed"])


def cmd_check_databases(_args: argparse.Namespace) -> None:
    logger.info("Database integrity: %s", maintenance.check_databases())


def cmd_backup_databases(_args: argparse.Namespace) -> None:
    logger.info("Database backups created: %s", maintenance.backup_databases())


def cmd_evaluate(_args: argparse.Namespace) -> None:
    logger.info("Paper evaluation: %s", evaluation.summarize_trades(executor.fetch_all_trades()))


def cmd_history(args: argparse.Namespace) -> None:
    """Print the full LangGraph checkpoint (time-travel) history for a symbol."""
    from app import graph

    history = graph.symbol_history(args.symbol.upper())
    if not history:
        logger.info("No pipeline run recorded for %s yet.", args.symbol.upper())
        return
    for step in reversed(history):
        logger.info(
            "step=%s next=%s paused_for_approval=%s values=%s",
            step["created_at"], step["next"], step["paused_for_approval"], step["values"],
        )


def _scheduled_scan() -> None:
    """apscheduler job: run the daily universe scan."""
    try:
        pipeline.run_universe_scan(universe.get_universe())
    except Exception:  # noqa: BLE001 - a bad scheduled run must not kill the scheduler
        logger.exception("Scheduled scan failed.")


def _scheduled_universe_refresh() -> None:
    """apscheduler job: monthly forced universe refresh, notifies Telegram of changes."""
    try:
        old = universe.get_universe()
        new = universe.get_universe(force_refresh=True)
        delta = universe.diff_universe(old, new)
        if delta["added"] or delta["removed"]:
            settings = get_settings()
            text = (
                "\U0001F504 *NIFTY 100 universe updated*\n"
                f"Added: {', '.join(delta['added']) or 'none'}\n"
                f"Removed: {', '.join(delta['removed']) or 'none'}"
            )
            telegram_bot.notify_text(settings.TELEGRAM_CHAT_ID, text)
    except Exception:  # noqa: BLE001
        logger.exception("Scheduled universe refresh failed.")


def _start_scheduler() -> Any:
    """Wire the daily EOD scan and the monthly universe refresh into apscheduler."""
    from apscheduler.schedulers.background import BackgroundScheduler

    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)
    scheduler.add_job(
        _scheduled_scan, "cron",
        hour=settings.SCAN_CRON_HOUR, minute=settings.SCAN_CRON_MINUTE,
        day_of_week=settings.SCAN_CRON_DAYS, id="daily_scan",
    )
    scheduler.add_job(
        _scheduled_universe_refresh, "cron",
        day=int(settings.UNIVERSE_REFRESH_DAY_OF_MONTH), hour=int(settings.UNIVERSE_REFRESH_HOUR),
        minute=int(settings.UNIVERSE_REFRESH_MINUTE), id="monthly_universe_refresh",
    )
    scheduler.start()
    logger.info("Scheduler started: daily scan at %02d:%02d %s (%s), monthly universe refresh on day %s at %02d:%02d %s.",
                settings.SCAN_CRON_HOUR, settings.SCAN_CRON_MINUTE,
                settings.SCHEDULER_TIMEZONE, settings.SCAN_CRON_DAYS,
                settings.UNIVERSE_REFRESH_DAY_OF_MONTH,
                int(settings.UNIVERSE_REFRESH_HOUR), int(settings.UNIVERSE_REFRESH_MINUTE),
                settings.SCHEDULER_TIMEZONE)
    return scheduler


def cmd_serve(_args: argparse.Namespace) -> None:
    """Start the daily scheduler and the Telegram bot (long-running)."""
    bot_thread = _start_telegram_in_background()
    scheduler = _start_scheduler()
    shutdown = threading.Event()

    def request_shutdown(signum: int, _frame: object) -> None:
        logger.info("Shutdown requested by signal %s.", signum)
        shutdown.set()

    previous_sigint = signal.signal(signal.SIGINT, request_shutdown)
    previous_sigterm = signal.signal(signal.SIGTERM, request_shutdown)
    try:
        while not shutdown.wait(timeout=1):
            pass
    except KeyboardInterrupt:
        shutdown.set()
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)
        logger.info("Shutting down services...")
        scheduler.shutdown(wait=False)
        telegram_bot.stop_bot()
        if bot_thread.is_alive():
            bot_thread.join(timeout=10)
        logger.info("Shutdown complete.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NIFTY 100 Swing Trading Assistant")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scan", help="Scan the universe and generate proposals")
    run_p = sub.add_parser("run", help="Run a single symbol through the graph")
    run_p.add_argument("symbol", help="NSE symbol, e.g. RELIANCE")
    sub.add_parser("serve", help="Start scheduler + Telegram bot")
    sub.add_parser("refresh-universe", help="Force a live refresh of the NIFTY 100 universe")
    sub.add_parser("check-databases", help="Check local SQLite database integrity")
    sub.add_parser("backup-databases", help="Back up local SQLite databases")
    sub.add_parser("evaluate", help="Evaluate paper-trade outcomes")
    history_p = sub.add_parser("history", help="Show full checkpoint history for one symbol (time travel)")
    history_p.add_argument("symbol", help="NSE symbol, e.g. RELIANCE")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    settings = get_settings()
    logger.info("TRADING_MODE=%s CAPITAL=%.2f RISK=%.1f%%",
                settings.TRADING_MODE, settings.PORTFOLIO_CAPITAL,
                settings.RISK_PER_TRADE_PCT * 100)

    # Auto-create the audit schema on boot.
    observability.configure()
    executor.init_db()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "refresh-universe":
        cmd_refresh_universe(args)
    elif args.command == "check-databases":
        cmd_check_databases(args)
    elif args.command == "backup-databases":
        cmd_backup_databases(args)
    elif args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "history":
        cmd_history(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
