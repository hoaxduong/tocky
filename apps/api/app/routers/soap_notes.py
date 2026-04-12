import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.db_models.consultation import Consultation
from app.db_models.soap_note import SOAPNote
from app.db_models.transcript import Transcript
from app.dependencies import CurrentUserDep, DbSessionDep
from app.models.soap_note import SOAPNoteResponse, SOAPNoteUpdate

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
    db: DbSessionDep,
    user: CurrentUserDep,
):
    soap = await _get_soap_note(db, consultation_id, user["id"])
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
    soap = await _get_soap_note(db, consultation_id, user["id"])

    # Fetch consultation language
    result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consultation = result.scalar_one()

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

    dashscope_client = request.app.state.dashscope_client
    new_soap = await dashscope_client.generate_soap(
        relevant_text, consultation.language
    )
    entities = await dashscope_client.extract_medical_entities(
        relevant_text, consultation.language
    )

    soap.subjective = new_soap.get("subjective", "")
    soap.objective = new_soap.get("objective", "")
    soap.assessment = new_soap.get("assessment", "")
    soap.plan = new_soap.get("plan", "")
    soap.medical_entities = entities
    soap.is_draft = True
    soap.version += 1
    await db.commit()
    await db.refresh(soap)
    return SOAPNoteResponse.model_validate(soap)


async def _get_soap_note(db, consultation_id: uuid.UUID, user_id: str) -> SOAPNote:
    # Verify the consultation belongs to the user
    result = await db.execute(
        select(Consultation).where(
            Consultation.id == consultation_id,
            Consultation.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation {consultation_id} not found",
        )

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
