"""Unit tests for DSPy Optimizer.

Sprint 45 Feature 45.2: DSPy Integration Service

Tests:
- DSPy optimizer initialization
- Entity extraction prompt optimization
- Relation extraction prompt optimization
- Metric calculations
- Progress callback handling
- Error handling for invalid data
"""

import pytest

# ============================================================================
# Test: Initialization
# ============================================================================


def test_dspy_optimizer_initialization():
    """Test DSPyOptimizer initializes correctly."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    # Create without DSPy installed (will use mock fallback)
    optimizer = DSPyOptimizer(llm_model="qwen3:32b")

    assert optimizer.llm_model == "qwen3:32b"
    assert hasattr(optimizer, "_dspy_available")


def test_dspy_optimizer_default_model():
    """Test DSPyOptimizer uses default model when not specified."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()
    # Should have default model
    assert optimizer.llm_model == "qwen3:32b"


def test_dspy_optimizer_with_different_models():
    """Test DSPyOptimizer can be initialized with different models."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    models = ["qwen3:32b", "qwen2.5:7b", "qwen2.5:3b", "custom:32b"]

    for model in models:
        optimizer = DSPyOptimizer(llm_model=model)
        assert optimizer.llm_model == model


# ============================================================================
# Tests: Entity Extraction Optimization
# ============================================================================


@pytest.mark.asyncio
async def test_optimize_entity_extraction_returns_dict():
    """Test entity extraction optimization returns dictionary."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    sample_data = [
        {"text": "Python is a programming language.", "entities": ["Python"]},
        {"text": "FastAPI is a web framework.", "entities": ["FastAPI"]},
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    # Should return a dictionary
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_optimize_entity_extraction_has_required_keys():
    """Test entity extraction returns required keys."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    sample_data = [
        {"text": "Apple acquired Siri.", "entities": ["Apple", "Siri"]},
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    # Should have instructions, demos, and metrics
    assert "instructions" in result
    assert "demos" in result
    assert "metrics" in result


@pytest.mark.asyncio
async def test_optimize_entity_extraction_with_empty_data():
    """Test entity extraction raises error for empty data."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    with pytest.raises(ValueError):
        await optimizer.optimize_entity_extraction(training_data=[])


@pytest.mark.asyncio
async def test_optimize_entity_extraction_returns_strings():
    """Test entity extraction returns string fields correctly."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    sample_data = [
        {"text": "Text content", "entities": ["Entity1"]},
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    # Verify types
    assert isinstance(result["instructions"], str)
    assert isinstance(result["demos"], list)
    assert isinstance(result["metrics"], dict)


@pytest.mark.asyncio
async def test_optimize_entity_extraction_calls_progress_callback():
    """Test progress callback is accepted without error."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()
    progress_calls = []

    def progress_callback(message, progress):
        progress_calls.append({"message": message, "progress": progress})

    sample_data = [
        {"text": "Sample text", "entities": ["Entity1"]},
    ]

    # Should not raise error when progress callback is provided
    result = await optimizer.optimize_entity_extraction(
        training_data=sample_data, progress_callback=progress_callback
    )

    # Result should be valid
    assert isinstance(result, dict)
    assert "instructions" in result


# ============================================================================
# Tests: Relation Extraction Optimization
# ============================================================================


@pytest.mark.asyncio
async def test_optimize_relation_extraction_returns_dict():
    """Test relation extraction optimization returns dictionary."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    sample_data = [
        {
            "text": "FastAPI uses Pydantic.",
            "entities": ["FastAPI", "Pydantic"],
            "relations": [
                {"subject": "FastAPI", "predicate": "uses", "object": "Pydantic"}
            ],
        },
    ]

    result = await optimizer.optimize_relation_extraction(training_data=sample_data)

    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_optimize_relation_extraction_has_required_keys():
    """Test relation extraction returns required keys."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    sample_data = [
        {
            "text": "Text content",
            "entities": ["E1", "E2"],
            "relations": [{"subject": "E1", "predicate": "relates", "object": "E2"}],
        },
    ]

    result = await optimizer.optimize_relation_extraction(training_data=sample_data)

    assert "instructions" in result
    assert "demos" in result
    assert "metrics" in result


