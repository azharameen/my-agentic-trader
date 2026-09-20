from __future__ import annotations

import pytest

from app import telegram_bot
from config.settings import get_settings


@pytest.mark.asyncio
async def test_run_handler_ignores_updates_without_effective_message(monkeypatch):
    class EmptyUpdate:
        effective_message = None

    await telegram_bot._on_run(EmptyUpdate(), None)


@pytest.mark.asyncio
async def test_unauthorized_update_is_rejected_without_running_pipeline(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    get_settings.cache_clear()
    replies = []

    class Message:
        async def reply_text(self, text, **kwargs):
            replies.append(text)

    class Update:
        effective_chat = type("Chat", (), {"id": 999})()
        effective_message = Message()

    await telegram_bot._on_scan(Update(), None)

    assert replies
    assert "registered operator" in replies[0]
    get_settings.cache_clear()


def test_stop_bot_requests_run_polling_shutdown(monkeypatch):
    class FakeLoop:
        def is_running(self):
            return True

        def call_soon_threadsafe(self, callback):
            callback()

    class FakeApplication:
        def __init__(self):
            self.stopped = False

        def stop_running(self):
            self.stopped = True

    application = FakeApplication()
    monkeypatch.setattr(telegram_bot, "_running_application", application)
    monkeypatch.setattr(telegram_bot, "_bot_loop", FakeLoop())

    telegram_bot.stop_bot()

    assert application.stopped


def test_update_is_authorized_only_for_configured_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    get_settings.cache_clear()

    class Update:
        class Chat:
            id = 123

        effective_chat = Chat()

    assert telegram_bot._is_authorized(Update())
    get_settings.cache_clear()


def test_update_without_configured_chat_is_rejected(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    get_settings.cache_clear()

    class Update:
        effective_chat = None

    assert not telegram_bot._is_authorized(Update())
    get_settings.cache_clear()
