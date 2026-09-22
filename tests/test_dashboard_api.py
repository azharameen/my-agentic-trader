from __future__ import annotations

import json
from unittest.mock import MagicMock
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.dashboard_api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "trading_mode" in data


def test_api_overview(client, monkeypatch):
    from app import executor, proposals, regime, screener

    monkeypatch.setattr(executor, "fetch_all_trades", lambda: [])
    monkeypatch.setattr(executor, "get_current_capital", lambda: 100000.0)
    monkeypatch.setattr(proposals, "fetch_pending_proposals", lambda: [])
    monkeypatch.setattr(
        regime,
        "get_regime_assessment",
        lambda: regime.RegimeAssessment(
            vix=15.0,
            nifty_close=25000.0,
            nifty_ema_50=24500.0,
            allow_new_entries=True,
            risk_multiplier=1.0,
            reasons=["Normal"],
        ),
    )

    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["current_capital"] == 100000.0
    assert data["market_regime"]["vix"] == 15.0
    assert data["open_positions_count"] == 0
    assert data["pending_proposals_count"] == 0


def test_api_positions(client, monkeypatch):
    from app import executor, screener

    sample_trades = [
        {
            "trade_id": "test-123",
            "symbol": "TATACAP",
            "status": "OPEN_PAPER",
            "fill_price": 350.0,
            "quantity": 50,
            "soft_stop": 340.0,
            "hard_stop": 330.0,
            "target_price": 390.0,
            "strategy_name": "BREAKOUT",
            "timestamp": "2026-09-20T10:00:00Z",
            "thesis": "High momentum breakout",
        }
    ]
    monkeypatch.setattr(executor, "fetch_all_trades", lambda: sample_trades)
    monkeypatch.setattr(screener, "get_symbol_snapshot", lambda sym: {"daily_close": 360.0})

    response = client.get("/api/positions")
    assert response.status_code == 200
    positions = response.json()
    assert len(positions) == 1
    pos = positions[0]
    assert pos["symbol"] == "TATACAP"
    assert pos["unrealized_pnl"] == 500.0
    assert pos["unrealized_pnl_pct"] == 2.86


def test_api_position_close(client, monkeypatch):
    from app import executor, screener

    sample_trades = [
        {
            "trade_id": "pos-close-1",
            "symbol": "TCS",
            "status": "OPEN_PAPER",
            "fill_price": 4000.0,
            "quantity": 10,
        }
    ]
    monkeypatch.setattr(executor, "fetch_all_trades", lambda: sample_trades)
    monkeypatch.setattr(screener, "get_symbol_snapshot", lambda sym: {"daily_close": 4200.0})
    monkeypatch.setattr(
        executor,
        "close_trade",
        lambda trade_id, exit_price, mistake_category: {
            "trade_id": trade_id,
            "exit_price": exit_price,
            "realized_pnl": 1950.0,
            "status": "CLOSED",
        },
    )

    response = client.post("/api/positions/pos-close-1/close", json={"exit_price": 4200.0})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CLOSED"
    assert data["realized_pnl"] == 1950.0


def test_api_proposals_flow(client, monkeypatch):
    from app import proposals

    sample_props = [
        {
            "proposal_id": "prop-123",
            "symbol": "INFY",
            "strategy_name": "PULLBACK",
            "entry_price": 1800.0,
            "soft_stop": 1750.0,
            "hard_stop": 1720.0,
            "target_price": 1960.0,
            "quantity": 25,
            "risk_amount": 2000.0,
            "risk_to_reward": 2.0,
            "thesis": "Bullish support bounce",
            "catalyst_type": "EARNINGS",
            "created_at": "2026-09-21T00:00:00Z",
            "status": "PENDING",
            "debate": {"symbol": "INFY", "verdict": "PROCEED"},
        }
    ]
    monkeypatch.setattr(proposals, "fetch_pending_proposals", lambda: sample_props)
    monkeypatch.setattr(proposals, "fetch_proposal_by_id", lambda pid: sample_props[0] if pid == "prop-123" else None)
    monkeypatch.setattr(proposals, "approve_proposal", lambda pid, notes: {"status": "APPROVED", "symbol": "INFY"})
    monkeypatch.setattr(proposals, "reject_proposal", lambda pid, reason: {"status": "REJECTED", "symbol": "INFY"})

    # List proposals
    res = client.get("/api/proposals/pending")
    assert res.status_code == 200
    assert len(res.json()) == 1

    # Get single proposal
    res_single = client.get("/api/proposals/prop-123")
    assert res_single.status_code == 200
    assert res_single.json()["symbol"] == "INFY"

    # Approve
    res_app = client.post("/api/proposals/prop-123/approve", json={"notes": "Web approved"})
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"

    # Reject
    res_rej = client.post("/api/proposals/prop-123/reject", json={"reason": "High risk"})
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "REJECTED"


def test_api_trades(client, monkeypatch):
    from app import executor

    sample_trades = [
        {"trade_id": "1", "symbol": "INFY", "status": "CLOSED", "realized_pnl": 1200.0},
        {"trade_id": "2", "symbol": "TCS", "status": "OPEN_PAPER", "realized_pnl": None},
    ]
    monkeypatch.setattr(executor, "fetch_all_trades", lambda: sample_trades)

    all_res = client.get("/api/trades")
    assert len(all_res.json()) == 2

    closed_res = client.get("/api/trades?status=CLOSED")
    assert len(closed_res.json()) == 1
    assert closed_res.json()[0]["symbol"] == "INFY"


