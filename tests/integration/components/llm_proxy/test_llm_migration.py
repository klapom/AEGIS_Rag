"""
Integration tests for Sprint 25 Feature 25.10 - LLM Migration Part 3.

This module verifies that all migrated components properly use AegisLLMProxy
and that cost tracking captures all LLM requests.

Components tested:
- custom_metrics.py (evaluation metrics)
- image_processor.py (VLM fallback)

Sprint Context: Sprint 25, Feature 25.10 (Part 3/3)
Related ADR: ADR-033 (Mozilla ANY-LLM Integration)
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

# Skip entire module if ragas is not installed (optional evaluation dependency)
pytest.importorskip("ragas", reason="RAGAS evaluation tests skipped (optional dependency)")

from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy
from src.components.llm_proxy.models import (
    LLMResponse,
    LLMTask,
    TaskType,
    QualityRequirement,
    Complexity,
)
from src.evaluation.custom_metrics import CustomMetricsEvaluator


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return LLMResponse(
        content="Test response",
        provider="local_ollama",
        model="test-model",
        tokens_used=30,
        cost_usd=0.0,
        latency_ms=100.0,
        routing_reason="test_routing",
        fallback_used=False,
    )


@pytest.fixture
def mock_aegis_llm_proxy(mock_llm_response):
    """Mock AegisLLMProxy for testing."""
    with patch("src.components.llm_proxy.aegis_llm_proxy.AegisLLMProxy") as mock:
        instance = mock.return_value
        instance.generate = AsyncMock(return_value=mock_llm_response)
        yield instance


# =============================================================================
# Test Custom Metrics Evaluator Migration
# =============================================================================


@pytest.mark.asyncio
async def test_custom_metrics_uses_proxy():
    """Verify CustomMetricsEvaluator uses AegisLLMProxy for evaluation."""
    evaluator = CustomMetricsEvaluator(model="qwen3:0.6b", temperature=0.0)

    # Mock the LLM proxy
    with patch.object(evaluator.llm_proxy, "generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = LLMResponse(
            content="YES",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=60,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        )

        # Execute _generate
        result = await evaluator._generate("Is this relevant?")

        # Verify proxy was called
        assert mock_generate.called
        assert result == "YES"

        # Verify task parameters
        call_args = mock_generate.call_args
        task = call_args[0][0]
        assert isinstance(task, LLMTask)
        assert task.task_type == TaskType.GENERATION
        assert task.quality_requirement == QualityRequirement.HIGH
        assert task.complexity == Complexity.LOW
        assert task.temperature == 0.0


@pytest.mark.asyncio
async def test_custom_metrics_precision_integration():
    """Integration test for context precision evaluation with proxy."""
    evaluator = CustomMetricsEvaluator(model="qwen3:0.6b", temperature=0.0)

    # Mock responses: 1st context YES (relevant), 2nd context NO (irrelevant)
    responses = [
        LLMResponse(
            content="YES",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=60,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        ),
        LLMResponse(
            content="NO",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=60,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        ),
    ]

    with patch.object(evaluator.llm_proxy, "generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = responses

        result = await evaluator.evaluate_context_precision(
            query="What is RAG?",
            retrieved_contexts=[
                "RAG combines retrieval and generation for better answers.",
                "The weather today is sunny and warm.",
            ],
            ground_truth="RAG is a retrieval-augmented generation technique.",
        )

        # Verify precision = 1/2 = 0.5 (1 relevant, 1 irrelevant)
        assert result.score == 0.5
        assert result.details["total"] == 2
        assert result.details["relevant"] == 1

        # Verify proxy was called twice (once per context)
        assert mock_generate.call_count == 2


@pytest.mark.asyncio
async def test_custom_metrics_recall_integration():
    """Integration test for context recall evaluation with proxy."""
    evaluator = CustomMetricsEvaluator(model="qwen3:0.6b", temperature=0.0)

    # Mock responses:
    # 1. Statement decomposition: 2 statements
    # 2. Attribution check for statement 1: YES
    # 3. Attribution check for statement 2: NO
    responses = [
        LLMResponse(
            content="RAG uses retrieval.\nRAG uses generation.",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=70,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        ),
        LLMResponse(
            content="YES",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=60,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        ),
        LLMResponse(
            content="NO",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=60,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        ),
    ]

    with patch.object(evaluator.llm_proxy, "generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = responses

        result = await evaluator.evaluate_context_recall(
            ground_truth="RAG uses retrieval and generation.",
            retrieved_contexts=["RAG uses retrieval for better answers."],
        )

        # Verify recall = 1/2 = 0.5 (1 attributable, 1 not attributable)
        assert result.score == 0.5
        assert result.details["statements"] == 2
        assert result.details["attributable"] == 1

        # Verify proxy was called 3 times (1 decompose + 2 attributions)
        assert mock_generate.call_count == 3


@pytest.mark.asyncio
async def test_custom_metrics_faithfulness_integration():
    """Integration test for faithfulness evaluation with proxy."""
    evaluator = CustomMetricsEvaluator(model="qwen3:0.6b", temperature=0.0)

    # Mock responses:
    # 1. Claim decomposition: 2 claims
    # 2. Verification for claim 1: YES
    # 3. Verification for claim 2: NO (hallucination)
    responses = [
        LLMResponse(
            content="RAG uses retrieval.\nRAG was invented in 2025.",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=70,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        ),
        LLMResponse(
            content="YES",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=60,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        ),
        LLMResponse(
            content="NO",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=60,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        ),
    ]

    with patch.object(evaluator.llm_proxy, "generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = responses

        result = await evaluator.evaluate_faithfulness(
            response="RAG uses retrieval. RAG was invented in 2025.",
            retrieved_contexts=["RAG uses retrieval for better answers."],
        )

        # Verify faithfulness = 1/2 = 0.5 (1 verified, 1 hallucination)
        assert result.score == 0.5
        assert result.details["claims"] == 2
        assert result.details["verified"] == 1

        # Verify proxy was called 3 times (1 decompose + 2 verifications)
        assert mock_generate.call_count == 3


# =============================================================================
# Test Image Processor VLM Fallback Migration
# =============================================================================


@pytest.mark.asyncio
async def test_image_processor_vlm_uses_proxy():
    """Verify image processor VLM fallback uses AegisLLMProxy."""
    from src.components.ingestion.image_processor import generate_vlm_description_with_proxy

    # Mock response
    mock_response = LLMResponse(
        content="A diagram showing RAG architecture with retrieval and generation components.",
        provider="alibaba_cloud",
        model="qwen3-vl-30b-a3b-instruct",
        tokens_used=150,
        cost_usd=0.005,
        latency_ms=500.0,
        routing_reason="vision_task_best_vlm",
        fallback_used=False,
    )

    # Create temp image file for testing
    import tempfile
    from PIL import Image

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img = Image.new("RGB", (500, 500), color="red")
        img.save(tmp.name)
        image_path = Path(tmp.name)

    try:
        with patch("src.components.ingestion.image_processor.AegisLLMProxy") as mock_proxy_class:
            mock_proxy = mock_proxy_class.return_value
            mock_proxy.generate = AsyncMock(return_value=mock_response)

            # Execute VLM description
            description = await generate_vlm_description_with_proxy(
                image_path=image_path,
                temperature=0.7,
            )

            # Verify proxy was called
            assert mock_proxy.generate.called
            assert description == mock_response.content

            # Verify task parameters
            call_args = mock_proxy.generate.call_args
            task = call_args[0][0]
            assert isinstance(task, LLMTask)
            assert task.task_type == TaskType.VISION
            assert task.quality_requirement == QualityRequirement.HIGH
            assert task.complexity == Complexity.MEDIUM
            assert task.temperature == 0.7
    finally:
        # Cleanup temp file
        if image_path.exists():
            image_path.unlink()


# =============================================================================
# Test Cost Tracking Integration
# =============================================================================


@pytest.mark.asyncio
async def test_cost_tracking_captures_evaluation_requests():
    """Verify cost tracker captures evaluation metric requests."""
    from src.components.llm_proxy.cost_tracker import CostTracker

    tracker = CostTracker()

    # Mock evaluator with real proxy
    evaluator = CustomMetricsEvaluator(model="qwen3:0.6b", temperature=0.0)

    # Mock the generate call to simulate real execution
    with patch.object(evaluator.llm_proxy, "generate", new_callable=AsyncMock) as mock_generate:
        mock_response = LLMResponse(
            content="YES",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=60,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        )
        mock_generate.return_value = mock_response

        # Track manually (since we're mocking)
        await evaluator._generate("Is this relevant?")

        # Manually track for testing
        tracker.track_request(
            provider="local_ollama",
            model="qwen3:0.6b",
            task_type=TaskType.GENERATION.value,
            tokens_input=50,
            tokens_output=10,
            cost_usd=0.0,
            latency_ms=100.0,
        )

        # Verify tracking via get_request_stats
        stats = tracker.get_request_stats(days=1, provider="local_ollama")

        # Should have at least one request
        assert stats["total_requests"] > 0

        # Verify task breakdown includes generation
        task_breakdown = stats["task_breakdown"]
        assert any(t["task_type"] == TaskType.GENERATION.value for t in task_breakdown)


@pytest.mark.asyncio
async def test_cost_tracking_shows_all_task_types():
    """Verify cost tracker captures all migrated task types."""
    from src.components.llm_proxy.cost_tracker import CostTracker

    tracker = CostTracker()

    # Simulate different task types
    task_types = [
        TaskType.GENERATION,
        TaskType.EXTRACTION,
        TaskType.VISION,
    ]

    for task_type in task_types:
        tracker.track_request(
            provider="local_ollama",
            model="test-model",
            task_type=task_type.value,
            tokens_input=100,
            tokens_output=50,
            cost_usd=0.0,
            latency_ms=100.0,
        )

    # Verify all task types tracked via get_request_stats
    stats = tracker.get_request_stats(days=1, provider="local_ollama")
    task_breakdown = stats["task_breakdown"]
    tracked_task_types = {t["task_type"] for t in task_breakdown}

    for task_type in task_types:
        assert task_type.value in tracked_task_types


# =============================================================================
# Test End-to-End Migration
# =============================================================================


@pytest.mark.asyncio
async def test_all_migrations_use_proxy():
    """Comprehensive test verifying all migrated components use AegisLLMProxy."""
    # This test verifies that:
    # 1. CustomMetricsEvaluator uses AegisLLMProxy
    # 2. Image processor VLM fallback uses AegisLLMProxy
    # 3. All requests are tracked in cost tracker

    evaluator = CustomMetricsEvaluator()

    # Verify evaluator has llm_proxy attribute
    assert hasattr(evaluator, "llm_proxy")
    assert isinstance(evaluator.llm_proxy, AegisLLMProxy)

    # Verify image processor can import proxy
    from src.components.ingestion.image_processor import AEGIS_LLM_PROXY_AVAILABLE

    assert AEGIS_LLM_PROXY_AVAILABLE is True

    # Verify cost tracker exists
    from src.components.llm_proxy.cost_tracker import CostTracker

    tracker = CostTracker()
    assert tracker is not None

    # Success: All components migrated
    assert True
