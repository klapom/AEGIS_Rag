"""Unit tests for GraphitiClient (Sprint 27 Feature 27.2).

This module tests the GraphitiClient wrapper with mocked dependencies.

Tests cover:
- Episode addition and retrieval
- Memory search (semantic, temporal)
- Entity and edge management
- LLM generation via AegisLLMProxy
- Neo4j storage integration
- Error handling and cleanup
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.components.memory.graphiti_wrapper import GraphitiClient, OllamaLLMClient
from src.core.exceptions import MemoryError, LLMError


@pytest.fixture
def mock_graphiti_instance():
    """Mock Graphiti core instance."""
    mock = MagicMock()
    mock.add_episode = AsyncMock(
        return_value={
            "id": "episode_123",
            "entities": [{"name": "TestEntity", "type": "CONCEPT"}],
            "relationships": [{"source": "A", "target": "B", "type": "RELATES_TO"}],
        }
    )
    mock.search = AsyncMock(
        return_value=[
            {
                "id": "result_1",
                "type": "entity",
                "content": "Test content",
                "score": 0.95,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"source": "test"},
            }
        ]
    )
    mock.add_entity = AsyncMock(return_value={"id": "entity_456"})
    mock.add_edge = AsyncMock(return_value={"id": "edge_789"})
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    client = MagicMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_aegis_llm_proxy():
    """Mock AegisLLMProxy."""
    proxy = MagicMock()
    result = MagicMock()
    result.content = "Generated response from LLM"
    result.provider = "local"
    result.model = "llama3.2:3b"
    result.tokens_used = 150
    result.cost_usd = 0.0
    result.latency_ms = 250
    proxy.generate = AsyncMock(return_value=result)
    return proxy


@pytest.fixture
async def graphiti_client(mock_graphiti_instance, mock_neo4j_client, mock_aegis_llm_proxy):
    """GraphitiClient with mocked dependencies."""
    with patch(
        "src.components.memory.graphiti_wrapper.Graphiti", return_value=mock_graphiti_instance
    ):
        with patch(
            "src.components.memory.graphiti_wrapper.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.memory.graphiti_wrapper.get_aegis_llm_proxy",
                return_value=mock_aegis_llm_proxy,
            ):
                client = GraphitiClient()
                return client


# ============================================================================
# Episode Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_graphiti_add_episode(graphiti_client):
    """Test adding an episode to memory."""
    content = "User asked about AEGIS RAG architecture"
    source = "user_conversation"

    result = await graphiti_client.add_episode(content, source)

    assert "episode_id" in result
    assert result["episode_id"] == "episode_123"
    assert "entities" in result
    assert "relationships" in result
    assert len(result["entities"]) > 0


@pytest.mark.asyncio
async def test_graphiti_add_episode_with_timestamp(graphiti_client):
    """Test adding episode with explicit timestamp."""
    content = "Test episode content"
    timestamp = datetime(2025, 1, 1, 12, 0, 0)

    result = await graphiti_client.add_episode(content=content, timestamp=timestamp)

    assert result["timestamp"] == timestamp.isoformat()


@pytest.mark.asyncio
async def test_graphiti_add_episode_with_metadata(graphiti_client):
    """Test adding episode with custom metadata."""
    content = "Episode with metadata"
    metadata = {"user_id": "user123", "session_id": "session456"}

    result = await graphiti_client.add_episode(content=content, metadata=metadata)

    assert result["metadata"] == metadata


@pytest.mark.asyncio
async def test_graphiti_add_episode_failure(graphiti_client):
    """Test error handling during episode addition."""
    graphiti_client.graphiti.add_episode = AsyncMock(
        side_effect=Exception("Neo4j connection failed")
    )

    with pytest.raises(MemoryError, match="add_episode"):
        await graphiti_client.add_episode("Test content")


# ============================================================================
# Memory Search Tests
# ============================================================================


@pytest.mark.asyncio
async def test_graphiti_search_memory(graphiti_client):
    """Test semantic memory search."""
    query = "What are the main components?"

    results = await graphiti_client.search(query, limit=10)

    assert len(results) > 0
    assert results[0]["id"] == "result_1"
    assert results[0]["type"] == "entity"
    assert results[0]["score"] == 0.95


@pytest.mark.asyncio
async def test_graphiti_search_with_score_threshold(graphiti_client):
    """Test search with minimum score threshold."""
    query = "Test query"
    score_threshold = 0.8

    results = await graphiti_client.search(query=query, score_threshold=score_threshold)

    assert all(r["score"] >= score_threshold for r in results)


@pytest.mark.skip(reason="SearchConfig API changed - time_filter field removed from graphiti library")
@pytest.mark.asyncio
async def test_graphiti_search_with_time_window(graphiti_client):
    """Test temporal search with time window."""
    query = "Recent events"
    time_window_hours = 24

    results = await graphiti_client.search(query=query, time_window_hours=time_window_hours)

    # Verify search was executed with time filter
    assert graphiti_client.graphiti.search.called


@pytest.mark.asyncio
async def test_graphiti_search_empty_results(graphiti_client):
    """Test search returning no results."""
    graphiti_client.graphiti.search = AsyncMock(return_value=[])

    results = await graphiti_client.search("Non-existent topic")

    assert len(results) == 0


@pytest.mark.asyncio
async def test_graphiti_search_failure(graphiti_client):
    """Test error handling during search."""
    graphiti_client.graphiti.search = AsyncMock(side_effect=Exception("Search failed"))

    with pytest.raises(MemoryError, match="memory_search"):
        await graphiti_client.search("Test query")


# ============================================================================
# Entity Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_graphiti_add_entity(graphiti_client):
    """Test adding an entity to memory graph."""
    name = "AEGIS RAG"
    entity_type = "SYSTEM"
    properties = {"version": "1.0", "status": "active"}

    result = await graphiti_client.add_entity(
        name=name, entity_type=entity_type, properties=properties
    )

    assert result["entity_id"] == "entity_456"
    assert result["name"] == name
    assert result["type"] == entity_type
    assert result["properties"] == properties


@pytest.mark.asyncio
async def test_graphiti_add_entity_minimal(graphiti_client):
    """Test adding entity with minimal information."""
    result = await graphiti_client.add_entity(name="TestEntity", entity_type="CONCEPT")

    assert "entity_id" in result
    assert result["name"] == "TestEntity"


@pytest.mark.asyncio
async def test_graphiti_add_entity_failure(graphiti_client):
    """Test error handling during entity addition."""
    graphiti_client.graphiti.add_entity = AsyncMock(side_effect=Exception("Entity creation failed"))

    with pytest.raises(MemoryError, match="add_entity"):
        await graphiti_client.add_entity("TestEntity", "CONCEPT")


# ============================================================================
# Relationship Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_graphiti_add_edge(graphiti_client):
    """Test adding a relationship edge."""
    source_id = "entity_1"
    target_id = "entity_2"
    relationship_type = "CONNECTED_TO"
    properties = {"strength": 0.95}

    result = await graphiti_client.add_edge(
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=relationship_type,
        properties=properties,
    )

    assert result["edge_id"] == "edge_789"
    assert result["source_id"] == source_id
    assert result["target_id"] == target_id
    assert result["type"] == relationship_type


@pytest.mark.asyncio
async def test_graphiti_add_edge_minimal(graphiti_client):
    """Test adding edge with minimal information."""
    result = await graphiti_client.add_edge(
        source_entity_id="entity_a", target_entity_id="entity_b", relationship_type="RELATES_TO"
    )

    assert "edge_id" in result
    assert result["properties"] == {}


@pytest.mark.asyncio
async def test_graphiti_add_edge_failure(graphiti_client):
    """Test error handling during edge addition."""
    graphiti_client.graphiti.add_edge = AsyncMock(side_effect=Exception("Edge creation failed"))

    with pytest.raises(MemoryError, match="add_edge"):
        await graphiti_client.add_edge(
            source_entity_id="e1", target_entity_id="e2", relationship_type="TEST"
        )


# ============================================================================
# LLM Integration Tests (OllamaLLMClient)
# ============================================================================


@pytest.mark.asyncio
async def test_ollama_llm_client_generate_response(mock_aegis_llm_proxy):
    """Test LLM generation via AegisLLMProxy."""
    with patch(
        "src.components.memory.graphiti_wrapper.get_aegis_llm_proxy",
        return_value=mock_aegis_llm_proxy,
    ):
        client = OllamaLLMClient()

        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "What is memory consolidation?"},
        ]

        response = await client._generate_response(messages)

        assert response == "Generated response from LLM"
        assert mock_aegis_llm_proxy.generate.called


@pytest.mark.asyncio
async def test_ollama_llm_client_generate_failure(mock_aegis_llm_proxy):
    """Test LLM generation error handling."""
    mock_aegis_llm_proxy.generate = AsyncMock(side_effect=Exception("LLM failed"))

    with patch(
        "src.components.memory.graphiti_wrapper.get_aegis_llm_proxy",
        return_value=mock_aegis_llm_proxy,
    ):
        client = OllamaLLMClient()

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(LLMError, match="graphiti_memory_generation"):
            await client._generate_response(messages)


# ============================================================================
# Cleanup Tests
# ============================================================================


@pytest.mark.asyncio
async def test_graphiti_close(graphiti_client):
    """Test proper cleanup of connections."""
    await graphiti_client.close()

    assert graphiti_client.graphiti.close.called


@pytest.mark.asyncio
async def test_graphiti_aclose(graphiti_client):
    """Test async cleanup method."""
    await graphiti_client.aclose()

    assert graphiti_client.graphiti.close.called
    assert graphiti_client.neo4j_client.close.called
