"""Unit tests for bounded concurrency and thread pool management (app/telegram_bot.py)."""

from __future__ import annotations

import time
from concurrent.futures import Future

from app import telegram_bot


def test_worker_pool_is_singleton_with_bounded_workers():
    pool1 = telegram_bot.get_worker_pool()
    pool2 = telegram_bot.get_worker_pool()

    assert pool1 is pool2
    assert pool1._max_workers == 3


def test_submit_background_task_executes_successfully():
    def _task(x: int, y: int) -> int:
        return x + y

    future: Future = telegram_bot.submit_background_task(_task, 10, 20)
    result = future.result(timeout=2.0)

    assert result == 30


def test_worker_pool_handles_concurrent_burst():
    def _slow_work(duration: float) -> str:
        time.sleep(duration)
        return "done"

    futures = [
        telegram_bot.submit_background_task(_slow_work, 0.05)
        for _ in range(6)
    ]
    results = [f.result(timeout=2.0) for f in futures]

    assert results == ["done"] * 6


def test_shutdown_and_reinitialize_worker_pool():
    pool = telegram_bot.get_worker_pool()
    assert pool is not None

    telegram_bot.shutdown_worker_pool(wait=True)
    assert telegram_bot._WORKER_POOL is None

    # Requesting pool again lazily reinitializes it
    new_pool = telegram_bot.get_worker_pool()
    assert new_pool is not None
    assert new_pool._max_workers == 3
