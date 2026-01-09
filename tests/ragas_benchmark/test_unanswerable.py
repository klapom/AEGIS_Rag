"""
Unit tests for RAGAS benchmark unanswerable question generation.

Sprint 82: Phase 1 - Text-Only Benchmark
"""

import pytest
from scripts.ragas_benchmark.models import NormalizedSample
from scripts.ragas_benchmark.unanswerable import UnanswerableGenerator


def create_sample(idx: int = 0) -> NormalizedSample:
    """Helper to create test samples."""
    return NormalizedSample(
        id=f"test_{idx}",
        question="What year was Apple founded?",
        ground_truth="1976",
        contexts=["Apple Inc. was founded in 1976 by Steve Jobs, Steve Wozniak, and Ronald Wayne."],
        doc_type="clean_text",
        question_type="lookup",
        difficulty="D1",
        answerable=True,
        source_dataset="test",
        metadata={"original_id": f"orig_{idx}"},
    )


class TestUnanswerableGenerator:
    """Tests for unanswerable question generation."""

    @pytest.fixture
    def generator(self):
        return UnanswerableGenerator(seed=42)

    @pytest.fixture
    def sample(self):
        return create_sample()

    def test_temporal_shift(self, generator, sample):
        """Test temporal_shift method."""
        result = generator.temporal_shift(sample)

        assert result is not None
        assert result.answerable is False
        assert result.ground_truth == ""
        assert "unanswerable_" in result.id
        assert result.metadata["unanswerable_method"] == "temporal_shift"
        assert result.metadata["original_question"] == sample.question

        # Check question was modified
        assert result.question != sample.question
        # Should have a temporal prefix
        assert any(
            prefix.lower() in result.question.lower()
            for prefix in ["version", "update", "deprecated", "2030"]
        )

    def test_entity_swap(self, generator, sample):
        """Test entity_swap method."""
        result = generator.entity_swap(sample)

        assert result is not None
        assert result.answerable is False
        assert result.metadata["unanswerable_method"] == "entity_swap"

        # Original entity should be replaced
        assert "Apple" not in result.question or "Zephyrix" in result.question

    def test_negation(self, generator, sample):
        """Test negation method."""
        result = generator.negation(sample)

        assert result is not None
        assert result.answerable is False
        assert result.metadata["unanswerable_method"] == "negation"

        # Should ask about what's NOT in the document
        assert any(
            word in result.question.lower()
            for word in ["not", "absent", "missing", "cannot"]
        )

    def test_cross_domain(self, generator, sample):
        """Test cross_domain method."""
        result = generator.cross_domain(sample)

        assert result is not None
        assert result.answerable is False
        assert result.metadata["unanswerable_method"] == "cross_domain"

        # Should ask about unrelated topic
        assert any(
            word in result.question.lower()
            for word in ["chemical", "constellation", "atomic", "painted", "boiling"]
        )

    def test_generate_batch(self, generator):
        """Test batch generation."""
        samples = [create_sample(idx=i) for i in range(100)]

        unanswerables = generator.generate_batch(
            samples,
            target_count=50,
        )

        assert len(unanswerables) == 50

        # All should be unanswerable
        assert all(not s.answerable for s in unanswerables)

        # Check method distribution (approximately)
        methods = [s.metadata["unanswerable_method"] for s in unanswerables]
        method_counts = {}
        for m in methods:
            method_counts[m] = method_counts.get(m, 0) + 1

        # Should have all 4 methods used
        assert len(method_counts) == 4

    def test_difficulty_always_d3(self, generator, sample):
        """Test that unanswerables are always D3 (hard)."""
        result = generator.temporal_shift(sample)
        assert result.difficulty == "D3"

    def test_contexts_preserved(self, generator, sample):
        """Test that original contexts are preserved."""
        result = generator.temporal_shift(sample)
        assert result.contexts == sample.contexts

    def test_stats_tracking(self, generator):
        """Test generation statistics."""
        samples = [create_sample(idx=i) for i in range(20)]
        generator.generate_batch(samples, target_count=10)

        stats = generator.get_stats()
        assert stats["total_generated"] == 10
        assert sum(stats["by_method"].values()) == 10

    def test_reset_stats(self, generator):
        """Test stats reset."""
        samples = [create_sample(idx=i) for i in range(10)]
        generator.generate_batch(samples, target_count=5)

        generator.reset_stats()

        stats = generator.get_stats()
        assert stats["total_generated"] == 0

    def test_reproducibility(self):
        """Test that same seed gives same results."""
        samples = [create_sample(idx=i) for i in range(10)]

        gen1 = UnanswerableGenerator(seed=42)
        result1 = gen1.generate_batch(samples, target_count=5)

        gen2 = UnanswerableGenerator(seed=42)
        result2 = gen2.generate_batch(samples, target_count=5)

        # Questions should match
        q1 = [s.question for s in result1]
        q2 = [s.question for s in result2]
        assert q1 == q2


class TestUnanswerableIntegration:
    """Integration tests for unanswerable generation."""

    def test_mixed_doc_types(self):
        """Test generation from mixed doc_type samples."""
        samples = []
        for i in range(10):
            samples.append(NormalizedSample(
                id=f"clean_{i}",
                question="What is X?",
                ground_truth="X is Y",
                contexts=["Context about X"],
                doc_type="clean_text",
                question_type="definition",
                difficulty="D1",
            ))
        for i in range(10):
            samples.append(NormalizedSample(
                id=f"log_{i}",
                question="What error occurred?",
                ground_truth="NullPointer",
                contexts=["ERROR: NullPointer at line 42"],
                doc_type="log_ticket",
                question_type="lookup",
                difficulty="D2",
            ))

        generator = UnanswerableGenerator(seed=42)
        unanswerables = generator.generate_batch(samples, target_count=10)

        # Should have mix of doc_types
        doc_types = [s.doc_type for s in unanswerables]
        assert "clean_text" in doc_types or "log_ticket" in doc_types
