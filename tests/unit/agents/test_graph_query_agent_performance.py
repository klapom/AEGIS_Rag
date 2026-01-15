"""Unit tests for graph_query_agent performance optimizations.

Sprint 92: Graph Search Performance Optimization

Tests verify:
1. Intent extraction runs in background (non-blocking)
2. Entity expansion uses expand_entities() (not expand_and_rerank())
3. Timing logs are present in output
4. Overall latency is under 2s for typical queries
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.graph_query_agent import GraphQueryAgent
from src.components.graph_rag.dual_level_search import SearchMode
from src.core.models import GraphEntity, GraphQueryResult


@pytest.fixture
def mock_query_rewriter_v2():
    """Mock QueryRewriterV2 for intent extraction."""
    mock = AsyncMock()
    mock.extract_graph_intents = AsyncMock(
        return_value=MagicMock(
            graph_intents=["entity_relationships"],
            entities_mentioned=["RAG", "LLMs"],
            cypher_hints=[],
            confidence=0.85,
            latency_ms=800.0,
        )
    )
    return mock


@pytest.fixture
def mock_dual_level_search():
    """Mock DualLevelSearch for graph queries."""
    mock = AsyncMock()

    # Mock local_search (entity expansion) - Sprint 92: returns (entities, metadata) tuple
    mock.local_search = AsyncMock(
        return_value=(
            [
                GraphEntity(
                    id="entity1",
                    name="RAG",
                    type="CONCEPT",
                    description="Retrieval Augmented Generation",
                    properties={},
                    source_document="doc1",
                    confidence=0.9,
                ),
                GraphEntity(
                    id="entity2",
                    name="LLM",
                    type="CONCEPT",
                    description="Large Language Model",
                    properties={},
                    source_document="doc1",
                    confidence=0.85,
                ),
            ],
            {  # metadata dict
                "execution_time_ms": 100.0,
                "chunks_found": 2,
                "graph_hops_used": 1,
            }
        )
    )

    # Mock global_search (topics)
    mock.global_search = AsyncMock(return_value=[])

    # Mock hybrid_search
    mock.hybrid_search = AsyncMock(
        return_value=GraphQueryResult(
            query="What is RAG?",
            answer="RAG is Retrieval Augmented Generation",
            entities=[],
            relationships=[],
            topics=[],
            context="RAG context",
            mode="hybrid",
            metadata={},
        )
    )

    return mock


@pytest.mark.asyncio
async def test_intent_extraction_runs_in_background(
    mock_query_rewriter_v2,
    mock_dual_level_search,
):
    """Test that intent extraction runs in background (non-blocking).

    Sprint 92: Intent extraction should not block search execution.
    Expected: Search completes before intent extraction finishes.
    """
    # Slow intent extraction (1.5s)
    async def slow_intent_extraction(query):
        await asyncio.sleep(1.5)
        return MagicMock(
            graph_intents=["entity_relationships"],
            entities_mentioned=["RAG"],
            cypher_hints=[],
            confidence=0.85,
            latency_ms=1500.0,
        )

    mock_query_rewriter_v2.extract_graph_intents = AsyncMock(
        side_effect=slow_intent_extraction
    )

    # Create agent with mocks
    agent = GraphQueryAgent(
        query_rewriter_v2=mock_query_rewriter_v2,
        dual_level_search=mock_dual_level_search,
    )

    # Create state
    state = {
        "query": "What is RAG?",
        "intent": "graph",
        "namespaces": ["test"],
        "metadata": {},
        "retrieved_contexts": [],
        "trace": [],
    }

    # Time the execution
    start_time = time.perf_counter()
    result = await agent.process(state)
    execution_time = (time.perf_counter() - start_time) * 1000

    # Assertions
    assert result is not None
    assert "graph_query_result" in result

    # Sprint 92: Execution should complete in <500ms (before intent extraction finishes)
    # Intent extraction runs in background and doesn't block
    assert execution_time < 1000, (
        f"Expected execution < 1000ms (background intent), got {execution_time:.2f}ms"
    )

    # Intent extraction was called but not awaited
    mock_query_rewriter_v2.extract_graph_intents.assert_called_once()


@pytest.mark.asyncio
async def test_entity_expansion_timing_logged(
    mock_query_rewriter_v2,
    mock_dual_level_search,
):
    """Test that entity expansion timing is logged.

    Sprint 92: Phase timings should be logged for performance analysis.
    """
    import asyncio
    from unittest.mock import patch

    # Create agent with mocks
    agent = GraphQueryAgent(
        query_rewriter_v2=mock_query_rewriter_v2,
        dual_level_search=mock_dual_level_search,
    )

    # Patch logger to capture log calls
    with patch.object(agent, "_log_success") as mock_log:
        state = {
            "query": "What is RAG?",
            "intent": "graph",
            "namespaces": ["test"],
            "metadata": {},
            "retrieved_contexts": [],
            "trace": [],
        }

        await agent.process(state)

        # Check that _log_success was called with phase_timings
        assert mock_log.called
        call_kwargs = mock_log.call_args[1]

        # Sprint 92: phase_timings should be present in log
        assert "phase_timings" in call_kwargs, "phase_timings not logged"
        phase_timings = call_kwargs["phase_timings"]
        assert isinstance(phase_timings, dict)


@pytest.mark.asyncio
@patch("src.components.graph_rag.entity_expansion.SmartEntityExpander")
async def test_entity_expansion_uses_expand_entities_not_rerank(
    mock_expander_class,
    mock_query_rewriter_v2,
):
    """Test that entity expansion uses expand_entities() not expand_and_rerank().

    Sprint 92: expand_and_rerank() causes 2-5s overhead due to embeddings.
    Should use expand_entities() instead.
    """
    # Mock SmartEntityExpander instance
    # Sprint 92: expand_entities returns (entities, hops_used) tuple
    mock_expander = AsyncMock()
    mock_expander.expand_entities = AsyncMock(
        return_value=(["RAG", "Retrieval", "Generation"], 1)  # (entities, hops)
    )
    mock_expander.expand_and_rerank = AsyncMock(
        return_value=[("RAG", 0.95), ("Retrieval", 0.85)]
    )
    mock_expander_class.return_value = mock_expander

    # Mock Neo4j client
    mock_neo4j = AsyncMock()
    mock_neo4j.execute_read = AsyncMock(return_value=[])

    # Create dual_level_search
    from src.components.graph_rag.dual_level_search import DualLevelSearch

    search = DualLevelSearch()
    search.neo4j_client = mock_neo4j

    # Execute local_search
    await search.local_search(
        query="What is RAG?",
        top_k=5,
        namespaces=["test"]
    )

    # Assertions
    # Sprint 92: Should call expand_entities(), NOT expand_and_rerank()
    mock_expander.expand_entities.assert_called_once()
    mock_expander.expand_and_rerank.assert_not_called()


@pytest.mark.asyncio
async def test_graph_search_performance_target(
    mock_query_rewriter_v2,
    mock_dual_level_search,
):
    """Test that graph search meets <2s performance target.

    Sprint 92: Graph search should complete in <2s for typical queries.
    """
    # Create agent with mocks
    agent = GraphQueryAgent(
        query_rewriter_v2=mock_query_rewriter_v2,
        dual_level_search=mock_dual_level_search,
    )

    # Create state
    state = {
        "query": "What is RAG?",
        "intent": "graph",
        "namespaces": ["test"],
        "metadata": {},
        "retrieved_contexts": [],
        "trace": [],
    }

    # Time the execution (run 3 times, check average)
    execution_times = []
    for _ in range(3):
        start_time = time.perf_counter()
        await agent.process(state)
        execution_time = (time.perf_counter() - start_time) * 1000
        execution_times.append(execution_time)

    avg_time = sum(execution_times) / len(execution_times)

    # Assertions
    # Sprint 92: Average execution should be < 2000ms (p95 target)
    assert avg_time < 2000, (
        f"Expected avg execution < 2000ms, got {avg_time:.2f}ms"
    )


@pytest.mark.asyncio
async def test_local_search_phase_timings_logged():
    """Test that local_search logs phase timings.

    Sprint 92: Detailed timing logs help identify bottlenecks.
    """
    from src.components.graph_rag.dual_level_search import DualLevelSearch
    from unittest.mock import patch

    # Mock dependencies
    mock_neo4j = AsyncMock()
    mock_neo4j.execute_read = AsyncMock(return_value=[])

    search = DualLevelSearch()
    search.neo4j_client = mock_neo4j

    # Patch SmartEntityExpander
    with patch("src.components.graph_rag.entity_expansion.SmartEntityExpander") as mock_exp:
        mock_expander = AsyncMock()
        mock_expander.expand_entities = AsyncMock(return_value=(["RAG"], 1))  # (entities, hops)
        mock_exp.return_value = mock_expander

        # Execute local_search (logger will be called internally)
        result_entities, result_metadata = await search.local_search(
            query="What is RAG?",
            top_k=5,
            namespaces=["test"]
        )

        # Check that metadata contains phase timing fields
        # Sprint 92: Phase timings are flattened into metadata dict
        assert "entity_expansion_ms" in result_metadata, "entity_expansion_ms not in metadata"
        assert "neo4j_chunk_query_ms" in result_metadata, "neo4j_chunk_query_ms not in metadata"
        assert "graph_hops_used" in result_metadata, "graph_hops_used not in metadata"


# Add asyncio import for tests
import asyncio
