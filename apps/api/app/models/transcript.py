import uuid

from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    id: uuid.UUID
    sequence_number: int
    text: str
    language: str
    is_medically_relevant: bool
    speaker_label: str | None
    timestamp_start_ms: int
    timestamp_end_ms: int

    model_config = {"from_attributes": True}


class TranscriptResponse(BaseModel):
    consultation_id: uuid.UUID
    segments: list[TranscriptSegment]
