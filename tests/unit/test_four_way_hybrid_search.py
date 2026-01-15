"""Unit tests for 4-Way Hybrid Search with Intent-Weighted RRF.

Sprint 42 - Feature: 4-Way Hybrid RRF (TD-057)

This module tests the FourWayHybridSearch component that combines four
retrieval channels (vector, BM25, graph local, graph global) with
intent-weighted RRF fusion.

Test Coverage:
- Search with all 4 channels working
- Search with some channels failing (graceful degradation)
- Intent-weighted RRF fusion
- Intent override functionality
- Reranking integration
- Metadata handling across channels
- Latency tracking
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.retrieval.filters import MetadataFilters
from src.components.retrieval.four_way_hybrid_search import (
    FourWayHybridSearch,
    FourWaySearchMetadata,
    four_way_search,
    get_four_way_hybrid_search,
)
from src.components.retrieval.intent_classifier import (
    INTENT_WEIGHT_PROFILES,
    Intent,
    IntentClassificationResult,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_hybrid_search():
    """Create mock HybridSearch instance."""
    mock = AsyncMock()
    mock.vector_search = AsyncMock()
    mock.keyword_search = AsyncMock()
    mock.reranker = AsyncMock()
    mock.reranker.rerank = AsyncMock()
    return mock


@pytest.fixture
def mock_neo4j_client():
    """Create mock Neo4j client."""
    mock = AsyncMock()
    mock.execute_read = AsyncMock()
    return mock


@pytest.fixture
def four_way_search_engine(mock_hybrid_search, mock_neo4j_client):
    """Create FourWayHybridSearch with mocked dependencies."""
    return FourWayHybridSearch(
        hybrid_search=mock_hybrid_search,
        neo4j_client=mock_neo4j_client,
        rrf_k=60,
    )


@pytest.fixture
def sample_vector_results():
    """Sample vector search results."""
    return [
        {
            "id": "chunk_1",
            "text": "Vector search result 1",
            "source": "doc1.txt",
            "score": 0.95,
            "rank": 1,
        },
        {
            "id": "chunk_2",
            "text": "Vector search result 2",
            "source": "doc2.txt",
            "score": 0.85,
            "rank": 2,
        },
        {
            "id": "chunk_3",
            "text": "Vector search result 3",
            "source": "doc3.txt",
            "score": 0.75,
            "rank": 3,
        },
    ]


@pytest.fixture
def sample_bm25_results():
    """Sample BM25 search results."""
    return [
        {
            "id": "chunk_2",
            "text": "BM25 search result 2",
            "source": "doc2.txt",
            "score": 0.92,
            "rank": 1,
        },
        {
            "id": "chunk_4",
            "text": "BM25 search result 4",
            "source": "doc4.txt",
            "score": 0.80,
            "rank": 2,
        },
    ]


@pytest.fixture
def sample_graph_local_results():
    """Sample graph local search results."""
    return [
        {
            "id": "chunk_1",
            "text": "Graph local result 1",
            "source": "doc1.txt",
            "score": 2,
            "rank": 1,
            "matched_entities": ["entity_A", "entity_B"],
        },
        {
            "id": "chunk_5",
            "text": "Graph local result 5",
            "source": "doc5.txt",
            "score": 1,
            "rank": 2,
            "matched_entities": ["entity_C"],
        },
    ]


@pytest.fixture
def sample_graph_global_results():
    """Sample graph global search results."""
    return [
        {
            "id": "chunk_3",
            "text": "Graph global result 3",
            "source": "doc3.txt",
            "score": 5,
            "rank": 1,
            "community_id": "community_1",
        },
        {
            "id": "chunk_6",
            "text": "Graph global result 6",
            "source": "doc6.txt",
            "score": 3,
            "rank": 2,
            "community_id": "community_2",
        },
    ]


# ============================================================================
# Test FourWaySearchMetadata
# ============================================================================


class TestFourWaySearchMetadata:
    """Test FourWaySearchMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating FourWaySearchMetadata - Sprint 92: Updated to use dense/sparse."""
        metadata = FourWaySearchMetadata(
            dense_results_count=3,  # Sprint 92: Use dense instead of vector
            sparse_results_count=2,  # Sprint 92: Use sparse instead of bm25
            graph_local_results_count=2,
            graph_global_results_count=2,
            intent="factual",
            intent_confidence=0.95,
            intent_method="rule_based",
            intent_latency_ms=2.5,
            weights={"dense": 0.3, "sparse": 0.3, "local": 0.4, "global": 0.0},
            total_latency_ms=150.5,
            channels_executed=["multivector", "graph_local"],  # Sprint 88: multivector replaces vector+bm25
            namespaces_searched=["default"],  # Sprint 41: Namespace isolation
        )

        assert metadata.dense_results_count == 3
        assert metadata.sparse_results_count == 2
        assert metadata.intent == "factual"
        assert metadata.total_latency_ms == 150.5

    def test_metadata_channels_executed(self):
        """Test channels_executed field - Sprint 92: Updated to use multivector."""
        metadata = FourWaySearchMetadata(
            dense_results_count=5,  # Sprint 92
            sparse_results_count=0,  # Sprint 92
            graph_local_results_count=3,
            graph_global_results_count=0,
            intent="keyword",
            intent_confidence=0.8,
            intent_method="llm",
            intent_latency_ms=5.0,
            weights={"dense": 0.1, "sparse": 0.6, "local": 0.3, "global": 0.0},
            total_latency_ms=200.0,
            channels_executed=["multivector", "graph_local"],  # Sprint 88
            namespaces_searched=["default"],  # Sprint 41: Namespace isolation
        )

        assert len(metadata.channels_executed) == 2
        assert "multivector" in metadata.channels_executed  # Sprint 88: multivector replaces vector
        assert "bm25" not in metadata.channels_executed


# ============================================================================
# Test Initialization
# ============================================================================


class TestInitialization:
    """Test FourWayHybridSearch initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        with (
            patch("src.components.retrieval.four_way_hybrid_search.HybridSearch") as mock_hybrid,
            patch("src.components.retrieval.four_way_hybrid_search.Neo4jClient") as mock_neo4j,
        ):
            search = FourWayHybridSearch()

            assert search.rrf_k == 60
            mock_hybrid.assert_called_once()
            mock_neo4j.assert_called_once()

    def test_init_with_custom_rrf_k(self, mock_hybrid_search, mock_neo4j_client):
        """Test initialization with custom RRF k value."""
        search = FourWayHybridSearch(
            hybrid_search=mock_hybrid_search,
            neo4j_client=mock_neo4j_client,
            rrf_k=100,
        )

        assert search.rrf_k == 100

    def test_init_stores_dependencies(self, mock_hybrid_search, mock_neo4j_client):
        """Test initialization stores dependencies."""
        search = FourWayHybridSearch(
            hybrid_search=mock_hybrid_search,
            neo4j_client=mock_neo4j_client,
        )

        assert search.hybrid_search is mock_hybrid_search
        assert search.neo4j_client is mock_neo4j_client


