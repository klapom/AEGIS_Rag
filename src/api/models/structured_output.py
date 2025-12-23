"""Structured Output Models.

Sprint 63 Feature 63.4: Structured Output Formatting (5 SP)

This module defines Pydantic models for structured JSON output format,
providing programmatic consumption of chat and research responses.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SectionMetadata(BaseModel):
    """Section metadata for precise citations.

    Provides hierarchical section information for document navigation.
    """

    section_headings: list[str] = Field(
        default_factory=list, description="Hierarchical section headings"
    )
    section_pages: list[int] = Field(default_factory=list, description="Page numbers")
    primary_section: str | None = Field(default=None, description="Primary section name")


class StructuredSource(BaseModel):
    """Structured source document with complete metadata.

    Provides all source information in machine-readable format.
    """

    text: str = Field(..., description="Source text content")
    score: float = Field(..., description="Relevance score (0-1)")
    document_id: str | None = Field(default=None, description="Document identifier")
    chunk_id: str | None = Field(default=None, description="Chunk identifier")
    source: str | None = Field(default=None, description="Source file path")
    title: str | None = Field(default=None, description="Document/section title")
    section: SectionMetadata | None = Field(default=None, description="Section metadata")
    entities: list[str] = Field(default_factory=list, description="Extracted entities")
    relationships: list[str] = Field(default_factory=list, description="Extracted relationships")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "AegisRAG is an agentic enterprise graph intelligence system...",
                "score": 0.92,
                "document_id": "doc_123",
                "chunk_id": "chunk_456",
                "source": "docs/CLAUDE.md",
                "title": "CLAUDE.md - Section: 'Architecture' (Page 2)",
                "section": {
                    "section_headings": ["Architecture", "Components"],
                    "section_pages": [2],
                    "primary_section": "Architecture",
                },
                "entities": ["AegisRAG", "LangGraph", "Qdrant"],
                "relationships": ["uses", "integrates_with"],
                "metadata": {"chunk_size": 800, "collection": "documents_v1"},
            }
        }
    }


class ResponseMetadata(BaseModel):
    """Response execution metadata.

    Provides performance and execution information.
    """

    latency_ms: float = Field(..., description="Total response latency in milliseconds")
    search_type: str = Field(..., description="Search type used (vector, graph, hybrid)")
    reranking_used: bool = Field(default=False, description="Whether reranking was applied")
    graph_used: bool = Field(default=False, description="Whether graph search was used")
    total_sources: int = Field(..., description="Total number of sources retrieved")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Response timestamp (ISO 8601)",
    )
    session_id: str | None = Field(default=None, description="Session identifier")
    agent_path: list[str] = Field(
        default_factory=list, description="Agent execution path (e.g., ['router', 'vector_agent'])"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "latency_ms": 245.3,
                "search_type": "hybrid",
                "reranking_used": True,
                "graph_used": True,
                "total_sources": 10,
                "timestamp": "2025-12-23T10:30:00.123Z",
                "session_id": "user-123-session",
                "agent_path": ["router", "vector_agent", "graph_agent", "generator"],
            }
        }
    }


class StructuredChatResponse(BaseModel):
    """Structured chat response for programmatic consumption.

    Provides chat response in structured JSON format with separate fields
    for answer, sources, and metadata.
    """

    query: str = Field(..., description="Original user query")
    answer: str = Field(..., description="Generated answer text")
    sources: list[StructuredSource] = Field(
        default_factory=list, description="Source documents with complete metadata"
    )
    metadata: ResponseMetadata = Field(..., description="Response execution metadata")
    followup_questions: list[str] = Field(
        default_factory=list, description="Suggested follow-up questions"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What is AegisRAG?",
                "answer": "AegisRAG (Agentic Enterprise Graph Intelligence System) is...",
                "sources": [
                    {
                        "text": "AegisRAG = Agentic Enterprise Graph Intelligence System",
                        "score": 0.92,
                        "document_id": "doc_123",
                        "chunk_id": "chunk_456",
                        "source": "docs/CLAUDE.md",
                        "title": "CLAUDE.md",
                        "section": {
                            "section_headings": ["Project Overview"],
                            "section_pages": [1],
                            "primary_section": "Project Overview",
                        },
                        "entities": ["AegisRAG", "LangGraph"],
                        "relationships": ["uses"],
                        "metadata": {},
                    }
                ],
                "metadata": {
                    "latency_ms": 245.3,
                    "search_type": "hybrid",
                    "reranking_used": True,
                    "graph_used": True,
                    "total_sources": 10,
                    "timestamp": "2025-12-23T10:30:00.123Z",
                    "session_id": "user-123-session",
                    "agent_path": ["router", "vector_agent", "generator"],
                },
                "followup_questions": [
                    "How does AegisRAG differ from traditional RAG?",
                    "What are the main components of AegisRAG?",
                ],
            }
        }
    }


class StructuredResearchResponse(BaseModel):
    """Structured research response for programmatic consumption.

    Provides research response in structured JSON format with synthesis,
    sources, and execution metadata.
    """

    query: str = Field(..., description="Original research question")
    synthesis: str = Field(..., description="Synthesized research answer")
    sources: list[StructuredSource] = Field(
        default_factory=list, description="Source documents with complete metadata"
    )
    metadata: ResponseMetadata = Field(..., description="Response execution metadata")
    research_plan: list[str] = Field(
        default_factory=list, description="Search queries executed during research"
    )
    iterations: int = Field(default=1, description="Number of research iterations performed")
    quality_metrics: dict[str, Any] = Field(
        default_factory=dict, description="Research quality metrics"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "How does hybrid search work in AegisRAG?",
                "synthesis": "Hybrid search in AegisRAG combines vector similarity...",
                "sources": [
                    {
                        "text": "Vector search uses BGE-M3 embeddings...",
                        "score": 0.89,
                        "document_id": "doc_456",
                        "chunk_id": "chunk_789",
                        "source": "docs/ARCHITECTURE.md",
                        "title": "ARCHITECTURE.md - Section: 'Hybrid Search'",
                        "section": None,
                        "entities": ["BGE-M3", "Qdrant"],
                        "relationships": ["uses"],
                        "metadata": {},
                    }
                ],
                "metadata": {
                    "latency_ms": 1850.0,
                    "search_type": "research",
                    "reranking_used": True,
                    "graph_used": True,
                    "total_sources": 15,
                    "timestamp": "2025-12-23T10:35:00.456Z",
                    "session_id": None,
                    "agent_path": ["research_planner", "multi_search", "synthesizer"],
                },
                "research_plan": [
                    "vector search explanation",
                    "graph search explanation",
                    "hybrid combination strategy",
                ],
                "iterations": 2,
                "quality_metrics": {"coverage": 0.85, "coherence": 0.92},
            }
        }
    }
