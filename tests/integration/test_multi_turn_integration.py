"""Integration tests for multi-turn RAG system.

Sprint 63 Feature 63.1: Multi-Turn RAG Template (13 SP)

Tests for the complete multi-turn conversation flow including:
- API endpoint
- Agent workflow
- Redis storage
- LLM integration
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.multi_turn import MultiTurnRequest, MultiTurnResponse


@pytest.fixture
def test_client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_multi_turn_agent():
    """Mock MultiTurnAgent for integration tests."""
    with patch("src.api.v1.chat.MultiTurnAgent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.process_turn = AsyncMock(
            return_value={
                "answer": "AEGIS RAG is an agentic RAG system with vector, graph, and memory components.",
                "query": "What is AEGIS RAG?",
                "conversation_id": "test-conv-123",
                "sources": [
                    {
                        "text": "AEGIS RAG architecture description...",
                        "title": "CLAUDE.md",
                        "source": "docs/CLAUDE.md",
                        "score": 0.95,
                        "metadata": {},
                    }
                ],
                "contradictions": [],
                "memory_summary": None,
                "turn_number": 1,
                "metadata": {
                    "latency_seconds": 0.5,
                    "enhanced_query": "What is AEGIS RAG?",
                    "agent_path": [
                        "prepare_context",
                        "search",
                        "detect_contradictions",
                        "answer",
                        "update_memory",
                    ],
                },
            }
        )
        mock_agent_class.return_value = mock_agent
        yield mock_agent


@pytest.fixture
def mock_redis_memory():
    """Mock Redis memory for integration tests."""
    with patch("src.api.v1.chat.get_redis_memory") as mock_get_redis:
        mock_redis = AsyncMock()
        mock_redis.retrieve = AsyncMock(return_value=None)
        mock_redis.store = AsyncMock(return_value=True)
        mock_get_redis.return_value = mock_redis
        yield mock_redis


class TestMultiTurnAPIIntegration:
    """Integration tests for multi-turn API endpoint."""

    @pytest.mark.asyncio
    async def test_multi_turn_first_turn(
        self, test_client, mock_multi_turn_agent, mock_redis_memory
    ):
        """Test first turn in multi-turn conversation."""
        # Setup request
        request_data = {
            "query": "What is AEGIS RAG?",
            "conversation_id": "test-conv-123",
            "namespace": "default",
            "detect_contradictions": True,
            "max_history_turns": 5,
        }

        # Execute
        response = test_client.post("/api/v1/chat/multi-turn", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "AEGIS RAG is an agentic RAG system with vector, graph, and memory components."
        assert data["conversation_id"] == "test-conv-123"
        assert data["turn_number"] == 1
        assert len(data["sources"]) == 1
        assert data["contradictions"] == []

    @pytest.mark.asyncio
    async def test_multi_turn_subsequent_turn(
        self, test_client, mock_multi_turn_agent, mock_redis_memory
    ):
        """Test subsequent turn with existing conversation history."""
        # Setup existing conversation
        existing_history = {
            "turns": [
                {
                    "query": "What is AEGIS RAG?",
                    "answer": "AEGIS RAG is an agentic system.",
                    "sources": [],
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            ],
            "updated_at": datetime.now(UTC).isoformat(),
        }

        mock_redis_memory.retrieve = AsyncMock(return_value={"value": existing_history})

        # Update mock agent for second turn
        mock_multi_turn_agent.process_turn = AsyncMock(
            return_value={
                "answer": "Performance metrics are excellent with <200ms latency.",
                "query": "What about performance?",
                "conversation_id": "test-conv-123",
                "sources": [],
                "contradictions": [],
                "memory_summary": None,
                "turn_number": 2,
                "metadata": {"latency_seconds": 0.4},
            }
        )

        # Setup request
        request_data = {
            "query": "What about performance?",
            "conversation_id": "test-conv-123",
            "namespace": "default",
        }

        # Execute
        response = test_client.post("/api/v1/chat/multi-turn", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["turn_number"] == 2
        assert "performance" in data["answer"].lower()

    @pytest.mark.asyncio
    async def test_multi_turn_with_contradictions(
        self, test_client, mock_multi_turn_agent, mock_redis_memory
    ):
        """Test multi-turn with contradiction detection."""
        # Update mock agent to return contradictions
        mock_multi_turn_agent.process_turn = AsyncMock(
            return_value={
                "answer": "I notice a contradiction in the performance data.",
                "query": "What are the metrics?",
                "conversation_id": "test-conv-123",
                "sources": [],
                "contradictions": [
                    {
                        "current_info": "Latency is 200ms",
                        "previous_info": "Latency is under 100ms",
                        "turn_index": 0,
                        "confidence": 0.9,
                        "explanation": "Performance metrics differ",
                    }
                ],
                "memory_summary": None,
                "turn_number": 2,
                "metadata": {"latency_seconds": 0.5},
            }
        )

        # Setup request
        request_data = {
            "query": "What are the metrics?",
            "conversation_id": "test-conv-123",
            "namespace": "default",
            "detect_contradictions": True,
        }

        # Execute
        response = test_client.post("/api/v1/chat/multi-turn", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert len(data["contradictions"]) == 1
        assert data["contradictions"][0]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_multi_turn_memory_summary(
        self, test_client, mock_multi_turn_agent, mock_redis_memory
    ):
        """Test multi-turn with memory summary generation."""
        # Update mock agent to return memory summary (at turn 5)
        mock_multi_turn_agent.process_turn = AsyncMock(
            return_value={
                "answer": "Summary of our discussion so far...",
                "query": "Can you summarize?",
                "conversation_id": "test-conv-123",
                "sources": [],
                "contradictions": [],
                "memory_summary": "Discussion about AEGIS RAG system architecture, components, and performance metrics.",
                "turn_number": 5,
                "metadata": {"latency_seconds": 0.6},
            }
        )

        # Setup request
        request_data = {
            "query": "Can you summarize?",
            "conversation_id": "test-conv-123",
            "namespace": "default",
        }

        # Execute
        response = test_client.post("/api/v1/chat/multi-turn", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["turn_number"] == 5
        assert data["memory_summary"] is not None
        assert "AEGIS RAG system architecture" in data["memory_summary"]

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_pruning(
        self, test_client, mock_multi_turn_agent, mock_redis_memory
    ):
        """Test that conversation history is pruned to last 10 turns."""
        # Setup long history (15 turns)
        long_history = {
            "turns": [
                {
                    "query": f"Query {i}",
                    "answer": f"Answer {i}",
                    "sources": [],
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                for i in range(15)
            ],
            "updated_at": datetime.now(UTC).isoformat(),
        }

        mock_redis_memory.retrieve = AsyncMock(return_value={"value": long_history})

        # Setup request
        request_data = {
            "query": "New query",
            "conversation_id": "test-conv-123",
            "namespace": "default",
        }

        # Execute
        response = test_client.post("/api/v1/chat/multi-turn", json=request_data)

        # Assert
        assert response.status_code == 200

        # Verify Redis store was called
        mock_redis_memory.store.assert_called_once()
        stored_data = mock_redis_memory.store.call_args[1]["value"]

        # Check that only last 10 turns are stored
        assert len(stored_data["turns"]) == 10


class TestMultiTurnAgentIntegration:
    """Integration tests for MultiTurnAgent workflow."""

    @pytest.mark.asyncio
    @patch("src.agents.multi_turn.nodes.get_aegis_llm_proxy")
    @patch("src.agents.multi_turn.nodes.get_qdrant_client")
    @patch("src.agents.multi_turn.nodes.get_embeddings")
    @patch("src.agents.multi_turn.nodes.get_redis_memory")
    async def test_full_agent_workflow(
        self, mock_get_redis, mock_get_embeddings, mock_get_qdrant, mock_get_llm
    ):
        """Test complete agent workflow through all nodes."""
        from src.agents.multi_turn import MultiTurnAgent

        # Setup mocks for all nodes
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(
            return_value=MagicMock(
                content="Enhanced query with context"  # For prepare_context
            )
        )
        mock_get_llm.return_value = mock_llm

        mock_embeddings = AsyncMock()
        mock_embeddings.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_get_embeddings.return_value = mock_embeddings

        mock_scored_point = MagicMock()
        mock_scored_point.score = 0.95
        mock_scored_point.payload = {
            "text": "AEGIS RAG is an agentic system...",
            "title": "CLAUDE.md",
            "source": "docs/CLAUDE.md",
            "metadata": {},
        }

        mock_qdrant = MagicMock()
        mock_qdrant.async_client.search = AsyncMock(return_value=[mock_scored_point])
        mock_get_qdrant.return_value = mock_qdrant

        mock_redis = AsyncMock()
        mock_redis.store = AsyncMock(return_value=True)
        mock_get_redis.return_value = mock_redis

        # Initialize agent
        agent = MultiTurnAgent()

        # Execute
        result = await agent.process_turn(
            query="What is AEGIS RAG?",
            conversation_id="test-conv-integration",
            conversation_history=[],
            namespace="default",
        )

        # Assert
        assert result["conversation_id"] == "test-conv-integration"
        assert result["turn_number"] == 1
        assert len(result["sources"]) > 0
        assert "latency_seconds" in result["metadata"]
