"""Admin API endpoints for system statistics and utilities.

Sprint 16 Feature 16.3: Original admin module
Sprint 53 Feature 53.3: Indexing endpoints moved to admin_indexing.py

This module provides endpoints for:
- System statistics (/stats)
- Namespace management (/namespaces)
- Relation synonym overrides (/graph/relation-synonyms)

For indexing endpoints, see admin_indexing.py
For cost endpoints, see admin_costs.py
For LLM config endpoints, see admin_llm.py
For graph analytics, see admin_graph.py
"""

from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.components.shared.embedding_service import get_embedding_service
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# Sprint 53: Import reindex timestamp function from admin_indexing
from src.api.v1.admin_indexing import get_last_reindex_timestamp

# ============================================================================
# Sprint 17 Feature 17.6: Admin Statistics API
# ============================================================================


class SystemStats(BaseModel):
    """System statistics for admin dashboard.

    Sprint 17 Feature 17.6: Admin Statistics API
    """

    # Qdrant statistics
    qdrant_total_chunks: int = Field(..., description="Total chunks indexed in Qdrant")
    qdrant_collection_name: str = Field(..., description="Qdrant collection name")
    qdrant_vector_dimension: int = Field(..., description="Vector dimension (BGE-M3: 1024)")

    # BM25 statistics (if available)
    bm25_corpus_size: int | None = Field(None, description="BM25 corpus size (number of documents)")

    # Neo4j / LightRAG statistics
    neo4j_total_entities: int | None = Field(None, description="Total entities in Neo4j graph")
    neo4j_total_relations: int | None = Field(
        None, description="Total relationships in Neo4j graph"
    )

    # System metadata
    last_reindex_timestamp: str | None = Field(
        None, description="Timestamp of last re-indexing operation"
    )
    embedding_model: str = Field(..., description="Current embedding model name")

    # Additional stats
    total_conversations: int | None = Field(None, description="Total active conversations in Redis")


