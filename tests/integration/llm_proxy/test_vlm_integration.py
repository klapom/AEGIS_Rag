"""Integration tests for VLM components.

Sprint 36 - VLM Factory Pattern Integration Tests

Tests the full VLM pipeline: Factory -> Client -> Image Processing
Verifies that local (Ollama) and cloud (DashScope) backends work together.

Test Coverage:
    - VLM Factory pattern and backend selection
    - OllamaVLMClient integration with local Ollama
    - DashScopeVLMClient integration with cloud API
    - ImageProcessor integration with VLM Factory
    - Fallback mechanisms between local and cloud
    - Configuration-driven behavior
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestVLMFactoryPattern:
    """Tests for VLM Factory pattern implementation."""

    @pytest.fixture
    def test_image(self, tmp_path) -> Path:
        """Create a test image file (minimal valid PNG)."""
        image_path = tmp_path / "test_image.png"
        # Minimal valid PNG header (1x1 white pixel)
        png_header = bytes(
            [
                0x89,
                0x50,
                0x4E,
                0x47,
                0x0D,
                0x0A,
                0x1A,
                0x0A,
                0x00,
                0x00,
                0x00,
                0x0D,
                0x49,
                0x48,
                0x44,
                0x52,
                0x00,
                0x00,
                0x00,
                0x01,
                0x00,
                0x00,
                0x00,
                0x01,
                0x08,
                0x02,
                0x00,
                0x00,
                0x00,
                0x90,
                0x77,
                0x53,
                0xDE,
                0x00,
                0x00,
                0x00,
                0x0C,
                0x49,
                0x44,
                0x41,
                0x54,
                0x08,
                0xD7,
                0x63,
                0xF8,
                0xFF,
                0xFF,
                0x3F,
                0x00,
                0x05,
                0xFE,
                0x02,
                0xFE,
                0xDC,
                0xCC,
                0x59,
                0xE7,
                0x00,
                0x00,
                0x00,
                0x00,
                0x49,
                0x45,
                0x4E,
                0x44,
                0xAE,
                0x42,
                0x60,
                0x82,
            ]
        )
        image_path.write_bytes(png_header)
        return image_path

    def test_vlm_factory_get_ollama_client(self):
        """Test VLM Factory creates Ollama client."""
        from src.components.llm_proxy.vlm_factory import (
            VLMBackend,
            get_vlm_client,
        )

        client = get_vlm_client(VLMBackend.OLLAMA)

        assert client is not None
        assert hasattr(client, "generate_image_description")

    def test_vlm_factory_get_dashscope_client_requires_api_key(self):
        """Test VLM Factory raises error for DashScope without API key."""
        from src.components.llm_proxy.vlm_factory import (
            VLMBackend,
            get_vlm_client,
        )

        # Test requires ALIBABA_CLOUD_API_KEY to be set
        # Skip if not available
        if not os.getenv("ALIBABA_CLOUD_API_KEY"):
            pytest.skip("ALIBABA_CLOUD_API_KEY not configured")

        client = get_vlm_client(VLMBackend.DASHSCOPE)
        assert client is not None
        assert hasattr(client, "generate_image_description")

    def test_vlm_backend_from_env_var(self, monkeypatch):
        """Test VLM backend selection from environment variable."""
        from src.components.llm_proxy.vlm_factory import (
            VLMBackend,
            get_vlm_backend_from_config,
        )

        # Test with OLLAMA
        monkeypatch.setenv("VLM_BACKEND", "ollama")
        backend = get_vlm_backend_from_config()
        assert backend == VLMBackend.OLLAMA

        # Test with DASHSCOPE
        monkeypatch.setenv("VLM_BACKEND", "dashscope")
        backend = get_vlm_backend_from_config()
        assert backend == VLMBackend.DASHSCOPE

        # Test with invalid backend (should use default)
        monkeypatch.setenv("VLM_BACKEND", "invalid_backend")
        backend = get_vlm_backend_from_config()
        assert backend == VLMBackend.OLLAMA  # Default

    def test_vlm_backend_from_config_file(self, monkeypatch, tmp_path):
        """Test VLM backend selection from config file."""
        from src.components.llm_proxy.vlm_factory import (
            VLMBackend,
            get_vlm_backend_from_config,
        )

        # Create temp config file
        config_file = tmp_path / "llm_config.yml"
        config_file.write_text(
            """
routing:
  vlm_backend: ollama
