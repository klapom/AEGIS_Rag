"""Unit tests for result fusion.

Sprint 63 Feature 63.9: WebSearch Integration for Research Agent.

Tests cover:
- Result fusion across vector/graph/web sources
- Deduplication logic
- Weighted scoring
- Diversity calculation
- Query optimization
"""

import pytest

from src.domains.web_search.fusion import (
    calculate_diversity_score,
    deduplicate_fused_results,
    fuse_results,
    optimize_web_query,
)
from src.domains.web_search.models import WebSearchResult


@pytest.fixture
def vector_results():
    """Sample vector search results."""
    return [
        {
            "text": "Vector result 1",
            "score": 0.9,
            "source": "vector",
            "metadata": {},
        },
        {
            "text": "Vector result 2",
            "score": 0.8,
            "source": "vector",
            "metadata": {},
        },
    ]


@pytest.fixture
def graph_results():
    """Sample graph search results."""
    return [
        {
            "text": "Graph result 1",
            "score": 0.85,
            "source": "graph",
            "entities": ["Entity1"],
            "metadata": {},
        },
    ]


@pytest.fixture
def web_results():
    """Sample web search results."""
    return [
        WebSearchResult(
            title="Web Result 1",
            url="https://example.com/1",
            snippet="Web content 1",
            score=0.75,
        ),
        WebSearchResult(
            title="Web Result 2",
            url="https://example.com/2",
            snippet="Web content 2",
            score=0.70,
        ),
    ]


