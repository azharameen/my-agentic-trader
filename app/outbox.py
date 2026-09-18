"""SQLite outbox for at-least-once Telegram proposal delivery."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from config.settings import get_settings

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notification_outbox (
    event_id    TEXT PRIMARY KEY,
    event_type  TEXT NOT NULL,
    recipient   TEXT NOT NULL,
    payload     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    delivered_at TEXT
);
"""


def _db_path() -> Path:
    path = Path(get_settings().DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    with sqlite3.connect(_db_path()) as conn:
        conn.executescript(_SCHEMA)


def enqueue(event_type: str, recipient: str, payload: dict) -> str:
    """Persist a notification before attempting external delivery."""
    event_id = uuid.uuid4().hex
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            "INSERT INTO notification_outbox (event_id, event_type, recipient, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (event_id, event_type, recipient, json.dumps(payload, default=str), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return event_id


def pending() -> list[dict]:
    """Return undelivered notifications in creation order."""
    with sqlite3.connect(_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM notification_outbox WHERE delivered_at IS NULL ORDER BY created_at"
        ).fetchall()
    return [dict(row) for row in rows]


def mark_delivered(event_id: str) -> None:
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            "UPDATE notification_outbox SET delivered_at = ? WHERE event_id = ?",
            (datetime.now(timezone.utc).isoformat(), event_id),
        )
        conn.commit()


def deliver_pending(sender: Callable[[str, dict], bool]) -> int:
    """Deliver pending rows and mark only confirmed sends as delivered."""
    delivered = 0
    for item in pending():
        try:
            if sender(item["recipient"], json.loads(item["payload"])):
                mark_delivered(item["event_id"])
                delivered += 1
        except Exception:  # noqa: BLE001 - failed rows remain for the next retry sweep
            logger.exception("Outbox delivery failed for event %s.", item["event_id"])
    return delivered
