"""Real-time SSE event bus for TrAId Web Application.

Provides an asynchronous pub-sub event broadcast mechanism for streaming
live universe scan progress, new trade proposal alerts, position changes,
and system status updates to connected web clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Active SSE listener queues
_subscribers: Set[asyncio.Queue] = set()
_subscribers_lock = asyncio.Lock()

# Reference to the FastAPI/uvicorn event loop, captured at startup so that
# broadcasts triggered from background threads (e.g. APScheduler jobs) can be
# safely scheduled onto it instead of silently no-oping.
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def bind_main_loop(loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    """Capture the running asyncio loop so background threads can broadcast."""
    global _main_loop
    _main_loop = loop or asyncio.get_event_loop()


async def subscribe() -> AsyncGenerator[Dict[str, Any], None]:
    """Register a new SSE client subscriber and yield events as they occur."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    async with _subscribers_lock:
        _subscribers.add(queue)
    logger.debug("New SSE client subscribed. Total active listeners: %d", len(_subscribers))

    # Send an initial connection heartbeat event
    yield {
        "event": "connected",
        "data": json.dumps({"status": "connected", "timestamp": datetime.now(timezone.utc).isoformat()}),
    }

    try:
        while True:
            event = await queue.get()
            yield event
    except (asyncio.CancelledError, GeneratorExit):
        pass
    finally:
        async with _subscribers_lock:
            _subscribers.discard(queue)
        logger.debug("SSE client disconnected. Remaining listeners: %d", len(_subscribers))


def broadcast_event(event_type: str, payload: Dict[str, Any]) -> None:
    """Broadcast an event payload to all connected SSE clients (thread-safe)."""
    event_data = {
        "event": event_type,
        "data": json.dumps({
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }),
    }

    def _dispatch() -> None:
        for q in list(_subscribers):
            try:
                q.put_nowait(event_data)
            except asyncio.QueueFull:
                # If a slow subscriber has filled its buffer, drop the oldest to stay responsive
                try:
                    q.get_nowait()
                    q.put_nowait(event_data)
                except Exception:  # noqa: BLE001
                    pass

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        _dispatch()
        return

    # Called from a synchronous background thread (e.g. APScheduler job) —
    # schedule the dispatch onto the captured main loop instead of dropping it.
    if _main_loop is not None and _main_loop.is_running():
        _main_loop.call_soon_threadsafe(_dispatch)
    else:
        logger.debug("No active event loop bound; dropping event %s", event_type)
