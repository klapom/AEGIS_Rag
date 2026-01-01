"""Unit tests for MemoryWritePolicy.

Sprint 68 Feature 68.6: Memory-Write Policy + Forgetting
Tests adaptive write policy with importance filtering and budget enforcement.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.memory.importance_scorer import ImportanceScore
from src.components.memory.write_policy import MemoryWritePolicy


class TestMemoryWritePolicy:
    """Test suite for MemoryWritePolicy."""

    @pytest.fixture
    def mock_graphiti(self):
        """Mock GraphitiClient."""
        mock = MagicMock()
        mock.add_episode = AsyncMock(
            return_value={
                "episode_id": "episode_123",  # Changed from "id" to "episode_id"
                "entities": [],
                "relationships": [],
            }
        )
        mock.neo4j_client = MagicMock()
        mock.neo4j_client.execute_query = AsyncMock(return_value=[{"count": 100}])
        return mock

    @pytest.fixture
    def mock_scorer(self):
        """Mock ImportanceScorer."""
        mock = MagicMock()
        mock.importance_threshold = 0.6
        # Make score_fact and batch_score_facts async
        mock.score_fact = AsyncMock()
        mock.batch_score_facts = AsyncMock()
        return mock

    @pytest.fixture
    def mock_forgetting(self):
        """Mock ForgettingMechanism."""
        mock = MagicMock()
        mock.forget_by_importance = AsyncMock(
            return_value={"removed_count": 100, "avg_importance": 0.3}
        )
        return mock

    @pytest.fixture
    def policy(self, mock_graphiti, mock_scorer, mock_forgetting):
        """Create MemoryWritePolicy with mocked dependencies."""
        return MemoryWritePolicy(
            graphiti_wrapper=mock_graphiti,
            importance_scorer=mock_scorer,
            forgetting_mechanism=mock_forgetting,
            memory_budget=10000,
            importance_threshold=0.6,
        )

    @pytest.mark.asyncio
    async def test_should_write_high_importance(self, policy: MemoryWritePolicy):
        """Test should_write accepts high-importance fact."""
        fact = {
            "content": "Important fact",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        score = ImportanceScore(
            novelty=0.8,
            relevance=0.8,
            frequency=0.7,
            recency=0.9,
            total_score=0.8,
            breakdown={},
        )

        should_write, reason, returned_score = await policy.should_write(fact, importance_score=score)

        assert should_write is True
        assert reason == "accepted"
        assert returned_score.total_score == 0.8

    @pytest.mark.asyncio
    async def test_should_write_low_importance(self, policy: MemoryWritePolicy):
        """Test should_write rejects low-importance fact."""
        fact = {
            "content": "Unimportant fact",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        score = ImportanceScore(
            novelty=0.3,
            relevance=0.4,
            frequency=0.2,
            recency=0.5,
            total_score=0.35,
            breakdown={},
        )

        should_write, reason, returned_score = await policy.should_write(fact, importance_score=score)

        assert should_write is False
        assert "importance_score" in reason
        assert "threshold" in reason
        assert returned_score.total_score == 0.35

    @pytest.mark.asyncio
    async def test_should_write_budget_exceeded(self, policy: MemoryWritePolicy):
        """Test should_write when memory budget is exceeded."""
        # Mock memory full
        policy.graphiti.neo4j_client.execute_query = AsyncMock(return_value=[{"count": 10001}])

        fact = {
            "content": "Fact when budget exceeded",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        score = ImportanceScore(
            novelty=0.8,
            relevance=0.8,
            frequency=0.7,
            recency=0.9,
            total_score=0.8,
            breakdown={},
        )

        should_write, reason, returned_score = await policy.should_write(fact, importance_score=score)

        # Should still write, but trigger forgetting
        assert should_write is True
        assert "budget_exceeded" in reason

    @pytest.mark.asyncio
    async def test_write_fact_accepted(self, policy: MemoryWritePolicy):
        """Test write_fact successfully writes high-importance fact."""
        fact = {
            "content": "Important fact to write",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        score = ImportanceScore(
            novelty=0.8,
            relevance=0.8,
            frequency=0.7,
            recency=0.9,
            total_score=0.8,
            breakdown={},
        )

        # Mock score_fact as AsyncMock
        policy.scorer.score_fact = AsyncMock(return_value=score)

        result = await policy.write_fact(fact)

        assert result["written"] is True
        assert result["episode_id"] == "episode_123"
        assert result["importance_score"] == 0.8
        assert policy.stats["written"] == 1

    @pytest.mark.asyncio
    async def test_write_fact_rejected(self, policy: MemoryWritePolicy):
        """Test write_fact rejects low-importance fact."""
        fact = {
            "content": "Unimportant fact",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        score = ImportanceScore(
            novelty=0.3,
            relevance=0.4,
            frequency=0.2,
            recency=0.5,
            total_score=0.35,
            breakdown={},
        )

        # Mock score_fact as AsyncMock
        policy.scorer.score_fact = AsyncMock(return_value=score)

        result = await policy.write_fact(fact)

        assert result["written"] is False
        assert "importance_score" in result["reason"]
        assert result["importance_score"] == 0.35
        assert policy.stats["rejected_low_importance"] == 1

    @pytest.mark.asyncio
    async def test_write_fact_triggers_forgetting(self, policy: MemoryWritePolicy):
        """Test write_fact triggers forgetting when budget exceeded."""
        # Mock memory full
        policy.graphiti.neo4j_client.execute_query = AsyncMock(return_value=[{"count": 10001}])

        fact = {
            "content": "Fact triggering forgetting",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        score = ImportanceScore(
            novelty=0.8,
            relevance=0.8,
            frequency=0.7,
            recency=0.9,
            total_score=0.8,
            breakdown={},
        )

        # Mock score_fact as AsyncMock
        policy.scorer.score_fact = AsyncMock(return_value=score)

        result = await policy.write_fact(fact)

        # Should trigger forgetting
        policy.forgetting.forget_by_importance.assert_called_once()
        assert policy.stats["forgetting_triggered"] == 1
        assert result["written"] is True

    @pytest.mark.asyncio
    async def test_batch_write_facts(self, policy: MemoryWritePolicy):
        """Test batch_write_facts with mixed importance scores."""
        facts = [
            {"content": "High importance 1", "created_at": datetime.now(UTC).isoformat(), "metadata": {}},
            {"content": "Low importance", "created_at": datetime.now(UTC).isoformat(), "metadata": {}},
            {"content": "High importance 2", "created_at": datetime.now(UTC).isoformat(), "metadata": {}},
        ]

        # Mock batch scoring
        scores = [
            (facts[0], ImportanceScore(0.8, 0.8, 0.7, 0.9, 0.8, {})),
            (facts[1], ImportanceScore(0.3, 0.4, 0.2, 0.5, 0.35, {})),
            (facts[2], ImportanceScore(0.7, 0.8, 0.6, 0.9, 0.75, {})),
        ]

        # Mock batch_score_facts as AsyncMock
        policy.scorer.batch_score_facts = AsyncMock(return_value=scores)

        result = await policy.batch_write_facts(facts)

        assert result["total_facts"] == 3
        assert result["written"] == 2  # 2 high-importance
        assert result["rejected"] == 1  # 1 low-importance

    @pytest.mark.asyncio
    async def test_get_fact_count(self, policy: MemoryWritePolicy):
        """Test _get_fact_count queries Neo4j correctly."""
        count = await policy._get_fact_count()
        assert count == 100
        policy.graphiti.neo4j_client.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_fact_count_error_handling(self, policy: MemoryWritePolicy):
        """Test _get_fact_count handles errors gracefully."""
        policy.graphiti.neo4j_client.execute_query = AsyncMock(side_effect=Exception("Neo4j error"))

        count = await policy._get_fact_count()
        assert count == 0  # Should return 0 on error

    @pytest.mark.asyncio
    async def test_is_memory_full(self, policy: MemoryWritePolicy):
        """Test _is_memory_full correctly detects budget exceeded."""
        # Below budget
        policy.graphiti.neo4j_client.execute_query = AsyncMock(return_value=[{"count": 5000}])
        assert await policy._is_memory_full() is False

        # At budget
        policy.graphiti.neo4j_client.execute_query = AsyncMock(return_value=[{"count": 10000}])
        assert await policy._is_memory_full() is True

        # Above budget
        policy.graphiti.neo4j_client.execute_query = AsyncMock(return_value=[{"count": 15000}])
        assert await policy._is_memory_full() is True

    def test_get_statistics(self, policy: MemoryWritePolicy):
        """Test get_statistics returns correct stats."""
        policy.stats = {
            "total_attempted": 100,
            "rejected_low_importance": 30,
            "rejected_budget_exceeded": 10,
            "written": 60,
            "forgetting_triggered": 5,
        }

        stats = policy.get_statistics()

        assert stats["total_attempted"] == 100
        assert stats["written"] == 60
        assert stats["write_rate"] == 0.6
        assert stats["rejection_rate"] == 0.4

    def test_reset_statistics(self, policy: MemoryWritePolicy):
        """Test reset_statistics clears all stats."""
        policy.stats = {
            "total_attempted": 100,
            "rejected_low_importance": 30,
            "rejected_budget_exceeded": 10,
            "written": 60,
            "forgetting_triggered": 5,
        }

        policy.reset_statistics()

        assert policy.stats["total_attempted"] == 0
        assert policy.stats["written"] == 0
        assert policy.stats["rejected_low_importance"] == 0

    @pytest.mark.asyncio
    async def test_forget_least_important(self, policy: MemoryWritePolicy):
        """Test _forget_least_important calls forgetting mechanism."""
        await policy._forget_least_important(forget_count=50)

        policy.forgetting.forget_by_importance.assert_called_once_with(limit=50)

    @pytest.mark.asyncio
    async def test_write_fact_adds_importance_to_metadata(self, policy: MemoryWritePolicy):
        """Test write_fact adds importance score to metadata."""
        fact = {
            "content": "Fact with metadata",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {"existing_key": "value"},
        }

        score = ImportanceScore(
            novelty=0.8,
            relevance=0.8,
            frequency=0.7,
            recency=0.9,
            total_score=0.8,
            breakdown={},
        )

        # Mock score_fact as AsyncMock
        policy.scorer.score_fact = AsyncMock(return_value=score)

        result = await policy.write_fact(fact)

        # Check Graphiti was called with importance in metadata
        call_args = policy.graphiti.add_episode.call_args
        assert call_args.kwargs["metadata"]["importance_score"] == 0.8
        assert call_args.kwargs["metadata"]["importance_breakdown"] == {}
        assert call_args.kwargs["metadata"]["existing_key"] == "value"
