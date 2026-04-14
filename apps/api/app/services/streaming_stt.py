from __future__ import annotations

import asyncio
import base64
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

import websockets

logger = logging.getLogger(__name__)

# 100ms of 16kHz 16-bit mono PCM = 3200 bytes
_SEND_CHUNK_BYTES = 3200


@dataclass
class STTSegment:
    """A finalized transcript segment from the streaming ASR engine."""

    text: str
    timestamp_start_ms: int
    timestamp_end_ms: int
    emotion: str | None


class LiveSTTSession(Protocol):
    """Incremental audio feeding for live recording."""

    async def start(self) -> None: ...
    async def feed_audio(self, chunk: bytes) -> None: ...
    async def finish(self) -> None: ...


class StreamingSTTClient(Protocol):
    """High-level interface for streaming speech-to-text."""

    async def transcribe_stream(
        self,
        pcm_audio: bytes,
        language: str,
        on_segment: Callable[[STTSegment], Awaitable[None]],
        on_progress: Callable[[int], Awaitable[None]],
    ) -> None: ...

    def create_live_session(
        self,
        language: str,
        on_segment: Callable[[STTSegment], Awaitable[None]],
    ) -> LiveSTTSession: ...


class DashScopeLiveSTTSession:
    """Manages a persistent WebSocket to DashScope for live audio streaming."""

    def __init__(
        self,
        api_key: str,
        ws_base_url: str,
        model: str,
        language: str,
        on_segment: Callable[[STTSegment], Awaitable[None]],
        *,
        vad_threshold: float = 0.5,
        vad_silence_ms: int = 1200,
        vad_prefix_ms: int = 300,
    ):
        self._api_key = api_key
        self._ws_base_url = ws_base_url
        self._model = model
        self._language = language
        self._on_segment = on_segment
        self._vad_threshold = vad_threshold
        self._vad_silence_ms = vad_silence_ms
        self._vad_prefix_ms = vad_prefix_ms
        self._ws: websockets.ClientConnection | None = None
        self._receiver_task: asyncio.Task[None] | None = None
        self._finished = asyncio.Event()

    async def start(self) -> None:
        ws_url = f"{self._ws_base_url}/api-ws/v1/realtime?model={self._model}"
        headers = {"Authorization": f"bearer {self._api_key}"}
        self._ws = await websockets.connect(
            ws_url,
            additional_headers=headers,
            max_size=None,
        )

        transcription_params: dict = {"sample_rate": 16000}
        if self._language != "auto":
            transcription_params["language"] = self._language

        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "input_audio_format": "pcm",
                "input_audio_transcription": transcription_params,
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": self._vad_threshold,
                    "silence_duration_ms": self._vad_silence_ms,
                },
            },
        }
        await self._ws.send(json.dumps(session_update))
        logger.debug("Live STT session started, sent session.update")

        self._receiver_task = asyncio.create_task(self._receiver())

    async def feed_audio(self, chunk: bytes) -> None:
        if self._ws is None:
            return
        try:
            await self._ws.send(
                json.dumps(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode(),
                    }
                )
            )
        except Exception:
            # STT connection dropped — stop feeding but don't crash.
            # Already-received segments are still usable for SOAP.
            logger.warning("Live STT feed_audio failed, connection likely closed")
            self._ws = None

    async def finish(self) -> None:
        if self._ws is None:
            return
        try:
            await self._ws.send(json.dumps({"type": "session.finish"}))
            logger.debug("Sent session.finish, waiting for receiver to drain")
            await asyncio.wait_for(self._finished.wait(), timeout=30.0)
        except TimeoutError:
            logger.warning("Timed out waiting for session.finished from DashScope")
        finally:
            if self._receiver_task and not self._receiver_task.done():
                self._receiver_task.cancel()
            if self._ws:
                await self._ws.close()
                self._ws = None

    async def _receiver(self) -> None:
        assert self._ws is not None
        pending_start_ms = 0
        pending_end_ms = 0
        segment_count = 0
        # Track segment processing tasks so we don't block the receiver
        # on slow downstream callbacks (e.g. classification HTTP calls).
        segment_tasks: list[asyncio.Task[None]] = []

        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                event_type = msg.get("type", "")

                if event_type == "input_audio_buffer.speech_started":
                    pending_start_ms = msg.get("audio_start_ms", 0)

                elif event_type == "input_audio_buffer.speech_stopped":
                    pending_end_ms = msg.get("audio_end_ms", 0)

                elif (
                    event_type
                    == "conversation.item.input_audio_transcription.completed"
                ):
                    text = msg.get("transcript", "").strip()
                    if not text:
                        continue

                    segment_count += 1
                    segment = STTSegment(
                        text=text,
                        timestamp_start_ms=pending_start_ms,
                        timestamp_end_ms=pending_end_ms,
                        emotion=msg.get("emotion"),
                    )
                    logger.debug(
                        "Live segment %d: [%d-%d ms] %s (emotion=%s)",
                        segment_count,
                        pending_start_ms,
                        pending_end_ms,
                        text[:80],
                        segment.emotion,
                    )
                    # Fire-and-forget so we don't block reading the next
                    # DashScope message while classification runs.
                    coro = self._on_segment(segment)
                    task = asyncio.ensure_future(coro)
                    segment_tasks.append(task)
                    pending_start_ms = pending_end_ms
                    pending_end_ms = pending_start_ms

                elif event_type == "error":
                    error_msg = msg.get("error", {}).get("message", str(msg))
                    logger.error("Live STT error: %s", error_msg)

                elif event_type == "session.finished":
                    logger.info(
                        "Live STT session finished, %d segments", segment_count
                    )
                    break
        except websockets.ConnectionClosed:
            logger.warning("Live STT WebSocket closed unexpectedly")
        finally:
            # Wait for all in-flight segment tasks to complete
            if segment_tasks:
                await asyncio.gather(*segment_tasks, return_exceptions=True)
            self._finished.set()


