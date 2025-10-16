"""Community Labeling using LLM.

This module provides automatic labeling of detected communities using
an LLM to generate concise, descriptive labels based on community members.

Sprint 6.3: Feature - Community Detection & Clustering

Uses Ollama LLM to generate labels that capture the main theme or topic
of each community based on entity names and descriptions.
"""

import structlog
from ollama import AsyncClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.components.graph_rag.neo4j_client import Neo4jClient
from src.core.config import settings
from src.core.models import Community, GraphEntity

logger = structlog.get_logger(__name__)


class CommunityLabeler:
    """Generate descriptive labels for communities using LLM.

    Features:
    - LLM-based label generation from entity descriptions
    - Batch labeling of all communities
    - Label storage in Neo4j
    - Configurable LLM model and temperature
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        llm_model: str | None = None,
        ollama_base_url: str | None = None,
        enabled: bool | None = None,
    ):
        """Initialize community labeler.

        Args:
            neo4j_client: Neo4j client instance (default: global singleton)
            llm_model: Ollama LLM model for labeling
            ollama_base_url: Ollama server URL
            enabled: Whether labeling is enabled (default: from settings)
        """
        self.neo4j_client = neo4j_client or Neo4jClient()
        self.llm_model = llm_model or settings.graph_community_labeling_model
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        self.enabled = enabled if enabled is not None else settings.graph_community_labeling_enabled

        # Initialize Ollama client
        self.ollama_client = AsyncClient(host=self.ollama_base_url)

        logger.info(
            "community_labeler_initialized",
            llm_model=self.llm_model,
            enabled=self.enabled,
        )

    async def _fetch_community_entities(self, community: Community) -> list[GraphEntity]:
        """Fetch full entity details for a community.

        Args:
            community: Community object with entity IDs

        Returns:
            List of GraphEntity objects
        """
        try:
            cypher = """
            UNWIND $entity_ids AS entity_id
            MATCH (e:Entity {id: entity_id})
            RETURN e.id AS id, e.name AS name, e.type AS type,
                   e.description AS description, e.properties AS properties,
                   e.source_document AS source_document, e.confidence AS confidence
            """

            results = await self.neo4j_client.execute_read(
                cypher,
                {"entity_ids": community.entity_ids},
            )

            entities = []
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

            return entities

        except Exception as e:
            logger.error(
                "fetch_community_entities_failed",
                community_id=community.id,
                error=str(e),
            )
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def generate_label(self, community_entities: list[GraphEntity]) -> str:
        """Generate a label for a community using LLM.

        Args:
            community_entities: List of entities in the community

        Returns:
            Generated label string (2-5 words)

        Raises:
            Exception: If LLM call fails after retries
        """
        if not self.enabled:
            return "Unlabeled Community"

        if not community_entities:
            return "Empty Community"

        try:
            # Build entity list for prompt (limit to first 10 for brevity)
            entity_descriptions = []
            for entity in community_entities[:10]:
                desc = f"- {entity.name} ({entity.type})"
                if entity.description:
                    desc += f": {entity.description[:100]}"
                entity_descriptions.append(desc)

            entity_list = "\n".join(entity_descriptions)

            # Prepare prompt
            prompt = f"""You are labeling a community of related entities in a knowledge graph.

Community members ({len(community_entities)} total, showing first {len(entity_descriptions)}):
{entity_list}

Generate a concise label (2-5 words) that captures the main theme or topic.
Examples: "Machine Learning Research", "European Politics", "Software Engineering"

Return ONLY the label, nothing else. No explanation, no quotes, just the label.

Label:"""

            logger.debug(
                "generating_community_label",
                entities_count=len(community_entities),
            )

            # Call LLM with low temperature for consistency
            response = await self.ollama_client.generate(
                model=self.llm_model,
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "num_predict": 50,  # Short response
                },
            )

            label = response.get("response", "").strip()

            # Clean up label (remove quotes, extra whitespace)
            label = label.strip("\"'")
            label = " ".join(label.split())

            # Validate length (should be 2-5 words)
            words = label.split()
            if len(words) > 5:
                label = " ".join(words[:5])
            elif len(words) < 2:
                label = "Unlabeled Community"

            logger.info(
                "community_label_generated",
                entities_count=len(community_entities),
                label=label,
            )

            return label

        except Exception as e:
            logger.error("generate_label_failed", error=str(e))
            return "Unlabeled Community"

    async def label_all_communities(self, communities: list[Community]) -> list[Community]:
        """Generate and store labels for all communities.

        Args:
            communities: List of Community objects

        Returns:
            List of Community objects with labels populated
        """
        if not self.enabled:
            logger.info("community_labeling_disabled")
            return communities

        logger.info("labeling_communities", count=len(communities))

        labeled_communities = []

        for community in communities:
            try:
                # Fetch full entity details
                entities = await self._fetch_community_entities(community)

                if not entities:
                    logger.warning(
                        "no_entities_found_for_community",
                        community_id=community.id,
                    )
                    community.label = "Empty Community"
                    labeled_communities.append(community)
                    continue

                # Generate label
                label = await self.generate_label(entities)

                # Update community object
                community.label = label

                # Store label in Neo4j
                await self.update_community_label(community.id, label)

                labeled_communities.append(community)

            except Exception as e:
                logger.error(
                    "label_community_failed",
                    community_id=community.id,
                    error=str(e),
                )
                community.label = "Unlabeled Community"
                labeled_communities.append(community)

        logger.info(
            "communities_labeled",
            total=len(communities),
            labeled=len([c for c in labeled_communities if c.label != "Unlabeled Community"]),
        )

        return labeled_communities

    async def update_community_label(self, community_id: str, label: str) -> bool:
        """Update the label for a community in Neo4j.

        Stores the label on all entity nodes in the community.

        Args:
            community_id: Community ID
            label: Label to store

        Returns:
            True if successful, False otherwise
        """
        try:
            cypher = """
            MATCH (e:Entity {community_id: $community_id})
            SET e.community_label = $label
            RETURN count(e) AS updated_count
            """

            result = await self.neo4j_client.execute_write(
                cypher,
                {"community_id": community_id, "label": label},
            )

            updated_count = result[0].get("updated_count", 0) if result else 0

            logger.info(
                "community_label_updated",
                community_id=community_id,
                label=label,
                entities_updated=updated_count,
            )

            return updated_count > 0

        except Exception as e:
            logger.error(
                "update_community_label_failed",
                community_id=community_id,
                error=str(e),
            )
            return False

    async def get_community_label(self, community_id: str) -> str | None:
        """Get the label for a community.

        Args:
            community_id: Community ID

        Returns:
            Label string or None if not found
        """
        try:
            cypher = """
            MATCH (e:Entity {community_id: $community_id})
            RETURN e.community_label AS label
            LIMIT 1
            """

            result = await self.neo4j_client.execute_read(
                cypher,
                {"community_id": community_id},
            )

            if result:
                return result[0].get("label")

            return None

        except Exception as e:
            logger.error(
                "get_community_label_failed",
                community_id=community_id,
                error=str(e),
            )
            return None


# Singleton instance
_community_labeler: CommunityLabeler | None = None


def get_community_labeler() -> CommunityLabeler:
    """Get global CommunityLabeler instance (singleton).

    Returns:
        CommunityLabeler instance
    """
    global _community_labeler
    if _community_labeler is None:
        _community_labeler = CommunityLabeler()
    return _community_labeler
