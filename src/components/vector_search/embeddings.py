"""Embedding Service for nomic-embed-text via Ollama.

This module provides embedding generation using Ollama's nomic-embed-text model
with automatic batching, caching, and error handling.
"""

from typing import List, Optional, Dict, Any
from functools import lru_cache
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

        # Cache for embeddings (in-memory)
        self._cache: Dict[str, List[float]] = {}

        logger.info(
            "Embedding service initialized",
            model=self.model_name,
            base_url=self.base_url,
            batch_size=self.batch_size,
            cache_enabled=self.enable_cache,
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
            if cache_key in self._cache:
                logger.debug("Embedding cache hit", text_length=len(text))
                return self._cache[cache_key]

        try:
            # Generate embedding
            embedding = await self._embedding_model.aget_text_embedding(text)

            # Cache result
            if self.enable_cache:
                cache_key = self._get_cache_key(text)
                self._cache[cache_key] = embedding

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

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            LLMError: If batch embedding fails
        """
        if not texts:
            return []

        embeddings = []
        cache_hits = 0
        cache_misses = 0

        # Check cache for each text
        texts_to_embed = []
        text_indices = []

        for idx, text in enumerate(texts):
            if self.enable_cache:
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    embeddings.append(self._cache[cache_key])
                    cache_hits += 1
                    continue

            texts_to_embed.append(text)
            text_indices.append(idx)
            cache_misses += 1

        # Generate embeddings for uncached texts in batches
        if texts_to_embed:
            try:
                # Process in batches
                for i in range(0, len(texts_to_embed), self.batch_size):
                    batch = texts_to_embed[i : i + self.batch_size]
                    batch_embeddings = await self._embedding_model.aget_text_embedding_batch(
                        batch
                    )

                    # Cache results
                    if self.enable_cache:
                        for text, embedding in zip(batch, batch_embeddings):
                            cache_key = self._get_cache_key(text)
                            self._cache[cache_key] = embedding

                    embeddings.extend(batch_embeddings)

                logger.info(
                    "Batch embeddings generated",
                    total_texts=len(texts),
                    cache_hits=cache_hits,
                    cache_misses=cache_misses,
                    batches=len(texts_to_embed) // self.batch_size + 1,
                )

            except Exception as e:
                logger.error(
                    "Batch embedding failed",
                    texts_count=len(texts_to_embed),
                    error=str(e),
                )
                raise LLMError(f"Failed to generate batch embeddings: {e}") from e

        return embeddings

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for the model.

        Returns:
            Embedding dimension (768 for nomic-embed-text)
        """
        # nomic-embed-text has 768 dimensions
        return 768

    def clear_cache(self):
        """Clear embedding cache."""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info("Embedding cache cleared", cached_embeddings=cache_size)

    def get_cache_size(self) -> int:
        """Get number of cached embeddings.

        Returns:
            Number of cached embeddings
        """
        return len(self._cache)

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
