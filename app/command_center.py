"""Command Center: unified portfolio aggregation, manual position tracking, and
deterministic buy-more/hold/trim/sell signals for every asset a user holds
(Groww-synced or manually recorded), plus new-stock suggestions.

Design notes (ponytail: reuse, don't rebuild):
- Groww holdings are ingested through `groww_sync` and read from the PostgreSQL
  snapshot. Manually recorded stocks/F&O/mutual funds live in
  `user_positions` / `user_fno_positions` / `user_mutual_funds` so the Command
  Center has one consistent read path.
- Per-holding signals are deterministic technical reads via
  `screener.get_symbol_snapshot()` (works for ANY NSE symbol, not just the
  NIFTY 100 scan universe — the scan universe is a separate, deliberate concern
  for *discovering new* trade ideas, not for analyzing what a user already
  owns). No LLM calls here: this endpoint must stay fast for frequent polling.
  Deep qualitative thesis (LLM debate) is available on-demand via the existing
  `/api/run/{symbol}` graph pipeline.
- "Suggested" new stocks reuse the existing `pending_proposals` table (already
  populated by the scan pipeline) filtered to symbols not already held.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app import db, events, groww_client, groww_sync, proposals, regime, screener

logger = logging.getLogger(__name__)

MANUAL_PORTFOLIO_ID_FMT = "manual-{user_id}"

# Default risk envelope applied to positions with no explicit stop/target
# (mirrors the Groww auto-sync defaults for consistency: -6% stop, +8%/+16% targets).
DEFAULT_STOP_PCT = -0.06
DEFAULT_TARGET_PCT = 0.08


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sync_groww_if_stale(user_id: str) -> dict[str, Any]:
    """Keep the Command Center database current without syncing on every poll."""
    client = groww_client.get_groww_client()
    if not client.is_configured():
        return {"status": "SKIPPED", "reason": "Groww is not configured"}

    latest = db.fetchone(
        """
        SELECT finished_at, status FROM groww_sync_runs
        WHERE user_id = %s ORDER BY started_at DESC LIMIT 1;
        """,
        (user_id,),
    )
    if latest and latest.get("finished_at"):
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(latest["finished_at"])
            if age.total_seconds() < 600:
                return {"status": "FRESH", "last_synced_at": latest["finished_at"]}
        except ValueError:
            pass
    return groww_sync.sync_groww_portfolio(user_id=user_id)


def _ensure_manual_portfolio(user_id: str) -> str:
    """Ensure a housing portfolio row exists for manually-recorded positions."""
    db.init_all_tables()
    portfolio_id = MANUAL_PORTFOLIO_ID_FMT.format(user_id=user_id)
    row = db.fetchone("SELECT portfolio_id FROM user_portfolios WHERE portfolio_id = %s;", (portfolio_id,))
    if not row:
        db.execute(
            """
            INSERT INTO user_portfolios (
                portfolio_id, user_id, created_at, initial_capital,
                allocated_capital, cash_balance, risk_vibe, status
            ) VALUES (%s, %s, %s, 0, 0, 0, 'MANUAL', 'ACTIVE')
            ON CONFLICT (portfolio_id) DO NOTHING;
            """,
            (portfolio_id, user_id, _now()),
        )
    return portfolio_id


# --------------------------------------------------------------------------- #
# Manual Stock CRUD
# --------------------------------------------------------------------------- #
def add_manual_stock(
    user_id: str,
    symbol: str,
    shares: int,
    entry_price: float,
    stop_loss_price: Optional[float] = None,
    target_price: Optional[float] = None,
    sector: Optional[str] = None,
    broker_name: str = "Manual Entry",
) -> str:
    """Record a stock the user bought outside Groww/basket flows."""
    db.init_all_tables()
    portfolio_id = _ensure_manual_portfolio(user_id)
    symbol = symbol.strip().upper()
    stop = stop_loss_price if stop_loss_price is not None else round(entry_price * (1 + DEFAULT_STOP_PCT), 2)
    target = target_price if target_price is not None else round(entry_price * (1 + DEFAULT_TARGET_PCT), 2)
    position_id = f"manual-pos-{uuid.uuid4().hex[:10]}"

    db.execute(
        """
        INSERT INTO user_positions (
            position_id, portfolio_id, user_id, symbol, shares,
            suggested_price, entry_price, target_price, stop_loss_price,
            status, created_at, filled_at, sector, broker_name, source,
            investment_source, plan_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s, %s, %s, 'MANUAL', 'MANUAL', 'NONE');
        """,
        (
            position_id, portfolio_id, user_id, symbol, int(shares),
            entry_price, entry_price, target, stop,
            _now(), _now(), sector, broker_name,
        ),
    )
    events.broadcast_event("STOCK_ADDED", {"symbol": symbol, "position_id": position_id, "source": "MANUAL"})
    return position_id


def update_manual_stock(position_id: str, **fields: Any) -> None:
    """Inline-edit a manually recorded stock (qty/avg price/stop/target)."""
    row = db.fetchone("SELECT * FROM user_positions WHERE position_id = %s AND source = 'MANUAL';", (position_id,))
    if not row:
        raise ValueError(f"Manual position {position_id} not found.")
    allowed = {"shares": "shares", "entry_price": "entry_price", "stop_loss_price": "stop_loss_price", "target_price": "target_price"}
    sets, params = [], []
    for key, col in allowed.items():
        if key in fields and fields[key] is not None:
            sets.append(f"{col} = %s")
            params.append(fields[key])
    if not sets:
        return
    params.append(position_id)
    db.execute(f"UPDATE user_positions SET {', '.join(sets)} WHERE position_id = %s;", tuple(params))
    events.broadcast_event("STOCK_UPDATED", {"position_id": position_id})


def delete_manual_stock(position_id: str) -> None:
    """Remove a manually recorded stock (Groww-synced holdings cannot be deleted here)."""
    db.execute("DELETE FROM user_positions WHERE position_id = %s AND source = 'MANUAL';", (position_id,))
    events.broadcast_event("STOCK_REMOVED", {"position_id": position_id})


# --------------------------------------------------------------------------- #
# Manual F&O CRUD
# --------------------------------------------------------------------------- #
def add_fno_position(
    user_id: str,
    symbol: str,
    instrument_type: str,
    quantity: int,
    entry_price: float,
    lot_size: int = 1,
    strike_price: Optional[float] = None,
    expiry_date: Optional[str] = None,
) -> str:
    """Record an F&O position manually (no live F&O data source is available today)."""
    db.init_all_tables()
    position_id = f"fno-{uuid.uuid4().hex[:10]}"
    db.execute(
        """
        INSERT INTO user_fno_positions (
            position_id, user_id, symbol, instrument_type, strike_price, expiry_date,
            lot_size, quantity, entry_price, current_price, status, created_at, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s);
        """,
        (
            position_id, user_id, symbol.strip().upper(), instrument_type.strip().upper(),
            strike_price, expiry_date, int(lot_size), int(quantity), entry_price, entry_price,
            _now(), _now(),
        ),
    )
    events.broadcast_event("FNO_ADDED", {"symbol": symbol, "position_id": position_id})
    return position_id


def update_fno_position(position_id: str, **fields: Any) -> None:
    allowed = {"quantity", "entry_price", "current_price", "status"}
    sets, params = [], []
    for key in allowed:
        if key in fields and fields[key] is not None:
            sets.append(f"{key} = %s")
            params.append(fields[key])
    if not sets:
        return
    sets.append("last_updated = %s")
    params.append(_now())
    params.append(position_id)
    db.execute(f"UPDATE user_fno_positions SET {', '.join(sets)} WHERE position_id = %s;", tuple(params))
    events.broadcast_event("FNO_UPDATED", {"position_id": position_id})


def delete_fno_position(position_id: str) -> None:
    db.execute("DELETE FROM user_fno_positions WHERE position_id = %s;", (position_id,))
    events.broadcast_event("FNO_REMOVED", {"position_id": position_id})


# --------------------------------------------------------------------------- #
# Manual Mutual Fund CRUD (Groww's free API has no MF endpoint — confirmed)
# --------------------------------------------------------------------------- #
def add_mutual_fund(
    user_id: str,
    scheme_name: str,
    units: float,
    nav: float,
    invested_amount: float,
    folio_number: str = "",
    asset_category: str = "EQUITY",
) -> str:
    db.init_all_tables()
    folio_id = f"mf-{uuid.uuid4().hex[:10]}"
    current_value = round(units * nav, 2)
    pnl = round(current_value - invested_amount, 2)
    pnl_pct = round((pnl / invested_amount) * 100.0, 2) if invested_amount > 0 else 0.0
    db.execute(
        """
        INSERT INTO user_mutual_funds (
            folio_id, user_id, scheme_name, folio_number, units, nav,
            invested_amount, current_value, pnl, pnl_pct, asset_category, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (folio_id, user_id, scheme_name, folio_number, units, nav, invested_amount, current_value, pnl, pnl_pct, asset_category, _now()),
    )
    events.broadcast_event("MF_ADDED", {"scheme_name": scheme_name, "folio_id": folio_id})
    return folio_id


