import base64
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_factory
from app.db_models.consultation import Consultation
from app.db_models.soap_note import SOAPNote
from app.db_models.transcript import Transcript
from app.models.ws_messages import (
    ErrorMessage,
    SOAPUpdateMessage,
    StatusMessage,
    TranscriptMessage,
)
from app.services.audio_processor import AudioProcessor

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
    assert async_session_factory is not None
    async with async_session_factory() as db:
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

    # Set up audio processor
    settings = get_settings()
    dashscope_client = websocket.app.state.dashscope_client
    processor = AudioProcessor(
        consultation_id=consultation_id,
        language=language,
        model_client=dashscope_client,
        buffer_seconds=settings.audio_buffer_seconds,
        soap_interval_seconds=settings.soap_update_interval_seconds,
    )

    async def on_transcript(segment: dict) -> None:
        await websocket.send_json(
            TranscriptMessage(
                text=segment["text"],
                is_medically_relevant=segment["is_medically_relevant"],
                speaker_label=segment["speaker_label"],
                sequence=segment["sequence"],
            ).model_dump()
        )

    async def on_soap_update(section: str, content: str) -> None:
        await websocket.send_json(
            SOAPUpdateMessage(section=section, content=content).model_dump()
        )

    processor.on_transcript = on_transcript
    processor.on_soap_update = on_soap_update

    await websocket.send_json(StatusMessage(status="ready").model_dump())

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg["type"] == "audio_chunk":
                audio_bytes = base64.b64decode(msg["data"])
                await processor.add_audio_chunk(audio_bytes, msg["timestamp_ms"])

            elif msg["type"] == "start":
                async with async_session_factory() as db:
                    result = await db.execute(
                        select(Consultation).where(Consultation.id == consultation_id)
                    )
                    c = result.scalar_one()
                    c.status = "recording"
                    await db.commit()

                await websocket.send_json(
                    StatusMessage(status="recording").model_dump()
                )

            elif msg["type"] == "stop":
                await websocket.send_json(
                    StatusMessage(status="processing").model_dump()
                )

                soap_data = await processor.finalize()

                # Persist transcript segments
                async with async_session_factory() as db:
                    for seg in processor.transcript_segments:
                        db.add(
                            Transcript(
                                consultation_id=consultation_id,
                                sequence_number=seg["sequence"],
                                text=seg["text"],
                                language=language,
                                is_medically_relevant=seg["is_medically_relevant"],
                                speaker_label=seg["speaker_label"],
                                timestamp_start_ms=seg["timestamp_start_ms"],
                                timestamp_end_ms=seg["timestamp_end_ms"],
                            )
                        )

                    # Auto-suggest ICD-10 codes from clinical context
                    icd10_codes: list[dict] = []
                    entities = soap_data.get("medical_entities", {})
                    if entities.get("diagnoses"):
                        try:
                            from app.services.icd10_suggester import suggest_codes

                            icd10_codes = await suggest_codes(
                                entities,
                                soap_data.get("assessment", ""),
                                dashscope_client,
                                db,
                                language=language,
                            )
                        except Exception:
                            pass  # non-critical, proceed without codes

                    # Persist SOAP note
                    db.add(
                        SOAPNote(
                            consultation_id=consultation_id,
                            subjective=soap_data.get("subjective", ""),
                            objective=soap_data.get("objective", ""),
                            assessment=soap_data.get("assessment", ""),
                            plan=soap_data.get("plan", ""),
                            medical_entities=entities,
                            icd10_codes=icd10_codes,
                        )
                    )

                    # Update consultation status
                    result = await db.execute(
                        select(Consultation).where(Consultation.id == consultation_id)
                    )
                    c = result.scalar_one()
                    c.status = "completed"
                    await db.commit()

                # Send final SOAP sections
                for section in (
                    "subjective",
                    "objective",
                    "assessment",
                    "plan",
                ):
                    if soap_data.get(section):
                        await websocket.send_json(
                            SOAPUpdateMessage(
                                section=section, content=soap_data[section]
                            ).model_dump()
                        )

                await websocket.send_json(
                    StatusMessage(status="completed").model_dump()
                )
                break

    except WebSocketDisconnect:
        # Client disconnected - try to save what we have
        soap_data = await processor.finalize()
        async with async_session_factory() as db:
            for seg in processor.transcript_segments:
                db.add(
                    Transcript(
                        consultation_id=consultation_id,
                        sequence_number=seg["sequence"],
                        text=seg["text"],
                        language=language,
                        is_medically_relevant=seg["is_medically_relevant"],
                        speaker_label=seg["speaker_label"],
                        timestamp_start_ms=seg["timestamp_start_ms"],
                        timestamp_end_ms=seg["timestamp_end_ms"],
                    )
                )
            sections = ("subjective", "objective", "assessment", "plan")
            if any(soap_data.get(s) for s in sections):
                # Auto-suggest ICD-10 codes
                disconnect_icd10: list[dict] = []
                disconnect_entities = soap_data.get("medical_entities", {})
                if disconnect_entities.get("diagnoses"):
                    try:
                        from app.services.icd10_suggester import suggest_codes

                        disconnect_icd10 = await suggest_codes(
                            disconnect_entities,
                            soap_data.get("assessment", ""),
                            dashscope_client,
                            db,
                        )
                    except Exception:
                        pass

                db.add(
                    SOAPNote(
                        consultation_id=consultation_id,
                        subjective=soap_data.get("subjective", ""),
                        objective=soap_data.get("objective", ""),
                        assessment=soap_data.get("assessment", ""),
                        plan=soap_data.get("plan", ""),
                        medical_entities=disconnect_entities,
                        icd10_codes=disconnect_icd10,
                    )
                )
            result = await db.execute(
                select(Consultation).where(Consultation.id == consultation_id)
            )
            c = result.scalar_one()
            c.status = "completed"
            await db.commit()
    except Exception as e:
        await websocket.send_json(
            ErrorMessage(message=str(e), code="INTERNAL_ERROR").model_dump()
        )
        await websocket.close()
