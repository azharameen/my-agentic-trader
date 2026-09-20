from __future__ import annotations

import pytest

from app import llm
from config.settings import get_settings


def test_llm_client_uses_configured_timeout_and_retries(monkeypatch):
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("LLM_MAX_RETRIES", "0")
    get_settings.cache_clear()

    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(llm, "ChatOpenAI", FakeChatOpenAI)
    llm.build_chat_model()

    assert captured["timeout"] == 7
    assert captured["max_retries"] == 0
    get_settings.cache_clear()


def test_llm_client_uses_native_gemini_adapter(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    get_settings.cache_clear()

    captured = {}

    class FakeGemini:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(llm, "ChatGoogleGenerativeAI", FakeGemini)
    llm.build_chat_model()

    assert captured["model"] == "gemini-test"
    assert captured["google_api_key"] == "google-test-key"
    assert "base_url" not in captured
    get_settings.cache_clear()


def test_unknown_llm_provider_fails_closed(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    get_settings.cache_clear()

    try:
        llm.build_chat_model()
    except ValueError as exc:
        assert "Unknown LLM_PROVIDER" in str(exc)
    else:
        raise AssertionError("Unknown provider should fail closed")
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    ("provider", "key_name"),
    [
        ("openai_compatible", "OPENAI_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
        ("gemini", "GOOGLE_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("groq", "GROQ_API_KEY"),
    ],
)
def test_provider_requires_its_own_credentials(monkeypatch, provider, key_name):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv(key_name, "")
    get_settings.cache_clear()

    assert not llm.is_configured()
    get_settings.cache_clear()


@pytest.mark.parametrize("provider", ["openai", "gemini", "anthropic", "groq"])
def test_native_provider_supports_required_langchain_capabilities(monkeypatch, provider):
    key_names = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
    }
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv(key_names[provider], "test-key")
    get_settings.cache_clear()

    model = llm.build_chat_model()

    assert callable(model.with_structured_output)
    assert callable(model.bind_tools)
    get_settings.cache_clear()
