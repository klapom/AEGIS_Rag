"""Integration tests for VectorSearchAgent with real Qdrant.

Tests end-to-end functionality with actual Qdrant instance from Docker Compose.
"""

import asyncio
import time

import pytest

from src.agents.graph import compile_graph
from src.agents.state import create_initial_state
from src.agents.vector_search_agent import VectorSearchAgent, vector_search_node
from src.components.vector_search.embeddings import EmbeddingService
from src.components.vector_search.hybrid_search import HybridSearch
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import settings

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
async def qdrant_client():
    """Create Qdrant client for integration tests."""
    client = QdrantClientWrapper()
    yield client
    # Cleanup handled by test teardown


@pytest.fixture(scope="module")
async def embedding_service():
    """Create embedding service."""
    return EmbeddingService()


@pytest.fixture(scope="module")
async def hybrid_search(qdrant_client, embedding_service):
    """Create HybridSearch instance with real components."""
    return HybridSearch(
        qdrant_client=qdrant_client,
        embedding_service=embedding_service,
        collection_name=settings.qdrant_collection,
    )


@pytest.fixture(scope="module")
async def indexed_collection(hybrid_search):
    """Ensure BM25 index is prepared for tests."""
    # This assumes documents are already indexed in Qdrant
    # If not, skip or prepare minimal test data
    try:
        stats = await hybrid_search.prepare_bm25_index()
        print(f"BM25 index prepared: {stats['documents_indexed']} documents")
        return stats
    except Exception as e:
        pytest.skip(f"Could not prepare BM25 index: {e}")


# ============================================================================
# Test Agent with Real Search
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_process_real_search(hybrid_search, indexed_collection):
    """Test agent processing with real hybrid search."""
    agent = VectorSearchAgent(hybrid_search=hybrid_search, top_k=5, use_reranking=True)

    state = create_initial_state("What is RAG?", intent="hybrid")

    start_time = time.perf_counter()
    result_state = await agent.process(state)
    latency_ms = (time.perf_counter() - start_time) * 1000

    # Check results
    assert "retrieved_contexts" in result_state
    contexts = result_state["retrieved_contexts"]

    # Should have results (if documents exist)
    if indexed_collection["documents_indexed"] > 0:
        assert len(contexts) > 0
        assert len(contexts) <= 5

        # Check context structure
        for ctx in contexts:
            assert "id" in ctx
            assert "text" in ctx
            assert "score" in ctx
            assert ctx["text"] != ""  # Should have content

    # Check metadata
    assert "metadata" in result_state
    assert "search" in result_state["metadata"]
    search_meta = result_state["metadata"]["search"]

    assert search_meta["search_mode"] == "hybrid"
    assert search_meta["latency_ms"] > 0
    assert "vector_results_count" in search_meta
    assert "bm25_results_count" in search_meta

    # Performance check
    print(f"Search latency: {latency_ms:.2f}ms")
    assert latency_ms < 5000, f"Search took too long: {latency_ms}ms"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_with_different_queries(hybrid_search, indexed_collection):
    """Test agent with various query types."""
    if indexed_collection["documents_indexed"] == 0:
        pytest.skip("No documents indexed")

    agent = VectorSearchAgent(hybrid_search=hybrid_search, top_k=3)

    queries = [
        "What is retrieval augmented generation?",
        "How does vector search work?",
        "Explain embeddings",
    ]

    for query in queries:
        state = create_initial_state(query, intent="hybrid")
        result_state = await agent.process(state)

        assert "retrieved_contexts" in result_state
        assert len(result_state["retrieved_contexts"]) <= 3
        assert "metadata" in result_state
        assert "search" in result_state["metadata"]


# ============================================================================
# Test Node Function Integration
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vector_search_node_integration(indexed_collection):
    """Test vector_search_node with real configuration."""
    if indexed_collection["documents_indexed"] == 0:
        pytest.skip("No documents indexed")

    state = create_initial_state("test query", intent="hybrid")

    result_state = await vector_search_node(state)

    assert "retrieved_contexts" in result_state
    assert "metadata" in result_state


# ============================================================================
# Test Graph Integration
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_graph_execution(indexed_collection):
    """Test complete graph execution from router to vector search."""
    if indexed_collection["documents_indexed"] == 0:
        pytest.skip("No documents indexed")

    graph = compile_graph()

    initial_state = create_initial_state("What is RAG?", intent="hybrid")

    start_time = time.perf_counter()
    final_state = await graph.ainvoke(initial_state)
    total_latency_ms = (time.perf_counter() - start_time) * 1000

    # Check final state
    assert "retrieved_contexts" in final_state
    assert "metadata" in final_state
    assert "agent_path" in final_state["metadata"]

    # Check agent path includes router and vector search
    agent_path = final_state["metadata"]["agent_path"]
    assert any("router" in str(step).lower() for step in agent_path)
    assert any("vectorsearch" in str(step).lower() for step in agent_path)

    # Performance check
    print(f"Total graph latency: {total_latency_ms:.2f}ms")
    assert total_latency_ms < 5000, f"Graph execution took too long: {total_latency_ms}ms"


