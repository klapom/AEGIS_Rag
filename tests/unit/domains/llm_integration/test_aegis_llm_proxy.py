"""Unit tests for AegisLLMProxy - Extended coverage for routing and streaming.

Tests focus on:
- Provider routing logic (data privacy, task type, budget, complexity)
- Streaming response handling
- Error handling and fallback mechanisms
- Budget tracking and enforcement
- Streaming execution and token yielding
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import LLMExecutionError
from src.domains.llm_integration.models import (
    Complexity,
    DataClassification,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.domains.llm_integration.proxy.aegis_llm_proxy import AegisLLMProxy


class TestRoutingLogic:
    """Test provider routing decision logic."""

    @pytest.mark.asyncio
    async def test_routing_sensitive_data_always_local(self, aegis_proxy_with_config) -> None:
        """Test sensitive data (PII, HIPAA) always routes to local."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract PII from document",
            data_classification=DataClassification.PII,
            quality_requirement=QualityRequirement.CRITICAL,
            complexity=Complexity.VERY_HIGH,
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "local_ollama"
        assert reason == "sensitive_data_local_only_engine_auto"

    @pytest.mark.asyncio
    async def test_routing_hipaa_data_always_local(self, aegis_proxy_with_config) -> None:
        """Test HIPAA data always routes to local."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract medical records",
            data_classification=DataClassification.HIPAA,
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "local_ollama"
        assert reason == "sensitive_data_local_only_engine_auto"

    @pytest.mark.asyncio
    async def test_routing_confidential_data_always_local(self, aegis_proxy_with_config) -> None:
        """Test confidential data always routes to local."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract trade secrets",
            data_classification=DataClassification.CONFIDENTIAL,
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "local_ollama"
        assert reason == "sensitive_data_local_only_engine_auto"

    @pytest.mark.asyncio
    async def test_routing_embeddings_always_local(self, aegis_proxy_with_config) -> None:
        """Test embedding task type always routes to local."""
        task = LLMTask(
            task_type=TaskType.EMBEDDING,
            prompt="Generate embeddings",
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "local_ollama"
        assert reason == "embeddings_local_only_engine_auto"

    @pytest.mark.asyncio
    async def test_routing_vision_task_to_alibaba_cloud(self, aegis_proxy_with_config) -> None:
        """Test vision tasks prefer Alibaba Cloud."""
        task = LLMTask(
            task_type=TaskType.VISION,
            prompt="Describe image",
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "alibaba_cloud"
        assert reason == "vision_task_best_vlm"

    @pytest.mark.asyncio
    async def test_routing_vision_task_fallback_local(self, aegis_proxy_with_config) -> None:
        """Test vision task falls back to local if Alibaba Cloud disabled."""
        config = aegis_proxy_with_config.config
        config.providers.pop("alibaba_cloud", None)

        task = LLMTask(
            task_type=TaskType.VISION,
            prompt="Describe image",
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "local_ollama"
        assert reason == "vision_task_local_fallback"

    @pytest.mark.asyncio
    async def test_routing_critical_quality_high_complexity_openai(
        self, aegis_proxy_with_config
    ) -> None:
        """Test critical quality + high complexity routes to OpenAI."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract from legal document",
            quality_requirement=QualityRequirement.CRITICAL,
            complexity=Complexity.HIGH,
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "openai"
        assert reason == "critical_quality_high_complexity"

    @pytest.mark.asyncio
    async def test_routing_critical_quality_very_high_complexity_openai(
        self, aegis_proxy_with_config
    ) -> None:
        """Test critical quality + very high complexity routes to OpenAI."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Complex extraction task",
            quality_requirement=QualityRequirement.CRITICAL,
            complexity=Complexity.VERY_HIGH,
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "openai"

    @pytest.mark.asyncio
    async def test_routing_high_quality_high_complexity_alibaba(
        self, aegis_proxy_with_config
    ) -> None:
        """Test high quality + high complexity routes to Alibaba Cloud."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="High quality extraction",
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "alibaba_cloud"
        assert reason == "high_quality_high_complexity"

    @pytest.mark.asyncio
    async def test_routing_batch_processing_alibaba(self, aegis_proxy_with_config) -> None:
        """Test batch processing (>10 docs) routes to Alibaba Cloud."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract from 100 documents",
            batch_size=100,
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "alibaba_cloud"
        assert reason == "batch_processing"

    @pytest.mark.asyncio
    async def test_routing_small_batch_local(self, aegis_proxy_with_config) -> None:
        """Test small batch (<10 docs) routes to local."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract from 5 documents",
            batch_size=5,
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "local_ollama"
        assert reason == "default_local_engine_auto"

    @pytest.mark.asyncio
    async def test_routing_prefer_cloud_flag(self, aegis_proxy_with_config) -> None:
        """Test prefer_cloud routing configuration."""
        aegis_proxy_with_config.config.routing["prefer_cloud"] = True

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract entities",
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "alibaba_cloud"
        assert reason == "prefer_cloud_extraction_generation"

    @pytest.mark.asyncio
    async def test_routing_budget_exceeded_fallback(self, aegis_proxy_with_config) -> None:
        """Test fallback to local when budget exceeded."""
        # Set budget to exceeded
        aegis_proxy_with_config._monthly_spending["openai"] = 25.0
        aegis_proxy_with_config.config.budgets["monthly_limits"]["openai"] = 20.0

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract",
            quality_requirement=QualityRequirement.CRITICAL,
            complexity=Complexity.HIGH,
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        # Should fall back from OpenAI due to budget
        assert provider in ["alibaba_cloud", "local_ollama"]

    @pytest.mark.asyncio
    async def test_routing_default_local(self, aegis_proxy_with_config) -> None:
        """Test default routing to local for simple tasks."""
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Generate a response",
            quality_requirement=QualityRequirement.LOW,
            complexity=Complexity.LOW,
        )

        provider, reason = await aegis_proxy_with_config._route_task(task)

        assert provider == "local_ollama"
        assert reason == "default_local_engine_auto"


class TestBudgetTracking:
    """Test budget checking and tracking."""

    def test_budget_not_exceeded_returns_false(self, aegis_proxy_with_config) -> None:
        """Test budget check returns False when under limit."""
        aegis_proxy_with_config._monthly_spending["alibaba_cloud"] = 5.0

        is_exceeded = aegis_proxy_with_config._is_budget_exceeded("alibaba_cloud")

        assert not is_exceeded

    def test_budget_exceeded_returns_true(self, aegis_proxy_with_config) -> None:
        """Test budget check returns True when exceeded."""
        aegis_proxy_with_config._monthly_spending["alibaba_cloud"] = 11.0

        is_exceeded = aegis_proxy_with_config._is_budget_exceeded("alibaba_cloud")

        assert is_exceeded

    def test_budget_at_limit_returns_true(self, aegis_proxy_with_config) -> None:
        """Test budget check returns True when exactly at limit."""
        aegis_proxy_with_config._monthly_spending["alibaba_cloud"] = 10.0

        is_exceeded = aegis_proxy_with_config._is_budget_exceeded("alibaba_cloud")

        assert is_exceeded

    def test_local_ollama_never_budget_exceeded(self, aegis_proxy_with_config) -> None:
        """Test local ollama always has budget available."""
        is_exceeded = aegis_proxy_with_config._is_budget_exceeded("local_ollama")

        assert not is_exceeded

    def test_no_limit_configured_never_exceeded(self, aegis_proxy_with_config) -> None:
        """Test provider with no limit never exceeds budget."""
        aegis_proxy_with_config.config.budgets["monthly_limits"].pop("openai", None)

        is_exceeded = aegis_proxy_with_config._is_budget_exceeded("openai")

        assert not is_exceeded


class TestCostCalculation:
    """Test cost calculation for different providers."""

    def test_calculate_cost_local_ollama_free(self, aegis_proxy_with_config) -> None:
        """Test local Ollama has zero cost."""
        cost = aegis_proxy_with_config._calculate_cost(
            provider="local_ollama",
            tokens_input=1000,
            tokens_output=500,
        )

        assert cost == 0.0

    def test_calculate_cost_alibaba_cloud_accurate_split(self, aegis_proxy_with_config) -> None:
        """Test Alibaba Cloud cost with input/output split."""
        cost = aegis_proxy_with_config._calculate_cost(
            provider="alibaba_cloud",
            tokens_input=1000000,  # 1M input tokens
            tokens_output=1000000,  # 1M output tokens
        )

        # $0.05 per 1M input + $0.2 per 1M output = $0.25
        assert cost == pytest.approx(0.25, rel=1e-3)

    def test_calculate_cost_openai_accurate_split(self, aegis_proxy_with_config) -> None:
        """Test OpenAI cost with input/output split."""
        cost = aegis_proxy_with_config._calculate_cost(
            provider="openai",
            tokens_input=1000000,  # 1M input tokens
            tokens_output=1000000,  # 1M output tokens
        )

        # $2.50 per 1M input + $10.00 per 1M output = $12.50
        assert cost == pytest.approx(12.50, rel=1e-3)

    def test_calculate_cost_fallback_legacy_pricing(self, aegis_proxy_with_config) -> None:
        """Test fallback to legacy pricing when input/output unavailable."""
        cost = aegis_proxy_with_config._calculate_cost(
            provider="alibaba_cloud",
            tokens_input=0,
            tokens_output=0,
            tokens_total=1000000,  # 1M total tokens
        )

        # $0.125 per 1M (average of input/output pricing)
        assert cost == pytest.approx(0.125, rel=1e-3)

    def test_calculate_cost_tracks_total(self, aegis_proxy_with_config) -> None:
        """Test cost calculation updates total cost tracking."""
        initial_total = aegis_proxy_with_config._total_cost

        aegis_proxy_with_config._calculate_cost(
            provider="openai",
            tokens_input=1000000,
            tokens_output=1000000,
        )

        assert aegis_proxy_with_config._total_cost > initial_total


class TestGetModelForProvider:
    """Test model selection for providers."""

    def test_get_model_task_preference_local(self, aegis_proxy_with_config) -> None:
        """Test task-specific model preference is used for local."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract",
            model_local="custom-local-model",
        )

        model = aegis_proxy_with_config._get_model_for_provider("local_ollama", task)

        assert model == "custom-local-model"

    def test_get_model_task_preference_cloud(self, aegis_proxy_with_config) -> None:
        """Test task-specific model preference for cloud."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract",
            model_cloud="custom-cloud-model",
        )

        model = aegis_proxy_with_config._get_model_for_provider("alibaba_cloud", task)

        assert model == "custom-cloud-model"

    def test_get_model_config_default_local(self, aegis_proxy_with_config) -> None:
        """Test config default model for local."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract",
        )

        model = aegis_proxy_with_config._get_model_for_provider("local_ollama", task)

        assert model == "gemma-3-4b-it-Q8_0"

    def test_get_model_config_default_cloud(self, aegis_proxy_with_config) -> None:
        """Test config default model for cloud."""
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract",
        )

        model = aegis_proxy_with_config._get_model_for_provider("alibaba_cloud", task)

        assert model == "qwen-turbo"


