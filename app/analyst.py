"""
LLM catalyst analyst node.

Connects to an OpenAI-compatible chat endpoint (OpenAI, Azure OpenAI, Ollama,
vLLM, LM Studio, corporate gateways, ...) via `langchain-openai` and classifies
the *qualitative* nature of a price drop using structured output. The LLM is a
research filter only: it decides whether a pullback looks temporary or whether
it signals structural damage (governance red flags, accounting fraud, promoter
pledge spikes, material loss). It never emits prices, sizes or orders.

The prompt explicitly instructs the model to be conservative: when in doubt it
should classify as `STRUCTURAL_DAMAGE` so the deterministic risk gate and the
human approver can reject the trade.
"""

from __future__ import annotations

import logging

from app.llm import build_chat_openai
from app.state import CatalystAssessment
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Conservative default used when the LLM is unavailable or returns garbage.
# Failing closed means the trade is NOT treated as a clean pullback.
_FALLBACK_ASSESSMENT = CatalystAssessment(
    is_temporary_pullback=False,
    confidence_score=0.0,
    thesis_rationale="Analyst unavailable; failing closed (no clean-pullback signal).",
    catalyst_type="GENERAL_MARKET",
)

_SYSTEM_PROMPT = """\
You are a disciplined equity research analyst for a NIFTY 100 swing-trading
desk. You are given a stock symbol and recent news headlines / corporate
disclosures. Your ONLY job is to classify the nature of the recent price drop.

Classify into exactly one of:
- EARNINGS_NOISE: routine quarterly/earnings noise, no fundamental change.
- SECTOR_CONTAGION: the drop is driven by a peer or sector-wide de-rating.
- STRUCTURAL_DAMAGE: governance red flags, accounting fraud, promoter pledge
  spikes, regulatory action, or a material loss of the business thesis.
- GENERAL_MARKET: a broad index-level move with no stock-specific cause.

Rules:
1. Be conservative. If you see ANY governance, fraud, pledge or regulatory
   concern, classify as STRUCTURAL_DAMAGE.
2. is_temporary_pullback is True ONLY for EARNINGS_NOISE, SECTOR_CONTAGION or
   GENERAL_MARKET with no structural red flags.
3. confidence_score is your honest 0.0-1.0 confidence in the classification.
4. thesis_rationale must be 2-4 sentences citing the specific headlines.
5. Do NOT recommend a trade, price, size or order. Classification only.
"""


def _build_llm():
    """Instantiate the OpenAI-compatible chat model from settings."""
    return build_chat_openai()


def analyze_catalyst(symbol: str, news_headlines: list[str]) -> CatalystAssessment:
    """Run the LLM catalyst classification for a single symbol.

    Parameters
    ----------
    symbol:
        NSE symbol being evaluated.
    news_headlines:
        List of recent headlines / disclosure snippets for the symbol.

    Returns
    -------
    CatalystAssessment
        The structured classification. On any failure (missing API key, network
        error, schema violation) this returns a conservative fallback that
        fails the trade closed rather than letting a bad signal through.
    """
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set; returning conservative fallback for %s.", symbol)
        return _FALLBACK_ASSESSMENT

    headlines_text = "\n".join(f"- {h}" for h in news_headlines) if news_headlines else "(no headlines available)"
    user_prompt = (
        f"Symbol: {symbol}\n\n"
        f"Recent news / disclosures:\n{headlines_text}\n\n"
        "Classify the nature of the recent price drop."
    )

    try:
        llm = _build_llm()
        structured = llm.with_structured_output(CatalystAssessment)
        assessment: CatalystAssessment = structured.invoke(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        logger.info(
            "ANALYST %s: type=%s pullback=%s conf=%.2f",
            symbol, assessment.catalyst_type,
            assessment.is_temporary_pullback, assessment.confidence_score,
        )
        return assessment
    except Exception as exc:  # noqa: BLE001 - fail closed on any analyst error
        logger.error("Catalyst analysis failed for %s: %s", symbol, exc)
        return _FALLBACK_ASSESSMENT