def update_mutual_fund(folio_id: str, **fields: Any) -> None:
    row = db.fetchone("SELECT * FROM user_mutual_funds WHERE folio_id = %s;", (folio_id,))
    if not row:
        raise ValueError(f"Mutual fund folio {folio_id} not found.")
    units = float(fields.get("units", row["units"]))
    nav = float(fields.get("nav", row["nav"]))
    invested = float(fields.get("invested_amount", row["invested_amount"]))
    current_value = round(units * nav, 2)
    pnl = round(current_value - invested, 2)
    pnl_pct = round((pnl / invested) * 100.0, 2) if invested > 0 else 0.0
    db.execute(
        """
        UPDATE user_mutual_funds SET units = %s, nav = %s, invested_amount = %s,
            current_value = %s, pnl = %s, pnl_pct = %s, last_updated = %s
        WHERE folio_id = %s;
        """,
        (units, nav, invested, current_value, pnl, pnl_pct, _now(), folio_id),
    )
    events.broadcast_event("MF_UPDATED", {"folio_id": folio_id})


def delete_mutual_fund(folio_id: str) -> None:
    db.execute("DELETE FROM user_mutual_funds WHERE folio_id = %s;", (folio_id,))
    events.broadcast_event("MF_REMOVED", {"folio_id": folio_id})


