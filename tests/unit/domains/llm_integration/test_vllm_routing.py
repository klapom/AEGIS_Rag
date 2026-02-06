"""
Unit tests for vLLM routing in AegisLLMProxy.

Sprint 125 Feature 125.2: vLLM Provider Integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.domains.llm_integration.models import LLMTask, TaskType, DataClassification
from src.domains.llm_integration.proxy.aegis_llm_proxy import AegisLLMProxy


@pytest.fixture
def mock_config():
    """Mock LLMProxyConfig for testing."""
    config = MagicMock()
    config.providers = {"local_ollama": {"base_url": "http://localhost:11434"}}
    config.budgets = {"monthly_limits": {}}
    config.routing = {}
    config.is_provider_enabled = MagicMock(return_value=True)
    config.get_budget_limit = MagicMock(return_value=0.0)
    config.get_default_model = MagicMock(return_value="nemotron-3-nano")
    return config


@pytest.fixture
def mock_settings():
    """Mock settings for vLLM configuration."""
    with patch("src.core.config.settings") as mock_settings:
        mock_settings.vllm_enabled = True
        mock_settings.vllm_base_url = "http://localhost:8001"
        mock_settings.vllm_model = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4"
        yield mock_settings


@pytest.mark.asyncio
async def test_vllm_health_check_success(mock_config, mock_settings):
    """Test vLLM health check returns True when service is healthy."""
    proxy = AegisLLMProxy(config=mock_config)

    with patch("httpx.AsyncClient") as mock_client:
        # Mock successful health check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        is_healthy = await proxy._check_vllm_health()

        assert is_healthy is True
        assert proxy._vllm_health_cache is True


@pytest.mark.asyncio
async def test_vllm_health_check_failure(mock_config, mock_settings):
    """Test vLLM health check returns False when service is down."""
    proxy = AegisLLMProxy(config=mock_config)

    with patch("httpx.AsyncClient") as mock_client:
        # Mock failed health check
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        is_healthy = await proxy._check_vllm_health()

        assert is_healthy is False
        assert proxy._vllm_health_cache is False


@pytest.mark.asyncio
async def test_vllm_health_check_caching(mock_config, mock_settings):
    """Test vLLM health check uses cache within TTL."""
    proxy = AegisLLMProxy(config=mock_config)

    with patch("httpx.AsyncClient") as mock_client:
        # Mock successful health check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # First call - should hit network
        await proxy._check_vllm_health()
        assert mock_get.call_count == 1

        # Second call within TTL - should use cache
        await proxy._check_vllm_health()
        assert mock_get.call_count == 1  # No additional call


@pytest.mark.asyncio
async def test_vllm_routing_for_extraction_task(mock_config, mock_settings):
    """Test that extraction tasks are routed to vLLM when enabled and healthy."""
    proxy = AegisLLMProxy(config=mock_config)

    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt="Extract entities from text",
        data_classification=DataClassification.PUBLIC,
    )

    # Mock vLLM health check
    with patch.object(proxy, "_check_vllm_health", return_value=True):
        provider, reason = await proxy._route_task(task)

        assert provider == "vllm"
        assert reason == "extraction_high_concurrency"


@pytest.mark.asyncio
async def test_vllm_routing_fallback_when_unhealthy(mock_config, mock_settings):
    """Test that extraction tasks fall back to Ollama when vLLM is unhealthy."""
    proxy = AegisLLMProxy(config=mock_config)

    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt="Extract entities from text",
        data_classification=DataClassification.PUBLIC,
    )

    # Mock vLLM health check failure
    with patch.object(proxy, "_check_vllm_health", return_value=False):
        provider, reason = await proxy._route_task(task)

        # Should fall back to local_ollama (default)
        assert provider == "local_ollama"
        assert "extraction_high_concurrency" not in reason


@pytest.mark.asyncio
async def test_vllm_routing_disabled(mock_config):
    """Test that vLLM is not used when disabled."""
    # Override settings to disable vLLM
    with patch("src.core.config.settings") as mock_settings:
        mock_settings.vllm_enabled = False
        mock_settings.vllm_base_url = "http://localhost:8001"
        mock_settings.vllm_model = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4"

        proxy = AegisLLMProxy(config=mock_config)

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract entities from text",
            data_classification=DataClassification.PUBLIC,
        )

        provider, reason = await proxy._route_task(task)

        # Should route to local_ollama when vLLM disabled
        assert provider == "local_ollama"
        assert "extraction_high_concurrency" not in reason


@pytest.mark.asyncio
async def test_vllm_call_success(mock_config, mock_settings):
    """Test successful vLLM API call."""
    proxy = AegisLLMProxy(config=mock_config)

    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt="Extract entities from text",
    )

    with patch("httpx.AsyncClient") as mock_client:
        # Mock successful vLLM response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Entity: John Smith (Person)"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        }
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        response = await proxy._call_vllm(task)

        assert response.content == "Entity: John Smith (Person)"
        assert response.provider == "vllm"
        assert response.tokens_input == 10
        assert response.tokens_output == 8
        assert response.tokens_used == 18
        assert response.cost_usd == 0.0  # Local deployment is free


@pytest.mark.asyncio
async def test_vllm_routing_respects_data_classification(mock_config, mock_settings):
    """Test that sensitive data always routes to local Ollama, not vLLM."""
    proxy = AegisLLMProxy(config=mock_config)

    # Test PII classification
    task_pii = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt="Extract entities from medical record",
        data_classification=DataClassification.PII,
    )

    with patch.object(proxy, "_check_vllm_health", return_value=True):
        provider, reason = await proxy._route_task(task_pii)

        assert provider == "local_ollama"
        assert reason == "sensitive_data_local_only"


@pytest.mark.asyncio
async def test_vllm_cost_calculation(mock_config, mock_settings):
    """Test that vLLM costs are calculated as $0.00."""
    proxy = AegisLLMProxy(config=mock_config)

    cost = proxy._calculate_cost(
        provider="vllm",
        tokens_input=100,
        tokens_output=50,
        tokens_total=150,
    )

    assert cost == 0.0


@pytest.mark.asyncio
async def test_vllm_model_selection(mock_config, mock_settings):
    """Test that vLLM uses configured model."""
    proxy = AegisLLMProxy(config=mock_config)

    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt="Extract entities",
    )

    model = proxy._get_model_for_provider("vllm", task)

    assert model == "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4"
