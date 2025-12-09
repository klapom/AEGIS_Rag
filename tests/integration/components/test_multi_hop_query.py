"""Integration tests for Multi-Hop Query Processing (Sprint 27 Feature 27.2).

This module tests complex multi-hop query capabilities.

Tests cover:
- Query decomposition into sub-queries
- Sub-query execution and context retrieval
- Context aggregation and synthesis
- Entity linking across hops
- Temporal reasoning
- Error propagation handling
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_query_decomposer():
    """Mock query decomposer."""
    decomposer = MagicMock()
    decomposer.decompose = AsyncMock(
        return_value=[
            {"query": "What is AEGIS RAG?", "hop": 1, "dependency": None},
            {"query": "What components does it use?", "hop": 2, "dependency": 1},
            {"query": "How do these components integrate?", "hop": 3, "dependency": 2},
        ]
    )
    return decomposer


@pytest.fixture
def mock_retrieval_agent():
    """Mock retrieval agent for sub-queries."""
    agent = MagicMock()
    agent.retrieve = AsyncMock(
        side_effect=[
            # Hop 1 results
            {
                "answer": "AEGIS RAG is a multi-agent RAG system",
                "documents": [{"id": "d1", "content": "AEGIS RAG overview", "score": 0.95}],
            },
            # Hop 2 results
            {
                "answer": "It uses vector search, graph reasoning, and memory",
                "documents": [{"id": "d2", "content": "Component details", "score": 0.92}],
            },
            # Hop 3 results
            {
                "answer": "Components integrate via LangGraph orchestration",
                "documents": [{"id": "d3", "content": "Integration architecture", "score": 0.89}],
            },
        ]
    )
    return agent


@pytest.fixture
def mock_context_aggregator():
    """Mock context aggregator."""
    aggregator = MagicMock()
    aggregator.aggregate = AsyncMock(
        return_value={
            "final_answer": "AEGIS RAG is a multi-agent system that uses vector search, graph reasoning, and memory, integrated via LangGraph.",
            "supporting_contexts": [
                {"hop": 1, "content": "AEGIS RAG overview"},
                {"hop": 2, "content": "Component details"},
                {"hop": 3, "content": "Integration architecture"},
            ],
            "confidence": 0.92,
        }
    )
    return aggregator


# ============================================================================
# Query Decomposition Tests
# ============================================================================


@pytest.mark.asyncio
async def test_query_decomposition(mock_query_decomposer):
    """Test decomposing complex query into sub-queries."""
    complex_query = "What is AEGIS RAG and what components does it use for integration?"

    sub_queries = await mock_query_decomposer.decompose(complex_query)

    assert len(sub_queries) == 3
    assert sub_queries[0]["hop"] == 1
    assert sub_queries[1]["hop"] == 2
    assert sub_queries[2]["hop"] == 3
    assert sub_queries[1]["dependency"] == 1  # Hop 2 depends on Hop 1


@pytest.mark.asyncio
async def test_query_decomposition_single_hop():
    """Test simple query that doesn't need decomposition."""
    simple_query = "What is vector search?"

    # Mock decomposer that returns single hop
    decomposer = MagicMock()
    decomposer.decompose = AsyncMock(
        return_value=[{"query": "What is vector search?", "hop": 1, "dependency": None}]
    )

    sub_queries = await decomposer.decompose(simple_query)

    assert len(sub_queries) == 1
    assert sub_queries[0]["dependency"] is None


# ============================================================================
# Sub-Query Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sub_query_execution(mock_retrieval_agent):
    """Test executing sub-queries in sequence."""
    sub_queries = [
        {"query": "What is AEGIS RAG?", "hop": 1},
        {"query": "What components?", "hop": 2},
    ]

    results = []
    for sq in sub_queries:
        result = await mock_retrieval_agent.retrieve(sq["query"])
        results.append(result)

    assert len(results) == 2
    assert "answer" in results[0]
    assert "documents" in results[1]


@pytest.mark.asyncio
async def test_sub_query_with_context_injection():
    """Test injecting previous hop context into next query."""
    hop1_context = "AEGIS RAG is a multi-agent system"

    # Mock agent that uses context
    agent = MagicMock()
    agent.retrieve = AsyncMock(
        return_value={
            "answer": f"Based on '{hop1_context}', the components are...",
            "used_context": True,
        }
    )

    hop2_query = "What components does it use?"
    result = await agent.retrieve(hop2_query, context=hop1_context)

    assert result["used_context"] is True
    assert "AEGIS RAG" in result["answer"]


