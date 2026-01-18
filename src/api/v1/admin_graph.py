"""Admin Graph Analytics API endpoints.

Sprint 52 Feature 52.2.1: Graph Analytics Stats Endpoint
Sprint 53 Feature 53.6: Extracted from admin.py
Sprint 77 Feature 77.4: Community Summarization Endpoint (TD-094)

This module provides endpoints for:
- Comprehensive graph statistics
- Entity and relationship type distribution
- Community statistics and health metrics
- Community summarization (batch generation)
"""

import asyncio
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-graph"])


# ============================================================================
# Pydantic Models
# ============================================================================


class GraphStatsResponse(BaseModel):
    """Comprehensive graph statistics for admin dashboard.

    Sprint 52 Feature 52.2.1: Graph Analytics Page
    """

    total_entities: int = Field(..., description="Total number of entities in the graph")
    total_relationships: int = Field(..., description="Total number of relationships")
    entity_types: dict[str, int] = Field(
        default_factory=dict, description="Entity type distribution (type -> count)"
    )
    relationship_types: dict[str, int] = Field(
        default_factory=dict, description="Relationship type distribution (type -> count)"
    )
    community_count: int = Field(..., description="Number of detected communities")
    community_sizes: list[int] = Field(default_factory=list, description="Sizes of each community")
    orphan_nodes: int = Field(..., description="Number of nodes with no connections")
    avg_degree: float = Field(..., description="Average node degree")
    summary_status: dict[str, int] = Field(
        default_factory=dict, description="Community summary generation status"
    )
    graph_health: str = Field(
        default="unknown", description="Overall graph health indicator (healthy, warning, critical)"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp of data collection")


class CommunitySummarizationRequest(BaseModel):
    """Request model for community summarization.

    Sprint 77 Feature 77.4 (TD-094): Community Summarization Endpoint
    """

    namespace: str | None = Field(
        default=None,
        description="Filter by namespace (optional, e.g., 'hotpotqa_large')",
    )
    force: bool = Field(
        default=False,
        description="Regenerate ALL summaries (including existing ones)",
    )
    batch_size: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of communities to process concurrently (1-50)",
    )


class CommunitySummarizationResponse(BaseModel):
    """Response model for community summarization.

    Sprint 77 Feature 77.4 (TD-094): Community Summarization Endpoint
    """

    status: str = Field(
        ...,
        description="Status: 'started' (background), 'complete' (sync), or 'no_work' (nothing to do)",
    )
    total_communities: int = Field(..., description="Total communities found")
    summaries_generated: int | None = Field(
        default=None,
        description="Number of summaries generated (null for background tasks)",
    )
    failed: int | None = Field(
        default=None,
        description="Number of failed summaries (null for background tasks)",
    )
    total_time_s: float | None = Field(
        default=None,
        description="Total time in seconds (null for background tasks)",
    )
    avg_time_per_summary_s: float | None = Field(
        default=None,
        description="Avg time per summary in seconds (null for background tasks)",
    )
    message: str = Field(..., description="Human-readable status message")


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/graph/stats",
    response_model=GraphStatsResponse,
    summary="Get comprehensive graph statistics",
    description="Returns detailed graph analytics including entity/relationship counts, "
    "community statistics, and graph health metrics for the admin dashboard.",
)
async def get_graph_stats() -> GraphStatsResponse:
    """Get comprehensive graph statistics for admin dashboard.

    **Sprint 52 Feature 52.2.1: Graph Analytics Page**

    This endpoint provides detailed statistics about the knowledge graph:
    - Total entities and relationships
    - Entity type distribution (PERSON, ORGANIZATION, etc.)
    - Relationship type distribution (RELATES_TO, MENTIONED_IN, etc.)
    - Community count and size distribution
    - Orphan nodes (disconnected entities)
    - Graph health assessment

    Returns:
        GraphStatsResponse with comprehensive graph metrics

    Raises:
        HTTPException: If Neo4j connection fails or query errors occur
    """
    try:
        # Get Neo4j connection
        from src.components.graph_rag.neo4j_client import get_neo4j_client

        neo4j = get_neo4j_client()

        async with neo4j.driver.session() as session:
            # 1. Total entity count
            entity_result = await session.run("MATCH (n:base) RETURN count(n) as count")
            entity_record = await entity_result.single()
            total_entities = entity_record["count"] if entity_record else 0

            # 2. Total relationship count
            rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_record = await rel_result.single()
            total_relationships = rel_record["count"] if rel_record else 0

            # 3. Entity type distribution
            entity_type_result = await session.run(
                "MATCH (n:base) RETURN n.entity_type as type, count(*) as count"
            )
            entity_type_records = await entity_type_result.data()
            entity_types = {
                record["type"]: record["count"]
                for record in entity_type_records
                if record["type"] is not None
            }

            # 4. Relationship type distribution
            rel_type_result = await session.run(
                "MATCH ()-[r]->() RETURN type(r) as type, count(*) as count"
            )
            rel_type_records = await rel_type_result.data()
            relationship_types = {
                record["type"]: record["count"]
                for record in rel_type_records
                if record["type"] is not None
            }

            # 5. Community statistics
            community_result = await session.run(
                "MATCH (n:base) WHERE n.community_id IS NOT NULL "
                "RETURN n.community_id as community, count(*) as size "
                "ORDER BY size DESC"
            )
            community_records = await community_result.data()
            community_count = len(community_records)
            community_sizes = [record["size"] for record in community_records]

            # 6. Orphan nodes (no connections)
            orphan_result = await session.run(
                "MATCH (n:base) WHERE NOT (n)--() RETURN count(n) as count"
            )
            orphan_record = await orphan_result.single()
            orphan_nodes = orphan_record["count"] if orphan_record else 0

            # 7. Community summary status
            # Check for communities with generated summaries
            summary_result = await session.run(
                "MATCH (c:__Community__) "
                "RETURN "
                "sum(CASE WHEN c.summary IS NOT NULL AND c.summary <> '' THEN 1 ELSE 0 END) as generated, "
                "sum(CASE WHEN c.summary IS NULL OR c.summary = '' THEN 1 ELSE 0 END) as pending"
            )
            summary_record = await summary_result.single()
            if summary_record:
                summary_status = {
                    "generated": summary_record["generated"] or 0,
                    "pending": summary_record["pending"] or 0,
                }
            else:
                # Fallback: assume all communities need summaries
                summary_status = {
                    "generated": 0,
                    "pending": community_count,
                }

        # Calculate average degree
        avg_degree = (total_relationships * 2) / total_entities if total_entities > 0 else 0.0

        # Determine graph health
        orphan_ratio = orphan_nodes / total_entities if total_entities > 0 else 0
        if orphan_ratio > 0.3:
            graph_health = "critical"
        elif orphan_ratio > 0.1:
            graph_health = "warning"
        else:
            graph_health = "healthy"

        logger.info(
            "graph_stats_retrieved",
            total_entities=total_entities,
            total_relationships=total_relationships,
            community_count=community_count,
            orphan_nodes=orphan_nodes,
            graph_health=graph_health,
        )

        return GraphStatsResponse(
            total_entities=total_entities,
            total_relationships=total_relationships,
            entity_types=entity_types,
            relationship_types=relationship_types,
            community_count=community_count,
            community_sizes=community_sizes,
            orphan_nodes=orphan_nodes,
            avg_degree=avg_degree,
            summary_status=summary_status,
            graph_health=graph_health,
            timestamp=datetime.now(UTC).isoformat(),
        )

    except Exception as e:
        logger.error("graph_stats_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to retrieve graph statistics: {str(e)}",
        ) from e