# --------------------------------------------------------------------------- #
# Deterministic signal engine (fast, no LLM — safe for frequent polling)
# --------------------------------------------------------------------------- #
def _compute_signal(
    current_price: float,
    entry_price: float,
    stop_loss_price: Optional[float],
    target_price: Optional[float],
    symbol: str,
) -> dict[str, Any]:
    """Deterministic Buy More / Hold / Trim / Sell badge for a held symbol, plus
    the underlying technical analytics (strategy tags, RSI, sector strength) so
    the UI can surface *why* without an extra round trip.

    Pure technical + risk-envelope read. Never touches LLM output (per
    app/AGENTS.md invariant #1 — this module only classifies using numbers
    already computed by risk.py-style envelopes and screener.py indicators).
    Deeper qualitative reasoning (LLM Bear/Bull/Synthesizer debate) is
    available on-demand via `get_deep_dive()` below, never inline here.
    """
    stop = stop_loss_price if stop_loss_price is not None else entry_price * (1 + DEFAULT_STOP_PCT)
    target = target_price if target_price is not None else entry_price * (1 + DEFAULT_TARGET_PCT)

    snapshot = None
    try:
        snapshot = screener.get_symbol_snapshot(symbol)
    except Exception:  # noqa: BLE001 - fail-open to price-only signal
        snapshot = None

    analytics: dict[str, Any] = {
        "strategy_name": snapshot.strategy_name if snapshot else None,
        "secondary_strategies": snapshot.secondary_strategies if snapshot else [],
        "sector_name": snapshot.sector_name if snapshot else None,
        "sector_rs_20d": snapshot.sector_rs_20d if snapshot else None,
        "rsi": round(snapshot.rsi, 1) if snapshot else None,
        "ema_200": round(snapshot.ema_200, 2) if snapshot else None,
        "qualifies": bool(snapshot.qualifies) if snapshot else False,
    }

    if current_price <= stop:
        return {"action": "SELL", "label": "Stop breached", "rationale": f"Price ₹{current_price:.2f} is at/below your stop ₹{stop:.2f}. Consider exiting to protect capital.", "analytics": analytics}
    if current_price >= target:
        return {"action": "TRIM", "label": "Target reached", "rationale": f"Price ₹{current_price:.2f} has reached your target ₹{target:.2f}. Consider booking partial profit.", "analytics": analytics}

    if snapshot is not None:
        if snapshot.qualifies and (snapshot.rsi or 50) < 55:
            return {
                "action": "BUY_MORE",
                "label": f"{snapshot.strategy_name or 'Setup'} qualifies",
                "rationale": f"Technical setup ({snapshot.strategy_name}) is active with RSI {snapshot.rsi:.1f}. Averaging in may improve cost basis.",
                "analytics": analytics,
            }
        if (snapshot.rsi or 50) > 72:
            return {"action": "TRIM", "label": "Overbought", "rationale": f"RSI {snapshot.rsi:.1f} is overbought. Consider trimming into strength.", "analytics": analytics}

    return {"action": "HOLD", "label": "On track", "rationale": f"Price ₹{current_price:.2f} is between stop ₹{stop:.2f} and target ₹{target:.2f}. No action needed.", "analytics": analytics}


