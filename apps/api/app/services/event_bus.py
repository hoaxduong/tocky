"""In-memory pub/sub for streaming consultation processing events.

Usage:
  - The background processor calls ``publish(consultation_id, event)`` after each
    checkpoint (progress tick, new transcript segment, status change).
  - The SSE endpoint calls ``subscribe(consultation_id)`` to get an async
    iterator of events, closes it on client disconnect.

Processing runs in FastAPI ``BackgroundTasks`` and is independent of any
subscriber: clients can disconnect & reconnect without affecting the run.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Cap each subscriber's buffer so a slow client can't balloon memory.
_SUBSCRIBER_QUEUE_MAXSIZE = 256


@dataclass
class _Channel:
    subscribers: set[asyncio.Queue[dict[str, Any]]] = field(default_factory=set)


class EventBus:
    def __init__(self) -> None:
        self._channels: dict[uuid.UUID, _Channel] = {}
        self._lock = asyncio.Lock()

    async def publish(self, consultation_id: uuid.UUID, event: dict[str, Any]) -> None:
        channel = self._channels.get(consultation_id)
        if channel is None:
            return
        # Snapshot to avoid "set changed size during iteration"
        for queue in list(channel.subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Event bus subscriber lagging for %s; dropping oldest event",
                    consultation_id,
                )
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except asyncio.QueueEmpty:
                    pass

    async def subscribe(
        self, consultation_id: uuid.UUID
    ) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=_SUBSCRIBER_QUEUE_MAXSIZE
        )
        async with self._lock:
            channel = self._channels.setdefault(consultation_id, _Channel())
            channel.subscribers.add(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                channel = self._channels.get(consultation_id)
                if channel is not None:
                    channel.subscribers.discard(queue)
                    if not channel.subscribers:
                        self._channels.pop(consultation_id, None)


# Module-level singleton used by processor & SSE endpoint.
event_bus = EventBus()
