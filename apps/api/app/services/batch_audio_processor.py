from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db_models.consultation import Consultation
from app.db_models.soap_note import SOAPNote
from app.db_models.transcript import Transcript
from app.services.dashscope_client import DashScopeClient
from app.services.event_bus import event_bus
from app.services.oss_client import OSSClient

logger = logging.getLogger(__name__)

# 16kHz, 16-bit mono = 32000 bytes/second. 5 seconds per chunk.
CHUNK_BYTES = 5 * 32000
CHUNK_DURATION_MS = 5000


class BatchAudioProcessor:
    """Checkpointed batch transcription pipeline.

    Each chunk's transcribe+classify+persist cycle runs as a unit, so a failure
    mid-run is resumable from the last fully-persisted chunk without
    re-transcribing the ones already stored.
    """

    def __init__(
        self,
        consultation_id: uuid.UUID,
        model_client: DashScopeClient,
        db_session_factory: async_sessionmaker[AsyncSession],
        oss_client: OSSClient,
    ):
        self.consultation_id = consultation_id
        self.model_client = model_client
        self.db_session_factory = db_session_factory
        self.oss_client = oss_client

    # --- Public entry points ---

    async def start(self, pcm_audio: bytes) -> None:
        """Start a fresh transcription run for the given PCM audio."""
        # Persist the converted PCM so a failed run can resume without the
        # original upload round-tripping through the client again.
        oss_key = await asyncio.to_thread(
            self.oss_client.upload_pcm, self.consultation_id, pcm_audio
        )
        total_chunks = max(1, (len(pcm_audio) + CHUNK_BYTES - 1) // CHUNK_BYTES)
        async with self.db_session_factory() as db:
            c = await self._load(db)
            c.pcm_audio_oss_key = oss_key
            c.pcm_audio_size_bytes = len(pcm_audio)
            c.chunks_total = total_chunks
            c.chunks_completed = 0
            c.soap_generated = False
            c.status = "processing"
            c.processing_step = "transcribing"
            c.processing_progress = 0
            c.error_message = None
            await db.commit()
        await self._publish_status("processing", step="transcribing", progress=0)
        await self._run(pcm_audio)

    async def resume(self) -> None:
        """Resume a previously-failed run from the last checkpoint."""
        async with self.db_session_factory() as db:
            c = await self._load(db)
            if c.pcm_audio_oss_key is None:
                raise RuntimeError(
                    "Cannot resume: PCM audio has not been persisted yet"
                )
            oss_key = c.pcm_audio_oss_key
            c.status = "processing"
            c.error_message = None
            await db.commit()
        pcm_audio = await asyncio.to_thread(self.oss_client.download_object, oss_key)
        await self._publish_status("processing", step="transcribing")
        await self._run(pcm_audio)

    # --- Core pipeline ---

    async def _run(self, pcm_audio: bytes) -> None:
        try:
            chunks = self._split(pcm_audio)
            total_chunks = len(chunks)
            logger.info(
                "Consultation %s: run starting (%d bytes PCM, %d chunks)",
                self.consultation_id,
                len(pcm_audio),
                total_chunks,
            )

            existing_seqs = await self._existing_chunk_sequences()
            logger.info(
                "Consultation %s: resuming with %d/%d chunks already persisted",
                self.consultation_id,
                len(existing_seqs),
                total_chunks,
            )

            # --- Transcribe + classify + persist per chunk ---
            await self._update_step(
                "transcribing", self._progress_pct(len(existing_seqs), total_chunks)
            )
            for i in range(total_chunks):
                seq = i + 1  # sequence_number is 1-indexed
                if seq in existing_seqs:
                    continue
                chunk = chunks[i]
                try:
                    text = await self.model_client.transcribe_audio(chunk, "auto")
                except Exception:
                    logger.exception(
                        "Consultation %s: transcription failed for chunk %d/%d",
                        self.consultation_id,
                        seq,
                        total_chunks,
                    )
                    raise
                text = text.strip()

                # Skip silent/empty chunks but still count them toward progress.
                if not text:
                    await self._record_chunk_progress(seq, total_chunks)
                    continue

                # Classify relevance (auto language — will be refined later)
                try:
                    is_relevant = await self.model_client.classify_relevance(
                        text, "auto"
                    )
                except Exception:
                    logger.warning(
                        "Consultation %s: classify failed for chunk %d; "
                        "defaulting to irrelevant",
                        self.consultation_id,
                        seq,
                    )
                    is_relevant = False

                await self._persist_chunk(
                    seq=seq,
                    text=text,
                    language="auto",
                    is_medically_relevant=is_relevant,
                    timestamp_start_ms=i * CHUNK_DURATION_MS,
                    timestamp_end_ms=(i + 1) * CHUNK_DURATION_MS,
                )
                await self._record_chunk_progress(seq, total_chunks)

            # All chunks persisted. Continue to metadata + SOAP.
            segments = await self._load_segments()
            full_transcript = "\n".join(s["text"] for s in segments)

            # --- Detect language & extract metadata (idempotent) ---
            await self._update_step("detecting", 60)
            if full_transcript.strip():
                detected_lang = await self.model_client.detect_language(full_transcript)
                metadata = await self.model_client.extract_consultation_metadata(
                    full_transcript
                )
            else:
                detected_lang = "en"
                metadata = {"title": "", "patient_identifier": None}

            await self._update_consultation_metadata(
                language=detected_lang,
                title=str(metadata.get("title") or ""),
                patient_identifier=metadata.get("patient_identifier"),
            )

            # Back-fill per-transcript language now that detection ran
            await self._backfill_transcript_language(detected_lang)

            # --- Generate SOAP if we haven't already ---
            await self._update_step("generating_soap", 75)
            relevant_texts = [s["text"] for s in segments if s["is_medically_relevant"]]

            soap_already_done = await self._soap_already_generated()
            if not soap_already_done:
                if relevant_texts:
                    full_relevant = "\n".join(relevant_texts)
                    soap = await self.model_client.generate_soap(
                        full_relevant, detected_lang
                    )
                    await self._update_step("extracting_entities", 90)
                    entities = await self.model_client.extract_medical_entities(
                        full_relevant, detected_lang
                    )
                else:
                    soap = {
                        "subjective": "",
                        "objective": "",
                        "assessment": "",
                        "plan": "",
                    }
                    entities = {}

                await self._persist_soap(soap, entities)

            # --- Done ---
            await self._mark_complete()
            logger.info("Consultation %s: processing complete", self.consultation_id)
        except Exception as e:
            logger.exception("Consultation %s: processing failed", self.consultation_id)
            await self._mark_failed(str(e)[:1000])

    # --- Helpers ---

    @staticmethod
    def _split(pcm_audio: bytes) -> list[bytes]:
        return [
            pcm_audio[i : i + CHUNK_BYTES]
            for i in range(0, len(pcm_audio), CHUNK_BYTES)
        ] or [b""]

    @staticmethod
    def _progress_pct(done: int, total: int) -> int:
        # Chunks occupy 0-60% of the overall progress bar.
        if total == 0:
            return 0
        return min(60, int(done / total * 60))

    async def _load(self, db: AsyncSession) -> Consultation:
        result = await db.execute(
            select(Consultation).where(Consultation.id == self.consultation_id)
        )
        return result.scalar_one()

    async def _existing_chunk_sequences(self) -> set[int]:
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Transcript.sequence_number).where(
                    Transcript.consultation_id == self.consultation_id
                )
            )
            return set(result.scalars().all())

    async def _persist_chunk(
        self,
        *,
        seq: int,
        text: str,
        language: str,
        is_medically_relevant: bool,
        timestamp_start_ms: int,
        timestamp_end_ms: int,
    ) -> None:
        async with self.db_session_factory() as db:
            db.add(
                Transcript(
                    consultation_id=self.consultation_id,
                    sequence_number=seq,
                    text=text,
                    language=language,
                    is_medically_relevant=is_medically_relevant,
                    speaker_label=None,
                    timestamp_start_ms=timestamp_start_ms,
                    timestamp_end_ms=timestamp_end_ms,
                )
            )
            await db.commit()

    async def _record_chunk_progress(self, seq: int, total: int) -> None:
        async with self.db_session_factory() as db:
            c = await self._load(db)
            c.chunks_completed = max(c.chunks_completed, seq)
            c.processing_progress = self._progress_pct(c.chunks_completed, total)
            await db.commit()
            progress = c.processing_progress
            completed = c.chunks_completed
        await event_bus.publish(
            self.consultation_id,
            {
                "type": "progress",
                "step": "transcribing",
                "progress": progress,
                "chunks_completed": completed,
                "chunks_total": total,
                "latest_sequence": seq,
            },
        )

    async def _load_segments(self) -> list[dict[str, Any]]:
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Transcript)
                .where(Transcript.consultation_id == self.consultation_id)
                .order_by(Transcript.sequence_number.asc())
            )
            rows = result.scalars().all()
            return [
                {
                    "sequence": r.sequence_number,
                    "text": r.text,
                    "is_medically_relevant": r.is_medically_relevant,
                }
                for r in rows
            ]

    async def _update_step(self, step: str, progress: int) -> None:
        async with self.db_session_factory() as db:
            c = await self._load(db)
            c.processing_step = step
            c.processing_progress = progress
            await db.commit()
        await event_bus.publish(
            self.consultation_id,
            {"type": "progress", "step": step, "progress": progress},
        )

    async def _update_consultation_metadata(
        self,
        language: str,
        title: str,
        patient_identifier: str | None,
    ) -> None:
        async with self.db_session_factory() as db:
            c = await self._load(db)
            c.language = language
            if title:
                c.title = title
            if patient_identifier:
                c.patient_identifier = patient_identifier
            await db.commit()

    async def _backfill_transcript_language(self, language: str) -> None:
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Transcript).where(
                    Transcript.consultation_id == self.consultation_id,
                    Transcript.language == "auto",
                )
            )
            for row in result.scalars().all():
                row.language = language
            await db.commit()

    async def _soap_already_generated(self) -> bool:
        async with self.db_session_factory() as db:
            c = await self._load(db)
            return c.soap_generated

    async def _persist_soap(
        self,
        soap: dict[str, str],
        entities: dict[str, Any],
    ) -> None:
        async with self.db_session_factory() as db:
            # Upsert semantics: a retry shouldn't create a duplicate row.
            result = await db.execute(
                select(SOAPNote).where(SOAPNote.consultation_id == self.consultation_id)
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                existing.subjective = soap.get("subjective", "")
                existing.objective = soap.get("objective", "")
                existing.assessment = soap.get("assessment", "")
                existing.plan = soap.get("plan", "")
                existing.medical_entities = entities
            else:
                db.add(
                    SOAPNote(
                        consultation_id=self.consultation_id,
                        subjective=soap.get("subjective", ""),
                        objective=soap.get("objective", ""),
                        assessment=soap.get("assessment", ""),
                        plan=soap.get("plan", ""),
                        medical_entities=entities,
                    )
                )
            c = await self._load(db)
            c.soap_generated = True
            await db.commit()

    async def _mark_complete(self) -> None:
        async with self.db_session_factory() as db:
            c = await self._load(db)
            c.status = "completed"
            c.processing_step = None
            c.processing_progress = 100
            c.error_message = None
            await db.commit()
        await self._publish_status("completed", progress=100)

    async def _mark_failed(self, message: str) -> None:
        async with self.db_session_factory() as db:
            c = await self._load(db)
            c.status = "failed"
            c.error_message = message
            await db.commit()
            progress = c.processing_progress
            step = c.processing_step
        await self._publish_status(
            "failed", step=step, progress=progress, error=message
        )

    async def _publish_status(
        self,
        status: str,
        *,
        step: str | None = None,
        progress: int | None = None,
        error: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"type": "status", "status": status}
        if step is not None:
            payload["step"] = step
        if progress is not None:
            payload["progress"] = progress
        if error is not None:
            payload["error"] = error
        await event_bus.publish(self.consultation_id, payload)
