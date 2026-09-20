"""Unit tests for the unified PostgreSQL database abstraction (app/db.py)."""

from __future__ import annotations

from app import db
from config.settings import get_settings


def test_is_postgres_detection(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    get_settings.cache_clear()
    assert db.is_postgres() is True

    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/db")
    get_settings.cache_clear()
    assert db.is_postgres() is True

    monkeypatch.setenv("DATABASE_URL", "invalid://test")
    get_settings.cache_clear()
    assert db.is_postgres() is False


def test_postgres_crud_operations():
    db.reset()
    db.init_all_tables()

    # Insert
    db.execute(
        "INSERT INTO graph_threads (thread_id, symbol, updated_at) VALUES (%s, %s, %s)",
        ("trade-TEST-2026-09-20", "TEST", "2026-09-20T00:00:00Z"),
    )

    # Fetchone
    row = db.fetchone("SELECT * FROM graph_threads WHERE thread_id = %s", ("trade-TEST-2026-09-20",))
    assert row is not None
    assert row["symbol"] == "TEST"

    # Fetchall
    rows = db.fetchall("SELECT * FROM graph_threads WHERE symbol = %s", ("TEST",))
    assert len(rows) == 1
    assert rows[0]["thread_id"] == "trade-TEST-2026-09-20"


def test_db_reset_clears_pool():
    db.reset()
    assert db._pool is None
