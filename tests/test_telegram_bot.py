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


def test_build_keyboard_includes_debate_button():
    markup = telegram_bot._build_keyboard("TATACAP")
    buttons = [btn for row in markup.inline_keyboard for btn in row]
    callback_data_list = [btn.callback_data for btn in buttons]

    assert "approve:TATACAP" in callback_data_list
    assert "reject:TATACAP" in callback_data_list
    assert "debate:TATACAP" in callback_data_list


def test_format_debate_response():
    sample_info = {
        "symbol": "TATACAP",
        "research_verdict": {
            "verdict": "BUY",
            "composite_confidence": 0.82,
            "invalidation_conditions": "Close below ₹331",
            "citations": ["Headline 1", "ET Market News"],
            "bear_assessment": {
                "red_flags": ["Overhead supply at 360"],
                "governance_score": 0.95,
                "bear_rationale": "Routine sector pullback without structural damage.",
            },
            "bull_assessment": {
                "momentum_thesis": "Clean breakout retest holding 50 EMA.",
                "volume_quality": "High volume accumulation.",
                "sector_tailwinds": ["NBFC credit expansion"],
            },
        },
    }

    formatted = telegram_bot._format_debate_response("TATACAP", sample_info)
    assert "Multi-Agent Debate Analysis: TATACAP" in formatted
    assert "Bear Risk Critic" in formatted
    assert "Overhead supply at 360" in formatted
    assert "Bull Momentum Analyst" in formatted
    assert "NBFC credit expansion" in formatted
    assert "Synthesis Arbiter Decision" in formatted
    assert "82%" in formatted


def test_format_positions_empty(monkeypatch):
    monkeypatch.setattr(telegram_bot.executor, "fetch_all_trades", lambda: [])
    output = telegram_bot._format_positions()
    assert "No open paper positions currently active" in output


def test_format_positions_with_active_trades(monkeypatch):
    sample_trades = [
        {
            "symbol": "TATACAP",
            "status": "OPEN_PAPER",
            "fill_price": 350.0,
            "quantity": 50,
            "hard_stop": 330.0,
            "target_price": 390.0,
            "strategy_name": "BREAKOUT",
        }
    ]
    monkeypatch.setattr(telegram_bot.executor, "fetch_all_trades", lambda: sample_trades)
    monkeypatch.setattr(telegram_bot.executor, "get_current_capital", lambda: 100000.0)
    monkeypatch.setattr(
        telegram_bot.screener,
        "get_symbol_snapshot",
        lambda sym: {"daily_close": 360.0},
    )

    output = telegram_bot._format_positions()
    assert "Active Paper Positions (1)" in output
    assert "TATACAP" in output
    assert "BREAKOUT" in output
    assert "+₹500.00" in output
    assert "+2.86%" in output
    assert "Portfolio Capital Heat" in output


@pytest.mark.asyncio
async def test_on_callback_debate_replies_without_resuming(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    get_settings.cache_clear()

    replies = []

    class FakeMessage:
        async def reply_text(self, text, **kwargs):
            replies.append(text)

    class FakeQuery:
        data = "debate:TATACAP"
        async def answer(self):
            pass

    class FakeUpdate:
        effective_chat = type("Chat", (), {"id": 123})()
        effective_message = FakeMessage()
        callback_query = FakeQuery()

    sample_info = {
        "symbol": "TATACAP",
        "research_verdict": {
            "verdict": "BUY",
            "composite_confidence": 0.85,
            "bear_assessment": {"red_flags": [], "governance_score": 1.0, "bear_rationale": "Clean."},
            "bull_assessment": {"momentum_thesis": "Breakout", "volume_quality": "High", "sector_tailwinds": []},
        },
    }

    from app import graph
    monkeypatch.setattr(graph, "get_symbol_debate", lambda sym: sample_info)

    await telegram_bot._on_callback(FakeUpdate(), None)

    assert replies
    assert "Multi-Agent Debate Analysis: TATACAP" in replies[0]
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_on_positions_handler(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    get_settings.cache_clear()

    replies = []

    class FakeMessage:
        async def reply_text(self, text, **kwargs):
            replies.append(text)

    class FakeUpdate:
        effective_chat = type("Chat", (), {"id": 123})()
        effective_message = FakeMessage()

    monkeypatch.setattr(telegram_bot.executor, "fetch_all_trades", lambda: [])

    await telegram_bot._on_positions(FakeUpdate(), None)

    assert replies
    assert "No open paper positions" in replies[0]
    get_settings.cache_clear()


def test_send_scan_digest_notification(monkeypatch):
    from app import pipeline, regime

    notifications = []
    monkeypatch.setattr(
        telegram_bot,
        "notify_text",
        lambda chat_id, text: notifications.append(text),
    )

    fake_regime = regime.RegimeAssessment(
        vix=14.5,
        nifty_close=25000.0,
        nifty_ema_50=24500.0,
        allow_new_entries=True,
        risk_multiplier=1.0,
        reasons=["Normal market"],
    )

    pipeline._send_scan_digest(
        universe_count=100,
        duration_seconds=12.5,
        regime_assessment=fake_regime,
        qualifiers=[{"symbol": "TATACAP"}],
        proposed=["TATACAP"],
        rejected={"GENERAL_MARKET": 2},
    )

    assert notifications
    digest = notifications[0]
    assert "Daily Universe Scan Digest" in digest
    assert "Universe Screened:" in digest
    assert "100 symbols" in digest
    assert "TATACAP" in digest
    assert "2 GENERAL_MARKET" in digest


