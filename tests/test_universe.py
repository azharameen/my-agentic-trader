"""Unit tests for the universe fallback chain (app/universe.py)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app import universe

_VALID_CSV = (
    "Company Name,Industry,Symbol,Series,ISIN Code\n"
    + "\n".join(f"Company {i} Ltd.,Sector {i % 5},SYM{i:03d},EQ,INE{i:06d}01" for i in range(100))
    + "\n"
)


def _write_seed(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_VALID_CSV, encoding="utf-8")


def test_parse_csv_accepts_valid_shape():
    rows = universe._parse_csv(_VALID_CSV)
    assert len(rows) == 100
    assert rows[0]["Symbol"] == "SYM000"


def test_parse_csv_rejects_wrong_columns():
    with pytest.raises(universe.UniverseFetchError):
        universe._parse_csv("A,B,C\n1,2,3\n")


def test_parse_csv_rejects_bad_row_count():
    small_csv = "Company Name,Industry,Symbol,Series,ISIN Code\nOnly One,Sector,ONE,EQ,INE000\n"
    with pytest.raises(universe.UniverseFetchError):
        universe._parse_csv(small_csv)


def test_get_universe_prefers_fresh_cache(monkeypatch):
    settings = universe.get_settings()
    cache_path = Path(settings.UNIVERSE_CACHE_PATH)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(_VALID_CSV, encoding="utf-8")
    cache_path.with_suffix(".meta.json").write_text(
        json.dumps({"fetched_at": datetime.now(timezone.utc).isoformat(), "count": 100}),
        encoding="utf-8",
    )

    def _boom():
        raise AssertionError("Live fetch should not be called when cache is fresh")

    monkeypatch.setattr(universe, "fetch_live_universe", _boom)
    symbols = universe.get_universe()
    assert len(symbols) == 100
    assert "SYM000" in symbols


def test_get_universe_refetches_when_cache_stale(monkeypatch):
    settings = universe.get_settings()
    cache_path = Path(settings.UNIVERSE_CACHE_PATH)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(_VALID_CSV, encoding="utf-8")
    stale_time = datetime.now(timezone.utc) - timedelta(days=999)
    cache_path.with_suffix(".meta.json").write_text(
        json.dumps({"fetched_at": stale_time.isoformat(), "count": 100}), encoding="utf-8"
    )

    fresh_rows = universe._parse_csv(_VALID_CSV)
    monkeypatch.setattr(universe, "fetch_live_universe", lambda: fresh_rows)
    symbols = universe.get_universe()
    assert len(symbols) == 100


def test_get_universe_falls_back_to_stale_cache_on_fetch_failure(monkeypatch):
    settings = universe.get_settings()
    cache_path = Path(settings.UNIVERSE_CACHE_PATH)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(_VALID_CSV, encoding="utf-8")
    stale_time = datetime.now(timezone.utc) - timedelta(days=999)
    cache_path.with_suffix(".meta.json").write_text(
        json.dumps({"fetched_at": stale_time.isoformat(), "count": 100}), encoding="utf-8"
    )

    def _boom():
        raise universe.UniverseFetchError("simulated network failure")

    monkeypatch.setattr(universe, "fetch_live_universe", _boom)
    symbols = universe.get_universe()
    assert len(symbols) == 100  # served from the stale cache, not empty


def test_get_universe_falls_back_to_seed_when_no_cache(monkeypatch, tmp_path):
    seed_path = tmp_path / "seed.csv"
    _write_seed(seed_path)
    monkeypatch.setenv("UNIVERSE_SEED_PATH", str(seed_path))
    universe.get_settings.cache_clear()

    def _boom():
        raise universe.UniverseFetchError("simulated network failure")

    monkeypatch.setattr(universe, "fetch_live_universe", _boom)
    symbols = universe.get_universe()
    assert len(symbols) == 100


def test_diff_universe_reports_added_and_removed():
    delta = universe.diff_universe(["A", "B", "C"], ["B", "C", "D"])
    assert delta == {"added": ["D"], "removed": ["A"]}
