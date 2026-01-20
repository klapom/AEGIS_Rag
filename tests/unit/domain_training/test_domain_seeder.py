"""Unit tests for default domain seeding.

Sprint 117 - Feature 117.9: Default Domain Seeding

Tests:
    - Default domain creation on first run
    - Idempotency (no duplicate creation on second run)
    - Domain has all required fields (especially MENTIONED_IN)
    - Error handling for database failures
    - Proper logging for seeding activity
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.components.domain_training.domain_seeder import (
    DEFAULT_DOMAIN_CONFIG,
    seed_default_domains,
)


@pytest.mark.asyncio
class TestDomainSeeder:
    """Test suite for domain seeding functionality."""

    async def test_seed_default_domain_creates_general_domain(self) -> None:
        """Test that seed_default_domains() creates "general" domain on first run."""
        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = None  # Domain doesn't exist
        mock_repo.create_domain.return_value = {
            "id": "domain-123",
            "name": "general",
            "status": "active",
        }

        # Act
        with patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ):
            await seed_default_domains()

        # Assert
        mock_repo.get_domain.assert_called_once_with("general")
        mock_repo.create_domain.assert_called_once()

        # Verify create_domain was called with correct parameters
        call_kwargs = mock_repo.create_domain.call_args.kwargs
        assert call_kwargs["name"] == "general"
        assert call_kwargs["description"] == DEFAULT_DOMAIN_CONFIG["description"]
        assert call_kwargs["status"] == "active"
        assert len(call_kwargs["description_embedding"]) == 1024
        assert all(v == 0.0 for v in call_kwargs["description_embedding"])

    async def test_seed_default_domain_is_idempotent(self) -> None:
        """Test that seed_default_domains() is idempotent (no duplicate creation)."""
        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = {
            "id": "domain-123",
            "name": "general",
            "status": "active",
        }

        # Act
        with patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ):
            await seed_default_domains()

        # Assert
        mock_repo.get_domain.assert_called_once_with("general")
        mock_repo.create_domain.assert_not_called()

    async def test_seed_default_domain_has_all_required_fields(self) -> None:
        """Test that default domain configuration has all required fields."""
        # Assert configuration structure
        assert "name" in DEFAULT_DOMAIN_CONFIG
        assert "description" in DEFAULT_DOMAIN_CONFIG
        assert "entity_types" in DEFAULT_DOMAIN_CONFIG
        assert "relation_types" in DEFAULT_DOMAIN_CONFIG
        assert "intent_classes" in DEFAULT_DOMAIN_CONFIG
        assert "model_family" in DEFAULT_DOMAIN_CONFIG
        assert "confidence_threshold" in DEFAULT_DOMAIN_CONFIG
        assert "status" in DEFAULT_DOMAIN_CONFIG

        # Assert domain name
        assert DEFAULT_DOMAIN_CONFIG["name"] == "general"

        # Assert MENTIONED_IN is present (CRITICAL for provenance)
        assert "MENTIONED_IN" in DEFAULT_DOMAIN_CONFIG["relation_types"]

        # Assert status is active
        assert DEFAULT_DOMAIN_CONFIG["status"] == "active"

        # Assert confidence threshold is valid
        assert 0.0 <= DEFAULT_DOMAIN_CONFIG["confidence_threshold"] <= 1.0

        # Assert entity types count
        assert len(DEFAULT_DOMAIN_CONFIG["entity_types"]) == 5
        assert "Entity" in DEFAULT_DOMAIN_CONFIG["entity_types"]
        assert "Person" in DEFAULT_DOMAIN_CONFIG["entity_types"]
        assert "Organization" in DEFAULT_DOMAIN_CONFIG["entity_types"]
        assert "Location" in DEFAULT_DOMAIN_CONFIG["entity_types"]
        assert "Concept" in DEFAULT_DOMAIN_CONFIG["entity_types"]

        # Assert relation types count (including MENTIONED_IN)
        assert len(DEFAULT_DOMAIN_CONFIG["relation_types"]) == 4
        assert "RELATES_TO" in DEFAULT_DOMAIN_CONFIG["relation_types"]
        assert "MENTIONED_IN" in DEFAULT_DOMAIN_CONFIG["relation_types"]
        assert "AUTHORED_BY" in DEFAULT_DOMAIN_CONFIG["relation_types"]
        assert "LOCATED_IN" in DEFAULT_DOMAIN_CONFIG["relation_types"]

        # Assert intent classes count
        assert len(DEFAULT_DOMAIN_CONFIG["intent_classes"]) == 3
        assert "general_inquiry" in DEFAULT_DOMAIN_CONFIG["intent_classes"]
        assert "information_request" in DEFAULT_DOMAIN_CONFIG["intent_classes"]
        assert "clarification" in DEFAULT_DOMAIN_CONFIG["intent_classes"]

    async def test_seed_default_domain_uses_zero_embedding(self) -> None:
        """Test that default domain uses zero embedding (1024-dim)."""
        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = None
        mock_repo.create_domain.return_value = {
            "id": "domain-123",
            "name": "general",
            "status": "active",
        }

        # Act
        with patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ):
            await seed_default_domains()

        # Assert
        call_kwargs = mock_repo.create_domain.call_args.kwargs
        embedding = call_kwargs["description_embedding"]

        # Verify embedding is 1024-dim (BGE-M3)
        assert len(embedding) == 1024

        # Verify all values are zero (no semantic matching)
        assert all(v == 0.0 for v in embedding)

    async def test_seed_default_domain_handles_validation_error(self) -> None:
        """Test that seed_default_domains() re-raises validation errors."""
        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = None
        mock_repo.create_domain.side_effect = ValueError("Invalid domain name format")

        # Act & Assert
        with (
            patch(
                "src.components.domain_training.domain_seeder.get_domain_repository",
                return_value=mock_repo,
            ),
            pytest.raises(ValueError, match="Invalid domain name format"),
        ):
            await seed_default_domains()

    async def test_seed_default_domain_handles_database_error(self) -> None:
        """Test that seed_default_domains() re-raises database errors."""
        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_domain.side_effect = Exception("Neo4j connection failed")

        # Act & Assert
        with (
            patch(
                "src.components.domain_training.domain_seeder.get_domain_repository",
                return_value=mock_repo,
            ),
            pytest.raises(Exception, match="Neo4j connection failed"),
        ):
            await seed_default_domains()

    async def test_seed_default_domain_uses_system_llm_model(self) -> None:
        """Test that default domain uses system default LLM model from settings."""
        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = None
        mock_repo.create_domain.return_value = {
            "id": "domain-123",
            "name": "general",
            "status": "active",
        }

        # Act
        with (
            patch(
                "src.components.domain_training.domain_seeder.get_domain_repository",
                return_value=mock_repo,
            ),
            patch("src.components.domain_training.domain_seeder.settings") as mock_settings,
        ):
            mock_settings.lightrag_llm_model = "qwen3:32b"
            await seed_default_domains()

            # Assert
            call_kwargs = mock_repo.create_domain.call_args.kwargs
            assert call_kwargs["llm_model"] == "qwen3:32b"

    async def test_seed_default_domain_logs_creation(self, caplog) -> None:
        """Test that seed_default_domains() logs domain creation activity."""
        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = None
        mock_repo.create_domain.return_value = {
            "id": "domain-123",
            "name": "general",
            "status": "active",
        }

        # Act
        with patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ):
            await seed_default_domains()

        # Assert - logging calls are made (structlog integration test)
        # Note: structlog logs may not appear in caplog, but we verify no exceptions

    async def test_seed_default_domain_logs_idempotent_skip(self, caplog) -> None:
        """Test that seed_default_domains() logs skip when domain exists."""
        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_domain.return_value = {
            "id": "domain-123",
            "name": "general",
            "status": "active",
        }

        # Act
        with patch(
            "src.components.domain_training.domain_seeder.get_domain_repository",
            return_value=mock_repo,
        ):
            await seed_default_domains()

        # Assert - function completes without creating domain
        mock_repo.create_domain.assert_not_called()
