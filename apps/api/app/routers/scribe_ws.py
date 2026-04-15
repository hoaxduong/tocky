import asyncio
import base64
import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app import database
from app.config import get_settings
from app.db_models.consultation import Consultation
from app.db_models.soap_note import SOAPNote
from app.db_models.transcript import STATUS_CLASSIFIED, Transcript
from app.models.ws_messages import (
    ErrorMessage,
    MetadataUpdateMessage,
    SOAPUpdateMessage,
    StatusMessage,
    TranscriptMessage,
)
from app.services.audio_stitcher import _wrap_pcm_as_wav
from app.services.streaming_audio_processor import StreamingAudioProcessor

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scribe"])


@router.websocket("/ws/scribe/{consultation_id}")
async def scribe_websocket(
    websocket: WebSocket,
    consultation_id: uuid.UUID,
    token: str = "",
):
    # Validate JWT from query param or cookie
    access_token = token or websocket.cookies.get("tocky_access", "")
    if not access_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        from app.services.auth import decode_access_token

        payload = decode_access_token(access_token)
        user_id = payload.get("sub")
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    # Verify consultation ownership
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
            await websocket.send_json(
                ErrorMessage(
                    message="Consultation not found", code="NOT_FOUND"
                ).model_dump()
            )
            await websocket.close()
            return

        language = consultation.language

    # Set up streaming audio processor
    settings = get_settings()
    dashscope_client = websocket.app.state.dashscope_client
    streaming_stt = websocket.app.state.streaming_stt
    processor = StreamingAudioProcessor(
        consultation_id=consultation_id,
        language=language,
        model_client=dashscope_client,
        streaming_stt=streaming_stt,
        soap_interval_seconds=settings.soap_update_interval_seconds,
    )

    async def on_transcript(segment: dict) -> None:
        await websocket.send_json(
            TranscriptMessage(
                text=segment["text"],
                is_medically_relevant=segment["is_medically_relevant"],
                speaker_label=segment["speaker_label"],
                sequence=segment["sequence"],
                emotion=segment.get("emotion"),
                timestamp_start_ms=segment.get("timestamp_start_ms", 0),
                timestamp_end_ms=segment.get("timestamp_end_ms", 0),
            ).model_dump()
        )

    async def on_soap_update(section: str, content: str) -> None:
        msg = SOAPUpdateMessage.model_construct(
            type="soap_update", section=section, content=content
        )
        await websocket.send_json(msg.model_dump())

    async def on_metadata_update(metadata: dict) -> None:
        nonlocal language
        detected_lang = processor.language
        assert database.async_session_factory is not None
        async with database.async_session_factory() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == consultation_id)
            )
            c = result.scalar_one()
            if metadata.get("title"):
                c.title = metadata["title"]
            if metadata.get("patient_identifier"):
                c.patient_identifier = metadata["patient_identifier"]
            if detected_lang:
                c.language = detected_lang
                language = detected_lang
            await db.commit()
        await websocket.send_json(
            MetadataUpdateMessage(
                title=metadata.get("title", ""),
                patient_identifier=metadata.get("patient_identifier"),
                language=detected_lang,
            ).model_dump()
        )

    processor.on_transcript = on_transcript
    processor.on_soap_update = on_soap_update
    processor.on_metadata_update = on_metadata_update

    await websocket.send_json(StatusMessage(status="ready").model_dump())

    persisted = False

    async def _finalize_and_persist() -> dict:
        """Finalize processor, persist all data to DB + storage."""
        nonlocal persisted
        if persisted:
            return {}

        try:
            soap_data = await processor.finalize()
        except Exception:
            logger.exception("Consultation %s: finalize failed", consultation_id)
            soap_data = {
                "subjective": "",
                "objective": "",
                "assessment": "",
                "plan": "",
                "medical_entities": {},
            }

        # Persist transcripts + SOAP + status
        assert database.async_session_factory is not None
        async with database.async_session_factory() as db:
            for seg in processor.transcript_segments:
                db.add(
                    Transcript(
                        consultation_id=consultation_id,
                        sequence_number=seg["sequence"],
                        text=seg["text"],
                        language=language,
                        is_medically_relevant=seg["is_medically_relevant"],
                        status=STATUS_CLASSIFIED,
                        speaker_label=seg["speaker_label"],
                        emotion=seg.get("emotion"),
                        timestamp_start_ms=seg["timestamp_start_ms"],
                        timestamp_end_ms=seg["timestamp_end_ms"],
                    )
                )

            icd10_codes: list[dict] = []
            entities = soap_data.get("medical_entities", {})
            if isinstance(entities, dict) and entities.get("diagnoses"):
                try:
                    from app.services.icd10_suggester import suggest_codes

                    icd10_codes = await suggest_codes(
                        entities,
                        str(soap_data.get("assessment", "")),
                        dashscope_client,
                        db,
                        language=language,
                    )
                except Exception:
                    pass

            review_flags = soap_data.get("review_flags", [])
            soap_note = SOAPNote(
                consultation_id=consultation_id,
                subjective=soap_data.get("subjective", ""),
                objective=soap_data.get("objective", ""),
                assessment=soap_data.get("assessment", ""),
                plan=soap_data.get("plan", ""),
                medical_entities=entities if isinstance(entities, dict) else {},
                icd10_codes=icd10_codes,
                review_flags=review_flags if isinstance(review_flags, list) else [],
            )
            db.add(soap_note)
            await db.flush()

            from app.services.soap_versioning import archive_initial_version

            await archive_initial_version(db, soap_note)

            result = await db.execute(
                select(Consultation).where(Consultation.id == consultation_id)
            )
            c = result.scalar_one()
            c.status = "completed"
            c.ended_at = datetime.now(UTC)
            await db.commit()

        logger.info("Consultation %s: data persisted to DB", consultation_id)

        # Persist audio to storage
        try:
            await _persist_audio(websocket, consultation_id, processor.audio_buffer)
        except Exception:
            logger.warning("Consultation %s: audio persistence failed", consultation_id)

        persisted = True
        return soap_data

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg["type"] == "audio_chunk":
                audio_bytes = base64.b64decode(msg["data"])
                await processor.feed_audio(audio_bytes)

            elif msg["type"] == "start":
                async with database.async_session_factory() as db:
                    result = await db.execute(
                        select(Consultation).where(Consultation.id == consultation_id)
                    )
                    c = result.scalar_one()
                    c.status = "recording"
                    await db.commit()

                await processor.start()
                await websocket.send_json(
                    StatusMessage(status="recording").model_dump()
                )

            elif msg["type"] == "stop":
                await websocket.send_json(
                    StatusMessage(status="processing").model_dump()
                )

                try:
                    soap_data = await _finalize_and_persist()
                except Exception:
                    logger.exception(
                        "Consultation %s: finalize/persist failed in stop handler",
                        consultation_id,
                    )
                    soap_data = {}

                # Send final SOAP sections to client
                for section in (
                    "subjective",
                    "objective",
                    "assessment",
                    "plan",
                ):
                    if soap_data.get(section):
                        try:
                            soap_msg = SOAPUpdateMessage.model_construct(
                                type="soap_update",
                                section=section,
                                content=soap_data[section],
                            )
                            await websocket.send_json(soap_msg.model_dump())
                        except Exception:
                            break

                try:
                    await websocket.send_json(
                        StatusMessage(status="completed").model_dump()
                    )
                except Exception:
                    logger.warning(
                        "Consultation %s: failed to send completed status",
                        consultation_id,
                    )
                break

    except WebSocketDisconnect:
        # Client disconnected — persist if not already done
        logger.info(
            "Consultation %s: client disconnected, saving data",
            consultation_id,
        )
        try:
            await _finalize_and_persist()
        except Exception:
            logger.exception(
                "Consultation %s: failed to save on disconnect",
                consultation_id,
            )
    except Exception as e:
        # Persist before reporting error
        try:
            await _finalize_and_persist()
        except Exception:
            logger.exception(
                "Consultation %s: failed to save on error", consultation_id
            )
        try:
            await websocket.send_json(
                ErrorMessage(message=str(e), code="INTERNAL_ERROR").model_dump()
            )
            await websocket.close()
        except Exception:
            pass


