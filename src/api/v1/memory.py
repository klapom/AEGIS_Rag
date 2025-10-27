"""Memory API Endpoints - Sprint 7 Feature 7.6.

FastAPI endpoints for the 3-layer memory system:
- Layer 1 (SHORT_TERM): Redis working memory for recent context
- Layer 2 (LONG_TERM): Qdrant vector store for semantic facts
- Layer 3 (EPISODIC): Graphiti temporal graph for episodic memory

Provides:
- Unified memory search across layers
- Point-in-time temporal queries
- Session context management
- Manual consolidation triggers
- Memory statistics and monitoring
"""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.api.middleware import limiter
from src.components.memory import (
    get_consolidation_pipeline,
    get_memory_router,
    get_redis_memory,
    get_temporal_query,
)
from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


# ============================================================================
# Request/Response Models
# ============================================================================


class MemorySearchRequest(BaseModel):
    """Request model for unified memory search."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query text",
        examples=["What did we discuss about RAG architecture?"],
    )
    layers: list[str] | None = Field(
        default=None,
        description="Memory layers to search. If None, automatically routes based on query. "
        "Options: 'short_term', 'long_term', 'episodic'",
        examples=[["short_term", "episodic"]],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum results per layer",
    )
    session_id: str | None = Field(
        default=None,
        description="Session ID for context-aware search",
        examples=["session_123abc"],
    )
    time_window_hours: int | None = Field(
        default=None,
        ge=1,
        le=720,  # Max 30 days
        description="Limit temporal search to recent N hours",
    )

    class Config:
        validate_assignment = True
        str_strip_whitespace = True


class MemorySearchResult(BaseModel):
    """Individual memory search result."""

    layer: str = Field(description="Memory layer the result came from")
    content: str = Field(description="Result content or text")
    score: float | None = Field(default=None, description="Relevance score if available")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Result metadata")


class MemorySearchResponse(BaseModel):
    """Response model for memory search."""

    query: str
    results_by_layer: dict[str, list[MemorySearchResult]] = Field(
        description="Results grouped by memory layer"
    )
    total_results: int
    layers_searched: list[str]
    search_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Search execution metadata"
    )


class PointInTimeQueryRequest(BaseModel):
    """Request model for point-in-time temporal queries."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Entity or query to search for at point in time",
        examples=["Claude AI"],
    )
    timestamp: datetime = Field(
        ...,
        description="Point in time to query (valid time)",
        examples=["2024-01-15T10:30:00Z"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum results to return",
    )

    class Config:
        validate_assignment = True
        str_strip_whitespace = True


class PointInTimeQueryResponse(BaseModel):
    """Response model for point-in-time queries."""

    query: str
    timestamp: datetime
    results: list[dict[str, Any]] = Field(description="Entity states at the specified time")
    total_results: int


class SessionContextResponse(BaseModel):
    """Response model for session context retrieval."""

    session_id: str
    messages: list[dict[str, str]] = Field(description="Conversation messages in the session")
    message_count: int
    summary: dict[str, Any] = Field(
        default_factory=dict, description="Session summary across layers"
    )


class ConsolidationRequest(BaseModel):
    """Request model for manual memory consolidation."""

    consolidate_to_qdrant: bool = Field(
        default=True,
        description="Enable Redis → Qdrant consolidation",
    )
    consolidate_conversations: bool = Field(
        default=True,
        description="Enable Redis → Graphiti conversation consolidation",
    )
    active_sessions: list[str] | None = Field(
        default=None,
        description="List of active session IDs to consolidate. If None, no conversation consolidation.",
        examples=[["session_123", "session_456"]],
    )

    class Config:
        validate_assignment = True


class ConsolidationResponse(BaseModel):
    """Response model for consolidation operations."""

    status: str
    started_at: str
    completed_at: str | None = None
    qdrant_consolidation: dict[str, Any] | None = Field(
        default=None,
        description="Statistics for Redis → Qdrant consolidation",
    )
    conversation_consolidations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Results for each conversation consolidation",
    )


class MemoryStatsResponse(BaseModel):
    """Response model for memory system statistics."""

    short_term: dict[str, Any] = Field(description="Redis working memory statistics")
    long_term: dict[str, Any] = Field(description="Qdrant vector store statistics")
    episodic: dict[str, Any] = Field(description="Graphiti episodic memory statistics")
    consolidation: dict[str, Any] = Field(description="Memory consolidation statistics")


class SessionDeleteResponse(BaseModel):
    """Response model for session deletion."""

    session_id: str
    deleted: bool
    message: str


