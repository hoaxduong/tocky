import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.db_models.consultation import Consultation
from app.db_models.transcript import Transcript
from app.dependencies import CurrentUserDep, DbSessionDep
from app.models.transcript import TranscriptResponse, TranscriptSegment

router = APIRouter(
    prefix="/consultations/{consultation_id}/transcripts",
    tags=["transcripts"],
)


@router.get("", response_model=TranscriptResponse)
async def get_transcripts(
    consultation_id: uuid.UUID,
    db: DbSessionDep,
    user: CurrentUserDep,
    medically_relevant_only: bool = False,
):
    # Verify the consultation belongs to the user
    result = await db.execute(
        select(Consultation).where(
            Consultation.id == consultation_id,
            Consultation.user_id == user["id"],
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation {consultation_id} not found",
        )

    query = (
        select(Transcript)
        .where(Transcript.consultation_id == consultation_id)
        .order_by(Transcript.sequence_number)
    )
    if medically_relevant_only:
        query = query.where(Transcript.is_medically_relevant.is_(True))

    result = await db.execute(query)
    segments = result.scalars().all()

    return TranscriptResponse(
        consultation_id=consultation_id,
        segments=[TranscriptSegment.model_validate(s) for s in segments],
    )
