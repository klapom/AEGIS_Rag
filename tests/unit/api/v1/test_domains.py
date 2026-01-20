"""Unit tests for Domain CRUD API.

Sprint 117 Feature 117.1: Domain CRUD API

Tests cover:
- Domain creation with validation
- Domain retrieval (single and list)
- Domain update with MENTIONED_IN auto-injection
- Domain deletion with protection for default domain
- Error handling and validation
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.v1.domain_training import create_domain, delete_domain, get_domain, update_domain
from src.core.models import DomainCreateRequest, DomainLLMConfig, DomainUpdateRequest


@pytest.fixture
def mock_domain_repository():
    """Mock domain repository for testing."""
    with patch("src.api.v1.domain_training.get_domain_repository") as mock:
        repo = MagicMock()
        mock.return_value = repo
        yield repo


@pytest.fixture
def sample_domain_data():
    """Sample domain data for testing."""
    return {
        "id": "domain_test_123",
        "name": "medical",
        "description": "Medical domain with disease and symptom extraction",
        "entity_types": ["Disease", "Symptom", "Treatment"],
        "relation_types": ["TREATS", "CAUSES", "SYMPTOM_OF", "MENTIONED_IN"],
        "intent_classes": ["inquiry", "symptom_report"],
        "model_family": "medical",
        "confidence_threshold": 0.6,
        "status": "active",
        "training_samples": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": "test_user",
        "llm_model": "nemotron3",
        "training_metrics": "{}",
        "trained_at": None,
    }


@pytest.fixture
def sample_create_request():
    """Sample domain create request."""
    return DomainCreateRequest(
        name="medical",
        description="Medical domain with disease and symptom extraction",
        entity_types=["Disease", "Symptom", "Treatment"],
        relation_types=["TREATS", "CAUSES", "SYMPTOM_OF"],
        intent_classes=["inquiry", "symptom_report"],
        model_family="medical",
        confidence_threshold=0.6,
    )


@pytest.fixture
def sample_update_request():
    """Sample domain update request."""
    return DomainUpdateRequest(
        description="Updated medical domain description",
        confidence_threshold=0.7,
    )


class TestGetDomain:
    """Tests for GET /admin/domains/{name} endpoint."""

    @pytest.mark.asyncio
    async def test_get_domain_success(self, mock_domain_repository, sample_domain_data):
        """Test successful domain retrieval."""
        mock_domain_repository.get_domain = AsyncMock(return_value=sample_domain_data)

        response = await get_domain("medical")

        assert response.id == "domain_test_123"
        assert response.name == "medical"
        assert response.status == "active"
        mock_domain_repository.get_domain.assert_called_once_with("medical")

    @pytest.mark.asyncio
    async def test_get_domain_not_found(self, mock_domain_repository):
        """Test domain not found returns 404."""
        mock_domain_repository.get_domain = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_domain("nonexistent")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


class TestUpdateDomain:
    """Tests for PUT /admin/domains/{name} endpoint."""

    @pytest.mark.asyncio
    async def test_update_domain_success(
        self, mock_domain_repository, sample_domain_data, sample_update_request
    ):
        """Test successful domain update."""
        updated_data = {**sample_domain_data, "description": "Updated medical domain description"}
        mock_domain_repository.update_domain = AsyncMock(return_value=updated_data)

        response = await update_domain("medical", sample_update_request)

        assert response["success"] is True
        assert "updated successfully" in response["message"]
        assert response["domain"]["description"] == "Updated medical domain description"

    @pytest.mark.asyncio
    async def test_update_domain_not_found(self, mock_domain_repository, sample_update_request):
        """Test updating non-existent domain returns 400."""
        mock_domain_repository.update_domain = AsyncMock(
            side_effect=ValueError("Domain 'nonexistent' not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_domain("nonexistent", sample_update_request)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_domain_mentioned_in_auto_added(
        self, mock_domain_repository, sample_domain_data
    ):
        """Test MENTIONED_IN is automatically added to relation_types."""
        update_request = DomainUpdateRequest(
            relation_types=["TREATS", "CAUSES"]  # No MENTIONED_IN
        )

        # Mock repository will receive relation_types with MENTIONED_IN
        async def mock_update(name, **kwargs):
            assert "MENTIONED_IN" in kwargs.get("relation_types", [])
            return {**sample_domain_data, "relation_types": kwargs["relation_types"]}

        mock_domain_repository.update_domain = AsyncMock(side_effect=mock_update)

        response = await update_domain("medical", update_request)

        assert response["success"] is True
        assert "MENTIONED_IN" in response["domain"]["relation_types"]

    @pytest.mark.asyncio
    async def test_update_domain_validation_error(self, mock_domain_repository):
        """Test validation error for invalid entity types."""
        update_request = DomainUpdateRequest(
            entity_types=["AB"]  # Too short (< 5 chars)
        )

        mock_domain_repository.update_domain = AsyncMock(
            side_effect=ValueError("Entity type 'AB' must be 5-50 characters, got 2")
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_domain("medical", update_request)

        assert exc_info.value.status_code == 400


class TestDeleteDomain:
    """Tests for DELETE /admin/domains/{name} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_domain_success(self, mock_domain_repository):
        """Test successful domain deletion."""
        mock_domain_repository.delete_domain = AsyncMock(return_value=True)

        response = await delete_domain("medical")

        assert response["success"] is True
        assert "deleted successfully" in response["message"]
        mock_domain_repository.delete_domain.assert_called_once_with("medical")

    @pytest.mark.asyncio
    async def test_delete_domain_not_found(self, mock_domain_repository):
        """Test deleting non-existent domain returns 404."""
        mock_domain_repository.delete_domain = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await delete_domain("nonexistent")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_default_domain_forbidden(self, mock_domain_repository):
        """Test deleting default 'general' domain is forbidden."""
        mock_domain_repository.delete_domain = AsyncMock(
            side_effect=ValueError("Cannot delete default domain: general")
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_domain("general")

        assert exc_info.value.status_code == 400


class TestDomainValidation:
    """Tests for domain validation logic."""

    def test_mentioned_in_auto_injection_create(self, sample_create_request):
        """Test MENTIONED_IN is auto-injected during domain creation."""
        # Validation happens in Pydantic model
        assert "MENTIONED_IN" in sample_create_request.relation_types

    def test_entity_type_validation_too_short(self):
        """Test entity type validation rejects names < 5 chars."""
        with pytest.raises(ValueError) as exc_info:
            DomainCreateRequest(
                name="test",
                description="Test domain",
                entity_types=["AB"],  # Too short
                relation_types=["RELATES_TO"],
            )
        assert "must be 5-50 characters" in str(exc_info.value)

    def test_entity_type_validation_too_long(self):
        """Test entity type validation rejects names > 50 chars."""
        with pytest.raises(ValueError) as exc_info:
            DomainCreateRequest(
                name="test",
                description="Test domain",
                entity_types=["A" * 51],  # Too long
                relation_types=["RELATES_TO"],
            )
        assert "must be 5-50 characters" in str(exc_info.value)

    def test_relation_type_validation_invalid_chars(self):
        """Test relation type validation rejects non-alphanumeric characters."""
        with pytest.raises(ValueError) as exc_info:
            DomainCreateRequest(
                name="test",
                description="Test domain",
                entity_types=["Entity"],
                relation_types=["RELATES-TO"],  # Hyphens not allowed in relation types
            )
        assert "alphanumeric with underscores" in str(exc_info.value)

    def test_confidence_threshold_validation_too_low(self):
        """Test confidence threshold validation rejects values < 0.0."""
        with pytest.raises(ValueError):
            DomainCreateRequest(
                name="test",
                description="Test domain",
                entity_types=["Entity"],
                relation_types=["RELATES_TO"],
                confidence_threshold=-0.1,
            )

    def test_confidence_threshold_validation_too_high(self):
        """Test confidence threshold validation rejects values > 1.0."""
        with pytest.raises(ValueError):
            DomainCreateRequest(
                name="test",
                description="Test domain",
                entity_types=["Entity"],
                relation_types=["RELATES_TO"],
                confidence_threshold=1.5,
            )

    def test_domain_name_validation_invalid_pattern(self):
        """Test domain name validation rejects invalid patterns."""
        with pytest.raises(ValueError):
            DomainCreateRequest(
                name="Medical Domain",  # Spaces not allowed
                description="Test domain",
                entity_types=["Entity"],
                relation_types=["RELATES_TO"],
            )

    def test_model_family_validation(self):
        """Test model family validation only accepts predefined values."""
        with pytest.raises(ValueError):
            DomainCreateRequest(
                name="test",
                description="Test domain",
                entity_types=["Entity"],
                relation_types=["RELATES_TO"],
                model_family="invalid_family",
            )


class TestLLMConfig:
    """Tests for domain LLM configuration."""

    def test_llm_config_defaults(self):
        """Test LLM config has correct defaults."""
        config = DomainLLMConfig()
        assert config.training_model == "qwen3:32b"
        assert config.extraction_model == "nemotron3"
        assert config.provider == "ollama"
        assert config.training_temperature == 0.7
        assert config.extraction_temperature == 0.3

    def test_llm_config_custom_values(self):
        """Test LLM config accepts custom values."""
        config = DomainLLMConfig(
            training_model="qwen3:8b",
            extraction_model="qwen3:8b",
            provider="alibaba",
            training_temperature=0.9,
        )
        assert config.training_model == "qwen3:8b"
        assert config.extraction_model == "qwen3:8b"
        assert config.provider == "alibaba"
        assert config.training_temperature == 0.9

    def test_temperature_validation_too_high(self):
        """Test temperature validation rejects values > 2.0."""
        with pytest.raises(ValueError):
            DomainLLMConfig(training_temperature=2.5)

    def test_temperature_validation_too_low(self):
        """Test temperature validation rejects values < 0.0."""
        with pytest.raises(ValueError):
            DomainLLMConfig(extraction_temperature=-0.1)
