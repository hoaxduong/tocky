import uuid
from datetime import datetime

from pydantic import BaseModel, model_validator


class ConsultationCreate(BaseModel):
    title: str = ""
    patient_identifier: str | None = None
    language: str = "vi"
    mode: str = "live"


class ConsultationUpdate(BaseModel):
    title: str | None = None
    patient_identifier: str | None = None
    language: str | None = None
    status: str | None = None
    ended_at: datetime | None = None


class ConsultationResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    title: str
    patient_identifier: str | None
    language: str
    mode: str
    status: str
    processing_step: str | None
    processing_progress: int
    error_message: str | None
    has_audio: bool = False
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="wrap")
    @classmethod
    def _compute_has_audio(cls, data, handler):
        has = False
        if hasattr(data, "full_audio_oss_key"):
            has = bool(data.full_audio_oss_key or data.pcm_audio_oss_key)
        elif isinstance(data, dict):
            has = bool(
                data.get("full_audio_oss_key") or data.get("pcm_audio_oss_key")
            )
        result = handler(data)
        result.has_audio = has
        return result


class ConsultationListResponse(BaseModel):
    items: list[ConsultationResponse]
    total: int
    offset: int
    limit: int
