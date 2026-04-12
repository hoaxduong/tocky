import uuid
from datetime import datetime

from pydantic import BaseModel


class ConsultationCreate(BaseModel):
    title: str = ""
    patient_identifier: str | None = None
    language: str = "vi"


class ConsultationUpdate(BaseModel):
    title: str | None = None
    patient_identifier: str | None = None
    status: str | None = None
    ended_at: datetime | None = None


class ConsultationResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    title: str
    patient_identifier: str | None
    language: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConsultationListResponse(BaseModel):
    items: list[ConsultationResponse]
    total: int
    offset: int
    limit: int
