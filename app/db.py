"""
Database connection pool and unified PostgreSQL storage abstraction (ADR-023).

Manages PostgreSQL connection pooling via `psycopg_pool.ConnectionPool` for all
relational tables, audit logs, outbox queues, research caches, and evidence snapshots.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional, Union

from config.settings import get_settings

logger = logging.getLogger(__name__)

_pool: Optional[Any] = None


def is_postgres() -> bool:
    """Return True if the configured DATABASE_URL is a PostgreSQL connection."""
    url = get_settings().DATABASE_URL.get_secret_value()
    return url.startswith("postgresql://") or url.startswith("postgres://") or url.startswith("postgresql+psycopg://")


def get_connection_pool() -> Any:
    """Return or initialize the singleton psycopg connection pool."""
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool

        conninfo = get_settings().DATABASE_URL.get_secret_value()
        min_size = get_settings().DB_POOL_MIN_SIZE
        max_size = get_settings().DB_POOL_MAX_SIZE
        _pool = ConnectionPool(conninfo=conninfo, min_size=min_size, max_size=max_size, open=True)
    return _pool


@contextmanager
def get_connection() -> Generator[Any, None, None]:
    """Yield an open database connection from the PostgreSQL connection pool."""
    pool = get_connection_pool()
    with pool.connection() as conn:
        yield conn


def execute(query: str, params: Union[tuple, list, dict] = ()) -> Any:
    """Execute a query with parameter substitution against PostgreSQL."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor


def fetchall(query: str, params: Union[tuple, list, dict] = ()) -> list[dict[str, Any]]:
    """Execute a query and return all matching rows as dictionaries."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row, strict=False)) for row in rows]


def fetchone(query: str, params: Union[tuple, list, dict] = ()) -> Optional[dict[str, Any]]:
    """Execute a query and return the first matching row as a dictionary."""
    rows = fetchall(query, params)
    return rows[0] if rows else None


def init_all_tables() -> None:
    """Create all required PostgreSQL relational tables and indexes (idempotent)."""
    ddl_audit = """
    CREATE TABLE IF NOT EXISTS trade_audit_log (
        trade_id        TEXT PRIMARY KEY,
        timestamp       TEXT NOT NULL,
        symbol          TEXT NOT NULL,
        entry_price     DOUBLE PRECISION NOT NULL,
        soft_stop       DOUBLE PRECISION NOT NULL,
        hard_stop       DOUBLE PRECISION NOT NULL,
        target_price    DOUBLE PRECISION NOT NULL,
        quantity        INTEGER NOT NULL,
        rsi             DOUBLE PRECISION,
        ema_200         DOUBLE PRECISION,
        atr             DOUBLE PRECISION,
        thesis          TEXT,
        headlines_used  TEXT,
        human_decision  TEXT,
        fill_price      DOUBLE PRECISION,
        status          TEXT NOT NULL DEFAULT 'OPEN_PAPER',
        exit_price      DOUBLE PRECISION,
        realized_pnl    DOUBLE PRECISION,
        gross_pnl       DOUBLE PRECISION,
        transaction_costs TEXT,
        evidence_snapshot_id TEXT,
        strategy_name   TEXT,
        market_regime   TEXT,
        catalyst_type   TEXT,
        source_set      TEXT,
        llm_provider    TEXT,
        llm_model       TEXT,
        cache_hits      TEXT,
        mistake_category TEXT
    );
    """

    ddl_outbox = """
    CREATE TABLE IF NOT EXISTS notification_outbox (
        event_id        TEXT PRIMARY KEY,
        event_type      TEXT NOT NULL,
        recipient       TEXT NOT NULL,
        payload         TEXT NOT NULL,
        created_at      TEXT NOT NULL,
        delivered_at    TEXT,
        quarantined_at  TEXT,
        error           TEXT
    );
    """

    ddl_cache = """
    CREATE TABLE IF NOT EXISTS research_cache (
        namespace       TEXT NOT NULL,
        cache_key       TEXT NOT NULL,
        payload         TEXT NOT NULL,
        created_at      TEXT NOT NULL,
        expires_at      TEXT NOT NULL,
        PRIMARY KEY (namespace, cache_key)
    );
    """

    ddl_evidence = """
    CREATE TABLE IF NOT EXISTS evidence_snapshots (
        snapshot_id     TEXT PRIMARY KEY,
        created_at      TEXT NOT NULL,
        symbol          TEXT NOT NULL,
        payload         TEXT NOT NULL
    );
    """

    ddl_threads = """
    CREATE TABLE IF NOT EXISTS graph_threads (
        thread_id       TEXT PRIMARY KEY,
        symbol          TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );
    """

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_audit_status ON trade_audit_log(status);",
        "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON trade_audit_log(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_audit_symbol ON trade_audit_log(symbol);",
        "CREATE INDEX IF NOT EXISTS idx_outbox_created ON notification_outbox(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_evidence_symbol ON evidence_snapshots(symbol);",
    ]

    with get_connection() as conn:
        cursor = conn.cursor()
        for statement in [ddl_audit, ddl_outbox, ddl_cache, ddl_evidence, ddl_threads] + indexes:
            cursor.execute(statement)

    logger.info("All relational tables and indexes initialized successfully.")


def reset() -> None:
    """Close active connection pool and clear cached pool instances."""
    global _pool
    if _pool is not None:
        try:
            _pool.close()
        except Exception:  # noqa: BLE001
            pass
        _pool = None
