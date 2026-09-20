"""LLM qualitative research analyst integration (ADR-022).

Coordinates qualitative catalyst classification by delegating to the sequential
multi-agent research subgraph (BearRiskCritic -> BullMomentumAnalyst -> SynthesisArbiter).
"""

from __future__ import annotations

import logging

from app.agents import ResearchVerdict, run_qualitative_research
from app.state import CatalystAssessment

logger = logging.getLogger(__name__)

# Conservative default used when the LLM is unavailable or returns garbage.
_FALLBACK_ASSESSMENT = CatalystAssessment(
    is_temporary_pullback=False,
    confidence_score=0.0,
    thesis_rationale="Analyst unavailable; failing closed (no clean-pullback signal).",
    catalyst_type="GENERAL_MARKET",
)


def analyze_catalyst(symbol: str, news_headlines: list[str]) -> CatalystAssessment:
    """Run sequential qualitative research for a symbol.

    Delegates to `run_qualitative_research` (Bear Critic -> Early Exit -> Bull -> Synthesizer)
    and maps the structured `ResearchVerdict` into `CatalystAssessment` for graph consumption.
    """
    verdict: ResearchVerdict = run_qualitative_research(symbol, news_headlines)
    is_pullback = bool(verdict.verdict == "BUY" and verdict.composite_confidence >= 0.60)
    return CatalystAssessment(
        is_temporary_pullback=is_pullback,
        confidence_score=round(verdict.composite_confidence, 2),
        thesis_rationale=verdict.thesis_summary,
        catalyst_type=verdict.catalyst_type,
    )