class TestStreamingExecution:
    """Test streaming response handling."""

    @pytest.mark.asyncio
    async def test_generate_streaming_yields_content(self, aegis_proxy_with_config) -> None:
        """Test streaming execution yields content chunks."""
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Generate a response",
        )

        # Mock streaming response
        async def mock_stream():
            yield {"content": "Hello "}
            yield {"content": "world"}

        with patch.object(
            aegis_proxy_with_config,
            "_execute_streaming",
            return_value=mock_stream(),
        ):
            chunks = []
            async for chunk in aegis_proxy_with_config.generate_streaming(task):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0]["content"] == "Hello "
            assert chunks[1]["content"] == "world"

    @pytest.mark.asyncio
    async def test_streaming_provider_error_fallback_to_local(
        self, aegis_proxy_with_config
    ) -> None:
        """Test streaming falls back when cloud provider fails.

        Sprint 128: Routing now checks engine_mode. In auto mode, if routed to
        cloud and it fails, falls back to local_ollama.
        """
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Generate",
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
        )

        # Route to alibaba_cloud first (high quality + high complexity)
        # then fallback to local_ollama
        async def mock_succeed():
            chunk = SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="Fallback"))]
            )
            yield chunk

        call_count = 0

        async def mock_execute_streaming(provider, task):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and provider == "alibaba_cloud":
                raise LLMExecutionError("Provider failed")
            else:
                async for chunk in mock_succeed():
                    yield chunk

        with patch.object(
            aegis_proxy_with_config, "_execute_streaming", side_effect=mock_execute_streaming
        ):
            chunks = []
            async for chunk in aegis_proxy_with_config.generate_streaming(task):
                chunks.append(chunk)

            assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_streaming_all_providers_fail_raises_error(self, aegis_proxy_with_config) -> None:
        """Test streaming raises error when provider fails with no fallback.

        Sprint 128: In auto mode, when local_ollama fails there's no different
        fallback (fallback_provider == provider), so it raises immediately.
        """
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Generate",
        )

        async def mock_fail(*args, **kwargs):
            raise LLMExecutionError("Provider failed")

        with (
            patch.object(
                aegis_proxy_with_config,
                "_execute_streaming",
                side_effect=mock_fail,
            ),
            pytest.raises(LLMExecutionError, match="LLM provider local_ollama failed"),
        ):
            async for _ in aegis_proxy_with_config.generate_streaming(task):
                pass


