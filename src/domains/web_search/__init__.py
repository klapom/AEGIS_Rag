"""Web Search Domain.

Sprint 63 Feature 63.9: WebSearch Integration for Research Agent.

This domain provides web search capabilities using DuckDuckGo to augment
internal knowledge with external information.

Components:
    - client: WebSearchClient for executing DuckDuckGo searches
    - models: Pydantic models for search requests/responses
    - fusion: Result fusion logic for combining web/vector/graph results
"""

from src.domains.web_search.client import WebSearchClient
from src.domains.web_search.models import WebSearchRequest, WebSearchResult

__all__ = [
    "WebSearchClient",
    "WebSearchRequest",
    "WebSearchResult",
]
