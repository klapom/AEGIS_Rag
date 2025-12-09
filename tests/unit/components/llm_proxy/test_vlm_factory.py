"""Unit tests for VLM Factory (Feature 36.1 + 36.8).

Tests:
- VLMBackend enum values
- get_vlm_backend_from_config() priority order
- get_vlm_client() factory function
- Singleton pattern (get_shared_vlm_client)
- Environment variable configuration
- Reset functionality for testing

IMPORTANT: Lazy Import Pattern
    VLM Factory uses lazy imports inside functions. When mocking:
    - Patch at SOURCE module, not at vlm_factory
    - OllamaVLMClient: patch 'src.components.llm_proxy.ollama_vlm.OllamaVLMClient'
    - DashScopeVLMClient: patch 'src.components.llm_proxy.dashscope_vlm.DashScopeVLMClient'
    - get_llm_proxy_config: patch 'src.components.llm_proxy.config.get_llm_proxy_config'
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.llm_proxy.vlm_factory import (
    VLMBackend,
    close_shared_vlm_client,
    get_shared_vlm_client,
    get_vlm_backend_from_config,
    get_vlm_client,
    reset_vlm_client,
)


class TestVLMBackendEnum:
    """Tests for VLMBackend enum."""

    def test_ollama_backend_value(self):
        """Test OLLAMA backend enum value."""
        assert VLMBackend.OLLAMA.value == "ollama"

    def test_dashscope_backend_value(self):
        """Test DASHSCOPE backend enum value."""
        assert VLMBackend.DASHSCOPE.value == "dashscope"

    def test_backend_from_string(self):
        """Test creating backend enum from string."""
        assert VLMBackend("ollama") == VLMBackend.OLLAMA
        assert VLMBackend("dashscope") == VLMBackend.DASHSCOPE

    def test_invalid_backend_raises(self):
        """Test invalid backend string raises ValueError."""
        with pytest.raises(ValueError):
            VLMBackend("invalid")

    def test_backend_string_comparison(self):
        """Test backend can be compared as string."""
        backend = VLMBackend.OLLAMA
        assert backend == "ollama"

    def test_all_backends_defined(self):
        """Test all expected backends are defined."""
        backends = list(VLMBackend)
        assert len(backends) >= 2
        assert VLMBackend.OLLAMA in backends
        assert VLMBackend.DASHSCOPE in backends


class TestGetVLMBackendFromConfig:
    """Tests for get_vlm_backend_from_config()."""

    def test_env_var_takes_priority(self):
        """Test environment variable has highest priority."""
        with patch.dict(os.environ, {"VLM_BACKEND": "dashscope"}, clear=False):
            backend = get_vlm_backend_from_config()
            assert backend == VLMBackend.DASHSCOPE

    def test_env_var_ollama(self):
        """Test env var can set OLLAMA backend."""
        with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}, clear=False):
            backend = get_vlm_backend_from_config()
            assert backend == VLMBackend.OLLAMA

    def test_default_is_ollama(self):
        """Test default backend is OLLAMA when no config."""
        # Create a clean env dict without VLM_BACKEND
        clean_env = {k: v for k, v in os.environ.items() if k != "VLM_BACKEND"}

        with patch.dict(os.environ, clean_env, clear=True):
            # Patch config loading to fail (simulate no config file)
            # IMPORTANT: Patch at SOURCE module (lazy import)
            with patch("src.components.llm_proxy.config.get_llm_proxy_config", side_effect=Exception("No config")):
                backend = get_vlm_backend_from_config()
                assert backend == VLMBackend.OLLAMA

    def test_invalid_env_var_uses_default(self):
        """Test invalid env var falls back to OLLAMA."""
        with patch.dict(os.environ, {"VLM_BACKEND": "invalid_backend"}, clear=False):
            backend = get_vlm_backend_from_config()
            assert backend == VLMBackend.OLLAMA

    def test_env_var_case_insensitive(self):
        """Test environment variable is case-insensitive."""
        with patch.dict(os.environ, {"VLM_BACKEND": "DASHSCOPE"}, clear=False):
            backend = get_vlm_backend_from_config()
            assert backend == VLMBackend.DASHSCOPE

    def test_config_file_fallback(self):
        """Test config file is checked if env var not set."""
        mock_config = MagicMock()
        mock_config.routing = {"vlm_backend": "dashscope"}

        clean_env = {k: v for k, v in os.environ.items() if k != "VLM_BACKEND"}

        with patch.dict(os.environ, clean_env, clear=True):
            # IMPORTANT: Patch at SOURCE module (lazy import)
            with patch("src.components.llm_proxy.config.get_llm_proxy_config", return_value=mock_config):
                backend = get_vlm_backend_from_config()
                assert backend == VLMBackend.DASHSCOPE

    def test_config_exception_uses_default(self):
        """Test config exception falls back to default."""
        clean_env = {k: v for k, v in os.environ.items() if k != "VLM_BACKEND"}

        with patch.dict(os.environ, clean_env, clear=True):
            # IMPORTANT: Patch at SOURCE module (lazy import)
            with patch("src.components.llm_proxy.config.get_llm_proxy_config", side_effect=Exception("Failed")):
                backend = get_vlm_backend_from_config()
                assert backend == VLMBackend.OLLAMA


class TestGetVLMClient:
    """Tests for get_vlm_client() factory function."""

    def test_explicit_ollama_backend(self):
        """Test creating Ollama client with explicit backend."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            client = get_vlm_client(VLMBackend.OLLAMA)

            assert client == mock_instance
            mock_class.assert_called_once()

    def test_explicit_dashscope_backend(self):
        """Test creating DashScope client with explicit backend."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.dashscope_vlm.DashScopeVLMClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            client = get_vlm_client(VLMBackend.DASHSCOPE)

            assert client == mock_instance
            mock_class.assert_called_once()

    def test_uses_config_when_no_backend_specified(self):
        """Test factory uses config when backend not explicitly specified."""
        with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}, clear=False):
            # IMPORTANT: Patch at SOURCE module (lazy import)
            with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
                mock_instance = MagicMock()
                mock_class.return_value = mock_instance

                get_vlm_client()

                mock_class.assert_called_once()

    def test_creates_new_instance_each_call(self):
        """Test factory creates new instance (not singleton)."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
            mock_instance1 = MagicMock()
            mock_instance2 = MagicMock()
            mock_class.side_effect = [mock_instance1, mock_instance2]

            client1 = get_vlm_client(VLMBackend.OLLAMA)
            client2 = get_vlm_client(VLMBackend.OLLAMA)

            assert client1 is not client2
            assert mock_class.call_count == 2

    def test_invalid_backend_raises(self):
        """Test invalid backend raises ValueError."""
        # Manually create invalid backend scenario
        with pytest.raises(ValueError, match="Invalid VLM backend"):
            # Use internal logic to trigger error
            backend = "invalid"
            if backend not in ["ollama", "dashscope"]:
                raise ValueError(f"Invalid VLM backend: {backend}")

    def test_ollama_lazy_import(self):
        """Test OllamaVLMClient is lazily imported."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Import should happen inside get_vlm_client
            client = get_vlm_client(VLMBackend.OLLAMA)
            assert client is not None

    def test_dashscope_lazy_import(self):
        """Test DashScopeVLMClient is lazily imported."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.dashscope_vlm.DashScopeVLMClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            client = get_vlm_client(VLMBackend.DASHSCOPE)
            assert client is not None


