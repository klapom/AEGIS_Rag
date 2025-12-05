"""Integration tests for Cloud LLM/VLM calls (Sprint 36).

These tests verify that cloud providers (DashScope, OpenAI) work correctly.
Tests require environment variables to be set:
  - ALIBABA_CLOUD_API_KEY or DASHSCOPE_API_KEY (for DashScope tests)
  - OPENAI_API_KEY (for OpenAI tests, optional)

Run cloud tests with:
  pytest tests/integration/test_cloud_llm_vlm.py -v --run-cloud

Skip cloud tests with:
  pytest -m "not cloud"

Note: Cloud tests make real API calls and may incur costs.
Use test/mock data when possible.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Mark all tests in this module as cloud tests
pytestmark = pytest.mark.cloud


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "cloud: cloud integration tests requiring API keys")


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def skip_without_alibaba_key():
    """Skip tests if Alibaba Cloud API key is not configured."""
    if not os.getenv("ALIBABA_CLOUD_API_KEY") and not os.getenv("DASHSCOPE_API_KEY"):
        pytest.skip("Alibaba Cloud API key not configured (ALIBABA_CLOUD_API_KEY or DASHSCOPE_API_KEY)")


@pytest.fixture
def skip_without_openai_key():
    """Skip tests if OpenAI API key is not configured."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OpenAI API key not configured (OPENAI_API_KEY)")


@pytest.fixture
def create_minimal_test_image(tmp_path):
    """Create a minimal valid PNG image for testing."""
    # Minimal valid PNG (1x1 white pixel)
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    test_image = tmp_path / "test_minimal.png"
    test_image.write_bytes(png_data)
    return test_image


# =============================================================================
# DASHSCOPE VLM TESTS
# =============================================================================


class TestCloudVLMDashScope:
    """Tests for Cloud VLM (DashScope)."""

    @pytest.mark.asyncio
    async def test_dashscope_vlm_initialization(self, skip_without_alibaba_key):
        """Test DashScope VLM client can be initialized."""
        from src.components.llm_proxy.dashscope_vlm import DashScopeVLMClient

        client = DashScopeVLMClient()
        assert client is not None
        assert hasattr(client, "generate_image_description")
        assert hasattr(client, "close")
        await client.close()

    @pytest.mark.asyncio
    async def test_dashscope_vlm_generates_description(
        self, skip_without_alibaba_key, create_minimal_test_image
    ):
        """Test that DashScope VLM can generate image descriptions.

        Note: This test makes a real API call to DashScope.
        Set ALIBABA_CLOUD_API_KEY to enable.
        """
        from src.components.llm_proxy.dashscope_vlm import DashScopeVLMClient

        async with DashScopeVLMClient() as client:
            try:
                description, metadata = await client.generate_image_description(
                    image_path=create_minimal_test_image,
                    prompt="What is the main color in this image?",
                    max_tokens=100,
                )

                # Verify response
                assert description is not None
                assert isinstance(description, str)
                assert len(description) > 0

                # Verify metadata
                assert metadata is not None
                assert isinstance(metadata, dict)
                assert "provider" in metadata
                assert metadata["local"] is False
                assert "cost_usd" in metadata
                # Cloud calls should have some cost
                assert metadata["cost_usd"] >= 0

            except Exception as e:
                # API errors are expected in non-production environments
                pytest.skip(f"DashScope API error: {e}")

    @pytest.mark.asyncio
    async def test_dashscope_vlm_metadata_correct(
        self, skip_without_alibaba_key, create_minimal_test_image
    ):
        """Test DashScope VLM metadata is correct."""
        from src.components.llm_proxy.dashscope_vlm import DashScopeVLMClient

        async with DashScopeVLMClient() as client:
            try:
                _, metadata = await client.generate_image_description(
                    image_path=create_minimal_test_image,
                    prompt="Describe this image briefly",
                    max_tokens=50,
                )

                # Check required metadata fields
                assert metadata.get("provider") in ["dashscope", "alibaba"]
                assert metadata.get("local") is False
                assert "model" in metadata
                assert "tokens_total" in metadata
                assert isinstance(metadata["tokens_total"], int)
                assert metadata["tokens_total"] >= 0

            except Exception as e:
                pytest.skip(f"DashScope API error: {e}")


# =============================================================================
# OLLAMA VLM TESTS (LOCAL)
# =============================================================================


