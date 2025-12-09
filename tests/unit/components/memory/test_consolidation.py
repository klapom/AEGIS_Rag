"""Unit tests for MemoryConsolidationPipeline (Feature 9.3).

Tests:
1. test_consolidation_pipeline_initialization - Test pipeline setup
2. test_cosine_similarity_calculation - Test vector similarity
3. test_deduplication_basic - Test basic deduplication logic
4. test_deduplication_with_threshold - Test similarity threshold
5. test_deduplication_edge_cases - Test empty/single item cases
6. test_relevance_scoring_integration - Test integration with RelevanceScorer
7. test_top_percentile_selection - Test top N% selection
8. test_cron_scheduler_parsing - Test cron schedule validation
9. test_scheduler_start_stop - Test scheduler lifecycle
10. test_consolidation_with_empty_items - Test empty data handling
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.components.memory.consolidation import MemoryConsolidationPipeline
from src.components.memory.relevance_scorer import RelevanceScorer


@pytest.fixture
def mock_redis_memory():
    """Mock Redis memory manager."""
    mock = AsyncMock()
    mock.get_frequently_accessed = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    return Mock()


@pytest.fixture
def mock_graphiti_wrapper():
    """Mock Graphiti wrapper."""
    return Mock()


@pytest.fixture
def consolidation_pipeline(mock_redis_memory, mock_qdrant_client):
    """Create consolidation pipeline with mocked dependencies."""
    with (
        patch(
            "src.components.memory.consolidation.get_redis_memory", return_value=mock_redis_memory
        ),
        patch(
            "src.components.memory.consolidation.get_qdrant_client", return_value=mock_qdrant_client
        ),
        patch("src.components.memory.consolidation.settings") as mock_settings,
    ):
        mock_settings.graphiti_enabled = False
        mock_settings.memory_consolidation_min_access_count = 3

        pipeline = MemoryConsolidationPipeline(
            access_count_threshold=3,
            time_threshold_hours=1,
            deduplication_threshold=0.95,
        )

        return pipeline


class TestConsolidationPipeline:
    """Test suite for MemoryConsolidationPipeline."""

    def test_consolidation_pipeline_initialization(self, consolidation_pipeline):
        """Test 1: Test pipeline initialization."""
        assert consolidation_pipeline is not None
        assert consolidation_pipeline.deduplication_threshold == 0.95
        assert isinstance(consolidation_pipeline.relevance_scorer, RelevanceScorer)
        assert consolidation_pipeline.scheduler is not None
        assert len(consolidation_pipeline.policies) == 2

    def test_cosine_similarity_calculation(self, consolidation_pipeline):
        """Test 2: Test cosine similarity calculation."""
        # Identical vectors
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = consolidation_pipeline._calculate_cosine_similarity(vec1, vec2)
        assert pytest.approx(similarity, abs=0.001) == 1.0

        # Orthogonal vectors (90 degrees)
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = consolidation_pipeline._calculate_cosine_similarity(vec1, vec2)
        assert pytest.approx(similarity, abs=0.001) == 0.0

        # Opposite vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = consolidation_pipeline._calculate_cosine_similarity(vec1, vec2)
        assert pytest.approx(similarity, abs=0.001) == -1.0

        # Similar but not identical
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.1, 2.9]
        similarity = consolidation_pipeline._calculate_cosine_similarity(vec1, vec2)
        assert 0.95 < similarity < 1.0

        # Empty vectors
        assert consolidation_pipeline._calculate_cosine_similarity([], []) == 0.0
        assert consolidation_pipeline._calculate_cosine_similarity([1.0], []) == 0.0

        # Zero vector
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = consolidation_pipeline._calculate_cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    @pytest.mark.asyncio
    async def test_deduplication_basic(self, consolidation_pipeline):
        """Test 3: Test basic deduplication logic."""
        items = [
            {"key": "item1", "value": "test"},
            {"key": "item2", "value": "test"},
            {"key": "item3", "value": "test"},
        ]

        # Embeddings: item1 and item2 are duplicates (similarity=1.0)
        embeddings = [
            [1.0, 2.0, 3.0],  # item1
            [1.0, 2.0, 3.0],  # item2 (identical)
            [1.0, 0.0, -1.0],  # item3 (different, low similarity ~0.27)
        ]

        unique_items, duplicates_removed = await consolidation_pipeline._deduplicate_memories(
            items, embeddings
        )

        # Should keep item1 and item3, remove item2
        assert len(unique_items) == 2
        assert duplicates_removed == 1
        assert unique_items[0]["key"] == "item1"
        assert unique_items[1]["key"] == "item3"

    @pytest.mark.asyncio
    async def test_deduplication_with_threshold(self, consolidation_pipeline):
        """Test 4: Test deduplication with different similarity thresholds."""
        # Lower threshold to test boundary
        consolidation_pipeline.deduplication_threshold = 0.90

        items = [
            {"key": "item1", "value": "test"},
            {"key": "item2", "value": "test"},
        ]

        # Similar but below threshold (similarity ~0.75)
        embeddings = [
            [1.0, 2.0, 3.0],
            [2.0, -1.0, 4.0],  # Different direction, similarity ~0.75
        ]

        unique_items, duplicates_removed = await consolidation_pipeline._deduplicate_memories(
            items, embeddings
        )

        # Both should be kept (similarity < 0.90)
        assert len(unique_items) == 2
        assert duplicates_removed == 0

        # Now with very similar embeddings (above threshold)
        embeddings = [
            [1.0, 2.0, 3.0],
            [1.0, 2.01, 3.01],  # Very similar (> 0.99)
        ]

        unique_items, duplicates_removed = await consolidation_pipeline._deduplicate_memories(
            items, embeddings
        )

        # Second should be removed
        assert len(unique_items) == 1
        assert duplicates_removed == 1

    @pytest.mark.asyncio
    async def test_deduplication_edge_cases(self, consolidation_pipeline):
        """Test 5: Test edge cases for deduplication."""
        # Empty items
        unique_items, duplicates_removed = await consolidation_pipeline._deduplicate_memories(
            [], []
        )
        assert len(unique_items) == 0
        assert duplicates_removed == 0

        # Single item
        items = [{"key": "item1", "value": "test"}]
        embeddings = [[1.0, 2.0, 3.0]]
        unique_items, duplicates_removed = await consolidation_pipeline._deduplicate_memories(
            items, embeddings
        )
        assert len(unique_items) == 1
        assert duplicates_removed == 0

        # No embeddings provided (should skip deduplication)
        items = [{"key": "item1"}, {"key": "item2"}]
        unique_items, duplicates_removed = await consolidation_pipeline._deduplicate_memories(
            items, embeddings=None
        )
        assert len(unique_items) == 2
        assert duplicates_removed == 0

        # Mismatched counts
        items = [{"key": "item1"}, {"key": "item2"}]
        embeddings = [[1.0, 2.0, 3.0]]  # Only one embedding
        unique_items, duplicates_removed = await consolidation_pipeline._deduplicate_memories(
            items, embeddings
        )
        assert len(unique_items) == 2  # Should skip deduplication
        assert duplicates_removed == 0

    @pytest.mark.asyncio
    async def test_relevance_scoring_integration(self, mock_redis_memory):
        """Test 6: Test integration with RelevanceScorer."""
        now = datetime.now(UTC)

        # Mock Redis items with metadata
        mock_items = [
            {
                "key": "high_value",
                "value": "important data",
                "access_count": 50,
                "stored_at": (now - timedelta(days=1)).isoformat(),
                "user_rating": 0.9,
            },
            {
                "key": "low_value",
                "value": "old data",
                "access_count": 2,
                "stored_at": (now - timedelta(days=100)).isoformat(),
                "user_rating": 0.3,
            },
        ]

        mock_redis_memory.get_frequently_accessed = AsyncMock(return_value=mock_items)

        with (
            patch(
                "src.components.memory.consolidation.get_redis_memory",
                return_value=mock_redis_memory,
            ),
            patch("src.components.memory.consolidation.get_qdrant_client"),
            patch("src.components.memory.consolidation.settings") as mock_settings,
        ):
            mock_settings.graphiti_enabled = False
            mock_settings.memory_consolidation_min_access_count = 1

            pipeline = MemoryConsolidationPipeline()
            result = await pipeline.consolidate_with_relevance_scoring(batch_size=10)

            # Verify scoring happened
            assert result["scored"] == 2
            assert result["processed"] == 2

            # High-value item should have higher score
            # We can't directly check scores here, but they should be processed

    @pytest.mark.asyncio
    async def test_top_percentile_selection(self, mock_redis_memory):
        """Test 7: Test top N% selection logic."""
        now = datetime.now(UTC)

        # Create 10 items with varying access counts
        mock_items = [
            {
                "key": f"item{i}",
                "value": f"data{i}",
                "access_count": i * 10,  # 0, 10, 20, ... 90
                "stored_at": (now - timedelta(days=1)).isoformat(),
            }
            for i in range(10)
        ]

        mock_redis_memory.get_frequently_accessed = AsyncMock(return_value=mock_items)

        with (
            patch(
                "src.components.memory.consolidation.get_redis_memory",
                return_value=mock_redis_memory,
            ),
            patch("src.components.memory.consolidation.get_qdrant_client"),
            patch("src.components.memory.consolidation.settings") as mock_settings,
        ):
            mock_settings.graphiti_enabled = False
            mock_settings.memory_consolidation_min_access_count = 1

            pipeline = MemoryConsolidationPipeline()

            # Test top 20% (should select 2 items)
            result = await pipeline.consolidate_with_relevance_scoring(
                batch_size=10,
                top_percentile=0.2,
            )

            assert result["scored"] == 10
            assert result["top_selected"] == 2

            # Test top 50% (should select 5 items)
            result = await pipeline.consolidate_with_relevance_scoring(
                batch_size=10,
                top_percentile=0.5,
            )

            assert result["top_selected"] == 5

    @pytest.mark.asyncio
    async def test_cron_scheduler_parsing(self, consolidation_pipeline):
        """Test 8: Test cron schedule validation."""
        # Ensure scheduler is stopped before starting
        if consolidation_pipeline.scheduler.running:
            consolidation_pipeline.stop_scheduler()

        # Valid schedules
        valid_schedules = [
            "0 2 * * *",  # Daily at 2 AM
            "0 */6 * * *",  # Every 6 hours
            "0 0 * * 0",  # Weekly on Sunday
        ]

        for schedule in valid_schedules:
            # Should not raise
            consolidation_pipeline.start_cron_scheduler(schedule)
            consolidation_pipeline.stop_scheduler()
            # Wait a bit for shutdown to complete
            await asyncio.sleep(0.1)

        # Invalid schedule (not 5 parts)
        with pytest.raises(ValueError, match="Invalid cron schedule"):
            consolidation_pipeline.start_cron_scheduler("0 2 * *")  # Missing day_of_week

        with pytest.raises(ValueError, match="Invalid cron schedule"):
            consolidation_pipeline.start_cron_scheduler("invalid")

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, consolidation_pipeline):
        """Test 9: Test scheduler lifecycle."""
        # Ensure clean state
        if consolidation_pipeline.scheduler.running:
            consolidation_pipeline.stop_scheduler()
            await asyncio.sleep(0.1)

        # Start scheduler
        consolidation_pipeline.start_cron_scheduler("0 2 * * *")
        assert consolidation_pipeline.scheduler.running

        # Try to start again (should warn, not error)
        consolidation_pipeline.start_cron_scheduler("0 2 * * *")
        assert consolidation_pipeline.scheduler.running

        # Stop scheduler
        consolidation_pipeline.stop_scheduler()
        # Wait for scheduler to fully stop
        await asyncio.sleep(0.1)
        assert not consolidation_pipeline.scheduler.running

    @pytest.mark.asyncio
    async def test_consolidation_with_empty_items(self, mock_redis_memory):
        """Test 10: Test consolidation with empty item list."""
        mock_redis_memory.get_frequently_accessed = AsyncMock(return_value=[])

        with (
            patch(
                "src.components.memory.consolidation.get_redis_memory",
                return_value=mock_redis_memory,
            ),
            patch("src.components.memory.consolidation.get_qdrant_client"),
            patch("src.components.memory.consolidation.settings") as mock_settings,
        ):
            mock_settings.graphiti_enabled = False
            mock_settings.memory_consolidation_min_access_count = 3

            pipeline = MemoryConsolidationPipeline()
            result = await pipeline.consolidate_with_relevance_scoring()

            # Should handle gracefully
            assert result["processed"] == 0
            assert result["scored"] == 0
            assert result["top_selected"] == 0
            assert result["consolidated"] == 0
