"""Validated market-data loading with source provenance and incremental PostgreSQL caching (ADR-026)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import yfinance as yf
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app import db

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def _validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Market data missing required columns: {sorted(missing)}")
    values = frame.loc[:, REQUIRED_COLUMNS].apply(pd.to_numeric, errors="coerce")
    if values.isna().any().any():
        raise ValueError("Market data contains non-numeric OHLCV values")
    if (values["Volume"] < 0).any():
        raise ValueError("Market data contains negative volume")
    return values


@dataclass(frozen=True)
class MarketDataResult:
    frame: pd.DataFrame
    source: str
    fetched_at: datetime


def _canonical_symbol(symbol: str) -> str:
    """Normalize symbol to clean uppercase without .NS suffix."""
    return symbol.replace(".NS", "").replace(".ns", "").strip().upper()


def save_bars(symbol: str, frame: pd.DataFrame, source: str = "yfinance") -> int:
    """Upsert daily OHLCV bars into PostgreSQL ohlcv_daily_bars table."""
    clean_sym = _canonical_symbol(symbol)
    if frame is None or frame.empty:
        return 0

    saved_count = 0
    query = """
    INSERT INTO ohlcv_daily_bars (symbol, timestamp, open_price, high_price, low_price, close_price, volume, source)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (symbol, timestamp) DO UPDATE SET
        open_price = EXCLUDED.open_price,
        high_price = EXCLUDED.high_price,
        low_price = EXCLUDED.low_price,
        close_price = EXCLUDED.close_price,
        volume = EXCLUDED.volume,
        source = EXCLUDED.source
    """

    for idx, row in frame.iterrows():
        ts = str(idx.date() if hasattr(idx, "date") else idx)[:10]
        try:
            db.execute(
                query,
                (
                    clean_sym,
                    ts,
                    float(row["Open"]),
                    float(row["High"]),
                    float(row["Low"]),
                    float(row["Close"]),
                    int(row["Volume"]),
                    source,
                ),
            )
            saved_count += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not upsert OHLCV bar %s for %s: %s", ts, clean_sym, exc)

    return saved_count


def load_cached_bars(symbol: str) -> Optional[pd.DataFrame]:
    """Retrieve all stored OHLCV daily bars for a symbol from PostgreSQL."""
    clean_sym = _canonical_symbol(symbol)
    try:
        rows = db.fetchall(
            "SELECT timestamp, open_price, high_price, low_price, close_price, volume FROM ohlcv_daily_bars WHERE symbol = %s ORDER BY timestamp ASC",
            (clean_sym,),
        )
        if not rows:
            return None

        records = []
        index_dates = []
        for r in rows:
            index_dates.append(pd.to_datetime(r["timestamp"]))
            records.append({
                "Open": float(r["open_price"]),
                "High": float(r["high_price"]),
                "Low": float(r["low_price"]),
                "Close": float(r["close_price"]),
                "Volume": int(r["volume"]),
            })

        frame = pd.DataFrame(records, index=index_dates)
        return _validate_frame(frame)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load cached bars for %s: %s", clean_sym, exc)
        return None


def get_latest_cached_date(symbol: str) -> Optional[str]:
    """Return the most recent bar timestamp (YYYY-MM-DD) stored for a symbol."""
    clean_sym = _canonical_symbol(symbol)
    try:
        row = db.fetchone(
            "SELECT MAX(timestamp) AS latest_date FROM ohlcv_daily_bars WHERE symbol = %s",
            (clean_sym,),
        )
        return row.get("latest_date") if row else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not query latest cached date for %s: %s", clean_sym, exc)
        return None


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=6),
    retry=retry_if_exception_type(Exception),
)
def _download_raw_yfinance(nse_symbol: str, period: str) -> pd.DataFrame:
    """Direct yfinance download with retry policy."""
    frame = yf.download(nse_symbol, period=period, interval="1d", auto_adjust=True, progress=False)
    if frame is None or frame.empty:
        raise ValueError(f"No market data returned for {nse_symbol}")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    return _validate_frame(frame)


def load_history(nse_symbol: str, period: str = "1y", use_cache: bool = True) -> MarketDataResult:
    """Load historical OHLCV data using incremental PostgreSQL caching with yfinance fallback."""
    clean_sym = _canonical_symbol(nse_symbol)
    yfinance_ticker = nse_symbol if nse_symbol.endswith(".NS") else f"{clean_sym}.NS"

    if not use_cache:
        frame = _download_raw_yfinance(yfinance_ticker, period=period)
        return MarketDataResult(frame=frame, source="yfinance", fetched_at=datetime.now(timezone.utc))

    cached_frame = load_cached_bars(clean_sym)

    # If warm cache with sufficient history (>= 50 bars), do delta update
    if cached_frame is not None and len(cached_frame) >= 50:
        try:
            delta_frame = _download_raw_yfinance(yfinance_ticker, period="5d")
            if delta_frame is not None and not delta_frame.empty:
                save_bars(clean_sym, delta_frame, source="yfinance")
                merged = load_cached_bars(clean_sym)
                if merged is not None and not merged.empty:
                    return MarketDataResult(
                        frame=merged,
                        source="postgresql_incremental",
                        fetched_at=datetime.now(timezone.utc),
                    )
        except Exception as exc:  # noqa: BLE001 - fallback to existing cache
            logger.warning(
                "Delta fetch failed for %s (%s); falling back to stored cached history.",
                clean_sym,
                exc,
            )
        return MarketDataResult(
            frame=cached_frame,
            source="postgresql_cache",
            fetched_at=datetime.now(timezone.utc),
        )

    # Cold start: download full period and populate database
    try:
        frame = _download_raw_yfinance(yfinance_ticker, period=period)
        save_bars(clean_sym, frame, source="yfinance")
        return MarketDataResult(frame=frame, source="yfinance", fetched_at=datetime.now(timezone.utc))
    except Exception as exc:
        if cached_frame is not None and not cached_frame.empty:
            logger.warning(
                "Full download failed for %s (%s); falling back to existing cached history.",
                clean_sym,
                exc,
            )
            return MarketDataResult(
                frame=cached_frame,
                source="postgresql_cache",
                fetched_at=datetime.now(timezone.utc),
            )
        raise
