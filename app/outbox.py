"""Outbox pattern for at-least-once Telegram proposal delivery (ADR-023)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Callable

from app import db

logger = logging.getLogger(__name__)


def init_db() -> None:
    db.init_all_tables()


def enqueue(event_type: str, recipient: str, payload: object) -> str:
    """Persist a notification before attempting external delivery."""
    event_id = uuid.uuid4().hex
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    if not isinstance(payload, dict):
        raise TypeError("Outbox payload must be a mapping or Pydantic model")
    db.execute(
        "INSERT INTO notification_outbox (event_id, event_type, recipient, payload, created_at) VALUES (%s, %s, %s, %s, %s)",
        (event_id, event_type, recipient, json.dumps(payload, default=str), datetime.now(timezone.utc).isoformat()),
    )
    return event_id


def pending() -> list[dict]:
    """Return undelivered notifications in creation order."""
    return db.fetchall(
        "SELECT * FROM notification_outbox "
        "WHERE delivered_at IS NULL AND quarantined_at IS NULL ORDER BY created_at"
    )


def mark_delivered(event_id: str) -> None:
    db.execute(
        "UPDATE notification_outbox SET delivered_at = %s WHERE event_id = %s",
        (datetime.now(timezone.utc).isoformat(), event_id),
    )


def quarantine(event_id: str, error: str) -> None:
    db.execute(
        "UPDATE notification_outbox SET quarantined_at = %s, error = %s WHERE event_id = %s",
        (datetime.now(timezone.utc).isoformat(), error, event_id),
    )


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
