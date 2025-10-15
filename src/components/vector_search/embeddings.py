"""Embedding Service for nomic-embed-text via Ollama.

This module provides embedding generation using Ollama's nomic-embed-text model
with automatic batching, caching, and error handling.
"""

from typing import List, Optional, Dict, Any
from functools import lru_cache
from collections import OrderedDict
import hashlib

import structlog
from llama_index.embeddings.ollama import OllamaEmbedding
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.core.config import settings
from src.core.exceptions import LLMError

logger = structlog.get_logger(__name__)


class LRUCache:
    """Least Recently Used (LRU) cache with size limit.

    Prevents unbounded memory growth by evicting least recently used items
    when cache reaches max_size.
    """

    def __init__(self, max_size: int = 10000):
        """Initialize LRU cache.

        Args:
            max_size: Maximum number of items to cache (default: 10000)
        """
        self.cache: OrderedDict[str, List[float]] = OrderedDict()
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[List[float]]:
        """Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if key in self.cache:
            self._hits += 1
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        self._misses += 1
        return None

    def set(self, key: str, value: List[float]) -> None:
        """Add item to cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self.cache:
            # Update existing item and move to end
            self.cache.move_to_end(key)
        self.cache[key] = value

        # Evict least recently used item if cache is full
        if len(self.cache) > self.max_size:
            evicted_key, _ = self.cache.popitem(last=False)
            logger.debug(
                "Cache eviction",
                evicted_key=evicted_key[:16],
                cache_size=len(self.cache),
                max_size=self.max_size,
            )

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self._hits = 0
        self._misses = 0

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

    def __len__(self) -> int:
        """Get current cache size (allows len(cache))."""
        return len(self.cache)

    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate(),
        }


class EmbeddingService:
    """Production-ready embedding service with caching and batching."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        batch_size: int = 32,
        enable_cache: bool = True,
    ):
        """Initialize embedding service.

        Args:
            model_name: Ollama model name (default: from settings)
            base_url: Ollama server URL (default: from settings)
            batch_size: Number of texts to embed in one batch (default: 32)
            enable_cache: Enable in-memory caching (default: True)
        """
        self.model_name = model_name or settings.ollama_model_embedding
        self.base_url = base_url or settings.ollama_base_url
        self.batch_size = batch_size
        self.enable_cache = enable_cache

        # Initialize Ollama embedding model
        self._embedding_model = OllamaEmbedding(
            model_name=self.model_name,
            base_url=self.base_url,
            ollama_additional_kwargs={"temperature": 0},
        )

        # Cache for embeddings (LRU cache with bounded size)
        self._cache = LRUCache(max_size=10000)

        logger.info(
            "Embedding service initialized",
            model=self.model_name,
            base_url=self.base_url,
            batch_size=self.batch_size,
            cache_enabled=self.enable_cache,
            cache_max_size=10000,
        )

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text.

        Args:
            text: Input text

        Returns:
            MD5 hash of text
        """
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
    )
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (768-dim for nomic-embed-text)

        Raises:
            LLMError: If embedding generation fails
        """
        # Check cache first
        if self.enable_cache:
            cache_key = self._get_cache_key(text)
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Embedding cache hit", text_length=len(text))
                return cached

        try:
            # Generate embedding
            embedding = await self._embedding_model.aget_text_embedding(text)

            # Cache result
            if self.enable_cache:
                cache_key = self._get_cache_key(text)
                self._cache.set(cache_key, embedding)

            logger.debug(
                "Embedding generated",
                text_length=len(text),
                embedding_dim=len(embedding),
            )

            return embedding

        except Exception as e:
            logger.error(
                "Embedding generation failed",
                text_length=len(text),
                error=str(e),
            )
            raise LLMError(f"Failed to generate embedding: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batches.

        IMPORTANT: Maintains input order - embeddings[i] corresponds to texts[i].

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors in same order as input

        Raises:
            LLMError: If batch embedding fails
        """
        if not texts:
            return []

        # Dictionary to store embeddings by index (preserves order)
        embeddings_dict: Dict[int, List[float]] = {}
        cache_hits = 0
        cache_misses = 0

        # Separate cached and uncached texts
        uncached_texts = []
        uncached_indices = []

        for idx, text in enumerate(texts):
            if self.enable_cache:
                cache_key = self._get_cache_key(text)
                cached = self._cache.get(cache_key)
                if cached is not None:
                    embeddings_dict[idx] = cached
                    cache_hits += 1
                    continue

            uncached_texts.append(text)
            uncached_indices.append(idx)
            cache_misses += 1

        # Generate embeddings for uncached texts in batches
        if uncached_texts:
            try:
                new_embeddings = []
                # Process in batches
                for i in range(0, len(uncached_texts), self.batch_size):
                    batch = uncached_texts[i : i + self.batch_size]
                    batch_embeddings = await self._embedding_model.aget_text_embedding_batch(
                        batch
                    )
                    new_embeddings.extend(batch_embeddings)

                # Map embeddings back to original indices and cache them
                for uncached_idx, embedding in zip(uncached_indices, new_embeddings):
                    embeddings_dict[uncached_idx] = embedding

                    # Cache result
                    if self.enable_cache:
                        text = texts[uncached_idx]
                        cache_key = self._get_cache_key(text)
                        self._cache.set(cache_key, embedding)

                logger.info(
                    "Batch embeddings generated",
                    total_texts=len(texts),
                    cache_hits=cache_hits,
                    cache_misses=cache_misses,
                    batches=(len(uncached_texts) + self.batch_size - 1) // self.batch_size,
                )

            except Exception as e:
                logger.error(
                    "Batch embedding failed",
                    texts_count=len(uncached_texts),
                    error=str(e),
                )
                raise LLMError(f"Failed to generate batch embeddings: {e}") from e

        # Return embeddings in original order
        return [embeddings_dict[i] for i in range(len(texts))]

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for the model.

        Returns:
            Embedding dimension (768 for nomic-embed-text)
        """
        # nomic-embed-text has 768 dimensions
        return 768

    def clear_cache(self):
        """Clear embedding cache."""
        cache_size = self._cache.size()
        self._cache.clear()
        logger.info("Embedding cache cleared", cached_embeddings=cache_size)

    def get_cache_size(self) -> int:
        """Get number of cached embeddings.

        Returns:
            Number of cached embeddings
        """
        return self._cache.size()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats (size, hits, misses, hit_rate)
        """
        return self._cache.stats()

    @property
    def model_info(self) -> Dict[str, Any]:
        """Get model information.

        Returns:
            Dictionary with model metadata
        """
        return {
            "model_name": self.model_name,
            "base_url": self.base_url,
            "embedding_dimension": self.get_embedding_dimension(),
            "batch_size": self.batch_size,
            "cache_enabled": self.enable_cache,
            "cached_embeddings": self.get_cache_size(),
        }


# Global embedding service instance (singleton pattern)
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get global embedding service instance (singleton).

    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
