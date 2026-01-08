"""Unit tests for SmartEntityExpander (Sprint 78 Feature 78.2).

Tests the 3-stage entity expansion pipeline:
- Stage 1: LLM entity extraction
- Stage 2: Graph-based N-hop expansion
- Stage 3: LLM synonym generation (fallback)
- Stage 4: Semantic reranking via BGE-M3
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.graph_rag.entity_expansion import SmartEntityExpander
from src.domains.llm_integration.models import LLMResponse


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4jClient for graph operations."""
    client = MagicMock()
    client.execute_read = AsyncMock()
    return client


@pytest.fixture
def mock_llm_proxy():
    """Mock AegisLLMProxy for LLM operations."""
    proxy = MagicMock()
    proxy.generate = AsyncMock()
    return proxy


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for semantic operations."""
    service = MagicMock()
    service.encode = AsyncMock()
    return service


@pytest.fixture
def entity_expander(mock_neo4j_client, mock_llm_proxy, mock_embedding_service):
    """SmartEntityExpander instance with mocked dependencies."""
    with patch("src.components.graph_rag.entity_expansion.get_aegis_llm_proxy", return_value=mock_llm_proxy), \
         patch("src.components.graph_rag.entity_expansion.get_embedding_service", return_value=mock_embedding_service):
        expander = SmartEntityExpander(
            neo4j_client=mock_neo4j_client,
            graph_expansion_hops=1,
            min_entities_threshold=10,
            max_synonyms_per_entity=3,
        )
        return expander


class TestSmartEntityExpander:
    """Test suite for SmartEntityExpander."""

    @pytest.mark.asyncio
    async def test_extract_entities_llm_basic(self, entity_expander, mock_llm_proxy):
        """Test Stage 1: LLM extracts entities from query."""
        # Mock LLM response
        mock_llm_proxy.generate.return_value = LLMResponse(
            content="global implications\nabortion\nreproductive rights",
            provider="local_ollama",
            model="nemotron-3-nano",
            tokens_used=50,
            tokens_input=30,
            tokens_output=20,
            cost_usd=0.0,
            latency_ms=100,
        )

        # Execute
        entities = await entity_expander._extract_entities_llm("What are the global implications of abortion?")

        # Verify
        assert len(entities) == 3
        assert "global implications" in entities
        assert "abortion" in entities
        assert "reproductive rights" in entities
        mock_llm_proxy.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_entities_llm_deduplication(self, entity_expander, mock_llm_proxy):
        """Test Stage 1: LLM entity extraction with deduplication."""
        # Mock LLM response with duplicates
        mock_llm_proxy.generate.return_value = LLMResponse(
            content="abortion\nAbortion\nABORTION\nreproductive rights",
            provider="local_ollama",
            model="nemotron-3-nano",
            tokens_used=50,
            tokens_input=30,
            tokens_output=20,
            cost_usd=0.0,
            latency_ms=100,
        )

        # Execute
        entities = await entity_expander._extract_entities_llm("Question about abortion")

        # Verify - should deduplicate case-insensitive
        assert len(entities) == 2
        assert "abortion" in entities
        assert "reproductive rights" in entities

    @pytest.mark.asyncio
    async def test_extract_entities_llm_filters_noise(self, entity_expander, mock_llm_proxy):
        """Test Stage 1: LLM entity extraction filters noise."""
        # Mock LLM response with noise
        mock_llm_proxy.generate.return_value = LLMResponse(
            content="# Header\nabortion\n- bullet point\nreproductive rights\n\n\nUSA",
            provider="local_ollama",
            model="nemotron-3-nano",
            tokens_used=50,
            tokens_input=30,
            tokens_output=20,
            cost_usd=0.0,
            latency_ms=100,
        )

        # Execute
        entities = await entity_expander._extract_entities_llm("Question")

        # Verify - should filter headers, bullets, empty lines
        assert "abortion" in entities
        assert "reproductive rights" in entities
        assert "USA" in entities
        assert "# Header" not in entities
        assert "- bullet point" not in entities

    @pytest.mark.asyncio
    async def test_expand_via_graph_1hop(self, entity_expander, mock_neo4j_client):
        """Test Stage 2: Graph expansion with 1-hop traversal."""
        # Mock Neo4j response - correct field name is "name" not "entity_name"
        mock_neo4j_client.execute_read.return_value = [
            {"name": "abortion"},
            {"name": "reproductive rights"},
            {"name": "women's health"},  # 1-hop neighbor
        ]

        # Execute
        expanded = await entity_expander._expand_via_graph(
            initial_entities=["abortion"],
            namespaces=["amnesty_qa"],
            max_hops=1
        )

        # Verify
        assert len(expanded) == 3
        assert "abortion" in expanded
        assert "reproductive rights" in expanded
        assert "women's health" in expanded
        mock_neo4j_client.execute_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_expand_via_graph_3hop(self, entity_expander, mock_neo4j_client):
        """Test Stage 2: Graph expansion with 3-hop traversal."""
        # Mock Neo4j response for 3-hop - correct field name is "name"
        mock_neo4j_client.execute_read.return_value = [
            {"name": "abortion"},
            {"name": "reproductive rights"},  # 1-hop
            {"name": "women's health"},  # 2-hop
            {"name": "Supreme Court"},  # 3-hop
        ]

        # Execute with 3 hops
        entity_expander.graph_expansion_hops = 3
        expanded = await entity_expander._expand_via_graph(
            initial_entities=["abortion"],
            namespaces=["amnesty_qa"],
            max_hops=3
        )

        # Verify
        assert len(expanded) == 4
        # Check Cypher query contains 3-hop path pattern
        call_args = mock_neo4j_client.execute_read.call_args
        cypher_query = call_args[0][0]
        assert "*1..3" in cypher_query  # Variable-length path up to 3 hops

    @pytest.mark.asyncio
    async def test_generate_synonyms_llm_basic(self, entity_expander, mock_llm_proxy):
        """Test Stage 3: LLM synonym generation."""
        # Mock LLM response
        mock_llm_proxy.generate.return_value = LLMResponse(
            content="pregnancy termination\ninduced abortion\nreproductive choice",
            provider="local_ollama",
            model="nemotron-3-nano",
            tokens_used=50,
            tokens_input=30,
            tokens_output=20,
            cost_usd=0.0,
            latency_ms=100,
        )

        # Execute
        synonyms = await entity_expander._generate_synonyms_llm(
            entities=["abortion"],
            max_per_entity=3
        )

        # Verify
        assert len(synonyms) == 3
        assert "pregnancy termination" in synonyms
        assert "induced abortion" in synonyms
        assert "reproductive choice" in synonyms

    @pytest.mark.asyncio
    async def test_generate_synonyms_llm_respects_max(self, entity_expander, mock_llm_proxy):
        """Test Stage 3: LLM synonym generation respects max_per_entity."""
        # Mock LLM response with many synonyms
        mock_llm_proxy.generate.return_value = LLMResponse(
            content="syn1\nsyn2\nsyn3\nsyn4\nsyn5\nsyn6\nsyn7\nsyn8",
            provider="local_ollama",
            model="nemotron-3-nano",
            tokens_used=50,
            tokens_input=30,
            tokens_output=20,
            cost_usd=0.0,
            latency_ms=100,
        )

        # Execute with max=3 per entity, 2 entities
        synonyms = await entity_expander._generate_synonyms_llm(
            entities=["abortion", "rights"],
            max_per_entity=3
        )

        # Verify - should get 3 * 2 = 6 synonyms max
        assert len(synonyms) <= 6

    @pytest.mark.asyncio
    async def test_expand_entities_3stage_no_fallback(self, entity_expander, mock_llm_proxy, mock_neo4j_client):
        """Test full 3-stage pipeline when graph expansion sufficient (no synonym fallback)."""
        # Stage 1: LLM extracts entities
        mock_llm_proxy.generate.return_value = LLMResponse(
            content="abortion\nreproductive rights",
            provider="local_ollama",
            model="nemotron-3-nano",
            tokens_used=50,
            tokens_input=30,
            tokens_output=20,
            cost_usd=0.0,
            latency_ms=100,
        )

        # Stage 2: Graph expansion returns 12 entities (above threshold of 10)
        # Correct field name is "name" not "entity_name"
        mock_neo4j_client.execute_read.return_value = [
            {"name": f"entity_{i}"} for i in range(12)
        ]

        # Execute
        entity_expander.min_entities_threshold = 10
        expanded = await entity_expander.expand_entities(
            query="What are the global implications of abortion?",
            namespaces=["amnesty_qa"],
            top_k=10
        )

        # Verify - should NOT call LLM for synonyms (graph gave enough)
        assert len(expanded) == 12
        assert mock_llm_proxy.generate.call_count == 1  # Only Stage 1, not Stage 3

    @pytest.mark.asyncio
    async def test_expand_entities_3stage_with_fallback(self, entity_expander, mock_llm_proxy, mock_neo4j_client):
        """Test full 3-stage pipeline when graph sparse (triggers synonym fallback)."""
        # Stage 1: LLM extracts entities
        llm_responses = [
            # Stage 1: Entity extraction
            LLMResponse(
                content="abortion\nreproductive rights",
                provider="local_ollama",
                model="nemotron-3-nano",
                tokens_used=50,
                tokens_input=30,
                tokens_output=20,
                cost_usd=0.0,
                latency_ms=100,
            ),
            # Stage 3: Synonym generation
            LLMResponse(
                content="pregnancy termination\ninduced abortion\nreproductive choice",
                provider="local_ollama",
                model="nemotron-3-nano",
                tokens_used=50,
                tokens_input=30,
                tokens_output=20,
                cost_usd=0.0,
                latency_ms=100,
            )
        ]
        mock_llm_proxy.generate.side_effect = llm_responses

        # Stage 2: Graph expansion returns only 5 entities (below threshold of 10)
        # Correct field name is "name" not "entity_name"
        mock_neo4j_client.execute_read.return_value = [
            {"name": f"graph_entity_{i}"} for i in range(5)
        ]

        # Execute
        entity_expander.min_entities_threshold = 10
        expanded = await entity_expander.expand_entities(
            query="What are the global implications of abortion?",
            namespaces=["amnesty_qa"],
            top_k=10
        )

        # Verify - should call LLM twice (Stage 1 + Stage 3)
        assert mock_llm_proxy.generate.call_count == 2
        # Should have graph entities + synonyms
        assert len(expanded) == 8  # 5 from graph + 3 synonyms

    @pytest.mark.asyncio
    async def test_expand_and_rerank_semantic(self, entity_expander, mock_llm_proxy, mock_neo4j_client, mock_embedding_service):
        """Test Stage 4: Semantic reranking with BGE-M3."""
        # Setup Stage 1-3
        mock_llm_proxy.generate.return_value = LLMResponse(
            content="abortion",
            provider="local_ollama",
            model="nemotron-3-nano",
            tokens_used=50,
            tokens_input=30,
            tokens_output=20,
            cost_usd=0.0,
            latency_ms=100,
        )
        # Correct field name is "name" not "entity_name"
        mock_neo4j_client.execute_read.return_value = [
            {"name": "abortion"},
            {"name": "reproductive rights"},
            {"name": "climate change"},  # Low relevance
        ]

        # Mock embeddings for semantic similarity
        import numpy as np
        query_embedding = np.array([1.0, 0.0, 0.0])
        entity_embeddings = {
            "abortion": np.array([0.9, 0.1, 0.0]),  # High similarity (0.9)
            "reproductive rights": np.array([0.7, 0.3, 0.0]),  # Medium (0.7)
            "climate change": np.array([0.0, 0.0, 1.0]),  # Low (0.0)
        }

        async def mock_encode(text):
            # Query text has unique signature
            if "global implications" in text:
                return query_embedding
            # Entity names lookup
            return entity_embeddings.get(text, np.array([0.0, 0.0, 0.0]))

        mock_embedding_service.encode.side_effect = mock_encode

        # Execute
        ranked_entities = await entity_expander.expand_and_rerank(
            query="What are the global implications of abortion?",
            namespaces=["amnesty_qa"],
            top_k=3
        )

        # Verify semantic ranking
        assert len(ranked_entities) == 3
        # Should be ranked by cosine similarity
        entity_names = [e[0] for e in ranked_entities]
        entity_scores = [e[1] for e in ranked_entities]

        # abortion should be first (highest similarity)
        assert entity_names[0] == "abortion"
        assert entity_scores[0] > 0.8
        # Remaining should be ordered by score
        assert entity_scores[0] >= entity_scores[1] >= entity_scores[2]

    @pytest.mark.asyncio
    async def test_cosine_similarity_calculation(self, entity_expander):
        """Test cosine similarity calculation."""
        import numpy as np

        # Test orthogonal vectors (similarity = 0)
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        similarity = entity_expander._cosine_similarity(vec1, vec2)
        assert abs(similarity) < 0.01

        # Test identical vectors (similarity = 1)
        vec3 = np.array([1.0, 1.0, 1.0])
        vec4 = np.array([1.0, 1.0, 1.0])
        similarity = entity_expander._cosine_similarity(vec3, vec4)
        assert abs(similarity - 1.0) < 0.01

        # Test opposite vectors (similarity = -1)
        vec5 = np.array([1.0, 0.0, 0.0])
        vec6 = np.array([-1.0, 0.0, 0.0])
        similarity = entity_expander._cosine_similarity(vec5, vec6)
        assert abs(similarity - (-1.0)) < 0.01

    def test_initialization_validates_hops(self, mock_neo4j_client):
        """Test that initialization validates graph_expansion_hops range (1-3)."""
        with patch("src.components.graph_rag.entity_expansion.get_aegis_llm_proxy"), \
             patch("src.components.graph_rag.entity_expansion.get_embedding_service"):
            # Test minimum clamping
            expander = SmartEntityExpander(
                neo4j_client=mock_neo4j_client,
                graph_expansion_hops=0  # Below minimum
            )
            assert expander.graph_expansion_hops == 1

            # Test maximum clamping
            expander = SmartEntityExpander(
                neo4j_client=mock_neo4j_client,
                graph_expansion_hops=5  # Above maximum
            )
            assert expander.graph_expansion_hops == 3

    def test_initialization_validates_threshold(self, mock_neo4j_client):
        """Test that initialization validates min_entities_threshold range (5-20)."""
        with patch("src.components.graph_rag.entity_expansion.get_aegis_llm_proxy"), \
             patch("src.components.graph_rag.entity_expansion.get_embedding_service"):
            # Test minimum clamping
            expander = SmartEntityExpander(
                neo4j_client=mock_neo4j_client,
                min_entities_threshold=2  # Below minimum
            )
            assert expander.min_entities_threshold == 5

            # Test maximum clamping
            expander = SmartEntityExpander(
                neo4j_client=mock_neo4j_client,
                min_entities_threshold=30  # Above maximum
            )
            assert expander.min_entities_threshold == 20

    def test_initialization_validates_synonyms(self, mock_neo4j_client):
        """Test that initialization validates max_synonyms_per_entity range (1-5)."""
        with patch("src.components.graph_rag.entity_expansion.get_aegis_llm_proxy"), \
             patch("src.components.graph_rag.entity_expansion.get_embedding_service"):
            # Test minimum clamping
            expander = SmartEntityExpander(
                neo4j_client=mock_neo4j_client,
                max_synonyms_per_entity=0  # Below minimum
            )
            assert expander.max_synonyms_per_entity == 1

            # Test maximum clamping
            expander = SmartEntityExpander(
                neo4j_client=mock_neo4j_client,
                max_synonyms_per_entity=10  # Above maximum
            )
            assert expander.max_synonyms_per_entity == 5
