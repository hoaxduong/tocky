import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Consultation(Base):
    __tablename__ = "consultations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    patient_identifier: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(10), default="vi")
    mode: Mapped[str] = mapped_column(String(20), default="live")
    status: Mapped[str] = mapped_column(String(30), default="recording")
    processing_step: Mapped[str | None] = mapped_column(String(50))
    processing_progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Final stitched audio (populated on finalize)
    full_audio_oss_key: Mapped[str | None] = mapped_column(String(500))
    full_audio_duration_ms: Mapped[int | None] = mapped_column()

    # Transcription checkpoint: converted PCM persisted to OSS so a run that
    # fails mid-transcription can re-transcribe only the chunks flagged
    # STATUS_FAILED_TRANSCRIPTION in the transcripts table, without a
    # re-upload.
    pcm_audio_oss_key: Mapped[str | None] = mapped_column(String(500))
    pcm_audio_size_bytes: Mapped[int | None] = mapped_column(Integer)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
