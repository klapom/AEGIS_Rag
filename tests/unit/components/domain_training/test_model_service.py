"""Unit tests for ModelService.

Sprint 117 Feature 117.12: Per-domain LLM model selection

This module tests the ModelService which provides:
- Ollama model discovery
- Model categorization by size and capabilities
- Model recommendations for training vs extraction
- Model availability validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.components.domain_training.model_service import (
    ModelService,
    ModelInfo,
    get_model_service,
    SMALL_MODEL_THRESHOLD_GB,
    MEDIUM_MODEL_THRESHOLD_GB,
)
from src.core.exceptions import ExternalServiceError


# --- Test Fixtures ---


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama /api/tags response with sample models."""
    return {
        "models": [
            {
                "name": "nemotron3:latest",
                "model": "nemotron3:latest",
                "size": 5059903488,  # ~4.7 GB
                "digest": "sha256:abc123",
                "details": {
                    "format": "gguf",
                    "family": "nemotron",
                    "parameter_size": "8B",
                },
            },
            {
                "name": "qwen3:32b",
                "model": "qwen3:32b",
                "size": 19873891328,  # ~18.5 GB
                "digest": "sha256:def456",
                "details": {
                    "format": "gguf",
                    "family": "qwen",
                    "parameter_size": "32B",
                },
            },
            {
                "name": "llama3.2:3b",
                "model": "llama3.2:3b",
                "size": 3221225472,  # ~3.0 GB
                "digest": "sha256:ghi789",
                "details": {
                    "format": "gguf",
                    "family": "llama",
                    "parameter_size": "3B",
                },
            },
        ]
    }


@pytest.fixture
def model_service():
    """Create ModelService instance for testing."""
    return ModelService(ollama_base_url="http://localhost:11434")


# --- Model Parsing Tests ---


def test_parse_ollama_model_small(model_service):
    """Test parsing a small model (<5GB)."""
    raw_model = {
        "name": "llama3.2:3b",
        "size": 3221225472,  # 3.0 GB
        "details": {
            "parameter_size": "3B",
        },
    }

    model_info = model_service._parse_ollama_model(raw_model)

    assert model_info is not None
    assert model_info.id == "llama3.2:3b"
    assert model_info.name == "Llama3.2 3B"
    assert abs(model_info.size_gb - 3.0) < 0.1
    assert model_info.speed == "fast"
    assert model_info.quality == "good"
    assert "extraction" in model_info.recommended_for
    assert "classification" in model_info.recommended_for


def test_parse_ollama_model_large(model_service):
    """Test parsing a large model (>15GB)."""
    raw_model = {
        "name": "qwen3:32b",
        "size": 19873891328,  # 18.5 GB
        "details": {
            "parameter_size": "32B",
        },
    }

    model_info = model_service._parse_ollama_model(raw_model)

    assert model_info is not None
    assert model_info.id == "qwen3:32b"
    assert model_info.name == "Qwen3 32B"
    assert abs(model_info.size_gb - 18.5) < 0.5
    assert model_info.speed == "slow"
    assert model_info.quality == "excellent"
    assert "training" in model_info.recommended_for


def test_parse_ollama_model_with_latest_suffix(model_service):
    """Test parsing a model with :latest suffix."""
    raw_model = {
        "name": "nemotron3:latest",
        "size": 5059903488,  # 4.7 GB
        "details": {
            "parameter_size": "8B",
        },
    }

    model_info = model_service._parse_ollama_model(raw_model)

    assert model_info is not None
    assert model_info.id == "nemotron3"
    assert model_info.name == "Nemotron3 8B"


def test_parse_ollama_model_invalid_data(model_service):
    """Test parsing invalid model data handles gracefully."""
    raw_model = {}

    model_info = model_service._parse_ollama_model(raw_model)

    # Should handle gracefully - may return model with defaults or None
    # Either behavior is acceptable as long as it doesn't crash
    if model_info is not None:
        assert isinstance(model_info, ModelInfo)
        assert model_info.id == ""  # Empty name
        assert model_info.size_gb == 0.0  # Empty size


# --- Model Discovery Tests ---


@pytest.mark.asyncio
async def test_get_available_models_success(model_service, mock_ollama_response):
    """Test successful model discovery from Ollama."""
    with patch("httpx.AsyncClient") as mock_client:
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ollama_response

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        models = await model_service.get_available_models()

        assert len(models) == 3
        assert all(isinstance(m, ModelInfo) for m in models)

        # Check small model
        small_models = [m for m in models if m.size_gb < SMALL_MODEL_THRESHOLD_GB]
        assert len(small_models) == 2
        assert all(m.speed == "fast" for m in small_models)

        # Check large model
        large_models = [m for m in models if m.size_gb >= MEDIUM_MODEL_THRESHOLD_GB]
        assert len(large_models) == 1
        assert large_models[0].speed == "slow"
        assert large_models[0].quality == "excellent"