def get_deep_dive(symbol: str) -> Optional[dict[str, Any]]:
    """On-demand qualitative deep dive (Bear/Bull/Synthesizer debate) for a symbol.

    Cheap DB read of the last completed LangGraph run for this symbol — does
    NOT trigger a new LLM run. If no prior run exists, returns None so the
    caller can offer to trigger one via the existing `/api/run/{symbol}` path.
    """
    from app import graph

    return graph.get_symbol_debate(symbol)


# --------------------------------------------------------------------------- #
# Aggregated overview
# --------------------------------------------------------------------------- #
def get_overview(user_id: str = "default_user") -> dict[str, Any]:
    """Single aggregated payload powering the Command Center screen."""
    db.init_all_tables()
    sync_result = _sync_groww_if_stale(user_id)

    synced_rows = db.fetchall(
        "SELECT * FROM user_positions WHERE user_id = %s AND status = 'ACTIVE' AND source = 'GROWW_SYNC' ORDER BY symbol;",
        (user_id,),
    )
    groww_symbols = {r["symbol"] for r in synced_rows}

    tracked_rows = db.fetchall(
        """
        SELECT * FROM user_positions
        WHERE user_id = %s AND status IN ('ACTIVE', 'PENDING_CONFIRMATION')
          AND source IN ('MANUAL', 'BASKET', 'GROWW_SYNC')
        ORDER BY symbol;
        """,
        (user_id,),
    )

    stocks: list[dict[str, Any]] = []
    total_invested = 0.0
    total_current_value = 0.0

    for r in synced_rows:
        symbol = r["symbol"]
        current_price = float(r.get("synced_current_price") or r.get("current_price") or r["entry_price"])
        entry = float(r["entry_price"])
        invested = float(r.get("synced_invested_amount") or (entry * float(r["shares"])))
        current_value = float(r.get("synced_current_value") or (current_price * float(r["shares"])))
        pnl = float(r.get("synced_pnl") or (current_value - invested))
        pnl_pct = float(r.get("synced_pnl_pct") or (round((pnl / invested) * 100.0, 2) if invested > 0 else 0.0))
        signal = _compute_signal(current_price, entry, None, None, symbol)
        stocks.append({
            "position_id": r["position_id"],
            "symbol": symbol,
            "company_name": r.get("company_name") or symbol,
            "shares": int(r["shares"]),
            "entry_price": entry,
            "current_price": current_price,
            "invested_amount": invested,
            "current_value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "source": "GROWW_SYNC",
            "investment_source": r.get("investment_source") or "GROWW_DIRECT",
            "plan_status": r.get("plan_status") or "NONE",
            "status": r.get("status") or "ACTIVE",
            "broker_name": r.get("broker_name") or "Groww",
            "isin": r.get("isin") or "",
            "editable": False,
            "signal": signal,
            "last_synced_at": r.get("synced_last_synced_at") or r.get("filled_at"),
        })
        if r.get("status") == "ACTIVE":
            total_invested += invested
            total_current_value += current_value

    for r in tracked_rows:
        symbol = r["symbol"]
        if r.get("source") == "GROWW_SYNC" and symbol in groww_symbols:
            continue
        current_price = float(r.get("current_price") or r.get("synced_current_price") or r["entry_price"])
        shares = int(r["shares"])
        entry = float(r["entry_price"])
        is_planned = r.get("status") == "PENDING_CONFIRMATION"
        invested = 0.0 if is_planned else entry * shares
        current_value = 0.0 if is_planned else current_price * shares
        pnl = current_value - invested
        pnl_pct = round((pnl / invested) * 100.0, 2) if invested > 0 else 0.0
        signal = _compute_signal(current_price, entry, r.get("stop_loss_price"), r.get("target_price"), symbol)
        row_source = r.get("source") or "MANUAL"
        stocks.append({
            "position_id": r["position_id"],
            "symbol": symbol,
            "company_name": r.get("company_name") or symbol,
            "shares": shares,
            "entry_price": entry,
            "current_price": round(current_price, 2),
            "stop_loss_price": r.get("stop_loss_price"),
            "target_price": r.get("target_price"),
            "invested_amount": round(invested, 2),
            "current_value": round(current_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": pnl_pct,
            "source": row_source,
            "investment_source": r.get("investment_source") or ("PLANNED" if row_source == "BASKET" else row_source),
            "plan_status": r.get("plan_status") or ("PLANNED" if is_planned else "NONE"),
            "status": r.get("status") or "ACTIVE",
            "broker_name": r.get("broker_name") or "",
            "isin": r.get("isin") or "",
            "editable": row_source == "MANUAL",
            "signal": signal,
            "last_synced_at": r.get("synced_last_synced_at") or r.get("filled_at"),
        })
        if r.get("status") == "ACTIVE":
            total_invested += invested
            total_current_value += current_value

    fno_rows = db.fetchall("SELECT * FROM user_fno_positions WHERE user_id = %s AND status = 'ACTIVE';", (user_id,))
    fno_positions = []
    for r in fno_rows:
        qty = int(r["quantity"]) * int(r["lot_size"])
        entry = float(r["entry_price"])
        current = float(r["current_price"] or entry)
        invested = entry * qty
        current_value = current * qty
        pnl = current_value - invested
        fno_positions.append({
            "position_id": r["position_id"],
            "symbol": r["symbol"],
            "instrument_type": r["instrument_type"],
            "strike_price": r.get("strike_price"),
            "expiry_date": r.get("expiry_date"),
            "lot_size": r["lot_size"],
            "quantity": r["quantity"],
            "entry_price": entry,
            "current_price": current,
            "invested_amount": round(invested, 2),
            "current_value": round(current_value, 2),
            "pnl": round(pnl, 2),
            "editable": True,
        })

    mf_rows = db.fetchall("SELECT * FROM user_mutual_funds WHERE user_id = %s;", (user_id,))
    mutual_funds = [
        {
            "folio_id": r["folio_id"],
            "scheme_name": r["scheme_name"],
            "folio_number": r["folio_number"],
            "units": r["units"],
            "nav": r["nav"],
            "invested_amount": r["invested_amount"],
            "current_value": r["current_value"],
            "pnl": r["pnl"],
            "pnl_pct": r["pnl_pct"],
            "asset_category": r["asset_category"],
            "editable": True,
        }
        for r in mf_rows
    ]
    mf_invested = sum(r["invested_amount"] for r in mf_rows)
    mf_current = sum(r["current_value"] for r in mf_rows)

    fno_invested = sum(item["invested_amount"] for item in fno_positions)
    fno_current = sum(item["current_value"] for item in fno_positions)

    realized_positions = db.fetchone(
        """
        SELECT COALESCE(SUM(realized_pnl), 0) AS total
        FROM user_positions WHERE user_id = %s AND realized_pnl IS NOT NULL;
        """,
        (user_id,),
    )
    realized_audit = db.fetchone(
        "SELECT COALESCE(SUM(realized_pnl), 0) AS total FROM trade_audit_log WHERE status = 'CLOSED';"
    )
    realized_earnings = float(realized_positions["total"] or 0.0) + float(realized_audit["total"] or 0.0)

    cash_available = 0.0
    portfolio_row = db.fetchone(
        "SELECT cash_balance, allocated_capital, created_at FROM user_portfolios WHERE user_id = %s AND status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1;",
        (user_id,),
    )
    if portfolio_row:
        cash_available = float(portfolio_row.get("cash_balance") or 0.0)

    held_symbols = groww_symbols | {r["symbol"] for r in tracked_rows}
    suggested = [
        {
            "proposal_id": p["proposal_id"],
            "symbol": p["symbol"],
            "strategy_name": p["strategy_name"],
            "entry_price": p["entry_price"],
            "target_price": p["target_price"],
            "hard_stop": p["hard_stop"],
            "risk_to_reward": p["risk_to_reward"],
            "thesis": p["thesis"],
        }
        for p in proposals.fetch_pending_proposals()
        if p["symbol"] not in held_symbols
    ]

    unrealized_earnings = (
        (total_current_value - total_invested)
        + (fno_current - fno_invested)
        + (mf_current - mf_invested)
    )
    total_pnl = unrealized_earnings + realized_earnings
    grand_invested = total_invested + fno_invested + mf_invested
    grand_current = total_current_value + fno_current + mf_current

    market_regime: dict[str, Any] = {"allow_new_entries": True, "risk_multiplier": 1.0, "reasons": []}
    try:
        assessment = regime.get_regime_assessment()
        market_regime = {
            "allow_new_entries": assessment.allow_new_entries,
            "risk_multiplier": assessment.risk_multiplier,
            "reasons": assessment.reasons,
            "vix": assessment.vix,
        }
    except Exception:  # noqa: BLE001 - fail-open, regime badge is informational only
        pass

    return {
        "generated_at": _now(),
        "totals": {
            "capital_invested": round(grand_invested, 2),
            "current_value": round(grand_current, 2),
            "total_pnl": round(total_pnl, 2),
            "unrealized_earnings": round(unrealized_earnings, 2),
            "realized_earnings": round(realized_earnings, 2),
            "total_earnings": round(total_pnl, 2),
            "total_pnl_pct": round((unrealized_earnings / grand_invested) * 100.0, 2) if grand_invested > 0 else 0.0,
            "cash_available": round(cash_available, 2),
        },
        "stocks": stocks,
        "fno": fno_positions,
        "mutual_funds": mutual_funds,
        "suggested": suggested,
        "groww_connected": groww_client.get_groww_client().is_configured(),
        "groww_sync": sync_result,
        "market_regime": market_regime,
    }
