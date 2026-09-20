from __future__ import annotations

from app.evaluation import summarize_trades


def test_summarize_trades_calculates_net_metrics_and_drawdown():
    rows = [
        {"status": "CLOSED", "realized_pnl": 100.0, "gross_pnl": 120.0, "catalyst_type": "GENERAL_MARKET", "llm_provider": "openai"},
        {"status": "CLOSED", "realized_pnl": -40.0, "gross_pnl": -20.0, "catalyst_type": "GENERAL_MARKET", "llm_provider": "openai"},
        {"status": "OPEN_PAPER", "realized_pnl": None, "gross_pnl": None, "catalyst_type": "EARNINGS_NOISE", "llm_provider": "gemini"},
    ]

    result = summarize_trades(rows)

    assert result["total_trades"] == 3
    assert result["closed_trades"] == 2
    assert result["open_trades"] == 1
    assert result["net_pnl"] == 60.0
    assert result["gross_pnl"] == 100.0
    assert result["winning_trades"] == 1
    assert result["losing_trades"] == 1
    assert result["win_rate"] == 0.5
    assert result["expectancy"] == 30.0
    assert result["max_drawdown"] == 40.0
    assert result["by_catalyst"]["GENERAL_MARKET"]["net_pnl"] == 60.0
    assert result["by_provider"]["openai"]["closed_trades"] == 2


def test_summarize_trades_drawdown_uses_closed_trade_sequence():
    rows = [
        {"status": "CLOSED", "realized_pnl": 50.0, "gross_pnl": 50.0},
        {"status": "CLOSED", "realized_pnl": -100.0, "gross_pnl": -100.0},
        {"status": "CLOSED", "realized_pnl": 20.0, "gross_pnl": 20.0},
    ]

    assert summarize_trades(rows)["max_drawdown"] == 100.0
