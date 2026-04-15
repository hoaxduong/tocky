from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.services.graph.nodes import (
    detect_language_node,
    extract_entities_node,
    extract_metadata_node,
    generate_soap_node,
    polish_transcript_node,
    review_soap_node,
    suggest_icd10_node,
)
from app.services.graph.state import ScribePipelineState


def _route_start(state: ScribePipelineState) -> str:
    if state.get("language_known"):
        return "skip_detect"
    return "detect"


def _route_after_detect(state: ScribePipelineState) -> str:
    if state.get("metadata_extracted"):
        return "skip_meta"
    return "meta"


def _route_after_meta(state: ScribePipelineState) -> str:
    return "polish"


def _route_by_mode(state: ScribePipelineState) -> str:
    if state.get("mode") == "live_periodic":
        return "periodic"
    return "full"


def _route_after_soap(state: ScribePipelineState) -> str:
    if state.get("mode") == "live_periodic":
        return "end"
    return "review"


def build_scribe_pipeline() -> CompiledStateGraph:
    graph = StateGraph(ScribePipelineState)

    graph.add_node("detect_language", detect_language_node)
    graph.add_node("extract_metadata", extract_metadata_node)
    graph.add_node("polish_transcript", polish_transcript_node)
    graph.add_node("extract_entities", extract_entities_node)
    graph.add_node("generate_soap", generate_soap_node)
    graph.add_node("review_soap", review_soap_node)
    graph.add_node("suggest_icd10", suggest_icd10_node)

    # Entry: conditionally detect language
    graph.add_conditional_edges(
        "__start__",
        _route_start,
        {"detect": "detect_language", "skip_detect": "extract_metadata"},
    )

    # After detection: conditionally extract metadata
    graph.add_conditional_edges(
        "detect_language",
        _route_after_detect,
        {"meta": "extract_metadata", "skip_meta": "polish_transcript"},
    )

    # After metadata: always polish
    graph.add_conditional_edges(
        "extract_metadata",
        _route_after_meta,
        {"polish": "polish_transcript"},
    )

    # After polish: route by mode
    graph.add_conditional_edges(
        "polish_transcript",
        _route_by_mode,
        {"periodic": "generate_soap", "full": "extract_entities"},
    )

    # Full path: entities -> SOAP -> review -> ICD-10 -> END
    graph.add_edge("extract_entities", "generate_soap")

    # After SOAP: periodic -> END, full -> review
    graph.add_conditional_edges(
        "generate_soap",
        _route_after_soap,
        {"end": END, "review": "review_soap"},
    )

    graph.add_edge("review_soap", "suggest_icd10")
    graph.add_edge("suggest_icd10", END)

    return graph.compile()
