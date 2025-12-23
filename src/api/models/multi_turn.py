"""Multi-Turn RAG Models.

Sprint 63 Feature 63.1: Multi-Turn RAG Template (13 SP)

This module defines Pydantic models for multi-turn conversation state,
contradiction detection, and API requests/responses.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Source document metadata for citations."""

    text: str = Field(..., description="Document text content")
    title: str | None = Field(default=None, description="Document title")
    source: str | None = Field(default=None, description="Source file path")
    score: float | None = Field(default=None, description="Relevance score")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationTurn(BaseModel):
    """A single conversation turn (Q&A pair)."""

    query: str = Field(..., description="User query")
    answer: str = Field(..., description="Generated answer")
    sources: list[Source] = Field(default_factory=list, description="Source documents used")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Turn timestamp"
    )
    intent: str | None = Field(default=None, description="Detected query intent")


class Contradiction(BaseModel):
    """Detected contradiction between conversation turns."""

    current_info: str = Field(..., description="Current information (conflicting)")
    previous_info: str = Field(..., description="Previous information (conflicting)")
    turn_index: int = Field(..., ge=0, description="Index of previous turn with contradiction")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Contradiction confidence (0-1)")
    explanation: str | None = Field(default=None, description="Explanation of the contradiction")


class MultiTurnRequest(BaseModel):
    """Request for multi-turn conversation."""

    query: str = Field(..., min_length=1, max_length=5000, description="User query")
    conversation_id: str = Field(..., description="Conversation ID for tracking state")
    namespace: str = Field(default="default", description="Namespace to search in")
    detect_contradictions: bool = Field(default=True, description="Enable contradiction detection")
    max_history_turns: int = Field(
        default=5, ge=1, le=20, description="Max conversation turns to include in context"
    )


class MultiTurnResponse(BaseModel):
    """Response for multi-turn conversation."""

    answer: str = Field(..., description="Generated answer")
    query: str = Field(..., description="Original user query")
    conversation_id: str = Field(..., description="Conversation ID")
    sources: list[Source] = Field(default_factory=list, description="Source documents used")
    contradictions: list[Contradiction] = Field(
        default_factory=list, description="Detected contradictions"
    )
    memory_summary: str | None = Field(default=None, description="Conversation summary (if any)")
    turn_number: int = Field(..., ge=1, description="Current turn number")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
