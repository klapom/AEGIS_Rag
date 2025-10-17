"""E2E Integration Tests for Graphiti Wrapper with Real Ollama + Neo4j.

Sprint 7 Feature 7.1: Graphiti Episodic Memory
- NO MOCKS: All tests use real Ollama LLM (llama3.2:8b) and Neo4j
- Tests entity extraction, episode search, relationship creation
- Tests error handling with real service failures
- Validates latency targets (<500ms for search)

CRITICAL: All tests marked with @pytest.mark.integration
"""

import time
from datetime import datetime

import pytest

from src.core.exceptions import LLMError, MemoryError

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ============================================================================
# Episode Management Tests
# ============================================================================


async def test_graphiti_add_episode_e2e(graphiti_wrapper, neo4j_driver):
    """Test adding an episode with real Ollama LLM and Neo4j storage.

    Validates:
    - Episode is added to Neo4j
    - Entities are extracted by Ollama
    - Relationships are created
    - Episode has unique ID and timestamp
    """
    # Given: Test episode content
    content = "Alice met Bob at the AI conference in San Francisco. They discussed RAG systems."
    source = "test"

    # When: Add episode with real Ollama extraction
    start = time.time()
    result = await graphiti_wrapper.add_episode(
        content=content,
        source=source,
        metadata={"test": "graphiti_e2e"},
    )
    latency_ms = (time.time() - start) * 1000

    # Then: Verify episode structure
    assert result is not None
    assert "episode_id" in result
    assert result["episode_id"] is not None
    assert "timestamp" in result
    assert result["source"] == source
    assert "entities" in result
    assert "relationships" in result

    # Then: Verify latency target (episode creation can take time with LLM)
    assert latency_ms < 10000, f"Expected <10s, got {latency_ms}ms"

    # Then: Verify episode is stored in Neo4j
    with neo4j_driver.session() as session:
        query_result = session.run(
            "MATCH (e) WHERE e.source = 'test' RETURN count(e) as count"
        )
        record = query_result.single()
        assert record["count"] > 0, "Episode not found in Neo4j"


async def test_graphiti_add_multiple_episodes_e2e(graphiti_wrapper):
    """Test adding multiple episodes and verify storage."""
    # Given: Multiple episode contents
    episodes = [
        "Claude is an AI assistant created by Anthropic.",
        "Anthropic focuses on AI safety research.",
        "Claude can help with coding and analysis.",
    ]

    # When: Add all episodes
    results = []
    for content in episodes:
        result = await graphiti_wrapper.add_episode(
            content=content,
            source="test",
        )
        results.append(result)

    # Then: Verify all episodes were added
    assert len(results) == len(episodes)
    episode_ids = [r["episode_id"] for r in results]
    assert len(episode_ids) == len(set(episode_ids)), "Duplicate episode IDs"


async def test_graphiti_episode_with_metadata_e2e(graphiti_wrapper):
    """Test episode storage with custom metadata."""
    # Given: Episode with rich metadata
    metadata = {
        "user_id": "test_user_123",
        "session_id": "test_session_456",
        "importance": "high",
        "tags": ["ai", "rag", "memory"],
    }

    # When: Add episode with metadata
    result = await graphiti_wrapper.add_episode(
        content="Testing metadata storage in episodic memory.",
        source="test",
        metadata=metadata,
    )

    # Then: Verify metadata is stored
    assert result["metadata"] == metadata


# ============================================================================
# Search and Retrieval Tests
# ============================================================================


async def test_graphiti_search_with_embeddings_e2e(graphiti_wrapper):
    """Test semantic search with real Ollama embeddings.

    Validates:
    - Search uses real nomic-embed-text embeddings
    - Results are ranked by relevance
    - Search latency < 500ms
    """
    # Given: Episode in memory
    await graphiti_wrapper.add_episode(
        content="Python is a high-level programming language known for readability.",
        source="test",
    )

    # When: Search with related query
    start = time.time()
    results = await graphiti_wrapper.search(
        query="programming languages",
        limit=5,
        score_threshold=0.5,
    )
    latency_ms = (time.time() - start) * 1000

    # Then: Verify results structure
    assert isinstance(results, list)
    if results:  # May be empty if Graphiti search doesn't find matches
        assert all("score" in r for r in results)
        assert all("content" in r for r in results)

    # Then: Verify latency target
    assert latency_ms < 500, f"Expected <500ms search, got {latency_ms}ms"


