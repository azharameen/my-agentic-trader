"""Bull Momentum Analyst agent (ADR-022).

Specialized constructive research persona evaluating breakout strength,
institutional accumulation, sector rotation tailwinds, and earnings catalysts.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.models import BullAssessment
from app.llm import build_chat_model, is_configured

logger = logging.getLogger(__name__)

_BULL_SYSTEM_PROMPT = """\
You are a constructive Bull Momentum Analyst for a NIFTY 100 equity trading desk.
Your mission is to identify high-probability momentum catalysts and sector tailwinds.

You are given a stock symbol and recent news headlines / corporate disclosures.

Evaluate:
1. Technical and fundamental momentum drivers (earnings beats, order inflows, capacity expansion).
2. Sector tailwinds, macro policy support, or peer group strength.
3. Institutional interest, volume quality, and product market demand.

Rules:
- Express realistic confidence (0.0 to 1.0) based on tangible evidence.
- Identify specific catalyst drivers and sector tailwinds.
- Do NOT output prices, stop loss levels, or position sizes.
"""

_FALLBACK_BULL = BullAssessment(
    momentum_thesis="Bull Analyst unavailable; failing closed.",
    volume_quality="Unknown",
    sector_tailwinds=[],
    catalyst_drivers=[],
    confidence=0.0,
    bull_rationale="Bull Analyst unavailable; default fallback.",
)


def analyze_bull_momentum(symbol: str, headlines: list[str]) -> BullAssessment:
    """Run bullish momentum and catalyst analysis on a symbol."""
    if not is_configured():
        logger.warning("LLM not configured; BullAnalyst returning fallback for %s.", symbol)
        return _FALLBACK_BULL

    headlines_text = "\n".join(f"- {h}" for h in headlines) if headlines else "(no headlines available)"
    user_prompt = (
        f"Symbol: {symbol}\n\n"
        f"Recent disclosures / news:\n{headlines_text}\n\n"
        "Evaluate the bullish momentum drivers, accumulation quality, and catalysts."
    )

    try:
        llm: Any = build_chat_model()
        structured = llm.with_structured_output(BullAssessment)
        assessment: BullAssessment = structured.invoke(
            [
                {"role": "system", "content": _BULL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        logger.info(
            "BULL_ANALYST %s: conf=%.2f drivers=%d",
            symbol, assessment.confidence, len(assessment.catalyst_drivers),
        )
        return assessment
    except Exception as exc:  # noqa: BLE001 - fail-closed on any LLM or schema error
        logger.warning("BullAnalyst error on %s: %s; failing closed.", symbol, exc)
        return _FALLBACK_BULL
