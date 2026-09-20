"""Unit tests for database maintenance operations."""

from __future__ import annotations

from app import maintenance


def test_check_databases_reports_healthy_databases():
    result = maintenance.check_databases()
    assert result["postgres"] == "ok"


def test_backup_databases_reports_status():
    result = maintenance.backup_databases()
    assert result["status"] == "managed_by_postgres_sidecar"
    assert result["integrity"]["postgres"] == "ok"
