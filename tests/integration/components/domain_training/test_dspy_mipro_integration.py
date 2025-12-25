"""Integration tests for DSPy MIPROv2 Optimizer.

Sprint 64 Feature 64.3: Real DSPy Domain Training with MIPROv2

These tests verify that MIPROv2 optimizer produces real optimization results.
They require:
- Ollama running on localhost:11434
- qwen3:32b model available
- Sufficient time (10-60 seconds per test)

Run with: poetry run pytest tests/integration/components/domain_training/test_dspy_mipro_integration.py -xvs -m requires_llm
"""

import time

import pytest

from src.components.domain_training.dspy_optimizer import DSPyOptimizer


@pytest.mark.requires_llm
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mipro_entity_extraction_real_training():
    """Test that MIPROv2 produces real F1 scores with actual LLM calls.

    This test verifies:
    - Training takes realistic time (>5 seconds, not milliseconds)
    - F1 scores are realistic (0.0-1.0 range, not fake values like 0.85)
    - Optimized prompts are extracted
    """
    optimizer = DSPyOptimizer(llm_model="qwen3:32b")

    # Check DSPy is available
    if not optimizer._dspy_available:
        pytest.skip("DSPy not installed - install with: poetry install --with domain-training")

    # Realistic training data (at least 6 samples for proper train/val split)
    training_data = [
        {
            "text": "Python is a high-level programming language created by Guido van Rossum.",
            "entities": ["Python", "Guido van Rossum"],
        },
        {
            "text": "FastAPI is a modern web framework for building APIs with Python 3.7+.",
            "entities": ["FastAPI", "Python 3.7+"],
        },
        {
            "text": "Docker containers encapsulate applications and their dependencies.",
            "entities": ["Docker", "containers", "applications"],
        },
        {
            "text": "PostgreSQL is an open-source relational database management system.",
            "entities": ["PostgreSQL"],
        },
        {
            "text": "Kubernetes orchestrates containerized applications across clusters.",
            "entities": ["Kubernetes", "applications", "clusters"],
        },
        {
            "text": "Redis is an in-memory data structure store used as a database and cache.",
            "entities": ["Redis"],
        },
    ]

    # Track training time
    start_time = time.time()

    result = await optimizer.optimize_entity_extraction(training_data=training_data)

    training_duration = time.time() - start_time

    # Verify realistic training duration (should take 5-60 seconds, not milliseconds)
    assert training_duration > 5.0, (
        f"Training completed in {training_duration:.2f}s, "
        f"which suggests mock results. Real MIPROv2 training should take >5s"
    )

    print(f"\n[MIPRO TIMING] Entity extraction training: {training_duration:.2f}s")

    # Verify result structure
    assert isinstance(result, dict)
    assert "instructions" in result
    assert "demos" in result
    assert "metrics" in result

    # Verify metrics are realistic (not fake)
    metrics = result["metrics"]
    assert "val_f1" in metrics or "f1" in metrics
    f1_score = metrics.get("val_f1", metrics.get("f1", 0.0))

    print(f"[MIPRO METRICS] Entity F1: {f1_score:.3f}")

    # F1 should be between 0.0 and 1.0
    assert 0.0 <= f1_score <= 1.0, f"F1 score {f1_score} is out of valid range [0.0, 1.0]"

    # For 6 samples, we expect F1 > 0.3 (anything less suggests broken training)
    assert f1_score > 0.3, (
        f"F1 score {f1_score:.3f} is too low for real training. "
        f"This suggests either mock results or broken optimization."
    )

    # Verify demos were extracted
    assert isinstance(result["demos"], list)
    print(f"[MIPRO DEMOS] Extracted {len(result['demos'])} demonstration examples")


