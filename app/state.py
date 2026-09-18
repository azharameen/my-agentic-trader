"""
Typed state contracts for the trading graph.

This module defines the *data contracts* that flow between LangGraph nodes:

* Pydantic models — validated, serializable payloads produced by individual
  nodes (catalyst assessment, trade proposal).
* `TradingState` — the `TypedDict` that LangGraph uses as the shared,
  checkpointed state across the whole graph.

Keeping the contracts here (rather than inside each node) means every node
agrees on field names and types, and the state is trivially serializable to
SQLite checkpoints.
"""

from __future__ import annotations

import operator
from datetime import datetime
from typing import Annotated, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Pydantic payload models
# --------------------------------------------------------------------------- #
class CatalystAssessment(BaseModel):
    """Structured output of the LLM catalyst analyst.

    The LLM is constrained to this schema via `.with_structured_output(...)`.
    It may only *classify* the nature of a price drop and express confidence —
    it never emits prices, quantities or order instructions.
    """

    is_temporary_pullback: bool = Field(
        description="True if the drop looks like a temporary, non-structural pullback.",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Analyst confidence in the classification (0.0 - 1.0).",
    )
    thesis_rationale: str = Field(
        description="Concise natural-language rationale for the classification.",
    )
    catalyst_type: Literal[
        "EARNINGS_NOISE",
        "SECTOR_CONTAGION",
        "STRUCTURAL_DAMAGE",
        "GENERAL_MARKET",
    ] = Field(
        description=(
            "EARNINGS_NOISE: routine earnings/quarterly noise. "
            "SECTOR_CONTAGION: peer/sector-wide de-rating. "
            "STRUCTURAL_DAMAGE: governance, fraud, pledge or fundamental loss. "
            "GENERAL_MARKET: broad index-level move."
        ),
    )


class TradeProposal(BaseModel):
    """Deterministic trade proposal produced by the risk engine.

    Every numeric field here is computed by pure Python math in `risk.py`.
    The LLM has no influence on any of these values.
    """

    symbol: str = Field(description="NSE symbol (without the .NS suffix).")
    entry_price: float = Field(description="Proposed entry price (last close).")
    soft_stop: float = Field(description="Soft inspection stop: Entry - 1.5*ATR.")
    hard_stop: float = Field(description="Hard disaster stop: Entry - 2.5*ATR.")
    target_price: float = Field(description="Target: Entry + 2*(Entry - HardStop).")
    quantity: int = Field(description="Position size from the 1% risk rule.")
    risk_amount: float = Field(description="Absolute INR risked (capital * 1%).")
    risk_to_reward: float = Field(description="Computed R:R ratio (must be >= 2.0).")


class ProposalCard(TradeProposal):
    """Validated payload shared by the graph pause and Telegram renderers."""

    thesis: str
    catalyst_type: str
    proposed_at: datetime

    def __getitem__(self, key: str):
        return getattr(self, key)

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


# --------------------------------------------------------------------------- #
# LangGraph shared state
# --------------------------------------------------------------------------- #
class TradingState(TypedDict, total=False):
    """Shared, checkpointed state for the trading StateGraph.

    `total=False` means every key is optional; nodes read/write only the keys
    they own. LangGraph merges node outputs into this dict and persists the
    whole thing to the SqliteSaver checkpoint after each super-step.

    Lifecycle of keys:
      * `symbol`            — set by the entry (screener) node.
      * `daily_close`       — last close, set by screener.
      * `rsi`, `ema_200`, `atr` — technical snapshot, set by screener.
      * `news_headlines`    — raw headlines gathered for the analyst.
      * `catalyst_assessment` — dict form of CatalystAssessment.
      * `order_proposal`    — dict form of TradeProposal.
      * `proposal_card`     — the interrupt payload shown to the human (incl. `proposed_at`), used to detect stale approvals.
      * `human_decision`    — "APPROVED" | "REJECTED" | "KILLED" (from interrupt).
      * `execution_details` — fill info written by the executor node.
    """

    symbol: str
    daily_close: float
    rsi: float
    ema_200: float
    atr: float
    news_headlines: list[str]
    catalyst_assessment: Optional[CatalystAssessment]
    order_proposal: Optional[TradeProposal]
    proposal_card: Optional[ProposalCard]
    human_decision: Optional[str]
    execution_details: Optional[dict]
    evidence_snapshot_id: Optional[str]
    source_set: list[str]
    strategy_name: Optional[str]
    market_regime: Optional[str]
    corporate_events: list[dict]
    analyst_verdicts: Annotated[list[dict], operator.add]
    approved_orders: Annotated[list[dict], operator.add]
