"""Unit tests for web search client.

Sprint 63 Feature 63.9: WebSearch Integration for Research Agent.

Tests cover:
- DuckDuckGo search execution (mocked)
- Timeout handling
- Error recovery
- Result formatting
- Retry logic
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domains.web_search.client import WebSearchClient, get_web_search_client
from src.domains.web_search.models import WebSearchResult


@pytest.fixture
def mock_ddgs_results():
    """Mock DuckDuckGo search results."""
    return [
        {
            "title": "AI Research 2025",
            "href": "https://example.com/ai-research",
            "body": "Latest advances in AI research...",
            "published_date": "2025-01-15T10:30:00Z",
        },
        {
            "title": "Machine Learning Trends",
            "href": "https://example.com/ml-trends",
            "body": "Machine learning is evolving...",
            "published_date": None,
        },
        {
            "title": "Deep Learning Tutorial",
            "href": "https://example.com/dl-tutorial",
            "body": "A comprehensive guide to deep learning...",
        },
    ]


class TestWebSearchClient:
    """Test WebSearchClient."""

    @pytest.mark.asyncio
    async def test_search_success(self, mock_ddgs_results):
        """Test successful search execution."""
        client = WebSearchClient()

        # Mock DDGS
        with patch("src.domains.web_search.client.DDGS") as mock_ddgs_class:
            # Create context manager mock
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__.return_value = mock_ddgs
            mock_ddgs.__exit__.return_value = None
            mock_ddgs_class.return_value = mock_ddgs

            # Mock text search
            mock_ddgs.text.return_value = iter(mock_ddgs_results)

            # Execute search
            results = await client.search(
                query="AI research",
                max_results=5,
            )

            # Verify results
            assert len(results) == 3
            assert all(isinstance(r, WebSearchResult) for r in results)

            # Check first result
            assert results[0].title == "AI Research 2025"
            assert results[0].url == "https://example.com/ai-research"
            assert results[0].snippet == "Latest advances in AI research..."
            assert results[0].source == "duckduckgo"
            assert results[0].published_date is not None

            # Check result without published_date
            assert results[1].published_date is None

    @pytest.mark.asyncio
    async def test_search_timeout(self):
        """Test search timeout handling."""
        client = WebSearchClient()

        with patch("src.domains.web_search.client.DDGS") as mock_ddgs_class:
            # Mock slow search
            def slow_search(*args, **kwargs):
                import time
                time.sleep(20)  # Exceeds timeout
                return []

            mock_ddgs = MagicMock()
            mock_ddgs.__enter__.return_value = mock_ddgs
            mock_ddgs.__exit__.return_value = None
            mock_ddgs.text.side_effect = slow_search
            mock_ddgs_class.return_value = mock_ddgs

            # Execute search with short timeout
            results = await client.search(
                query="test",
                timeout=1,
            )

            # Should return empty on timeout
            assert results == []

    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        """Test error handling during search."""
        client = WebSearchClient()

        with patch("src.domains.web_search.client.DDGS") as mock_ddgs_class:
            # Mock search that raises exception
            def failing_search(*args, **kwargs):
                raise Exception("Network error")

            mock_ddgs = MagicMock()
            mock_ddgs.__enter__.return_value = mock_ddgs
            mock_ddgs.__exit__.return_value = None
            mock_ddgs.text.side_effect = failing_search
            mock_ddgs_class.return_value = mock_ddgs

            # Execute search
            results = await client.search(query="test")

            # Should return empty on error
            assert results == []

    @pytest.mark.asyncio
    async def test_format_result_with_published_date(self):
        """Test result formatting with published date."""
        client = WebSearchClient()

        raw_result = {
            "title": "Test Article",
            "href": "https://example.com/article",
            "body": "Article content...",
            "published_date": "2025-01-15T10:30:00Z",
        }

        result = client._format_result(raw_result)

        assert result is not None
        assert result.title == "Test Article"
        assert result.url == "https://example.com/article"
        assert result.snippet == "Article content..."
        assert result.published_date is not None
        assert isinstance(result.published_date, datetime)

    @pytest.mark.asyncio
    async def test_format_result_without_published_date(self):
        """Test result formatting without published date."""
        client = WebSearchClient()

        raw_result = {
            "title": "Test Article",
            "href": "https://example.com/article",
            "body": "Article content...",
        }

        result = client._format_result(raw_result)

        assert result is not None
        assert result.published_date is None

    @pytest.mark.asyncio
    async def test_format_result_invalid_date(self):
        """Test result formatting with invalid date."""
        client = WebSearchClient()

        raw_result = {
            "title": "Test Article",
            "href": "https://example.com/article",
            "body": "Article content...",
            "published_date": "invalid-date",
        }

        result = client._format_result(raw_result)

        assert result is not None
        assert result.published_date is None  # Invalid date should be skipped

    @pytest.mark.asyncio
    async def test_format_result_missing_fields(self):
        """Test result formatting with missing fields."""
        client = WebSearchClient()

        raw_result = {
            "href": "https://example.com/article",
        }

        result = client._format_result(raw_result)

        assert result is not None
        assert result.title == "No Title"
        assert result.snippet == ""

    @pytest.mark.asyncio
    async def test_format_result_minimal_fields(self):
        """Test result formatting with minimal fields."""
        client = WebSearchClient()

        # Minimal raw result (empty dict gets default values)
        raw_result = {}

        result = client._format_result(raw_result)

        # Should create result with defaults
        assert result is not None
        assert result.title == "No Title"
        assert result.url == ""
        assert result.snippet == ""

    @pytest.mark.asyncio
    async def test_search_with_retry_success_first_attempt(self, mock_ddgs_results):
        """Test retry logic - success on first attempt."""
        client = WebSearchClient()

        with patch("src.domains.web_search.client.DDGS") as mock_ddgs_class:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__.return_value = mock_ddgs
            mock_ddgs.__exit__.return_value = None
            mock_ddgs_class.return_value = mock_ddgs

            mock_ddgs.text.return_value = iter(mock_ddgs_results)

            # Execute with retry
            results = await client.search_with_retry(
                query="AI research",
                max_results=5,
                max_retries=3,
            )

            # Should succeed on first attempt
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_with_retry_no_results(self):
        """Test retry logic - no results after retries."""
        client = WebSearchClient()

        with patch("src.domains.web_search.client.DDGS") as mock_ddgs_class:
            mock_ddgs = MagicMock()
            mock_ddgs.__enter__.return_value = mock_ddgs
            mock_ddgs.__exit__.return_value = None
            mock_ddgs_class.return_value = mock_ddgs

            # Empty results
            mock_ddgs.text.return_value = iter([])

            # Execute with retry
            results = await client.search_with_retry(
                query="test",
                max_retries=2,
            )

            # Should return empty after retries
            assert results == []

    @pytest.mark.asyncio
    async def test_search_with_retry_exception(self):
        """Test retry logic - exception handling."""
        client = WebSearchClient()

        call_count = 0

        with patch.object(client, "search") as mock_search:
            async def mock_search_fail(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                raise Exception("Network error")

            mock_search.side_effect = mock_search_fail

            # Execute with retry
            results = await client.search_with_retry(
                query="test",
                max_retries=3,
            )

            # Should exhaust retries
            assert call_count == 3
            assert results == []

    def test_get_web_search_client_singleton(self):
        """Test global client singleton."""
        client1 = get_web_search_client()
        client2 = get_web_search_client()

        # Should return same instance
        assert client1 is client2
        assert isinstance(client1, WebSearchClient)
