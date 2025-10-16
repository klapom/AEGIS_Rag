"""Community-Based Search for Knowledge Graphs.

This module extends DualLevelSearch to provide community-filtered search
capabilities, allowing users to search within specific communities or
find related communities.

Sprint 6.3: Feature - Community Detection & Clustering

Integrates with existing graph search to provide:
- Community-filtered entity search
- Related community discovery
- Community statistics and analytics
"""

import time
from typing import Any

import structlog

from src.components.graph_rag.dual_level_search import DualLevelSearch
from src.components.graph_rag.neo4j_client import Neo4jClient
from src.core.models import Community, CommunitySearchResult, GraphEntity

logger = structlog.get_logger(__name__)


class CommunitySearch(DualLevelSearch):
    """Community-aware graph search extending DualLevelSearch.

    Provides:
    - Search filtered by specific communities
    - Related community discovery
    - Community statistics and metrics
    - Integration with existing local/global/hybrid search
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        llm_model: str | None = None,
        ollama_base_url: str | None = None,
    ):
        """Initialize community search.

        Args:
            neo4j_client: Neo4j client instance (default: global singleton)
            llm_model: Ollama LLM model for answer generation
            ollama_base_url: Ollama server URL
        """
        # Initialize parent DualLevelSearch
        super().__init__(
            neo4j_uri=None,
            neo4j_user=None,
            neo4j_password=None,
            llm_model=llm_model,
            ollama_base_url=ollama_base_url,
        )

        # Override neo4j_client if provided
        if neo4j_client:
            self.neo4j_client = neo4j_client

        logger.info("community_search_initialized")

    async def search_by_community(
        self,
        query: str,
        community_ids: list[str] | None = None,
        top_k: int = 5,
    ) -> CommunitySearchResult:
        """Search for entities filtered by community.

        Args:
            query: User query
            community_ids: List of community IDs to search within (None = all)
            top_k: Number of entities to return

        Returns:
            CommunitySearchResult with communities and entities
        """
        start_time = time.time()

        logger.info(
            "community_search_started",
            query=query[:100],
            community_ids=community_ids,
            top_k=top_k,
        )

        try:
            # Extract query terms
            query_term = " ".join(query.split()[:3])

            # Build cypher query with optional community filter
            if community_ids:
                cypher = """
                MATCH (e:Entity)
                WHERE e.community_id IN $community_ids
                  AND (toLower(e.name) CONTAINS toLower($query_term)
                       OR toLower(e.description) CONTAINS toLower($query_term))
                RETURN e.id AS id, e.name AS name, e.type AS type,
                       e.description AS description, e.properties AS properties,
                       e.source_document AS source_document, e.confidence AS confidence,
                       e.community_id AS community_id, e.community_label AS community_label
                LIMIT $top_k
                """
                params = {
                    "community_ids": community_ids,
                    "query_term": query_term,
                    "top_k": top_k,
                }
            else:
                cypher = """
                MATCH (e:Entity)
                WHERE toLower(e.name) CONTAINS toLower($query_term)
                   OR toLower(e.description) CONTAINS toLower($query_term)
                RETURN e.id AS id, e.name AS name, e.type AS type,
                       e.description AS description, e.properties AS properties,
                       e.source_document AS source_document, e.confidence AS confidence,
                       e.community_id AS community_id, e.community_label AS community_label
                LIMIT $top_k
                """
                params = {"query_term": query_term, "top_k": top_k}

            results = await self.neo4j_client.execute_read(cypher, params)

            # Convert to GraphEntity objects and collect communities
            entities = []
            community_map: dict[str, dict[str, Any]] = {}

            for record in results:
                entity = GraphEntity(
                    id=record.get("id", ""),
                    name=record.get("name", ""),
                    type=record.get("type", "UNKNOWN"),
                    description=record.get("description", ""),
                    properties=record.get("properties", {}),
                    source_document=record.get("source_document"),
                    confidence=record.get("confidence", 1.0),
                )
                entities.append(entity)

                # Track communities
                comm_id = record.get("community_id")
                if comm_id and comm_id not in community_map:
                    community_map[comm_id] = {
                        "id": comm_id,
                        "label": record.get("community_label", ""),
                        "entity_ids": [],
                    }
                if comm_id:
                    community_map[comm_id]["entity_ids"].append(entity.id)

            # Build Community objects
            communities = [
                Community(
                    id=comm_data["id"],
                    label=comm_data["label"],
                    entity_ids=comm_data["entity_ids"],
                    size=len(comm_data["entity_ids"]),
                    density=0.0,
                    metadata={},
                )
                for comm_data in community_map.values()
            ]

            # Generate answer from context
            context = self._build_context(entities, [], [])
            answer = await self._generate_answer(query, context)

            execution_time = (time.time() - start_time) * 1000

            result = CommunitySearchResult(
                query=query,
                communities=communities,
                entities=entities,
                answer=answer,
                metadata={
                    "execution_time_ms": execution_time,
                    "entities_found": len(entities),
                    "communities_found": len(communities),
                    "filtered_by_communities": community_ids is not None,
                },
            )

            logger.info(
                "community_search_completed",
                query=query[:100],
                entities=len(entities),
                communities=len(communities),
                execution_time_ms=execution_time,
            )

            return result

        except Exception as e:
            logger.error("community_search_failed", query=query[:100], error=str(e))
            raise

    async def find_related_communities(
        self,
        community_id: str,
        top_k: int = 5,
    ) -> list[Community]:
        """Find communities related to a given community.

        Related communities are those with many inter-community relationships.

        Args:
            community_id: Source community ID
            top_k: Number of related communities to return

        Returns:
            List of related Community objects
        """
        logger.info("find_related_communities", community_id=community_id, top_k=top_k)

        try:
            # Find communities connected by relationships
            cypher = """
            MATCH (e1:Entity {community_id: $community_id})-[r:RELATED_TO]-(e2:Entity)
            WHERE e2.community_id IS NOT NULL
              AND e2.community_id <> $community_id
            WITH e2.community_id AS related_community_id,
                 e2.community_label AS label,
                 count(r) AS connection_count,
                 collect(DISTINCT e2.id) AS entity_ids
            ORDER BY connection_count DESC
            LIMIT $top_k
            RETURN related_community_id, label, entity_ids, size(entity_ids) AS size
            """

            results = await self.neo4j_client.execute_read(
                cypher,
                {"community_id": community_id, "top_k": top_k},
            )

            communities = []
            for record in results:
                community = Community(
                    id=record["related_community_id"],
                    label=record.get("label", ""),
                    entity_ids=record["entity_ids"],
                    size=record["size"],
                    density=0.0,
                    metadata={"connection_type": "relationship_based"},
                )
                communities.append(community)

            logger.info(
                "related_communities_found",
                community_id=community_id,
                count=len(communities),
            )

            return communities

        except Exception as e:
            logger.error(
                "find_related_communities_failed",
                community_id=community_id,
                error=str(e),
            )
            return []

    async def get_community_statistics(self, community_id: str) -> dict[str, Any]:
        """Get statistics for a specific community.

        Args:
            community_id: Community ID

        Returns:
            Dictionary with community statistics
        """
        logger.info("get_community_statistics", community_id=community_id)

        try:
            # Get basic statistics
            stats_cypher = """
            MATCH (e:Entity {community_id: $community_id})
            WITH e.community_id AS community_id,
                 e.community_label AS label,
                 count(e) AS size,
                 collect(e.type) AS types
            MATCH (e1:Entity {community_id: $community_id})-[r:RELATED_TO]-(e2:Entity)
            WHERE e2.community_id = $community_id
            WITH community_id, label, size, types, count(r) AS internal_edges
            RETURN community_id, label, size, types, internal_edges
            """

            results = await self.neo4j_client.execute_read(
                stats_cypher,
                {"community_id": community_id},
            )

            if not results:
                return {
                    "community_id": community_id,
                    "error": "Community not found",
                }

            record = results[0]

            # Calculate density (edges / max_possible_edges)
            size = record["size"]
            internal_edges = record["internal_edges"]
            max_edges = size * (size - 1) / 2 if size > 1 else 1
            density = internal_edges / max_edges if max_edges > 0 else 0.0

            # Count entity types
            types = record["types"]
            type_counts = {}
            for t in types:
                type_counts[t] = type_counts.get(t, 0) + 1

            statistics = {
                "community_id": community_id,
                "label": record.get("label", ""),
                "size": size,
                "internal_edges": internal_edges,
                "density": round(density, 4),
                "entity_types": type_counts,
            }

            logger.info("community_statistics_calculated", **statistics)

            return statistics

        except Exception as e:
            logger.error(
                "get_community_statistics_failed",
                community_id=community_id,
                error=str(e),
            )
            return {
                "community_id": community_id,
                "error": str(e),
            }


# Singleton instance
_community_search: CommunitySearch | None = None


def get_community_search() -> CommunitySearch:
    """Get global CommunitySearch instance (singleton).

    Returns:
        CommunitySearch instance
    """
    global _community_search
    if _community_search is None:
        _community_search = CommunitySearch()
    return _community_search
