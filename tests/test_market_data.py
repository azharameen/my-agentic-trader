from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from app import market_data


def test_validate_frame_rejects_missing_ohlcv_columns():
    with pytest.raises(ValueError, match="missing required columns"):
        market_data._validate_frame(pd.DataFrame({"Close": [1.0]}))


def test_validate_frame_rejects_non_numeric_ohlcv_values():
    frame = pd.DataFrame({column: ["bad"] for column in market_data.REQUIRED_COLUMNS})

    with pytest.raises(ValueError, match="non-numeric"):
        market_data._validate_frame(frame)


def test_validate_frame_rejects_negative_volume():
    frame = pd.DataFrame({
        "Open": [100.0],
        "High": [105.0],
        "Low": [95.0],
        "Close": [102.0],
        "Volume": [-10],
    })
    with pytest.raises(ValueError, match="negative volume"):
        market_data._validate_frame(frame)


def test_load_history_uses_mocked_yfinance_boundary(monkeypatch):
    frame = pd.DataFrame({column: [100.0] for column in market_data.REQUIRED_COLUMNS})
    monkeypatch.setattr(market_data.yf, "download", lambda *args, **kwargs: frame)
    monkeypatch.setattr(market_data, "save_bars", lambda *args, **kwargs: 1)
    monkeypatch.setattr(market_data, "load_cached_bars", lambda *args, **kwargs: None)

    result = market_data.load_history("TEST.NS", "1y")

    assert result.source == "yfinance"
    assert result.frame.equals(frame)


def test_save_and_load_cached_bars(monkeypatch):
    stored = []

    def fake_execute(query, params=()):
        stored.append(params)

    def fake_fetchall(query, params=()):
        return [
            {
                "timestamp": "2026-09-18",
                "open_price": 100.0,
                "high_price": 105.0,
                "low_price": 98.0,
                "close_price": 104.0,
                "volume": 50000,
            }
        ]

    monkeypatch.setattr(market_data.db, "execute", fake_execute)
    monkeypatch.setattr(market_data.db, "fetchall", fake_fetchall)

    frame = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [105.0],
            "Low": [98.0],
            "Close": [104.0],
            "Volume": [50000],
        },
        index=[pd.to_datetime("2026-09-18")],
    )

    saved = market_data.save_bars("INFY", frame)
    assert saved == 1
    assert len(stored) == 1
    assert stored[0][0] == "INFY"
    assert stored[0][1] == "2026-09-18"

    loaded = market_data.load_cached_bars("INFY")
    assert loaded is not None
    assert len(loaded) == 1
    assert float(loaded.iloc[0]["Close"]) == 104.0


def test_load_history_incremental_cache_update(monkeypatch):
    # Construct 60 days of cached history
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(60)]
    cached_df = pd.DataFrame(
        {
            "Open": [100.0] * 60,
            "High": [105.0] * 60,
            "Low": [95.0] * 60,
            "Close": [102.0] * 60,
            "Volume": [1000] * 60,
        },
        index=pd.to_datetime(dates),
    )

    delta_df = pd.DataFrame(
        {
            "Open": [102.0],
            "High": [106.0],
            "Low": [101.0],
            "Close": [105.0],
            "Volume": [1500],
        },
        index=pd.to_datetime([date(2026, 3, 3)]),
    )

    call_params = []

    def fake_download(sym, period, **kwargs):
        call_params.append((sym, period))
        return delta_df

    saved_bars = []
    monkeypatch.setattr(market_data, "_download_raw_yfinance", fake_download)
    monkeypatch.setattr(market_data, "load_cached_bars", lambda sym: cached_df)
    monkeypatch.setattr(market_data, "save_bars", lambda sym, frame, **kwargs: saved_bars.append(frame))

    result = market_data.load_history("RELIANCE.NS", "1y", use_cache=True)

    assert result.source == "postgresql_incremental"
    assert len(call_params) == 1
    assert call_params[0][1] == "5d"  # Incremental fetch only asked for 5 days


