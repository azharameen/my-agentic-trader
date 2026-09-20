"""Normalized evidence contracts and immutable snapshot persistence (ADR-023)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app import db
from config.settings import get_settings


class Provenance(BaseModel):
    source: str
    fetched_at: datetime
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    content_hash: Optional[str] = None
    freshness_seconds: Optional[float] = Field(default=None, ge=0)
    validation_status: Literal["VALID", "STALE", "MISSING", "CONFLICT"] = "VALID"


class EvidenceItem(BaseModel):
    kind: Literal["MARKET", "NEWS", "CORPORATE_EVENT", "FUNDAMENTAL", "FLOW", "REGIME"]
    symbol: Optional[str] = None
    payload: dict
    provenance: Provenance


class EvidenceSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: Optional[str] = None
    items: list[EvidenceItem]

    @property
    def source_set(self) -> list[str]:
        return sorted({item.provenance.source for item in self.items})


def content_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_snapshot(snapshot: EvidenceSnapshot, max_age_seconds: Optional[float] = None) -> None:
    """Reject missing or conflicting critical evidence before proposal use."""
    if max_age_seconds is None:
        max_age_seconds = get_settings().EVIDENCE_MAX_AGE_SECONDS or None
    if not snapshot.items:
        raise ValueError("Evidence snapshot must contain at least one item")
    for item in snapshot.items:
        if item.provenance.validation_status in {"MISSING", "CONFLICT"}:
            raise ValueError(f"Evidence is {item.provenance.validation_status}: {item.kind}")
        if max_age_seconds is not None:
            age = (datetime.now(timezone.utc) - item.provenance.fetched_at).total_seconds()
            if age > max_age_seconds:
                raise ValueError(f"Evidence is stale: {item.kind}")


def init_db() -> None:
    db.init_all_tables()


def save_snapshot(snapshot: EvidenceSnapshot) -> str:
    db.init_all_tables()
    payload = snapshot.model_dump_json()
    db.execute(
        "INSERT INTO evidence_snapshots (snapshot_id, created_at, symbol, payload) VALUES (%s, %s, %s, %s)",
        (snapshot.snapshot_id, snapshot.created_at.isoformat(), snapshot.symbol, payload),
    )
    return snapshot.snapshot_id


def load_snapshot(snapshot_id: str) -> EvidenceSnapshot:
    db.init_all_tables()
    row = db.fetchone(
        "SELECT payload FROM evidence_snapshots WHERE snapshot_id = %s", (snapshot_id,)
    )
    if row is None:
        raise ValueError(f"Unknown evidence snapshot: {snapshot_id}")
    return EvidenceSnapshot.model_validate_json(row["payload"])