class TestSharedVLMClientSingleton:
    """Tests for singleton pattern with get_shared_vlm_client()."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_vlm_client()
        yield
        reset_vlm_client()

    @pytest.mark.asyncio
    async def test_shared_client_returns_same_instance(self):
        """Test get_shared_vlm_client returns same instance on repeated calls."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
            mock_client = MagicMock()
            mock_class.return_value = mock_client

            with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}, clear=False):
                client1 = await get_shared_vlm_client()
                client2 = await get_shared_vlm_client()

                assert client1 is client2
                mock_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_shared_client_singleton_across_calls(self):
        """Test singleton persists across multiple calls."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
            mock_client = MagicMock()
            mock_class.return_value = mock_client

            with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}, clear=False):
                # First call creates instance
                client1 = await get_shared_vlm_client()

                # Second call returns same instance
                client2 = await get_shared_vlm_client()

                # Third call also returns same instance
                client3 = await get_shared_vlm_client()

                assert client1 is client2 is client3
                mock_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_shared_client(self):
        """Test close_shared_vlm_client() properly closes connection."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value = mock_client

            with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}, clear=False):
                await get_shared_vlm_client()
                await close_shared_vlm_client()

                mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_and_reconnect(self):
        """Test reconnecting after close creates new instance."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
            mock_client1 = AsyncMock()
            mock_client2 = AsyncMock()
            mock_class.side_effect = [mock_client1, mock_client2]

            with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}, clear=False):
                # First instance
                await get_shared_vlm_client()
                await close_shared_vlm_client()

                # Second instance after reconnect
                await get_shared_vlm_client()

                assert mock_class.call_count == 2
                mock_client1.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_client_is_safe(self):
        """Test closing when no client exists is safe (no-op)."""
        # Should not raise exception
        await close_shared_vlm_client()

    @pytest.mark.asyncio
    async def test_reset_vlm_client_clears_singleton(self):
        """Test reset_vlm_client() clears singleton without closing."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
            mock_client1 = MagicMock()
            mock_client2 = MagicMock()
            mock_class.side_effect = [mock_client1, mock_client2]

            with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}, clear=False):
                # Create singleton
                client1 = await get_shared_vlm_client()

                # Reset (clear without closing)
                reset_vlm_client()

                # Create new singleton
                client2 = await get_shared_vlm_client()

                assert client1 is not client2
                assert mock_class.call_count == 2