@pytest.mark.asyncio
async def test_get_available_models_ollama_down(model_service):
    """Test model discovery when Ollama is unreachable."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(ExternalServiceError) as exc_info:
            await model_service.get_available_models()

        assert "Ollama" in str(exc_info.value)
        assert "Failed to connect" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_available_models_http_error(model_service):
    """Test model discovery when Ollama returns HTTP error."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(ExternalServiceError) as exc_info:
            await model_service.get_available_models()

        assert "Ollama" in str(exc_info.value)
        assert "500" in str(exc_info.value)


# --- Model Recommendations Tests ---


def test_get_model_recommendations_with_varied_models(model_service):
    """Test recommendations with small, medium, and large models."""
    models = [
        ModelInfo(
            id="llama3.2:3b",
            name="Llama3.2 3B",
            size_gb=3.0,
            recommended_for=["extraction", "classification"],
            speed="fast",
            quality="good",
        ),
        ModelInfo(
            id="nemotron3",
            name="Nemotron3 8B",
            size_gb=4.7,
            recommended_for=["extraction", "classification"],
            speed="fast",
            quality="good",
        ),
        ModelInfo(
            id="qwen3:32b",
            name="Qwen3 32B",
            size_gb=18.5,
            recommended_for=["training"],
            speed="slow",
            quality="excellent",
        ),
    ]

    recommendations = model_service.get_model_recommendations(models)

    assert recommendations["training"] == "qwen3:32b"
    assert recommendations["extraction"] == "llama3.2:3b"  # Smallest extraction model
    assert recommendations["classification"] == "llama3.2:3b"


def test_get_model_recommendations_no_training_model(model_service):
    """Test recommendations when no training-specific model exists."""
    models = [
        ModelInfo(
            id="nemotron3",
            name="Nemotron3 8B",
            size_gb=4.7,
            recommended_for=["extraction", "classification"],
            speed="fast",
            quality="good",
        ),
    ]

    recommendations = model_service.get_model_recommendations(models)

    # Fallback to largest available model
    assert recommendations["training"] == "nemotron3"
    assert recommendations["extraction"] == "nemotron3"


def test_get_model_recommendations_empty_list(model_service):
    """Test recommendations with empty model list."""
    recommendations = model_service.get_model_recommendations([])

    assert recommendations == {}


# --- Model Validation Tests ---


@pytest.mark.asyncio
async def test_validate_model_available_success(model_service, mock_ollama_response):
    """Test validating a model that exists."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ollama_response

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        is_available = await model_service.validate_model_available("nemotron3")

        assert is_available is True


@pytest.mark.asyncio
async def test_validate_model_available_with_latest_suffix(model_service, mock_ollama_response):
    """Test validating a model with :latest suffix."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ollama_response

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        is_available = await model_service.validate_model_available("nemotron3:latest")

        assert is_available is True


@pytest.mark.asyncio
async def test_validate_model_not_available(model_service, mock_ollama_response):
    """Test validating a model that doesn't exist."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ollama_response

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        is_available = await model_service.validate_model_available("nonexistent:7b")

        assert is_available is False


@pytest.mark.asyncio
async def test_validate_model_ollama_down_fails_open(model_service):
    """Test validation fails open when Ollama is down."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        # Should fail open (return True) when Ollama is unreachable
        is_available = await model_service.validate_model_available("nemotron3")

        assert is_available is True


# --- Singleton Tests ---


def test_get_model_service_singleton():
    """Test that get_model_service returns singleton instance."""
    service1 = get_model_service()
    service2 = get_model_service()

    assert service1 is service2


# --- ModelInfo Tests ---


def test_model_info_to_dict():
    """Test ModelInfo.to_dict() serialization."""
    model = ModelInfo(
        id="nemotron3",
        name="Nemotron3 8B",
        size_gb=4.712,
        provider="ollama",
        recommended_for=["extraction", "classification"],
        speed="fast",
        quality="good",
        available=True,
    )

    model_dict = model.to_dict()

    assert model_dict["id"] == "nemotron3"
    assert model_dict["name"] == "Nemotron3 8B"
    assert model_dict["size_gb"] == 4.71  # Rounded to 2 decimals
    assert model_dict["provider"] == "ollama"
    assert model_dict["recommended_for"] == ["extraction", "classification"]
    assert model_dict["speed"] == "fast"
    assert model_dict["quality"] == "good"
    assert model_dict["available"] is True


# --- Model Categorization Tests ---


def test_categorize_model_small(model_service):
    """Test categorization of small model."""
    speed, quality, recommended_for = model_service._categorize_model(3.0, "llama3.2:3b")

    assert speed == "fast"
    assert quality == "good"
    assert "extraction" in recommended_for
    assert "classification" in recommended_for


def test_categorize_model_medium(model_service):
    """Test categorization of medium model."""
    speed, quality, recommended_for = model_service._categorize_model(7.5, "mistral:7b")

    assert speed == "medium"
    assert quality == "good"
    assert "extraction" in recommended_for
    assert "classification" in recommended_for


def test_categorize_model_large(model_service):
    """Test categorization of large model."""
    speed, quality, recommended_for = model_service._categorize_model(18.5, "qwen3:32b")

    assert speed == "slow"
    assert quality == "excellent"
    assert "training" in recommended_for
