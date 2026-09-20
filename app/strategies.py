"""Pluggable deterministic setup strategies and priority resolution engine (ADR-024).

Implements:
  1. PullbackInUptrendStrategy (Trend-following oversold pullbacks)
  2. BreakoutMomentumStrategy (20-day high momentum expansions)
  3. BollingerMeanReversionStrategy (Lower Bollinger Band oversold reversals)
  4. Deterministic priority resolution: BREAKOUT > PULLBACK > MEAN_REVERSION
  5. Strategy-specific risk parameter profiles
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

import pandas as pd

from config.settings import Settings, get_settings


class SetupStrategy(Protocol):
    """Contract implemented by deterministic setup filters."""

    name: str

    def qualifies(self, row: pd.Series, settings: Settings) -> bool:
        """Return whether the latest indicator row qualifies."""


class PullbackInUptrendStrategy:
    """Uptrend, oversold pullback, liquid tape (baseline strategy)."""

    name = "pullback_in_uptrend"

    def qualifies(self, row: pd.Series, settings: Settings) -> bool:
        try:
            values = (
                row["close"],
                row["ema_200"],
                row["rsi_14"],
                row["volume"],
                row["avg_volume_20"],
            )
        except (KeyError, TypeError):
            return False

        if any(pd.isna(value) for value in values):
            return False
        price, ema_200, rsi, volume, avg_volume = values
        return bool(
            price > ema_200
            and rsi < settings.RSI_OVERSOLD_MAX
            and volume > avg_volume * settings.VOLUME_RATIO_MIN
        )


class BreakoutMomentumStrategy:
    """Momentum expansion breaking out of 20-day highs with high volume."""

    name = "breakout_momentum"

    def qualifies(self, row: pd.Series, settings: Settings) -> bool:
        try:
            values = (
                row["close"],
                row["high_20"],
                row["ema_50"],
                row["volume"],
                row["avg_volume_20"],
            )
        except (KeyError, TypeError):
            return False

        if any(pd.isna(value) for value in values):
            return False
        price, high_20, ema_50, volume, avg_volume = values
        return bool(
            price > high_20
            and price > ema_50
            and volume > avg_volume * 1.5
        )


class BollingerMeanReversionStrategy:
    """Mean reversion bounce from lower Bollinger Band in secular uptrend."""

    name = "bollinger_mean_reversion"

    def qualifies(self, row: pd.Series, settings: Settings) -> bool:
        try:
            values = (
                row["close"],
                row["bb_lower_20"],
                row["rsi_14"],
                row["ema_200"],
                row["volume"],
                row["avg_volume_20"],
            )
        except (KeyError, TypeError):
            return False

        if any(pd.isna(value) for value in values):
            return False
        price, bb_lower, rsi, ema_200, volume, avg_volume = values
        return bool(
            price <= bb_lower
            and rsi < 30.0
            and price > ema_200
            and volume > avg_volume * settings.VOLUME_RATIO_MIN
        )


@dataclass(frozen=True)
class StrategyRiskProfile:
    """Strategy-specific ATR stop multipliers and target expectations."""

    name: str
    atr_soft_mult: float
    atr_hard_mult: float
    min_risk_to_reward: float


_STRATEGY_RISK_PROFILES: dict[str, StrategyRiskProfile] = {
    "breakout_momentum": StrategyRiskProfile(
        name="breakout_momentum",
        atr_soft_mult=1.0,
        atr_hard_mult=2.0,
        min_risk_to_reward=3.0,
    ),
    "pullback_in_uptrend": StrategyRiskProfile(
        name="pullback_in_uptrend",
        atr_soft_mult=1.5,
        atr_hard_mult=2.5,
        min_risk_to_reward=2.0,
    ),
    "bollinger_mean_reversion": StrategyRiskProfile(
        name="bollinger_mean_reversion",
        atr_soft_mult=1.2,
        atr_hard_mult=2.0,
        min_risk_to_reward=2.0,
    ),
}

# Deterministic hierarchy: BREAKOUT > PULLBACK > MEAN_REVERSION
STRATEGY_PRIORITY: list[str] = [
    "breakout_momentum",
    "pullback_in_uptrend",
    "bollinger_mean_reversion",
]

_ALL_STRATEGIES: dict[str, SetupStrategy] = {
    BreakoutMomentumStrategy.name: BreakoutMomentumStrategy(),
    PullbackInUptrendStrategy.name: PullbackInUptrendStrategy(),
    BollingerMeanReversionStrategy.name: BollingerMeanReversionStrategy(),
}


def get_setup_strategy(name: str) -> SetupStrategy:
    """Resolve a named strategy, failing closed for unknown configuration."""
    try:
        return _ALL_STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown setup strategy: {name}") from exc


def get_strategy_risk_profile(strategy_name: Optional[str] = None) -> StrategyRiskProfile:
    """Return the risk profile for a strategy, falling back to settings baseline."""
    settings = get_settings()
    if strategy_name and strategy_name in _STRATEGY_RISK_PROFILES:
        return _STRATEGY_RISK_PROFILES[strategy_name]
    return StrategyRiskProfile(
        name="default",
        atr_soft_mult=settings.ATR_SOFT_MULT,
        atr_hard_mult=settings.ATR_HARD_MULT,
        min_risk_to_reward=settings.MIN_RISK_TO_REWARD,
    )


def evaluate_all_strategies(
    row: pd.Series,
    settings: Optional[Settings] = None,
) -> tuple[Optional[SetupStrategy], list[str]]:
    """Simultaneously evaluate all strategies against the latest bar.

    Returns:
        (primary_strategy, secondary_strategy_names)
        If no strategy qualifies, returns (None, []).
    """
    cfg = settings or get_settings()
    qualifying_names: list[str] = []

    for name in STRATEGY_PRIORITY:
        strategy = _ALL_STRATEGIES[name]
        if strategy.qualifies(row, cfg):
            qualifying_names.append(name)

    if not qualifying_names:
        return None, []

    primary_name = qualifying_names[0]
    secondary_names = qualifying_names[1:]
    return _ALL_STRATEGIES[primary_name], secondary_names
