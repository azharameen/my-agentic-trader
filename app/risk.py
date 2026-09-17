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

from config.settings import get_settings
from app.state import TradeProposal

logger = logging.getLogger(__name__)


def calculate_risk(
    symbol: str,
    entry_price: float,
    atr: float,
    portfolio_capital: Optional[float] = None,
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
    risk_amount = capital * settings.RISK_PER_TRADE_PCT
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
