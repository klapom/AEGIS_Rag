"""Multi-Vector Collection Manager for Qdrant.

Sprint 87 Feature 87.3: Qdrant Multi-Vector Collection Manager

This module provides management utilities for Qdrant collections that support
both dense (semantic) and sparse (lexical) vectors using named vectors.

Architecture:
    - Dense vectors: 1024D BGE-M3 embeddings (semantic search)
    - Sparse vectors: Token-level lexical weights (replaces BM25)
    - Both vectors stored in same point (guaranteed sync)
    - Server-side RRF fusion via Query API

Key Features:
    - Create collections with named vectors (dense + sparse)
    - Check if collection supports sparse vectors
    - Blue-green deployment (aliases for zero-downtime migration)
    - Collection introspection and metadata

Example:
    >>> manager = get_multi_vector_manager()
    >>> await manager.create_multi_vector_collection("aegis_chunks_v2")
    >>> has_sparse = await manager.collection_has_sparse("aegis_chunks_v2")
    >>> info = await manager.get_collection_info("aegis_chunks_v2")
    >>> await manager.create_alias("aegis_chunks", "aegis_chunks_v2")
    >>> await manager.switch_alias("aegis_chunks", "aegis_chunks_v3")

See Also:
    - Sprint 87 Plan: docs/sprints/SPRINT_87_PLAN.md
    - ADR-042: BGE-M3 Native Hybrid Search
    - TD-103: BM25 Index Desync
"""

from typing import Any

import structlog
from qdrant_client.models import (
    CollectionInfo,
    Distance,
    SparseIndexParams,
    SparseVectorParams,
    VectorParams,
)
from tenacity import retry, stop_after_attempt, wait_exponential

from src.components.vector_search.qdrant_client import (  # type: ignore[attr-defined]
    QdrantClient,
    get_qdrant_client,
)
from src.core.exceptions import VectorSearchError

logger = structlog.get_logger(__name__)


