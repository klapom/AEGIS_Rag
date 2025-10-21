"""Unit tests for Chat API Endpoints.

Sprint 10 Feature 10.1: FastAPI Chat Endpoints Tests

This test suite validates the chat endpoints using pytest and httpx.
Tests cover:
- Basic chat functionality
- Session management
- Conversation history
- Error handling
- Source citation retrieval
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock

# Test data
SAMPLE_QUERY = "Was ist AEGIS RAG?"
SAMPLE_SESSION_ID = "test-session-123"

SAMPLE_COORDINATOR_RESULT = {
    "query": SAMPLE_QUERY,
    "intent": "vector",
    "retrieved_contexts": [
        {
            "text": "AEGIS RAG ist ein agentisches RAG-System für Enterprise-Anwendungen.",
            "source": "docs/core/CLAUDE.md",
            "title": "CLAUDE.md",
            "score": 0.92,
            "metadata": {"file_type": "markdown"}
        },
        {
            "text": "Das System nutzt LangGraph für Multi-Agent Orchestration.",
            "source": "docs/TECH_STACK.md",
            "title": "TECH_STACK.md",
            "score": 0.88,
            "metadata": {}
        }
    ],
    "messages": [
        {"role": "user", "content": SAMPLE_QUERY},
        {
            "role": "assistant",
            "content": "AEGIS RAG ist ein agentisches RAG-System (Agentic Enterprise Graph Intelligence System) "
                      "für Enterprise-Anwendungen. Es kombiniert Vector Search, Graph-basierte Retrieval und "
                      "Multi-Agent Orchestration mit LangGraph."
        }
    ],
    "metadata": {
        "latency_seconds": 1.23,
        "agent_path": ["router", "vector_agent", "generator"],
        "tokens_used": 250
    }
}


@pytest.mark.asyncio
class TestChatEndpoint:
    """Tests for POST /api/v1/chat endpoint."""

    async def test_chat_endpoint_basic_success(self, async_client: AsyncClient):
        """Test basic chat request returns answer."""
        with patch("src.api.v1.chat.get_coordinator") as mock_get_coordinator:
            # Mock coordinator
            mock_coordinator = AsyncMock()
            mock_coordinator.process_query.return_value = SAMPLE_COORDINATOR_RESULT
            mock_get_coordinator.return_value = mock_coordinator

            # Send request
            response = await async_client.post(
                "/api/v1/chat/",
                json={"query": SAMPLE_QUERY, "session_id": SAMPLE_SESSION_ID}
            )

            # Assertions
            assert response.status_code == 200
            data = response.json()

            assert "answer" in data
            assert len(data["answer"]) > 0
            assert "AEGIS RAG" in data["answer"]

            assert data["query"] == SAMPLE_QUERY
            assert data["session_id"] == SAMPLE_SESSION_ID
            assert data["intent"] == "vector"

            assert "sources" in data
            assert len(data["sources"]) > 0

            assert "metadata" in data
            assert "latency_seconds" in data["metadata"]

    async def test_chat_endpoint_generates_session_id_if_not_provided(self, async_client: AsyncClient):
        """Test that session_id is auto-generated if not provided."""
        with patch("src.api.v1.chat.get_coordinator") as mock_get_coordinator:
            mock_coordinator = AsyncMock()
            mock_coordinator.process_query.return_value = SAMPLE_COORDINATOR_RESULT
            mock_get_coordinator.return_value = mock_coordinator

            # Send request WITHOUT session_id
            response = await async_client.post(
                "/api/v1/chat/",
                json={"query": SAMPLE_QUERY}
            )

            assert response.status_code == 200
            data = response.json()

            # Should have auto-generated session_id (UUID format)
            assert "session_id" in data
            assert len(data["session_id"]) == 36  # UUID length
            assert "-" in data["session_id"]  # UUID contains dashes

    async def test_chat_endpoint_includes_sources(self, async_client: AsyncClient):
        """Test that sources are included in response."""
        with patch("src.api.v1.chat.get_coordinator") as mock_get_coordinator:
            mock_coordinator = AsyncMock()
            mock_coordinator.process_query.return_value = SAMPLE_COORDINATOR_RESULT
            mock_get_coordinator.return_value = mock_coordinator

            response = await async_client.post(
                "/api/v1/chat/",
                json={"query": SAMPLE_QUERY, "include_sources": True}
            )

            assert response.status_code == 200
            data = response.json()

            assert "sources" in data
            assert len(data["sources"]) >= 1

            # Validate source structure
            source = data["sources"][0]
            assert "text" in source
            assert "title" in source
            assert "source" in source
            assert "score" in source

            # Check actual values
            assert "AEGIS RAG" in source["text"]
            assert source["score"] is not None
            assert source["score"] > 0.5  # Should be relevant

    async def test_chat_endpoint_excludes_sources_when_requested(self, async_client: AsyncClient):
        """Test that sources can be excluded."""
        with patch("src.api.v1.chat.get_coordinator") as mock_get_coordinator:
            mock_coordinator = AsyncMock()
            mock_coordinator.process_query.return_value = SAMPLE_COORDINATOR_RESULT
            mock_get_coordinator.return_value = mock_coordinator

            response = await async_client.post(
                "/api/v1/chat/",
                json={"query": SAMPLE_QUERY, "include_sources": False}
            )

            assert response.status_code == 200
            data = response.json()

            assert "sources" in data
            assert len(data["sources"]) == 0  # Should be empty

    async def test_chat_endpoint_with_intent_override(self, async_client: AsyncClient):
        """Test that intent can be overridden."""
        with patch("src.api.v1.chat.get_coordinator") as mock_get_coordinator:
            mock_coordinator = AsyncMock()
            custom_result = SAMPLE_COORDINATOR_RESULT.copy()
            custom_result["intent"] = "graph"
            mock_coordinator.process_query.return_value = custom_result
            mock_get_coordinator.return_value = mock_coordinator

            response = await async_client.post(
                "/api/v1/chat/",
                json={"query": SAMPLE_QUERY, "intent": "graph"}
            )

            assert response.status_code == 200
            data = response.json()

            assert data["intent"] == "graph"

            # Verify coordinator was called with intent
            mock_coordinator.process_query.assert_called_once()
            call_args = mock_coordinator.process_query.call_args
            assert call_args[1]["intent"] == "graph"

    async def test_chat_endpoint_handles_empty_query(self, async_client: AsyncClient):
        """Test validation error for empty query."""
        response = await async_client.post(
            "/api/v1/chat/",
            json={"query": ""}
        )

        # Should return validation error
        assert response.status_code == 422
        data = response.json()
        assert "error" in data or "detail" in data

    async def test_chat_endpoint_handles_coordinator_exception(self, async_client: AsyncClient):
        """Test error handling when coordinator fails."""
        with patch("src.api.v1.chat.get_coordinator") as mock_get_coordinator:
            mock_coordinator = AsyncMock()
            mock_coordinator.process_query.side_effect = Exception("Coordinator failure")
            mock_get_coordinator.return_value = mock_coordinator

            response = await async_client.post(
                "/api/v1/chat/",
                json={"query": SAMPLE_QUERY}
            )

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data or "message" in data

    async def test_chat_endpoint_extracts_answer_from_messages(self, async_client: AsyncClient):
        """Test answer extraction from different result formats."""
        with patch("src.api.v1.chat.get_coordinator") as mock_get_coordinator:
            mock_coordinator = AsyncMock()

            # Test with messages format (LangGraph style)
            result_with_messages = {
                "messages": [
                    {"role": "user", "content": SAMPLE_QUERY},
                    {"role": "assistant", "content": "This is the answer from messages"}
                ],
                "intent": "vector",
                "retrieved_contexts": [],
                "metadata": {}
            }
            mock_coordinator.process_query.return_value = result_with_messages
            mock_get_coordinator.return_value = mock_coordinator

            response = await async_client.post(
                "/api/v1/chat/",
                json={"query": SAMPLE_QUERY}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "This is the answer from messages"

    async def test_chat_endpoint_fallback_answer_if_none_found(self, async_client: AsyncClient):
        """Test fallback message when no answer is found in result."""
        with patch("src.api.v1.chat.get_coordinator") as mock_get_coordinator:
            mock_coordinator = AsyncMock()

            # Result with no answer
            empty_result = {
                "intent": "vector",
                "retrieved_contexts": [],
                "metadata": {}
            }
            mock_coordinator.process_query.return_value = empty_result
            mock_get_coordinator.return_value = mock_coordinator

            response = await async_client.post(
                "/api/v1/chat/",
                json={"query": SAMPLE_QUERY}
            )

            assert response.status_code == 200
            data = response.json()

            # Should have fallback message
            assert "sorry" in data["answer"].lower() or "couldn't" in data["answer"].lower()


@pytest.mark.asyncio
class TestConversationHistoryEndpoint:
    """Tests for GET /api/v1/chat/history/{session_id} endpoint."""

    async def test_get_conversation_history_success(self, async_client: AsyncClient):
        """Test retrieving conversation history."""
        with patch("src.api.v1.chat.get_unified_memory_api") as mock_get_memory:
            # Mock memory API
            mock_memory = AsyncMock()
            mock_memory.retrieve.return_value = {
                "messages": [
                    {"role": "user", "content": "First question"},
                    {"role": "assistant", "content": "First answer"},
                    {"role": "user", "content": "Second question"},
                    {"role": "assistant", "content": "Second answer"}
                ]
            }
            mock_get_memory.return_value = mock_memory

            response = await async_client.get(f"/api/v1/chat/history/{SAMPLE_SESSION_ID}")

            assert response.status_code == 200
            data = response.json()

            assert data["session_id"] == SAMPLE_SESSION_ID
            assert "messages" in data
            assert len(data["messages"]) == 4
            assert data["message_count"] == 4

    async def test_get_conversation_history_empty_session(self, async_client: AsyncClient):
        """Test retrieving history for session with no messages."""
        with patch("src.api.v1.chat.get_unified_memory_api") as mock_get_memory:
            mock_memory = AsyncMock()
            mock_memory.retrieve.return_value = None  # No data found
            mock_get_memory.return_value = mock_memory

            response = await async_client.get(f"/api/v1/chat/history/{SAMPLE_SESSION_ID}")

            assert response.status_code == 200
            data = response.json()

            assert data["session_id"] == SAMPLE_SESSION_ID
            assert data["messages"] == []
            assert data["message_count"] == 0

    async def test_get_conversation_history_handles_exception(self, async_client: AsyncClient):
        """Test error handling in history retrieval."""
        with patch("src.api.v1.chat.get_unified_memory_api") as mock_get_memory:
            mock_memory = AsyncMock()
            mock_memory.retrieve.side_effect = Exception("Memory error")
            mock_get_memory.return_value = mock_memory

            response = await async_client.get(f"/api/v1/chat/history/{SAMPLE_SESSION_ID}")

            assert response.status_code == 500


@pytest.mark.asyncio
class TestDeleteConversationHistoryEndpoint:
    """Tests for DELETE /api/v1/chat/history/{session_id} endpoint."""

    async def test_delete_conversation_history_success(self, async_client: AsyncClient):
        """Test deleting conversation history."""
        with patch("src.api.v1.chat.get_unified_memory_api") as mock_get_memory:
            mock_memory = AsyncMock()
            mock_memory.delete.return_value = None  # Success
            mock_get_memory.return_value = mock_memory

            response = await async_client.delete(f"/api/v1/chat/history/{SAMPLE_SESSION_ID}")

            assert response.status_code == 200
            data = response.json()

            assert data["session_id"] == SAMPLE_SESSION_ID
            assert data["status"] == "success"
            assert "deleted" in data["message"].lower()

            # Verify delete was called with correct key
            mock_memory.delete.assert_called_once()
            call_args = mock_memory.delete.call_args
            assert f"conversation:{SAMPLE_SESSION_ID}" in str(call_args)

    async def test_delete_conversation_history_handles_exception(self, async_client: AsyncClient):
        """Test error handling in history deletion."""
        with patch("src.api.v1.chat.get_unified_memory_api") as mock_get_memory:
            mock_memory = AsyncMock()
            mock_memory.delete.side_effect = Exception("Delete failed")
            mock_get_memory.return_value = mock_memory

            response = await async_client.delete(f"/api/v1/chat/history/{SAMPLE_SESSION_ID}")

            assert response.status_code == 500


# Fixtures

@pytest.fixture
async def async_client():
    """Fixture for async HTTP client."""
    from src.api.main import app
    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client