class TestMetricsTracking:
    """Test metrics tracking and monitoring."""

    def test_track_metrics_increments_request_count(self, aegis_proxy_with_config) -> None:
        """Test metrics tracking increments request counter."""
        from src.domains.llm_integration.models import LLMResponse

        initial_count = aegis_proxy_with_config._request_count

        task = LLMTask(task_type=TaskType.EXTRACTION, prompt="Test")
        result = LLMResponse(
            content="Response",
            provider="local_ollama",
            model="test-model",
            tokens_used=100,
            cost_usd=0.0,
        )

        aegis_proxy_with_config._track_metrics("local_ollama", task, result)

        assert aegis_proxy_with_config._request_count == initial_count + 1

    def test_track_metrics_persists_to_database(self, aegis_proxy_with_config) -> None:
        """Test metrics tracking persists data to cost tracker."""
        from src.domains.llm_integration.models import LLMResponse

        task = LLMTask(task_type=TaskType.EXTRACTION, prompt="Test")
        result = LLMResponse(
            content="Response",
            provider="alibaba_cloud",
            model="qwen-turbo",
            tokens_used=1000,
            tokens_input=500,
            tokens_output=500,
            cost_usd=0.05,
            latency_ms=100.0,
        )

        # Verify cost_tracker.track_request is called
        aegis_proxy_with_config._track_metrics("alibaba_cloud", task, result)
        aegis_proxy_with_config.cost_tracker.track_request.assert_called_once()


