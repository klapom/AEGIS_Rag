"""Unit tests for SemanticDeduplicator.

Tests semantic entity deduplication using sentence-transformers including:
- Initialization with various configurations
- Deduplication logic (happy path)
- Edge cases (empty lists, single entities, no duplicates)
- Type grouping and cross-type isolation
- Similarity threshold behavior
- Error handling (missing dependencies, invalid inputs)
- Factory function from config
- Device selection (CPU/CUDA)
- Performance tracking and logging

Sprint 13 Feature 13.9: ADR-017 Semantic Entity Deduplication
Target Coverage: 60%+ (20+ tests)
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer model."""
    model = MagicMock()
    # Mock encode to return embeddings with shape (batch_size, 384)
    model.encode.return_value = MagicMock()
    model.encode.return_value.cpu.return_value.numpy.return_value = [
        [0.1] * 384,  # Entity 1 embedding
        [0.1] * 384,  # Entity 2 embedding (identical - will be duplicate)
        [0.5] * 384,  # Entity 3 embedding (different)
    ]
    return model


@pytest.fixture
def mock_torch():
    """Mock torch module."""
    mock = MagicMock()
    mock.cuda.is_available.return_value = False
    mock.cuda.get_device_name.return_value = "NVIDIA RTX 3090"
    mock.cuda.get_device_properties.return_value.total_memory = 24 * 1024**3  # 24GB
    return mock


@pytest.fixture
def mock_sklearn():
    """Mock sklearn cosine_similarity."""
    import numpy as np

    def mock_cosine_similarity(embeddings):
        """Mock cosine similarity matrix."""
        n = len(embeddings)
        similarity = np.eye(n)  # Identity matrix (1.0 on diagonal)
        # Make first two entities similar (0.95)
        if n >= 2:
            similarity[0, 1] = 0.95
            similarity[1, 0] = 0.95
        return similarity

    return mock_cosine_similarity


@pytest.fixture
def sample_entities() -> list[dict[str, Any]]:
    """Sample entities for testing."""
    return [
        {"name": "Alex", "type": "PERSON", "description": "Software engineer at Anthropic"},
        {"name": "Alex", "type": "PERSON", "description": "AI researcher"},  # Duplicate
        {"name": "Alexander", "type": "PERSON", "description": "Team lead"},  # Similar name
        {"name": "Jordan", "type": "PERSON", "description": "Product manager"},
        {"name": "Anthropic", "type": "ORGANIZATION", "description": "AI safety company"},
        {"name": "OpenAI", "type": "ORGANIZATION", "description": "AI research lab"},
    ]


@pytest.fixture
def sample_entities_no_duplicates() -> list[dict[str, Any]]:
    """Sample entities with no duplicates."""
    return [
        {"name": "Alice", "type": "PERSON", "description": "Engineer"},
        {"name": "Bob", "type": "PERSON", "description": "Designer"},
        {"name": "Carol", "type": "PERSON", "description": "Manager"},
    ]


@pytest.fixture
def mock_config():
    """Mock application config."""
    config = MagicMock()
    config.enable_semantic_dedup = True
    config.semantic_dedup_model = "sentence-transformers/all-MiniLM-L6-v2"
    config.semantic_dedup_threshold = 0.93
    config.semantic_dedup_device = "auto"
    return config


# ============================================================================
# Test Initialization
# ============================================================================


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_semantic_deduplicator_init_default(mock_get_singleton):
    """Test initialization with default parameters (Sprint 20.3 Singleton)."""
    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Default initialization with singleton
    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # When: Initialize deduplicator
    dedup = SemanticDeduplicator()

    # Then: Verify initialization uses singleton
    assert dedup.model == mock_model
    assert dedup.threshold == 0.93
    assert dedup.device == "cpu"
    mock_get_singleton.assert_called_once_with(
        model_name="sentence-transformers/all-MiniLM-L6-v2", device="cpu"
    )


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_semantic_deduplicator_init_custom_params(mock_get_singleton):
    """Test initialization with custom parameters (Sprint 20.3 Singleton)."""
    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Custom parameters with singleton
    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # When: Initialize with custom params
    dedup = SemanticDeduplicator(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        threshold=0.90,
        device="cuda",
    )

    # Then: Verify custom configuration uses singleton
    assert dedup.model == mock_model
    assert dedup.threshold == 0.90
    assert dedup.device == "cuda"
    mock_get_singleton.assert_called_once_with(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", device="cuda"
    )


