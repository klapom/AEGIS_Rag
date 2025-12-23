"""Research API Models.

Sprint 62 Feature 62.10: Research Endpoint Backend (6 SP)

This module defines Pydantic models for the research API endpoints.
"""

from typing import Any

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Source document with metadata.

    Represents a source used in research synthesis.
    """

    text: str = Field(..., description="Source text content")
    score: float = Field(..., description="Relevance score (0-1)")
    source_type: str = Field(..., description="Source type (vector, graph)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    entities: list[str] = Field(default_factory=list, description="Extracted entities")
    relationships: list[str] = Field(default_factory=list, description="Extracted relationships")

    model_config = {"frozen": True}


class ResearchQueryRequest(BaseModel):
    """Request model for research queries.

    Examples:
        >>> request = ResearchQueryRequest(
        ...     query="What is machine learning?",
        ...     namespace="ml_docs"
        ... )
        >>> request.max_iterations
        3
    """

    query: str = Field(..., min_length=1, description="Research question")
    namespace: str = Field(default="default", description="Namespace to search in")
    max_iterations: int = Field(
        default=3, ge=1, le=5, description="Maximum search iterations (1-5)"
    )
    stream: bool = Field(default=True, description="Enable SSE streaming")

    model_config = {"frozen": True}


class ResearchProgress(BaseModel):
    """Progress update during research.

    Used for SSE streaming to show research progress.
    """

    phase: str = Field(..., description="Current phase (plan, search, evaluate, synthesize)")
    message: str = Field(..., description="Progress message")
    iteration: int = Field(default=0, description="Current iteration number")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"frozen": True}


class ResearchQueryResponse(BaseModel):
    """Response model for research queries.

    Examples:
        >>> response = ResearchQueryResponse(
        ...     query="What is ML?",
        ...     synthesis="Machine learning is...",
        ...     sources=[Source(text="ML is AI", score=0.9, source_type="vector")]
        ... )
        >>> len(response.sources)
        1
    """

    query: str = Field(..., description="Original research question")
    synthesis: str = Field(..., description="Synthesized research answer")
    sources: list[Source] = Field(default_factory=list, description="Source documents used")
    iterations: int = Field(default=1, description="Number of search iterations performed")
    quality_metrics: dict[str, Any] = Field(default_factory=dict, description="Quality metrics")
    research_plan: list[str] = Field(default_factory=list, description="Search queries executed")

    model_config = {"frozen": True}
