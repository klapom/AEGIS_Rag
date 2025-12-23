"""Pydantic models for web search requests and responses.

Sprint 63 Feature 63.9: WebSearch Integration for Research Agent.

This module defines type-safe models for web search operations using DuckDuckGo.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WebSearchRequest(BaseModel):
    """Request model for web search.

    Attributes:
        query: Search query string (optimized for web search)
        max_results: Maximum number of results to return (default: 5)
        region: Region code for search results (default: de-DE for German)
        safesearch: SafeSearch setting (strict, moderate, off)
        timeout: Timeout in seconds (default: 10s)

    Example:
        >>> request = WebSearchRequest(
        ...     query="latest AI research 2025",
        ...     max_results=10,
        ...     region="en-US"
        ... )
    """

    query: str = Field(..., min_length=1, description="Search query")
    max_results: int = Field(default=5, ge=1, le=20, description="Max results to return")
    region: str = Field(default="de-DE", description="Region code (e.g., de-DE, en-US)")
    safesearch: Literal["strict", "moderate", "off"] = Field(
        default="moderate", description="SafeSearch setting"
    )
    timeout: int = Field(default=10, ge=1, le=30, description="Timeout in seconds")


class WebSearchResult(BaseModel):
    """Result model for web search.

    Attributes:
        title: Title of the search result
        url: URL of the result page
        snippet: Text snippet/description from the page
        published_date: Publication date (if available)
        source: Source identifier (always 'duckduckgo')
        score: Relevance score (0.0-1.0, assigned during fusion)

    Example:
        >>> result = WebSearchResult(
        ...     title="AI Research Paper",
        ...     url="https://example.com/paper",
        ...     snippet="Latest advances in AI...",
        ...     source="duckduckgo"
        ... )
    """

    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: str = Field(..., description="Text snippet/description")
    published_date: datetime | None = Field(default=None, description="Publication date")
    source: str = Field(default="duckduckgo", description="Source identifier")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance score")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "title": "Latest AI Research 2025",
                "url": "https://example.com/ai-research",
                "snippet": "Comprehensive overview of AI advances in 2025...",
                "published_date": "2025-01-15T10:30:00Z",
                "source": "duckduckgo",
                "score": 0.85,
            }
        }
