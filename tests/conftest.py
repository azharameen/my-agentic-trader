"""Shared pytest fixtures: isolate every test's DB/checkpoint/universe paths."""

from __future__ import annotations

import pytest

from config.settings import get_settings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Point all persistence at a per-test tmp_path so tests never touch real data/.

    Also resets `app.graph`'s module-level checkpointer globals, since they
    are cached process-wide and would otherwise leak the previous test's
    (or the real) checkpoint DB across tests.
    """
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "trading_audit.db"))
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    monkeypatch.setenv("STORE_DB_PATH", str(tmp_path / "store.db"))
    monkeypatch.setenv("UNIVERSE_CACHE_PATH", str(tmp_path / "universe" / "nifty100.csv"))
    get_settings.cache_clear()

    from app import checkpoint
    checkpoint.reset()
    from app import store
    store.reset()
    from app import universe
    universe.clear_cache()

    from app import executor
    executor.init_db()

    yield

    checkpoint.reset()
    store.reset()
    universe.clear_cache()
    get_settings.cache_clear()
