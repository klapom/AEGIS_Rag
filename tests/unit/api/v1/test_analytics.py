"""Unit tests for Analytics API endpoints.

Sprint 62 Feature 62.9: Section Analytics Endpoint

Tests cover:
- Successful analytics retrieval
- Caching behavior
- Error handling (missing document, empty sections)
- Statistics calculation
- Response validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.models.analytics import (
    SectionAnalyticsRequest,
    SectionAnalyticsResponse,
    SectionStats,
)


@pytest.fixture
def sample_section_stats():
    """Sample section statistics for testing."""
    return [
        SectionStats(
            section_id="4:abc123:0",
            section_title="Introduction",
            section_level=1,
            entity_count=25,
            chunk_count=15,
            relationship_count=42,
        ),
        SectionStats(
            section_id="4:abc123:1",
            section_title="Background",
            section_level=2,
            entity_count=18,
            chunk_count=12,
            relationship_count=30,
        ),
        SectionStats(
            section_id="4:abc123:2",
            section_title="Methods",
            section_level=2,
            entity_count=30,
            chunk_count=20,
            relationship_count=55,
        ),
        SectionStats(
            section_id="4:abc123:3",
            section_title="Results",
            section_level=2,
            entity_count=22,
            chunk_count=16,
            relationship_count=38,
        ),
        SectionStats(
            section_id="4:abc123:4",
            section_title="Discussion",
            section_level=2,
            entity_count=20,
            chunk_count=14,
            relationship_count=35,
        ),
    ]


@pytest.fixture
def sample_analytics_response(sample_section_stats):
    """Sample analytics response for testing."""
    return SectionAnalyticsResponse(
        document_id="doc_123",
        total_sections=5,
        level_distribution={1: 1, 2: 4},
        avg_entities_per_section=23.0,
        avg_chunks_per_section=15.4,
        top_sections=sorted(
            sample_section_stats,
            key=lambda s: s.relationship_count,
            reverse=True,
        )[:10],
    )


class TestSectionAnalyticsEndpoint:
    """Tests for POST /api/v1/analytics/sections endpoint."""

    @pytest.mark.asyncio
    async def test_successful_analytics_retrieval(self, sample_analytics_response):
        """Test successful section analytics retrieval."""
        # Mock the service
        mock_service = MagicMock()
        mock_service.get_section_analytics = AsyncMock(return_value=sample_analytics_response)

        with patch(
            "src.api.v1.analytics.get_section_analytics_service",
            return_value=mock_service,
        ):
            from src.api.v1.analytics import get_section_analytics

            request = SectionAnalyticsRequest(
                document_id="doc_123",
                namespace="default",
            )

            response = await get_section_analytics(request)

            # Verify response
            assert response.document_id == "doc_123"
            assert response.total_sections == 5
            assert response.level_distribution == {1: 1, 2: 4}
            assert response.avg_entities_per_section == 23.0
            assert response.avg_chunks_per_section == 15.4
            assert len(response.top_sections) == 5

            # Verify service was called correctly
            mock_service.get_section_analytics.assert_called_once_with(
                document_id="doc_123",
                namespace="default",
            )

    @pytest.mark.asyncio
    async def test_empty_document_id_validation(self):
        """Test validation error for empty document_id."""
        mock_service = MagicMock()

        with patch(
            "src.api.v1.analytics.get_section_analytics_service",
            return_value=mock_service,
        ):
            from src.api.v1.analytics import get_section_analytics

            request = SectionAnalyticsRequest(
                document_id="   ",  # Empty after strip
                namespace="default",
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_section_analytics(request)

            assert exc_info.value.status_code == 400
            assert "cannot be empty" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_document_not_found(self):
        """Test 404 error when document has no sections."""
        # Mock service to return response with 0 sections
        mock_service = MagicMock()
        mock_service.get_section_analytics = AsyncMock(
            return_value=SectionAnalyticsResponse(
                document_id="doc_404",
                total_sections=0,
                level_distribution={},
                avg_entities_per_section=0.0,
                avg_chunks_per_section=0.0,
                top_sections=[],
            )
        )

        with patch(
            "src.api.v1.analytics.get_section_analytics_service",
            return_value=mock_service,
        ):
            from src.api.v1.analytics import get_section_analytics

            request = SectionAnalyticsRequest(
                document_id="doc_404",
                namespace="default",
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_section_analytics(request)

            assert exc_info.value.status_code == 404
            assert "No sections found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_service_error_handling(self):
        """Test error handling when service raises exception."""
        mock_service = MagicMock()
        mock_service.get_section_analytics = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        with patch(
            "src.api.v1.analytics.get_section_analytics_service",
            return_value=mock_service,
        ):
            from src.api.v1.analytics import get_section_analytics

            request = SectionAnalyticsRequest(
                document_id="doc_123",
                namespace="default",
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_section_analytics(request)

            assert exc_info.value.status_code == 500
            assert "Failed to retrieve section analytics" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_custom_namespace(self, sample_analytics_response):
        """Test analytics retrieval with custom namespace."""
        mock_service = MagicMock()
        mock_service.get_section_analytics = AsyncMock(return_value=sample_analytics_response)

        with patch(
            "src.api.v1.analytics.get_section_analytics_service",
            return_value=mock_service,
        ):
            from src.api.v1.analytics import get_section_analytics

            request = SectionAnalyticsRequest(
                document_id="doc_123",
                namespace="project_x",
            )

            await get_section_analytics(request)

            # Verify namespace was passed correctly
            mock_service.get_section_analytics.assert_called_once_with(
                document_id="doc_123",
                namespace="project_x",
            )


class TestSectionAnalyticsService:
    """Tests for SectionAnalyticsService."""

    @pytest.mark.asyncio
    async def test_query_section_stats(self, sample_section_stats):
        """Test Neo4j query for section statistics."""
        from src.domains.knowledge_graph.analytics.section_analytics import (
            SectionAnalyticsService,
        )

        # Mock Neo4j client
        mock_neo4j = MagicMock()
        mock_neo4j.execute_query = AsyncMock(
            return_value=[
                {
                    "section_id": "4:abc123:0",
                    "section_heading": "Introduction",
                    "section_level": 1,
                    "entity_count": 25,
                    "chunk_count": 15,
                    "relationship_count": 42,
                },
                {
                    "section_id": "4:abc123:1",
                    "section_heading": "Background",
                    "section_level": 2,
                    "entity_count": 18,
                    "chunk_count": 12,
                    "relationship_count": 30,
                },
            ]
        )

        service = SectionAnalyticsService(neo4j_client=mock_neo4j)

        stats = await service._query_section_stats("doc_123", "default")

        # Verify query was executed
        mock_neo4j.execute_query.assert_called_once()
        call_args = mock_neo4j.execute_query.call_args

        # Verify query parameters
        assert call_args.kwargs["parameters"]["document_id"] == "doc_123"
        assert call_args.kwargs["parameters"]["namespace"] == "default"

        # Verify results
        assert len(stats) == 2
        assert stats[0].section_title == "Introduction"
        assert stats[0].entity_count == 25
        assert stats[1].section_title == "Background"

    @pytest.mark.asyncio
    async def test_calculate_level_distribution(self, sample_section_stats):
        """Test level distribution calculation."""
        from src.domains.knowledge_graph.analytics.section_analytics import (
            SectionAnalyticsService,
        )

        mock_neo4j = MagicMock()
        service = SectionAnalyticsService(neo4j_client=mock_neo4j)

        distribution = service._calculate_level_distribution(sample_section_stats)

        assert distribution == {1: 1, 2: 4}

    @pytest.mark.asyncio
    async def test_calculate_average_entities(self, sample_section_stats):
        """Test average entities calculation."""
        from src.domains.knowledge_graph.analytics.section_analytics import (
            SectionAnalyticsService,
        )

        mock_neo4j = MagicMock()
        service = SectionAnalyticsService(neo4j_client=mock_neo4j)

        avg = service._calculate_average(sample_section_stats, "entity_count")

        # (25 + 18 + 30 + 22 + 20) / 5 = 23.0
        assert avg == 23.0

    @pytest.mark.asyncio
    async def test_calculate_average_chunks(self, sample_section_stats):
        """Test average chunks calculation."""
        from src.domains.knowledge_graph.analytics.section_analytics import (
            SectionAnalyticsService,
        )

        mock_neo4j = MagicMock()
        service = SectionAnalyticsService(neo4j_client=mock_neo4j)

        avg = service._calculate_average(sample_section_stats, "chunk_count")

        # (15 + 12 + 20 + 16 + 14) / 5 = 15.4
        assert avg == 15.4

    @pytest.mark.asyncio
    async def test_calculate_average_empty_list(self):
        """Test average calculation with empty list."""
        from src.domains.knowledge_graph.analytics.section_analytics import (
            SectionAnalyticsService,
        )

        mock_neo4j = MagicMock()
        service = SectionAnalyticsService(neo4j_client=mock_neo4j)

        avg = service._calculate_average([], "entity_count")

        assert avg == 0.0

    @pytest.mark.asyncio
    async def test_caching_behavior(self, sample_analytics_response):
        """Test Redis caching behavior."""
        from src.domains.knowledge_graph.analytics.section_analytics import (
            SectionAnalyticsService,
        )

        # Mock Neo4j client
        mock_neo4j = MagicMock()

        # Mock Redis
        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=None)  # Cache miss
        mock_redis_client.setex = AsyncMock()

        mock_redis_memory = MagicMock()
        mock_redis_memory.client = AsyncMock(return_value=mock_redis_client)

        with patch(
            "src.domains.knowledge_graph.analytics.section_analytics.get_redis_memory",
            return_value=mock_redis_memory,
        ):
            service = SectionAnalyticsService(neo4j_client=mock_neo4j)

            # Test cache key generation
            cache_key = service._get_cache_key("doc_123", "default")
            assert cache_key.startswith("section_analytics:")
            assert len(cache_key) > len("section_analytics:")

    @pytest.mark.asyncio
    async def test_top_sections_ranking(self, sample_section_stats):
        """Test that top sections are ranked by relationship count."""
        from src.domains.knowledge_graph.analytics.section_analytics import (
            SectionAnalyticsService,
        )

        mock_neo4j = MagicMock()
        mock_neo4j.execute_query = AsyncMock(
            return_value=[
                {
                    "section_id": stats.section_id,
                    "section_heading": stats.section_title,
                    "section_level": stats.section_level,
                    "entity_count": stats.entity_count,
                    "chunk_count": stats.chunk_count,
                    "relationship_count": stats.relationship_count,
                }
                for stats in sample_section_stats
            ]
        )

        # Mock Redis for cache miss
        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=None)
        mock_redis_client.setex = AsyncMock()
        mock_redis_memory = MagicMock()
        mock_redis_memory.client = AsyncMock(return_value=mock_redis_client)

        with patch(
            "src.domains.knowledge_graph.analytics.section_analytics.get_redis_memory",
            return_value=mock_redis_memory,
        ):
            service = SectionAnalyticsService(neo4j_client=mock_neo4j)
            response = await service.get_section_analytics("doc_123", "default")

            # Top section should be "Methods" with 55 relationships
            assert response.top_sections[0].section_title == "Methods"
            assert response.top_sections[0].relationship_count == 55

            # Second should be "Introduction" with 42 relationships
            assert response.top_sections[1].section_title == "Introduction"
            assert response.top_sections[1].relationship_count == 42


class TestPydanticModels:
    """Tests for Pydantic models."""

    def test_section_stats_validation(self):
        """Test SectionStats model validation."""
        stats = SectionStats(
            section_id="test_id",
            section_title="Test Section",
            section_level=2,
            entity_count=10,
            chunk_count=5,
            relationship_count=20,
        )

        assert stats.section_id == "test_id"
        assert stats.section_title == "Test Section"
        assert stats.section_level == 2

    def test_section_stats_negative_counts(self):
        """Test that negative counts are rejected."""
        with pytest.raises(ValueError):
            SectionStats(
                section_id="test_id",
                section_title="Test Section",
                section_level=2,
                entity_count=-1,  # Invalid
                chunk_count=5,
                relationship_count=20,
            )

    def test_section_analytics_request_defaults(self):
        """Test request model default values."""
        request = SectionAnalyticsRequest(document_id="doc_123")

        assert request.document_id == "doc_123"
        assert request.namespace == "default"

    def test_section_analytics_response_validation(self):
        """Test response model validation."""
        response = SectionAnalyticsResponse(
            document_id="doc_123",
            total_sections=5,
            level_distribution={1: 2, 2: 3},
            avg_entities_per_section=15.5,
            avg_chunks_per_section=10.2,
            top_sections=[],
        )

        assert response.document_id == "doc_123"
        assert response.total_sections == 5
        assert response.level_distribution == {1: 2, 2: 3}