# ============================================================================
# Test Search with All Channels Working
# ============================================================================


@pytest.mark.integration  # Requires complex mock setup, may need update after Sprint 41
class TestSearchAllChannelsWorking:
    """Test search when all 4 channels are operational."""

    @pytest.mark.skip(reason="Mock structure needs refactoring for Sprint 56 domains/ migration")
    @pytest.mark.asyncio
    async def test_search_all_channels_factual_intent(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test search with all channels for factual intent."""
        # Setup mocks
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        # Mock intent classification
        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.FACTUAL,
                weights=INTENT_WEIGHT_PROFILES[Intent.FACTUAL],
                confidence=0.95,
                latency_ms=5.0,
                method="rule_based",
            )

            result = await four_way_search_engine.search("What is X?", top_k=5)

        # Verify result structure
        assert "query" in result
        assert "results" in result
        assert "intent" in result
        assert "weights" in result
        assert "metadata" in result

        assert result["query"] == "What is X?"
        assert result["intent"] == "factual"
        assert len(result["results"]) <= 5

        # Verify metadata
        metadata = result["metadata"]
        assert metadata.vector_results_count == 3
        assert metadata.bm25_results_count == 2
        assert metadata.graph_local_results_count == 2
        # FACTUAL has zero global weight, so graph_global won't execute
        assert metadata.graph_global_results_count == 0
        assert "vector" in metadata.channels_executed
        assert "bm25" in metadata.channels_executed
        assert "graph_local" in metadata.channels_executed
        # graph_global won't execute for FACTUAL intent (weight=0.0)
        assert "graph_global" not in metadata.channels_executed

    @pytest.mark.asyncio
    async def test_search_executes_all_channels_in_parallel(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test that all channels execute in parallel for EXPLORATORY intent."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.EXPLORATORY,
                weights=INTENT_WEIGHT_PROFILES[Intent.EXPLORATORY],
                confidence=0.9,
                latency_ms=5.0,
                method="rule_based",
            )

            result = await four_way_search_engine.search("How does X work?", top_k=5)

        # EXPLORATORY intent has all weights > 0, so all channels execute
        # Sprint 88/92: multivector replaces separate vector+bm25 channels
        metadata = result["metadata"]
        assert "multivector" in metadata.channels_executed  # Sprint 88: vector+bm25 → multivector
        assert "graph_local" in metadata.channels_executed
        assert "graph_global" in metadata.channels_executed
        assert len(metadata.channels_executed) == 3  # Sprint 88: 4→3 (multivector, graph_local, graph_global)

    @pytest.mark.asyncio
    async def test_search_respects_top_k(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test search returns exactly top_k results."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.SUMMARY,
                weights=INTENT_WEIGHT_PROFILES[Intent.SUMMARY],
                confidence=0.85,
                latency_ms=4.0,
                method="rule_based",
            )

            result = await four_way_search_engine.search("Summarize X", top_k=3)

        assert len(result["results"]) <= 3

    @pytest.mark.skip(reason="Mock structure needs refactoring for Sprint 56 domains/ migration")
    @pytest.mark.asyncio
    async def test_search_with_filters(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test search with metadata filters applied."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        filters = MetadataFilters(source="doc1.txt")

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.KEYWORD,
                weights=INTENT_WEIGHT_PROFILES[Intent.KEYWORD],
                confidence=0.92,
                latency_ms=3.0,
                method="rule_based",
            )

            await four_way_search_engine.search("Find X", top_k=5, filters=filters)

        # Verify filters passed to vector search
        four_way_search_engine.hybrid_search.vector_search.assert_called_once()
        call_kwargs = four_way_search_engine.hybrid_search.vector_search.call_args[1]
        assert call_kwargs.get("filters") is filters


# ============================================================================
# Test Search with Failing Channels (Graceful Degradation)
# ============================================================================


@pytest.mark.integration  # Requires complex mock setup, may need update after Sprint 41
class TestGracefulDegradation:
    """Test search when some channels fail."""

    @pytest.mark.asyncio
    async def test_search_vector_channel_fails(
        self,
        four_way_search_engine,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test search gracefully handles vector search failure."""
        # Vector search fails
        four_way_search_engine.hybrid_search.vector_search.side_effect = Exception(
            "Vector search failed"
        )
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.KEYWORD,
                weights=INTENT_WEIGHT_PROFILES[Intent.KEYWORD],
                confidence=0.9,
                latency_ms=5.0,
                method="rule_based",
            )

            result = await four_way_search_engine.search("Find X", top_k=5)

        # Should still return results from other channels
        # Sprint 92: Use dense/sparse counts instead of vector/bm25
        assert "results" in result
        assert result["metadata"].dense_results_count == 0
        assert result["metadata"].sparse_results_count == 0  # Sprint 92: multivector fails completely (no separate sparse)

    @pytest.mark.skip(reason="Mock structure needs refactoring for Sprint 56 domains/ migration")
    @pytest.mark.asyncio
    async def test_search_bm25_channel_fails(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test search gracefully handles BM25 search failure."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.side_effect = Exception(
            "BM25 search failed"
        )
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.FACTUAL,
                weights=INTENT_WEIGHT_PROFILES[Intent.FACTUAL],
                confidence=0.95,
                latency_ms=5.0,
                method="rule_based",
            )

            result = await four_way_search_engine.search("What is X?", top_k=5)

        assert "results" in result
        assert result["metadata"].bm25_results_count == 0
        assert result["metadata"].vector_results_count > 0

    @pytest.mark.asyncio
    async def test_search_graph_channels_fail(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
    ):
        """Test search when both graph channels fail - Sprint 88/92: Updated for multivector."""
        # Sprint 88: Mock multivector_search instead of separate vector/keyword
        four_way_search_engine.multi_vector_search.hybrid_search = AsyncMock(
            return_value=sample_vector_results
        )
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            Exception("Neo4j error - graph_local"),
            Exception("Neo4j error - graph_global"),
        ]

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.EXPLORATORY,
                weights=INTENT_WEIGHT_PROFILES[Intent.EXPLORATORY],
                confidence=0.85,
                latency_ms=5.0,
                method="rule_based",
            )

            result = await four_way_search_engine.search("How does X work?", top_k=5)

        # Should still have results from multivector (Sprint 88: vector+bm25 → multivector)
        assert len(result["results"]) > 0
        # Graph channels should have failed
        assert result["metadata"].graph_local_results_count == 0
        assert result["metadata"].graph_global_results_count == 0

    @pytest.mark.asyncio
    async def test_search_all_channels_fail(
        self,
        four_way_search_engine,
    ):
        """Test search when all channels fail returns empty results."""
        four_way_search_engine.hybrid_search.vector_search.side_effect = Exception("Vector failed")
        four_way_search_engine.hybrid_search.keyword_search.side_effect = Exception("BM25 failed")
        four_way_search_engine.neo4j_client.execute_read.side_effect = Exception("Neo4j failed")

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.KEYWORD,
                weights=INTENT_WEIGHT_PROFILES[Intent.KEYWORD],
                confidence=0.9,
                latency_ms=5.0,
                method="rule_based",
            )

            result = await four_way_search_engine.search("Search X", top_k=5)

        # Should return empty results
        assert len(result["results"]) == 0
        assert result["metadata"].vector_results_count == 0
        assert result["metadata"].bm25_results_count == 0
        assert result["metadata"].graph_local_results_count == 0
        assert result["metadata"].graph_global_results_count == 0


