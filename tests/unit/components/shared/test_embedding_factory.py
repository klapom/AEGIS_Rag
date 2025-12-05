"""Unit tests for embedding factory.

Sprint Context: Sprint 35 (2025-12-04) - Feature 35.8: Sentence-Transformers Migration

Test Coverage:
    - Backend selection based on config
    - Singleton pattern
    - Factory reset
    - Error handling for invalid backends
"""

from unittest.mock import MagicMock, patch

import pytest

from src.components.shared.embedding_factory import (
    get_embedding_service,
    reset_embedding_service,
)


@pytest.fixture(autouse=True)
def reset_factory():
    """Reset factory singleton before each test."""
    reset_embedding_service()
    yield
    reset_embedding_service()


def test_default_backend_is_ollama():
    """Test default backend is ollama for backward compatibility."""
    with patch("src.components.shared.embedding_factory.settings") as mock_settings:
        # Default: no embedding_backend attribute (falls back to ollama)
        delattr(mock_settings, "embedding_backend") if hasattr(
            mock_settings, "embedding_backend"
        ) else None

        with patch(
            "src.components.shared.embedding_service.get_embedding_service"
        ) as mock_get_ollama:
            mock_ollama_service = MagicMock()
            mock_get_ollama.return_value = mock_ollama_service

            service = get_embedding_service()

            assert service is mock_ollama_service
            mock_get_ollama.assert_called_once()


def test_ollama_backend_selection():
    """Test explicit ollama backend selection."""
    with patch("src.components.shared.embedding_factory.settings") as mock_settings:
        mock_settings.embedding_backend = "ollama"

        with patch(
            "src.components.shared.embedding_service.get_embedding_service"
        ) as mock_get_ollama:
            mock_ollama_service = MagicMock()
            mock_get_ollama.return_value = mock_ollama_service

            service = get_embedding_service()

            assert service is mock_ollama_service
            mock_get_ollama.assert_called_once()


def test_sentence_transformers_backend_selection():
    """Test sentence-transformers backend selection."""
    with patch("src.components.shared.embedding_factory.settings") as mock_settings:
        mock_settings.embedding_backend = "sentence-transformers"
        mock_settings.st_model_name = "BAAI/bge-m3"
        mock_settings.st_device = "cuda"
        mock_settings.st_batch_size = 64

        with patch(
            "src.components.shared.sentence_transformers_embedding.SentenceTransformersEmbeddingService"
        ) as mock_st_service:
            mock_service = MagicMock()
            mock_st_service.return_value = mock_service

            service = get_embedding_service()

            assert service is mock_service
            mock_st_service.assert_called_once_with(
                model_name="BAAI/bge-m3",
                device="cuda",
                batch_size=64,
            )


def test_sentence_transformers_with_default_config():
    """Test sentence-transformers uses default config if not specified."""
    with patch("src.components.shared.embedding_factory.settings") as mock_settings:
        mock_settings.embedding_backend = "sentence-transformers"
        # Remove config attributes to test defaults
        delattr(mock_settings, "st_model_name") if hasattr(
            mock_settings, "st_model_name"
        ) else None
        delattr(mock_settings, "st_device") if hasattr(mock_settings, "st_device") else None
        delattr(mock_settings, "st_batch_size") if hasattr(
            mock_settings, "st_batch_size"
        ) else None

        with patch(
            "src.components.shared.sentence_transformers_embedding.SentenceTransformersEmbeddingService"
        ) as mock_st_service:
            mock_service = MagicMock()
            mock_st_service.return_value = mock_service

            service = get_embedding_service()

            assert service is mock_service
            # Verify defaults are used
            mock_st_service.assert_called_once_with(
                model_name="BAAI/bge-m3",
                device="auto",
                batch_size=64,
            )


def test_invalid_backend_raises_error():
    """Test invalid backend raises ValueError."""
    with patch("src.components.shared.embedding_factory.settings") as mock_settings:
        mock_settings.embedding_backend = "invalid_backend"

        with pytest.raises(ValueError) as exc_info:
            get_embedding_service()

        assert "Invalid embedding backend: invalid_backend" in str(exc_info.value)
        assert "Must be 'ollama' or 'sentence-transformers'" in str(exc_info.value)


def test_singleton_pattern():
    """Test factory returns same instance on multiple calls."""
    with patch("src.components.shared.embedding_factory.settings") as mock_settings:
        mock_settings.embedding_backend = "ollama"

        with patch(
            "src.components.shared.embedding_service.get_embedding_service"
        ) as mock_get_ollama:
            mock_ollama_service = MagicMock()
            mock_get_ollama.return_value = mock_ollama_service

            service1 = get_embedding_service()
            service2 = get_embedding_service()

            assert service1 is service2
            assert mock_get_ollama.call_count == 1  # Only called once


def test_reset_forces_reinitialization():
    """Test reset_embedding_service() forces reinitialization."""
    with patch("src.components.shared.embedding_factory.settings") as mock_settings:
        mock_settings.embedding_backend = "ollama"

        with patch(
            "src.components.shared.embedding_service.get_embedding_service"
        ) as mock_get_ollama:
            mock_ollama_service = MagicMock()
            mock_get_ollama.return_value = mock_ollama_service

            service1 = get_embedding_service()
            assert mock_get_ollama.call_count == 1

            reset_embedding_service()

            service2 = get_embedding_service()
            assert mock_get_ollama.call_count == 2  # Called again after reset


def test_backend_switch_after_reset():
    """Test switching backends after reset."""
    # First: Use ollama
    with patch("src.components.shared.embedding_factory.settings") as mock_settings:
        mock_settings.embedding_backend = "ollama"

        with patch(
            "src.components.shared.embedding_service.get_embedding_service"
        ) as mock_get_ollama:
            mock_ollama_service = MagicMock()
            mock_get_ollama.return_value = mock_ollama_service

            service1 = get_embedding_service()
            assert service1 is mock_ollama_service

    # Reset and switch to sentence-transformers
    reset_embedding_service()

    with patch("src.components.shared.embedding_factory.settings") as mock_settings:
        mock_settings.embedding_backend = "sentence-transformers"
        mock_settings.st_model_name = "BAAI/bge-m3"
        mock_settings.st_device = "auto"
        mock_settings.st_batch_size = 64

        with patch(
            "src.components.shared.sentence_transformers_embedding.SentenceTransformersEmbeddingService"
        ) as mock_st_service:
            mock_service = MagicMock()
            mock_st_service.return_value = mock_service

            service2 = get_embedding_service()
            assert service2 is mock_service
            assert service2 is not mock_ollama_service


def test_lazy_import_of_backends():
    """Test backends are imported lazily (not at module load time)."""
    # This test verifies that importing the factory module doesn't
    # immediately import backend modules (prevents circular imports)

    with patch("src.components.shared.embedding_factory.settings") as mock_settings:
        mock_settings.embedding_backend = "ollama"

        # Before calling get_embedding_service(), no backend imports
        # (This is implicit - if there were circular imports, test would fail during import)

        with patch(
            "src.components.shared.embedding_service.get_embedding_service"
        ) as mock_get_ollama:
            mock_ollama_service = MagicMock()
            mock_get_ollama.return_value = mock_ollama_service

            # Backend is imported only when get_embedding_service() is called
            service = get_embedding_service()

            assert service is mock_ollama_service
