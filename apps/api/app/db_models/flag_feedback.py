import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FlagFeedback(Base):
    __tablename__ = "flag_feedback"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    soap_note_id: Mapped[uuid.UUID] = mapped_column(index=True)
    flag_index: Mapped[int] = mapped_column()
    flag_issue_type: Mapped[str] = mapped_column(String(50))
    flag_section: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
