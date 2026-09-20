from __future__ import annotations

from app.agents import (
    BearAssessment,
    BullAssessment,
    ResearchVerdict,
    analyze_bear_risks,
    analyze_bull_momentum,
    run_qualitative_research,
    synthesize_research,
)
from app.analyst import analyze_catalyst
from config.settings import get_settings


def test_agent_models_instantiation():
    bear = BearAssessment(
        red_flags=["Promoter pledge increased 15%"],
        structural_risks=["Debt maturity in Q3"],
        governance_score=0.45,
        is_structural_damage=True,
        confidence=0.85,
        bear_rationale="Material governance and leverage risk detected.",
    )
    assert bear.is_structural_damage is True
    assert bear.governance_score == 0.45
    assert len(bear.red_flags) == 1

    bull = BullAssessment(
        momentum_thesis="Multi-year breakout with volume surge",
        volume_quality="Strong institutional accumulation",
        sector_tailwinds=["PLI scheme expansion"],
        catalyst_drivers=["Q2 earnings beat expectations"],
        confidence=0.80,
        bull_rationale="Robust momentum supported by volume and sector growth.",
    )
    assert bull.confidence == 0.80
    assert len(bull.sector_tailwinds) == 1

    verdict = ResearchVerdict(
        composite_confidence=0.75,
        verdict="BUY",
        catalyst_type="EARNINGS_NOISE",
        thesis_summary="Routine quarterly noise in secular uptrend.",
        invalidation_criteria=["Close below 50 EMA on high volume"],
        citations=["Q2 Revenue beats street estimates"],
        bear_assessment=bear,
        bull_assessment=bull,
    )
    assert verdict.verdict == "BUY"
    assert verdict.composite_confidence == 0.75
    assert not verdict.early_vetoed


def test_unconfigured_llm_fails_closed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    bear = analyze_bear_risks("RELIANCE", ["Headline 1"])
    assert bear.confidence == 0.0
    assert bear.is_structural_damage is True

    bull = analyze_bull_momentum("RELIANCE", ["Headline 1"])
    assert bull.confidence == 0.0

    synth = synthesize_research("RELIANCE", bear, bull, ["Headline 1"])
    assert synth.verdict == "PASS"
    assert synth.composite_confidence == 0.0

    verdict = run_qualitative_research("RELIANCE", ["Headline 1"])
    assert verdict.verdict == "PASS"
    assert verdict.composite_confidence == 0.0

    get_settings.cache_clear()


def test_bear_early_exit_skips_downstream_agents(monkeypatch):
    """Verify that when Bear Critic detects structural damage (conf >= 0.70),
    Bull Analyst and Synthesizer are NEVER called, saving LLM tokens."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("RESEARCH_CACHE_ENABLED", "false")
    get_settings.cache_clear()

    bull_called = False
    synth_called = False

    def fake_bear(symbol, headlines):
        return BearAssessment(
            red_flags=["SEBI forensic audit initiated"],
            structural_risks=["Promoter pledging 80%"],
            governance_score=0.1,
            is_structural_damage=True,
            confidence=0.90,  # >= 0.70 threshold
            bear_rationale="Severe forensic audit and promoter leverage.",
        )

    def fake_bull(symbol, headlines):
        nonlocal bull_called
        bull_called = True
        return BullAssessment(
            momentum_thesis="Thesis",
            volume_quality="Good",
            sector_tailwinds=[],
            catalyst_drivers=[],
            confidence=0.5,
            bull_rationale="Rationale",
        )

    def fake_synth(symbol, bear, bull, headlines):
        nonlocal synth_called
        synth_called = True
        return ResearchVerdict(
            composite_confidence=0.5,
            verdict="PASS",
            catalyst_type="STRUCTURAL_DAMAGE",
            thesis_summary="Summary",
            invalidation_criteria=[],
            citations=[],
        )

    monkeypatch.setattr("app.agents.research_subgraph.analyze_bear_risks", fake_bear)
    monkeypatch.setattr("app.agents.research_subgraph.analyze_bull_momentum", fake_bull)
    monkeypatch.setattr("app.agents.research_subgraph.synthesize_research", fake_synth)

    verdict = run_qualitative_research("ADANIPORTS", ["SEBI orders forensic audit"])

    assert verdict.early_vetoed is True
    assert verdict.verdict == "PASS"
    assert verdict.catalyst_type == "STRUCTURAL_DAMAGE"
    assert "Early exit" in verdict.thesis_summary
    assert bull_called is False
    assert synth_called is False

    get_settings.cache_clear()


def test_full_sequential_debate_when_bear_passes(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("RESEARCH_CACHE_ENABLED", "false")
    get_settings.cache_clear()

    bull_called = False
    synth_called = False

    def fake_bear(symbol, headlines):
        return BearAssessment(
            red_flags=[],
            structural_risks=[],
            governance_score=0.95,
            is_structural_damage=False,  # Clean setup
            confidence=0.85,
            bear_rationale="No material governance or balance sheet red flags.",
        )

    def fake_bull(symbol, headlines):
        nonlocal bull_called
        bull_called = True
        return BullAssessment(
            momentum_thesis="Multi-quarter margin expansion",
            volume_quality="Institutional accumulation on breakout",
            sector_tailwinds=["Capital goods capex upcycle"],
            catalyst_drivers=["Record order book"],
            confidence=0.82,
            bull_rationale="Strong business tailwinds and order inflows.",
        )

    def fake_synth(symbol, bear, bull, headlines):
        nonlocal synth_called
        synth_called = True
        return ResearchVerdict(
            composite_confidence=0.78,
            verdict="BUY",
            catalyst_type="EARNINGS_NOISE",
            thesis_summary="Clean balance sheet with accelerating order book growth.",
            invalidation_criteria=["Close below 50 EMA"],
            citations=headlines,
            bear_assessment=bear,
            bull_assessment=bull,
            early_vetoed=False,
        )

    monkeypatch.setattr("app.agents.research_subgraph.analyze_bear_risks", fake_bear)
    monkeypatch.setattr("app.agents.research_subgraph.analyze_bull_momentum", fake_bull)
    monkeypatch.setattr("app.agents.research_subgraph.synthesize_research", fake_synth)

    verdict = run_qualitative_research("SIEMENS", ["Siemens bags ₹500 Cr order"])

    assert verdict.early_vetoed is False
    assert verdict.verdict == "BUY"
    assert verdict.composite_confidence == 0.78
    assert bull_called is True
    assert synth_called is True

    # Check analyst adapter integration
    assessment = analyze_catalyst("SIEMENS", ["Siemens bags ₹500 Cr order"])
    assert assessment.is_temporary_pullback is True
    assert assessment.confidence_score == 0.78
    assert assessment.catalyst_type == "EARNINGS_NOISE"

    get_settings.cache_clear()
