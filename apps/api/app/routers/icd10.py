import logging
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select, text

from app.db_models.icd10_code import ICD10Code
from app.dependencies import DbSessionDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/icd10", tags=["icd10"])


def _localized(code: ICD10Code, lang: str) -> dict:
    """Return code dict with description in the requested language."""
    descs = code.descriptions or {}
    desc = descs.get(lang, code.description)
    return {
        "code": code.code,
        "description": desc,
        "description_en": code.description,
    }


@router.get("/search")
async def search_icd10(
    db: DbSessionDep,
    q: Annotated[str, Query(min_length=1, description="Search query")],
    lang: Annotated[str, Query(description="Language code")] = "en",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[dict]:
    """Search ICD-10 codes by description or code."""
    # Try exact code match first
    result = await db.execute(
        select(ICD10Code).where(
            func.upper(ICD10Code.code) == q.strip().upper()
        )
    )
    exact = result.scalar_one_or_none()
    if exact:
        return [_localized(exact, lang)]

    # Trigram similarity + ILIKE on English description
    similarity = func.similarity(ICD10Code.description, q)
    result = await db.execute(
        select(ICD10Code, similarity.label("sim"))
        .where(
            (ICD10Code.description.ilike(f"%{q}%"))
            | (text("description % :q").bindparams(q=q))
            | (ICD10Code.code.ilike(f"{q}%"))
        )
        .order_by(similarity.desc())
        .limit(limit)
    )

    rows = result.all()
    return [_localized(row.ICD10Code, lang) for row in rows]
