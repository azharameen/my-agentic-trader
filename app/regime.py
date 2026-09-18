"""Deterministic India-market regime policy."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegimeAssessment(BaseModel):
    """Market context used before individual stock research."""

    allow_new_entries: bool
    risk_multiplier: float = Field(ge=0.0, le=1.0)
    reasons: list[str]


def evaluate_regime(
    vix: float,
    nifty_close: float,
    nifty_ema_50: float,
    *,
    elevated_vix: float = 22.0,
    blocking_vix: float = 25.0,
) -> RegimeAssessment:
    """Apply the documented conservative regime gate.

    VIX above the blocking threshold or NIFTY below its 50 EMA blocks new
    entries. Elevated but non-blocking VIX halves the risk budget.
    """
    reasons: list[str] = []
    if vix > blocking_vix:
        reasons.append("INDIA_VIX")
    if nifty_close < nifty_ema_50:
        reasons.append("NIFTY_BELOW_EMA_50")
    if reasons:
        return RegimeAssessment(allow_new_entries=False, risk_multiplier=0.0, reasons=reasons)
    if vix > elevated_vix:
        return RegimeAssessment(
            allow_new_entries=True,
            risk_multiplier=0.5,
            reasons=["INDIA_VIX_ELEVATED"],
        )
    return RegimeAssessment(allow_new_entries=True, risk_multiplier=1.0, reasons=[])
