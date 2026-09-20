"""Research cache abstraction backed by relational storage (ADR-023)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app import db
from config.settings import get_settings


def _enabled() -> bool:
    return get_settings().RESEARCH_CACHE_ENABLED


def init_db() -> None:
    db.init_all_tables()


def get_value(namespace: str, cache_key: str) -> Optional[Any]:
    if not _enabled():
        return None
    now = datetime.now(timezone.utc)
    row = db.fetchone(
        "SELECT payload, expires_at FROM research_cache WHERE namespace = %s AND cache_key = %s",
        (namespace, cache_key),
    )
    if row is None:
        return None
    if datetime.fromisoformat(row["expires_at"]) <= now:
        db.execute(
            "DELETE FROM research_cache WHERE namespace = %s AND cache_key = %s",
            (namespace, cache_key),
        )
        return None
    return json.loads(row["payload"])


def get_value_with_status(namespace: str, cache_key: str) -> tuple[Optional[Any], bool]:
    value = get_value(namespace, cache_key)
    return value, value is not None


def set_value(namespace: str, cache_key: str, value: Any, ttl_minutes: int) -> None:
    if not _enabled():
        return
    created = datetime.now(timezone.utc)
    expires = created + timedelta(minutes=ttl_minutes)
    db.execute(
        """
        INSERT INTO research_cache (namespace, cache_key, payload, created_at, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT(namespace, cache_key) DO UPDATE SET
            payload = EXCLUDED.payload,
            created_at = EXCLUDED.created_at,
            expires_at = EXCLUDED.expires_at
        """,
        (namespace, cache_key, json.dumps(value, default=str), created.isoformat(), expires.isoformat()),
    )


def get_or_set(
    namespace: str,
    cache_key: str,
    fetcher: Any,
    ttl_minutes: int,
    force_refresh: bool = False,
) -> Any:
    """Fetch value from cache, or invoke fetcher and cache the result."""
    if not force_refresh:
        cached = get_value(namespace, cache_key)
        if cached is not None:
            return cached
    fresh = fetcher()
    set_value(namespace, cache_key, fresh, ttl_minutes)
    return fresh

