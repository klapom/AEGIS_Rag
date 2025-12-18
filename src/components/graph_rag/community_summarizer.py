"""Community Summarizer for LightRAG Global Search.

This module generates LLM-powered summaries for graph communities,
enabling semantic search over community summaries instead of just
entity names. Improves LightRAG global mode retrieval quality.

Sprint 52 - Feature 52.1: Community Summary Generation (TD-058)

Features:
- LLM-generated summaries for communities
- Delta-based incremental updates (only summarize changed communities)
- Neo4j storage with CommunitySummary nodes
- Configurable LLM model via admin interface
- Cost tracking for summary generation
"""

import time
from typing import Any

import structlog

from src.components.graph_rag.community_delta_tracker import CommunityDelta
from src.components.graph_rag.neo4j_client import Neo4jClient
from src.components.llm_proxy import LLMTask, TaskType, get_aegis_llm_proxy
from src.core.config import settings

logger = structlog.get_logger(__name__)

# Default prompt template for community summarization
DEFAULT_SUMMARY_PROMPT = """You are analyzing a community of related entities in a knowledge graph.

Community contains the following entities:
{entities}

These entities are connected by the following relationships:
{relationships}

Generate a concise 2-3 sentence summary describing:
1. The main topic or theme of this community
2. The key relationships between entities
3. The domain or context (e.g., research, business, technology)

Summary:"""