@router.get("/stats", response_model=SystemStats)
async def get_system_stats() -> SystemStats:
    """Get comprehensive system statistics for admin dashboard.

    Sprint 17 Feature 17.6: Admin Statistics API

    Returns statistics from:
    - Qdrant (vector database)
    - BM25 (keyword search corpus)
    - Neo4j/LightRAG (knowledge graph)
    - Redis (conversation storage)
    - System configuration

    **Example Response:**
    ```json
    {
      "qdrant_total_chunks": 1523,
      "qdrant_collection_name": "aegis_documents",
      "qdrant_vector_dimension": 1024,
      "bm25_corpus_size": 342,
      "neo4j_total_entities": 856,
      "neo4j_total_relations": 1204,
      "neo4j_total_chunks": 1523,
      "last_reindex_timestamp": "2025-10-29T10:30:00Z",
      "embedding_model": "BAAI/bge-m3",
      "total_conversations": 15
    }
    ```

    Returns:
        SystemStats with comprehensive system statistics

    Raises:
        HTTPException: If statistics retrieval fails
    """
    # TD-41: Enhanced logging for request tracking
    logger.info(
        "admin_stats_endpoint_called",
        endpoint="/api/v1/admin/stats",
        method="GET",
        note="Sprint 18 TD-41: Tracking stats request",
    )

    try:
        # TD-41: Log stats collection start
        logger.info("stats_collection_started", phase="initialization")

        # Qdrant statistics
        logger.info("stats_collection_phase", phase="qdrant", status="starting")
        qdrant_client = get_qdrant_client()
        embedding_service = get_embedding_service()
        collection_name = settings.qdrant_collection
        logger.info("qdrant_clients_initialized", collection=collection_name)

        try:
            collection_info = await qdrant_client.get_collection_info(collection_name)
            if collection_info:
                qdrant_total_chunks = collection_info.points_count
                logger.info(
                    "qdrant_stats_retrieved", chunks=qdrant_total_chunks, collection=collection_name
                )
            else:
                logger.warning("collection_not_found", collection=collection_name)
                qdrant_total_chunks = 0
        except Exception as e:
            logger.warning("failed_to_get_qdrant_stats", error=str(e), exc_info=True)
            qdrant_total_chunks = 0

        # BM25 statistics (from HybridSearch)
        logger.info("stats_collection_phase", phase="bm25", status="starting")
        bm25_corpus_size = None
        try:
            from src.api.v1.retrieval import get_hybrid_search

            hybrid_search = get_hybrid_search()
            if hybrid_search.bm25_search.is_fitted():
                bm25_corpus_size = hybrid_search.bm25_search.get_corpus_size()
                logger.info("bm25_stats_retrieved", corpus_size=bm25_corpus_size)
            else:
                logger.debug("bm25_not_fitted")
        except Exception as e:
            logger.debug("bm25_stats_unavailable", error=str(e))

        # Neo4j statistics (direct Neo4j client)
        logger.info("stats_collection_phase", phase="neo4j", status="starting")
        neo4j_total_entities = None
        neo4j_total_relations = None

        try:
            from src.components.graph_rag.neo4j_client import get_neo4j_client

            neo4j_client = get_neo4j_client()
            logger.info("neo4j_client_initialized")

            # Query Neo4j for statistics
            # Note: LightRAG uses "base" label for entities, not "Entity"
            query_entities = "MATCH (e:base) RETURN count(e) as count"
            query_relations = "MATCH ()-[r]->() RETURN count(r) as count"

            # Execute queries
            logger.info("executing_neo4j_query", query="entities")
            entities_result = await neo4j_client.execute_query(query_entities)
            if entities_result and len(entities_result) > 0:
                neo4j_total_entities = entities_result[0].get("count", 0)
                logger.info("neo4j_entities_retrieved", count=neo4j_total_entities)

            logger.info("executing_neo4j_query", query="relations")
            relations_result = await neo4j_client.execute_query(query_relations)
            if relations_result and len(relations_result) > 0:
                neo4j_total_relations = relations_result[0].get("count", 0)
                logger.info("neo4j_relations_retrieved", count=neo4j_total_relations)

        except Exception as e:
            logger.warning("failed_to_get_neo4j_stats", error=str(e), exc_info=True)

        # Redis conversation statistics
        logger.info("stats_collection_phase", phase="redis", status="starting")
        total_conversations = None
        try:
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client
            logger.info("redis_client_initialized")

            # Count conversation keys
            conversation_count = 0
            cursor = 0
            scan_iterations = 0
            while True:
                cursor, keys = await redis_client.scan(
                    cursor=cursor, match="conversation:*", count=100
                )
                conversation_count += len(keys)
                scan_iterations += 1
                if cursor == 0:
                    break

            total_conversations = conversation_count
            logger.info(
                "redis_stats_retrieved",
                conversations=total_conversations,
                scan_iterations=scan_iterations,
            )
        except Exception as e:
            logger.warning("failed_to_get_redis_stats", error=str(e), exc_info=True)

        # Sprint 33: Get last reindex timestamp from Redis
        last_reindex_timestamp = await get_last_reindex_timestamp()

        # TD-41: Log final stats assembly
        logger.info("stats_collection_phase", phase="assembly", status="starting")

        stats = SystemStats(
            qdrant_total_chunks=qdrant_total_chunks,
            qdrant_collection_name=collection_name,
            qdrant_vector_dimension=embedding_service.embedding_dim,
            bm25_corpus_size=bm25_corpus_size,
            neo4j_total_entities=neo4j_total_entities,
            neo4j_total_relations=neo4j_total_relations,
            last_reindex_timestamp=last_reindex_timestamp,
            embedding_model=embedding_service.model_name,
            total_conversations=total_conversations,
        )

        logger.info(
            "admin_stats_successfully_retrieved",
            stats=stats.model_dump(),
            note="Sprint 18 TD-41: Stats successfully assembled and ready to return",
        )

        return stats

    except Exception as e:
        logger.error(
            "admin_stats_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
            note="Sprint 18 TD-41: Stats retrieval failed with exception",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system statistics: {str(e)}",
        ) from e


# ============================================================================
# Sprint 42: Namespace Management API
# ============================================================================


class NamespaceResponse(BaseModel):
    """Response model for namespace information."""

    namespace_id: str = Field(..., description="Unique namespace identifier")
    namespace_type: str = Field(..., description="Type: general, project, evaluation, test")
    document_count: int = Field(..., description="Number of documents in namespace")
    description: str = Field(default="", description="Optional namespace description")


class NamespaceListResponse(BaseModel):
    """Response model for namespace list."""

    namespaces: list[NamespaceResponse] = Field(..., description="List of available namespaces")
    total_count: int = Field(..., description="Total number of namespaces")


@router.get(
    "/namespaces",
    response_model=NamespaceListResponse,
    summary="List available namespaces",
    description="Get all available namespaces with document counts for project/search filtering.",
)
async def list_namespaces() -> NamespaceListResponse:
    """List all available namespaces.

    Sprint 42: Namespace selection for search UI.

    Returns:
        NamespaceListResponse with all namespaces and their document counts.
    """
    logger.info("listing_namespaces")

    try:
        from src.core.namespace import NamespaceManager

        manager = NamespaceManager()
        namespace_infos = await manager.list_namespaces()

        namespaces = [
            NamespaceResponse(
                namespace_id=ns.namespace_id,
                namespace_type=ns.namespace_type,
                document_count=ns.document_count,
                description=ns.description,
            )
            for ns in namespace_infos
        ]

        logger.info("namespaces_listed", count=len(namespaces))

        return NamespaceListResponse(
            namespaces=namespaces,
            total_count=len(namespaces),
        )

    except Exception as e:
        logger.error("failed_to_list_namespaces", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list namespaces: {str(e)}",
        ) from e

