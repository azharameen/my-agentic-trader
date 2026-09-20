"""Unit tests for centralized retry decorators (app/retry.py)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from app.retry import db_retry, network_retry


def test_network_retry_succeeds_on_first_try():
    mock_func = MagicMock(return_value="success")
    decorated = network_retry(max_attempts=3, min_wait=0.01, max_wait=0.05)(mock_func)

    result = decorated()
    assert result == "success"
    assert mock_func.call_count == 1


def test_network_retry_recovers_after_transient_errors():
    attempts = [0]

    def _flaky():
        attempts[0] += 1
        if attempts[0] < 3:
            raise requests.ConnectionError("Temporary DNS drop")
        return "recovered"

    decorated = network_retry(max_attempts=3, min_wait=0.01, max_wait=0.05)(_flaky)
    result = decorated()

    assert result == "recovered"
    assert attempts[0] == 3


def test_network_retry_exhausts_and_raises_after_max_attempts():
    mock_func = MagicMock(side_effect=requests.Timeout("Connection timed out"))
    decorated = network_retry(max_attempts=3, min_wait=0.01, max_wait=0.05)(mock_func)

    with pytest.raises(requests.Timeout):
        decorated()

    assert mock_func.call_count == 3


def test_db_retry_recovers_on_transient_os_error():
    attempts = [0]

    def _db_query():
        attempts[0] += 1
        if attempts[0] < 2:
            raise OSError("Socket temporarily closed")
        return [{"symbol": "RELIANCE"}]

    decorated = db_retry(max_attempts=3, min_wait=0.01, max_wait=0.05)(_db_query)
    result = decorated()

    assert result == [{"symbol": "RELIANCE"}]
    assert attempts[0] == 2
