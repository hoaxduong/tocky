from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db_models.consultation import Consultation
from app.db_models.soap_note import SOAPNote
from app.db_models.transcript import (
    STATUS_CLASSIFIED,
    STATUS_FAILED_CLASSIFICATION,
    STATUS_FAILED_TRANSCRIPTION,
    STATUS_TRANSCRIBED,
    Transcript,
)
from app.services.ai_protocol import AIClient
from app.services.event_queue import (
    EventQueueRegistry,
    ProgressEvent,
    SegmentClassifiedEvent,
    SegmentFailedEvent,
    StatusEvent,
    TranscriptSegmentEvent,
)
from app.services.oss_client import OSSClient

logger = logging.getLogger(__name__)

# 16kHz, 16-bit mono = 32000 bytes/second. 5 seconds per chunk.
CHUNK_BYTES = 5 * 32000


class BatchAudioProcessor:
    def __init__(
        self,
        consultation_id: uuid.UUID,
        model_client: AIClient,
        db_session_factory: async_sessionmaker[AsyncSession],
        event_registry: EventQueueRegistry | None = None,
        oss_client: OSSClient | None = None,
    ):
        self.consultation_id = consultation_id
        self.model_client = model_client
        self.db_session_factory = db_session_factory
        self.event_registry = event_registry
        self.oss_client = oss_client

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def process(self, pcm_audio: bytes) -> None:
        """Full pipeline: chunk → transcribe → detect → classify → SOAP."""
        try:
            # Persist PCM to OSS so a run that fails mid-transcription can
            # retry only the failed chunks without a re-upload.
            await self._persist_pcm_checkpoint(pcm_audio)

            chunks = [
                pcm_audio[i : i + CHUNK_BYTES]
                for i in range(0, len(pcm_audio), CHUNK_BYTES)
            ]
            total_chunks = len(chunks)
            logger.info(
                "Consultation %s: %d bytes PCM, %d chunks",
                self.consultation_id,
                len(pcm_audio),
                total_chunks,
            )

            # --- Transcribe (per-segment persist) ---
            await self._update_progress("transcribing", 0)
            seq = 0
            for i, chunk in enumerate(chunks):
                logger.debug(
                    "Consultation %s: transcribing chunk %d/%d (%d bytes)",
                    self.consultation_id,
                    i + 1,
                    total_chunks,
                    len(chunk),
                )
                try:
                    text = await self.model_client.transcribe_audio(chunk, "auto")
                    logger.debug(
                        "Consultation %s: chunk %d returned %d chars: %s",
                        self.consultation_id,
                        i + 1,
                        len(text),
                        text[:200],
                    )
                    if text.strip():
                        seq += 1
                        await self._persist_segment(
                            sequence=seq,
                            text=text,
                            status=STATUS_TRANSCRIBED,
                            language="pending",
                            timestamp_start_ms=i * 5000,
                            timestamp_end_ms=(i + 1) * 5000,
                        )
                        self._push(
                            TranscriptSegmentEvent(
                                data={
                                    "sequence": seq,
                                    "text": text,
                                    "timestamp_start_ms": i * 5000,
                                    "timestamp_end_ms": (i + 1) * 5000,
                                }
                            )
                        )
                except Exception as e:
                    logger.warning(
                        "Consultation %s: chunk %d transcription failed: %s",
                        self.consultation_id,
                        i + 1,
                        e,
                    )
                    seq += 1
                    await self._persist_segment(
                        sequence=seq,
                        text="",
                        status=STATUS_FAILED_TRANSCRIPTION,
                        language="pending",
                        timestamp_start_ms=i * 5000,
                        timestamp_end_ms=(i + 1) * 5000,
                        error_message=str(e)[:500],
                    )
                    self._push(
                        SegmentFailedEvent(
                            data={
                                "sequence": seq,
                                "step": "transcription",
                                "error_message": str(e)[:500],
                            }
                        )
                    )

                progress = int(((i + 1) / total_chunks) * 45)
                await self._update_progress("transcribing", progress)
                self._push(
                    ProgressEvent(data={"step": "transcribing", "progress": progress})
                )

            logger.info("Consultation %s: transcription done", self.consultation_id)

            # Continue with detection → classification → SOAP
            await self._post_transcription_pipeline()

        except Exception as e:
            logger.exception("Consultation %s: processing failed", self.consultation_id)
            await self._finish("failed", str(e)[:1000])

    async def resume(self) -> None:
        """Resume processing from where it left off.

        Re-transcribes any chunks flagged STATUS_FAILED_TRANSCRIPTION if the
        PCM checkpoint is still in OSS, then continues with the post-
        transcription pipeline. Requires transcripts to already exist.
        """
        try:
            async with self.db_session_factory() as db:
                result = await db.execute(
                    select(func.count())
                    .select_from(Transcript)
                    .where(Transcript.consultation_id == self.consultation_id)
                )
                count = result.scalar_one()

            if count == 0:
                raise ValueError(
                    "No transcripts found. Please re-upload the audio file."
                )

            await self._retry_failed_transcription_chunks()
            await self._post_transcription_pipeline()

        except Exception as e:
            logger.exception("Consultation %s: resume failed", self.consultation_id)
            await self._finish("failed", str(e)[:1000])

    async def _retry_failed_transcription_chunks(self) -> None:
        """Re-run transcription on segments flagged STATUS_FAILED_TRANSCRIPTION.

        Skips silently if the PCM checkpoint isn't in OSS (first-generation
        consultations created before the checkpoint feature).
        """
        if self.oss_client is None:
            return

        async with self.db_session_factory() as db:
            consultation = (
                await db.execute(
                    select(Consultation).where(Consultation.id == self.consultation_id)
                )
            ).scalar_one()
            pcm_key = consultation.pcm_audio_oss_key

            result = await db.execute(
                select(Transcript)
                .where(
                    Transcript.consultation_id == self.consultation_id,
                    Transcript.status == STATUS_FAILED_TRANSCRIPTION,
                )
                .order_by(Transcript.sequence_number)
            )
            failed = result.scalars().all()

        if not failed or pcm_key is None:
            return

        logger.info(
            "Consultation %s: retrying %d failed chunks from PCM checkpoint",
            self.consultation_id,
            len(failed),
        )
        try:
            pcm_audio = await asyncio.to_thread(
                self.oss_client.download_object, pcm_key
            )
        except Exception:
            logger.exception(
                "Consultation %s: failed to fetch PCM checkpoint; skipping chunk retry",
                self.consultation_id,
            )
            return

        total = len(pcm_audio)
        for seg in failed:
            # Each chunk's timestamp range maps cleanly to a PCM byte slice,
            # since we chunk on a fixed 5-second cadence.
            start = (seg.timestamp_start_ms // 5000) * CHUNK_BYTES
            end = min(start + CHUNK_BYTES, total)
            if start >= total:
                continue
            chunk = pcm_audio[start:end]
            try:
                text = await self.model_client.transcribe_audio(chunk, "auto")
            except Exception as e:
                logger.warning(
                    "Consultation %s: retry chunk %d still failing: %s",
                    self.consultation_id,
                    seg.sequence_number,
                    e,
                )
                continue

            if not text.strip():
                continue

            async with self.db_session_factory() as db:
                await db.execute(
                    update(Transcript)
                    .where(Transcript.id == seg.id)
                    .values(
                        text=text,
                        status=STATUS_TRANSCRIBED,
                        error_message=None,
                    )
                )
                await db.commit()
            self._push(
                TranscriptSegmentEvent(
                    data={
                        "sequence": seg.sequence_number,
                        "text": text,
                        "timestamp_start_ms": seg.timestamp_start_ms,
                        "timestamp_end_ms": seg.timestamp_end_ms,
                    }
                )
            )

    async def _persist_pcm_checkpoint(self, pcm_audio: bytes) -> None:
        """Upload PCM to OSS and record its key on the consultation row."""
        if self.oss_client is None:
            return
        try:
            oss_key = await asyncio.to_thread(
                self.oss_client.upload_pcm,
                self.consultation_id,
                pcm_audio,
            )
        except Exception:
            # Non-fatal: the run proceeds without checkpoint support. If it
            # later fails, resume() will simply skip the chunk retry step.
            logger.exception(
                "Consultation %s: failed to persist PCM checkpoint",
                self.consultation_id,
            )
            return
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == self.consultation_id)
            )
            c = result.scalar_one()
            c.pcm_audio_oss_key = oss_key
            c.pcm_audio_size_bytes = len(pcm_audio)
            await db.commit()

    # ------------------------------------------------------------------
    # Shared pipeline stages (used by both process() and resume())
    # ------------------------------------------------------------------

    async def _post_transcription_pipeline(self) -> None:
        """Run detection → classification → SOAP on persisted transcripts."""

        # --- Fetch transcribed segments ---
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Transcript)
                .where(
                    Transcript.consultation_id == self.consultation_id,
                    Transcript.status.in_([STATUS_TRANSCRIBED, STATUS_CLASSIFIED]),
                )
                .order_by(Transcript.sequence_number)
            )
            good_segments = result.scalars().all()

        if not good_segments:
            # Check if there are ANY segments (all failed)
            async with self.db_session_factory() as db:
                result = await db.execute(
                    select(func.count())
                    .select_from(Transcript)
                    .where(Transcript.consultation_id == self.consultation_id)
                )
                total = result.scalar_one()

            if total > 0:
                await self._finish("failed", "All audio segments failed transcription")
            else:
                await self._finish("failed", "No audio segments to process")
            return

        full_transcript = "\n".join(seg.text for seg in good_segments if seg.text)

        # --- Detect language & extract metadata (soft fail) ---
        await self._update_progress("detecting", 45)
        self._push(ProgressEvent(data={"step": "detecting", "progress": 45}))

        detected_lang = "en"
        if full_transcript.strip():
            try:
                detected_lang = await self.model_client.detect_language(full_transcript)
            except Exception:
                logger.warning(
                    "Consultation %s: language detection failed, defaulting to 'en'",
                    self.consultation_id,
                )

            metadata: dict = {"title": "", "patient_identifier": None}
            try:
                metadata = await self.model_client.extract_consultation_metadata(
                    full_transcript
                )
            except Exception:
                logger.warning(
                    "Consultation %s: metadata extraction failed",
                    self.consultation_id,
                )

            await self._update_consultation_metadata(
                language=detected_lang,
                title=metadata.get("title", ""),
                patient_identifier=metadata.get("patient_identifier"),
            )

        # Update all transcript language fields
        async with self.db_session_factory() as db:
            await db.execute(
                update(Transcript)
                .where(
                    Transcript.consultation_id == self.consultation_id,
                    Transcript.language == "pending",
                )
                .values(language=detected_lang)
            )
            await db.commit()

        # --- Classify relevance (per-segment error handling) ---
        await self._update_progress("classifying", 50)
        self._push(ProgressEvent(data={"step": "classifying", "progress": 50}))

        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Transcript)
                .where(
                    Transcript.consultation_id == self.consultation_id,
                    Transcript.status.in_(
                        [STATUS_TRANSCRIBED, STATUS_FAILED_CLASSIFICATION]
                    ),
                )
                .order_by(Transcript.sequence_number)
            )
            to_classify = result.scalars().all()

        total_segs = len(to_classify)
        for i, seg in enumerate(to_classify):
            logger.debug(
                "Consultation %s: classifying segment %d/%d",
                self.consultation_id,
                i + 1,
                total_segs,
            )
            try:
                is_relevant = await self.model_client.classify_relevance(
                    seg.text, detected_lang
                )
                async with self.db_session_factory() as db:
                    await db.execute(
                        update(Transcript)
                        .where(Transcript.id == seg.id)
                        .values(
                            status=STATUS_CLASSIFIED,
                            is_medically_relevant=is_relevant,
                            error_message=None,
                        )
                    )
                    await db.commit()
                logger.debug(
                    "Consultation %s: segment %d → %s",
                    self.consultation_id,
                    seg.sequence_number,
                    "RELEVANT" if is_relevant else "IRRELEVANT",
                )
                self._push(
                    SegmentClassifiedEvent(
                        data={
                            "sequence": seg.sequence_number,
                            "is_medically_relevant": is_relevant,
                        }
                    )
                )
            except Exception as e:
                logger.warning(
                    "Consultation %s: segment %d classification failed: %s",
                    self.consultation_id,
                    seg.sequence_number,
                    e,
                )
                async with self.db_session_factory() as db:
                    await db.execute(
                        update(Transcript)
                        .where(Transcript.id == seg.id)
                        .values(
                            status=STATUS_FAILED_CLASSIFICATION,
                            error_message=str(e)[:500],
                        )
                    )
                    await db.commit()
                self._push(
                    SegmentFailedEvent(
                        data={
                            "sequence": seg.sequence_number,
                            "step": "classification",
                            "error_message": str(e)[:500],
                        }
                    )
                )

            progress = 50 + int(((i + 1) / max(total_segs, 1)) * 15)
            await self._update_progress("classifying", progress)
            self._push(
                ProgressEvent(data={"step": "classifying", "progress": progress})
            )

        # --- Evaluate results ---
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Transcript)
                .where(
                    Transcript.consultation_id == self.consultation_id,
                    Transcript.status == STATUS_CLASSIFIED,
                    Transcript.is_medically_relevant.is_(True),
                )
                .order_by(Transcript.sequence_number)
            )
            relevant_segments = result.scalars().all()

            result = await db.execute(
                select(func.count())
                .select_from(Transcript)
                .where(
                    Transcript.consultation_id == self.consultation_id,
                    Transcript.status.in_(
                        [STATUS_FAILED_TRANSCRIPTION, STATUS_FAILED_CLASSIFICATION]
                    ),
                )
            )
            failed_count = result.scalar_one()

            result = await db.execute(
                select(func.count())
                .select_from(Transcript)
                .where(Transcript.consultation_id == self.consultation_id)
            )
            total_count = result.scalar_one()

        relevant_texts = [seg.text for seg in relevant_segments]

        logger.info(
            "Consultation %s: classification done, %d/%d relevant, %d failed",
            self.consultation_id,
            len(relevant_texts),
            total_count,
            failed_count,
        )

        # --- Generate SOAP ---
        await self._update_progress("generating_soap", 65)
        self._push(ProgressEvent(data={"step": "generating_soap", "progress": 65}))

        full_relevant = "\n".join(relevant_texts)
        if full_relevant.strip():
            try:
                soap = await self.model_client.generate_soap(
                    full_relevant, detected_lang
                )
            except Exception as e:
                logger.exception(
                    "Consultation %s: SOAP generation failed",
                    self.consultation_id,
                )
                await self._finish(
                    "completed_with_errors",
                    f"SOAP generation failed: {e!s:.500}",
                )
                return

            try:
                entities = await self.model_client.extract_medical_entities(
                    full_relevant, detected_lang
                )
            except Exception:
                logger.warning(
                    "Consultation %s: entity extraction failed, using empty",
                    self.consultation_id,
                )
                entities = {}
        else:
            soap = {
                "subjective": "",
                "objective": "",
                "assessment": "",
                "plan": "",
            }
            entities = {}

        await self._update_progress("extracting_entities", 85)
        self._push(ProgressEvent(data={"step": "extracting_entities", "progress": 85}))

        # --- Persist SOAP note ---
        async with self.db_session_factory() as db:
            # Delete existing SOAP note if retrying
            result = await db.execute(
                select(SOAPNote).where(SOAPNote.consultation_id == self.consultation_id)
            )
            existing_soap = result.scalar_one_or_none()
            if existing_soap:
                existing_soap.subjective = soap.get("subjective", "")
                existing_soap.objective = soap.get("objective", "")
                existing_soap.assessment = soap.get("assessment", "")
                existing_soap.plan = soap.get("plan", "")
                existing_soap.medical_entities = entities
                existing_soap.is_draft = True
                existing_soap.version += 1
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
            await db.commit()

        # --- Final status ---
        if failed_count > 0:
            await self._finish(
                "completed_with_errors",
                f"{failed_count} of {total_count} segments failed processing",
            )
        else:
            await self._finish("completed", None)

        logger.info("Consultation %s: processing complete", self.consultation_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _push(self, event) -> None:
        if self.event_registry:
            self.event_registry.push(self.consultation_id, event)

    async def _persist_segment(
        self,
        *,
        sequence: int,
        text: str,
        status: str,
        language: str,
        timestamp_start_ms: int,
        timestamp_end_ms: int,
        error_message: str | None = None,
    ) -> None:
        async with self.db_session_factory() as db:
            db.add(
                Transcript(
                    consultation_id=self.consultation_id,
                    sequence_number=sequence,
                    text=text,
                    language=language,
                    is_medically_relevant=False,
                    status=status,
                    error_message=error_message,
                    speaker_label=None,
                    timestamp_start_ms=timestamp_start_ms,
                    timestamp_end_ms=timestamp_end_ms,
                )
            )
            await db.commit()

    async def _update_progress(self, step: str, progress: int) -> None:
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == self.consultation_id)
            )
            c = result.scalar_one()
            c.processing_step = step
            c.processing_progress = progress
            await db.commit()

    async def _update_consultation_metadata(
        self,
        language: str,
        title: str,
        patient_identifier: str | None,
    ) -> None:
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == self.consultation_id)
            )
            c = result.scalar_one()
            c.language = language
            if title:
                c.title = title
            if patient_identifier:
                c.patient_identifier = patient_identifier
            await db.commit()

    async def _finish(self, status: str, error_message: str | None) -> None:
        progress = 100 if status in ("completed", "completed_with_errors") else None
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == self.consultation_id)
            )
            c = result.scalar_one()
            c.status = status
            c.processing_step = None
            c.error_message = error_message
            if progress is not None:
                c.processing_progress = progress
            await db.commit()

        self._push(StatusEvent(data={"status": status, "error_message": error_message}))
        if self.event_registry:
            self.event_registry.remove_topic(self.consultation_id)
