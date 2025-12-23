"""Multi-Turn Agent State.

Sprint 63 Feature 63.1: Multi-Turn RAG Template (13 SP)

This module defines the state structure for the multi-turn LangGraph workflow.
"""

from typing import Any

from langgraph.graph import MessagesState
from pydantic import Field

from src.api.models.multi_turn import Contradiction, ConversationTurn


class MultiTurnState(MessagesState):
    """State for multi-turn conversation workflow.

    This state flows through the LangGraph nodes and accumulates:
    - Conversation history
    - Current query context
    - Retrieved documents
    - Detected contradictions
    - Memory summaries
    """

    # Core conversation data
    conversation_history: list[ConversationTurn] = Field(
        default_factory=list, description="Full conversation history"
    )
    current_query: str = Field(default="", description="Current user query")
    enhanced_query: str = Field(
        default="", description="Query enhanced with conversation context"
    )

    # Retrieval results
    current_context: list[dict[str, Any]] = Field(
        default_factory=list, description="Retrieved contexts for current query"
    )

    # Contradiction detection
    contradictions: list[Contradiction] = Field(
        default_factory=list, description="Detected contradictions in conversation"
    )

    # Memory management
    memory_summary: str | None = Field(
        default=None, description="Summary of conversation (generated every N turns)"
    )

    # Metadata
    namespace: str = Field(default="default", description="Namespace to search in")
    conversation_id: str = Field(..., description="Unique conversation identifier")
    turn_number: int = Field(default=1, ge=1, description="Current turn number")
    detect_contradictions: bool = Field(
        default=True, description="Whether to detect contradictions"
    )
    max_history_turns: int = Field(
        default=5, ge=1, le=20, description="Max turns to include in context"
    )

    # Output
    answer: str = Field(default="", description="Generated answer for current query")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata (latency, etc.)"
    )