# ============================================================================
# Test Intent-Weighted RRF
# ============================================================================


class TestIntentWeightedRRF:
    """Test intent-weighted RRF fusion."""

    @pytest.mark.asyncio
    async def test_factual_intent_weights_rrf(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test RRF uses FACTUAL intent weights correctly."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        factual_weights = INTENT_WEIGHT_PROFILES[Intent.FACTUAL]

        with (
            patch(
                "src.components.retrieval.four_way_hybrid_search.classify_intent"
            ) as mock_classify,
            patch(
                "src.components.retrieval.four_way_hybrid_search.weighted_reciprocal_rank_fusion"
            ) as mock_rrf,
        ):
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.FACTUAL,
                weights=factual_weights,
                confidence=0.95,
                latency_ms=5.0,
                method="rule_based",
            )
            mock_rrf.return_value = []

            await four_way_search_engine.search("What is X?", top_k=5)

            # Verify RRF called with correct weights
            mock_rrf.assert_called_once()
            call_kwargs = mock_rrf.call_args[1]
            weights = call_kwargs["weights"]

            # FACTUAL: vector=0.3, bm25=0.3, local=0.4, global=0.0
            assert weights[0] == 0.3  # vector
            assert weights[1] == 0.3  # bm25
            assert weights[2] == 0.4  # local

    @pytest.mark.asyncio
    async def test_keyword_intent_weights_rrf(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test RRF uses KEYWORD intent weights correctly."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        keyword_weights = INTENT_WEIGHT_PROFILES[Intent.KEYWORD]

        with (
            patch(
                "src.components.retrieval.four_way_hybrid_search.classify_intent"
            ) as mock_classify,
            patch(
                "src.components.retrieval.four_way_hybrid_search.weighted_reciprocal_rank_fusion"
            ) as mock_rrf,
        ):
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.KEYWORD,
                weights=keyword_weights,
                confidence=0.92,
                latency_ms=5.0,
                method="rule_based",
            )
            mock_rrf.return_value = []

            await four_way_search_engine.search("Find JWT API", top_k=5)

            call_kwargs = mock_rrf.call_args[1]
            weights = call_kwargs["weights"]

            # KEYWORD: vector=0.1, bm25=0.6, local=0.3, global=0.0
            assert weights[1] == 0.6  # bm25 (highest)
            assert weights[0] == 0.1  # vector (lowest)

    @pytest.mark.asyncio
    async def test_exploratory_intent_weights_rrf(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test RRF uses EXPLORATORY intent weights correctly."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        exploratory_weights = INTENT_WEIGHT_PROFILES[Intent.EXPLORATORY]

        with (
            patch(
                "src.components.retrieval.four_way_hybrid_search.classify_intent"
            ) as mock_classify,
            patch(
                "src.components.retrieval.four_way_hybrid_search.weighted_reciprocal_rank_fusion"
            ) as mock_rrf,
        ):
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.EXPLORATORY,
                weights=exploratory_weights,
                confidence=0.88,
                latency_ms=5.0,
                method="rule_based",
            )
            mock_rrf.return_value = []

            await four_way_search_engine.search("How does X work?", top_k=5)

            call_kwargs = mock_rrf.call_args[1]
            weights = call_kwargs["weights"]

            # EXPLORATORY: vector=0.2, bm25=0.1, local=0.2, global=0.5
            assert weights[3] == 0.5  # global (highest)

    @pytest.mark.asyncio
    async def test_summary_intent_weights_rrf(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test RRF uses SUMMARY intent weights correctly."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        summary_weights = INTENT_WEIGHT_PROFILES[Intent.SUMMARY]

        with (
            patch(
                "src.components.retrieval.four_way_hybrid_search.classify_intent"
            ) as mock_classify,
            patch(
                "src.components.retrieval.four_way_hybrid_search.weighted_reciprocal_rank_fusion"
            ) as mock_rrf,
        ):
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.SUMMARY,
                weights=summary_weights,
                confidence=0.90,
                latency_ms=5.0,
                method="rule_based",
            )
            mock_rrf.return_value = []

            await four_way_search_engine.search("Summarize X", top_k=5)

            call_kwargs = mock_rrf.call_args[1]
            weights = call_kwargs["weights"]

            # SUMMARY: vector=0.1, bm25=0.0, local=0.1, global=0.8
            # Only vector, local, and global execute (BM25 has weight 0.0)
            # weights will be [vector=0.1, local=0.1, global=0.8]
            assert len(weights) == 3
            assert weights[0] == 0.1  # vector
            assert weights[1] == 0.1  # local
            assert weights[2] == 0.8  # global (very high)


