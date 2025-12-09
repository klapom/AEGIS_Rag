"""Namespace Management for Multi-Tenant Document Isolation.

Sprint 41 Feature 41.1: Namespace Isolation Layer

This module provides unified namespace management across all storage backends:
- Qdrant: Payload-based filtering (namespace_id field)
- Neo4j: Property-based filtering (namespace_id property on all nodes)
- BM25: In-memory filtering by namespace
- Redis: Key prefix isolation

Enterprise Use Case:
- "general": Company-wide documents (accessible to all)
- "user_proj_xyz": User-specific project documents (isolated)

Query Examples:
- General question: namespaces=["general"]
- Project question: namespaces=["general", "user_proj_123"]
- Benchmark evaluation: namespaces=["eval_hotpotqa"]
"""

from dataclasses import dataclass
from typing import Any

import structlog
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    PayloadSchemaType,
)

from src.core.neo4j_safety import SecureNeo4jClient, get_secure_neo4j_client

logger = structlog.get_logger(__name__)


# Default namespace for existing/legacy data
DEFAULT_NAMESPACE = "default"

# Reserved namespace prefixes
NAMESPACE_PREFIXES = {
    "eval_": "Evaluation/Benchmark namespace",
    "user_": "User-specific namespace",
    "proj_": "Project namespace",
    "test_": "Test namespace (auto-cleanup)",
}


@dataclass
class NamespaceInfo:
    """Information about a namespace."""

    namespace_id: str
    namespace_type: str  # "general", "project", "evaluation", "test"
    description: str = ""
    document_count: int = 0