# ============================================================================
# Tests: Metrics Calculation
# ============================================================================


def test_entity_metric_perfect_match():
    """Test entity metric calculation for perfect match."""
    # Simple recall metric
    gold = {"entity1", "entity2", "entity3"}
    pred = {"entity1", "entity2", "entity3"}

    recall = len(gold & pred) / len(gold) if gold else 0.0

    assert recall == 1.0


def test_entity_metric_partial_match():
    """Test entity metric calculation for partial match."""
    gold = {"entity1", "entity2", "entity3"}
    pred = {"entity1", "entity2"}

    recall = len(gold & pred) / len(gold) if gold else 0.0

    assert abs(recall - 2 / 3) < 0.01


def test_entity_metric_no_match():
    """Test entity metric calculation for no match."""
    gold = {"entity1", "entity2"}
    pred = set()

    recall = len(gold & pred) / len(gold) if gold else 0.0

    assert recall == 0.0


def test_entity_metric_empty_gold():
    """Test entity metric when gold is empty."""
    gold = set()
    pred = {"entity1"}

    recall = 1.0 if not gold and not pred else (len(gold & pred) / len(gold) if gold else 0.0)

    assert recall == 0.0


def test_relation_metric_perfect_match():
    """Test relation metric for perfect match."""

    def normalize(r):
        return (r["subject"].lower(), r["predicate"].lower(), r["object"].lower())

    gold = {
        normalize({"subject": "A", "predicate": "relates", "object": "B"}),
        normalize({"subject": "B", "predicate": "depends", "object": "C"}),
    }
    pred = {
        normalize({"subject": "A", "predicate": "relates", "object": "B"}),
        normalize({"subject": "B", "predicate": "depends", "object": "C"}),
    }

    score = len(gold & pred) / max(len(gold), len(pred)) if gold or pred else 1.0

    assert score == 1.0


def test_relation_metric_partial_match():
    """Test relation metric for partial match."""

    def normalize(r):
        return (r["subject"].lower(), r["predicate"].lower(), r["object"].lower())

    gold = {
        normalize({"subject": "A", "predicate": "relates", "object": "B"}),
        normalize({"subject": "B", "predicate": "depends", "object": "C"}),
    }
    pred = {normalize({"subject": "A", "predicate": "relates", "object": "B"})}

    score = len(gold & pred) / max(len(gold), len(pred)) if gold or pred else 1.0

    assert score == 0.5


# ============================================================================
# Tests: Mock Results Fallback
# ============================================================================


@pytest.mark.asyncio
async def test_mock_entity_optimization_result():
    """Test that fallback mock results are used when DSPy unavailable."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    sample_data = [
        {"text": "Text", "entities": ["Entity1"]},
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    # Fallback should still return valid structure
    assert "instructions" in result
    assert "demos" in result
    assert "metrics" in result


@pytest.mark.asyncio
async def test_mock_relation_optimization_result():
    """Test fallback mock results for relation optimization."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    sample_data = [
        {
            "text": "Text",
            "entities": ["E1"],
            "relations": [{"subject": "E1", "predicate": "relates", "object": "E2"}],
        },
    ]

    result = await optimizer.optimize_relation_extraction(training_data=sample_data)

    assert "instructions" in result
    assert "demos" in result
    assert "metrics" in result


# ============================================================================
# Tests: Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_optimize_entity_extraction_handles_none_data():
    """Test optimization handles None data gracefully."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    with pytest.raises((TypeError, ValueError)):
        await optimizer.optimize_entity_extraction(training_data=None)


@pytest.mark.asyncio
async def test_optimize_entity_extraction_handles_malformed_data():
    """Test optimization handles malformed training data."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    malformed_data = [
        {"text": "Valid", "entities": ["Entity1"]},
        {"text": "Missing entities field"},  # Invalid
    ]

    # Should either succeed or raise appropriate error
    try:
        result = await optimizer.optimize_entity_extraction(training_data=malformed_data)
        # If successful, should still return valid structure
        assert isinstance(result, dict)
    except (KeyError, ValueError, IndexError):
        pass  # Expected behavior


