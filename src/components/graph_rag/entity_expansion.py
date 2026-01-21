"""3-Stage Entity Expansion for Graph Search.

Sprint 78 Feature 78.2

Combines LLM entity extraction, graph traversal, and semantic expansion
for improved entity retrieval precision and recall.

Architecture:
    STAGE 1: LLM extracts entities from query
    STAGE 2: Graph expands via N-hop traversal (configurable 1-3 hops)
    STAGE 3: LLM generates synonyms (fallback if graph sparse, configurable threshold)
    STAGE 4: Semantic reranking via BGE-M3 (Feature 78.3)
"""

from typing import Any
import numpy as np
import structlog

from src.components.graph_rag.neo4j_client import Neo4jClient
from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.shared.embedding_service import get_embedding_service
from src.domains.llm_integration.models import (
    LLMTask,
    TaskType,
    Complexity,
    QualityRequirement,
)

logger = structlog.get_logger(__name__)


class SmartEntityExpander:
    """3-Stage Entity Expansion with Graph + LLM.

    Sprint 78 Feature 78.2

    Stage 1: LLM extracts entities from query
    Stage 2: Graph expands via N-hop traversal (configurable)
    Stage 3: LLM generates synonyms (fallback if graph sparse, configurable)
    Stage 4: Semantic reranking via BGE-M3

    UI-Configurable Parameters:
        - graph_expansion_hops: 1-3 (default: 1)
        - min_entities_threshold: 5-20 (default: 10)
        - max_synonyms_per_entity: 1-5 (default: 3)
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        graph_expansion_hops: int = 1,
        min_entities_threshold: int = 10,
        max_synonyms_per_entity: int = 3,
    ):
        """Initialize SmartEntityExpander.

        Args:
            neo4j_client: Neo4j client instance
            graph_expansion_hops: Number of hops for graph expansion (1-3)
            min_entities_threshold: Minimum entities before synonym fallback (5-20)
            max_synonyms_per_entity: Max synonyms to generate per entity (1-5)
        """
        self.neo4j_client = neo4j_client or Neo4jClient()
        self.llm_proxy = get_aegis_llm_proxy()
        self.embedding_service = get_embedding_service()

        # UI-Configurable parameters
        self.graph_expansion_hops = max(1, min(3, graph_expansion_hops))  # Clamp 1-3
        self.min_entities_threshold = max(5, min(20, min_entities_threshold))  # Clamp 5-20
        self.max_synonyms_per_entity = max(1, min(5, max_synonyms_per_entity))  # Clamp 1-5

        logger.info(
            "smart_entity_expander_initialized",
            graph_expansion_hops=self.graph_expansion_hops,
            min_entities_threshold=self.min_entities_threshold,
            max_synonyms_per_entity=self.max_synonyms_per_entity,
        )

    async def _namespace_has_entities(self, namespaces: list[str]) -> bool:
        """Early-exit check: Does namespace have any entities?

        Sprint 113: Performance optimization - skip expensive LLM calls
        if the namespace has no entities in Neo4j.

        Args:
            namespaces: List of namespaces to check

        Returns:
            True if namespace has at least 1 entity, False otherwise
        """
        cypher = """
        MATCH (e:base)
        WHERE e.namespace_id IN $namespaces
        RETURN count(e) > 0 AS has_entities
        LIMIT 1
        """
        try:
            results = await self.neo4j_client.execute_read(cypher, {"namespaces": namespaces})
            if results and len(results) > 0:
                return results[0].get("has_entities", False)
            return False
        except Exception as e:
            logger.warning(
                "namespace_entity_check_failed",
                error=str(e),
                namespaces=namespaces,
                fallback="proceeding_with_expansion",
            )
            # On error, proceed with expansion (don't break functionality)
            return True

    async def expand_entities(
        self, query: str, namespaces: list[str], top_k: int = 10
    ) -> tuple[list[str], int]:
        """Execute 3-stage entity expansion.

        Args:
            query: User query
            namespaces: List of namespaces to search in
            top_k: Target number of final entities

        Returns:
            Tuple of (expanded entity names, hops_used)
            - List of expanded entity names (initial + graph + synonyms)
            - Number of graph hops used (0 if graph expansion not used)
        """
        # Sprint 113: Early-exit if namespace has no entities
        # This avoids 2x LLM calls (~10-12s) when graph is empty
        if not await self._namespace_has_entities(namespaces):
            logger.info(
                "entity_expansion_early_exit",
                reason="namespace_has_no_entities",
                namespaces=namespaces,
                query=query[:50],
            )
            return [], 0

        # STAGE 1: LLM Entity Extraction
        initial_entities = await self._extract_entities_llm(query)
        logger.info(
            "stage1_llm_extraction",
            query=query[:50],
            entities_found=len(initial_entities),
            entities=initial_entities[:5],
        )

        # Sprint 115: Early-exit if LLM found no entities
        # Avoids unnecessary graph expansion and synonym generation
        if not initial_entities or len(initial_entities) == 0:
            logger.info(
                "entity_expansion_early_exit",
                reason="llm_found_no_entities",
                query=query[:50],
            )
            return [], 0

        # STAGE 2: Graph Expansion (N-hop configurable)
        graph_expanded = await self._expand_via_graph(
            initial_entities, namespaces, max_hops=self.graph_expansion_hops
        )
        logger.info(
            "stage2_graph_expansion",
            initial_count=len(initial_entities),
            expanded_count=len(graph_expanded),
            hops_used=self.graph_expansion_hops,
        )

        # Sprint 115: Early-exit if graph expansion returned nothing
        # If both LLM extraction AND graph expansion found nothing,
        # skip expensive synonym generation (saves ~10-15s per query)
        if not graph_expanded or len(graph_expanded) == 0:
            logger.info(
                "entity_expansion_early_exit",
                reason="graph_expansion_empty",
                query=query[:50],
                initial_entities_count=len(initial_entities),
            )
            return [], 0

        # STAGE 3: LLM Synonym Fallback (only if graph sparse)
        final_entities = graph_expanded
        if len(graph_expanded) < self.min_entities_threshold:
            synonyms = await self._generate_synonyms_llm(
                initial_entities[:2],  # Top-2 only for performance
                max_per_entity=self.max_synonyms_per_entity,
            )
            final_entities = graph_expanded + synonyms
            logger.info(
                "stage3_synonym_fallback",
                graph_count=len(graph_expanded),
                synonym_count=len(synonyms),
                final_count=len(final_entities),
                threshold=self.min_entities_threshold,
            )
        else:
            logger.info(
                "stage3_synonym_skipped",
                reason="graph_expansion_sufficient",
                entities_found=len(graph_expanded),
                threshold=self.min_entities_threshold,
            )

        return final_entities, self.graph_expansion_hops

    async def expand_and_rerank(
        self, query: str, namespaces: list[str], top_k: int = 10
    ) -> tuple[list[tuple[str, float]], int]:
        """Expand entities and rerank by semantic similarity.

        Sprint 78 Feature 78.3: Semantic Entity Reranking

        Args:
            query: User query
            namespaces: List of namespaces to search in
            top_k: Number of top entities to return

        Returns:
            Tuple of (scored_entities, hops_used)
            - List of (entity_name, semantic_score) tuples, sorted by score
            - Number of graph hops used
        """
        # Stages 1-3: Expansion
        expanded_entities, hops_used = await self.expand_entities(query, namespaces, top_k * 3)

        if not expanded_entities:
            return [], hops_used

        # Stage 4: Semantic Reranking
        query_embedding = await self.embedding_service.encode(query)

        scored_entities = []
        for entity_name in expanded_entities:
            # Embed entity name on-the-fly
            entity_embedding = await self.embedding_service.encode(entity_name)

            # Cosine similarity
            similarity = self._cosine_similarity(query_embedding, entity_embedding)

            scored_entities.append((entity_name, float(similarity)))

        # Sort by similarity, return top-k
        scored_entities.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            "stage4_semantic_reranking",
            total_entities=len(expanded_entities),
            reranked_top_k=min(top_k, len(scored_entities)),
            top_score=scored_entities[0][1] if scored_entities else 0.0,
            hops_used=hops_used,
        )

        return scored_entities[:top_k], hops_used

    async def _extract_entities_llm(self, query: str) -> list[str]:
        """Stage 1: Extract entities from query using LLM.

        Args:
            query: User query

        Returns:
            List of entity names extracted from query
        """
        prompt = f"""Extract key entities, concepts, named entities, and important topics from this question.