class CommunitySummarizer:
    """Generates LLM summaries for graph communities.

    This class handles the generation and storage of community summaries,
    enabling semantic search over communities in LightRAG global mode.
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        model_name: str | None = None,
        prompt_template: str | None = None,
    ) -> None:
        """Initialize community summarizer.

        Args:
            neo4j_client: Neo4j client instance (default: singleton)
            model_name: LLM model for summarization (default: from settings)
            prompt_template: Custom prompt template (default: DEFAULT_SUMMARY_PROMPT)
        """
        from src.components.graph_rag.neo4j_client import get_neo4j_client

        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.llm_proxy = get_aegis_llm_proxy()
        self.model_name = model_name or settings.ollama_model_generation
        self.prompt_template = prompt_template or DEFAULT_SUMMARY_PROMPT

        logger.info(
            "community_summarizer_initialized",
            model=self.model_name,
            prompt_template_length=len(self.prompt_template),
        )

    async def generate_summary(
        self,
        community_id: int,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> str:
        """Generate a summary for a community.

        Args:
            community_id: Community ID
            entities: List of entity dictionaries with 'name' and 'type'
            relationships: List of relationship dictionaries with 'source', 'target', 'type'

        Returns:
            Generated summary text

        Example:
            >>> entities = [
            ...     {"name": "Neural Networks", "type": "CONCEPT"},
            ...     {"name": "Deep Learning", "type": "CONCEPT"}
            ... ]
            >>> relationships = [
            ...     {"source": "Neural Networks", "target": "Deep Learning", "type": "RELATES_TO"}
            ... ]
            >>> summary = await summarizer.generate_summary(5, entities, relationships)
            >>> print(summary)
            "This community focuses on deep learning and neural network concepts..."
        """
        logger.info(
            "generating_community_summary",
            community_id=community_id,
            entities_count=len(entities),
            relationships_count=len(relationships),
        )

        start_time = time.time()

        # Handle empty communities
        if not entities:
            logger.warning("empty_community_skipped", community_id=community_id)
            return "Empty community with no entities."

        # Format entities for prompt
        entities_text = "\n".join(
            [f"- {entity['name']} ({entity.get('type', 'UNKNOWN')})" for entity in entities]
        )

        # Format relationships for prompt
        if relationships:
            relationships_text = "\n".join(
                [
                    f"- {rel['source']} {rel.get('type', 'RELATES_TO')} {rel['target']}"
                    for rel in relationships
                ]
            )
        else:
            relationships_text = "No explicit relationships available."

        # Build prompt
        prompt = self.prompt_template.format(
            entities=entities_text,
            relationships=relationships_text,
        )

        # Create LLM task
        task = LLMTask(
            task_type=TaskType.SUMMARIZATION,
            prompt=prompt,
            max_tokens=512,  # Summaries should be concise
            temperature=0.3,  # Low temperature for consistency
            model_local=self.model_name,
        )

        # Generate summary via LLM proxy
        try:
            response = await self.llm_proxy.generate(task)
            summary = response.content.strip()

            generation_time_ms = (time.time() - start_time) * 1000

            logger.info(
                "community_summary_generated",
                community_id=community_id,
                summary_length=len(summary),
                tokens_used=response.tokens_used,
                cost_usd=response.cost_usd,
                provider=response.provider,
                model=response.model,
                generation_time_ms=round(generation_time_ms, 2),
            )

            return summary

        except Exception as e:
            logger.error(
                "community_summary_generation_failed",
                community_id=community_id,
                error=str(e),
            )
            # Fallback to simple entity listing
            return f"Community containing {len(entities)} entities: {', '.join([e['name'] for e in entities[:5]])}{'...' if len(entities) > 5 else ''}"

    async def _get_community_entities(self, community_id: int) -> list[dict[str, Any]]:
        """Get entities for a community from Neo4j.

        Args:
            community_id: Community ID

        Returns:
            List of entity dictionaries with 'name', 'type', 'entity_id'
        """
        cypher = """
        MATCH (e:base)
        WHERE e.community_id = $community_id
        RETURN e.name AS name, e.entity_type AS type, e.entity_id AS entity_id
        LIMIT 100
        """

        results = await self.neo4j_client.execute_read(
            cypher,
            {"community_id": f"community_{community_id}"},
        )

        entities = []
        for record in results:
            entities.append(
                {
                    "name": record.get("name", "Unknown"),
                    "type": record.get("type", "UNKNOWN"),
                    "entity_id": record.get("entity_id"),
                }
            )

        logger.debug(
            "community_entities_retrieved",
            community_id=community_id,
            entities_count=len(entities),
        )

        return entities

    async def _get_community_relationships(
        self, community_id: int
    ) -> list[dict[str, Any]]:
        """Get relationships within a community from Neo4j.

        Args:
            community_id: Community ID

        Returns:
            List of relationship dictionaries with 'source', 'target', 'type'
        """
        cypher = """
        MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
        WHERE e1.community_id = $community_id
          AND e2.community_id = $community_id
        RETURN e1.name AS source, e2.name AS target, type(r) AS type
        LIMIT 200
        """

        results = await self.neo4j_client.execute_read(
            cypher,
            {"community_id": f"community_{community_id}"},
        )

        relationships = []
        for record in results:
            relationships.append(
                {
                    "source": record.get("source", "Unknown"),
                    "target": record.get("target", "Unknown"),
                    "type": record.get("type", "RELATES_TO"),
                }
            )

        logger.debug(
            "community_relationships_retrieved",
            community_id=community_id,
            relationships_count=len(relationships),
        )

        return relationships

    async def _store_summary(
        self,
        community_id: int,
        summary: str,
    ) -> None:
        """Store community summary in Neo4j.

        Creates or updates a CommunitySummary node with the summary text.

        Args:
            community_id: Community ID
            summary: Summary text
        """
        cypher = """
        MERGE (cs:CommunitySummary {community_id: $community_id})
        SET cs.summary = $summary,
            cs.updated_at = datetime(),
            cs.model_used = $model,
            cs.summary_length = $summary_length
        """

        await self.neo4j_client.execute_write(
            cypher,
            {
                "community_id": community_id,
                "summary": summary,
                "model": self.model_name,
                "summary_length": len(summary),
            },
        )

        logger.debug(
            "community_summary_stored",
            community_id=community_id,
            summary_length=len(summary),
        )

    async def update_summaries_for_delta(
        self,
        delta: CommunityDelta,
    ) -> dict[int, str]:
        """Generate summaries only for affected communities.

        This is the main entry point for incremental summary updates.
        Only communities that changed are re-summarized.

        Args:
            delta: Community delta tracking changes

        Returns:
            Map of community_id → summary for all updated communities

        Example:
            >>> from src.components.graph_rag.community_delta_tracker import CommunityDelta
            >>> delta = CommunityDelta(new_communities={5, 6}, updated_communities={3})
            >>> summaries = await summarizer.update_summaries_for_delta(delta)
            >>> len(summaries)
            3
        """
        if not delta.has_changes():
            logger.info("no_community_changes_detected", skipping_summary_generation=True)
            return {}

        affected = delta.get_affected_communities()

        logger.info(
            "updating_summaries_for_delta",
            total_affected=len(affected),
            new=len(delta.new_communities),
            updated=len(delta.updated_communities),
            merged=len(delta.merged_communities),
            split=len(delta.split_communities),
        )

        start_time = time.time()
        summaries = {}

        for community_id in affected:
            try:
                # Fetch community data
                entities = await self._get_community_entities(community_id)
                relationships = await self._get_community_relationships(community_id)

                # Generate summary
                summary = await self.generate_summary(community_id, entities, relationships)

                # Store summary
                await self._store_summary(community_id, summary)

                summaries[community_id] = summary

            except Exception as e:
                logger.error(
                    "failed_to_update_community_summary",
                    community_id=community_id,
                    error=str(e),
                )
                continue

        total_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "community_summaries_updated",
            summaries_generated=len(summaries),
            total_time_ms=round(total_time_ms, 2),
            avg_time_per_summary_ms=round(total_time_ms / len(summaries), 2)
            if summaries
            else 0,
        )

        return summaries

    async def regenerate_all_summaries(self) -> dict[int, str]:
        """Regenerate summaries for all communities in the graph.

        This is a full rebuild operation - use sparingly. Prefer delta updates.

        Returns:
            Map of community_id → summary for all communities
        """
        logger.info("regenerating_all_community_summaries")

        # Get all unique community IDs
        cypher = """
        MATCH (e:base)
        WHERE e.community_id IS NOT NULL
        RETURN DISTINCT e.community_id AS community_id
        """

        results = await self.neo4j_client.execute_read(cypher)

        community_ids = []
        for record in results:
            community_id_str = record.get("community_id")
            if community_id_str:
                # Parse "community_5" → 5
                try:
                    community_id = int(community_id_str.split("_")[-1])
                    community_ids.append(community_id)
                except (ValueError, IndexError):
                    logger.warning(
                        "invalid_community_id_format_skipped",
                        community_id=community_id_str,
                    )

        logger.info("found_communities_to_summarize", count=len(community_ids))

        # Create a fake delta with all communities as "new"
        from src.components.graph_rag.community_delta_tracker import CommunityDelta

        delta = CommunityDelta(new_communities=set(community_ids))

        return await self.update_summaries_for_delta(delta)

    async def get_summary(self, community_id: int) -> str | None:
        """Get existing summary for a community.

        Args:
            community_id: Community ID

        Returns:
            Summary text or None if not found
        """
        cypher = """
        MATCH (cs:CommunitySummary {community_id: $community_id})
        RETURN cs.summary AS summary
        """

        results = await self.neo4j_client.execute_read(
            cypher,
            {"community_id": community_id},
        )

        if results and len(results) > 0:
            return results[0].get("summary")  # type: ignore[return-value]

        return None


# Singleton instance
_community_summarizer: CommunitySummarizer | None = None


def get_community_summarizer() -> CommunitySummarizer:
    """Get global CommunitySummarizer instance (singleton).

    Returns:
        CommunitySummarizer instance
    """
    global _community_summarizer
    if _community_summarizer is None:
        _community_summarizer = CommunitySummarizer()
    return _community_summarizer
