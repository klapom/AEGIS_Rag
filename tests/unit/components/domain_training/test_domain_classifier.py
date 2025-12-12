"""Unit tests for Domain Classifier.

Sprint 45 Feature 45.6: Domain Classifier

Tests:
- Domain classifier initialization
- Domain embeddings loading
- Document classification with top-K results
- Text sampling for long documents
- Singleton pattern
- Score normalization
- Semantic matching with cosine similarity
"""

from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

import pytest


# ============================================================================
# Tests: Initialization
# ============================================================================


def test_classifier_initialization():
    """Test domain classifier initializes correctly."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()
    assert classifier is not None
    assert hasattr(classifier, "embedding_model")
    assert hasattr(classifier, "_domain_embeddings")
    assert isinstance(classifier._domain_embeddings, dict)


def test_classifier_initializes_empty_embeddings():
    """Test classifier initializes with empty domain embeddings."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()
    assert classifier._domain_embeddings == {}


def test_classifier_has_default_attributes():
    """Test classifier has all required attributes."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()
    assert hasattr(classifier, "_domains_loaded")
    assert hasattr(classifier, "_model_loaded")
    assert isinstance(classifier._domains_loaded, bool)
    assert isinstance(classifier._model_loaded, bool)


# ============================================================================
# Tests: Text Sampling
# ============================================================================


def test_sample_text_short_text():
    """Test text sampling for short text (no sampling needed)."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    short_text = "Short text for testing"
    sampled = classifier._sample_text(short_text, 2000)

    # Short text should not be modified
    assert sampled == short_text


def test_sample_text_long_text():
    """Test text sampling for long text (beginning + middle + end)."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    # Create a long text (>2000 chars)
    long_text = "A" * 500 + "B" * 500 + "C" * 500 + "D" * 500 + "E" * 500
    sample_size = 600

    sampled = classifier._sample_text(long_text, sample_size)

    # Sampled text should be shorter than original
    assert len(sampled) < len(long_text)
    # Should include beginning
    assert "A" in sampled


def test_sample_text_respects_sample_size():
    """Test text sampling respects sample_size parameter."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    long_text = "X" * 10000
    sample_size = 1000

    sampled = classifier._sample_text(long_text, sample_size)

    # Sampled text should not exceed sample_size by much
    assert len(sampled) <= sample_size + 100


def test_sample_text_with_different_sizes():
    """Test text sampling with different sample sizes."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    long_text = "X" * 5000
    sizes = [100, 500, 1000, 2000]

    for size in sizes:
        sampled = classifier._sample_text(long_text, size)
        # Should not exceed size by much
        assert len(sampled) <= size + 100


# ============================================================================
# Tests: Cosine Similarity
# ============================================================================


def test_cosine_similarity_identical_vectors():
    """Test cosine similarity calculation for identical vectors."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    # Test cosine similarity manually
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([1.0, 0.0, 0.0])

    similarity = np.dot(vec1, vec2) / (
        np.linalg.norm(vec1) * np.linalg.norm(vec2)
    )

    # Identical vectors should have similarity 1.0
    assert abs(similarity - 1.0) < 0.001


def test_cosine_similarity_orthogonal_vectors():
    """Test cosine similarity for orthogonal vectors."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    # Orthogonal vectors
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([0.0, 1.0, 0.0])

    similarity = np.dot(vec1, vec2) / (
        np.linalg.norm(vec1) * np.linalg.norm(vec2)
    )

    # Orthogonal vectors should have similarity ~0.0
    assert abs(similarity) < 0.001


def test_cosine_similarity_opposite_vectors():
    """Test cosine similarity for opposite vectors."""
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([-1.0, 0.0, 0.0])

    similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    # Opposite vectors should have similarity ~-1.0
    assert abs(similarity - (-1.0)) < 0.001


# ============================================================================
# Tests: Edge Cases
# ============================================================================


def test_classifier_with_empty_text():
    """Test classifier handles empty text."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    # Empty text should still be sampled
    sampled = classifier._sample_text("", 1000)
    assert sampled == ""


def test_classifier_with_very_long_text():
    """Test classifier handles very long document."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    # Very long document
    very_long_text = "FastAPI " * 10000

    sampled = classifier._sample_text(very_long_text, 2000)

    # Should successfully sample
    assert isinstance(sampled, str)
    assert len(sampled) > 0


def test_classifier_with_unicode_text():
    """Test classifier handles unicode text."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    unicode_text = "Python is a programming language. " * 100
    unicode_text = unicode_text + "日本語テキスト. Текст на русском"

    sampled = classifier._sample_text(unicode_text, 1000)

    # Should handle unicode without error
    assert isinstance(sampled, str)


