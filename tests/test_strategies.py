from __future__ import annotations

import pandas as pd
import pytest

from app import risk, screener, strategies
from config.settings import get_settings


@pytest.fixture
def base_settings():
    get_settings.cache_clear()
    return get_settings()


def test_pullback_strategy_qualification(base_settings):
    strat = strategies.PullbackInUptrendStrategy()

    # Passes
    row_pass = pd.Series({
        "close": 150.0,
        "ema_200": 140.0,
        "rsi_14": 38.0,
        "volume": 1000.0,
        "avg_volume_20": 1000.0,
    })
    assert strat.qualifies(row_pass, base_settings) is True

    # Fails uptrend
    row_fail_uptrend = pd.Series({
        "close": 130.0,
        "ema_200": 140.0,
        "rsi_14": 38.0,
        "volume": 1000.0,
        "avg_volume_20": 1000.0,
    })
    assert strat.qualifies(row_fail_uptrend, base_settings) is False

    # Fails RSI
    row_fail_rsi = pd.Series({
        "close": 150.0,
        "ema_200": 140.0,
        "rsi_14": 48.0,
        "volume": 1000.0,
        "avg_volume_20": 1000.0,
    })
    assert strat.qualifies(row_fail_rsi, base_settings) is False


def test_breakout_strategy_qualification(base_settings):
    strat = strategies.BreakoutMomentumStrategy()

    # Passes: Price > 20-day High, Price > EMA 50, Volume > 1.5 * avg
    row_pass = pd.Series({
        "close": 210.0,
        "high_20": 200.0,
        "ema_50": 190.0,
        "volume": 1600.0,
        "avg_volume_20": 1000.0,
    })
    assert strat.qualifies(row_pass, base_settings) is True

    # Fails High 20 breakout
    row_fail_high = pd.Series({
        "close": 195.0,
        "high_20": 200.0,
        "ema_50": 190.0,
        "volume": 1600.0,
        "avg_volume_20": 1000.0,
    })
    assert strat.qualifies(row_fail_high, base_settings) is False

    # Fails Volume expansion (< 1.5 * avg)
    row_fail_vol = pd.Series({
        "close": 210.0,
        "high_20": 200.0,
        "ema_50": 190.0,
        "volume": 1200.0,
        "avg_volume_20": 1000.0,
    })
    assert strat.qualifies(row_fail_vol, base_settings) is False


def test_bollinger_mean_reversion_qualification(base_settings):
    strat = strategies.BollingerMeanReversionStrategy()

    # Passes: Price <= Lower Band, RSI < 30, Price > EMA 200, Volume > 0.5 * avg
    row_pass = pd.Series({
        "close": 95.0,
        "bb_lower_20": 100.0,
        "rsi_14": 26.0,
        "ema_200": 85.0,
        "volume": 600.0,
        "avg_volume_20": 1000.0,
    })
    assert strat.qualifies(row_pass, base_settings) is True

    # Fails lower band (Price > Lower Band)
    row_fail_band = pd.Series({
        "close": 105.0,
        "bb_lower_20": 100.0,
        "rsi_14": 26.0,
        "ema_200": 85.0,
        "volume": 600.0,
        "avg_volume_20": 1000.0,
    })
    assert strat.qualifies(row_fail_band, base_settings) is False

    # Fails oversold threshold (RSI >= 30)
    row_fail_rsi = pd.Series({
        "close": 95.0,
        "bb_lower_20": 100.0,
        "rsi_14": 35.0,
        "ema_200": 85.0,
        "volume": 600.0,
        "avg_volume_20": 1000.0,
    })
    assert strat.qualifies(row_fail_rsi, base_settings) is False


def test_deterministic_priority_resolution(base_settings):
    # Bar qualifying for BOTH Breakout and Pullback: Breakout MUST win
    row_multi = pd.Series({
        "close": 210.0,
        "high_20": 200.0,
        "ema_50": 190.0,
        "ema_200": 170.0,
        "rsi_14": 39.0,
        "volume": 2000.0,
        "avg_volume_20": 1000.0,
        "bb_lower_20": 180.0,
    })
    primary, secondaries = strategies.evaluate_all_strategies(row_multi, base_settings)
    assert primary is not None
    assert primary.name == "breakout_momentum"
    assert "pullback_in_uptrend" in secondaries

    # Bar qualifying only for Pullback
    row_pullback_only = pd.Series({
        "close": 180.0,
        "high_20": 200.0,
        "ema_50": 185.0,
        "ema_200": 170.0,
        "rsi_14": 39.0,
        "volume": 800.0,
        "avg_volume_20": 1000.0,
        "bb_lower_20": 160.0,
    })
    primary_pb, secondaries_pb = strategies.evaluate_all_strategies(row_pullback_only, base_settings)
    assert primary_pb is not None
    assert primary_pb.name == "pullback_in_uptrend"
    assert secondaries_pb == []

    # Bar qualifying for nothing
    row_none = pd.Series({
        "close": 100.0,
        "high_20": 200.0,
        "ema_50": 150.0,
        "ema_200": 160.0,
        "rsi_14": 55.0,
        "volume": 400.0,
        "avg_volume_20": 1000.0,
        "bb_lower_20": 90.0,
    })
    primary_none, secondaries_none = strategies.evaluate_all_strategies(row_none, base_settings)
    assert primary_none is None
    assert secondaries_none == []


