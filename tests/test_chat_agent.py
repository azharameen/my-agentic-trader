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


def test_get_groww_quote_returns_not_configured_when_disabled(monkeypatch):
    """ADR-036: read-only live quote tool must be fail-closed when Groww is off."""
    monkeypatch.setenv("GROWW_ENABLED", "false")
    from config.settings import get_settings

    get_settings.cache_clear()
    result = chat_agent.get_groww_quote("RELIANCE")
    assert "not enabled or configured" in result
    get_settings.cache_clear()


def test_get_groww_quote_formats_live_quote(monkeypatch):
    """ADR-036: real-time quote tool reports LTP/day change from Groww."""
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    from config.settings import get_settings

    get_settings.cache_clear()

    from app import groww_client

    client = groww_client.GrowwClient()

    def _fake_status():
        return groww_client.GrowwStatus(configured=True, authenticated=True, status="CONNECTED")

    def _fake_quote(symbol):
        return {
            "last_price": 2500.5,
            "day_change": 12.5,
            "day_change_perc": 0.5,
            "high_trade_range": 2510.0,
            "low_trade_range": 2480.0,
            "ohlc": {"open": 2490.0, "high": 2510.0, "low": 2480.0, "close": 2500.5},
            "volume": 10000,
            "week_52_high": 2600.0,
            "week_52_low": 2200.0,
        }

    client.get_connection_status = _fake_status
    client.get_quote = _fake_quote

    import app.groww_client as groww_client_mod

    monkeypatch.setattr(groww_client_mod, "get_groww_client", lambda: client)

    result = chat_agent.get_groww_quote("reliance.NS")
    assert '"symbol": "RELIANCE"' in result
    assert '"last_price": 2500.5' in result
    get_settings.cache_clear()
