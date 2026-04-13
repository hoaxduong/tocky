from __future__ import annotations

from typing import Protocol


class AIClient(Protocol):
    async def transcribe_audio(self, audio_bytes: bytes, language: str) -> str: ...

    async def classify_relevance(self, text: str, language: str) -> bool: ...

    async def generate_soap(
        self, transcript_text: str, language: str
    ) -> dict[str, str]: ...

    async def review_soap(
        self,
        transcript_text: str,
        soap: dict[str, str],
        language: str,
    ) -> list[dict]: ...

    async def extract_medical_entities(self, text: str, language: str) -> dict: ...

    async def detect_language(self, text: str) -> str: ...

    async def extract_consultation_metadata(
        self, transcript_text: str
    ) -> dict[str, str]: ...

    async def suggest_icd10_codes(
        self, clinical_context: str, diagnoses: list[str]
    ) -> list[dict]: ...

    async def close(self) -> None: ...