class TestMetricsSummary:
    """Test metrics summary retrieval."""

    def test_get_metrics_summary_contains_request_count(self, aegis_proxy_with_config) -> None:
        """Test metrics summary includes request count."""
        summary = aegis_proxy_with_config.get_metrics_summary()

        assert "request_count" in summary
        assert isinstance(summary["request_count"], int)

    def test_get_metrics_summary_contains_total_cost(self, aegis_proxy_with_config) -> None:
        """Test metrics summary includes total cost."""
        summary = aegis_proxy_with_config.get_metrics_summary()

        assert "total_cost_usd" in summary
        assert isinstance(summary["total_cost_usd"], float)

    def test_get_metrics_summary_contains_providers(self, aegis_proxy_with_config) -> None:
        """Test metrics summary includes enabled providers."""
        summary = aegis_proxy_with_config.get_metrics_summary()

        assert "providers_enabled" in summary
        assert isinstance(summary["providers_enabled"], list)


class TestConfigValidation:
    """Test configuration validation."""

    def test_init_requires_local_ollama_provider(self, mock_llm_config) -> None:
        """Test initialization fails without local_ollama provider."""
        # Remove local_ollama from config
        mock_llm_config.providers.pop("local_ollama", None)

        with pytest.raises(ValueError, match="local_ollama provider is required"):
            AegisLLMProxy(config=mock_llm_config)

    def test_init_with_disabled_local_ollama_raises(self, mock_llm_config) -> None:
        """Test initialization fails if local_ollama is not enabled."""
        mock_llm_config.providers["local_ollama"] = {}  # Missing base_url

        with pytest.raises(ValueError, match="local_ollama provider is required"):
            AegisLLMProxy(config=mock_llm_config)


# ============================================================================
# Fixtures for tests
# ============================================================================


@pytest.fixture
def aegis_proxy_with_config(mock_llm_config):
    """Create AegisLLMProxy instance with mock config and cost tracker."""
    with patch("src.domains.llm_integration.proxy.aegis_llm_proxy.CostTracker") as mock_tracker:
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.get_monthly_spending.return_value = {
            "alibaba_cloud": 0.0,
            "openai": 0.0,
        }
        mock_tracker.return_value = mock_tracker_instance

        proxy = AegisLLMProxy(config=mock_llm_config)
        proxy.cost_tracker = mock_tracker_instance
        # Mock _get_engine_mode to avoid Redis dependency (Sprint 128)
        proxy._get_engine_mode = AsyncMock(return_value="auto")
        # Disable vLLM in unit tests to test original routing logic
        proxy._vllm_enabled = False
        return proxy


class TestVLLMActiveRequests:
    """Test vLLM active request monitoring for cascade guard.

    Sprint 128 Feature 128.2: Cascade timeout guard.
    """

    @pytest.mark.asyncio
    async def test_get_vllm_active_requests_success(self) -> None:
        """Test parsing vLLM Prometheus metrics for active requests."""
        # Mock vLLM metrics response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
