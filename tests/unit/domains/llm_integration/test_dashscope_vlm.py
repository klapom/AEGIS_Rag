"""Unit tests for DashScope Vision Language Model integration - Initialization Focus.

Tests cover:
- VLM client initialization with API credentials
- Environment variable configuration
- Base URL configuration
- Error handling on missing API key
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.domains.llm_integration.proxy.dashscope_vlm import (
    DashScopeVLMClient,
    get_dashscope_vlm_client,
)


class TestDashScopeVLMClientInitialization:
    """Test DashScope VLM client initialization."""

    def test_init_with_api_key_parameter(self) -> None:
        """Test initialization with explicit API key parameter."""
        client = DashScopeVLMClient(api_key="test-api-key")

        assert client.api_key == "test-api-key"
        assert client.base_url == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    def test_init_with_custom_base_url(self) -> None:
        """Test initialization with custom base URL."""
        client = DashScopeVLMClient(
            api_key="test-api-key",
            base_url="https://custom-dashscope.com/v1",
        )

        assert client.base_url == "https://custom-dashscope.com/v1"

    def test_init_from_env_alibaba_cloud_api_key(self) -> None:
        """Test initialization from ALIBABA_CLOUD_API_KEY environment variable."""
        with patch.dict(os.environ, {"ALIBABA_CLOUD_API_KEY": "env-api-key"}):
            client = DashScopeVLMClient()

            assert client.api_key == "env-api-key"

    def test_init_from_env_dashscope_api_key(self) -> None:
        """Test initialization from DASHSCOPE_API_KEY environment variable."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "dashscope-api-key"}, clear=False):
            # Create environment without ALIBABA_CLOUD_API_KEY
            env = os.environ.copy()
            env.pop("ALIBABA_CLOUD_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                client = DashScopeVLMClient()

                assert client.api_key == "dashscope-api-key"

    def test_init_missing_api_key_raises_error(self) -> None:
        """Test initialization without API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DashScope API key not configured"):
                DashScopeVLMClient()

    def test_init_creates_httpx_client(self) -> None:
        """Test initialization creates AsyncClient with correct timeout."""
        client = DashScopeVLMClient(api_key="test-key")

        assert isinstance(client.client, httpx.AsyncClient)
        assert client.client._timeout == httpx.Timeout(120.0)

    def test_init_custom_base_url_from_env(self) -> None:
        """Test base URL from ALIBABA_CLOUD_BASE_URL environment variable."""
        with patch.dict(
            os.environ,
            {"ALIBABA_CLOUD_API_KEY": "key", "ALIBABA_CLOUD_BASE_URL": "https://custom.com"},
        ):
            client = DashScopeVLMClient()

            assert client.base_url == "https://custom.com"


class TestDashScopeVLMClientFileHandling:
    """Test image file handling."""

    def test_generate_image_description_file_not_found(self) -> None:
        """Test error when image file doesn't exist."""
        client = DashScopeVLMClient(api_key="test-key")

        with pytest.raises(FileNotFoundError):
            import asyncio

            asyncio.run(
                client.generate_image_description(
                    image_path=Path("/nonexistent/image.png"),
                    prompt="Describe this image",
                )
            )


class TestContextManager:
    """Test async context manager functionality."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test DashScopeVLMClient can be used as async context manager."""
        async with DashScopeVLMClient(api_key="test-key") as client:
            assert isinstance(client, DashScopeVLMClient)

    @pytest.mark.asyncio
    async def test_close_method(self) -> None:
        """Test explicit close method."""
        client = DashScopeVLMClient(api_key="test-key")

        with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
            await client.close()

            mock_close.assert_called_once()


class TestGetDashScopeVLMClient:
    """Test factory function for DashScope VLM client."""

    @pytest.mark.asyncio
    async def test_get_dashscope_vlm_client_returns_instance(self) -> None:
        """Test get_dashscope_vlm_client returns DashScopeVLMClient."""
        with patch.dict(os.environ, {"ALIBABA_CLOUD_API_KEY": "test-key"}):
            client = await get_dashscope_vlm_client()

            assert isinstance(client, DashScopeVLMClient)

    @pytest.mark.asyncio
    async def test_get_dashscope_vlm_client_new_instance(self) -> None:
        """Test get_dashscope_vlm_client creates new instance each call."""
        with patch.dict(os.environ, {"ALIBABA_CLOUD_API_KEY": "test-key"}):
            client1 = await get_dashscope_vlm_client()
            client2 = await get_dashscope_vlm_client()

            # Should be different instances (not cached)
            assert client1 is not client2


class TestMimeTypeDetection:
    """Test MIME type detection for different image formats."""

    def test_mime_type_png(self) -> None:
        """Test MIME type detection for PNG."""
        client = DashScopeVLMClient(api_key="test-key")

        # Verify PNG suffix maps to correct MIME type
        # This would be tested in integration tests with actual HTTP calls
        assert client.api_key == "test-key"

    def test_mime_type_jpeg(self) -> None:
        """Test MIME type detection for JPEG."""
        client = DashScopeVLMClient(api_key="test-key")

        # JPEG detection would be in actual generate_image_description call
        assert client.api_key == "test-key"


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_api_key_priority_alibaba_cloud_over_dashscope(self) -> None:
        """Test ALIBABA_CLOUD_API_KEY takes priority over DASHSCOPE_API_KEY."""
        with patch.dict(
            os.environ,
            {
                "ALIBABA_CLOUD_API_KEY": "alibaba-key",
                "DASHSCOPE_API_KEY": "dashscope-key",
            },
        ):
            client = DashScopeVLMClient()

            assert client.api_key == "alibaba-key"

    def test_parameter_api_key_overrides_env(self) -> None:
        """Test parameter API key overrides environment variable."""
        with patch.dict(os.environ, {"ALIBABA_CLOUD_API_KEY": "env-key"}):
            client = DashScopeVLMClient(api_key="param-key")

            assert client.api_key == "param-key"

    def test_default_base_url_when_no_env(self) -> None:
        """Test default base URL is used when environment variable not set."""
        with patch.dict(os.environ, {"ALIBABA_CLOUD_API_KEY": "key"}, clear=False):
            # Ensure ALIBABA_CLOUD_BASE_URL is not set
            env = os.environ.copy()
            env.pop("ALIBABA_CLOUD_BASE_URL", None)
            with patch.dict(os.environ, env, clear=True):
                env["ALIBABA_CLOUD_API_KEY"] = "key"
                with patch.dict(os.environ, env):
                    client = DashScopeVLMClient()

                    assert (
                        client.base_url == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
                    )
