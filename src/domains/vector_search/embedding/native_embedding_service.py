"""Native Sentence-Transformers embedding service.

Sprint 61 Feature 61.1: Native BGE-M3 Embeddings
Based on TD-073 investigation - 3-5x faster than Ollama.

Performance Benchmarks (from TD-073):
- Single embedding: 20ms (vs 100ms Ollama) = 5x faster
- Batch 32: 100ms (vs 1600ms Ollama) = 16x faster
- VRAM: 2GB (vs 5GB Ollama) = 60% reduction
- Quality: Identical (same BGE-M3 weights)
"""

import structlog
import torch
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger(__name__)


class NativeEmbeddingService:
    """Native sentence-transformers embedding service using BGE-M3.

    This service provides a direct alternative to Ollama embeddings with
    significant performance improvements while maintaining identical quality.

    Performance (from TD-073):
    - Single embedding: 20ms (vs 100ms Ollama) = 5x faster
    - Batch 32: 100ms (vs 1600ms Ollama) = 16x faster
    - VRAM: 2GB (vs 5GB Ollama) = 60% reduction

    Memory Efficiency:
    - Model is kept loaded in VRAM (small 2GB footprint)
    - Batch processing is highly optimized
    - Automatic GPU/CPU fallback
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "auto",
        batch_size: int = 32,
        normalize_embeddings: bool = True,
    ):
        """Initialize native embedding service.

        Args:
            model_name: HuggingFace model ID (default: BAAI/bge-m3)
            device: Device to run on ('cuda', 'cpu', or 'auto')
            batch_size: Batch size for encoding (default: 32)
            normalize_embeddings: Whether to L2-normalize embeddings
        """
        logger.info(
            "initializing_native_embedding_service",
            model=model_name,
            device=device,
            batch_size=batch_size,
        )

        # Determine device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.batch_size = batch_size
        self.normalize_embeddings = normalize_embeddings
        self.model_name = model_name

        # Load model
        try:
            self.model = SentenceTransformer(
                model_name,
                device=device,
                trust_remote_code=True,
            )

            # Get embedding dimension
            self.embedding_dim = self.model.get_sentence_embedding_dimension()

            logger.info(
                "native_embedding_service_initialized",
                model=model_name,
                device=device,
                embedding_dim=self.embedding_dim,
                vram_usage_gb=self._estimate_vram_usage(),
            )

        except Exception as e:
            logger.error(
                "native_embedding_service_init_failed",
                model=model_name,
                device=device,
                error=str(e),
            )
            raise

    def _estimate_vram_usage(self) -> float:
        """Estimate VRAM usage in GB.

        Returns:
            Estimated VRAM usage in GB
        """
        if self.device == "cpu":
            return 0.0

        try:
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                allocated_gb = torch.cuda.memory_allocated() / 1024**3
                return round(allocated_gb, 2)
        except Exception:
            pass

        # Fallback estimate for BGE-M3
        return 2.0

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        embedding = self.model.encode(
            text,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False,
        )
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts efficiently.

        This method uses automatic batching for optimal performance.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        logger.debug(
            "embedding_batch",
            count=len(texts),
            batch_size=self.batch_size,
        )

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a search query.

        For BGE-M3, queries should be prefixed with "Represent this sentence for searching
        relevant passages:" for optimal retrieval performance.

        Args:
            query: Search query text

        Returns:
            Embedding vector as list of floats
        """
        # BGE-M3 query prefix for optimal retrieval
        prefixed_query = f"Represent this sentence for searching relevant passages: {query}"

        return self.embed_text(prefixed_query)

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model.

        Returns:
            Embedding dimension (1024 for BGE-M3)
        """
        return self.embedding_dim

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"NativeEmbeddingService("
            f"model={self.model_name}, "
            f"device={self.device}, "
            f"dim={self.embedding_dim})"
        )
