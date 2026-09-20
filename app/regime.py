"""Deterministic India-market regime policy and automated macro data ingestion."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import yfinance as yf
from pydantic import BaseModel, Field

from app import cache
from config.settings import get_settings

logger = logging.getLogger(__name__)


class RegimeAssessment(BaseModel):
    """Market context used before individual stock research."""

    allow_new_entries: bool
    risk_multiplier: float = Field(default=1.0, ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    vix: Optional[float] = None
    nifty_close: Optional[float] = None
    nifty_ema_50: Optional[float] = None
    as_of: Optional[str] = None


def evaluate_regime(
    vix: float,
    nifty_close: float,
    nifty_ema_50: float,
    *,
    elevated_vix: Optional[float] = None,
    crisis_vix: Optional[float] = None,
) -> RegimeAssessment:
    """Apply the documented conservative regime gate (ADR-011).

    VIX above the crisis threshold (default 24.0) or NIFTY below its 50 EMA
    blocks new entries. Elevated VIX (default 19.0 to 24.0) halves the risk budget.
    """
    settings = get_settings()
    elevated = elevated_vix if elevated_vix is not None else settings.VIX_ELEVATED_THRESHOLD
    crisis = crisis_vix if crisis_vix is not None else settings.VIX_CRISIS_THRESHOLD

    reasons: list[str] = []
    if vix > crisis:
        reasons.append("INDIA_VIX_CRISIS")
    if nifty_close < nifty_ema_50:
        reasons.append("NIFTY_BELOW_EMA_50")

    if reasons:
        return RegimeAssessment(
            allow_new_entries=False,
            risk_multiplier=0.0,
            reasons=reasons,
            vix=round(vix, 2),
            nifty_close=round(nifty_close, 2),
            nifty_ema_50=round(nifty_ema_50, 2),
        )

    if vix > elevated:
        return RegimeAssessment(
            allow_new_entries=True,
            risk_multiplier=0.5,
            reasons=["INDIA_VIX_ELEVATED"],
            vix=round(vix, 2),
            nifty_close=round(nifty_close, 2),
            nifty_ema_50=round(nifty_ema_50, 2),
        )

    return RegimeAssessment(
        allow_new_entries=True,
        risk_multiplier=1.0,
        reasons=[],
        vix=round(vix, 2),
        nifty_close=round(nifty_close, 2),
        nifty_ema_50=round(nifty_ema_50, 2),
    )


def fetch_macro_data() -> dict:
    """Download daily data for NIFTY 50 and India VIX and compute indicators."""
    settings = get_settings()
    nifty_sym = settings.NIFTY_INDEX_SYMBOL
    vix_sym = settings.INDIA_VIX_SYMBOL

    logger.info("Fetching macro regime data (%s, %s)...", nifty_sym, vix_sym)
    df = yf.download(
        tickers=[nifty_sym, vix_sym],
        period="6mo",
        interval="1d",
        progress=False,
        auto_adjust=False,
    )

    if df.empty:
        raise ValueError("yfinance returned empty dataframe for macro symbols")

    # Handle MultiIndex columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        if "Close" in df.columns.levels[0]:
            close_df = df["Close"]
        else:
            close_df = df.xs("Close", axis=1, level=0)
    else:
        close_df = df[["Close"]]

    if nifty_sym not in close_df.columns or vix_sym not in close_df.columns:
        raise ValueError(f"Missing expected macro symbols in downloaded data. Found: {list(close_df.columns)}")

    nifty_series = close_df[nifty_sym].dropna()
    vix_series = close_df[vix_sym].dropna()

    if len(nifty_series) < 50:
        raise ValueError(f"Insufficient history for NIFTY 50-day EMA: {len(nifty_series)} bars")
    if vix_series.empty:
        raise ValueError("No valid India VIX data points")

    nifty_ema_50_series = nifty_series.ewm(span=50, adjust=False).mean()

    latest_nifty_close = float(nifty_series.iloc[-1])
    latest_nifty_ema_50 = float(nifty_ema_50_series.iloc[-1])
    latest_vix = float(vix_series.iloc[-1])
    as_of = datetime.now(timezone.utc).isoformat()

    return {
        "vix": latest_vix,
        "nifty_close": latest_nifty_close,
        "nifty_ema_50": latest_nifty_ema_50,
        "as_of": as_of,
    }


def get_regime_assessment(force_refresh: bool = False) -> RegimeAssessment:
    """Fetch macro indicators (with caching) and evaluate current market regime.

    Fails closed (allow_new_entries=False) on any data or network error.
    """
    settings = get_settings()
    try:
        data = cache.get_or_set(
            namespace="macro_regime",
            cache_key="india_macro",
            fetcher=fetch_macro_data,
            ttl_minutes=settings.REGIME_CACHE_TTL_MINUTES,
            force_refresh=force_refresh,
        )
        assessment = evaluate_regime(
            vix=float(data["vix"]),
            nifty_close=float(data["nifty_close"]),
            nifty_ema_50=float(data["nifty_ema_50"]),
        )
        assessment.as_of = str(data.get("as_of", ""))
        return assessment
    except Exception as exc:  # noqa: BLE001 - fail-closed on any error
        logger.exception("Failed to evaluate macro market regime: %s", exc)
        return RegimeAssessment(
            allow_new_entries=False,
            risk_multiplier=0.0,
            reasons=["MACRO_DATA_UNAVAILABLE"],
            as_of=datetime.now(timezone.utc).isoformat(),
        )
