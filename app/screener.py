"""Quantitative multi-strategy screening engine (ADR-024).

Downloads daily OHLCV for the NIFTY 100 universe via `yfinance`, computes
technical indicators (EMA 200, EMA 50, RSI 14, ATR 14, 20-day High, Bollinger Bands),
and evaluates universe candidates against all active setup strategies simultaneously
with deterministic priority resolution:

  BREAKOUT_MOMENTUM > PULLBACK_IN_UPTREND > BOLLINGER_MEAN_REVERSION
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, Optional

import pandas as pd

from app import cache, market_data
from app.evidence import content_hash
from app.models import TechnicalSnapshot
from app.strategies import evaluate_all_strategies
from config.settings import get_settings

logger = logging.getLogger(__name__)


def _load_history(nse_symbol: str, period: str) -> market_data.MarketDataResult:
    return market_data.load_history(nse_symbol, period)


def _to_nse_symbol(symbol: str) -> str:
    """Append the NSE exchange suffix if it is not already present."""
    symbol = symbol.strip().upper()
    if symbol.endswith(".NSE"):
        symbol = symbol[:-4]
    return symbol if symbol.endswith(".NS") else f"{symbol}.NS"


def canonical_symbol(symbol: str) -> str:
    """Return the application symbol without an exchange suffix."""
    value = symbol.strip().upper()
    for suffix in (".NSE", ".NS"):
        if value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Attach technical indicator columns to an OHLCV frame.

    Computed indicators:
      - `ema_200`, `ema_50`
      - `rsi_14`, `atr_14`
      - `avg_volume_20`, `high_20` (shifted by 1 day)
      - `bb_middle_20`, `bb_lower_20`, `bb_upper_20`
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
    volume = df["volume"]

    # Moving averages
    df["ema_200"] = close.ewm(span=200, adjust=False).mean()
    df["ema_50"] = close.ewm(span=50, adjust=False).mean()

    # RSI 14
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # ATR 14
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

    # Volume and Channels
    df["avg_volume_20"] = volume.rolling(window=20).mean()
    df["high_20"] = high.shift(1).rolling(window=20).max()

    # Bollinger Bands (20, 2.0)
    bb_middle = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    df["bb_middle_20"] = bb_middle
    df["bb_lower_20"] = bb_middle - 2.0 * bb_std
    df["bb_upper_20"] = bb_middle + 2.0 * bb_std

    return df


def _passes_setup_filter(row: pd.Series) -> bool:
    """Return whether the row qualifies under any active setup strategy."""
    primary, _ = evaluate_all_strategies(row)
    return primary is not None


def get_symbol_snapshot(symbol: str) -> Optional[TechnicalSnapshot]:
    """Fetch the latest technical snapshot for a single symbol with multi-strategy evaluation.

    Evaluates all active setup strategies simultaneously and resolves the primary
    qualifying strategy and secondary supporting tags.
    """
    settings = get_settings()
    cache_key = content_hash({
        "symbol": canonical_symbol(symbol),
        "history_period": settings.HISTORY_PERIOD,
        "rsi_max": settings.RSI_OVERSOLD_MAX,
        "volume_ratio_min": settings.VOLUME_RATIO_MIN,
    })
    cached, cache_hit = cache.get_value_with_status("technical", cache_key)
    if cached is not None:
        if isinstance(cached, dict):
            return TechnicalSnapshot(**{**cached, "cache_hit": cache_hit})
        return cached

    nse_symbol = _to_nse_symbol(symbol)
    try:
        result = _load_history(nse_symbol, settings.HISTORY_PERIOD)
    except Exception as exc:  # noqa: BLE001 - network errors are expected
        logger.warning("Failed to download %s: %s", nse_symbol, exc)
        return None

    df = _compute_indicators(result.frame)
    latest = df.iloc[-1]
    primary_strategy, secondary_strategies = evaluate_all_strategies(latest, settings)
    passes_override = _passes_setup_filter(latest)
    qualifies = bool(primary_strategy is not None or passes_override)
    strategy_name = primary_strategy.name if primary_strategy else (settings.SETUP_STRATEGY if qualifies else None)

    def _safe_float(val: object) -> Optional[float]:
        return float(val) if val is not None and not pd.isna(val) else None

    snapshot = TechnicalSnapshot(
        symbol=canonical_symbol(symbol),
        daily_close=float(latest["close"]),
        rsi=float(latest["rsi_14"]),
        ema_200=float(latest["ema_200"]),
        atr=float(latest["atr_14"]),
        volume=float(latest["volume"]),
        avg_volume_20=float(latest["avg_volume_20"]),
        ema_50=_safe_float(latest.get("ema_50")),
        high_20=_safe_float(latest.get("high_20")),
        bb_lower=_safe_float(latest.get("bb_lower_20")),
        bb_middle=_safe_float(latest.get("bb_middle_20")),
        bb_upper=_safe_float(latest.get("bb_upper_20")),
        qualifies=qualifies,
        strategy_name=strategy_name,
        secondary_strategies=secondary_strategies,
        data_source=result.source,
        data_fetched_at=result.fetched_at.isoformat(),
        cache_hit=False,
    )
    cache.set_value("technical", cache_key, snapshot.model_dump(), settings.TECHNICAL_CACHE_MINUTES)
    return snapshot


def scan_nifty_universe(universe: Iterable[str]) -> list[TechnicalSnapshot]:
    """Screen the NIFTY 100 universe and return all qualifying multi-strategy setups.

    Parameters
    ----------
    universe:
        Iterable of NSE symbols, with or without `.NS` suffix.

    Returns
    -------
    list[TechnicalSnapshot]
        One TechnicalSnapshot per qualifying symbol.
    """
    settings = get_settings()
    symbols = list(universe)
    results: list[TechnicalSnapshot] = []

    def _screen_one(raw_symbol: str) -> Optional[TechnicalSnapshot]:
        snapshot = get_symbol_snapshot(raw_symbol)
        if snapshot is None or not snapshot.qualifies:
            logger.debug("Symbol %s did not qualify for any setup.", raw_symbol)
            return None

        logger.info(
            "SETUP QUALIFIED: %s [%s] close=%.2f rsi=%.1f atr=%.2f secondary=%s",
            raw_symbol, snapshot.strategy_name, snapshot.daily_close,
            snapshot.rsi, snapshot.atr, snapshot.secondary_strategies,
        )
        return snapshot

    with ThreadPoolExecutor(max_workers=settings.SCREENER_MAX_WORKERS) as pool:
        futures = {pool.submit(_screen_one, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            row = future.result()
            if row is not None:
                results.append(row)

    logger.info("Scan complete: %d of %d symbols qualified across active strategies.", len(results), len(symbols))
    return results
