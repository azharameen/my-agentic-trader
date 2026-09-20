"""Regression tests for the Phase 3–5 architecture foundations."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from app import broker, executor, observability, outbox, pipeline, regime
from app.state import TradeProposal
from app.strategies import PullbackInUptrendStrategy, get_setup_strategy
from config.settings import get_settings


def test_strategy_protocol_preserves_current_filter():
    settings = get_settings()
    strategy = get_setup_strategy("pullback_in_uptrend")
    assert isinstance(strategy, PullbackInUptrendStrategy)
    row = pd.Series({
        "close": 110.0,
        "ema_200": 100.0,
        "rsi_14": 30.0,
        "volume": 600.0,
        "avg_volume_20": 1000.0,
    })
    assert strategy.qualifies(row, settings)


def test_unknown_strategy_fails_closed():
    with pytest.raises(ValueError, match="Unknown setup strategy"):
        get_setup_strategy("not-configured")


def test_broker_boundary_keeps_live_blocked():
    paper = broker.get_broker("PAPER_TRADING")
    assert isinstance(paper, broker.PaperBroker)
    live = broker.get_broker("LIVE")
    with pytest.raises(RuntimeError, match="not implemented"):
        live.open_trade(None)  # type: ignore[arg-type]


def test_outbox_retries_until_sender_succeeds():
    outbox.init_db()
    event_id = outbox.enqueue("TEST", "chat-1", {"symbol": "RELIANCE"})
    attempts = []

    def flaky_sender(recipient: str, payload: dict) -> bool:
        attempts.append((recipient, payload))
        return len(attempts) == 2

    assert outbox.deliver_pending(flaky_sender) == 0
    assert [row["event_id"] for row in outbox.pending()] == [event_id]
    assert outbox.deliver_pending(flaky_sender) == 1
    assert outbox.pending() == []


def test_close_trade_is_idempotent():
    proposal = TradeProposal(
        symbol="RELIANCE",
        entry_price=100.0,
        soft_stop=97.0,
        hard_stop=95.0,
        target_price=110.0,
        quantity=10,
        risk_amount=1000.0,
        risk_to_reward=2.0,
    )
    open_trade = executor.record_open_trade(
        proposal=proposal,
        rsi=30.0,
        ema_200=90.0,
        atr=2.0,
        thesis="Test",
        human_decision="APPROVED",
        news_headlines=[],
    )
    first = executor.close_trade(open_trade["trade_id"], exit_price=105.0)
    second = executor.close_trade(open_trade["trade_id"], exit_price=999.0)

    assert first["status"] == "CLOSED"
    assert second["realized_pnl"] == first["realized_pnl"]
    rows = [row for row in executor.fetch_all_trades() if row["trade_id"] == open_trade["trade_id"]]
    assert rows[0]["exit_price"] == 105.0
    assert rows[0]["realized_pnl"] == first["realized_pnl"]


def test_universe_scan_continues_if_one_symbol_fails(monkeypatch):
    monkeypatch.setattr(pipeline.monitor, "check_open_trades", lambda: [])
    monkeypatch.setattr(pipeline.outbox, "deliver_pending", lambda sender: 0)
    monkeypatch.setattr(pipeline.observability, "event", lambda *args, **kwargs: None)

    from contextlib import nullcontext

    monkeypatch.setattr(pipeline.observability, "span", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(pipeline.news, "fetch_headlines", lambda symbol: [])
    monkeypatch.setattr(
        pipeline.screener,
        "scan_nifty_universe",
        lambda universe_symbols: [{"symbol": "FAILME"}, {"symbol": "OKAY"}],
    )

    def fake_process_symbol(symbol: str, news_headlines=None, snapshot=None, events=None):
        if symbol == "FAILME":
            raise RuntimeError("boom")
        return {"__interrupt__": [SimpleNamespace(value={"symbol": symbol})]}

    monkeypatch.setattr(pipeline, "process_symbol", fake_process_symbol)

    proposed = pipeline.run_universe_scan(["FAILME", "OKAY"])
    assert proposed == ["OKAY"]


def test_scan_blocks_before_screening_when_regime_vetoes(monkeypatch):
    monkeypatch.setattr(pipeline.monitor, "check_open_trades", lambda: [])
    monkeypatch.setattr(pipeline.outbox, "deliver_pending", lambda sender: 0)
    monkeypatch.setattr(pipeline.corporate_events, "fetch_events", lambda: [])
    monkeypatch.setattr(pipeline.screener, "scan_nifty_universe", lambda _: pytest.fail("screening ran"))

    result = pipeline.run_universe_scan(
        ["TEST"],
        regime_assessment=regime.RegimeAssessment(
            allow_new_entries=False,
            risk_multiplier=0.0,
            reasons=["INDIA_VIX"],
        ),
    )

    assert result == []


def test_evaluation_fixture_is_valid_jsonl():
    fixture = Path(__file__).parents[1] / "evals" / "chat_agent_cases.jsonl"
    rows = [json.loads(line) for line in fixture.read_text(encoding="utf-8").splitlines()]
    assert len(rows) >= 5
    assert {"id", "query", "expected_tools", "policy"}.issubset(rows[0])
    assert any(row["expected_tools"] == [] for row in rows)


def test_observability_span_is_safe_when_disabled(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    get_settings.cache_clear()
    monkeypatch.setattr(observability, "_configured", False)
    with observability.span("test.span", symbol="TEST"):
        pass
