from __future__ import annotations

import logging
import re
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

_SOAP_SLUG_MAP = {
    "vi": "soap_vi",
    "ar-eg": "soap_ar_eg",
    "ar-gulf": "soap_ar_gulf",
    "en": "soap_en",
    "fr": "soap_fr",
}

_SOAP_EXTRACT_SLUG_MAP = {
    "vi": "soap_extract_vi",
    "ar-eg": "soap_extract_ar",
    "ar-gulf": "soap_extract_ar",
    "en": "soap_extract_en",
    "fr": "soap_extract_fr",
}

_SOAP_REASON_SLUG_MAP = {
    "vi": "soap_reason_vi",
    "ar-eg": "soap_reason_ar",
    "ar-gulf": "soap_reason_ar",
    "en": "soap_reason_en",
    "fr": "soap_reason_fr",
}


class SOAPGenerator:
    def __init__(self, prompt_registry: PromptRegistry) -> None:
        self.prompts = prompt_registry

    # ------------------------------------------------------------------
    # Single-pass (legacy, kept for periodic updates during recording)
    # ------------------------------------------------------------------

    def build_soap_prompt(self, transcript: str, language: str) -> list[dict]:
        slug = _SOAP_SLUG_MAP.get(language, "soap_en")
        system_prompt = self.prompts.get(slug)
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Consultation transcript:\n\n{transcript}",
            },
        ]

    # ------------------------------------------------------------------
    # Two-pass generation
    # ------------------------------------------------------------------

    def build_extract_prompt(self, transcript: str, language: str) -> list[dict]:
        """Pass 1: Extract factual Subjective + Objective from transcript."""
        slug = _SOAP_EXTRACT_SLUG_MAP.get(language, "soap_extract_en")
        system_prompt = self.prompts.get(slug)
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Consultation transcript:\n\n{transcript}",
            },
        ]

    def build_reason_prompt(
        self,
        subjective: str,
        objective: str,
        language: str,
        patient_history: str = "",
    ) -> list[dict]:
        """Pass 2: Generate Assessment + Plan from extracted findings."""
        slug = _SOAP_REASON_SLUG_MAP.get(language, "soap_reason_en")
        history_block = ""
        if patient_history:
            history_block = (
                f"Prior consultations for this patient:\n{patient_history}\n\n"
            )
        system_prompt = self.prompts.get(
            slug,
            patient_history_context=history_block,
            subjective=subjective,
            objective=objective,
        )
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Generate the Assessment and Plan sections"
                    " based on the findings above."
                ),
            },
        ]

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def parse_soap_response(self, response_text: str) -> dict[str, str]:
        sections: dict[str, str] = {
            "subjective": "",
            "objective": "",
            "assessment": "",
            "plan": "",
        }

        heading = r"Subjective|Objective|Assessment|Plan"
        pattern = rf"##\s*({heading})\s*\n(.*?)" rf"(?=##\s*(?:{heading})|\Z)"
        matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)

        for heading, content in matches:
            key = heading.strip().lower()
            if key in sections:
                sections[key] = content.strip()

        # Extract confidence flags from [Low confidence: ...] markers
        confidence_flags: list[dict[str, str]] = []
        flag_pattern = re.compile(r"\[Low confidence:\s*(.+?)\]", re.IGNORECASE)
        for section_key, content in sections.items():
            for match in flag_pattern.finditer(content):
                confidence_flags.append(
                    {
                        "section": section_key,
                        "issue_type": "low_confidence_section",
                        "suggestion": match.group(1).strip(),
                        "confidence": "low",
                    }
                )
        sections["_confidence_flags"] = confidence_flags  # type: ignore[assignment]

        return sections

    def build_relevance_prompt(self, text: str, language: str) -> list[dict]:
        return [
            {
                "role": "system",
                "content": self.prompts.get("classification"),
            },
            {"role": "user", "content": text},
        ]


async def fetch_patient_history(
    db: AsyncSession,
    patient_identifier: str | None,
    user_id: str,
    exclude_consultation_id: uuid.UUID,
    limit: int = 3,
) -> str:
    """Return a text summary of prior SOAP notes for the same patient.

    Returns an empty string if no prior consultations exist or
    ``patient_identifier`` is None.
    """
    if not patient_identifier:
        return ""

    from sqlalchemy import select

    from app.db_models.consultation import Consultation
    from app.db_models.soap_note import SOAPNote

    result = await db.execute(
        select(Consultation, SOAPNote)
        .join(SOAPNote, SOAPNote.consultation_id == Consultation.id)
        .where(
            Consultation.patient_identifier == patient_identifier,
            Consultation.user_id == user_id,
            Consultation.id != exclude_consultation_id,
            SOAPNote.is_draft.is_(False),
        )
        .order_by(Consultation.created_at.desc())
        .limit(limit)
    )
    rows = result.all()

    if not rows:
        return ""

    parts: list[str] = []
    for consultation, soap in rows:
        date_str = consultation.created_at.strftime("%Y-%m-%d")
        parts.append(
            f"Prior consultation ({date_str}):\n"
            f"Assessment: {soap.assessment}\n"
            f"Plan: {soap.plan}"
        )

    history = "\n\n".join(parts)
    logger.debug(
        "Patient history for %s: %d prior consultations",
        patient_identifier,
        len(rows),
    )
    return history
