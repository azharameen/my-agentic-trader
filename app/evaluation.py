"""Deterministic evaluation of closed and open paper trades."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable


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


def summarize_trades(trades: Iterable[dict]) -> dict:
    rows = list(trades)
    closed = [row for row in rows if row.get("status") == "CLOSED"]
    pnl = [float(row.get("realized_pnl") or 0.0) for row in closed]
    net_pnl = round(sum(pnl), 2)
    winning = sum(value > 0 for value in pnl)
    losing = sum(value < 0 for value in pnl)
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in reversed(pnl):
        cumulative += value
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)

    by_catalyst: dict[str, list[dict]] = defaultdict(list)
    by_provider: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_catalyst[row.get("catalyst_type") or "UNKNOWN"].append(row)
        by_provider[row.get("llm_provider") or "UNKNOWN"].append(row)

    return {
        "total_trades": len(rows),
        "closed_trades": len(closed),
        "open_trades": sum(row.get("status") == "OPEN_PAPER" for row in rows),
        "net_pnl": net_pnl,
        "gross_pnl": round(sum(float(row.get("gross_pnl") or 0.0) for row in closed), 2),
        "transaction_costs": round(
            sum(float(row.get("gross_pnl") or 0.0) - float(row.get("realized_pnl") or 0.0) for row in closed),
            2,
        ),
        "winning_trades": winning,
        "losing_trades": losing,
        "win_rate": round(winning / len(closed), 4) if closed else 0.0,
        "expectancy": round(net_pnl / len(closed), 2) if closed else 0.0,
        "max_drawdown": round(max_drawdown, 2),
        "by_catalyst": {key: _group_summary(value) for key, value in by_catalyst.items()},
        "by_provider": {key: _group_summary(value) for key, value in by_provider.items()},
    }