# ============================================================================
# Endpoint Implementations
# ============================================================================


@router.post("/search", response_model=MemorySearchResponse)
@limiter.limit("20/minute")
async def unified_memory_search(
    request: Request,
    search_params: MemorySearchRequest,
) -> MemorySearchResponse:
    """Search across multiple memory layers with intelligent routing.

    This endpoint performs unified search across the 3-layer memory system:
    - Layer 1 (SHORT_TERM): Redis working memory for recent context
    - Layer 2 (LONG_TERM): Qdrant vector store for semantic facts
    - Layer 3 (EPISODIC): Graphiti temporal graph for episodic memory

    If `layers` is not specified, the system automatically routes the query
    to appropriate layers based on temporal signals and query intent.

    Rate limited to 20 requests per minute.

    Args:
        request: FastAPI request (for rate limiting)
        search_params: Memory search parameters

    Returns:
        MemorySearchResponse with results grouped by layer

    Raises:
        HTTPException: 400 for invalid parameters, 500 for internal errors

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/memory/search" \\
             -H "Content-Type: application/json" \\
             -d '{
                "query": "What did we discuss about RAG?",
                "session_id": "session_123",
                "top_k": 5
             }'
        ```
    """
    try:
        # Get or create memory router for this session
        memory_router = get_memory_router(session_id=search_params.session_id)

        # Perform multi-layer search
        results = await memory_router.search_memory(
            query=search_params.query,
            session_id=search_params.session_id,
            limit=search_params.top_k,
            time_window_hours=search_params.time_window_hours,
        )

        # Transform results to response format
        results_by_layer = {}
        total_results = 0

        for layer_name, layer_results in results.items():
            formatted_results = []
            for result in layer_results:
                # Extract common fields
                content = result.get("content", "")
                if not content and "text" in result:
                    content = result.get("text", "")

                formatted_result = MemorySearchResult(
                    layer=layer_name,
                    content=content,
                    score=result.get("score") or result.get("relevance_score"),
                    metadata={
                        k: v
                        for k, v in result.items()
                        if k not in ["content", "text", "layer", "score", "relevance_score"]
                    },
                )
                formatted_results.append(formatted_result)

            results_by_layer[layer_name] = formatted_results
            total_results += len(formatted_results)

        logger.info(
            "Memory search completed",
            query=search_params.query[:100],
            total_results=total_results,
            layers=list(results.keys()),
        )

        return MemorySearchResponse(
            query=search_params.query,
            results_by_layer=results_by_layer,
            total_results=total_results,
            layers_searched=list(results.keys()),
            search_metadata={
                "session_id": search_params.session_id,
                "time_window_hours": search_params.time_window_hours,
            },
        )

    except MemoryError as e:
        logger.error("Memory search failed", error=str(e), query=search_params.query)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory search failed: {e}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error in memory search",
            error=str(e),
            query=search_params.query,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during memory search",
        ) from e


@router.post("/temporal/point-in-time", response_model=PointInTimeQueryResponse)
@limiter.limit("15/minute")
async def point_in_time_query(
    request: Request,
    query_params: PointInTimeQueryRequest,
) -> PointInTimeQueryResponse:
    """Query memory state at a specific point in time (bi-temporal query).

    Retrieves entity or memory states as they existed at a specific point in time,
    using bi-temporal modeling (valid time + transaction time).

    This is useful for:
    - Historical analysis: "What did we know about X on date Y?"
    - Temporal reasoning: "When did entity Z change?"
    - Audit trails: "What was the state before/after an event?"

    Rate limited to 15 requests per minute.

    Args:
        request: FastAPI request (for rate limiting)
        query_params: Point-in-time query parameters

    Returns:
        PointInTimeQueryResponse with historical results

    Raises:
        HTTPException: 400 for invalid parameters, 500 for internal errors

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/memory/temporal/point-in-time" \\
             -H "Content-Type: application/json" \\
             -d '{
                "query": "OpenAI",
                "timestamp": "2024-01-15T10:30:00Z",
                "top_k": 5
             }'
        ```
    """
    try:
        temporal_query = get_temporal_query()

        # Query entity at point in time
        entity_result = await temporal_query.query_point_in_time(
            entity_name=query_params.query,
            valid_time=query_params.timestamp,
        )

        results = []
        if entity_result:
            results.append(entity_result)

        logger.info(
            "Point-in-time query completed",
            query=query_params.query,
            timestamp=query_params.timestamp.isoformat(),
            results_found=len(results),
        )

        return PointInTimeQueryResponse(
            query=query_params.query,
            timestamp=query_params.timestamp,
            results=results,
            total_results=len(results),
        )

    except MemoryError as e:
        logger.error(
            "Point-in-time query failed",
            error=str(e),
            query=query_params.query,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Point-in-time query failed: {e}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error in point-in-time query",
            error=str(e),
            query=query_params.query,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during point-in-time query",
        ) from e


