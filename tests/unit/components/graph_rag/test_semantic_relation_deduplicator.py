"""Unit tests for SemanticRelationDeduplicator (Sprint 49 Feature 49.7).

Tests semantic relation type deduplication using BGE-M3 embeddings and hierarchical clustering.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.components.graph_rag.semantic_relation_deduplicator import (
    SYMMETRIC_RELATIONS,
    SemanticRelationDeduplicator,
    create_semantic_relation_deduplicator,
)


class TestSemanticRelationDeduplicator:
    """Test suite for SemanticRelationDeduplicator."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock UnifiedEmbeddingService."""
        service = MagicMock()
        service.model_name = "bge-m3"

        # Mock embeddings: similar types get similar vectors
        async def mock_embed_batch(texts, max_concurrent=10):
            embeddings = []
            for text in texts:
                # Generate deterministic embeddings based on text
                # Similar relation types get similar embeddings (with small noise for realism)
                if "act" in text or "star" in text or "play" in text:
                    # ACTED_IN, STARRED_IN, PLAYED_IN cluster
                    # Use very small noise (0.01) to ensure clustering works
                    base = np.array([1.0, 0.0, 0.0] + [0.0] * 1021)
                    noise = np.random.RandomState(hash(text) % 2**32).randn(1024) * 0.01
                    embeddings.append((base + noise).tolist())
                elif "direct" in text or "helm" in text:
                    # DIRECTED, HELMED cluster
                    base = np.array([0.0, 1.0, 0.0] + [0.0] * 1021)
                    noise = np.random.RandomState(hash(text) % 2**32).randn(1024) * 0.01
                    embeddings.append((base + noise).tolist())
                elif "work" in text or "employ" in text:
                    # WORKS_FOR, EMPLOYED_BY cluster
                    base = np.array([0.0, 0.0, 1.0] + [0.0] * 1021)
                    noise = np.random.RandomState(hash(text) % 2**32).randn(1024) * 0.01
                    embeddings.append((base + noise).tolist())
                else:
                    # Unique embedding for other types
                    seed = hash(text) % 2**32
                    embeddings.append(np.random.RandomState(seed).randn(1024).tolist())
            return embeddings

        service.embed_batch = AsyncMock(side_effect=mock_embed_batch)
        return service

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        redis = AsyncMock()
        redis.ping = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        redis.close = AsyncMock()
        return redis

    @pytest.fixture
    async def deduplicator(self, mock_embedding_service):
        """Create deduplicator with mocked embedding service."""
        with patch(
            "src.components.graph_rag.semantic_relation_deduplicator.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            dedup = SemanticRelationDeduplicator(similarity_threshold=0.88)
            yield dedup
            await dedup.close()

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test deduplicator initialization."""
        mock_service = MagicMock()
        mock_service.model_name = "bge-m3"

        with patch(
            "src.components.graph_rag.semantic_relation_deduplicator.get_embedding_service",
            return_value=mock_service,
        ):
            dedup = SemanticRelationDeduplicator(similarity_threshold=0.88)

            assert dedup.similarity_threshold == 0.88
            assert dedup.symmetric_relations == SYMMETRIC_RELATIONS
            assert dedup.embedding_service == mock_service

    @pytest.mark.asyncio
    async def test_normalize_type_for_embedding(self, deduplicator):
        """Test relation type normalization for embeddings."""
        # Test case conversion and separator replacement
        assert deduplicator._normalize_type_for_embedding("WORKS_AT") == "works at"
        assert deduplicator._normalize_type_for_embedding("ACTED-IN") == "acted in"
        assert deduplicator._normalize_type_for_embedding("works_for") == "works for"
        assert deduplicator._normalize_type_for_embedding("  DIRECTED  ") == "directed"

    @pytest.mark.asyncio
    async def test_generate_cache_key(self, deduplicator):
        """Test cache key generation."""
        types1 = ["ACTED_IN", "DIRECTED", "WORKS_FOR"]
        types2 = ["WORKS_FOR", "DIRECTED", "ACTED_IN"]  # Different order

        key1 = deduplicator._generate_cache_key(types1, 0.88)
        key2 = deduplicator._generate_cache_key(types2, 0.88)

        # Same types (different order) should generate same key
        assert key1 == key2

        # Different threshold should generate different key
        key3 = deduplicator._generate_cache_key(types1, 0.90)
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_deduplicate_types_empty(self, deduplicator):
        """Test deduplication with empty input."""
        result = await deduplicator.deduplicate_types([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_deduplicate_types_single(self, deduplicator, mock_redis_client):
        """Test deduplication with single type."""
        with patch.object(deduplicator, "_get_redis_client", return_value=mock_redis_client):
            result = await deduplicator.deduplicate_types(["ACTED_IN"], use_cache=False)

            # Single type maps to itself
            assert result == {"ACTED_IN": "ACTED_IN"}

    @pytest.mark.asyncio
    async def test_deduplicate_types_similar_cluster(self, deduplicator, mock_redis_client):
        """Test deduplication with semantically similar types."""
        with patch.object(deduplicator, "_get_redis_client", return_value=mock_redis_client):
            # These should cluster together (similar embeddings)
            types = ["ACTED_IN", "STARRED_IN", "PLAYED_IN"]
            result = await deduplicator.deduplicate_types(types, use_cache=False)

            # All should map to alphabetically first (ACTED_IN)
            assert result["ACTED_IN"] == "ACTED_IN"
            assert result["STARRED_IN"] == "ACTED_IN"
            assert result["PLAYED_IN"] == "ACTED_IN"

    @pytest.mark.asyncio
    async def test_deduplicate_types_multiple_clusters(self, deduplicator, mock_redis_client):
        """Test deduplication with multiple distinct clusters."""
        with patch.object(deduplicator, "_get_redis_client", return_value=mock_redis_client):
            # Two distinct clusters
            types = ["ACTED_IN", "STARRED_IN", "DIRECTED", "HELMED"]
            result = await deduplicator.deduplicate_types(types, use_cache=False)

            # Acting cluster
            assert result["ACTED_IN"] == "ACTED_IN"
            assert result["STARRED_IN"] == "ACTED_IN"

            # Directing cluster
            assert result["DIRECTED"] == "DIRECTED"
            assert result["HELMED"] == "DIRECTED"

    @pytest.mark.asyncio
    async def test_deduplicate_types_case_insensitive(self, deduplicator, mock_redis_client):
        """Test that deduplication is case-insensitive."""
        with patch.object(deduplicator, "_get_redis_client", return_value=mock_redis_client):
            types = ["ACTED_IN", "acted_in", "Acted_In"]
            result = await deduplicator.deduplicate_types(types, use_cache=False)

            # All variants normalized to uppercase
            assert result["ACTED_IN"] == "ACTED_IN"
            assert len(result) == 1  # Duplicates removed

    @pytest.mark.asyncio
    async def test_deduplicate_types_with_cache_hit(self, deduplicator, mock_redis_client):
        """Test deduplication with Redis cache hit."""
        cached_mapping = {"ACTED_IN": "ACTED_IN", "STARRED_IN": "ACTED_IN"}
        mock_redis_client.get.return_value = json.dumps(cached_mapping)

        with patch.object(deduplicator, "_get_redis_client", return_value=mock_redis_client):
            result = await deduplicator.deduplicate_types(
                ["ACTED_IN", "STARRED_IN"],
                use_cache=True,
            )

            assert result == cached_mapping
            mock_redis_client.get.assert_called_once()
            # Embedding service should NOT be called (cache hit)
            assert not deduplicator.embedding_service.embed_batch.called

    @pytest.mark.asyncio
    async def test_deduplicate_types_cache_miss(self, deduplicator, mock_redis_client):
        """Test deduplication with Redis cache miss."""
        mock_redis_client.get.return_value = None

        with patch.object(deduplicator, "_get_redis_client", return_value=mock_redis_client):
            types = ["ACTED_IN", "STARRED_IN"]
            result = await deduplicator.deduplicate_types(types, use_cache=True)

            # Cache miss: should compute fresh
            mock_redis_client.get.assert_called_once()
            deduplicator.embedding_service.embed_batch.assert_called_once()

            # Should write to cache
            mock_redis_client.set.assert_called_once()
            call_args = mock_redis_client.set.call_args
            assert call_args[1]["ex"] == 7 * 24 * 3600  # 7 days TTL

    @pytest.mark.asyncio
    async def test_deduplicate_types_no_cache(self, deduplicator, mock_redis_client):
        """Test deduplication with caching disabled."""
        with patch.object(deduplicator, "_get_redis_client", return_value=mock_redis_client):
            types = ["ACTED_IN", "STARRED_IN"]
            result = await deduplicator.deduplicate_types(types, use_cache=False)

            # Should not touch Redis
            assert not mock_redis_client.get.called
            assert not mock_redis_client.set.called

            # Should compute embeddings
            deduplicator.embedding_service.embed_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_deduplicate_types_custom_threshold(self, deduplicator, mock_redis_client):
        """Test deduplication with custom clustering threshold."""
        with patch.object(deduplicator, "_get_redis_client", return_value=mock_redis_client):
            types = ["ACTED_IN", "STARRED_IN"]

            # Very high threshold (0.95): might not cluster
            result_high = await deduplicator.deduplicate_types(
                types,
                clustering_threshold=0.95,
                use_cache=False,
            )

            # Lower threshold (0.70): more likely to cluster
            result_low = await deduplicator.deduplicate_types(
                types,
                clustering_threshold=0.70,
                use_cache=False,
            )

            # Both should produce valid mappings
            assert len(result_high) > 0
            assert len(result_low) > 0

    @pytest.mark.asyncio
    async def test_deduplicate_types_embedding_failure(self, deduplicator, mock_redis_client):
        """Test deduplication when embedding generation fails."""
        # Mock embedding failure
        deduplicator.embedding_service.embed_batch = AsyncMock(
            side_effect=Exception("Embedding service error")
        )

        with patch.object(deduplicator, "_get_redis_client", return_value=mock_redis_client):
            types = ["ACTED_IN", "STARRED_IN"]
            result = await deduplicator.deduplicate_types(types, use_cache=False)

            # Should fallback: each type maps to itself
            assert result == {"ACTED_IN": "ACTED_IN", "STARRED_IN": "STARRED_IN"}

    @pytest.mark.asyncio
    async def test_hierarchical_cluster_empty(self, deduplicator):
        """Test clustering with empty embeddings."""
        result = deduplicator._hierarchical_cluster({}, 0.88)
        assert result == {}

    @pytest.mark.asyncio
    async def test_hierarchical_cluster_single(self, deduplicator):
        """Test clustering with single embedding."""
        embeddings = {"ACTED_IN": [0.1] * 1024}
        result = deduplicator._hierarchical_cluster(embeddings, 0.88)

        assert result == {"ACTED_IN": "ACTED_IN"}

    @pytest.mark.asyncio
    async def test_hierarchical_cluster_similar_types(self, deduplicator):
        """Test clustering with very similar embeddings."""
        # Create very similar embeddings (high cosine similarity)
        base_embedding = [1.0] * 512 + [0.0] * 512
        noise1 = np.random.RandomState(42).randn(1024) * 0.01
        noise2 = np.random.RandomState(43).randn(1024) * 0.01

        embeddings = {
            "ACTED_IN": (np.array(base_embedding) + noise1).tolist(),
            "STARRED_IN": (np.array(base_embedding) + noise2).tolist(),
        }

        result = deduplicator._hierarchical_cluster(embeddings, 0.88)

        # Should cluster together (high similarity)
        canonical = result["ACTED_IN"]
        assert result["STARRED_IN"] == canonical

    @pytest.mark.asyncio
    async def test_hierarchical_cluster_distinct_types(self, deduplicator):
        """Test clustering with distinct embeddings."""
        # Create orthogonal embeddings (low similarity)
        embeddings = {
            "ACTED_IN": [1.0] * 512 + [0.0] * 512,
            "DIRECTED": [0.0] * 512 + [1.0] * 512,
        }

        result = deduplicator._hierarchical_cluster(embeddings, 0.88)

        # Should NOT cluster together (low similarity)
        assert result["ACTED_IN"] == "ACTED_IN"
        assert result["DIRECTED"] == "DIRECTED"

    @pytest.mark.asyncio
    async def test_symmetric_relations_defined(self):
        """Test that symmetric relations are properly defined."""
        assert len(SYMMETRIC_RELATIONS) > 0
        assert "KNOWS" in SYMMETRIC_RELATIONS
        assert "RELATED_TO" in SYMMETRIC_RELATIONS
        assert "MARRIED_TO" in SYMMETRIC_RELATIONS

    @pytest.mark.asyncio
    async def test_custom_symmetric_relations(self, mock_embedding_service):
        """Test deduplicator with custom symmetric relations."""
        custom_symmetric = {"CUSTOM_REL_1", "CUSTOM_REL_2"}

        with patch(
            "src.components.graph_rag.semantic_relation_deduplicator.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            dedup = SemanticRelationDeduplicator(
                similarity_threshold=0.88,
                symmetric_relations=custom_symmetric,
            )

            assert dedup.symmetric_relations == custom_symmetric
            assert "CUSTOM_REL_1" in dedup.symmetric_relations

    @pytest.mark.asyncio
    async def test_factory_function(self, mock_embedding_service):
        """Test factory function creates deduplicator correctly."""
        with patch(
            "src.components.graph_rag.semantic_relation_deduplicator.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            dedup = await create_semantic_relation_deduplicator(similarity_threshold=0.90)

            assert isinstance(dedup, SemanticRelationDeduplicator)
            assert dedup.similarity_threshold == 0.90

    @pytest.mark.asyncio
    async def test_close(self, deduplicator):
        """Test closing Redis client."""
        mock_redis = AsyncMock()
        deduplicator._redis_client = mock_redis

        await deduplicator.close()

        mock_redis.close.assert_called_once()
        assert deduplicator._redis_client is None
