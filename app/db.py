"""
Database connection pool and unified PostgreSQL storage abstraction (ADR-023).

Manages PostgreSQL connection pooling via `psycopg_pool.ConnectionPool` for all
relational tables, audit logs, outbox queues, research caches, and evidence snapshots.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from threading import Lock
from typing import Any, Generator, Optional, Union

from config.settings import get_settings

logger = logging.getLogger(__name__)

_pool: Optional[Any] = None
_tables_initialized = False
_tables_lock = Lock()


def is_postgres() -> bool:
    """Return True if the configured DATABASE_URL is a PostgreSQL connection."""
    url = get_settings().DATABASE_URL.get_secret_value()
    return (
        url.startswith("postgresql://")
        or url.startswith("postgres://")
        or url.startswith("postgresql+psycopg://")
    )


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
    global _tables_initialized
    if _tables_initialized:
        return
    with _tables_lock:
        if _tables_initialized:
            return
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
        mistake_category TEXT,
        highest_price   DOUBLE PRECISION,
        trailing_stop   DOUBLE PRECISION
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

        ddl_ohlcv = """
        CREATE TABLE IF NOT EXISTS ohlcv_daily_bars (
        symbol          TEXT NOT NULL,
        timestamp       TEXT NOT NULL,
        open_price      DOUBLE PRECISION NOT NULL,
        high_price      DOUBLE PRECISION NOT NULL,
        low_price       DOUBLE PRECISION NOT NULL,
        close_price     DOUBLE PRECISION NOT NULL,
        volume          BIGINT NOT NULL,
        source          TEXT NOT NULL DEFAULT 'yfinance',
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (symbol, timestamp)
    );
        """

        ddl_portfolios = """
        CREATE TABLE IF NOT EXISTS user_portfolios (
        portfolio_id    TEXT PRIMARY KEY,
        user_id         TEXT NOT NULL DEFAULT 'default_user',
        created_at      TEXT NOT NULL,
        initial_capital DOUBLE PRECISION NOT NULL,
        allocated_capital DOUBLE PRECISION NOT NULL,
        cash_balance    DOUBLE PRECISION NOT NULL,
        risk_vibe       TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'ACTIVE'
    );
        """

        ddl_positions = """
        CREATE TABLE IF NOT EXISTS user_positions (
        position_id     TEXT PRIMARY KEY,
        portfolio_id    TEXT NOT NULL,
        user_id         TEXT NOT NULL DEFAULT 'default_user',
        symbol          TEXT NOT NULL,
        shares          INTEGER NOT NULL,
        suggested_price DOUBLE PRECISION NOT NULL,
        entry_price     DOUBLE PRECISION NOT NULL,
        target_price    DOUBLE PRECISION NOT NULL,
        stop_loss_price DOUBLE PRECISION NOT NULL,
        target2_price   DOUBLE PRECISION,
        target1_shares  INTEGER,
        target2_shares  INTEGER,
        tranche1_exited BOOLEAN DEFAULT FALSE,
        breakeven_locked BOOLEAN DEFAULT FALSE,
        holding_period  TEXT,
        status          TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at      TEXT NOT NULL,
        filled_at       TEXT,
        exit_price      DOUBLE PRECISION,
        exit_at         TEXT,
        realized_pnl    DOUBLE PRECISION,
        highest_price   DOUBLE PRECISION,
        trailing_stop   DOUBLE PRECISION,
        layman_rationale TEXT,
         sector          TEXT,
         broker_name     TEXT,
         company_name    TEXT,
         isin            TEXT,
         source          TEXT NOT NULL DEFAULT 'GROWW_SYNC',
         investment_source TEXT NOT NULL DEFAULT 'GROWW_DIRECT',
         plan_status     TEXT NOT NULL DEFAULT 'NONE',
         synced_current_price DOUBLE PRECISION,
        synced_invested_amount DOUBLE PRECISION,
        synced_current_value DOUBLE PRECISION,
        synced_pnl      DOUBLE PRECISION,
        synced_pnl_pct  DOUBLE PRECISION,
        synced_last_synced_at TEXT
    );
        """

        ddl_fno_positions = """
        CREATE TABLE IF NOT EXISTS user_fno_positions (
        position_id     TEXT PRIMARY KEY,
        user_id         TEXT NOT NULL DEFAULT 'default_user',
        symbol          TEXT NOT NULL,
        instrument_type TEXT NOT NULL DEFAULT 'FUT',
        strike_price    DOUBLE PRECISION,
        expiry_date     TEXT,
        lot_size        INTEGER NOT NULL DEFAULT 1,
        quantity        INTEGER NOT NULL,
        entry_price     DOUBLE PRECISION NOT NULL,
        current_price   DOUBLE PRECISION,
        status          TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at      TEXT NOT NULL,
        last_updated    TEXT NOT NULL
    );
        """

        ddl_mutual_funds = """
        CREATE TABLE IF NOT EXISTS user_mutual_funds (
        folio_id        TEXT PRIMARY KEY,
        user_id         TEXT NOT NULL DEFAULT 'default_user',
        scheme_name     TEXT NOT NULL,
        folio_number    TEXT NOT NULL,
        units           DOUBLE PRECISION NOT NULL,
        nav             DOUBLE PRECISION NOT NULL,
        invested_amount DOUBLE PRECISION NOT NULL,
        current_value   DOUBLE PRECISION NOT NULL,
        pnl             DOUBLE PRECISION NOT NULL,
        pnl_pct         DOUBLE PRECISION NOT NULL,
        asset_category  TEXT NOT NULL DEFAULT 'EQUITY',
        last_updated    TEXT NOT NULL
    );
        """

        ddl_groww_sync_runs = """
        CREATE TABLE IF NOT EXISTS groww_sync_runs (
        run_id          TEXT PRIMARY KEY,
        user_id         TEXT NOT NULL DEFAULT 'default_user',
        started_at      TEXT NOT NULL,
        finished_at     TEXT,
        status          TEXT NOT NULL,
        holdings_found  INTEGER NOT NULL DEFAULT 0,
        synced_count    INTEGER NOT NULL DEFAULT 0,
        updated_count   INTEGER NOT NULL DEFAULT 0,
        closed_count    INTEGER NOT NULL DEFAULT 0,
        positions_found INTEGER NOT NULL DEFAULT 0,
        available_cash  DOUBLE PRECISION,
        total_margin    DOUBLE PRECISION,
        error           TEXT
    );
        """

        ddl_scheduled_jobs = """
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
        id              TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        description     TEXT NOT NULL DEFAULT '',
        action          TEXT NOT NULL,
        trigger_type    TEXT NOT NULL,
        schedule_config TEXT NOT NULL,
        timezone        TEXT NOT NULL,
        enabled         BOOLEAN NOT NULL DEFAULT TRUE,
        last_run_at     TEXT,
        last_status     TEXT,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );
        """

        ddl_scheduler_state = """
        CREATE TABLE IF NOT EXISTS scheduler_state (
        state_key       TEXT PRIMARY KEY
    );
        """

        ddl_schedule_run_requests = """
        CREATE TABLE IF NOT EXISTS schedule_run_requests (
        request_id      TEXT PRIMARY KEY,
        schedule_id     TEXT NOT NULL,
        requested_at    TEXT NOT NULL,
        claimed_at      TEXT,
        completed_at    TEXT,
        status          TEXT NOT NULL DEFAULT 'PENDING',
        error           TEXT
    );
        """

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_audit_status ON trade_audit_log(status);",
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON trade_audit_log(timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_audit_symbol ON trade_audit_log(symbol);",
            "CREATE INDEX IF NOT EXISTS idx_outbox_created ON notification_outbox(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_evidence_symbol ON evidence_snapshots(symbol);",
            "CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_ts ON ohlcv_daily_bars(symbol, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_portfolios_user ON user_portfolios(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_positions_portfolio ON user_positions(portfolio_id);",
            "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON user_positions(symbol);",
            "CREATE INDEX IF NOT EXISTS idx_positions_status ON user_positions(status);",
            "CREATE INDEX IF NOT EXISTS idx_mutual_funds_user ON user_mutual_funds(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_positions_source ON user_positions(source);",
            "CREATE INDEX IF NOT EXISTS idx_positions_synced_at ON user_positions(synced_last_synced_at);",
            "CREATE INDEX IF NOT EXISTS idx_groww_sync_runs_user_started ON groww_sync_runs(user_id, started_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_fno_user ON user_fno_positions(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_fno_status ON user_fno_positions(status);",
        ]

        with get_connection() as conn:
            cursor = conn.cursor()
            for statement in [
                ddl_audit,
                ddl_outbox,
                ddl_cache,
                ddl_evidence,
                ddl_threads,
                ddl_ohlcv,
                ddl_portfolios,
                ddl_positions,
                ddl_mutual_funds,
                ddl_groww_sync_runs,
                ddl_fno_positions,
                ddl_scheduled_jobs,
                ddl_scheduler_state,
                ddl_schedule_run_requests,
            ]:
                cursor.execute(statement)
            # Backfill 'source' column for pre-existing deployments (idempotent) before indexing it.
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'GROWW_SYNC';"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS synced_current_price DOUBLE PRECISION;"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS synced_invested_amount DOUBLE PRECISION;"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS synced_current_value DOUBLE PRECISION;"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS synced_pnl DOUBLE PRECISION;"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS synced_pnl_pct DOUBLE PRECISION;"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS synced_last_synced_at TEXT;"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS company_name TEXT;"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS current_price DOUBLE PRECISION;"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS isin TEXT;"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS investment_source TEXT NOT NULL DEFAULT 'GROWW_DIRECT';"
            )
            cursor.execute(
                "ALTER TABLE user_positions ADD COLUMN IF NOT EXISTS plan_status TEXT NOT NULL DEFAULT 'NONE';"
            )
            cursor.execute(
                """
                UPDATE user_positions
                SET source = 'BASKET', investment_source = 'PLANNED', plan_status = 'PLANNED'
                WHERE status = 'PENDING_CONFIRMATION' AND source = 'GROWW_SYNC';
                """
            )
            cursor.execute(
                """
                UPDATE user_positions
                SET investment_source = 'PLANNED',
                    plan_status = CASE WHEN status = 'ACTIVE' THEN 'BOUGHT' ELSE 'PLANNED' END
                WHERE source = 'BASKET' AND investment_source = 'GROWW_DIRECT';
                """
            )
            cursor.execute(
                """
                UPDATE user_positions
                SET investment_source = 'MANUAL', plan_status = 'NONE'
                WHERE source = 'MANUAL' AND investment_source = 'GROWW_DIRECT';
                """
            )
            cursor.execute("ALTER TABLE groww_sync_runs ADD COLUMN IF NOT EXISTS error TEXT;")
            for statement in indexes:
                cursor.execute(statement)

            _tables_initialized = True
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
