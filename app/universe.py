"""
NIFTY 100 constituent universe — trustworthy, self-refreshing, zero hardcoding.

Replaces any hand-maintained symbol list with a fallback chain:

    1. Runtime cache (`data/universe/nifty100.csv`) — auto-refreshed live
       snapshot, gitignored (regenerated per environment).
    2. If the cache is missing or older than `UNIVERSE_REFRESH_DAYS`, attempt a
       live fetch from the official NSE Indices CSV endpoint (with retries).
       On success this becomes the new cache.
    3. If the live fetch fails and no cache exists, fall back to the committed
       seed snapshot (`config/universe/nifty100_seed.csv`) so the app always
       has a genuine, working NIFTY 100 list — even offline on a fresh clone.

Every path is logged so it is always clear which source produced the universe
for a given run (LIVE_FETCH / CACHE / SEED_FALLBACK).
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from app.retry import network_retry
from config.settings import get_settings

logger = logging.getLogger(__name__)

_MIN_EXPECTED_ROWS = 90
_MAX_EXPECTED_ROWS = 110
COL_COMPANY = "Company Name"
COL_INDUSTRY = "Industry"
COL_SYMBOL = "Symbol"
COL_SERIES = "Series"
COL_ISIN = "ISIN Code"
_CSV_FIELDNAMES = [COL_COMPANY, COL_INDUSTRY, COL_SYMBOL, COL_SERIES, COL_ISIN]
_REQUIRED_COLUMNS = set(_CSV_FIELDNAMES)
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
}
_resolved_cache: Optional[list[dict]] = None


class UniverseFetchError(RuntimeError):
    """Raised when the live source returns unusable data (network, schema, or size)."""


def _parse_csv(raw_text: str) -> list[dict]:
    """Parse the NSE Indices CSV text into row dicts, validating shape."""
    reader = csv.DictReader(io.StringIO(raw_text))
    rows = [row for row in reader if row.get(COL_SYMBOL)]

    if not _REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])):
        raise UniverseFetchError(f"Unexpected CSV columns: {reader.fieldnames}")
    if not (_MIN_EXPECTED_ROWS <= len(rows) <= _MAX_EXPECTED_ROWS):
        raise UniverseFetchError(f"Unexpected row count: {len(rows)} (expected ~100)")
    return rows


@network_retry(
    max_attempts=3,
    min_wait=1.0,
    max_wait=8.0,
    retry_exceptions=(requests.RequestException, UniverseFetchError),
)
def _fetch_live_csv_text() -> str:
    settings = get_settings()
    resp = requests.get(settings.UNIVERSE_SOURCE_URL, headers=_BROWSER_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def fetch_live_universe() -> list[dict]:
    """Fetch and validate the live NIFTY 100 constituent list.

    Raises `UniverseFetchError` (or a `requests` exception) if the source is
    unreachable or returns data that doesn't look like a genuine constituent
    list. Callers should catch broadly and fall back to cache/seed.
    """
    raw_text = _fetch_live_csv_text()
    rows = _parse_csv(raw_text)
    logger.info("Fetched live NIFTY 100 universe: %d symbols.", len(rows))
    return rows


def _rows_to_symbols(rows: list[dict]) -> list[str]:
    return [row[COL_SYMBOL].strip().upper() for row in rows]


def _write_cache(rows: list[dict]) -> None:
    settings = get_settings()
    cache_path = Path(settings.UNIVERSE_CACHE_PATH)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    with cache_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    meta = {
        "source": settings.UNIVERSE_SOURCE_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
    }
    cache_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _load_rows_from_csv(path: Path) -> Optional[list[dict]]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return _parse_csv(f.read())
    except (UniverseFetchError, OSError) as exc:
        logger.warning("Could not parse universe file %s: %s", path, exc)
        return None


def _load_cache() -> Optional[tuple[list[dict], dict]]:
    settings = get_settings()
    cache_path = Path(settings.UNIVERSE_CACHE_PATH)
    meta_path = cache_path.with_suffix(".meta.json")

    rows = _load_rows_from_csv(cache_path)
    if rows is None:
        return None

    meta: dict = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    return rows, meta


def _cache_is_stale(meta: dict) -> bool:
    settings = get_settings()
    fetched_at = meta.get("fetched_at")
    if not fetched_at:
        return True
    try:
        fetched_dt = datetime.fromisoformat(fetched_at)
    except ValueError:
        return True
    age_days = (datetime.now(timezone.utc) - fetched_dt).days
    return age_days >= settings.UNIVERSE_REFRESH_DAYS


def _load_seed() -> list[dict]:
    settings = get_settings()
    seed_path = Path(settings.UNIVERSE_SEED_PATH)
    rows = _load_rows_from_csv(seed_path)
    if rows is None:
        raise UniverseFetchError(
            f"Committed seed universe file is missing or unparseable: {seed_path}"
        )
    return rows


def _resolve_rows(force_refresh: bool = False) -> list[dict]:
    """Resolve the current universe rows using the same fallback chain everywhere."""
    global _resolved_cache
    if _resolved_cache is not None and not force_refresh:
        return _resolved_cache
    cached = _load_cache()

    if not force_refresh and cached is not None:
        rows, meta = cached
        if not _cache_is_stale(meta):
            logger.info("Universe source: CACHE (%d symbols, fetched_at=%s)",
                        len(rows), meta.get("fetched_at"))
            _resolved_cache = rows
            return rows

    try:
        rows = fetch_live_universe()
        _write_cache(rows)
        logger.info("Universe source: LIVE_FETCH (%d symbols)", len(rows))
        _resolved_cache = rows
        return rows
    except Exception as exc:  # noqa: BLE001 - any network/schema failure falls back
        logger.warning("Live universe fetch failed (%s); falling back.", exc)

    if cached is not None:
        rows, meta = cached
        logger.warning("Universe source: STALE CACHE (%d symbols, fetched_at=%s)",
                       len(rows), meta.get("fetched_at"))
        _resolved_cache = rows
        return rows

    rows = _load_seed()
    logger.warning("Universe source: SEED_FALLBACK (%d symbols)", len(rows))
    _resolved_cache = rows
    return rows


def clear_cache() -> None:
    global _resolved_cache
    _resolved_cache = None


def cache_size() -> int:
    return 1 if _resolved_cache is not None else 0


def get_universe(force_refresh: bool = False) -> list[str]:
    """Return the current NIFTY 100 symbol list via the fallback chain.

    Resolution order: fresh cache -> live fetch (refreshing the cache on
    success) -> stale cache -> committed seed. Never raises; always returns a
    usable, genuine NIFTY 100 list.
    """
    return _rows_to_symbols(_resolve_rows(force_refresh=force_refresh))


def get_universe_with_industries() -> dict[str, str]:
    """Return `{symbol: industry}` for the current universe (sector-risk / news-alias use)."""
    rows = _resolve_rows()
    return {row[COL_SYMBOL].strip().upper(): row[COL_INDUSTRY].strip() for row in rows}


def get_symbol_company_names() -> dict[str, str]:
    """Return `{symbol: company_name}` — used to match news headlines to symbols."""
    rows = _resolve_rows()
    return {row[COL_SYMBOL].strip().upper(): row[COL_COMPANY].strip() for row in rows}


def diff_universe(old: list[str], new: list[str]) -> dict:
    """Return `{"added": [...], "removed": [...]}` between two symbol lists."""
    old_set, new_set = set(old), set(new)
    return {
        "added": sorted(new_set - old_set),
        "removed": sorted(old_set - new_set),
    }