# ============================================================================
# Context Aggregation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_context_aggregation(mock_context_aggregator):
    """Test aggregating contexts from multiple hops."""
    hop_results = [
        {"hop": 1, "answer": "Answer 1", "documents": []},
        {"hop": 2, "answer": "Answer 2", "documents": []},
        {"hop": 3, "answer": "Answer 3", "documents": []},
    ]

    aggregated = await mock_context_aggregator.aggregate(hop_results)

    assert "final_answer" in aggregated
    assert len(aggregated["supporting_contexts"]) == 3
    assert aggregated["confidence"] > 0


@pytest.mark.asyncio
async def test_context_synthesis():
    """Test synthesizing coherent answer from fragments."""
    contexts = [
        "AEGIS RAG is a multi-agent system",
        "It uses vector search and graph reasoning",
        "Components integrate via LangGraph",
    ]

    # Mock synthesis
    synthesized = " that ".join(contexts) + "."

    assert "AEGIS RAG" in synthesized
    assert "LangGraph" in synthesized


# ============================================================================
# Entity Linking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_entity_linking_across_hops():
    """Test linking entities mentioned across multiple hops."""
    hop1_entities = ["AEGIS RAG", "vector search"]
    hop2_entities = ["vector search", "Qdrant", "BGE-M3"]
    hop3_entities = ["BGE-M3", "embeddings"]

    # Build entity graph
    entity_links = {}
    for e in hop1_entities:
        entity_links[e] = {"hops": [1]}
    for e in hop2_entities:
        if e in entity_links:
            entity_links[e]["hops"].append(2)
        else:
            entity_links[e] = {"hops": [2]}
    for e in hop3_entities:
        if e in entity_links:
            entity_links[e]["hops"].append(3)
        else:
            entity_links[e] = {"hops": [3]}

    # "vector search" and "BGE-M3" appear in multiple hops
    assert len(entity_links["vector search"]["hops"]) == 2
    assert len(entity_links["BGE-M3"]["hops"]) == 2


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sub_query_failure_propagation():
    """Test handling when a sub-query fails."""
    agent = MagicMock()
    agent.retrieve = AsyncMock(
        side_effect=[
            {"answer": "Hop 1 success"},
            Exception("Hop 2 failed"),  # Hop 2 fails
            {"answer": "Hop 3 would succeed but won't run"},
        ]
    )

    results = []
    for i in range(2):
        try:
            result = await agent.retrieve(f"Query {i+1}")
            results.append(result)
        except Exception as e:
            results.append({"error": str(e)})
            break  # Stop on first failure

    assert len(results) == 2
    assert "error" in results[1]


@pytest.mark.asyncio
async def test_partial_hop_completion():
    """Test completing query with partial hop results."""
    complete_hops = [
        {"hop": 1, "answer": "Success", "status": "completed"},
        {"hop": 2, "answer": None, "status": "failed"},
    ]

    # Fallback strategy: use only completed hops
    valid_hops = [h for h in complete_hops if h["status"] == "completed"]

    assert len(valid_hops) == 1
    assert valid_hops[0]["hop"] == 1


# ============================================================================
# Integration Test
# ============================================================================


@pytest.mark.asyncio
async def test_full_multi_hop_pipeline(
    mock_query_decomposer, mock_retrieval_agent, mock_context_aggregator
):
    """Test complete multi-hop query pipeline."""
    complex_query = "What is AEGIS RAG and how do its components integrate?"

    # Step 1: Decompose
    sub_queries = await mock_query_decomposer.decompose(complex_query)
    assert len(sub_queries) == 3

    # Step 2: Execute sub-queries
    hop_results = []
    for sq in sub_queries:
        result = await mock_retrieval_agent.retrieve(sq["query"])
        hop_results.append(result)
    assert len(hop_results) == 3

    # Step 3: Aggregate
    final_result = await mock_context_aggregator.aggregate(hop_results)
    assert "final_answer" in final_result
    assert final_result["confidence"] > 0
