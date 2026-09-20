"""Centralized retry policies and decorators (ADR-019).

Provides robust, configurable retry decorators with exponential backoff, jitter,
and logging for external network requests, data feeds, and transient database glitches.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Sequence, Type

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)

DEFAULT_NETWORK_EXCEPTIONS: tuple[Type[BaseException], ...] = (
    requests.RequestException,
    ConnectionError,
    TimeoutError,
    OSError,
)


def network_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_exceptions: Sequence[Type[BaseException]] = DEFAULT_NETWORK_EXCEPTIONS,
    custom_logger: logging.Logger = logger,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator applying exponential backoff with jitter for network calls."""
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(tuple(retry_exceptions)),
        before_sleep=before_sleep_log(custom_logger, logging.WARNING),
    )


def db_retry(
    max_attempts: int = 3,
    min_wait: float = 0.5,
    max_wait: float = 5.0,
    custom_logger: logging.Logger = logger,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator applying exponential backoff for transient database operations."""
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=before_sleep_log(custom_logger, logging.WARNING),
    )