def test_api_performance(client, monkeypatch):
    from app import evaluation, executor

    sample_trades = [
        {"trade_id": "1", "symbol": "INFY", "status": "CLOSED", "realized_pnl": 1200.0, "fill_price": 1500.0, "hard_stop": 1450.0, "quantity": 10},
    ]
    monkeypatch.setattr(executor, "fetch_all_trades", lambda: sample_trades)

    response = client.get("/api/performance")
    assert response.status_code == 200
    data = response.json()
    assert "win_rate" in data
    assert "profit_factor" in data


def test_api_candles(client, monkeypatch):
    from app import market_data

    frame = pd.DataFrame(
        {
            "Open": [100.0, 102.0],
            "High": [105.0, 106.0],
            "Low": [98.0, 101.0],
            "Close": [104.0, 105.0],
            "Volume": [50000, 60000],
        },
        index=pd.to_datetime(["2026-09-18", "2026-09-19"]),
    )

    monkeypatch.setattr(
        market_data,
        "load_history",
        lambda sym, period, use_cache: market_data.MarketDataResult(
            frame=frame, source="yfinance", fetched_at=pd.Timestamp.now()
        ),
    )

    response = client.get("/api/candles/TATACAP")
    assert response.status_code == 200
    candles = response.json()
    assert len(candles) == 2
    assert candles[0]["open"] == 100.0
    assert candles[0]["close"] == 104.0


def test_api_backtest(client, monkeypatch):
    from app import backtester

    sample_report = backtester.BacktestResult(
        symbol="RELIANCE",
        start_date="2024-01-01",
        end_date="2024-06-30",
        initial_capital=100000.0,
        final_equity=112000.0,
        total_net_pnl=12000.0,
        total_return_pct=12.0,
        total_trades=10,
        winning_trades=6,
        losing_trades=4,
        win_rate=0.6,
        profit_factor=2.1,
        max_drawdown_pct=4.5,
        sharpe_ratio=1.45,
        average_r=1.2,
        trades=[],
        equity_curve=[{"date": "2024-01-01", "equity": 100000.0, "drawdown_pct": 0.0, "in_position": False}],
    )

    monkeypatch.setattr(backtester, "run_backtest", lambda *args, **kwargs: sample_report)

    response = client.post(
        "/api/backtest",
        json={"start_date": "2024-01-01", "end_date": "2024-06-30", "initial_capital": 100000.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["final_equity"] == 112000.0
    assert data["summary"]["sharpe_ratio"] == 1.45


def test_api_universe_and_workflows(client, monkeypatch):
    from app import pipeline, universe

    monkeypatch.setattr(universe, "get_universe", lambda force_refresh=False: ["RELIANCE", "TCS", "INFY"])
    monkeypatch.setattr(pipeline, "run_universe_scan", lambda symbols: ["RELIANCE"])
    monkeypatch.setattr(pipeline, "process_symbol", lambda sym: {"symbol": sym})

    u_res = client.get("/api/universe")
    assert u_res.status_code == 200
    assert u_res.json()["count"] == 3

    ref_res = client.post("/api/universe/refresh")
    assert ref_res.status_code == 200
    assert ref_res.json()["status"] == "SUCCESS"

    scan_res = client.post("/api/scan")
    assert scan_res.status_code == 200
    assert scan_res.json()["status"] == "QUEUED"

    run_res = client.post("/api/run/RELIANCE")
    assert run_res.status_code == 200
    assert run_res.json()["status"] == "QUEUED"


def test_api_chat_stream(client, monkeypatch):
    from app import chat_agent

    def fake_stream(msg, thread_id=None):
        yield {"type": "token", "content": "Hello "}
        yield {"type": "token", "content": "Trader!"}
        yield {"type": "done", "full_answer": "Hello Trader!"}

    monkeypatch.setattr(chat_agent, "stream_ask", fake_stream)

    response = client.post("/api/chat/stream", json={"message": "Hi"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    text = response.text
    assert "Hello " in text
    assert "Trader!" in text


def test_api_levels_open_position(client, monkeypatch):
    from app import executor, proposals

    sample_trades = [
        {
            "trade_id": "test-pos-1",
            "symbol": "INFY",
            "status": "OPEN_PAPER",
            "fill_price": 1800.0,
            "quantity": 50,
            "soft_stop": 1750.0,
            "hard_stop": 1700.0,
            "target_price": 1950.0,
            "trailing_stop": 1780.0,
            "highest_price": 1850.0,
        }
    ]
    monkeypatch.setattr(executor, "fetch_all_trades", lambda: sample_trades)
    monkeypatch.setattr(proposals, "fetch_pending_proposals", lambda: [])

    response = client.get("/api/levels/INFY")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "INFY"
    assert data["entry_price"] == 1800.0
    assert data["soft_stop"] == 1750.0
    assert data["hard_stop"] == 1700.0
    assert data["target_price"] == 1950.0
    assert data["trailing_stop"] == 1780.0
    assert data["status"] == "OPEN_PAPER"


def test_api_levels_pending_proposal(client, monkeypatch):
    from app import executor, proposals

    sample_props = [
        {
            "proposal_id": "prop-456",
            "symbol": "TCS",
            "entry_price": 4000.0,
            "soft_stop": 3900.0,
            "hard_stop": 3850.0,
            "target_price": 4300.0,
            "status": "PENDING",
        }
    ]
    monkeypatch.setattr(executor, "fetch_all_trades", lambda: [])
    monkeypatch.setattr(proposals, "fetch_pending_proposals", lambda: sample_props)

    response = client.get("/api/levels/TCS")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "TCS"
    assert data["entry_price"] == 4000.0
    assert data["soft_stop"] == 3900.0
    assert data["target_price"] == 4300.0
    assert data["status"] == "PENDING"


def test_root_serves_spa(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "<html" in response.text.lower() or "TrAId" in response.text

