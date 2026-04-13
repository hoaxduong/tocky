from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from app.services.ai_protocol import AIClient


class AudioProcessor:
    def __init__(
        self,
        consultation_id: uuid.UUID,
        language: str,
        model_client: AIClient,
        buffer_seconds: float = 5.0,
        soap_interval_seconds: float = 30.0,
    ):
        self.consultation_id = consultation_id
        self.language = language
        self.model_client = model_client
        self.buffer_seconds = buffer_seconds
        self.soap_interval_seconds = soap_interval_seconds

        self.audio_buffer = bytearray()
        self.buffer_start_ms: int = 0
        self.transcript_segments: list[dict] = []
        self.sequence_counter = 0
        self.last_soap_time = time.monotonic()
        self.all_relevant_text: list[str] = []

        # Callbacks set by the WebSocket handler
        self.on_transcript: Callable[..., Coroutine[Any, Any, None]] | None = None
        self.on_soap_update: Callable[..., Coroutine[Any, Any, None]] | None = None

    async def add_audio_chunk(self, chunk: bytes, timestamp_ms: int) -> None:
        if not self.audio_buffer:
            self.buffer_start_ms = timestamp_ms

        self.audio_buffer.extend(chunk)

        # 16kHz, 16-bit mono = 32000 bytes/second
        bytes_threshold = int(self.buffer_seconds * 32000)
        if len(self.audio_buffer) >= bytes_threshold:
            await self._process_buffer(timestamp_ms)

    async def _process_buffer(self, current_timestamp_ms: int) -> None:
        if not self.audio_buffer:
            return

        audio_data = bytes(self.audio_buffer)
        start_ms = self.buffer_start_ms
        self.audio_buffer = bytearray()

        # Transcribe
        text = await self.model_client.transcribe_audio(audio_data, self.language)
        if not text.strip():
            return

        # Classify relevance
        is_relevant = await self.model_client.classify_relevance(text, self.language)

        self.sequence_counter += 1
        segment = {
            "text": text,
            "is_medically_relevant": is_relevant,
            "speaker_label": None,
            "sequence": self.sequence_counter,
            "timestamp_start_ms": start_ms,
            "timestamp_end_ms": current_timestamp_ms,
        }
        self.transcript_segments.append(segment)

        if is_relevant:
            self.all_relevant_text.append(text)

        if self.on_transcript:
            await self.on_transcript(segment)

        # Check if we should update SOAP
        elapsed = time.monotonic() - self.last_soap_time
        if elapsed >= self.soap_interval_seconds and self.all_relevant_text:
            await self._update_soap()
            self.last_soap_time = time.monotonic()

    async def _update_soap(self) -> None:
        full_transcript = "\n".join(self.all_relevant_text)
        soap = await self.model_client.generate_soap(full_transcript, self.language)

        if self.on_soap_update:
            for section in ("subjective", "objective", "assessment", "plan"):
                if soap.get(section):
                    await self.on_soap_update(section, soap[section])

    async def finalize(self) -> dict[str, str]:
        # Process any remaining audio in the buffer
        if self.audio_buffer:
            await self._process_buffer(
                self.buffer_start_ms + int(len(self.audio_buffer) / 32)
            )

        # Generate final SOAP note
        if self.all_relevant_text:
            full_transcript = "\n".join(self.all_relevant_text)
            soap = await self.model_client.generate_soap(full_transcript, self.language)
            entities = await self.model_client.extract_medical_entities(
                full_transcript, self.language
            )
            soap["medical_entities"] = entities
        else:
            soap = {
                "subjective": "",
                "objective": "",
                "assessment": "",
                "plan": "",
                "medical_entities": {},
            }

        return soap
