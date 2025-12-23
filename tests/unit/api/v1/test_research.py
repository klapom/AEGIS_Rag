"""Unit tests for research API endpoint.

Sprint 62 Feature 62.10: Research Endpoint Backend
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.main import app
from src.api.models.research import ResearchQueryRequest


@pytest.mark.asyncio
class TestResearchQueryEndpoint:
    """Test /api/v1/research/query endpoint."""

    async def test_research_query_non_streaming(self):
        """Test non-streaming research query."""
        with patch("src.api.v1.research._stream_research_progress") as mock_research:
            # Mock research workflow
            mock_research.return_value = {
                "query": "What is AI?",
                "namespace": "default",
                "research_plan": ["Query 1", "Query 2"],
                "search_results": [
                    {
                        "text": "AI is artificial intelligence",
                        "score": 0.9,
                        "source": "vector",
                        "metadata": {},
                    }
                ],
                "synthesis": "AI is a field of computer science.",
                "iteration": 2,
                "quality_metrics": {"sufficient": True},
            }

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/research/query",
                    json={
                        "query": "What is AI?",
                        "namespace": "default",
                        "max_iterations": 3,
                        "stream": False,
                    },
                )

            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert data["query"] == "What is AI?"
            assert "synthesis" in data
            assert len(data["sources"]) > 0
            assert data["iterations"] == 2

    async def test_research_query_streaming(self):
        """Test streaming research query."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("src.api.v1.research.create_research_graph") as mock_create:
                # Mock graph
                mock_graph = AsyncMock()

                # Mock async stream that yields events
                async def mock_astream(state):
                    # Yield plan event
                    yield {"plan": {"research_plan": ["Query 1"], "iteration": 0}}
                    # Yield search event
                    yield {"search": {"search_results": [{"text": "Result"}], "iteration": 1}}
                    # Yield evaluate event
                    yield {"evaluate": {"quality_metrics": {"sufficient": True}, "iteration": 1}}
                    # Yield synthesize event
                    yield {
                        "synthesize": {
                            "synthesis": "Final answer",
                            "search_results": [{"text": "Result"}],
                            "iteration": 1,
                        }
                    }

                mock_graph.astream = mock_astream
                mock_create.return_value = mock_graph

                response = await client.post(
                    "/api/v1/research/query",
                    json={
                        "query": "What is AI?",
                        "namespace": "default",
                        "max_iterations": 3,
                        "stream": True,
                    },
                )

                assert response.status_code == status.HTTP_200_OK
                assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

                # Read SSE events
                content = response.text
                assert "data:" in content

    async def test_research_query_validation(self):
        """Test request validation."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Empty query should fail
            response = await client.post(
                "/api/v1/research/query",
                json={
                    "query": "",
                    "namespace": "default",
                },
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_research_query_max_iterations_validation(self):
        """Test max_iterations validation."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Max iterations > 5 should fail
            response = await client.post(
                "/api/v1/research/query",
                json={
                    "query": "Test query",
                    "max_iterations": 10,
                    "stream": False,
                },
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_research_query_timeout(self):
        """Test timeout handling."""
        with patch("src.api.v1.research._stream_research_progress") as mock_research:
            # Simulate timeout
            import asyncio

            mock_research.side_effect = asyncio.TimeoutError()

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/research/query",
                    json={
                        "query": "What is AI?",
                        "stream": False,
                    },
                )

            assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    async def test_research_query_error_handling(self):
        """Test general error handling."""
        with patch("src.api.v1.research._stream_research_progress") as mock_research:
            # Simulate general error
            mock_research.side_effect = Exception("Research failed")

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/research/query",
                    json={
                        "query": "What is AI?",
                        "stream": False,
                    },
                )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_research_query_default_values(self):
        """Test default values in request."""
        with patch("src.api.v1.research._stream_research_progress") as mock_research:
            mock_research.return_value = {
                "query": "Test",
                "namespace": "default",
                "research_plan": [],
                "search_results": [],
                "synthesis": "Answer",
                "iteration": 1,
                "quality_metrics": {},
            }

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/research/query",
                    json={"query": "Test query", "stream": False},
                )

            assert response.status_code == status.HTTP_200_OK

            # Verify defaults were used
            call_args = mock_research.call_args
            assert call_args.kwargs.get("max_iterations") == 3
            assert call_args.kwargs.get("namespace") == "default"


