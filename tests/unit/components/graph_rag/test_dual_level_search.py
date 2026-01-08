"""Unit tests for dual-level search functionality.

Sprint 5: Feature 5.4 - Dual-Level Retrieval
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.dual_level_search import (
    DualLevelSearch,
    get_dual_level_search,
)
from src.core.models import GraphEntity, GraphQueryResult, GraphRelationship, Topic


class TestDualLevelSearch:
    """Test dual-level search functionality."""

    @pytest.fixture
    def mock_neo4j_client(self):
        """Mock Neo4j client."""
        with patch("src.components.graph_rag.dual_level_search.Neo4jClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.execute_read = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_llm_proxy(self):
        """Mock AegisLLMProxy."""
        mock_proxy = AsyncMock()
        mock_result = MagicMock()
        mock_result.content = "Mock answer from graph context."
        mock_result.provider = "local_ollama"
        mock_result.model = "llama3.2:8b"
        mock_result.cost_usd = 0.0
        mock_result.latency_ms = 100
        mock_proxy.generate.return_value = mock_result
        return mock_proxy

    @pytest.fixture
    def dual_level_search(self, mock_neo4j_client, mock_llm_proxy):
        """DualLevelSearch instance with mocked dependencies."""
        with patch(
            "src.components.graph_rag.dual_level_search.get_aegis_llm_proxy"
        ) as mock_get_proxy:
            mock_get_proxy.return_value = mock_llm_proxy
            search = DualLevelSearch(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="test",
                llm_model="llama3.2:8b",
                ollama_base_url="http://localhost:11434",
            )
            # Replace Neo4j client and proxy with mocks
            search.neo4j_client = mock_neo4j_client
            search.proxy = mock_llm_proxy
            return search

    def test_initialization(self, dual_level_search):
        """Test DualLevelSearch initializes correctly."""
        assert dual_level_search is not None
        assert dual_level_search.llm_model == "llama3.2:8b"
        assert dual_level_search.neo4j_uri == "bolt://localhost:7687"

    @pytest.mark.asyncio
    async def test_local_search_empty_results(self, dual_level_search, mock_neo4j_client):
        """Test local search with no matching entities."""
        mock_neo4j_client.execute_read = AsyncMock(return_value=[])

        entities = await dual_level_search.local_search("What is machine learning?", top_k=5)

        assert entities == []
        mock_neo4j_client.execute_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_local_search_with_results(self, dual_level_search, mock_neo4j_client):
        """Test local search with matching entities."""
        mock_results = [
            {
                "id": "e1",
                "name": "Machine Learning",
                "type": "CONCEPT",
                "description": "Field of artificial intelligence",
                "properties": {},
                "source_document": "doc1",
                "confidence": 0.95,
            },
            {
                "id": "e2",
                "name": "Python",
                "type": "TECHNOLOGY",
                "description": "Programming language",
                "properties": {},
                "source_document": "doc1",
                "confidence": 0.90,
            },
        ]

        mock_neo4j_client.execute_read = AsyncMock(return_value=mock_results)

        entities = await dual_level_search.local_search("machine learning with python", top_k=5)

        assert len(entities) == 2
        assert isinstance(entities[0], GraphEntity)
        assert entities[0].name == "Machine Learning"
        assert entities[0].type == "CONCEPT"
        assert entities[1].name == "Python"

    @pytest.mark.asyncio
    async def test_global_search_empty_results(self, dual_level_search, mock_neo4j_client):
        """Test global search with no matching topics."""
        mock_neo4j_client.execute_read = AsyncMock(return_value=[])

        topics = await dual_level_search.global_search("What are the main themes?", top_k=3)

        assert topics == []

    @pytest.mark.asyncio
    async def test_global_search_with_results(self, dual_level_search, mock_neo4j_client):
        """Test global search with matching topics."""
        mock_results = [
            {
                "topic_name": "TECHNOLOGY",
                "sample_entities": ["Python", "JavaScript", "Docker"],
                "entity_ids": ["e1", "e2", "e3"],
                "entity_count": 15,
            },
            {
                "topic_name": "PERSON",
                "sample_entities": ["John Smith", "Jane Doe"],
                "entity_ids": ["e4", "e5"],
                "entity_count": 8,
            },
        ]

        mock_neo4j_client.execute_read = AsyncMock(return_value=mock_results)

        topics = await dual_level_search.global_search("technology topics", top_k=3)

        assert len(topics) == 2
        assert isinstance(topics[0], Topic)
        assert topics[0].name == "TECHNOLOGY"
        assert topics[0].score >= topics[1].score  # Scores should be descending
        assert "Python" in topics[0].keywords

    @pytest.mark.asyncio
    async def test_get_entity_relationships_empty(self, dual_level_search, mock_neo4j_client):
        """Test getting relationships with no entities."""
        relationships = await dual_level_search._get_entity_relationships([])
        assert relationships == []

    @pytest.mark.asyncio
    async def test_get_entity_relationships_with_results(
        self, dual_level_search, mock_neo4j_client
    ):
        """Test getting relationships for entities."""
        entities = [
            GraphEntity(
                id="e1",
                name="John Smith",
                type="PERSON",
                description="Engineer",
            ),
            GraphEntity(
                id="e2",
                name="Google",
                type="ORGANIZATION",
                description="Company",
            ),
        ]

        mock_rel_results = [
            {
                "id": "r1",
                "source": "John Smith",
                "target": "Google",
                "type": "WORKS_AT",
                "description": "Employment relationship",
                "properties": {},
                "source_document": "doc1",
                "confidence": 0.92,
            }
        ]

        mock_neo4j_client.execute_read = AsyncMock(return_value=mock_rel_results)

        relationships = await dual_level_search._get_entity_relationships(entities)

        assert len(relationships) == 1
        assert isinstance(relationships[0], GraphRelationship)
        assert relationships[0].source == "John Smith"
        assert relationships[0].target == "Google"
        assert relationships[0].type == "WORKS_AT"

    def test_build_context_entities_only(self, dual_level_search):
        """Test building context with only entities."""
        entities = [
            GraphEntity(
                id="e1",
                name="Python",
                type="TECHNOLOGY",
                description="Programming language",
            )
        ]

        context = dual_level_search._build_context(entities, [], [])

        assert "Entities:" in context
        assert "Python" in context
        assert "TECHNOLOGY" in context

    def test_build_context_full(self, dual_level_search):
        """Test building context with entities, relationships, and topics."""
        entities = [
            GraphEntity(
                id="e1",
                name="Python",
                type="TECHNOLOGY",
                description="Programming language",
            )
        ]

        relationships = [
            GraphRelationship(
                id="r1",
                source="John",
                target="Python",
                type="USES",
                description="John uses Python",
            )
        ]

        topics = [
            Topic(
                id="t1",
                name="Programming",
                summary="Programming languages and tools",
                entities=["e1"],
                keywords=["Python", "coding"],
                score=0.9,
            )
        ]

        context = dual_level_search._build_context(entities, relationships, topics)

        assert "Entities:" in context
        assert "Python" in context
        assert "Relationships:" in context
        assert "USES" in context
        assert "Topics:" in context
        assert "Programming" in context

    @pytest.mark.asyncio
    async def test_generate_answer(self, dual_level_search):
        """Test answer generation from graph context via AegisLLMProxy."""
        context = "Entity: Python (TECHNOLOGY)\nRelationship: John-USES->Python"
        answer = await dual_level_search._generate_answer("What does John use?", context)

        assert answer == "Mock answer from graph context."
        dual_level_search.proxy.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_answer_error(self, dual_level_search):
        """Test answer generation handles errors gracefully."""
        dual_level_search.proxy.generate.side_effect = Exception("LLM proxy error")

        answer = await dual_level_search._generate_answer("query", "context")

        assert "Unable to generate answer" in answer

    @pytest.mark.skip(reason="Mock structure needs refactoring for Sprint 56 domains/ migration")
    @pytest.mark.asyncio
    async def test_hybrid_search(self, dual_level_search, mock_neo4j_client):
        """Test hybrid search combining local and global results."""
        # Mock entity results
        entity_results = [
            {
                "id": "e1",
                "name": "Python",
                "type": "TECHNOLOGY",
                "description": "Programming language",
                "properties": {},
                "source_document": "doc1",
                "confidence": 0.95,
            }
        ]

        # Mock topic results
        topic_results = [
            {
                "topic_name": "TECHNOLOGY",
                "sample_entities": ["Python", "JavaScript"],
                "entity_ids": ["e1", "e2"],
                "entity_count": 10,
            }
        ]

        # Mock relationship results
        rel_results = []

        # Setup mock to return different results for different queries
        mock_neo4j_client.execute_read = AsyncMock(
            side_effect=[entity_results, topic_results, rel_results]
        )

        # Mock proxy answer generation
        mock_result = MagicMock()
        mock_result.content = "Hybrid search answer."
        dual_level_search.proxy.generate.return_value = mock_result

        result = await dual_level_search.hybrid_search("python programming", top_k=10)

        assert isinstance(result, GraphQueryResult)
        assert result.query == "python programming"
        assert result.mode == "hybrid"
        assert len(result.entities) >= 0
        assert len(result.topics) >= 0
        assert result.answer == "Hybrid search answer."
        assert "execution_time_ms" in result.metadata

    @pytest.mark.asyncio
    async def test_hybrid_search_split_top_k(self, dual_level_search, mock_neo4j_client):
        """Test hybrid search correctly splits top_k between local and global."""
        # Return empty results for local and global search
        # Note: relationship query won't be called if entities list is empty
        mock_neo4j_client.execute_read = AsyncMock(return_value=[])

        mock_result = MagicMock()
        mock_result.content = "Answer."
        dual_level_search.proxy.generate.return_value = mock_result

        await dual_level_search.hybrid_search("test query", top_k=10)

        # Should be called 2 times: local search, global search
        # Relationships query skipped because entities list is empty
        assert mock_neo4j_client.execute_read.call_count == 2

    def test_singleton_pattern(self):
        """Test singleton pattern for global instance."""
        instance1 = get_dual_level_search()
        instance2 = get_dual_level_search()
        assert instance1 is instance2


class TestDualLevelSearchIntegration:
    """Integration tests for dual-level search with real Neo4j."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_search(self):
        """Test search with real Neo4j and Ollama.

        NOTE: This test requires Neo4j and Ollama to be running locally.
        Skip this test if dependencies are not available.
        """
        pytest.skip("Integration test - requires Neo4j and Ollama running")

        search = DualLevelSearch()

        # Assuming some test data exists in Neo4j
        entities = await search.local_search("machine learning", top_k=5)
        assert isinstance(entities, list)

        topics = await search.global_search("technology topics", top_k=3)
        assert isinstance(topics, list)

        result = await search.hybrid_search("python programming", top_k=10)
        assert isinstance(result, GraphQueryResult)
        assert result.answer != ""


