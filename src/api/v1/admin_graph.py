"""Admin Graph Analytics API endpoints.

Sprint 52 Feature 52.2.1: Graph Analytics Stats Endpoint
Sprint 53 Feature 53.6: Extracted from admin.py

This module provides endpoints for:
- Comprehensive graph statistics
- Entity and relationship type distribution
- Community statistics and health metrics
"""

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, HTTPException, status
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
    community_sizes: list[int] = Field(
        default_factory=list, description="Sizes of each community"
    )
    orphan_nodes: int = Field(..., description="Number of nodes with no connections")
    avg_degree: float = Field(..., description="Average node degree")
    summary_status: dict[str, int] = Field(
        default_factory=dict, description="Community summary generation status"
    )
    graph_health: str = Field(
        default="unknown", description="Overall graph health indicator (healthy, warning, critical)"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp of data collection")


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
        avg_degree = (
            (total_relationships * 2) / total_entities if total_entities > 0 else 0.0
        )

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
