from __future__ import annotations

from app import analyst, chat_agent, graph
from app.state import CatalystAssessment

_SNAPSHOT = {"daily_close": 100.0, "rsi": 30.0, "ema_200": 90.0, "atr": 2.0}


def test_get_symbol_history_reports_no_run_when_absent():
    assert "No pipeline run recorded" in chat_agent.get_symbol_history("NEVERRUN")


def test_get_symbol_history_reports_step_trail_after_a_run(monkeypatch):
    def _pullback_assessment(*_args, **_kwargs):
        return CatalystAssessment(
            is_temporary_pullback=True,
            confidence_score=0.8,
            thesis_rationale="Routine earnings noise.",
            catalyst_type="EARNINGS_NOISE",
        )

    monkeypatch.setattr(analyst, "analyze_catalyst", _pullback_assessment)
    graph.run_symbol("CHATHISTORY", snapshot=_SNAPSHOT)

    result = chat_agent.get_symbol_history("CHATHISTORY")

    assert "human_approval" in result
    assert "paused_for_approval" in result


def test_build_agent_uses_create_agent_with_safety_middleware(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from config.settings import get_settings
    get_settings.cache_clear()

    built = chat_agent._build_agent()
    node_names = " ".join(built.nodes.keys())

    assert "model" in built.nodes
    assert "SummarizationMiddleware" in node_names
    assert "ToolCallLimitMiddleware" in node_names
    assert "PIIMiddleware" in node_names
    get_settings.cache_clear()
