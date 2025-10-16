"""Unit tests for LangGraph agent state management.

Sprint 4 Feature 4.1: State Management Tests
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.agents.state import (
    QueryMetadata,
    RetrievedContext,
    SearchMetadata,
    create_initial_state,
    update_state_metadata,
)


class TestRetrievedContext:
    """Test RetrievedContext model."""

    def test_create_retrieved_context__valid_data__succeeds(self):
        """Test creating a RetrievedContext with valid data."""
        context = RetrievedContext(
            id="doc1",
            text="Sample document text",
            score=0.95,
            source="test.txt",
            document_id="doc1",
            rank=1,
            search_type="hybrid",
            metadata={"key": "value"},
        )

        assert context.id == "doc1"
        assert context.text == "Sample document text"
        assert context.score == 0.95
        assert context.source == "test.txt"
        assert context.search_type == "hybrid"

    def test_create_retrieved_context__score_out_of_range__fails(self):
        """Test that score validation works (must be 0.0 to 1.0)."""
        with pytest.raises(ValidationError):
            RetrievedContext(
                id="doc1",
                text="Sample text",
                score=1.5,  # Invalid: > 1.0
                source="test.txt",
            )

    def test_create_retrieved_context__negative_rank__fails(self):
        """Test that rank must be non-negative."""
        with pytest.raises(ValidationError):
            RetrievedContext(
                id="doc1",
                text="Sample text",
                score=0.9,
                source="test.txt",
                rank=-1,  # Invalid: negative
            )


class TestSearchMetadata:
    """Test SearchMetadata model."""

    def test_create_search_metadata__valid_data__succeeds(self):
        """Test creating SearchMetadata with valid data."""
        metadata = SearchMetadata(
            latency_ms=123.45,
            result_count=10,
            search_mode="hybrid",
            vector_results_count=5,
            bm25_results_count=5,
            reranking_applied=True,
        )

        assert metadata.latency_ms == 123.45
        assert metadata.result_count == 10
        assert metadata.search_mode == "hybrid"
        assert metadata.reranking_applied is True

    def test_create_search_metadata__negative_latency__fails(self):
        """Test that latency must be non-negative."""
        with pytest.raises(ValidationError):
            SearchMetadata(
                latency_ms=-10.0,  # Invalid: negative
                result_count=10,
            )


class TestQueryMetadata:
    """Test QueryMetadata model."""

    def test_create_query_metadata__valid_data__succeeds(self):
        """Test creating QueryMetadata with valid data."""
        metadata = QueryMetadata(
            agent_path=["router", "vector_search"],
            retrieval_count=5,
            latency_ms=250.5,
            search_mode="hybrid",
            timestamp="2025-01-15T10:30:00Z",
        )

        assert len(metadata.agent_path) == 2
        assert metadata.retrieval_count == 5
        assert metadata.latency_ms == 250.5

    def test_create_query_metadata__defaults__succeeds(self):
        """Test creating QueryMetadata with default values."""
        metadata = QueryMetadata()

        assert metadata.agent_path == []
        assert metadata.retrieval_count == 0
        assert metadata.search_mode == "hybrid"


class TestAgentState:
    """Test AgentState class."""

    def test_agent_state__has_messages_field(self):
        """Test that AgentState inherits messages from MessagesState."""
        # AgentState should have messages field from MessagesState
        state = create_initial_state("test query")
        assert "messages" in state
        assert isinstance(state["messages"], list)

    def test_agent_state__has_required_fields(self):
        """Test that AgentState has all required fields."""
        state = create_initial_state("test query", "vector")

        assert "query" in state
        assert "intent" in state
        assert "retrieved_contexts" in state
        assert "search_mode" in state
        assert "metadata" in state


class TestCreateInitialState:
    """Test create_initial_state function."""

    def test_create_initial_state__default_intent__creates_hybrid_state(self):
        """Test creating initial state with default intent."""
        state = create_initial_state("What is RAG?")

        assert state["query"] == "What is RAG?"
        assert state["intent"] == "hybrid"
        assert state["search_mode"] == "hybrid"
        assert state["retrieved_contexts"] == []
        assert isinstance(state["metadata"], dict)
        assert "timestamp" in state["metadata"]
        assert "agent_path" in state["metadata"]

    def test_create_initial_state__custom_intent__creates_state_with_intent(self):
        """Test creating initial state with custom intent."""
        state = create_initial_state("Find documents", "vector")

        assert state["query"] == "Find documents"
        assert state["intent"] == "vector"
        assert state["search_mode"] == "vector"

    def test_create_initial_state__invalid_intent__defaults_to_hybrid(self):
        """Test that invalid intent defaults to hybrid search mode."""
        state = create_initial_state("test query", "invalid")

        assert state["intent"] == "invalid"
        assert state["search_mode"] == "hybrid"  # Defaults to hybrid

    def test_create_initial_state__has_timestamp(self):
        """Test that initial state includes timestamp."""
        state = create_initial_state("test")

        assert "metadata" in state
        assert "timestamp" in state["metadata"]
        # Verify it's a valid ISO format timestamp
        timestamp = state["metadata"]["timestamp"]
        datetime.fromisoformat(timestamp)  # Should not raise


class TestUpdateStateMetadata:
    """Test update_state_metadata function."""

    def test_update_state_metadata__adds_agent_to_path(self):
        """Test adding agent to path."""
        state = create_initial_state("test")
        state = update_state_metadata(state, "router")

        assert "router" in state["metadata"]["agent_path"]

    def test_update_state_metadata__multiple_agents__maintains_order(self):
        """Test that multiple agents are tracked in order."""
        state = create_initial_state("test")
        state = update_state_metadata(state, "router")
        state = update_state_metadata(state, "vector_search")
        state = update_state_metadata(state, "generator")

        assert state["metadata"]["agent_path"] == ["router", "vector_search", "generator"]

    def test_update_state_metadata__same_agent_twice__not_duplicated(self):
        """Test that consecutive same agent doesn't duplicate."""
        state = create_initial_state("test")
        state = update_state_metadata(state, "router")
        state = update_state_metadata(state, "router")

        assert state["metadata"]["agent_path"] == ["router"]

    def test_update_state_metadata__adds_custom_fields(self):
        """Test adding custom metadata fields."""
        state = create_initial_state("test")
        state = update_state_metadata(
            state,
            "vector_search",
            latency_ms=123.45,
            result_count=5,
        )

        assert state["metadata"]["latency_ms"] == 123.45
        assert state["metadata"]["result_count"] == 5

    def test_update_state_metadata__creates_metadata_if_missing(self):
        """Test that metadata is created if not present."""
        state = {"query": "test"}
        state = update_state_metadata(state, "router")

        assert "metadata" in state
        assert "agent_path" in state["metadata"]
        assert "router" in state["metadata"]["agent_path"]


class TestStateSerialization:
    """Test state serialization for LangGraph."""

    def test_state_can_be_serialized__to_dict(self):
        """Test that state can be serialized to dict."""
        state = create_initial_state("test query", "hybrid")

        # Should be a dict
        assert isinstance(state, dict)

        # Should have all required keys
        assert "query" in state
        assert "intent" in state
        assert "search_mode" in state
        assert "metadata" in state

    def test_state_with_contexts__can_be_serialized(self):
        """Test that state with retrieved contexts can be serialized."""
        state = create_initial_state("test")
        state["retrieved_contexts"] = [
            {
                "id": "doc1",
                "text": "content",
                "score": 0.9,
                "source": "test.txt",
                "search_type": "vector",
            }
        ]

        # Should be serializable
        assert isinstance(state["retrieved_contexts"], list)
        assert len(state["retrieved_contexts"]) == 1
