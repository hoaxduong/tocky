from __future__ import annotations

import logging
from typing import Any

from langgraph.types import RunnableConfig

from app.services.graph.state import ScribePipelineState

logger = logging.getLogger(__name__)


def _append_error(
    state: ScribePipelineState, node: str, error: str
) -> list[dict[str, str]]:
    errors = list(state.get("errors") or [])
    errors.append({"node": node, "error": str(error)[:500]})
    return errors


def _effective_language(state: ScribePipelineState) -> str:
    return state.get("detected_language") or state.get("language", "en")


async def detect_language_node(
    state: ScribePipelineState, config: RunnableConfig
) -> dict[str, Any]:
    ai_client = config["configurable"]["ai_client"]
    try:
        detected = await ai_client.detect_language(state["relevant_text"])
        return {"detected_language": detected}
    except Exception as e:
        logger.warning("detect_language failed [%s]: %s", type(e).__name__, e)
        return {
            "detected_language": state.get("language", "en"),
            "errors": _append_error(state, "detect_language", e),
        }


async def extract_metadata_node(
    state: ScribePipelineState, config: RunnableConfig
) -> dict[str, Any]:
    ai_client = config["configurable"]["ai_client"]
    try:
        metadata = await ai_client.extract_consultation_metadata(state["relevant_text"])
        return {"consultation_metadata": metadata}
    except Exception as e:
        logger.warning("extract_metadata failed [%s]: %s", type(e).__name__, e)
        return {
            "consultation_metadata": {},
            "errors": _append_error(state, "extract_metadata", e),
        }


async def polish_transcript_node(
    state: ScribePipelineState, config: RunnableConfig
) -> dict[str, Any]:
    ai_client = config["configurable"]["ai_client"]
    language = _effective_language(state)
    try:
        polished = await ai_client.polish_transcript(state["relevant_text"], language)
        return {"polished_transcript": polished}
    except Exception as e:
        logger.warning("polish_transcript failed [%s]: %s", type(e).__name__, e)
        return {
            "polished_transcript": state["relevant_text"],
            "errors": _append_error(state, "polish_transcript", e),
        }


async def extract_entities_node(
    state: ScribePipelineState, config: RunnableConfig
) -> dict[str, Any]:
    ai_client = config["configurable"]["ai_client"]
    language = _effective_language(state)
    polished = state.get("polished_transcript") or state["relevant_text"]
    try:
        entities = await ai_client.extract_medical_entities(polished, language)
        return {"medical_entities": entities}
    except Exception as e:
        logger.warning("extract_entities failed [%s]: %s", type(e).__name__, e)
        return {
            "medical_entities": {},
            "errors": _append_error(state, "extract_entities", e),
        }


async def generate_soap_node(
    state: ScribePipelineState, config: RunnableConfig
) -> dict[str, Any]:
    ai_client = config["configurable"]["ai_client"]
    on_update = config["configurable"].get("on_update")
    language = _effective_language(state)
    polished = state.get("polished_transcript") or state["relevant_text"]
    patient_history = config["configurable"].get("patient_history", "")

    try:
        soap = await ai_client.generate_soap(
            polished, language, patient_history=patient_history
        )
        confidence_flags = soap.pop("_confidence_flags", [])

        if on_update:
            for section in ("subjective", "objective", "assessment", "plan"):
                if soap.get(section):
                    await on_update("soap_update", section, soap[section])

        return {"soap": soap, "confidence_flags": confidence_flags}
    except Exception as e:
        logger.exception("generate_soap failed [%s]: %s", type(e).__name__, e)
        return {
            "soap": {
                "subjective": "",
                "objective": "",
                "assessment": "",
                "plan": "",
            },
            "confidence_flags": [],
            "errors": _append_error(state, "generate_soap", e),
        }


async def review_soap_node(
    state: ScribePipelineState, config: RunnableConfig
) -> dict[str, Any]:
    ai_client = config["configurable"]["ai_client"]
    language = _effective_language(state)
    polished = state.get("polished_transcript") or state["relevant_text"]
    soap = state.get("soap", {})
    confidence_flags = list(state.get("confidence_flags") or [])

    try:
        review_flags = await ai_client.review_soap(polished, soap, language)
        all_flags = confidence_flags + list(review_flags)
        return {"review_flags": all_flags}
    except Exception as e:
        logger.warning("review_soap failed [%s]: %s", type(e).__name__, e)
        return {
            "review_flags": confidence_flags,
            "errors": _append_error(state, "review_soap", e),
        }


async def suggest_icd10_node(
    state: ScribePipelineState, config: RunnableConfig
) -> dict[str, Any]:
    ai_client = config["configurable"]["ai_client"]
    db_session_factory = config["configurable"].get("db_session_factory")
    language = _effective_language(state)
    entities = state.get("medical_entities", {})
    assessment = state.get("soap", {}).get("assessment", "")

    if not entities.get("diagnoses") or not db_session_factory:
        return {"icd10_codes": []}

    try:
        from app.services.icd10_suggester import suggest_codes

        async with db_session_factory() as db:
            codes = await suggest_codes(
                entities, assessment, ai_client, db, language=language
            )
        return {"icd10_codes": codes}
    except Exception as e:
        logger.warning("suggest_icd10 failed [%s]: %s", type(e).__name__, e)
        return {
            "icd10_codes": [],
            "errors": _append_error(state, "suggest_icd10", e),
        }
