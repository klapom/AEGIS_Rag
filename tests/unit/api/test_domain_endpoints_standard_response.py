"""Unit tests for domain endpoints with standardized response format.

Sprint 117 Feature 117.8: Response Format Standardization (3 SP)

Tests that domain endpoints return standardized ApiResponse wrapper with:
- success: true/false
- data: actual response payload
- metadata: request_id, timestamp, processing_time_ms, api_version
- pagination: (for list endpoints)
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from src.api.v1.domain_training import router
from src.core.models.response import ApiResponse


@pytest.fixture
def mock_request():
    """Create mock FastAPI Request with request tracking."""
    request = Mock(spec=Request)
    request.state.request_id = "req_test123"
    request.state.start_time = 1000.0  # Fixed timestamp for testing
    return request


@pytest.fixture
def mock_domain_repository():
    """Mock domain repository."""
    with patch("src.components.domain_training.get_domain_repository") as mock_get_repo:
        repo = AsyncMock()
        mock_get_repo.return_value = repo
        yield repo


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    with patch("src.components.vector_search.EmbeddingService") as mock_service:
        service = AsyncMock()
        service.embed_single = AsyncMock(return_value=[0.1] * 1024)
        mock_service.return_value = service
        yield service


class TestListDomainsStandardResponse:
    """Tests for list_domains endpoint with standard response."""

    @pytest.mark.asyncio
    async def test_list_domains_returns_standard_response(
        self,
        mock_request,
        mock_domain_repository,
    ):
        """Test list_domains returns standardized ApiResponse."""
        from src.api.v1.domain_training import list_domains

        # Mock repository response
        mock_domain_repository.list_domains.return_value = [
            {
                "id": "domain1",
                "name": "tech_docs",
                "description": "Technical documentation",
                "status": "ready",
                "llm_model": "qwen3:32b",
                "training_metrics": None,
                "created_at": "2026-01-20T12:00:00Z",
                "trained_at": None,
            }
        ]

        # Call endpoint
        with patch("time.time", return_value=1001.0):  # 1s elapsed
            response = await list_domains(mock_request)

        # Verify response structure
        assert isinstance(response, ApiResponse)
        assert response.success is True
        assert isinstance(response.data, list)
        assert len(response.data) == 1

        # Verify metadata
        assert response.metadata.request_id == "req_test123"
        assert response.metadata.processing_time_ms == 1000.0  # 1s = 1000ms
        assert response.metadata.api_version == "v1"
        assert response.metadata.timestamp.endswith("Z")

        # Verify data content
        domain = response.data[0]
        assert domain.name == "tech_docs"
        assert domain.status == "ready"

    @pytest.mark.asyncio
    async def test_list_domains_empty_list(
        self,
        mock_request,
        mock_domain_repository,
    ):
        """Test list_domains with empty repository."""
        from src.api.v1.domain_training import list_domains

        mock_domain_repository.list_domains.return_value = []

        response = await list_domains(mock_request)

        assert response.success is True
        assert response.data == []
        assert response.metadata.request_id == "req_test123"


class TestCreateDomainStandardResponse:
    """Tests for create_domain endpoint with standard response."""

    @pytest.mark.asyncio
    async def test_create_domain_returns_standard_response(
        self,
        mock_request,
        mock_domain_repository,
        mock_embedding_service,
    ):
        """Test create_domain returns standardized ApiResponse."""
        from src.api.v1.domain_training import DomainCreateRequest, create_domain

        # Mock repository response
        mock_domain_repository.create_domain.return_value = {
            "id": "domain_new",
            "name": "medical",
            "description": "Medical documents",
            "status": "pending",
            "llm_model": "qwen3:32b",
            "created_at": "2026-01-20T12:00:00Z",
        }

        # Create request
        domain_request = DomainCreateRequest(
            name="medical",
            description="Medical documents and research papers",
            llm_model="qwen3:32b",
        )

        # Call endpoint
        with patch("time.time", return_value=1000.5):  # 0.5s elapsed
            response = await create_domain(domain_request, mock_request)

        # Verify response structure
        assert isinstance(response, ApiResponse)
        assert response.success is True

        # Verify metadata
        assert response.metadata.request_id == "req_test123"
        assert response.metadata.processing_time_ms == 500.0  # 0.5s = 500ms
        assert response.metadata.api_version == "v1"

        # Verify data content
        assert response.data.name == "medical"
        assert response.data.status == "pending"
        assert response.data.llm_model == "qwen3:32b"

        # Verify embedding was generated
        mock_embedding_service.embed_single.assert_called_once()

        # Verify domain was created in repository
        mock_domain_repository.create_domain.assert_called_once()


class TestResponseStructureCompliance:
    """Tests to verify response structure matches specification."""

    @pytest.mark.asyncio
    async def test_response_has_all_required_fields(
        self,
        mock_request,
        mock_domain_repository,
    ):
        """Test response includes all required fields per spec."""
        from src.api.v1.domain_training import list_domains

        mock_domain_repository.list_domains.return_value = []

        response = await list_domains(mock_request)

        # Serialize to dict to check structure
        response_dict = response.model_dump()

        # Required top-level fields
        assert "success" in response_dict
        assert "data" in response_dict
        assert "metadata" in response_dict

        # Required metadata fields
        assert "request_id" in response_dict["metadata"]
        assert "timestamp" in response_dict["metadata"]
        assert "api_version" in response_dict["metadata"]

    @pytest.mark.asyncio
    async def test_response_json_serializable(
        self,
        mock_request,
        mock_domain_repository,
    ):
        """Test response can be serialized to JSON."""
        import json

        from src.api.v1.domain_training import list_domains

        mock_domain_repository.list_domains.return_value = [
            {
                "id": "d1",
                "name": "tech",
                "description": "Tech docs",
                "status": "ready",
                "llm_model": "qwen3:32b",
                "training_metrics": "{'f1': 0.85}",  # String format as stored in Neo4j
                "created_at": "2026-01-20T12:00:00Z",
                "trained_at": "2026-01-20T13:00:00Z",
            }
        ]

        response = await list_domains(mock_request)

        # Should be JSON serializable
        response_dict = response.model_dump()
        json_str = json.dumps(response_dict)

        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"][0]["name"] == "tech"
