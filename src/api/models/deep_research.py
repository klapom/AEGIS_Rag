"""Deep Research API Models.

Sprint 116.10: Deep Research Multi-Step (13 SP)

This module defines Pydantic models for the deep research API endpoints
with enhanced tracking and intermediate results display.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.api.models.research import Source


class ExecutionStepModel(BaseModel):
    """Single execution step in research workflow.

    Tracks timing, status, and results for each step.
    """

    step_name: str = Field(..., description="Name of the step")
    started_at: datetime = Field(..., description="Step start time")
    completed_at: datetime | None = Field(None, description="Step completion time")
    duration_ms: int | None = Field(None, description="Duration in milliseconds")
    status: Literal["running", "completed", "failed"] = Field(..., description="Step status")
    result: dict[str, Any] = Field(default_factory=dict, description="Step result data")
    error: str | None = Field(None, description="Error message if failed")

    model_config = {"frozen": True}


class DeepResearchRequest(BaseModel):
    """Request model for deep research queries.

    Examples:
        >>> request = DeepResearchRequest(
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
    timeout_seconds: int = Field(
        default=180, ge=30, le=300, description="Total timeout in seconds (30-300)"
    )
    step_timeout_seconds: int = Field(
        default=60, ge=10, le=120, description="Per-step timeout in seconds (10-120)"
    )

    model_config = {"frozen": True}


class IntermediateAnswer(BaseModel):
    """Intermediate answer for a sub-question.

    Represents partial results during multi-step research.
    """

    sub_question: str = Field(..., description="Sub-question being answered")
    answer: str = Field(..., description="Intermediate answer")
    contexts_count: int = Field(..., description="Number of contexts used")
    sources: list[Source] = Field(default_factory=list, description="Sources used")
    confidence: float = Field(..., description="Confidence score (0-1)")

    model_config = {"frozen": True}


class DeepResearchResponse(BaseModel):
    """Response model for deep research queries.

    Examples:
        >>> response = DeepResearchResponse(
        ...     id="research_abc123",
        ...     query="What is ML?",
        ...     status="complete",
        ...     final_answer="Machine learning is...",
        ...     sources=[Source(text="ML is AI", score=0.9, source_type="vector")]
        ... )
        >>> len(response.sources)
        1
    """

    id: str = Field(..., description="Unique research ID")
    query: str = Field(..., description="Original research question")
    status: Literal[
        "pending",
        "decomposing",
        "retrieving",
        "analyzing",
        "synthesizing",
        "complete",
        "error",
        "cancelled",
    ] = Field(..., description="Current status")
    sub_questions: list[str] = Field(default_factory=list, description="Generated sub-questions")
    intermediate_answers: list[IntermediateAnswer] = Field(
        default_factory=list, description="Intermediate answers for sub-questions"
    )
    final_answer: str = Field(default="", description="Final synthesized answer")
    sources: list[Source] = Field(default_factory=list, description="All sources used")
    execution_steps: list[ExecutionStepModel] = Field(
        default_factory=list, description="Execution step history"
    )
    total_time_ms: int = Field(default=0, description="Total execution time in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    error: str | None = Field(None, description="Error message if failed")

    model_config = {"frozen": True}


class DeepResearchStatusResponse(BaseModel):
    """Status response for ongoing deep research.

    Used for polling research status.
    """

    id: str = Field(..., description="Research ID")
    status: Literal[
        "pending",
        "decomposing",
        "retrieving",
        "analyzing",
        "synthesizing",
        "complete",
        "error",
        "cancelled",
    ] = Field(..., description="Current status")
    current_step: str = Field(..., description="Current step name")
    progress_percent: int = Field(..., description="Progress percentage (0-100)")
    estimated_time_remaining_ms: int | None = Field(
        None, description="Estimated time remaining in milliseconds"
    )
    execution_steps: list[ExecutionStepModel] = Field(
        default_factory=list, description="Completed execution steps"
    )

    model_config = {"frozen": True}


class CancelResearchRequest(BaseModel):
    """Request to cancel ongoing research."""

    reason: str | None = Field(None, description="Optional cancellation reason")

    model_config = {"frozen": True}


class ExportFormat(str):
    """Export format options."""

    PDF = "pdf"
    MARKDOWN = "markdown"


class ExportResearchRequest(BaseModel):
    """Request to export research results."""

    format: Literal["pdf", "markdown"] = Field(..., description="Export format")
    include_sources: bool = Field(default=True, description="Include source citations")
    include_intermediate: bool = Field(default=False, description="Include intermediate answers")

    model_config = {"frozen": True}