# ============================================================================
# Sprint 49 Feature 49.8: Manual Relation Synonym Overrides
# ============================================================================


class AddRelationOverrideRequest(BaseModel):
    """Request model for adding a relation synonym override.

    Sprint 49 Feature 49.8: Manual synonym overrides for relation deduplication.
    """

    from_type: str = Field(
        ...,
        description="Relation type to map (e.g., 'USES', 'ACTED_IN')",
        min_length=1,
    )
    to_type: str = Field(
        ...,
        description="Target canonical type (e.g., 'USED_BY', 'STARRED_IN')",
        min_length=1,
    )


class RelationOverrideResponse(BaseModel):
    """Response model for relation synonym override operations.

    Sprint 49 Feature 49.8: Manual synonym overrides for relation deduplication.
    """

    from_type: str = Field(..., description="Relation type that was mapped")
    to_type: str = Field(..., description="Canonical type it maps to")
    status: Literal["created", "deleted"] = Field(..., description="Operation status")


class RelationOverridesListResponse(BaseModel):
    """Response model for listing all relation synonym overrides.

    Sprint 49 Feature 49.8: Manual synonym overrides for relation deduplication.
    """

    overrides: dict[str, str] = Field(
        ...,
        description="Mapping of relation types to canonical types",
        examples=[{"USES": "USED_BY", "ACTED_IN": "STARRED_IN"}],
    )
    total_overrides: int = Field(..., description="Total number of overrides")


class RelationOverridesResetResponse(BaseModel):
    """Response model for resetting all relation synonym overrides.

    Sprint 49 Feature 49.8: Manual synonym overrides for relation deduplication.
    """

    cleared_count: int = Field(..., description="Number of overrides that were cleared")
    status: str = Field(..., description="Operation status")


@router.get(
    "/graph/relation-synonyms",
    response_model=RelationOverridesListResponse,
    summary="Get all manual relation synonym overrides",
    description="Returns all manual synonym overrides stored in Redis (Sprint 49.8)",
)
async def get_relation_synonyms() -> RelationOverridesListResponse:
    """Get all manual relation synonym overrides.

    **Sprint 49 Feature 49.8: Manual Relation Synonym Overrides**

    Returns all manual synonym overrides stored in Redis hash map.
    These overrides take precedence over automatic semantic clustering.

    **Redis Schema:**
    - Key: `graph:relation-synonyms`
    - Type: Hash
    - Fields: `{"USES": "USED_BY", "ACTED_IN": "STARRED_IN", ...}`
    - TTL: None (persistent)

    **Example Response:**
    ```json
    {
      "overrides": {
        "USES": "USED_BY",
        "ACTED_IN": "STARRED_IN",
        "RELATED_TO": "RELATES_TO"
      },
      "total_overrides": 3
    }
    ```

    Returns:
        RelationOverridesListResponse with all overrides
    """
    try:
        from src.components.graph_rag.hybrid_relation_deduplicator import (
            get_hybrid_relation_deduplicator,
        )

        deduplicator = get_hybrid_relation_deduplicator()
        overrides = await deduplicator.get_all_manual_overrides()

        logger.info("relation_synonyms_retrieved", count=len(overrides))

        return RelationOverridesListResponse(
            overrides=overrides,
            total_overrides=len(overrides),
        )

    except Exception as e:
        logger.error("failed_to_get_relation_synonyms", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve relation synonyms: {str(e)}",
        ) from e


