"""Small SQLite-backed cache for reusable research artifacts."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from config.settings import get_settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_cache (
    namespace TEXT NOT NULL,
    cache_key TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY (namespace, cache_key)
);
"""


def _path() -> Path:
    path = Path(get_settings().DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _enabled() -> bool:
    return get_settings().RESEARCH_CACHE_ENABLED


def init_db() -> None:
    with sqlite3.connect(_path()) as conn:
        conn.executescript(_SCHEMA)


def get_value(namespace: str, cache_key: str) -> Optional[Any]:
    if not _enabled():
        return None
    init_db()
    now = datetime.now(timezone.utc)
    with sqlite3.connect(_path()) as conn:
        row = conn.execute(
            "SELECT payload, expires_at FROM research_cache WHERE namespace = ? AND cache_key = ?",
            (namespace, cache_key),
        ).fetchone()
        if row is None:
            return None
        if datetime.fromisoformat(row[1]) <= now:
            conn.execute(
                "DELETE FROM research_cache WHERE namespace = ? AND cache_key = ?",
                (namespace, cache_key),
            )
            conn.commit()
            return None
    return json.loads(row[0])


def get_value_with_status(namespace: str, cache_key: str) -> tuple[Optional[Any], bool]:
    value = get_value(namespace, cache_key)
    return value, value is not None


def set_value(namespace: str, cache_key: str, value: Any, ttl_minutes: int) -> None:
    if not _enabled():
        return
    init_db()
    created = datetime.now(timezone.utc)
    expires = created + timedelta(minutes=ttl_minutes)
    with sqlite3.connect(_path()) as conn:
        conn.execute(
            """
            INSERT INTO research_cache (namespace, cache_key, payload, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(namespace, cache_key) DO UPDATE SET
                payload = excluded.payload,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at
            """,
            (namespace, cache_key, json.dumps(value, default=str), created.isoformat(), expires.isoformat()),
        )
        conn.commit()