# ============================================================================
# Test Intent Override
# ============================================================================


class TestIntentOverride:
    """Test intent override functionality."""

    @pytest.mark.asyncio
    async def test_intent_override_factual(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test overriding intent to FACTUAL."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            result = await four_way_search_engine.search(
                "Ambiguous query",
                top_k=5,
                intent_override=Intent.FACTUAL,
            )

            # Classify should NOT be called
            mock_classify.assert_not_called()

        assert result["intent"] == "factual"
        assert result["metadata"].intent == "factual"
        assert result["metadata"].intent_method == "override"

    @pytest.mark.asyncio
    async def test_intent_override_keyword(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test overriding intent to KEYWORD."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        result = await four_way_search_engine.search(
            "Query",
            top_k=5,
            intent_override=Intent.KEYWORD,
        )

        assert result["intent"] == "keyword"
        assert result["weights"]["bm25"] == 0.6  # KEYWORD has high BM25

    @pytest.mark.asyncio
    async def test_intent_override_exploratory(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test overriding intent to EXPLORATORY."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        result = await four_way_search_engine.search(
            "Query",
            top_k=5,
            intent_override=Intent.EXPLORATORY,
        )

        assert result["intent"] == "exploratory"
        assert result["weights"]["global"] == 0.5  # EXPLORATORY has high global

    @pytest.mark.asyncio
    async def test_intent_override_summary(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test overriding intent to SUMMARY."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        result = await four_way_search_engine.search(
            "Query",
            top_k=5,
            intent_override=Intent.SUMMARY,
        )

        assert result["intent"] == "summary"
        assert result["weights"]["global"] == 0.8  # SUMMARY has very high global


