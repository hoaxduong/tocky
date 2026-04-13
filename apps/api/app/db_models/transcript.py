import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Transcript processing statuses
STATUS_TRANSCRIBED = "transcribed"
STATUS_CLASSIFIED = "classified"
STATUS_FAILED_TRANSCRIPTION = "failed_transcription"
STATUS_FAILED_CLASSIFICATION = "failed_classification"


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    consultation_id: Mapped[uuid.UUID] = mapped_column(index=True)
    sequence_number: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10))
    is_medically_relevant: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(30), default=STATUS_TRANSCRIBED)
    error_message: Mapped[str | None] = mapped_column(Text)
    speaker_label: Mapped[str | None] = mapped_column(String(20))
    emotion: Mapped[str | None] = mapped_column(String(20))
    timestamp_start_ms: Mapped[int]
    timestamp_end_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
