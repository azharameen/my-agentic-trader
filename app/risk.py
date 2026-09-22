"""Deterministic risk engine (ADR-003, ADR-024).

This module is pure Python math with zero LLM calls. It converts a qualifying
technical snapshot into a concrete `TradeProposal` (or rejects the setup) using
the mission's hardcoded risk invariants and strategy-specific risk profiles:

* Portfolio risk cap: 1.0% of total equity per trade.
* Position sizing: Quantity = floor((Capital * 0.01 * risk_mult) / (Entry - HardStop))
* Strategy-specific ATR stops and minimum R:R floor:
    - Breakout Momentum: 1.0 ATR soft / 2.0 ATR hard / 3.0 R:R
    - Pullback in Uptrend: 1.5 ATR soft / 2.5 ATR hard / 2.0 R:R
    - Bollinger Mean Reversion: 1.2 ATR soft / 2.0 ATR hard / 2.0 R:R
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from pydantic import BaseModel

from app.state import TradeProposal
from app.strategies import get_strategy_risk_profile
from config.settings import get_settings

logger = logging.getLogger(__name__)


class DeliveryCosts(BaseModel):
    """Conservative paper-model delivery charges in INR."""

    stt: float
    exchange_charges: float
    sebi_charges: float
    gst: float
    stamp_duty: float
    total: float


def market_safety_rejection(
    *, circuit_locked: bool = False, asm_gsm_flag: bool = False
) -> Optional[str]:
    if circuit_locked:
        return "CIRCUIT_LOCKED"
    if asm_gsm_flag:
        return "ASM_GSM_SURVEILLANCE"
    return None


def calculate_delivery_costs(buy_value: float, sell_value: float) -> DeliveryCosts:
    """Calculate delivery friction without any broker or LLM dependency."""
    turnover = buy_value + sell_value
    stt = turnover * 0.001
    exchange_charges = turnover * 0.0000325
    sebi_charges = turnover * 0.000001
    stamp_duty = buy_value * 0.00015
    gst = (exchange_charges + sebi_charges) * 0.18
    total = stt + exchange_charges + sebi_charges + gst + stamp_duty
    return DeliveryCosts(
        stt=round(stt, 2),
        exchange_charges=round(exchange_charges, 2),
        sebi_charges=round(sebi_charges, 2),
        gst=round(gst, 2),
        stamp_duty=round(stamp_duty, 2),
        total=round(total, 2),
    )


def calculate_trailing_stop(
    entry_price: float,
    hard_stop: float,
    highest_price: float,
    current_price: float,
    atr: float,
    previous_trailing_stop: Optional[float] = None,
) -> tuple[float, str]:
    """Calculate dynamic ATR-based trailing stop and break-even stop (ADR-028).

    Parameters
    ----------
    entry_price:
        Original trade entry price.
    hard_stop:
        Initial baseline protective stop loss.
    highest_price:
        Highest price reached by the asset since trade entry.
    current_price:
        Latest daily close or live market price.
    atr:
        Current 14-period Average True Range.
    previous_trailing_stop:
        Previously recorded trailing stop level.

    Returns
    -------
    tuple[float, str]
        (new_trailing_stop, stop_mode) where stop_mode is 'ATR_TRAILING',
        'BREAK_EVEN', or 'INITIAL'.
    """
    initial_risk = entry_price - hard_stop
    if initial_risk <= 0:
        return hard_stop, "INITIAL"

    # Monotonic baseline: stop never ratchets below previous stop or hard stop
    base_stop = max(previous_trailing_stop or hard_stop, hard_stop)
    target_stop = base_stop
    mode = "INITIAL"

    # 1. Chandelier / ATR Trailing Gate (+2.0R expansion)
    if highest_price >= entry_price + (2.0 * initial_risk):
        atr_stop = highest_price - (1.5 * atr)
        # Ensure trailing stop is at least at breakeven
        target_stop = max(base_stop, entry_price, atr_stop)
        mode = "ATR_TRAILING"
    # 2. Break-Even Gate (+1.5R expansion)
    elif highest_price >= entry_price + (1.5 * initial_risk):
        target_stop = max(base_stop, entry_price)
        mode = "BREAK_EVEN"

    # Cap stop below current price so we don't calculate a stop higher than current price
    new_stop = min(target_stop, current_price)
    new_stop = max(new_stop, base_stop)

    return round(new_stop, 2), mode


def evaluate_sector_exposure_gate(
    symbol: str,
    sector: Optional[str],
    open_trades: list[dict],
    portfolio_capital: float,
    max_sector_capital_pct: float = 0.25,
    max_sector_positions: int = 2,
) -> Optional[str]:
    """Evaluate deterministic sector concentration and correlation risk gates (ADR-031).

    Parameters
    ----------
    symbol:
        Candidate symbol under review.
    sector:
        Industry or sector classification (e.g. 'IT', 'BANKING', 'AUTO').
    open_trades:
        List of active OPEN_PAPER trade dictionaries.
    portfolio_capital:
        Total current equity in INR.
    max_sector_capital_pct:
        Maximum fraction of total capital allowable in one sector (default 25%).
    max_sector_positions:
        Maximum concurrent open positions allowable in one sector (default 2).

    Returns
    -------
    Optional[str]
        None if gate passes, or a descriptive rejection reason code.
    """
    if not sector or sector.upper() == "UNKNOWN":
        return None

    sector_clean = sector.strip().upper()
    sector_positions = 0
    sector_capital_allocated = 0.0

    for t in open_trades:
        t_sector = (t.get("sector") or t.get("industry") or "").strip().upper()
        if t_sector == sector_clean and t["status"] == "OPEN_PAPER":
            sector_positions += 1
            entry = float(t.get("fill_price") or t.get("entry_price") or 0.0)
            qty = int(t.get("quantity") or 0)
            sector_capital_allocated += (entry * qty)

    # 1. Maximum Concurrent Positions Gate
    if sector_positions >= max_sector_positions:
        logger.warning(
            "Rejecting %s: sector %s already has %d active open positions (max=%d).",
            symbol, sector_clean, sector_positions, max_sector_positions,
        )
        return "SECTOR_MAX_POSITIONS_EXCEEDED"

    # 2. Maximum Capital Exposure Gate
    max_capital = portfolio_capital * max_sector_capital_pct
    if sector_capital_allocated >= max_capital:
        logger.warning(
            "Rejecting %s: sector %s capital allocated (₹%.2f) exceeds max allowed (₹%.2f, %.0f%%).",
            symbol, sector_clean, sector_capital_allocated, max_capital, max_sector_capital_pct * 100,
        )
        return "SECTOR_CAPITAL_EXPOSURE_EXCEEDED"

    return None


def calculate_risk(
    symbol: str,
    entry_price: float,
    atr: float,
    portfolio_capital: Optional[float] = None,
    risk_multiplier: float = 1.0,
    strategy_name: Optional[str] = None,
) -> Optional[TradeProposal]:
    """Build a `TradeProposal` from a technical snapshot, or return `None`.

    Parameters
    ----------
    symbol:
        NSE symbol (without `.NS`).
    entry_price:
        Proposed entry price (typically the last daily close).
    atr:
        14-day Average True Range.
    portfolio_capital:
        Total equity in INR. Defaults to the configured `PORTFOLIO_CAPITAL`.
    risk_multiplier:
        Macro regime risk scaling factor (0.0 to 1.0).
    strategy_name:
        Optional name of the active setup strategy to apply custom ATR stop
        multipliers and minimum R:R expectations.

    Returns
    -------
    Optional[TradeProposal]
        A fully-specified proposal, or `None` if the setup is rejected.
    """
    settings = get_settings()
    capital = portfolio_capital if portfolio_capital is not None else settings.PORTFOLIO_CAPITAL
    if not 0.0 <= risk_multiplier <= 1.0:
        return None

    # --- Input sanity ----------------------------------------------------- #
    if entry_price <= 0 or atr <= 0 or capital <= 0:
        logger.warning(
            "Rejecting %s: invalid inputs (entry=%s, atr=%s, capital=%s).",
            symbol, entry_price, atr, capital,
        )
        return None

    # --- Strategy Risk Profile -------------------------------------------- #
    risk_profile = get_strategy_risk_profile(strategy_name)

    # --- Two-tier ATR stops ---------------------------------------------- #
    soft_stop = entry_price - risk_profile.atr_soft_mult * atr
    hard_stop = entry_price - risk_profile.atr_hard_mult * atr

    # A stop must sit below entry; otherwise the ATR is degenerate.
    if hard_stop >= entry_price or soft_stop >= entry_price:
        logger.warning("Rejecting %s: computed stops are not below entry.", symbol)
        return None
    if hard_stop <= 0:
        logger.warning(
            "Rejecting %s: computed hard stop is non-positive (ATR too large for entry).",
            symbol,
        )
        return None

    # --- Target & R:R ----------------------------------------------------- #
    risk_per_share = entry_price - hard_stop
    target_price = entry_price + risk_profile.min_risk_to_reward * risk_per_share
    reward_per_share = target_price - entry_price
    risk_to_reward = reward_per_share / risk_per_share if risk_per_share > 0 else 0.0

    if risk_to_reward < risk_profile.min_risk_to_reward:
        logger.warning(
            "Rejecting %s: R:R %.2f below minimum %.2f.",
            symbol, risk_to_reward, risk_profile.min_risk_to_reward,
        )
        return None

    # --- Position sizing (1% risk rule) ----------------------------------- #
    risk_amount = capital * settings.RISK_PER_TRADE_PCT * risk_multiplier
    quantity = math.floor(risk_amount / risk_per_share)

    if quantity <= 0:
        logger.warning(
            "Rejecting %s: position size rounds to 0 shares (risk/share=%.2f, risk=%.2f).",
            symbol, risk_per_share, risk_amount,
        )
        return None

    proposal = TradeProposal(
        symbol=symbol,
        entry_price=round(entry_price, 2),
        soft_stop=round(soft_stop, 2),
        hard_stop=round(hard_stop, 2),
        target_price=round(target_price, 2),
        quantity=quantity,
        risk_amount=round(risk_amount, 2),
        risk_to_reward=round(risk_to_reward, 2),
    )
    logger.info(
        "PROPOSAL %s [%s]: entry=%.2f soft=%.2f hard=%.2f target=%.2f qty=%d rr=%.2f",
        symbol, risk_profile.name, proposal.entry_price, proposal.soft_stop,
        proposal.hard_stop, proposal.target_price, proposal.quantity,
        proposal.risk_to_reward,
    )
    return proposal
