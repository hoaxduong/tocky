from typing import Literal

from pydantic import BaseModel

# Client -> Server messages


class AudioChunkMessage(BaseModel):
    type: Literal["audio_chunk"] = "audio_chunk"
    data: str  # base64-encoded audio bytes
    sequence: int
    timestamp_ms: int


class ControlMessage(BaseModel):
    type: Literal["start", "pause", "resume", "stop"]


# Server -> Client messages


class TranscriptMessage(BaseModel):
    type: Literal["transcript"] = "transcript"
    text: str
    is_medically_relevant: bool
    speaker_label: str | None = None
    sequence: int
    emotion: str | None = None
    timestamp_start_ms: int = 0
    timestamp_end_ms: int = 0


class SOAPUpdateMessage(BaseModel):
    type: Literal["soap_update"] = "soap_update"
    section: Literal["subjective", "objective", "assessment", "plan"]
    content: str


class StatusMessage(BaseModel):
    type: Literal["status"] = "status"
    status: str
    message: str | None = None


class MetadataUpdateMessage(BaseModel):
    type: Literal["metadata_update"] = "metadata_update"
    title: str
    patient_identifier: str | None = None
    language: str | None = None


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: str | None = None