class MultiVectorCollectionManager:
    """Manager for Qdrant collections with named vectors (dense + sparse).

    Sprint 87 Feature 87.3: Provides management utilities for collections that
    support both dense (1024D BGE-M3) and sparse (lexical) vectors.

    This manager enables:
    1. Creating collections with dual vector support
    2. Inspecting collection capabilities (has sparse?)
    3. Blue-green deployment via aliases
    4. Zero-downtime migrations

    Architecture:
        Collection Schema:
            vectors:
                dense:
                    size: 1024
                    distance: Cosine
                    on_disk: true
            sparse_vectors:
                sparse:
                    index:
                        on_disk: true

    Attributes:
        client: QdrantClient instance for database operations
    """

    def __init__(self, client: QdrantClient | None = None) -> None:
        """Initialize multi-vector collection manager.

        Args:
            client: Optional QdrantClient instance. If None, uses global client.
        """
        self.client = client or get_qdrant_client()
        logger.info("MultiVectorCollectionManager initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def create_multi_vector_collection(
        self,
        collection_name: str,
        dense_dim: int = 1024,
        on_disk: bool = True,
        shard_number: int | None = None,
        replication_factor: int | None = None,
    ) -> bool:
        """Create collection with named vectors (dense + sparse).

        Sprint 87 Feature 87.3: Creates a Qdrant collection that supports both
        dense (semantic) and sparse (lexical) vectors in the same point.

        This schema enables:
        - Native hybrid search via Query API
        - Server-side RRF fusion (no Python-side merge)
        - Guaranteed synchronization (both vectors in same point)

        Args:
            collection_name: Name of collection to create
            dense_dim: Dimension of dense vectors (default: 1024 for BGE-M3)
            on_disk: Store vectors on disk to save RAM (default: True)
            shard_number: Number of shards (default: None = auto)
            replication_factor: Replication factor (default: None = 1)

        Returns:
            True if collection created successfully

        Raises:
            VectorSearchError: If creation fails

        Example:
            >>> manager = get_multi_vector_manager()
            >>> await manager.create_multi_vector_collection("aegis_chunks_v2")
            >>> # Collection now supports both dense and sparse vectors
        """
        try:
            # Check if collection already exists
            collections = await self.client.async_client.get_collections()  # type: ignore[attr-defined]
            if collection_name in [c.name for c in collections.collections]:
                logger.info(
                    "Collection already exists",
                    collection_name=collection_name,
                )
                return True

            # Create collection with named vectors
            await self.client.async_client.create_collection(  # type: ignore[attr-defined]
                collection_name=collection_name,
                vectors_config={
                    "dense": VectorParams(
                        size=dense_dim,
                        distance=Distance.COSINE,
                        on_disk=on_disk,
                    ),
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        index=SparseIndexParams(
                            on_disk=on_disk,
                        ),
                    ),
                },
                shard_number=shard_number,
                replication_factor=replication_factor,
                # Optimized settings for large collections
                optimizers_config={
                    "memmap_threshold": 20000,  # Use mmap for >20K points
                },
                on_disk_payload=True,  # Store payload on disk
            )

            logger.info(
                "Multi-vector collection created successfully",
                collection_name=collection_name,
                dense_dim=dense_dim,
                on_disk=on_disk,
                shard_number=shard_number,
                replication_factor=replication_factor,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to create multi-vector collection",
                collection_name=collection_name,
                error=str(e),
            )
            raise VectorSearchError(
                query="", reason=f"Failed to create multi-vector collection: {e}"
            ) from e

    async def collection_has_sparse(self, collection_name: str) -> bool:
        """Check if collection supports sparse vectors.

        Sprint 87 Feature 87.3: Utility to determine if a collection has been
        migrated to the multi-vector schema (has sparse vectors).

        Args:
            collection_name: Collection to check

        Returns:
            True if collection has sparse vectors configured, False otherwise

        Example:
            >>> manager = get_multi_vector_manager()
            >>> has_sparse = await manager.collection_has_sparse("aegis_chunks_v2")
            >>> if has_sparse:
            ...     print("Collection supports hybrid search!")
        """
        try:
            info = await self.get_collection_info(collection_name)
            if info is None:
                logger.warning(
                    "Collection not found",
                    collection_name=collection_name,
                )
                return False

            # Check if sparse_vectors exists and has "sparse" key
            # Note: Qdrant API returns sparse vectors in info.config.params.sparse_vectors
            has_sparse = (
                hasattr(info.config, "params")
                and hasattr(info.config.params, "sparse_vectors")
                and info.config.params.sparse_vectors is not None
                and "sparse" in info.config.params.sparse_vectors
            )

            logger.debug(
                "Collection sparse check",
                collection_name=collection_name,
                has_sparse=has_sparse,
            )
            return has_sparse

        except Exception as e:
            logger.error(
                "Failed to check sparse support",
                collection_name=collection_name,
                error=str(e),
            )
            return False

    async def get_collection_info(self, collection_name: str) -> CollectionInfo | None:
        """Get detailed information about a collection.

        Sprint 87 Feature 87.3: Retrieves collection metadata including:
        - Vector configurations (dense + sparse)
        - Point count
        - Shard configuration
        - Index status

        Args:
            collection_name: Name of collection

        Returns:
            CollectionInfo object or None if not found

        Example:
            >>> manager = get_multi_vector_manager()
            >>> info = await manager.get_collection_info("aegis_chunks_v2")
            >>> print(f"Points: {info.points_count}")
            >>> print(f"Vectors: {info.config.params.vectors}")
        """
        try:
            info = await self.client.async_client.get_collection(  # type: ignore[attr-defined]
                collection_name=collection_name
            )
            logger.debug(
                "Retrieved collection info",
                collection_name=collection_name,
                points_count=info.points_count,
                has_sparse=(
                    hasattr(info.config, "sparse_vectors_config")
                    and info.config.sparse_vectors_config is not None
                ),
            )
            return info  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning(
                "Failed to get collection info",
                collection_name=collection_name,
                error=str(e),
            )
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection.

        Sprint 87 Feature 87.3: Permanently deletes a collection and all its data.

        Warning:
            This operation is IRREVERSIBLE. All vectors, payloads, and indices
            will be permanently deleted.

        Args:
            collection_name: Name of collection to delete

        Returns:
            True if deleted successfully, False otherwise

        Example:
            >>> manager = get_multi_vector_manager()
            >>> # Delete old collection after migration
            >>> await manager.delete_collection("aegis_chunks_v1_backup")
        """
        try:
            await self.client.async_client.delete_collection(  # type: ignore[attr-defined]
                collection_name=collection_name
            )
            logger.info("Collection deleted successfully", collection_name=collection_name)
            return True
        except Exception as e:
            logger.error(
                "Failed to delete collection",
                collection_name=collection_name,
                error=str(e),
            )
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def create_alias(self, alias_name: str, collection_name: str) -> bool:
        """Create an alias pointing to a collection.

        Sprint 87 Feature 87.3: Creates a named alias for blue-green deployments.

        Aliases enable zero-downtime migrations:
        1. Create new collection (aegis_chunks_v2)
        2. Migrate data
        3. Create alias (aegis_chunks → v2)
        4. Atomic switch via switch_alias()

        Args:
            alias_name: Name of alias (e.g., "aegis_chunks")
            collection_name: Target collection (e.g., "aegis_chunks_v2")

        Returns:
            True if alias created successfully

        Raises:
            VectorSearchError: If creation fails

        Example:
            >>> manager = get_multi_vector_manager()
            >>> # Point production alias to new collection
            >>> await manager.create_alias("aegis_chunks", "aegis_chunks_v2")
        """
        try:
            await self.client.async_client.update_collection_aliases(  # type: ignore[attr-defined]
                change_aliases_operations=[
                    {
                        "create_alias": {
                            "alias_name": alias_name,
                            "collection_name": collection_name,
                        }
                    }
                ]
            )
            logger.info(
                "Alias created successfully",
                alias_name=alias_name,
                collection_name=collection_name,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to create alias",
                alias_name=alias_name,
                collection_name=collection_name,
                error=str(e),
            )
            raise VectorSearchError(query="", reason=f"Failed to create alias: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def switch_alias(self, alias_name: str, new_collection: str) -> bool:
        """Atomically switch an alias to a different collection.

        Sprint 87 Feature 87.3: Atomic alias switch for zero-downtime migrations.

        This operation is:
        - Atomic: No queries are dropped during switch
        - Safe: Rollback by switching back to old collection
        - Fast: Instant switch, no data movement

        Args:
            alias_name: Alias to switch (e.g., "aegis_chunks")
            new_collection: New target collection (e.g., "aegis_chunks_v3")

        Returns:
            True if switch successful

        Raises:
            VectorSearchError: If switch fails

        Example:
            >>> manager = get_multi_vector_manager()
            >>> # Switch production to v3 (instant, zero-downtime)
            >>> await manager.switch_alias("aegis_chunks", "aegis_chunks_v3")
            >>> # Rollback if needed
            >>> await manager.switch_alias("aegis_chunks", "aegis_chunks_v2")
        """
        try:
            # Use rename_alias for atomic switch
            await self.client.async_client.update_collection_aliases(  # type: ignore[attr-defined]
                change_aliases_operations=[
                    {
                        "rename_alias": {
                            "old_alias_name": alias_name,
                            "new_alias_name": alias_name,
                            "new_collection_name": new_collection,
                        }
                    }
                ]
            )
            logger.info(
                "Alias switched successfully",
                alias_name=alias_name,
                new_collection=new_collection,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to switch alias",
                alias_name=alias_name,
                new_collection=new_collection,
                error=str(e),
            )
            raise VectorSearchError(query="", reason=f"Failed to switch alias: {e}") from e

    async def list_collections(self) -> list[dict[str, Any]]:
        """List all collections with metadata.

        Sprint 87 Feature 87.3: Retrieves list of all collections with key metadata
        including sparse vector support.

        Returns:
            List of collection metadata dicts:
                [
                    {
                        "name": "aegis_chunks_v2",
                        "points_count": 10250,
                        "has_sparse": True,
                        "dense_dim": 1024,
                    },
                    ...
                ]

        Example:
            >>> manager = get_multi_vector_manager()
            >>> collections = await manager.list_collections()
            >>> for col in collections:
            ...     print(f"{col['name']}: {col['points_count']} points, "
            ...           f"sparse={col['has_sparse']}")
        """
        try:
            response = await self.client.async_client.get_collections()  # type: ignore[attr-defined]
            collections = []

            for collection in response.collections:
                info = await self.get_collection_info(collection.name)
                if info is None:
                    continue

                # Extract metadata
                has_sparse = (
                    hasattr(info.config, "sparse_vectors_config")
                    and info.config.sparse_vectors_config is not None
                    and "sparse" in info.config.sparse_vectors_config
                )

                # Get dense vector dimension
                dense_dim = None
                if hasattr(info.config.params, "vectors"):
                    if isinstance(info.config.params.vectors, dict):
                        dense_config = info.config.params.vectors.get("dense")
                        if dense_config:
                            dense_dim = dense_config.size
                    else:
                        # Legacy single-vector collection
                        if info.config.params.vectors is not None:
                            dense_dim = info.config.params.vectors.size

                collections.append(
                    {
                        "name": collection.name,
                        "points_count": info.points_count,
                        "has_sparse": has_sparse,
                        "dense_dim": dense_dim,
                    }
                )

            logger.debug(
                "Listed collections",
                total_collections=len(collections),
                multi_vector_count=sum(1 for c in collections if c["has_sparse"]),
            )
            return collections

        except Exception as e:
            logger.error("Failed to list collections", error=str(e))
            return []


# ============================================================================
# Global Singleton
# ============================================================================

_multi_vector_manager: MultiVectorCollectionManager | None = None


def get_multi_vector_manager() -> MultiVectorCollectionManager:
    """Get global MultiVectorCollectionManager instance (singleton).

    Sprint 87 Feature 87.3: Singleton pattern for collection manager.

    Returns:
        MultiVectorCollectionManager instance

    Example:
        >>> manager = get_multi_vector_manager()
        >>> await manager.create_multi_vector_collection("aegis_chunks_v2")
    """
    global _multi_vector_manager
    if _multi_vector_manager is None:
        _multi_vector_manager = MultiVectorCollectionManager()
    return _multi_vector_manager
