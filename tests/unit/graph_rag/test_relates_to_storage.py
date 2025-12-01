"""Unit tests for RELATES_TO relationship storage in Neo4j.

Sprint 34 Feature 34.1: LightRAG Schema Alignment (ADR-040)

Tests the _store_relations_to_neo4j() method which creates RELATES_TO
relationships between entities in Neo4j using the RelationExtractor output.
"""

import pytest

from src.components.graph_rag.lightrag_wrapper import LightRAGClient


@pytest.mark.asyncio
async def test_store_relations_to_neo4j_success(mocker):
    """Test successful storage of RELATES_TO relationships."""
    # Mock Neo4j session and driver
    mock_session = mocker.MagicMock()
    mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = mocker.AsyncMock(return_value=None)

    mock_result = mocker.AsyncMock()
    mock_record = {"created": 3}
    mock_result.single = mocker.AsyncMock(return_value=mock_record)
    mock_session.run = mocker.AsyncMock(return_value=mock_result)

    mock_driver = mocker.MagicMock()
    mock_driver.session = mocker.MagicMock(return_value=mock_session)

    # Mock LightRAG initialization
    mock_graph = mocker.MagicMock()
    mock_graph._driver = mock_driver

    mock_rag = mocker.MagicMock()
    mock_rag.chunk_entity_relation_graph = mock_graph

    # Create client and mock initialization
    client = LightRAGClient()
    client._initialized = True
    client.rag = mock_rag

    # Test data
    relations = [
        {"source": "Alex", "target": "TechCorp", "description": "Works at", "strength": 8},
        {"source": "Jordan", "target": "TechCorp", "description": "Works at", "strength": 8},
        {"source": "Alex", "target": "Jordan", "description": "Colleagues", "strength": 7},
    ]
    chunk_id = "abc123def456"

    # Call method
    result = await client._store_relations_to_neo4j(relations=relations, chunk_id=chunk_id)

    # Assertions
    assert result == 3
    mock_session.run.assert_called_once()

    # Verify Cypher query structure
    call_args = mock_session.run.call_args
    cypher_query = call_args[0][0]
    assert "UNWIND $relations AS rel" in cypher_query
    assert "MATCH (e1:base {entity_name: rel.source})" in cypher_query
    assert "MATCH (e2:base {entity_name: rel.target})" in cypher_query
    assert "MERGE (e1)-[r:RELATES_TO]->(e2)" in cypher_query
    assert "r.weight = toFloat(rel.strength) / 10.0" in cypher_query
    assert "r.description = rel.description" in cypher_query
    assert "r.source_chunk_id = $chunk_id" in cypher_query

    # Verify relations parameter structure
    relations_param = call_args[1]["relations"]
    assert len(relations_param) == 3
    assert relations_param[0]["source"] == "Alex"
    assert relations_param[0]["target"] == "TechCorp"
    assert relations_param[0]["description"] == "Works at"
    assert relations_param[0]["strength"] == 8


@pytest.mark.asyncio
async def test_store_relations_to_neo4j_empty_list(mocker):
    """Test that empty relations list returns 0 without Neo4j call."""
    client = LightRAGClient()
    client._initialized = True

    # Call with empty relations
    result = await client._store_relations_to_neo4j(relations=[], chunk_id="abc123")

    # Should return 0 immediately without Neo4j call
    assert result == 0


