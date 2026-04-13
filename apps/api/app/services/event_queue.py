"""SSE event models and in-process pub/sub queue registry.

The background ``BatchAudioProcessor`` pushes events into the registry.
The SSE endpoint subscribes and streams them to clients.  Multiple
subscribers (e.g. multiple browser tabs) are supported via fan-out.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

MAX_QUEUE_SIZE = 200


# ---------------------------------------------------------------------------
# SSE event models
# ---------------------------------------------------------------------------


class SSEEvent(BaseModel):
    event: str
    data: dict[str, Any]


class TranscriptSegmentEvent(SSEEvent):
    event: str = "transcript_segment"


class SegmentClassifiedEvent(SSEEvent):
    event: str = "segment_classified"


class SegmentFailedEvent(SSEEvent):
    event: str = "segment_failed"


class ProgressEvent(SSEEvent):
    event: str = "progress"


class StatusEvent(SSEEvent):
    event: str = "status"


# ---------------------------------------------------------------------------
# Pub/sub registry
# ---------------------------------------------------------------------------


class EventQueueRegistry:
    """In-process pub/sub for SSE events, keyed by consultation ID.

    Lifecycle:
        1. ``create_topic(cid)`` — called when processing starts.
        2. ``push(cid, event)`` — called by the processor; fans out to all
           subscribers.
        3. ``subscribe(cid)`` — called by the SSE endpoint; returns a
           ``(sub_id, queue)`` pair.  Returns ``None`` if no active topic.
        4. ``unsubscribe(cid, sub_id)`` — called when the SSE client
           disconnects.
        5. ``remove_topic(cid)`` — called when processing finishes.
    """

    def __init__(self) -> None:
        self._topics: dict[uuid.UUID, dict[uuid.UUID, asyncio.Queue[SSEEvent]]] = {}

    def create_topic(self, consultation_id: uuid.UUID) -> None:
        self._topics.setdefault(consultation_id, {})

    def has_topic(self, consultation_id: uuid.UUID) -> bool:
        return consultation_id in self._topics

    def subscribe(
        self, consultation_id: uuid.UUID
    ) -> tuple[uuid.UUID, asyncio.Queue[SSEEvent]] | None:
        subs = self._topics.get(consultation_id)
        if subs is None:
            return None
        sub_id = uuid.uuid4()
        q: asyncio.Queue[SSEEvent] = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        subs[sub_id] = q
        return sub_id, q

    def unsubscribe(self, consultation_id: uuid.UUID, sub_id: uuid.UUID) -> None:
        subs = self._topics.get(consultation_id)
        if subs:
            subs.pop(sub_id, None)

    def push(self, consultation_id: uuid.UUID, event: SSEEvent) -> None:
        subs = self._topics.get(consultation_id)
        if not subs:
            return
        for q in subs.values():
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "SSE queue full for consultation %s, dropping event",
                    consultation_id,
                )

    def remove_topic(self, consultation_id: uuid.UUID) -> None:
        self._topics.pop(consultation_id, None)
