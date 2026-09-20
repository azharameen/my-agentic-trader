"""Sequential Multi-Agent Research Subgraph Coordinator (ADR-022).

Executes the Bear-first sequential qualitative analysis pipeline:
  1. BearRiskCritic (adversarial risk stress-testing)
  2. Early-Exit Gate: If structural damage with confidence >= 0.70, halt immediately (~60% token savings)
  3. BullMomentumAnalyst (constructive momentum & catalyst evaluation)
  4. SynthesisArbiter (balanced decision, invalidation criteria, and composite confidence)
"""

from __future__ import annotations

import logging

from app import cache
from app.agents.bear_critic import analyze_bear_risks
from app.agents.bull_analyst import analyze_bull_momentum
from app.agents.models import BearAssessment, BullAssessment, ResearchVerdict
from app.agents.synthesizer import synthesize_research
from app.evidence import content_hash
from app.llm import is_configured, provider_metadata
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Early exit thresholds (ADR-022)
EARLY_EXIT_CONFIDENCE_THRESHOLD = 0.70


def run_qualitative_research(
    symbol: str,
    news_headlines: list[str],
) -> ResearchVerdict:
    """Execute sequential qualitative multi-agent research on a screened candidate.

    Enforces Bear-first early exit: If Bear Critic detects structural damage
    with confidence >= 0.70, Bull Analyst and Synthesizer are skipped entirely.
    """
    if not is_configured():
        logger.warning("LLM provider not configured; returning fallback research verdict for %s.", symbol)
        return ResearchVerdict(
            composite_confidence=0.0,
            verdict="PASS",
            catalyst_type="GENERAL_MARKET",
            thesis_summary="LLM unconfigured; qualitative research rejected setup.",
            invalidation_criteria=["No LLM provider configured"],
            citations=[],
            early_vetoed=False,
        )

    settings = get_settings()
    metadata = provider_metadata()
    cache_key = content_hash({
        "symbol": symbol.upper(),
        "headlines": news_headlines,
        "type": "multi_agent_research_v1",
        **metadata,
    })

    cached, _cache_hit = cache.get_value_with_status("catalyst", cache_key)
    if cached is not None and settings.RESEARCH_CACHE_ENABLED:
        logger.debug("Cache hit for qualitative research on %s", symbol)
        return ResearchVerdict.model_validate(cached)

    logger.info("Starting multi-agent research debate for %s...", symbol)

    # 1. Bear Risk Critic (Adversarial)
    bear: BearAssessment = analyze_bear_risks(symbol, news_headlines)

    # 2. Early-Exit Gate (ADR-022)
    if bear.is_structural_damage and bear.confidence >= EARLY_EXIT_CONFIDENCE_THRESHOLD:
        logger.info(
            "EARLY EXIT TRIGGERED for %s: Bear Critic scored STRUCTURAL_DAMAGE (conf=%.2f >= %.2f). "
            "Skipping Bull Analyst and Synthesizer (~60%% token savings).",
            symbol, bear.confidence, EARLY_EXIT_CONFIDENCE_THRESHOLD,
        )
        early_verdict = ResearchVerdict(
            composite_confidence=0.0,
            verdict="PASS",
            catalyst_type="STRUCTURAL_DAMAGE",
            thesis_summary=f"Early exit: {bear.bear_rationale}",
            invalidation_criteria=bear.red_flags or ["Structural corporate governance/fraud risk identified"],
            citations=news_headlines[:3] if news_headlines else [],
            bear_assessment=bear,
            bull_assessment=None,
            early_vetoed=True,
        )
        if settings.RESEARCH_CACHE_ENABLED:
            cache.set_value(
                "catalyst", cache_key, early_verdict.model_dump(mode="json"),
                settings.CATALYST_CACHE_MINUTES,
            )
        return early_verdict

    # 3. Bull Momentum Analyst (Constructive)
    bull: BullAssessment = analyze_bull_momentum(symbol, news_headlines)

    # 4. Synthesis Arbiter (Decision & Invalidation criteria)
    verdict: ResearchVerdict = synthesize_research(symbol, bear, bull, news_headlines)

    if settings.RESEARCH_CACHE_ENABLED:
        cache.set_value(
            "catalyst", cache_key, verdict.model_dump(mode="json"),
            settings.CATALYST_CACHE_MINUTES,
        )

    logger.info(
        "Multi-agent debate concluded for %s: verdict=%s composite_conf=%.2f",
        symbol, verdict.verdict, verdict.composite_confidence,
    )
    return verdict
