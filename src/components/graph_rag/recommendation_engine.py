"""Graph Recommendation Engine.

This module provides entity recommendation capabilities using various methods:
- Collaborative filtering (entities connected to similar entities)
- Community-based recommendations (same community entities)
- Relationship-based recommendations (connected entities)
- Attribute-based recommendations (similar properties)
"""

from typing import Literal

import structlog

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.core.config import settings
from src.core.exceptions import DatabaseConnectionError
from src.core.models import GraphEntity, Recommendation

logger = structlog.get_logger(__name__)

# Type alias for recommendation methods
RecommendationMethod = Literal["collaborative", "community", "relationships", "attributes"]


class RecommendationEngine:
    """Entity recommendation engine."""

    def __init__(self, neo4j_client: Neo4jClient | None = None) -> None:
        """Initialize the recommendation engine.

        Args:
            neo4j_client: Neo4j client instance (defaults to singleton)
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.top_k = settings.graph_recommendations_top_k
        self.default_method = settings.graph_recommendations_method

        logger.info(
            "RecommendationEngine initialized", top_k=self.top_k, default_method=self.default_method
        )

    async def recommend_similar_entities(
        self,
        entity_id: str,
        method: RecommendationMethod = "collaborative",
        top_k: int | None = None,
    ) -> list[Recommendation]:
        """Recommend similar entities based on the specified method.

        Args:
            entity_id: Source entity ID
            method: Recommendation method (collaborative, community, relationships, attributes)
            top_k: Number of recommendations (defaults to config)

        Returns:
            List of Recommendation objects

        Raises:
            DatabaseConnectionError: If recommendation fails
        """
        top_k = top_k or self.top_k

        logger.info("Generating recommendations", entity_id=entity_id, method=method, top_k=top_k)

        # Validate method before database operations
        if method not in ["collaborative", "community", "relationships", "attributes"]:
            raise ValueError(f"Unsupported recommendation method: {method}")

        try:
            if method == "collaborative":
                recommendations = await self.recommend_by_collaborative(entity_id, top_k)
            elif method == "community":
                recommendations = await self.recommend_by_community(entity_id, top_k)
            elif method == "relationships":
                recommendations = await self.recommend_by_relationships(entity_id, top_k)
            else:  # method == "attributes"
                recommendations = await self.recommend_by_attributes(entity_id, top_k)

            logger.info(
                "Recommendations generated", entity_id=entity_id, count=len(recommendations)
            )
            return recommendations

        except Exception as e:
            logger.error("Failed to generate recommendations", error=str(e), entity_id=entity_id)
            raise DatabaseConnectionError("Neo4j", f"Recommendation generation failed: {e}") from e

    async def recommend_by_collaborative(self, entity_id: str, top_k: int) -> list[Recommendation]:
        """Recommend entities using collaborative filtering.

        Find entities that are connected to entities similar to the source entity.
        "Users who liked this also liked..."

        Args:
            entity_id: Source entity ID
            top_k: Number of recommendations

        Returns:
            List of Recommendation objects
        """
        query = """
        MATCH (source {id: $entity_id})-[r1]-(neighbor)-[r2]-(recommendation)
        WHERE recommendation.id <> $entity_id
            AND NOT (source)-[]-(recommendation)
        WITH recommendation, count(DISTINCT neighbor) AS common_neighbors
        ORDER BY common_neighbors DESC
        LIMIT $top_k
        RETURN recommendation.id AS id,
               recommendation.name AS name,
               COALESCE(labels(recommendation)[0], 'Unknown') AS type,
               COALESCE(recommendation.description, '') AS description,
               properties(recommendation) AS properties,
               common_neighbors,
               (toFloat(common_neighbors) / 10.0) AS score
        """

        result = await self.neo4j_client.execute_query(
            query, {"entity_id": entity_id, "top_k": top_k}
        )

        recommendations = []
        for row in result:
            entity = GraphEntity(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                description=row["description"],
                properties=row["properties"],
                confidence=1.0,
            )
            recommendations.append(
                Recommendation(
                    entity=entity,
                    score=min(float(row["score"]), 1.0),
                    reason="similar_community",
                )
            )

        return recommendations

    async def recommend_by_community(self, entity_id: str, top_k: int) -> list[Recommendation]:
        """Recommend entities from the same community.

        Args:
            entity_id: Source entity ID
            top_k: Number of recommendations

        Returns:
            List of Recommendation objects
        """
        query = """
        MATCH (source {id: $entity_id})
        WITH source.community_id AS community_id
        MATCH (recommendation)
        WHERE recommendation.community_id = community_id
            AND recommendation.id <> $entity_id
        WITH recommendation, community_id
        MATCH (recommendation)-[r]-()
        WITH recommendation, count(r) AS degree
        ORDER BY degree DESC
        LIMIT $top_k
        RETURN recommendation.id AS id,
               recommendation.name AS name,
               COALESCE(labels(recommendation)[0], 'Unknown') AS type,
               COALESCE(recommendation.description, '') AS description,
               properties(recommendation) AS properties,
               degree,
               (toFloat(degree) / 20.0) AS score
        """

        try:
            result = await self.neo4j_client.execute_query(
                query, {"entity_id": entity_id, "top_k": top_k}
            )
        except Exception:
            # If community_id property doesn't exist, return empty list
            logger.warning(
                "Community-based recommendation failed (no community_id?)", entity_id=entity_id
            )
            return []

        recommendations = []
        for row in result:
            entity = GraphEntity(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                description=row["description"],
                properties=row["properties"],
                confidence=1.0,
            )
            recommendations.append(
                Recommendation(
                    entity=entity, score=min(float(row["score"]), 1.0), reason="similar_community"
                )
            )

        return recommendations

    async def recommend_by_relationships(self, entity_id: str, top_k: int) -> list[Recommendation]:
        """Recommend directly connected entities.

        Args:
            entity_id: Source entity ID
            top_k: Number of recommendations

        Returns:
            List of Recommendation objects
        """
        query = """
        MATCH (source {id: $entity_id})-[r]-(recommendation)
        WITH recommendation, type(r) AS rel_type, count(r) AS rel_count
        ORDER BY rel_count DESC
        LIMIT $top_k
        RETURN recommendation.id AS id,
               recommendation.name AS name,
               COALESCE(labels(recommendation)[0], 'Unknown') AS type,
               COALESCE(recommendation.description, '') AS description,
               properties(recommendation) AS properties,
               rel_type,
               rel_count,
               (toFloat(rel_count) / 5.0) AS score
        """

        result = await self.neo4j_client.execute_query(
            query, {"entity_id": entity_id, "top_k": top_k}
        )

        recommendations = []
        for row in result:
            entity = GraphEntity(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                description=row["description"],
                properties=row["properties"],
                confidence=1.0,
            )
            recommendations.append(
                Recommendation(
                    entity=entity,
                    score=min(float(row["score"]), 1.0),
                    reason=f"connected ({row['rel_type']})",
                )
            )

        return recommendations

    async def recommend_by_attributes(self, entity_id: str, top_k: int) -> list[Recommendation]:
        """Recommend entities with similar attributes/properties.

        Args:
            entity_id: Source entity ID
            top_k: Number of recommendations

        Returns:
            List of Recommendation objects
        """
        query = """
        MATCH (source {id: $entity_id})
        WITH source, labels(source)[0] AS source_type
        MATCH (recommendation)
        WHERE labels(recommendation)[0] = source_type
            AND recommendation.id <> $entity_id
        WITH recommendation, source, source_type
        MATCH (recommendation)-[r]-()
        WITH recommendation, count(r) AS degree
        ORDER BY degree DESC
        LIMIT $top_k
        RETURN recommendation.id AS id,
               recommendation.name AS name,
               COALESCE(labels(recommendation)[0], 'Unknown') AS type,
               COALESCE(recommendation.description, '') AS description,
               properties(recommendation) AS properties,
               degree,
               (toFloat(degree) / 15.0) AS score
        """

        result = await self.neo4j_client.execute_query(
            query, {"entity_id": entity_id, "top_k": top_k}
        )

        recommendations = []
        for row in result:
            entity = GraphEntity(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                description=row["description"],
                properties=row["properties"],
                confidence=1.0,
            )
            recommendations.append(
                Recommendation(
                    entity=entity,
                    score=min(float(row["score"]), 1.0),
                    reason="similar_attributes",
                )
            )

        return recommendations


# Singleton instance
_recommendation_engine: RecommendationEngine | None = None


def get_recommendation_engine() -> RecommendationEngine:
    """Get singleton RecommendationEngine instance.

    Returns:
        RecommendationEngine instance
    """
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine
