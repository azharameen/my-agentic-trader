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
from config.settings import get_settings

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


def _period_to_days(period: str) -> int:
    """Convert a yfinance-style period string ('5d', '6mo', '1y', '2y') to a day count."""
    period = period.strip().lower()
    try:
        if period.endswith("d"):
            return int(period[:-1])
        if period.endswith("mo"):
            return int(period[:-2]) * 31
        if period.endswith("y"):
            return int(period[:-1]) * 366
    except ValueError:
        pass
    return 365


def _download_raw_groww(clean_symbol: str, period: str) -> Optional[pd.DataFrame]:
    """Fetch daily historical candles from Groww (ADR-036). Returns None if unavailable.

    Fails fast (no retries) so the caller can fall back to yfinance immediately;
    yfinance already has its own retry policy.
    """
    from app.groww_client import get_groww_client

    client = get_groww_client()
    if not client.is_configured():
        return None

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - pd.Timedelta(days=_period_to_days(period))
    response = client.get_historical_candle_data(
        trading_symbol=clean_symbol,
        start_time=start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        end_time=end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        interval_in_minutes=1440,
    )
    candles = response.get("candles") if response else None
    if not candles:
        return None

    records = []
    index_dates = []
    for candle in candles:
        # [epoch_seconds, open, high, low, close, volume]
        index_dates.append(pd.to_datetime(candle[0], unit="s"))
        records.append({
            "Open": float(candle[1]),
            "High": float(candle[2]),
            "Low": float(candle[3]),
            "Close": float(candle[4]),
            "Volume": int(candle[5]),
        })
    frame = pd.DataFrame(records, index=index_dates)
    return _validate_frame(frame)


def _download_raw(clean_symbol: str, yfinance_ticker: str, period: str) -> tuple[pd.DataFrame, str]:
    """Groww-first historical fetch with automatic yfinance fallback (ADR-036)."""
    if get_settings().GROWW_MARKET_DATA_ENABLED:
        try:
            frame = _download_raw_groww(clean_symbol, period)
            if frame is not None and not frame.empty:
                return frame, "groww_historical"
        except Exception as exc:  # noqa: BLE001
            logger.info("Groww historical data unavailable for %s (%s); falling back to yfinance.", clean_symbol, exc)
    return _download_raw_yfinance(yfinance_ticker, period=period), "yfinance"


def load_history(nse_symbol: str, period: str = "1y", use_cache: bool = True) -> MarketDataResult:
    """Load historical OHLCV data using incremental PostgreSQL caching with Groww-first, yfinance-fallback sourcing."""
    clean_sym = _canonical_symbol(nse_symbol)
    yfinance_ticker = nse_symbol if nse_symbol.endswith(".NS") else f"{clean_sym}.NS"

    if not use_cache:
        frame, source = _download_raw(clean_sym, yfinance_ticker, period)
        return MarketDataResult(frame=frame, source=source, fetched_at=datetime.now(timezone.utc))

    cached_frame = load_cached_bars(clean_sym)

    # If warm cache with sufficient history (>= 50 bars), do delta update
    if cached_frame is not None and len(cached_frame) >= 50:
        try:
            delta_frame, delta_source = _download_raw(clean_sym, yfinance_ticker, "5d")
            if delta_frame is not None and not delta_frame.empty:
                save_bars(clean_sym, delta_frame, source=delta_source)
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
        frame, source = _download_raw(clean_sym, yfinance_ticker, period)
        save_bars(clean_sym, frame, source=source)
        return MarketDataResult(frame=frame, source=source, fetched_at=datetime.now(timezone.utc))
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


SECTOR_INDEX_TICKERS: dict[str, str] = {
    "IT": "^CNXIT",
    "BANKING": "^NSEBANK",
    "AUTO": "^CNXAUTO",
    "PHARMA": "^CNXPHARMA",
    "METALS": "^CNXMETAL",
    "FMCG": "^CNXFMCG",
    "ENERGY": "^CNXENERGY",
    "REALTY": "^CNXREALTY",
    "INFRA": "^CNXINFRA",
}


def resample_to_weekly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV DataFrame into weekly Friday bars (ADR-030)."""
    if daily_df is None or daily_df.empty:
        return pd.DataFrame()
    df = daily_df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    weekly = df.resample("W-FRI").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()
    return weekly


def load_sector_indices_history(period: str = "6mo") -> dict[str, pd.DataFrame]:
    """Load historical daily bars for key NSE Sectoral Indices (ADR-029)."""
    results = {}
    for sector, ticker in SECTOR_INDEX_TICKERS.items():
        try:
            res = load_history(ticker, period=period)
            if res and res.frame is not None and not res.frame.empty:
                results[sector] = res.frame
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not load sector index %s (%s): %s", sector, ticker, exc)
    return results