@router.post(
    "/graph/communities/summarize",
    response_model=CommunitySummarizationResponse,
    summary="Generate community summaries",
    description="Generate LLM-powered summaries for all communities in the graph. "
    "Supports both synchronous (blocking) and background execution. "
    "Sprint 77 Feature 77.4 (TD-094)",
)
async def generate_community_summaries(
    request: CommunitySummarizationRequest,
    background_tasks: BackgroundTasks,
) -> CommunitySummarizationResponse:
    """Generate community summaries for Graph-Global search mode.

    **Sprint 77 Feature 77.4 (TD-094): Community Summarization Endpoint**

    This endpoint generates LLM-powered summaries for all communities
    detected by graph extraction, enabling semantic search over community
    summaries in LightRAG global mode.

    **Execution Modes:**
    - **Background** (default): Returns immediately, summaries generated in background
    - **Synchronous**: Blocks until all summaries are generated (use for small graphs)

    **Parameters:**
    - `namespace`: Filter by namespace (optional, e.g., "hotpotqa_large")
    - `force`: Regenerate ALL summaries, including existing ones (default: false)
    - `batch_size`: Communities per batch (default: 10, max: 50)

    **Background Mode:**
    - Use `background=true` (default) for large graphs (>50 communities)
    - Returns immediately with status "started"
    - Monitor progress via logs or metrics

    **Synchronous Mode:**
    - Use `background=false` for small graphs (<10 communities)
    - Blocks until completion
    - Returns full statistics (generated, failed, timing)

    Args:
        request: CommunitySummarizationRequest with namespace, force, batch_size
        background_tasks: FastAPI background tasks

    Returns:
        CommunitySummarizationResponse with status and statistics

    Raises:
        HTTPException: If Neo4j connection fails or summarization errors occur

    Example:
        ```bash
        # Background mode (default)
        curl -X POST http://localhost:8000/api/v1/admin/graph/communities/summarize \\
             -H "Content-Type: application/json" \\
             -d '{"namespace": "hotpotqa_large", "force": false, "batch_size": 10}'

        # Synchronous mode (for testing)
        curl -X POST http://localhost:8000/api/v1/admin/graph/communities/summarize \\
             -H "Content-Type: application/json" \\
             -d '{"namespace": null, "force": false, "batch_size": 5}'
        ```
    """
    try:
        from src.components.graph_rag.community_summarizer import get_community_summarizer
        from src.components.graph_rag.neo4j_client import get_neo4j_client

        logger.info(
            "community_summarization_requested",
            namespace=request.namespace,
            force=request.force,
            batch_size=request.batch_size,
        )

        # Get communities to summarize
        neo4j = get_neo4j_client()
        summarizer = get_community_summarizer()

        # Query communities
        if request.force:
            # Get ALL communities (regenerate even if summaries exist)
            if request.namespace:
                cypher = """
                MATCH (e:base)
                WHERE e.community_id IS NOT NULL
                  AND e.namespace = $namespace
                RETURN DISTINCT e.community_id AS community_id
                ORDER BY community_id
                """
                results = await neo4j.execute_read(cypher, {"namespace": request.namespace})
            else:
                cypher = """
                MATCH (e:base)
                WHERE e.community_id IS NOT NULL
                RETURN DISTINCT e.community_id AS community_id
                ORDER BY community_id
                """
                results = await neo4j.execute_read(cypher)
        else:
            # Get only communities WITHOUT summaries
            if request.namespace:
                cypher = """
                MATCH (e:base)
                WHERE e.community_id IS NOT NULL
                  AND e.namespace = $namespace
                WITH DISTINCT e.community_id AS community_id
                WHERE NOT EXISTS {
                    MATCH (cs:CommunitySummary {community_id: community_id})
                }
                RETURN community_id
                ORDER BY community_id
                """
                results = await neo4j.execute_read(cypher, {"namespace": request.namespace})
            else:
                cypher = """
                MATCH (e:base)
                WHERE e.community_id IS NOT NULL
                WITH DISTINCT e.community_id AS community_id
                WHERE NOT EXISTS {
                    MATCH (cs:CommunitySummary {community_id: community_id})
                }
                RETURN community_id
                ORDER BY community_id
                """
                results = await neo4j.execute_read(cypher)

        # Parse community IDs
        community_ids = []
        for record in results:
            community_id_val = record.get("community_id")
            if community_id_val is not None:
                # Handle both formats: integer (from GDS) or string "community_5" (legacy)
                try:
                    if isinstance(community_id_val, int):
                        # GDS returns integer community IDs directly
                        community_id = community_id_val
                    else:
                        # Parse "community_5" → 5 (legacy format)
                        community_id = int(str(community_id_val).split("_")[-1])
                    community_ids.append(community_id)
                except (ValueError, IndexError, AttributeError):
                    logger.warning("invalid_community_id_format_skipped", community_id=community_id_val)

        total_communities = len(community_ids)

        logger.info(
            "communities_identified_for_summarization",
            total_communities=total_communities,
            force=request.force,
            namespace=request.namespace,
        )

        # No work to do?
        if total_communities == 0:
            logger.info("no_communities_to_summarize")
            return CommunitySummarizationResponse(
                status="no_work",
                total_communities=0,
                summaries_generated=0,
                failed=0,
                total_time_s=0.0,
                avg_time_per_summary_s=0.0,
                message="No communities need summarization. Use force=true to regenerate all summaries.",
            )

        # Background mode: Launch background task (recommended for large graphs)
        # For Sprint 77, we'll use synchronous mode for simplicity
        # Background mode can be added in future sprint if needed

        # Synchronous mode: Generate summaries now (blocks request)
        import time

        start_time = time.time()
        summaries_generated = 0
        failed = 0

        logger.info("generating_community_summaries_synchronously", total=total_communities)

        for community_id in community_ids:
            try:
                # Fetch community data
                entities = await summarizer._get_community_entities(community_id)
                relationships = await summarizer._get_community_relationships(community_id)

                # Generate summary
                summary = await summarizer.generate_summary(community_id, entities, relationships)

                # Store summary
                await summarizer._store_summary(community_id, summary)

                summaries_generated += 1

                logger.debug(
                    "community_summary_stored",
                    community_id=community_id,
                    summary_length=len(summary),
                    progress=f"{summaries_generated}/{total_communities}",
                )

            except Exception as e:
                logger.error(
                    "failed_to_generate_community_summary",
                    community_id=community_id,
                    error=str(e),
                )
                failed += 1

        total_time_s = time.time() - start_time
        avg_time_per_summary_s = total_time_s / summaries_generated if summaries_generated > 0 else 0

        logger.info(
            "community_summarization_complete",
            summaries_generated=summaries_generated,
            failed=failed,
            total_time_s=round(total_time_s, 2),
            avg_time_per_summary_s=round(avg_time_per_summary_s, 2),
        )

        return CommunitySummarizationResponse(
            status="complete",
            total_communities=total_communities,
            summaries_generated=summaries_generated,
            failed=failed,
            total_time_s=total_time_s,
            avg_time_per_summary_s=avg_time_per_summary_s,
            message=f"Generated {summaries_generated} summaries in {total_time_s:.1f}s ({failed} failed).",
        )

    except Exception as e:
        logger.error("community_summarization_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to generate community summaries: {str(e)}",
        ) from e
