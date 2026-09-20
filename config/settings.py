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
    # The analyst uses one explicitly selected LangChain provider.
    LLM_PROVIDER: str = Field(
        default="openai_compatible",
        description="Active provider: openai_compatible, openai, gemini, anthropic, or groq.",
    )
    OPENAI_API_KEY: str = Field(
        default="",
        description="API key for OpenAI or an OpenAI-compatible gateway.",
    )
    OPENAI_BASE_URL: str = Field(
        default="",
        description="Optional custom base URL (e.g. https://api.openai.com/v1 or a gateway). Empty = default OpenAI.",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Chat model id served by the endpoint.",
    )
    GOOGLE_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash")
    ANTHROPIC_API_KEY: str = Field(default="")
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-haiku-latest")
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    LLM_TIMEOUT_SECONDS: int = Field(default=20)
    LLM_MAX_RETRIES: int = Field(default=1)
    RESEARCH_CACHE_ENABLED: bool = Field(default=True)
    TECHNICAL_CACHE_MINUTES: int = Field(default=360)
    NEWS_CACHE_MINUTES: int = Field(default=30)
    CATALYST_CACHE_MINUTES: int = Field(default=1440)
    EVIDENCE_CACHE_MINUTES: int = Field(default=1440)
    EVIDENCE_MAX_AGE_SECONDS: int = Field(
        default=0,
        description="Maximum evidence age for proposal validation; 0 disables the global default.",
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
    STORE_DB_PATH: str = Field(
        default="data/store.db",
        description="SQLite path for the LangGraph long-term memory store (operator profile, cross-thread notes).",
    )
    DATABASE_BACKUP_DIR: str = Field(
        default="data/backups",
        description="Directory for timestamped SQLite backups.",
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
    SCREENER_MAX_WORKERS: int = Field(
        default=8,
        description="Thread-pool size for concurrent yfinance downloads during a universe scan.",
    )
    SETUP_STRATEGY: str = Field(
        default="pullback_in_uptrend",
        description="Named deterministic setup strategy resolved by app.strategies.",
    )

    # ------------------------------------------------------------------ #
    # Observability
    # ------------------------------------------------------------------ #
    OTEL_ENABLED: bool = Field(
        default=False,
        description="Enable OpenTelemetry spans for pipeline and graph operations.",
    )
    OTEL_CONSOLE_EXPORTER: bool = Field(
        default=False,
        description="Export enabled OpenTelemetry spans to stdout for local debugging.",
    )
    LANGSMITH_TRACING_ENABLED: bool = Field(
        default=False,
        description="Opt-in LangSmith tracing for LangGraph/LangChain runs (ADR-021). "
        "Off by default; requires LANGSMITH_API_KEY to actually activate.",
    )
    LANGSMITH_API_KEY: str = Field(
        default="",
        description="LangSmith API key. Never logged; stays in .env/secret storage only.",
    )
    LANGSMITH_PROJECT: str = Field(
        default="traid-nifty100",
        description="LangSmith project name traces are grouped under.",
    )
    LANGSMITH_ENDPOINT: str = Field(
        default="",
        description="Optional custom LangSmith endpoint (self-hosted). Empty = default SaaS endpoint.",
    )

    # ------------------------------------------------------------------ #
    # Universe (NIFTY 100 constituents) — see app/universe.py
    # ------------------------------------------------------------------ #
    UNIVERSE_SEED_PATH: str = Field(
        default="config/universe/nifty100_seed.csv",
        description="Committed fallback snapshot of the NIFTY 100 constituent list.",
    )
    UNIVERSE_CACHE_PATH: str = Field(
        default="data/universe/nifty100.csv",
        description="Auto-refreshed runtime cache of the NIFTY 100 constituent list.",
    )
    UNIVERSE_SOURCE_URL: str = Field(
        default="https://www.niftyindices.com/IndexConstituent/ind_nifty100list.csv",
        description="Official NSE Indices CSV endpoint for the live NIFTY 100 constituent list.",
    )
    UNIVERSE_REFRESH_DAYS: int = Field(
        default=30,
        description="Runtime cache is considered stale after this many days and is re-fetched live.",
    )

    # ------------------------------------------------------------------ #
    # Human approval / scheduling
    # ------------------------------------------------------------------ #
    STALE_PROPOSAL_MINUTES: int = Field(
        default=240,
        description="A paused proposal older than this is rejected as stale on resume rather than executed at outdated levels.",
    )
    STALE_PROPOSAL_PRICE_MOVE_PCT: float = Field(
        default=0.02,
        description="Price must have moved less than this fraction from the proposed entry for a stale-but-recent approval to still execute.",
    )
    CORPORATE_EVENT_BLACKOUT_DAYS: int = Field(
        default=10,
        description="Projected holding window used for earnings and board-event vetoes.",
    )
    CORPORATE_EVENTS_ENABLED: bool = Field(
        default=False,
        description="Enable configured corporate-event source collection.",
    )
    CORPORATE_EVENTS_SOURCE_URL: str = Field(
        default="",
        description="Configured corporate-event JSON/CSV source URL; empty disables collection.",
    )
    CORPORATE_EVENTS_CACHE_PATH: str = Field(
        default="data/corporate_events.json",
        description="Local cache for normalized corporate events.",
    )
    SCAN_CRON_HOUR: int = Field(
        default=15,
        description="Hour (24h) of the daily automatic universe scan.",
    )
    SCAN_CRON_MINUTE: int = Field(
        default=45,
        description="Minute of the daily automatic universe scan (post NSE close).",
    )
    SCAN_CRON_DAYS: str = Field(
        default="mon-fri",
        description="APScheduler cron day-of-week expression for the daily scan (e.g. 'mon-fri').",
    )
    SCHEDULER_TIMEZONE: str = Field(
        default="Asia/Kolkata",
        description="Timezone used for all APScheduler cron jobs.",
    )
    UNIVERSE_REFRESH_DAY_OF_MONTH: int = Field(
        default=1,
        description="Day of month for the monthly universe refresh.",
    )
    UNIVERSE_REFRESH_HOUR: int = Field(
        default=6,
        description="Hour (24h) of the monthly universe refresh.",
    )
    UNIVERSE_REFRESH_MINUTE: int = Field(
        default=0,
        description="Minute of the monthly universe refresh.",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so repeated imports across the app share one validated object.
    Tests can call `get_settings.cache_clear()` to reload after mutating env.
    """
    return Settings()
