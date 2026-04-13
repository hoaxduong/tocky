from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db_models.consultation import Consultation
from app.db_models.soap_note import SOAPNote
from app.db_models.transcript import Transcript
from app.services.dashscope_client import DashScopeClient

logger = logging.getLogger(__name__)

# 16kHz, 16-bit mono = 32000 bytes/second. 5 seconds per chunk.
CHUNK_BYTES = 5 * 32000


class BatchAudioProcessor:
    def __init__(
        self,
        consultation_id: uuid.UUID,
        model_client: DashScopeClient,
        db_session_factory: async_sessionmaker[AsyncSession],
    ):
        self.consultation_id = consultation_id
        self.model_client = model_client
        self.db_session_factory = db_session_factory

    async def process(self, pcm_audio: bytes) -> None:
        try:
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

            # --- Transcribe (auto-detect language) ---
            await self._update_progress("transcribing", 0)
            segments: list[dict] = []
            for i, chunk in enumerate(chunks):
                logger.debug(
                    "Consultation %s: transcribing chunk %d/%d (%d bytes)",
                    self.consultation_id,
                    i + 1,
                    total_chunks,
                    len(chunk),
                )
                text = await self.model_client.transcribe_audio(chunk, "auto")
                logger.debug(
                    "Consultation %s: chunk %d returned %d chars: %s",
                    self.consultation_id,
                    i + 1,
                    len(text),
                    text[:200],
                )
                if text.strip():
                    segments.append(
                        {
                            "sequence": len(segments) + 1,
                            "text": text,
                            "is_medically_relevant": False,
                            "speaker_label": None,
                            "timestamp_start_ms": i * 5000,
                            "timestamp_end_ms": (i + 1) * 5000,
                        }
                    )
                progress = int(((i + 1) / total_chunks) * 45)  # 0-45%
                await self._update_progress("transcribing", progress)

            logger.info(
                "Consultation %s: transcription done, %d segments from %d chunks",
                self.consultation_id,
                len(segments),
                total_chunks,
            )

            full_transcript = "\n".join(seg["text"] for seg in segments)

            # --- Detect language & extract metadata ---
            await self._update_progress("detecting", 45)
            if full_transcript.strip():
                detected_lang = await self.model_client.detect_language(full_transcript)
                metadata = await self.model_client.extract_consultation_metadata(
                    full_transcript
                )
            else:
                detected_lang = "en"
                metadata = {"title": "", "patient_identifier": None}

            logger.debug(
                "Consultation %s: detected language=%s, title=%s",
                self.consultation_id,
                detected_lang,
                metadata.get("title", ""),
            )

            # Update consultation with detected info
            await self._update_consultation_metadata(
                language=detected_lang,
                title=metadata.get("title", ""),
                patient_identifier=metadata.get("patient_identifier"),
            )

            # --- Classify relevance ---
            await self._update_progress("classifying", 50)
            relevant_texts: list[str] = []
            total_segs = len(segments)
            for i, seg in enumerate(segments):
                logger.debug(
                    "Consultation %s: classifying segment %d/%d",
                    self.consultation_id,
                    i + 1,
                    total_segs,
                )
                is_relevant = await self.model_client.classify_relevance(
                    seg["text"], detected_lang
                )
                seg["is_medically_relevant"] = is_relevant
                if is_relevant:
                    relevant_texts.append(seg["text"])
                logger.debug(
                    "Consultation %s: segment %d → %s",
                    self.consultation_id,
                    i + 1,
                    "RELEVANT" if is_relevant else "IRRELEVANT",
                )
                progress = 50 + int(((i + 1) / max(total_segs, 1)) * 15)  # 50-65%
                await self._update_progress("classifying", progress)
            logger.info(
                "Consultation %s: classification done, %d/%d relevant",
                self.consultation_id,
                len(relevant_texts),
                total_segs,
            )

            # --- Persist transcripts ---
            logger.debug(
                "Consultation %s: persisting %d transcript segments",
                self.consultation_id,
                len(segments),
            )
            async with self.db_session_factory() as db:
                for seg in segments:
                    db.add(
                        Transcript(
                            consultation_id=self.consultation_id,
                            sequence_number=seg["sequence"],
                            text=seg["text"],
                            language=detected_lang,
                            is_medically_relevant=seg["is_medically_relevant"],
                            speaker_label=seg["speaker_label"],
                            timestamp_start_ms=seg["timestamp_start_ms"],
                            timestamp_end_ms=seg["timestamp_end_ms"],
                        )
                    )
                await db.commit()

            # --- Generate SOAP ---
            await self._update_progress("generating_soap", 65)
            full_relevant = "\n".join(relevant_texts)
            if full_relevant.strip():
                soap = await self.model_client.generate_soap(
                    full_relevant, detected_lang
                )
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

            await self._update_progress("extracting_entities", 85)

            # --- Persist SOAP note ---
            async with self.db_session_factory() as db:
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

            # --- Mark complete ---
            await self._update_status("completed", None, 100)
            logger.info("Consultation %s: processing complete", self.consultation_id)

        except Exception as e:
            logger.exception("Consultation %s: processing failed", self.consultation_id)
            await self._update_status("failed", str(e)[:1000], None)

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

    async def _update_status(
        self,
        status: str,
        error_message: str | None,
        progress: int | None,
    ) -> None:
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