# Sprint 20.5: Auto-device detection removed - tests disabled
# Device now defaults to 'cpu' to free VRAM for LLMs
# @patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
# @patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
# def test_semantic_deduplicator_init_auto_device_cpu(mock_get_singleton):
#     """Test device defaults to CPU (Sprint 20.5)."""
#     pass

# @patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
# @patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
# def test_semantic_deduplicator_init_auto_device_cuda(mock_get_singleton):
#     """Test explicit CUDA device selection (Sprint 20.5)."""
#     pass


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", False)
def test_semantic_deduplicator_init_missing_dependencies():
    """Test initialization fails gracefully when dependencies missing."""
    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # When/Then: Should raise ImportError
    with pytest.raises(ImportError) as exc_info:
        SemanticDeduplicator()

    assert "sentence-transformers required" in str(exc_info.value)


# ============================================================================
# Test Deduplication Logic
# ============================================================================


# Check if sklearn is available for this test
try:
    from sklearn.metrics.pairwise import cosine_similarity as _sklearn_available

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="sklearn not installed - optional dependency")
@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_deduplicate_with_duplicates(mock_get_singleton, sample_entities):
    """Test deduplication removes duplicate entities (Sprint 20.3 Singleton)."""
    import numpy as np

    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Deduplicator and entities with duplicates
    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # Mock embeddings - first two PERSON entities are similar
    embeddings_np = np.array([[0.1] * 384, [0.1] * 384, [0.5] * 384, [0.9] * 384])
    mock_model.encode.return_value.cpu.return_value.numpy.return_value = embeddings_np

    # Mock cosine similarity - first two entities highly similar
    similarity = np.eye(4)
    similarity[0, 1] = 0.95  # High similarity between first two
    similarity[1, 0] = 0.95

    with patch(
        "src.components.graph_rag.semantic_deduplicator.cosine_similarity",
        return_value=similarity,
    ):
        dedup = SemanticDeduplicator(threshold=0.93)

        # Get only PERSON entities for this test
        person_entities = [e for e in sample_entities if e["type"] == "PERSON"][:4]

        # When: Deduplicate
        result = dedup.deduplicate(person_entities)

        # Then: Should merge first two entities
        assert len(result) < len(person_entities)
        assert any("[Deduplicated from" in r["description"] for r in result)


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_deduplicate_empty_list(mock_get_singleton):
    """Test deduplication with empty entity list."""
    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Empty entity list
    mock_get_singleton.return_value = MagicMock()
    dedup = SemanticDeduplicator()

    # When: Deduplicate empty list
    result = dedup.deduplicate([])

    # Then: Should return empty list
    assert result == []


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="sklearn not installed - optional dependency")
@patch("src.components.graph_rag.semantic_deduplicator.cosine_similarity")
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_deduplicate_no_duplicates(
    mock_get_singleton, mock_cosine_sim, sample_entities_no_duplicates
):
    """Test deduplication with no duplicate entities (Sprint 20.3 Singleton)."""
    import numpy as np

    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Entities with no duplicates
    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # Mock embeddings - all different
    n = len(sample_entities_no_duplicates)
    embeddings_np = np.array([[i * 0.1] * 384 for i in range(n)])
    mock_model.encode.return_value.cpu.return_value.numpy.return_value = embeddings_np

    # Mock cosine similarity - all below threshold
    similarity = np.eye(n) * 0.5  # Low similarity
    mock_cosine_sim.return_value = similarity

    dedup = SemanticDeduplicator(threshold=0.93)

    # When: Deduplicate
    result = dedup.deduplicate(sample_entities_no_duplicates)

    # Then: Should keep all entities
    assert len(result) == len(sample_entities_no_duplicates)


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_deduplicate_single_entity(mock_get_singleton):
    """Test deduplication with single entity."""
    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Single entity
    mock_get_singleton.return_value = MagicMock()
    dedup = SemanticDeduplicator()

    single_entity = [{"name": "Alice", "type": "PERSON", "description": "Engineer"}]

    # When: Deduplicate
    result = dedup.deduplicate(single_entity)

    # Then: Should return same entity
    assert len(result) == 1
    assert result[0]["name"] == "Alice"


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="sklearn not installed - optional dependency")
@patch("src.components.graph_rag.semantic_deduplicator.cosine_similarity")
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_deduplicate_groups_by_type(mock_get_singleton, mock_cosine_sim, sample_entities):
    """Test deduplication groups entities by type before comparing (Sprint 20.3 Singleton)."""
    import numpy as np

    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Entities of different types
    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # Mock embeddings for each type group
    def mock_encode(names, **kwargs):
        """Mock encode that tracks calls per type group."""
        result = MagicMock()
        result.cpu.return_value.numpy.return_value = np.array(
            [[0.1] * 384 for _ in range(len(names))]
        )
        return result

    mock_model.encode.side_effect = mock_encode

    # Mock cosine similarity - all low similarity
    mock_cosine_sim.side_effect = lambda x: np.eye(len(x)) * 0.5

    dedup = SemanticDeduplicator(threshold=0.93)

    # When: Deduplicate mixed types
    result = dedup.deduplicate(sample_entities)

    # Then: Should process each type group separately
    assert len(result) == len(sample_entities)  # No duplicates with low similarity
    # Verify all types are preserved
    result_types = {e["type"] for e in result}
    original_types = {e["type"] for e in sample_entities}
    assert result_types == original_types


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="sklearn not installed - optional dependency")
@patch("src.components.graph_rag.semantic_deduplicator.cosine_similarity")
def test_deduplicate_threshold_sensitivity(mock_cosine_sim, mock_get_singleton):
    """Test deduplication behavior with different threshold values."""
    import numpy as np

    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Two similar entities
    entities = [
        {"name": "Alex", "type": "PERSON", "description": "Engineer"},
        {"name": "Alex", "type": "PERSON", "description": "Developer"},
    ]

    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # Mock embeddings - moderate similarity (0.92)
    embeddings_np = np.array([[0.1] * 384, [0.15] * 384])
    mock_model.encode.return_value.cpu.return_value.numpy.return_value = embeddings_np

    # Similarity is 0.92
    similarity = np.array([[1.0, 0.92], [0.92, 1.0]])
    mock_cosine_sim.return_value = similarity

    # When: Test with high threshold (should not merge)
    dedup_high = SemanticDeduplicator(threshold=0.95)
    result_high = dedup_high.deduplicate(entities)

    # Then: Should keep both entities
    assert len(result_high) == 2

    # When: Test with low threshold (should merge)
    dedup_low = SemanticDeduplicator(threshold=0.90)
    result_low = dedup_low.deduplicate(entities)

    # Then: Should merge entities
    assert len(result_low) == 1


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="sklearn not installed - optional dependency")
@patch("src.components.graph_rag.semantic_deduplicator.cosine_similarity")
def test_deduplicate_preserves_first_entity(mock_cosine_sim, mock_get_singleton):
    """Test deduplication keeps first entity as representative."""
    import numpy as np

    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Three similar entities
    entities = [
        {"name": "Alice", "type": "PERSON", "description": "First"},
        {"name": "Alice", "type": "PERSON", "description": "Second"},
        {"name": "Alice", "type": "PERSON", "description": "Third"},
    ]

    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # Mock embeddings - all identical
    embeddings_np = np.array([[0.1] * 384, [0.1] * 384, [0.1] * 384])
    mock_model.encode.return_value.cpu.return_value.numpy.return_value = embeddings_np

    # All highly similar
    similarity = np.ones((3, 3))
    mock_cosine_sim.return_value = similarity

    dedup = SemanticDeduplicator(threshold=0.93)

    # When: Deduplicate
    result = dedup.deduplicate(entities)

    # Then: Should keep only first entity name
    assert len(result) == 1
    assert result[0]["name"] == "Alice"
    assert "[Deduplicated from 3 mentions]" in result[0]["description"]


