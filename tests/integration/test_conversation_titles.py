"""Integration tests for auto-generated conversation titles.

Sprint 35 Feature 35.4: Auto-Generated Conversation Titles

Tests:
1. Title generation with AegisLLMProxy
2. Title storage in conversation metadata
3. Title update endpoint
4. Title retrieval via GET /sessions/{session_id}

Note: These tests require real LLM responses to validate title generation quality.
Run locally with Ollama, skipped in CI (marked with @pytest.mark.requires_llm).
"""

import pytest

from src.api.v1.title_generator import generate_conversation_title

# Mark all tests in this module as requiring real LLM
pytestmark = pytest.mark.requires_llm


@pytest.mark.asyncio
async def test_generate_conversation_title_basic():
    """Test that title generation works with basic Q&A."""
    title = await generate_conversation_title(
        query="What is retrieval augmented generation?",
        answer="RAG is a technique that combines retrieval with generation..."
    )

    assert title is not None
    assert len(title) > 0
    assert len(title.split()) <= 7  # Max 7 words (5 + ... if truncated)
    assert title != "New Conversation"  # Should generate something meaningful


@pytest.mark.asyncio
async def test_generate_conversation_title_max_length():
    """Test that title respects max_length constraint."""
    title = await generate_conversation_title(
        query="What is retrieval augmented generation?",
        answer="RAG is a technique...",
        max_length=3
    )

    assert title is not None
    # Should be short (either 3 words or truncated with ...)
    words = title.replace("...", "").split()
    assert len(words) <= 5  # 3 words + potential truncation


@pytest.mark.asyncio
async def test_generate_conversation_title_fallback():
    """Test that fallback works when LLM fails."""
    # Simulate error by using empty strings (will trigger fallback)
    title = await generate_conversation_title(
        query="What is RAG?",
        answer=""  # Empty answer should still generate fallback
    )

    assert title is not None
    assert title == "What is RAG?" or "RAG" in title  # Fallback uses first few words


@pytest.mark.asyncio
async def test_generate_conversation_title_long_inputs():
    """Test title generation with very long inputs."""
    long_query = "A" * 500  # Exceeds 200 char truncation
    long_answer = "B" * 1000  # Exceeds 300 char truncation

    title = await generate_conversation_title(
        query=long_query,
        answer=long_answer
    )

    assert title is not None
    assert len(title) > 0
    # Should still generate reasonable title despite long inputs
