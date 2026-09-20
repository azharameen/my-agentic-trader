"""Bear Risk Critic agent (ADR-022).

Specialized adversarial research persona tasked with detecting corporate
governance irregularities, promoter pledge spikes, litigation, accounting flags,
debt burdens, and overhead chart resistance.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.models import BearAssessment
from app.llm import build_chat_model, is_configured

logger = logging.getLogger(__name__)

_BEAR_SYSTEM_PROMPT = """\
You are an adversarial Bear Risk Critic for a NIFTY 100 equity trading desk.
Your ONLY mission is to stress-test candidates and uncover hidden risks.

You are given a stock symbol and recent news headlines / corporate disclosures.

Investigate:
1. Corporate governance flags, auditor resignations, SEBI/regulatory scrutiny.
2. Promoter pledging, insider selling, management turmoil.
3. Accounting irregularities, sudden write-downs, or forensic concerns.
4. Structural business threats or unmanageable debt load.

Rules:
- Be aggressively skeptical.
- If you find material structural, legal, or governance red flags, set `is_structural_damage=True`.
- Assign a `governance_score` from 0.0 (severe issues) to 1.0 (clean governance).
- Provide an honest `confidence` (0.0 to 1.0) in your bear thesis.
- Do NOT output prices, stop loss levels, or position sizes.
"""

_FALLBACK_BEAR = BearAssessment(
    red_flags=["Analyst model unavailable; failing closed."],
    structural_risks=["LLM unavailable"],
    governance_score=0.0,
    is_structural_damage=True,
    confidence=0.0,
    bear_rationale="Bear Critic unavailable; failing closed with conservative risk assessment.",
)


def analyze_bear_risks(symbol: str, headlines: list[str]) -> BearAssessment:
    """Run adversarial risk analysis on a symbol.

    Fails closed if the LLM provider is not configured or encounters an error.
    """
    if not is_configured():
        logger.warning("LLM not configured; BearCritic returning fallback for %s.", symbol)
        return _FALLBACK_BEAR

    headlines_text = "\n".join(f"- {h}" for h in headlines) if headlines else "(no headlines available)"
    user_prompt = (
        f"Symbol: {symbol}\n\n"
        f"Recent disclosures / news:\n{headlines_text}\n\n"
        "Identify all adversarial bear risks and structural threats."
    )

    try:
        llm: Any = build_chat_model()
        structured = llm.with_structured_output(BearAssessment)
        assessment: BearAssessment = structured.invoke(
            [
                {"role": "system", "content": _BEAR_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        logger.info(
            "BEAR_CRITIC %s: structural=%s gov=%.2f conf=%.2f",
            symbol, assessment.is_structural_damage,
            assessment.governance_score, assessment.confidence,
        )
        return assessment
    except Exception as exc:  # noqa: BLE001 - fail-closed on any LLM or schema error
        logger.warning("BearCritic error on %s: %s; failing closed.", symbol, exc)
        return _FALLBACK_BEAR
