"""Validated market-data loading with source provenance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


@dataclass(frozen=True)
class MarketDataResult:
    frame: pd.DataFrame
    source: str
    fetched_at: datetime


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=6),
    retry=retry_if_exception_type(Exception),
)
def load_history(nse_symbol: str, period: str) -> MarketDataResult:
    frame = yf.download(nse_symbol, period=period, interval="1d", auto_adjust=True, progress=False)
    if frame is None or frame.empty:
        raise ValueError(f"No market data returned for {nse_symbol}")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    return MarketDataResult(
        frame=frame,
        source="yfinance",
        fetched_at=datetime.now(timezone.utc),
    )
