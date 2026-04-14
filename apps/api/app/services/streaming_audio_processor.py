from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from app.services.ai_protocol import AIClient
from app.services.streaming_stt import LiveSTTSession, StreamingSTTClient, STTSegment

logger = logging.getLogger(__name__)

# Extract metadata after this many medically relevant segments.
_METADATA_SEGMENT_THRESHOLD = 3


class StreamingAudioProcessor:
    """Real-time audio processor that uses a streaming STT session.

    Replaces the buffer-based ``AudioProcessor`` for the live recording
    WebSocket flow.  Audio chunks are forwarded directly to a
    ``LiveSTTSession`` which performs VAD-based turn detection and
    returns per-turn transcript segments.

    For each segment the processor:
    - Classifies medical relevance via the AI client
    - Emits the annotated segment to the WebSocket client
    - Triggers metadata extraction after the first few relevant segments
    - Generates SOAP note updates at a configurable interval
    """

    def __init__(
        self,
        consultation_id: uuid.UUID,
        language: str,
        model_client: AIClient,
        streaming_stt: StreamingSTTClient,
        soap_interval_seconds: float = 30.0,
    ):
        self.consultation_id = consultation_id
        self.language = language
        self.model_client = model_client
        self._streaming_stt = streaming_stt
        self.soap_interval_seconds = soap_interval_seconds

        self._session: LiveSTTSession | None = None
        self.audio_buffer = bytearray()  # accumulate raw PCM for persistence
        self.transcript_segments: list[dict] = []
        self.sequence_counter = 0
        self.all_relevant_text: list[str] = []
        self._medically_relevant_count = 0
        self._metadata_extracted = False
        self._last_soap_time = time.monotonic()
        self._soap_task: asyncio.Task[None] | None = None
        self._metadata_task: asyncio.Task[None] | None = None

        # Callbacks set by the WebSocket handler
        self.on_transcript: Callable[..., Coroutine[Any, Any, None]] | None = None
        self.on_soap_update: Callable[..., Coroutine[Any, Any, None]] | None = None
        self.on_metadata_update: Callable[..., Coroutine[Any, Any, None]] | None = None

    async def start(self) -> None:
        # Use "auto" for STT so DashScope auto-detects the language.
        # self.language is still used for classification and SOAP prompts
        # until metadata extraction updates it.
        self._session = self._streaming_stt.create_live_session(
            "auto", self._on_stt_segment
        )
        await self._session.start()
        self._last_soap_time = time.monotonic()
        logger.info("StreamingAudioProcessor started for %s", self.consultation_id)

    async def feed_audio(self, chunk: bytes) -> None:
        if self._session is None:
            return
        self.audio_buffer.extend(chunk)
        await self._session.feed_audio(chunk)

        # Check if it's time for a periodic SOAP update
        elapsed = time.monotonic() - self._last_soap_time
        if elapsed >= self.soap_interval_seconds and self.all_relevant_text:
            self._schedule_soap_update()

    async def finalize(self) -> dict[str, Any]:
        # Finish the STT session (drains remaining segments)
        if self._session is not None:
            logger.info("Consultation %s: finishing STT session", self.consultation_id)
            await self._session.finish()
            logger.info("Consultation %s: STT session finished", self.consultation_id)

        # Wait for any in-flight background tasks (with timeout)
        pending: list[asyncio.Task[None]] = []
        if self._soap_task and not self._soap_task.done():
            pending.append(self._soap_task)
        if self._metadata_task and not self._metadata_task.done():
            pending.append(self._metadata_task)
        if pending:
            await asyncio.wait(pending, timeout=15.0)

        # Generate final SOAP note
        logger.info("Consultation %s: generating final SOAP", self.consultation_id)
        result: dict[str, Any] = {
            "subjective": "",
            "objective": "",
            "assessment": "",
            "plan": "",
            "medical_entities": {},
        }
        if self.all_relevant_text:
            full_transcript = "\n".join(self.all_relevant_text)
            try:
                soap = await asyncio.wait_for(
                    self.model_client.generate_soap(full_transcript, self.language),
                    timeout=200.0,
                )
                result.update(soap)
                logger.info(
                    "Consultation %s: SOAP generated", self.consultation_id
                )
            except Exception:
                logger.exception(
                    "Consultation %s: SOAP generation failed",
                    self.consultation_id,
                )
            try:
                entities = await asyncio.wait_for(
                    self.model_client.extract_medical_entities(
                        full_transcript, self.language
                    ),
                    timeout=140.0,
                )
                result["medical_entities"] = entities
            except Exception:
                logger.exception(
                    "Consultation %s: entity extraction failed",
                    self.consultation_id,
                )

        logger.info(
            "StreamingAudioProcessor finalized for %s: %d segments, %d relevant",
            self.consultation_id,
            len(self.transcript_segments),
            self._medically_relevant_count,
        )
        return result

    # ------------------------------------------------------------------
    # Internal callbacks and helpers
    # ------------------------------------------------------------------

    async def _on_stt_segment(self, stt_segment: STTSegment) -> None:
        """Called by the LiveSTTSession when a speech turn is detected."""
        text = stt_segment.text
        if not text.strip():
            return

        # Classify medical relevance (default to relevant on failure)
        is_relevant = True
        try:
            classify_text = text
            if stt_segment.emotion and stt_segment.emotion != "neutral":
                classify_text = f"[Speaker emotion: {stt_segment.emotion}] {text}"
            is_relevant = await self.model_client.classify_relevance(
                classify_text, self.language
            )
        except Exception:
            logger.warning(
                "Consultation %s: classification failed for segment, "
                "defaulting to relevant",
                self.consultation_id,
            )

        self.sequence_counter += 1
        segment = {
            "text": text,
            "is_medically_relevant": is_relevant,
            "speaker_label": None,
            "sequence": self.sequence_counter,
            "timestamp_start_ms": stt_segment.timestamp_start_ms,
            "timestamp_end_ms": stt_segment.timestamp_end_ms,
            "emotion": stt_segment.emotion,
        }
        self.transcript_segments.append(segment)

        if is_relevant:
            self.all_relevant_text.append(text)
            self._medically_relevant_count += 1

        if self.on_transcript:
            try:
                await self.on_transcript(segment)
            except Exception:
                logger.warning(
                    "Consultation %s: failed to send transcript segment %d",
                    self.consultation_id,
                    self.sequence_counter,
                )

        # Trigger metadata extraction after enough relevant segments
        if (
            self._medically_relevant_count >= _METADATA_SEGMENT_THRESHOLD
            and not self._metadata_extracted
            and (self._metadata_task is None or self._metadata_task.done())
        ):
            self._metadata_extracted = True
            self._metadata_task = asyncio.create_task(self._extract_metadata())

    async def _extract_metadata(self) -> None:
        try:
            full_text = "\n".join(self.all_relevant_text)

            # Detect language and update for subsequent classification/SOAP
            try:
                detected_lang = await self.model_client.detect_language(full_text)
                self.language = detected_lang
            except Exception:
                logger.warning(
                    "Consultation %s: language detection failed",
                    self.consultation_id,
                )

            metadata = await self.model_client.extract_consultation_metadata(
                full_text
            )
            if self.on_metadata_update:
                await self.on_metadata_update(metadata)
        except Exception:
            logger.warning(
                "Consultation %s: metadata extraction failed",
                self.consultation_id,
            )

    def _schedule_soap_update(self) -> None:
        if self._soap_task is not None and not self._soap_task.done():
            return  # don't overlap SOAP generations
        self._soap_task = asyncio.create_task(self._update_soap())
        self._last_soap_time = time.monotonic()

    async def _update_soap(self) -> None:
        full_transcript = "\n".join(self.all_relevant_text)
        try:
            soap = await self.model_client.generate_soap(
                full_transcript, self.language
            )
        except Exception:
            logger.warning(
                "Consultation %s: periodic SOAP update failed",
                self.consultation_id,
            )
            return

        if self.on_soap_update:
            for section in ("subjective", "objective", "assessment", "plan"):
                if soap.get(section):
                    await self.on_soap_update(section, soap[section])
