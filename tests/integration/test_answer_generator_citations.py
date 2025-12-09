"""Integration tests for AnswerGenerator citation functionality.

Sprint 27 Feature 27.10: Inline Source Citations

Integration tests that verify citation generation works end-to-end
with real LLM proxy (mocked responses).
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.answer_generator import AnswerGenerator
from src.components.llm_proxy.models import LLMResponse


@pytest.mark.asyncio
@pytest.mark.integration
async def test_citations_e2e_with_mocked_llm():
    """Test full citation flow with mocked LLM responses."""
    # Create answer generator
    generator = AnswerGenerator(model_name="llama3.2:3b", temperature=0.0)

    # Sample contexts
    contexts = [
        {
            "text": "AEGIS RAG is an agentic enterprise graph intelligence system.",
            "source": "docs/CLAUDE.md",
            "title": "CLAUDE Documentation",
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

    # Mock LLM response with citations
    mock_response = LLMResponse(
        content="AEGIS RAG is an agentic system [1] that uses LangGraph [2] for orchestration.",
        provider="ollama",
        model="llama3.2:3b",
        cost_usd=0.0,
        latency_ms=200.0,
        tokens_used=60,
    )

    with patch.object(generator.proxy, "generate", new=AsyncMock(return_value=mock_response)):
        # Generate answer with citations
        answer, citation_map = await generator.generate_with_citations(
            query="What is AEGIS RAG and what does it use?", contexts=contexts
        )

    # Verify answer structure
    assert "[1]" in answer
    assert "[2]" in answer
    assert "AEGIS RAG" in answer
    assert "LangGraph" in answer

    # Verify citation map
    assert len(citation_map) == 2

    # Verify citation 1
    assert citation_map[1]["source"] == "docs/CLAUDE.md"
    assert citation_map[1]["title"] == "CLAUDE Documentation"
    assert citation_map[1]["score"] == 0.95
    assert "agentic enterprise" in citation_map[1]["text"]

    # Verify citation 2
    assert citation_map[2]["source"] == "docs/architecture.md"
    assert citation_map[2]["title"] == "Architecture Overview"
    assert citation_map[2]["score"] == 0.88
    assert "LangGraph" in citation_map[2]["text"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_citations_empty_contexts():
    """Test citation generation with no contexts returns fallback."""
    generator = AnswerGenerator(model_name="llama3.2:3b", temperature=0.0)

    answer, citation_map = await generator.generate_with_citations(
        query="What is AEGIS RAG?", contexts=[]
    )

    # Should return no-context answer
    assert "don't have enough information" in answer
    assert citation_map == {}


@pytest.mark.asyncio
@pytest.mark.integration
async def test_citations_llm_failure_returns_fallback():
    """Test citation generation falls back gracefully on LLM errors."""
    generator = AnswerGenerator(model_name="llama3.2:3b", temperature=0.0)

    contexts = [
        {
            "text": "AEGIS RAG is a system.",
            "source": "doc.md",
            "title": "Document",
            "score": 0.9,
            "metadata": {},
        }
    ]

    # Mock LLM to raise exception
    with patch.object(
        generator.proxy, "generate", new=AsyncMock(side_effect=Exception("LLM unavailable"))
    ):
        answer, citation_map = await generator.generate_with_citations(
            query="What is AEGIS?", contexts=contexts
        )

    # Should return fallback answer
    assert "Based on the retrieved documents:" in answer

    # Citation map should still exist
    assert len(citation_map) == 1
    assert citation_map[1]["source"] == "doc.md"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_citations_text_truncation():
    """Test that citation map text is truncated to 500 characters."""
    generator = AnswerGenerator(model_name="llama3.2:3b", temperature=0.0)

    # Create context with very long text
    long_text = "A" * 1000
    contexts = [
        {
            "text": long_text,
            "source": "long.pdf",
            "title": "Long Document",
            "score": 0.9,
            "metadata": {},
        }
    ]

    mock_response = LLMResponse(
        content="Summary [1].",
        provider="ollama",
        model="llama3.2:3b",
        cost_usd=0.0,
        latency_ms=100.0,
        tokens_used=20,
    )

    with patch.object(generator.proxy, "generate", new=AsyncMock(return_value=mock_response)):
        answer, citation_map = await generator.generate_with_citations(
            query="Summarize", contexts=contexts
        )

    # Verify text is truncated to exactly 500 chars
    assert len(citation_map[1]["text"]) == 500
    assert citation_map[1]["text"] == "A" * 500


@pytest.mark.asyncio
@pytest.mark.integration
async def test_citations_max_10_sources():
    """Test that citation map limits to top 10 sources."""
    generator = AnswerGenerator(model_name="llama3.2:3b", temperature=0.0)

    # Create 15 contexts
    contexts = [
        {
            "text": f"Context {i}",
            "source": f"doc{i}.pdf",
            "title": f"Document {i}",
            "score": 0.9,
            "metadata": {},
        }
        for i in range(1, 16)
    ]

    mock_response = LLMResponse(
        content="Summary from sources.",
        provider="ollama",
        model="llama3.2:3b",
        cost_usd=0.0,
        latency_ms=150.0,
        tokens_used=25,
    )

    with patch.object(generator.proxy, "generate", new=AsyncMock(return_value=mock_response)):
        answer, citation_map = await generator.generate_with_citations(
            query="Summarize", contexts=contexts
        )

    # Should limit to 10 sources
    assert len(citation_map) == 10

    # Verify it's the first 10
    for i in range(1, 11):
        assert i in citation_map
        assert citation_map[i]["source"] == f"doc{i}.pdf"

    # 11-15 should not be in map
    assert 11 not in citation_map
    assert 15 not in citation_map
