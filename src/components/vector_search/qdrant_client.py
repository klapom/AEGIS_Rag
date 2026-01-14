"""Qdrant Client Wrapper with Connection Pooling and Error Handling.

This module provides a production-ready wrapper around the Qdrant client with:
- Connection pooling
- Automatic retry logic
- Health checks
- Collection management
- Batch operations
"""

import time
from contextlib import asynccontextmanager
from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    CollectionInfo,
    Distance,
    Filter,
    PointStruct,
    VectorParams,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.core.exceptions import DatabaseConnectionError, VectorSearchError

logger = structlog.get_logger(__name__)


class QdrantClient:
    """Production-ready Qdrant client with connection pooling and error handling.

    Sprint 25 Feature 25.9: Renamed from QdrantClientWrapper to QdrantClient for consistency.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        grpc_port: int | None = None,
        prefer_grpc: bool = True,
        timeout: int = 30,
    ) -> None:
        """Initialize Qdrant client wrapper.

        Args:
            host: Qdrant server host (default: from settings)
            port: Qdrant HTTP port (default: from settings)
            grpc_port: Qdrant gRPC port (default: from settings)
            prefer_grpc: Use gRPC for better performance (default: True)
            timeout: Request timeout in seconds (default: 30)
        """
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.grpc_port = grpc_port or settings.qdrant_grpc_port
        self.prefer_grpc = prefer_grpc
        self.timeout = timeout

        self._client: QdrantClient | None = None
        self._async_client: AsyncQdrantClient | None = None

        logger.info(
            "Initializing Qdrant client",
            host=self.host,
            port=self.port,
            grpc_port=self.grpc_port,
            prefer_grpc=self.prefer_grpc,
        )

    @property
    def client(self) -> QdrantClient:
        """Get synchronous Qdrant client (lazy initialization)."""
        if self._client is None:
            self._client = QdrantClient(
                host=self.host,
                port=self.port,
                grpc_port=self.grpc_port,
                prefer_grpc=self.prefer_grpc,
                timeout=self.timeout,  # P1: Add timeout
                # P1: Connection pool limits to prevent resource exhaustion
                grpc_options={
                    "grpc.max_receive_message_length": 100 * 1024 * 1024,  # 100MB
                    "grpc.max_send_message_length": 100 * 1024 * 1024,
                    "grpc.keepalive_time_ms": 30000,
                    "grpc.keepalive_timeout_ms": 10000,
                },
            )
            logger.info("Qdrant sync client initialized")
        return self._client

    @property
    def async_client(self) -> AsyncQdrantClient:
        """Get asynchronous Qdrant client (lazy initialization)."""
        if self._async_client is None:
            self._async_client = AsyncQdrantClient(
                host=self.host,
                port=self.port,
                grpc_port=self.grpc_port,
                prefer_grpc=self.prefer_grpc,
                timeout=self.timeout,
            )
            logger.info("Qdrant async client initialized")
        return self._async_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(UnexpectedResponse),
    )
    async def health_check(self) -> bool:
        """Check if Qdrant server is healthy.

        Returns:
            True if server is healthy, False otherwise

        Raises:
            DatabaseConnectionError: If connection fails after retries
        """
        try:
            # Try to get cluster info
            await self.async_client.get_collections()
            logger.info("Qdrant health check passed")
            return True
        except Exception as e:
            logger.error("Qdrant health check failed", error=str(e))
            raise DatabaseConnectionError(
                database="Qdrant", reason=f"Health check failed: {e}"
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        on_disk_payload: bool = True,
    ) -> bool:
        """Create a new collection with optimized settings.

        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors (1024 for bge-m3, Sprint 16 migration)
            distance: Distance metric (COSINE, EUCLIDEAN, DOT)
            on_disk_payload: Store payload on disk to save RAM

        Returns:
            True if collection created successfully

        Raises:
            VectorSearchError: If creation fails
        """
        try:
            # Check if collection exists
            collections = await self.async_client.get_collections()
            if collection_name in [c.name for c in collections.collections]:
                logger.info(
                    "Collection already exists",
                    collection_name=collection_name,
                )
                return True

            # Create collection with optimized settings
            await self.async_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                    on_disk=False,  # Keep vectors in RAM for speed
                ),
                on_disk_payload=on_disk_payload,
                optimizers_config={
                    "memmap_threshold": 20000,  # Use mmap for large collections
                },
            )

            logger.info(
                "Collection created successfully",
                collection_name=collection_name,
                vector_size=vector_size,
                distance=distance,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to create collection",
                collection_name=collection_name,
                error=str(e),
            )
            raise VectorSearchError(query="", reason=f"Failed to create collection: {e}") from e

    async def upsert_points(
        self,
        collection_name: str,
        points: list[PointStruct],
        batch_size: int = 100,
    ) -> bool:
        """Upsert points to collection in batches.

        Args:
            collection_name: Target collection name
            points: list of PointStruct objects
            batch_size: Number of points per batch (default: 100)

        Returns:
            True if all points upserted successfully

        Raises:
            VectorSearchError: If upsert fails
        """
        upsert_start = time.perf_counter()
        num_batches = (len(points) + batch_size - 1) // batch_size
        batch_timings = []

        try:
            # Process in batches for better performance
            for i in range(0, len(points), batch_size):
                batch_start = time.perf_counter()
                batch = points[i : i + batch_size]
                await self.async_client.upsert(
                    collection_name=collection_name,
                    points=batch,
                )
                batch_duration_ms = (time.perf_counter() - batch_start) * 1000
                batch_timings.append(batch_duration_ms)

            upsert_end = time.perf_counter()
            total_duration_ms = (upsert_end - upsert_start) * 1000
            points_per_sec = (
                len(points) / (total_duration_ms / 1000) if total_duration_ms > 0 else 0
            )
            avg_batch_ms = sum(batch_timings) / len(batch_timings) if batch_timings else 0

            logger.info(
                "TIMING_qdrant_upsert_complete",
                stage="qdrant",
                duration_ms=round(total_duration_ms, 2),
                collection_name=collection_name,
                total_points=len(points),
                batch_size=batch_size,
                num_batches=num_batches,
                avg_batch_ms=round(avg_batch_ms, 2),
                throughput_points_per_sec=round(points_per_sec, 2),
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to upsert points",
                collection_name=collection_name,
                error=str(e),
            )
            raise VectorSearchError(query="", reason=f"Failed to upsert points: {e}") from e

    async def ingest_adaptive_chunks(
        self,
        chunks: list[Any],
        collection_name: str,
        batch_size: int = 100,
    ) -> bool:
        """Ingest AdaptiveChunk objects with multi-section metadata into Qdrant.

        Sprint 32 Feature 32.3: Multi-Section Metadata in Qdrant
        ADR-039: Adaptive Section-Aware Chunking

        This method handles the ingestion of adaptive chunks with section metadata.
        It expects chunks to have the following attributes:
        - text: str (chunk content)
        - section_headings: list[str] (section titles)
        - section_pages: list[int] (page numbers)
        - section_bboxes: list[dict] (bounding boxes)
        - primary_section: str (main section)
        - metadata: dict (additional metadata)

        The section metadata enables:
        1. Section-based re-ranking (boost results matching query sections)
        2. Precise citations (include section names in citations)
        3. Hierarchical queries (find all chunks from a specific section)

        Args:
            chunks: list of AdaptiveChunk objects (from src.components.retrieval.chunking)
            collection_name: Target Qdrant collection
            batch_size: Batch size for ingestion (default: 100)

        Returns:
            True if all chunks ingested successfully

        Raises:
            VectorSearchError: If ingestion fails

        Example:
            >>> from src.components.retrieval.chunking import AdaptiveChunk
            >>> chunks = [
            ...     AdaptiveChunk(
            ...         text="Multi-Server Architecture\\n\\nLoad Balancing...",
            ...         token_count=1050,
            ...         section_headings=["Multi-Server", "Load Balancing"],
            ...         section_pages=[1, 2],
            ...         section_bboxes=[{"l": 50, "t": 30, "r": 670, "b": 80}, ...],
            ...         primary_section="Multi-Server Architecture",
            ...         metadata={"source": "doc.pptx", "num_sections": 2}
            ...     )
            ... ]
            >>> await client.ingest_adaptive_chunks(chunks, "documents")
        """
        try:
            # Import embedding service (lazy to avoid circular imports)
            from src.components.shared.embedding_service import get_embedding_service

            embedding_service = get_embedding_service()

            # Build points with embeddings and section metadata
            points: list[PointStruct] = []

            for idx, chunk in enumerate(chunks):
                # Generate embedding for chunk text
                # Sprint 92 Fix: Handle both list (Ollama/ST) and dict (FlagEmbedding) returns
                embedding_result = await embedding_service.embed_single(chunk.text)
                embedding = (
                    embedding_result["dense"]
                    if isinstance(embedding_result, dict)
                    else embedding_result
                )

                # Build Qdrant payload with section metadata
                payload = {
                    "text": chunk.text,
                    "token_count": chunk.token_count,
                    # Sprint 32: Multi-section metadata
                    "section_headings": chunk.section_headings,
                    "section_pages": chunk.section_pages,
                    "section_bboxes": chunk.section_bboxes,
                    "primary_section": chunk.primary_section,
                    # Sprint 62.2: Add section_id for filtering
                    # Extract section_id from metadata if available
                    "section_id": chunk.metadata.get("section_id", ""),
                    # Additional metadata (source, file_type, etc.)
                    **chunk.metadata,
                }

                point = PointStruct(
                    id=idx,
                    vector=embedding,
                    payload=payload,
                )
                points.append(point)

            # Upsert points in batches
            success = await self.upsert_points(
                collection_name=collection_name,
                points=points,
                batch_size=batch_size,
            )

            logger.info(
                "Adaptive chunks ingested with section metadata",
                collection_name=collection_name,
                chunks_count=len(chunks),
                sections_tracked=sum(len(c.section_headings) for c in chunks),
                batch_size=batch_size,
            )

            return success

        except Exception as e:
            logger.error(
                "Failed to ingest adaptive chunks",
                collection_name=collection_name,
                error=str(e),
            )
            raise VectorSearchError(
                query="", reason=f"Failed to ingest adaptive chunks: {e}"
            ) from e

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float | None = None,
        query_filter: Filter | None = None,
        section_filter: str | list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors in collection.

        Sprint 62 Feature 62.2: Added section_filter parameter for section-based filtering.

        Args:
            collection_name: Collection to search in
            query_vector: Query embedding vector
            limit: Maximum number of results (default: 10)
            score_threshold: Minimum similarity score (default: None)
            query_filter: Optional metadata filter
            section_filter: Filter by section ID(s) (Sprint 62.2)
                - Single section: "1.2"
                - Multiple sections: ["1.1", "1.2", "2.1"]
                - None: No section filtering (backward compatible)

        Returns:
            list of search results with id, score, and payload

        Raises:
            VectorSearchError: If search fails
        """
        try:
            # Sprint 62.2: Build section filter if provided
            combined_filter = query_filter
            if section_filter is not None:
                from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

                # Normalize section_filter to list
                section_ids = (
                    [section_filter] if isinstance(section_filter, str) else section_filter
                )

                # Build section filter condition
                if len(section_ids) == 1:
                    # Single section - use MatchValue
                    section_condition = FieldCondition(
                        key="section_id",
                        match=MatchValue(value=section_ids[0]),
                    )
                else:
                    # Multiple sections - use MatchAny
                    section_condition = FieldCondition(
                        key="section_id",
                        match=MatchAny(any=section_ids),
                    )

                # Combine with existing filter if present
                if combined_filter is not None:
                    # Merge filters using AND logic
                    must_conditions = combined_filter.must if combined_filter.must else []
                    combined_filter = Filter(
                        must=[
                            *must_conditions,
                            section_condition,
                        ],
                        should=combined_filter.should,
                        must_not=combined_filter.must_not,
                    )
                else:
                    combined_filter = Filter(must=[section_condition])

                logger.debug(
                    "section_filter_applied",
                    section_ids=section_ids,
                    num_sections=len(section_ids),
                )

            results = await self.async_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=combined_filter,
            )

            formatted_results = [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                }
                for hit in results
            ]

            logger.debug(
                "Vector search completed",
                collection_name=collection_name,
                results_count=len(formatted_results),
                limit=limit,
                section_filter_applied=section_filter is not None,
            )

            return formatted_results

        except Exception as e:
            logger.error(
                "Vector search failed",
                collection_name=collection_name,
                error=str(e),
            )
            raise VectorSearchError(query="", reason=f"Vector search failed: {e}") from e

    async def get_collection_info(self, collection_name: str) -> CollectionInfo | None:
        """Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            CollectionInfo object or None if not found
        """
        try:
            return await self.async_client.get_collection(collection_name=collection_name)
        except Exception as e:
            logger.warning(
                "Failed to get collection info",
                collection_name=collection_name,
                error=str(e),
            )
            return None

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            True if deleted successfully
        """
        try:
            await self.async_client.delete_collection(collection_name=collection_name)
            logger.info("Collection deleted", collection_name=collection_name)
            return True
        except Exception as e:
            logger.error(
                "Failed to delete collection",
                collection_name=collection_name,
                error=str(e),
            )
            return False

    async def close(self) -> None:
        """Close client connections."""
        if self._async_client:
            await self._async_client.close()
            logger.info("Qdrant async client closed")
        if self._client:
            self._client.close()
            logger.info("Qdrant sync client closed")


# Global client instance (singleton pattern)
_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Get global Qdrant client instance (singleton).

    Returns:
        QdrantClient instance (renamed from QdrantClientWrapper in Sprint 25)
    """
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient()
    return _qdrant_client


@asynccontextmanager
async def get_qdrant_client_async() -> None:
    """Async context manager for Qdrant client.

    Usage:
        async with get_qdrant_client_async() as client:
            await client.health_check()
    """
    client = get_qdrant_client()
    try:
        yield client
    finally:
        # Connection is pooled, no need to close here
        pass


# ============================================================================
# Backward Compatibility Alias (Sprint 25 Feature 25.9)
# ============================================================================
# Deprecation period: Sprint 25-26
# Remove after all references are updated
QdrantClientWrapper = QdrantClient
