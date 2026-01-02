"""Phase Event Models for Real-Time Thinking Process Tracking.

Sprint 48 Feature 48.1: Phase Event Models & Types (5 SP)

These models enable tracking of each processing phase in the RAG pipeline,
providing real-time visibility into what the system is doing during query processing.
This supports the Real-Time Thinking Display feature for the frontend.

Usage Example:
    >>> from src.models.phase_event import PhaseEvent, PhaseType, PhaseStatus
    >>> from datetime import datetime
    >>>
    >>> # Create a phase event
    >>> event = PhaseEvent(
    ...     phase_type=PhaseType.VECTOR_SEARCH,
    ...     status=PhaseStatus.IN_PROGRESS,
    ...     start_time=datetime.now(),
    ...     metadata={"top_k": 10, "collection": "documents_v1"}
    ... )
    >>>
    >>> # Complete the phase
    >>> event.end_time = datetime.now()
    >>> event.status = PhaseStatus.COMPLETED
    >>> event.duration_ms = (event.end_time - event.start_time).total_seconds() * 1000

Architecture:
    - PhaseType: Enum of all possible processing phases
    - PhaseStatus: Enum of phase execution states
    - PhaseEvent: Pydantic model for tracking individual phase execution

Related Features:
    - Sprint 48 Feature 48.2: CoordinatorAgent Streaming (5 SP)
    - Sprint 48 Feature 48.7: ReasoningData Builder (3 SP)
    - Sprint 48 Feature 48.10: Request Timeout & Cancel (5 SP)

See Also:
    - src/agents/reasoning_data.py: Builder for accumulating phase events
    - docs/sprints/SPRINT_48.md: Sprint 48 implementation plan
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PhaseType(str, Enum):
    """Enumeration of all processing phases in the RAG pipeline.

    Each phase represents a distinct step in query processing:
    - INTENT_CLASSIFICATION: RouterAgent determines query intent
    - VECTOR_SEARCH: VectorSearchAgent retrieves via Qdrant
    - BM25_SEARCH: Keyword-based search (hybrid retrieval)
    - RRF_FUSION: Reciprocal Rank Fusion combining vector + BM25
    - RERANKING: Cross-encoder reranking of results
    - GRAPH_QUERY: GraphQueryAgent retrieves from Neo4j
    - MEMORY_RETRIEVAL: MemoryAgent fetches from Redis/Graphiti
    - TOOL_EXECUTION: ActionAgent executes MCP tools (Sprint 70 Feature 70.9)
    - LLM_GENERATION: Final answer generation
    - FOLLOW_UP_QUESTIONS: FollowUpGenerator creates suggested questions
    - LLM_PROMPT_*: Granular LLM prompt executions (Sprint 70 Feature 70.12)

    Sprint 70 Feature 70.12: LLM Prompt Tracing
    The following phase types enable tracking individual LLM prompt executions:
    - LLM_PROMPT_INTENT: Graph intent extraction (GRAPH_INTENT_PROMPT)
    - LLM_PROMPT_DECOMPOSITION: Query decomposition (DECOMPOSITION_PROMPT)
    - LLM_PROMPT_EXPANSION: Query expansion (QUERY_EXPANSION_PROMPT)
    - LLM_PROMPT_REFINEMENT: Query refinement (QUERY_REFINEMENT_PROMPT)
    - LLM_PROMPT_ENTITY_EXTRACTION: Entity extraction prompts
    - LLM_PROMPT_RESEARCH_PLANNING: Research planning (RESEARCH_PLANNING_PROMPT)
    - LLM_PROMPT_CONTRADICTION: Contradiction detection (multi-turn)
    - LLM_PROMPT_VLM: Vision-Language Model image descriptions
    - LLM_PROMPT_OTHER: Generic LLM prompt execution (fallback)

    Example:
        >>> PhaseType.VECTOR_SEARCH
        <PhaseType.VECTOR_SEARCH: 'vector_search'>
        >>> PhaseType.LLM_PROMPT_INTENT
        <PhaseType.LLM_PROMPT_INTENT: 'llm_prompt_intent'>
    """

    INTENT_CLASSIFICATION = "intent_classification"
    VECTOR_SEARCH = "vector_search"
    BM25_SEARCH = "bm25_search"
    RRF_FUSION = "rrf_fusion"
    RERANKING = "reranking"
    GRAPH_QUERY = "graph_query"
    MEMORY_RETRIEVAL = "memory_retrieval"
    TOOL_EXECUTION = "tool_execution"  # Sprint 70 Feature 70.9
    LLM_GENERATION = "llm_generation"
    FOLLOW_UP_QUESTIONS = "follow_up_questions"

    # Sprint 70 Feature 70.12: LLM Prompt Tracing
    LLM_PROMPT_INTENT = "llm_prompt_intent"
    LLM_PROMPT_DECOMPOSITION = "llm_prompt_decomposition"
    LLM_PROMPT_EXPANSION = "llm_prompt_expansion"
    LLM_PROMPT_REFINEMENT = "llm_prompt_refinement"
    LLM_PROMPT_ENTITY_EXTRACTION = "llm_prompt_entity_extraction"
    LLM_PROMPT_RESEARCH_PLANNING = "llm_prompt_research_planning"
    LLM_PROMPT_CONTRADICTION = "llm_prompt_contradiction"
    LLM_PROMPT_VLM = "llm_prompt_vlm"
    LLM_PROMPT_OTHER = "llm_prompt_other"


class PhaseStatus(str, Enum):
    """Enumeration of phase execution states.

    Lifecycle:
        PENDING → IN_PROGRESS → (COMPLETED | FAILED | SKIPPED)

    - PENDING: Phase is queued but not started
    - IN_PROGRESS: Phase is currently executing
    - COMPLETED: Phase finished successfully
    - FAILED: Phase encountered an error
    - SKIPPED: Phase was not needed for this query (e.g., graph query for vector-only intent)

    Example:
        >>> PhaseStatus.IN_PROGRESS
        <PhaseStatus.IN_PROGRESS: 'in_progress'>
        >>> PhaseStatus.COMPLETED.value
        'completed'
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PhaseEvent(BaseModel):
    """Model for tracking individual phase execution in the RAG pipeline.

    Each PhaseEvent represents one processing step, capturing:
    - Phase type and status
    - Timing information (start, end, duration)
    - Phase-specific metadata (e.g., documents retrieved, LLM tokens)
    - Error information if the phase failed

    Attributes:
        phase_type: Type of processing phase (see PhaseType)
        status: Current execution status (see PhaseStatus)
        start_time: When the phase began execution
        end_time: When the phase completed (None if still running)
        duration_ms: Phase execution time in milliseconds (None if not completed)
        metadata: Phase-specific data (e.g., {"docs_retrieved": 10, "top_k": 5})
        error: Error message if phase failed (None if successful)

    Example:
        >>> from datetime import datetime
        >>> event = PhaseEvent(
        ...     phase_type=PhaseType.VECTOR_SEARCH,
        ...     status=PhaseStatus.COMPLETED,
        ...     start_time=datetime(2025, 1, 1, 12, 0, 0),
        ...     end_time=datetime(2025, 1, 1, 12, 0, 0, 150000),
        ...     duration_ms=150.0,
        ...     metadata={"docs_retrieved": 10, "collection": "documents_v1"}
        ... )
        >>> event.phase_type
        <PhaseType.VECTOR_SEARCH: 'vector_search'>
        >>> event.duration_ms
        150.0

    Serialization:
        >>> event.model_dump()
        {
            "phase_type": "vector_search",
            "status": "completed",
            "start_time": "2025-01-01T12:00:00",
            "end_time": "2025-01-01T12:00:00.150000",
            "duration_ms": 150.0,
            "metadata": {"docs_retrieved": 10, "collection": "documents_v1"},
            "error": None
        }

    Notes:
        - Use PhaseType and PhaseStatus enums for type safety
        - duration_ms should be calculated from (end_time - start_time)
        - metadata is flexible - agents can store phase-specific info
        - Pydantic v2 syntax: use model_dump() instead of dict()

    See Also:
        - PhaseType: All possible phase types
        - PhaseStatus: All possible phase states
        - src/agents/reasoning_data.py: Builder for accumulating events
    """

    phase_type: PhaseType = Field(..., description="Type of processing phase (see PhaseType enum)")
    status: PhaseStatus = Field(..., description="Current execution status (see PhaseStatus enum)")
    start_time: datetime = Field(..., description="Phase start timestamp (UTC)")
    end_time: datetime | None = Field(
        default=None, description="Phase end timestamp (UTC, None if still running)"
    )
    duration_ms: float | None = Field(
        default=None,
        description="Phase execution time in milliseconds (None if not completed)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Phase-specific metadata (e.g., docs retrieved, LLM tokens)",
    )
    error: str | None = Field(
        default=None, description="Error message if phase failed (None if successful)"
    )

    class Config:
        """Pydantic configuration for PhaseEvent model."""

        # Allow arbitrary types for datetime
        arbitrary_types_allowed = True
        # Serialize datetime as ISO string
        json_encoders = {datetime: lambda v: v.isoformat()}
