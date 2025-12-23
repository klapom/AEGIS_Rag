"""Unit tests for research synthesizer.

Sprint 62 Feature 62.10: Research Endpoint Backend
"""

import pytest

from src.agents.research.synthesizer import (
    create_structured_summary,
    extract_citations,
    extract_key_points,
    format_results_for_synthesis,
    synthesize_findings,
)


@pytest.fixture
def sample_results():
    """Sample search results for testing."""
    return [
        {
            "text": "Machine learning is a subset of artificial intelligence.",
            "score": 0.9,
            "source": "vector",
            "metadata": {"doc_id": "1"},
        },
        {
            "text": "Deep learning uses neural networks with multiple layers.",
            "score": 0.8,
            "source": "graph",
            "entities": ["Deep Learning", "Neural Networks"],
            "relationships": ["uses"],
            "metadata": {"doc_id": "2"},
        },
        {
            "text": "AI systems can learn from data without explicit programming.",
            "score": 0.85,
            "source": "vector",
            "metadata": {"doc_id": "3"},
        },
    ]


class TestFormatResultsForSynthesis:
    """Test result formatting for synthesis."""

    def test_format_results_basic(self, sample_results):
        """Test basic result formatting."""
        formatted = format_results_for_synthesis(sample_results, max_length=5000)

        assert "Vector #1" in formatted
        assert "Graph #2" in formatted
        assert "Score: 0.90" in formatted
        assert "Machine learning" in formatted

    def test_format_results_respects_max_length(self, sample_results):
        """Test that max_length is respected."""
        formatted = format_results_for_synthesis(sample_results, max_length=200)

        assert len(formatted) <= 300  # Some overhead for formatting

    def test_format_results_truncates_long_text(self):
        """Test truncation of long text."""
        results = [
            {
                "text": "A" * 1000,
                "score": 0.9,
                "source": "vector",
            }
        ]

        formatted = format_results_for_synthesis(results, max_length=200)

        assert "..." in formatted

    def test_format_results_empty(self):
        """Test formatting empty results."""
        formatted = format_results_for_synthesis([])

        assert formatted == ""

    def test_format_results_skips_empty_text(self):
        """Test that results with empty text are skipped."""
        results = [
            {"text": "", "score": 0.9, "source": "vector"},
            {"text": "Valid content", "score": 0.8, "source": "vector"},
        ]

        formatted = format_results_for_synthesis(results)

        assert "Valid content" in formatted
        assert formatted.count("Vector #") == 1


@pytest.mark.asyncio
class TestSynthesizeFindings:
    """Test findings synthesis."""

    async def test_synthesize_findings_basic(self, sample_results):
        """Test basic synthesis."""
        from unittest.mock import AsyncMock, patch

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(
            return_value="AI is a field of computer science focused on creating intelligent machines."
        )

        with patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        ):
            synthesis = await synthesize_findings("What is AI?", sample_results)

            assert len(synthesis) > 0
            assert "AI" in synthesis or "artificial intelligence" in synthesis.lower()
            mock_llm.generate.assert_called_once()

    async def test_synthesize_findings_empty_results(self):
        """Test synthesis with no results."""
        synthesis = await synthesize_findings("What is AI?", [])

        assert "No information found" in synthesis

    async def test_synthesize_findings_respects_max_context(self):
        """Test that max_context_length is respected."""
        from unittest.mock import AsyncMock, patch

        # Create many results
        results = [{"text": "A" * 100, "score": 0.9, "source": "vector"} for _ in range(100)]

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="Synthesis")

        with patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        ):
            await synthesize_findings("Query", results, max_context_length=500)

            # Check that prompt doesn't exceed limit
            call_args = mock_llm.generate.call_args
            prompt = call_args.kwargs.get("prompt", "")

            # Context should be limited
            assert len(prompt) < 10000  # Reasonable upper bound

    async def test_synthesize_findings_fallback_on_error(self, sample_results):
        """Test fallback synthesis on LLM error."""
        from unittest.mock import AsyncMock, patch

        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = Exception("LLM failed")

        with patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        ):
            synthesis = await synthesize_findings("What is AI?", sample_results)

            # Should return fallback synthesis
            assert "Information found for" in synthesis
            assert "Machine learning" in synthesis

    async def test_synthesize_findings_temperature(self, sample_results):
        """Test that synthesis uses correct temperature."""
        from unittest.mock import AsyncMock, patch

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="Synthesis")

        with patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        ):
            await synthesize_findings("Query", sample_results)

            call_args = mock_llm.generate.call_args
            assert call_args.kwargs.get("temperature") == 0.3  # Low for accuracy


