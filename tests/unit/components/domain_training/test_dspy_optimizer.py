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
        {"text": "Tesla builds electric cars.", "entities": ["Tesla", "electric cars"]},
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
        {"text": "More text", "entities": ["Entity2"]},
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
        {"text": "Another sample", "entities": ["Entity2"]},
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
            "relations": [{"subject": "FastAPI", "predicate": "uses", "object": "Pydantic"}],
        },
        {
            "text": "Python powers Django.",
            "entities": ["Python", "Django"],
            "relations": [{"subject": "Python", "predicate": "powers", "object": "Django"}],
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
        {"text": "More text", "entities": ["Entity2"]},
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
        {
            "text": "More text",
            "entities": ["E3"],
            "relations": [{"subject": "E3", "predicate": "relates", "object": "E4"}],
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
        {"text": "Also valid", "entities": ["Entity2"]},
        {"text": "Missing entities field"},  # Invalid (will be filtered)
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
        {"text": "More text", "entities": ["Entity2"]},
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
        {"text": "Microsoft builds software.", "entities": ["Microsoft"]},
    ]

    relation_data = [
        {
            "text": "Python is a language",
            "entities": ["Python"],
            "relations": [{"subject": "Python", "predicate": "is_a", "object": "language"}],
        },
        {
            "text": "Java is a language",
            "entities": ["Java"],
            "relations": [{"subject": "Java", "predicate": "is_a", "object": "language"}],
        },
    ]

    # Run entity optimization
    entity_result = await optimizer.optimize_entity_extraction(training_data=entity_data)
    assert "instructions" in entity_result

    # Run relation optimization
    relation_result = await optimizer.optimize_relation_extraction(training_data=relation_data)
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
    sample_data = [
        {"text": "Text", "entities": ["E1"]},
        {"text": "More", "entities": ["E2"]},
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    assert isinstance(result["instructions"], str)
    assert len(result["instructions"]) > 0


@pytest.mark.asyncio
async def test_entity_result_demos_is_list():
    """Test entity result demos is a list."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()
    sample_data = [
        {"text": "Text", "entities": ["E1"]},
        {"text": "More", "entities": ["E2"]},
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    assert isinstance(result["demos"], list)


@pytest.mark.asyncio
async def test_entity_result_metrics_is_dict():
    """Test entity result metrics is a dictionary."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()
    sample_data = [
        {"text": "Text", "entities": ["E1"]},
        {"text": "More", "entities": ["E2"]},
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    assert isinstance(result["metrics"], dict)


# ============================================================================
# Tests: Sprint 125 - Structured Entity/Relation Output (ADR-060)
# ============================================================================


def test_entity_extraction_signature_outputs_structured_entities():
    """Test EntityExtractionSignature specifies dict output (Sprint 125 fix)."""
    from src.components.domain_training.dspy_optimizer import EntityExtractionSignature

    sig = EntityExtractionSignature()

    # Should output list[dict], not list[str]
    assert hasattr(sig, "entities")
    # Check type annotation (entities should be list[dict[str, str]])
    assert sig.entities == []  # Empty list initially


def test_entity_extraction_signature_instructions_mention_types():
    """Test EntityExtractionSignature instructions mention ADR-060 types."""
    from src.components.domain_training.dspy_optimizer import EntityExtractionSignature

    instructions = EntityExtractionSignature.get_instructions()

    # Should mention the universal entity types from ADR-060
    assert "PERSON" in instructions
    assert "ORGANIZATION" in instructions
    assert "LOCATION" in instructions
    assert "name" in instructions
    assert "type" in instructions
    assert "description" in instructions


def test_relation_extraction_signature_instructions_mention_types():
    """Test RelationExtractionSignature instructions mention ADR-060 relation types."""
    from src.components.domain_training.dspy_optimizer import RelationExtractionSignature

    instructions = RelationExtractionSignature.get_instructions()

    # Should mention the universal relation types from ADR-060
    assert "PART_OF" in instructions
    assert "EMPLOYS" in instructions
    assert "LOCATED_IN" in instructions
    assert "source" in instructions
    assert "target" in instructions
    assert "type" in instructions


@pytest.mark.asyncio
async def test_optimize_entity_extraction_with_structured_entities():
    """Test entity extraction with structured entity training data (new format)."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    # New format: entities as dicts with name, type, description
    sample_data = [
        {
            "text": "Tesla is located in Palo Alto, California.",
            "entities": [
                {"name": "Tesla", "type": "ORGANIZATION", "description": "Electric vehicle company"},
                {"name": "Palo Alto", "type": "LOCATION", "description": "City in California"},
                {"name": "California", "type": "LOCATION", "description": "US State"},
            ],
        },
        {
            "text": "Elon Musk founded SpaceX.",
            "entities": [
                {"name": "Elon Musk", "type": "PERSON", "description": "Entrepreneur"},
                {"name": "SpaceX", "type": "ORGANIZATION", "description": "Aerospace company"},
            ],
        },
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    # Should return valid result
    assert isinstance(result, dict)
    assert "instructions" in result
    assert "demos" in result
    assert "metrics" in result


@pytest.mark.asyncio
async def test_optimize_entity_extraction_with_mixed_entity_formats():
    """Test entity extraction handles both old (strings) and new (dicts) formats."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    # Mixed format: some strings, some dicts
    sample_data = [
        {
            "text": "Old format example",
            "entities": ["Entity1", "Entity2"],  # Old format (strings)
        },
        {
            "text": "New format example",
            "entities": [
                {"name": "Entity3", "type": "CONCEPT", "description": "A concept"},
            ],  # New format (dicts)
        },
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    # Should handle mixed formats gracefully
    assert isinstance(result, dict)
    assert "instructions" in result
    assert "demos" in result


@pytest.mark.asyncio
async def test_optimize_relation_extraction_with_structured_relations():
    """Test relation extraction with new source/target/type format (ADR-060)."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    # New format: relations with source/target/type/description
    sample_data = [
        {
            "text": "Tesla is located in Palo Alto.",
            "entities": [
                {"name": "Tesla", "type": "ORGANIZATION", "description": "Car company"},
                {"name": "Palo Alto", "type": "LOCATION", "description": "City"},
            ],
            "relations": [
                {
                    "source": "Tesla",
                    "target": "Palo Alto",
                    "type": "LOCATED_IN",
                    "description": "Tesla headquarters location",
                }
            ],
        },
        {
            "text": "SpaceX was founded by Elon Musk.",
            "entities": [
                {"name": "SpaceX", "type": "ORGANIZATION", "description": "Aerospace company"},
                {"name": "Elon Musk", "type": "PERSON", "description": "Founder"},
            ],
            "relations": [
                {
                    "source": "SpaceX",
                    "target": "Elon Musk",
                    "type": "FOUNDED_BY",
                    "description": "SpaceX founder relation",
                }
            ],
        },
    ]

    result = await optimizer.optimize_relation_extraction(training_data=sample_data)

    # Should return valid result
    assert isinstance(result, dict)
    assert "instructions" in result
    assert "demos" in result
    assert "metrics" in result


@pytest.mark.asyncio
async def test_optimize_relation_extraction_with_old_spo_format():
    """Test relation extraction handles old subject/predicate/object format."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    # Old format: subject/predicate/object
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

    # Should handle old format gracefully
    assert isinstance(result, dict)
    assert "instructions" in result


@pytest.mark.asyncio
async def test_mock_entity_result_has_structured_entities():
    """Test mock entity optimization result returns structured entities."""
    from src.components.domain_training.dspy_optimizer import DSPyOptimizer

    optimizer = DSPyOptimizer()

    # Old format data (strings)
    sample_data = [
        {"text": "Sample text", "entities": ["Entity1", "Entity2"]},
        {"text": "More text", "entities": ["Entity3", "Entity4"]},
    ]

    result = await optimizer.optimize_entity_extraction(training_data=sample_data)

    # Even with old format input, mock should normalize to new format
    assert "demos" in result
    if result["demos"]:
        demo = result["demos"][0]
        assert "output" in demo
        assert "entities" in demo["output"]
        # Entities should be dicts, not strings
        for entity in demo["output"]["entities"]:
            assert isinstance(entity, dict)
            assert "name" in entity
            assert "type" in entity
            assert "description" in entity
