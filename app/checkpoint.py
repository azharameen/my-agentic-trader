"""
Shared LangGraph checkpoint lifecycle (ADR-023).

Provides PostgreSQL 16 persistence via `PostgresSaver` backed by connection pooling.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row

from config.settings import get_settings

logger = logging.getLogger(__name__)

_checkpointer: Optional[Any] = None
_connection: Optional[Any] = None


def get_checkpointer() -> PostgresSaver:
    """Return the process-wide PostgresSaver checkpointer instance."""
    global _checkpointer, _connection
    if _checkpointer is None:
        conninfo = get_settings().DATABASE_URL.get_secret_value()
        _connection = psycopg.Connection.connect(
            conninfo, autocommit=True, prepare_threshold=0, row_factory=dict_row
        )
        _checkpointer = PostgresSaver(_connection)
        _checkpointer.setup()
        logger.info("Initialized PostgresSaver checkpointer.")
    return _checkpointer


def current_connection() -> Optional[Any]:
    """Return the underlying active connection used by the checkpointer."""
    return _connection


def reset() -> None:
    """Close and clear the checkpointer instance and underlying connection."""
    global _checkpointer, _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:  # noqa: BLE001
            pass
    _checkpointer = None
    _connection = None
