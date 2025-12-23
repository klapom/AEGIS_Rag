"""Unit tests for multi-turn agent nodes.

Sprint 63 Feature 63.1: Multi-Turn RAG Template (13 SP)

Tests for individual LangGraph nodes:
- prepare_context_node
- search_node
- detect_contradictions_node
- answer_node
- update_memory_node
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.multi_turn.nodes import (
    answer_node,
    detect_contradictions_node,
    prepare_context_node,
    search_node,
    update_memory_node,
)
from src.api.models.multi_turn import Contradiction, ConversationTurn, Source


@pytest.fixture
def mock_llm_response():
    """Mock LLM response."""
    mock_response = MagicMock()
    mock_response.content = "Enhanced query with context"
    return mock_response


@pytest.fixture
def sample_conversation_turn():
    """Sample conversation turn for testing."""
    return ConversationTurn(
        query="What is AEGIS RAG?",
        answer="AEGIS RAG is an agentic RAG system with vector, graph, and memory components.",
        sources=[
            Source(
                text="AEGIS RAG architecture...",
                title="CLAUDE.md",
                source="docs/CLAUDE.md",
                score=0.95,
            )
        ],
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def minimal_state():
    """Minimal state for testing."""
    return {
        "conversation_id": "test-conv-123",
        "current_query": "What are the performance metrics?",
        "conversation_history": [],
        "max_history_turns": 5,
    }


class TestPrepareContextNode:
    """Tests for prepare_context_node."""

    @pytest.mark.asyncio
    async def test_prepare_context_no_history(self, minimal_state):
        """Test context preparation with no conversation history."""
        result = await prepare_context_node(minimal_state)

        assert result["enhanced_query"] == minimal_state["current_query"]

    @pytest.mark.asyncio
    @patch("src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy")
    async def test_prepare_context_with_history(
        self, mock_get_llm, minimal_state, sample_conversation_turn, mock_llm_response
    ):
        """Test context preparation with conversation history."""
        # Setup
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        minimal_state["conversation_history"] = [sample_conversation_turn]

        # Execute
        result = await prepare_context_node(minimal_state)

        # Assert
        assert "enhanced_query" in result
        assert result["enhanced_query"] == "Enhanced query with context"
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy")
    async def test_prepare_context_llm_failure(
        self, mock_get_llm, minimal_state, sample_conversation_turn
    ):
        """Test context preparation fallback on LLM failure."""
        # Setup
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM error"))
        mock_get_llm.return_value = mock_llm

        minimal_state["conversation_history"] = [sample_conversation_turn]

        # Execute
        result = await prepare_context_node(minimal_state)

        # Assert - should fall back to original query
        assert result["enhanced_query"] == minimal_state["current_query"]


class TestSearchNode:
    """Tests for search_node."""

    @pytest.mark.asyncio
    @patch("src.components.vector_search.qdrant_client.get_qdrant_client")
    @patch("src.components.vector_search.embeddings.get_embedding_service")
    async def test_search_node_success(self, mock_get_embeddings, mock_get_qdrant, minimal_state):
        """Test successful document search."""
        # Setup
        mock_embeddings = AsyncMock()
        mock_embeddings.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_get_embeddings.return_value = mock_embeddings

        # Mock Qdrant search result
        mock_scored_point = MagicMock()
        mock_scored_point.score = 0.95
        mock_scored_point.payload = {
            "text": "AEGIS RAG is a system...",
            "title": "CLAUDE.md",
            "source": "docs/CLAUDE.md",
            "metadata": {},
        }

        mock_qdrant = MagicMock()
        mock_qdrant.async_client.search = AsyncMock(return_value=[mock_scored_point])
        mock_get_qdrant.return_value = mock_qdrant

        minimal_state["enhanced_query"] = "What are performance metrics?"
        minimal_state["namespace"] = "default"

        # Execute
        result = await search_node(minimal_state)

        # Assert
        assert "current_context" in result
        assert len(result["current_context"]) == 1
        assert result["current_context"][0]["text"] == "AEGIS RAG is a system..."
        assert result["current_context"][0]["score"] == 0.95

    @pytest.mark.asyncio
    @patch("src.components.vector_search.qdrant_client.get_qdrant_client")
    @patch("src.components.vector_search.embeddings.get_embedding_service")
    async def test_search_node_failure(self, mock_get_embeddings, mock_get_qdrant, minimal_state):
        """Test search node failure handling."""
        # Setup
        mock_embeddings = AsyncMock()
        mock_embeddings.embed_query = AsyncMock(side_effect=Exception("Embedding error"))
        mock_get_embeddings.return_value = mock_embeddings

        minimal_state["enhanced_query"] = "What are performance metrics?"

        # Execute
        result = await search_node(minimal_state)

        # Assert - should return empty contexts on failure
        assert result["current_context"] == []


class TestDetectContradictionsNode:
    """Tests for detect_contradictions_node."""

    @pytest.mark.asyncio
    async def test_detect_contradictions_disabled(self, minimal_state):
        """Test contradiction detection when disabled."""
        minimal_state["detect_contradictions"] = False

        result = await detect_contradictions_node(minimal_state)

        assert result["contradictions"] == []

    @pytest.mark.asyncio
    async def test_detect_contradictions_no_history(self, minimal_state):
        """Test contradiction detection with no history."""
        minimal_state["detect_contradictions"] = True
        minimal_state["conversation_history"] = []

        result = await detect_contradictions_node(minimal_state)

        assert result["contradictions"] == []

    @pytest.mark.asyncio
    @patch("src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy")
    async def test_detect_contradictions_none_found(
        self, mock_get_llm, minimal_state, sample_conversation_turn
    ):
        """Test contradiction detection when no contradictions exist."""
        # Setup
        mock_llm_response = MagicMock()
        mock_llm_response.content = "NO CONTRADICTIONS"

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        minimal_state["detect_contradictions"] = True
        minimal_state["conversation_history"] = [sample_conversation_turn]
        minimal_state["current_context"] = [
            {
                "text": "AEGIS RAG performance is excellent.",
                "score": 0.9,
            }
        ]

        # Execute
        result = await detect_contradictions_node(minimal_state)

        # Assert
        assert result["contradictions"] == []

    @pytest.mark.asyncio
    @patch("src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy")
    async def test_detect_contradictions_found(
        self, mock_get_llm, minimal_state, sample_conversation_turn
    ):
        """Test contradiction detection when contradictions exist."""
        # Setup
        mock_llm_response = MagicMock()
        mock_llm_response.content = """CONTRADICTION: Performance metrics differ
