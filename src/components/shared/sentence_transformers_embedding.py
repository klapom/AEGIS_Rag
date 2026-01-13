"""High-performance embedding service using sentence-transformers.

Sprint Context: Sprint 35 (2025-12-04) - Feature 35.8: Sentence-Transformers Migration
Sprint 88 (2026-01-13): Bug fix - Made embed_single/embed_batch async for LangGraph compatibility

Optimized for DGX Spark deployment with native batch processing and direct GPU access.
Provides 5-10x performance improvement over Ollama HTTP API for embeddings.

Performance Characteristics:
    - Ollama HTTP API: ~50-100 embeddings/sec (single requests, HTTP overhead)
    - SentenceTransformers: ~500-1000 embeddings/sec (batch processing, direct GPU)
    - GPU Utilization: 90%+ (vs 30-50% with Ollama)

Architecture:
    - Native batch processing (100+ texts in parallel)
    - Direct GPU access via PyTorch (no HTTP overhead)
    - LRU cache for deduplication
    - Device auto-selection (CUDA/CPU)
    - Async methods using asyncio.to_thread() for non-blocking GPU ops

Compatible API:
    This service implements the same API as UnifiedEmbeddingService:
    - async embed_single(text: str) -> list[float]
    - async embed_batch(texts: list[str]) -> list[list[float]]

    This allows drop-in replacement via factory pattern.

Example:
    >>> from src.components.shared.sentence_transformers_embedding import (
    ...     SentenceTransformersEmbeddingService
    ... )
    >>> service = SentenceTransformersEmbeddingService()
    >>> embedding = service.embed_single("Hello world")
    >>> len(embedding)
    1024
    >>> embeddings = service.embed_batch(["Hello", "World", "Test"])
    >>> len(embeddings)
    3

Notes:
    - Model is loaded lazily on first embedding request
    - Cache is shared across all method calls
    - Device selection: 'auto' uses CUDA if available, else CPU
    - Batch size defaults to 64 (optimal for most GPUs)

See Also:
    - src/components/shared/embedding_service.py: Original Ollama-based service
    - src/components/shared/embedding_factory.py: Factory for backend selection
    - docs/adr/ADR-024: BGE-M3 embedding selection
"""

import asyncio
import hashlib
import time
from collections import OrderedDict
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Lazy import for optional dependency
SentenceTransformer = None


class LRUCache:
    """Least Recently Used (LRU) cache with size limit.

    Identical implementation to UnifiedEmbeddingService.LRUCache
    to maintain consistency across embedding backends.
    """

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


