"""Unit tests for web search models.

Sprint 63 Feature 63.9: WebSearch Integration for Research Agent.

Tests cover:
- WebSearchRequest validation
- WebSearchResult validation
- Default values and constraints
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.domains.web_search.models import WebSearchRequest, WebSearchResult


class TestWebSearchRequest:
    """Test WebSearchRequest model."""

    def test_valid_request(self):
        """Test valid request creation."""
        request = WebSearchRequest(
            query="AI research",
            max_results=10,
            region="en-US",
            safesearch="strict",
            timeout=15,
        )

        assert request.query == "AI research"
        assert request.max_results == 10
        assert request.region == "en-US"
        assert request.safesearch == "strict"
        assert request.timeout == 15

    def test_default_values(self):
        """Test default values."""
        request = WebSearchRequest(query="test query")

        assert request.query == "test query"
        assert request.max_results == 5
        assert request.region == "de-DE"
        assert request.safesearch == "moderate"
        assert request.timeout == 10

    def test_empty_query_rejected(self):
        """Test empty query is rejected."""
        with pytest.raises(ValidationError):
            WebSearchRequest(query="")

    def test_max_results_bounds(self):
        """Test max_results bounds."""
        # Min bound (1)
        request = WebSearchRequest(query="test", max_results=1)
        assert request.max_results == 1

        # Max bound (20)
        request = WebSearchRequest(query="test", max_results=20)
        assert request.max_results == 20

        # Below min (0)
        with pytest.raises(ValidationError):
            WebSearchRequest(query="test", max_results=0)

        # Above max (21)
        with pytest.raises(ValidationError):
            WebSearchRequest(query="test", max_results=21)

    def test_safesearch_validation(self):
        """Test safesearch literal validation."""
        # Valid values
        for value in ["strict", "moderate", "off"]:
            request = WebSearchRequest(query="test", safesearch=value)
            assert request.safesearch == value

        # Invalid value
        with pytest.raises(ValidationError):
            WebSearchRequest(query="test", safesearch="invalid")

    def test_timeout_bounds(self):
        """Test timeout bounds."""
        # Min bound (1)
        request = WebSearchRequest(query="test", timeout=1)
        assert request.timeout == 1

        # Max bound (30)
        request = WebSearchRequest(query="test", timeout=30)
        assert request.timeout == 30

        # Below min (0)
        with pytest.raises(ValidationError):
            WebSearchRequest(query="test", timeout=0)

        # Above max (31)
        with pytest.raises(ValidationError):
            WebSearchRequest(query="test", timeout=31)


class TestWebSearchResult:
    """Test WebSearchResult model."""

    def test_valid_result(self):
        """Test valid result creation."""
        now = datetime.now()
        result = WebSearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet text",
            published_date=now,
            source="duckduckgo",
            score=0.85,
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet text"
        assert result.published_date == now
        assert result.source == "duckduckgo"
        assert result.score == 0.85

    def test_default_values(self):
        """Test default values."""
        result = WebSearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test snippet",
        )

        assert result.published_date is None
        assert result.source == "duckduckgo"
        assert result.score == 0.0

    def test_optional_published_date(self):
        """Test optional published_date field."""
        # Without published_date
        result = WebSearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test",
        )
        assert result.published_date is None

        # With published_date
        now = datetime.now()
        result = WebSearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test",
            published_date=now,
        )
        assert result.published_date == now

    def test_score_bounds(self):
        """Test score bounds."""
        # Min bound (0.0)
        result = WebSearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test",
            score=0.0,
        )
        assert result.score == 0.0

        # Max bound (1.0)
        result = WebSearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test",
            score=1.0,
        )
        assert result.score == 1.0

        # Below min (-0.1)
        with pytest.raises(ValidationError):
            WebSearchResult(
                title="Test",
                url="https://example.com",
                snippet="Test",
                score=-0.1,
            )

        # Above max (1.1)
        with pytest.raises(ValidationError):
            WebSearchResult(
                title="Test",
                url="https://example.com",
                snippet="Test",
                score=1.1,
            )

    def test_required_fields(self):
        """Test required fields."""
        # Missing title
        with pytest.raises(ValidationError):
            WebSearchResult(
                url="https://example.com",
                snippet="Test",
            )

        # Missing url
        with pytest.raises(ValidationError):
            WebSearchResult(
                title="Test",
                snippet="Test",
            )

        # Missing snippet
        with pytest.raises(ValidationError):
            WebSearchResult(
                title="Test",
                url="https://example.com",
            )
