"""Tests for performance evaluation, institutional metrics, benchmark comparator, and reports (T-007, ADR-011, ADR-013)."""

from __future__ import annotations

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app import evaluation, telegram_bot
from app.evaluation import format_performance_report, summarize_trades
from app.main import cmd_evaluate


def test_summarize_trades_calculates_net_metrics_and_drawdown() -> None:
    rows = [
        {
            "status": "CLOSED",
            "fill_price": 100.0,
            "entry_price": 100.0,
            "hard_stop": 95.0,
            "exit_price": 110.0,
            "realized_pnl": 100.0,
            "gross_pnl": 120.0,
            "catalyst_type": "GENERAL_MARKET",
            "llm_provider": "openai",
            "timestamp": "2026-01-01T10:00:00Z",
        },
        {
            "status": "CLOSED",
            "fill_price": 100.0,
            "entry_price": 100.0,
            "hard_stop": 95.0,
            "exit_price": 96.0,
            "realized_pnl": -40.0,
            "gross_pnl": -20.0,
            "catalyst_type": "GENERAL_MARKET",
            "llm_provider": "openai",
            "timestamp": "2026-01-05T10:00:00Z",
        },
        {
            "status": "OPEN_PAPER",
            "fill_price": 200.0,
            "entry_price": 200.0,
            "hard_stop": 190.0,
            "realized_pnl": None,
            "gross_pnl": None,
            "catalyst_type": "EARNINGS_NOISE",
            "llm_provider": "gemini",
            "timestamp": "2026-01-10T10:00:00Z",
        },
    ]

    result = summarize_trades(rows, initial_capital=100_000.0, include_benchmark=False)

    assert result["total_trades"] == 3
    assert result["closed_trades"] == 2
    assert result["open_trades"] == 1
    assert result["net_pnl"] == 60.0
    assert result["gross_pnl"] == 100.0
    assert result["transaction_costs"] == 40.0
    assert result["winning_trades"] == 1
    assert result["losing_trades"] == 1
    assert result["win_rate"] == 0.5
    assert result["expectancy"] == 30.0
    assert result["max_drawdown"] == 40.0
    assert result["profit_factor"] == 6.0  # 120.0 / 20.0
    assert result["sample_size_sufficient"] is False
    assert "PRELIMINARY CONFIDENCE" in (result["sample_size_warning"] or "")
    assert result["by_catalyst"]["GENERAL_MARKET"]["net_pnl"] == 60.0
    assert result["by_provider"]["openai"]["closed_trades"] == 2


def test_summarize_trades_r_multiples() -> None:
    rows = [
        # Win: Fill 100, Stop 95 (Risk 5), Exit 110 -> (110-100)/5 = +2.0R
        {
            "status": "CLOSED",
            "fill_price": 100.0,
            "hard_stop": 95.0,
            "exit_price": 110.0,
            "realized_pnl": 500.0,
            "gross_pnl": 520.0,
        },
        # Loss: Fill 200, Stop 180 (Risk 20), Exit 180 -> (180-200)/20 = -1.0R
        {
            "status": "CLOSED",
            "fill_price": 200.0,
            "hard_stop": 180.0,
            "exit_price": 180.0,
            "realized_pnl": -200.0,
            "gross_pnl": -190.0,
        },
    ]
    result = summarize_trades(rows, include_benchmark=False)
    assert result["r_multiples"] == [2.0, -1.0]
    assert result["avg_r_multiple"] == 0.5
    assert result["avg_win_r"] == 2.0
    assert result["avg_loss_r"] == -1.0