class TestSprint78EntityChunkExpansion:
    """Test Sprint 78 Feature 78.1: Entity→Chunk Expansion."""

    @pytest.fixture
    def mock_neo4j_client(self):
        """Mock Neo4j client for chunk expansion tests."""
        with patch("src.components.graph_rag.dual_level_search.Neo4jClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.execute_read = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_entity_expander(self):
        """Mock SmartEntityExpander for 3-stage expansion."""
        with patch("src.components.graph_rag.entity_expansion.SmartEntityExpander") as mock_expander_class:
            mock_instance = MagicMock()
            mock_instance.expand_entities = AsyncMock(return_value=["abortion", "reproductive rights"])
            mock_expander_class.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def dual_level_search(self, mock_neo4j_client):
        """DualLevelSearch instance with mocked dependencies."""
        with patch("src.components.graph_rag.dual_level_search.get_aegis_llm_proxy"), \
             patch("src.components.graph_rag.dual_level_search.Neo4jClient", return_value=mock_neo4j_client):
            search = DualLevelSearch(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password",
            )
            return search

    @pytest.mark.asyncio
    async def test_local_search_returns_chunks_not_descriptions(
        self, dual_level_search, mock_neo4j_client, mock_entity_expander
    ):
        """Test that local_search returns full chunk text, not entity descriptions."""
        # Mock chunk data from Neo4j (Sprint 78: MENTIONED_IN traversal)
        mock_neo4j_client.execute_read.return_value = [
            {
                "id": "chunk_001",
                "chunk_text": "The Supreme Court ruling on abortion has significant global implications for reproductive rights. Many countries look to USA jurisprudence when shaping their own policies on women's health and bodily autonomy.",
                "document_id": "amnesty_report_2023.pdf",
                "chunk_index": 5,
                "matched_entities": ["abortion", "reproductive rights", "Supreme Court"],
                "entity_count": 3,
            },
            {
                "id": "chunk_002",
                "chunk_text": "International organizations have expressed concern about the impact of restrictive abortion laws on women's health outcomes globally.",
                "document_id": "who_report_2024.pdf",
                "chunk_index": 12,
                "matched_entities": ["abortion", "women's health"],
                "entity_count": 2,
            }
        ]

        # Execute
        with patch("src.components.graph_rag.entity_expansion.SmartEntityExpander", return_value=mock_entity_expander):
            entities = await dual_level_search.local_search(
                query="What are the global implications of abortion?",
                top_k=5,
                namespaces=["amnesty_qa"]
            )

        # Verify - should return chunks as GraphEntity objects
        assert len(entities) == 2

        # Check first chunk
        assert entities[0].id == "chunk_001"
        assert "Supreme Court ruling" in entities[0].description  # Full chunk text
        assert len(entities[0].description) > 100  # Real chunk, not 100-char description
        assert entities[0].type == "CHUNK"
        assert entities[0].source_document == "amnesty_report_2023.pdf"

        # Check metadata
        assert "matched_entities" in entities[0].properties
        assert "abortion" in entities[0].properties["matched_entities"]
        assert entities[0].properties["entity_match_count"] == 3

    @pytest.mark.asyncio
    async def test_local_search_uses_mentioned_in_relationship(
        self, dual_level_search, mock_neo4j_client, mock_entity_expander
    ):
        """Test that Cypher query uses MENTIONED_IN relationship to expand to chunks."""
        mock_neo4j_client.execute_read.return_value = []

        with patch("src.components.graph_rag.entity_expansion.SmartEntityExpander", return_value=mock_entity_expander):
            await dual_level_search.local_search(
                query="Test query",
                top_k=5,
                namespaces=["test_ns"]
            )

        # Verify Cypher query structure
        call_args = mock_neo4j_client.execute_read.call_args
        cypher_query = call_args[0][0]

        # Should traverse from entities to chunks
        assert "MATCH (e:base)-[:MENTIONED_IN]->(c:chunk)" in cypher_query
        # Should return chunk properties
        assert "c.chunk_id" in cypher_query
        assert "c.text" in cypher_query
        assert "c.document_id" in cypher_query

    @pytest.mark.asyncio
    async def test_local_search_uses_smart_entity_expander(
        self, dual_level_search, mock_neo4j_client
    ):
        """Test that local_search uses SmartEntityExpander instead of manual stop words."""
        mock_neo4j_client.execute_read.return_value = []

        # Mock SmartEntityExpander
        with patch("src.components.graph_rag.entity_expansion.SmartEntityExpander") as mock_expander_class:
            mock_instance = MagicMock()
            mock_instance.expand_entities = AsyncMock(
                return_value=["abortion", "reproductive rights", "Supreme Court"]
            )
            mock_expander_class.return_value = mock_instance

            await dual_level_search.local_search(
                query="What are the global implications of abortion?",
                top_k=5,
                namespaces=["amnesty_qa"]
            )

            # Verify SmartEntityExpander was instantiated and called
            mock_expander_class.assert_called_once()
            mock_instance.expand_entities.assert_called_once()

            # Check expand_entities was called with correct parameters
            call_kwargs = mock_instance.expand_entities.call_args[1]
            assert call_kwargs["query"] == "What are the global implications of abortion?"
            assert call_kwargs["namespaces"] == ["amnesty_qa"]

    @pytest.mark.asyncio
    async def test_local_search_filters_by_namespace(
        self, dual_level_search, mock_neo4j_client, mock_entity_expander
    ):
        """Test that local_search correctly filters chunks by namespace."""
        mock_neo4j_client.execute_read.return_value = []

        with patch("src.components.graph_rag.entity_expansion.SmartEntityExpander", return_value=mock_entity_expander):
            await dual_level_search.local_search(
                query="Test query",
                top_k=5,
                namespaces=["namespace_a", "namespace_b"]
            )

        # Verify Cypher query filters by namespace
        call_args = mock_neo4j_client.execute_read.call_args
        cypher_query = call_args[0][0]
        params = call_args[0][1]

        assert "e.namespace_id IN $namespaces" in cypher_query
        assert "c.namespace_id IN $namespaces" in cypher_query
        assert params["namespaces"] == ["namespace_a", "namespace_b"]

    @pytest.mark.asyncio
    async def test_local_search_orders_by_entity_count(
        self, dual_level_search, mock_neo4j_client, mock_entity_expander
    ):
        """Test that local_search orders results by entity match count."""
        # Mock chunks with different entity counts
        mock_neo4j_client.execute_read.return_value = [
            {
                "id": "chunk_high",
                "chunk_text": "Text with many entity matches",
                "document_id": "doc1.pdf",
                "chunk_index": 1,
                "matched_entities": ["e1", "e2", "e3"],
                "entity_count": 3,
            },
            {
                "id": "chunk_low",
                "chunk_text": "Text with fewer matches",
                "document_id": "doc2.pdf",
                "chunk_index": 2,
                "matched_entities": ["e1"],
                "entity_count": 1,
            }
        ]

        with patch("src.components.graph_rag.entity_expansion.SmartEntityExpander", return_value=mock_entity_expander):
            entities = await dual_level_search.local_search(
                query="Test",
                top_k=5,
                namespaces=["test"]
            )

        # Verify ordering - higher entity count should come first
        assert entities[0].id == "chunk_high"
        assert entities[0].properties["entity_match_count"] == 3
        assert entities[1].id == "chunk_low"
        assert entities[1].properties["entity_match_count"] == 1

    @pytest.mark.asyncio
    async def test_local_search_respects_top_k(
        self, dual_level_search, mock_neo4j_client, mock_entity_expander
    ):
        """Test that local_search respects top_k limit."""
        # Mock more chunks than top_k
        mock_neo4j_client.execute_read.return_value = [
            {
                "id": f"chunk_{i}",
                "chunk_text": f"Chunk text {i}",
                "document_id": f"doc{i}.pdf",
                "chunk_index": i,
                "matched_entities": ["entity"],
                "entity_count": 1,
            }
            for i in range(10)
        ]

        with patch("src.components.graph_rag.entity_expansion.SmartEntityExpander", return_value=mock_entity_expander):
            entities = await dual_level_search.local_search(
                query="Test",
                top_k=3,
                namespaces=["test"]
            )

        # Verify Cypher LIMIT was applied
        call_args = mock_neo4j_client.execute_read.call_args
        params = call_args[0][1]
        assert params["top_k"] == 3
