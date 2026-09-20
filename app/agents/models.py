"""Structured output models for the multi-agent research debate (ADR-022).

Defines strongly-typed Pydantic schemas for:
  - BearAssessment: Adversarial risk critic findings
  - BullAssessment: Constructive momentum and catalyst findings
  - ResearchVerdict: Synthesis arbiter decision with composite confidence and citations
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class BearAssessment(BaseModel):
    """Adversarial risk analysis emitted by BearRiskCritic."""

    red_flags: list[str] = Field(
        default_factory=list,
        description="Identified governance, promoter pledging, legal, or accounting concerns.",
    )
    structural_risks: list[str] = Field(
        default_factory=list,
        description="Fundamental business threats or overhead resistance levels.",
    )
    governance_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Governance health score (1.0 = clean, 0.0 = severe irregularities).",
    )
    is_structural_damage: bool = Field(
        default=False,
        description="True if drop is caused by structural damage rather than routine pullback.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Critic confidence in the risk assessment (0.0 - 1.0).",
    )
    bear_rationale: str = Field(
        description="Concise adversarial argument citing specific risk factors or headlines.",
    )


class BullAssessment(BaseModel):
    """Constructive momentum and fundamental analysis emitted by BullMomentumAnalyst."""

    momentum_thesis: str = Field(
        description="Key growth or momentum narrative supporting the setup.",
    )
    volume_quality: str = Field(
        description="Assessment of institutional accumulation or volume expansion.",
    )
    sector_tailwinds: list[str] = Field(
        default_factory=list,
        description="Industry or macro catalysts supporting continued upside.",
    )
    catalyst_drivers: list[str] = Field(
        default_factory=list,
        description="Upcoming product, quarterly, or earnings drivers.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Analyst confidence in the bullish thesis (0.0 - 1.0).",
    )
    bull_rationale: str = Field(
        description="Concise bullish thesis synthesizing momentum and catalyst quality.",
    )


class ResearchVerdict(BaseModel):
    """Final synthesized qualitative research verdict from SynthesisArbiter."""

    composite_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Balanced composite confidence score (0.0 - 1.0). Requires >= 0.60 to proceed.",
    )
    verdict: Literal["BUY", "PASS", "WAIT"] = Field(
        description="BUY = proceed to risk math; PASS = reject setup; WAIT = monitor setup.",
    )
    catalyst_type: Literal[
        "EARNINGS_NOISE",
        "SECTOR_CONTAGION",
        "STRUCTURAL_DAMAGE",
        "GENERAL_MARKET",
    ] = Field(
        default="GENERAL_MARKET",
        description="Underlying nature of the setup or price move.",
    )
    thesis_summary: str = Field(
        description="Final synthesized qualitative thesis (used in proposal card).",
    )
    invalidation_criteria: list[str] = Field(
        default_factory=list,
        description="Concrete conditions that invalidate the thesis.",
    )
    citations: list[str] = Field(
        default_factory=list,
        description="Referenced headlines or sources backing the verdict.",
    )
    bear_assessment: Optional[BearAssessment] = Field(
        default=None,
        description="Underlying Bear Critic assessment if executed.",
    )
    bull_assessment: Optional[BullAssessment] = Field(
        default=None,
        description="Underlying Bull Analyst assessment if executed.",
    )
    early_vetoed: bool = Field(
        default=False,
        description="True if early exit was triggered by Bear Critic without invoking Bull/Synthesizer.",
    )
