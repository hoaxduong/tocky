import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from app.db_models.consultation import Consultation
from app.dependencies import CurrentUserDep, DbSessionDep
from app.models.consultation import (
    ConsultationCreate,
    ConsultationListResponse,
    ConsultationResponse,
    ConsultationUpdate,
)

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.get("/", response_model=ConsultationListResponse)
async def list_consultations(
    db: DbSessionDep,
    user: CurrentUserDep,
    offset: int = 0,
    limit: int = 20,
    status_filter: str | None = None,
):
    query = select(Consultation).where(Consultation.user_id == user["id"])
    if status_filter:
        query = query.where(Consultation.status == status_filter)

    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_query)).scalar_one()

    query = query.order_by(Consultation.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return ConsultationListResponse(
        items=[ConsultationResponse.model_validate(c) for c in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_consultation(
    body: ConsultationCreate,
    db: DbSessionDep,
    user: CurrentUserDep,
    response: Response,
):
    consultation = Consultation(
        user_id=user["id"],
        title=body.title,
        patient_identifier=body.patient_identifier,
        language=body.language,
    )
    db.add(consultation)
    await db.commit()
    await db.refresh(consultation)
    response.headers["Location"] = f"/api/v1/consultations/{consultation.id}"
    return ConsultationResponse.model_validate(consultation)


@router.get("/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(
    consultation_id: uuid.UUID,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_user_consultation(db, consultation_id, user["id"])
    return ConsultationResponse.model_validate(consultation)


@router.patch("/{consultation_id}", response_model=ConsultationResponse)
async def update_consultation(
    consultation_id: uuid.UUID,
    body: ConsultationUpdate,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_user_consultation(db, consultation_id, user["id"])
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(consultation, key, value)
    await db.commit()
    await db.refresh(consultation)
    return ConsultationResponse.model_validate(consultation)


@router.delete(
    "/{consultation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_consultation(
    consultation_id: uuid.UUID,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_user_consultation(db, consultation_id, user["id"])
    await db.delete(consultation)
    await db.commit()


async def _get_user_consultation(
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