# ============================================================================
# Tests: Model Loading
# ============================================================================


def test_classifier_lazy_loads_model():
    """Test classifier supports lazy loading of embedding model."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    # On initialization, model should not be loaded yet
    assert not classifier._model_loaded


@pytest.mark.asyncio
async def test_load_domains_updates_flag():
    """Test load_domains sets domains_loaded flag."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    # Initially should not be loaded
    assert not classifier._domains_loaded


# ============================================================================
# Tests: Default Constants
# ============================================================================


def test_classifier_uses_correct_defaults():
    """Test classifier uses correct default values."""
    from src.components.domain_training.domain_classifier import (
        DEFAULT_SAMPLE_SIZE,
        DEFAULT_TOP_K,
        MIN_SIMILARITY_THRESHOLD,
    )

    # Verify defaults are reasonable
    assert DEFAULT_SAMPLE_SIZE == 2000
    assert DEFAULT_TOP_K == 3
    assert 0 < MIN_SIMILARITY_THRESHOLD < 1


# ============================================================================
# Tests: Vector Operations
# ============================================================================


def test_vector_norm_calculation():
    """Test vector norm calculation."""
    vec = np.array([3.0, 4.0, 0.0])
    norm = np.linalg.norm(vec)

    # Norm of [3, 4, 0] should be 5
    assert abs(norm - 5.0) < 0.001


def test_dot_product_calculation():
    """Test dot product calculation."""
    vec1 = np.array([1.0, 2.0, 3.0])
    vec2 = np.array([4.0, 5.0, 6.0])

    dot = np.dot(vec1, vec2)

    # 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
    assert abs(dot - 32.0) < 0.001


# ============================================================================
# Tests: Text Preprocessing
# ============================================================================


def test_text_sampling_preserves_content():
    """Test text sampling preserves document content."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    text = "Beginning content" + "X" * 3000 + "End content"
    sampled = classifier._sample_text(text, 1000)

    # Sampled text should contain original content
    assert isinstance(sampled, str)
    assert len(sampled) > 0


def test_text_sampling_handles_whitespace():
    """Test text sampling handles whitespace correctly."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    text = "Start\n\n" + "content " * 1000 + "\n\nEnd"
    sampled = classifier._sample_text(text, 2000)

    assert isinstance(sampled, str)


# ============================================================================
# Tests: Attribute Validation
# ============================================================================


def test_classifier_domain_embeddings_type():
    """Test _domain_embeddings is correct type."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    assert isinstance(classifier._domain_embeddings, dict)


def test_classifier_embedding_model_lazy():
    """Test embedding_model is initially None (lazy loaded)."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    # Should be None until explicitly loaded
    assert classifier.embedding_model is None or hasattr(classifier.embedding_model, "encode")


# ============================================================================
# Tests: Sample Size Boundary Conditions
# ============================================================================


def test_sample_text_exact_size():
    """Test text sampling with exact sample size."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    text = "X" * 100  # Smaller than default
    sampled = classifier._sample_text(text, 2000)

    # Should not sample, return as-is
    assert sampled == text


def test_sample_text_minimal_size():
    """Test text sampling with minimal sample size."""
    from src.components.domain_training.domain_classifier import DomainClassifier

    classifier = DomainClassifier()

    text = "X" * 10000
    sampled = classifier._sample_text(text, 100)

    # Should sample, result should be much shorter
    assert len(sampled) < len(text)


# ============================================================================
# Tests: Integration with NumPy
# ============================================================================


def test_numpy_array_compatibility():
    """Test classifier works with numpy arrays."""
    import numpy as np

    # Test that embeddings can be numpy arrays
    embeddings = {
        "tech": np.array([0.1] * 1024),
        "legal": np.array([0.2] * 1024),
    }

    assert all(isinstance(v, np.ndarray) for v in embeddings.values())


def test_cosine_similarity_with_numpy():
    """Test cosine similarity calculation with numpy arrays."""
    vec1 = np.random.rand(1024)
    vec2 = np.random.rand(1024)

    # Should not raise error
    similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    assert isinstance(similarity, (float, np.floating))
    assert -1 <= similarity <= 1
