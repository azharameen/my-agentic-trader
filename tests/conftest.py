"""Shared pytest fixtures: isolate every test's PostgreSQL tables and settings."""

from __future__ import annotations

import os

import pytest

from config.settings import get_settings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Point persistence at PostgreSQL and isolate test runs."""
    test_db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://trader_admin:trader_secret@localhost:5433/trader_db",
    )
    monkeypatch.setenv("DATABASE_URL", test_db_url)
    monkeypatch.setenv("UNIVERSE_CACHE_PATH", str(tmp_path / "universe" / "nifty100.csv"))
    get_settings.cache_clear()

    from app import db
    db.reset()
    from app import checkpoint
    checkpoint.reset()
    from app import store
    store.reset()
    from app import universe
    universe.clear_cache()

    from app import executor
    executor.init_db()

    # Clean out tables between test runs for deterministic isolation
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "TRUNCATE TABLE trade_audit_log, notification_outbox, research_cache, "
                    "evidence_snapshots, graph_threads, checkpoints, checkpoint_blobs, "
                    "checkpoint_writes, store CASCADE;"
                )
    except Exception:  # noqa: BLE001
        pass

    yield

    db.reset()
    checkpoint.reset()
    store.reset()
    universe.clear_cache()
    get_settings.cache_clear()