@pytest.mark.asyncio
async def test_store_relations_to_neo4j_missing_entities(mocker):
    """Test that relations with missing entities are skipped."""
    # Mock Neo4j session - simulate MATCH returning no nodes
    mock_session = mocker.MagicMock()
    mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = mocker.AsyncMock(return_value=None)

    mock_result = mocker.AsyncMock()
    mock_record = {"created": 0}  # No relationships created
    mock_result.single = mocker.AsyncMock(return_value=mock_record)
    mock_session.run = mocker.AsyncMock(return_value=mock_result)

    mock_driver = mocker.MagicMock()
    mock_driver.session = mocker.MagicMock(return_value=mock_session)

    # Mock LightRAG initialization
    mock_graph = mocker.MagicMock()
    mock_graph._driver = mock_driver

    mock_rag = mocker.MagicMock()
    mock_rag.chunk_entity_relation_graph = mock_graph

    # Create client and mock initialization
    client = LightRAGClient()
    client._initialized = True
    client.rag = mock_rag

    # Test data with non-existent entities
    relations = [
        {
            "source": "NonExistentEntity1",
            "target": "NonExistentEntity2",
            "description": "Related",
            "strength": 5,
        }
    ]
    chunk_id = "abc123"

    # Call method
    result = await client._store_relations_to_neo4j(relations=relations, chunk_id=chunk_id)

    # Should return 0 (no relationships created)
    assert result == 0
    mock_session.run.assert_called_once()


@pytest.mark.asyncio
async def test_store_relations_to_neo4j_not_initialized():
    """Test that method raises error when LightRAG not initialized."""
    client = LightRAGClient()
    client._initialized = False

    relations = [{"source": "A", "target": "B", "description": "Related", "strength": 5}]

    with pytest.raises(Exception):  # Should raise during _ensure_initialized or RuntimeError
        await client._store_relations_to_neo4j(relations=relations, chunk_id="abc123")


@pytest.mark.asyncio
async def test_store_relations_to_neo4j_default_strength(mocker):
    """Test that missing strength field defaults to 5."""
    # Mock Neo4j session
    mock_session = mocker.MagicMock()
    mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = mocker.AsyncMock(return_value=None)

    mock_result = mocker.AsyncMock()
    mock_record = {"created": 1}
    mock_result.single = mocker.AsyncMock(return_value=mock_record)
    mock_session.run = mocker.AsyncMock(return_value=mock_result)

    mock_driver = mocker.MagicMock()
    mock_driver.session = mocker.MagicMock(return_value=mock_session)

    # Mock LightRAG initialization
    mock_graph = mocker.MagicMock()
    mock_graph._driver = mock_driver

    mock_rag = mocker.MagicMock()
    mock_rag.chunk_entity_relation_graph = mock_graph

    # Create client and mock initialization
    client = LightRAGClient()
    client._initialized = True
    client.rag = mock_rag

    # Test data without strength field
    relations = [{"source": "Alex", "target": "TechCorp", "description": "Works at"}]
    chunk_id = "abc123"

    # Call method
    result = await client._store_relations_to_neo4j(relations=relations, chunk_id=chunk_id)

    # Verify default strength is 5
    call_args = mock_session.run.call_args
    relations_param = call_args[1]["relations"]
    assert relations_param[0]["strength"] == 5


@pytest.mark.asyncio
async def test_store_relations_to_neo4j_default_description(mocker):
    """Test that missing description field defaults to empty string."""
    # Mock Neo4j session
    mock_session = mocker.MagicMock()
    mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = mocker.AsyncMock(return_value=None)

    mock_result = mocker.AsyncMock()
    mock_record = {"created": 1}
    mock_result.single = mocker.AsyncMock(return_value=mock_record)
    mock_session.run = mocker.AsyncMock(return_value=mock_result)

    mock_driver = mocker.MagicMock()
    mock_driver.session = mocker.MagicMock(return_value=mock_session)

    # Mock LightRAG initialization
    mock_graph = mocker.MagicMock()
    mock_graph._driver = mock_driver

    mock_rag = mocker.MagicMock()
    mock_rag.chunk_entity_relation_graph = mock_graph

    # Create client and mock initialization
    client = LightRAGClient()
    client._initialized = True
    client.rag = mock_rag

    # Test data without description field
    relations = [{"source": "Alex", "target": "TechCorp", "strength": 8}]
    chunk_id = "abc123"

    # Call method
    result = await client._store_relations_to_neo4j(relations=relations, chunk_id=chunk_id)

    # Verify default description is empty string
    call_args = mock_session.run.call_args
    relations_param = call_args[1]["relations"]
    assert relations_param[0]["description"] == ""
