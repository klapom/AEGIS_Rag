"""
Integration tests for Sprint 25 Feature 25.10 - LLM Migration.

This module verifies that all migrated components properly use AegisLLMProxy.
Sprint Context: Sprint 25, Feature 25.10
Related ADR: ADR-033 (Mozilla ANY-LLM Integration)
"""

import pytest
from unittest.mock import AsyncMock, patch

# Skip entire module if ragas is not installed (optional evaluation dependency)
pytest.importorskip("ragas", reason="RAGAS evaluation tests skipped (optional dependency)")

from src.components.llm_proxy.models import (
    LLMResponse,
    LLMTask,
    TaskType,
    QualityRequirement,
    Complexity,
)
from src.evaluation.custom_metrics import CustomMetricsEvaluator


@pytest.mark.asyncio
async def test_custom_metrics_uses_proxy():
    """Verify CustomMetricsEvaluator uses AegisLLMProxy."""
    evaluator = CustomMetricsEvaluator(model="qwen3:0.6b", temperature=0.0)

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

        result = await evaluator._generate("Is this relevant?")

        assert mock_generate.called
        assert result == "YES"


@pytest.mark.asyncio
async def test_custom_metrics_precision():
    """Test context precision with proxy."""
    evaluator = CustomMetricsEvaluator(model="qwen3:0.6b", temperature=0.0)

    responses = [
        LLMResponse(
            content="YES",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=60,
            cost_usd=0.0,
        ),
        LLMResponse(
            content="NO",
            provider="local_ollama",
            model="qwen3:0.6b",
            tokens_used=60,
            cost_usd=0.0,
        ),
    ]

    with patch.object(evaluator.llm_proxy, "generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = responses

        result = await evaluator.evaluate_context_precision(
            query="What is RAG?",
            retrieved_contexts=["RAG combines retrieval.", "Weather is sunny."],
            ground_truth="RAG is a technique.",
        )

        assert result.score == 0.5
        assert mock_generate.call_count == 2
