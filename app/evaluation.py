"""Deterministic evaluation of closed and open paper trades with benchmark comparator."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import pandas as pd
import yfinance as yf

from app import cache
from config.settings import get_settings

logger = logging.getLogger(__name__)

MINIMUM_SAMPLE_SIZE = 30


def _group_summary(rows: list[dict]) -> dict:
    closed = [row for row in rows if row.get("status") == "CLOSED"]
    net = round(sum(float(row.get("realized_pnl") or 0.0) for row in closed), 2)
    return {
        "total_trades": len(rows),
        "closed_trades": len(closed),
        "open_trades": sum(row.get("status") == "OPEN_PAPER" for row in rows),
        "net_pnl": net,
        "gross_pnl": round(sum(float(row.get("gross_pnl") or 0.0) for row in closed), 2),
    }


def fetch_benchmark_return(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[float]:
    """Calculate the NIFTY benchmark index percentage return over a date window.

    Falls back safely to None if data cannot be retrieved.
    """
    settings = get_settings()
    benchmark_symbol = settings.NIFTY_INDEX_SYMBOL

    if not start_date or not end_date:
        return None

    cache_key = f"{benchmark_symbol}_{start_date}_{end_date}"
    try:
        def _fetch() -> dict[str, Any]:
            df = yf.download(
                tickers=benchmark_symbol,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=False,
            )
            if df.empty:
                return {"return_pct": None}
            if isinstance(df.columns, pd.MultiIndex):
                close_series = df["Close"].iloc[:, 0].dropna()
            else:
                close_series = df["Close"].dropna()
            if len(close_series) < 2:
                return {"return_pct": None}
            first_close = float(close_series.iloc[0])
            last_close = float(close_series.iloc[-1])
            if first_close <= 0:
                return {"return_pct": None}
            ret = round(((last_close - first_close) / first_close) * 100, 2)
            return {"return_pct": ret}

        cached_data = cache.get_or_set(
            namespace="benchmark_cache",
            cache_key=cache_key,
            fetcher=_fetch,
            ttl_minutes=1440,
        )
        return cached_data.get("return_pct") if isinstance(cached_data, dict) else None
    except Exception as exc:  # noqa: BLE001 - benchmark fetch is non-blocking
        logger.warning("Could not fetch benchmark return: %s", exc)
        return None


def summarize_trades(
    trades: Iterable[dict],
    initial_capital: Optional[float] = None,
    include_benchmark: bool = True,
) -> dict:
    """Calculate institutional performance metrics and net alpha (ADR-011, ADR-013)."""
    settings = get_settings()
    capital = initial_capital if initial_capital is not None else settings.PORTFOLIO_CAPITAL
    rows = list(trades)
    closed = [row for row in rows if row.get("status") == "CLOSED"]
    pnl = [float(row.get("realized_pnl") or 0.0) for row in closed]
    gross_pnls = [float(row.get("gross_pnl") or 0.0) for row in closed]

    net_pnl = round(sum(pnl), 2)
    gross_pnl = round(sum(gross_pnls), 2)
    transaction_costs = round(
        sum(float(row.get("gross_pnl") or 0.0) - float(row.get("realized_pnl") or 0.0) for row in closed),
        2,
    )

    winning = sum(value > 0 for value in pnl)
    losing = sum(value < 0 for value in pnl)
    breakeven = sum(value == 0 for value in pnl)

    gross_wins = sum(v for v in gross_pnls if v > 0)
    gross_losses = abs(sum(v for v in gross_pnls if v < 0))

    if gross_losses > 0:
        profit_factor: Optional[float] = round(gross_wins / gross_losses, 2)
    elif gross_wins > 0:
        profit_factor = None  # Infinite (no losses)
    else:
        profit_factor = 0.0

    # Realized R-Multiples
    r_multiples: list[float] = []
    for row in closed:
        fill_price = float(row.get("fill_price") or row.get("entry_price") or 0.0)
        exit_price = float(row.get("exit_price") or 0.0)
        hard_stop = float(row.get("hard_stop") or 0.0)
        initial_risk = fill_price - hard_stop
        if initial_risk > 0 and fill_price > 0 and exit_price > 0:
            r_val = round((exit_price - fill_price) / initial_risk, 2)
            r_multiples.append(r_val)

    avg_r = round(sum(r_multiples) / len(r_multiples), 2) if r_multiples else 0.0
    win_r = [r for r in r_multiples if r > 0]
    loss_r = [r for r in r_multiples if r < 0]
    avg_win_r = round(sum(win_r) / len(win_r), 2) if win_r else 0.0
    avg_loss_r = round(sum(loss_r) / len(loss_r), 2) if loss_r else 0.0

    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in reversed(pnl):
        cumulative += value
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)

    strategy_return_pct = round((net_pnl / capital) * 100, 2) if capital > 0 else 0.0
    max_drawdown_pct = round((max_drawdown / capital) * 100, 2) if capital > 0 else 0.0

    # Benchmark & Net Alpha
    benchmark_return_pct: Optional[float] = None
    net_alpha_pct: Optional[float] = None
    timestamps = [str(r.get("timestamp")) for r in closed if r.get("timestamp")]
    if include_benchmark and len(timestamps) >= 2:
        sorted_ts = sorted(timestamps)
        start_date = sorted_ts[0][:10]
        end_date = sorted_ts[-1][:10]
        if start_date != end_date:
            benchmark_return_pct = fetch_benchmark_return(start_date, end_date)
            if benchmark_return_pct is not None:
                net_alpha_pct = round(strategy_return_pct - benchmark_return_pct, 2)

    sample_size_sufficient = len(closed) >= MINIMUM_SAMPLE_SIZE
    sample_size_warning = (
        f"⚠️ *PRELIMINARY CONFIDENCE:* Sample size is {len(closed)} closed trade(s) (< {MINIMUM_SAMPLE_SIZE}). "
        "Statistical significance requires at least 30 closed trades."
        if not sample_size_sufficient
        else None
    )

    by_catalyst: dict[str, list[dict]] = defaultdict(list)
    by_provider: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_catalyst[row.get("catalyst_type") or "UNKNOWN"].append(row)
        by_provider[row.get("llm_provider") or "UNKNOWN"].append(row)

    return {
        "total_trades": len(rows),
        "closed_trades": len(closed),
        "open_trades": sum(row.get("status") == "OPEN_PAPER" for row in rows),
        "capital": capital,
        "net_pnl": net_pnl,
        "gross_pnl": gross_pnl,
        "transaction_costs": transaction_costs,
        "winning_trades": winning,
        "losing_trades": losing,
        "breakeven_trades": breakeven,
        "win_rate": round(winning / len(closed), 4) if closed else 0.0,
        "profit_factor": profit_factor,
        "expectancy": round(net_pnl / len(closed), 2) if closed else 0.0,
        "r_multiples": r_multiples,
        "avg_r_multiple": avg_r,
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_pct": max_drawdown_pct,
        "strategy_return_pct": strategy_return_pct,
        "benchmark_return_pct": benchmark_return_pct,
        "net_alpha_pct": net_alpha_pct,
        "sample_size_sufficient": sample_size_sufficient,
        "sample_size_warning": sample_size_warning,
        "by_catalyst": {key: _group_summary(value) for key, value in by_catalyst.items()},
        "by_provider": {key: _group_summary(value) for key, value in by_provider.items()},
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def format_performance_report(summary: dict) -> str:
    """Render a structured Markdown performance scorecard."""
    lines: list[str] = [
        "📊 *Paper Trading Performance Scorecard*",
        "",
    ]
    if summary.get("sample_size_warning"):
        lines.extend([summary["sample_size_warning"], ""])

    net = summary.get("net_pnl", 0.0)
    gross = summary.get("gross_pnl", 0.0)
    costs = summary.get("transaction_costs", 0.0)
    ret_pct = summary.get("strategy_return_pct", 0.0)
    sign = "+" if net > 0 else ""

    lines.extend([
        f"• *Capital Baseline:* ₹{summary.get('capital', 100000.0):,.2f}",
        f"• *Net Realized P&L:* {sign}₹{net:,.2f} ({sign}{ret_pct:.2f}%)",
        f"• *Gross P&L:* ₹{gross:,.2f} (Friction Costs: ₹{costs:,.2f})",
        f"• *Closed / Total Trades:* {summary.get('closed_trades', 0)} / {summary.get('total_trades', 0)}",
        f"• *Win Rate:* {summary.get('win_rate', 0.0) * 100:.1f}% ({summary.get('winning_trades', 0)}W / {summary.get('losing_trades', 0)}L)",
    ])

    pf = summary.get("profit_factor")
    pf_str = "∞" if pf is None else f"{pf:.2f}"
    lines.extend([
        f"• *Profit Factor:* {pf_str}",
        f"• *Average Realized R:* {summary.get('avg_r_multiple', 0.0):+.2f}R (Win: {summary.get('avg_win_r', 0.0):+.2f}R, Loss: {summary.get('avg_loss_r', 0.0):+.2f}R)",
        f"• *Trade Expectancy:* ₹{summary.get('expectancy', 0.0):+,.2f} per trade",
        f"• *Max Drawdown:* ₹{summary.get('max_drawdown', 0.0):,.2f} ({summary.get('max_drawdown_pct', 0.0):.2f}%)",
    ])

    bench = summary.get("benchmark_return_pct")
    alpha = summary.get("net_alpha_pct")
    if bench is not None and alpha is not None:
        alpha_sign = "+" if alpha > 0 else ""
        lines.extend([
            "",
            "📈 *Benchmark Comparator (NIFTY 100):*",
            f"• *NIFTY 100 Buy & Hold:* {bench:+.2f}%",
            f"• *Strategy Net Alpha:* {alpha_sign}{alpha:.2f}%",
        ])

    by_catalyst = summary.get("by_catalyst", {})
    if by_catalyst:
        lines.extend(["", "🏷️ *P&L by Catalyst Type:*"])
        for cat, stats in by_catalyst.items():
            lines.append(f"• `{cat}`: ₹{stats.get('net_pnl', 0.0):+,.2f} ({stats.get('closed_trades', 0)} closed)")

    return "\n".join(lines)
