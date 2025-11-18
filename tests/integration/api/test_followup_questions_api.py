"""Integration tests for follow-up questions API endpoint.

Sprint 27 Feature 27.5: Follow-up Question Suggestions

Tests the GET /chat/sessions/{session_id}/followup-questions endpoint:
- Successful question generation
- Cache behavior (5min TTL)
- Session not found (404)
- Insufficient messages (empty list)
- Error handling
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_redis_memory():
    """Mock Redis memory for testing."""
    with patch("src.api.v1.chat.get_redis_memory") as mock:
        yield mock


@pytest.fixture
def sample_conversation():
    """Sample conversation data for testing."""
    return {
        "messages": [
            {
                "role": "user",
                "content": "What is AEGIS RAG?",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "role": "assistant",
                "content": "AEGIS RAG is an agentic RAG system with vector search and graph reasoning.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "intent": "vector",
                "source_count": 2,
                "sources": [
                    {"text": "AEGIS RAG uses LangGraph...", "source": "doc1.pdf"},
                    {"text": "Vector search with Qdrant...", "source": "doc2.pdf"},
                ],
            },
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "message_count": 2,
    }


def test_get_followup_questions_success(client, mock_redis_memory, sample_conversation):
    """Test successful follow-up question generation."""
    session_id = "test-session-123"

    # Mock Redis retrieval
    async def mock_retrieve(key: str, namespace: str):
        if namespace == "cache":
            return None  # No cache
        if namespace == "conversation":
            return {"value": sample_conversation}
        return None

    mock_redis_memory.return_value.retrieve = AsyncMock(side_effect=mock_retrieve)
    mock_redis_memory.return_value.store = AsyncMock(return_value=True)

    # Mock follow-up generation
    mock_questions = [
        "How does LangGraph orchestrate agents?",
        "What role does Qdrant play in vector search?",
        "Can you explain graph reasoning in AEGIS RAG?",
    ]

    with patch("src.api.v1.chat.generate_followup_questions") as mock_gen:
        mock_gen.return_value = mock_questions

        response = client.get(f"/chat/sessions/{session_id}/followup-questions")

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == session_id
        assert len(data["followup_questions"]) == 3
        assert data["followup_questions"] == mock_questions
        assert data["from_cache"] is False
        assert "generated_at" in data

        # Verify function was called with correct arguments
        mock_gen.assert_called_once()
        call_args = mock_gen.call_args
        assert call_args[1]["query"] == "What is AEGIS RAG?"
        assert "agentic RAG system" in call_args[1]["answer"]
        assert len(call_args[1]["sources"]) == 2


def test_get_followup_questions_from_cache(client, mock_redis_memory):
    """Test retrieving follow-up questions from cache."""
    session_id = "test-session-456"
    cached_questions = [
        "Cached question 1?",
        "Cached question 2?",
        "Cached question 3?",
    ]

    # Mock Redis retrieval with cache hit
    async def mock_retrieve(key: str, namespace: str):
        if namespace == "cache":
            return {"value": {"questions": cached_questions}}
        return None

    mock_redis_memory.return_value.retrieve = AsyncMock(side_effect=mock_retrieve)

    with patch("src.api.v1.chat.generate_followup_questions") as mock_gen:
        response = client.get(f"/chat/sessions/{session_id}/followup-questions")

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == session_id
        assert data["followup_questions"] == cached_questions
        assert data["from_cache"] is True

        # Verify generation was NOT called (cache hit)
        mock_gen.assert_not_called()


def test_get_followup_questions_session_not_found(client, mock_redis_memory):
    """Test handling of non-existent session."""
    session_id = "nonexistent-session"

    # Mock Redis retrieval with no conversation
    async def mock_retrieve(key: str, namespace: str):
        if namespace == "cache":
            return None
        if namespace == "conversation":
            return None  # Session not found
        return None

    mock_redis_memory.return_value.retrieve = AsyncMock(side_effect=mock_retrieve)

    response = client.get(f"/chat/sessions/{session_id}/followup-questions")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_followup_questions_insufficient_messages(client, mock_redis_memory):
    """Test handling of conversation with insufficient messages."""
    session_id = "new-session"

    # Mock conversation with only one message
    single_message_conv = {
        "messages": [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message_count": 1,
    }

    async def mock_retrieve(key: str, namespace: str):
        if namespace == "cache":
            return None
        if namespace == "conversation":
            return {"value": single_message_conv}
        return None

    mock_redis_memory.return_value.retrieve = AsyncMock(side_effect=mock_retrieve)

    response = client.get(f"/chat/sessions/{session_id}/followup-questions")

    assert response.status_code == 200
    data = response.json()

    assert data["session_id"] == session_id
    assert data["followup_questions"] == []  # Empty list
    assert data["from_cache"] is False


def test_get_followup_questions_no_qa_pair(client, mock_redis_memory):
    """Test handling of conversation without Q&A pair."""
    session_id = "broken-session"

    # Mock conversation with messages but no assistant response
    no_qa_conv = {
        "messages": [
            {"role": "user", "content": "Query 1", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"role": "user", "content": "Query 2", "timestamp": datetime.now(timezone.utc).isoformat()},
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message_count": 2,
    }

    async def mock_retrieve(key: str, namespace: str):
        if namespace == "cache":
            return None
        if namespace == "conversation":
            return {"value": no_qa_conv}
        return None

    mock_redis_memory.return_value.retrieve = AsyncMock(side_effect=mock_retrieve)

    response = client.get(f"/chat/sessions/{session_id}/followup-questions")

    assert response.status_code == 200
    data = response.json()

    assert data["followup_questions"] == []


def test_get_followup_questions_generation_failure(client, mock_redis_memory, sample_conversation):
    """Test handling of follow-up generation failure."""
    session_id = "test-session-789"

    async def mock_retrieve(key: str, namespace: str):
        if namespace == "cache":
            return None
        if namespace == "conversation":
            return {"value": sample_conversation}
        return None

    mock_redis_memory.return_value.retrieve = AsyncMock(side_effect=mock_retrieve)

    # Mock generation to raise exception
    with patch("src.api.v1.chat.generate_followup_questions") as mock_gen:
        mock_gen.side_effect = Exception("LLM service unavailable")

        response = client.get(f"/chat/sessions/{session_id}/followup-questions")

        assert response.status_code == 500
        assert "Failed to generate follow-up questions" in response.json()["detail"]


def test_get_followup_questions_caches_results(client, mock_redis_memory, sample_conversation):
    """Test that generated questions are cached in Redis."""
    session_id = "test-session-cache"

    async def mock_retrieve(key: str, namespace: str):
        if namespace == "cache":
            return None
        if namespace == "conversation":
            return {"value": sample_conversation}
        return None

    mock_store = AsyncMock(return_value=True)
    mock_redis_memory.return_value.retrieve = AsyncMock(side_effect=mock_retrieve)
    mock_redis_memory.return_value.store = mock_store

    mock_questions = ["Question 1?", "Question 2?"]

    with patch("src.api.v1.chat.generate_followup_questions") as mock_gen:
        mock_gen.return_value = mock_questions

        response = client.get(f"/chat/sessions/{session_id}/followup-questions")

        assert response.status_code == 200

        # Verify cache storage was called
        mock_store.assert_called_once()
        call_args = mock_store.call_args

        assert call_args[1]["key"] == f"{session_id}:followup"
        assert call_args[1]["value"] == {"questions": mock_questions}
        assert call_args[1]["namespace"] == "cache"
        assert call_args[1]["ttl_seconds"] == 300  # 5 minutes


def test_get_followup_questions_multi_turn_conversation(client, mock_redis_memory):
    """Test follow-up generation for multi-turn conversation (uses last Q&A)."""
    session_id = "multi-turn-session"

    # Mock conversation with multiple turns
    multi_turn_conv = {
        "messages": [
            {"role": "user", "content": "First query", "timestamp": datetime.now(timezone.utc).isoformat()},
            {
                "role": "assistant",
                "content": "First answer",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {"role": "user", "content": "Second query", "timestamp": datetime.now(timezone.utc).isoformat()},
            {
                "role": "assistant",
                "content": "Second answer",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sources": [{"text": "Source for second answer", "source": "doc.pdf"}],
            },
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message_count": 4,
    }

    async def mock_retrieve(key: str, namespace: str):
        if namespace == "cache":
            return None
        if namespace == "conversation":
            return {"value": multi_turn_conv}
        return None

    mock_redis_memory.return_value.retrieve = AsyncMock(side_effect=mock_retrieve)
    mock_redis_memory.return_value.store = AsyncMock(return_value=True)

    mock_questions = ["Follow-up 1?", "Follow-up 2?"]

    with patch("src.api.v1.chat.generate_followup_questions") as mock_gen:
        mock_gen.return_value = mock_questions

        response = client.get(f"/chat/sessions/{session_id}/followup-questions")

        assert response.status_code == 200

        # Verify last Q&A was used
        call_args = mock_gen.call_args
        assert call_args[1]["query"] == "Second query"
        assert call_args[1]["answer"] == "Second answer"
        assert len(call_args[1]["sources"]) == 1


def test_get_followup_questions_no_sources(client, mock_redis_memory):
    """Test follow-up generation when sources are not available."""
    session_id = "no-sources-session"

    # Mock conversation without sources
    no_sources_conv = {
        "messages": [
            {"role": "user", "content": "Query", "timestamp": datetime.now(timezone.utc).isoformat()},
            {
                "role": "assistant",
                "content": "Answer without sources",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                # No sources field
            },
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message_count": 2,
    }

    async def mock_retrieve(key: str, namespace: str):
        if namespace == "cache":
            return None
        if namespace == "conversation":
            return {"value": no_sources_conv}
        return None

    mock_redis_memory.return_value.retrieve = AsyncMock(side_effect=mock_retrieve)
    mock_redis_memory.return_value.store = AsyncMock(return_value=True)

    mock_questions = ["Question 1?", "Question 2?"]

    with patch("src.api.v1.chat.generate_followup_questions") as mock_gen:
        mock_gen.return_value = mock_questions

        response = client.get(f"/chat/sessions/{session_id}/followup-questions")

        assert response.status_code == 200

        # Verify sources is empty list
        call_args = mock_gen.call_args
        assert call_args[1]["sources"] == []