# ============================================================================
# Test Edge Cases
# ============================================================================


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_deduplicate_missing_type_field(mock_get_singleton):
    """Test deduplication handles entities missing 'type' field."""
    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Entities without type field
    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    entities = [
        {"name": "Alice", "description": "Engineer"},  # Missing type
        {"name": "Bob", "type": "PERSON", "description": "Designer"},
    ]

    dedup = SemanticDeduplicator()

    # When: Deduplicate
    result = dedup.deduplicate(entities)

    # Then: Should handle gracefully (assigns "OTHER" type)
    assert len(result) == 2


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="sklearn not installed - optional dependency")
@patch("src.components.graph_rag.semantic_deduplicator.cosine_similarity")
def test_deduplicate_multiple_type_groups(mock_cosine_sim, mock_get_singleton):
    """Test deduplication correctly handles multiple entity types."""
    import numpy as np

    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Multiple entity types
    entities = [
        {"name": "Alice", "type": "PERSON", "description": "Engineer"},
        {"name": "Bob", "type": "PERSON", "description": "Designer"},
        {"name": "Anthropic", "type": "ORGANIZATION", "description": "AI company"},
        {"name": "Python", "type": "TECHNOLOGY", "description": "Language"},
    ]

    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # Mock encode called once per type group
    def mock_encode_side_effect(names, **kwargs):
        result = MagicMock()
        result.cpu.return_value.numpy.return_value = np.array(
            [[i * 0.1] * 384 for i in range(len(names))]
        )
        return result

    mock_model.encode.side_effect = mock_encode_side_effect

    # Mock cosine similarity - low similarity within groups
    mock_cosine_sim.side_effect = lambda x: np.eye(len(x)) * 0.5

    dedup = SemanticDeduplicator(threshold=0.93)

    # When: Deduplicate
    result = dedup.deduplicate(entities)

    # Then: Should preserve all entities (no duplicates)
    assert len(result) == 4
    # Verify all types are preserved (each type group processed separately)
    result_types = {e["type"] for e in result}
    original_types = {e["type"] for e in entities}
    assert result_types == original_types