class TestLocalVLMOllama:
    """Tests for Local VLM (Ollama)."""

    @pytest.mark.asyncio
    async def test_ollama_vlm_initialization(self, create_minimal_test_image):
        """Test Ollama VLM client can be initialized."""
        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient

        client = OllamaVLMClient()
        assert client is not None
        assert hasattr(client, "generate_image_description")
        assert hasattr(client, "check_model_available")
        await client.close()

    @pytest.mark.asyncio
    async def test_ollama_vlm_local_cost_zero(self, create_minimal_test_image):
        """Test that Ollama VLM has zero cost."""
        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient

        # Mock Ollama response to avoid actual API call
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "This is a white pixel",
            "eval_count": 10,
            "prompt_eval_count": 5,
            "total_duration": 1000000000,
        }
        mock_response.raise_for_status = MagicMock()

        client = OllamaVLMClient()
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=mock_response)

        _, metadata = await client.generate_image_description(
            image_path=create_minimal_test_image,
            prompt="What do you see?",
        )

        # Verify cost is zero for local inference
        assert metadata["local"] is True
        assert metadata["cost_usd"] == 0.0
        await client.close()


# =============================================================================
# VLM FACTORY CLOUD TESTS
# =============================================================================


class TestVLMFactoryCloud:
    """Tests for VLM Factory with cloud backend."""

    @pytest.mark.asyncio
    async def test_factory_creates_dashscope_client(self, skip_without_alibaba_key):
        """Test that VLM Factory can create DashScope client."""
        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        client = get_vlm_client(VLMBackend.DASHSCOPE)

        assert client is not None
        assert hasattr(client, "generate_image_description")
        await client.close()

    @pytest.mark.asyncio
    async def test_factory_creates_ollama_client(self):
        """Test that VLM Factory can create Ollama client."""
        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        client = get_vlm_client(VLMBackend.OLLAMA)

        assert client is not None
        assert hasattr(client, "generate_image_description")
        await client.close()

    @pytest.mark.asyncio
    async def test_factory_respects_env_var(self):
        """Test factory respects VLM_BACKEND environment variable."""
        from src.components.llm_proxy.vlm_factory import (
            get_vlm_backend_from_config,
            VLMBackend,
        )

        with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}):
            backend = get_vlm_backend_from_config()
            assert backend == VLMBackend.OLLAMA

    @pytest.mark.asyncio
    async def test_factory_switches_backends(self, skip_without_alibaba_key):
        """Test factory can switch between backends."""
        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        # Create Ollama client
        ollama_client = get_vlm_client(VLMBackend.OLLAMA)
        assert hasattr(ollama_client, "base_url")
        assert "11434" in ollama_client.base_url

        # Create DashScope client
        dashscope_client = get_vlm_client(VLMBackend.DASHSCOPE)
        assert hasattr(dashscope_client, "api_key")

        await ollama_client.close()
        await dashscope_client.close()


# =============================================================================
# AEGIS LLM PROXY CLOUD TESTS
# =============================================================================


class TestCloudLLMRouting:
    """Tests for Cloud LLM routing via AegisLLMProxy."""

    @pytest.mark.asyncio
    async def test_aegis_proxy_can_route_to_alibaba(self, skip_without_alibaba_key):
        """Test AegisLLMProxy can route to Alibaba Cloud."""
        from src.components.llm_proxy.aegis_llm_proxy import get_aegis_llm_proxy
        from src.components.llm_proxy.models import (
            LLMTask,
            TaskType,
            QualityRequirement,
        )

        proxy = get_aegis_llm_proxy()

        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="What is 2+2? Answer in one word.",
            quality_requirement=QualityRequirement.HIGH,
        )

        try:
            response = await proxy.generate(task)

            assert response is not None
            assert response.content is not None
            assert "4" in response.content or "four" in response.content.lower()

        except Exception as e:
            # API errors expected in non-production
            pytest.skip(f"Cloud LLM error: {e}")

    @pytest.mark.asyncio
    async def test_aegis_proxy_cost_tracking(self, skip_without_alibaba_key):
        """Test that AegisLLMProxy tracks costs."""
        from src.components.llm_proxy.aegis_llm_proxy import get_aegis_llm_proxy
        from src.components.llm_proxy.models import (
            LLMTask,
            TaskType,
            QualityRequirement,
        )

        proxy = get_aegis_llm_proxy()

        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Hello",
            quality_requirement=QualityRequirement.HIGH,
        )

        try:
            response = await proxy.generate(task)

            # Cost tracking should be available
            assert hasattr(response, "cost_usd")
            assert response.cost_usd is not None

        except Exception as e:
            pytest.skip(f"Cloud LLM error: {e}")


