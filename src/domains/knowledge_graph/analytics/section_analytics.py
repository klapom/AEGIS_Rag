"""Section Analytics Service.

Sprint 62 Feature 62.9: Section Analytics Endpoint

This module provides section-level statistics and analytics:
- Entity counts per section
- Chunk counts per section
- Relationship counts per section
- Level distribution
- Top sections by various metrics

Architecture:
- Queries Neo4j for section and entity data
- Queries Qdrant for chunk counts
- Caches results in Redis (5 min TTL)
- Performance target: <200ms with caching
"""

import hashlib
import json
import time
from typing import Any

import structlog

from src.api.models.analytics import SectionAnalyticsResponse, SectionStats
from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.components.memory import get_redis_memory

logger = structlog.get_logger(__name__)

# Redis cache TTL for section analytics (5 minutes)
CACHE_TTL_SECONDS = 300


class SectionAnalyticsService:
    """Service for retrieving section-level analytics.

    This service aggregates data from Neo4j and Qdrant to provide
    comprehensive statistics about document sections.

    Example:
        >>> service = SectionAnalyticsService()
        >>> response = await service.get_section_analytics(
        ...     document_id="doc_123",
        ...     namespace="default"
        ... )
        >>> print(f"Total sections: {response.total_sections}")
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
    ) -> None:
        """Initialize section analytics service.

        Args:
            neo4j_client: Neo4j client instance (uses singleton if None)
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        logger.info("section_analytics_service_initialized")

    async def get_section_analytics(
        self,
        document_id: str,
        namespace: str = "default",
    ) -> SectionAnalyticsResponse:
        """Get comprehensive section analytics for a document.

        This method:
        1. Checks Redis cache for existing results
        2. Queries Neo4j for section metadata and entity counts
        3. Queries Qdrant for chunk counts
        4. Calculates statistics and rankings
        5. Caches results in Redis

        Args:
            document_id: Document ID to analyze
            namespace: Namespace to query (default: "default")

        Returns:
            SectionAnalyticsResponse with aggregated statistics

        Example:
            >>> response = await service.get_section_analytics("doc_123")
            >>> print(f"Average entities: {response.avg_entities_per_section:.1f}")
        """
        start_time = time.perf_counter()

        # Check cache
        cache_key = self._get_cache_key(document_id, namespace)
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            logger.info(
                "section_analytics_cache_hit",
                document_id=document_id,
                namespace=namespace,
            )
            return SectionAnalyticsResponse.model_validate(cached_result)

        logger.info(
            "section_analytics_cache_miss",
            document_id=document_id,
            namespace=namespace,
        )

        # Query Neo4j for section statistics
        section_stats = await self._query_section_stats(document_id, namespace)

        # Calculate aggregations
        total_sections = len(section_stats)
        level_distribution = self._calculate_level_distribution(section_stats)
        avg_entities = self._calculate_average(section_stats, "entity_count")
        avg_chunks = self._calculate_average(section_stats, "chunk_count")

        # Get top sections by relationship count
        top_sections = sorted(
            section_stats,
            key=lambda s: s.relationship_count,
            reverse=True,
        )[:10]

        response = SectionAnalyticsResponse(
            document_id=document_id,
            total_sections=total_sections,
            level_distribution=level_distribution,
            avg_entities_per_section=avg_entities,
            avg_chunks_per_section=avg_chunks,
            top_sections=top_sections,
        )

        # Cache result
        await self._save_to_cache(cache_key, response.model_dump())

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "section_analytics_completed",
            document_id=document_id,
            namespace=namespace,
            total_sections=total_sections,
            elapsed_ms=round(elapsed_ms, 2),
        )

        return response

    async def _query_section_stats(
        self,
        document_id: str,
        namespace: str,
    ) -> list[SectionStats]:
        """Query Neo4j for section statistics.

        Executes a Cypher query to retrieve:
        - Section metadata (id, heading, level)
        - Entity count per section (via DEFINES relationship)
        - Chunk count per section (via CONTAINS_CHUNK relationship)
        - Relationship count (entities in section with relationships)

        Args:
            document_id: Document ID to query
            namespace: Namespace filter

        Returns:
            List of SectionStats objects
        """
        # Cypher query to get section statistics
        # Note: Adjust label names based on actual Neo4j schema from Sprint 32
        cypher = """
        MATCH (d:Document {id: $document_id, namespace: $namespace})-[:HAS_SECTION]->(s:Section)
        OPTIONAL MATCH (s)-[:DEFINES]->(e:base)
        OPTIONAL MATCH (s)-[:CONTAINS_CHUNK]->(c:Chunk)
        OPTIONAL MATCH (e)-[r]-()
        WITH s,
             count(DISTINCT e) as entity_count,
             count(DISTINCT c) as chunk_count,
             count(DISTINCT r) as relationship_count
        RETURN elementId(s) as section_id,
               s.heading as section_heading,
               COALESCE(s.level, 1) as section_level,
               entity_count,
               chunk_count,
               relationship_count
        ORDER BY s.order
        """

        logger.debug(
            "querying_section_stats",
            document_id=document_id,
            namespace=namespace,
        )

        records = await self.neo4j_client.execute_query(
            cypher,
            parameters={
                "document_id": document_id,
                "namespace": namespace,
            },
        )

        section_stats = []
        for record in records:
            stats = SectionStats(
                section_id=str(record["section_id"]),
                section_title=record["section_heading"] or "Untitled Section",
                section_level=int(record["section_level"]),
                entity_count=int(record["entity_count"]),
                chunk_count=int(record["chunk_count"]),
                relationship_count=int(record["relationship_count"]),
            )
            section_stats.append(stats)

        logger.debug(
            "section_stats_retrieved",
            document_id=document_id,
            count=len(section_stats),
        )

        return section_stats

    def _calculate_level_distribution(self, section_stats: list[SectionStats]) -> dict[int, int]:
        """Calculate distribution of sections by level.

        Args:
            section_stats: List of section statistics

        Returns:
            Dictionary mapping level to count (e.g., {1: 3, 2: 8, 3: 4})
        """
        distribution: dict[int, int] = {}
        for stats in section_stats:
            level = stats.section_level
            distribution[level] = distribution.get(level, 0) + 1
        return distribution

    def _calculate_average(
        self,
        section_stats: list[SectionStats],
        field: str,
    ) -> float:
        """Calculate average value for a field across all sections.

        Args:
            section_stats: List of section statistics
            field: Field name to average (e.g., "entity_count")

        Returns:
            Average value (0.0 if no sections)
        """
        if not section_stats:
            return 0.0

        total = sum(getattr(stats, field) for stats in section_stats)
        return float(total) / float(len(section_stats))

    def _get_cache_key(self, document_id: str, namespace: str) -> str:
        """Generate Redis cache key for section analytics.

        Args:
            document_id: Document ID
            namespace: Namespace

        Returns:
            Redis key string
        """
        # Use hash to keep key length reasonable
        key_data = f"section_analytics:{namespace}:{document_id}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"section_analytics:{key_hash}"

    async def _get_from_cache(self, cache_key: str) -> dict[str, Any] | None:
        """Retrieve section analytics from Redis cache.

        Args:
            cache_key: Redis key

        Returns:
            Cached analytics dict or None if not found
        """
        try:
            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            cached_data = await redis_client.get(cache_key)
            if cached_data:
                result: dict[str, Any] = json.loads(cached_data)
                return result
            return None

        except Exception as e:
            logger.warning("cache_read_failed", error=str(e), key=cache_key)
            return None

    async def _save_to_cache(self, cache_key: str, data: dict[str, Any]) -> None:
        """Save section analytics to Redis cache.

        Args:
            cache_key: Redis key
            data: Analytics data to cache
        """
        try:
            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            await redis_client.setex(
                cache_key,
                CACHE_TTL_SECONDS,
                json.dumps(data),
            )

            logger.debug(
                "cache_saved",
                key=cache_key,
                ttl_seconds=CACHE_TTL_SECONDS,
            )

        except Exception as e:
            logger.warning("cache_write_failed", error=str(e), key=cache_key)


# Singleton instance
_section_analytics_service: SectionAnalyticsService | None = None


def get_section_analytics_service() -> SectionAnalyticsService:
    """Get or create singleton SectionAnalyticsService instance.

    Returns:
        SectionAnalyticsService singleton
    """
    global _section_analytics_service
    if _section_analytics_service is None:
        _section_analytics_service = SectionAnalyticsService()
    return _section_analytics_service
