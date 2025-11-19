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
    async def local_search(self, query: str, top_k: int = 5) -> list[GraphEntity]:
        """Execute entity-level (local) search.

        Retrieves specific entities and their direct relationships relevant to the query.

        Args:
            query: User query
            top_k: Number of entities to retrieve

        Returns:
            list of GraphEntity objects
        """
        start_time = time.time()

        logger.info("local_search_started", query=query[:100], top_k=top_k)

        try:
            # Query Neo4j for entities matching the query
            # Use full-text search or embedding similarity (simplified version here)
            cypher_query = """
            MATCH (e:Entity)
            WHERE toLower(e.name) CONTAINS toLower($query_term)
               OR toLower(e.description) CONTAINS toLower($query_term)
            RETURN e.id AS id, e.name AS name, e.type AS type,
                   e.description AS description, e.properties AS properties,
                   e.source_document AS source_document, e.confidence AS confidence
            LIMIT $top_k
            """

            # Extract query terms (simple approach - first few words)
            query_term = " ".join(query.split()[:3])

            results = await self.neo4j_client.execute_read(
                cypher_query,
                {"query_term": query_term, "top_k": top_k},
            )

            # Convert to GraphEntity objects
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

            execution_time = (time.time() - start_time) * 1000

            logger.info(
                "local_search_completed",
                query=query[:100],
                entities_found=len(entities),
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
    async def global_search(self, query: str, top_k: int = 3) -> list[Topic]:
        """Execute topic-level (global) search.

        Retrieves high-level topics/communities relevant to the query.
        Uses community detection algorithms (e.g., Leiden) to identify topic clusters.

        Args:
            query: User query
            top_k: Number of topics to retrieve

        Returns:
            list of Topic objects
        """
        start_time = time.time()

        logger.info("global_search_started", query=query[:100], top_k=top_k)

        try:
            # Query Neo4j for topic-level information
            # This is a simplified implementation - production would use
            # community detection algorithms (Leiden, Louvain)
            cypher_query = """
            MATCH (e:Entity)
            WHERE toLower(e.name) CONTAINS toLower($query_term)
               OR toLower(e.description) CONTAINS toLower($query_term)
            WITH e.type AS entity_type, collect(e.name) AS entity_names,
                 collect(e.id) AS entity_ids, count(e) AS entity_count
            RETURN entity_type AS topic_name,
                   entity_names[..5] AS sample_entities,
                   entity_ids AS entity_ids,
                   entity_count
            ORDER BY entity_count DESC
            LIMIT $top_k
            """

            query_term = " ".join(query.split()[:3])

            results = await self.neo4j_client.execute_read(
                cypher_query,
                {"query_term": query_term, "top_k": top_k},
            )

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
    async def hybrid_search(self, query: str, top_k: int = 10) -> GraphQueryResult:
        """Execute combined local + global search with answer generation.

        Combines entity-level and topic-level results, generates an answer
        from the combined context.

        Args:
            query: User query
            top_k: Total number of results to retrieve (split between local/global)

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
            entities = await self.local_search(query, top_k=local_k)
            topics = await self.global_search(query, top_k=global_k)

            # Retrieve relationships for found entities
            relationships = await self._get_entity_relationships(entities)

            # Build context for answer generation
            context = self._build_context(entities, relationships, topics)

            # Generate answer
            answer = await self._generate_answer(query, context)

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

            cypher_query = """
            MATCH (e1:Entity)-[r:RELATED_TO]->(e2:Entity)
            WHERE e1.name IN $entity_names OR e2.name IN $entity_names
            RETURN r.id AS id, e1.name AS source, e2.name AS target, r.type AS type,
                   r.description AS description, r.properties AS properties,
                   r.source_document AS source_document, r.confidence AS confidence
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
