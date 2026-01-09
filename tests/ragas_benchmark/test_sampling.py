"""
Unit tests for RAGAS benchmark stratified sampling.

Sprint 82: Phase 1 - Text-Only Benchmark
"""

import pytest
from scripts.ragas_benchmark.models import NormalizedSample
from scripts.ragas_benchmark.sampling import (
    stratified_sample,
    classify_question_type,
    assign_difficulty,
    rebalance_difficulty,
    validate_distribution,
)


def create_sample(
    doc_type: str = "clean_text",
    question_type: str = "lookup",
    difficulty: str = "D1",
    idx: int = 0
) -> NormalizedSample:
    """Helper to create test samples."""
    return NormalizedSample(
        id=f"test_{idx}",
        question=f"Test question {idx}?",
        ground_truth=f"Answer {idx}",
        contexts=[f"Context for sample {idx}"],
        doc_type=doc_type,
        question_type=question_type,
        difficulty=difficulty,
        answerable=True,
        source_dataset="test",
        metadata={},
    )


class TestClassifyQuestionType:
    """Tests for question type classification."""

    def test_definition_questions(self):
        """Test definition question detection."""
        assert classify_question_type("What is machine learning?") == "definition"
        assert classify_question_type("Define photosynthesis") == "definition"
        assert classify_question_type("Explain what RAG means") == "definition"

    def test_howto_questions(self):
        """Test how-to question detection."""
        assert classify_question_type("How to install Python?") == "howto"
        assert classify_question_type("Steps to deploy the application") == "howto"
        assert classify_question_type("Procedure for backup") == "howto"

    def test_comparison_questions(self):
        """Test comparison question detection."""
        assert classify_question_type("Compare Python vs Java") == "comparison"
        assert classify_question_type("Difference between A and B") == "comparison"
        assert classify_question_type("Which is better, X or Y?") == "comparison"

    def test_lookup_questions(self):
        """Test lookup question detection."""
        assert classify_question_type("When was the company founded?") == "lookup"
        assert classify_question_type("Where is the headquarters?") == "lookup"
        assert classify_question_type("Who invented the telephone?") == "lookup"

    def test_numeric_questions(self):
        """Test numeric question detection."""
        assert classify_question_type("How many employees are there?") == "numeric"
        assert classify_question_type("Total count of items") == "numeric"

    def test_default_fallback(self):
        """Test default fallback for unrecognized patterns."""
        result = classify_question_type("Xyzzy plugh?")
        assert result == "lookup"  # default


class TestAssignDifficulty:
    """Tests for difficulty assignment."""

    def test_multihop_is_hard(self):
        """Test that multihop questions get higher difficulty."""
        import random
        rng = random.Random(42)

        difficulties = [assign_difficulty("clean_text", "multihop", rng) for _ in range(10)]

        # Most should be D2 or D3 (at least 70%)
        hard_count = sum(1 for d in difficulties if d in ["D2", "D3"])
        assert hard_count >= 7

    def test_lookup_is_easier(self):
        """Test that lookup questions tend to be easier."""
        import random
        rng = random.Random(42)

        difficulties = [assign_difficulty("clean_text", "lookup", rng) for _ in range(10)]

        # Most should be D1 or D2
        easy_count = sum(1 for d in difficulties if d in ["D1", "D2"])
        assert easy_count >= 7


class TestStratifiedSampling:
    """Tests for stratified sampling."""

    @pytest.fixture
    def sample_pool(self):
        """Create a pool of test samples."""
        samples = []

        # Create samples for clean_text
        for qtype in ["lookup", "definition", "howto", "multihop", "comparison"]:
            for i in range(20):
                samples.append(create_sample(
                    doc_type="clean_text",
                    question_type=qtype,
                    idx=len(samples)
                ))

        # Create samples for log_ticket
        for qtype in ["lookup", "howto", "entity", "multihop"]:
            for i in range(15):
                samples.append(create_sample(
                    doc_type="log_ticket",
                    question_type=qtype,
                    idx=len(samples)
                ))

        return samples

    def test_basic_sampling(self, sample_pool):
        """Test basic stratified sampling."""
        doc_quotas = {"clean_text": 10, "log_ticket": 5}
        qtype_quotas = {
            "clean_text": {"lookup": 5, "definition": 3, "howto": 2},
            "log_ticket": {"lookup": 3, "howto": 2},
        }

        result = stratified_sample(
            pool=sample_pool,
            doc_type_quotas=doc_quotas,
            qtype_quotas=qtype_quotas,
            seed=42
        )

        # Should get exactly 15 samples (10 + 5)
        assert len(result) == 15

    def test_reproducibility(self, sample_pool):
        """Test that same seed gives same results."""
        doc_quotas = {"clean_text": 10}
        qtype_quotas = {"clean_text": {"lookup": 5, "definition": 5}}

        result1 = stratified_sample(sample_pool, doc_quotas, qtype_quotas, seed=42)
        result2 = stratified_sample(sample_pool, doc_quotas, qtype_quotas, seed=42)

        assert [s.id for s in result1] == [s.id for s in result2]

    def test_no_duplicates(self, sample_pool):
        """Test that no duplicate samples are returned."""
        doc_quotas = {"clean_text": 20, "log_ticket": 10}
        qtype_quotas = {
            "clean_text": {"lookup": 10, "definition": 5, "howto": 5},
            "log_ticket": {"lookup": 5, "howto": 5},
        }

        result = stratified_sample(sample_pool, doc_quotas, qtype_quotas, seed=42)

        ids = [s.id for s in result]
        assert len(ids) == len(set(ids))  # No duplicates


class TestRebalanceDifficulty:
    """Tests for difficulty rebalancing."""

    def test_rebalance_distribution(self):
        """Test that rebalancing achieves target distribution."""
        samples = [create_sample(difficulty="D1", idx=i) for i in range(100)]

        target = {"D1": 0.40, "D2": 0.35, "D3": 0.25}
        result = rebalance_difficulty(samples, target, seed=42)

        # Count difficulties
        counts = {}
        for s in result:
            counts[s.difficulty] = counts.get(s.difficulty, 0) + 1

        # Check within tolerance
        assert 35 <= counts.get("D1", 0) <= 45  # 40% ± 5
        assert 30 <= counts.get("D2", 0) <= 40  # 35% ± 5
        assert 20 <= counts.get("D3", 0) <= 30  # 25% ± 5


class TestValidateDistribution:
    """Tests for distribution validation."""

    def test_valid_distribution(self):
        """Test validation passes for correct distribution."""
        # Create samples with proper difficulty distribution
        samples = []
        difficulties = ["D1"] * 4 + ["D2"] * 3 + ["D3"] * 3  # 40/30/30%
        for i in range(10):
            samples.append(create_sample(
                doc_type="clean_text",
                question_type="lookup",
                difficulty=difficulties[i],
                idx=i
            ))

        doc_quotas = {"clean_text": 10}
        qtype_quotas = {"clean_text": {"lookup": 10}}

        # Use high tolerance to account for small sample size
        is_valid, msg = validate_distribution(samples, doc_quotas, qtype_quotas, tolerance_pct=15.0)
        assert is_valid

    def test_invalid_distribution(self):
        """Test validation fails for incorrect distribution."""
        samples = []
        for i in range(5):  # Only 5, but quota is 10
            samples.append(create_sample(doc_type="clean_text", question_type="lookup", idx=i))

        doc_quotas = {"clean_text": 10}
        qtype_quotas = {"clean_text": {"lookup": 10}}

        is_valid, msg = validate_distribution(samples, doc_quotas, qtype_quotas)
        assert not is_valid
        assert "clean_text" in msg
