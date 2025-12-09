"""Tests for LLM-based answer generation.

Sprint 11: Feature 11.1 - LLM-Based Answer Generation
"""

import pytest

from src.agents.answer_generator import AnswerGenerator


@pytest.mark.asyncio
async def test_answer_generation_with_context():
    """Test answer generation with valid context."""
    generator = AnswerGenerator()

    contexts = [
        {
            "text": "AEGIS RAG uses LangGraph for multi-agent orchestration.",
            "source": "README.md",
        },
        {
            "text": "LangGraph provides state management and conditional routing.",
            "source": "docs/architecture.md",
        },
    ]

    answer = await generator.generate_answer(
        query="What does AEGIS RAG use for orchestration?",
        contexts=contexts,
    )

    assert answer
    assert len(answer) > 50
    assert "LangGraph" in answer or "langgraph" in answer.lower()


@pytest.mark.asyncio
async def test_answer_generation_no_context():
    """Test answer generation with no context."""
    generator = AnswerGenerator()

    answer = await generator.generate_answer(
        query="What is the meaning of life?",
        contexts=[],
    )

    assert "don't have enough information" in answer.lower()


@pytest.mark.asyncio
async def test_multi_hop_reasoning():
    """Test multi-hop reasoning mode."""
    generator = AnswerGenerator()

    contexts = [
        {"text": "AEGIS RAG uses LangGraph.", "source": "doc1.md"},
        {"text": "LangGraph was created by LangChain.", "source": "doc2.md"},
    ]

    answer = await generator.generate_answer(
        query="Who created the orchestration framework used by AEGIS RAG?",
        contexts=contexts,
        mode="multi_hop",
    )

    assert answer
    assert "LangChain" in answer or "langchain" in answer.lower()


@pytest.mark.asyncio
async def test_format_contexts():
    """Test context formatting for prompts."""
    generator = AnswerGenerator()

    contexts = [
        {"text": "First document text", "source": "doc1.txt"},
        {"text": "Second document text", "source": "doc2.txt"},
    ]

    formatted = generator._format_contexts(contexts)

    assert "[Context 1 - Source: doc1.txt]" in formatted
    assert "First document text" in formatted
    assert "[Context 2 - Source: doc2.txt]" in formatted
    assert "Second document text" in formatted


@pytest.mark.asyncio
async def test_singleton_pattern():
    """Test that get_answer_generator returns singleton instance."""
    from src.agents.answer_generator import get_answer_generator

    gen1 = get_answer_generator()
    gen2 = get_answer_generator()

    assert gen1 is gen2


@pytest.mark.asyncio
async def test_context_limit():
    """Test that only top 5 contexts are used."""
    generator = AnswerGenerator()

    # Create 10 contexts
    contexts = [{"text": f"Context {i}", "source": f"doc{i}.txt"} for i in range(10)]

    formatted = generator._format_contexts(contexts)

    # Should only have Context 1-5
    assert "[Context 1 -" in formatted
    assert "[Context 5 -" in formatted
    assert "[Context 6 -" not in formatted


@pytest.mark.asyncio
async def test_answer_with_missing_source():
    """Test answer generation when context is missing source field."""
    generator = AnswerGenerator()

    contexts = [
        {"text": "Document without source field"},  # Missing 'source' key
    ]

    answer = await generator.generate_answer(
        query="Test query",
        contexts=contexts,
    )

    # Should not crash, should use "Unknown" as source
    assert answer
    assert len(answer) > 0