@pytest.mark.asyncio
class TestCreateStructuredSummary:
    """Test structured summary creation."""

    async def test_create_structured_summary(self, sample_results):
        """Test structured summary creation."""
        from unittest.mock import AsyncMock, patch

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="AI is about creating intelligent machines.")

        with patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        ):
            summary = await create_structured_summary("What is AI?", sample_results)

            assert summary["query"] == "What is AI?"
            assert "synthesis" in summary
            assert "sources" in summary
            assert summary["num_results"] == 3
            assert len(summary["key_findings"]) > 0

    async def test_create_structured_summary_extracts_entities(self):
        """Test that entities are extracted from graph results."""
        from unittest.mock import AsyncMock, patch

        results = [
            {
                "text": "Graph result",
                "score": 0.9,
                "source": "graph",
                "entities": ["Entity1", "Entity2"],
            }
        ]

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="Summary")

        with patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        ):
            summary = await create_structured_summary("Query", results)

            assert "Entity1" in summary["entities"]
            assert "Entity2" in summary["entities"]

    async def test_create_structured_summary_limits_findings(self):
        """Test that key findings are limited."""
        from unittest.mock import AsyncMock, patch

        results = [
            {"text": f"Result {i}", "score": 0.9 - i * 0.1, "source": "vector"} for i in range(10)
        ]

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="Summary")

        with patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        ):
            summary = await create_structured_summary("Query", results)

            # Should limit to top 5 findings
            assert len(summary["key_findings"]) <= 5


class TestExtractCitations:
    """Test citation extraction."""

    def test_extract_citations_basic(self):
        """Test basic citation extraction."""
        synthesis = (
            "According to [Source #1], AI is important. [Source #2] shows that ML is useful."
        )

        citations = extract_citations(synthesis)

        assert citations == [1, 2]

    def test_extract_citations_multiple_same_source(self):
        """Test deduplication of citations."""
        synthesis = "[Source #1] says this. Later, [Source #1] says that."

        citations = extract_citations(synthesis)

        assert citations == [1]

    def test_extract_citations_none_found(self):
        """Test when no citations are found."""
        synthesis = "This text has no citations."

        citations = extract_citations(synthesis)

        assert citations == []

    def test_extract_citations_sorted(self):
        """Test that citations are sorted."""
        synthesis = "[Source #3] and [Source #1] and [Source #2]"

        citations = extract_citations(synthesis)

        assert citations == [1, 2, 3]


class TestExtractKeyPoints:
    """Test key point extraction."""

    def test_extract_key_points_basic(self):
        """Test basic key point extraction."""
        text = """First, machine learning is important. Second, it uses data.
        Third, it enables automation. Additionally, it's widely used."""

        points = extract_key_points(text, max_points=3)

        assert len(points) <= 3
        assert any("First" in point or "machine learning" in point for point in points)

    def test_extract_key_points_with_indicators(self):
        """Test extraction with key indicators."""
        text = "This is critical for AI. It is primarily used for automation."

        points = extract_key_points(text, max_points=5)

        assert len(points) == 2
        assert any("critical" in point for point in points)
        assert any("primarily" in point for point in points)

    def test_extract_key_points_empty(self):
        """Test extraction from empty text."""
        points = extract_key_points("")

        assert points == []

    def test_extract_key_points_respects_max(self):
        """Test that max_points is respected."""
        text = ". ".join([f"Point {i} is important" for i in range(10)])

        points = extract_key_points(text, max_points=3)

        assert len(points) <= 3
