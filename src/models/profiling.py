"""Pydantic models for user profiling and conversation archiving.

Sprint 17 Feature 17.4: Implicit User Profiling - Conversation Archiving Pipeline (Phase 1)
"""

from typing import Any

from pydantic import BaseModel, Field


class ArchivedConversation(BaseModel):
    """Archived conversation stored in Qdrant."""

    session_id: str = Field(..., description="Unique session ID")
    user_id: str = Field(..., description="User identifier")
    title: str | None = Field(default=None, description="Conversation title (auto-generated or manual)")
    summary: str | None = Field(default=None, description="Conversation summary")
    topics: list[str] = Field(default_factory=list, description="Extracted topics")
    created_at: str = Field(..., description="Conversation creation timestamp (ISO 8601)")
    archived_at: str = Field(..., description="Archiving timestamp (ISO 8601)")
    message_count: int = Field(..., description="Number of messages in conversation")
    full_text: str = Field(..., description="Concatenated conversation text for embedding")
    messages: list[dict[str, Any]] = Field(
        default_factory=list, description="Full conversation messages"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (intents, sources, etc.)"
    )


class ConversationSearchRequest(BaseModel):
    """Request model for semantic conversation search."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    user_id: str | None = Field(
        default=None, description="Filter to specific user (None = current user only)"
    )
    limit: int = Field(default=5, ge=1, le=20, description="Maximum results to return")
    score_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum relevance score"
    )
    date_from: str | None = Field(
        default=None, description="Filter conversations created after this date (ISO 8601)"
    )
    date_to: str | None = Field(
        default=None, description="Filter conversations created before this date (ISO 8601)"
    )


class ConversationSearchResult(BaseModel):
    """Single conversation search result."""

    session_id: str = Field(..., description="Session ID")
    title: str | None = Field(default=None, description="Conversation title")
    summary: str | None = Field(default=None, description="Conversation summary")
    topics: list[str] = Field(default_factory=list, description="Conversation topics")
    created_at: str = Field(..., description="Creation timestamp")
    archived_at: str = Field(..., description="Archiving timestamp")
    message_count: int = Field(..., description="Number of messages")
    relevance_score: float = Field(..., description="Semantic similarity score")
    snippet: str = Field(..., description="Relevant conversation snippet (first 300 chars)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationSearchResponse(BaseModel):
    """Response model for semantic conversation search."""

    query: str = Field(..., description="Original search query")
    results: list[ConversationSearchResult] = Field(
        default_factory=list, description="Search results"
    )
    total_count: int = Field(..., description="Total number of results")
    search_timestamp: str = Field(..., description="Search execution timestamp")


class ArchiveConversationRequest(BaseModel):
    """Request model for manual conversation archiving."""

    reason: str | None = Field(
        default=None, max_length=200, description="Optional reason for archiving"
    )


class ArchiveConversationResponse(BaseModel):
    """Response model for conversation archiving."""

    session_id: str = Field(..., description="Archived session ID")
    status: str = Field(..., description="Archiving status")
    message: str = Field(..., description="Status message")
    archived_at: str = Field(..., description="Archiving timestamp")
    qdrant_point_id: str = Field(..., description="Qdrant vector point ID")


class ArchiveJobStatus(BaseModel):
    """Status of background archiving job."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status (running, completed, failed)")
    conversations_processed: int = Field(..., description="Number of conversations processed")
    conversations_archived: int = Field(..., description="Number of conversations archived")
    conversations_failed: int = Field(..., description="Number of failed archiving attempts")
    started_at: str = Field(..., description="Job start timestamp")
    completed_at: str | None = Field(default=None, description="Job completion timestamp")
    error_message: str | None = Field(default=None, description="Error message if failed")