# ============================================================================
# Test Factory Function
# ============================================================================


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_create_deduplicator_from_config_enabled(mock_get_singleton, mock_config):
    """Test factory function creates deduplicator from config."""
    from src.components.graph_rag.semantic_deduplicator import (
        create_deduplicator_from_config,
    )

    # Given: Config with deduplication enabled
    mock_get_singleton.return_value = MagicMock()

    # When: Create from config
    dedup = create_deduplicator_from_config(mock_config)

    # Then: Should create deduplicator
    assert dedup is not None
    assert dedup.threshold == 0.93
    mock_get_singleton.assert_called_once()


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
def test_create_deduplicator_from_config_disabled(mock_config):
    """Test factory function returns None when deduplication disabled."""
    from src.components.graph_rag.semantic_deduplicator import (
        create_deduplicator_from_config,
    )

    # Given: Config with deduplication disabled
    mock_config.enable_semantic_dedup = False

    # When: Create from config
    dedup = create_deduplicator_from_config(mock_config)

    # Then: Should return None
    assert dedup is None


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_create_deduplicator_from_config_auto_device(mock_get_singleton, mock_config):
    """Test factory function handles 'auto' device setting (Sprint 20.3 Singleton)."""
    from src.components.graph_rag.semantic_deduplicator import (
        create_deduplicator_from_config,
    )

    # Given: Config with device='auto'
    mock_config.semantic_dedup_device = "auto"
    mock_get_singleton.return_value = MagicMock()

    # When: Create from config
    dedup = create_deduplicator_from_config(mock_config)

    # Then: Should convert 'auto' to None for auto-detection
    assert dedup is not None
    assert dedup.device == "cpu"


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_create_deduplicator_from_config_custom_model(mock_get_singleton, mock_config):
    """Test factory function uses custom model from config (Sprint 20.3 Singleton)."""
    from src.components.graph_rag.semantic_deduplicator import (
        create_deduplicator_from_config,
    )

    # Given: Config with custom model
    mock_config.semantic_dedup_model = "sentence-transformers/paraphrase-MiniLM-L3-v2"
    mock_get_singleton.return_value = MagicMock()

    # When: Create from config
    dedup = create_deduplicator_from_config(mock_config)

    # Then: Should use custom model
    assert dedup is not None
    mock_get_singleton.assert_called_once_with(
        model_name="sentence-transformers/paraphrase-MiniLM-L3-v2", device="cpu"
    )