# ============================================================================
# Test Reranking Integration
# ============================================================================


class TestReranking:
    """Test reranking integration."""

    @pytest.mark.skip(reason="Mock structure needs refactoring for Sprint 56 domains/ migration")
    @pytest.mark.asyncio
    async def test_search_with_reranking_enabled(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test search with reranking enabled."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        # Mock reranker
        reranked_results = [
            MagicMock(doc_id="chunk_1", rerank_score=0.99, final_rank=1),
            MagicMock(doc_id="chunk_2", rerank_score=0.95, final_rank=2),
        ]
        four_way_search_engine.hybrid_search.reranker.rerank.return_value = reranked_results

        with (
            patch(
                "src.components.retrieval.four_way_hybrid_search.classify_intent"
            ) as mock_classify,
            patch(
                "src.components.retrieval.four_way_hybrid_search.weighted_reciprocal_rank_fusion"
            ) as mock_rrf,
        ):
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.FACTUAL,
                weights=INTENT_WEIGHT_PROFILES[Intent.FACTUAL],
                confidence=0.95,
                latency_ms=5.0,
                method="rule_based",
            )

            # Mock RRF to return some results
            mock_rrf.return_value = [
                {"id": "chunk_1", "text": "Result 1"},
                {"id": "chunk_2", "text": "Result 2"},
                {"id": "chunk_3", "text": "Result 3"},
            ]

            result = await four_way_search_engine.search("What is X?", top_k=5, use_reranking=True)

        # Verify reranker was called
        four_way_search_engine.hybrid_search.reranker.rerank.assert_called_once()

        # Verify results have reranking scores
        assert "rerank_score" in result["results"][0]
        assert "final_rank" in result["results"][0]

    @pytest.mark.asyncio
    async def test_search_without_reranking(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test search without reranking."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        with (
            patch(
                "src.components.retrieval.four_way_hybrid_search.classify_intent"
            ) as mock_classify,
            patch(
                "src.components.retrieval.four_way_hybrid_search.weighted_reciprocal_rank_fusion"
            ) as mock_rrf,
        ):
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.FACTUAL,
                weights=INTENT_WEIGHT_PROFILES[Intent.FACTUAL],
                confidence=0.95,
                latency_ms=5.0,
                method="rule_based",
            )
            mock_rrf.return_value = [
                {"id": "chunk_1", "text": "Result 1"},
                {"id": "chunk_2", "text": "Result 2"},
            ]

            await four_way_search_engine.search("What is X?", top_k=5, use_reranking=False)

        # Reranker should NOT be called
        four_way_search_engine.hybrid_search.reranker.rerank.assert_not_called()


