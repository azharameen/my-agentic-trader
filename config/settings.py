"""
Application settings loaded from environment variables via pydantic-settings.

This module is the single source of truth for all runtime configuration.
Every value can be overridden through a local `.env` file (see `.env.example`)
or through real environment variables in the Docker container.

Design notes
------------
* We deliberately keep *deterministic risk constants* (risk %, ATR multipliers,
  R:R floor) as explicit fields so they are visible, reviewable and unit-testable.
  The LLM never touches these numbers.
* `TRADING_MODE` is a hard gate: the executor refuses to route real orders
  unless the mode is explicitly `LIVE` AND a broker adapter is wired in.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application configuration.

    Field defaults mirror the mission's baseline assumptions. Anything that
    must come from the operator (API keys, chat id) has no safe default and is
    required at runtime.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # LLM (qualitative research filter only — never makes trade decisions)
    # ------------------------------------------------------------------ #
    # The analyst uses any OpenAI-compatible chat endpoint (OpenAI, Azure
    # OpenAI, Ollama, vLLM, LM Studio, corporate gateways, ...).
    OPENAI_API_KEY: str = Field(
        default="",
        description="API key for the OpenAI-compatible endpoint used by the analyst.",
    )
    OPENAI_BASE_URL: str = Field(
        default="",
        description="Optional custom base URL (e.g. https://api.openai.com/v1 or a gateway). Empty = default OpenAI.",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Chat model id served by the endpoint.",
    )

    # ------------------------------------------------------------------ #
    # Telegram (Human-in-the-Loop approval channel)
    # ------------------------------------------------------------------ #
    TELEGRAM_BOT_TOKEN: str = Field(
        default="",
        description="Bot token from @BotFather. Required for HITL approval.",
    )
    TELEGRAM_CHAT_ID: str = Field(
        default="",
        description="Chat/user id that receives trade proposal cards.",
    )

    # ------------------------------------------------------------------ #
    # Execution mode & capital
    # ------------------------------------------------------------------ #
    TRADING_MODE: Literal["PAPER_TRADING", "LIVE"] = Field(
        default="PAPER_TRADING",
        description="PAPER_TRADING simulates fills; LIVE is blocked until a broker adapter exists.",
    )
    PORTFOLIO_CAPITAL: float = Field(
        default=100_000.0,
        description="Total portfolio equity in INR (₹1,00,000 baseline).",
    )

    # ------------------------------------------------------------------ #
    # Deterministic risk invariants (hardcoded math — no LLM)
    # ------------------------------------------------------------------ #
    RISK_PER_TRADE_PCT: float = Field(
        default=0.01,
        description="Fraction of portfolio equity risked per trade (1.0%).",
    )
    ATR_SOFT_MULT: float = Field(
        default=1.5,
        description="ATR multiplier for the soft inspection stop.",
    )
    ATR_HARD_MULT: float = Field(
        default=2.5,
        description="ATR multiplier for the hard disaster stop.",
    )
    MIN_RISK_TO_REWARD: float = Field(
        default=2.0,
        description="Minimum acceptable R:R. Target >= Entry + 2*(Entry - HardStop).",
    )

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    DATABASE_PATH: str = Field(
        default="data/trading_audit.db",
        description="SQLite audit database path (relative to working dir).",
    )
    CHECKPOINT_DB_PATH: str = Field(
        default="data/checkpoints.db",
        description="SQLite path for LangGraph SqliteSaver checkpoints.",
    )

    # ------------------------------------------------------------------ #
    # Screener parameters
    # ------------------------------------------------------------------ #
    RSI_OVERSOLD_MAX: float = Field(
        default=42.0,
        description="RSI_14 must be below this for a pullback setup.",
    )
    VOLUME_RATIO_MIN: float = Field(
        default=0.5,
        description="Volume must exceed this fraction of the 20-day average volume.",
    )
    HISTORY_PERIOD: str = Field(
        default="1y",
        description="yfinance history window used for indicator computation.",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so repeated imports across the app share one validated object.
    Tests can call `get_settings.cache_clear()` to reload after mutating env.
    """
    return Settings()