@pytest.mark.asyncio
class TestResearchHealthEndpoint:
    """Test /api/v1/research/health endpoint."""

    async def test_research_health(self):
        """Test health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/research/health")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "research"


class TestExtractSources:
    """Test source extraction helper."""

    def test_extract_sources_basic(self):
        """Test basic source extraction."""
        from src.api.v1.research import _extract_sources

        results = [
            {
                "text": "Text 1",
                "score": 0.9,
                "source": "vector",
                "metadata": {},
                "entities": [],
                "relationships": [],
            },
            {
                "text": "Text 2",
                "score": 0.8,
                "source": "graph",
                "metadata": {},
                "entities": ["Entity1"],
                "relationships": ["rel1"],
            },
        ]

        sources = _extract_sources(results)

        assert len(sources) == 2
        assert sources[0].score == 0.9  # Sorted by score
        assert sources[1].score == 0.8

    def test_extract_sources_sorts_by_score(self):
        """Test that sources are sorted by score."""
        from src.api.v1.research import _extract_sources

        results = [
            {"text": "Low", "score": 0.5, "source": "vector", "metadata": {}},
            {"text": "High", "score": 0.9, "source": "vector", "metadata": {}},
            {"text": "Medium", "score": 0.7, "source": "vector", "metadata": {}},
        ]

        sources = _extract_sources(results)

        assert sources[0].score == 0.9
        assert sources[1].score == 0.7
        assert sources[2].score == 0.5

    def test_extract_sources_limits_to_20(self):
        """Test that sources are limited to 20."""
        from src.api.v1.research import _extract_sources

        results = [
            {"text": f"Text {i}", "score": 0.9, "source": "vector", "metadata": {}}
            for i in range(30)
        ]

        sources = _extract_sources(results)

        assert len(sources) == 20

    def test_extract_sources_empty(self):
        """Test extraction from empty results."""
        from src.api.v1.research import _extract_sources

        sources = _extract_sources([])

        assert sources == []

    def test_extract_sources_handles_missing_fields(self):
        """Test handling of missing optional fields."""
        from src.api.v1.research import _extract_sources

        results = [
            {
                "text": "Text",
                "score": 0.9,
                "source": "vector",
                # Missing metadata, entities, relationships
            }
        ]

        sources = _extract_sources(results)

        assert len(sources) == 1
        assert sources[0].metadata == {}
        assert sources[0].entities == []
        assert sources[0].relationships == []


class TestResearchModels:
    """Test Pydantic models."""

    def test_research_query_request_defaults(self):
        """Test default values in request model."""
        request = ResearchQueryRequest(query="Test query")

        assert request.query == "Test query"
        assert request.namespace == "default"
        assert request.max_iterations == 3
        assert request.stream is True

    def test_research_query_request_validation(self):
        """Test validation in request model."""
        # Empty query should fail
        with pytest.raises(Exception):  # Pydantic validation error
            ResearchQueryRequest(query="")

        # max_iterations < 1 should fail
        with pytest.raises(Exception):
            ResearchQueryRequest(query="Test", max_iterations=0)

        # max_iterations > 5 should fail
        with pytest.raises(Exception):
            ResearchQueryRequest(query="Test", max_iterations=6)

    def test_research_query_request_immutable(self):
        """Test that request model is immutable."""
        request = ResearchQueryRequest(query="Test")

        with pytest.raises(Exception):  # Frozen model
            request.query = "Modified"