# ============================================================================
# Test Description Merging
# ============================================================================


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="sklearn not installed - optional dependency")
@patch("src.components.graph_rag.semantic_deduplicator.cosine_similarity")
def test_deduplicate_merges_descriptions(mock_cosine_sim, mock_get_singleton):
    """Test deduplication merges descriptions from duplicate entities."""
    import numpy as np

    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Two duplicate entities
    entities = [
        {"name": "Alice", "type": "PERSON", "description": "Original description"},
        {"name": "Alice", "type": "PERSON", "description": "Duplicate description"},
    ]

    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # Mock embeddings - identical
    embeddings_np = np.array([[0.1] * 384, [0.1] * 384])
    mock_model.encode.return_value.cpu.return_value.numpy.return_value = embeddings_np

    # High similarity
    similarity = np.array([[1.0, 0.95], [0.95, 1.0]])
    mock_cosine_sim.return_value = similarity

    dedup = SemanticDeduplicator(threshold=0.93)

    # When: Deduplicate
    result = dedup.deduplicate(entities)

    # Then: Should merge descriptions
    assert len(result) == 1
    assert "[Deduplicated from 2 mentions]" in result[0]["description"]
    assert "Original description" in result[0]["description"]


# ============================================================================
# Test Performance and Logging
# ============================================================================


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="sklearn not installed - optional dependency")
@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
@patch("src.components.graph_rag.semantic_deduplicator.logger")
def test_deduplicate_logs_statistics(mock_logger, mock_get_singleton):
    """Test deduplication logs statistics about removed/kept entities."""
    import numpy as np

    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Entities
    entities = [
        {"name": "Alice", "type": "PERSON", "description": "Engineer"},
        {"name": "Bob", "type": "PERSON", "description": "Designer"},
    ]

    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # Mock embeddings
    embeddings_np = np.array([[0.1] * 384, [0.5] * 384])
    mock_model.encode.return_value.cpu.return_value.numpy.return_value = embeddings_np

    dedup = SemanticDeduplicator()

    # When: Deduplicate
    with patch("src.components.graph_rag.semantic_deduplicator.cosine_similarity") as mock_cs:
        mock_cs.return_value = np.eye(2) * 0.5  # Low similarity
        dedup.deduplicate(entities)

    # Then: Should log statistics
    assert mock_logger.info.called


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="sklearn not installed - optional dependency")
@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_deduplicate_batch_processing(mock_get_singleton):
    """Test deduplication uses batch encoding for efficiency."""
    import numpy as np

    from src.components.graph_rag.semantic_deduplicator import SemanticDeduplicator

    # Given: Large entity list
    entities = [
        {"name": f"Person_{i}", "type": "PERSON", "description": f"Description {i}"}
        for i in range(100)
    ]

    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # Mock embeddings
    embeddings_np = np.array([[i * 0.01] * 384 for i in range(100)])
    mock_model.encode.return_value.cpu.return_value.numpy.return_value = embeddings_np

    dedup = SemanticDeduplicator()

    # When: Deduplicate
    with patch("src.components.graph_rag.semantic_deduplicator.cosine_similarity") as mock_cs:
        mock_cs.return_value = np.eye(100) * 0.5  # Low similarity
        dedup.deduplicate(entities)

    # Then: Should call encode with batch_size parameter
    mock_model.encode.assert_called()
    call_kwargs = mock_model.encode.call_args[1]
    assert "batch_size" in call_kwargs
    assert call_kwargs["batch_size"] == 64