@router.post(
    "/graph/relation-synonyms",
    response_model=RelationOverrideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add manual relation synonym override",
    description="Add a manual synonym override that takes precedence over automatic clustering (Sprint 49.8)",
)
async def add_relation_synonym(
    request: AddRelationOverrideRequest,
) -> RelationOverrideResponse:
    """Add a manual relation synonym override.

    **Sprint 49 Feature 49.8: Manual Relation Synonym Overrides**

    Adds a manual synonym override to Redis. Manual overrides take precedence
    over automatic semantic clustering during relation deduplication.

    **Use Cases:**
    - Fix edge cases where semantic clustering is incorrect
    - Enforce domain-specific naming conventions
    - Override automatic decisions without code changes

    **Storage:**
    - Stored in Redis hash map: `graph:relation-synonyms`
    - Persistent (no TTL)
    - Changes apply immediately to new extractions

    **Example Request:**
    ```json
    {
      "from_type": "ACTED_IN",
      "to_type": "STARRED_IN"
    }
    ```

    **Example Response:**
    ```json
    {
      "from_type": "ACTED_IN",
      "to_type": "STARRED_IN",
      "status": "created"
    }
    ```

    Args:
        request: AddRelationOverrideRequest with from_type and to_type

    Returns:
        RelationOverrideResponse confirming the override

    Raises:
        HTTPException 400: If types are invalid
        HTTPException 500: If Redis operation fails
    """
    try:
        from src.components.graph_rag.hybrid_relation_deduplicator import (
            get_hybrid_relation_deduplicator,
        )

        # Validate types
        if not request.from_type.strip() or not request.to_type.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both from_type and to_type must be non-empty strings",
            )

        deduplicator = get_hybrid_relation_deduplicator()
        await deduplicator.add_manual_override(
            from_type=request.from_type,
            to_type=request.to_type,
        )

        logger.info(
            "relation_synonym_override_added",
            from_type=request.from_type,
            to_type=request.to_type,
        )

        return RelationOverrideResponse(
            from_type=request.from_type.upper(),
            to_type=request.to_type.upper(),
            status="created",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "failed_to_add_relation_synonym",
            from_type=request.from_type,
            to_type=request.to_type,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add relation synonym: {str(e)}",
        ) from e


@router.delete(
    "/graph/relation-synonyms/{from_type}",
    response_model=RelationOverrideResponse,
    summary="Delete manual relation synonym override",
    description="Remove a manual synonym override (Sprint 49.8)",
)
async def delete_relation_synonym(from_type: str) -> RelationOverrideResponse:
    """Delete a manual relation synonym override.

    **Sprint 49 Feature 49.8: Manual Relation Synonym Overrides**

    Removes a manual synonym override from Redis. After deletion, the
    relation type will fall back to automatic semantic clustering.

    **Example Request:**
    ```
    DELETE /api/v1/admin/graph/relation-synonyms/ACTED_IN
    ```

    **Example Response:**
    ```json
    {
      "from_type": "ACTED_IN",
      "to_type": "",
      "status": "deleted"
    }
    ```

    Args:
        from_type: Relation type to remove override for

    Returns:
        RelationOverrideResponse confirming deletion

    Raises:
        HTTPException 404: If override doesn't exist
        HTTPException 500: If Redis operation fails
    """
    try:
        from src.components.graph_rag.hybrid_relation_deduplicator import (
            get_hybrid_relation_deduplicator,
        )

        deduplicator = get_hybrid_relation_deduplicator()
        success = await deduplicator.remove_manual_override(from_type=from_type)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No override found for relation type: {from_type}",
            )

        logger.info("relation_synonym_override_deleted", from_type=from_type)

        return RelationOverrideResponse(
            from_type=from_type.upper(),
            to_type="",
            status="deleted",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "failed_to_delete_relation_synonym",
            from_type=from_type,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete relation synonym: {str(e)}",
        ) from e


@router.post(
    "/graph/relation-synonyms/reset",
    response_model=RelationOverridesResetResponse,
    summary="Clear all manual relation synonym overrides",
    description="Remove all manual synonym overrides from Redis (Sprint 49.8)",
)
async def reset_relation_synonyms() -> RelationOverridesResetResponse:
    """Clear all manual relation synonym overrides.

    **Sprint 49 Feature 49.8: Manual Relation Synonym Overrides**

    Removes ALL manual synonym overrides from Redis. After reset, all
    relation types will fall back to automatic semantic clustering.

    **Warning:** This operation cannot be undone.

    **Example Response:**
    ```json
    {
      "cleared_count": 15,
      "status": "reset_complete"
    }
    ```

    Returns:
        RelationOverridesResetResponse with count of cleared overrides

    Raises:
        HTTPException 500: If Redis operation fails
    """
    try:
        from src.components.graph_rag.hybrid_relation_deduplicator import (
            get_hybrid_relation_deduplicator,
        )

        deduplicator = get_hybrid_relation_deduplicator()
        cleared_count = await deduplicator.clear_all_manual_overrides()

        logger.info("relation_synonyms_reset", cleared_count=cleared_count)

        return RelationOverridesResetResponse(
            cleared_count=cleared_count,
            status="reset_complete",
        )

    except Exception as e:
        logger.error("failed_to_reset_relation_synonyms", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset relation synonyms: {str(e)}",
        ) from e


# ============================================================================
# Sprint 53: LLM Config and Graph Analytics moved to separate modules
# See: admin_llm.py, admin_graph.py
# ============================================================================

# Re-exports for backward compatibility with external scripts
# These can be imported from src.components.graph_rag.llm_config_provider directly
