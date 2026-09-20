"""Tests for deterministic India-market macro regime policy and ingestion (ADR-011)."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from app import pipeline, regime


def test_evaluate_regime_normal() -> None:
    """Normal market condition: VIX below elevated threshold, NIFTY above 50 EMA."""
    assessment = regime.evaluate_regime(
        vix=15.2,
        nifty_close=24500.0,
        nifty_ema_50=24000.0,
    )
    assert assessment.allow_new_entries is True
    assert assessment.risk_multiplier == 1.0
    assert assessment.reasons == []
    assert assessment.vix == 15.2
    assert assessment.nifty_close == 24500.0
    assert assessment.nifty_ema_50 == 24000.0


def test_evaluate_regime_elevated_vix() -> None:
    """Elevated VIX (19.0 <= VIX <= 24.0) cuts risk budget in half."""
    assessment = regime.evaluate_regime(
        vix=21.5,
        nifty_close=24500.0,
        nifty_ema_50=24000.0,
    )
    assert assessment.allow_new_entries is True
    assert assessment.risk_multiplier == 0.5
    assert assessment.reasons == ["INDIA_VIX_ELEVATED"]


def test_evaluate_regime_crisis_vix() -> None:
    """Crisis VIX (> 24.0) completely vetoes new proposals."""
    assessment = regime.evaluate_regime(
        vix=26.5,
        nifty_close=24500.0,
        nifty_ema_50=24000.0,
    )
    assert assessment.allow_new_entries is False
    assert assessment.risk_multiplier == 0.0
    assert "INDIA_VIX_CRISIS" in assessment.reasons


def test_evaluate_regime_nifty_below_50_ema() -> None:
    """NIFTY close below 50-day EMA vetoes new proposals."""
    assessment = regime.evaluate_regime(
        vix=14.0,
        nifty_close=23800.0,
        nifty_ema_50=24000.0,
    )
    assert assessment.allow_new_entries is False
    assert assessment.risk_multiplier == 0.0
    assert "NIFTY_BELOW_EMA_50" in assessment.reasons


def test_evaluate_regime_compound_crisis() -> None:
    """Both crisis VIX and NIFTY downtrend trigger compound reasons."""
    assessment = regime.evaluate_regime(
        vix=27.0,
        nifty_close=23000.0,
        nifty_ema_50=24000.0,
    )
    assert assessment.allow_new_entries is False
    assert assessment.risk_multiplier == 0.0
    assert "INDIA_VIX_CRISIS" in assessment.reasons
    assert "NIFTY_BELOW_EMA_50" in assessment.reasons


def test_evaluate_regime_custom_thresholds() -> None:
    """Explicit keyword threshold overrides."""
    assessment = regime.evaluate_regime(
        vix=17.0,
        nifty_close=25000.0,
        nifty_ema_50=24000.0,
        elevated_vix=16.0,
        crisis_vix=20.0,
    )
    assert assessment.allow_new_entries is True
    assert assessment.risk_multiplier == 0.5
    assert assessment.reasons == ["INDIA_VIX_ELEVATED"]


def _make_mock_macro_df(n_bars: int = 60) -> pd.DataFrame:
    """Create a realistic MultiIndex DataFrame mimicking yfinance.download."""
    dates = pd.date_range("2026-01-01", periods=n_bars, freq="B")
    nifty_prices = np.linspace(23000, 25000, n_bars)
    vix_prices = np.linspace(14, 16, n_bars)

    arrays = [
        ["Close", "Close", "Open", "Open"],
        ["^NSEI", "^INDIAVIX", "^NSEI", "^INDIAVIX"],
    ]
    tuples = list(zip(*arrays, strict=False))
    columns = pd.MultiIndex.from_tuples(tuples)

    data = np.column_stack([
        nifty_prices,
        vix_prices,
        nifty_prices - 10,
        vix_prices - 0.2,
    ])
    return pd.DataFrame(data, index=dates, columns=columns)


def test_fetch_macro_data_success() -> None:
    """Successfully compute EMA 50 and extract latest metrics from yfinance."""
    mock_df = _make_mock_macro_df(60)
    with patch("yfinance.download", return_value=mock_df):
        data = regime.fetch_macro_data()
        assert "vix" in data
        assert "nifty_close" in data
        assert "nifty_ema_50" in data
        assert data["nifty_close"] > 24000
        assert data["nifty_ema_50"] > 23000
        assert 13 < data["vix"] < 17


def test_fetch_macro_data_empty_error() -> None:
    """Empty dataframe raises ValueError."""
    with patch("yfinance.download", return_value=pd.DataFrame()):
        with pytest.raises(ValueError, match="empty dataframe"):
            regime.fetch_macro_data()


def test_fetch_macro_data_missing_symbol_error() -> None:
    """Missing symbol column raises ValueError."""
    dates = pd.date_range("2026-01-01", periods=10, freq="B")
    df = pd.DataFrame({"Close": [100.0] * 10}, index=dates)
    with patch("yfinance.download", return_value=df):
        with pytest.raises(ValueError, match="Missing expected macro symbols"):
            regime.fetch_macro_data()


def test_fetch_macro_data_insufficient_history() -> None:
    """Fewer than 50 bars raises ValueError."""
    mock_df = _make_mock_macro_df(30)
    with patch("yfinance.download", return_value=mock_df):
        with pytest.raises(ValueError, match="Insufficient history"):
            regime.fetch_macro_data()


def test_get_regime_assessment_fail_closed() -> None:
    """Network failure during regime assessment fails closed."""
    with patch("yfinance.download", side_effect=RuntimeError("Yahoo Finance Connection Timeout")):
        assessment = regime.get_regime_assessment(force_refresh=True)
        assert assessment.allow_new_entries is False
        assert assessment.risk_multiplier == 0.0
        assert assessment.reasons == ["MACRO_DATA_UNAVAILABLE"]


def test_pipeline_scan_halts_on_macro_veto() -> None:
    """Universe scan halts immediately when macro regime vetoes new entries."""
    veto_assessment = regime.RegimeAssessment(
        allow_new_entries=False,
        risk_multiplier=0.0,
        reasons=["INDIA_VIX_CRISIS"],
        vix=26.5,
        nifty_close=24500.0,
        nifty_ema_50=24000.0,
    )
    with patch("app.telegram_bot.notify_text") as mock_notify:
        result = pipeline.run_universe_scan(
            universe_symbols=["RELIANCE", "TCS", "INFY"],
            regime_assessment=veto_assessment,
        )
        assert result == []
        mock_notify.assert_called_once()
        msg = mock_notify.call_args[0][1]
        assert "🛑" in msg
        assert "INDIA_VIX_CRISIS" in msg
