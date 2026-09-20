"""Read-only operational health and status reporting."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app import executor, graph, maintenance, outbox
from app.llm import is_configured, provider_metadata
from config.settings import get_settings


def _cache_entries() -> int:
    path = Path(get_settings().DATABASE_PATH)
    if not path.exists():
        return 0
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM research_cache").fetchone()
    return int(row[0] or 0)


def get_summary() -> dict[str, Any]:
    settings = get_settings()
    trades = executor.fetch_all_trades()
    metadata = provider_metadata()
    return {
        "trading_mode": settings.TRADING_MODE,
        "llm_provider": metadata["provider"],
        "llm_model": metadata["model"],
        "llm_configured": is_configured(),
        "pending_approvals": len(graph.list_pending_approvals()),
        "open_paper_trades": sum(row.get("status") == "OPEN_PAPER" for row in trades),
        "cache_entries": _cache_entries(),
        "pending_notifications": len(outbox.pending()),
        "database_integrity": maintenance.check_databases(),
        "heartbeat": "running" if Path("data/bot_heartbeat").exists() else "not-running",
        "scan_schedule": (
            f"{settings.SCAN_CRON_HOUR:02d}:{settings.SCAN_CRON_MINUTE:02d} "
            f"{settings.SCHEDULER_TIMEZONE} {settings.SCAN_CRON_DAYS}"
        ),
    }


def format_summary(summary: dict[str, Any]) -> str:
    integrity = summary["database_integrity"]
    return "\n".join([
        "*TrAId status*",
        f"Mode: `{summary['trading_mode']}`",
        f"LLM: `{summary['llm_provider']}/{summary['llm_model']}` "
        f"({'configured' if summary['llm_configured'] else 'not configured'})",
        f"Scan schedule: `{summary['scan_schedule']}`",
        f"Pending approvals: {summary['pending_approvals']}",
        f"Open paper trades: {summary['open_paper_trades']}",
        f"Cached artifacts: {summary['cache_entries']}",
        f"Pending notifications: {summary['pending_notifications']}",
        f"Databases: audit={integrity.get('audit')} checkpoints={integrity.get('checkpoints')}",
        f"Bot heartbeat: `{summary['heartbeat']}`",
    ])
