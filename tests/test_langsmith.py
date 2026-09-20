from __future__ import annotations

import os

from app import observability
from config.settings import get_settings


def test_langsmith_disabled_by_default_does_not_touch_environment(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING_ENABLED", "false")
    get_settings.cache_clear()

    observability._apply_langsmith_env(get_settings())

    assert "LANGSMITH_TRACING" not in os.environ
    get_settings.cache_clear()


def test_langsmith_enabled_without_api_key_stays_disabled(monkeypatch, caplog):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING_ENABLED", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "")
    get_settings.cache_clear()

    observability._apply_langsmith_env(get_settings())

    assert "LANGSMITH_TRACING" not in os.environ
    get_settings.cache_clear()


def test_langsmith_enabled_with_api_key_sets_environment_without_leaking_key(monkeypatch, caplog):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING_ENABLED", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-secret-value")
    monkeypatch.setenv("LANGSMITH_PROJECT", "traid-test")
    get_settings.cache_clear()

    with caplog.at_level("INFO"):
        observability._apply_langsmith_env(get_settings())

    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "ls-secret-value"
    assert os.environ["LANGSMITH_PROJECT"] == "traid-test"
    assert "ls-secret-value" not in caplog.text
    get_settings.cache_clear()
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