# ============================================================================
# Sprint 43: MultiCriteriaDeduplicator Tests (ADR-044, TD-062)
# ============================================================================


@pytest.fixture
def nicolas_cage_entities() -> list[dict[str, Any]]:
    """Nicolas Cage test case entities for multi-criteria deduplication."""
    return [
        {"name": "Nicolas Cage", "type": "PERSON", "description": "American actor"},
        {"name": "nicolas cage", "type": "PERSON", "description": "Oscar winner"},  # Case variant
        {"name": "Nicholas Cage", "type": "PERSON", "description": "Born 1964"},  # Typo
        {"name": "Nick Cage", "type": "PERSON", "description": "Film star"},  # Semantic variant
        {"name": "Cage", "type": "PERSON", "description": "Actor in Leaving Las Vegas"},  # Short name
        {"name": "Mike Figgis", "type": "PERSON", "description": "Director"},  # Different person
    ]


@pytest.fixture
def short_entity_names() -> list[dict[str, Any]]:
    """Entities with short names to test min-length guards."""
    return [
        {"name": "AI", "type": "TECHNOLOGY", "description": "Artificial Intelligence"},
        {"name": "UI", "type": "TECHNOLOGY", "description": "User Interface"},
        {"name": "NVIDIA", "type": "ORGANIZATION", "description": "GPU maker"},
    ]


@pytest.fixture
def mock_config_multi_criteria():
    """Mock config with multi-criteria deduplication enabled."""
    config = MagicMock()
    config.enable_semantic_dedup = True
    config.enable_multi_criteria_dedup = True
    config.semantic_dedup_model = "sentence-transformers/all-MiniLM-L6-v2"
    config.semantic_dedup_threshold = 0.93
    config.semantic_dedup_device = "cpu"
    config.dedup_edit_distance_threshold = 3
    config.dedup_min_length_for_edit = 5
    config.dedup_min_length_for_substring = 6
    return config


# ============================================================================
# Test MultiCriteriaDeduplicator Initialization
# ============================================================================


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_multi_criteria_deduplicator_init_default(mock_get_singleton):
    """Test MultiCriteriaDeduplicator initialization with defaults."""
    from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator

    # Given: Default initialization
    mock_get_singleton.return_value = MagicMock()

    # When: Initialize
    dedup = MultiCriteriaDeduplicator()

    # Then: Verify default parameters
    assert dedup.threshold == 0.93
    assert dedup.edit_distance_threshold == 3
    assert dedup.min_length_for_edit == 5
    assert dedup.min_length_for_substring == 6


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_multi_criteria_deduplicator_init_custom_params(mock_get_singleton):
    """Test MultiCriteriaDeduplicator initialization with custom parameters."""
    from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator

    # Given: Custom parameters
    mock_get_singleton.return_value = MagicMock()

    # When: Initialize with custom params
    dedup = MultiCriteriaDeduplicator(
        threshold=0.90,
        edit_distance_threshold=2,
        min_length_for_edit=4,
        min_length_for_substring=5,
    )

    # Then: Verify custom parameters
    assert dedup.threshold == 0.90
    assert dedup.edit_distance_threshold == 2
    assert dedup.min_length_for_edit == 4
    assert dedup.min_length_for_substring == 5