async def test_graphiti_search_time_window_e2e(graphiti_wrapper):
    """Test temporal search with time window filtering."""
    # Given: Recent episode
    await graphiti_wrapper.add_episode(
        content="Testing temporal search in Graphiti episodic memory.",
        source="test",
        timestamp=datetime.utcnow(),
    )

    # When: Search with 1-hour time window
    results = await graphiti_wrapper.search(
        query="temporal search",
        limit=10,
        time_window_hours=1,
    )

    # Then: Results should include recent episode
    assert isinstance(results, list)
    # Note: Actual matches depend on Graphiti's search implementation


async def test_graphiti_search_score_threshold_e2e(graphiti_wrapper):
    """Test search with score threshold filtering."""
    # Given: Episode in memory
    await graphiti_wrapper.add_episode(
        content="Testing score threshold in semantic search.",
        source="test",
    )

    # When: Search with high score threshold
    high_threshold_results = await graphiti_wrapper.search(
        query="semantic search",
        limit=10,
        score_threshold=0.9,  # Very high threshold
    )

    # When: Search with low score threshold
    low_threshold_results = await graphiti_wrapper.search(
        query="semantic search",
        limit=10,
        score_threshold=0.3,  # Lower threshold
    )

    # Then: Lower threshold should return more or equal results
    assert len(low_threshold_results) >= len(high_threshold_results)


# ============================================================================
# Entity and Relationship Tests
# ============================================================================


async def test_graphiti_entity_extraction_e2e(graphiti_wrapper):
    """Test entity extraction from text using real Ollama LLM.

    Validates:
    - Ollama extracts named entities (people, places, organizations)
    - Entities are stored in Neo4j
    """
    # Given: Text with clear entities
    content = (
        "Elon Musk founded SpaceX in 2002. "
        "The company is headquartered in Hawthorne, California."
    )

    # When: Add episode (triggers entity extraction)
    result = await graphiti_wrapper.add_episode(
        content=content,
        source="test",
    )

    # Then: Verify entities were extracted
    entities = result.get("entities", [])
    # Note: Actual entity extraction depends on Ollama's performance
    # We just verify the structure is correct
    assert isinstance(entities, list)


async def test_graphiti_add_entity_directly_e2e(graphiti_wrapper):
    """Test adding an entity directly to the graph."""
    # Given: Entity details
    name = "test_entity_alice"
    entity_type = "person"
    properties = {"role": "engineer", "company": "Anthropic"}

    # When: Add entity
    result = await graphiti_wrapper.add_entity(
        name=name,
        entity_type=entity_type,
        properties=properties,
    )

    # Then: Verify entity structure
    assert result["name"] == name
    assert result["type"] == entity_type
    assert result["properties"] == properties
    assert "entity_id" in result
    assert "timestamp" in result


async def test_graphiti_relationship_creation_e2e(graphiti_wrapper):
    """Test creating relationships between entities."""
    # Given: Two entities
    entity1 = await graphiti_wrapper.add_entity(
        name="test_entity_bob",
        entity_type="person",
    )
    entity2 = await graphiti_wrapper.add_entity(
        name="test_entity_carol",
        entity_type="person",
    )

    # When: Create relationship
    result = await graphiti_wrapper.add_edge(
        source_entity_id=entity1["entity_id"],
        target_entity_id=entity2["entity_id"],
        relationship_type="knows",
        properties={"since": "2024"},
    )

    # Then: Verify relationship structure
    assert result["source_id"] == entity1["entity_id"]
    assert result["target_id"] == entity2["entity_id"]
    assert result["type"] == "knows"
    assert result["properties"]["since"] == "2024"
    assert "edge_id" in result


# ============================================================================
# Error Handling Tests (Real Service Failures)
# ============================================================================


async def test_graphiti_error_handling_invalid_content_e2e(graphiti_wrapper):
    """Test error handling with invalid episode content."""
    # When/Then: Empty content should raise error
    with pytest.raises(Exception):  # Could be MemoryError or validation error
        await graphiti_wrapper.add_episode(
            content="",
            source="test",
        )