# ============================================================================
# Test Latency Tracking
# ============================================================================


class TestLatencyTracking:
    """Test latency tracking in metadata."""

    @pytest.mark.asyncio
    async def test_total_latency_tracked(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test total latency is tracked."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.FACTUAL,
                weights=INTENT_WEIGHT_PROFILES[Intent.FACTUAL],
                confidence=0.95,
                latency_ms=5.5,
                method="rule_based",
            )

            result = await four_way_search_engine.search("What is X?", top_k=5)

        metadata = result["metadata"]
        assert metadata.total_latency_ms > 0
        assert metadata.intent_latency_ms == 5.5

    @pytest.mark.asyncio
    async def test_intent_latency_in_metadata(
        self,
        four_way_search_engine,
        sample_vector_results,
        sample_bm25_results,
        sample_graph_local_results,
        sample_graph_global_results,
    ):
        """Test intent classification latency in metadata."""
        four_way_search_engine.hybrid_search.vector_search.return_value = sample_vector_results
        four_way_search_engine.hybrid_search.keyword_search.return_value = sample_bm25_results
        four_way_search_engine.neo4j_client.execute_read.side_effect = [
            sample_graph_local_results,
            sample_graph_global_results,
        ]

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = IntentClassificationResult(
                intent=Intent.KEYWORD,
                weights=INTENT_WEIGHT_PROFILES[Intent.KEYWORD],
                confidence=0.92,
                latency_ms=3.2,
                method="llm",
            )

            result = await four_way_search_engine.search("Find X", top_k=5)

        metadata = result["metadata"]
        assert metadata.intent_latency_ms == 3.2
        assert metadata.intent_method == "llm"


# ============================================================================
# Test Singleton Functions
# ============================================================================


class TestSingletonFunctions:
    """Test singleton getter functions."""

    def test_get_four_way_hybrid_search_returns_instance(self):
        """Test get_four_way_hybrid_search returns instance."""
        with (
            patch("src.components.retrieval.four_way_hybrid_search.HybridSearch"),
            patch("src.components.retrieval.four_way_hybrid_search.Neo4jClient"),
        ):
            search = get_four_way_hybrid_search()

            assert isinstance(search, FourWayHybridSearch)

    def test_get_four_way_hybrid_search_singleton(self):
        """Test get_four_way_hybrid_search returns same instance."""
        with (
            patch("src.components.retrieval.four_way_hybrid_search.HybridSearch"),
            patch("src.components.retrieval.four_way_hybrid_search.Neo4jClient"),
        ):
            search1 = get_four_way_hybrid_search()
            search2 = get_four_way_hybrid_search()

            assert search1 is search2

    @pytest.mark.asyncio
    async def test_four_way_search_function(self):
        """Test four_way_search convenience function."""
        mock_search_engine = AsyncMock()
        mock_result = {
            "query": "Test query",
            "results": [],
            "intent": "factual",
            "weights": {},
            "metadata": MagicMock(),
        }
        mock_search_engine.search.return_value = mock_result

        with patch(
            "src.components.retrieval.four_way_hybrid_search.get_four_way_hybrid_search"
        ) as mock_get:
            mock_get.return_value = mock_search_engine

            result = await four_way_search("Test query", top_k=10)

            assert result == mock_result
            mock_search_engine.search.assert_called_once()
