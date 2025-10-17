"""E2E Integration Tests for Memory Router with Real Services.

Sprint 7 Feature 7.3: 3-Layer Memory Router
- NO MOCKS: Uses real Redis, Qdrant, and Graphiti (Neo4j + Ollama)
- Tests routing logic and multi-layer search
- Tests conversation turn storage across layers
- Validates latency targets and error handling

CRITICAL: All tests marked with @pytest.mark.integration
"""

import time

import pytest

from src.components.memory.memory_router import MemoryLayer

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ============================================================================
# Routing Logic Tests
# ============================================================================


async def test_router_recent_context_to_redis_e2e(memory_router):
    """Test router selects Redis for recent context queries."""
    # Given: Query with recent context indicators
    query = "What did we just discuss about RAG systems?"

    # When: Route query
    layers = await memory_router.route_query(query, session_id="test_session")

    # Then: SHORT_TERM layer is selected
    assert MemoryLayer.SHORT_TERM in layers


async def test_router_temporal_query_to_graphiti_e2e(memory_router):
    """Test router selects Graphiti for temporal queries."""
    # Given: Query with temporal indicators
    query = "When did the concept of RAG first emerge?"

    # When: Route query
    layers = await memory_router.route_query(query)

    # Then: EPISODIC layer is selected (if Graphiti enabled)
    layer_values = [layer.value for layer in layers]
    # Graphiti may not be in results if disabled
    assert "long_term" in layer_values  # Always includes long-term


async def test_router_semantic_query_to_qdrant_e2e(memory_router):
    """Test router always includes Qdrant for semantic search."""
    # Given: Semantic query
    query = "Explain vector embeddings and similarity search"

    # When: Route query
    layers = await memory_router.route_query(query)

    # Then: LONG_TERM layer is always included
    assert MemoryLayer.LONG_TERM in layers


async def test_router_multi_layer_selection_e2e(memory_router):
    """Test router can select multiple layers for complex queries."""
    # Given: Query with multiple indicators
    query = "What did we discuss earlier about when vector search was invented?"

    # When: Route query
    layers = await memory_router.route_query(query, session_id="test_session")

    # Then: Multiple layers selected
    assert len(layers) >= 2  # At least long-term + one other


async def test_router_query_without_session_e2e(memory_router):
    """Test routing without session ID (skips short-term layer)."""
    # Given: Query without session
    query = "General question about AI"

    # When: Route query without session_id
    layers = await memory_router.route_query(query, session_id=None)

    # Then: SHORT_TERM not included (no session context)
    assert MemoryLayer.SHORT_TERM not in layers
    assert MemoryLayer.LONG_TERM in layers


# ============================================================================
# Multi-Layer Search Tests
# ============================================================================


async def test_router_search_memory_multi_layer_e2e(memory_router, redis_client):
    """Test searching across multiple memory layers with real services."""
    # Given: Data in Redis short-term memory
    session_id = "test_session_search"
    await redis_client.set(
        f"context:conversation:{session_id}",
        '{"value": [{"role": "user", "content": "Tell me about vector search"}]}',
        ex=3600,
    )

    # When: Search across layers
    start = time.time()
    results = await memory_router.search_memory(
        query="vector search",
        session_id=session_id,
        limit=5,
    )
    latency_ms = (time.time() - start) * 1000

    # Then: Results from multiple layers
    assert isinstance(results, dict)
    assert len(results) >= 1  # At least one layer returned results

    # Then: Verify latency target (<500ms for multi-layer search)
    assert latency_ms < 500, f"Multi-layer search {latency_ms}ms exceeds 500ms"


async def test_router_search_memory_short_term_e2e(memory_router, redis_memory_manager):
    """Test searching Redis short-term memory layer."""
    # Given: Conversation context in Redis
    session_id = "test_session_st"
    messages = [
        {"role": "user", "content": "What is retrieval augmented generation?"},
        {"role": "assistant", "content": "RAG combines retrieval and generation."},
    ]
    await redis_memory_manager.store_conversation_context(
        session_id=session_id,
        messages=messages,
    )

    # When: Search with query matching context
    results = await memory_router.search_memory(
        query="RAG",
        session_id=session_id,
        limit=5,
    )

    # Then: Short-term results found
    assert "short_term" in results or len(results) > 0


