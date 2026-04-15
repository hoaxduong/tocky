import logging
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.db_models.consultation import Consultation
from app.db_models.soap_note import SOAPNote
from app.db_models.soap_note_version import SOAPNoteVersion
from app.db_models.transcript import Transcript
from app.dependencies import CurrentUserDep, DbSessionDep
from app.models.soap_note import SOAPNoteResponse, SOAPNoteUpdate
from app.models.soap_note_version import (
    SOAPNoteVersionListResponse,
    SOAPNoteVersionResponse,
)
from app.services.audio_stitcher import AudioStitcher
from app.services.graph import ScribePipelineState, build_scribe_pipeline
from app.services.soap_versioning import archive_soap_snapshot

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


@router.get("/versions", response_model=SOAPNoteVersionListResponse)
async def list_soap_note_versions(
    consultation_id: uuid.UUID,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    soap = await _get_soap_note(db, consultation_id, user["id"])
    result = await db.execute(
        select(SOAPNoteVersion)
        .where(SOAPNoteVersion.soap_note_id == soap.id)
        .order_by(SOAPNoteVersion.version.desc())
    )
    versions = result.scalars().all()
    return SOAPNoteVersionListResponse(
        items=[SOAPNoteVersionResponse.model_validate(v) for v in versions],
        total=len(versions),
    )


@router.put("/", response_model=SOAPNoteResponse)
async def update_soap_note(
    consultation_id: uuid.UUID,
    body: SOAPNoteUpdate,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    soap = await _get_soap_note(db, consultation_id, user["id"])
    await archive_soap_snapshot(db, soap, "doctor_edited", edited_by=user["id"])
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

    await archive_soap_snapshot(db, soap, "finalized", edited_by=user["id"])
    soap.review_flags = flags
    soap.is_draft = False
    soap.version += 1
    await db.commit()
    await db.refresh(soap)
    return SOAPNoteResponse.model_validate(soap)


@router.post("/regenerate", response_model=SOAPNoteResponse)
async def regenerate_soap_note(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_consultation(db, consultation_id, user["id"])
    soap = await _get_soap_note_row(db, consultation_id)
    await archive_soap_snapshot(db, soap, "regenerated", edited_by=user["id"])

    # Fetch medically relevant transcripts
    result = await db.execute(
        select(Transcript)
        .where(
            Transcript.consultation_id == consultation_id,
            Transcript.is_medically_relevant.is_(True),
        )
        .order_by(Transcript.sequence_number)
    )
    segments = result.scalars().all()
    relevant_text = "\n".join(seg.text for seg in segments)

    if not relevant_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No medically relevant transcript segments to generate from",
        )

    from app import database

    graph = build_scribe_pipeline()
    graph_state = ScribePipelineState(
        consultation_id=consultation_id,
        relevant_text=relevant_text,
        language=consultation.language,
        language_known=True,
        metadata_extracted=True,
        mode="batch",
    )
    graph_config = {
        "configurable": {
            "ai_client": request.app.state.dashscope_client,
            "db_session_factory": database.async_session_factory,
        }
    }
    graph_result = await graph.ainvoke(graph_state, config=graph_config)

    new_soap = graph_result.get("soap", {})
    soap.subjective = new_soap.get("subjective", "")
    soap.objective = new_soap.get("objective", "")
    soap.assessment = new_soap.get("assessment", "")
    soap.plan = new_soap.get("plan", "")
    soap.medical_entities = graph_result.get("medical_entities", {})
    soap.icd10_codes = graph_result.get("icd10_codes", [])

    soap.is_draft = True
    soap.version += 1
    await db.commit()
    await db.refresh(soap)
    return SOAPNoteResponse.model_validate(soap)


@router.post("/suggest-icd10", response_model=SOAPNoteResponse)
async def suggest_icd10_codes(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_consultation(db, consultation_id, user["id"])
    soap = await _get_soap_note_row(db, consultation_id)
    await archive_soap_snapshot(db, soap, "icd10_suggested", edited_by=user["id"])

    entities = soap.medical_entities or {}
    if not entities.get("diagnoses"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No diagnoses found in medical entities",
        )

    from app.services.icd10_suggester import suggest_codes

    soap.icd10_codes = await suggest_codes(
        entities,
        soap.assessment,
        request.app.state.dashscope_client,
        db,
        language=consultation.language,
    )
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
