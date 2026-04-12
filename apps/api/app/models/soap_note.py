import uuid
from datetime import datetime

from pydantic import BaseModel


class SOAPNoteResponse(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    subjective: str
    objective: str
    assessment: str
    plan: str
    medical_entities: dict
    is_draft: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SOAPNoteUpdate(BaseModel):
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    is_draft: bool | None = None
