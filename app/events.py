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
from typing import Any, AsyncGenerator, Dict, Set

logger = logging.getLogger(__name__)

# Active SSE listener queues
_subscribers: Set[asyncio.Queue] = set()
_subscribers_lock = asyncio.Lock()


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

    # If an asyncio event loop is running, schedule put onto each subscriber queue
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop in the current thread (e.g. called from synchronous background thread)
        return

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
