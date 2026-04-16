import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ValidationError, model_validator

from app.models.review_flag import ReviewFlag

logger = logging.getLogger(__name__)


class SOAPNoteResponse(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    subjective: str
    objective: str
    assessment: str
    plan: str
    medical_entities: dict
    review_flags: list[ReviewFlag] = []
    icd10_codes: list[dict] = []
    is_draft: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _coerce_review_flags(cls, values: Any) -> Any:
        """Silently drop invalid flags from DB data instead of rejecting."""
        raw = None
        if isinstance(values, dict):
            raw = values.get("review_flags")
        elif hasattr(values, "review_flags"):
            raw = values.review_flags
        if not isinstance(raw, list):
            return values
        cleaned = []
        for item in raw:
            try:
                if isinstance(item, ReviewFlag):
                    cleaned.append(item)
                elif isinstance(item, dict):
                    cleaned.append(ReviewFlag.model_validate(item))
                # else: skip
            except (ValidationError, ValueError):
                logger.debug("Dropping invalid review flag: %s", item)
                continue
        if isinstance(values, dict):
            values["review_flags"] = cleaned
        elif hasattr(values, "__dict__"):
            values.__dict__["review_flags"] = cleaned
        return values


class SOAPNoteUpdate(BaseModel):
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    icd10_codes: list[dict] | None = None
    is_draft: bool | None = None
