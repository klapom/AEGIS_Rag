"""LightRAG wrapper for graph-based knowledge retrieval.

This module wraps the LightRAG library to provide:
- Ollama LLM integration
- Neo4j backend storage
- Async support
- Error handling and retry logic

Sprint 5: Feature 5.1 - LightRAG Core Integration
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

from src.core.config import settings
from src.core.models import GraphQueryResult

logger = structlog.get_logger(__name__)


class LightRAGWrapper:
    """Async wrapper for LightRAG with Ollama and Neo4j backend.

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
    ):
        """Initialize LightRAG wrapper.

        Args:
            working_dir: Working directory for LightRAG
            llm_model: Ollama LLM model name
            embedding_model: Ollama embedding model name
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        # Configuration
        self.working_dir = Path(working_dir or settings.lightrag_working_dir)
        self.llm_model = llm_model or settings.lightrag_llm_model
        self.embedding_model = embedding_model or settings.lightrag_embedding_model
        self.neo4j_uri = neo4j_uri or settings.neo4j_uri
        self.neo4j_user = neo4j_user or settings.neo4j_user
        self.neo4j_password = neo4j_password or settings.neo4j_password.get_secret_value()

        # Create working directory
        self.working_dir.mkdir(parents=True, exist_ok=True)

        # Initialize LightRAG with Ollama LLM functions
        self.rag: Any = None  # Will be initialized lazily
        self._initialized = False

        logger.info(
            "lightrag_wrapper_initialized",
            working_dir=str(self.working_dir),
            llm_model=self.llm_model,
            embedding_model=self.embedding_model,
            neo4j_uri=self.neo4j_uri,
        )

    async def _ensure_initialized(self) -> None:
        """Ensure LightRAG is initialized (lazy initialization)."""
        if self._initialized:
            return

        try:
            # Import LightRAG components (optional dependency)
            from lightrag import LightRAG
            from lightrag.storage import Neo4JStorage

            # Configure Ollama LLM function
            async def ollama_llm_complete(
                prompt: str,
                model: str = self.llm_model,
                **kwargs: Any,
            ) -> str:
                """Ollama LLM completion function for LightRAG."""
                from ollama import AsyncClient

                client = AsyncClient(host=settings.ollama_base_url)

                response = await client.generate(
                    model=model,
                    prompt=prompt,
                    options={
                        "temperature": settings.lightrag_llm_temperature,
                        "num_predict": settings.lightrag_llm_max_tokens,
                    },
                )

                result: str = response.get("response", "")
                return result

            # Configure Ollama embedding function
            async def ollama_embedding_func(
                texts: list[str],
                model: str = self.embedding_model,
                **kwargs: Any,
            ) -> list[list[float]]:
                """Ollama embedding function for LightRAG."""
                from ollama import AsyncClient

                client = AsyncClient(host=settings.ollama_base_url)

                embeddings: list[list[float]] = []
                for text in texts:
                    response = await client.embeddings(
                        model=model,
                        prompt=text,
                    )
                    embedding = response.get("embedding", [])
                    embeddings.append(list(embedding))

                return embeddings

            # Initialize Neo4j storage
            neo4j_storage = Neo4JStorage(
                uri=self.neo4j_uri,
                user=self.neo4j_user,
                password=self.neo4j_password,
            )

            # Initialize LightRAG
            self.rag = LightRAG(
                working_dir=str(self.working_dir),
                llm_model_func=ollama_llm_complete,
                embedding_func=ollama_embedding_func,
                graph_storage=neo4j_storage,
            )

            self._initialized = True
            logger.info("lightrag_initialized_successfully")

        except ImportError as e:
            logger.error(
                "lightrag_import_failed",
                error=str(e),
                hint="Run: poetry add lightrag-hku networkx graspologic",
            )
            raise
        except Exception as e:
            logger.error("lightrag_initialization_failed", error=str(e))
            raise

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

        logger.info("lightrag_insert_documents", count=len(documents))

        results = []
        for i, doc in enumerate(documents):
            try:
                text = doc.get("text", "")
                if not text:
                    logger.warning("empty_document", index=i)
                    results.append({"index": i, "status": "skipped", "reason": "empty_text"})
                    continue

                # Insert text into LightRAG
                # LightRAG automatically:
                # 1. Extracts entities and relationships using LLM
                # 2. Builds knowledge graph in Neo4j
                # 3. Creates embeddings for entities
                result = await self.rag.ainsert(text)

                results.append({"index": i, "status": "success", "result": result})
                logger.debug("document_inserted", index=i, result=result)

            except Exception as e:
                logger.error(
                    "lightrag_insert_document_failed",
                    index=i,
                    error=str(e),
                )
                results.append({"index": i, "status": "error", "error": str(e)})

        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(
            "lightrag_insert_documents_complete",
            total=len(documents),
            success=success_count,
            failed=len(documents) - success_count,
        )

        return {
            "total": len(documents),
            "success": success_count,
            "failed": len(documents) - success_count,
            "results": results,
        }

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

        logger.info("lightrag_query", query=query[:100], mode=mode)

        try:
            # Import QueryParam
            from lightrag import QueryParam

            # Query LightRAG
            # - local: Entity-level retrieval (specific entities and relationships)
            # - global: Topic-level retrieval (high-level summaries, communities)
            # - hybrid: Combined local + global
            answer = await self.rag.aquery(
                query=query,
                param=QueryParam(mode=mode),
            )

            # LightRAG returns a string answer
            # We need to parse/structure it for our response
            result = GraphQueryResult(
                query=query,
                answer=answer or "",
                entities=[],  # TODO: Extract from LightRAG internal state
                relationships=[],  # TODO: Extract from LightRAG internal state
                topics=[],
                context="",  # TODO: Get context used for generation
                mode=mode,
                metadata={
                    "mode": mode,
                    "answer_length": len(answer) if answer else 0,
                },
            )

            logger.info(
                "lightrag_query_complete",
                query=query[:100],
                mode=mode,
                answer_length=len(answer) if answer else 0,
            )

            return result

        except Exception as e:
            logger.error("lightrag_query_failed", query=query[:100], mode=mode, error=str(e))
            raise

    async def get_stats(self) -> dict[str, Any]:
        """Get graph statistics (entity count, relationship count).

        Returns:
            Dictionary with entity_count and relationship_count
        """
        logger.info("lightrag_get_stats")

        try:
            # Query Neo4j directly for statistics
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
            )

            async with driver.session() as session:
                # Get entity count
                entity_result = await session.run("MATCH (e:Entity) RETURN count(e) AS count")
                entity_record = await entity_result.single()
                entity_count = entity_record["count"] if entity_record else 0

                # Get relationship count
                rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) AS count")
                rel_record = await rel_result.single()
                relationship_count = rel_record["count"] if rel_record else 0

            await driver.close()

            stats = {
                "entity_count": entity_count,
                "relationship_count": relationship_count,
            }

            logger.info("lightrag_stats", **stats)
            return stats

        except Exception as e:
            logger.error("lightrag_stats_failed", error=str(e))
            return {
                "entity_count": 0,
                "relationship_count": 0,
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """Check health of LightRAG and Neo4j connection.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Test Neo4j connection
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
            )

            async with driver.session() as session:
                result = await session.run("RETURN 1 AS health")
                record = await result.single()
                healthy: bool = bool(record and record["health"] == 1)

            await driver.close()

            logger.info("lightrag_health_check", healthy=healthy)
            return healthy

        except Exception as e:
            logger.error("lightrag_health_check_failed", error=str(e))
            return False


# Global instance (singleton pattern)
_lightrag_wrapper: LightRAGWrapper | None = None


def get_lightrag_wrapper() -> LightRAGWrapper:
    """Get global LightRAG wrapper instance (singleton).

    Returns:
        LightRAGWrapper instance
    """
    global _lightrag_wrapper
    if _lightrag_wrapper is None:
        _lightrag_wrapper = LightRAGWrapper()
    return _lightrag_wrapper


async def get_lightrag_wrapper_async() -> LightRAGWrapper:
    """Get global LightRAG wrapper instance (singleton) - async version.

    Ensures LightRAG is properly initialized before returning.

    Returns:
        LightRAGWrapper instance
    """
    wrapper = get_lightrag_wrapper()
    await wrapper._ensure_initialized()
    return wrapper