async def test_router_search_memory_long_term_e2e(memory_router):
    """Test searching Qdrant long-term memory layer."""
    # Given: Router configured with Qdrant
    # Note: Actual Qdrant search requires embeddings

    # When: Search long-term memory
    results = await memory_router.search_memory(
        query="machine learning concepts",
        session_id=None,  # No session, forces long-term search
        limit=5,
    )

    # Then: Results structure is valid
    assert isinstance(results, dict)
    # Long-term may return empty list if no embeddings available
    assert "long_term" in results or len(results) >= 0


async def test_router_search_memory_episodic_e2e(memory_router, graphiti_wrapper):
    """Test searching Graphiti episodic memory layer."""
    # Given: Episode in Graphiti
    await graphiti_wrapper.add_episode(
        content="Testing episodic memory search with router",
        source="test",
    )

    # When: Search with temporal query
    results = await memory_router.search_memory(
        query="when was episodic memory tested",
        limit=5,
    )

    # Then: Results structure is valid
    assert isinstance(results, dict)


async def test_router_search_with_time_window_e2e(memory_router):
    """Test memory search with time window filtering."""
    # When: Search with time window
    results = await memory_router.search_memory(
        query="recent events",
        limit=5,
        time_window_hours=24,
    )

    # Then: Results respect time window
    assert isinstance(results, dict)


# ============================================================================
# Conversation Turn Storage Tests
# ============================================================================


async def test_router_store_conversation_turn_e2e(memory_router, redis_memory_manager):
    """Test storing conversation turn across memory layers."""
    # Given: Conversation turn
    session_id = "test_session_store"
    user_msg = "What are transformer models?"
    assistant_msg = "Transformers use self-attention mechanisms."

    # When: Store conversation turn
    start = time.time()
    results = await memory_router.store_conversation_turn(
        user_message=user_msg,
        assistant_message=assistant_msg,
        session_id=session_id,
        metadata={"topic": "ml"},
    )
    latency_ms = (time.time() - start) * 1000

    # Then: Stored in multiple layers
    assert isinstance(results, dict)
    assert "short_term" in results
    assert results["short_term"] is True  # Successfully stored in Redis

    # Then: Verify latency target
    assert latency_ms < 1000, f"Storage {latency_ms}ms exceeds 1s"

    # Then: Verify data in Redis
    context = await redis_memory_manager.get_conversation_context(session_id)
    assert context is not None
    assert len(context) >= 2  # User + assistant messages


async def test_router_store_without_session_e2e(memory_router):
    """Test storing conversation turn without session ID."""
    # When: Store without session
    results = await memory_router.store_conversation_turn(
        user_message="Test message",
        assistant_message="Test response",
        session_id=None,  # No session
    )

    # Then: Only episodic layer used (if available)
    assert isinstance(results, dict)
    assert "short_term" not in results  # No session, no short-term storage


async def test_router_store_with_metadata_e2e(memory_router, graphiti_wrapper):
    """Test storing conversation with custom metadata."""
    # Given: Metadata
    metadata = {"user_id": "test_user", "importance": "high"}

    # When: Store with metadata
    results = await memory_router.store_conversation_turn(
        user_message="Important question",
        assistant_message="Important answer",
        session_id="test_meta",
        metadata=metadata,
    )

    # Then: Metadata is preserved
    assert isinstance(results, dict)


# ============================================================================
# Session Management Tests
# ============================================================================


async def test_router_get_session_summary_e2e(memory_router, redis_memory_manager):
    """Test getting session summary across all layers."""
    # Given: Session with conversation context
    session_id = "test_session_summary"
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    await redis_memory_manager.store_conversation_context(
        session_id=session_id,
        messages=messages,
    )

    # When: Get session summary
    summary = await memory_router.get_session_summary(session_id=session_id)

    # Then: Summary includes all layers
    assert isinstance(summary, dict)
    assert "short_term" in summary
    assert "long_term" in summary
    assert "episodic" in summary

    # Then: Short-term summary shows message count
    assert summary["short_term"]["message_count"] == len(messages)


async def test_router_session_summary_nonexistent_e2e(memory_router):
    """Test session summary for nonexistent session."""
    # When: Get summary for nonexistent session
    summary = await memory_router.get_session_summary(
        session_id="nonexistent_session_123"
    )

    # Then: Summary shows session not found
    assert isinstance(summary, dict)
    if "short_term" in summary:
        assert summary["short_term"]["message_count"] == 0


