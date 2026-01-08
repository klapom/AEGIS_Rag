"""Dual-Level Graph Search (Local & Global Retrieval).

This module provides dual-level search functionality for graph-based retrieval:
- Local search: Entity-level queries (specific entities and relationships)
- Global search: Topic-level queries (high-level summaries, communities)
- Hybrid search: Combined local + global

Sprint 5: Feature 5.4 - Dual-Level Retrieval

Implementation uses LightRAG's built-in retrieval modes for efficient graph queries.
"""

import time
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.components.graph_rag.neo4j_client import Neo4jClient
from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.core.config import settings
from src.core.models import GraphEntity, GraphQueryResult, GraphRelationship, Topic

logger = structlog.get_logger(__name__)


class SearchMode(str, Enum):
    """Search modes for dual-level retrieval."""

    LOCAL = "local"  # Entity-level: specific entities and relationships
    GLOBAL = "global"  # Topic-level: high-level summaries, communities
    HYBRID = "hybrid"  # Combined: local + global results fused


class GraphSearchResult(BaseModel):
    """Result from graph search."""

    query: str = Field(..., description="Original query")
    mode: SearchMode = Field(..., description="Search mode used")
    answer: str = Field(default="", description="LLM-generated answer")
    entities: list[dict[str, Any]] = Field(default_factory=list, description="Retrieved entities")
    relationships: list[dict[str, Any]] = Field(
        default_factory=list, description="Retrieved relationships"
    )
    context: str = Field(default="", description="Graph context used")
    topics: list[str] = Field(default_factory=list, description="Topics/communities")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")


