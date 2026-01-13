"""Multi-vector embedding service using FlagEmbedding (BGE-M3).

Sprint Context: Sprint 87 (2026-01-13) - Feature 87.1: FlagEmbedding Service

Generates both dense and sparse vectors in a single forward pass to solve
the BM25 desync problem (TD-103). Replaces separate SentenceTransformers
(dense) + BM25 (sparse) with unified FlagEmbedding model.

Architecture:
    Text → FlagEmbedding → Dense (1024D) + Sparse (lexical weights) → Qdrant

    Dense Vector:
        - 1024-dimensional semantic embedding (identical to SentenceTransformers)
        - Used for semantic similarity search (cosine distance)
        - Stored in Qdrant named vector "dense"

    Sparse Vector:
        - Token-level lexical weights (learned BM25-like scoring)
        - Used for keyword/exact match retrieval
        - Stored in Qdrant sparse vector "sparse"

Benefits over SentenceTransformers + BM25:
    1. **Always in Sync:** Both vectors generated in same call, stored together
    2. **Learned Lexical Weights:** BGE-M3 learns better token importance than BM25
    3. **Single Model:** Simpler deployment, lower memory footprint
    4. **Server-Side RRF:** Qdrant Query API fuses both vectors natively

Performance Characteristics:
    - Dense + Sparse Generation: ~100-150 embeddings/sec (GPU)
    - GPU Utilization: 90%+ (same as SentenceTransformers)
    - Memory: ~2GB VRAM (BGE-M3 model)
    - Latency: ~10-20ms overhead vs dense-only

Compatible API:
    This service implements the same API as SentenceTransformersEmbeddingService:
    - embed_single(text: str) -> dict[str, Any]
    - embed_batch(texts: list[str]) -> list[dict[str, Any]]
    - embed_single_dense(text: str) -> list[float]  # Backward compat
    - embed_batch_dense(texts: list[str]) -> list[list[float]]  # Backward compat

Example:
    >>> from src.components.shared.flag_embedding_service import (
    ...     FlagEmbeddingService
    ... )
    >>> service = FlagEmbeddingService()
    >>>
    >>> # Multi-vector embedding (dense + sparse)
    >>> result = service.embed_single("Hello world")
    >>> result.keys()
    dict_keys(['dense', 'sparse', 'sparse_vector'])
    >>> len(result["dense"])
    1024
    >>> result["sparse"]  # {token_id: weight}
    {12345: 0.8, 67890: 0.6, ...}
    >>>
    >>> # Backward compatibility (dense-only)
    >>> dense_embedding = service.embed_single_dense("Hello world")
    >>> len(dense_embedding)
    1024

Feature Flag:
    To enable FlagEmbedding service:
        AEGIS_USE_FLAG_EMBEDDING=true

    Fallback to SentenceTransformers if:
        - Feature flag disabled
        - FlagEmbedding library not installed
        - Model loading fails

Notes:
    - Model is loaded lazily on first embedding request
    - LRU cache deduplicates identical texts (10,000 entries)
    - Batch processing is 5-10x faster than sequential calls
    - Device 'auto' uses CUDA if available, else CPU

See Also:
    - src/components/shared/sentence_transformers_embedding.py: Dense-only service
    - src/components/shared/sparse_vector_utils.py: Sparse vector conversion
    - src/components/shared/embedding_factory.py: Backend selection factory
    - docs/adr/ADR-042-bge-m3-native-hybrid.md: Architecture decision
"""

import hashlib
import time
from collections import OrderedDict
from typing import Any

import structlog

from src.components.shared.sparse_vector_utils import (
    hash_token,
    lexical_to_sparse_vector,
)

logger = structlog.get_logger(__name__)

# Lazy import for optional dependency
BGEM3FlagModel = None


