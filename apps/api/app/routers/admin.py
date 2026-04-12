from fastapi import APIRouter
from sqlalchemy import func, select

from app.db_models.consultation import Consultation
from app.dependencies import AdminUserDep, DbSessionDep
from app.models.consultation import ConsultationListResponse, ConsultationResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/consultations", response_model=ConsultationListResponse)
async def list_all_consultations(
    db: DbSessionDep,
    _user: AdminUserDep,
    offset: int = 0,
    limit: int = 20,
):
    query = select(Consultation)
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


@router.get("/stats")
async def get_stats(
    db: DbSessionDep,
    _user: AdminUserDep,
):
    total_consultations = (
        await db.execute(select(func.count()).select_from(Consultation))
    ).scalar_one()

    active_consultations = (
        await db.execute(
            select(func.count())
            .select_from(Consultation)
            .where(Consultation.status == "recording")
        )
    ).scalar_one()

    completed_consultations = (
        await db.execute(
            select(func.count())
            .select_from(Consultation)
            .where(Consultation.status == "completed")
        )
    ).scalar_one()

    return {
        "total_consultations": total_consultations,
        "active_consultations": active_consultations,
        "completed_consultations": completed_consultations,
    }