async def _persist_audio(
    websocket: WebSocket,
    consultation_id: uuid.UUID,
    audio_buffer: bytearray,
) -> None:
    """Persist recorded PCM audio to storage and update the consultation."""
    if not audio_buffer:
        return

    oss_client = getattr(websocket.app.state, "oss_client", None)
    if oss_client is None:
        return

    pcm_bytes = bytes(audio_buffer)
    sample_rate = 16000

    # Upload PCM checkpoint and WAV in parallel
    pcm_key = await asyncio.to_thread(oss_client.upload_pcm, consultation_id, pcm_bytes)
    wav_bytes = _wrap_pcm_as_wav(pcm_bytes, sample_rate)
    wav_key = await asyncio.to_thread(
        oss_client.upload_full_audio, consultation_id, wav_bytes, "wav"
    )
    # 16-bit mono: 2 bytes per sample
    duration_ms = (len(pcm_bytes) * 1000) // (sample_rate * 2)

    assert database.async_session_factory is not None
    async with database.async_session_factory() as db:
        result = await db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        c = result.scalar_one()
        c.pcm_audio_oss_key = pcm_key
        c.pcm_audio_size_bytes = len(pcm_bytes)
        c.full_audio_oss_key = wav_key
        c.full_audio_duration_ms = duration_ms
        await db.commit()

    logger.info(
        "Consultation %s: persisted %d bytes PCM (%.1fs)",
        consultation_id,
        len(pcm_bytes),
        duration_ms / 1000,
    )
