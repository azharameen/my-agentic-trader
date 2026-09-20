"""Unit tests for the LangGraph trading pipeline (app/graph.py)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import analyst, executor, graph, screener
from app.state import CatalystAssessment
from config.settings import get_settings

_SNAPSHOT = {"daily_close": 100.0, "rsi": 30.0, "ema_200": 90.0, "atr": 2.0}


def _pullback_assessment(*_args, **_kwargs):
    return CatalystAssessment(
        is_temporary_pullback=True,
        confidence_score=0.8,
        thesis_rationale="Routine earnings noise, no structural concern.",
        catalyst_type="EARNINGS_NOISE",
    )


def _structural_damage_assessment(*_args, **_kwargs):
    return CatalystAssessment(
        is_temporary_pullback=False,
        confidence_score=0.9,
        thesis_rationale="Promoter pledge spike detected.",
        catalyst_type="STRUCTURAL_DAMAGE",
    )


def _unsupported_market_assessment(*_args, **_kwargs):
    return CatalystAssessment(
        is_temporary_pullback=True,
        confidence_score=0.5,
        thesis_rationale="No stock-specific evidence was available.",
        catalyst_type="GENERAL_MARKET",
    )


def test_qualifying_symbol_pauses_for_approval(monkeypatch):
    monkeypatch.setattr(analyst, "analyze_catalyst", _pullback_assessment)
    state = graph.run_symbol("TESTPASS", snapshot=_SNAPSHOT)
    assert "__interrupt__" in state
    card = state["__interrupt__"][0].value
    assert card["symbol"] == "TESTPASS"
    assert "proposed_at" in card


def test_structural_damage_rejects_without_human_prompt(monkeypatch):
    monkeypatch.setattr(analyst, "analyze_catalyst", _structural_damage_assessment)
    state = graph.run_symbol("TESTBAD", snapshot=_SNAPSHOT)
    assert "__interrupt__" not in state
    assert state["execution_details"]["status"] == "REJECTED"
    assert state["rejection_reason"] == "STRUCTURAL_DAMAGE"


def test_general_market_without_regime_evidence_rejects_without_proposal(monkeypatch):
    monkeypatch.setattr(analyst, "analyze_catalyst", _unsupported_market_assessment)

    state = graph.run_symbol("NOREGIME", snapshot=_SNAPSHOT)

    assert "__interrupt__" not in state
    assert state["execution_details"]["status"] == "REJECTED"


def test_approved_resume_records_open_trade(monkeypatch):
    monkeypatch.setattr(analyst, "analyze_catalyst", _pullback_assessment)
    graph.run_symbol("TESTAPPROVE", snapshot=_SNAPSHOT)

    result = graph.resume_symbol("TESTAPPROVE", "APPROVED")
    assert result["execution_details"]["status"] == "OPEN_PAPER"

    trades = executor.fetch_all_trades()
    assert any(t["symbol"] == "TESTAPPROVE" for t in trades)


def test_rejected_resume_does_not_record_trade(monkeypatch):
    monkeypatch.setattr(analyst, "analyze_catalyst", _pullback_assessment)
    graph.run_symbol("TESTREJECT", snapshot=_SNAPSHOT)

    result = graph.resume_symbol("TESTREJECT", "REJECTED")
    assert result["execution_details"]["status"] == "REJECTED"
    trades = executor.fetch_all_trades()
    assert not any(t["symbol"] == "TESTREJECT" for t in trades)


def test_latest_thread_id_for_and_pending_list(monkeypatch):
    monkeypatch.setattr(analyst, "analyze_catalyst", _pullback_assessment)
    graph.run_symbol("TESTPENDING", snapshot=_SNAPSHOT)

    thread_id = graph.latest_thread_id_for("TESTPENDING")
    assert thread_id is not None
    assert thread_id.startswith("trade-TESTPENDING-")

    pending = graph.list_pending_approvals()
    assert any(card["symbol"] == "TESTPENDING" for card in pending)


def test_stale_proposal_with_price_drift_is_rejected(monkeypatch):
    old_card = {"proposed_at": (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()}
    monkeypatch.setattr(screener, "get_symbol_snapshot", lambda symbol: {"daily_close": 200.0})
    assert graph._proposal_is_stale(old_card, "ANY", entry_price=100.0) is True


def test_recent_proposal_is_never_stale():
    fresh_card = {"proposed_at": datetime.now(timezone.utc).isoformat()}
    assert graph._proposal_is_stale(fresh_card, "ANY", entry_price=100.0) is False


def test_precomputed_technical_cache_hit_is_preserved_in_state(monkeypatch):
    monkeypatch.setattr(analyst, "analyze_catalyst", _pullback_assessment)
    snapshot = {**_SNAPSHOT, "cache_hit": True}

    state = graph.run_symbol("TECHCACHE", snapshot=snapshot)

    assert "technical" in state["cache_hits"]


def test_identical_evidence_reuses_snapshot_despite_fresh_fetch_times(monkeypatch):
    monkeypatch.setattr(analyst, "analyze_catalyst", _pullback_assessment)

    first = graph.run_symbol("EVIDENCECACHE", snapshot=_SNAPSHOT, news_headlines=["Same headline"])
    second = graph.run_symbol("EVIDENCECACHE", snapshot=_SNAPSHOT, news_headlines=["Same headline"])

    assert first["evidence_snapshot_id"] == second["evidence_snapshot_id"]
    assert "evidence" in second["cache_hits"]


def test_evidence_cache_reuse_revalidates_configured_age(monkeypatch):
    monkeypatch.setattr(analyst, "analyze_catalyst", _pullback_assessment)
    monkeypatch.setenv("EVIDENCE_MAX_AGE_SECONDS", "0")
    get_settings.cache_clear()
    graph.run_symbol("EVIDENCEAGE", snapshot=_SNAPSHOT)

    monkeypatch.setenv("EVIDENCE_MAX_AGE_SECONDS", "-1")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="Evidence is stale"):
        graph.run_symbol("EVIDENCEAGE", snapshot=_SNAPSHOT)


def test_build_graph_is_compiled_with_the_shared_long_term_store():
    compiled = graph.build_graph()

    assert compiled.store is not None


def test_symbol_history_returns_ordered_checkpoint_steps(monkeypatch):
    monkeypatch.setattr(analyst, "analyze_catalyst", _pullback_assessment)
    graph.run_symbol("HISTORYSYMBOL", snapshot=_SNAPSHOT)

    history = graph.symbol_history("HISTORYSYMBOL")

    assert len(history) >= 2
    assert history[0]["next"] == ["human_approval"]
    assert history[0]["paused_for_approval"] is True
    assert history[-1]["next"] == ["__start__"]


def test_trace_metadata_builder_marks_normal_run():
    metadata = graph._trace_metadata("RELIANCE", decision=None)

    assert metadata["symbol"] == "RELIANCE"
    assert metadata["strategy"] == "pullback_in_uptrend"
    assert metadata["trader"] == "nifty100-swing"
    assert metadata["decision"] == "pending"


def test_trace_metadata_builder_marks_terminal_decision():
    metadata = graph._trace_metadata("RELIANCE", decision="REJECTED_RISK")

    assert metadata["decision"] == "REJECTED_RISK"
    assert metadata["symbol"] == "RELIANCE"
