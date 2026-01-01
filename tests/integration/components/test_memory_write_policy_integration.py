"""Integration tests for Memory-Write Policy + Forgetting.

Sprint 68 Feature 68.6: Memory-Write Policy + Forgetting
Tests full pipeline with real dependencies (mocked Graphiti/Neo4j).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.memory.forgetting import ForgettingMechanism
from src.components.memory.importance_scorer import ImportanceScorer
from src.components.memory.write_policy import MemoryWritePolicy


class TestMemoryWritePolicyIntegration:
    """Integration tests for memory-write policy pipeline."""

    @pytest.fixture
    def mock_graphiti(self):
        """Mock GraphitiClient with realistic behavior."""
        mock = MagicMock()

        # Mock add_episode
        mock.add_episode = AsyncMock(
            side_effect=lambda content, **kwargs: {
                "id": f"episode_{hash(content) % 1000}",
                "entities": [{"name": "TestEntity", "type": "concept"}],
                "relationships": [],
                "timestamp": kwargs.get("timestamp", datetime.now(UTC)).isoformat(),
            }
        )

        # Mock Neo4j client for fact counting
        mock.neo4j_client = MagicMock()
        mock.neo4j_client.execute_query = AsyncMock(return_value=[{"count": 100}])

        return mock

    @pytest.fixture
    def scorer(self):
        """Create real ImportanceScorer."""
        return ImportanceScorer(
            novelty_weight=0.3,
            relevance_weight=0.3,
            frequency_weight=0.2,
            recency_weight=0.2,
            importance_threshold=0.6,
        )

    @pytest.fixture
    def forgetting(self, mock_graphiti):
        """Create real ForgettingMechanism with mocked Graphiti."""
        return ForgettingMechanism(
            graphiti_wrapper=mock_graphiti,
            decay_half_life_days=30,
            effective_importance_threshold=0.3,
        )

    @pytest.fixture
    def policy(self, mock_graphiti, scorer, forgetting):
        """Create MemoryWritePolicy with real components."""
        return MemoryWritePolicy(
            graphiti_wrapper=mock_graphiti,
            importance_scorer=scorer,
            forgetting_mechanism=forgetting,
            memory_budget=10000,
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_write_high_importance(self, policy: MemoryWritePolicy):
        """Test full pipeline: high-importance fact gets written."""
        fact = {
            "content": "User prefers Python for machine learning tasks with TensorFlow",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {"reference_count": 10},
        }

        result = await policy.write_fact(fact, domain_context="machine learning AI")

        # Should be written (high relevance + frequency + recency)
        assert result["written"] is True
        assert result["importance_score"] > 0.6
        assert "episode_" in result["episode_id"]

    @pytest.mark.asyncio
    async def test_full_pipeline_reject_low_importance(self, policy: MemoryWritePolicy):
        """Test full pipeline: low-importance fact gets rejected."""
        fact = {
            "content": "Random irrelevant fact",
            "created_at": (datetime.now(UTC) - timedelta(days=60)).isoformat(),  # Old
            "metadata": {"reference_count": 0},  # Never referenced
        }

        result = await policy.write_fact(fact, domain_context="machine learning")

        # Should be rejected (low relevance + low frequency + old)
        assert result["written"] is False
        assert result["importance_score"] < 0.6

    @pytest.mark.asyncio
    async def test_batch_write_with_importance_filtering(self, policy: MemoryWritePolicy):
        """Test batch write with mixed importance facts."""
        facts = [
            {
                "content": "TensorFlow GPU optimization techniques",
                "created_at": datetime.now(UTC).isoformat(),
                "metadata": {"reference_count": 15},
            },
            {
                "content": "Unrelated random text",
                "created_at": (datetime.now(UTC) - timedelta(days=90)).isoformat(),
                "metadata": {"reference_count": 0},
            },
            {
                "content": "PyTorch distributed training best practices",
                "created_at": datetime.now(UTC).isoformat(),
                "metadata": {"reference_count": 8},
            },
        ]

        result = await policy.batch_write_facts(facts, domain_context="machine learning")

        # Should write 2 high-importance, reject 1 low-importance
        assert result["total_facts"] == 3
        assert result["written"] >= 2
        assert result["rejected"] >= 1

    @pytest.mark.asyncio
    async def test_memory_budget_triggers_forgetting(self, policy: MemoryWritePolicy):
        """Test that exceeding memory budget triggers forgetting."""
        # Mock memory full
        policy.graphiti.neo4j_client.execute_query = AsyncMock(return_value=[{"count": 10001}])

        # Mock forgetting mechanism
        policy.forgetting.forget_by_importance = AsyncMock(
            return_value={"removed_count": 100, "avg_importance": 0.25}
        )

        fact = {
            "content": "Important fact when budget exceeded",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {"reference_count": 10},
        }

        result = await policy.write_fact(fact)

        # Should trigger forgetting
        policy.forgetting.forget_by_importance.assert_called_once()
        assert policy.stats["forgetting_triggered"] == 1
        assert result["written"] is True

    @pytest.mark.asyncio
    async def test_importance_scores_added_to_metadata(self, policy: MemoryWritePolicy):
        """Test that importance scores are stored in metadata."""
        fact = {
            "content": "Fact with importance metadata",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {"reference_count": 5},
        }

        result = await policy.write_fact(fact)

        # Check that add_episode was called with importance in metadata
        call_args = policy.graphiti.add_episode.call_args
        assert "importance_score" in call_args.kwargs["metadata"]
        assert "importance_breakdown" in call_args.kwargs["metadata"]

    @pytest.mark.asyncio
    async def test_forgetting_decay_calculation(self, forgetting: ForgettingMechanism):
        """Test decay calculation with real ForgettingMechanism."""
        # Recent fact - should not forget
        recent_fact = {
            "id": "fact_1",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {"importance_score": 0.5},
        }
        assert forgetting.should_forget(recent_fact) is False

        # Old fact with low importance - should forget
        old_fact = {
            "id": "fact_2",
            "created_at": (datetime.now(UTC) - timedelta(days=120)).isoformat(),
            "metadata": {"importance_score": 0.5},
        }
        assert forgetting.should_forget(old_fact) is True

        # Old fact with high importance - should not forget
        old_important_fact = {
            "id": "fact_3",
            "created_at": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
            "metadata": {"importance_score": 0.9},
        }
        assert forgetting.should_forget(old_important_fact) is False

    @pytest.mark.asyncio
    async def test_novelty_detection_with_existing_facts(self, scorer: ImportanceScorer):
        """Test novelty detection with existing facts."""
        existing_facts = [
            {"content": "Python machine learning"},
            {"content": "TensorFlow neural networks"},
        ]

        # Novel fact
        novel_fact = {
            "content": "Rust systems programming performance",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        score = await scorer.score_fact(novel_fact, existing_facts=existing_facts)
        assert score.novelty > 0.7  # High novelty

        # Duplicate fact
        duplicate_fact = {
            "content": "Python machine learning",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        score = await scorer.score_fact(duplicate_fact, existing_facts=existing_facts)
        assert score.novelty < 0.3  # Low novelty

    @pytest.mark.asyncio
    async def test_relevance_scoring_with_domain(self, scorer: ImportanceScorer):
        """Test relevance scoring with domain context."""
        # Highly relevant fact
        relevant_fact = {
            "content": "Deep learning neural networks training optimization",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        score = await scorer.score_fact(
            relevant_fact, domain_context="machine learning deep learning AI"
        )
        assert score.relevance > 0.5

        # Irrelevant fact
        irrelevant_fact = {
            "content": "Cooking recipes and kitchen tips",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {},
        }

        score = await scorer.score_fact(
            irrelevant_fact, domain_context="machine learning deep learning AI"
        )
        assert score.relevance < 0.5

    @pytest.mark.asyncio
    async def test_write_policy_statistics(self, policy: MemoryWritePolicy):
        """Test that write policy correctly tracks statistics."""
        # Write some facts
        high_importance_fact = {
            "content": "High importance fact",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {"reference_count": 10},
        }

        low_importance_fact = {
            "content": "Low importance fact",
            "created_at": (datetime.now(UTC) - timedelta(days=90)).isoformat(),
            "metadata": {"reference_count": 0},
        }

        await policy.write_fact(high_importance_fact)
        await policy.write_fact(low_importance_fact)

        stats = policy.get_statistics()

        assert stats["total_attempted"] == 2
        assert stats["written"] >= 1
        assert stats["rejected_low_importance"] >= 1
        assert 0.0 <= stats["write_rate"] <= 1.0
        assert 0.0 <= stats["rejection_rate"] <= 1.0

    @pytest.mark.asyncio
    async def test_merge_facts_consolidation(self, forgetting: ForgettingMechanism):
        """Test fact merging and consolidation."""
        facts = [
            {
                "id": "fact_1",
                "content": "Python is great for data science",
                "created_at": "2025-01-01T00:00:00Z",
                "metadata": {"importance_score": 0.8},
            },
            {
                "id": "fact_2",
                "content": "Python has excellent ML libraries",
                "created_at": "2025-01-02T00:00:00Z",
                "metadata": {"importance_score": 0.7},
            },
        ]

        merged = await forgetting._merge_facts(facts)

        # Check consolidated content
        assert "Python" in merged["content"]
        assert "data science" in merged["content"] or "ML libraries" in merged["content"]

        # Check consolidated metadata
        assert merged["metadata"]["consolidated_from"] == 2
        assert 0.7 <= merged["metadata"]["importance_score"] <= 0.8  # Average
        assert merged["created_at"] == "2025-01-01T00:00:00Z"  # Earliest

    @pytest.mark.asyncio
    async def test_graphiti_wrapper_integration(self, mock_graphiti):
        """Test that write policy integrates correctly with GraphitiClient."""
        from src.components.memory.graphiti_wrapper import GraphitiClient

        # Create GraphitiClient wrapper
        wrapper = GraphitiClient(llm_client=None)
        wrapper.graphiti = mock_graphiti

        # Test add_episode with write policy
        result = await wrapper.add_episode(
            content="Test episode with write policy",
            use_write_policy=False,  # Direct write
        )

        assert result["episode_id"] is not None
        mock_graphiti.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_to_end_write_forget_cycle(self, policy: MemoryWritePolicy):
        """Test complete cycle: write facts, trigger forgetting, verify removal."""
        # 1. Write high-importance facts
        high_importance_facts = [
            {
                "content": f"Important fact {i}",
                "created_at": datetime.now(UTC).isoformat(),
                "metadata": {"reference_count": 10},
            }
            for i in range(5)
        ]

        for fact in high_importance_facts:
            await policy.write_fact(fact)

        # 2. Simulate memory full
        policy.graphiti.neo4j_client.execute_query = AsyncMock(return_value=[{"count": 10001}])

        # 3. Mock forgetting to return removed facts
        policy.forgetting.forget_by_importance = AsyncMock(
            return_value={"removed_count": 100, "avg_importance": 0.25}
        )

        # 4. Write another fact (should trigger forgetting)
        trigger_fact = {
            "content": "Fact triggering forgetting",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {"reference_count": 10},
        }

        result = await policy.write_fact(trigger_fact)

        # Verify forgetting was triggered
        assert policy.stats["forgetting_triggered"] == 1
        policy.forgetting.forget_by_importance.assert_called_once()
        assert result["written"] is True
