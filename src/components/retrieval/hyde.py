"""Hypothetical Document Embeddings (HyDE) Query Expansion.

Sprint 128 Feature 128.4: HyDE Query Expansion

HyDE improves retrieval quality by embedding a hypothetical answer document
instead of the raw query. This produces embeddings closer to actual relevant
documents in vector space, especially for abstract or complex queries.

Architecture:
    Query → LLM generates hypothetical answer → BGE-M3 embeds hypothetical → Qdrant search
         ↘ Original query embedding → Qdrant search (parallel)
         → RRF fusion of both result sets

Academic Reference:
    - HyDE: Precise Zero-Shot Dense Retrieval (Gao et al., 2022)
    - arXiv:2212.10496

Performance Target:
    - <100ms hypothetical document generation (with cache)
    - <200ms total HyDE search (parallel with dense search)
    - >90% cache hit rate for repeated queries

Example:
    >>> hyde = HyDEGenerator()
    >>> results = await hyde.hyde_search(
    ...     query="What are the benefits of HyDE?",
    ...     top_k=10,
    ...     namespaces=["research_papers"]
    ... )
    >>> print(f"Found {len(results)} results via HyDE")
"""

import hashlib
import time
from typing import Any

import structlog

from src.components.shared.embedding_service import get_embedding_service
from src.core.config import settings
from src.core.exceptions import LLMError
from src.domains.llm_integration.models import LLMTask, QualityRequirement, TaskType
from src.domains.llm_integration.proxy.aegis_llm_proxy import get_aegis_llm_proxy

logger = structlog.get_logger(__name__)


