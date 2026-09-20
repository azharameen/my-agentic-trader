"""Synthesis Arbiter agent (ADR-022).

Independent research arbiter that balances adversarial Bear Critic risks against
Bull Analyst momentum drivers, establishes concrete thesis invalidation criteria,
and assigns a composite confidence score (0.0 to 1.0).
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.models import BearAssessment, BullAssessment, ResearchVerdict
from app.llm import build_chat_model, is_configured

logger = logging.getLogger(__name__)

_SYNTHESIZER_SYSTEM_PROMPT = """\
You are the Synthesis Arbiter for a NIFTY 100 quantitative trading desk.
You receive adversarial Bear Critic risks and constructive Bull Analyst drivers.

Your mission:
1. Objectively weigh Bear risks against Bull momentum drivers.
2. Establish 2-4 concrete `invalidation_criteria` (conditions that prove the setup wrong).
3. Assign a `composite_confidence` (0.0 to 1.0).
4. Set the final `verdict`:
   - "BUY": Only if composite_confidence >= 0.60 AND Bear governance/fraud risks are low.
   - "PASS": If structural risks outweigh momentum or composite_confidence < 0.60.
   - "WAIT": If the setup is developing but requires further confirmation.
5. Classify the `catalyst_type` into: EARNINGS_NOISE, SECTOR_CONTAGION, STRUCTURAL_DAMAGE, or GENERAL_MARKET.
6. Provide a 2-4 sentence `thesis_summary` citing specific headlines or arguments.

Rules:
- Be disciplined and conservative.
- Never output prices, stop loss levels, or position sizes.
"""

_FALLBACK_VERDICT = ResearchVerdict(
    composite_confidence=0.0,
    verdict="PASS",
    catalyst_type="GENERAL_MARKET",
    thesis_summary="Synthesis Arbiter unavailable; failing closed with PASS verdict.",
    invalidation_criteria=["LLM unavailable"],
    citations=[],
    early_vetoed=False,
)


def synthesize_research(
    symbol: str,
    bear: BearAssessment,
    bull: BullAssessment,
    headlines: list[str],
) -> ResearchVerdict:
    """Synthesize the multi-agent debate into a unified ResearchVerdict."""
    if not is_configured():
        logger.warning("LLM not configured; SynthesisArbiter returning fallback for %s.", symbol)
        return _FALLBACK_VERDICT

    headlines_text = "\n".join(f"- {h}" for h in headlines) if headlines else "(no headlines available)"
    user_prompt = f"""\
Symbol: {symbol}

=== BEAR CRITIC ASSESSMENT ===
Structural Damage: {bear.is_structural_damage}
Governance Score: {bear.governance_score:.2f}
Bear Confidence: {bear.confidence:.2f}
Red Flags: {", ".join(bear.red_flags) if bear.red_flags else "None"}
Structural Risks: {", ".join(bear.structural_risks) if bear.structural_risks else "None"}
Bear Rationale: {bear.bear_rationale}

=== BULL ANALYST ASSESSMENT ===
Bull Confidence: {bull.confidence:.2f}
Momentum Thesis: {bull.momentum_thesis}
Volume Quality: {bull.volume_quality}
Sector Tailwinds: {", ".join(bull.sector_tailwinds) if bull.sector_tailwinds else "None"}
Catalyst Drivers: {", ".join(bull.catalyst_drivers) if bull.catalyst_drivers else "None"}
Bull Rationale: {bull.bull_rationale}

=== RECENT NEWS HEADLINES ===
{headlines_text}

Deliver your synthesized ResearchVerdict.
"""

    try:
        llm: Any = build_chat_model()
        structured = llm.with_structured_output(ResearchVerdict)
        verdict: ResearchVerdict = structured.invoke(
            [
                {"role": "system", "content": _SYNTHESIZER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        verdict.bear_assessment = bear
        verdict.bull_assessment = bull
        logger.info(
            "SYNTHESIZER %s: verdict=%s conf=%.2f type=%s",
            symbol, verdict.verdict, verdict.composite_confidence, verdict.catalyst_type,
        )
        return verdict
    except Exception as exc:  # noqa: BLE001 - fail-closed on any LLM or schema error
        logger.warning("Synthesizer error on %s: %s; failing closed.", symbol, exc)
        return _FALLBACK_VERDICT
