"""Unit tests for AnswerGenerator with citation support.

Sprint 27 Feature 27.10: Inline Source Citations

NOTE: These tests are currently skipped as generate_with_citations()
      has not been implemented yet. Tests will be enabled when feature is complete.
"""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.answer_generator import AnswerGenerator
from src.components.llm_proxy.models import LLMResponse


# Skip all citation tests until feature is implemented
pytestmark = pytest.mark.skip(reason="Feature 27.10 (generate_with_citations) not yet implemented")


@pytest.fixture
def mock_llm_proxy():
    """Mock AegisLLMProxy for testing."""
    with patch("src.agents.answer_generator.get_aegis_llm_proxy") as mock:
        proxy = MagicMock()
        proxy.generate = AsyncMock()
        mock.return_value = proxy
        yield proxy


@pytest.fixture
def answer_generator(mock_llm_proxy):
    """Create AnswerGenerator instance with mocked proxy."""
    return AnswerGenerator(model_name="llama3.2:3b", temperature=0.0)


@pytest.fixture
def sample_contexts():
    """Sample context documents for testing."""
    return [
        {
            "text": (
                "AEGIS RAG is an agentic enterprise RAG system "
                "with vector search and graph reasoning."
            ),
            "source": "docs/CLAUDE.md",
            "title": "CLAUDE.md",
            "score": 0.95,
            "metadata": {"page": 1},
        },
        {
            "text": "The system uses LangGraph for multi-agent orchestration.",
            "source": "docs/architecture.md",
            "title": "Architecture Overview",
            "score": 0.88,
            "metadata": {"section": "orchestration"},
        },
    ]


