"""Unit tests for operational health checks."""

from __future__ import annotations

from app import health
from config.settings import get_settings


def test_health_summary_reports_safe_runtime_state(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    result = health.get_summary()

    assert result["trading_mode"] == "PAPER_TRADING"
    assert result["llm_configured"] is False
    assert "pending_approvals" in result
    assert "database_integrity" in result
    get_settings.cache_clear()


def test_format_summary_is_readable():
    text = health.format_summary({
        "trading_mode": "PAPER_TRADING",
        "llm_provider": "gemini",
        "llm_model": "gemini-test",
        "llm_configured": True,
        "pending_approvals": 2,
        "open_paper_trades": 1,
        "cache_entries": 4,
        "pending_notifications": 0,
        "database_integrity": {"postgres": "ok"},
        "heartbeat": "not-running",
        "scan_schedule": "15:45 Asia/Kolkata mon-fri",
    })

    assert "PAPER_TRADING" in text
    assert "gemini-test" in text
    assert "Pending approvals: 2" in text
    assert "postgres=ok" in text
