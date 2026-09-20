"""
Deterministic risk engine.

This module is *pure Python math with zero LLM calls*. It converts a qualifying
technical snapshot into a concrete `TradeProposal` (or rejects the setup) using
the mission's hardcoded risk invariants:

* Portfolio risk cap: 1.0% of total equity per trade.
* Position sizing:  Quantity = floor((Capital * 0.01) / (Entry - HardStop))
* Two-tier ATR stops:
    - Soft alert        = Entry - (1.5 * ATR_14)   (inspection only)
    - Hard disaster stop = Entry - (2.5 * ATR_14)  (absolute invalidation)
* R:R floor: minimum 1:2.0, i.e. Target >= Entry + 2*(Entry - HardStop).

The function is a pure function of its inputs so it is trivially unit-testable
and auditable.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from pydantic import BaseModel

from app.state import TradeProposal
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


def calculate_risk(
    symbol: str,
    entry_price: float,
    atr: float,
    portfolio_capital: Optional[float] = None,
    risk_multiplier: float = 1.0,
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

    Returns
    -------
    Optional[TradeProposal]
        A fully-specified proposal, or `None` if the setup is rejected. A setup
        is rejected when:
          * inputs are non-positive or ATR is missing,
          * the computed R:R is below the configured minimum (2.0), or
          * the position size rounds to zero shares.
    """
    settings = get_settings()
    capital = portfolio_capital if portfolio_capital is not None else settings.PORTFOLIO_CAPITAL
    if not 0.0 <= risk_multiplier <= 1.0:
        return None

    # --- Input sanity ----------------------------------------------------- #
    if entry_price <= 0 or atr <= 0 or capital <= 0:
        logger.warning("Rejecting %s: invalid inputs (entry=%s, atr=%s, capital=%s).",
                       symbol, entry_price, atr, capital)
        return None

    # --- Two-tier ATR stops ---------------------------------------------- #
    soft_stop = entry_price - settings.ATR_SOFT_MULT * atr
    hard_stop = entry_price - settings.ATR_HARD_MULT * atr

    # A stop must sit below entry; otherwise the ATR is degenerate.
    if hard_stop >= entry_price or soft_stop >= entry_price:
        logger.warning("Rejecting %s: computed stops are not below entry.", symbol)
        return None
    if hard_stop <= 0:
        logger.warning("Rejecting %s: computed hard stop is non-positive (ATR too large for entry).", symbol)
        return None

    # --- Target & R:R ----------------------------------------------------- #
    risk_per_share = entry_price - hard_stop
    target_price = entry_price + settings.MIN_RISK_TO_REWARD * risk_per_share
    reward_per_share = target_price - entry_price
    risk_to_reward = reward_per_share / risk_per_share if risk_per_share > 0 else 0.0

    if risk_to_reward < settings.MIN_RISK_TO_REWARD:
        logger.warning(
            "Rejecting %s: R:R %.2f below minimum %.2f.",
            symbol, risk_to_reward, settings.MIN_RISK_TO_REWARD,
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
        "PROPOSAL %s: entry=%.2f soft=%.2f hard=%.2f target=%.2f qty=%d rr=%.2f",
        symbol, proposal.entry_price, proposal.soft_stop, proposal.hard_stop,
        proposal.target_price, proposal.quantity, proposal.risk_to_reward,
    )
    return proposal