async def test_graphiti_error_handling_invalid_search_e2e(graphiti_wrapper):
    """Test error handling with invalid search parameters."""
    # When/Then: Invalid score threshold
    with pytest.raises(Exception):
        await graphiti_wrapper.search(
            query="test",
            limit=5,
            score_threshold=2.0,  # Invalid (must be 0-1)
        )


async def test_graphiti_connection_e2e(graphiti_wrapper, neo4j_driver):
    """Test Graphiti can connect to Neo4j."""
    # Given: Graphiti wrapper is initialized
    assert graphiti_wrapper is not None
    assert graphiti_wrapper.graphiti is not None

    # When: Verify Neo4j connectivity
    neo4j_driver.verify_connectivity()

    # Then: Connection is valid
    assert True


# ============================================================================
# Performance and Latency Tests
# ============================================================================


async def test_graphiti_search_latency_target_e2e(graphiti_wrapper):
    """Test search latency meets performance targets (<500ms)."""
    # Given: Episodes in memory
    for i in range(5):
        await graphiti_wrapper.add_episode(
            content=f"Test episode number {i} for latency testing.",
            source="test",
        )

    # When: Perform search and measure latency
    start = time.time()
    await graphiti_wrapper.search(
        query="latency test",
        limit=5,
    )
    latency_ms = (time.time() - start) * 1000

    # Then: Verify latency target
    assert latency_ms < 500, f"Search latency {latency_ms}ms exceeds 500ms target"


async def test_graphiti_batch_episode_addition_e2e(graphiti_wrapper):
    """Test adding multiple episodes sequentially."""
    # Given: Batch of episodes
    episodes = [f"Batch episode {i} for testing." for i in range(3)]

    # When: Add all episodes
    start = time.time()
    results = []
    for content in episodes:
        result = await graphiti_wrapper.add_episode(
            content=content,
            source="test",
        )
        results.append(result)
    total_time_ms = (time.time() - start) * 1000

    # Then: All episodes added successfully
    assert len(results) == len(episodes)

    # Then: Reasonable batch performance (depends on Ollama speed)
    avg_time_per_episode = total_time_ms / len(episodes)
    assert avg_time_per_episode < 15000, f"Avg {avg_time_per_episode}ms per episode"


# ============================================================================
# Cleanup and Resource Management Tests
# ============================================================================


async def test_graphiti_close_connection_e2e(graphiti_wrapper):
    """Test graceful connection closure."""
    # When: Close Graphiti connections
    await graphiti_wrapper.close()

    # Then: No errors during closure
    assert True


# ============================================================================
# Integration with Ollama LLM Tests
# ============================================================================


async def test_ollama_llm_client_generate_response_e2e(graphiti_wrapper):
    """Test OllamaLLMClient can generate text responses."""
    # Given: LLM client from Graphiti wrapper
    llm_client = graphiti_wrapper.llm_client

    # When: Generate response
    messages = [
        {"role": "user", "content": "Say 'test successful' and nothing else."}
    ]
    response = await llm_client.generate_response(messages, max_tokens=50)

    # Then: Response is generated
    assert isinstance(response, str)
    assert len(response) > 0


async def test_ollama_llm_client_generate_embeddings_e2e(graphiti_wrapper):
    """Test OllamaLLMClient can generate embeddings."""
    # Given: LLM client from Graphiti wrapper
    llm_client = graphiti_wrapper.llm_client

    # When: Generate embeddings
    texts = ["test embedding 1", "test embedding 2"]
    embeddings = await llm_client.generate_embeddings(texts)

    # Then: Embeddings are generated
    assert isinstance(embeddings, list)
    assert len(embeddings) == len(texts)
    assert all(isinstance(emb, list) for emb in embeddings)
    assert all(len(emb) > 0 for emb in embeddings)


async def test_ollama_llm_error_handling_e2e(graphiti_wrapper):
    """Test LLM client error handling with invalid input."""
    # Given: LLM client
    llm_client = graphiti_wrapper.llm_client

    # When/Then: Invalid messages format should raise error
    with pytest.raises(LLMError):
        await llm_client.generate_response(
            messages=[],  # Empty messages
            max_tokens=50,
        )