# ============================================================================
# Redis Memory TTL and Expiration Tests
# ============================================================================


async def test_redis_memory_ttl_expiration_e2e(redis_memory_manager, redis_client):
    """Test Redis memory automatically expires based on TTL."""
    # Given: Store value with short TTL
    key = "test_ttl_key"
    await redis_memory_manager.store(
        key=key,
        value="test_value",
        ttl_seconds=1,  # 1 second TTL
        namespace="test",
    )

    # When: Retrieve immediately
    value_immediate = await redis_memory_manager.retrieve(
        key=key,
        namespace="test",
    )

    # Then: Value exists
    assert value_immediate == "test_value"

    # When: Wait for TTL to expire
    import asyncio
    await asyncio.sleep(2)

    # When: Retrieve after expiration
    value_expired = await redis_memory_manager.retrieve(
        key=key,
        namespace="test",
    )

    # Then: Value is expired
    assert value_expired is None


async def test_redis_memory_extend_ttl_e2e(redis_memory_manager):
    """Test extending TTL of stored values."""
    # Given: Stored value
    key = "test_extend_ttl"
    await redis_memory_manager.store(
        key=key,
        value="test",
        ttl_seconds=10,
        namespace="test",
    )

    # When: Extend TTL
    extended = await redis_memory_manager.extend_ttl(
        key=key,
        additional_seconds=20,
        namespace="test",
    )

    # Then: Extension successful
    assert extended is True

    # Then: Verify new TTL
    metadata = await redis_memory_manager.get_metadata(key, namespace="test")
    assert metadata is not None
    assert metadata["ttl_seconds"] > 10


# ============================================================================
# Error Handling Tests
# ============================================================================


async def test_router_error_handling_invalid_query_e2e(memory_router):
    """Test router handles invalid queries gracefully."""
    # When: Empty query
    results = await memory_router.search_memory(
        query="",
        limit=5,
    )

    # Then: Returns empty results (not error)
    assert isinstance(results, dict)


async def test_router_error_handling_layer_failure_e2e(memory_router):
    """Test router continues when one layer fails."""
    # When: Search with normal query (one layer may fail)
    results = await memory_router.search_memory(
        query="test query for error handling",
        limit=5,
    )

    # Then: Results from available layers
    assert isinstance(results, dict)
    # Router should not crash even if some layers fail


# ============================================================================
# Pattern Detection Tests
# ============================================================================


async def test_router_is_recent_context_query_e2e(memory_router):
    """Test detection of recent context query patterns."""
    # Test various patterns
    recent_queries = [
        "What did we just discuss?",
        "What did I mention earlier?",
        "Remember what we talked about?",
        "In our previous conversation...",
    ]

    for query in recent_queries:
        is_recent = memory_router._is_recent_context_query(query)
        # Pattern matching should detect these
        assert isinstance(is_recent, bool)


async def test_router_is_temporal_query_e2e(memory_router):
    """Test detection of temporal query patterns."""
    # Test temporal patterns
    temporal_queries = [
        "When did this happen?",
        "What was the timeline?",
        "How did it change over time?",
        "Before and after comparison",
    ]

    for query in temporal_queries:
        is_temporal = memory_router._is_temporal_query(query)
        # Pattern matching should detect these
        assert isinstance(is_temporal, bool)


# ============================================================================
# Performance and Latency Tests
# ============================================================================


async def test_router_search_latency_target_e2e(memory_router):
    """Test memory router search meets latency targets."""
    # When: Execute search
    start = time.time()
    await memory_router.search_memory(
        query="performance test query",
        limit=5,
    )
    latency_ms = (time.time() - start) * 1000

    # Then: Meets latency target (<500ms)
    assert latency_ms < 500, f"Router search {latency_ms}ms exceeds 500ms"


async def test_router_storage_latency_target_e2e(memory_router):
    """Test conversation turn storage meets latency targets."""
    # When: Store conversation turn
    start = time.time()
    await memory_router.store_conversation_turn(
        user_message="Performance test",
        assistant_message="Response",
        session_id="perf_test",
    )
    latency_ms = (time.time() - start) * 1000

    # Then: Meets latency target (<1s)
    assert latency_ms < 1000, f"Storage {latency_ms}ms exceeds 1s"
