"""Walk-forward backtesting framework (ADR-012).

Provides an event-driven, bar-by-bar historical backtesting engine that directly
reuses production indicator math, strategy definitions, deterministic risk calculation,
and realistic transaction friction (slippage + delivery charges) with zero lookahead bias.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

import pandas as pd
import yfinance as yf
from pydantic import BaseModel, Field

from app.executor import SLIPPAGE_PCT
from app.risk import calculate_delivery_costs, calculate_risk, calculate_trailing_stop
from app.screener import _compute_indicators, _to_nse_symbol
from app.strategies import evaluate_all_strategies
from config.settings import get_settings

logger = logging.getLogger(__name__)


class BacktestTrade(BaseModel):
    """Record of a single simulated trade during backtesting."""

    trade_id: str
    symbol: str
    strategy_name: str
    entry_date: str
    entry_price: float
    quantity: int
    soft_stop: float
    hard_stop: float
    target_price: float
    highest_price: Optional[float] = None
    trailing_stop: Optional[float] = None
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # TARGET_HIT, STOPPED_OUT, TRAILING_STOP_HIT, BREAK_EVEN_STOP_HIT, END_OF_DATA
    gross_pnl: Optional[float] = None
    net_pnl: Optional[float] = None
    r_multiple: Optional[float] = None
    friction_costs: Optional[float] = None


class BacktestResult(BaseModel):
    """Comprehensive performance metrics and trade log from a backtest run."""

    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    total_net_pnl: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    average_r: float
    trades: list[BacktestTrade] = Field(default_factory=list)
    equity_curve: list[dict[str, Any]] = Field(default_factory=list)
    monte_carlo_stats: Optional[dict[str, Any]] = None


def _load_historical_ohlcv(
    symbol: str,
    start_date: str,
    end_date: str,
    warmup_days: int = 300,
) -> pd.DataFrame:
    """Download daily OHLCV with sufficient pre-warmup lookback for EMA 200."""
    start_dt = pd.to_datetime(start_date) - pd.Timedelta(days=warmup_days)
    nse_symbol = _to_nse_symbol(symbol)
    ticker = yf.Ticker(nse_symbol)
    df = ticker.history(
        start=start_dt.strftime("%Y-%m-%d"),
        end=(pd.to_datetime(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=True,
    )
    if df.empty:
        raise ValueError(f"No historical market data returned for {nse_symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if hasattr(df.index, "tz") and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


def run_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    initial_capital: Optional[float] = None,
    df: Optional[pd.DataFrame] = None,
) -> BacktestResult:
    """Run an event-driven, bar-by-bar backtest for a symbol over a date range.

    Parameters
    ----------
    symbol:
        NSE symbol (e.g. 'RELIANCE' or 'INFY').
    start_date:
        ISO start date 'YYYY-MM-DD' for trade evaluation.
    end_date:
        ISO end date 'YYYY-MM-DD'.
    initial_capital:
        Initial portfolio equity in INR (defaults to PORTFOLIO_CAPITAL).
    df:
        Optional pre-loaded OHLCV DataFrame (for unit tests / offline fixtures).
    """
    settings = get_settings()
    capital = initial_capital if initial_capital is not None else settings.PORTFOLIO_CAPITAL
    sym = symbol.strip().upper()

    if df is None:
        raw_df = _load_historical_ohlcv(sym, start_date, end_date)
    else:
        raw_df = df.copy()

    if isinstance(raw_df.columns, pd.MultiIndex):
        raw_df.columns = raw_df.columns.get_level_values(0)

    if hasattr(raw_df.index, "tz") and raw_df.index.tz is not None:
        raw_df.index = raw_df.index.tz_localize(None)

    indicators_df = _compute_indicators(raw_df)

    # Filter evaluation window from start_date to end_date (ensure timezone-naive)
    if hasattr(indicators_df.index, "tz") and indicators_df.index.tz is not None:
        indicators_df.index = indicators_df.index.tz_localize(None)
    indicators_df.index = pd.to_datetime(indicators_df.index)

    start_ts = pd.to_datetime(start_date)
    if hasattr(start_ts, "tz") and start_ts.tz is not None:
        start_ts = start_ts.tz_localize(None)

    end_ts = pd.to_datetime(end_date)
    if hasattr(end_ts, "tz") and end_ts.tz is not None:
        end_ts = end_ts.tz_localize(None)

    eval_mask = (indicators_df.index >= start_ts) & (indicators_df.index <= end_ts)
    eval_df = indicators_df.loc[eval_mask]

    if eval_df.empty:
        raise ValueError(f"No trading data available in evaluation window {start_date} to {end_date}")

    current_capital = capital
    open_trade: Optional[BacktestTrade] = None
    completed_trades: list[BacktestTrade] = []
    equity_curve: list[dict[str, Any]] = []
    peak_equity = capital

    for date_idx, row in eval_df.iterrows():
        current_date_str = date_idx.strftime("%Y-%m-%d")
        open_price = float(row["open"])
        high_price = float(row["high"])
        low_price = float(row["low"])
        close_price = float(row["close"])

        # ------------------------------------------------------------------ #
        # 1. Manage Active Position (Check Stops / Targets / Trailing Stops)
        # ------------------------------------------------------------------ #
        if open_trade is not None:
            exit_price: Optional[float] = None
            exit_reason: Optional[str] = None

            # Track highest price achieved
            open_trade.highest_price = max(open_trade.highest_price or open_trade.entry_price, high_price)

            # Dynamic ATR Trailing Stop (ADR-028)
            atr_val = float(row.get("atr_14") or 10.0)
            new_trailing, stop_mode = calculate_trailing_stop(
                entry_price=open_trade.entry_price,
                hard_stop=open_trade.hard_stop,
                highest_price=open_trade.highest_price,
                current_price=close_price,
                atr=atr_val,
                previous_trailing_stop=open_trade.trailing_stop,
            )
            open_trade.trailing_stop = new_trailing

            # Exit Evaluation Order: Hard Stop -> Trailing/Breakeven Stop -> Target Hit
            if low_price <= open_trade.hard_stop:
                exit_price = min(open_price, open_trade.hard_stop)
                exit_reason = "STOPPED_OUT"
            elif open_trade.trailing_stop and low_price <= open_trade.trailing_stop and open_trade.trailing_stop > open_trade.hard_stop:
                exit_price = min(open_price, open_trade.trailing_stop)
                exit_reason = "TRAILING_STOP_HIT" if stop_mode == "ATR_TRAILING" else "BREAK_EVEN_STOP_HIT"
            elif high_price >= open_trade.target_price:
                exit_price = max(open_price, open_trade.target_price)
                exit_reason = "TARGET_HIT"

            if exit_reason is not None and exit_price is not None:
                # Apply slippage on exit
                fill_exit = round(exit_price * (1.0 - SLIPPAGE_PCT), 2)
                gross_pnl = (fill_exit - open_trade.entry_price) * open_trade.quantity
                exit_costs = calculate_delivery_costs(
                    buy_value=0.0, sell_value=fill_exit * open_trade.quantity
                ).total
                net_pnl = gross_pnl - exit_costs

                risk_per_share = open_trade.entry_price - open_trade.hard_stop
                r_mult = (
                    (fill_exit - open_trade.entry_price) / risk_per_share
                    if risk_per_share > 0
                    else 0.0
                )

                open_trade.exit_date = current_date_str
                open_trade.exit_price = fill_exit
                open_trade.exit_reason = exit_reason
                open_trade.gross_pnl = round(gross_pnl, 2)
                open_trade.net_pnl = round(net_pnl, 2)
                open_trade.r_multiple = round(r_mult, 2)
                open_trade.friction_costs = round(
                    (open_trade.friction_costs or 0.0) + exit_costs, 2
                )

                current_capital += net_pnl
                completed_trades.append(open_trade)
                open_trade = None

        # ------------------------------------------------------------------ #
        # 2. Evaluate Setup Strategy & Risk Rules (If Flat)
        # ------------------------------------------------------------------ #
        if open_trade is None and not pd.isna(row.get("rsi_14")) and not pd.isna(row.get("atr_14")):
            primary_strat, _ = evaluate_all_strategies(row)
            if primary_strat is not None:
                proposal = calculate_risk(
                    symbol=sym,
                    entry_price=close_price,
                    atr=float(row["atr_14"]),
                    portfolio_capital=current_capital,
                    strategy_name=primary_strat.name,
                )
                if proposal is not None:
                    # Apply slippage on entry
                    fill_entry = round(proposal.entry_price * (1.0 + SLIPPAGE_PCT), 2)
                    entry_costs = calculate_delivery_costs(
                        buy_value=fill_entry * proposal.quantity, sell_value=0.0
                    ).total

                    open_trade = BacktestTrade(
                        trade_id=f"BT-{sym}-{len(completed_trades) + 1}",
                        symbol=sym,
                        strategy_name=primary_strat.name,
                        entry_date=current_date_str,
                        entry_price=fill_entry,
                        quantity=proposal.quantity,
                        soft_stop=proposal.soft_stop,
                        hard_stop=proposal.hard_stop,
                        target_price=proposal.target_price,
                        friction_costs=round(entry_costs, 2),
                    )

        # ------------------------------------------------------------------ #
        # 3. Mark-to-Market Equity Calculation
        # ------------------------------------------------------------------ #
        unrealized_pnl = 0.0
        if open_trade is not None:
            unrealized_pnl = (close_price - open_trade.entry_price) * open_trade.quantity

        daily_equity = current_capital + unrealized_pnl
        peak_equity = max(peak_equity, daily_equity)
        drawdown_pct = ((daily_equity - peak_equity) / peak_equity) * 100.0 if peak_equity > 0 else 0.0

        equity_curve.append({
            "date": current_date_str,
            "equity": round(daily_equity, 2),
            "drawdown_pct": round(drawdown_pct, 2),
            "in_position": open_trade is not None,
        })

    # Close any open position at end of simulation
    if open_trade is not None and not eval_df.empty:
        last_row = eval_df.iloc[-1]
        last_close = float(last_row["close"])
        fill_exit = round(last_close * (1.0 - SLIPPAGE_PCT), 2)
        gross_pnl = (fill_exit - open_trade.entry_price) * open_trade.quantity
        exit_costs = calculate_delivery_costs(
            buy_value=0.0, sell_value=fill_exit * open_trade.quantity
        ).total
        net_pnl = gross_pnl - exit_costs
        risk_per_share = open_trade.entry_price - open_trade.hard_stop
        r_mult = (
            (fill_exit - open_trade.entry_price) / risk_per_share
            if risk_per_share > 0
            else 0.0
        )

        open_trade.exit_date = eval_df.index[-1].strftime("%Y-%m-%d")
        open_trade.exit_price = fill_exit
        open_trade.exit_reason = "END_OF_DATA"
        open_trade.gross_pnl = round(gross_pnl, 2)
        open_trade.net_pnl = round(net_pnl, 2)
        open_trade.r_multiple = round(r_mult, 2)
        open_trade.friction_costs = round((open_trade.friction_costs or 0.0) + exit_costs, 2)

        current_capital += net_pnl
        completed_trades.append(open_trade)

    # ---------------------------------------------------------------------- #
    # 4. Aggregate Performance Metrics
    # ---------------------------------------------------------------------- #
    total_trades = len(completed_trades)
    winning_trades = [t for t in completed_trades if (t.net_pnl or 0.0) > 0]
    losing_trades = [t for t in completed_trades if (t.net_pnl or 0.0) <= 0]
    total_net_pnl = current_capital - capital
    total_return_pct = (total_net_pnl / capital) * 100.0 if capital > 0 else 0.0

    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
    gross_wins = sum(t.net_pnl for t in winning_trades if t.net_pnl)
    gross_losses = abs(sum(t.net_pnl for t in losing_trades if t.net_pnl))

    if gross_losses > 0:
        profit_factor = gross_wins / gross_losses
    elif gross_wins > 0:
        profit_factor = 99.9
    else:
        profit_factor = 0.0

    max_drawdown = min((item["drawdown_pct"] for item in equity_curve), default=0.0)
    avg_r = (
        sum(t.r_multiple for t in completed_trades if t.r_multiple is not None) / total_trades
        if total_trades > 0
        else 0.0
    )

    # Annualized Sharpe ratio from daily equity returns
    if len(equity_curve) > 1:
        equity_series = pd.Series([x["equity"] for x in equity_curve])
        daily_returns = equity_series.pct_change().dropna()
        std_dev = float(daily_returns.std())
        if std_dev > 1e-8:
            sharpe_ratio = float((daily_returns.mean() / std_dev) * math.sqrt(252))
        else:
            sharpe_ratio = 0.0
    else:
        sharpe_ratio = 0.0

    mc_stats = run_monte_carlo_simulation(completed_trades, initial_capital=capital)

    return BacktestResult(
        symbol=sym,
        start_date=start_date,
        end_date=end_date,
        initial_capital=round(capital, 2),
        final_equity=round(current_capital, 2),
        total_net_pnl=round(total_net_pnl, 2),
        total_return_pct=round(total_return_pct, 2),
        total_trades=total_trades,
        winning_trades=len(winning_trades),
        losing_trades=len(losing_trades),
        win_rate=round(win_rate, 4),
        profit_factor=round(profit_factor, 2),
        max_drawdown_pct=round(abs(max_drawdown), 2),
        sharpe_ratio=round(sharpe_ratio, 2),
        average_r=round(avg_r, 2),
        trades=completed_trades,
        equity_curve=equity_curve,
        monte_carlo_stats=mc_stats,
    )


def format_backtest_report(result: BacktestResult) -> str:
    """Format the backtest result into a structured Markdown summary."""
    lines = [
        "=================================================================",
        f"📊 BACKTEST SCORECARD — {result.symbol}",
        "=================================================================",
        f"Period:            {result.start_date} -> {result.end_date}",
        f"Initial Capital:   ₹{result.initial_capital:,.2f}",
        f"Final Equity:      ₹{result.final_equity:,.2f}",
        f"Total Net P&L:     ₹{result.total_net_pnl:+,.2f} ({result.total_return_pct:+.2f}%)",
        "-----------------------------------------------------------------",
        f"Total Trades:      {result.total_trades}",
        f"Wins / Losses:     {result.winning_trades} / {result.losing_trades}",
        f"Win Rate:          {result.win_rate * 100:.1f}%",
        f"Profit Factor:     {result.profit_factor:.2f}",
        f"Average R-Mult:    {result.average_r:+.2f}R",
        f"Max Drawdown:      {result.max_drawdown_pct:.2f}%",
        f"Sharpe Ratio:      {result.sharpe_ratio:.2f}",
        "-----------------------------------------------------------------",
    ]
    if result.trades:
        lines.append("Trade Log (Most Recent):")
        for t in result.trades[-10:]:
            pnl_str = f"₹{t.net_pnl:+,.2f}" if t.net_pnl is not None else "open"
            r_str = f"({t.r_multiple:+.2f}R)" if t.r_multiple is not None else ""
            lines.append(
                f"• [{t.entry_date} -> {t.exit_date or 'open'}] {t.strategy_name} | "
                f"Entry: ₹{t.entry_price:.2f} × {t.quantity} | Exit: ₹{t.exit_price or 0:.2f} | "
                f"{t.exit_reason or 'OPEN'} | P&L: {pnl_str} {r_str}"
            )
    else:
        lines.append("No trades generated during this evaluation window.")

    lines.append("=================================================================")
    return "\n".join(lines)


def run_monte_carlo_simulation(
    trades: list[BacktestTrade],
    initial_capital: float = 100000.0,
    num_simulations: int = 1000,
) -> dict[str, Any]:
    """Execute Monte Carlo bootstrap resamplings on historical trade outcomes (ADR-033).

    Parameters
    ----------
    trades:
        List of completed BacktestTrade objects.
    initial_capital:
        Initial baseline portfolio equity in INR.
    num_simulations:
        Number of randomized bootstrap iterations (default 1,000).

    Returns
    -------
    dict[str, Any]
        Monte Carlo risk metrics (95th/99th percentile Max Drawdown, Ruin Risk %,
        Confidence intervals for net return).
    """
    import random
    import numpy as np

    closed_pnl = [t.net_pnl for t in trades if t.net_pnl is not None]
    if not closed_pnl:
        return {
            "num_simulations": num_simulations,
            "sample_trades_count": 0,
            "median_max_drawdown_pct": 0.0,
            "p95_max_drawdown_pct": 0.0,
            "p99_max_drawdown_pct": 0.0,
            "probability_of_ruin_pct": 0.0,
            "expected_return_p05_pct": 0.0,
            "expected_return_p50_pct": 0.0,
            "expected_return_p95_pct": 0.0,
            "distribution_buckets": [],
        }

    n_trades = len(closed_pnl)
    drawdowns = []
    final_returns = []
    ruin_count = 0
    ruin_threshold = initial_capital * 0.80  # 20% drawdown threshold

    for _ in range(num_simulations):
        sampled_pnl = random.choices(closed_pnl, k=n_trades)
        equity = initial_capital
        peak = initial_capital
        max_dd = 0.0
        ruined = False

        for pnl in sampled_pnl:
            equity += pnl
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
            if equity <= ruin_threshold:
                ruined = True

        if ruined:
            ruin_count += 1
        drawdowns.append(max_dd * 100)
        ret_pct = ((equity - initial_capital) / initial_capital) * 100
        final_returns.append(ret_pct)

    p95_dd = float(np.percentile(drawdowns, 95))
    p99_dd = float(np.percentile(drawdowns, 99))
    p50_dd = float(np.median(drawdowns))

    p05_ret = float(np.percentile(final_returns, 5))
    p50_ret = float(np.percentile(final_returns, 50))
    p95_ret = float(np.percentile(final_returns, 95))

    ruin_prob = (ruin_count / num_simulations) * 100

    # Build histogram distribution buckets for UI visualization
    hist, bin_edges = np.histogram(final_returns, bins=10)
    distribution_buckets = [
        {
            "range": f"{bin_edges[i]:.1f}% to {bin_edges[i+1]:.1f}%",
            "count": int(hist[i]),
        }
        for i in range(len(hist))
    ]

    return {
        "num_simulations": num_simulations,
        "sample_trades_count": n_trades,
        "median_max_drawdown_pct": round(p50_dd, 2),
        "p95_max_drawdown_pct": round(p95_dd, 2),
        "p99_max_drawdown_pct": round(p99_dd, 2),
        "probability_of_ruin_pct": round(ruin_prob, 2),
        "expected_return_p05_pct": round(p05_ret, 2),
        "expected_return_p50_pct": round(p50_ret, 2),
        "expected_return_p95_pct": round(p95_ret, 2),
        "distribution_buckets": distribution_buckets,
    }

