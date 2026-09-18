"""Normalized corporate events and deterministic event-risk policy."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, Field

from app import evidence
from config.settings import get_settings

logger = logging.getLogger(__name__)


class CorporateEventType(StrEnum):
    EARNINGS = "EARNINGS"
    BOARD_MEETING = "BOARD_MEETING"
    DIVIDEND = "DIVIDEND"
    SPLIT = "SPLIT"
    BONUS = "BONUS"
    RIGHTS = "RIGHTS"
    PLEDGE = "PLEDGE"
    ANNOUNCEMENT = "ANNOUNCEMENT"


class CorporateEvent(BaseModel):
    symbol: str
    event_type: CorporateEventType
    event_date: date
    title: str
    source: str
    source_url: Optional[str] = None
    published_at: Optional[datetime] = None
    isin: Optional[str] = None
    details: dict = Field(default_factory=dict)
    provenance: Optional[evidence.Provenance] = None

    @property
    def event_id(self) -> str:
        value = "|".join(
            [
                self.symbol.upper(),
                self.event_type.value,
                self.event_date.isoformat(),
                self.title.strip().lower(),
                self.source,
            ]
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


def deduplicate_events(events: Iterable[CorporateEvent]) -> list[CorporateEvent]:
    """Return stable first-seen events, keyed by deterministic event ID."""
    unique: dict[str, CorporateEvent] = {}
    for event in events:
        unique.setdefault(event.event_id, event)
    return list(unique.values())


def events_in_window(
    events: Iterable[CorporateEvent],
    symbol: str,
    *,
    start: date,
    holding_days: int = 10,
) -> list[CorporateEvent]:
    end = start + timedelta(days=holding_days)
    return [
        event
        for event in deduplicate_events(events)
        if event.symbol.upper() == symbol.upper()
        and event.event_date >= start
        and event.event_date <= end
    ]


def blackout_reason(
    events: Iterable[CorporateEvent],
    symbol: str,
    *,
    as_of: Optional[date] = None,
    holding_days: int = 10,
) -> Optional[str]:
    """Return a deterministic rejection reason for material upcoming events."""
    upcoming = events_in_window(
        events,
        symbol,
        start=as_of or datetime.now(timezone.utc).date(),
        holding_days=holding_days,
    )
    material = {
        CorporateEventType.EARNINGS,
        CorporateEventType.BOARD_MEETING,
        CorporateEventType.PLEDGE,
    }
    blocked = [event for event in upcoming if event.event_type in material]
    if not blocked:
        return None
    return f"CORPORATE_EVENT_BLACKOUT:{blocked[0].event_type.value}"


def to_evidence_items(events: Iterable[CorporateEvent]) -> list[evidence.EvidenceItem]:
    return [
        evidence.EvidenceItem(
            kind="CORPORATE_EVENT",
            symbol=event.symbol,
            payload=json.loads(event.model_dump_json()),
            provenance=event.provenance
            or evidence.Provenance(
                source=event.source,
                fetched_at=datetime.now(timezone.utc),
                published_at=event.published_at,
                url=event.source_url,
            ),
        )
        for event in deduplicate_events(events)
    ]


def _event_from_row(row: dict) -> CorporateEvent:
    return CorporateEvent.model_validate(row)


def parse_event_rows(rows: Iterable[dict]) -> list[CorporateEvent]:
    """Parse independent rows, skipping malformed records without aborting."""
    parsed: list[CorporateEvent] = []
    for row in rows:
        try:
            parsed.append(_event_from_row(row))
        except Exception as exc:  # noqa: BLE001 - one bad disclosure must not abort collection
            logger.warning("Skipping malformed corporate event: %s", exc)
    return deduplicate_events(parsed)


def events_for_identity(
    events: Iterable[CorporateEvent],
    *,
    symbol: str,
    isin: Optional[str] = None,
) -> list[CorporateEvent]:
    """Match by NSE symbol or ISIN without fuzzy company-name guessing."""
    normalized_symbol = symbol.strip().upper()
    normalized_isin = isin.strip().upper() if isin else None
    return [
        event
        for event in deduplicate_events(events)
        if event.symbol.strip().upper() == normalized_symbol
        or (normalized_isin and event.isin and event.isin.strip().upper() == normalized_isin)
    ]


def _load_cached_events() -> list[CorporateEvent]:
    path = Path(get_settings().CORPORATE_EVENTS_CACHE_PATH)
    if not path.exists():
        return []
    try:
        return parse_event_rows(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Could not load corporate-event cache: %s", exc)
        return []


def fetch_events() -> list[CorporateEvent]:
    """Load configured event data, falling back to the local cache.

    The source is intentionally disabled by default until its access terms and
    schema are reviewed. The adapter accepts a JSON URL returning a list of
    normalized event rows; exchange-specific parsing belongs in a reviewed
    source adapter rather than this policy module.
    """
    settings = get_settings()
    if not settings.CORPORATE_EVENTS_ENABLED or not settings.CORPORATE_EVENTS_SOURCE_URL:
        return _load_cached_events()
    try:
        import requests

        response = requests.get(settings.CORPORATE_EVENTS_SOURCE_URL, timeout=15)
        response.raise_for_status()
        events = parse_event_rows(response.json())
        if events:
            path = Path(settings.CORPORATE_EVENTS_CACHE_PATH)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps([event.model_dump(mode="json") for event in events], indent=2),
                encoding="utf-8",
            )
            return events
    except Exception as exc:  # noqa: BLE001 - source failure falls back to cache
        logger.warning("Corporate-event source failed: %s", exc)
    return _load_cached_events()
