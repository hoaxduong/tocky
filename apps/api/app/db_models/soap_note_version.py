import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SOAPNoteVersion(Base):
    __tablename__ = "soap_note_versions"
    __table_args__ = (
        UniqueConstraint("soap_note_id", "version", name="uq_soap_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    soap_note_id: Mapped[uuid.UUID] = mapped_column(index=True)
    version: Mapped[int]
    subjective: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    assessment: Mapped[str] = mapped_column(Text, default="")
    plan: Mapped[str] = mapped_column(Text, default="")
    medical_entities: Mapped[dict] = mapped_column(JSON, default=dict)
    icd10_codes: Mapped[list] = mapped_column(JSON, default=list)
    review_flags: Mapped[list] = mapped_column(JSON, default=list)
    is_draft: Mapped[bool] = mapped_column(default=True)
    source: Mapped[str] = mapped_column(String(30))
    edited_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
