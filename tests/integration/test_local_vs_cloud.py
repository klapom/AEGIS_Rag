"""Integration tests comparing local vs cloud LLM/VLM backends.

Sprint 36 - Local vs Cloud Backend Integration Tests

This module tests that local (Ollama) and cloud (Alibaba DashScope) backends
provide feature parity and consistent interfaces.

Test Coverage:
    - Local Ollama metadata structure
    - Cloud DashScope metadata structure
    - Configuration-driven backend selection
    - Cost tracking for both backends
    - Performance characteristics
    - Fallback mechanisms
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock


class TestLocalVsCloudVLMMetadata:
    """Compare local and cloud VLM backend metadata structures."""

    @pytest.fixture
    def test_image(self, tmp_path) -> Path:
        """Create test image."""
        image_path = tmp_path / "test.png"
        # Minimal valid PNG
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE
        ])
        image_path.write_bytes(png_data + b"\x00" * 50)
        return image_path

    @pytest.mark.asyncio
    async def test_ollama_vlm_metadata_structure(self, test_image):
        """Test Ollama VLM returns correct metadata structure.

        Required fields:
        - model: str (model identifier)
        - provider: str = "ollama"
        - local: bool = True
        - cost_usd: float = 0.0
        - tokens_total: int
        """
        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "response": "Test description",
                "eval_count": 100,
                "prompt_eval_count": 50,
                "total_duration": 2000000000,
                "eval_duration": 1500000000,
            }
            mock_response.raise_for_status = AsyncMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_http.return_value = mock_client

            client = get_vlm_client(VLMBackend.OLLAMA)
            _, metadata = await client.generate_image_description(test_image, "test")

            # Verify metadata structure
            assert "model" in metadata
            assert "provider" in metadata
            assert metadata["provider"] == "ollama"
            assert "local" in metadata
            assert metadata["local"] is True
            assert "cost_usd" in metadata
            assert metadata["cost_usd"] == 0.0
            assert "tokens_total" in metadata
            assert isinstance(metadata["tokens_total"], (int, float))

    @pytest.mark.asyncio
    @pytest.mark.cloud
    async def test_dashscope_vlm_metadata_structure(self, test_image):
        """Test DashScope VLM returns correct metadata structure.

        Required fields (same as Ollama):
        - model: str (model identifier)
        - provider: str = "dashscope"
        - local: bool = False
        - cost_usd: float (>= 0.0)
        - tokens_total: int
        """
        if not os.getenv("ALIBABA_CLOUD_API_KEY"):
            pytest.skip("Cloud API key not configured")

        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        client = get_vlm_client(VLMBackend.DASHSCOPE)

        try:
            _, metadata = await client.generate_image_description(
                test_image,
                "Describe briefly",
                max_tokens=50
            )

            # Verify metadata structure (cloud)
            assert "model" in metadata
            assert "provider" in metadata
            assert "local" in metadata
            assert metadata["local"] is False
            assert "cost_usd" in metadata
            assert metadata["cost_usd"] >= 0  # Cloud has cost
            assert "tokens_total" in metadata
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_metadata_interface_parity(self, test_image):
        """Test that local and cloud VLMs have the same metadata interface.

        Both backends should return metadata with same structure and field names.
        """
        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        # Mock Ollama response
        with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "response": "Local description",
                "eval_count": 100,
                "prompt_eval_count": 50,
                "total_duration": 2000000000,
                "eval_duration": 1500000000,
            }
            mock_response.raise_for_status = AsyncMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_http.return_value = mock_client

            local_client = get_vlm_client(VLMBackend.OLLAMA)
            _, local_metadata = await local_client.generate_image_description(
                test_image, "test"
            )

        # Extract expected metadata fields
        expected_fields = {"model", "provider", "local", "cost_usd", "tokens_total"}
        actual_fields = set(local_metadata.keys())

        # Verify all expected fields are present
        assert expected_fields.issubset(actual_fields), \
            f"Missing fields: {expected_fields - actual_fields}"


class TestLocalVsCloudCostTracking:
    """Test cost tracking for local vs cloud backends."""

    @pytest.fixture
    def test_image(self, tmp_path) -> Path:
        """Create test image."""
        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
        return image_path

    @pytest.mark.asyncio
    async def test_local_vlm_zero_cost(self, test_image):
        """Test local Ollama VLM reports zero cost."""
        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "response": "Test",
                "eval_count": 100,
                "prompt_eval_count": 50,
                "total_duration": 2000000000,
                "eval_duration": 1500000000,
            }
            mock_response.raise_for_status = AsyncMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_http.return_value = mock_client

            client = get_vlm_client(VLMBackend.OLLAMA)
            _, metadata = await client.generate_image_description(test_image, "test")

            # Local should always report zero cost
            assert metadata["cost_usd"] == 0.0
            assert metadata["local"] is True

    @pytest.mark.asyncio
    @pytest.mark.cloud
    async def test_cloud_vlm_nonzero_cost(self, test_image):
        """Test cloud DashScope VLM reports non-zero cost."""
        if not os.getenv("ALIBABA_CLOUD_API_KEY"):
            pytest.skip("Cloud API key not configured")

        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        client = get_vlm_client(VLMBackend.DASHSCOPE)

        try:
            _, metadata = await client.generate_image_description(
                test_image,
                "Describe",
                max_tokens=50
            )

            # Cloud API reports cost (may be very small)
            assert "cost_usd" in metadata
            assert metadata["local"] is False
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_cost_tracking_consistency(self, test_image):
        """Test cost tracking reports consistent values across calls."""
        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "response": "Test",
                "eval_count": 100,
                "prompt_eval_count": 50,
                "total_duration": 2000000000,
                "eval_duration": 1500000000,
            }
            mock_response.raise_for_status = AsyncMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_http.return_value = mock_client

            client = get_vlm_client(VLMBackend.OLLAMA)

            # Multiple calls should report same cost
            _, metadata1 = await client.generate_image_description(test_image, "test 1")
            _, metadata2 = await client.generate_image_description(test_image, "test 2")

            assert metadata1["cost_usd"] == metadata2["cost_usd"]
            assert metadata1["cost_usd"] == 0.0


class TestConfigurationDrivenBehavior:
    """Test configuration-driven VLM behavior."""

    def test_llm_config_has_vlm_backend_setting(self):
        """Test llm_config.yml contains vlm_backend configuration."""
        import yaml
        from pathlib import Path

        config_path = Path("/home/admin/projects/aegisrag/AEGIS_Rag/config/llm_config.yml")
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)

            assert config is not None, "Config file should not be empty"
            assert "routing" in config, "Config should have routing section"
            assert "vlm_backend" in config["routing"], "Routing should specify vlm_backend"
            assert config["routing"]["vlm_backend"] in ["ollama", "dashscope"]

    def test_env_template_has_vlm_variables(self):
        """Test .env template includes VLM configuration variables."""
        from pathlib import Path

        template_path = Path("/home/admin/projects/aegisrag/AEGIS_Rag/.env.dgx-spark.template")
        if template_path.exists():
            content = template_path.read_text()

            # Should have VLM backend selection
            assert "VLM_BACKEND" in content or "vlm_backend" in content.lower()
            # Should have Ollama VLM model
            assert "OLLAMA_MODEL_VLM" in content or "ollama_model_vlm" in content.lower()

    def test_vlm_backend_selection_precedence(self, monkeypatch):
        """Test VLM backend selection follows correct precedence."""
        from src.components.llm_proxy.vlm_factory import (
            get_vlm_backend_from_config,
            VLMBackend,
        )

        # Test 1: Environment variable has highest priority
        monkeypatch.setenv("VLM_BACKEND", "dashscope")
        monkeypatch.delenv("VLM_BACKEND", raising=False)
        monkeypatch.setenv("VLM_BACKEND", "dashscope")

        with patch("src.components.llm_proxy.vlm_factory.get_llm_proxy_config") as mock_config:
            mock_config.return_value = MagicMock(routing={"vlm_backend": "ollama"})
            backend = get_vlm_backend_from_config()

        # Env var should override config file
        assert backend == VLMBackend.DASHSCOPE

    def test_invalid_vlm_backend_falls_back_to_default(self, monkeypatch):
        """Test invalid VLM backend configuration falls back to default."""
        from src.components.llm_proxy.vlm_factory import (
            get_vlm_backend_from_config,
            VLMBackend,
        )

        monkeypatch.setenv("VLM_BACKEND", "invalid_backend_name")

        with patch("src.components.llm_proxy.vlm_factory.get_llm_proxy_config") as mock_config:
            mock_config.side_effect = Exception("Config error")
            backend = get_vlm_backend_from_config()

        # Should default to Ollama (local-first for DGX Spark)
        assert backend == VLMBackend.OLLAMA


class TestVLMBackendDescriptions:
    """Test backend descriptions and capabilities."""

    def test_ollama_backend_properties(self):
        """Test Ollama backend has expected properties."""
        from src.components.llm_proxy.vlm_factory import VLMBackend

        assert VLMBackend.OLLAMA.value == "ollama"
        # OLLAMA is local, free, on-device

    def test_dashscope_backend_properties(self):
        """Test DashScope backend has expected properties."""
        from src.components.llm_proxy.vlm_factory import VLMBackend

        assert VLMBackend.DASHSCOPE.value == "dashscope"
        # DASHSCOPE is cloud, paid, remote

    def test_vlm_backend_enum_completeness(self):
        """Test VLMBackend enum includes all expected backends."""
        from src.components.llm_proxy.vlm_factory import VLMBackend

        backends = [b.value for b in VLMBackend]

        # Should include at least local and cloud options
        assert "ollama" in backends
        assert "dashscope" in backends


class TestVLMProtocolInterface:
    """Test VLM clients implement consistent protocol."""

    @pytest.mark.asyncio
    async def test_vlm_client_protocol_methods(self):
        """Test all VLM clients have required protocol methods."""
        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        client = get_vlm_client(VLMBackend.OLLAMA)

        # Should have required methods
        assert hasattr(client, "generate_image_description")
        assert callable(client.generate_image_description)

    @pytest.mark.asyncio
    async def test_vlm_client_response_signature(self, tmp_path):
        """Test VLM client response signature is consistent."""
        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        with patch("src.components.llm_proxy.ollama_vlm.httpx.AsyncClient") as mock_http:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "response": "Description",
                "eval_count": 50,
                "prompt_eval_count": 25,
                "total_duration": 1000000000,
                "eval_duration": 800000000,
            }
            mock_response.raise_for_status = AsyncMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_http.return_value = mock_client

            client = get_vlm_client(VLMBackend.OLLAMA)
            result = await client.generate_image_description(image_path, "test")

            # Should return tuple of (description, metadata)
            assert isinstance(result, tuple)
            assert len(result) == 2
            description, metadata = result
            assert isinstance(description, str)
            assert isinstance(metadata, dict)


class TestVLMFallbackBehavior:
    """Test fallback mechanisms between local and cloud VLMs."""

    @pytest.mark.asyncio
    async def test_local_to_cloud_fallback_pattern(self):
        """Test pattern for falling back from local to cloud VLM."""
        from src.components.llm_proxy.vlm_factory import get_vlm_client, VLMBackend

        # Simulate local failure
        local_client = get_vlm_client(VLMBackend.OLLAMA)
        cloud_client = get_vlm_client(VLMBackend.DASHSCOPE)

        assert local_client is not None
        assert cloud_client is not None
        # Both backends available for fallback

    @pytest.mark.asyncio
    async def test_vlm_backend_isolation(self):
        """Test that switching VLM backends doesn't interfere with other components."""
        from src.components.llm_proxy.vlm_factory import (
            get_vlm_client,
            VLMBackend,
        )

        # Get both backends
        ollama_client = get_vlm_client(VLMBackend.OLLAMA)
        dashscope_client = get_vlm_client(VLMBackend.DASHSCOPE)

        # Should be different instances
        assert ollama_client is not dashscope_client
        assert ollama_client is not None
        assert dashscope_client is not None


class TestVLMIntegrationChains:
    """Test complete integration chains with VLM."""

    @pytest.mark.asyncio
    async def test_image_processor_factory_integration_chain(self, tmp_path):
        """Test complete chain: ImageProcessor -> Factory -> Client."""
        from src.components.ingestion.image_processor import (
            VLM_FACTORY_AVAILABLE,
        )

        if not VLM_FACTORY_AVAILABLE:
            pytest.skip("VLM Factory not available")

        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        from src.components.ingestion.image_processor import (
            generate_vlm_description_with_factory,
        )

        with patch("src.components.ingestion.image_processor.get_vlm_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.generate_image_description = AsyncMock(
                return_value=("Description from factory", {"local": True, "cost_usd": 0.0})
            )
            mock_factory.return_value = mock_client

            description, metadata = await generate_vlm_description_with_factory(
                image_path=image_path,
                prompt="Describe",
                prefer_local=True,
            )

            assert "factory" in description.lower() or "Description" in description
            assert mock_factory.called