@pytest.mark.requires_llm
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mipro_relation_extraction_real_training():
    """Test that MIPROv2 produces real results for relation extraction.

    This test verifies:
    - Training takes realistic time (>5 seconds)
    - F1 scores are realistic
    - Optimized prompts are extracted
    """
    optimizer = DSPyOptimizer(llm_model="qwen3:32b")

    if not optimizer._dspy_available:
        pytest.skip("DSPy not installed")

    # Realistic relation extraction training data
    training_data = [
        {
            "text": "Python was created by Guido van Rossum in 1991.",
            "entities": ["Python", "Guido van Rossum", "1991"],
            "relations": [
                {"subject": "Python", "predicate": "created_by", "object": "Guido van Rossum"},
                {"subject": "Python", "predicate": "created_in", "object": "1991"},
            ],
        },
        {
            "text": "FastAPI is built on top of Starlette for web routing.",
            "entities": ["FastAPI", "Starlette"],
            "relations": [
                {"subject": "FastAPI", "predicate": "built_on", "object": "Starlette"}
            ],
        },
        {
            "text": "Docker was developed by Docker Inc. and released in 2013.",
            "entities": ["Docker", "Docker Inc.", "2013"],
            "relations": [
                {"subject": "Docker", "predicate": "developed_by", "object": "Docker Inc."},
                {"subject": "Docker", "predicate": "released_in", "object": "2013"},
            ],
        },
        {
            "text": "PostgreSQL is based on the POSTGRES system from UC Berkeley.",
            "entities": ["PostgreSQL", "POSTGRES", "UC Berkeley"],
            "relations": [
                {"subject": "PostgreSQL", "predicate": "based_on", "object": "POSTGRES"},
                {"subject": "POSTGRES", "predicate": "from", "object": "UC Berkeley"},
            ],
        },
        {
            "text": "Kubernetes was originally designed by Google and is now maintained by CNCF.",
            "entities": ["Kubernetes", "Google", "CNCF"],
            "relations": [
                {"subject": "Kubernetes", "predicate": "designed_by", "object": "Google"},
                {"subject": "Kubernetes", "predicate": "maintained_by", "object": "CNCF"},
            ],
        },
        {
            "text": "Redis was created by Salvatore Sanfilippo and is written in C.",
            "entities": ["Redis", "Salvatore Sanfilippo", "C"],
            "relations": [
                {
                    "subject": "Redis",
                    "predicate": "created_by",
                    "object": "Salvatore Sanfilippo",
                },
                {"subject": "Redis", "predicate": "written_in", "object": "C"},
            ],
        },
    ]

    # Track training time
    start_time = time.time()

    result = await optimizer.optimize_relation_extraction(training_data=training_data)

    training_duration = time.time() - start_time

    # Verify realistic training duration
    assert training_duration > 5.0, (
        f"Training completed in {training_duration:.2f}s, which suggests mock results"
    )

    print(f"\n[MIPRO TIMING] Relation extraction training: {training_duration:.2f}s")

    # Verify result structure
    assert isinstance(result, dict)
    assert "instructions" in result
    assert "demos" in result
    assert "metrics" in result

    # Verify metrics
    metrics = result["metrics"]
    f1_score = metrics.get("val_f1", metrics.get("f1", 0.0))

    print(f"[MIPRO METRICS] Relation F1: {f1_score:.3f}")

    assert 0.0 <= f1_score <= 1.0
    assert f1_score > 0.3, f"F1 score {f1_score:.3f} is too low for real training"

    # Verify demos
    assert isinstance(result["demos"], list)
    print(f"[MIPRO DEMOS] Extracted {len(result['demos'])} demonstration examples")


@pytest.mark.requires_llm
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mipro_with_progress_callback():
    """Test that MIPROv2 calls progress callbacks during training.

    This verifies that the progress tracking integration works correctly.
    """
    optimizer = DSPyOptimizer(llm_model="qwen3:32b")

    if not optimizer._dspy_available:
        pytest.skip("DSPy not installed")

    progress_calls = []

    def progress_callback(message: str, progress: float):
        progress_calls.append({"message": message, "progress": progress})
        print(f"[PROGRESS] {progress:.1f}% - {message}")

    training_data = [
        {"text": "Sample text 1", "entities": ["Entity1"]},
        {"text": "Sample text 2", "entities": ["Entity2"]},
        {"text": "Sample text 3", "entities": ["Entity3"]},
        {"text": "Sample text 4", "entities": ["Entity4"]},
        {"text": "Sample text 5", "entities": ["Entity5"]},
        {"text": "Sample text 6", "entities": ["Entity6"]},
    ]

    result = await optimizer.optimize_entity_extraction(
        training_data=training_data, progress_callback=progress_callback
    )

    # Verify progress callbacks were called
    assert len(progress_calls) > 0, "Progress callback was never called"

    # Verify progress values are in range [0, 100]
    for call in progress_calls:
        assert 0.0 <= call["progress"] <= 100.0

    print(f"\n[PROGRESS TRACKING] {len(progress_calls)} progress updates received")

    # Verify result is valid
    assert isinstance(result, dict)
    assert "metrics" in result