class TestAnswerGeneratorCitations:
    """Test suite for citation generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_with_citations_basic(
        self, answer_generator, mock_llm_proxy, sample_contexts
    ):
        """Test basic citation generation."""
        # Mock LLM response with citations
        mock_response = LLMResponse(
            content="AEGIS RAG is an agentic enterprise system [1] using LangGraph [2].",
            provider="ollama",
            model="llama3.2:3b",
            cost_usd=0.0,
            latency_ms=150.0,
        )
        mock_llm_proxy.generate.return_value = mock_response

        # Generate answer with citations
        answer, citation_map = await answer_generator.generate_with_citations(
            query="What is AEGIS RAG?", contexts=sample_contexts
        )

        # Verify answer contains citations
        assert "[1]" in answer
        assert "[2]" in answer
        assert "AEGIS RAG" in answer

        # Verify citation map structure
        assert len(citation_map) == 2
        assert 1 in citation_map
        assert 2 in citation_map

        # Verify citation map content
        assert citation_map[1]["source"] == "docs/CLAUDE.md"
        assert citation_map[1]["title"] == "CLAUDE.md"
        assert citation_map[1]["score"] == 0.95

        assert citation_map[2]["source"] == "docs/architecture.md"
        assert citation_map[2]["title"] == "Architecture Overview"
        assert citation_map[2]["score"] == 0.88

    @pytest.mark.asyncio
    async def test_generate_with_citations_no_contexts(self, answer_generator, mock_llm_proxy):
        """Test citation generation with no contexts."""
        # Generate with empty contexts
        answer, citation_map = await answer_generator.generate_with_citations(
            query="What is AEGIS RAG?", contexts=[]
        )

        # Should return no-context answer
        assert "don't have enough information" in answer
        assert citation_map == {}

        # LLM should not be called
        mock_llm_proxy.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_with_citations_multiple_citations(
        self, answer_generator, mock_llm_proxy, sample_contexts
    ):
        """Test answer with multiple citations for same sentence."""
        # Mock LLM response with multiple citations
        mock_response = LLMResponse(
            content="AEGIS RAG is an agentic system [1][2] with advanced capabilities.",
            provider="ollama",
            model="llama3.2:3b",
            cost_usd=0.0,
            latency_ms=200.0,
        )
        mock_llm_proxy.generate.return_value = mock_response

        answer, citation_map = await answer_generator.generate_with_citations(
            query="What is AEGIS RAG?", contexts=sample_contexts
        )

        # Verify multiple citations exist
        assert "[1][2]" in answer or ("[1]" in answer and "[2]" in answer)

        # Verify citation map has both sources
        assert len(citation_map) == 2

    @pytest.mark.asyncio
    async def test_generate_with_citations_text_truncation(self, answer_generator, mock_llm_proxy):
        """Test that citation map text is truncated to 500 chars."""
        # Create context with long text
        long_context = [
            {
                "text": "A" * 1000,  # 1000 character text
                "source": "long_doc.pdf",
                "title": "Long Document",
                "score": 0.9,
                "metadata": {},
            }
        ]

        mock_response = LLMResponse(
            content="This is a summary [1].",
            provider="ollama",
            model="llama3.2:3b",
            cost_usd=0.0,
            latency_ms=100.0,
        )
        mock_llm_proxy.generate.return_value = mock_response

        answer, citation_map = await answer_generator.generate_with_citations(
            query="Test query", contexts=long_context
        )

        # Verify text is truncated to 500 chars
        assert len(citation_map[1]["text"]) == 500

    @pytest.mark.asyncio
    async def test_generate_with_citations_max_10_sources(self, answer_generator, mock_llm_proxy):
        """Test that citation map limits to 10 sources."""
        # Create 15 contexts
        many_contexts = [
            {
                "text": f"Context {i}",
                "source": f"doc{i}.pdf",
                "title": f"Doc {i}",
                "score": 0.9,
                "metadata": {},
            }
            for i in range(1, 16)
        ]

        mock_response = LLMResponse(
            content="Summary with sources.",
            provider="ollama",
            model="llama3.2:3b",
            cost_usd=0.0,
            latency_ms=100.0,
        )
        mock_llm_proxy.generate.return_value = mock_response

        answer, citation_map = await answer_generator.generate_with_citations(
            query="Test query", contexts=many_contexts
        )

        # Verify only 10 sources in citation map
        assert len(citation_map) == 10

    @pytest.mark.asyncio
    async def test_generate_with_citations_llm_failure_fallback(
        self, answer_generator, mock_llm_proxy, sample_contexts
    ):
        """Test fallback behavior when LLM generation fails."""
        # Mock LLM to raise exception
        mock_llm_proxy.generate.side_effect = Exception("LLM service unavailable")

        answer, citation_map = await answer_generator.generate_with_citations(
            query="What is AEGIS RAG?", contexts=sample_contexts
        )

        # Should return fallback answer
        assert "Based on the retrieved documents:" in answer

        # Citation map should still be populated (even though answer has no citations)
        assert len(citation_map) == 2

    @pytest.mark.asyncio
    async def test_citation_extraction_from_answer(
        self, answer_generator, mock_llm_proxy, sample_contexts
    ):
        """Test that cited sources are extracted correctly for logging."""
        mock_response = LLMResponse(
            content="AEGIS RAG is a system [1] with features [3]. It does not use [2].",
            provider="ollama",
            model="llama3.2:3b",
            cost_usd=0.0,
            latency_ms=100.0,
        )
        mock_llm_proxy.generate.return_value = mock_response

        answer, citation_map = await answer_generator.generate_with_citations(
            query="Test query", contexts=sample_contexts
        )

        # Extract citations from answer
        cited_sources = set(re.findall(r"\[(\d+)\]", answer))

        # Verify citations are extracted
        assert "1" in cited_sources
        assert "3" in cited_sources

    @pytest.mark.asyncio
    async def test_citation_map_metadata_fields(
        self, answer_generator, mock_llm_proxy, sample_contexts
    ):
        """Test that citation map includes all required metadata fields."""
        mock_response = LLMResponse(
            content="Test answer [1].",
            provider="ollama",
            model="llama3.2:3b",
            cost_usd=0.0,
            latency_ms=100.0,
        )
        mock_llm_proxy.generate.return_value = mock_response

        answer, citation_map = await answer_generator.generate_with_citations(
            query="Test query", contexts=sample_contexts
        )

        # Verify all required fields in citation map
        citation = citation_map[1]
        assert "text" in citation
        assert "source" in citation
        assert "title" in citation
        assert "score" in citation
        assert "metadata" in citation

        # Verify values match source context
        assert citation["source"] == sample_contexts[0]["source"]
        assert citation["title"] == sample_contexts[0]["title"]
        assert citation["score"] == sample_contexts[0]["score"]
        assert citation["metadata"] == sample_contexts[0]["metadata"]


class TestAnswerGeneratorPrompt:
    """Test prompt formatting for citations."""

    @pytest.mark.asyncio
    async def test_prompt_includes_source_ids(
        self, answer_generator, mock_llm_proxy, sample_contexts
    ):
        """Test that prompt includes [Source N] markers."""
        mock_response = LLMResponse(
            content="Test answer.",
            provider="ollama",
            model="llama3.2:3b",
            cost_usd=0.0,
            latency_ms=100.0,
        )
        mock_llm_proxy.generate.return_value = mock_response

        await answer_generator.generate_with_citations(query="Test query", contexts=sample_contexts)

        # Verify LLM was called
        assert mock_llm_proxy.generate.called

        # Get the prompt from the call
        call_args = mock_llm_proxy.generate.call_args
        task = call_args[0][0]  # First positional argument (LLMTask)

        # Verify prompt includes source IDs
        assert "[Source 1]:" in task.prompt
        assert "[Source 2]:" in task.prompt
        assert sample_contexts[0]["text"] in task.prompt
        assert sample_contexts[1]["text"] in task.prompt
