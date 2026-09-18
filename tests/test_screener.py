"""Unit tests for the deterministic screener filter (app/screener.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.screener import _compute_indicators, _passes_setup_filter


def _row(**overrides) -> pd.Series:
    base = {"close": 110.0, "ema_200": 100.0, "rsi_14": 30.0, "volume": 600.0, "avg_volume_20": 1000.0}
    base.update(overrides)
    return pd.Series(base)


def test_qualifying_row_passes():
    assert _passes_setup_filter(_row())


def test_price_below_ema_fails():
    assert not _passes_setup_filter(_row(close=90.0))


def test_rsi_at_or_above_threshold_fails():
    assert not _passes_setup_filter(_row(rsi_14=50.0))


def test_thin_volume_fails():
    # 400 < 1000 * 0.5 (VOLUME_RATIO_MIN default)
    assert not _passes_setup_filter(_row(volume=400.0))


@pytest.mark.parametrize("field", ["close", "ema_200", "rsi_14", "volume", "avg_volume_20"])
def test_nan_in_any_field_fails_safely(field):
    assert _passes_setup_filter(_row(**{field: np.nan})) is False


def test_missing_columns_fail_safely():
    assert _passes_setup_filter(pd.Series({"close": 100.0})) is False


def test_compute_indicators_adds_expected_columns():
    n = 260
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    prices = pd.Series(100 + np.cumsum(np.random.default_rng(0).normal(0, 1, n)), index=dates)
    df = pd.DataFrame({
        "Open": prices, "High": prices + 1, "Low": prices - 1,
        "Close": prices, "Volume": pd.Series(1_000_000.0, index=dates),
    })

    out = _compute_indicators(df)

    for col in ("ema_200", "rsi_14", "atr_14", "avg_volume_20"):
        assert col in out.columns
    # With 260 days of history the latest bar should have fully-formed indicators.
    latest = out.iloc[-1]
    assert not pd.isna(latest["ema_200"])
    assert not pd.isna(latest["rsi_14"])
    assert not pd.isna(latest["atr_14"])
