"""Research Agent State Definitions.

Sprint 70: Deep Research & Tool Use Integration
Sprint 116.10: Enhanced state tracking with execution steps

This module defines the state schema for the research supervisor graph.
The supervisor coordinates planning, searching, and synthesis phases.
"""

from datetime import datetime
from typing import Any, Literal, TypedDict


class ExecutionStep(TypedDict, total=False):
    """Single execution step in research workflow.

    Sprint 116.10: Track each step with timing and results.
    """

    step_name: str  # Name of the step (e.g., "decompose_query", "retrieve_context")
    started_at: str  # ISO 8601 timestamp
    completed_at: str | None  # ISO 8601 timestamp
    duration_ms: int | None  # Duration in milliseconds
    status: Literal["running", "completed", "failed"]  # Step status
    result: dict[str, Any]  # Step result data
    error: str | None  # Error message if failed


class ResearchSupervisorState(TypedDict, total=False):
    """State for research supervisor workflow.

    The supervisor manages multi-turn iterative research by:
    1. Planning: Decomposing query into sub-queries
    2. Searching: Executing searches via CoordinatorAgent
    3. Evaluating: Checking if more research is needed
    4. Synthesizing: Aggregating findings into final report

    Attributes:
        original_query: User's original research question
        sub_queries: List of planned search queries
        iteration: Current iteration number (starts at 0)
        max_iterations: Maximum iterations allowed (default: 3)
        all_contexts: Accumulated search results from all iterations
        synthesis: Final synthesized answer/report
        should_continue: Whether to continue iterating
        metadata: Additional metadata (TTFT, model info, etc.)
        error: Error message if something went wrong
        current_step: Current execution step (Sprint 116.10)
        execution_steps: List of all execution steps (Sprint 116.10)
        intermediate_answers: Map of sub-question to answer (Sprint 116.10)
    """

    # Core fields
    original_query: str
    sub_queries: list[str]
    iteration: int
    max_iterations: int
    all_contexts: list[dict[str, Any]]
    synthesis: str
    should_continue: bool

    # Optional fields
    metadata: dict[str, Any]
    error: str | None

    # Sprint 116.10: Enhanced tracking
    current_step: Literal[
        "pending",
        "decomposing",
        "retrieving",
        "analyzing",
        "synthesizing",
        "complete",
        "error"
    ]
    execution_steps: list[ExecutionStep]
    intermediate_answers: dict[str, str]  # sub_question -> answer