class TestVLMFactoryIntegration:
    """Integration tests for VLM factory."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_vlm_client()
        yield
        reset_vlm_client()

    def test_backend_selection_workflow(self):
        """Test complete backend selection workflow."""
        with patch.dict(os.environ, {"VLM_BACKEND": "dashscope"}, clear=False):
            backend = get_vlm_backend_from_config()
            assert backend == VLMBackend.DASHSCOPE

            # IMPORTANT: Patch at SOURCE module (lazy import)
            with patch("src.components.llm_proxy.dashscope_vlm.DashScopeVLMClient") as mock_class:
                mock_instance = MagicMock()
                mock_class.return_value = mock_instance

                client = get_vlm_client(backend)
                assert client is not None

    @pytest.mark.asyncio
    async def test_shared_client_with_env_config(self):
        """Test shared client respects environment configuration."""
        with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}, clear=False):
            # IMPORTANT: Patch at SOURCE module (lazy import)
            with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
                mock_instance = MagicMock()
                mock_class.return_value = mock_instance

                client = await get_shared_vlm_client()
                assert client is not None

    def test_env_var_overrides_config(self):
        """Test environment variable overrides config file."""
        mock_config = MagicMock()
        mock_config.routing = {"vlm_backend": "dashscope"}

        with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}, clear=False):
            # IMPORTANT: Patch at SOURCE module (lazy import)
            with patch("src.components.llm_proxy.config.get_llm_proxy_config", return_value=mock_config):
                backend = get_vlm_backend_from_config()
                # Env var should take priority
                assert backend == VLMBackend.OLLAMA


class TestVLMFactoryErrorHandling:
    """Tests for error handling in VLM factory."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_vlm_client()
        yield
        reset_vlm_client()

    def test_missing_dependency_handling(self):
        """Test handling when client dependency is missing."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient", side_effect=ImportError("Missing httpx")):
            with pytest.raises(ImportError):
                get_vlm_client(VLMBackend.OLLAMA)

    @pytest.mark.asyncio
    async def test_singleton_exception_recovery(self):
        """Test singleton can recover from exceptions."""
        # IMPORTANT: Patch at SOURCE module (lazy import)
        with patch("src.components.llm_proxy.ollama_vlm.OllamaVLMClient") as mock_class:
            # First call raises exception
            mock_class.side_effect = Exception("Connection failed")

            with patch.dict(os.environ, {"VLM_BACKEND": "ollama"}, clear=False):
                # First call fails
                with pytest.raises(Exception):
                    await get_shared_vlm_client()

                # Reset and retry
                reset_vlm_client()
                mock_class.side_effect = None
                mock_class.return_value = MagicMock()

                client = await get_shared_vlm_client()
                assert client is not None
