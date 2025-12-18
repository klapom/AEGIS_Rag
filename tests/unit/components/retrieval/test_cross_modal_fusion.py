"""Unit tests for Cross-Modal Fusion.

Sprint 51 - Feature 51.7: Maximum Hybrid Search Foundation

Tests for aligning entity-based and chunk-based retrieval results via MENTIONED_IN.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.retrieval.cross_modal_fusion import (
    _get_entity_chunk_mentions,
    cross_modal_fusion,
    get_chunks_for_entities,
)


class TestCrossModalFusion:
    """Tests for cross_modal_fusion() main function."""

    @pytest.mark.asyncio
    async def test_fusion_with_empty_inputs(self):
        """Test fusion handles empty inputs gracefully."""
        # Empty chunks
        result = await cross_modal_fusion(
            chunk_ranking=[],
            entity_names=["Amsterdam"],
        )
        assert result == []

        # Empty entities
        result = await cross_modal_fusion(
            chunk_ranking=[{"id": "chunk1", "rrf_score": 0.8}],
            entity_names=[],
        )
        assert len(result) == 1
        assert result[0]["id"] == "chunk1"

    @pytest.mark.asyncio
    async def test_fusion_with_no_mentions(self):
        """Test fusion when no entities are mentioned in chunks."""
        chunks = [
            {"id": "chunk1", "rrf_score": 0.9, "rank": 1},
            {"id": "chunk2", "rrf_score": 0.8, "rank": 2},
        ]

        with patch(
            "src.components.retrieval.cross_modal_fusion._get_entity_chunk_mentions",
            return_value={},
        ):
            result = await cross_modal_fusion(
                chunk_ranking=chunks,
                entity_names=["Amsterdam", "Netherlands"],
            )

            # Should return original ranking (no boosts applied)
            assert len(result) == 2
            assert result[0]["id"] == "chunk1"

    @pytest.mark.asyncio
    async def test_fusion_with_entity_boosts(self):
        """Test fusion applies entity boosts correctly."""
        chunks = [
            {"id": "chunk1", "rrf_score": 0.7, "rank": 1},
            {"id": "chunk2", "rrf_score": 0.6, "rank": 2},
            {"id": "chunk3", "rrf_score": 0.5, "rank": 3},
        ]

        # Mock: Amsterdam mentioned in chunk2, Netherlands in chunk1 and chunk2
        entity_chunk_map = {
            "Amsterdam": ["chunk2"],
            "Netherlands": ["chunk1", "chunk2"],
        }

        with patch(
            "src.components.retrieval.cross_modal_fusion._get_entity_chunk_mentions",
            return_value=entity_chunk_map,
        ):
            result = await cross_modal_fusion(
                chunk_ranking=chunks,
                entity_names=["Amsterdam", "Netherlands"],
                alpha=0.3,
                k=60,
            )

            # Check boosts were applied
            assert len(result) == 3
            assert all("entity_boost" in chunk for chunk in result)
            assert all("final_score" in chunk for chunk in result)

            # chunk2 should have highest boost (mentions both entities)
            chunk2_result = next(c for c in result if c["id"] == "chunk2")
            assert chunk2_result["entity_boost"] > 0

            # chunk1 should have some boost (mentions Netherlands)
            chunk1_result = next(c for c in result if c["id"] == "chunk1")
            assert chunk1_result["entity_boost"] > 0

            # chunk3 should have no boost
            chunk3_result = next(c for c in result if c["id"] == "chunk3")
            assert chunk3_result["entity_boost"] == 0

            # Results should be re-ranked by final_score
            assert result[0]["final_rank"] == 1

    @pytest.mark.asyncio
    async def test_fusion_entity_importance_by_rank(self):
        """Test that entity importance is calculated by rank (RRF formula)."""
        chunks = [{"id": "chunk1", "rrf_score": 0.5, "rank": 1}]

        # First entity (rank=1) should have higher score than second (rank=2)
        entity_chunk_map = {
            "Amsterdam": ["chunk1"],
            "Netherlands": ["chunk1"],
        }

        with patch(
            "src.components.retrieval.cross_modal_fusion._get_entity_chunk_mentions",
            return_value=entity_chunk_map,
        ):
            result = await cross_modal_fusion(
                chunk_ranking=chunks,
                entity_names=["Amsterdam", "Netherlands"],  # Order matters!
                alpha=1.0,  # Full weight for testing
                k=60,
            )

            chunk1 = result[0]
            # Amsterdam (rank 1): 1/(60+1) = 0.0164
            # Netherlands (rank 2): 1/(60+2) = 0.0161
            # Total boost: ~0.0325
            assert chunk1["entity_boost"] > 0.03
            assert chunk1["entity_boost"] < 0.04


class TestGetEntityChunkMentions:
    """Tests for _get_entity_chunk_mentions() Neo4j query function."""

    @pytest.mark.asyncio
    async def test_get_mentions_empty_entities(self):
        """Test querying with empty entity list."""
        mock_neo4j = MagicMock()
        result = await _get_entity_chunk_mentions(
            entity_names=[],
            neo4j_client=mock_neo4j,
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_mentions_with_namespace_filter(self):
        """Test querying with namespace filtering."""
        mock_neo4j = MagicMock()
        mock_neo4j.execute_read = AsyncMock(
            return_value=[
                {"entity_name": "Amsterdam", "chunk_ids": ["chunk1", "chunk2"]},
                {"entity_name": "Netherlands", "chunk_ids": ["chunk1"]},
            ]
        )

        result = await _get_entity_chunk_mentions(
            entity_names=["Amsterdam", "Netherlands"],
            neo4j_client=mock_neo4j,
            allowed_namespaces=["default", "general"],
        )

        assert len(result) == 2
        assert result["Amsterdam"] == ["chunk1", "chunk2"]
        assert result["Netherlands"] == ["chunk1"]

        # Verify Cypher query included namespace filter
        call_args = mock_neo4j.execute_read.call_args
        cypher_query = call_args[0][0]
        assert "namespace_id IN" in cypher_query

    @pytest.mark.asyncio
    async def test_get_mentions_no_namespace_filter(self):
        """Test querying without namespace filtering."""
        mock_neo4j = MagicMock()
        mock_neo4j.execute_read = AsyncMock(return_value=[])

        result = await _get_entity_chunk_mentions(
            entity_names=["Amsterdam"],
            neo4j_client=mock_neo4j,
            allowed_namespaces=None,
        )

        # Verify Cypher query did NOT include namespace filter
        call_args = mock_neo4j.execute_read.call_args
        cypher_query = call_args[0][0]
        assert "namespace_id IN" not in cypher_query

    @pytest.mark.asyncio
    async def test_get_mentions_handles_neo4j_error(self):
        """Test error handling when Neo4j query fails."""
        mock_neo4j = MagicMock()
        mock_neo4j.execute_read = AsyncMock(side_effect=Exception("Neo4j connection failed"))

        result = await _get_entity_chunk_mentions(
            entity_names=["Amsterdam"],
            neo4j_client=mock_neo4j,
        )

        # Should return empty dict on error (graceful degradation)
        assert result == {}


class TestGetChunksForEntities:
    """Tests for get_chunks_for_entities() direct entity-based retrieval."""

    @pytest.mark.asyncio
    async def test_get_chunks_empty_entities(self):
        """Test retrieving chunks with empty entity list."""
        result = await get_chunks_for_entities(entity_names=[])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_chunks_for_entities_success(self):
        """Test successful chunk retrieval for entities."""
        mock_neo4j = MagicMock()
        mock_neo4j.execute_read = AsyncMock(
            return_value=[
                {
                    "id": "chunk1",
                    "text": "Amsterdam is the capital",
                    "document_id": "doc1",
                    "namespace_id": "default",
                    "mentioned_entities": ["Amsterdam", "Netherlands"],
                    "score": 2,
                },
                {
                    "id": "chunk2",
                    "text": "Netherlands is in Europe",
                    "document_id": "doc1",
                    "namespace_id": "default",
                    "mentioned_entities": ["Netherlands"],
                    "score": 1,
                },
            ]
        )

        result = await get_chunks_for_entities(
            entity_names=["Amsterdam", "Netherlands"],
            neo4j_client=mock_neo4j,
            top_k=20,
        )

        assert len(result) == 2
        assert result[0]["id"] == "chunk1"
        assert result[0]["search_type"] == "entity_mention"
        assert result[0]["mentioned_entities"] == ["Amsterdam", "Netherlands"]
        assert result[0]["score"] == 2  # Mentions 2 entities
        assert result[0]["rank"] == 1

        assert result[1]["score"] == 1  # Mentions 1 entity

    @pytest.mark.asyncio
    async def test_get_chunks_with_namespace_filter(self):
        """Test chunk retrieval with namespace filtering."""
        mock_neo4j = MagicMock()
        mock_neo4j.execute_read = AsyncMock(return_value=[])

        await get_chunks_for_entities(
            entity_names=["Amsterdam"],
            neo4j_client=mock_neo4j,
            allowed_namespaces=["default"],
        )

        # Verify Cypher included namespace filter
        call_args = mock_neo4j.execute_read.call_args
        cypher_query = call_args[0][0]
        assert "namespace_id IN" in cypher_query

    @pytest.mark.asyncio
    async def test_get_chunks_handles_error(self):
        """Test error handling when Neo4j query fails."""
        mock_neo4j = MagicMock()
        mock_neo4j.execute_read = AsyncMock(side_effect=Exception("Query failed"))

        result = await get_chunks_for_entities(
            entity_names=["Amsterdam"],
            neo4j_client=mock_neo4j,
        )

        # Should return empty list on error
        assert result == []