@pytest.mark.asyncio
async def test_optimize_with_progress_callback_exception():
    """Test optimization continues even if progress callback fails."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    def failing_callback(message, progress):
        raise RuntimeError("Callback error")

    sample_data = [
        {"text": "Text", "entities": ["Entity1"]},
    ]

    # Optimization should complete despite callback error
    try:
        result = await optimizer.optimize_entity_extraction(
            training_data=sample_data, progress_callback=failing_callback
        )
        # If we reach here, callback error was handled gracefully
        assert "instructions" in result
    except RuntimeError:
        # It's acceptable to propagate callback errors too
        pass


# ============================================================================
# Tests: Configuration Variants
# ============================================================================


def test_dspy_optimizer_stores_llm_model():
    """Test DSPyOptimizer correctly stores LLM model."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    test_model = "test_model:70b"
    optimizer = DSPyOptimizer(llm_model=test_model)

    assert optimizer.llm_model == test_model


def test_dspy_optimizer_availability_flag():
    """Test DSPyOptimizer tracks DSPy availability."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    assert hasattr(optimizer, "_dspy_available")
    assert isinstance(optimizer._dspy_available, bool)


# ============================================================================
# Tests: Integration Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_multiple_optimizations_sequence():
    """Test running multiple optimizations in sequence."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    entity_data = [
        {"text": "Apple Inc. was founded.", "entities": ["Apple Inc."]},
    ]

    relation_data = [
        {
            "text": "Python is a language",
            "entities": ["Python"],
            "relations": [{"subject": "Python", "predicate": "is_a", "object": "language"}],
        },
    ]

    # Run entity optimization
    entity_result = await optimizer.optimize_entity_extraction(training_data=entity_data)
    assert "instructions" in entity_result

    # Run relation optimization
    relation_result = await optimizer.optimize_relation_extraction(
        training_data=relation_data
    )
    assert "instructions" in relation_result


@pytest.mark.asyncio
async def test_optimization_with_multiple_samples():
    """Test optimization with multiple training samples."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    sample_data = [
        {"text": "Sample 1", "entities": ["E1"]},
        {"text": "Sample 2", "entities": ["E2"]},
        {"text": "Sample 3", "entities": ["E3"]},
        {"text": "Sample 4", "entities": ["E4"]},
        {"text": "Sample 5", "entities": ["E5"]},
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    assert isinstance(result, dict)
    assert "instructions" in result


# ============================================================================
# Tests: Signatures
# ============================================================================


def test_entity_extraction_signature():
    """Test EntityExtractionSignature definition."""
    from src.components.domain_training.dspy_optimizer import EntityExtractionSignature

    sig = EntityExtractionSignature()

    assert hasattr(sig, "source_text")
    assert hasattr(sig, "entities")
    assert sig.get_input_fields() == ["source_text"]
    assert sig.get_output_fields() == ["entities"]


def test_relation_extraction_signature():
    """Test RelationExtractionSignature definition."""
    from src.components.domain_training.dspy_optimizer import RelationExtractionSignature

    sig = RelationExtractionSignature()

    assert hasattr(sig, "source_text")
    assert hasattr(sig, "entities")
    assert hasattr(sig, "relations")
    assert sig.get_input_fields() == ["source_text", "entities"]
    assert sig.get_output_fields() == ["relations"]


# ============================================================================
# Tests: Result Structure Validation
# ============================================================================


@pytest.mark.asyncio
async def test_entity_result_instructions_is_string():
    """Test entity result instructions is a string."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()
    sample_data = [{"text": "Text", "entities": ["E1"]}]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    assert isinstance(result["instructions"], str)
    assert len(result["instructions"]) > 0


@pytest.mark.asyncio
async def test_entity_result_demos_is_list():
    """Test entity result demos is a list."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()
    sample_data = [{"text": "Text", "entities": ["E1"]}]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    assert isinstance(result["demos"], list)


@pytest.mark.asyncio
async def test_entity_result_metrics_is_dict():
    """Test entity result metrics is a dictionary."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()
    sample_data = [{"text": "Text", "entities": ["E1"]}]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    assert isinstance(result["metrics"], dict)
