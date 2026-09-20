"""
Shared LangGraph long-term memory store lifecycle (ADR-023).

Provides PostgreSQL 16 persistence via `PostgresStore` backed by connection pooling.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import psycopg
from langgraph.store.postgres import PostgresStore
from psycopg.rows import dict_row

from config.settings import get_settings

logger = logging.getLogger(__name__)

_store: Optional[Any] = None
_connection: Optional[Any] = None


def get_store() -> PostgresStore:
    """Return the process-wide PostgresStore instance."""
    global _store, _connection
    if _store is None:
        conninfo = get_settings().DATABASE_URL.get_secret_value()
        _connection = psycopg.Connection.connect(
            conninfo, autocommit=True, prepare_threshold=0, row_factory=dict_row
        )
        _store = PostgresStore(_connection)
        _store.setup()
        logger.info("Initialized PostgresStore long-term memory store.")
    return _store


def current_connection() -> Optional[Any]:
    """Return the underlying active connection used by the store."""
    return _connection


def reset() -> None:
    """Close and clear the store instance and underlying connection."""
    global _store, _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:  # noqa: BLE001
            pass
    _store = None
    _connection = None
