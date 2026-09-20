from __future__ import annotations

from app import cache
from config.settings import get_settings


def test_cache_round_trip_and_expiry(monkeypatch):
    monkeypatch.setenv("RESEARCH_CACHE_ENABLED", "true")
    get_settings.cache_clear()
    cache.init_db()

    cache.set_value("test", "key", {"value": 1}, ttl_minutes=10)
    assert cache.get_value("test", "key") == {"value": 1}
    get_settings.cache_clear()


def test_cache_can_be_disabled(monkeypatch):
    monkeypatch.setenv("RESEARCH_CACHE_ENABLED", "false")
    get_settings.cache_clear()
    cache.set_value("test", "key", {"value": 1}, ttl_minutes=10)
    assert cache.get_value("test", "key") is None
    get_settings.cache_clear()
