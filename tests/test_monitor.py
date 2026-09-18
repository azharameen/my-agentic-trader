"""Unit tests for the position monitor (app/monitor.py)."""

from __future__ import annotations

from app import executor, monitor, screener
from app.risk import calculate_risk


def _open_trade(symbol: str, entry: float, atr: float) -> dict:
    proposal = calculate_risk(symbol, entry_price=entry, atr=atr, portfolio_capital=100_000)
    assert proposal is not None
    return executor.record_open_trade(
        proposal, rsi=30.0, ema_200=90.0, atr=atr, thesis="test", human_decision="APPROVED"
    )


def test_check_open_trades_closes_on_stop_hit(monkeypatch):
    trade = _open_trade("STOPTEST", entry=100.0, atr=2.0)  # hard_stop = 95.0
    monkeypatch.setattr(screener, "get_symbol_snapshot", lambda symbol: {"daily_close": 90.0})

    closed = monitor.check_open_trades()
    assert any(c["trade_id"] == trade["trade_id"] and c["mistake_category"] == "STOPPED_OUT" for c in closed)

    trades = {t["trade_id"]: t for t in executor.fetch_all_trades()}
    assert trades[trade["trade_id"]]["status"] == "CLOSED"


def test_check_open_trades_closes_on_target_hit(monkeypatch):
    trade = _open_trade("TARGETTEST", entry=100.0, atr=2.0)  # target = 110.0
    monkeypatch.setattr(screener, "get_symbol_snapshot", lambda symbol: {"daily_close": 115.0})

    closed = monitor.check_open_trades()
    assert any(c["trade_id"] == trade["trade_id"] and c["mistake_category"] == "TARGET_HIT" for c in closed)


def test_check_open_trades_leaves_healthy_position_open(monkeypatch):
    trade = _open_trade("HOLDTEST", entry=100.0, atr=2.0)
    monkeypatch.setattr(screener, "get_symbol_snapshot", lambda symbol: {"daily_close": 102.0})

    closed = monitor.check_open_trades()
    assert not any(c["trade_id"] == trade["trade_id"] for c in closed)

    trades = {t["trade_id"]: t for t in executor.fetch_all_trades()}
    assert trades[trade["trade_id"]]["status"] == "OPEN_PAPER"


def test_check_open_trades_skips_symbol_with_no_snapshot(monkeypatch):
    _open_trade("NODATA", entry=100.0, atr=2.0)
    monkeypatch.setattr(screener, "get_symbol_snapshot", lambda symbol: None)

    closed = monitor.check_open_trades()
    assert closed == []
