"""Pluggable deterministic setup strategies for Phase 4 extensions."""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from config.settings import Settings


class SetupStrategy(Protocol):
    """Contract implemented by deterministic setup filters."""

    name: str

    def qualifies(self, row: pd.Series, settings: Settings) -> bool:
        """Return whether the latest indicator row qualifies."""


class PullbackInUptrendStrategy:
    """Current production strategy: uptrend, oversold pullback, liquid tape."""

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
        return (
            price > ema_200
            and rsi < settings.RSI_OVERSOLD_MAX
            and volume > avg_volume * settings.VOLUME_RATIO_MIN
        )


_DEFAULT_STRATEGIES: dict[str, SetupStrategy] = {
    PullbackInUptrendStrategy.name: PullbackInUptrendStrategy(),
}


def get_setup_strategy(name: str) -> SetupStrategy:
    """Resolve a named strategy, failing closed for unknown configuration."""
    try:
        return _DEFAULT_STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown setup strategy: {name}") from exc
