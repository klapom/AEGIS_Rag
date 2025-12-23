"""Response Formatter Service.

Sprint 63 Feature 63.4: Structured Output Formatting (5 SP)

This module provides transformation services to convert natural language
chat/research responses into structured JSON format for programmatic consumption.
"""

import time
from datetime import UTC, datetime
from typing import Any

import structlog

from src.api.models.structured_output import (
    ResponseMetadata,
    SectionMetadata,
    StructuredChatResponse,
    StructuredResearchResponse,
    StructuredSource,
)

logger = structlog.get_logger(__name__)


def _extract_section_metadata(source_metadata: dict[str, Any]) -> SectionMetadata | None:
    """Extract section metadata from source.

    Args:
        source_metadata: Source metadata dictionary

    Returns:
        SectionMetadata object or None if no section info
    """
    section_headings = source_metadata.get("section_headings", [])
    section_pages = source_metadata.get("section_pages", [])
    primary_section = source_metadata.get("primary_section")

    if not (section_headings or section_pages or primary_section):
        return None

    return SectionMetadata(
        section_headings=section_headings,
        section_pages=section_pages,
        primary_section=primary_section,
    )


def _convert_source_to_structured(source: dict[str, Any]) -> StructuredSource:
    """Convert source document to StructuredSource.

    Args:
        source: Source document dictionary (from SourceDocument model or dict)

    Returns:
        StructuredSource object
    """
    # Handle both dict and Pydantic model sources
    if hasattr(source, "model_dump"):
        source = source.model_dump()
    elif hasattr(source, "dict"):
        source = source.dict()

    metadata = source.get("metadata", {})

    # Extract IDs from metadata
    document_id = metadata.get("document_id") or metadata.get("doc_id")
    chunk_id = metadata.get("chunk_id") or metadata.get("id")

    # Extract section metadata
    section = _extract_section_metadata(metadata)

    # Extract entities and relationships
    entities = metadata.get("entities", [])
    relationships = metadata.get("relationships", [])

    return StructuredSource(
        text=source.get("text", ""),
        score=source.get("score", 0.0),
        document_id=document_id,
        chunk_id=chunk_id,
        source=source.get("source"),
        title=source.get("title"),
        section=section,
        entities=entities,
        relationships=relationships,
        metadata=metadata,
    )


def format_chat_response_structured(
    query: str,
    answer: str,
    sources: list[Any],
    metadata: dict[str, Any],
    session_id: str | None = None,
    followup_questions: list[str] | None = None,
    start_time: float | None = None,
) -> StructuredChatResponse:
    """Format chat response as structured JSON.

    Transforms natural language chat response into structured format
    with separate fields for answer, sources, and metadata.

    Args:
        query: Original user query
        answer: Generated answer text
        sources: List of source documents (SourceDocument objects or dicts)
        metadata: Response metadata dict
        session_id: Session identifier
        followup_questions: Suggested follow-up questions
        start_time: Request start time (seconds since epoch)

    Returns:
        StructuredChatResponse with complete structured data

    Example:
        >>> sources = [{"text": "...", "score": 0.9, "metadata": {...}}]
        >>> response = format_chat_response_structured(
        ...     query="What is AegisRAG?",
        ...     answer="AegisRAG is...",
        ...     sources=sources,
        ...     metadata={"latency_seconds": 0.245},
        ...     session_id="user-123-session"
        ... )
        >>> response.metadata.latency_ms
        245.0
    """
    # Convert sources to structured format
    structured_sources = [_convert_source_to_structured(src) for src in sources]

    # Calculate latency
    latency_ms = metadata.get("latency_seconds", 0.0) * 1000
    if start_time:
        latency_ms = (time.time() - start_time) * 1000

    # Determine search type
    intent = metadata.get("intent") or metadata.get("search_type", "unknown")

    # Determine if graph was used
    graph_used = "graph" in intent.lower() or "hybrid" in intent.lower()

    # Determine if reranking was used (check metadata)
    reranking_used = metadata.get("reranking_used", False) or metadata.get(
        "reranked", False
    )

    # Extract agent path
    agent_path = metadata.get("agent_path", [])

    # Create response metadata
    response_metadata = ResponseMetadata(
        latency_ms=latency_ms,
        search_type=intent,
        reranking_used=reranking_used,
        graph_used=graph_used,
        total_sources=len(structured_sources),
        timestamp=datetime.now(UTC).isoformat(),
        session_id=session_id,
        agent_path=agent_path,
    )

    logger.info(
        "chat_response_formatted_structured",
        query_length=len(query),
        answer_length=len(answer),
        sources_count=len(structured_sources),
        latency_ms=latency_ms,
    )

    return StructuredChatResponse(
        query=query,
        answer=answer,
        sources=structured_sources,
        metadata=response_metadata,
        followup_questions=followup_questions or [],
    )


def format_research_response_structured(
    query: str,
    synthesis: str,
    sources: list[Any],
    research_plan: list[str],
    iterations: int,
    quality_metrics: dict[str, Any],
    start_time: float | None = None,
) -> StructuredResearchResponse:
    """Format research response as structured JSON.

    Transforms research response into structured format with synthesis,
    sources, and execution metadata.

    Args:
        query: Original research question
        synthesis: Synthesized research answer
        sources: List of source documents
        research_plan: Search queries executed
        iterations: Number of iterations performed
        quality_metrics: Research quality metrics
        start_time: Request start time (seconds since epoch)

    Returns:
        StructuredResearchResponse with complete structured data

    Example:
        >>> sources = [{"text": "...", "score": 0.85, "metadata": {...}}]
        >>> response = format_research_response_structured(
        ...     query="How does hybrid search work?",
        ...     synthesis="Hybrid search combines...",
        ...     sources=sources,
        ...     research_plan=["vector search", "graph search"],
        ...     iterations=2,
        ...     quality_metrics={"coverage": 0.85}
        ... )
        >>> response.iterations
        2
    """
    # Convert sources to structured format
    structured_sources = [_convert_source_to_structured(src) for src in sources]

    # Calculate latency
    latency_ms = 0.0
    if start_time:
        latency_ms = (time.time() - start_time) * 1000

    # Determine if reranking was used (assume true for research)
    reranking_used = True

    # Determine if graph was used (assume true for research)
    graph_used = True

    # Create response metadata
    response_metadata = ResponseMetadata(
        latency_ms=latency_ms,
        search_type="research",
        reranking_used=reranking_used,
        graph_used=graph_used,
        total_sources=len(structured_sources),
        timestamp=datetime.now(UTC).isoformat(),
        session_id=None,  # Research queries don't have sessions
        agent_path=["research_planner", "multi_search", "synthesizer"],
    )

    logger.info(
        "research_response_formatted_structured",
        query_length=len(query),
        synthesis_length=len(synthesis),
        sources_count=len(structured_sources),
        iterations=iterations,
        latency_ms=latency_ms,
    )

    return StructuredResearchResponse(
        query=query,
        synthesis=synthesis,
        sources=structured_sources,
        metadata=response_metadata,
        research_plan=research_plan,
        iterations=iterations,
        quality_metrics=quality_metrics,
    )