Return only the entity names, one per line.

Examples:
- Question: "What are the global implications of abortion?"
  Entities:
  global implications
  abortion
  reproductive rights

- Question: "Which companies emit most GHG?"
  Entities:
  GHG emissions
  companies
  greenhouse gas

Question: {query}

Entities:"""

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt=prompt,
            complexity=Complexity.LOW,
            quality_requirement=QualityRequirement.MEDIUM,
        )
        response = await self.llm_proxy.generate(task)

        # Parse entities (one per line)
        entities = [
            line.strip()
            for line in response.content.split("\n")
            if line.strip() and not line.startswith("#") and not line.startswith("-")
        ]

        # Deduplicate and limit
        unique_entities = []
        seen = set()
        for e in entities:
            e_lower = e.lower()
            if e_lower not in seen:
                unique_entities.append(e)
                seen.add(e_lower)

        return unique_entities[:10]  # Max 10 initial entities

    async def _expand_via_graph(
        self, initial_entities: list[str], namespaces: list[str], max_hops: int = 1
    ) -> list[str]:
        """Stage 2: Expand entities via graph traversal.

        Args:
            initial_entities: Entities extracted from query
            namespaces: List of namespaces to filter by
            max_hops: Maximum number of hops for expansion (1-3)

        Returns:
            List of expanded entity names (initial + connected)
        """
        if not initial_entities:
            return []

        # Build Cypher query with variable hop count
        # Use path expressions: -[r*1..N]- for N-hop traversal
        hop_pattern = f"*1..{max_hops}" if max_hops > 1 else ""

        cypher_query = f"""
        // Find initial entities (case-insensitive partial match)
        MATCH (e1:base)
        WHERE e1.namespace_id IN $namespaces
          AND ANY(init_entity IN $initial_entities WHERE
              toLower(e1.entity_name) CONTAINS toLower(init_entity)
              OR toLower(init_entity) CONTAINS toLower(e1.entity_name))

        // Expand to connected entities (N-hop traversal)
        OPTIONAL MATCH path = (e1)-[r:RELATES_TO|PART_OF|SIMILAR_TO{hop_pattern}]-(e2:base)
        WHERE e2.namespace_id IN $namespaces
          AND e2 <> e1  // Exclude self-loops

        // Collect all entities: initial + expanded
        WITH collect(DISTINCT e1.entity_name) + collect(DISTINCT e2.entity_name) AS all_names
        UNWIND all_names AS name
        WITH DISTINCT name
        WHERE name IS NOT NULL
        RETURN name
        LIMIT 50
        """

        params = {
            "initial_entities": initial_entities,
            "namespaces": namespaces,
        }

        try:
            results = await self.neo4j_client.execute_read(cypher_query, params)
            expanded_names = [r.get("name") for r in results if r.get("name")]

            return expanded_names
        except Exception as e:
            logger.warning(
                "graph_expansion_failed",
                error=str(e),
                hops=max_hops,
                fallback="returning_initial_entities",
            )
            # Fallback: return initial entities if graph expansion fails
            return initial_entities

    async def _generate_synonyms_llm(
        self, entities: list[str], max_per_entity: int = 3
    ) -> list[str]:
        """Stage 3: Generate synonyms for entities using LLM.

        Args:
            entities: Entity names to generate synonyms for
            max_per_entity: Maximum synonyms per entity

        Returns:
            List of synonym terms
        """
        if not entities:
            return []

        prompt = f"""Generate {max_per_entity} synonyms, related terms, or paraphrases for each entity.
Return only the synonym terms, one per line.

Examples:
- Entity: "reproductive rights"
  Synonyms:
  procreative autonomy
  reproductive freedom
  reproductive health rights

- Entity: "abortion"
  Synonyms:
  pregnancy termination
  induced abortion
  reproductive choice

Entities:
{chr(10).join(f'- {e}' for e in entities)}

Synonyms:"""

        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            complexity=Complexity.LOW,
            quality_requirement=QualityRequirement.MEDIUM,
        )
        response = await self.llm_proxy.generate(task)

        synonyms = [
            line.strip()
            for line in response.content.split("\n")
            if line.strip() and not line.startswith("-") and not line.startswith("#")
        ]

        # Deduplicate
        unique_synonyms = []
        seen = set()
        for s in synonyms:
            s_lower = s.lower()
            if s_lower not in seen:
                unique_synonyms.append(s)
                seen.add(s_lower)

        return unique_synonyms[: len(entities) * max_per_entity]

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        # Ensure vectors are 1D
        if vec1.ndim > 1:
            vec1 = vec1.flatten()
        if vec2.ndim > 1:
            vec2 = vec2.flatten()

        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))
