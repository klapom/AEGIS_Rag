"""Unit tests for AegisLLMProxy - Sprint 25 Feature 25.3.

This module tests token tracking accuracy with proper input/output token parsing.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy
from src.components.llm_proxy.config import LLMProxyConfig
from src.components.llm_proxy.models import (
    Complexity,
    DataClassification,
    LLMTask,
    QualityRequirement,
    TaskType,
)


@pytest.fixture
def mock_config():
    """Create mock LLMProxy configuration."""
    config_data = {
        "providers": {
            "local_ollama": {
                "enabled": True,
                "base_url": "http://localhost:11434",
            },
            "alibaba_cloud": {
                "enabled": True,
                "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                "api_key": "test-key",
            },
            "openai": {
                "enabled": True,
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-key",
            },
        },
        "budgets": {
            "monthly_limits": {
                "alibaba_cloud": 10.0,
                "openai": 20.0,
            }
        },
        "routing": {
            "default": "local_ollama",
        },
        "model_defaults": {
            "local_ollama": {
                "extraction": "gemma-3-4b-it-Q8_0",
                "generation": "llama3.2:8b",
            },
            "alibaba_cloud": {
                "extraction": "qwen-turbo",
                "generation": "qwen-plus",
            },
            "openai": {
                "extraction": "gpt-4o-mini",
                "generation": "gpt-4o",
            },
        },
        "fallback": {
            "enabled": True,
            "order": ["local_ollama", "alibaba_cloud", "openai"],
        },
        "monitoring": {
            "prometheus_enabled": False,
            "langsmith_enabled": False,
        },
    }
    return LLMProxyConfig(**config_data)


@pytest.fixture
def aegis_proxy(mock_config):
    """Create AegisLLMProxy instance with mocked cost tracker."""
    with patch("src.domains.llm_integration.proxy.aegis_llm_proxy.CostTracker") as mock_tracker:
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.get_monthly_spending.return_value = {
            "alibaba_cloud": 0.0,
            "openai": 0.0,
        }
        mock_tracker.return_value = mock_tracker_instance

        proxy = AegisLLMProxy(config=mock_config)
        proxy.cost_tracker = mock_tracker_instance
        return proxy


@pytest.fixture
def sample_task():
    """Create sample LLM task."""
    return LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt="Extract entities from: John Smith works at Acme Corp.",
        data_classification=DataClassification.PUBLIC,
        quality_requirement=QualityRequirement.MEDIUM,
        complexity=Complexity.MEDIUM,
        max_tokens=1024,
        temperature=0.1,
    )


@pytest.mark.asyncio
async def test_token_parsing_with_usage_field(aegis_proxy, sample_task):
    """Test token parsing when usage field is available (accurate split)."""
    # Mock ANY-LLM response with detailed usage field
    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="John Smith (Person) works at Acme Corp (Organization)."
                )
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=25,
            completion_tokens=15,
            total_tokens=40,
        ),
    )

    with patch(
        "src.domains.llm_integration.proxy.aegis_llm_proxy.acompletion", new_callable=AsyncMock
    ) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        result = await aegis_proxy.generate(sample_task)

        # Verify response has accurate token breakdown
        assert result.tokens_used == 40
        assert hasattr(result, "tokens_input")
        assert hasattr(result, "tokens_output")
        assert result.tokens_input == 25
        assert result.tokens_output == 15

        # Verify cost tracking called with accurate split
        aegis_proxy.cost_tracker.track_request.assert_called_once()
        call_kwargs = aegis_proxy.cost_tracker.track_request.call_args[1]
        assert call_kwargs["tokens_input"] == 25
        assert call_kwargs["tokens_output"] == 15


@pytest.mark.asyncio
async def test_token_parsing_without_usage_field(aegis_proxy, sample_task):
    """Test token parsing when usage field is missing (50/50 fallback)."""
    # Mock ANY-LLM response WITHOUT usage field
    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="John Smith (Person) works at Acme Corp (Organization)."
                )
            )
        ],
        tokens_used=40,
        usage=None,
    )

    with patch(
        "src.domains.llm_integration.proxy.aegis_llm_proxy.acompletion", new_callable=AsyncMock
    ) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        result = await aegis_proxy.generate(sample_task)

        # Verify response has estimated token breakdown (50/50 split)
        assert result.tokens_used == 40
        assert hasattr(result, "tokens_input")
        assert hasattr(result, "tokens_output")
        assert result.tokens_input == 20  # 40 // 2
        assert result.tokens_output == 20  # 40 - 20

        # Verify cost tracking called with estimated split
        aegis_proxy.cost_tracker.track_request.assert_called_once()
        call_kwargs = aegis_proxy.cost_tracker.track_request.call_args[1]
        assert call_kwargs["tokens_input"] == 20
        assert call_kwargs["tokens_output"] == 20


@pytest.mark.asyncio
async def test_token_parsing_zero_tokens_edge_case(aegis_proxy, sample_task):
    """Test token parsing when tokens are zero (edge case)."""
    # Mock ANY-LLM response with zero tokens
    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=""))],
        usage=SimpleNamespace(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        ),
    )

    with patch(
        "src.domains.llm_integration.proxy.aegis_llm_proxy.acompletion", new_callable=AsyncMock
    ) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        result = await aegis_proxy.generate(sample_task)

        # Verify zero tokens handled correctly
        assert result.tokens_used == 0
        assert result.tokens_input == 0
        assert result.tokens_output == 0
        assert result.cost_usd == 0.0


@pytest.mark.asyncio
async def test_token_parsing_missing_usage_entirely(aegis_proxy, sample_task):
    """Test token parsing when usage field is missing entirely."""
    # Mock ANY-LLM response without any usage field
    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Test response"))],
    )

    with patch(
        "src.domains.llm_integration.proxy.aegis_llm_proxy.acompletion", new_callable=AsyncMock
    ) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        result = await aegis_proxy.generate(sample_task)

        # Verify defaults to zero tokens
        assert result.tokens_used == 0
        assert result.tokens_input == 0
        assert result.tokens_output == 0


@pytest.mark.asyncio
async def test_cost_calculation_with_accurate_split(aegis_proxy, sample_task):
    """Test cost calculation uses accurate input/output token rates."""
    # Mock response for Alibaba Cloud with accurate token split
    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Test"))],
        usage=SimpleNamespace(
            prompt_tokens=1000,  # Input tokens
            completion_tokens=500,  # Output tokens
            total_tokens=1500,
        ),
    )

    with patch(
        "src.domains.llm_integration.proxy.aegis_llm_proxy.acompletion", new_callable=AsyncMock
    ) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        # Force routing to Alibaba Cloud
        sample_task.quality_requirement = QualityRequirement.HIGH
        sample_task.complexity = Complexity.HIGH

        result = await aegis_proxy.generate(sample_task)

        # Alibaba Cloud qwen-turbo pricing:
        # Input: $0.05 per 1M tokens = $0.00000005 per token
        # Output: $0.2 per 1M tokens = $0.0000002 per token
        expected_cost = (1000 / 1_000_000) * 0.05 + (500 / 1_000_000) * 0.2
        # = 0.00005 + 0.0001 = 0.00015

        assert result.cost_usd == pytest.approx(expected_cost, rel=1e-6)


@pytest.mark.asyncio
async def test_cost_calculation_with_fallback_estimation(aegis_proxy, sample_task):
    """Test cost calculation falls back to average rate when split unavailable."""
    # Mock response WITHOUT usage field
    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Test"))],
        tokens_used=1000,
        usage=None,
    )

    with patch(
        "src.domains.llm_integration.proxy.aegis_llm_proxy.acompletion", new_callable=AsyncMock
    ) as mock_acompletion:
        mock_acompletion.return_value = mock_response

        result = await aegis_proxy.generate(sample_task)

        # Local Ollama is free
        assert result.cost_usd == 0.0


def test_calculate_cost_accurate_split(mock_config):
    """Test _calculate_cost method with accurate input/output split."""
    with patch("src.domains.llm_integration.proxy.aegis_llm_proxy.CostTracker") as mock_tracker:
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.get_monthly_spending.return_value = {}
        mock_tracker.return_value = mock_tracker_instance

        proxy = AegisLLMProxy(config=mock_config)

        # Test Alibaba Cloud pricing
        cost = proxy._calculate_cost(
            provider="alibaba_cloud",
            tokens_input=1000,
            tokens_output=500,
            tokens_total=0,  # Should be ignored
        )

        # Expected: (1000/1M * $0.05) + (500/1M * $0.2) = $0.00015
        assert cost == pytest.approx(0.00015, rel=1e-6)

        # Test OpenAI pricing
        cost = proxy._calculate_cost(
            provider="openai",
            tokens_input=1000,
            tokens_output=500,
            tokens_total=0,
        )

        # Expected: (1000/1M * $2.50) + (500/1M * $10.00) = $0.0075
        assert cost == pytest.approx(0.0075, rel=1e-6)


def test_calculate_cost_fallback_legacy(mock_config):
    """Test _calculate_cost falls back to legacy pricing when split unavailable."""
    with patch("src.domains.llm_integration.proxy.aegis_llm_proxy.CostTracker") as mock_tracker:
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.get_monthly_spending.return_value = {}
        mock_tracker.return_value = mock_tracker_instance

        proxy = AegisLLMProxy(config=mock_config)

        # Test legacy fallback (input/output = 0, total > 0)
        cost = proxy._calculate_cost(
            provider="alibaba_cloud",
            tokens_input=0,
            tokens_output=0,
            tokens_total=1000,
        )

        # Expected: 1000/1M * $0.125 (average rate) = $0.000125
        assert cost == pytest.approx(0.000125, rel=1e-6)
