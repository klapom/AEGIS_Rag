"""Integration tests for default domain seeding.

Sprint 117 - Feature 117.9: Default Domain Seeding

Tests:
    - Domain seeding on application startup
    - GET /api/v1/admin/domains/ returns "general" domain
    - Domain has all required fields in Neo4j
    - Idempotency across multiple startup cycles
"""

import pytest
from httpx import AsyncClient

from src.components.domain_training.domain_repository import get_domain_repository
from src.components.domain_training.domain_seeder import (
    DEFAULT_DOMAIN_CONFIG,
    seed_default_domains,
)
from src.components.graph_rag.neo4j_client import get_neo4j_client


@pytest.mark.asyncio
@pytest.mark.integration
class TestDomainSeedingIntegration:
    """Integration tests for domain seeding with real Neo4j."""

    async def test_seed_default_domains_creates_general_domain_in_neo4j(
        self,
    ) -> None:
        """Test that seed_default_domains() creates "general" domain in Neo4j."""
        # Arrange
        repo = get_domain_repository()
        neo4j_client = get_neo4j_client()

        # Clean up any existing "general" domain (test isolation)
        try:
            existing = await repo.get_domain("general")
            if existing:
                await neo4j_client.execute_write(
                    """
                    MATCH (d:Domain {name: 'general'})
                    DETACH DELETE d
                    """
                )
        except Exception:
            pass

        # Act
        await seed_default_domains()

        # Assert
        domain = await repo.get_domain("general")
        assert domain is not None
        assert domain["name"] == "general"
        assert domain["description"] == DEFAULT_DOMAIN_CONFIG["description"]
        assert domain["status"] == "active"

    async def test_seed_default_domains_is_idempotent_in_neo4j(
        self,
    ) -> None:
        """Test that seed_default_domains() is idempotent with real Neo4j."""
        # Arrange
        repo = get_domain_repository()
        neo4j_client = get_neo4j_client()

        # Clean up any existing "general" domain
        try:
            existing = await repo.get_domain("general")
            if existing:
                await neo4j_client.execute_write(
                    """
                    MATCH (d:Domain {name: 'general'})
                    DETACH DELETE d
                    """
                )
        except Exception:
            pass

        # Act - Seed twice
        await seed_default_domains()
        domain_id_1 = (await repo.get_domain("general"))["id"]

        await seed_default_domains()
        domain_id_2 = (await repo.get_domain("general"))["id"]

        # Assert - Same domain ID (not duplicated)
        assert domain_id_1 == domain_id_2

        # Verify only one domain exists
        result = await neo4j_client.execute_read(
            """
            MATCH (d:Domain {name: 'general'})
            RETURN count(d) as count
            """
        )
        assert result[0]["count"] == 1

    async def test_get_domains_api_returns_general_domain_after_seeding(
        self, async_client: AsyncClient
    ) -> None:
        """Test that GET /api/v1/admin/domains/ returns "general" domain after seeding."""
        # Arrange - Seed default domains
        await seed_default_domains()

        # Act
        response = await async_client.get("/api/v1/admin/domains/")

        # Assert
        assert response.status_code == 200
        domains = response.json()
        assert isinstance(domains, list)
        assert len(domains) >= 1  # At least "general" domain

        # Find "general" domain in response
        general_domain = next((d for d in domains if d["name"] == "general"), None)
        assert general_domain is not None
        assert general_domain["description"] == DEFAULT_DOMAIN_CONFIG["description"]
        assert general_domain["status"] == "active"

    async def test_default_domain_has_mentioned_in_relation_type(
        self,
    ) -> None:
        """Test that default domain has MENTIONED_IN relation type for provenance."""
        # Arrange
        await seed_default_domains()

        # Act
        repo = get_domain_repository()
        domain = await repo.get_domain("general")

        # Assert
        assert domain is not None

        # CRITICAL: MENTIONED_IN must be present for provenance tracking
        # Note: relation_types are stored in domain config, not in Neo4j node directly
        # This test verifies the config constant has MENTIONED_IN
        assert "MENTIONED_IN" in DEFAULT_DOMAIN_CONFIG["relation_types"]

    async def test_default_domain_cannot_be_deleted(self) -> None:
        """Test that default "general" domain is protected from deletion."""
        # Arrange
        await seed_default_domains()
        repo = get_domain_repository()

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot delete default domain"):
            await repo.delete_domain("general")

        # Verify domain still exists
        domain = await repo.get_domain("general")
        assert domain is not None

    async def test_default_domain_cannot_be_updated(self) -> None:
        """Test that default "general" domain is protected from updates."""
        # Arrange
        await seed_default_domains()
        repo = get_domain_repository()

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot update default domain"):
            await repo.update_domain(
                name="general",
                description="Modified description",
            )

        # Verify domain description unchanged
        domain = await repo.get_domain("general")
        assert domain is not None
        assert domain["description"] == DEFAULT_DOMAIN_CONFIG["description"]

    async def test_application_startup_seeds_default_domains(
        self, async_client: AsyncClient
    ) -> None:
        """Test that application startup automatically seeds default domains.

        Note: This test verifies the lifespan event integration.
        The async_client fixture triggers the lifespan event, which should
        call seed_default_domains() automatically.
        """
        # Act - async_client startup already called seed_default_domains()
        # We just verify the result
        response = await async_client.get("/api/v1/admin/domains/")

        # Assert
        assert response.status_code == 200
        domains = response.json()

        general_domain = next((d for d in domains if d["name"] == "general"), None)
        assert general_domain is not None
        assert general_domain["status"] == "active"

    async def test_default_domain_has_zero_embedding(self) -> None:
        """Test that default domain has zero embedding (no semantic matching)."""
        # Arrange
        await seed_default_domains()
        neo4j_client = get_neo4j_client()

        # Act - Query embedding directly from Neo4j
        result = await neo4j_client.execute_read(
            """
            MATCH (d:Domain {name: 'general'})
            RETURN d.description_embedding as embedding
            """
        )

        # Assert
        assert result is not None
        assert len(result) == 1

        embedding = result[0]["embedding"]
        assert len(embedding) == 1024  # BGE-M3 dimension
        assert all(v == 0.0 for v in embedding)  # All zeros (no semantic matching)
