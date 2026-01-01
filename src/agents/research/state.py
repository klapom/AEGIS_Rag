"""Research Agent State Definitions.

Sprint 70: Deep Research & Tool Use Integration

This module defines the state schema for the research supervisor graph.
The supervisor coordinates planning, searching, and synthesis phases.
"""

from typing import Any, TypedDict


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
