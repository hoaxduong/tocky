import logging
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.db_models.consultation import Consultation
from app.db_models.soap_note import SOAPNote
from app.db_models.transcript import Transcript
from app.dependencies import CurrentUserDep, DbSessionDep
from app.models.soap_note import SOAPNoteResponse, SOAPNoteUpdate
from app.services.audio_stitcher import AudioStitcher

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/consultations/{consultation_id}/soap-note",
    tags=["soap-notes"],
)


@router.get("/", response_model=SOAPNoteResponse)
async def get_soap_note(
    consultation_id: uuid.UUID,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    soap = await _get_soap_note(db, consultation_id, user["id"])
    return SOAPNoteResponse.model_validate(soap)


@router.put("/", response_model=SOAPNoteResponse)
async def update_soap_note(
    consultation_id: uuid.UUID,
    body: SOAPNoteUpdate,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    soap = await _get_soap_note(db, consultation_id, user["id"])
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(soap, key, value)
    soap.version += 1
    await db.commit()
    await db.refresh(soap)
    return SOAPNoteResponse.model_validate(soap)


@router.post("/finalize", response_model=SOAPNoteResponse)
async def finalize_soap_note(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_consultation(db, consultation_id, user["id"])
    soap = await _get_soap_note_row(db, consultation_id)

    transcript_text = await _build_transcript_text(db, consultation_id)

    flags: list[dict] = []
    if transcript_text:
        try:
            flags = await request.app.state.dashscope_client.review_soap(
                transcript_text,
                {
                    "subjective": soap.subjective,
                    "objective": soap.objective,
                    "assessment": soap.assessment,
                    "plan": soap.plan,
                },
                consultation.language,
            )
        except Exception:
            logger.exception("SOAP reviewer call failed; proceeding without flags")

    if consultation.full_audio_oss_key is None:
        try:
            stitcher = AudioStitcher(request.app.state.oss_client)
            stitched = await stitcher.stitch_consultation(db, consultation_id)
            if stitched is not None:
                consultation.full_audio_oss_key, consultation.full_audio_duration_ms = (
                    stitched
                )
        except Exception:
            logger.exception("Audio stitching failed; finalizing without audio")

    soap.review_flags = flags
    soap.is_draft = False
    soap.version += 1
    await db.commit()
    await db.refresh(soap)
    return SOAPNoteResponse.model_validate(soap)


@router.get("/audio")
async def get_consultation_audio_url(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_consultation(db, consultation_id, user["id"])
    if consultation.full_audio_oss_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stitched audio available; finalize the SOAP note first.",
        )
    url = request.app.state.oss_client.get_audio_url(
        consultation.full_audio_oss_key, expires=3600
    )
    return {
        "url": url,
        "duration_ms": consultation.full_audio_duration_ms,
    }


async def _get_consultation(
    db, consultation_id: uuid.UUID, user_id: str
) -> Consultation:
    result = await db.execute(
        select(Consultation).where(
            Consultation.id == consultation_id,
            Consultation.user_id == user_id,
        )
    )
    consultation = result.scalar_one_or_none()
    if consultation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation {consultation_id} not found",
        )
    return consultation


async def _get_soap_note_row(db, consultation_id: uuid.UUID) -> SOAPNote:
    result = await db.execute(
        select(SOAPNote).where(SOAPNote.consultation_id == consultation_id)
    )
    soap = result.scalar_one_or_none()
    if soap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SOAP note not yet generated for this consultation",
        )
    return soap


async def _get_soap_note(db, consultation_id: uuid.UUID, user_id: str) -> SOAPNote:
    await _get_consultation(db, consultation_id, user_id)
    return await _get_soap_note_row(db, consultation_id)


async def _build_transcript_text(db, consultation_id: uuid.UUID) -> str:
    result = await db.execute(
        select(Transcript)
        .where(
            Transcript.consultation_id == consultation_id,
            Transcript.is_medically_relevant.is_(True),
        )
        .order_by(Transcript.sequence_number.asc())
    )
    segments = result.scalars().all()
    lines: list[str] = []
    for seg in segments:
        speaker = f"{seg.speaker_label}: " if seg.speaker_label else ""
        lines.append(f"{speaker}{seg.text}")
    return "\n".join(lines)