# ============================================================================
# Test _is_duplicate_by_criteria Method
# ============================================================================


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_is_duplicate_exact_match(mock_get_singleton):
    """Test exact case-insensitive match detection."""
    from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator

    mock_get_singleton.return_value = MagicMock()
    dedup = MultiCriteriaDeduplicator()

    # When: Check exact match (case-insensitive)
    is_dup, criterion = dedup._is_duplicate_by_criteria("Nicolas Cage", "nicolas cage")

    # Then: Should detect as duplicate with "exact" criterion
    assert is_dup is True
    assert criterion == "exact"


# Check if python-Levenshtein is available
try:
    from Levenshtein import distance as _lev_check

    LEVENSHTEIN_INSTALLED = True
except ImportError:
    LEVENSHTEIN_INSTALLED = False


@pytest.mark.skipif(not LEVENSHTEIN_INSTALLED, reason="python-Levenshtein not installed")
@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_is_duplicate_edit_distance(mock_get_singleton):
    """Test edit distance typo detection."""
    from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator

    mock_get_singleton.return_value = MagicMock()
    dedup = MultiCriteriaDeduplicator(edit_distance_threshold=3)

    # When: Check typo (1 char difference: Nicolas -> Nicholas)
    is_dup, criterion = dedup._is_duplicate_by_criteria("Nicolas Cage", "Nicholas Cage")

    # Then: Should detect as duplicate with "edit_distance" criterion
    assert is_dup is True
    assert criterion == "edit_distance"


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_is_duplicate_substring(mock_get_singleton):
    """Test substring containment detection."""
    from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator

    mock_get_singleton.return_value = MagicMock()
    dedup = MultiCriteriaDeduplicator(min_length_for_substring=6)

    # When: Check substring (Nicolas is in "Nicolas Cage")
    is_dup, criterion = dedup._is_duplicate_by_criteria("Nicolas Cage", "Nicolas")

    # Then: Should detect as duplicate with "substring" criterion
    assert is_dup is True
    assert criterion == "substring"


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_is_duplicate_none(mock_get_singleton):
    """Test no duplicate detection for different entities."""
    from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator

    mock_get_singleton.return_value = MagicMock()
    dedup = MultiCriteriaDeduplicator()

    # When: Check completely different entities
    is_dup, criterion = dedup._is_duplicate_by_criteria("Nicolas Cage", "Mike Figgis")

    # Then: Should NOT detect as duplicate
    assert is_dup is False
    assert criterion == "none"


# ============================================================================
# Test Min-Length Guards (Prevent False Positives)
# ============================================================================


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_min_length_edit_prevents_false_positive(mock_get_singleton):
    """Test min_length_for_edit prevents 'AI' ~ 'UI' false positive."""
    from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator

    mock_get_singleton.return_value = MagicMock()
    dedup = MultiCriteriaDeduplicator(min_length_for_edit=5)

    # When: Check short names (AI, UI have edit distance 1 but are too short)
    is_dup, criterion = dedup._is_duplicate_by_criteria("AI", "UI")

    # Then: Should NOT detect as duplicate (too short for edit distance check)
    assert is_dup is False
    assert criterion == "none"


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_min_length_substring_prevents_false_positive(mock_get_singleton):
    """Test min_length_for_substring prevents 'AI' in 'NVIDIA' false positive."""
    from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator

    mock_get_singleton.return_value = MagicMock()
    dedup = MultiCriteriaDeduplicator(min_length_for_substring=6)

    # When: Check short name contained in longer name ("AI" in "NVIDIA")
    is_dup, criterion = dedup._is_duplicate_by_criteria("AI", "NVIDIA")

    # Then: Should NOT detect as duplicate ("AI" is only 2 chars < 6)
    assert is_dup is False
    assert criterion == "none"