def test_summarize_trades_sample_size_threshold_warning() -> None:
    # 29 closed trades -> warning present
    trades_29 = [
        {"status": "CLOSED", "realized_pnl": 10.0, "gross_pnl": 12.0}
        for _ in range(29)
    ]
    summary_29 = summarize_trades(trades_29, include_benchmark=False)
    assert summary_29["sample_size_sufficient"] is False
    assert summary_29["sample_size_warning"] is not None
    assert "< 30" in summary_29["sample_size_warning"]

    # 30 closed trades -> warning absent
    trades_30 = [
        {"status": "CLOSED", "realized_pnl": 10.0, "gross_pnl": 12.0}
        for _ in range(30)
    ]
    summary_30 = summarize_trades(trades_30, include_benchmark=False)
    assert summary_30["sample_size_sufficient"] is True
    assert summary_30["sample_size_warning"] is None


def test_fetch_benchmark_return() -> None:
    dates = pd.date_range("2026-01-01", periods=5, freq="B")
    mock_df = pd.DataFrame({"Close": [24000.0, 24100.0, 24200.0, 24300.0, 25200.0]}, index=dates)
    with patch("yfinance.download", return_value=mock_df):
        ret = evaluation.fetch_benchmark_return("2026-01-01", "2026-01-08")
        assert ret == 5.0  # (25200 - 24000) / 24000 * 100 = 5.0%


def test_summarize_trades_net_alpha() -> None:
    rows = [
        {"status": "CLOSED", "realized_pnl": 4000.0, "gross_pnl": 4200.0, "timestamp": "2026-01-01T10:00:00Z"},
        {"status": "CLOSED", "realized_pnl": 6000.0, "gross_pnl": 6200.0, "timestamp": "2026-01-15T10:00:00Z"},
    ]
    with patch("app.evaluation.fetch_benchmark_return", return_value=3.5):
        summary = summarize_trades(rows, initial_capital=100_000.0, include_benchmark=True)
        assert summary["strategy_return_pct"] == 10.0  # 10000 / 100000 * 100
        assert summary["benchmark_return_pct"] == 3.5
        assert summary["net_alpha_pct"] == 6.5  # 10.0 - 3.5


def test_format_performance_report() -> None:
    summary = {
        "capital": 100000.0,
        "net_pnl": 12500.0,
        "gross_pnl": 13200.0,
        "transaction_costs": 700.0,
        "strategy_return_pct": 12.5,
        "closed_trades": 15,
        "total_trades": 18,
        "winning_trades": 10,
        "losing_trades": 5,
        "win_rate": 0.6667,
        "profit_factor": 2.45,
        "avg_r_multiple": 0.85,
        "avg_win_r": 1.75,
        "avg_loss_r": -0.95,
        "expectancy": 833.33,
        "max_drawdown": 2500.0,
        "max_drawdown_pct": 2.5,
        "benchmark_return_pct": 4.5,
        "net_alpha_pct": 8.0,
        "sample_size_warning": "⚠️ *PRELIMINARY CONFIDENCE:* Sample size is 15 closed trade(s) (< 30).",
        "by_catalyst": {"EARNINGS_NOISE": {"net_pnl": 8000.0, "closed_trades": 8}},
    }
    report = format_performance_report(summary)
    assert "Paper Trading Performance Scorecard" in report
    assert "PRELIMINARY CONFIDENCE" in report
    assert "₹12,500.00" in report
    assert "Profit Factor" in report
    assert "Benchmark Comparator" in report
    assert "Net Alpha" in report


@pytest.mark.asyncio
async def test_telegram_performance_command() -> None:
    update = MagicMock()
    update.effective_chat.id = 123456
    update.effective_message.reply_text = AsyncMock()
    context = MagicMock()

    with patch("app.telegram_bot._is_authorized", return_value=True), \
         patch("app.executor.fetch_all_trades", return_value=[]):
        await telegram_bot._on_performance(update, context)
        update.effective_message.reply_text.assert_called_once()
        msg = update.effective_message.reply_text.call_args[0][0]
        assert "Performance Scorecard" in msg


def test_cmd_evaluate_cli(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("app.executor.fetch_all_trades", return_value=[]):
        cmd_evaluate(argparse.Namespace())
        captured = capsys.readouterr()
        assert "Performance Scorecard" in captured.out
