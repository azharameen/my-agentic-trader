from __future__ import annotations

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


def test_load_history_uses_mocked_yfinance_boundary(monkeypatch):
    frame = pd.DataFrame({column: [100.0] for column in market_data.REQUIRED_COLUMNS})
    monkeypatch.setattr(market_data.yf, "download", lambda *args, **kwargs: frame)

    result = market_data.load_history("TEST.NS", "1y")

    assert result.source == "yfinance"
    assert result.frame.equals(frame)
