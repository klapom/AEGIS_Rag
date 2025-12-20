"""Vector Search Domain Protocols.

Sprint 57 Feature 57.4: Protocol definitions for vector operations.
Enables dependency injection and improves testability.

Usage:
    from src.domains.vector_search.protocols import (
        EmbeddingService,
        VectorStore,
        HybridSearchService,
    )

These protocols define interfaces for:
- Embedding generation (BGE-M3)
- Vector storage (Qdrant)
- Hybrid search (Vector + BM25 + RRF)
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingService(Protocol):
    """Protocol for embedding generation.

    Implementations should generate vector embeddings for text
    using embedding models.

    ADR-024: BGE-M3 embeddings (1024-dim, multilingual).

    Example:
        >>> class BGEEmbeddingService:
        ...     async def embed(self, text: str) -> list[float]:
        ...         # Use BGE-M3 to generate embedding
        ...         pass
    """

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1024 dimensions for BGE-M3)
        """
        ...

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        ...

    def get_dimension(self) -> int:
        """Get embedding dimension.

        Returns:
            Dimension of embedding vectors
        """
        ...

    def get_model_name(self) -> str:
        """Get embedding model name.

        Returns:
            Model identifier
        """
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Protocol for vector storage.

    Implementations should provide CRUD operations for vectors
    in a vector database.

    Example:
        >>> class QdrantVectorStore:
        ...     async def upsert(self, vectors: list[dict], collection: str) -> None:
        ...         # Store in Qdrant
        ...         pass
    """

    async def upsert(
        self,
        vectors: list[dict[str, Any]],
        collection: str,
    ) -> None:
        """Upsert vectors to collection.

        Args:
            vectors: List of vectors with:
                - id: str
                - vector: list[float]
                - payload: dict
            collection: Collection name
        """
        ...

    async def search(
        self,
        query_vector: list[float],
        collection: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.

        Args:
            query_vector: Query embedding
            collection: Collection name
            top_k: Number of results to return
            filters: Optional filters
            score_threshold: Minimum score threshold

        Returns:
            List of results with:
            - id: str
            - score: float
            - payload: dict
        """
        ...

    async def delete(
        self,
        ids: list[str],
        collection: str,
    ) -> None:
        """Delete vectors from collection.

        Args:
            ids: List of vector IDs to delete
            collection: Collection name
        """
        ...

    async def get_collection_info(
        self,
        collection: str,
    ) -> dict[str, Any]:
        """Get collection information.

        Args:
            collection: Collection name

        Returns:
            Collection info with:
            - vectors_count: int
            - status: str
        """
        ...


@runtime_checkable
class HybridSearchService(Protocol):
    """Protocol for hybrid search.

    Implementations should combine vector search with keyword
    search using Reciprocal Rank Fusion (RRF).

    Example:
        >>> class MaximumHybridSearch:
        ...     async def search(self, query: str, top_k: int = 10) -> list[dict]:
        ...         # Combine vector + BM25 with RRF
        ...         pass
    """

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute hybrid search.

        Args:
            query: Natural language query
            top_k: Number of results to return
            filters: Optional filters
            namespace: Optional namespace filter

        Returns:
            List of results with:
            - id: str
            - score: float
            - text: str
            - metadata: dict
        """
        ...

    async def search_vector_only(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute vector-only search.

        Args:
            query: Natural language query
            top_k: Number of results

        Returns:
            Vector search results
        """
        ...

    async def search_keyword_only(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute keyword-only (BM25) search.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            BM25 search results
        """
        ...


@runtime_checkable
class RerankingService(Protocol):
    """Protocol for search result reranking.

    Implementations should rerank search results using
    cross-encoder or other reranking models.
    """

    async def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Rerank search results.

        Args:
            query: Original query
            results: Search results to rerank
            top_k: Number of results to return

        Returns:
            Reranked results with updated scores
        """
        ...


__all__ = [
    "EmbeddingService",
    "VectorStore",
    "HybridSearchService",
    "RerankingService",
]
