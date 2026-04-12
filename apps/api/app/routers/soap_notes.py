import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.db_models.consultation import Consultation
from app.db_models.soap_note import SOAPNote
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
