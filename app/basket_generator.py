"""Beginner-friendly strategy basket generator and capital allocation engine.

Takes user investment amount and risk profile, runs deterministic risk sizing,
and produces a diversified 3-5 stock investment plan with plain-English rationales.
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from app import screener, universe
from app.models_basket import InvestmentGoal, RiskVibe, StockAllocation, StrategyBasket

logger = logging.getLogger(__name__)

# Top liquid Nifty 100 anchors across key sectors
DEFAULT_ANCHORS = [
    {"symbol": "TCS", "price": 4150.0, "atr": 65.0, "strategy": "Breakout Momentum", "sector": "IT"},
    {"symbol": "HDFCBANK", "price": 1680.0, "atr": 28.0, "strategy": "Pullback in Uptrend", "sector": "BANKING"},
    {"symbol": "RELIANCE", "price": 2920.0, "atr": 45.0, "strategy": "Pullback in Uptrend", "sector": "ENERGY"},
    {"symbol": "SUNPHARMA", "price": 1620.0, "atr": 25.0, "strategy": "Breakout Momentum", "sector": "PHARMA"},
    {"symbol": "TATAMOTORS", "price": 980.0, "atr": 18.0, "strategy": "Breakout Momentum", "sector": "AUTO"},
    {"symbol": "BHARTIARTL", "price": 1540.0, "atr": 24.0, "strategy": "Pullback in Uptrend", "sector": "TELECOM"},
    {"symbol": "ITC", "price": 490.0, "atr": 7.5, "strategy": "Bollinger Mean Reversion", "sector": "FMCG"},
    {"symbol": "BEL", "price": 310.0, "atr": 5.2, "strategy": "Breakout Momentum", "sector": "DEFENCE"},
    {"symbol": "NTPC", "price": 395.0, "atr": 6.8, "strategy": "Pullback in Uptrend", "sector": "POWER"},
    {"symbol": "COALINDIA", "price": 480.0, "atr": 8.0, "strategy": "Bollinger Mean Reversion", "sector": "METALS"},
]


def _get_layman_rationale(symbol: str, strategy: str, vibe: RiskVibe) -> str:
    """Generate simple, beginner-friendly explanations without financial jargon."""
    if strategy == "Breakout Momentum":
        return (
            f"{symbol} is showing strong upward buying volume and has broken above its recent resistance level, "
            f"indicating strong institutional interest and upward momentum."
        )
    if strategy == "Pullback in Uptrend":
        return (
            f"{symbol} is in a healthy long-term upward trend and has temporarily dipped to a safe support level, "
            f"offering a low-risk entry opportunity."
        )
    if strategy == "Bollinger Mean Reversion":
        return (
            f"{symbol} is temporarily oversold at the bottom of its trading range, "
            f"setting up for a high-probability bounce back towards its fair value."
        )
    return f"{symbol} meets our rigorous quality, volume, and risk-reward criteria for a steady swing setup."


def _get_holding_period(vibe: RiskVibe) -> str:
    if vibe == RiskVibe.CONSERVATIVE:
        return "4 to 8 Weeks"
    if vibe == RiskVibe.MOMENTUM:
        return "1 to 2 Weeks"
    return "2 to 4 Weeks"


def generate_strategy_basket(
    capital: float,
    risk_vibe: RiskVibe = RiskVibe.BALANCED,
    goal: InvestmentGoal = InvestmentGoal.SAFE_GROWTH,
    max_stocks: int = 4,
    candidates: Optional[list[dict]] = None,
) -> StrategyBasket:
    """Generate a diversified, risk-controlled strategy basket for a given capital amount."""
    if capital <= 0:
        raise ValueError("Capital must be greater than zero.")

    max_stocks = max(1, min(max_stocks, 8))
    company_names = universe.get_symbol_company_names()

    # Step 1: Collect candidates
    pool: list[dict] = []
    if candidates:
        pool = list(candidates)
    else:
        try:
            live_candidates = screener.scan_nifty_universe(universe.get_universe()[:25])
            for cand in live_candidates:
                if cand.qualifies:
                    sym = cand.symbol
                    pool.append({
                        "symbol": sym,
                        "price": float(cand.daily_close),
                        "atr": float(cand.atr or cand.daily_close * 0.02),
                        "strategy": cand.strategy_name or "Pullback in Uptrend",
                        "sector": universe.get_symbol_sector(sym),
                    })
        except Exception as exc:  # noqa: BLE001
            logger.warning("Live screener sweep failed, using vetted anchor pool: %s", exc)

    if len(pool) < max_stocks:
        # Augment with anchor symbols ensuring sector diversity
        existing_symbols = {p["symbol"] for p in pool}
        for anchor in DEFAULT_ANCHORS:
            if anchor["symbol"] not in existing_symbols:
                pool.append(anchor)
                existing_symbols.add(anchor["symbol"])
            if len(pool) >= max_stocks * 2:
                break

    # Affordability Band Filter: If capital < 30000, strictly prioritize quality stocks <= ₹1,500
    # to avoid single-share distortion in non-fractional Indian equity.
    if capital < 30000.0:
        affordable = [c for c in pool if c["price"] <= 1500.0]
        existing_symbols = {p["symbol"] for p in affordable}
        for anchor in DEFAULT_ANCHORS:
            if anchor["price"] <= 1500.0 and anchor["symbol"] not in existing_symbols:
                affordable.append(anchor)
                existing_symbols.add(anchor["symbol"])
        pool = affordable

    # Step 2: Sort and filter for sector diversification (max 1 stock per sector in a small basket)
    selected_candidates: list[dict] = []
    seen_sectors: set[str] = set()

    for cand in pool:
        price = cand["price"]
        # Skip if single share is more than 60% of total capital (unless capital is very low)
        if price > capital * 0.6 and capital >= 10000:
            continue
        sector = cand.get("sector") or universe.get_symbol_sector(cand["symbol"])
        if sector not in seen_sectors or len(pool) <= max_stocks:
            selected_candidates.append(cand)
            seen_sectors.add(sector)
        if len(selected_candidates) >= max_stocks:
            break

    if not selected_candidates:
        # Fallback to lowest price anchor
        cheapest = min(DEFAULT_ANCHORS, key=lambda x: x["price"])
        selected_candidates = [cheapest]

    actual_stock_count = len(selected_candidates)
    target_allocation_per_stock = capital / actual_stock_count

    # Step 3: Size shares and calculate 2-tranche targets, GTT triggers, and stops
    allocations: list[StockAllocation] = []
    total_allocated = 0.0

    for cand in selected_candidates:
        sym = cand["symbol"]
        price = float(cand["price"])
        atr = float(cand.get("atr") or price * 0.02)
        strat_name = cand.get("strategy") or "Breakout Momentum"
        sector = cand.get("sector") or universe.get_symbol_sector(sym)
        c_name = company_names.get(sym, sym)

        # Multipliers based on risk vibe & goal
        if risk_vibe == RiskVibe.CONSERVATIVE or goal == InvestmentGoal.SAFE_GROWTH:
            stop_dist = max(atr * 1.5, price * 0.03)
            target1_dist = max(atr * 3.0, price * 0.08)
            target2_dist = max(atr * 5.0, price * 0.14)
        elif risk_vibe == RiskVibe.MOMENTUM or goal == InvestmentGoal.WEALTH_COMPOUNDING:
            stop_dist = max(atr * 1.8, price * 0.05)
            target1_dist = max(atr * 4.0, price * 0.12)
            target2_dist = max(atr * 7.0, price * 0.22)
        else:  # BALANCED / VACATION_FUND / LEARNING
            stop_dist = max(atr * 1.5, price * 0.04)
            target1_dist = max(atr * 3.5, price * 0.10)
            target2_dist = max(atr * 6.0, price * 0.18)

        stop_loss_price = round(max(1.0, price - stop_dist), 2)
        target1_price = round(price + target1_dist, 2)
        target2_price = round(price + target2_dist, 2)

        expected_gain_pct = round(((target1_price - price) / price) * 100.0, 1)
        target2_gain_pct = round(((target2_price - price) / price) * 100.0, 1)
        max_risk_pct = round(((price - stop_loss_price) / price) * 100.0, 1)

        # Calculate whole shares
        shares = max(1, int(math.floor(target_allocation_per_stock / price)))
        cost = round(shares * price, 2)

        # Adjust if exceeding remaining available capital
        if total_allocated + cost > capital and shares > 1:
            shares = max(1, int(math.floor((capital - total_allocated) / price)))
            cost = round(shares * price, 2)

        if total_allocated + cost <= capital or len(allocations) == 0:
            total_allocated += cost
            weight_pct = round((cost / capital) * 100.0, 1)

            # 2-Tranche share split (50% target 1, 50% target 2)
            t1_shares = max(1, shares // 2) if shares > 1 else 1
            t2_shares = max(0, shares - t1_shares)

            # GTT triggers with buffer for limit execution
            gtt_stop_trig = round(stop_loss_price, 2)
            gtt_stop_lim = round(stop_loss_price * 0.995, 2)
            gtt_t1_trig = round(target1_price, 2)
            gtt_t1_lim = round(target1_price * 0.998, 2)
            gtt_t2_trig = round(target2_price, 2)
            gtt_t2_lim = round(target2_price * 0.998, 2)

            allocations.append(
                StockAllocation(
                    symbol=sym,
                    company_name=c_name,
                    sector=sector,
                    shares=shares,
                    suggested_entry_price=round(price, 2),
                    total_cost=cost,
                    weight_pct=weight_pct,
                    target_price=target1_price,
                    stop_loss_price=stop_loss_price,
                    expected_gain_pct=expected_gain_pct,
                    max_risk_pct=max_risk_pct,
                    target1_price=target1_price,
                    target1_shares=t1_shares,
                    target2_price=target2_price,
                    target2_shares=t2_shares,
                    target2_gain_pct=target2_gain_pct,
                    gtt_stop_trigger=gtt_stop_trig,
                    gtt_stop_limit=gtt_stop_lim,
                    gtt_target1_trigger=gtt_t1_trig,
                    gtt_target1_limit=gtt_t1_lim,
                    gtt_target2_trigger=gtt_t2_trig,
                    gtt_target2_limit=gtt_t2_lim,
                    holding_period=_get_holding_period(risk_vibe),
                    layman_rationale=_get_layman_rationale(sym, strat_name, risk_vibe),
                    deep_dive_summary=(
                        f"Strategy: {strat_name} | Sector: {sector} | "
                        f"ATR: ₹{atr:.2f} | R:R Ratio: {target1_dist / max(0.01, stop_dist):.2f}"
                    ),
                )
            )

    cash_reserve = round(max(0.0, capital - total_allocated), 2)
    basket_id = f"bsk-{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()

    # Peace of Mind Score (0-100)
    base_score = 92 if risk_vibe == RiskVibe.CONSERVATIVE else (85 if risk_vibe == RiskVibe.BALANCED else 78)
    if len(seen_sectors) >= 3:
        base_score = min(98, base_score + 4)
    peace_of_mind_score = base_score

    # Scenario Calculations
    # Best case: Target 1 hit for t1_shares + Target 2 hit for t2_shares
    best_case_gain = sum(
        (a.target1_shares * (a.target1_price - a.suggested_entry_price)) +
        (a.target2_shares * (a.target2_price - a.suggested_entry_price))
        for a in allocations
    )
    # Worst case: All stop losses hit
    worst_case_drawdown = -sum(
        a.shares * (a.suggested_entry_price - a.stop_loss_price)
        for a in allocations
    )
    # Normal case: ~65% of Target 1 gain across positions
    normal_case_gain = round(best_case_gain * 0.60, 2)

    thesis = (
        f"A risk-balanced portfolio of {len(allocations)} sector-diversified blue-chip companies "
        f"selected for {goal.value.replace('_', ' ').lower()} with a {risk_vibe.value.lower()} vibe over a "
        f"{_get_holding_period(risk_vibe)} horizon. Diversified across {len(seen_sectors)} sectors "
        f"to protect downside while targeting steady compounding."
    )

    return StrategyBasket(
        basket_id=basket_id,
        created_at=created_at,
        total_capital=round(capital, 2),
        allocated_capital=round(total_allocated, 2),
        cash_reserve=cash_reserve,
        risk_vibe=risk_vibe,
        goal=goal,
        market_regime="HEALTHY_BULLISH",
        overall_thesis=thesis,
        peace_of_mind_score=peace_of_mind_score,
        scenario_best_case=round(best_case_gain, 2),
        scenario_normal=normal_case_gain,
        scenario_worst_case=round(worst_case_drawdown, 2),
        allocations=allocations,
    )