class DashScopeStreamingSTT:
    """Streams PCM audio through DashScope's real-time ASR WebSocket API.

    One WebSocket connection per ``transcribe_stream`` call.  For uploaded
    audio files the entire buffer is sent as fast as the server will accept.
    For live recording, use ``create_live_session`` instead.
    """

    def __init__(
        self,
        api_key: str,
        ws_base_url: str,
        model: str,
        *,
        vad_threshold: float = 0.5,
        vad_silence_ms: int = 1200,
        vad_prefix_ms: int = 300,
    ):
        self.api_key = api_key
        self.ws_base_url = ws_base_url
        self.model = model
        self.vad_threshold = vad_threshold
        self.vad_silence_ms = vad_silence_ms
        self.vad_prefix_ms = vad_prefix_ms

    def create_live_session(
        self,
        language: str,
        on_segment: Callable[[STTSegment], Awaitable[None]],
    ) -> DashScopeLiveSTTSession:
        return DashScopeLiveSTTSession(
            api_key=self.api_key,
            ws_base_url=self.ws_base_url,
            model=self.model,
            language=language,
            on_segment=on_segment,
            vad_threshold=self.vad_threshold,
            vad_silence_ms=self.vad_silence_ms,
            vad_prefix_ms=self.vad_prefix_ms,
        )

    async def transcribe_stream(
        self,
        pcm_audio: bytes,
        language: str,
        on_segment: Callable[[STTSegment], Awaitable[None]],
        on_progress: Callable[[int], Awaitable[None]],
    ) -> None:
        total_bytes = len(pcm_audio)
        logger.info(
            "Starting streaming STT: %d bytes (%.1fs), model=%s, language=%s",
            total_bytes,
            total_bytes / 32000,
            self.model,
            language,
        )

        # Model is specified via URL query parameter per DashScope docs
        ws_url = f"{self.ws_base_url}/api-ws/v1/realtime?model={self.model}"
        headers = {"Authorization": f"bearer {self.api_key}"}
        async with websockets.connect(
            ws_url,
            additional_headers=headers,
            max_size=None,
        ) as ws:
            # Configure session
            transcription_params: dict = {
                "sample_rate": 16000,
            }
            if language != "auto":
                transcription_params["language"] = language

            session_update = {
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "input_audio_format": "pcm",
                    "input_audio_transcription": transcription_params,
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": self.vad_threshold,
                        "silence_duration_ms": self.vad_silence_ms,
                    },
                },
            }

            await ws.send(json.dumps(session_update))
            logger.debug("Sent session.update: %s", json.dumps(session_update))

            # Run sender and receiver concurrently.
            # DashScope emits speech_started (audio_start_ms) and
            # speech_stopped (audio_end_ms) events before each completed
            # event. We capture those to get accurate timestamps.
            pending_start_ms = 0
            pending_end_ms = 0

            async def _sender() -> None:
                for offset in range(0, total_bytes, _SEND_CHUNK_BYTES):
                    chunk = pcm_audio[offset : offset + _SEND_CHUNK_BYTES]
                    await ws.send(
                        json.dumps(
                            {
                                "type": "input_audio_buffer.append",
                                "audio": base64.b64encode(chunk).decode(),
                            }
                        )
                    )
                    await on_progress(min(offset + len(chunk), total_bytes))
                    # Yield to receiver so it can process incoming messages
                    await asyncio.sleep(0)

                await ws.send(json.dumps({"type": "session.finish"}))
                logger.debug("Sender finished, sent session.finish")

            async def _receiver() -> None:
                nonlocal pending_start_ms, pending_end_ms
                segment_count = 0
                async for raw in ws:
                    msg = json.loads(raw)
                    event_type = msg.get("type", "")

                    if event_type == "input_audio_buffer.speech_started":
                        pending_start_ms = msg.get("audio_start_ms", 0)

                    elif event_type == "input_audio_buffer.speech_stopped":
                        pending_end_ms = msg.get("audio_end_ms", 0)

                    elif (
                        event_type
                        == "conversation.item.input_audio_transcription.completed"
                    ):
                        text = msg.get("transcript", "").strip()
                        if not text:
                            continue

                        segment_count += 1
                        segment = STTSegment(
                            text=text,
                            timestamp_start_ms=pending_start_ms,
                            timestamp_end_ms=pending_end_ms,
                            emotion=msg.get("emotion"),
                        )
                        logger.debug(
                            "Segment %d: [%d-%d ms] %s (emotion=%s)",
                            segment_count,
                            pending_start_ms,
                            pending_end_ms,
                            text[:80],
                            segment.emotion,
                        )
                        await on_segment(segment)

                        # Reset for next segment
                        pending_start_ms = pending_end_ms
                        pending_end_ms = pending_start_ms

                    elif event_type == "error":
                        error_msg = msg.get("error", {}).get("message", str(msg))
                        logger.error("DashScope STT error: %s", error_msg)
                        raise RuntimeError(
                            f"DashScope streaming STT error: {error_msg}"
                        )

                    elif event_type == "session.finished":
                        logger.info(
                            "Session finished, received %d segments",
                            segment_count,
                        )
                        break

            await asyncio.gather(_sender(), _receiver())