@router.get("/session/{session_id}", response_model=SessionContextResponse)
@limiter.limit("30/minute")
async def get_session_context(
    request: Request,
    session_id: str,
) -> SessionContextResponse:
    """Retrieve full context for a conversation session.

    Returns all messages and metadata for a specific session from
    short-term (Redis) memory.

    Rate limited to 30 requests per minute.

    Args:
        request: FastAPI request (for rate limiting)
        session_id: Session identifier

    Returns:
        SessionContextResponse with session messages and summary

    Raises:
        HTTPException: 404 if session not found, 500 for internal errors

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/memory/session/session_123"
        ```
    """
    try:
        redis_memory = get_redis_memory()
        memory_router = get_memory_router(session_id=session_id)

        # Retrieve conversation context
        messages = await redis_memory.get_conversation_context(session_id)

        if messages is None:
            logger.warning("Session not found", session_id=session_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found or expired",
            )

        # Get session summary across all layers
        summary = await memory_router.get_session_summary(session_id=session_id)

        logger.info(
            "Retrieved session context",
            session_id=session_id,
            message_count=len(messages),
        )

        return SessionContextResponse(
            session_id=session_id,
            messages=messages,
            message_count=len(messages),
            summary=summary,
        )

    except HTTPException:
        raise
    except MemoryError as e:
        logger.error(
            "Failed to retrieve session context",
            error=str(e),
            session_id=session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session context: {e}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error retrieving session context",
            error=str(e),
            session_id=session_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving session context",
        ) from e


@router.post("/consolidate", response_model=ConsolidationResponse)
@limiter.limit("5/hour")
async def trigger_consolidation(
    request: Request,
    consolidation_params: ConsolidationRequest = ConsolidationRequest(),
) -> ConsolidationResponse:
    """Manually trigger memory consolidation between layers.

    Consolidates memories from short-term (Redis) to long-term (Qdrant)
    and/or episodic (Graphiti) storage based on access patterns and policies.

    Consolidation moves frequently accessed or important memories from
    fast, temporary storage to permanent, structured storage.

    Rate limited to 5 requests per hour (expensive operation).

    Args:
        request: FastAPI request (for rate limiting)
        consolidation_params: Consolidation configuration options

    Returns:
        ConsolidationResponse with consolidation statistics

    Raises:
        HTTPException: 500 for internal errors

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/memory/consolidate" \\
             -H "Content-Type: application/json" \\
             -d '{
                "consolidate_to_qdrant": true,
                "consolidate_conversations": true,
                "active_sessions": ["session_123", "session_456"]
             }'
        ```
    """
    try:
        pipeline = get_consolidation_pipeline()

        # Run consolidation cycle
        results = await pipeline.run_consolidation_cycle(
            consolidate_to_qdrant=consolidation_params.consolidate_to_qdrant,
            consolidate_conversations=consolidation_params.consolidate_conversations,
            active_sessions=consolidation_params.active_sessions,
        )

        logger.info(
            "Manual consolidation completed",
            qdrant_enabled=consolidation_params.consolidate_to_qdrant,
            conversations_enabled=consolidation_params.consolidate_conversations,
            sessions_count=len(consolidation_params.active_sessions or []),
        )

        return ConsolidationResponse(
            status="success",
            started_at=results.get("started_at", ""),
            completed_at=results.get("completed_at"),
            qdrant_consolidation=results.get("qdrant_consolidation"),
            conversation_consolidations=results.get("conversation_consolidations", []),
        )

    except MemoryError as e:
        logger.error("Consolidation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory consolidation failed: {e}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error during consolidation",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during consolidation",
        ) from e


