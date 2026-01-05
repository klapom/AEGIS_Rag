"""LightRAG Client - Main Facade.

Sprint 55 Feature 55.7: Unified interface for LightRAG operations.
Orchestrates initialization, ingestion, querying, and storage.

This module provides the main LightRAGClient class that wraps all LightRAG
functionality with:
- Lazy initialization
- Multi-cloud LLM integration via AegisLLMProxy
- Neo4j backend storage
- Async support
- Error handling and retry logic
"""

from pathlib import Path
from typing import Any

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.components.graph_rag.lightrag.ingestion import (
    insert_documents,
    insert_documents_optimized,
    insert_prechunked_documents,
)
from src.components.graph_rag.lightrag.initialization import (
    create_lightrag_instance,
    get_default_config,
)
from src.components.graph_rag.lightrag.neo4j_storage import (
    check_neo4j_health,
    clear_neo4j_database,
    get_neo4j_stats,
    store_relates_to_relationships,
)
from src.components.graph_rag.lightrag.types import LightRAGConfig
from src.core.models import GraphQueryResult

logger = structlog.get_logger(__name__)


class LightRAGClient:
    """Async wrapper for LightRAG with Ollama and Neo4j backend.

    Sprint 25 Feature 25.9: Renamed from LightRAGWrapper to LightRAGClient.

    Provides:
    - Document ingestion and graph construction
    - Dual-level retrieval (local/global/hybrid)
    - Entity and relationship extraction
    - Integration with existing AEGIS RAG components
    """

    def __init__(
        self,
        working_dir: str | None = None,
        llm_model: str | None = None,
        embedding_model: str | None = None,
        neo4j_uri: str | None = None,
        neo4j_user: str | None = None,
        neo4j_password: str | None = None,
    ) -> None:
        """Initialize LightRAG client.

        Args:
            working_dir: Working directory for LightRAG
            llm_model: Ollama LLM model name
            embedding_model: Ollama embedding model name
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        # Get default config
        default_config = get_default_config()

        # Build config with overrides
        self.working_dir = Path(working_dir or default_config.working_dir)
        self.llm_model = llm_model or default_config.llm_model
        self.embedding_model = embedding_model or default_config.embedding_model
        self.neo4j_uri = neo4j_uri or default_config.neo4j_uri
        self.neo4j_user = neo4j_user or default_config.neo4j_user
        self.neo4j_password = neo4j_password or default_config.neo4j_password

        # Create working directory
        self.working_dir.mkdir(parents=True, exist_ok=True)

        # Initialize LightRAG with Ollama LLM functions
        self.rag: Any = None
        self._initialized = False

        logger.info(
            "lightrag_client_initialized",
            working_dir=str(self.working_dir),
            llm_model=self.llm_model,
            embedding_model=self.embedding_model,
            neo4j_uri=self.neo4j_uri,
        )

    async def _ensure_initialized(self) -> None:
        """Ensure LightRAG is initialized (lazy initialization)."""
        if self._initialized:
            return

        config = LightRAGConfig(
            working_dir=str(self.working_dir),
            llm_model=self.llm_model,
            embedding_model=self.embedding_model,
            neo4j_uri=self.neo4j_uri,
            neo4j_user=self.neo4j_user,
            neo4j_password=self.neo4j_password,
        )

        self.rag = await create_lightrag_instance(config)
        self._initialized = True
        logger.info("lightrag_initialized_successfully")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def insert_documents(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        """Insert multiple documents into knowledge graph.

        Args:
            documents: List of documents with 'text' and optional 'metadata' fields

        Returns:
            Batch insertion result with success/failure counts
        """
        await self._ensure_initialized()
        return await insert_documents(self.rag, documents)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def insert_documents_optimized(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Insert documents using LLM Extraction Pipeline with Graph-based Provenance.

        Sprint 14 Feature 14.1 - Optimized insertion with:
        - Per-chunk extraction
        - Provenance tracking
        - Neo4j chunk nodes

        Args:
            documents: List of documents with 'text' and optional 'id' fields

        Returns:
            Batch insertion result with stats
        """
        await self._ensure_initialized()
        return await insert_documents_optimized(self.rag, documents)

    async def insert_prechunked_documents(
        self,
        chunks: list[dict[str, Any]],
        document_id: str,
        namespace_id: str = "default",
        document_path: str = "",
        domain_id: str | None = None,
    ) -> dict[str, Any]:
        """Insert pre-chunked documents with existing chunk_ids.

        Sprint 42: Unified chunk IDs between Qdrant and Neo4j.
        Sprint 51: Added namespace_id for multi-tenant isolation.
        Sprint 75 Fix: Added document_path for Neo4j source attribution.
        Sprint 76 TD-085: Added domain_id for DSPy-optimized extraction prompts.

        Args:
            chunks: List of pre-chunked documents with chunk_id, text, chunk_index
            document_id: Source document ID
            namespace_id: Namespace for multi-tenant isolation
            document_path: Source document path for attribution (default: "")
            domain_id: Optional domain for DSPy-optimized prompts

        Returns:
            Batch insertion result with entities/relations extracted
        """
        await self._ensure_initialized()
        return await insert_prechunked_documents(
            self.rag, chunks, document_id, document_path, namespace_id, domain_id
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def query_graph(
        self,
        query: str,
        mode: str = "hybrid",
    ) -> GraphQueryResult:
        """Query knowledge graph with dual-level retrieval.

        Args:
            query: User query string
            mode: Search mode (local/global/hybrid)

        Returns:
            GraphQueryResult with answer and retrieved entities/relationships
        """
        await self._ensure_initialized()

        logger.info("lightrag_query_start", query=query, mode=mode)

        try:
            from lightrag import QueryParam

            # Check if graph has entities
            try:
                stats = await self.get_stats()
                logger.info("graph_stats", **stats)

                if stats.get("entity_count", 0) == 0:
                    logger.warning("graph_empty_query_may_fail")
            except Exception as e:
                logger.warning("stats_check_failed", error=str(e))

            # Query LightRAG
            query_param = QueryParam(mode=mode)
            answer = await self.rag.aquery(query=query, param=query_param)

            logger.info(
                "lightrag_query_complete",
                answer_length=len(answer) if answer else 0,
                answer_is_empty=(not answer or answer.strip() == ""),
            )

            if not answer or answer.strip() == "":
                logger.error("empty_answer_returned", query=query, mode=mode)

            result = GraphQueryResult(
                query=query,
                answer=answer or "",
                entities=[],
                relationships=[],
                topics=[],
                context="",
                mode=mode,
                metadata={
                    "mode": mode,
                    "answer_length": len(answer) if answer else 0,
                },
            )

            logger.info(
                "query_complete",
                query=query[:100],
                mode=mode,
                has_answer=bool(result.answer),
            )

            return result

        except Exception as e:
            logger.error(
                "query_failed",
                query=query[:100],
                mode=mode,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_stats(self) -> dict[str, Any]:
        """Get graph statistics (entity count, relationship count).

        Returns:
            Dictionary with entity_count and relationship_count
        """
        return await get_neo4j_stats(self.neo4j_uri, self.neo4j_user, self.neo4j_password)

    async def health_check(self) -> bool:
        """Check health of LightRAG and Neo4j connection.

        Returns:
            True if healthy, False otherwise
        """
        return await check_neo4j_health(self.neo4j_uri, self.neo4j_user, self.neo4j_password)

    async def _store_relations_to_neo4j(
        self,
        relations: list[dict[str, Any]],
        chunk_id: str,
        namespace_id: str = "default",
    ) -> int:
        """Store RELATES_TO relationships between entities in Neo4j.

        Args:
            relations: List of relations
            chunk_id: Source chunk ID
            namespace_id: Namespace for multi-tenant isolation

        Returns:
            Number of relationships created
        """
        await self._ensure_initialized()
        return await store_relates_to_relationships(self.rag, relations, chunk_id, namespace_id)

    async def _clear_neo4j_database(self) -> None:
        """Clear all data from Neo4j database (for test cleanup)."""
        await self._ensure_initialized()
        await clear_neo4j_database(self.rag)


# Global instance (singleton pattern)
_lightrag_client: LightRAGClient | None = None


def get_lightrag_client() -> LightRAGClient:
    """Get global LightRAG client instance (singleton).

    Returns:
        LightRAGClient instance
    """
    global _lightrag_client
    if _lightrag_client is None:
        _lightrag_client = LightRAGClient()
    return _lightrag_client


async def get_lightrag_client_async() -> LightRAGClient:
    """Get global LightRAG client instance (singleton) - async version.

    Ensures LightRAG is properly initialized before returning.

    Returns:
        Initialized LightRAGClient instance
    """
    client = get_lightrag_client()
    await client._ensure_initialized()
    return client


# Backward Compatibility Aliases (Sprint 25 Feature 25.9)
LightRAGWrapper = LightRAGClient
get_lightrag_wrapper = get_lightrag_client
get_lightrag_wrapper_async = get_lightrag_client_async


__all__ = [
    "LightRAGClient",
    "LightRAGWrapper",
    "get_lightrag_client",
    "get_lightrag_client_async",
    "get_lightrag_wrapper",
    "get_lightrag_wrapper_async",
]
