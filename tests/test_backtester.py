"""Unit tests for the walk-forward backtester (app/backtester.py)."""

from __future__ import annotations

import argparse

import pandas as pd
import pytest

from app import backtester


def _create_synthetic_ohlcv(
    start_date: str = "2024-01-01",
    num_days: int = 350,
    base_price: float = 100.0,
) -> pd.DataFrame:
    """Generate a deterministic synthetic daily OHLCV dataframe with uptrend and pullback."""
    dates = pd.date_range(start=start_date, periods=num_days, freq="D")
    data = []
    price = base_price

    for i in range(num_days):
        # Establish uptrend (ema200 will be lower than price)
        # Warmup period 0-250: steady rise
        # Days 250-260: pullback with oversold RSI
        # Days 261-280: bounce to profit target
        if i < 250:
            price += 0.5
        elif 250 <= i <= 260:
            price -= 2.0  # sharp pullback -> drops RSI < 35
        elif 261 <= i <= 275:
            price += 3.0  # sharp bounce -> hits target
        else:
            price += 0.2

        open_p = price - 0.2
        high_p = price + 1.5
        low_p = price - 1.5
        close_p = price
        volume = 2_000_000 if i >= 250 else 1_000_000

        data.append({
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": volume,
        })

    df = pd.DataFrame(data, index=dates)
    return df


def test_run_backtest_on_synthetic_data():
    df = _create_synthetic_ohlcv(start_date="2024-01-01", num_days=300, base_price=100.0)
    eval_start = "2024-09-01"
    eval_end = "2024-10-25"

    result = backtester.run_backtest(
        symbol="TESTSYM",
        start_date=eval_start,
        end_date=eval_end,
        initial_capital=100_000.0,
        df=df,
    )

    assert result.symbol == "TESTSYM"
    assert result.start_date == eval_start
    assert result.end_date == eval_end
    assert result.initial_capital == 100_000.0
    assert result.total_trades >= 1
    assert result.total_return_pct != 0.0
    assert len(result.equity_curve) > 0


def test_format_backtest_report():
    df = _create_synthetic_ohlcv(start_date="2024-01-01", num_days=300, base_price=100.0)
    result = backtester.run_backtest(
        symbol="TESTSYM",
        start_date="2024-09-01",
        end_date="2024-10-25",
        initial_capital=100_000.0,
        df=df,
    )

    report = backtester.format_backtest_report(result)

    assert "BACKTEST SCORECARD" in report
    assert "TESTSYM" in report
    assert "Initial Capital:" in report
    assert "Total Net P&L:" in report
    assert "Win Rate:" in report


def test_run_backtest_raises_on_empty_date_window():
    df = _create_synthetic_ohlcv(start_date="2024-01-01", num_days=50, base_price=100.0)

    with pytest.raises(ValueError, match="No trading data available in evaluation window"):
        backtester.run_backtest(
            symbol="TESTSYM",
            start_date="2025-01-01",
            end_date="2025-02-01",
            initial_capital=100_000.0,
            df=df,
        )


def test_cmd_backtest_cli_invocation(monkeypatch, capsys):
    df = _create_synthetic_ohlcv(start_date="2024-01-01", num_days=300, base_price=100.0)

    # Mock _load_historical_ohlcv to return synthetic df
    monkeypatch.setattr(backtester, "_load_historical_ohlcv", lambda *args, **kwargs: df)

    from app.main import cmd_backtest

    args = argparse.Namespace(
        symbol="TESTCLI",
        start="2024-09-01",
        end="2024-10-25",
        capital=50_000.0,
    )
    cmd_backtest(args)

    captured = capsys.readouterr()
    assert "BACKTEST SCORECARD" in captured.out
    assert "TESTCLI" in captured.out
    assert "Initial Capital:   ₹50,000.00" in captured.out


def test_monte_carlo_simulation():
    from app.backtester import BacktestTrade, run_monte_carlo_simulation

    synthetic_trades = [
        BacktestTrade(
            trade_id="T1", symbol="TEST", strategy_name="PULLBACK",
            entry_date="2024-01-01", entry_price=100.0, quantity=10,
            soft_stop=95.0, hard_stop=90.0, target_price=120.0,
            net_pnl=150.0,
        ),
        BacktestTrade(
            trade_id="T2", symbol="TEST", strategy_name="PULLBACK",
            entry_date="2024-01-10", entry_price=100.0, quantity=10,
            soft_stop=95.0, hard_stop=90.0, target_price=120.0,
            net_pnl=-80.0,
        ),
        BacktestTrade(
            trade_id="T3", symbol="TEST", strategy_name="PULLBACK",
            entry_date="2024-01-20", entry_price=100.0, quantity=10,
            soft_stop=95.0, hard_stop=90.0, target_price=120.0,
            net_pnl=200.0,
        ),
    ]

    mc = run_monte_carlo_simulation(synthetic_trades, initial_capital=100_000.0, num_simulations=500)
    assert mc["sample_trades_count"] == 3
    assert mc["num_simulations"] == 500
    assert "p95_max_drawdown_pct" in mc
    assert "expected_return_p50_pct" in mc
    assert len(mc["distribution_buckets"]) > 0


def test_monte_carlo_empty_trades():
    from app.backtester import run_monte_carlo_simulation

    mc = run_monte_carlo_simulation([], initial_capital=100_000.0)
    assert mc["sample_trades_count"] == 0
    assert mc["probability_of_ruin_pct"] == 0.0
