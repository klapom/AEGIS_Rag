"""Unit tests for multi-turn API models.

Sprint 63 Feature 63.1: Multi-Turn RAG Template (13 SP)

Tests for Pydantic models used in multi-turn conversations.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.api.models.multi_turn import (
    Contradiction,
    ConversationTurn,
    MultiTurnRequest,
    MultiTurnResponse,
    Source,
)


class TestSource:
    """Tests for Source model."""

    def test_source_creation_valid(self):
        """Test creating a valid Source."""
        source = Source(
            text="AEGIS RAG is an agentic system.",
            title="CLAUDE.md",
            source="docs/CLAUDE.md",
            score=0.95,
            metadata={"section": "Overview"},
        )

        assert source.text == "AEGIS RAG is an agentic system."
        assert source.score == 0.95
        assert source.metadata["section"] == "Overview"

    def test_source_minimal(self):
        """Test creating Source with minimal fields."""
        source = Source(text="Sample text")

        assert source.text == "Sample text"
        assert source.title is None
        assert source.source is None
        assert source.score is None
        assert source.metadata == {}


class TestConversationTurn:
    """Tests for ConversationTurn model."""

    def test_conversation_turn_valid(self):
        """Test creating a valid ConversationTurn."""
        turn = ConversationTurn(
            query="What is AEGIS RAG?",
            answer="AEGIS RAG is an agentic RAG system.",
            sources=[Source(text="Sample text", score=0.9)],
            timestamp=datetime.now(UTC),
            intent="hybrid",
        )

        assert turn.query == "What is AEGIS RAG?"
        assert turn.answer == "AEGIS RAG is an agentic RAG system."
        assert len(turn.sources) == 1
        assert turn.intent == "hybrid"

    def test_conversation_turn_auto_timestamp(self):
        """Test ConversationTurn with auto-generated timestamp."""
        turn = ConversationTurn(
            query="What is AEGIS RAG?", answer="AEGIS RAG is an agentic RAG system."
        )

        assert turn.timestamp is not None
        assert isinstance(turn.timestamp, datetime)


class TestContradiction:
    """Tests for Contradiction model."""

    def test_contradiction_valid(self):
        """Test creating a valid Contradiction."""
        contradiction = Contradiction(
            current_info="Latency is 200ms",
            previous_info="Latency is 100ms",
            turn_index=2,
            confidence=0.9,
            explanation="Performance metrics differ",
        )

        assert contradiction.current_info == "Latency is 200ms"
        assert contradiction.previous_info == "Latency is 100ms"
        assert contradiction.turn_index == 2
        assert contradiction.confidence == 0.9

    def test_contradiction_confidence_validation(self):
        """Test Contradiction confidence validation (0-1)."""
        # Valid confidence
        contradiction = Contradiction(
            current_info="Info A",
            previous_info="Info B",
            turn_index=0,
            confidence=0.5,
        )
        assert contradiction.confidence == 0.5

        # Invalid confidence (too high)
        with pytest.raises(ValidationError):
            Contradiction(
                current_info="Info A",
                previous_info="Info B",
                turn_index=0,
                confidence=1.5,
            )

        # Invalid confidence (negative)
        with pytest.raises(ValidationError):
            Contradiction(
                current_info="Info A",
                previous_info="Info B",
                turn_index=0,
                confidence=-0.1,
            )


class TestMultiTurnRequest:
    """Tests for MultiTurnRequest model."""

    def test_multi_turn_request_valid(self):
        """Test creating a valid MultiTurnRequest."""
        request = MultiTurnRequest(
            query="What about performance?",
            conversation_id="conv-123",
            namespace="default",
            detect_contradictions=True,
            max_history_turns=5,
        )

        assert request.query == "What about performance?"
        assert request.conversation_id == "conv-123"
        assert request.namespace == "default"
        assert request.detect_contradictions is True
        assert request.max_history_turns == 5

    def test_multi_turn_request_defaults(self):
        """Test MultiTurnRequest with default values."""
        request = MultiTurnRequest(query="What is AEGIS RAG?", conversation_id="conv-123")

        assert request.namespace == "default"
        assert request.detect_contradictions is True
        assert request.max_history_turns == 5

    def test_multi_turn_request_validation(self):
        """Test MultiTurnRequest validation."""
        # Empty query
        with pytest.raises(ValidationError):
            MultiTurnRequest(query="", conversation_id="conv-123")

        # Query too long
        with pytest.raises(ValidationError):
            MultiTurnRequest(query="x" * 10000, conversation_id="conv-123")

        # max_history_turns too low
        with pytest.raises(ValidationError):
            MultiTurnRequest(
                query="What is AEGIS RAG?",
                conversation_id="conv-123",
                max_history_turns=0,
            )

        # max_history_turns too high
        with pytest.raises(ValidationError):
            MultiTurnRequest(
                query="What is AEGIS RAG?",
                conversation_id="conv-123",
                max_history_turns=50,
            )


class TestMultiTurnResponse:
    """Tests for MultiTurnResponse model."""

    def test_multi_turn_response_valid(self):
        """Test creating a valid MultiTurnResponse."""
        response = MultiTurnResponse(
            answer="AEGIS RAG is an agentic system.",
            query="What is AEGIS RAG?",
            conversation_id="conv-123",
            sources=[Source(text="Sample text", score=0.9)],
            contradictions=[
                Contradiction(
                    current_info="Info A",
                    previous_info="Info B",
                    turn_index=0,
                    confidence=0.8,
                )
            ],
            memory_summary="Discussion about AEGIS RAG architecture.",
            turn_number=3,
            metadata={"latency_seconds": 0.5},
        )

        assert response.answer == "AEGIS RAG is an agentic system."
        assert response.turn_number == 3
        assert len(response.sources) == 1
        assert len(response.contradictions) == 1
        assert response.memory_summary is not None

    def test_multi_turn_response_minimal(self):
        """Test MultiTurnResponse with minimal fields."""
        response = MultiTurnResponse(
            answer="Answer",
            query="Query",
            conversation_id="conv-123",
            turn_number=1,
        )

        assert response.answer == "Answer"
        assert response.sources == []
        assert response.contradictions == []
        assert response.memory_summary is None
        assert response.metadata == {}
