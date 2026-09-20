"""Typed domain transfer models across screener, pipeline, and execution (ADR-003).

Provides validated Pydantic models for technical snapshots, execution receipts,
audit records, and whole-universe scan results. All transfer models implement
dict-like accessors (`__getitem__`, `get`, `__contains__`) to maintain seamless
backward compatibility with existing dictionary consumption in LangGraph state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class DictCompatibleModel(BaseModel):
    """Base model with dictionary-like subscripting for backward compatibility."""

    model_config = ConfigDict(extra="ignore")

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError as err:
            raise KeyError(key) from err

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


class TechnicalSnapshot(DictCompatibleModel):
    """Normalized technical snapshot for a single asset from the screener."""

    symbol: str = Field(description="NSE symbol without exchange suffix.")
    daily_close: float = Field(description="Last close price in INR.")
    rsi: float = Field(description="14-period Relative Strength Index.")
    ema_200: float = Field(description="200-period Exponential Moving Average.")
    atr: float = Field(description="14-period Average True Range.")
    volume: float = Field(description="Latest session volume.")
    avg_volume_20: float = Field(description="20-session rolling average volume.")
    ema_50: Optional[float] = Field(default=None, description="50-period Exponential Moving Average.")
    high_20: Optional[float] = Field(default=None, description="20-period highest high.")
    bb_lower: Optional[float] = Field(default=None, description="Bollinger lower band (20, 2.0).")
    bb_middle: Optional[float] = Field(default=None, description="Bollinger middle band (20-SMA).")
    bb_upper: Optional[float] = Field(default=None, description="Bollinger upper band (20, 2.0).")
    qualifies: bool = Field(default=False, description="Whether setup criteria passed.")
    strategy_name: Optional[str] = Field(default=None, description="Primary resolved strategy.")
    secondary_strategies: list[str] = Field(
        default_factory=list,
        description="Secondary qualifying strategy names.",
    )
    data_source: str = Field(default="yfinance", description="Origin data provider.")
    data_fetched_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp of data retrieval.",
    )
    cache_hit: bool = Field(default=False, description="Whether resolved from cache.")


class ExecutionResult(DictCompatibleModel):
    """Simulated or live trade execution receipt."""

    trade_id: str = Field(description="Unique trade UUID string.")
    symbol: str = Field(description="NSE symbol.")
    fill_price: float = Field(description="Simulated fill price including slippage.")
    quantity: int = Field(description="Executed position quantity.")
    status: Literal["OPEN_PAPER", "FILLED", "REJECTED", "CLOSED"] = Field(
        default="OPEN_PAPER",
        description="Execution status.",
    )
    slippage_pct: float = Field(
        default=0.05,
        description="Applied slippage percentage (e.g. 0.05%).",
    )
    filled_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the execution fill.",
    )


class TradeRecord(DictCompatibleModel):
    """Complete typed audit log entry representation from trade_audit_log."""

    trade_id: str
    timestamp: str | datetime
    symbol: str
    entry_price: float
    soft_stop: float
    hard_stop: float
    target_price: float
    quantity: int
    rsi: Optional[float] = None
    ema_200: Optional[float] = None
    atr: Optional[float] = None
    thesis: Optional[str] = None
    headlines_used: Optional[str] = None
    human_decision: Optional[str] = None
    fill_price: Optional[float] = None
    exit_price: Optional[float] = None
    realized_pnl: Optional[float] = None
    gross_pnl: Optional[float] = None
    transaction_costs: Optional[dict[str, Any] | str] = None
    mistake_category: Optional[str] = None
    status: str
    evidence_snapshot_id: Optional[str] = None
    strategy_name: Optional[str] = None
    market_regime: Optional[str] = None
    catalyst_type: Optional[str] = None
    source_set: Optional[str | list[str]] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    cache_hits: Optional[str | list[str]] = None


class ScanResult(DictCompatibleModel):
    """Aggregated universe scan result."""

    scanned_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of scan execution.",
    )
    total_symbols: int = Field(description="Total universe symbols screened.")
    qualified_symbols: list[str] = Field(
        default_factory=list,
        description="Symbols meeting technical setup criteria.",
    )
    proposals_generated: int = Field(
        default=0,
        description="Number of trade proposals created and forwarded to Telegram.",
    )
    vetoed_by_regime: bool = Field(
        default=False,
        description="Whether scan execution was halted by macro regime gate.",
    )
    regime_rationale: Optional[str] = Field(
        default=None,
        description="Macro regime reason if scan was vetoed.",
    )
