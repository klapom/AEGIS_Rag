"""Integration tests for session management endpoints.

Sprint 35 Feature 35.5: Session History Sidebar
Tests for list sessions, get conversation, and delete session endpoints.
"""

import pytest
from datetime import UTC, datetime
from httpx import AsyncClient

from src.api.main import app
from src.components.memory import get_redis_memory


@pytest.mark.asyncio
async def test_list_sessions_empty():
    """Test listing sessions when no sessions exist."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/chat/sessions")

    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert "total" in data
    assert isinstance(data["sessions"], list)


@pytest.mark.asyncio
async def test_list_sessions_with_data():
    """Test listing sessions with existing conversation data."""
    # Setup: Create test conversation in Redis
    redis_memory = get_redis_memory()
    session_id = "test-session-123"

    conversation_data = {
        "messages": [
            {"role": "user", "content": "What is RAG?"},
            {"role": "assistant", "content": "RAG stands for Retrieval-Augmented Generation..."},
        ],
        "title": "Understanding RAG",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "message_count": 2,
    }

    await redis_memory.store(
        key=session_id, value=conversation_data, ttl_seconds=600, namespace="conversation"
    )

    # Test: List sessions
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/chat/sessions")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

    # Find our test session
    test_session = next((s for s in data["sessions"] if s["session_id"] == session_id), None)
    assert test_session is not None
    assert test_session["title"] == "Understanding RAG"
    assert test_session["message_count"] == 2
    assert test_session["preview"] == "What is RAG?"

    # Cleanup
    await redis_memory.delete(key=session_id, namespace="conversation")


@pytest.mark.asyncio
async def test_get_conversation_not_found():
    """Test getting conversation for non-existent session."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/chat/sessions/nonexistent-session/conversation")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_conversation_success():
    """Test getting full conversation for existing session."""
    # Setup: Create test conversation
    redis_memory = get_redis_memory()
    session_id = "test-session-456"

    conversation_data = {
        "messages": [
            {"role": "user", "content": "Explain hybrid search", "timestamp": datetime.now(UTC).isoformat()},
            {
                "role": "assistant",
                "content": "Hybrid search combines vector and keyword search...",
                "timestamp": datetime.now(UTC).isoformat(),
                "sources": [{"text": "Source 1", "score": 0.95}],
            },
        ],
        "title": "Hybrid Search Explanation",
        "follow_up_questions": ["What is vector search?", "How does BM25 work?"],
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    await redis_memory.store(
        key=session_id, value=conversation_data, ttl_seconds=600, namespace="conversation"
    )

    # Test: Get conversation
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/v1/chat/sessions/{session_id}/conversation")

    assert response.status_code == 200
    data = response.json()

    assert data["session_id"] == session_id
    assert data["title"] == "Hybrid Search Explanation"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Explain hybrid search"
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][1]["sources"] is not None
    assert len(data["follow_up_questions"]) == 2

    # Cleanup
    await redis_memory.delete(key=session_id, namespace="conversation")


@pytest.mark.asyncio
async def test_delete_session_not_found():
    """Test deleting non-existent session."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete("/api/v1/chat/sessions/nonexistent-session")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_success():
    """Test deleting existing session."""
    # Setup: Create test conversation
    redis_memory = get_redis_memory()
    session_id = "test-session-789"

    conversation_data = {
        "messages": [{"role": "user", "content": "Test message"}],
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    await redis_memory.store(
        key=session_id, value=conversation_data, ttl_seconds=600, namespace="conversation"
    )

    # Test: Delete session
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/chat/sessions/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["status"] == "success"

    # Verify session is deleted
    conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")
    assert conversation is None


@pytest.mark.asyncio
async def test_session_list_pagination():
    """Test session list pagination parameters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test with limit parameter
        response = await client.get("/api/v1/chat/sessions?limit=10&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert "total" in data
    # Should return at most 10 sessions
    assert len(data["sessions"]) <= 10


@pytest.mark.asyncio
async def test_session_list_date_grouping():
    """Test that sessions are sorted by most recent first."""
    # Setup: Create multiple sessions with different timestamps
    redis_memory = get_redis_memory()
    sessions_data = [
        ("old-session", datetime(2024, 1, 1).isoformat()),
        ("recent-session", datetime.now(UTC).isoformat()),
        ("middle-session", datetime(2024, 6, 1).isoformat()),
    ]

    for session_id, timestamp in sessions_data:
        conversation_data = {
            "messages": [{"role": "user", "content": "Test"}],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        await redis_memory.store(
            key=session_id, value=conversation_data, ttl_seconds=600, namespace="conversation"
        )

    # Test: List sessions (should be sorted by updated_at desc)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/chat/sessions")

    assert response.status_code == 200
    data = response.json()

    # Find our test sessions
    test_sessions = [s for s in data["sessions"] if s["session_id"] in [d[0] for d in sessions_data]]

    if len(test_sessions) >= 2:
        # Most recent should be first
        assert test_sessions[0]["session_id"] == "recent-session"

    # Cleanup
    for session_id, _ in sessions_data:
        await redis_memory.delete(key=session_id, namespace="conversation")


@pytest.mark.asyncio
async def test_get_conversation_with_long_preview():
    """Test session list truncates long messages for preview."""
    redis_memory = get_redis_memory()
    session_id = "test-long-preview"

    long_message = "A" * 150  # 150 chars, should be truncated to 100

    conversation_data = {
        "messages": [{"role": "user", "content": long_message}],
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    await redis_memory.store(
        key=session_id, value=conversation_data, ttl_seconds=600, namespace="conversation"
    )

    # Test: List sessions
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/chat/sessions")

    assert response.status_code == 200
    data = response.json()

    test_session = next((s for s in data["sessions"] if s["session_id"] == session_id), None)
    assert test_session is not None
    assert test_session["preview"] is not None
    # Preview should be truncated with "..."
    assert len(test_session["preview"]) <= 103  # 100 chars + "..."
    assert test_session["preview"].endswith("...")

    # Cleanup
    await redis_memory.delete(key=session_id, namespace="conversation")