def test_load_history_falls_back_to_cache_on_delta_failure(monkeypatch):
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(60)]
    cached_df = pd.DataFrame(
        {
            "Open": [100.0] * 60,
            "High": [105.0] * 60,
            "Low": [95.0] * 60,
            "Close": [102.0] * 60,
            "Volume": [1000] * 60,
        },
        index=pd.to_datetime(dates),
    )

    def fake_failing_download(*args, **kwargs):
        raise RuntimeError("401 Invalid Crumb / delisted")

    monkeypatch.setattr(market_data, "_download_raw_yfinance", fake_failing_download)
    monkeypatch.setattr(market_data, "load_cached_bars", lambda sym: cached_df)

    result = market_data.load_history("ABB.NS", "1y", use_cache=True)

    assert result.source == "postgresql_cache"
    assert len(result.frame) == 60


# --------------------------------------------------------------------------- #
# ADR-036: Groww-first historical data provider with automatic yfinance fallback
# --------------------------------------------------------------------------- #
def test_download_raw_groww_returns_none_when_not_configured(monkeypatch):
    """Groww-first dispatcher must fall straight to yfinance when Groww isn't configured (default test env)."""
    frame = pd.DataFrame({column: [100.0] for column in market_data.REQUIRED_COLUMNS})
    calls = []

    def fake_yfinance(sym, period):
        calls.append((sym, period))
        return frame

    monkeypatch.setattr(market_data, "_download_raw_yfinance", fake_yfinance)

    result_frame, source = market_data._download_raw("RELIANCE", "RELIANCE.NS", "1y")

    assert source == "yfinance"
    assert result_frame.equals(frame)
    assert calls == [("RELIANCE.NS", "1y")]


def test_download_raw_prefers_groww_when_configured(monkeypatch):
    """When Groww is configured and returns candles, it takes priority over yfinance."""
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    monkeypatch.setenv("GROWW_MARKET_DATA_ENABLED", "true")
    from config.settings import get_settings

    get_settings.cache_clear()

    groww_frame = pd.DataFrame(
        {column: [111.0] for column in market_data.REQUIRED_COLUMNS},
        index=[pd.to_datetime("2026-01-01")],
    )
    monkeypatch.setattr(market_data, "_download_raw_groww", lambda sym, period: groww_frame)

    def fail_yfinance(*args, **kwargs):
        raise AssertionError("yfinance should not be called when Groww succeeds")

    monkeypatch.setattr(market_data, "_download_raw_yfinance", fail_yfinance)

    frame, source = market_data._download_raw("RELIANCE", "RELIANCE.NS", "1y")

    assert source == "groww_historical"
    assert frame.equals(groww_frame)
    get_settings.cache_clear()


def test_download_raw_falls_back_to_yfinance_when_groww_errors(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    monkeypatch.setenv("GROWW_MARKET_DATA_ENABLED", "true")
    from config.settings import get_settings

    get_settings.cache_clear()

    def fake_groww_raises(sym, period):
        raise RuntimeError("rate limited")

    frame = pd.DataFrame({column: [100.0] for column in market_data.REQUIRED_COLUMNS})
    monkeypatch.setattr(market_data, "_download_raw_groww", fake_groww_raises)
    monkeypatch.setattr(market_data, "_download_raw_yfinance", lambda sym, period: frame)

    result_frame, source = market_data._download_raw("RELIANCE", "RELIANCE.NS", "1y")

    assert source == "yfinance"
    assert result_frame.equals(frame)
    get_settings.cache_clear()


def test_period_to_days_parses_common_suffixes():
    assert market_data._period_to_days("5d") == 5
    assert market_data._period_to_days("6mo") == 186
    assert market_data._period_to_days("1y") == 366
    assert market_data._period_to_days("bogus") == 365
