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
    delivered_at TEXT,
    quarantined_at TEXT,
    error TEXT
);
"""


def _db_path() -> Path:
    path = Path(get_settings().DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    with sqlite3.connect(_db_path()) as conn:
        conn.executescript(_SCHEMA)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(notification_outbox)")}
        if "quarantined_at" not in columns:
            conn.execute("ALTER TABLE notification_outbox ADD COLUMN quarantined_at TEXT")
        if "error" not in columns:
            conn.execute("ALTER TABLE notification_outbox ADD COLUMN error TEXT")
        conn.commit()


def enqueue(event_type: str, recipient: str, payload: object) -> str:
    """Persist a notification before attempting external delivery."""
    event_id = uuid.uuid4().hex
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    if not isinstance(payload, dict):
        raise TypeError("Outbox payload must be a mapping or Pydantic model")
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
            "SELECT * FROM notification_outbox "
            "WHERE delivered_at IS NULL AND quarantined_at IS NULL ORDER BY created_at"
        ).fetchall()
    return [dict(row) for row in rows]


def mark_delivered(event_id: str) -> None:
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            "UPDATE notification_outbox SET delivered_at = ? WHERE event_id = ?",
            (datetime.now(timezone.utc).isoformat(), event_id),
        )
        conn.commit()


def quarantine(event_id: str, error: str) -> None:
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            "UPDATE notification_outbox SET quarantined_at = ?, error = ? WHERE event_id = ?",
            (datetime.now(timezone.utc).isoformat(), error, event_id),
        )
        conn.commit()


def _decode_payload(raw: str) -> dict:
    payload = json.loads(raw)
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise TypeError("Outbox payload must decode to a mapping")
    return payload


def deliver_pending(sender: Callable[[str, dict], bool]) -> int:
    """Deliver pending rows and mark only confirmed sends as delivered."""
    delivered = 0
    for item in pending():
        try:
            if sender(item["recipient"], _decode_payload(item["payload"])):
                mark_delivered(item["event_id"])
                delivered += 1
        except (json.JSONDecodeError, TypeError) as exc:
            quarantine(item["event_id"], str(exc))
            logger.error("Quarantined malformed outbox event %s: %s", item["event_id"], exc)
        except Exception:  # noqa: BLE001 - failed rows remain for the next retry sweep
            logger.exception("Outbox delivery failed for event %s.", item["event_id"])
    return delivered
