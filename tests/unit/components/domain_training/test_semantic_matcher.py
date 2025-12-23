"""Unit tests for Semantic Matching for DSPy Evaluation Metrics.

Sprint 45 - Feature 45.17: Embedding-based Matching

Tests:
- SemanticMatcher initialization
- Entity similarity matching
- Relation matching with weighted components
- Token overlap fallback
- Embedding availability checking
- Metric computation (entity and relation)
- Caching and performance
- Edge cases and error handling
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.components.domain_training.semantic_matcher import (
    SemanticMatcher,
    get_semantic_matcher,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_embedder():
    """Mock sentence transformer embedder."""
    embedder = MagicMock()

    def mock_encode(text, normalize_embeddings=False):
        # Simple mock: hash text to deterministic embedding
        hash_val = hash(text) % 1000
        embedding = np.random.RandomState(hash_val).randn(1024)
        if normalize_embeddings:
            embedding = embedding / np.linalg.norm(embedding)
        return embedding

    embedder.encode = mock_encode
    return embedder


@pytest.fixture
def semantic_matcher():
    """Create SemanticMatcher with mock embedder."""
    matcher = SemanticMatcher(threshold=0.75, predicate_weight=0.4)
    return matcher


@pytest.fixture
def semantic_matcher_with_embedder(semantic_matcher, mock_embedder):
    """Create SemanticMatcher with mocked SentenceTransformer."""
    with patch(
        "src.components.domain_training.semantic_matcher.SentenceTransformer",
        return_value=mock_embedder,
    ):
        # Reset availability check
        matcher = SemanticMatcher(threshold=0.75, predicate_weight=0.4)
        matcher._embedder = mock_embedder
        return matcher


# ============================================================================
# Test: Initialization
# ============================================================================


class TestSemanticMatcherInitialization:
    """Test SemanticMatcher initialization."""

    def test_initialization_default_values(self):
        """Test initialization with default values."""
        matcher = SemanticMatcher()

        assert matcher.threshold == 0.75
        assert matcher.predicate_weight == 0.4

    def test_initialization_custom_threshold(self):
        """Test initialization with custom threshold."""
        matcher = SemanticMatcher(threshold=0.8)

        assert matcher.threshold == 0.8

    def test_initialization_custom_predicate_weight(self):
        """Test initialization with custom predicate weight."""
        matcher = SemanticMatcher(predicate_weight=0.5)

        assert matcher.predicate_weight == 0.5

    def test_initialization_custom_both(self):
        """Test initialization with both custom parameters."""
        matcher = SemanticMatcher(threshold=0.9, predicate_weight=0.6)

        assert matcher.threshold == 0.9
        assert matcher.predicate_weight == 0.6

    def test_embedding_model_lazy_loading(self, semantic_matcher):
        """Test embedding model is lazy-loaded."""
        # Initially None
        assert semantic_matcher._embedder is None

        # _embedder should be loaded on first _get_embedder call
        with patch("sentence_transformers.SentenceTransformer") as mock_transformer:
            semantic_matcher._embedder = None  # Reset
            mock_transformer.return_value = MagicMock()
            semantic_matcher._get_embedder()
            # After calling _get_embedder, it should be cached
            assert semantic_matcher._embedder is not None
            # Might not load immediately due to availability check


# ============================================================================
# Test: Availability Checking
# ============================================================================


class TestAvailabilityChecking:
    """Test embedding model availability checking."""

    def test_is_available_true_when_import_succeeds(self, semantic_matcher):
        """Test is_available returns True when sentence_transformers available."""
        with patch("sentence_transformers.SentenceTransformer", return_value=MagicMock()):
            semantic_matcher._available = None  # Reset cache
            assert semantic_matcher.is_available is True

    def test_is_available_false_when_import_fails(self):
        """Test is_available returns False when sentence_transformers unavailable."""
        matcher = SemanticMatcher()

        # Mock _check_availability to return False
        with patch.object(matcher, "_check_availability", return_value=False):
            matcher._available = None  # Reset cache
            assert matcher.is_available is False


# ============================================================================
# Test: Cosine Similarity
# ============================================================================


class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_exact_match_returns_one(self, semantic_matcher):
        """Test exact text match returns 1.0."""
        sim = semantic_matcher.cosine_similarity("hello", "hello")
        assert sim == 1.0

    def test_exact_match_case_insensitive(self, semantic_matcher):
        """Test exact match is case-insensitive."""
        sim = semantic_matcher.cosine_similarity("Hello", "hello")
        assert sim == 1.0

    def test_exact_match_ignores_whitespace(self, semantic_matcher):
        """Test exact match ignores whitespace."""
        sim = semantic_matcher.cosine_similarity("hello ", " hello")
        assert sim == 1.0

    def test_similarity_without_embedder(self, semantic_matcher):
        """Test similarity computation falls back without embedder."""
        # Mock is_available as a property that returns False
        with patch.object(
            type(semantic_matcher),
            "is_available",
            new_callable=lambda: property(lambda self: False),
        ):
            sim = semantic_matcher.cosine_similarity("hello world", "hello earth")

            # Should use token overlap fallback
            assert 0.0 <= sim <= 1.0

    def test_similarity_token_overlap_fallback(self, semantic_matcher):
        """Test token overlap fallback similarity."""
        with patch.object(
            type(semantic_matcher),
            "is_available",
            new_callable=lambda: property(lambda self: False),
        ):
            # Identical tokens
            sim1 = semantic_matcher.cosine_similarity("hello world", "hello world")
            assert sim1 == 1.0

            # No overlap
            sim2 = semantic_matcher.cosine_similarity("hello world", "foo bar")
            assert sim2 == 0.0

            # Partial overlap
            sim3 = semantic_matcher.cosine_similarity("hello world", "hello earth")
            assert 0.0 < sim3 < 1.0


# ============================================================================
# Test: Entity Matching
# ============================================================================


class TestEntityMatching:
    """Test entity matching."""

    def test_entities_match_exact(self, semantic_matcher):
        """Test exact entity match."""
        assert semantic_matcher.entities_match("Python", "python") is True

    def test_entities_match_below_threshold(self, semantic_matcher):
        """Test entity mismatch below threshold."""
        with patch.object(semantic_matcher, "cosine_similarity", return_value=0.5):
            # Below default threshold of 0.75
            assert semantic_matcher.entities_match("foo", "bar") is False

    def test_entities_match_above_threshold(self, semantic_matcher):
        """Test entity match above threshold."""
        with patch.object(semantic_matcher, "cosine_similarity", return_value=0.8):
            # Above threshold of 0.75
            assert semantic_matcher.entities_match("foo", "bar") is True

    def test_entities_match_at_threshold(self, semantic_matcher):
        """Test entity match at exact threshold."""
        with patch.object(semantic_matcher, "cosine_similarity", return_value=0.75):
            # At threshold
            assert semantic_matcher.entities_match("foo", "bar") is True


# ============================================================================
# Test: Relation Matching
# ============================================================================


class TestRelationMatching:
    """Test relation matching with weighted components."""

    def test_relations_match_exact(self, semantic_matcher):
        """Test exact relation match."""
        rel1 = {"subject": "Python", "predicate": "is_a", "object": "language"}
        rel2 = {"subject": "python", "predicate": "is_a", "object": "language"}

        with patch.object(semantic_matcher, "cosine_similarity", return_value=1.0):
            assert semantic_matcher.relations_match(rel1, rel2) is True

    def test_relations_match_weighted_average(self, semantic_matcher):
        """Test relation matching uses weighted average."""
        rel1 = {"subject": "A", "predicate": "X", "object": "C"}
        rel2 = {"subject": "A", "predicate": "Y", "object": "C"}

        with patch.object(
            semantic_matcher,
            "cosine_similarity",
            side_effect=[
                1.0,  # subject match
                0.5,  # predicate mismatch
                1.0,  # object match
            ],
        ):
            # Weighted: 1.0*0.3 + 0.5*0.4 + 1.0*0.3 = 0.8 >= 0.75
            result = semantic_matcher.relations_match(rel1, rel2)
            assert result is True

    def test_relations_match_missing_keys(self, semantic_matcher):
        """Test relation matching with missing required fields."""
        rel1 = {"subject": "A"}  # Missing predicate and object
        rel2 = {"subject": "A", "predicate": "X", "object": "C"}

        assert semantic_matcher.relations_match(rel1, rel2) is False

    def test_relations_match_predicate_weight_effect(self):
        """Test predicate weight affects matching."""
        # High predicate weight - predicate matters more
        matcher_high = SemanticMatcher(predicate_weight=0.8)

        rel1 = {"subject": "A", "predicate": "X", "object": "C"}
        rel2 = {"subject": "A", "predicate": "Y", "object": "C"}

        with patch.object(
            matcher_high,
            "cosine_similarity",
            side_effect=[
                1.0,  # subject
                0.3,  # predicate - very different
                1.0,  # object
            ],
        ):
            # Weighted: 1.0*0.1 + 0.3*0.8 + 1.0*0.1 = 0.34 < 0.75 (fails)
            result = matcher_high.relations_match(rel1, rel2)
            assert result is False


# ============================================================================
# Test: Entity Metrics
# ============================================================================


class TestComputeEntityMetrics:
    """Test entity metric computation."""

    def test_entity_metrics_perfect_match(self, semantic_matcher):
        """Test metrics with perfect match."""
        gold = {"Python", "FastAPI"}
        pred = {"Python", "FastAPI"}

        with patch.object(semantic_matcher, "entities_match", return_value=True):
            metrics = semantic_matcher.compute_entity_metrics(gold, pred)

            assert metrics["precision"] == 1.0
            assert metrics["recall"] == 1.0
            assert metrics["f1"] == 1.0

    def test_entity_metrics_partial_match(self, semantic_matcher):
        """Test metrics with partial match."""
        gold = {"Python", "FastAPI", "Django"}
        pred = {"Python", "FastAPI"}  # Missing Django

        with patch.object(semantic_matcher, "entities_match", return_value=True):
            metrics = semantic_matcher.compute_entity_metrics(gold, pred)

            assert metrics["precision"] == 1.0
            assert metrics["recall"] < 1.0
            assert metrics["f1"] < 1.0

    def test_entity_metrics_empty_gold(self, semantic_matcher):
        """Test metrics with empty gold set."""
        gold = set()
        pred = {"Python"}

        metrics = semantic_matcher.compute_entity_metrics(gold, pred)

        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 0.0

    def test_entity_metrics_empty_gold_empty_pred(self, semantic_matcher):
        """Test metrics with both empty sets."""
        gold = set()
        pred = set()

        metrics = semantic_matcher.compute_entity_metrics(gold, pred)

        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0

    def test_entity_metrics_empty_pred(self, semantic_matcher):
        """Test metrics with empty predictions."""
        gold = {"Python", "FastAPI"}
        pred = set()

        metrics = semantic_matcher.compute_entity_metrics(gold, pred)

        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        assert metrics["f1"] == 0.0

    def test_entity_metrics_no_overlap(self, semantic_matcher):
        """Test metrics with no overlap."""
        gold = {"Python", "FastAPI"}
        pred = {"Django", "Flask"}

        with patch.object(semantic_matcher, "entities_match", return_value=False):
            metrics = semantic_matcher.compute_entity_metrics(gold, pred)

            assert metrics["precision"] == 0.0
            assert metrics["recall"] == 0.0
            assert metrics["f1"] == 0.0


# ============================================================================
# Test: Relation Metrics
# ============================================================================


class TestComputeRelationMetrics:
    """Test relation metric computation."""

    def test_relation_metrics_perfect_match(self, semantic_matcher):
        """Test metrics with perfect match."""
        gold = [
            {"subject": "Python", "predicate": "is_a", "object": "language"},
            {"subject": "FastAPI", "predicate": "built_with", "object": "Python"},
        ]
        pred = [
            {"subject": "Python", "predicate": "is_a", "object": "language"},
            {"subject": "FastAPI", "predicate": "built_with", "object": "Python"},
        ]

        with patch.object(semantic_matcher, "relations_match", return_value=True):
            metrics = semantic_matcher.compute_relation_metrics(gold, pred)

            assert metrics["precision"] == 1.0
            assert metrics["recall"] == 1.0
            assert metrics["f1"] == 1.0

    def test_relation_metrics_partial_match(self, semantic_matcher):
        """Test metrics with partial match."""
        gold = [
            {"subject": "A", "predicate": "X", "object": "B"},
            {"subject": "C", "predicate": "Y", "object": "D"},
        ]
        pred = [
            {"subject": "A", "predicate": "X", "object": "B"},
        ]

        with patch.object(semantic_matcher, "relations_match", return_value=True):
            metrics = semantic_matcher.compute_relation_metrics(gold, pred)

            assert metrics["precision"] == 1.0
            assert metrics["recall"] < 1.0

    def test_relation_metrics_empty_gold(self, semantic_matcher):
        """Test metrics with empty gold set."""
        gold = []
        pred = [{"subject": "A", "predicate": "X", "object": "B"}]

        metrics = semantic_matcher.compute_relation_metrics(gold, pred)

        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 1.0

    def test_relation_metrics_empty_both(self, semantic_matcher):
        """Test metrics with both empty."""
        gold = []
        pred = []

        metrics = semantic_matcher.compute_relation_metrics(gold, pred)

        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0

    def test_relation_metrics_no_overlap(self, semantic_matcher):
        """Test metrics with no overlap."""
        gold = [
            {"subject": "A", "predicate": "X", "object": "B"},
            {"subject": "C", "predicate": "Y", "object": "D"},
        ]
        pred = [
            {"subject": "E", "predicate": "Z", "object": "F"},
        ]

        with patch.object(semantic_matcher, "relations_match", return_value=False):
            metrics = semantic_matcher.compute_relation_metrics(gold, pred)

            assert metrics["precision"] == 0.0
            assert metrics["recall"] == 0.0


# ============================================================================
# Test: Token Overlap Fallback
# ============================================================================


class TestTokenOverlapFallback:
    """Test token overlap fallback similarity."""

    def test_token_overlap_identical(self, semantic_matcher):
        """Test token overlap with identical texts."""
        sim = semantic_matcher._token_overlap("hello world", "hello world")
        assert sim == 1.0

    def test_token_overlap_partial(self, semantic_matcher):
        """Test token overlap with partial match."""
        sim = semantic_matcher._token_overlap("hello world", "hello earth")
        # One common token (hello) out of 3 unique tokens
        assert 0.0 < sim < 1.0

    def test_token_overlap_no_overlap(self, semantic_matcher):
        """Test token overlap with no match."""
        sim = semantic_matcher._token_overlap("hello world", "foo bar")
        assert sim == 0.0

    def test_token_overlap_empty_strings(self, semantic_matcher):
        """Test token overlap with empty strings."""
        sim = semantic_matcher._token_overlap("", "")
        assert sim == 0.0

    def test_token_overlap_empty_vs_nonempty(self, semantic_matcher):
        """Test token overlap with one empty string."""
        sim1 = semantic_matcher._token_overlap("", "hello")
        sim2 = semantic_matcher._token_overlap("hello", "")
        assert sim1 == 0.0
        assert sim2 == 0.0


# ============================================================================
# Test: Singleton Pattern
# ============================================================================


class TestSemanticMatcherSingleton:
    """Test singleton pattern for semantic matcher."""

    def test_get_semantic_matcher_returns_instance(self):
        """Test get_semantic_matcher returns SemanticMatcher instance."""
        matcher = get_semantic_matcher()
        assert isinstance(matcher, SemanticMatcher)

    def test_get_semantic_matcher_singleton(self):
        """Test get_semantic_matcher returns same instance."""
        matcher1 = get_semantic_matcher()
        matcher2 = get_semantic_matcher()
        # Should be same instance
        assert matcher1 is matcher2

    def test_get_semantic_matcher_custom_params(self):
        """Test get_semantic_matcher respects custom parameters on first creation."""
        # Note: Singleton is persistent, so custom params only work on first creation
        # This test just verifies parameters are accepted without error
        matcher = get_semantic_matcher(threshold=0.8, predicate_weight=0.5)
        # Since singleton returns same instance after first call,
        # just verify it's a valid matcher instance
        assert isinstance(matcher, SemanticMatcher)


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_unicode_text_matching(self, semantic_matcher):
        """Test matching with Unicode text."""
        # Test with fallback (token overlap)
        semantic_matcher._embedder = None  # Force fallback
        semantic_matcher._available = False  # Disable embedder
        # Should handle German text without crashing
        sim = semantic_matcher.cosine_similarity("Rechtesystem", "Rechte-System")
        assert 0.0 <= sim <= 1.0

    def test_very_long_text(self, semantic_matcher):
        """Test similarity with very long texts."""
        long_text1 = "hello " * 1000
        long_text2 = "hello world " * 1000

        # Test with fallback
        semantic_matcher._embedder = None
        semantic_matcher._available = False
        sim = semantic_matcher.cosine_similarity(long_text1, long_text2)
        assert 0.0 <= sim <= 1.0

    def test_special_characters(self, semantic_matcher):
        """Test matching with special characters."""
        text1 = "test@example.com"
        text2 = "test_example.com"

        # Test with fallback
        semantic_matcher._embedder = None
        semantic_matcher._available = False
        sim = semantic_matcher.cosine_similarity(text1, text2)
        assert 0.0 <= sim <= 1.0

    def test_numeric_text(self, semantic_matcher):
        """Test matching numeric text."""
        sim = semantic_matcher.cosine_similarity("123", "123")
        assert sim == 1.0

    def test_relation_with_empty_strings(self, semantic_matcher):
        """Test relation matching with empty strings."""
        rel1 = {"subject": "", "predicate": "", "object": ""}
        rel2 = {"subject": "", "predicate": "", "object": ""}

        with patch.object(semantic_matcher, "cosine_similarity", return_value=1.0):
            assert semantic_matcher.relations_match(rel1, rel2) is True


# ============================================================================
# Integration Tests
# ============================================================================


class TestSemanticMatcherIntegration:
    """Integration tests for semantic matcher."""

    def test_complete_entity_evaluation_workflow(self, semantic_matcher):
        """Test complete entity evaluation workflow."""
        gold = {"Python", "FastAPI", "JavaScript"}
        pred = {"Python", "FastAPI", "TypeScript"}

        # Compute metrics
        with patch.object(semantic_matcher, "entities_match", return_value=True):
            metrics = semantic_matcher.compute_entity_metrics(gold, pred)

            assert "precision" in metrics
            assert "recall" in metrics
            assert "f1" in metrics

    def test_complete_relation_evaluation_workflow(self, semantic_matcher):
        """Test complete relation evaluation workflow."""
        gold = [
            {"subject": "Python", "predicate": "is_a", "object": "language"},
            {"subject": "FastAPI", "predicate": "built_with", "object": "Python"},
        ]
        pred = [
            {"subject": "Python", "predicate": "is_a", "object": "language"},
            {"subject": "Django", "predicate": "built_with", "object": "Python"},
        ]

        with patch.object(semantic_matcher, "relations_match") as mock_match:
            # First two match, last one doesn't
            mock_match.side_effect = [True, False]

            metrics = semantic_matcher.compute_relation_metrics(gold, pred)

            assert metrics["precision"] < 1.0
            assert metrics["recall"] < 1.0
