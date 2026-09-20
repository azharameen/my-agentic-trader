"""Local SQLite integrity and backup operations."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config.settings import get_settings


def _database_paths() -> dict[str, Path]:
    settings = get_settings()
    return {
        "audit": Path(settings.DATABASE_PATH),
        "checkpoints": Path(settings.CHECKPOINT_DB_PATH),
    }


def check_databases() -> dict[str, str]:
    """Run SQLite integrity checks and raise if any database is unhealthy."""
    results: dict[str, str] = {}
    for name, path in _database_paths().items():
        if not path.exists():
            results[name] = "missing"
            continue
        with sqlite3.connect(path) as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"SQLite integrity check failed for {name}: {result}")
        results[name] = "ok"
    return results


def backup_databases() -> dict[str, Path]:
    """Create consistent timestamped backups of both local SQLite databases."""
    settings = get_settings()
    backup_dir = Path(settings.DATABASE_BACKUP_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    paths: dict[str, Path] = {}

    for name, source_path in _database_paths().items():
        if not source_path.exists():
            continue
        destination = backup_dir / f"{name}-{timestamp}.db"
        with sqlite3.connect(source_path) as source, sqlite3.connect(destination) as target:
            source.backup(target)
        paths[name] = destination
    return paths
