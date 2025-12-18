"""Unit tests for follow-up question generation.

Sprint 27 Feature 27.5: Follow-up Question Suggestions
Sprint 52 Feature 52.3: Async Follow-up Questions (TD-043)

Tests the generate_followup_questions function for:
- Successful question generation
- JSON parsing and validation
- Error handling (invalid JSON, LLM failures)
- Edge cases (empty sources, long answers)

Tests for Sprint 52.3:
- Redis context storage and retrieval
- Async question generation from stored context
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.followup_generator import (
    generate_followup_questions,
    generate_followup_questions_async,
    retrieve_conversation_context,
    store_conversation_context,
)
from src.components.llm_proxy.models import LLMResponse


@pytest.mark.asyncio
async def test_generate_followup_questions_success():
    """Test successful follow-up question generation."""
    query = "What is AEGIS RAG?"
    answer = "AEGIS RAG is an agentic RAG system with vector search and graph reasoning."
    sources = [
        {"text": "AEGIS RAG uses LangGraph for orchestration..."},
        {"text": "The system supports hybrid search combining vector and keyword..."},
    ]

    # Mock LLM response with valid JSON
    mock_questions = [
        "How does LangGraph orchestrate the agents?",
        "What is hybrid search and how does it work?",
        "Can you explain the graph reasoning component?",
    ]

    mock_response = LLMResponse(
        content=json.dumps(mock_questions),
        provider="local_ollama",
        model="llama3.2:3b",
        prompt_tokens=150,
        completion_tokens=80,
        total_tokens=230,
        tokens_used=230,
        cost_usd=0.0,
        latency_ms=450.0,
    )

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        mock_get_proxy.return_value = mock_proxy

        questions = await generate_followup_questions(query, answer, sources)

        # Verify results
        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)
        assert all(len(q) > 10 for q in questions)
        assert questions == mock_questions

        # Verify LLM was called
        mock_proxy.generate.assert_called_once()
        call_args = mock_proxy.generate.call_args
        task = call_args[0][0]
        assert "What is AEGIS RAG?" in task.prompt
        assert "agentic RAG system" in task.prompt


@pytest.mark.asyncio
async def test_generate_followup_questions_with_source_objects():
    """Test with source objects that have attributes instead of dicts."""
    query = "How does chunking work?"
    answer = "Chunking splits documents into smaller segments for better retrieval."

    # Create mock source objects with attributes
    class MockSource:
        def __init__(self, text: str):
            self.text = text

    sources = [
        MockSource("Chunking strategy uses 600-token overlapping windows..."),
        MockSource("The system preserves semantic coherence across chunks..."),
    ]

    mock_questions = ["What is the optimal chunk size?", "How is overlap calculated?"]
    mock_response = LLMResponse(
        content=json.dumps(mock_questions),
        provider="local_ollama",
        model="llama3.2:3b",
        prompt_tokens=120,
        completion_tokens=50,
        total_tokens=170,
        tokens_used=170,
        cost_usd=0.0,
        latency_ms=380.0,
    )

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        mock_get_proxy.return_value = mock_proxy

        questions = await generate_followup_questions(query, answer, sources)

        assert len(questions) == 2
        assert questions == mock_questions


@pytest.mark.asyncio
async def test_generate_followup_questions_no_sources():
    """Test generation without sources (should still work)."""
    query = "What is RAG?"
    answer = "RAG stands for Retrieval-Augmented Generation."

    mock_questions = [
        "How does retrieval improve generation?",
        "What are the main components of RAG?",
    ]
    mock_response = LLMResponse(
        content=json.dumps(mock_questions),
        provider="local_ollama",
        model="llama3.2:3b",
        prompt_tokens=100,
        completion_tokens=40,
        total_tokens=140,
        tokens_used=140,
        cost_usd=0.0,
        latency_ms=320.0,
    )

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        mock_get_proxy.return_value = mock_proxy

        questions = await generate_followup_questions(query, answer, sources=None)

        assert len(questions) == 2
        # Verify prompt doesn't include source context
        task = mock_proxy.generate.call_args[0][0]
        assert "Available Context:" not in task.prompt


@pytest.mark.asyncio
async def test_generate_followup_questions_markdown_wrapped_json():
    """Test handling of JSON wrapped in markdown code blocks."""
    query = "Test query"
    answer = "Test answer"

    # Mock LLM response with markdown-wrapped JSON
    mock_questions = ["Question 1?", "Question 2?", "Question 3?"]
    markdown_wrapped = f"```json\n{json.dumps(mock_questions)}\n```"

    mock_response = LLMResponse(
        content=markdown_wrapped,
        provider="local_ollama",
        model="llama3.2:3b",
        prompt_tokens=100,
        completion_tokens=60,
        total_tokens=160,
        tokens_used=160,
        cost_usd=0.0,
        latency_ms=400.0,
    )

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        mock_get_proxy.return_value = mock_proxy

        questions = await generate_followup_questions(query, answer)

        assert len(questions) == 3
        assert questions == mock_questions


@pytest.mark.asyncio
async def test_generate_followup_questions_invalid_json():
    """Test handling of invalid JSON response."""
    query = "Test query"
    answer = "Test answer"

    # Mock LLM response with invalid JSON
    mock_response = LLMResponse(
        content="This is not valid JSON",
        provider="local_ollama",
        model="llama3.2:3b",
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        tokens_used=120,
        cost_usd=0.0,
        latency_ms=300.0,
    )

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        mock_get_proxy.return_value = mock_proxy

        questions = await generate_followup_questions(query, answer)

        # Should return empty list for invalid JSON
        assert questions == []


@pytest.mark.asyncio
async def test_generate_followup_questions_non_list_response():
    """Test handling of JSON response that's not a list."""
    query = "Test query"
    answer = "Test answer"

    # Mock LLM response with valid JSON but wrong type
    mock_response = LLMResponse(
        content=json.dumps({"questions": ["Q1", "Q2"]}),  # Dict instead of list
        provider="local_ollama",
        model="llama3.2:3b",
        prompt_tokens=100,
        completion_tokens=30,
        total_tokens=130,
        tokens_used=130,
        cost_usd=0.0,
        latency_ms=350.0,
    )

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        mock_get_proxy.return_value = mock_proxy

        questions = await generate_followup_questions(query, answer)

        # Should return empty list for wrong type
        assert questions == []


