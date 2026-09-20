"""Shared LangGraph long-term memory store lifecycle.

Mirrors `app/checkpoint.py`: a process-wide `SqliteStore` backed by a
persistent `sqlite3` connection in the same local-first database directory.
No new infrastructure is introduced — the store uses the same SQLite engine
already required by ADR-006, and is the native LangGraph abstraction for
cross-thread, namespaced long-term memory (operator profile, future
per-symbol research notes) as documented at
https://docs.langchain.com/oss/python/langgraph/stores.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from langgraph.store.sqlite import SqliteStore

from config.settings import get_settings

_store: Optional[SqliteStore] = None
_connection: Optional[sqlite3.Connection] = None


def get_store() -> SqliteStore:
    global _store, _connection
    if _store is None:
        db_path = Path(get_settings().STORE_DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
        _store = SqliteStore(_connection)
        _store.setup()
    return _store


def current_connection() -> Optional[sqlite3.Connection]:
    return _connection


def reset() -> None:
    global _store, _connection
    if _connection is not None:
        _connection.close()
    _store = None
    _connection = None
