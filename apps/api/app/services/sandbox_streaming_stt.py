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


_SEGMENT_BYTES_THRESHOLD = 96000  # ~3 seconds of 16kHz 16-bit mono PCM


class SandboxLiveSTTSession:
    """Mock live STT session for development without a DashScope API key."""

    def __init__(
        self,
        on_segment: Callable[[STTSegment], Awaitable[None]],
        latency: float = 0.15,
    ):
        self._on_segment = on_segment
        self._latency = latency
        self._bytes_fed = 0
        self._segment_index = 0
        self._segments = _TRANSCRIPT_SEGMENTS

    async def start(self) -> None:
        self._bytes_fed = 0
        self._segment_index = 0
        logger.info("Sandbox live STT session started")

    async def feed_audio(self, chunk: bytes) -> None:
        self._bytes_fed += len(chunk)

        while (
            self._segment_index < len(self._segments)
            and self._bytes_fed
            >= (self._segment_index + 1) * _SEGMENT_BYTES_THRESHOLD
        ):
            await self._emit_segment()

    async def finish(self) -> None:
        # Emit a few more segments to simulate final speech turns,
        # but don't dump the entire canned transcript.
        remaining = min(3, len(self._segments) - self._segment_index)
        for _ in range(remaining):
            await self._emit_segment()
        logger.info(
            "Sandbox live STT session finished, %d segments emitted",
            self._segment_index,
        )

    async def _emit_segment(self) -> None:
        text = self._segments[self._segment_index]
        start_ms = self._segment_index * 3000
        end_ms = (self._segment_index + 1) * 3000
        emotion = random.choices(_EMOTIONS, weights=_EMOTION_WEIGHTS, k=1)[0]
        self._segment_index += 1

        await asyncio.sleep(self._latency)
        await self._on_segment(
            STTSegment(
                text=text,
                timestamp_start_ms=start_ms,
                timestamp_end_ms=end_ms,
                emotion=emotion,
            )
        )


class SandboxStreamingSTT:
    """Mock streaming STT for development without a DashScope API key.

    Returns canned transcript segments from a real consultation with
    simulated timing and random emotion labels.
    """

    def __init__(self, latency: float = 0.15):
        self.latency = latency

    def create_live_session(
        self,
        language: str,
        on_segment: Callable[[STTSegment], Awaitable[None]],
    ) -> SandboxLiveSTTSession:
        return SandboxLiveSTTSession(
            on_segment=on_segment,
            latency=self.latency,
        )

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
