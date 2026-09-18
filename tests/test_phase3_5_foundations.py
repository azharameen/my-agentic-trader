"""Regression tests for the Phase 3–5 architecture foundations."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from app import broker, observability, outbox
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
    settings = get_settings()
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