class SentenceTransformersEmbeddingService:
    """High-performance embedding service using sentence-transformers.

    Optimized for DGX Spark deployment with:
    - Native batch processing (100+ texts parallel)
    - Direct GPU access (no HTTP overhead)
    - GPU utilization: 90%+ (vs 30-50% with Ollama)
    - Throughput: ~500-1000 embeddings/sec (vs 50-100 with Ollama)

    Compatible API with UnifiedEmbeddingService for drop-in replacement.

    Args:
        model_name: HuggingFace model name (default: BAAI/bge-m3)
        device: Device for inference ('auto', 'cuda', 'cpu')
        batch_size: Batch size for embedding (default: 64)
        cache_max_size: Maximum cache size (default: 10000)

    Example:
        >>> service = SentenceTransformersEmbeddingService()
        >>> embedding = service.embed_single("Hello world")
        >>> len(embedding)
        1024

        >>> embeddings = service.embed_batch(["text1", "text2", "text3"])
        >>> len(embeddings)
        3

    Notes:
        - Model is loaded lazily on first embedding request
        - Batch size 64 is optimal for most GPUs
        - Device 'auto' uses CUDA if available, else CPU
        - Cache deduplicates identical texts automatically
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "auto",
        batch_size: int = 64,
        cache_max_size: int = 10000,
    ) -> None:
        """Initialize sentence-transformers embedding service.

        Args:
            model_name: HuggingFace model name (default: BAAI/bge-m3)
            device: Device for inference ('auto', 'cuda', 'cpu')
            batch_size: Batch size for embedding (default: 64)
            cache_max_size: Maximum cache size (default: 10000)
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.embedding_dim = 1024  # BGE-M3 dimension
        self._model: Any = None  # Lazy loading - will be SentenceTransformer when loaded
        self.cache = LRUCache(max_size=cache_max_size)

        logger.info(
            "sentence_transformers_embedding_service_initialized",
            model=self.model_name,
            device=self.device,
            batch_size=self.batch_size,
            embedding_dim=self.embedding_dim,
            cache_size=cache_max_size,
        )

    def _resolve_device(self) -> str:
        """Resolve 'auto' device to actual PyTorch device string.

        Returns:
            Device string ('cuda' or 'cpu') compatible with PyTorch

        Notes:
            - 'auto' resolves to 'cuda' if available, else 'cpu'
            - This is needed because SentenceTransformers requires valid PyTorch device strings
        """
        if self.device == "auto":
            import torch

            resolved = "cuda" if torch.cuda.is_available() else "cpu"
            logger.debug(
                "device_auto_resolved",
                original="auto",
                resolved=resolved,
                cuda_available=torch.cuda.is_available(),
            )
            return resolved
        return self.device

    def _load_model(self):
        """Load model lazily on first use.

        Returns:
            Loaded SentenceTransformer model

        Notes:
            - Model is loaded only once and cached in self._model
            - First load downloads model from HuggingFace (~400MB for BGE-M3)
            - Subsequent loads use cached model from disk
        """
        if self._model is None:
            # Lazy import for optional dependency
            from sentence_transformers import SentenceTransformer

            # Resolve 'auto' to actual device (Sprint 88 fix)
            resolved_device = self._resolve_device()

            load_start = time.perf_counter()
            self._model = SentenceTransformer(self.model_name, device=resolved_device)
            load_duration_ms = (time.perf_counter() - load_start) * 1000

            logger.info(
                "sentence_transformers_model_loaded",
                model=self.model_name,
                device=str(self._model.device),
                duration_ms=round(load_duration_ms, 2),
            )

        return self._model

    def _cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(text.encode()).hexdigest()

    def _embed_single_sync(self, text: str) -> list[float]:
        """Synchronous embedding for single text (internal use).

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1024 dimensions for BGE-M3)
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
            )
            return cached

        # Load model lazily
        model = self._load_model()

        # Generate embedding
        encode_start = time.perf_counter()
        embedding_array = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        embedding = embedding_array.tolist()
        encode_duration_ms = (time.perf_counter() - encode_start) * 1000

        # Cache result
        self.cache.set(cache_key, embedding)

        total_duration_ms = (time.perf_counter() - embed_start) * 1000
        logger.debug(
            "TIMING_embedding_single",
            duration_ms=round(total_duration_ms, 2),
            encode_duration_ms=round(encode_duration_ms, 2),
            text_length=len(text),
            embedding_dim=len(embedding),
        )

        return embedding

    async def embed_single(self, text: str) -> list[float]:
        """Embed single text with caching (async).

        Compatible API with UnifiedEmbeddingService.embed_single().
        Sprint 88: Made async for LangGraph compatibility.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1024 dimensions for BGE-M3)

        Example:
            >>> service = SentenceTransformersEmbeddingService()
            >>> embedding = await service.embed_single("Hello world")
            >>> len(embedding)
            1024
        """
        return await asyncio.to_thread(self._embed_single_sync, text)

    def _embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding (internal use).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        batch_start = time.perf_counter()
        embeddings = []
        cache_hits = 0
        cache_misses = 0
        uncached_texts: list[str] = []
        uncached_indices: list[int] = []
        total_chars = sum(len(t) for t in texts)

        # Check cache for each text
        for idx, text in enumerate(texts):
            cache_key = self._cache_key(text)
            cached = self.cache.get(cache_key)
            if cached:
                embeddings.append(cached)
                cache_hits += 1
            else:
                embeddings.append([])  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(idx)
                cache_misses += 1

        # Batch encode uncached texts
        if uncached_texts:
            model = self._load_model()

            encode_start = time.perf_counter()
            embeddings_array = model.encode(
                uncached_texts,
                batch_size=self.batch_size,
                show_progress_bar=len(uncached_texts) > 100,
                convert_to_numpy=True,
            )
            encode_duration_ms = (time.perf_counter() - encode_start) * 1000

            # Insert embeddings at correct positions and cache
            for i, idx in enumerate(uncached_indices):
                embedding = embeddings_array[i].tolist()
                embeddings[idx] = embedding
                cache_key = self._cache_key(uncached_texts[i])
                self.cache.set(cache_key, embedding)

            logger.debug(
                "TIMING_embedding_batch_encode",
                encode_duration_ms=round(encode_duration_ms, 2),
                batch_size=len(uncached_texts),
                embeddings_per_sec=round(len(uncached_texts) / (encode_duration_ms / 1000), 2),
            )

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
        )

        return embeddings

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed batch of texts with GPU acceleration (async).

        Compatible API with UnifiedEmbeddingService.embed_batch().
        Sprint 88: Made async for LangGraph compatibility.

        This method provides significant performance benefits:
        - 5-10x faster than sequential embed_single() calls
        - GPU utilization: 90%+ (parallel matrix operations)
        - Automatic deduplication via cache

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Example:
            >>> service = SentenceTransformersEmbeddingService()
            >>> embeddings = await service.embed_batch(["Hello", "World", "Test"])
            >>> len(embeddings)
            3
            >>> len(embeddings[0])
            1024

        Notes:
            - Cache is checked for each text before encoding
            - Uncached texts are batched for GPU encoding
            - Results are cached for future requests
            - Show progress bar for batches >100 texts
        """
        return await asyncio.to_thread(self._embed_batch_sync, texts)

    def get_stats(self) -> dict[str, Any]:
        """Get embedding service statistics.

        Compatible API with UnifiedEmbeddingService.get_stats().

        Returns:
            Dictionary with model info and cache statistics
        """
        return {
            "model": self.model_name,
            "device": self.device,
            "batch_size": self.batch_size,
            "embedding_dim": self.embedding_dim,
            "cache": self.cache.stats(),
        }