# HELP vllm:num_requests_running Number of requests currently running
# TYPE vllm:num_requests_running gauge
vllm:num_requests_running{model="nemotron-3-nano:128k"} 2.0
# HELP vllm:num_requests_waiting Number of requests waiting in queue
# TYPE vllm:num_requests_waiting gauge
vllm:num_requests_waiting{model="nemotron-3-nano:128k"} 1.0
"""

        # Create proxy with vLLM enabled
        proxy = AegisLLMProxy()
        proxy._vllm_enabled = True
        proxy._vllm_base_url = "http://localhost:8001"

        # Mock httpx client with AsyncMock for async context manager
        with patch("httpx.AsyncClient") as mock_httpx_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

            # Get active requests
            active = await proxy.get_vllm_active_requests()

            # Assertions
            assert active == 3  # 2 running + 1 waiting
            mock_client_instance.get.assert_called_once_with("http://localhost:8001/metrics")

    @pytest.mark.asyncio
    async def test_get_vllm_active_requests_vllm_disabled(self) -> None:
        """Test get_vllm_active_requests returns 0 when vLLM is disabled."""
        # Create proxy with vLLM disabled
        proxy = AegisLLMProxy()
        proxy._vllm_enabled = False

        # Get active requests (should return 0 immediately)
        active = await proxy.get_vllm_active_requests()

        # Assertions
        assert active == 0
        # No need to check httpx - it's not called

    @pytest.mark.asyncio
    async def test_get_vllm_active_requests_metrics_unavailable(self) -> None:
        """Test get_vllm_active_requests returns 0 when metrics endpoint fails."""
        # Mock vLLM metrics response with error status
        mock_response = MagicMock()
        mock_response.status_code = 404

        # Create proxy with vLLM enabled
        proxy = AegisLLMProxy()
        proxy._vllm_enabled = True
        proxy._vllm_base_url = "http://localhost:8001"

        with patch("httpx.AsyncClient") as mock_httpx_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

            # Get active requests
            active = await proxy.get_vllm_active_requests()

            # Assertions
            assert active == 0  # Default to 0 on error

    @pytest.mark.asyncio
    async def test_get_vllm_active_requests_connection_error(self) -> None:
        """Test get_vllm_active_requests returns 0 when connection fails."""
        # Create proxy with vLLM enabled
        proxy = AegisLLMProxy()
        proxy._vllm_enabled = True
        proxy._vllm_base_url = "http://localhost:8001"

        with patch("httpx.AsyncClient") as mock_httpx_client:
            # Mock httpx client to raise exception
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

            # Get active requests
            active = await proxy.get_vllm_active_requests()

            # Assertions
            assert active == 0  # Default to 0 on error

    @pytest.mark.asyncio
    async def test_get_vllm_active_requests_malformed_metrics(self) -> None:
        """Test get_vllm_active_requests handles malformed metrics gracefully."""
        # Mock vLLM metrics response with malformed data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
# HELP vllm:num_requests_running Number of requests currently running
vllm:num_requests_running{model="nemotron-3-nano:128k"} invalid_value
vllm:num_requests_waiting{model="nemotron-3-nano:128k"} also_invalid
"""

        # Create proxy with vLLM enabled
        proxy = AegisLLMProxy()
        proxy._vllm_enabled = True
        proxy._vllm_base_url = "http://localhost:8001"

        with patch("httpx.AsyncClient") as mock_httpx_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

            # Get active requests
            active = await proxy.get_vllm_active_requests()

            # Assertions
            assert active == 0  # Falls back to 0 on parse error

    @pytest.mark.asyncio
    async def test_get_vllm_active_requests_zero_active(self) -> None:
        """Test get_vllm_active_requests correctly returns 0 when no requests active."""
        # Mock vLLM metrics response with zero active requests
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
vllm:num_requests_running{model="nemotron-3-nano:128k"} 0.0
vllm:num_requests_waiting{model="nemotron-3-nano:128k"} 0.0
"""

        # Create proxy with vLLM enabled
        proxy = AegisLLMProxy()
        proxy._vllm_enabled = True
        proxy._vllm_base_url = "http://localhost:8001"

        with patch("httpx.AsyncClient") as mock_httpx_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

            # Get active requests
            active = await proxy.get_vllm_active_requests()

            # Assertions
            assert active == 0
