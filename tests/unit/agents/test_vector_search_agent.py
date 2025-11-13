"""Unit tests for VectorSearchAgent.

Tests the vector search agent integration with HybridSearch,
state management, error handling, and retry logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.state import create_initial_state
from src.agents.vector_search_agent import VectorSearchAgent, vector_search_node
from src.core.exceptions import VectorSearchError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_hybrid_search():
    """Create mock HybridSearch instance."""
    mock = MagicMock()
    mock.hybrid_search = AsyncMock(
        return_value={
            "query": "test query",
            "results": [
                {
                    "id": "doc1",
                    "text": "This is a test document",
                    "score": 0.95,
                    "source": "test.txt",
                    "document_id": "test_doc_1",
                    "rank": 1,
                    "search_type": "hybrid",
                    "rrf_score": 0.95,
                    "rrf_rank": 1,
                },
                {
                    "id": "doc2",
                    "text": "Another test document",
                    "score": 0.85,
                    "source": "test2.txt",
                    "document_id": "test_doc_2",
                    "rank": 2,
                    "search_type": "hybrid",
                    "rrf_score": 0.85,
                    "rrf_rank": 2,
                },
            ],
            "total_results": 2,
            "returned_results": 2,
            "search_metadata": {
                "vector_results_count": 2,
                "bm25_results_count": 2,
                "rrf_k": 60,
                "reranking_applied": False,
                "diversity_stats": {"common_percentage": 50.0},
            },
        }
    )
    return mock


@pytest.fixture
def mock_hybrid_search_with_reranking():
    """Create mock HybridSearch instance with reranking."""
    mock = MagicMock()
    mock.hybrid_search = AsyncMock(
        return_value={
            "query": "test query",
            "results": [
                {
                    "id": "doc1",
                    "text": "This is a test document",
                    "score": 0.95,
                    "source": "test.txt",
                    "document_id": "test_doc_1",
                    "rank": 1,
                    "search_type": "hybrid",
                    "rrf_score": 0.85,
                    "rrf_rank": 2,
                    "rerank_score": 0.95,
                    "normalized_rerank_score": 0.95,
                    "original_rrf_rank": 2,
                    "final_rank": 1,
                },
            ],
            "total_results": 1,
            "returned_results": 1,
            "search_metadata": {
                "vector_results_count": 2,
                "bm25_results_count": 2,
                "rrf_k": 60,
                "reranking_applied": True,
                "diversity_stats": {"common_percentage": 50.0},
            },
        }
    )
    return mock


@pytest.fixture
def sample_state():
    """Create sample agent state."""
    return create_initial_state("What is RAG?", intent="hybrid")


# ============================================================================
# Test Initialization
# ============================================================================


@pytest.mark.unit
def test_vector_search_agent_init_default():
    """Test VectorSearchAgent initialization with defaults."""
    with patch("src.agents.vector_search_agent.HybridSearch"):
        agent = VectorSearchAgent()

        assert agent.name == "VectorSearchAgent"
        assert agent.top_k == 5  # From settings default
        assert agent.use_reranking is True
        assert agent.max_retries == 3


@pytest.mark.unit
def test_vector_search_agent_init_custom(mock_hybrid_search):
    """Test VectorSearchAgent initialization with custom parameters."""
    agent = VectorSearchAgent(
        hybrid_search=mock_hybrid_search, top_k=10, use_reranking=False, max_retries=5
    )

    assert agent.hybrid_search is mock_hybrid_search
    assert agent.top_k == 10
    assert agent.use_reranking is False
    assert agent.max_retries == 5


# ============================================================================
# Test Process Method
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_success(mock_hybrid_search, sample_state):
    """Test successful processing with vector search."""
    agent = VectorSearchAgent(hybrid_search=mock_hybrid_search, top_k=5)

    result_state = await agent.process(sample_state)

    # Check that search was called
    mock_hybrid_search.hybrid_search.assert_called_once_with(
        query="What is RAG?",
        top_k=5,
        use_reranking=True,
    )

    # Check state updates
    assert "retrieved_contexts" in result_state
    assert len(result_state["retrieved_contexts"]) == 2

    # Check first context
    ctx = result_state["retrieved_contexts"][0]
    assert ctx["id"] == "doc1"
    assert ctx["text"] == "This is a test document"
    assert ctx["score"] == 0.95
    assert ctx["source"] == "test.txt"
    assert ctx["rank"] == 1

    # Check metadata
    assert "metadata" in result_state
    assert "search" in result_state["metadata"]
    search_meta = result_state["metadata"]["search"]
    assert search_meta["result_count"] == 2
    assert search_meta["search_mode"] == "hybrid"
    assert search_meta["vector_results_count"] == 2
    assert search_meta["bm25_results_count"] == 2
    assert search_meta["reranking_applied"] is False
    assert search_meta["latency_ms"] > 0

    # Check agent trace
    assert "agent_path" in result_state["metadata"]
    assert any(
        "VectorSearchAgent: started" in trace for trace in result_state["metadata"]["agent_path"]
    )
    assert any("completed" in trace for trace in result_state["metadata"]["agent_path"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_with_reranking(mock_hybrid_search_with_reranking, sample_state):
    """Test processing with reranking enabled."""
    agent = VectorSearchAgent(hybrid_search=mock_hybrid_search_with_reranking, top_k=5)

    result_state = await agent.process(sample_state)

    # Check reranking metadata
    ctx = result_state["retrieved_contexts"][0]
    assert "rerank_score" in ctx["metadata"]
    assert ctx["metadata"]["rerank_score"] == 0.95
    assert ctx["metadata"]["original_rrf_rank"] == 2

    # Check search metadata
    search_meta = result_state["metadata"]["search"]
    assert search_meta["reranking_applied"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_empty_query(mock_hybrid_search):
    """Test processing with empty query."""
    agent = VectorSearchAgent(hybrid_search=mock_hybrid_search)

    state = create_initial_state("", intent="hybrid")
    result_state = await agent.process(state)

    # Should skip search
    mock_hybrid_search.hybrid_search.assert_not_called()

    # Check trace
    assert "agent_path" in result_state["metadata"]
    assert any("skipped (empty query)" in trace for trace in result_state["metadata"]["agent_path"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_search_error(sample_state):
    """Test error handling when search fails."""
    mock = MagicMock()
    mock.hybrid_search = AsyncMock(side_effect=VectorSearchError("test query", "Search failed"))

    agent = VectorSearchAgent(hybrid_search=mock, max_retries=1)

    result_state = await agent.process(sample_state)

    # Check error metadata
    assert "error" in result_state["metadata"]
    error = result_state["metadata"]["error"]
    assert error["agent"] == "VectorSearchAgent"
    assert error["error_type"] == "VectorSearchError"
    assert "Search failed" in error["message"]

    # Check search metadata has error
    assert "search" in result_state["metadata"]
    search_meta = result_state["metadata"]["search"]
    assert search_meta["result_count"] == 0
    assert search_meta["error"] is not None


# ============================================================================
# Test Retry Logic
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_failure(sample_state):
    """Test retry logic on transient failures."""
    mock = MagicMock()
    # Fail twice, then succeed
    mock.hybrid_search = AsyncMock(
        side_effect=[
            VectorSearchError("test query", "Transient error 1"),
            VectorSearchError("test query", "Transient error 2"),
            {
                "query": "test",
                "results": [],
                "total_results": 0,
                "returned_results": 0,
                "search_metadata": {
                    "vector_results_count": 0,
                    "bm25_results_count": 0,
                    "rrf_k": 60,
                    "reranking_applied": False,
                    "diversity_stats": {},
                },
            },
        ]
    )

    agent = VectorSearchAgent(hybrid_search=mock, max_retries=3)

    result_state = await agent.process(sample_state)

    # Should have retried 3 times total
    assert mock.hybrid_search.call_count == 3

    # Should succeed eventually
    assert "retrieved_contexts" in result_state
    assert "error" not in result_state["metadata"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_exhausted(sample_state):
    """Test that retries are exhausted and error is set."""
    mock = MagicMock()
    mock.hybrid_search = AsyncMock(side_effect=VectorSearchError("test query", "Persistent error"))

    agent = VectorSearchAgent(hybrid_search=mock, max_retries=3)

    result_state = await agent.process(sample_state)

    # Should have retried max times
    assert mock.hybrid_search.call_count == 3

    # Should have error in state
    assert "error" in result_state["metadata"]
    assert result_state["metadata"]["search"]["error"] is not None


# ============================================================================
# Test Result Conversion
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_convert_results_basic(mock_hybrid_search, sample_state):
    """Test conversion of HybridSearch results to state format."""
    agent = VectorSearchAgent(hybrid_search=mock_hybrid_search)

    result_state = await agent.process(sample_state)

    contexts = result_state["retrieved_contexts"]
    assert len(contexts) == 2

    # Check required fields
    for ctx in contexts:
        assert "id" in ctx
        assert "text" in ctx
        assert "score" in ctx
        assert "source" in ctx
        assert "document_id" in ctx
        assert "rank" in ctx
        assert "search_type" in ctx
        assert "metadata" in ctx


@pytest.mark.unit
@pytest.mark.asyncio
async def test_convert_results_with_rrf_metadata(mock_hybrid_search, sample_state):
    """Test that RRF metadata is preserved."""
    agent = VectorSearchAgent(hybrid_search=mock_hybrid_search)

    result_state = await agent.process(sample_state)

    ctx = result_state["retrieved_contexts"][0]
    assert "rrf_score" in ctx["metadata"]
    assert ctx["metadata"]["rrf_score"] == 0.95
    assert "rrf_rank" in ctx["metadata"]


# ============================================================================
# Test Node Function
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_search_node(sample_state):
    """Test the vector_search_node function."""
    with patch("src.agents.vector_search_agent.VectorSearchAgent") as mock_agent_cls:
        mock_instance = MagicMock()
        mock_instance.process = AsyncMock(return_value=sample_state)
        mock_agent_cls.return_value = mock_instance

        result = await vector_search_node(sample_state)

        # Should instantiate agent
        mock_agent_cls.assert_called_once()

        # Should call process
        mock_instance.process.assert_called_once_with(sample_state)

        # Should return result
        assert result == sample_state


# ============================================================================
# Test State Updates
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_state_metadata_tracking(mock_hybrid_search, sample_state):
    """Test that state metadata is properly tracked."""
    agent = VectorSearchAgent(hybrid_search=mock_hybrid_search)

    result_state = await agent.process(sample_state)

    # Check metadata structure
    assert "metadata" in result_state
    metadata = result_state["metadata"]

    # Check agent path
    assert "agent_path" in metadata
    assert len(metadata["agent_path"]) >= 2  # started + completed

    # Check search metadata
    assert "search" in metadata
    search_meta = metadata["search"]
    assert "latency_ms" in search_meta
    assert "result_count" in search_meta
    assert "search_mode" in search_meta


@pytest.mark.unit
@pytest.mark.asyncio
async def test_latency_measurement(mock_hybrid_search, sample_state):
    """Test that latency is measured correctly."""
    agent = VectorSearchAgent(hybrid_search=mock_hybrid_search)

    result_state = await agent.process(sample_state)

    latency = result_state["metadata"]["search"]["latency_ms"]
    assert latency > 0
    assert latency < 10000  # Should be less than 10 seconds


# ============================================================================
# Test Edge Cases
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_results(sample_state):
    """Test handling of empty search results."""
    mock = MagicMock()
    mock.hybrid_search = AsyncMock(
        return_value={
            "query": "test",
            "results": [],
            "total_results": 0,
            "returned_results": 0,
            "search_metadata": {
                "vector_results_count": 0,
                "bm25_results_count": 0,
                "rrf_k": 60,
                "reranking_applied": False,
                "diversity_stats": {},
            },
        }
    )

    agent = VectorSearchAgent(hybrid_search=mock)

    result_state = await agent.process(sample_state)

    # Should have empty contexts
    assert result_state["retrieved_contexts"] == []
    assert result_state["metadata"]["search"]["result_count"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_malformed_results(sample_state):
    """Test handling of malformed search results."""
    mock = MagicMock()
    mock.hybrid_search = AsyncMock(
        return_value={
            "query": "test",
            "results": [
                {
                    "id": "doc1",
                    # Missing required fields
                }
            ],
            "total_results": 1,
            "returned_results": 1,
            "search_metadata": {
                "vector_results_count": 1,
                "bm25_results_count": 0,
                "rrf_k": 60,
                "reranking_applied": False,
                "diversity_stats": {},
            },
        }
    )

    agent = VectorSearchAgent(hybrid_search=mock)

    result_state = await agent.process(sample_state)

    # Should handle missing fields with defaults
    ctx = result_state["retrieved_contexts"][0]
    assert ctx["id"] == "doc1"
    assert ctx["text"] == ""  # Default
    assert ctx["score"] == 0.0  # Default
