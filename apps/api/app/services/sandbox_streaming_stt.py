from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from app.services.sandbox_client import _TRANSCRIPT_SEGMENTS
from app.services.streaming_stt import STTSegment

logger = logging.getLogger(__name__)

_EMOTIONS = ["surprised", "neutral", "happy", "sad", "disgusted", "angry", "fearful"]

# Weight neutral heavily since most medical conversation is neutral
_EMOTION_WEIGHTS = [0.03, 0.70, 0.05, 0.08, 0.02, 0.04, 0.08]


class SandboxStreamingSTT:
    """Mock streaming STT for development without a DashScope API key.

    Returns canned transcript segments from a real consultation with
    simulated timing and random emotion labels.
    """

    def __init__(self, latency: float = 0.15):
        self.latency = latency

    async def transcribe_stream(
        self,
        pcm_audio: bytes,
        language: str,
        on_segment: Callable[[STTSegment], Awaitable[None]],
        on_progress: Callable[[int], Awaitable[None]],
    ) -> None:
        total_bytes = len(pcm_audio)
        total_ms = (total_bytes * 1000) // 32000  # PCM duration in ms
        segments = _TRANSCRIPT_SEGMENTS
        num_segments = len(segments)

        if num_segments == 0:
            return

        segment_duration_ms = total_ms // num_segments

        logger.info(
            "Sandbox streaming STT: %d bytes (%.1fs), %d segments",
            total_bytes,
            total_bytes / 32000,
            num_segments,
        )

        for i, text in enumerate(segments):
            await asyncio.sleep(self.latency)

            start_ms = i * segment_duration_ms
            end_ms = (i + 1) * segment_duration_ms
            emotion = random.choices(_EMOTIONS, weights=_EMOTION_WEIGHTS, k=1)[0]

            await on_segment(
                STTSegment(
                    text=text,
                    timestamp_start_ms=start_ms,
                    timestamp_end_ms=end_ms,
                    emotion=emotion,
                )
            )

            bytes_consumed = int((i + 1) / num_segments * total_bytes)
            await on_progress(bytes_consumed)

        logger.info("Sandbox streaming STT complete: %d segments emitted", num_segments)
