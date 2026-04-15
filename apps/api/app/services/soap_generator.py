from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.prompt_registry import PromptRegistry

_SOAP_SLUG_MAP = {
    "vi": "soap_vi",
    "ar-eg": "soap_ar_eg",
    "ar-gulf": "soap_ar_gulf",
    "en": "soap_en",
    "fr": "soap_fr",
}


class SOAPGenerator:
    def __init__(self, prompt_registry: PromptRegistry) -> None:
        self.prompts = prompt_registry

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