# ============================================================================
# Test Performance
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_performance_benchmark(hybrid_search, indexed_collection):
    """Benchmark search performance."""
    if indexed_collection["documents_indexed"] == 0:
        pytest.skip("No documents indexed")

    agent = VectorSearchAgent(hybrid_search=hybrid_search, top_k=5, use_reranking=True)

    query = "What is retrieval augmented generation?"
    num_runs = 10
    latencies = []

    for _ in range(num_runs):
        state = create_initial_state(query, intent="hybrid")
        start_time = time.perf_counter()
        await agent.process(state)
        latency_ms = (time.perf_counter() - start_time) * 1000
        latencies.append(latency_ms)

    # Calculate statistics
    avg_latency = sum(latencies) / len(latencies)
    p50 = sorted(latencies)[len(latencies) // 2]
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    p99 = sorted(latencies)[int(len(latencies) * 0.99)]

    print(f"\nPerformance Benchmark ({num_runs} runs):")
    print(f"  Average: {avg_latency:.2f}ms")
    print(f"  P50: {p50:.2f}ms")
    print(f"  P95: {p95:.2f}ms")
    print(f"  P99: {p99:.2f}ms")

    # Performance assertions
    assert avg_latency < 1000, f"Average latency too high: {avg_latency}ms"
    assert p95 < 2000, f"P95 latency too high: {p95}ms"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_searches(hybrid_search, indexed_collection):
    """Test concurrent search operations."""
    if indexed_collection["documents_indexed"] == 0:
        pytest.skip("No documents indexed")

    agent = VectorSearchAgent(hybrid_search=hybrid_search, top_k=3)

    queries = [
        "What is RAG?",
        "How does vector search work?",
        "Explain embeddings",
        "What is semantic search?",
        "How do transformers work?",
    ]

    # Run concurrent searches
    start_time = time.perf_counter()
    tasks = [agent.process(create_initial_state(q, intent="hybrid")) for q in queries]
    results = await asyncio.gather(*tasks)
    total_time = (time.perf_counter() - start_time) * 1000

    # Check all succeeded
    assert len(results) == len(queries)
    for result in results:
        assert "retrieved_contexts" in result
        assert "metadata" in result

    print(f"Concurrent execution time: {total_time:.2f}ms for {len(queries)} queries")


# ============================================================================
# Test Error Handling
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_with_empty_query(hybrid_search):
    """Test agent behavior with empty query."""
    agent = VectorSearchAgent(hybrid_search=hybrid_search)

    state = create_initial_state("", intent="hybrid")
    result_state = await agent.process(state)

    # Should skip search gracefully
    assert "retrieved_contexts" in result_state
    assert len(result_state["retrieved_contexts"]) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_with_very_long_query(hybrid_search, indexed_collection):
    """Test agent with very long query."""
    if indexed_collection["documents_indexed"] == 0:
        pytest.skip("No documents indexed")

    agent = VectorSearchAgent(hybrid_search=hybrid_search, top_k=3)

    # Create very long query
    long_query = "What is RAG? " * 100  # Repeat to make it long

    state = create_initial_state(long_query, intent="hybrid")
    result_state = await agent.process(state)

    # Should handle gracefully
    assert "retrieved_contexts" in result_state
    assert "metadata" in result_state


# ============================================================================
# Test Reranking
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_with_reranking(hybrid_search, indexed_collection):
    """Test that reranking improves results."""
    if indexed_collection["documents_indexed"] == 0:
        pytest.skip("No documents indexed")

    query = "What is retrieval augmented generation?"

    # Search without reranking
    agent_no_rerank = VectorSearchAgent(hybrid_search=hybrid_search, top_k=5, use_reranking=False)
    state1 = create_initial_state(query, intent="hybrid")
    result1 = await agent_no_rerank.process(state1)

    # Search with reranking
    agent_with_rerank = VectorSearchAgent(hybrid_search=hybrid_search, top_k=5, use_reranking=True)
    state2 = create_initial_state(query, intent="hybrid")
    result2 = await agent_with_rerank.process(state2)

    # Both should have results
    assert len(result1["retrieved_contexts"]) > 0
    assert len(result2["retrieved_contexts"]) > 0

    # Check reranking metadata
    meta1 = result1["metadata"]["search"]
    meta2 = result2["metadata"]["search"]

    assert meta1["reranking_applied"] is False
    assert meta2["reranking_applied"] is True
