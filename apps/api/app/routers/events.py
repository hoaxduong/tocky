"""SSE endpoint for streaming processing events to clients."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app import database
from app.db_models.consultation import Consultation
from app.db_models.transcript import (
    STATUS_CLASSIFIED,
    STATUS_FAILED_CLASSIFICATION,
    STATUS_FAILED_TRANSCRIPTION,
    Transcript,
)
from app.services.auth import decode_access_token
from app.services.event_queue import EventQueueRegistry, SSEEvent, StatusEvent

router = APIRouter(
    prefix="/consultations/{consultation_id}/events",
    tags=["events"],
)

TERMINAL_STATUSES = {"completed", "failed", "completed_with_errors"}
KEEPALIVE_INTERVAL = 30  # seconds


# ---------------------------------------------------------------------------
# SSE wire format helpers
# ---------------------------------------------------------------------------


def _sse(event: str, data: dict) -> str:
    """Format an SSE event as a wire-format string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _sse_comment(text: str) -> str:
    return f": {text}\n\n"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def _authenticate(token: str | None, tocky_access: str | None) -> dict:
    access_token = token or tocky_access
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return decode_access_token(access_token)


# ---------------------------------------------------------------------------
# Transcript → SSE catchup events
# ---------------------------------------------------------------------------


def _transcript_to_sse(t: Transcript) -> list[str]:
    """Convert a persisted Transcript row into SSE wire-format strings."""
    events: list[str] = []

    if t.status == STATUS_FAILED_TRANSCRIPTION:
        events.append(
            _sse(
                "segment_failed",
                {
                    "sequence": t.sequence_number,
                    "step": "transcription",
                    "error_message": t.error_message or "Unknown error",
                },
            )
        )
    else:
        events.append(
            _sse(
                "transcript_segment",
                {
                    "sequence": t.sequence_number,
                    "text": t.text,
                    "timestamp_start_ms": t.timestamp_start_ms,
                    "timestamp_end_ms": t.timestamp_end_ms,
                    "emotion": t.emotion,
                },
            )
        )

        if t.status == STATUS_CLASSIFIED:
            events.append(
                _sse(
                    "segment_classified",
                    {
                        "sequence": t.sequence_number,
                        "is_medically_relevant": t.is_medically_relevant,
                    },
                )
            )
        elif t.status == STATUS_FAILED_CLASSIFICATION:
            events.append(
                _sse(
                    "segment_failed",
                    {
                        "sequence": t.sequence_number,
                        "step": "classification",
                        "error_message": t.error_message or "Unknown error",
                    },
                )
            )

    return events


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/")
async def stream_processing_events(
    consultation_id: uuid.UUID,
    request: Request,
    token: Annotated[str | None, Query()] = None,
    tocky_access: Annotated[str | None, Cookie()] = None,
) -> StreamingResponse:
    # --- Validate BEFORE starting the stream ---
    payload = _authenticate(token, tocky_access)
    user_id = payload["sub"]

    assert database.async_session_factory is not None
    async with database.async_session_factory() as db:
        result = await db.execute(
            select(Consultation).where(
                Consultation.id == consultation_id,
                Consultation.user_id == user_id,
            )
        )
        consultation = result.scalar_one_or_none()
        if consultation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consultation not found",
            )
        consultation_status = consultation.status
        consultation_progress = consultation.processing_progress
        consultation_step = consultation.processing_step

    # Pre-fetch existing transcripts for late-join catchup
    async with database.async_session_factory() as db:
        result = await db.execute(
            select(Transcript)
            .where(Transcript.consultation_id == consultation_id)
            .order_by(Transcript.sequence_number)
        )
        existing_transcripts = result.scalars().all()

    registry: EventQueueRegistry = request.app.state.event_registry

    # --- Streaming generator ---
    async def _generate() -> AsyncIterator[str]:
        # Late-join catchup
        for t in existing_transcripts:
            for chunk in _transcript_to_sse(t):
                yield chunk

        # Send current progress
        if consultation_step:
            yield _sse(
                "progress",
                {"step": consultation_step, "progress": consultation_progress},
            )

        # Already terminal? Send status and close.
        if consultation_status in TERMINAL_STATUSES:
            yield _sse("status", {"status": consultation_status})
            return

        # Subscribe to live events
        sub = registry.subscribe(consultation_id)
        if sub is None:
            # Topic gone — processing finished between our check and now
            async with database.async_session_factory() as db:
                result = await db.execute(
                    select(Consultation.status).where(
                        Consultation.id == consultation_id
                    )
                )
                current_status = result.scalar_one()
            yield _sse("status", {"status": current_status})
            return

        sub_id, queue = sub
        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event: SSEEvent = await asyncio.wait_for(
                        queue.get(), timeout=KEEPALIVE_INTERVAL
                    )
                except TimeoutError:
                    yield _sse_comment("keepalive")
                    continue

                yield _sse(event.event, event.data)

                if isinstance(event, StatusEvent):
                    break
        finally:
            registry.unsubscribe(consultation_id, sub_id)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