class LRUCache:
    """Least Recently Used (LRU) cache for embedding results.

    Identical implementation to SentenceTransformersEmbeddingService.LRUCache
    to maintain consistency across embedding backends.

    Cache Key Format:
        SHA256 hash of input text (hex string)

    Cache Value Format:
        {
            "dense": list[float],           # 1024D vector
            "sparse": dict[int, float],     # {token_id: weight}
            "sparse_vector": SparseVector   # Qdrant format
        }

    Example:
        >>> cache = LRUCache(max_size=1000)
        >>> cache.set("hello", {"dense": [...], "sparse": {...}})
        >>> result = cache.get("hello")
        >>> cache.hit_rate()
        0.5
    """

    def __init__(self, max_size: int = 10000):
        """Initialize LRU cache.

        Args:
            max_size: Maximum number of cached embeddings
        """
        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> dict[str, Any] | None:
        """Get item from cache.

        Args:
            key: Cache key (SHA256 hash of text)

        Returns:
            Cached embedding result or None if not found
        """
        if key in self.cache:
            self._hits += 1
            self.cache.move_to_end(key)
            return self.cache[key]
        self._misses += 1
        return None

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Add item to cache with LRU eviction.

        Args:
            key: Cache key (SHA256 hash of text)
            value: Embedding result to cache
        """
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value

        # Evict oldest item if cache is full
        if len(self.cache) > self.max_size:
            evicted_key, _ = self.cache.popitem(last=False)
            logger.debug("cache_eviction", evicted_key=evicted_key[:16])

    def hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Hit rate as float (0.0 to 1.0)
        """
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache size, hits, misses, hit rate
        """
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate(),
        }


class FlagEmbeddingService:
    """Multi-vector embedding service using FlagEmbedding (BGE-M3).

    Generates dense (semantic) and sparse (lexical) vectors in a single
    forward pass, solving the BM25 desync problem (TD-103).

    Features:
        - Dense + sparse vectors in one call (no desync)
        - LRU cache for deduplication (10,000 entries)
        - Batch processing for GPU efficiency (5-10x speedup)
        - Backward compatibility with SentenceTransformers API
        - Feature flag control (AEGIS_USE_FLAG_EMBEDDING)

    Args:
        model_name: HuggingFace model name (default: BAAI/bge-m3)
        device: Device for inference ('auto', 'cuda', 'cpu')
        use_fp16: Use half-precision for faster inference (default: True)
        batch_size: Batch size for embedding (default: 32)
        cache_max_size: Maximum cache size (default: 10000)
        sparse_min_weight: Filter sparse tokens below this weight (default: 0.0)
        sparse_top_k: Keep only top-k sparse tokens (default: None = all)

    Example:
        >>> service = FlagEmbeddingService()
        >>>
        >>> # Multi-vector embedding
        >>> result = service.embed_single("Hello world")
        >>> result.keys()
        dict_keys(['dense', 'sparse', 'sparse_vector'])
        >>>
        >>> # Backward compatibility
        >>> dense = service.embed_single_dense("Hello world")
        >>> len(dense)
        1024

    Notes:
        - Model is loaded lazily on first use (~400MB download)
        - Batch size 32 is optimal for BGE-M3 on most GPUs
        - sparse_top_k=100 reduces storage by ~50-80%
        - use_fp16=True requires CUDA (falls back to fp32 on CPU)
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "auto",
        use_fp16: bool = True,
        batch_size: int = 32,
        cache_max_size: int = 10000,
        sparse_min_weight: float = 0.0,
        sparse_top_k: int | None = None,
    ) -> None:
        """Initialize FlagEmbedding service.

        Args:
            model_name: HuggingFace model name (default: BAAI/bge-m3)
            device: Device for inference ('auto', 'cuda', 'cpu')
            use_fp16: Use half-precision (default: True)
            batch_size: Batch size for embedding (default: 32)
            cache_max_size: Maximum cache size (default: 10000)
            sparse_min_weight: Filter sparse tokens below this weight
            sparse_top_k: Keep only top-k sparse tokens (None = all)
        """
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self.batch_size = batch_size
        self.embedding_dim = 1024  # BGE-M3 dimension
        self.sparse_min_weight = sparse_min_weight
        self.sparse_top_k = sparse_top_k
        self._model: Any = None  # Lazy loading - will be BGEM3FlagModel when loaded
        self.cache = LRUCache(max_size=cache_max_size)

        logger.info(
            "flag_embedding_service_initialized",
            model=self.model_name,
            device=self.device,
            use_fp16=self.use_fp16,
            batch_size=self.batch_size,
            embedding_dim=self.embedding_dim,
            cache_size=cache_max_size,
            sparse_min_weight=self.sparse_min_weight,
            sparse_top_k=self.sparse_top_k,
        )

    def _load_model(self):
        """Load FlagEmbedding model lazily on first use.

        Returns:
            Loaded BGEM3FlagModel instance

        Raises:
            ImportError: If FlagEmbedding library not installed

        Notes:
            - Model is loaded only once and cached in self._model
            - First load downloads model from HuggingFace (~400MB for BGE-M3)
            - Subsequent loads use cached model from disk
            - use_fp16=True requires CUDA (auto-falls back to fp32 on CPU)
        """
        if self._model is None:
            # Lazy import for optional dependency
            try:
                from FlagEmbedding import BGEM3FlagModel
            except ImportError as e:
                logger.error(
                    "flag_embedding_import_failed",
                    error=str(e),
                    hint="Install with: pip install FlagEmbedding",
                )
                raise

            load_start = time.perf_counter()

            # Load model with specified device and precision
            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=self.use_fp16,
                device=self.device,
            )

            load_duration_ms = (time.perf_counter() - load_start) * 1000

            logger.info(
                "flag_embedding_model_loaded",
                model=self.model_name,
                device=self.device,
                use_fp16=self.use_fp16,
                duration_ms=round(load_duration_ms, 2),
            )

        return self._model

    def _cache_key(self, text: str) -> str:
        """Generate cache key for text.

        Args:
            text: Input text

        Returns:
            SHA256 hash of text (hex string)
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def embed_single(self, text: str) -> dict[str, Any]:
        """Embed single text with caching, returning dense + sparse vectors.

        Args:
            text: Text to embed

        Returns:
            Dict with keys:
                - "dense": list[float] (1024D vector)
                - "sparse": dict[int, float] ({token_id: weight})
                - "sparse_vector": SparseVector (Qdrant format)

        Example:
            >>> service = FlagEmbeddingService()
            >>> result = service.embed_single("Hello world")
            >>> len(result["dense"])
            1024
            >>> result["sparse"]
            {12345: 0.8, 67890: 0.6, ...}
            >>> result["sparse_vector"]
            SparseVector(indices=[12345, 67890], values=[0.8, 0.6])
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

        # Generate dense + sparse embeddings
        encode_start = time.perf_counter()
        output = model.encode(
            [text],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,  # Skip ColBERT vectors (not used)
        )
        encode_duration_ms = (time.perf_counter() - encode_start) * 1000

        # Extract dense vector
        dense_vector = output["dense_vecs"][0].tolist()

        # Extract and convert sparse vector
        lexical_weights = output["lexical_weights"][0]
        sparse_dict = {hash_token(k): v for k, v in lexical_weights.items()}
        sparse_vector = lexical_to_sparse_vector(
            lexical_weights,
            min_weight=self.sparse_min_weight,
            top_k=self.sparse_top_k,
        )

        # Create result dict
        result = {
            "dense": dense_vector,
            "sparse": sparse_dict,
            "sparse_vector": sparse_vector,
        }

        # Cache result
        self.cache.set(cache_key, result)

        total_duration_ms = (time.perf_counter() - embed_start) * 1000
        logger.debug(
            "TIMING_embedding_single",
            duration_ms=round(total_duration_ms, 2),
            encode_duration_ms=round(encode_duration_ms, 2),
            text_length=len(text),
            embedding_dim=len(dense_vector),
            sparse_tokens=len(sparse_vector.indices),
        )

        return result

    def embed_batch(self, texts: list[str]) -> list[dict[str, Any]]:
        """Embed batch of texts with GPU acceleration.

        This method provides significant performance benefits:
        - 5-10x faster than sequential embed_single() calls
        - GPU utilization: 90%+ (parallel matrix operations)
        - Automatic deduplication via cache

        Args:
            texts: List of texts to embed

        Returns:
            List of dicts, each with:
                - "dense": list[float] (1024D vector)
                - "sparse": dict[int, float] ({token_id: weight})
                - "sparse_vector": SparseVector (Qdrant format)

        Example:
            >>> service = FlagEmbeddingService()
            >>> results = service.embed_batch(["Hello", "World", "Test"])
            >>> len(results)
            3
            >>> len(results[0]["dense"])
            1024

        Notes:
            - Cache is checked for each text before encoding
            - Uncached texts are batched for GPU encoding
            - Results are cached for future requests
            - Show progress bar for batches >100 texts
        """
        batch_start = time.perf_counter()
        results: list[dict[str, Any]] = []
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
                results.append(cached)
                cache_hits += 1
            else:
                results.append({})  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(idx)
                cache_misses += 1

        # Batch encode uncached texts
        if uncached_texts:
            model = self._load_model()

            encode_start = time.perf_counter()
            output = model.encode(
                uncached_texts,
                batch_size=self.batch_size,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,
            )
            encode_duration_ms = (time.perf_counter() - encode_start) * 1000

            # Process each uncached result
            for i, idx in enumerate(uncached_indices):
                # Extract dense vector
                dense_vector = output["dense_vecs"][i].tolist()

                # Extract and convert sparse vector
                lexical_weights = output["lexical_weights"][i]
                sparse_dict = {hash_token(k): v for k, v in lexical_weights.items()}
                sparse_vector = lexical_to_sparse_vector(
                    lexical_weights,
                    min_weight=self.sparse_min_weight,
                    top_k=self.sparse_top_k,
                )

                # Create result dict
                result = {
                    "dense": dense_vector,
                    "sparse": sparse_dict,
                    "sparse_vector": sparse_vector,
                }

                # Update results and cache
                results[idx] = result
                cache_key = self._cache_key(uncached_texts[i])
                self.cache.set(cache_key, result)

            logger.debug(
                "TIMING_embedding_batch_encode",
                encode_duration_ms=round(encode_duration_ms, 2),
                batch_size=len(uncached_texts),
                embeddings_per_sec=round(len(uncached_texts) / (encode_duration_ms / 1000), 2),
                avg_sparse_tokens=round(
                    sum(len(r["sparse_vector"].indices) for r in results if r) / len(results),
                    0,
                )
                if results
                else 0,
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

        return results

    # Backward compatibility methods (dense-only)

    def embed_single_dense(self, text: str) -> list[float]:
        """Embed single text, returning only dense vector.

        Backward compatibility method for SentenceTransformers API.

        Args:
            text: Text to embed

        Returns:
            Dense embedding vector (1024 dimensions)

        Example:
            >>> service = FlagEmbeddingService()
            >>> embedding = service.embed_single_dense("Hello world")
            >>> len(embedding)
            1024
        """
        result = self.embed_single(text)
        return result["dense"]

    def embed_batch_dense(self, texts: list[str]) -> list[list[float]]:
        """Embed batch of texts, returning only dense vectors.

        Backward compatibility method for SentenceTransformers API.

        Args:
            texts: List of texts to embed

        Returns:
            List of dense embedding vectors

        Example:
            >>> service = FlagEmbeddingService()
            >>> embeddings = service.embed_batch_dense(["Hello", "World"])
            >>> len(embeddings)
            2
            >>> len(embeddings[0])
            1024
        """
        results = self.embed_batch(texts)
        return [r["dense"] for r in results]

    def get_stats(self) -> dict[str, Any]:
        """Get embedding service statistics.

        Compatible API with SentenceTransformersEmbeddingService.get_stats().

        Returns:
            Dictionary with model info and cache statistics
        """
        return {
            "model": self.model_name,
            "device": self.device,
            "use_fp16": self.use_fp16,
            "batch_size": self.batch_size,
            "embedding_dim": self.embedding_dim,
            "sparse_min_weight": self.sparse_min_weight,
            "sparse_top_k": self.sparse_top_k,
            "cache": self.cache.stats(),
        }


# Global singleton instance
_flag_embedding_service: FlagEmbeddingService | None = None


def get_flag_embedding_service(
    model_name: str = "BAAI/bge-m3",
    device: str = "auto",
    use_fp16: bool = True,
    batch_size: int = 32,
    cache_max_size: int = 10000,
    sparse_min_weight: float = 0.0,
    sparse_top_k: int | None = None,
) -> FlagEmbeddingService:
    """Get global FlagEmbedding service instance (singleton).

    Factory function that returns singleton instance for efficiency
    (shared cache, model loading). Subsequent calls return cached instance.

    Args:
        model_name: HuggingFace model name (default: BAAI/bge-m3)
        device: Device for inference ('auto', 'cuda', 'cpu')
        use_fp16: Use half-precision (default: True)
        batch_size: Batch size for embedding (default: 32)
        cache_max_size: Maximum cache size (default: 10000)
        sparse_min_weight: Filter sparse tokens below this weight
        sparse_top_k: Keep only top-k sparse tokens (None = all)

    Returns:
        FlagEmbeddingService instance (singleton)

    Example:
        >>> from src.components.shared.flag_embedding_service import (
        ...     get_flag_embedding_service
        ... )
        >>> service = get_flag_embedding_service()
        >>> result = service.embed_single("Hello world")

    Notes:
        - First call loads model and caches instance
        - Subsequent calls return cached instance (singleton)
        - To reset instance, use reset_flag_embedding_service()
    """
    global _flag_embedding_service

    if _flag_embedding_service is not None:
        return _flag_embedding_service

    _flag_embedding_service = FlagEmbeddingService(
        model_name=model_name,
        device=device,
        use_fp16=use_fp16,
        batch_size=batch_size,
        cache_max_size=cache_max_size,
        sparse_min_weight=sparse_min_weight,
        sparse_top_k=sparse_top_k,
    )

    logger.info("flag_embedding_service_created_singleton")

    return _flag_embedding_service


def reset_flag_embedding_service() -> None:
    """Reset global FlagEmbedding service instance.

    Used for testing to force reinitialization with different config.

    Example:
        >>> from src.components.shared.flag_embedding_service import (
        ...     reset_flag_embedding_service,
        ...     get_flag_embedding_service
        ... )
        >>> reset_flag_embedding_service()
        >>> service = get_flag_embedding_service()  # Forces reinitialization
    """
    global _flag_embedding_service
    _flag_embedding_service = None
    logger.debug("flag_embedding_service_reset")