@router.get("/stats", response_model=MemoryStatsResponse)
@limiter.limit("30/minute")
async def get_memory_stats(
    request: Request,
) -> MemoryStatsResponse:
    """Get comprehensive memory system statistics across all layers.

    Provides metrics and statistics for:
    - Redis short-term memory (connection, keys, TTL info)
    - Qdrant long-term memory (collection stats, point counts)
    - Graphiti episodic memory (entity/relationship counts)
    - Consolidation pipeline (last run, success rates)

    Rate limited to 30 requests per minute.

    Args:
        request: FastAPI request (for rate limiting)

    Returns:
        MemoryStatsResponse with statistics for all layers

    Raises:
        HTTPException: 500 for internal errors

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/memory/stats"
        ```
    """
    try:
        from src.core.config import settings

        redis_memory = get_redis_memory()

        # Redis statistics
        redis_stats = {
            "connected": False,
            "connection_url": settings.redis_memory_url,
            "default_ttl_seconds": settings.redis_memory_ttl_seconds,
        }

        try:
            redis_client = await redis_memory.client
            await redis_client.ping()
            redis_stats["connected"] = True

            # Get key count (approximate)
            info = await redis_client.info("keyspace")
            redis_stats["keyspace_info"] = info

        except Exception as e:
            logger.warning("Failed to get Redis stats", error=str(e))
            redis_stats["error"] = str(e)

        # Qdrant statistics
        long_term_stats = {
            "available": True,
            "note": "Qdrant collection statistics require dedicated endpoint",
        }

        # Graphiti/Neo4j statistics
        episodic_stats = {
            "enabled": settings.graphiti_enabled,
            "available": settings.graphiti_enabled,
        }

        if settings.graphiti_enabled:
            try:
                from src.components.graph_rag.neo4j_client import get_neo4j_client

                neo4j_client = get_neo4j_client()
                neo4j_connected = await neo4j_client.verify_connectivity()
                episodic_stats["neo4j_connected"] = neo4j_connected

                if neo4j_connected:
                    # Get entity/relationship counts
                    count_query = """
                    MATCH (e:Entity)
                    WITH count(e) as entity_count
                    MATCH ()-[r]->()
                    RETURN entity_count, count(r) as relationship_count
                    """
                    results = await neo4j_client.execute_read(count_query)
                    if results:
                        episodic_stats["entity_count"] = results[0].get("entity_count", 0)
                        episodic_stats["relationship_count"] = results[0].get(
                            "relationship_count", 0
                        )

            except Exception as e:
                logger.warning("Failed to get Graphiti stats", error=str(e))
                episodic_stats["error"] = str(e)
        else:
            episodic_stats["note"] = "Graphiti disabled in settings"

        # Consolidation statistics
        consolidation_stats = {
            "enabled": settings.memory_consolidation_enabled,
            "interval_minutes": settings.memory_consolidation_interval_minutes,
            "min_access_count": settings.memory_consolidation_min_access_count,
        }

        logger.info("Retrieved memory system statistics")

        return MemoryStatsResponse(
            short_term=redis_stats,
            long_term=long_term_stats,
            episodic=episodic_stats,
            consolidation=consolidation_stats,
        )

    except Exception as e:
        logger.error(
            "Failed to get memory statistics",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory statistics",
        ) from e


@router.delete("/session/{session_id}", response_model=SessionDeleteResponse)
@limiter.limit("10/minute")
async def delete_session(
    request: Request,
    session_id: str,
) -> SessionDeleteResponse:
    """Delete a session and all associated short-term memory.

    Removes the session's conversation context from Redis working memory.
    Note: This only affects short-term memory. Episodic memories in Graphiti
    are not deleted.

    Rate limited to 10 requests per minute.

    Args:
        request: FastAPI request (for rate limiting)
        session_id: Session identifier to delete

    Returns:
        SessionDeleteResponse with deletion status

    Raises:
        HTTPException: 500 for internal errors

    Example:
        ```bash
        curl -X DELETE "http://localhost:8000/api/v1/memory/session/session_123"
        ```
    """
    try:
        redis_memory = get_redis_memory()

        # Delete conversation context
        deleted = await redis_memory.delete(
            key=f"conversation:{session_id}",
            namespace="context",
        )

        if deleted:
            logger.info("Session deleted", session_id=session_id)
            return SessionDeleteResponse(
                session_id=session_id,
                deleted=True,
                message=f"Session '{session_id}' deleted successfully",
            )
        else:
            logger.warning("Session not found for deletion", session_id=session_id)
            return SessionDeleteResponse(
                session_id=session_id,
                deleted=False,
                message=f"Session '{session_id}' not found or already expired",
            )

    except MemoryError as e:
        logger.error(
            "Failed to delete session",
            error=str(e),
            session_id=session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {e}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error deleting session",
            error=str(e),
            session_id=session_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting session",
        ) from e