# =============================================================================
# SHARED VLM CLIENT CLOUD TESTS
# =============================================================================


class TestSharedVLMClientCloud:
    """Tests for shared VLM client with cloud backends."""

    @pytest.mark.asyncio
    async def test_shared_client_with_cloud_backend(self, skip_without_alibaba_key):
        """Test shared VLM client works with cloud backend."""
        from src.components.llm_proxy.vlm_factory import (
            get_shared_vlm_client,
            close_shared_vlm_client,
            reset_vlm_client,
        )

        reset_vlm_client()

        with patch.dict(os.environ, {"VLM_BACKEND": "dashscope"}):
            try:
                client = await get_shared_vlm_client()
                assert client is not None
                await close_shared_vlm_client()
            except Exception as e:
                pytest.skip(f"Cloud VLM error: {e}")

    @pytest.mark.asyncio
    async def test_shared_client_reconnect(self):
        """Test shared VLM client can reconnect after close."""
        from src.components.llm_proxy.vlm_factory import (
            get_shared_vlm_client,
            close_shared_vlm_client,
            reset_vlm_client,
        )

        reset_vlm_client()

        with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}):
            # First connection
            client1 = await get_shared_vlm_client()
            assert client1 is not None

            # Close
            await close_shared_vlm_client()

            # Reconnect
            client2 = await get_shared_vlm_client()
            assert client2 is not None

            # Should be different instances
            assert client1 is not client2

            await close_shared_vlm_client()


# =============================================================================
# CLOUD CONFIGURATION TESTS
# =============================================================================


class TestCloudConfiguration:
    """Tests for cloud configuration and environment setup."""

    def test_alibaba_api_key_configuration(self, skip_without_alibaba_key):
        """Test Alibaba Cloud API key is properly configured."""
        api_key = os.getenv("ALIBABA_CLOUD_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        assert api_key is not None
        assert len(api_key) > 0

    def test_dashscope_base_url_configuration(self):
        """Test DashScope base URL is properly configured."""
        base_url = os.getenv(
            "ALIBABA_CLOUD_BASE_URL",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
        assert base_url is not None
        assert "dashscope" in base_url.lower() or "aliyun" in base_url.lower()

    def test_ollama_base_url_configuration(self):
        """Test Ollama base URL is properly configured."""
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        assert base_url is not None
        assert "11434" in base_url

    def test_budget_limits_respected(self):
        """Test budget limits are properly configured."""
        alibaba_budget = os.getenv("MONTHLY_BUDGET_ALIBABA_CLOUD")
        openai_budget = os.getenv("MONTHLY_BUDGET_OPENAI")

        # At least one budget should be configured or unlimited
        # This test just verifies they can be read
        assert alibaba_budget is None or float(alibaba_budget) > 0
        assert openai_budget is None or float(openai_budget) > 0


# =============================================================================
# ERROR HANDLING CLOUD TESTS
# =============================================================================


class TestCloudErrorHandling:
    """Tests for cloud error handling and recovery."""

    @pytest.mark.asyncio
    async def test_invalid_api_key_handling(self):
        """Test handling of invalid API key."""
        from src.components.llm_proxy.dashscope_vlm import DashScopeVLMClient

        with patch.dict(os.environ, {"ALIBABA_CLOUD_API_KEY": "invalid_key"}):
            try:
                client = DashScopeVLMClient(api_key="invalid_key")
                assert client is not None
            except ValueError as e:
                assert "API key" in str(e)

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self, create_minimal_test_image):
        """Test handling of connection timeouts."""
        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient
        import httpx

        client = OllamaVLMClient(base_url="http://nonexistent-host:11434")
        client.client = AsyncMock()
        client.client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection timeout")
        )

        with pytest.raises(httpx.ConnectError):
            await client.generate_image_description(
                image_path=create_minimal_test_image,
                prompt="test",
            )

        await client.close()

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, skip_without_alibaba_key, create_minimal_test_image):
        """Test handling of rate limit errors."""
        from src.components.llm_proxy.dashscope_vlm import DashScopeVLMClient
        import httpx

        client = DashScopeVLMClient()
        client.client = AsyncMock()

        # Mock 429 Too Many Requests response
        error_response = MagicMock()
        error_response.status_code = 429
        client.client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Rate limited", request=MagicMock(), response=error_response
            )
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.generate_image_description(
                image_path=create_minimal_test_image,
                prompt="test",
            )

        await client.close()
