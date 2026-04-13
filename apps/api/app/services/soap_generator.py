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
        sections = {
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

        return sections

    def build_relevance_prompt(self, text: str, language: str) -> list[dict]:
        return [
            {
                "role": "system",
                "content": self.prompts.get("classification"),
            },
            {"role": "user", "content": text},
        ]
