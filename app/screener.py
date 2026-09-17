"""
Quantitative screening engine.

Downloads daily OHLCV for the NIFTY 100 universe via `yfinance`, computes the
technical indicators (EMA_200, RSI_14, ATR_14) with `pandas_ta`, and applies a
deterministic *pullback-in-an-uptrend* setup filter.

This module is pure math + data fetching. It contains no LLM calls and no
order logic — it only decides which symbols *qualify* for further analysis.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

import pandas as pd
import pandas_ta as ta
import yfinance as yf

from config.settings import get_settings

logger = logging.getLogger(__name__)


def _to_nse_symbol(symbol: str) -> str:
    """Append the NSE exchange suffix if it is not already present.

    yfinance requires the `.NS` suffix for NSE-listed equities.
    """
    symbol = symbol.strip().upper()
    return symbol if symbol.endswith(".NS") else f"{symbol}.NS"


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Attach EMA_200, RSI_14 and ATR_14 columns to an OHLCV frame.

    `pandas_ta` expects lowercase column names; yfinance already provides
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
    df["ema_200"] = ta.ema(df["close"], length=200)
    df["rsi_14"] = ta.rsi(df["close"], length=14)
    df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
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
    try:
        price = row["close"]
        ema_200 = row["ema_200"]
        rsi = row["rsi_14"]
        volume = row["volume"]
        avg_volume = row["avg_volume_20"]
    except (KeyError, TypeError):
        return False

    # Guard against NaN / None from insufficient history.
    for value in (price, ema_200, rsi, volume, avg_volume):
        if pd.isna(value):
            return False

    return (
        price > ema_200
        and rsi < settings.RSI_OVERSOLD_MAX
        and volume > avg_volume * settings.VOLUME_RATIO_MIN
    )


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
        df = yf.download(
            nse_symbol,
            period=settings.HISTORY_PERIOD,
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:  # noqa: BLE001 - network errors are expected
        logger.warning("Failed to download %s: %s", nse_symbol, exc)
        return None

    if df is None or df.empty:
        logger.warning("No data returned for %s.", nse_symbol)
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = _compute_indicators(df)
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
    """
    settings = get_settings()
    results: list[dict] = []

    for raw_symbol in universe:
        nse_symbol = _to_nse_symbol(raw_symbol)
        try:
            df = yf.download(
                nse_symbol,
                period=settings.HISTORY_PERIOD,
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
        except Exception as exc:  # noqa: BLE001 - network errors are expected
            logger.warning("Failed to download %s: %s", nse_symbol, exc)
            continue

        if df is None or df.empty:
            logger.warning("No data returned for %s; skipping.", nse_symbol)
            continue

        # yfinance may return a MultiIndex column frame for single tickers.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = _compute_indicators(df)
        latest = df.iloc[-1]

        if _passes_setup_filter(latest):
            results.append(
                {
                    "symbol": raw_symbol.strip().upper(),
                    "daily_close": float(latest["close"]),
                    "rsi": float(latest["rsi_14"]),
                    "ema_200": float(latest["ema_200"]),
                    "atr": float(latest["atr_14"]),
                    "volume": float(latest["volume"]),
                    "avg_volume_20": float(latest["avg_volume_20"]),
                }
            )
            logger.info(
                "SETUP QUALIFIED: %s close=%.2f rsi=%.1f ema200=%.2f atr=%.2f",
                raw_symbol,
                latest["close"],
                latest["rsi_14"],
                latest["ema_200"],
                latest["atr_14"],
            )
        else:
            logger.debug("Symbol %s did not pass the setup filter.", raw_symbol)

    logger.info("Scan complete: %d of %d symbols qualified.", len(results), len(list(universe)))
    return results
