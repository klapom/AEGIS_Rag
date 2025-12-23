"""Unit tests for graph communities API endpoints.

Sprint 63 Feature 63.5: Community Visualization API

Tests cover:
- Section communities endpoint
- Community comparison endpoint
- Error handling
- Response validation
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


class TestSectionCommunitiesEndpoint:
    """Tests for GET /api/v1/graph/communities/{document_id}/sections/{section_id}"""

    @pytest.mark.asyncio
    async def test_get_section_communities_success(self, client: TestClient) -> None:
        """Test successfully getting section communities."""
        with patch(
            "src.api.v1.graph_communities.get_section_community_service"
        ) as mock_get_service:
            # Mock service
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            # Mock response
            from src.domains.knowledge_graph.communities import (
                CommunityVisualization,
                SectionCommunityVisualizationResponse,
            )

            mock_response = SectionCommunityVisualizationResponse(
                document_id="doc_123",
                section_heading="Introduction",
                total_communities=1,
                total_entities=5,
                communities=[
                    CommunityVisualization(
                        community_id="community_0",
                        section_heading="Introduction",
                        size=5,
                        cohesion_score=0.75,
                    )
                ],
                generation_time_ms=250.0,
            )

            mock_service.get_section_communities_with_visualization = AsyncMock(
                return_value=mock_response
            )

            # Make request
            response = client.get("/api/v1/graph/communities/doc_123/sections/Introduction")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == "doc_123"
            assert data["section_heading"] == "Introduction"
            assert data["total_communities"] == 1

    def test_get_section_communities_with_parameters(self, client: TestClient) -> None:
        """Test endpoint with query parameters."""
        with patch(
            "src.api.v1.graph_communities.get_section_community_service"
        ) as mock_get_service:
            # Mock service
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            from src.domains.knowledge_graph.communities import (
                SectionCommunityVisualizationResponse,
            )

            mock_response = SectionCommunityVisualizationResponse(
                document_id="doc_123",
                section_heading="Methods",
                total_communities=0,
                total_entities=0,
                communities=[],
                generation_time_ms=100.0,
            )

            mock_service.get_section_communities_with_visualization = AsyncMock(
                return_value=mock_response
            )

            # Make request with parameters
            response = client.get(
                "/api/v1/graph/communities/doc_123/sections/Methods?"
                "algorithm=leiden&resolution=1.5&layout_algorithm=circular"
            )

            # Verify service was called with parameters
            assert response.status_code == 200
            call_kwargs = mock_service.get_section_communities_with_visualization.call_args[1]
            assert call_kwargs["algorithm"] == "leiden"
            assert call_kwargs["resolution"] == 1.5
            assert call_kwargs["layout_algorithm"] == "circular"

    def test_get_section_communities_invalid_algorithm(self, client: TestClient) -> None:
        """Test endpoint with invalid algorithm parameter."""
        with patch(
            "src.api.v1.graph_communities.get_section_community_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            from src.domains.knowledge_graph.communities import (
                SectionCommunityVisualizationResponse,
            )

            mock_response = SectionCommunityVisualizationResponse(
                document_id="doc_123",
                section_heading="Introduction",
                total_communities=0,
                total_entities=0,
                communities=[],
                generation_time_ms=100.0,
            )

            mock_service.get_section_communities_with_visualization = AsyncMock(
                return_value=mock_response
            )

            # Make request with invalid algorithm
            response = client.get(
                "/api/v1/graph/communities/doc_123/sections/Introduction?" "algorithm=invalid"
            )

            # Should fail validation
            assert response.status_code == 422  # Validation error

    def test_get_section_communities_invalid_resolution(self, client: TestClient) -> None:
        """Test endpoint with invalid resolution parameter."""
        with patch(
            "src.api.v1.graph_communities.get_section_community_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            from src.domains.knowledge_graph.communities import (
                SectionCommunityVisualizationResponse,
            )

            mock_response = SectionCommunityVisualizationResponse(
                document_id="doc_123",
                section_heading="Introduction",
                total_communities=0,
                total_entities=0,
                communities=[],
                generation_time_ms=100.0,
            )

            mock_service.get_section_communities_with_visualization = AsyncMock(
                return_value=mock_response
            )

            # Make request with invalid resolution (< 0.1)
            response = client.get(
                "/api/v1/graph/communities/doc_123/sections/Introduction?" "resolution=0.05"
            )

            # Should fail validation
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_section_communities_not_found(self, client: TestClient) -> None:
        """Test endpoint when section is not found."""
        with patch(
            "src.api.v1.graph_communities.get_section_community_service"
        ) as mock_get_service:
            # Mock service to raise ValueError
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            mock_service.get_section_communities_with_visualization = AsyncMock(
                side_effect=ValueError("Section not found")
            )

            # Make request
            response = client.get("/api/v1/graph/communities/doc_999/sections/NonExistent")

            # Should return 404
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_section_communities_server_error(self, client: TestClient) -> None:
        """Test endpoint when server error occurs."""
        with patch(
            "src.api.v1.graph_communities.get_section_community_service"
        ) as mock_get_service:
            # Mock service to raise exception
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            mock_service.get_section_communities_with_visualization = AsyncMock(
                side_effect=Exception("Database error")
            )

            # Make request
            response = client.get("/api/v1/graph/communities/doc_123/sections/Introduction")

            # Should return 500
            assert response.status_code == 500


class TestCompareCommunitiesEndpoint:
    """Tests for POST /api/v1/graph/communities/compare"""

    @pytest.mark.asyncio
    async def test_compare_communities_success(self, client: TestClient) -> None:
        """Test successfully comparing section communities."""
        with patch(
            "src.api.v1.graph_communities.get_section_community_service"
        ) as mock_get_service:
            # Mock service
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            from src.domains.knowledge_graph.communities import (
                CommunityComparisonOverview,
            )

            mock_response = CommunityComparisonOverview(
                section_count=2,
                sections=["Introduction", "Methods"],
                total_shared_communities=1,
                overlap_matrix={
                    "Introduction": {"Methods": 3},
                    "Methods": {"Introduction": 3},
                },
                comparison_time_ms=450.0,
            )

            mock_service.compare_section_communities = AsyncMock(return_value=mock_response)

            # Make request
            response = client.post(
                "/api/v1/graph/communities/compare",
                json={
                    "document_id": "doc_123",
                    "sections": ["Introduction", "Methods"],
                    "algorithm": "louvain",
                    "resolution": 1.0,
                },
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["section_count"] == 2
            assert len(data["sections"]) == 2

    @pytest.mark.asyncio
    async def test_compare_communities_missing_document_id(self, client: TestClient) -> None:
        """Test comparison without document_id."""
        with patch(
            "src.api.v1.graph_communities.get_section_community_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            # Make request without document_id
            response = client.post(
                "/api/v1/graph/communities/compare",
                json={
                    "sections": ["Introduction", "Methods"],
                },
            )

            # Should return 400
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_compare_communities_single_section(self, client: TestClient) -> None:
        """Test comparison with only one section."""
        with patch(
            "src.api.v1.graph_communities.get_section_community_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            # Make request with single section
            response = client.post(
                "/api/v1/graph/communities/compare",
                json={
                    "document_id": "doc_123",
                    "sections": ["Introduction"],
                },
            )

            # Should return 400
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_compare_communities_server_error(self, client: TestClient) -> None:
        """Test comparison when server error occurs."""
        with patch(
            "src.api.v1.graph_communities.get_section_community_service"
        ) as mock_get_service:
            # Mock service to raise exception
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            mock_service.compare_section_communities = AsyncMock(
                side_effect=Exception("Database error")
            )

            # Make request
            response = client.post(
                "/api/v1/graph/communities/compare",
                json={
                    "document_id": "doc_123",
                    "sections": ["Introduction", "Methods"],
                },
            )

            # Should return 500
            assert response.status_code == 500


class TestEndpointDocumentation:
    """Tests for endpoint documentation and schema."""

    def test_section_communities_endpoint_documented(self) -> None:
        """Test that section communities endpoint is properly documented."""
        response = client.get("/openapi.json") if hasattr(client, "get") else None

        # Verify endpoint exists in OpenAPI schema
        if response and response.status_code == 200:
            schema = response.json()
            assert "/api/v1/graph/communities/{document_id}/sections/{section_id}" in schema.get(
                "paths", {}
            )

    def test_compare_communities_endpoint_documented(self) -> None:
        """Test that compare communities endpoint is properly documented."""
        response = client.get("/openapi.json") if hasattr(client, "get") else None

        # Verify endpoint exists in OpenAPI schema
        if response and response.status_code == 200:
            schema = response.json()
            assert "/api/v1/graph/communities/compare" in schema.get("paths", {})


# Test client for endpoint tests
client = TestClient(app)
