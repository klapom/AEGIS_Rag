"""Web search client using DuckDuckGo.

Sprint 63 Feature 63.9: WebSearch Integration for Research Agent.

This module provides a client for executing web searches using DuckDuckGo
with async support, timeout handling, and error recovery.
"""

import asyncio
from datetime import datetime
from typing import Any

import structlog
from duckduckgo_search import DDGS

from src.core.config import settings
from src.domains.web_search.models import WebSearchRequest, WebSearchResult

logger = structlog.get_logger(__name__)


class WebSearchClient:
    """Web search client supporting DuckDuckGo.

    This client provides async web search capabilities with:
    - Timeout handling (default: 10s)
    - Error recovery and retry logic
    - Structured result formatting
    - Rate limiting awareness

    Example:
        >>> client = WebSearchClient()
        >>> results = await client.search("AI research 2025", max_results=5)
        >>> len(results) <= 5
        True
    """

    def __init__(self) -> None:
        """Initialize web search client.

        Note: AsyncDDGS instances are created per-request to avoid connection pooling issues.
        """
        logger.info("web_search_client_initialized")

    async def search(
        self,
        query: str,
        max_results: int = 5,
        region: str = "de-DE",
        safesearch: str = "moderate",
        timeout: int = 10,
    ) -> list[WebSearchResult]:
        """Execute web search with DuckDuckGo.

        Args:
            query: Search query string
            max_results: Maximum number of results (default: 5)
            region: Region code for localized results (default: de-DE)
            safesearch: SafeSearch setting (strict/moderate/off)
            timeout: Timeout in seconds (default: 10s)

        Returns:
            List of WebSearchResult objects

        Raises:
            asyncio.TimeoutError: If search exceeds timeout
            Exception: For network failures or API errors

        Example:
            >>> client = WebSearchClient()
            >>> results = await client.search("machine learning")
            >>> all(isinstance(r, WebSearchResult) for r in results)
            True
        """
        request = WebSearchRequest(
            query=query,
            max_results=max_results,
            region=region,
            safesearch=safesearch,
            timeout=timeout,
        )

        logger.info(
            "web_search_started",
            query=query,
            max_results=max_results,
            region=region,
            timeout=timeout,
        )

        try:
            # Execute search with timeout
            results = await asyncio.wait_for(
                self._execute_search(request),
                timeout=timeout,
            )

            logger.info(
                "web_search_completed",
                query=query,
                results_count=len(results),
            )

            return results

        except asyncio.TimeoutError:
            logger.error(
                "web_search_timeout",
                query=query,
                timeout=timeout,
            )
            # Return empty results on timeout (graceful degradation)
            return []

        except Exception as e:
            logger.error(
                "web_search_failed",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return empty results on error (graceful degradation)
            return []

    async def _execute_search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        """Execute DuckDuckGo search.

        Args:
            request: Web search request

        Returns:
            List of formatted WebSearchResult objects
        """
        results = []

        try:
            # Execute search in thread pool (DDGS is synchronous)
            def _sync_search():
                with DDGS() as ddgs:
                    # Execute text search
                    raw_results = list(
                        ddgs.text(
                            keywords=request.query,
                            region=request.region,
                            safesearch=request.safesearch,
                            max_results=request.max_results,
                        )
                    )
                    return raw_results

            # Run sync search in executor
            loop = asyncio.get_event_loop()
            raw_results = await loop.run_in_executor(None, _sync_search)

            # Format results
            for raw_result in raw_results:
                formatted = self._format_result(raw_result)
                if formatted:
                    results.append(formatted)

            logger.debug(
                "duckduckgo_search_completed",
                query=request.query,
                raw_count=len(raw_results),
                formatted_count=len(results),
            )

        except Exception as e:
            logger.error(
                "duckduckgo_search_failed",
                query=request.query,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        return results

    def _format_result(self, raw_result: dict[str, Any]) -> WebSearchResult | None:
        """Format raw DuckDuckGo result to WebSearchResult.

        Args:
            raw_result: Raw result dict from DuckDuckGo

        Returns:
            WebSearchResult or None if formatting fails

        DuckDuckGo Result Format:
            {
                'title': str,
                'href': str,
                'body': str,
                'published_date': str (optional, ISO format)
            }
        """
        try:
            # Parse published date if available
            published_date = None
            if "published_date" in raw_result and raw_result["published_date"]:
                try:
                    published_date = datetime.fromisoformat(
                        raw_result["published_date"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    # Skip invalid dates
                    pass

            return WebSearchResult(
                title=raw_result.get("title", "No Title"),
                url=raw_result.get("href", ""),
                snippet=raw_result.get("body", ""),
                published_date=published_date,
                source="duckduckgo",
                score=0.0,  # Score assigned during fusion
            )

        except Exception as e:
            logger.warning(
                "result_formatting_failed",
                error=str(e),
                raw_result=raw_result,
            )
            return None

    async def search_with_retry(
        self,
        query: str,
        max_results: int = 5,
        max_retries: int = 3,
    ) -> list[WebSearchResult]:
        """Execute web search with retry logic.

        Args:
            query: Search query
            max_results: Maximum results
            max_retries: Maximum retry attempts

        Returns:
            List of WebSearchResult objects

        Example:
            >>> client = WebSearchClient()
            >>> results = await client.search_with_retry("AI", max_retries=2)
            >>> isinstance(results, list)
            True
        """
        for attempt in range(max_retries):
            try:
                results = await self.search(query=query, max_results=max_results)
                if results:
                    return results

                logger.warning(
                    "web_search_no_results",
                    query=query,
                    attempt=attempt + 1,
                )

            except Exception as e:
                logger.error(
                    "web_search_retry_failed",
                    query=query,
                    attempt=attempt + 1,
                    error=str(e),
                )

                if attempt == max_retries - 1:
                    # Last attempt failed
                    return []

                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** attempt)

        return []


# Global client instance
_client: WebSearchClient | None = None


def get_web_search_client() -> WebSearchClient:
    """Get global web search client instance.

    Returns:
        WebSearchClient singleton instance

    Example:
        >>> client = get_web_search_client()
        >>> isinstance(client, WebSearchClient)
        True
    """
    global _client
    if _client is None:
        _client = WebSearchClient()
    return _client