class DualLevelSearch:
    """Dual-level graph search with local/global/hybrid modes.

    Sprint 25 Feature 25.10: Migrated to AegisLLMProxy for multi-cloud routing.

    Provides:
    - Local search (entity-level): Retrieves specific entities and their direct relationships
    - Global search (topic-level): Retrieves high-level topics/communities and summaries
    - Hybrid search (combined): Combines both local and global results with answer fusion
    - Multi-cloud routing: Local Ollama → Alibaba Cloud → OpenAI
    - Cost tracking and observability

    Uses Neo4j for graph storage and AegisLLMProxy for answer generation.
    """

    def __init__(
        self,
        neo4j_uri: str | None = None,
        neo4j_user: str | None = None,
        neo4j_password: str | None = None,
        llm_model: str | None = None,
        ollama_base_url: str | None = None,
    ) -> None:
        """Initialize dual-level search with AegisLLMProxy.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            llm_model: Preferred model for answer generation
            ollama_base_url: Deprecated (kept for compatibility)
        """
        self.neo4j_uri = neo4j_uri or settings.neo4j_uri
        self.neo4j_user = neo4j_user or settings.neo4j_user
        self.neo4j_password = neo4j_password or settings.neo4j_password.get_secret_value()
        self.llm_model = llm_model or settings.lightrag_llm_model
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url

        # Initialize Neo4j client
        self.neo4j_client = Neo4jClient(
            uri=self.neo4j_uri,
            user=self.neo4j_user,
            password=self.neo4j_password,
        )

        # Sprint 25: Use AegisLLMProxy for multi-cloud routing
        self.proxy = get_aegis_llm_proxy()

        logger.info(
            "dual_level_search_initialized_with_proxy",
            neo4j_uri=self.neo4j_uri,
            preferred_model=self.llm_model,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def local_search(
        self, query: str, top_k: int = 5, namespaces: list[str] | None = None
    ) -> list[GraphEntity]:
        """Execute entity-level (local) search with chunk expansion.

        Sprint 78 Feature 78.1: Entity → Chunk Expansion

        Finds entities matching the query, then expands to full document chunks
        via MENTIONED_IN relationships. Returns chunks as GraphEntity objects
        for backward compatibility.

        Args:
            query: User query
            top_k: Number of chunks to retrieve
            namespaces: List of namespaces to filter by (default: None = all namespaces)

        Returns:
            list of GraphEntity objects (containing chunk data in description field)
        """
        start_time = time.time()

        logger.info("local_search_started", query=query[:100], top_k=top_k)

        try:
            # Sprint 78 Feature 78.2 & 78.4: Use SmartEntityExpander instead of manual stop words
            # LLM extracts entities directly → stop words filtering not needed anymore
            from src.components.graph_rag.entity_expansion import SmartEntityExpander
            from src.core.config import settings

            # Sprint 78 Feature 78.5: Load config from settings (UI-configurable via env vars)
            expander = SmartEntityExpander(
                neo4j_client=self.neo4j_client,
                graph_expansion_hops=settings.graph_expansion_hops,
                min_entities_threshold=settings.graph_min_entities_threshold,
                max_synonyms_per_entity=settings.graph_max_synonyms_per_entity,
            )

            # Stage 1-3: Expand entities (LLM → Graph → Synonyms)
            expanded_entity_names = await expander.expand_entities(
                query=query,
                namespaces=namespaces or ["default"],
                top_k=top_k * 3
            )

            # Sprint 78 Feature 78.1: Entity → Chunk Expansion
            # Use expanded entity names to find chunks they're mentioned in
            if namespaces:
                cypher_query = """
                MATCH (e:base)-[:MENTIONED_IN]->(c:chunk)
                WHERE e.namespace_id IN $namespaces
                  AND c.namespace_id IN $namespaces
                  AND e.entity_name IN $expanded_entities
                WITH c, collect(DISTINCT e.entity_name) AS matched_entities, count(DISTINCT e) AS entity_count
                RETURN
                  c.chunk_id AS id,
                  c.text AS chunk_text,
                  c.document_id AS document_id,
                  c.chunk_index AS chunk_index,
                  matched_entities,
                  entity_count
                ORDER BY entity_count DESC
                LIMIT $top_k
                """
            else:
                cypher_query = """
                MATCH (e:base)-[:MENTIONED_IN]->(c:chunk)
                WHERE e.entity_name IN $expanded_entities
                WITH c, collect(DISTINCT e.entity_name) AS matched_entities, count(DISTINCT e) AS entity_count
                RETURN
                  c.chunk_id AS id,
                  c.text AS chunk_text,
                  c.document_id AS document_id,
                  c.chunk_index AS chunk_index,
                  matched_entities,
                  entity_count
                ORDER BY entity_count DESC
                LIMIT $top_k
                """

            # Build query parameters
            params = {"expanded_entities": expanded_entity_names, "top_k": top_k}
            if namespaces:
                params["namespaces"] = namespaces

            results = await self.neo4j_client.execute_read(cypher_query, params)

            # Sprint 78: Convert chunks to GraphEntity objects for backward compatibility
            # The "description" field now contains the full chunk text instead of entity description
            entities = []
            for i, record in enumerate(results):
                # Create a pseudo-entity representing the chunk
                matched_entities_str = ", ".join(record.get("matched_entities", [])[:5])
                entity_count = record.get("entity_count", 0)

                entity = GraphEntity(
                    id=record.get("id", f"chunk_{i}"),
                    name=f"Chunk with {entity_count} entities: {matched_entities_str}",
                    type="CHUNK",
                    description=record.get("chunk_text", ""),  # FULL CHUNK TEXT HERE!
                    properties={
                        "page_no": record.get("page_no"),
                        "heading": record.get("heading"),
                        "matched_entities": record.get("matched_entities", []),
                        "entity_match_count": entity_count,
                    },
                    source_document=record.get("document_id", ""),
                    confidence=1.0 / (1.0 + i),  # Simple ranking
                )
                entities.append(entity)

            execution_time = (time.time() - start_time) * 1000

            logger.info(
                "local_search_completed",
                query=query[:100],
                chunks_found=len(entities),
                execution_time_ms=execution_time,
            )

            return entities

        except Exception as e:
            logger.error("local_search_failed", query=query[:100], error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def global_search(
        self, query: str, top_k: int = 3, namespaces: list[str] | None = None
    ) -> list[Topic]:
        """Execute topic-level (global) search.

        Retrieves high-level topics/communities relevant to the query.
        Uses community detection algorithms (e.g., Leiden) to identify topic clusters.

        Args:
            query: User query
            top_k: Number of topics to retrieve
            namespaces: List of namespaces to filter by (default: None = all namespaces)

        Returns:
            list of Topic objects
        """
        start_time = time.time()

        logger.info("global_search_started", query=query[:100], top_k=top_k)

        try:
            # Query Neo4j for topic-level information
            # This is a simplified implementation - production would use
            # community detection algorithms (Leiden, Louvain)
            # Sprint 76: Add namespace filtering for multi-tenant isolation
            # Sprint 76: Use entity_name/entity_type (actual property names in Neo4j)
            # Sprint 77 Feature 77.6: Fix text matching - search for individual words, not concatenated string

            # Sprint 42: Extract meaningful query terms (skip stop words)
            stop_words = {
                "was",
                "weißt",
                "du",
                "über",
                "wie",
                "ist",
                "sind",
                "der",
                "die",
                "das",
                "ein",
                "eine",
                "und",
                "oder",
                "mit",
                "von",
                "zu",
                "für",
                "auf",
                "in",
                "what",
                "is",
                "are",
                "the",
                "a",
                "an",
                "and",
                "or",
                "with",
                "from",
                "to",
                "for",
                "on",
                "who",
                "where",
                "when",
                "how",
                "why",
                "tell",
                "me",
                "about",
                "know",
                "do",
                "you",
                "can",
                "could",
                "would",
            }
            words = query.lower().split()
            meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
            # Use meaningful words if found, otherwise use full query words
            query_words = meaningful_words if meaningful_words else query.lower().split()

            # Sprint 77 Feature 77.6: Build Cypher query with ANY word matching
            # Search for entities that contain ANY of the query words (not all concatenated)
            if namespaces:
                cypher_query = """
                MATCH (e:base)
                WHERE e.namespace_id IN $namespaces
                  AND ANY(word IN $query_words WHERE
                      toLower(e.entity_name) CONTAINS toLower(word)
                      OR toLower(e.description) CONTAINS toLower(word))
                WITH e.entity_type AS entity_type, collect(e.entity_name) AS entity_names,
                     collect(e.entity_id) AS entity_ids, count(e) AS entity_count
                RETURN entity_type AS topic_name,
                       entity_names[..5] AS sample_entities,
                       entity_ids AS entity_ids,
                       entity_count
                ORDER BY entity_count DESC
                LIMIT $top_k
                """
            else:
                cypher_query = """
                MATCH (e:base)
                WHERE ANY(word IN $query_words WHERE
                      toLower(e.entity_name) CONTAINS toLower(word)
                      OR toLower(e.description) CONTAINS toLower(word))
                WITH e.entity_type AS entity_type, collect(e.entity_name) AS entity_names,
                     collect(e.entity_id) AS entity_ids, count(e) AS entity_count
                RETURN entity_type AS topic_name,
                       entity_names[..5] AS sample_entities,
                       entity_ids AS entity_ids,
                       entity_count
                ORDER BY entity_count DESC
                LIMIT $top_k
                """

            # Build query parameters
            params = {"query_words": query_words, "top_k": top_k}
            if namespaces:
                params["namespaces"] = namespaces

            results = await self.neo4j_client.execute_read(cypher_query, params)

            # Convert to Topic objects
            topics = []
            for i, record in enumerate(results):
                topic = Topic(
                    id=f"topic_{i}",
                    name=record.get("topic_name", "Unknown Topic"),
                    summary=f"Topic containing {record.get('entity_count', 0)} entities",
                    entities=record.get("entity_ids", []),
                    keywords=record.get("sample_entities", []),
                    score=1.0 - (i * 0.1),  # Simple relevance scoring
                )
                topics.append(topic)

            execution_time = (time.time() - start_time) * 1000

            logger.info(
                "global_search_completed",
                query=query[:100],
                topics_found=len(topics),
                execution_time_ms=execution_time,
            )

            return topics

        except Exception as e:
            logger.error("global_search_failed", query=query[:100], error=str(e))
            raise

    async def _generate_answer(
        self,
        query: str,
        context: str,
    ) -> str:
        """Generate answer from graph context using AegisLLMProxy.

        Sprint 25: Migrated to AegisLLMProxy for multi-cloud routing.

        Args:
            query: User query
            context: Graph context (entities, relationships, topics)

        Returns:
            Generated answer string
        """
        prompt = f"""Based on the following graph context, answer the user's question.

Context:
{context}

Question: {query}

Provide a concise and accurate answer based only on the information in the context.
If the context doesn't contain enough information, say so.

Answer:"""

        try:
            # Sprint 25: Use AegisLLMProxy for answer generation
            task = LLMTask(
                task_type=TaskType.ANSWER_GENERATION,
                prompt=prompt,
                quality_requirement=QualityRequirement.HIGH,
                complexity=Complexity.MEDIUM,
                max_tokens=512,
                temperature=0.3,
                model_local=self.llm_model,
            )

            result = await self.proxy.generate(task)

            logger.debug(
                "answer_generated_via_proxy",
                provider=result.provider,
                model=result.model,
                cost_usd=result.cost_usd,
                latency_ms=result.latency_ms,
            )

            return result.content.strip()

        except Exception as e:
            logger.error("answer_generation_failed", error=str(e))
            return "Unable to generate answer from graph context."

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def hybrid_search(
        self, query: str, top_k: int = 10, namespaces: list[str] | None = None
    ) -> GraphQueryResult:
        """Execute combined local + global search with answer generation.

        Combines entity-level and topic-level results, generates an answer
        from the combined context.

        Args:
            query: User query
            top_k: Total number of results to retrieve (split between local/global)
            namespaces: List of namespaces to filter by (default: None = all namespaces)

        Returns:
            GraphQueryResult with combined information and generated answer
        """
        start_time = time.time()

        logger.info("hybrid_search_started", query=query[:100], top_k=top_k)

        try:
            # Split top_k between local and global
            local_k = max(top_k // 2, 3)
            global_k = max(top_k - local_k, 2)

            # Execute both searches in parallel would be ideal, but for simplicity:
            entities = await self.local_search(query, top_k=local_k, namespaces=namespaces)
            topics = await self.global_search(query, top_k=global_k, namespaces=namespaces)

            # Retrieve relationships for found entities
            relationships = await self._get_entity_relationships(entities)

            # Build context for answer generation
            context = self._build_context(entities, relationships, topics)

            # Sprint 52: REMOVED redundant LLM answer generation
            # The answer is generated by llm_answer_node in graph.py
            # This call was wasting ~1.5-23s per request
            answer = ""

            execution_time = (time.time() - start_time) * 1000

            result = GraphQueryResult(
                query=query,
                answer=answer,
                entities=entities,
                relationships=relationships,
                topics=topics,
                context=context,
                mode="hybrid",
                metadata={
                    "execution_time_ms": execution_time,
                    "entities_found": len(entities),
                    "relationships_found": len(relationships),
                    "topics_found": len(topics),
                },
            )

            logger.info(
                "hybrid_search_completed",
                query=query[:100],
                entities=len(entities),
                relationships=len(relationships),
                topics=len(topics),
                execution_time_ms=execution_time,
            )

            return result

        except Exception as e:
            logger.error("hybrid_search_failed", query=query[:100], error=str(e))
            raise

    async def _get_entity_relationships(
        self, entities: list[GraphEntity]
    ) -> list[GraphRelationship]:
        """Get relationships for a list of entities.

        Args:
            entities: list of entities

        Returns:
            list of relationships involving these entities
        """
        if not entities:
            return []

        try:
            entity_names = [e.name for e in entities]

            # Sprint 76: Use entity_name (actual property name in Neo4j)
            cypher_query = """
            MATCH (e1:base)-[r:RELATED_TO]->(e2:base)
            WHERE e1.entity_name IN $entity_names OR e2.entity_name IN $entity_names
            RETURN r.relationship_id AS id, e1.entity_name AS source, e2.entity_name AS target,
                   r.relationship_type AS type, r.description AS description,
                   r.source_id AS source_document
            LIMIT 20
            """

            results = await self.neo4j_client.execute_read(
                cypher_query,
                {"entity_names": entity_names},
            )

            relationships = []
            for record in results:
                rel = GraphRelationship(
                    id=record.get("id", ""),
                    source=record.get("source", ""),
                    target=record.get("target", ""),
                    type=record.get("type", "RELATED_TO"),
                    description=record.get("description", ""),
                    properties=record.get("properties", {}),
                    source_document=record.get("source_document"),
                    confidence=record.get("confidence", 1.0),
                )
                relationships.append(rel)

            return relationships

        except Exception as e:
            logger.error("get_relationships_failed", error=str(e))
            return []

    def _build_context(
        self,
        entities: list[GraphEntity],
        relationships: list[GraphRelationship],
        topics: list[Topic],
    ) -> str:
        """Build context string from graph elements.

        Args:
            entities: Retrieved entities
            relationships: Retrieved relationships
            topics: Retrieved topics

        Returns:
            Formatted context string
        """
        context_parts = []

        # Add entities
        if entities:
            context_parts.append("Entities:")
            for entity in entities[:10]:  # Limit to top 10
                context_parts.append(f"- {entity.name} ({entity.type}): {entity.description}")

        # Add relationships
        if relationships:
            context_parts.append("\nRelationships:")
            for rel in relationships[:10]:  # Limit to top 10
                context_parts.append(
                    f"- {rel.source} --[{rel.type}]--> {rel.target}: {rel.description}"
                )

        # Add topics
        if topics:
            context_parts.append("\nTopics:")
            for topic in topics:
                context_parts.append(
                    f"- {topic.name}: {topic.summary} (Keywords: {', '.join(topic.keywords[:5])})"
                )

        return "\n".join(context_parts)


# Singleton instance
_dual_level_search: DualLevelSearch | None = None


def get_dual_level_search() -> DualLevelSearch:
    """Get global DualLevelSearch instance (singleton).

    Returns:
        DualLevelSearch instance
    """
    global _dual_level_search
    if _dual_level_search is None:
        _dual_level_search = DualLevelSearch()
    return _dual_level_search
