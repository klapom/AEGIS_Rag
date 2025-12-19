"""Knowledge Graph Domain Protocols.

Sprint 57 Feature 57.1: Protocol definitions for graph operations.
Enables dependency injection and improves testability.

Usage:
    from src.domains.knowledge_graph.protocols import (
        EntityExtractor,
        RelationExtractor,
        GraphStorage,
        GraphQueryService,
        CommunityService,
        LLMConfigProvider,
    )

These protocols define interfaces for:
- Entity and relation extraction
- Graph storage operations
- Query execution
- Community detection and summarization
- LLM configuration
"""

from typing import Protocol, Any, AsyncIterator, runtime_checkable


@runtime_checkable
class EntityExtractor(Protocol):
    """Protocol for entity extraction from text.

    Implementations should extract named entities (persons, organizations,
    locations, concepts) from unstructured text.

    Example:
        >>> class LLMEntityExtractor:
        ...     async def extract_entities(self, text: str, metadata: dict | None = None) -> list[dict]:
        ...         # Use LLM to extract entities
        ...         pass
    """

    async def extract_entities(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract entities from text.

        Args:
            text: Source text to extract entities from
            metadata: Optional metadata for context (document_id, namespace, etc.)

        Returns:
            List of extracted entities, each containing:
            - name: str - Entity name
            - type: str - Entity type (PERSON, ORG, CONCEPT, etc.)
            - confidence: float - Extraction confidence (0.0-1.0)
            - attributes: dict - Additional attributes
        """
        ...


@runtime_checkable
class RelationExtractor(Protocol):
    """Protocol for relation extraction between entities.

    Implementations should identify relationships between
    previously extracted entities.
    """

    async def extract_relations(
        self,
        entities: list[dict[str, Any]],
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract relations between entities.

        Args:
            entities: List of extracted entities
            text: Original source text
            metadata: Optional metadata for context

        Returns:
            List of extracted relations, each containing:
            - source: str - Source entity name
            - target: str - Target entity name
            - relation_type: str - Relationship type
            - confidence: float - Extraction confidence
            - attributes: dict - Additional attributes
        """
        ...


@runtime_checkable
class GraphStorage(Protocol):
    """Protocol for graph persistence.

    Implementations provide CRUD operations for entities and
    relationships in a graph database.

    Example:
        >>> class Neo4jStorage:
        ...     async def upsert_entity(self, entity: dict) -> str:
        ...         # Store in Neo4j
        ...         pass
    """

    async def upsert_entity(self, entity: dict[str, Any]) -> str:
        """Upsert an entity to the graph.

        Args:
            entity: Entity data with 'name', 'type', and optional attributes

        Returns:
            Entity ID in the graph
        """
        ...

    async def upsert_relation(self, relation: dict[str, Any]) -> str:
        """Upsert a relation to the graph.

        Args:
            relation: Relation data with 'source', 'target', 'type'

        Returns:
            Relation ID in the graph
        """
        ...

    async def query(
        self,
        cypher: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query.

        Args:
            cypher: Cypher query string
            params: Optional query parameters

        Returns:
            List of result records
        """
        ...

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity from the graph.

        Args:
            entity_id: ID of entity to delete

        Returns:
            True if deleted, False if not found
        """
        ...


@runtime_checkable
class GraphQueryService(Protocol):
    """Protocol for graph querying.

    Implementations provide semantic querying capabilities
    using local, global, or hybrid strategies.
    """

    async def query_local(
        self,
        query: str,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Execute local (entity-focused) query.

        Args:
            query: Natural language query
            top_k: Number of results to return

        Returns:
            Query results with entities, relations, and context
        """
        ...

    async def query_global(
        self,
        query: str,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Execute global (community-focused) query.

        Args:
            query: Natural language query
            top_k: Number of communities to consider

        Returns:
            Query results with community summaries and context
        """
        ...

    async def query_hybrid(
        self,
        query: str,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Execute hybrid query combining local and global.

        Args:
            query: Natural language query
            top_k: Number of results to return

        Returns:
            Combined query results
        """
        ...


@runtime_checkable
class CommunityService(Protocol):
    """Protocol for community detection and summarization.

    Implementations handle graph community operations including
    detection, summarization, and tracking changes.
    """

    async def detect_communities(self) -> list[dict[str, Any]]:
        """Detect communities in the graph.

        Returns:
            List of detected communities with:
            - id: str - Community ID
            - members: list[str] - Entity IDs in community
            - size: int - Number of members
        """
        ...

    async def get_community(self, community_id: str) -> dict[str, Any] | None:
        """Get a specific community by ID.

        Args:
            community_id: ID of community to retrieve

        Returns:
            Community data or None if not found
        """
        ...

    async def summarize_community(
        self,
        community_id: str,
        llm_config_provider: "LLMConfigProvider | None" = None,
    ) -> str:
        """Generate summary for a community.

        Args:
            community_id: ID of community to summarize
            llm_config_provider: Optional LLM configuration provider

        Returns:
            Generated summary text
        """
        ...


@runtime_checkable
class LLMConfigProvider(Protocol):
    """Protocol for LLM configuration.

    Resolves OPL-001 circular dependency by providing LLM config
    without importing from admin modules.

    Example:
        >>> class AdminLLMConfigProvider:
        ...     async def get_community_summary_model(self) -> str:
        ...         return await get_model_from_redis()
    """

    async def get_community_summary_model(self) -> str:
        """Get configured model for community summaries.

        Returns:
            Model name string (e.g., "llama3.2:8b")
        """
        ...

    async def get_extraction_model(self) -> str:
        """Get configured model for entity extraction.

        Returns:
            Model name string
        """
        ...


@runtime_checkable
class DeduplicationService(Protocol):
    """Protocol for entity and relation deduplication.

    Implementations handle semantic deduplication to merge
    similar entities or relations.
    """

    async def deduplicate_entities(
        self,
        entities: list[dict[str, Any]],
        threshold: float = 0.85,
    ) -> list[dict[str, Any]]:
        """Deduplicate entities based on semantic similarity.

        Args:
            entities: List of entities to deduplicate
            threshold: Similarity threshold for merging

        Returns:
            Deduplicated list of entities
        """
        ...

    async def deduplicate_relations(
        self,
        relations: list[dict[str, Any]],
        threshold: float = 0.85,
    ) -> list[dict[str, Any]]:
        """Deduplicate relations based on semantic similarity.

        Args:
            relations: List of relations to deduplicate
            threshold: Similarity threshold for merging

        Returns:
            Deduplicated list of relations
        """
        ...


@runtime_checkable
class GraphAnalytics(Protocol):
    """Protocol for graph analytics and metrics.

    Implementations provide analytical capabilities for
    understanding graph structure and content.
    """

    async def get_statistics(self) -> dict[str, Any]:
        """Get graph statistics.

        Returns:
            Statistics including:
            - entity_count: int
            - relation_count: int
            - community_count: int
            - avg_degree: float
        """
        ...

    async def get_entity_recommendations(
        self,
        entity_id: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Get entity recommendations based on graph structure.

        Args:
            entity_id: Source entity ID
            top_k: Number of recommendations

        Returns:
            List of recommended entities with scores
        """
        ...


__all__ = [
    "EntityExtractor",
    "RelationExtractor",
    "GraphStorage",
    "GraphQueryService",
    "CommunityService",
    "LLMConfigProvider",
    "DeduplicationService",
    "GraphAnalytics",
]
