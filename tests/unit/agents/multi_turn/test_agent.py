"""Unit tests for MultiTurnAgent.

Sprint 63 Feature 63.1: Multi-Turn RAG Template (13 SP)

Tests for the main MultiTurnAgent class and workflow.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.multi_turn.agent import MultiTurnAgent


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing."""
    return [
        {
            "query": "What is AEGIS RAG?",
            "answer": "AEGIS RAG is an agentic RAG system.",
            "sources": [
                {
                    "text": "AEGIS RAG architecture...",
                    "title": "CLAUDE.md",
                    "source": "docs/CLAUDE.md",
                    "score": 0.95,
                    "metadata": {},
                }
            ],
            "timestamp": datetime.now(UTC).isoformat(),
        }
    ]


class TestMultiTurnAgent:
    """Tests for MultiTurnAgent."""

    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        agent = MultiTurnAgent()

        assert agent.graph is not None

    @pytest.mark.asyncio
    @patch("src.agents.multi_turn.agent.MultiTurnAgent._compile_graph")
    async def test_process_turn_empty_history(self, mock_compile_graph):
        """Test processing turn with empty conversation history."""
        # Setup mock graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "answer": "AEGIS RAG is an agentic RAG system.",
                "current_context": [
                    {
                        "text": "AEGIS RAG description...",
                        "title": "CLAUDE.md",
                        "source": "docs/CLAUDE.md",
                        "score": 0.95,
                        "metadata": {},
                    }
                ],
                "contradictions": [],
                "memory_summary": None,
                "turn_number": 1,
                "enhanced_query": "What is AEGIS RAG?",
            }
        )
        mock_compile_graph.return_value = mock_graph

        agent = MultiTurnAgent()

        # Execute
        result = await agent.process_turn(
            query="What is AEGIS RAG?",
            conversation_id="test-conv-123",
            conversation_history=[],
            namespace="default",
        )

        # Assert
        assert result["answer"] == "AEGIS RAG is an agentic RAG system."
        assert result["conversation_id"] == "test-conv-123"
        assert result["turn_number"] == 1
        assert len(result["sources"]) == 1
        assert result["contradictions"] == []
        assert "latency_seconds" in result["metadata"]

    @pytest.mark.asyncio
    @patch("src.agents.multi_turn.agent.MultiTurnAgent._compile_graph")
    async def test_process_turn_with_history(self, mock_compile_graph, sample_conversation_history):
        """Test processing turn with existing conversation history."""
        # Setup mock graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "answer": "Performance metrics are excellent.",
                "current_context": [
                    {
                        "text": "AEGIS RAG has excellent performance.",
                        "score": 0.9,
                        "metadata": {},
                    }
                ],
                "contradictions": [],
                "memory_summary": None,
                "turn_number": 2,
                "enhanced_query": "What are the performance metrics for AEGIS RAG?",
            }
        )
        mock_compile_graph.return_value = mock_graph

        agent = MultiTurnAgent()

        # Execute
        result = await agent.process_turn(
            query="What about performance?",
            conversation_id="test-conv-123",
            conversation_history=sample_conversation_history,
            namespace="default",
        )

        # Assert
        assert result["turn_number"] == 2
        assert "performance" in result["answer"].lower()

    @pytest.mark.asyncio
    @patch("src.agents.multi_turn.agent.MultiTurnAgent._compile_graph")
    async def test_process_turn_with_contradictions(self, mock_compile_graph):
        """Test processing turn that detects contradictions."""
        # Setup mock graph with contradictions
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "answer": "I notice a contradiction in the performance data.",
                "current_context": [{"text": "Performance data...", "score": 0.9}],
                "contradictions": [
                    {
                        "current_info": "Latency is 200ms",
                        "previous_info": "Latency is 100ms",
                        "turn_index": 0,
                        "confidence": 0.9,
                        "explanation": "Performance metrics differ",
                    }
                ],
                "memory_summary": None,
                "turn_number": 2,
                "enhanced_query": "Performance metrics",
            }
        )
        mock_compile_graph.return_value = mock_graph

        agent = MultiTurnAgent()

        # Execute
        result = await agent.process_turn(
            query="What are the metrics?",
            conversation_id="test-conv-123",
            conversation_history=[],
            namespace="default",
        )

        # Assert
        assert len(result["contradictions"]) == 1
        assert result["contradictions"][0].confidence == 0.9

    @pytest.mark.asyncio
    @patch("src.agents.multi_turn.agent.MultiTurnAgent._compile_graph")
    async def test_process_turn_error_handling(self, mock_compile_graph):
        """Test error handling during turn processing."""
        # Setup mock graph that raises exception
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph execution error"))
        mock_compile_graph.return_value = mock_graph

        agent = MultiTurnAgent()

        # Execute and expect exception
        with pytest.raises(Exception) as exc_info:
            await agent.process_turn(
                query="What is AEGIS RAG?",
                conversation_id="test-conv-123",
                conversation_history=[],
                namespace="default",
            )

        assert "Graph execution error" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("src.agents.multi_turn.agent.MultiTurnAgent._compile_graph")
    async def test_process_turn_max_history_limit(
        self, mock_compile_graph, sample_conversation_history
    ):
        """Test that max_history_turns is respected."""
        # Setup mock graph
        mock_graph = AsyncMock()

        def check_history_length(state):
            # Verify that conversation history is limited
            assert len(state["conversation_history"]) <= state["max_history_turns"]
            return {
                "answer": "Answer",
                "current_context": [],
                "contradictions": [],
                "memory_summary": None,
                "turn_number": 6,
                "enhanced_query": "Query",
            }

        mock_graph.ainvoke = AsyncMock(side_effect=check_history_length)
        mock_compile_graph.return_value = mock_graph

        agent = MultiTurnAgent()

        # Create long history (10 turns)
        long_history = sample_conversation_history * 10

        # Execute with max_history_turns=5
        result = await agent.process_turn(
            query="What is AEGIS RAG?",
            conversation_id="test-conv-123",
            conversation_history=long_history,
            namespace="default",
            max_history_turns=5,
        )

        # Assert
        assert result["turn_number"] == 6
