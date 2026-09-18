"""Shared OpenAI-compatible LLM helpers."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from config.settings import get_settings


def build_chat_openai() -> ChatOpenAI:
    """Build a deterministic ChatOpenAI client from app settings."""
    settings = get_settings()
    kwargs: dict = {
        "model": settings.OPENAI_MODEL,
        "api_key": settings.OPENAI_API_KEY,
        "temperature": 0.0,
        "max_retries": 3,
        "timeout": 30,
    }
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL
    return ChatOpenAI(**kwargs)
