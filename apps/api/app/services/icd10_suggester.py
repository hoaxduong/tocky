from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select, text

from app.db_models.icd10_code import ICD10Code

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _build_clinical_context(
    medical_entities: dict, assessment: str
) -> str:
    """Build a text representation of the full clinical context."""
    parts: list[str] = []
    for category, items in medical_entities.items():
        if isinstance(items, list) and items:
            parts.append(
                f"{category}: {', '.join(str(i) for i in items)}"
            )
    if assessment:
        parts.append(f"\nAssessment narrative:\n{assessment}")
    return "\n".join(parts)


def _code_to_dict(
    db_code: ICD10Code, diagnosis: str, language: str = "en"
) -> dict:
    """Build a suggestion dict with localized description."""
    descs = db_code.descriptions or {}
    return {
        "code": db_code.code,
        "description": descs.get(language, db_code.description),
        "description_en": db_code.description,
        "diagnosis": diagnosis,
        "status": "suggested",
    }


async def suggest_codes(
    medical_entities: dict,
    assessment: str,
    ai_client,
    db: AsyncSession,
    language: str = "en",
) -> list[dict]:
    """Suggest ICD-10 codes from clinical context, validated against DB.

    Returns list of {code, description, description_en,
                     diagnosis, status} dicts.
    """
    diagnoses = medical_entities.get("diagnoses", [])
    if not diagnoses:
        return []

    clinical_context = _build_clinical_context(
        medical_entities, assessment
    )

    try:
        suggestions = await ai_client.suggest_icd10_codes(
            clinical_context, diagnoses
        )
    except Exception:
        logger.exception(
            "AI ICD-10 suggestion failed; falling back to search"
        )
        suggestions = []

    # Validate codes against the database
    validated: list[dict] = []
    seen_codes: set[str] = set()

    for suggestion in suggestions:
        code = suggestion.get("code", "").strip()
        if not code or code in seen_codes:
            continue

        result = await db.execute(
            select(ICD10Code).where(ICD10Code.code == code)
        )
        db_code = result.scalar_one_or_none()
        if db_code:
            seen_codes.add(code)
            validated.append(
                _code_to_dict(
                    db_code,
                    suggestion.get("diagnosis", ""),
                    language,
                )
            )

    # Fallback: for diagnoses without a validated code, try text search
    covered = {v["diagnosis"].lower() for v in validated}
    for diagnosis in diagnoses:
        if diagnosis.lower() in covered:
            continue
        result = await db.execute(
            select(ICD10Code)
            .where(ICD10Code.description.ilike(f"%{diagnosis}%"))
            .order_by(
                text(
                    "similarity(description, :q) DESC"
                ).bindparams(q=diagnosis)
            )
            .limit(1)
        )
        fallback = result.scalar_one_or_none()
        if fallback and fallback.code not in seen_codes:
            seen_codes.add(fallback.code)
            validated.append(
                _code_to_dict(fallback, diagnosis, language)
            )

    return validated