class NamespaceManager:
    """Unified namespace management across all storage backends.

    This manager provides:
    1. Namespace creation and deletion
    2. Namespace-scoped document ingestion
    3. Namespace-scoped search operations
    4. Cross-namespace queries (e.g., "general" + "user_project")

    Storage Strategy:
    - Qdrant: Single collection with namespace_id payload field + index
    - Neo4j: namespace_id property on all nodes + query validation
    - BM25: Namespace filtering on corpus metadata
    - Redis: Key prefix pattern {namespace}:{key}

    Example:
        manager = NamespaceManager()

        # Create namespace
        await manager.create_namespace("user_alice_project1", "project")

        # Search within namespaces
        results = await manager.search(
            query="authentication flow",
            allowed_namespaces=["general", "user_alice_project1"],
            top_k=10
        )
    """

    def __init__(
        self,
        qdrant_client: Any = None,
        neo4j_client: SecureNeo4jClient | None = None,
        collection_name: str = "aegis_documents",
    ) -> None:
        """Initialize NamespaceManager.

        Args:
            qdrant_client: Qdrant client instance (lazy-loaded if None)
            neo4j_client: Secure Neo4j client (lazy-loaded if None)
            collection_name: Qdrant collection name
        """
        self._qdrant_client = qdrant_client
        self._neo4j_client = neo4j_client
        self._collection_name = collection_name

        logger.info(
            "NamespaceManager initialized",
            collection_name=collection_name,
        )

    @property
    def qdrant(self) -> Any:
        """Get Qdrant client (lazy initialization)."""
        if self._qdrant_client is None:
            from src.components.vector_search.qdrant_client import get_qdrant_client

            self._qdrant_client = get_qdrant_client()
        return self._qdrant_client

    @property
    def neo4j(self) -> SecureNeo4jClient:
        """Get secure Neo4j client (lazy initialization)."""
        if self._neo4j_client is None:
            self._neo4j_client = get_secure_neo4j_client()
        return self._neo4j_client

    # =========================================================================
    # Namespace CRUD Operations
    # =========================================================================

    async def create_namespace(
        self,
        namespace_id: str,
        namespace_type: str = "project",
        description: str = "",
    ) -> NamespaceInfo:
        """Create a new namespace.

        This creates the necessary infrastructure for namespace isolation:
        - Ensures Qdrant payload index exists
        - Creates Neo4j namespace index if needed

        Args:
            namespace_id: Unique namespace identifier
            namespace_type: Type of namespace (general, project, evaluation, test)
            description: Human-readable description

        Returns:
            NamespaceInfo for the created namespace
        """
        logger.info(
            "Creating namespace",
            namespace_id=namespace_id,
            namespace_type=namespace_type,
        )

        # Ensure Qdrant payload index exists
        await self._ensure_qdrant_namespace_index()

        # Ensure Neo4j namespace index exists
        await self._ensure_neo4j_namespace_index()

        return NamespaceInfo(
            namespace_id=namespace_id,
            namespace_type=namespace_type,
            description=description,
        )

    async def delete_namespace(self, namespace_id: str) -> dict[str, int]:
        """Delete all data in a namespace.

        WARNING: This permanently deletes all documents, entities, and
        relationships in the namespace.

        Args:
            namespace_id: Namespace to delete

        Returns:
            Dictionary with deletion statistics
        """
        logger.warning(
            "Deleting namespace",
            namespace_id=namespace_id,
        )

        stats = {
            "qdrant_points_deleted": 0,
            "neo4j_nodes_deleted": 0,
            "neo4j_relationships_deleted": 0,
        }

        # Delete from Qdrant
        try:
            # Use scroll to get all point IDs, then delete
            # This is safer than delete with filter for large namespaces
            result = await self.qdrant.async_client.delete(
                collection_name=self._collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="namespace_id",
                            match=MatchAny(any=[namespace_id]),
                        )
                    ]
                ),
            )
            stats["qdrant_points_deleted"] = getattr(result, "deleted_count", 0)
        except Exception as e:
            logger.error("Failed to delete Qdrant namespace data", error=str(e))

        # Delete from Neo4j (nodes and relationships)
        try:
            result = await self.neo4j.execute_write(
                """
                MATCH (n)
                WHERE n.namespace_id = $namespace_id
                DETACH DELETE n
                RETURN count(n) AS deleted
                """,
                parameters={"namespace_id": namespace_id},
                skip_validation=True,  # Admin operation
            )
            stats["neo4j_nodes_deleted"] = result.get("nodes_deleted", 0)
            stats["neo4j_relationships_deleted"] = result.get("relationships_deleted", 0)
        except Exception as e:
            logger.error("Failed to delete Neo4j namespace data", error=str(e))

        logger.info("Namespace deleted", namespace_id=namespace_id, stats=stats)
        return stats

    async def list_namespaces(self) -> list[NamespaceInfo]:
        """List all namespaces with document counts.

        Returns:
            List of NamespaceInfo objects
        """
        namespaces = []

        # Get namespaces from Qdrant (aggregate by namespace_id)
        try:
            # Use scroll to sample documents and extract unique namespaces
            result = await self.qdrant.async_client.scroll(
                collection_name=self._collection_name,
                limit=10000,
                with_payload=["namespace_id"],
            )

            namespace_counts: dict[str, int] = {}
            for point in result[0]:
                ns_id = point.payload.get("namespace_id", DEFAULT_NAMESPACE)
                namespace_counts[ns_id] = namespace_counts.get(ns_id, 0) + 1

            for ns_id, count in namespace_counts.items():
                ns_type = self._infer_namespace_type(ns_id)
                namespaces.append(
                    NamespaceInfo(
                        namespace_id=ns_id,
                        namespace_type=ns_type,
                        document_count=count,
                    )
                )

        except Exception as e:
            logger.warning("Failed to list Qdrant namespaces", error=str(e))

        return sorted(namespaces, key=lambda x: x.namespace_id)

    # =========================================================================
    # Qdrant Namespace Operations
    # =========================================================================

    async def _ensure_qdrant_namespace_index(self) -> None:
        """Ensure Qdrant has a payload index on namespace_id."""
        try:
            await self.qdrant.async_client.create_payload_index(
                collection_name=self._collection_name,
                field_name="namespace_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info("Qdrant namespace_id index created/verified")
        except Exception as e:
            # Index might already exist
            logger.debug("Qdrant namespace index creation", result=str(e))

    def build_qdrant_filter(
        self,
        allowed_namespaces: list[str],
        additional_filter: Filter | None = None,
    ) -> Filter:
        """Build Qdrant filter for namespace-scoped queries.

        Args:
            allowed_namespaces: List of namespaces to include
            additional_filter: Optional additional filter conditions

        Returns:
            Qdrant Filter object
        """
        namespace_condition = FieldCondition(
            key="namespace_id",
            match=MatchAny(any=allowed_namespaces),
        )

        if additional_filter and additional_filter.must:
            # Combine namespace filter with existing filter
            return Filter(
                must=[namespace_condition, *additional_filter.must]
            )
        else:
            return Filter(must=[namespace_condition])

    async def search_qdrant(
        self,
        query_vector: list[float],
        allowed_namespaces: list[str],
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Search Qdrant within specified namespaces.

        Args:
            query_vector: Query embedding vector
            allowed_namespaces: Namespaces to search in
            limit: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of search results with namespace info
        """
        if not allowed_namespaces:
            logger.warning("search_qdrant called with empty namespaces")
            return []

        query_filter = self.build_qdrant_filter(allowed_namespaces)

        results = await self.qdrant.search(
            collection_name=self._collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )

        # Add namespace info to results
        for result in results:
            result["source_namespace"] = result.get("payload", {}).get(
                "namespace_id", DEFAULT_NAMESPACE
            )

        logger.debug(
            "Qdrant namespace search completed",
            namespaces=allowed_namespaces,
            results=len(results),
        )

        return results

    # =========================================================================
    # Neo4j Namespace Operations
    # =========================================================================

    async def _ensure_neo4j_namespace_index(self) -> None:
        """Ensure Neo4j has indexes on namespace_id for all relevant labels."""
        indexes = [
            "CREATE INDEX idx_entity_namespace IF NOT EXISTS FOR (n:base) ON (n.namespace_id)",
            "CREATE INDEX idx_chunk_namespace IF NOT EXISTS FOR (n:chunk) ON (n.namespace_id)",
            "CREATE INDEX idx_document_namespace IF NOT EXISTS FOR (n:Document) ON (n.namespace_id)",
        ]

        for query in indexes:
            try:
                await self.neo4j.execute_write(query, skip_validation=True)
            except Exception as e:
                logger.debug("Neo4j index creation", query=query[:50], result=str(e))

        logger.info("Neo4j namespace indexes created/verified")

    def build_neo4j_namespace_clause(
        self,
        allowed_namespaces: list[str],
        node_alias: str = "n",
    ) -> tuple[str, dict[str, Any]]:
        """Build Neo4j WHERE clause for namespace filtering.

        Args:
            allowed_namespaces: List of namespaces to include
            node_alias: Node alias in query (default: "n")

        Returns:
            Tuple of (WHERE clause string, parameters dict)
        """
        clause = f"{node_alias}.namespace_id IN $allowed_namespaces"
        params = {"allowed_namespaces": allowed_namespaces}
        return clause, params

    async def search_neo4j_local(
        self,
        query_terms: list[str],
        allowed_namespaces: list[str],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute Graph Local search within namespaces.

        Searches for entities matching query terms and returns
        related chunks via MENTIONED_IN relationships.

        Args:
            query_terms: Query terms to match against entities
            allowed_namespaces: Namespaces to search in
            top_k: Maximum results

        Returns:
            List of chunk results with entity info
        """
        if not allowed_namespaces:
            return []

        cypher = """
        WITH $query_terms AS terms
        MATCH (e:base)
        WHERE e.namespace_id IN $allowed_namespaces
          AND (any(term IN terms WHERE toLower(e.entity_name) CONTAINS term)
               OR any(term IN terms WHERE toLower(e.description) CONTAINS term))
        WITH e
        MATCH (e)-[:MENTIONED_IN]->(c:chunk)
        WHERE c.namespace_id IN $allowed_namespaces
        WITH c, count(DISTINCT e) AS entity_matches, collect(DISTINCT e.entity_name) AS matched_entities
        RETURN c.chunk_id AS id,
               c.text AS text,
               c.document_id AS document_id,
               c.document_path AS source,
               c.namespace_id AS namespace_id,
               entity_matches AS relevance,
               matched_entities AS entities
        ORDER BY entity_matches DESC
        LIMIT $top_k
        """

        results = await self.neo4j.execute_read(
            cypher,
            parameters={
                "query_terms": query_terms,
                "allowed_namespaces": allowed_namespaces,
                "top_k": top_k,
            },
        )

        formatted = []
        for rank, record in enumerate(results, start=1):
            formatted.append({
                "id": record["id"],
                "text": record["text"] or "",
                "document_id": record.get("document_id", ""),
                "source": record.get("source", ""),
                "source_namespace": record.get("namespace_id", DEFAULT_NAMESPACE),
                "score": record.get("relevance", 1),
                "rank": rank,
                "search_type": "graph_local",
                "source_channel": "graph_local",
                "matched_entities": record.get("entities", []),
            })

        return formatted

    async def search_neo4j_global(
        self,
        query_terms: list[str],
        allowed_namespaces: list[str],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute Graph Global search within namespaces.

        Searches for communities matching query terms and returns
        related chunks via community expansion.

        Args:
            query_terms: Query terms to match against entities
            allowed_namespaces: Namespaces to search in
            top_k: Maximum results

        Returns:
            List of chunk results with community info
        """
        if not allowed_namespaces:
            return []

        cypher = """
        WITH $query_terms AS terms
        MATCH (e:base)
        WHERE e.namespace_id IN $allowed_namespaces
          AND e.community_id IS NOT NULL
          AND (any(term IN terms WHERE toLower(e.entity_name) CONTAINS term)
               OR any(term IN terms WHERE toLower(e.description) CONTAINS term))
        WITH e.community_id AS community, count(e) AS match_score
        ORDER BY match_score DESC
        LIMIT 3

        MATCH (e2:base {community_id: community})
        WHERE e2.namespace_id IN $allowed_namespaces
        MATCH (e2)-[:MENTIONED_IN]->(c:chunk)
        WHERE c.namespace_id IN $allowed_namespaces
        WITH c, community, count(DISTINCT e2) AS community_entities
        RETURN c.chunk_id AS id,
               c.text AS text,
               c.document_id AS document_id,
               c.document_path AS source,
               c.namespace_id AS namespace_id,
               community AS community_id,
               community_entities AS relevance
        ORDER BY community_entities DESC
        LIMIT $top_k
        """

        results = await self.neo4j.execute_read(
            cypher,
            parameters={
                "query_terms": query_terms,
                "allowed_namespaces": allowed_namespaces,
                "top_k": top_k,
            },
        )

        formatted = []
        for rank, record in enumerate(results, start=1):
            formatted.append({
                "id": record["id"],
                "text": record["text"] or "",
                "document_id": record.get("document_id", ""),
                "source": record.get("source", ""),
                "source_namespace": record.get("namespace_id", DEFAULT_NAMESPACE),
                "score": record.get("relevance", 1),
                "rank": rank,
                "search_type": "graph_global",
                "source_channel": "graph_global",
                "community_id": record.get("community_id"),
            })

        return formatted

    # =========================================================================
    # BM25 Namespace Operations
    # =========================================================================

    def filter_bm25_results(
        self,
        results: list[dict[str, Any]],
        allowed_namespaces: list[str],
    ) -> list[dict[str, Any]]:
        """Filter BM25 results by namespace.

        Args:
            results: BM25 search results
            allowed_namespaces: Namespaces to include

        Returns:
            Filtered results
        """
        filtered = []
        for result in results:
            namespace = result.get("metadata", {}).get("namespace_id", DEFAULT_NAMESPACE)
            if namespace in allowed_namespaces:
                result["source_namespace"] = namespace
                filtered.append(result)

        return filtered

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _infer_namespace_type(self, namespace_id: str) -> str:
        """Infer namespace type from ID prefix.

        Args:
            namespace_id: Namespace identifier

        Returns:
            Namespace type string
        """
        if namespace_id == "general" or namespace_id == DEFAULT_NAMESPACE:
            return "general"

        for prefix, _ in NAMESPACE_PREFIXES.items():
            if namespace_id.startswith(prefix):
                return prefix.rstrip("_")

        return "custom"


# Global singleton
_namespace_manager: NamespaceManager | None = None


def get_namespace_manager() -> NamespaceManager:
    """Get global NamespaceManager instance (singleton).

    Returns:
        NamespaceManager instance
    """
    global _namespace_manager
    if _namespace_manager is None:
        _namespace_manager = NamespaceManager()
    return _namespace_manager