class HyDEGenerator:
    """Hypothetical Document Embeddings (HyDE) Generator.

    This class generates hypothetical answer documents from queries,
    embeds them, and searches Qdrant for semantically similar chunks.

    Features:
        - LLM-generated hypothetical documents (100-200 words)
        - BGE-M3 embedding of hypothetical documents
        - Redis caching for repeated queries (24h TTL)
        - Parallel execution with dense search
        - Configurable via HYDE_ENABLED setting

    Example:
        >>> hyde = HyDEGenerator()
        >>> results = await hyde.hyde_search("What is Amsterdam?", top_k=10)
        >>> print(f"HyDE found {len(results)} results")
    """

    def __init__(self) -> None:
        """Initialize HyDE generator with LLM proxy and embedding service.

        Note:
            Uses singleton instances of AegisLLMProxy and EmbeddingService
            to avoid re-initialization on every call.
        """
        self.llm_proxy = get_aegis_llm_proxy()
        self.embedding_service = get_embedding_service()

        # Initialize Redis client for caching (lazy import to avoid circular dependency)
        self._redis_client = None  # Will be initialized on first use

        logger.info(
            "hyde_generator_initialized",
            enabled=settings.hyde_enabled,
            weight=settings.hyde_weight,
            max_tokens=settings.hyde_max_tokens,
        )

    async def _get_redis_client(self):
        """Get Redis client (lazy initialization).

        Returns:
            aioredis client for caching

        Note:
            Uses lazy initialization to avoid circular import issues
            and to initialize only when needed.
        """
        if self._redis_client is None:
            import redis.asyncio as aioredis

            redis_url = f"redis://{settings.redis_host}:{settings.redis_port}/0"
            self._redis_client = aioredis.from_url(redis_url, decode_responses=True)

        return self._redis_client

    def _cache_key(self, query: str) -> str:
        """Generate cache key for query.

        Args:
            query: User query string

        Returns:
            SHA256 hash of query for Redis key

        Example:
            >>> hyde._cache_key("What is Amsterdam?")
            'hyde:abc123def456...'
        """
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        return f"hyde:{query_hash}"

    async def generate_hypothetical_document(self, query: str) -> str:
        """Generate hypothetical answer document using LLM.

        This method uses AegisLLMProxy to generate a short hypothetical
        answer (100-200 words) that would answer the query. The hypothetical
        document is cached in Redis for 24 hours.

        Args:
            query: User query string

        Returns:
            Hypothetical answer document (100-200 words)

        Raises:
            LLMError: If LLM generation fails

        Example:
            >>> hyde = HyDEGenerator()
            >>> doc = await hyde.generate_hypothetical_document("What is Amsterdam?")
            >>> print(doc)
            'Amsterdam is the capital and most populous city of the Netherlands...'
        """
        start_time = time.perf_counter()

        # Check cache first
        cache_key = self._cache_key(query)
        try:
            redis_client = await self._get_redis_client()
            cached_doc = await redis_client.get(cache_key)
            if cached_doc:
                latency_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    "hyde_cache_hit",
                    query=query[:100],
                    latency_ms=round(latency_ms, 2),
                )
                return cached_doc
        except Exception as e:
            logger.warning("hyde_cache_lookup_failed", error=str(e), query=query[:50])
            # Continue without cache

        # Generate hypothetical document with LLM
        prompt = f"""Write a short passage (100-200 words) that would answer the following question:

{query}

Write as if you are providing a direct, informative answer. Be concise and factual."""

        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            quality_requirement=QualityRequirement.MEDIUM,
            max_tokens=settings.hyde_max_tokens,
            temperature=0.3,  # Low temperature for consistent, factual output
            metadata={"prompt_name": "HYDE_GENERATION"},
        )

        try:
            response = await self.llm_proxy.generate(task, use_cache=False)
            hypothetical_doc = response.content.strip()

            # Cache for 24 hours (86400 seconds)
            try:
                redis_client = await self._get_redis_client()
                await redis_client.setex(cache_key, 86400, hypothetical_doc)
            except Exception as e:
                logger.warning("hyde_cache_store_failed", error=str(e), query=query[:50])
                # Continue without caching

            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "hyde_generation_complete",
                query=query[:100],
                doc_length=len(hypothetical_doc),
                tokens_used=response.tokens_used,
                provider=response.provider,
                latency_ms=round(latency_ms, 2),
            )

            return hypothetical_doc

        except Exception as e:
            logger.error(
                "hyde_generation_failed",
                query=query[:100],
                error=str(e),
            )
            raise LLMError("generate_hypothetical_document", f"HyDE generation failed: {e}") from e

    async def hyde_search(
        self,
        query: str,
        top_k: int = 10,
        namespaces: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search using Hypothetical Document Embeddings (HyDE).

        This method generates a hypothetical answer document, embeds it,
        and searches Qdrant for semantically similar chunks.

        Args:
            query: User query string
            top_k: Number of results to return
            namespaces: List of namespaces to filter by (optional)

        Returns:
            List of search results with metadata

        Raises:
            LLMError: If hypothetical document generation fails
            Exception: If embedding or search fails

        Example:
            >>> hyde = HyDEGenerator()
            >>> results = await hyde.hyde_search("What is Amsterdam?", top_k=10)
            >>> print(f"Found {len(results)} results")
        """
        start_time = time.perf_counter()

        # Step 1: Generate hypothetical document
        hypothetical_doc = await self.generate_hypothetical_document(query)

        # Step 2: Embed hypothetical document with BGE-M3
        try:
            embedding = await self.embedding_service.embed_single(hypothetical_doc)
        except Exception as e:
            logger.error(
                "hyde_embedding_failed",
                query=query[:100],
                error=str(e),
            )
            raise

        # Step 3: Search Qdrant with hypothetical embedding
        try:
            from qdrant_client import QdrantClient

            qdrant_client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
            )

            # Build filter for namespaces if provided
            search_filter = None
            if namespaces:
                from qdrant_client.models import FieldCondition, Filter, MatchAny

                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key="namespace_id",
                            match=MatchAny(any=namespaces),
                        )
                    ]
                )

            # Search Qdrant (use dense vector only - HyDE is semantic by design)
            search_results = qdrant_client.search(
                collection_name=settings.qdrant_collection,
                query_vector=("dense", embedding),  # Named vector
                limit=top_k,
                query_filter=search_filter,
                with_payload=True,
            )

            # Convert Qdrant results to standard format
            results = []
            for hit in search_results:
                result = {
                    "id": str(hit.id),
                    "score": hit.score,
                    "content": hit.payload.get("content", ""),
                    "metadata": hit.payload,
                    "source": "hyde",
                }
                results.append(result)

            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "hyde_search_complete",
                query=query[:100],
                results_count=len(results),
                latency_ms=round(latency_ms, 2),
                hypothetical_length=len(hypothetical_doc),
            )

            return results

        except Exception as e:
            logger.error(
                "hyde_search_failed",
                query=query[:100],
                error=str(e),
            )
            raise


# Singleton instance
_hyde_generator: HyDEGenerator | None = None


def get_hyde_generator() -> HyDEGenerator:
    """Get singleton instance of HyDEGenerator.

    Returns:
        HyDEGenerator instance

    Example:
        >>> from src.components.retrieval.hyde import get_hyde_generator
        >>> hyde = get_hyde_generator()
        >>> results = await hyde.hyde_search("What is Amsterdam?", top_k=10)
    """
    global _hyde_generator

    if _hyde_generator is None:
        _hyde_generator = HyDEGenerator()

    return _hyde_generator