def test_strategy_risk_profiles():
    breakout_prof = strategies.get_strategy_risk_profile("breakout_momentum")
    assert breakout_prof.atr_soft_mult == 1.0
    assert breakout_prof.atr_hard_mult == 2.0
    assert breakout_prof.min_risk_to_reward == 3.0

    pullback_prof = strategies.get_strategy_risk_profile("pullback_in_uptrend")
    assert pullback_prof.atr_soft_mult == 1.5
    assert pullback_prof.atr_hard_mult == 2.5
    assert pullback_prof.min_risk_to_reward == 2.0

    mean_rev_prof = strategies.get_strategy_risk_profile("bollinger_mean_reversion")
    assert mean_rev_prof.atr_soft_mult == 1.2
    assert mean_rev_prof.atr_hard_mult == 2.0
    assert mean_rev_prof.min_risk_to_reward == 2.0


def test_risk_engine_applies_strategy_profile():
    # Breakout setup: 1.0 soft / 2.0 hard / 3.0 R:R
    # Entry: 1000.0, ATR: 50.0
    # Soft stop: 1000 - 1.0*50 = 950.0
    # Hard stop: 1000 - 2.0*50 = 900.0
    # Risk/share: 100.0
    # Target: 1000 + 3.0*100 = 1300.0
    prop_breakout = risk.calculate_risk(
        symbol="TCS",
        entry_price=1000.0,
        atr=50.0,
        portfolio_capital=100000.0,
        strategy_name="breakout_momentum",
    )
    assert prop_breakout is not None
    assert prop_breakout.soft_stop == 950.0
    assert prop_breakout.hard_stop == 900.0
    assert prop_breakout.target_price == 1300.0
    assert prop_breakout.risk_to_reward == 3.0

    # Pullback setup: 1.5 soft / 2.5 hard / 2.0 R:R
    # Soft stop: 1000 - 1.5*50 = 925.0
    # Hard stop: 1000 - 2.5*50 = 875.0
    # Risk/share: 125.0
    # Target: 1000 + 2.0*125 = 1250.0
    prop_pullback = risk.calculate_risk(
        symbol="TCS",
        entry_price=1000.0,
        atr=50.0,
        portfolio_capital=100000.0,
        strategy_name="pullback_in_uptrend",
    )
    assert prop_pullback is not None
    assert prop_pullback.soft_stop == 925.0
    assert prop_pullback.hard_stop == 875.0
    assert prop_pullback.target_price == 1250.0
    assert prop_pullback.risk_to_reward == 2.0


def test_screener_compute_indicators_extension():
    # Generate 60 days of synthetic OHLCV bars
    dates = pd.date_range("2026-01-01", periods=60)
    data = {
        "Open": [100.0 + i for i in range(60)],
        "High": [105.0 + i for i in range(60)],
        "Low": [95.0 + i for i in range(60)],
        "Close": [102.0 + i for i in range(60)],
        "Volume": [100000.0 for _ in range(60)],
    }
    df = pd.DataFrame(data, index=dates)
    computed = screener._compute_indicators(df)

    assert "ema_200" in computed.columns
    assert "ema_50" in computed.columns
    assert "rsi_14" in computed.columns
    assert "atr_14" in computed.columns
    assert "high_20" in computed.columns
    assert "bb_middle_20" in computed.columns
    assert "bb_lower_20" in computed.columns
    assert "bb_upper_20" in computed.columns

    # Verify high_20 is shifted (bar 50 high_20 reflects max high of previous 20 bars)
    assert not pd.isna(computed["high_20"].iloc[-1])
    assert not pd.isna(computed["bb_middle_20"].iloc[-1])


def test_mtf_confluence_qualification(base_settings):
    pullback = strategies.PullbackInUptrendStrategy()
    breakout = strategies.BreakoutMomentumStrategy()

    # Pullback with passing MTF
    row_pb_pass = pd.Series({
        "close": 150.0,
        "ema_200": 140.0,
        "rsi_14": 38.0,
        "volume": 1000.0,
        "avg_volume_20": 1000.0,
        "weekly_ema_30": 145.0,
        "weekly_rsi_14": 48.0,
    })
    assert pullback.qualifies(row_pb_pass, base_settings) is True

    # Pullback fails MTF weekly EMA (close < weekly_ema_30)
    row_pb_fail_ema = pd.Series({
        "close": 150.0,
        "ema_200": 140.0,
        "rsi_14": 38.0,
        "volume": 1000.0,
        "avg_volume_20": 1000.0,
        "weekly_ema_30": 155.0,
        "weekly_rsi_14": 48.0,
    })
    assert pullback.qualifies(row_pb_fail_ema, base_settings) is False

    # Pullback fails MTF weekly RSI (< 45.0)
    row_pb_fail_rsi = pd.Series({
        "close": 150.0,
        "ema_200": 140.0,
        "rsi_14": 38.0,
        "volume": 1000.0,
        "avg_volume_20": 1000.0,
        "weekly_ema_30": 145.0,
        "weekly_rsi_14": 42.0,
    })
    assert pullback.qualifies(row_pb_fail_rsi, base_settings) is False

    # Breakout with passing MTF
    row_bo_pass = pd.Series({
        "close": 210.0,
        "high_20": 200.0,
        "ema_50": 190.0,
        "volume": 1600.0,
        "avg_volume_20": 1000.0,
        "weekly_ema_30": 195.0,
        "weekly_rsi_14": 55.0,
    })
    assert breakout.qualifies(row_bo_pass, base_settings) is True

    # Breakout fails MTF weekly RSI (< 50.0)
    row_bo_fail_rsi = pd.Series({
        "close": 210.0,
        "high_20": 200.0,
        "ema_50": 190.0,
        "volume": 1600.0,
        "avg_volume_20": 1000.0,
        "weekly_ema_30": 195.0,
        "weekly_rsi_14": 48.0,
    })
    assert breakout.qualifies(row_bo_fail_rsi, base_settings) is False

