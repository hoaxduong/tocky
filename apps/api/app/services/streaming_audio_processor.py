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

# Language-specific VAD silence durations (ms).
_VAD_SILENCE_BY_LANGUAGE: dict[str, int] = {
    "vi": 900,
    "ar-eg": 1500,
    "ar-gulf": 1500,
    "en": 1200,
    "fr": 1200,
}

# Fallback batch size: ~5 seconds of 16 kHz 16-bit mono PCM.
_FALLBACK_BATCH_SIZE = 160_000


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

        # Language detection state (decoupled from metadata extraction)
        self._language_detection_task: asyncio.Task[None] | None = None
        self._total_segment_count = 0

        # Incremental metadata tracking
        self._current_metadata: dict[str, Any] = {
            "title": "",
            "patient_identifier": None,
        }

        # ASR fallback state
        self._fallback_mode = False
        self._fallback_buffer = bytearray()

        # Cached polished transcript (invalidated when new segments arrive)
        self._polished_transcript: str | None = None
        self._polished_segment_count = 0

        # Callbacks set by the WebSocket handler
        self.on_transcript: Callable[..., Coroutine[Any, Any, None]] | None = None
        self.on_soap_update: Callable[..., Coroutine[Any, Any, None]] | None = None
        self.on_metadata_update: Callable[..., Coroutine[Any, Any, None]] | None = None

    async def start(self) -> None:
        # Use "auto" for STT so DashScope auto-detects the language.
        # self.language is still used for classification and SOAP prompts
        # until language detection updates it.
        try:
            self._session = self._streaming_stt.create_live_session(
                "auto", self._on_stt_segment
            )
            await self._session.start()
        except Exception:
            logger.warning(
                "Consultation %s: STT session failed to start, entering fallback mode",
                self.consultation_id,
            )
            self._fallback_mode = True
            self._session = None
        self._last_soap_time = time.monotonic()
        logger.info("StreamingAudioProcessor started for %s", self.consultation_id)

    async def feed_audio(self, chunk: bytes) -> None:
        self.audio_buffer.extend(chunk)

        if self._fallback_mode:
            self._fallback_buffer.extend(chunk)
            if len(self._fallback_buffer) >= _FALLBACK_BATCH_SIZE:
                await self._process_fallback_buffer()
        elif self._session is not None:
            await self._session.feed_audio(chunk)
            # Check if session has failed mid-stream
            if hasattr(self._session, "is_failed") and self._session.is_failed:
                logger.warning(
                    "Consultation %s: STT session failed mid-stream, "
                    "switching to fallback",
                    self.consultation_id,
                )
                self._fallback_mode = True
                self._session = None

        # Check if it's time for a periodic SOAP update
        elapsed = time.monotonic() - self._last_soap_time
        if elapsed >= self.soap_interval_seconds and self.all_relevant_text:
            self._schedule_soap_update()

    async def finalize(self) -> dict[str, Any]:
        # Process any remaining fallback audio
        if self._fallback_mode and self._fallback_buffer:
            await self._process_fallback_buffer()

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
        if self._language_detection_task and not self._language_detection_task.done():
            pending.append(self._language_detection_task)
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
            "review_flags": [],
        }
        if self.all_relevant_text:
            full_transcript = "\n".join(self.all_relevant_text)

            # Step 1: Polish transcript
            try:
                polished = await asyncio.wait_for(
                    self.model_client.polish_transcript(full_transcript, self.language),
                    timeout=120.0,
                )
                logger.info(
                    "Consultation %s: transcript polished",
                    self.consultation_id,
                )
            except Exception:
                logger.warning(
                    "Consultation %s: transcript polish failed, using raw",
                    self.consultation_id,
                )
                polished = full_transcript

            # Step 2: Extract entities BEFORE SOAP (for context injection)
            entities: dict = {}
            try:
                entities = await asyncio.wait_for(
                    self.model_client.extract_medical_entities(polished, self.language),
                    timeout=140.0,
                )
                result["medical_entities"] = entities
                logger.info("Consultation %s: entities extracted", self.consultation_id)
            except Exception:
                logger.exception(
                    "Consultation %s: entity extraction failed",
                    self.consultation_id,
                )

            # Step 3: Generate SOAP from polished transcript
            try:
                soap = await asyncio.wait_for(
                    self.model_client.generate_soap(polished, self.language),
                    timeout=200.0,
                )
                # Collect confidence flags before stripping internal keys
                confidence_flags = soap.pop("_confidence_flags", [])
                result.update(soap)
                logger.info("Consultation %s: SOAP generated", self.consultation_id)

                # Step 4: Auto-review the SOAP note for quality issues
                try:
                    review_flags = await asyncio.wait_for(
                        self.model_client.review_soap(polished, soap, self.language),
                        timeout=60.0,
                    )
                    all_flags = list(confidence_flags) + list(review_flags)
                    result["review_flags"] = all_flags
                    if all_flags:
                        logger.info(
                            "Consultation %s: SOAP review found %d flags",
                            self.consultation_id,
                            len(all_flags),
                        )
                except Exception:
                    logger.warning(
                        "Consultation %s: SOAP auto-review failed",
                        self.consultation_id,
                    )
                    result["review_flags"] = list(confidence_flags)
            except Exception:
                logger.exception(
                    "Consultation %s: SOAP generation failed",
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

        # Classify medical relevance with context from recent segments
        is_relevant = True
        try:
            # Build context from last 3 segments for better classification
            context_parts: list[str] = []
            for seg in self.transcript_segments[-3:]:
                context_parts.append(f"[Previous] {seg['text']}")
            if context_parts:
                classify_text = "\n".join(context_parts) + f"\n[Current] {text}"
            else:
                classify_text = text

            if stt_segment.emotion and stt_segment.emotion != "neutral":
                classify_text = (
                    f"[Speaker emotion: {stt_segment.emotion}] {classify_text}"
                )
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

        self._total_segment_count += 1

        # Trigger language detection on first segment and every 10th segment
        should_detect_language = (
            self._total_segment_count == 1 or self._total_segment_count % 10 == 0
        ) and (
            self._language_detection_task is None
            or self._language_detection_task.done()
        )
        if should_detect_language:
            self._language_detection_task = asyncio.create_task(
                self._detect_language_standalone()
            )

        # Trigger metadata extraction after enough relevant segments
        if (
            self._medically_relevant_count >= _METADATA_SEGMENT_THRESHOLD
            and not self._metadata_extracted
            and (self._metadata_task is None or self._metadata_task.done())
        ):
            self._metadata_extracted = True
            self._metadata_task = asyncio.create_task(self._extract_metadata())

    async def _detect_language_standalone(self) -> None:
        """Detect language from recent segments, independently of metadata."""
        try:
            recent_texts = [seg["text"] for seg in self.transcript_segments[-10:]]
            all_text = "\n".join(recent_texts)
            if not all_text.strip():
                return

            detected_lang = await self.model_client.detect_language(all_text)
            if detected_lang != self.language:
                logger.info(
                    "Consultation %s: language changed %s -> %s",
                    self.consultation_id,
                    self.language,
                    detected_lang,
                )
                self.language = detected_lang

                # Update VAD params for the detected language
                new_vad_ms = _VAD_SILENCE_BY_LANGUAGE.get(detected_lang, 1200)
                if self._session and hasattr(self._session, "update_vad_params"):
                    await self._session.update_vad_params(new_vad_ms)

                # Notify frontend of language change
                if self.on_metadata_update:
                    await self.on_metadata_update(
                        {**self._current_metadata, "language": detected_lang}
                    )
        except Exception:
            logger.warning(
                "Consultation %s: standalone language detection failed",
                self.consultation_id,
            )

    async def _extract_metadata(self) -> None:
        """Extract consultation title and patient identifier."""
        try:
            full_text = "\n".join(self.all_relevant_text)
            metadata = await self.model_client.extract_consultation_metadata(full_text)
            # Merge: prefer non-empty new values
            for key in ("title", "patient_identifier"):
                if metadata.get(key):
                    self._current_metadata[key] = metadata[key]

            if self.on_metadata_update:
                await self.on_metadata_update(self._current_metadata)
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

        # Polish transcript (use cache if segment count hasn't changed)
        current_count = len(self.all_relevant_text)
        if self._polished_transcript and self._polished_segment_count == current_count:
            polished = self._polished_transcript
        else:
            try:
                polished = await self.model_client.polish_transcript(
                    full_transcript, self.language
                )
                self._polished_transcript = polished
                self._polished_segment_count = current_count
            except Exception:
                logger.warning(
                    "Consultation %s: transcript polish failed, using raw",
                    self.consultation_id,
                )
                polished = full_transcript

        try:
            soap = await self.model_client.generate_soap(polished, self.language)
            # Remove internal parsing keys before emitting
            soap.pop("_confidence_flags", None)
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

        # Re-extract metadata with accumulated transcript
        if self._metadata_extracted:
            try:
                await self._extract_metadata()
            except Exception:
                logger.warning(
                    "Consultation %s: metadata re-extraction failed",
                    self.consultation_id,
                )

    async def _process_fallback_buffer(self) -> None:
        """Transcribe buffered audio using the batch Omni model (fallback)."""
        audio_to_process = bytes(self._fallback_buffer)
        self._fallback_buffer.clear()
        try:
            text = await self.model_client.transcribe_audio(
                audio_to_process, self.language
            )
            if text.strip():
                segment = STTSegment(
                    text=text.strip(),
                    timestamp_start_ms=0,
                    timestamp_end_ms=0,
                    emotion=None,
                )
                await self._on_stt_segment(segment)
        except Exception:
            logger.warning(
                "Consultation %s: fallback transcription failed",
                self.consultation_id,
            )