# ============================================================================
# Test Factory Function with MultiCriteria
# ============================================================================


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_create_deduplicator_from_config_multi_criteria(mock_get_singleton, mock_config_multi_criteria):
    """Test factory creates MultiCriteriaDeduplicator when enabled."""
    from src.components.graph_rag.semantic_deduplicator import (
        MultiCriteriaDeduplicator,
        create_deduplicator_from_config,
    )

    # Given: Config with multi-criteria enabled
    mock_get_singleton.return_value = MagicMock()

    # When: Create from config
    dedup = create_deduplicator_from_config(mock_config_multi_criteria)

    # Then: Should create MultiCriteriaDeduplicator
    assert isinstance(dedup, MultiCriteriaDeduplicator)
    assert dedup.edit_distance_threshold == 3


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_create_deduplicator_from_config_semantic_only(mock_get_singleton, mock_config_multi_criteria):
    """Test factory creates SemanticDeduplicator when multi-criteria disabled."""
    from src.components.graph_rag.semantic_deduplicator import (
        MultiCriteriaDeduplicator,
        SemanticDeduplicator,
        create_deduplicator_from_config,
    )

    # Given: Config with multi-criteria disabled
    mock_config_multi_criteria.enable_multi_criteria_dedup = False
    mock_get_singleton.return_value = MagicMock()

    # When: Create from config
    dedup = create_deduplicator_from_config(mock_config_multi_criteria)

    # Then: Should create SemanticDeduplicator (not MultiCriteria)
    assert isinstance(dedup, SemanticDeduplicator)
    assert not isinstance(dedup, MultiCriteriaDeduplicator)


# ============================================================================
# Test Levenshtein Fallback
# ============================================================================


@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.LEVENSHTEIN_AVAILABLE", False)
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_multi_criteria_without_levenshtein(mock_get_singleton):
    """Test MultiCriteriaDeduplicator works without python-Levenshtein."""
    from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator

    mock_get_singleton.return_value = MagicMock()

    # When: Initialize without Levenshtein
    dedup = MultiCriteriaDeduplicator()

    # Then: Should still work (exact match and substring still available)
    is_dup, criterion = dedup._is_duplicate_by_criteria("Nicolas Cage", "nicolas cage")
    assert is_dup is True
    assert criterion == "exact"


# ============================================================================
# Test Full Deduplication Flow
# ============================================================================


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="sklearn not installed")
@patch("src.components.graph_rag.semantic_deduplicator.DEPENDENCIES_AVAILABLE", True)
@patch("src.components.graph_rag.semantic_deduplicator.cosine_similarity")
@patch("src.components.graph_rag.semantic_deduplicator.get_sentence_transformer_singleton")
def test_multi_criteria_deduplicate_nicolas_cage(
    mock_get_singleton, mock_cosine_sim, nicolas_cage_entities
):
    """Test full deduplication with Nicolas Cage test case.

    Note: Uses real levenshtein_distance if available, otherwise tests
    without edit distance criterion (exact + substring + semantic still work).
    """
    import numpy as np

    from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator

    # Given: Nicolas Cage entities with various duplicates
    mock_model = MagicMock()
    mock_get_singleton.return_value = mock_model

    # Mock embeddings - cluster representatives after fast criteria
    # Expected clusters after Phase 1:
    # - "Nicolas Cage" cluster (includes case variants, typos via levenshtein if available)
    # - Other entities that don't match fast criteria
    n = 5  # Conservative: assume worst case where only exact matches work
    embeddings_np = np.array([[i * 0.1] * 384 for i in range(n)])
    mock_model.encode.return_value.cpu.return_value.numpy.return_value = embeddings_np

    # Mock cosine similarity - low similarity (no semantic matches beyond fast criteria)
    similarity = np.eye(n) * 0.5
    mock_cosine_sim.return_value = similarity

    dedup = MultiCriteriaDeduplicator(threshold=0.93)

    # When: Deduplicate
    result = dedup.deduplicate(nicolas_cage_entities)

    # Then: Should reduce entity count (at least exact match "Nicolas Cage" == "nicolas cage")
    # Original: 6 entities
    # At minimum: "Nicolas Cage" + "nicolas cage" merge via exact match = 5 remaining
    # With levenshtein: "Nicholas Cage" also merges = 4 remaining
    assert len(result) < len(nicolas_cage_entities)
    # Mike Figgis should always remain separate
    result_names = [r["name"] for r in result]
    assert "Mike Figgis" in result_names