@pytest.mark.asyncio
async def test_generate_followup_questions_filters_short_questions():
    """Test filtering of questions shorter than 10 characters."""
    query = "Test query"
    answer = "Test answer"

    # Mock LLM response with some short questions
    mock_questions = [
        "This is a valid question?",
        "OK?",  # Too short (< 10 chars)
        "What about this one?",
        "No",  # Too short
        "Why does this happen?",
    ]
    mock_response = LLMResponse(
        content=json.dumps(mock_questions),
        provider="local_ollama",
        model="llama3.2:3b",
        prompt_tokens=100,
        completion_tokens=70,
        total_tokens=170,
        tokens_used=170,
        cost_usd=0.0,
        latency_ms=420.0,
    )

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        mock_get_proxy.return_value = mock_proxy

        questions = await generate_followup_questions(query, answer)

        # Should filter out short questions
        assert len(questions) == 3
        assert all(len(q.strip()) >= 10 for q in questions)


@pytest.mark.asyncio
async def test_generate_followup_questions_limits_to_max():
    """Test that questions are limited to max_questions parameter."""
    query = "Test query"
    answer = "Test answer"

    # Mock LLM response with 10 questions
    mock_questions = [f"Question {i}?" for i in range(1, 11)]
    mock_response = LLMResponse(
        content=json.dumps(mock_questions),
        provider="local_ollama",
        model="llama3.2:3b",
        prompt_tokens=100,
        completion_tokens=100,
        total_tokens=200,
        tokens_used=200,
        cost_usd=0.0,
        latency_ms=500.0,
    )

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        mock_get_proxy.return_value = mock_proxy

        # Test with default max (5)
        questions = await generate_followup_questions(query, answer)
        assert len(questions) == 5

        # Test with custom max (3)
        questions = await generate_followup_questions(query, answer, max_questions=3)
        assert len(questions) == 3


@pytest.mark.asyncio
async def test_generate_followup_questions_llm_exception():
    """Test handling of LLM execution exception."""
    query = "Test query"
    answer = "Test answer"

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(side_effect=Exception("LLM service unavailable"))
        mock_get_proxy.return_value = mock_proxy

        questions = await generate_followup_questions(query, answer)

        # Should return empty list on exception (non-critical feature)
        assert questions == []


