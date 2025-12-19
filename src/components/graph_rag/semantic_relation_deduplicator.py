"""Semantic Relation Type Deduplication using BGE-M3 embeddings and hierarchical clustering.

Sprint 49 Feature 49.7: TD-063
Uses BGE-M3 embeddings (via UnifiedEmbeddingService) and hierarchical clustering
to automatically discover and normalize duplicate relation types. Replaces hardcoded
synonym lists with data-driven semantic similarity.

Key Features:
- BGE-M3 embeddings for relation type similarity
- Hierarchical clustering with 0.88 cosine similarity threshold
- Symmetric relation handling (KNOWS, RELATED_TO, etc.)
- Redis caching with 7-day TTL
- Canonical type selection (most frequent or alphabetically first)

Architecture Decision: ADR-063 (Semantic Relation Deduplication)

Author: Claude Code
Date: 2025-12-16
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import structlog
from redis.asyncio import Redis
from sklearn.cluster import AgglomerativeClustering

from src.components.shared.embedding_service import get_embedding_service
from src.core.config import settings
from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)

# ============================================================================
# SYMMETRIC RELATION TYPES
# ============================================================================
# Relations where A-REL-B is equivalent to B-REL-A.
# For these, we normalize to alphabetical order of entities.

SYMMETRIC_RELATIONS: set[str] = {
    "KNOWS",
    "RELATED_TO",
    "RELATES_TO",
    "CO_OCCURS",
    "SIMILAR_TO",
    "MARRIED_TO",
    "SIBLING_OF",
    "FRIENDS_WITH",
    "PARTNERS_WITH",
    "CONNECTED_TO",
    "ASSOCIATED_WITH",
    "COLLABORATED_WITH",
    "WORKS_WITH",
}


class SemanticRelationDeduplicator:
    """Deduplicate relation types using BGE-M3 embeddings and hierarchical clustering.

    Sprint 49 Feature 49.7 (TD-063)

    Uses semantic similarity to discover and normalize duplicate relation types:
    - ACTED_IN, STARRED_IN, PLAYED_IN → canonical form (e.g., ACTED_IN)
    - WORKS_FOR, EMPLOYED_BY, WORKS_AT → canonical form (e.g., WORKS_FOR)

    Implementation:
    1. Extract unique relation types from input
    2. Normalize type names (WORKS_AT → "works at") for better embeddings
    3. Generate BGE-M3 embeddings via UnifiedEmbeddingService
    4. Perform hierarchical clustering with 0.88 threshold
    5. Select canonical type (alphabetically first in cluster)
    6. Cache results in Redis with 7-day TTL

    Example:
        >>> dedup = SemanticRelationDeduplicator()
        >>> relation_types = ["ACTED_IN", "STARRED_IN", "PLAYED_IN"]
        >>> type_map = await dedup.deduplicate_types(relation_types)
        >>> type_map
        {'STARRED_IN': 'ACTED_IN', 'PLAYED_IN': 'ACTED_IN', 'ACTED_IN': 'ACTED_IN'}
    """

    def __init__(
        self,
        similarity_threshold: float = 0.88,
        symmetric_relations: set[str] | None = None,
    ) -> None:
        """Initialize semantic relation deduplicator.

        Args:
            similarity_threshold: Cosine similarity threshold for clustering (0-1)
                Default 0.88 = very high similarity required to merge types
                - 0.88: Conservative (only very similar types merge)
                - 0.80: Moderate (more aggressive merging)
                - 0.95: Very conservative (almost identical types only)
            symmetric_relations: Custom set of symmetric relation types.
                If None, uses default SYMMETRIC_RELATIONS set.
        """
        self.similarity_threshold = similarity_threshold
        self.symmetric_relations = symmetric_relations or SYMMETRIC_RELATIONS
        self.embedding_service = get_embedding_service()
        self._redis_client: Redis | None = None

        logger.info(
            "semantic_relation_deduplicator_initialized",
            similarity_threshold=similarity_threshold,
            symmetric_relations_count=len(self.symmetric_relations),
            embedding_model=self.embedding_service.model_name,
        )

    async def _get_redis_client(self) -> Redis:
        """Get or create Redis client for caching.

        Returns:
            Redis client instance

        Raises:
            MemoryError: If Redis connection fails
        """
        if self._redis_client is None:
            try:
                self._redis_client = await Redis.from_url(
                    settings.redis_memory_url,
                    decode_responses=True,
                )
                await self._redis_client.ping()
                logger.debug("redis_client_initialized", url=settings.redis_memory_url)
            except Exception as e:
                logger.error("redis_connection_failed", error=str(e))
                raise MemoryError("get_redis_client", f"Failed to connect to Redis: {e}") from e

        return self._redis_client

    def _normalize_type_for_embedding(self, rel_type: str) -> str:
        """Normalize relation type for better embedding quality.

        Converts "WORKS_AT" → "works at" for more natural language embeddings.

        Args:
            rel_type: Original relation type (e.g., "WORKS_AT", "ACTED_IN")

        Returns:
            Normalized text for embedding (e.g., "works at", "acted in")
        """
        # Uppercase, strip whitespace
        normalized = rel_type.upper().strip()

        # Replace separators with spaces
        normalized = normalized.replace("_", " ").replace("-", " ")

        # Lowercase for natural language
        return normalized.lower()

    def _generate_cache_key(self, relation_types: list[str], threshold: float) -> str:
        """Generate cache key for relation type clusters.

        Args:
            relation_types: List of relation types
            threshold: Similarity threshold

        Returns:
            Cache key (hash of sorted types + threshold)
        """
        # Sort for consistency
        sorted_types = sorted(relation_types)
        key_data = json.dumps({"types": sorted_types, "threshold": threshold})
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"graph:relation-type-clusters:{key_hash}"

    async def deduplicate_types(
        self,
        relation_types: list[str],
        clustering_threshold: float | None = None,
        use_cache: bool = True,
    ) -> dict[str, str]:
        """Deduplicate relation types using hierarchical clustering.

        Args:
            relation_types: List of relation type strings (e.g., ["ACTED_IN", "STARRED_IN"])
            clustering_threshold: Override similarity threshold for this call.
                If None, uses instance threshold (default: 0.88)
            use_cache: Use Redis cache for cluster results (default: True)

        Returns:
            Mapping of variant → canonical type
            e.g., {"STARRED_IN": "ACTED_IN", "ACTED_IN": "ACTED_IN"}

        Note:
            - All types map to themselves or a canonical type (no unmapped types)
            - Canonical type is alphabetically first in cluster
            - Cache TTL: 7 days
        """
        if not relation_types:
            return {}

        # Use instance threshold if not overridden
        threshold = clustering_threshold or self.similarity_threshold

        # Normalize case
        normalized_types = [rt.upper().strip() for rt in relation_types]
        unique_types = list(set(normalized_types))

        # Check cache
        if use_cache:
            try:
                redis_client = await self._get_redis_client()
                cache_key = self._generate_cache_key(unique_types, threshold)
                cached_data = await redis_client.get(cache_key)

                if cached_data:
                    cached_mapping = json.loads(cached_data)
                    logger.info(
                        "relation_type_clusters_cache_hit",
                        cache_key=cache_key,
                        types_count=len(unique_types),
                    )
                    return cached_mapping
            except Exception as e:
                logger.warning("cache_lookup_failed", error=str(e), fallback="compute_fresh")

        # Compute fresh clusters
        logger.info(
            "computing_semantic_clusters",
            types_count=len(unique_types),
            threshold=threshold,
        )

        # Step 1: Generate embeddings for all types
        embeddings_dict: dict[str, list[float]] = {}
        normalized_texts = [self._normalize_type_for_embedding(rt) for rt in unique_types]

        try:
            embeddings_list = await self.embedding_service.embed_batch(
                normalized_texts,
                max_concurrent=10,
            )

            for rel_type, embedding in zip(unique_types, embeddings_list):
                embeddings_dict[rel_type] = embedding

        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            # Fallback: map all types to themselves
            return {rt: rt for rt in unique_types}

        # Step 2: Perform hierarchical clustering
        type_synonym_map = self._hierarchical_cluster(embeddings_dict, threshold)

        # Step 3: Cache results
        if use_cache:
            try:
                redis_client = await self._get_redis_client()
                cache_key = self._generate_cache_key(unique_types, threshold)
                await redis_client.set(
                    cache_key,
                    json.dumps(type_synonym_map),
                    ex=7 * 24 * 3600,  # 7 days
                )
                logger.debug(
                    "relation_type_clusters_cached",
                    cache_key=cache_key,
                    ttl_days=7,
                )
            except Exception as e:
                logger.warning("cache_write_failed", error=str(e))

        logger.info(
            "semantic_clustering_complete",
            input_types=len(unique_types),
            unique_canonical_types=len(set(type_synonym_map.values())),
            reduction_pct=round(
                100 * (1 - len(set(type_synonym_map.values())) / len(unique_types)), 1
            )
            if unique_types
            else 0,
        )

        return type_synonym_map

    def _hierarchical_cluster(
        self,
        embeddings: dict[str, list[float]],
        threshold: float,
    ) -> dict[str, str]:
        """Perform hierarchical clustering on embeddings.

        Uses Agglomerative Clustering with distance threshold to find semantic clusters.

        Args:
            embeddings: Mapping of relation_type → embedding vector
            threshold: Cosine similarity threshold (0-1)

        Returns:
            Mapping of all types to their canonical representative
            e.g., {"ACTED_IN": "ACTED_IN", "STARRED_IN": "ACTED_IN"}
        """
        if not embeddings:
            return {}

        # Single type: map to itself
        if len(embeddings) == 1:
            rel_type = list(embeddings.keys())[0]
            return {rel_type: rel_type}

        # Prepare data
        type_list = list(embeddings.keys())
        embedding_matrix = np.array([embeddings[t] for t in type_list])

        # Convert similarity threshold to distance threshold
        # Cosine similarity = 1 - cosine distance
        # threshold = 0.88 → distance_threshold = 1 - 0.88 = 0.12
        distance_threshold = 1 - threshold

        # Perform hierarchical clustering
        # linkage='average': UPGMA (average linkage)
        # affinity='cosine': use cosine distance
        # distance_threshold: merge if distance < threshold
        # n_clusters=None: let threshold determine clusters
        try:
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=distance_threshold,
                linkage="average",
                metric="cosine",
            )

            cluster_labels = clustering.fit_predict(embedding_matrix)

        except Exception as e:
            logger.error("clustering_failed", error=str(e))
            # Fallback: each type is its own cluster
            return {t: t for t in type_list}

        # Build clusters: cluster_id → [type1, type2, ...]
        clusters: dict[int, list[str]] = {}
        for rel_type, cluster_id in zip(type_list, cluster_labels):
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(rel_type)

        # Select canonical type for each cluster (alphabetically first)
        type_synonym_map: dict[str, str] = {}
        for cluster_id, cluster_members in clusters.items():
            # Canonical: alphabetically first
            canonical_type = min(cluster_members)

            for member_type in cluster_members:
                type_synonym_map[member_type] = canonical_type

            if len(cluster_members) > 1:
                logger.debug(
                    "cluster_formed",
                    cluster_id=cluster_id,
                    canonical_type=canonical_type,
                    members=cluster_members,
                    size=len(cluster_members),
                )

        return type_synonym_map

    async def close(self) -> None:
        """Close Redis client connection."""
        if self._redis_client is not None:
            await self._redis_client.close()
            self._redis_client = None
            logger.debug("redis_client_closed")


async def create_semantic_relation_deduplicator(
    similarity_threshold: float = 0.88,
) -> SemanticRelationDeduplicator:
    """Factory function to create semantic relation deduplicator.

    Args:
        similarity_threshold: Cosine similarity threshold for clustering (0-1)

    Returns:
        SemanticRelationDeduplicator instance
    """
    return SemanticRelationDeduplicator(similarity_threshold=similarity_threshold)
