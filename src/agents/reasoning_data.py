"""Reasoning Data Builder for Phase Event Accumulation.

Sprint 48 Feature 48.7: ReasoningData Builder (3 SP)

This module provides a builder pattern for accumulating phase events and
supporting data during query processing. The ReasoningData class enables:
- Progressive accumulation of phase events
- Storage of retrieved documents, entities, and memories
- Summary generation for API responses

Usage Example:
    >>> from src.agents.reasoning_data import ReasoningData
    >>> from src.models.phase_event import PhaseEvent, PhaseType, PhaseStatus
    >>> from datetime import datetime
    >>>
    >>> # Create builder
    >>> reasoning = ReasoningData()
    >>>
    >>> # Add phase event
    >>> event = PhaseEvent(
    ...     phase_type=PhaseType.VECTOR_SEARCH,
    ...     status=PhaseStatus.COMPLETED,
    ...     start_time=datetime.now(),
    ...     end_time=datetime.now(),
    ...     duration_ms=150.0,
    ...     metadata={"docs_retrieved": 10}
    ... )
    >>> reasoning.add_phase_event(event)
    >>>
    >>> # Add retrieved data
    >>> reasoning.retrieved_docs.append({"doc_id": "123", "content": "..."})
    >>>
    >>> # Generate summary
    >>> summary = reasoning.to_dict()
    >>> summary
    {
        "phase_events": [...],
        "retrieved_docs_count": 1,
        "graph_entities_count": 0,
        "memories_count": 0
    }

Architecture:
    - Uses dataclass for simplicity and performance
    - Mutable builder pattern (add_phase_event modifies in-place)
    - Provides to_dict() for API serialization
    - Stores full data for internal use, summary for responses

Integration Points:
    - CoordinatorAgent: Creates ReasoningData at query start
    - Individual Agents: Add phase events during execution
    - API Layer: Serializes to_dict() for frontend streaming

Related Features:
    - Sprint 48 Feature 48.1: Phase Event Models (5 SP)
    - Sprint 48 Feature 48.2: CoordinatorAgent Streaming (5 SP)
    - Sprint 48 Feature 48.8: Frontend Phase Display (8 SP)

See Also:
    - src/models/phase_event.py: PhaseEvent model definition
    - src/agents/coordinator.py: Main usage in CoordinatorAgent
    - docs/sprints/SPRINT_48.md: Sprint 48 implementation plan
"""

from dataclasses import dataclass, field
from typing import Any

from src.models.phase_event import PhaseEvent


@dataclass
class ReasoningData:
    """Builder for accumulating reasoning step data during query processing.

    This class provides a mutable container for collecting phase events
    and supporting data (documents, entities, memories) as a query
    progresses through the multi-agent RAG pipeline.

    Attributes:
        phase_events: List of phase events in chronological order
        retrieved_docs: List of retrieved document metadata
        graph_entities: List of graph entities retrieved from Neo4j
        memories: List of memories retrieved from Redis/Graphiti

    Example:
        >>> reasoning = ReasoningData()
        >>> reasoning.add_phase_event(PhaseEvent(...))
        >>> reasoning.retrieved_docs.append({"doc_id": "123", "score": 0.95})
        >>> summary = reasoning.to_dict()

    Design Rationale:
        - dataclass: Lightweight, no Pydantic overhead
        - field(default_factory=list): Avoids mutable default argument issues
        - Mutable: Builder pattern allows agents to modify in-place
        - to_dict(): Generates summary for API responses (not full data)

    Thread Safety:
        - NOT thread-safe (designed for single-threaded query processing)
        - Each query gets its own ReasoningData instance
        - No shared state between concurrent queries

    Performance:
        - Minimal overhead: simple list appends
        - Memory efficient: stores only metadata, not full documents
        - to_dict() is O(n) where n = number of phase events

    See Also:
        - PhaseEvent: Individual phase event model
        - CoordinatorAgent: Creates and manages ReasoningData
    """

    phase_events: list[PhaseEvent] = field(default_factory=list)
    retrieved_docs: list[dict] = field(default_factory=list)
    graph_entities: list[dict] = field(default_factory=list)
    memories: list[dict] = field(default_factory=list)

    def add_phase_event(self, event: PhaseEvent) -> None:
        """Add a phase event to the reasoning data.

        Appends the event to the phase_events list in chronological order.
        This method is called by individual agents as they complete phases.

        Args:
            event: PhaseEvent instance to add

        Example:
            >>> from src.models.phase_event import PhaseEvent, PhaseType, PhaseStatus
            >>> from datetime import datetime
            >>> reasoning = ReasoningData()
            >>> event = PhaseEvent(
            ...     phase_type=PhaseType.VECTOR_SEARCH,
            ...     status=PhaseStatus.COMPLETED,
            ...     start_time=datetime.now(),
            ...     end_time=datetime.now(),
            ...     duration_ms=150.0
            ... )
            >>> reasoning.add_phase_event(event)
            >>> len(reasoning.phase_events)
            1

        Notes:
            - Events should be added in chronological order
            - No deduplication - assumes unique events per phase
            - Modifies self.phase_events in-place
        """
        self.phase_events.append(event)

    def to_dict(self) -> dict:
        """Generate summary dictionary for API responses.

        Creates a JSON-serializable dictionary containing:
        - All phase events (serialized via Pydantic)
        - Counts of retrieved data (not full content)

        This method is called by the API layer to stream reasoning data
        to the frontend for real-time display.

        Returns:
            Dictionary with keys:
                - phase_events: List of serialized PhaseEvent dicts
                - retrieved_docs_count: Number of documents retrieved
                - graph_entities_count: Number of entities retrieved
                - memories_count: Number of memories retrieved

        Example:
            >>> reasoning = ReasoningData()
            >>> reasoning.retrieved_docs.append({"doc_id": "123"})
            >>> reasoning.graph_entities.append({"entity_id": "456"})
            >>> summary = reasoning.to_dict()
            >>> summary
            {
                "phase_events": [],
                "retrieved_docs_count": 1,
                "graph_entities_count": 1,
                "memories_count": 0
            }

        Design Rationale:
            - Returns counts, not full data (minimize response size)
            - Full documents are stored in retrieved_contexts (AgentState)
            - Serializes PhaseEvent via Pydantic model_dump()

        Performance:
            - O(n) where n = number of phase events
            - model_dump() is fast (Pydantic v2 Rust core)
            - Counts are O(1) (len() on lists)

        Notes:
            - Use this for API responses, not internal processing
            - For full data, access attributes directly (phase_events, retrieved_docs)
            - Frontend uses this to display thinking process
        """
        return {
            "phase_events": [e.model_dump(mode='json') for e in self.phase_events],
            "retrieved_docs_count": len(self.retrieved_docs),
            "graph_entities_count": len(self.graph_entities),
            "memories_count": len(self.memories),
        }