@pytest.mark.asyncio
async def test_generate_followup_questions_truncates_long_inputs():
    """Test that long queries and answers are truncated."""
    # Create very long query and answer
    query = "What is AEGIS RAG? " * 100  # Very long query
    answer = "AEGIS RAG is a system. " * 100  # Very long answer

    mock_questions = ["Question 1?", "Question 2?"]
    mock_response = LLMResponse(
        content=json.dumps(mock_questions),
        provider="local_ollama",
        model="llama3.2:3b",
        prompt_tokens=150,
        completion_tokens=50,
        total_tokens=200,
        tokens_used=200,
        cost_usd=0.0,
        latency_ms=400.0,
    )

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        mock_get_proxy.return_value = mock_proxy

        await generate_followup_questions(query, answer)

        # Verify truncation occurred in prompt
        task = mock_proxy.generate.call_args[0][0]
        prompt = task.prompt

        # Query should be truncated to 300 chars
        assert len([line for line in prompt.split("\n") if "What is AEGIS RAG?" in line][0]) < 320

        # Answer should be truncated to 500 chars
        assert (
            len([line for line in prompt.split("\n") if "AEGIS RAG is a system." in line][0]) < 520
        )


@pytest.mark.asyncio
async def test_generate_followup_questions_empty_strings():
    """Test handling of empty query or answer."""
    mock_questions = ["Generic question 1?", "Generic question 2?"]
    mock_response = LLMResponse(
        content=json.dumps(mock_questions),
        provider="local_ollama",
        model="llama3.2:3b",
        prompt_tokens=80,
        completion_tokens=40,
        total_tokens=120,
        tokens_used=120,
        cost_usd=0.0,
        latency_ms=300.0,
    )

    with patch("src.agents.followup_generator.get_aegis_llm_proxy") as mock_get_proxy:
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        mock_get_proxy.return_value = mock_proxy

        # Empty query
        questions = await generate_followup_questions("", "Some answer")
        assert len(questions) == 2

        # Empty answer
        questions = await generate_followup_questions("Some query", "")
        assert len(questions) == 2

        # Both empty
        questions = await generate_followup_questions("", "")
        assert len(questions) == 2


# ============================================================================
# Sprint 52 Feature 52.3: Async Follow-up Questions Tests
# ============================================================================


@pytest.mark.asyncio
async def test_store_conversation_context_success():
    """Test storing conversation context in Redis."""
    session_id = "test-session-123"
    query = "What is AEGIS RAG?"
    answer = "AEGIS RAG is an agentic RAG system."
    sources = [{"text": "Source 1"}, {"text": "Source 2"}]

    # Patch at the import site (inside the function)
    with patch("src.components.memory.get_redis_memory") as mock_get_redis:
        mock_redis = MagicMock()
        mock_redis.store = AsyncMock(return_value=True)
        mock_get_redis.return_value = mock_redis

        success = await store_conversation_context(session_id, query, answer, sources)

        assert success is True
        mock_redis.store.assert_called_once()
        call_kwargs = mock_redis.store.call_args[1]
        assert call_kwargs["key"] == f"{session_id}:followup_context"
        assert call_kwargs["namespace"] == "cache"
        assert call_kwargs["ttl_seconds"] == 1800  # 30 minutes
        # Verify context data
        context_value = call_kwargs["value"]
        assert context_value["query"] == query
        assert context_value["answer"] == answer
        assert context_value["sources"] == sources
        assert "stored_at" in context_value


@pytest.mark.asyncio
async def test_store_conversation_context_redis_failure():
    """Test handling Redis storage failure."""
    session_id = "test-session-123"
    query = "Test query"
    answer = "Test answer"

    with patch("src.components.memory.get_redis_memory") as mock_get_redis:
        mock_redis = MagicMock()
        mock_redis.store = AsyncMock(return_value=False)
        mock_get_redis.return_value = mock_redis

        success = await store_conversation_context(session_id, query, answer)

        assert success is False


@pytest.mark.asyncio
async def test_store_conversation_context_exception():
    """Test handling exception during storage."""
    session_id = "test-session-123"
    query = "Test query"
    answer = "Test answer"

    with patch("src.components.memory.get_redis_memory") as mock_get_redis:
        mock_redis = MagicMock()
        mock_redis.store = AsyncMock(side_effect=Exception("Redis connection failed"))
        mock_get_redis.return_value = mock_redis

        success = await store_conversation_context(session_id, query, answer)

        assert success is False