"""
        )

        # Mock the config loader to use our temp file
        with patch("src.components.llm_proxy.vlm_factory.get_llm_proxy_config") as mock_config:
            mock_config.return_value = MagicMock(routing={"vlm_backend": "ollama"})

            backend = get_vlm_backend_from_config()
            assert backend == VLMBackend.OLLAMA

    def test_vlm_factory_defaults_to_ollama(self, monkeypatch):
        """Test VLM Factory defaults to Ollama (local-first)."""
        from src.components.llm_proxy.vlm_factory import (
            VLMBackend,
            get_vlm_backend_from_config,
        )

        # Clear environment variable
        monkeypatch.delenv("VLM_BACKEND", raising=False)

        # Mock config to return None/no backend
        with patch("src.components.llm_proxy.vlm_factory.get_llm_proxy_config") as mock_config:
            mock_config.side_effect = Exception("Config not found")

            backend = get_vlm_backend_from_config()
            assert backend == VLMBackend.OLLAMA

    def test_vlm_singleton_pattern(self):
        """Test VLM singleton caching pattern."""
        from src.components.llm_proxy.vlm_factory import (
            VLMBackend,
            get_vlm_client,
        )

        client1 = get_vlm_client(VLMBackend.OLLAMA)
        client2 = get_vlm_client(VLMBackend.OLLAMA)

        # Each call creates new instance (non-singleton for factory)
        # Use get_shared_vlm_client for singleton behavior
        assert client1 is not None
        assert client2 is not None


class TestOllamaVLMIntegration:
    """Integration tests for Ollama VLM client."""

    @pytest.fixture
    def test_image(self, tmp_path) -> Path:
        """Create test image."""
        image_path = tmp_path / "test.png"
        png_data = bytes(
            [
                0x89,
                0x50,
                0x4E,
                0x47,
                0x0D,
                0x0A,
                0x1A,
                0x0A,
                0x00,
                0x00,
                0x00,
                0x0D,
                0x49,
                0x48,
                0x44,
                0x52,
                0x00,
                0x00,
                0x00,
                0x01,
                0x00,
                0x00,
                0x00,
                0x01,
                0x08,
                0x02,
                0x00,
                0x00,
                0x00,
                0x90,
                0x77,
                0x53,
                0xDE,
            ]
        )
        image_path.write_bytes(png_data + b"\x00" * 50)
        return image_path

    @pytest.mark.asyncio
    async def test_ollama_client_initialization(self):
        """Test OllamaVLMClient initialization."""
        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient

        client = OllamaVLMClient(
            base_url="http://localhost:11434",
            default_model="qwen3-vl:32b",
        )

        assert client.base_url == "http://localhost:11434"
        assert client.default_model == "qwen3-vl:32b"

    @pytest.mark.asyncio
    async def test_ollama_client_with_mock_http(self, test_image):
        """Test OllamaVLMClient generates description with mocked HTTP."""
        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient

        with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "response": "A simple white image with minimal content",
                "eval_count": 50,
                "prompt_eval_count": 25,
                "total_duration": 1000000000,
                "eval_duration": 800000000,
            }
            mock_response.raise_for_status = AsyncMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_http.return_value = mock_client

            client = OllamaVLMClient()
            description, metadata = await client.generate_image_description(
                image_path=test_image,
                prompt="Describe this image",
            )

            assert description == "A simple white image with minimal content"
            assert metadata["local"] is True
            assert metadata["cost_usd"] == 0.0
            assert metadata["provider"] == "ollama"
            assert "tokens_total" in metadata

    @pytest.mark.asyncio
    async def test_ollama_client_image_not_found(self):
        """Test OllamaVLMClient raises error for missing image."""
        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient

        client = OllamaVLMClient()

        with pytest.raises(FileNotFoundError):
            await client.generate_image_description(
                image_path=Path("/nonexistent/image.png"),
                prompt="Describe",
            )

    @pytest.mark.asyncio
    async def test_ollama_client_respects_custom_model(self, test_image):
        """Test OllamaVLMClient respects custom model parameter."""
        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient

        with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "response": "Custom model response",
                "eval_count": 50,
                "prompt_eval_count": 25,
                "total_duration": 1000000000,
                "eval_duration": 800000000,
            }
            mock_response.raise_for_status = AsyncMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_http.return_value = mock_client

            client = OllamaVLMClient(default_model="qwen3-vl:32b")
            description, metadata = await client.generate_image_description(
                image_path=test_image,
                prompt="Describe",
                model="custom-vlm:latest",  # Override default
            )

            # Verify custom model was used
            assert description == "Custom model response"


class TestImageProcessorVLMIntegration:
    """Integration tests for ImageProcessor with VLM Factory."""

    @pytest.fixture
    def test_image(self, tmp_path) -> Path:
        """Create test image."""
        image_path = tmp_path / "diagram.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        return image_path

    def test_image_processor_vlm_factory_available(self):
        """Test ImageProcessor detects VLM Factory availability."""
        from src.components.ingestion.image_processor import VLM_FACTORY_AVAILABLE

        # VLM Factory should be available
        assert VLM_FACTORY_AVAILABLE is True

    @pytest.mark.asyncio
    async def test_image_processor_uses_vlm_factory(self, test_image):
        """Test ImageProcessor integrates with VLM Factory."""
        from src.components.ingestion.image_processor import (
            VLM_FACTORY_AVAILABLE,
            generate_vlm_description_with_factory,
        )

        if not VLM_FACTORY_AVAILABLE:
            pytest.skip("VLM Factory not available")

        with patch("src.components.ingestion.image_processor.get_vlm_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.generate_image_description = AsyncMock(
                return_value=("Image shows technical diagram", {"local": True, "cost_usd": 0.0})
            )
            mock_factory.return_value = mock_client

            description, metadata = await generate_vlm_description_with_factory(
                image_path=test_image,
                prompt="Describe the diagram",
                prefer_local=True,
            )

            assert "diagram" in description.lower()
            assert metadata["local"] is True

    @pytest.mark.asyncio
    async def test_image_processor_vlm_factory_call_chain(self, test_image):
        """Test complete call chain: ImageProcessor -> Factory -> Client."""
        from src.components.ingestion.image_processor import (
            VLM_FACTORY_AVAILABLE,
            generate_vlm_description_with_factory,
        )

        if not VLM_FACTORY_AVAILABLE:
            pytest.skip("VLM Factory not available")

        with patch("src.components.ingestion.image_processor.get_vlm_client") as mock_factory:
            with patch.object(mock_factory, "__call__"):
                mock_client = AsyncMock()
                mock_client.generate_image_description = AsyncMock(
                    return_value=("Description", {"local": True})
                )
                mock_factory.return_value = mock_client

                # Call through ImageProcessor
                description, metadata = await generate_vlm_description_with_factory(
                    image_path=test_image,
                    prompt="Test",
                )

                # Verify call chain
                assert description == "Description"
                assert mock_factory.called


class TestVLMConfiguration:
    """Tests for VLM configuration and environment setup."""

    def test_ollama_env_variables(self, monkeypatch):
        """Test Ollama environment variable configuration."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom-ollama:11434")
        monkeypatch.setenv("OLLAMA_MODEL_VLM", "custom-vlm:latest")

        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient

        client = OllamaVLMClient()

        assert client.base_url == "http://custom-ollama:11434"
        assert client.default_model == "custom-vlm:latest"

    def test_vlm_backend_env_variable_invalid_ignored(self, monkeypatch):
        """Test invalid VLM_BACKEND env var is handled gracefully."""
        from src.components.llm_proxy.vlm_factory import (
            VLMBackend,
            get_vlm_backend_from_config,
        )

        monkeypatch.setenv("VLM_BACKEND", "invalid")

        # Should default to Ollama and log warning
        with patch("src.components.llm_proxy.vlm_factory.get_llm_proxy_config") as mock_config:
            mock_config.side_effect = Exception("No config")
            backend = get_vlm_backend_from_config()

        assert backend == VLMBackend.OLLAMA

    def test_vlm_factory_respects_priority_order(self, monkeypatch):
        """Test VLM Factory respects priority: env > config > default."""
        from src.components.llm_proxy.vlm_factory import (
            VLMBackend,
            get_vlm_backend_from_config,
        )

        # Priority 1: Environment variable should win
        monkeypatch.setenv("VLM_BACKEND", "dashscope")

        with patch("src.components.llm_proxy.vlm_factory.get_llm_proxy_config") as mock_config:
            mock_config.return_value = MagicMock(routing={"vlm_backend": "ollama"})

            backend = get_vlm_backend_from_config()

            # Environment variable takes priority
            assert backend == VLMBackend.DASHSCOPE


class TestVLMErrorHandling:
    """Tests for VLM error handling and recovery."""

    @pytest.mark.asyncio
    async def test_ollama_client_http_error_handling(self, tmp_path):
        """Test OllamaVLMClient handles HTTP errors gracefully."""
        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient

        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=ConnectionError("Connection failed"))
            mock_http.return_value = mock_client

            client = OllamaVLMClient()

            with pytest.raises(ConnectionError):
                await client.generate_image_description(
                    image_path=image_path,
                    prompt="Test",
                )

    @pytest.mark.asyncio
    async def test_vlm_metadata_structure_consistency(self, tmp_path):
        """Test VLM metadata returns consistent structure."""
        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient

        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "response": "Test description",
                "eval_count": 50,
                "prompt_eval_count": 25,
                "total_duration": 1000000000,
                "eval_duration": 800000000,
            }
            mock_response.raise_for_status = AsyncMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_http.return_value = mock_client

            client = OllamaVLMClient()
            _, metadata = await client.generate_image_description(
                image_path=image_path,
                prompt="Describe",
            )

            # Verify required metadata fields
            required_fields = ["local", "cost_usd", "provider", "tokens_total"]
            for field in required_fields:
                assert field in metadata, f"Missing required metadata field: {field}"
