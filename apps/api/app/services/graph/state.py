from __future__ import annotations

import uuid
from typing import Any, TypedDict


class ScribePipelineState(TypedDict, total=False):
    # --- Inputs (set by caller before invocation) ---
    consultation_id: uuid.UUID
    relevant_text: str  # pre-joined relevant segment text
    language: str  # detected or initial language
    language_known: bool  # skip detection if True
    metadata_extracted: bool  # skip metadata extraction if True
    mode: str  # "live_periodic" | "live_final" | "batch"

    # --- Intermediate state (populated by nodes) ---
    detected_language: str
    consultation_metadata: dict[str, str]
    polished_transcript: str
    medical_entities: dict[str, Any]
    soap: dict[str, str]  # {subjective, objective, assessment, plan}
    confidence_flags: list[dict[str, Any]]
    review_flags: list[dict[str, Any]]
    icd10_codes: list[dict[str, Any]]

    # --- Error tracking (soft-fail accumulator) ---
    errors: list[dict[str, str]]
