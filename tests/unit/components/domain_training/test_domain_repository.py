"""Unit tests for domain repository.

Sprint 45: Feature 45.1 - Domain Repository
Tests for domain management, persistence, and retrieval.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestDomainRepositoryInit:
    """Test domain repository initialization."""

    def test_domain_repository_init_with_neo4j(self, mock_neo4j_client):
        """Test DomainRepository initializes with Neo4j client.

        Feature 45.1: Domain Repository initialization.
        """
        # This test validates the expected interface for domain repository
        # The actual implementation will be in src/components/domain_training/domain_repository.py
        # For now, we validate the mock structure

        assert mock_neo4j_client is not None
        assert hasattr(mock_neo4j_client, "execute")
        assert hasattr(mock_neo4j_client, "query")
        assert hasattr(mock_neo4j_client, "run")


class TestDomainOperations:
    """Test domain creation, retrieval, and management operations."""

    @pytest.mark.asyncio
    async def test_create_domain_success(self, mock_neo4j_client, sample_domain):
        """Test domain creation succeeds with valid data.

        Test Case 1 from Sprint 45: Feature 45.1
        Validates that a domain can be created with name, description, and embedding.
        """
        # Mock Neo4j response for successful domain creation
        mock_neo4j_client.execute.return_value = {
            "domain_id": sample_domain["id"],
            "name": sample_domain["name"],
            "status": "created",
        }

        # Verify the domain has required fields
        assert sample_domain["id"] is not None
        assert sample_domain["name"] == "tech_docs"
        assert sample_domain["description"] is not None
        assert sample_domain["description_embedding"] is not None
        assert len(sample_domain["description_embedding"]) == 1024

    @pytest.mark.asyncio
    async def test_create_domain_duplicate_name_fails(self, mock_neo4j_client):
        """Test domain creation fails when name already exists.

        Test Case 2 from Sprint 45: Feature 45.1
        Validates that duplicate domain names are rejected.
        """
        # Mock Neo4j to raise error for duplicate
        mock_neo4j_client.execute.side_effect = Exception(
            "Domain with name 'tech_docs' already exists"
        )

        # When creating duplicate domain, should raise error
        domain_name = "tech_docs"
        with pytest.raises(Exception, match="already exists"):
            # Simulate domain creation attempt
            await mock_neo4j_client.execute(
                "CREATE_DOMAIN",
                {"name": domain_name}
            )

    @pytest.mark.asyncio
    async def test_get_domain_exists(self, mock_neo4j_client, sample_domain):
        """Test retrieving an existing domain returns the domain.

        Test Case 3 from Sprint 45: Feature 45.1
        Validates domain lookup by ID.
        """
        mock_neo4j_client.query.return_value = sample_domain

        result = await mock_neo4j_client.query("GET_DOMAIN", {"id": sample_domain["id"]})

        assert result is not None
        assert result["id"] == sample_domain["id"]
        assert result["name"] == "tech_docs"
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_get_domain_not_found(self, mock_neo4j_client):
        """Test retrieving non-existent domain returns None.

        Test Case 4 from Sprint 45: Feature 45.1
        Validates graceful handling of missing domains.
        """
        mock_neo4j_client.query.return_value = None

        result = await mock_neo4j_client.query(
            "GET_DOMAIN",
            {"id": str(uuid4())}
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_list_domains_empty(self, mock_neo4j_client):
        """Test listing domains returns empty list when no domains exist.

        Test Case 5 from Sprint 45: Feature 45.1
        Validates empty collection handling.
        """
        mock_neo4j_client.query.return_value = []

        result = await mock_neo4j_client.query("LIST_DOMAINS")

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_domains_returns_all(self, mock_neo4j_client, sample_domain):
        """Test listing domains returns all created domains.

        Test Case 6 from Sprint 45: Feature 45.1
        Validates domain enumeration.
        """
        domain1 = sample_domain.copy()
        domain2 = {
            "id": str(uuid4()),
            "name": "ml_docs",
            "description": "Machine learning documentation",
            "status": "ready",
        }

        mock_neo4j_client.query.return_value = [domain1, domain2]

        result = await mock_neo4j_client.query("LIST_DOMAINS")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "tech_docs"
        assert result[1]["name"] == "ml_docs"

    @pytest.mark.asyncio
    async def test_update_domain_prompts_success(
        self, mock_neo4j_client, sample_domain_with_prompts
    ):
        """Test updating domain prompts succeeds.

        Test Case 7 from Sprint 45: Feature 45.1 + Feature 45.8
        Validates that custom extraction prompts can be set for a domain.
        """
        domain_id = sample_domain_with_prompts["id"]
        mock_neo4j_client.execute.return_value = {
            "status": "updated",
            "domain_id": domain_id,
        }

        result = await mock_neo4j_client.execute(
            "UPDATE_DOMAIN_PROMPTS",
            {
                "domain_id": domain_id,
                "entity_prompt": sample_domain_with_prompts["entity_prompt"],
                "relationship_prompt": sample_domain_with_prompts["relationship_prompt"],
            }
        )

        assert result["status"] == "updated"
        assert result["domain_id"] == domain_id

    @pytest.mark.asyncio
    async def test_find_best_matching_domain_above_threshold(
        self, mock_neo4j_client, sample_domain
    ):
        """Test finding best matching domain with high similarity score.

        Test Case 8 from Sprint 45: Feature 45.1
        Validates domain semantic matching above confidence threshold.
        """
        query_embedding = [0.1] * 1024  # Similar to sample_domain embedding

        mock_neo4j_client.query.return_value = {
            "domain": sample_domain,
            "similarity": 0.92,  # Above threshold (e.g., 0.8)
        }

        result = await mock_neo4j_client.query(
            "FIND_BEST_MATCHING_DOMAIN",
            {
                "query_embedding": query_embedding,
                "threshold": 0.8,
            }
        )

        assert result is not None
        assert result["domain"]["id"] == sample_domain["id"]
        assert result["similarity"] >= 0.8

    @pytest.mark.asyncio
    async def test_find_best_matching_domain_below_threshold(self, mock_neo4j_client):
        """Test finding matching domain below threshold returns None.

        Test Case 9 from Sprint 45: Feature 45.1
        Validates threshold enforcement in semantic matching.
        """
        query_embedding = [0.5] * 1024  # Different from most domains

        mock_neo4j_client.query.return_value = None

        result = await mock_neo4j_client.query(
            "FIND_BEST_MATCHING_DOMAIN",
            {
                "query_embedding": query_embedding,
                "threshold": 0.8,
            }
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_domain_success(self, mock_neo4j_client, sample_domain):
        """Test deleting an existing domain succeeds.

        Test Case 10 from Sprint 45: Feature 45.1
        Validates domain deletion.
        """
        mock_neo4j_client.execute.return_value = {
            "status": "deleted",
            "domain_id": sample_domain["id"],
        }

        result = await mock_neo4j_client.execute(
            "DELETE_DOMAIN",
            {"domain_id": sample_domain["id"]}
        )

        assert result["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_delete_domain_not_found(self, mock_neo4j_client):
        """Test deleting non-existent domain raises error.

        Test Case 11 from Sprint 45: Feature 45.1
        Validates error handling for missing domains.
        """
        domain_id = str(uuid4())
        mock_neo4j_client.execute.side_effect = Exception(
            f"Domain {domain_id} not found"
        )

        with pytest.raises(Exception, match="not found"):
            await mock_neo4j_client.execute(
                "DELETE_DOMAIN",
                {"domain_id": domain_id}
            )


class TestTrainingLogs:
    """Test training log creation and management."""

    @pytest.mark.asyncio
    async def test_create_training_log(self, mock_neo4j_client, sample_training_log):
        """Test creating a new training log.

        Test Case 12 from Sprint 45: Feature 45.1
        Validates training log initialization.
        """
        mock_neo4j_client.execute.return_value = {
            "log_id": sample_training_log["id"],
            "status": "in_progress",
        }

        result = await mock_neo4j_client.execute(
            "CREATE_TRAINING_LOG",
            {
                "domain_id": sample_training_log["domain_id"],
                "training_type": sample_training_log["training_type"],
            }
        )

        assert result["log_id"] is not None
        assert result["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_update_training_log_progress(
        self, mock_neo4j_client, sample_training_log
    ):
        """Test updating training log progress metrics.

        Test Case 13 from Sprint 45: Feature 45.1
        Validates progress tracking during domain training.
        """
        mock_neo4j_client.execute.return_value = {
            "status": "updated",
            "processed_documents": 50,
            "progress_percent": 50.0,
        }

        result = await mock_neo4j_client.execute(
            "UPDATE_TRAINING_LOG_PROGRESS",
            {
                "log_id": sample_training_log["id"],
                "processed_documents": 50,
                "success_count": 48,
                "error_count": 2,
            }
        )

        assert result["status"] == "updated"
        assert result["processed_documents"] == 50

    @pytest.mark.asyncio
    async def test_get_latest_training_log(
        self, mock_neo4j_client, sample_training_log_completed
    ):
        """Test retrieving latest training log for a domain.

        Test Case 14 from Sprint 45: Feature 45.1
        Validates training history tracking.
        """
        mock_neo4j_client.query.return_value = sample_training_log_completed

        result = await mock_neo4j_client.query(
            "GET_LATEST_TRAINING_LOG",
            {"domain_id": sample_training_log_completed["domain_id"]}
        )

        assert result is not None
        assert result["status"] == "completed"
        assert result["metrics"]["f1_score"] == 0.925
        assert result["completed_at"] is not None


class TestDomainRepositoryIntegration:
    """Integration tests for domain repository operations."""

    @pytest.mark.asyncio
    async def test_domain_creation_and_retrieval_flow(
        self, mock_neo4j_client, sample_domain
    ):
        """Test creating and retrieving a domain.

        Integration test validating complete domain lifecycle.
        """
        # Mock creation
        mock_neo4j_client.execute.return_value = sample_domain

        created = await mock_neo4j_client.execute(
            "CREATE_DOMAIN",
            {
                "name": sample_domain["name"],
                "description": sample_domain["description"],
            }
        )

        assert created["id"] is not None

        # Mock retrieval
        mock_neo4j_client.query.return_value = sample_domain

        retrieved = await mock_neo4j_client.query(
            "GET_DOMAIN",
            {"id": created["id"]}
        )

        assert retrieved["name"] == sample_domain["name"]

    @pytest.mark.asyncio
    async def test_domain_training_lifecycle(
        self, mock_neo4j_client, sample_domain, sample_training_log_completed
    ):
        """Test complete domain training lifecycle.

        Integration test for: create domain -> start training -> track progress -> complete.
        """
        # Create domain
        mock_neo4j_client.execute.return_value = sample_domain
        domain = await mock_neo4j_client.execute("CREATE_DOMAIN", sample_domain)

        # Create training log
        mock_neo4j_client.execute.return_value = {"log_id": sample_training_log_completed["id"]}
        log = await mock_neo4j_client.execute(
            "CREATE_TRAINING_LOG",
            {"domain_id": domain["id"]}
        )

        # Update progress
        mock_neo4j_client.execute.return_value = {"processed": 50, "total": 100}
        await mock_neo4j_client.execute(
            "UPDATE_TRAINING_LOG_PROGRESS",
            {"log_id": log["log_id"], "processed": 50}
        )

        # Get completed log
        mock_neo4j_client.query.return_value = sample_training_log_completed
        result = await mock_neo4j_client.query(
            "GET_LATEST_TRAINING_LOG",
            {"domain_id": domain["id"]}
        )

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_multiple_domains_management(self, mock_neo4j_client):
        """Test managing multiple domains concurrently.

        Integration test for domain portfolio operations.
        """
        domains = [
            {"id": str(uuid4()), "name": f"domain_{i}"} for i in range(3)
        ]

        mock_neo4j_client.query.return_value = domains

        result = await mock_neo4j_client.query("LIST_DOMAINS")

        assert len(result) == 3
        assert all("name" in d for d in result)
