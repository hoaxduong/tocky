import uuid
from datetime import datetime

from pydantic import BaseModel


class SOAPNoteVersionResponse(BaseModel):
    id: uuid.UUID
    soap_note_id: uuid.UUID
    version: int
    subjective: str
    objective: str
    assessment: str
    plan: str
    medical_entities: dict
    icd10_codes: list[dict] = []
    review_flags: list = []
    is_draft: bool
    source: str
    edited_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SOAPNoteVersionListResponse(BaseModel):
    items: list[SOAPNoteVersionResponse]
    total: int
