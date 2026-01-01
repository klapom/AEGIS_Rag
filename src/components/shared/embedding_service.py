"""Unified embedding service for all AEGIS RAG components.

Sprint 61 Feature 61.1: Added native sentence-transformers backend (5x faster).

Shared by:
- DocumentIngestionPipeline (Qdrant chunks)
- LightRAG (Entity embeddings)
- Graphiti (Memory embeddings)

Backends:
- Ollama: HTTP API (backward compatible, ~50-100 emb/s)
- sentence-transformers: Native BGE-M3 (default Sprint 61, ~250-500 emb/s on CPU)
"""

import hashlib
import time
from collections import OrderedDict
from typing import Any

import structlog
from ollama import AsyncClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.core.exceptions import LLMError

logger = structlog.get_logger(__name__)


class LRUCache:
    """Least Recently Used (LRU) cache with size limit."""

    def __init__(self, max_size: int = 10000):
        self.cache: OrderedDict[str, list[float]] = OrderedDict()
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> list[float] | None:
        """Get item from cache."""
        if key in self.cache:
            self._hits += 1
            self.cache.move_to_end(key)
            return self.cache[key]
        self._misses += 1
        return None

    def set(self, key: str, value: list[float]) -> None:
        """Add item to cache."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value

        if len(self.cache) > self.max_size:
            evicted_key, _ = self.cache.popitem(last=False)
            logger.debug("cache_eviction", evicted_key=evicted_key[:16])

    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate(),
        }


class UnifiedEmbeddingService:
    """Shared embedding service for all AEGIS RAG components.

    Features:
    - Shared LRU cache (improves hit rate across components)
    - Unified retry logic and error handling
    - Centralized metrics and monitoring
    - **Pickle-compatible** for LightRAG deepcopy operations

    IMPORTANT - Pickle Compatibility Design Decision:
    =====================================================
    This class is designed to be PICKLE-COMPATIBLE to support LightRAG's
    internal deepcopy() operations during initialization.

    WHY NO self.ollama_client IN __init__?
    ---------------------------------------
    The "traditional" approach would be to create a single AsyncClient in __init__:

        def __init__(self, ...):
            self.ollama_client = AsyncClient(host=settings.ollama_base_url)  # ❌ NOT PICKLE-COMPATIBLE

    PROBLEM: AsyncClient contains non-picklable _thread.RLock objects
    - LightRAG uses asdict(self) → deepcopy() during initialization (lightrag.py:465)
    - deepcopy() attempts to pickle ALL object attributes including AsyncClient
    - Pickle fails with: "TypeError: cannot pickle '_thread.RLock' object"

    AFFECTED TESTS:
    - tests/integration/test_sprint5_critical_e2e.py::test_graph_construction_full_pipeline_e2e
    - tests/integration/test_sprint5_critical_e2e.py::test_entity_extraction_ollama_neo4j_e2e
    - tests/integration/test_sprint5_critical_e2e.py::test_dual_level_query_e2e
    - tests/integration/test_sprint5_critical_e2e.py::test_hybrid_query_integration_e2e
    - tests/integration/test_sprint5_critical_e2e.py::test_relationship_extraction_validation_e2e

    SOLUTION: Lazy AsyncClient Creation
    ------------------------------------
    Instead of storing AsyncClient as instance variable, we create a fresh
    client for each embed operation:

        async def embed_single(self, text: str):
            client = AsyncClient(host=settings.ollama_base_url)  # ✅ PICKLE-COMPATIBLE
            response = await client.embeddings(...)

    TRADEOFFS:
    - ✅ BENEFIT: Object is pickle-compatible (no RLock in state)
    - ✅ BENEFIT: Shared LRU cache still reduces API calls by 30-50%
    - ✅ BENEFIT: Singleton pattern still provides cross-component cache sharing
    - ❌ COST: Slight overhead from creating new AsyncClient per call
              (but Ollama AsyncClient is lightweight, minimal performance impact)

    ALTERNATIVE CONSIDERED AND REJECTED:
    - Skip LightRAG E2E tests → Loses test coverage for critical feature
    - Use separate embedding function for tests → Code duplication, maintenance burden
    - Monkey-patch deepcopy in tests → Fragile, breaks on library updates

    See Also:
    - Sprint 12 Feature 12.1: LightRAG E2E Test Infrastructure
    - Sprint 11 Commit 8d36754: GPU support and test isolation
    - SPRINT_12_BATCH_1_NOTES.md: Pickle error root cause analysis
    """

    def __init__(
        self,
        model_name: str | None = None,
        embedding_dim: int = 1024,
        cache_max_size: int = 10000,
        backend: str | None = None,
    ) -> None:
        """Initialize unified embedding service.

        Sprint 61 Feature 61.1: Added backend parameter for Ollama vs Native selection.

        Args:
            model_name: Embedding model (default: bge-m3)
            embedding_dim: Embedding dimension (bge-m3: 1024, Sprint 16 migration)
            cache_max_size: Maximum cache size (default: 10000)
            backend: Backend to use ('ollama' or 'sentence-transformers', default from settings)

        Note:
            No AsyncClient or SentenceTransformer stored as instance variables
            to maintain pickle compatibility for LightRAG deepcopy operations.
            See class docstring for detailed explanation.

            Sprint 16 Feature 16.2: Migrated from nomic-embed-text (768-dim) to
            bge-m3 (1024-dim) for unified embedding space across all components.

            Sprint 61 Feature 61.1: Native sentence-transformers backend is 5x faster
            than Ollama for single embeddings, 16x faster for batches.
        """
        self.backend = backend or settings.embedding_backend
        self.model_name = model_name or settings.st_model_name
        self.embedding_dim = embedding_dim
        # NO self.ollama_client or self.st_model here! See class docstring for why.
        self.cache = LRUCache(max_size=cache_max_size)

        # Store config for lazy initialization
        self._st_device = settings.st_device
        self._st_batch_size = settings.st_batch_size

        logger.info(
            "unified_embedding_service_initialized",
            backend=self.backend,
            model=self.model_name,
            embedding_dim=self.embedding_dim,
            cache_size=cache_max_size,
            device=self._st_device if self.backend == "sentence-transformers" else "n/a",
        )

    def _cache_key(self, text: str, document_id: str | None = None) -> str:
        """Generate cache key for text with optional document context.

        Sprint 68 Feature 68.3: Added document_id to enable cache invalidation
        when documents are updated/reprocessed.

        Args:
            text: Text content to embed
            document_id: Optional document ID for cache invalidation

        Returns:
            SHA256 hash of text + document_id (if provided)
        """
        # Use ternary operator for cache content
        cache_content = f"{text}::{document_id}" if document_id else text
        return hashlib.sha256(cache_content.encode()).hexdigest()

    def _embed_native(self, text: str) -> list[float]:
        """Embed text using native sentence-transformers.

        Sprint 61 Feature 61.1: Native BGE-M3 embeddings (5x faster than Ollama).

        Creates SentenceTransformer lazily to maintain pickle compatibility.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1024-dim)
        """
        from src.domains.vector_search.embedding import get_native_embedding_service

        # Sprint 65 Feature 65.1: Use singleton to prevent model reloading (95s → <1s)
        native_service = get_native_embedding_service(
            model_name=self.model_name,
            device=self._st_device,
            batch_size=self._st_batch_size,
        )

        return native_service.embed_text(text)

    def _embed_native_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed batch of texts using native sentence-transformers.

        Sprint 61 Feature 61.1: 16x faster than Ollama for batch embedding.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        from src.domains.vector_search.embedding import get_native_embedding_service

        # Sprint 65 Feature 65.1: Use singleton to prevent model reloading (95s → <1s)
        native_service = get_native_embedding_service(
            model_name=self.model_name,
            device=self._st_device,
            batch_size=self._st_batch_size,
        )

        return native_service.embed_batch(texts)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def embed_single(self, text: str) -> list[float]:
        """Embed single text with caching.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1024 dimensions for bge-m3, Sprint 16 migration)

        Note:
            Creates fresh AsyncClient for each call to maintain pickle compatibility.
            See class docstring for detailed explanation of design decision.
        """
        embed_start = time.perf_counter()

        # Check cache
        cache_key = self._cache_key(text)
        cached = self.cache.get(cache_key)
        if cached:
            cache_duration_ms = (time.perf_counter() - embed_start) * 1000
            logger.debug(
                "TIMING_embedding_cache_hit",
                duration_ms=round(cache_duration_ms, 3),
                text_length=len(text),
                backend=self.backend,
            )
            return cached

        # Sprint 61 Feature 61.1: Backend selection (Ollama vs Native)
        if self.backend == "sentence-transformers":
            # Native sentence-transformers path (5x faster, synchronous)
            try:
                backend_start = time.perf_counter()
                embedding = self._embed_native(text)
                backend_duration_ms = (time.perf_counter() - backend_start) * 1000

                logger.debug(
                    "TIMING_embedding_native",
                    duration_ms=round(backend_duration_ms, 2),
                    text_length=len(text),
                    embedding_dim=len(embedding),
                )

                # Cache and return
                self.cache.set(cache_key, embedding)
                return embedding

            except Exception as e:
                logger.error("native_embedding_failed", text_preview=text[:50], error=str(e))
                raise LLMError("embed_single_native", f"Native embedding failed: {e}") from e

        # Ollama backend path (backward compatible, asynchronous)
        # Generate embedding with fresh AsyncClient (pickle-compatible approach)
        try:
            # Sprint 51: Sanitize text to prevent NaN errors from Ollama
            # Remove control characters and normalize unicode
            import unicodedata

            sanitized_text = unicodedata.normalize("NFKC", text)
            # Remove control characters except newlines/tabs
            sanitized_text = "".join(
                c if c in "\n\t" or not unicodedata.category(c).startswith("C") else " "
                for c in sanitized_text
            )
            # Truncate to 32k chars (~8k tokens for BGE-M3 context window)
            max_chars = 32000
            if len(sanitized_text) > max_chars:
                logger.warning(
                    "embedding_text_truncated",
                    original_length=len(text),
                    truncated_to=max_chars,
                )
                sanitized_text = sanitized_text[:max_chars]

            # Create fresh client for this operation (no stored state = pickle-compatible)
            client = AsyncClient(host=settings.ollama_base_url)

            ollama_start = time.perf_counter()
            try:
                response = await client.embeddings(
                    model=self.model_name,
                    prompt=sanitized_text,
                )
            except Exception as ollama_error:
                # Sprint 51: Handle Ollama NaN errors by returning zero embedding
                error_str = str(ollama_error)
                if "NaN" in error_str or "unsupported value" in error_str:
                    logger.warning(
                        "ollama_nan_error_fallback",
                        text_preview=text[:100],
                        text_length=len(text),
                        error=error_str,
                        action="returning_zero_embedding",
                    )
                    # Return zero embedding (1024 dims for BGE-M3)
                    return [0.0] * 1024
                raise  # Re-raise non-NaN errors
            ollama_duration_ms = (time.perf_counter() - ollama_start) * 1000

            embedding = response.get("embedding", [])

            if not embedding:
                raise LLMError("embed_single", f"Empty embedding returned for text: {text[:100]}")

            # Sprint 51: Check for NaN values in embedding and replace with zeros
            import math

            has_nan = any(math.isnan(v) for v in embedding)
            if has_nan:
                logger.warning(
                    "embedding_contains_nan",
                    text_preview=text[:100],
                    text_length=len(text),
                    action="replacing_with_zeros",
                )
                # Replace NaN values with 0.0 to prevent JSON serialization errors
                embedding = [0.0 if math.isnan(v) else v for v in embedding]

            # Cache result
            self.cache.set(cache_key, embedding)

            total_duration_ms = (time.perf_counter() - embed_start) * 1000
            logger.debug(
                "TIMING_embedding_single",
                duration_ms=round(total_duration_ms, 2),
                ollama_duration_ms=round(ollama_duration_ms, 2),
                text_length=len(text),
                embedding_dim=len(embedding),
            )

            return embedding

        except Exception as e:
            logger.error("embedding_generation_failed", text_preview=text[:50], error=str(e))
            raise LLMError("embed_single", f"Failed to generate embedding: {e}") from e

    async def embed_batch(self, texts: list[str], max_concurrent: int = 10) -> list[list[float]]:
        """Embed batch of texts with caching and parallel processing.

        Sprint 41 Optimization: Parallel embedding generation to improve GPU utilization.
        Sprint 61 Feature 61.1: Added native sentence-transformers backend (16x faster for batches).

        Args:
            texts: list of texts to embed
            max_concurrent: Maximum concurrent embedding requests (Ollama only, default: 10)
                           Native backend uses internal batching instead.

        Returns:
            list of embedding vectors (order preserved)
        """
        import asyncio

        batch_start = time.perf_counter()

        # Sprint 61 Feature 61.1: Native backend for batch embedding (16x faster)
        if self.backend == "sentence-transformers":
            try:
                # Check cache for each text
                cache_hits = 0
                embeddings_to_compute = []
                indices_to_compute = []
                result = [None] * len(texts)

                for idx, text in enumerate(texts):
                    cache_key = self._cache_key(text)
                    cached = self.cache.get(cache_key)
                    if cached:
                        result[idx] = cached
                        cache_hits += 1
                    else:
                        embeddings_to_compute.append(text)
                        indices_to_compute.append(idx)

                # Compute missing embeddings in batch
                if embeddings_to_compute:
                    native_embeddings = self._embed_native_batch(embeddings_to_compute)

                    # Store in cache and result
                    for text, embedding, idx in zip(
                        embeddings_to_compute, native_embeddings, indices_to_compute, strict=True
                    ):
                        cache_key = self._cache_key(text)
                        self.cache.set(cache_key, embedding)
                        result[idx] = embedding

                batch_duration_ms = (time.perf_counter() - batch_start) * 1000
                total_chars = sum(len(t) for t in texts)
                embeddings_per_sec = (
                    len(texts) / (batch_duration_ms / 1000) if batch_duration_ms > 0 else 0
                )

                logger.info(
                    "TIMING_embedding_batch_native",
                    duration_ms=round(batch_duration_ms, 2),
                    batch_size=len(texts),
                    total_chars=total_chars,
                    cache_hits=cache_hits,
                    cache_misses=len(embeddings_to_compute),
                    throughput_embeddings_per_sec=round(embeddings_per_sec, 2),
                )

                return result

            except Exception as e:
                logger.error("native_batch_embedding_failed", batch_size=len(texts), error=str(e))
                raise LLMError("embed_batch_native", f"Native batch embedding failed: {e}") from e

        # Ollama backend path (original implementation)
        total_chars = sum(len(t) for t in texts)
        hits_before = self.cache._hits

        # Use semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def embed_with_semaphore(text: str, idx: int) -> tuple[int, list[float]]:
            """Embed single text with semaphore control, preserving order."""
            async with semaphore:
                embedding = await self.embed_single(text)
                return (idx, embedding)

        # Launch all embeddings in parallel (semaphore limits concurrency)
        tasks = [embed_with_semaphore(text, idx) for idx, text in enumerate(texts)]
        results = await asyncio.gather(*tasks)

        # Sort by index to preserve order
        results.sort(key=lambda x: x[0])
        embeddings = [emb for _, emb in results]

        # Calculate cache hits (difference in cache hits counter)
        cache_hits = self.cache._hits - hits_before
        cache_misses = len(texts) - cache_hits

        batch_end = time.perf_counter()
        batch_duration_ms = (batch_end - batch_start) * 1000
        embeddings_per_sec = len(texts) / (batch_duration_ms / 1000) if batch_duration_ms > 0 else 0
        chars_per_sec = total_chars / (batch_duration_ms / 1000) if batch_duration_ms > 0 else 0

        logger.info(
            "TIMING_embedding_batch_complete",
            stage="embedding",
            duration_ms=round(batch_duration_ms, 2),
            batch_size=len(texts),
            total_chars=total_chars,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            cache_hit_rate=round(self.cache.hit_rate(), 3),
            throughput_embeddings_per_sec=round(embeddings_per_sec, 2),
            throughput_chars_per_sec=round(chars_per_sec, 0),
            avg_ms_per_embedding=round(batch_duration_ms / len(texts), 2) if texts else 0,
            max_concurrent=max_concurrent,
        )

        return embeddings

    def get_stats(self) -> dict[str, Any]:
        """Get embedding service statistics."""
        return {
            "model": self.model_name,
            "embedding_dim": self.embedding_dim,
            "cache": self.cache.stats(),
        }


# Global instance (singleton)
_embedding_service: UnifiedEmbeddingService | None = None


def get_embedding_service() -> UnifiedEmbeddingService:
    """Get global UnifiedEmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = UnifiedEmbeddingService()
    return _embedding_service
