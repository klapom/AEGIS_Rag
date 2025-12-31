"""Agent State Management for LangGraph.

This module defines the state structure used by all agents in the LangGraph orchestration.
State is passed between nodes and tracks the complete conversation and retrieval context.

Sprint 4 Feature 4.1: LangGraph State Management
Uses MessagesState as the base to integrate with LangChain message history.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

from src.models.phase_event import PhaseEvent


class RetrievedContext(BaseModel):
    """A single retrieved context/document."""

    id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text content")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0 to 1.0)")
    source: str = Field(default="unknown", description="Document source")
    document_id: str = Field(default="", description="Parent document ID")
    rank: int = Field(default=0, ge=0, description="Ranking position")
    search_type: Literal["vector", "bm25", "hybrid", "graph", "graph_local", "graph_global"] = Field(
        default="hybrid", description="Search type used"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchMetadata(BaseModel):
    """Metadata about search execution."""

    latency_ms: float = Field(..., ge=0.0, description="Search latency in milliseconds")
    result_count: int = Field(..., ge=0, description="Number of results returned")
    search_mode: Literal["vector", "bm25", "hybrid", "graph", "graph_local", "graph_global"] = Field(
        default="hybrid", description="Search mode used"
    )
    vector_results_count: int = Field(default=0, ge=0, description="Vector search result count")
    bm25_results_count: int = Field(default=0, ge=0, description="BM25 search result count")
    reranking_applied: bool = Field(default=False, description="Whether reranking was applied")
    error: str | None = Field(default=None, description="Error message if search failed")


class AgentState(MessagesState):
    """State passed between LangGraph nodes.

    This is the central state object that flows through the entire agent graph.
    Each agent reads from and writes to this state.

    Inherits from MessagesState to maintain message history and integrates
    with LangChain's message-based conversation flow.

    Attributes:
        messages: List of messages (inherited from MessagesState)
        query: User's original query
        intent: Detected intent (vector, hybrid, graph, direct)
        retrieved_contexts: List of retrieved documents
        search_mode: Search mode to use
        graph_query_result: Results from graph RAG query (Sprint 5)
        metadata: Additional metadata for execution tracking
        namespaces: List of namespaces to search in (Sprint 41 Feature 41.4)
    """

    query: str = Field(default="", description="Original user query")
    intent: str = Field(
        default="hybrid",
        description="Detected query intent (vector, graph, hybrid, direct)",
    )
    retrieved_contexts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Retrieved document contexts from search",
    )
    search_mode: Literal["vector", "graph", "hybrid"] = Field(
        default="hybrid",
        description="Search mode to use for retrieval",
    )
    graph_query_result: dict[str, Any] | None = Field(
        default=None,
        description="Results from graph RAG query (Sprint 5)",
    )
    memory_results: dict[str, Any] | None = Field(
        default=None,
        description="Results from memory retrieval (Sprint 7)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for execution tracking",
    )
    citation_map: dict[int, dict[str, Any]] = Field(
        default_factory=dict,
        description="Map of citation numbers to source metadata (Sprint 27 Feature 27.10)",
    )
    answer: str = Field(
        default="",
        description="Generated answer from LLM (Sprint 51 Fix)",
    )
    namespaces: list[str] | None = Field(
        default=None,
        description='Namespaces to search in. Defaults to ["default", "general"] (Sprint 41 Feature 41.4)',
    )
    phase_event: PhaseEvent | None = Field(
        default=None,
        description="Latest phase event emitted by the current node (Sprint 48 Feature 48.2)",
    )
    phase_events: list[PhaseEvent] = Field(
        default_factory=list,
        description="List of all phase events for streaming (Sprint 51 Feature 51.1)",
    )


class QueryMetadata(BaseModel):
    """Metadata about query execution for observability.

    Attributes:
        agent_path: List of agents that processed the query
        retrieval_count: Number of documents retrieved
        latency_ms: Total query latency in milliseconds
        search_mode: Search mode used
        timestamp: Query timestamp in ISO format
    """

    agent_path: list[str] = Field(
        default_factory=list,
        description="Ordered list of agents that processed this query",
    )
    retrieval_count: int = Field(
        default=0,
        ge=0,
        description="Total number of documents retrieved",
    )
    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="Total query latency in milliseconds",
    )
    search_mode: str = Field(
        default="hybrid",
        description="Search mode used for retrieval",
    )
    timestamp: str | None = Field(
        default=None,
        description="Query timestamp in ISO format",
    )


def create_initial_state(
    query: str,
    intent: str = "hybrid",
    namespaces: list[str] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Create initial agent state from user query.

    Args:
        query: User's query string
        intent: Detected intent (default: "hybrid")
        namespaces: Namespaces to search in (default: None, will use ["default", "general"])
        session_id: Session identifier for real-time phase event streaming (Sprint 52)

    Returns:
        Dictionary representing the initial AgentState
    """
    return {
        "messages": [],
        "query": query,
        "intent": intent,
        "retrieved_contexts": [],
        "search_mode": intent if intent in ["vector", "graph", "hybrid"] else "hybrid",
        "namespaces": namespaces,
        "session_id": session_id,  # Sprint 52: For real-time phase events
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "agent_path": [],
        },
    }


def update_state_metadata(
    state: dict[str, Any],
    agent_name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Update state metadata with agent execution info.

    Args:
        state: Current agent state
        agent_name: Name of the agent updating the state
        **kwargs: Additional metadata fields to update

    Returns:
        Updated state dictionary
    """
    if "metadata" not in state:
        state["metadata"] = {}

    if "agent_path" not in state["metadata"]:
        state["metadata"]["agent_path"] = []

    # Add agent to path if not already the last entry
    if not state["metadata"]["agent_path"] or state["metadata"]["agent_path"][-1] != agent_name:
        state["metadata"]["agent_path"].append(agent_name)

    # Update additional metadata
    state["metadata"].update(kwargs)

    return state
