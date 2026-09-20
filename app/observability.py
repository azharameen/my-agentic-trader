"""Small OpenTelemetry boundary for pipeline, graph, and tool instrumentation."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_TRACER_NAME = "nifty-trading-agent"
_configured = False


def _apply_langsmith_env(settings: Settings) -> None:
    """Opt-in LangSmith tracing (ADR-021): set the standard env vars the
    LangSmith SDK reads directly, only when explicitly enabled and only when
    an API key is configured. Fails closed (no tracing, no crash) otherwise,
    and never logs the key itself.
    """
    if not settings.LANGSMITH_TRACING_ENABLED:
        return
    key = (
        settings.LANGSMITH_API_KEY.get_secret_value()
        if hasattr(settings.LANGSMITH_API_KEY, "get_secret_value")
        else str(settings.LANGSMITH_API_KEY or "")
    )
    if not key.strip():
        logger.warning(
            "LANGSMITH_TRACING_ENABLED is true but LANGSMITH_API_KEY is empty; "
            "LangSmith tracing stays disabled."
        )
        return
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = key
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    if settings.LANGSMITH_ENDPOINT:
        os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    logger.info("LangSmith tracing enabled for project '%s'.", settings.LANGSMITH_PROJECT)


def configure() -> None:
    """Configure an SDK provider when tracing is explicitly enabled.

    The API remains usable as a no-op when tracing is disabled, which keeps
    local tests and paper trading free of telemetry side effects.
    """
    global _configured
    if _configured:
        return
    _configured = True
    settings = get_settings()
    _apply_langsmith_env(settings)
    if not settings.OTEL_ENABLED:
        return

    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider = TracerProvider(resource=Resource.create({"service.name": _TRACER_NAME}))
    if settings.OTEL_CONSOLE_EXPORTER:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    logger.info("OpenTelemetry tracing enabled for %s.", _TRACER_NAME)


def tracer() -> trace.Tracer:
    """Return the application tracer."""
    configure()
    return trace.get_tracer(_TRACER_NAME)


@contextmanager
def span(name: str, **attributes: object) -> Iterator[Span]:
    """Create a span and record failures without changing business behavior."""
    with tracer().start_as_current_span(name) as current:
        for key, value in attributes.items():
            if value is not None:
                current.set_attribute(key, str(value))
        try:
            yield current
        except Exception as exc:
            current.record_exception(exc)
            current.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def event(name: str, **attributes: object) -> None:
    """Emit a lightweight structured event through the active span."""
    current = trace.get_current_span()
    if current.is_recording():
        current.add_event(name, {key: str(value) for key, value in attributes.items()})
