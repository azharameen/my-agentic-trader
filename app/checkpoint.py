"""Shared LangGraph checkpoint lifecycle."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from langgraph.checkpoint.sqlite import SqliteSaver

from config.settings import get_settings

_checkpointer: Optional[SqliteSaver] = None
_connection: Optional[sqlite3.Connection] = None


def get_checkpointer() -> SqliteSaver:
    global _checkpointer, _connection
    if _checkpointer is None:
        db_path = Path(get_settings().CHECKPOINT_DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(db_path), check_same_thread=False)
        _checkpointer = SqliteSaver(_connection)
    return _checkpointer


def current_connection() -> Optional[sqlite3.Connection]:
    return _connection


def reset() -> None:
    global _checkpointer, _connection
    if _connection is not None:
        _connection.close()
    _checkpointer = None
    _connection = None
