"""Shared provider-selected LangChain chat model helpers."""

from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from config.settings import get_settings


def _common_kwargs(settings: Any) -> dict[str, Any]:
    return {
        "temperature": 0.0,
        "max_retries": settings.LLM_MAX_RETRIES,
        "timeout": settings.LLM_TIMEOUT_SECONDS,
    }


def _secret_str(val: Any) -> str:
    """Safely extract the plain string from a SecretStr or string."""
    if hasattr(val, "get_secret_value"):
        return val.get_secret_value()
    return str(val or "")


def is_configured() -> bool:
    settings = get_settings()
    key_mapping = {
        "openai_compatible": _secret_str(settings.OPENAI_API_KEY),
        "openai": _secret_str(settings.OPENAI_API_KEY),
        "gemini": _secret_str(settings.GOOGLE_API_KEY),
        "anthropic": _secret_str(settings.ANTHROPIC_API_KEY),
        "groq": _secret_str(settings.GROQ_API_KEY),
    }
    key_val = key_mapping.get(settings.LLM_PROVIDER, "")
    return bool(key_val.strip())


def provider_metadata() -> dict[str, str]:
    settings = get_settings()
    model = {
        "openai_compatible": settings.OPENAI_MODEL,
        "openai": settings.OPENAI_MODEL,
        "gemini": settings.GEMINI_MODEL,
        "anthropic": settings.ANTHROPIC_MODEL,
        "groq": settings.GROQ_MODEL,
    }.get(settings.LLM_PROVIDER, "")
    return {"provider": settings.LLM_PROVIDER, "model": model}


def build_chat_model() -> Any:
    """Build the configured native LangChain chat model."""
    settings = get_settings()
    kwargs = _common_kwargs(settings)
    provider = settings.LLM_PROVIDER

    if provider in {"openai_compatible", "openai"}:
        kwargs.update(
            model=settings.OPENAI_MODEL,
            api_key=_secret_str(settings.OPENAI_API_KEY),
        )
        if provider == "openai_compatible" and settings.OPENAI_BASE_URL:
            kwargs["base_url"] = settings.OPENAI_BASE_URL
        return ChatOpenAI(**kwargs)
    if provider == "gemini":
        kwargs.update(
            model=settings.GEMINI_MODEL,
            google_api_key=_secret_str(settings.GOOGLE_API_KEY),
        )
        return ChatGoogleGenerativeAI(**kwargs)
    if provider == "anthropic":
        kwargs.update(
            model=settings.ANTHROPIC_MODEL,
            api_key=_secret_str(settings.ANTHROPIC_API_KEY),
        )
        return ChatAnthropic(**kwargs)
    if provider == "groq":
        kwargs.update(
            model=settings.GROQ_MODEL,
            api_key=_secret_str(settings.GROQ_API_KEY),
        )
        return ChatGroq(**kwargs)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def build_chat_openai() -> ChatOpenAI:
    """Backward-compatible name for callers that expect the old factory."""
    return build_chat_model()
