"""PostgreSQL database integrity and maintenance operations."""

from __future__ import annotations

import logging
from typing import Any

from app import db

logger = logging.getLogger(__name__)


def check_databases() -> dict[str, str]:
    """Run PostgreSQL integrity and table checks, verifying connectivity."""
    results: dict[str, str] = {}
    try:
        row = db.fetchone("SELECT 1 AS alive")
        if not row or row.get("alive") != 1:
            results["postgres"] = "unhealthy"
            raise RuntimeError("PostgreSQL liveness query returned invalid result")

        # Verify key tables exist
        tables = ["trade_audit_log", "notification_outbox", "research_cache", "evidence_snapshots", "graph_threads"]
        for table in tables:
            db.fetchone(f"SELECT COUNT(*) FROM {table}")

        results["postgres"] = "ok"
    except Exception as exc:
        logger.error("PostgreSQL health check failed: %s", exc)
        results["postgres"] = f"error: {exc}"
        raise RuntimeError(f"PostgreSQL integrity check failed: {exc}") from exc

    return results


def backup_databases() -> dict[str, Any]:
    """Report PostgreSQL operational status."""
    return {"status": "managed_by_postgres_sidecar", "integrity": check_databases()}