CURRENT: System latency is 200ms
PREVIOUS: System latency is under 100ms
TURN: 1
CONFIDENCE: 0.9"""

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        minimal_state["detect_contradictions"] = True
        minimal_state["conversation_history"] = [sample_conversation_turn]
        minimal_state["current_context"] = [{"text": "System latency is 200ms", "score": 0.9}]

        # Execute
        result = await detect_contradictions_node(minimal_state)

        # Assert
        assert len(result["contradictions"]) == 1
        contradiction = result["contradictions"][0]
        assert "200ms" in contradiction.current_info
        assert "100ms" in contradiction.previous_info
        assert contradiction.confidence == 0.9


class TestAnswerNode:
    """Tests for answer_node."""

    @pytest.mark.asyncio
    @patch("src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy")
    async def test_answer_node_success(self, mock_get_llm, minimal_state):
        """Test successful answer generation."""
        # Setup
        mock_llm_response = MagicMock()
        mock_llm_response.content = "Based on the context, performance metrics are excellent."

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        minimal_state["current_context"] = [
            {"text": "AEGIS RAG has excellent performance metrics.", "score": 0.95}
        ]
        minimal_state["contradictions"] = []

        # Execute
        result = await answer_node(minimal_state)

        # Assert
        assert "answer" in result
        assert "performance metrics are excellent" in result["answer"]

    @pytest.mark.asyncio
    @patch("src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy")
    async def test_answer_node_with_contradictions(self, mock_get_llm, minimal_state):
        """Test answer generation with contradictions."""
        # Setup
        mock_llm_response = MagicMock()
        mock_llm_response.content = "I notice a contradiction in the data..."

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        minimal_state["current_context"] = [{"text": "Performance is excellent.", "score": 0.9}]
        minimal_state["contradictions"] = [
            Contradiction(
                current_info="Latency is 200ms",
                previous_info="Latency is 100ms",
                turn_index=0,
                confidence=0.9,
            )
        ]

        # Execute
        result = await answer_node(minimal_state)

        # Assert
        assert "answer" in result
        # Verify LLM was called with contradiction warning
        mock_llm.generate.assert_called_once()
        call_args = mock_llm.generate.call_args[0][0]
        assert "WARNING" in call_args.prompt


class TestUpdateMemoryNode:
    """Tests for update_memory_node."""

    @pytest.mark.asyncio
    async def test_update_memory_skip_non_threshold(self, minimal_state):
        """Test memory update skipped when not at threshold."""
        minimal_state["turn_number"] = 3  # Not divisible by 5

        result = await update_memory_node(minimal_state)

        assert result == {}

    @pytest.mark.asyncio
    @patch("src.components.memory.get_redis_memory")
    @patch("src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy")
    async def test_update_memory_at_threshold(
        self, mock_get_llm, mock_get_redis, minimal_state, sample_conversation_turn
    ):
        """Test memory update at turn threshold (every 5 turns)."""
        # Setup
        mock_llm_response = MagicMock()
        mock_llm_response.content = "Summary: Discussion about AEGIS RAG system architecture."

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        mock_redis = AsyncMock()
        mock_redis.store = AsyncMock(return_value=True)
        mock_get_redis.return_value = mock_redis

        minimal_state["turn_number"] = 5  # Divisible by 5
        minimal_state["conversation_history"] = [sample_conversation_turn] * 5

        # Execute
        result = await update_memory_node(minimal_state)

        # Assert
        assert "memory_summary" in result
        assert "AEGIS RAG system architecture" in result["memory_summary"]
        mock_redis.store.assert_called_once()
