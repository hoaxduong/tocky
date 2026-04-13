from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ICD10Code(Base):
    __tablename__ = "icd10_codes"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    description: Mapped[str] = mapped_column(Text)  # English (canonical)
    # {"en": "...", "fr": "...", "vi": "...", "ar": "..."}
    descriptions: Mapped[dict] = mapped_column(JSONB, default=dict)
    category: Mapped[str] = mapped_column(String(5), index=True)