@pytest.mark.asyncio
async def test_retrieve_conversation_context_success():
    """Test retrieving conversation context from Redis."""
    session_id = "test-session-123"
    stored_context = {
        "query": "What is AEGIS RAG?",
        "answer": "AEGIS RAG is an agentic RAG system.",
        "sources": [{"text": "Source 1"}],
        "stored_at": "2025-12-18T10:00:00Z",
    }

    with patch("src.components.memory.get_redis_memory") as mock_get_redis:
        mock_redis = MagicMock()
        # Simulate Redis wrapper format
        mock_redis.retrieve = AsyncMock(return_value={"value": stored_context})
        mock_get_redis.return_value = mock_redis

        context = await retrieve_conversation_context(session_id)

        assert context == stored_context
        mock_redis.retrieve.assert_called_once()
        call_kwargs = mock_redis.retrieve.call_args[1]
        assert call_kwargs["key"] == f"{session_id}:followup_context"
        assert call_kwargs["namespace"] == "cache"


@pytest.mark.asyncio
async def test_retrieve_conversation_context_not_found():
    """Test retrieving context when not found in Redis."""
    session_id = "test-session-123"

    with patch("src.components.memory.get_redis_memory") as mock_get_redis:
        mock_redis = MagicMock()
        mock_redis.retrieve = AsyncMock(return_value=None)
        mock_get_redis.return_value = mock_redis

        context = await retrieve_conversation_context(session_id)

        assert context is None


@pytest.mark.asyncio
async def test_retrieve_conversation_context_exception():
    """Test handling exception during retrieval."""
    session_id = "test-session-123"

    with patch("src.components.memory.get_redis_memory") as mock_get_redis:
        mock_redis = MagicMock()
        mock_redis.retrieve = AsyncMock(side_effect=Exception("Redis connection failed"))
        mock_get_redis.return_value = mock_redis

        context = await retrieve_conversation_context(session_id)

        assert context is None


@pytest.mark.asyncio
async def test_generate_followup_questions_async_success():
    """Test async follow-up generation from stored context."""
    session_id = "test-session-123"
    stored_context = {
        "query": "What is AEGIS RAG?",
        "answer": "AEGIS RAG is an agentic RAG system.",
        "sources": [{"text": "Source 1"}],
        "stored_at": "2025-12-18T10:00:00Z",
    }

    mock_questions = [
        "How does the orchestration work?",
        "What are the key components?",
        "Can you explain the architecture?",
    ]

    with patch("src.agents.followup_generator.retrieve_conversation_context") as mock_retrieve:
        mock_retrieve.return_value = stored_context

        with patch("src.agents.followup_generator.generate_followup_questions") as mock_generate:
            mock_generate.return_value = mock_questions

            questions = await generate_followup_questions_async(session_id)

            assert questions == mock_questions
            mock_retrieve.assert_called_once_with(session_id)
            mock_generate.assert_called_once_with(
                query=stored_context["query"],
                answer=stored_context["answer"],
                sources=stored_context["sources"],
            )


@pytest.mark.asyncio
async def test_generate_followup_questions_async_no_context():
    """Test async generation when context not found."""
    session_id = "test-session-123"

    with patch("src.agents.followup_generator.retrieve_conversation_context") as mock_retrieve:
        mock_retrieve.return_value = None

        questions = await generate_followup_questions_async(session_id)

        assert questions == []
        mock_retrieve.assert_called_once_with(session_id)


@pytest.mark.asyncio
async def test_generate_followup_questions_async_exception():
    """Test handling exception during async generation."""
    session_id = "test-session-123"
    stored_context = {
        "query": "Test query",
        "answer": "Test answer",
        "sources": [],
        "stored_at": "2025-12-18T10:00:00Z",
    }

    with patch("src.agents.followup_generator.retrieve_conversation_context") as mock_retrieve:
        mock_retrieve.return_value = stored_context

        with patch(
            "src.agents.followup_generator.generate_followup_questions"
        ) as mock_generate:
            mock_generate.side_effect = Exception("LLM service unavailable")

            questions = await generate_followup_questions_async(session_id)

            assert questions == []
