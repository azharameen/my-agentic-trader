"""
Quantitative screening engine.

Downloads daily OHLCV for the NIFTY 100 universe via `yfinance`, computes the
technical indicators (EMA_200, RSI_14, ATR_14) with pandas, and applies a
deterministic *pullback-in-an-uptrend* setup filter.

This module is pure math + data fetching. It contains no LLM calls and no
order logic — it only decides which symbols *qualify* for further analysis.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, Optional

import pandas as pd

from app import market_data
from app.strategies import get_setup_strategy
from config.settings import get_settings

logger = logging.getLogger(__name__)


def _load_history(nse_symbol: str, period: str) -> market_data.MarketDataResult:
    return market_data.load_history(nse_symbol, period)


def _to_nse_symbol(symbol: str) -> str:
    """Append the NSE exchange suffix if it is not already present.

    yfinance requires the `.NS` suffix for NSE-listed equities.
    """
    symbol = symbol.strip().upper()
    return symbol if symbol.endswith(".NS") else f"{symbol}.NS"


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Attach EMA_200, RSI_14 and ATR_14 columns to an OHLCV frame.

    Indicators are computed directly with pandas; yfinance already provides
    `Open/High/Low/Close/Volume` which we normalize first.
    """
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    close = df["close"]
    high = df["high"]
    low = df["low"]

    df["ema_200"] = close.ewm(span=200, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr_14"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    df["avg_volume_20"] = df["volume"].rolling(window=20).mean()
    return df


def _passes_setup_filter(row: pd.Series) -> bool:
    """Deterministic setup filter.

    A symbol qualifies when ALL of the following hold on the latest bar:
      1. Price > EMA_200            (long-term uptrend intact)
      2. RSI_14 < RSI_OVERSOLD_MAX  (short-term pullback / oversold)
      3. Volume > 20-day avg * 0.5  (still liquid, not a dead tape)

    Any NaN (insufficient history) fails the filter safely.
    """
    settings = get_settings()
    strategy = get_setup_strategy(settings.SETUP_STRATEGY)
    return strategy.qualifies(row, settings)


def get_symbol_snapshot(symbol: str) -> Optional[dict]:
    """Fetch the latest technical snapshot for a single symbol.

    Unlike `scan_nifty_universe`, this does NOT apply the setup filter — it
    returns the indicators even when the symbol does not qualify, so callers
    (e.g. the chat agent) can explain *why* a symbol did or did not pass.

    Returns a dict with `symbol`, `daily_close`, `rsi`, `ema_200`, `atr`,
    `volume`, `avg_volume_20`, `qualifies`, or `None` if no data is available.
    """
    settings = get_settings()
    nse_symbol = _to_nse_symbol(symbol)
    try:
        result = _load_history(nse_symbol, settings.HISTORY_PERIOD)
    except Exception as exc:  # noqa: BLE001 - network errors are expected
        logger.warning("Failed to download %s: %s", nse_symbol, exc)
        return None

    df = _compute_indicators(result.frame)
    latest = df.iloc[-1]
    return {
        "symbol": symbol.strip().upper(),
        "daily_close": float(latest["close"]),
        "rsi": float(latest["rsi_14"]),
        "ema_200": float(latest["ema_200"]),
        "atr": float(latest["atr_14"]),
        "volume": float(latest["volume"]),
        "avg_volume_20": float(latest["avg_volume_20"]),
        "qualifies": bool(_passes_setup_filter(latest)),
        "data_source": result.source,
        "data_fetched_at": result.fetched_at.isoformat(),
    }


def scan_nifty_universe(universe: Iterable[str]) -> list[dict]:
    """Screen the NIFTY 100 universe and return qualifying setups.

    Parameters
    ----------
    universe:
        Iterable of NSE symbols, with or without the `.NS` suffix
        (e.g. `["RELIANCE", "TCS.NS", ...]`).

    Returns
    -------
    list[dict]
        One dict per qualifying symbol with the latest technical snapshot:
        `symbol`, `daily_close`, `rsi`, `ema_200`, `atr`, `volume`,
        `avg_volume_20`. Symbols that fail the filter or have bad data are
        skipped (and logged) rather than raising, so one bad ticker never
        aborts the whole scan.

    Downloads run concurrently (I/O-bound yfinance calls) via a thread pool
    sized by `SCREENER_MAX_WORKERS`, so a full 100-symbol scan takes roughly
    1/N of the serial wall-clock time.
    """
    settings = get_settings()
    symbols = list(universe)
    results: list[dict] = []

    def _screen_one(raw_symbol: str) -> Optional[dict]:
        nse_symbol = _to_nse_symbol(raw_symbol)
        try:
            result = _load_history(nse_symbol, settings.HISTORY_PERIOD)
        except Exception as exc:  # noqa: BLE001 - network errors are expected
            logger.warning("Failed to download %s: %s", nse_symbol, exc)
            return None

        df = _compute_indicators(result.frame)
        latest = df.iloc[-1]

        if not _passes_setup_filter(latest):
            logger.debug("Symbol %s did not pass the setup filter.", raw_symbol)
            return None

        logger.info(
            "SETUP QUALIFIED: %s close=%.2f rsi=%.1f ema200=%.2f atr=%.2f",
            raw_symbol, latest["close"], latest["rsi_14"], latest["ema_200"], latest["atr_14"],
        )
        return {
            "symbol": raw_symbol.strip().upper(),
            "daily_close": float(latest["close"]),
            "rsi": float(latest["rsi_14"]),
            "ema_200": float(latest["ema_200"]),
            "atr": float(latest["atr_14"]),
            "volume": float(latest["volume"]),
            "avg_volume_20": float(latest["avg_volume_20"]),
            "data_source": result.source,
            "data_fetched_at": result.fetched_at.isoformat(),
        }

    with ThreadPoolExecutor(max_workers=settings.SCREENER_MAX_WORKERS) as pool:
        futures = {pool.submit(_screen_one, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            row = future.result()
            if row is not None:
                results.append(row)

    logger.info("Scan complete: %d of %d symbols qualified.", len(results), len(symbols))
    return results
