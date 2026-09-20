from __future__ import annotations

import sqlite3

from app import maintenance
from config.settings import get_settings


def test_check_databases_reports_healthy_databases():
    checkpoint_path = get_settings().CHECKPOINT_DB_PATH
    with sqlite3.connect(checkpoint_path) as conn:
        conn.execute("CREATE TABLE health_check (value TEXT)")
    result = maintenance.check_databases()

    assert result["audit"] == "ok"
    assert result["checkpoints"] == "ok"


def test_backup_databases_copies_sqlite_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_BACKUP_DIR", str(tmp_path / "backups"))
    checkpoint_path = get_settings().CHECKPOINT_DB_PATH
    with sqlite3.connect(checkpoint_path) as conn:
        conn.execute("CREATE TABLE health_check (value TEXT)")

    paths = maintenance.backup_databases()

    assert set(paths) == {"audit", "checkpoints"}
    for path in paths.values():
        with sqlite3.connect(path) as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