class TestFuseResults:
    """Test result fusion."""

    def test_fuse_all_sources(self, vector_results, graph_results, web_results):
        """Test fusion with all sources."""
        results = fuse_results(
            vector_results=vector_results,
            graph_results=graph_results,
            web_results=web_results,
            top_k=10,
        )

        # Should have results from all sources
        assert len(results) == 5  # 2 vector + 1 graph + 2 web

        # Check weighted scores are calculated
        for result in results:
            assert "weighted_score" in result
            assert result["weighted_score"] > 0

        # Results should be sorted by weighted_score
        scores = [r["weighted_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_fuse_vector_only(self, vector_results):
        """Test fusion with vector results only."""
        results = fuse_results(
            vector_results=vector_results,
            graph_results=[],
            web_results=[],
            top_k=10,
        )

        assert len(results) == 2
        assert all(r["fusion_source"] == "vector" for r in results)

    def test_fuse_web_only(self, web_results):
        """Test fusion with web results only."""
        results = fuse_results(
            vector_results=[],
            graph_results=[],
            web_results=web_results,
            top_k=10,
        )

        assert len(results) == 2
        assert all(r["fusion_source"] == "web" for r in results)

    def test_fuse_top_k_limit(self, vector_results, graph_results, web_results):
        """Test top_k limit."""
        results = fuse_results(
            vector_results=vector_results,
            graph_results=graph_results,
            web_results=web_results,
            top_k=3,
        )

        # Should return only top 3 results
        assert len(results) == 3

    def test_weighted_scores(self, vector_results, graph_results, web_results):
        """Test weighted score calculation."""
        results = fuse_results(
            vector_results=vector_results,
            graph_results=graph_results,
            web_results=web_results,
            top_k=10,
        )

        # Vector results should have highest weight (0.7)
        vector_result = next(r for r in results if r["fusion_source"] == "vector")
        assert vector_result["weighted_score"] == vector_result["score"] * 0.7

        # Graph results should have medium weight (0.2)
        graph_result = next(r for r in results if r["fusion_source"] == "graph")
        assert graph_result["weighted_score"] == graph_result["score"] * 0.2

        # Web results should have lowest weight (0.1)
        web_result = next(r for r in results if r["fusion_source"] == "web")
        assert web_result["weighted_score"] == web_result["score"] * 0.1

    def test_web_result_conversion(self, web_results):
        """Test WebSearchResult to dict conversion."""
        results = fuse_results(
            vector_results=[],
            graph_results=[],
            web_results=web_results,
            top_k=10,
        )

        # Check web result fields are properly converted
        web_result = results[0]
        assert web_result["title"] == "Web Result 1"
        assert web_result["url"] == "https://example.com/1"
        assert web_result["text"] == "Web content 1"
        assert web_result["source"] == "web"


class TestDeduplicateFusedResults:
    """Test deduplication logic."""

    def test_deduplicate_by_url(self):
        """Test deduplication by URL."""
        results = [
            {
                "text": "Result 1",
                "url": "https://example.com/same",
                "weighted_score": 0.9,
            },
            {
                "text": "Result 2",
                "url": "https://example.com/same",
                "weighted_score": 0.8,
            },
            {
                "text": "Result 3",
                "url": "https://example.com/different",
                "weighted_score": 0.7,
            },
        ]

        unique = deduplicate_fused_results(results)

        # Should keep only first occurrence of duplicate URL
        assert len(unique) == 2
        assert unique[0]["url"] == "https://example.com/same"
        assert unique[1]["url"] == "https://example.com/different"

    def test_deduplicate_by_text(self):
        """Test deduplication by text content."""
        results = [
            {
                "text": "This is the same content for testing",
                "weighted_score": 0.9,
            },
            {
                "text": "This is the same content for testing",
                "weighted_score": 0.8,
            },
            {
                "text": "This is different content",
                "weighted_score": 0.7,
            },
        ]

        unique = deduplicate_fused_results(results)

        # Should keep only first occurrence of duplicate text
        assert len(unique) == 2

    def test_deduplicate_no_duplicates(self):
        """Test deduplication with no duplicates."""
        results = [
            {
                "text": "Result 1",
                "url": "https://example.com/1",
                "weighted_score": 0.9,
            },
            {
                "text": "Result 2",
                "url": "https://example.com/2",
                "weighted_score": 0.8,
            },
        ]

        unique = deduplicate_fused_results(results)

        # All results should be kept
        assert len(unique) == 2

    def test_deduplicate_empty_list(self):
        """Test deduplication with empty list."""
        results = []
        unique = deduplicate_fused_results(results)
        assert len(unique) == 0


class TestCalculateDiversityScore:
    """Test diversity score calculation."""

    def test_perfect_diversity(self):
        """Test perfect balance across sources."""
        results = [
            {"fusion_source": "vector"},
            {"fusion_source": "graph"},
            {"fusion_source": "web"},
        ]

        score = calculate_diversity_score(results)

        # Perfect balance should give high score
        assert 0.8 <= score <= 1.0

    def test_single_source(self):
        """Test single source only."""
        results = [
            {"fusion_source": "vector"},
            {"fusion_source": "vector"},
            {"fusion_source": "vector"},
        ]

        score = calculate_diversity_score(results)

        # Single source should give lower score
        assert 0.0 <= score < 0.8

    def test_empty_results(self):
        """Test empty results."""
        score = calculate_diversity_score([])
        assert score == 0.0

    def test_diverse_distribution(self):
        """Test realistic distribution."""
        results = [
            {"fusion_source": "vector"},
            {"fusion_source": "vector"},
            {"fusion_source": "vector"},
            {"fusion_source": "graph"},
            {"fusion_source": "web"},
        ]

        score = calculate_diversity_score(results)

        # Mixed sources should give medium-high score
        assert 0.5 <= score <= 1.0


class TestOptimizeWebQuery:
    """Test web query optimization."""

    def test_remove_conversational_elements(self):
        """Test removal of conversational phrases."""
        query = "Tell me about AI research"
        optimized = optimize_web_query(query)

        assert "tell me about" not in optimized.lower()
        assert "ai research" in optimized.lower()

    def test_remove_question_words(self):
        """Test removal of question words."""
        query = "What is machine learning?"
        optimized = optimize_web_query(query)

        assert "what is" not in optimized.lower()
        assert "machine learning" in optimized.lower()

    def test_add_year_context(self):
        """Test addition of year context."""
        query = "latest AI research"
        optimized = optimize_web_query(query)

        # Should add 2025 for recency
        assert "2025" in optimized

    def test_preserve_existing_year(self):
        """Test preservation of existing year."""
        query = "AI research 2024"
        optimized = optimize_web_query(query)

        # Should preserve 2024
        assert "2024" in optimized
        assert "2025" not in optimized

    def test_multiple_conversational_elements(self):
        """Test removal of multiple conversational elements."""
        query = "Can you please tell me about machine learning"
        optimized = optimize_web_query(query)

        assert "can you" not in optimized.lower()
        assert "please" not in optimized.lower()
        assert "tell me about" not in optimized.lower()
        assert "machine learning" in optimized.lower()

    def test_strip_whitespace(self):
        """Test whitespace stripping."""
        query = "  AI research  "
        optimized = optimize_web_query(query)

        # Should be trimmed
        assert optimized == optimized.strip()
        assert "ai research" in optimized.lower()
