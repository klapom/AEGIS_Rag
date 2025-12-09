"""Unit tests for GraphRAG Multi-Hop Retriever.

Sprint 38 Feature 38.4: Test GraphContext, GraphRAGRetriever routing and retrieval logic.

These tests verify:
- GraphContext deduplication logic
- GraphContext.to_prompt_context() formatting
- Query routing (SIMPLE/COMPOUND/MULTI_HOP)
- Mock-based retrieval flows
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.retrieval.graph_rag_retriever import (
    Document,
    Entity,
    GraphContext,
    GraphPath,
    GraphRAGResult,
    GraphRAGRetriever,
    Relationship,
    get_graph_rag_retriever,
)
from src.components.retrieval.query_decomposition import (
    DecompositionResult,
    QueryClassification,
    QueryType,
    SubQuery,
)

# ============================================================================
# Test GraphContext
# ============================================================================


class TestGraphContext:
    """Test GraphContext data accumulation and deduplication."""

    def test_add_entity_deduplication(self):
        """Test entity deduplication by name (case-insensitive)."""
        context = GraphContext()

        entity1 = Entity(name="Alice", type="Person")
        entity2 = Entity(name="alice", type="Person")  # Same name, different case
        entity3 = Entity(name="Bob", type="Person")

        context.add_entity(entity1)
        context.add_entity(entity2)  # Should be deduplicated
        context.add_entity(entity3)

        assert len(context.entities) == 2
        assert {e.name.lower() for e in context.entities} == {"alice", "bob"}

    def test_add_relationship_deduplication(self):
        """Test relationship deduplication by (source, target, type)."""
        context = GraphContext()

        rel1 = Relationship(source="Alice", target="Bob", type="KNOWS")
        rel2 = Relationship(source="alice", target="bob", type="knows")  # Same, different case
        rel3 = Relationship(source="Alice", target="Charlie", type="KNOWS")

        context.add_relationship(rel1)
        context.add_relationship(rel2)  # Should be deduplicated
        context.add_relationship(rel3)

        assert len(context.relationships) == 2

    def test_add_path_deduplication(self):
        """Test path deduplication by node sequence."""
        context = GraphContext()

        path1 = GraphPath(nodes=["A", "B", "C"], relationships=["R1", "R2"], length=2)
        path2 = GraphPath(nodes=["A", "B", "C"], relationships=["R1", "R2"], length=2)  # Duplicate
        path3 = GraphPath(nodes=["A", "D", "C"], relationships=["R3", "R4"], length=2)

        context.add_path(path1)
        context.add_path(path2)  # Should be deduplicated
        context.add_path(path3)

        assert len(context.paths) == 2

    def test_add_document_deduplication(self):
        """Test document deduplication by ID."""
        context = GraphContext()

        doc1 = Document(id="doc1", text="Text 1", score=0.9)
        doc2 = Document(id="doc1", text="Text 1 updated", score=0.95)  # Same ID
        doc3 = Document(id="doc2", text="Text 2", score=0.8)

        context.add_document(doc1)
        context.add_document(doc2)  # Should be deduplicated
        context.add_document(doc3)

        assert len(context.documents) == 2
        assert {d.id for d in context.documents} == {"doc1", "doc2"}

    def test_to_prompt_context_empty(self):
        """Test prompt context generation with empty context."""
        context = GraphContext()
        prompt_ctx = context.to_prompt_context()

        assert prompt_ctx == ""  # Empty context

    def test_to_prompt_context_with_data(self):
        """Test prompt context generation with entities, relationships, paths, documents."""
        context = GraphContext()

        # Add entities
        context.add_entity(Entity(name="Alice", type="Person", properties={"age": 30}))
        context.add_entity(Entity(name="Acme Corp", type="Organization"))

        # Add relationships
        context.add_relationship(Relationship(source="Alice", target="Acme Corp", type="WORKS_AT"))

        # Add paths
        context.add_path(GraphPath(nodes=["Alice", "Acme Corp"], relationships=["WORKS_AT"], length=1))

        # Add documents
        context.add_document(Document(
            id="doc1",
            text="Alice works at Acme Corp as a software engineer.",
            score=0.95,
            source="company_db.txt"
        ))

        prompt_ctx = context.to_prompt_context()

        # Verify sections are present
        assert "## Entities" in prompt_ctx
        assert "Alice (Person)" in prompt_ctx
        assert "Acme Corp (Organization)" in prompt_ctx
        assert "## Relationships" in prompt_ctx
        assert "Alice --[WORKS_AT]--> Acme Corp" in prompt_ctx
        assert "## Graph Paths" in prompt_ctx
        assert "## Retrieved Documents" in prompt_ctx
        assert "company_db.txt" in prompt_ctx
        assert "score: 0.950" in prompt_ctx


# ============================================================================
# Test GraphRAGRetriever
# ============================================================================


class TestGraphRAGRetriever:
    """Test GraphRAGRetriever routing and retrieval logic."""

    @pytest.fixture
    def mock_query_decomposer(self):
        """Mock QueryDecomposer."""
        decomposer = MagicMock()
        return decomposer

    @pytest.fixture
    def mock_hybrid_search(self):
        """Mock HybridSearch."""
        search = MagicMock()
        return search

    @pytest.fixture
    def mock_neo4j_client(self):
        """Mock Neo4jClient."""
        client = MagicMock()
        return client

    @pytest.fixture
    def retriever(self, mock_query_decomposer, mock_hybrid_search, mock_neo4j_client):
        """Create GraphRAGRetriever with mocked dependencies."""
        return GraphRAGRetriever(
            query_decomposer=mock_query_decomposer,
            hybrid_search=mock_hybrid_search,
            neo4j_client=mock_neo4j_client,
        )

    @pytest.mark.asyncio
    async def test_simple_query_routing(self, retriever, mock_query_decomposer, mock_hybrid_search):
        """Test SIMPLE query routing: vector search only."""
        # Mock decomposition
        mock_query_decomposer.decompose = AsyncMock(return_value=DecompositionResult(
            original_query="What is RAG?",
            classification=QueryClassification(
                query_type=QueryType.SIMPLE,
                confidence=0.95,
                reasoning="Simple question",
            ),
            sub_queries=[SubQuery(query="What is RAG?", index=0, depends_on=[])],
            execution_strategy="direct",
        ))

        # Mock vector search
        mock_hybrid_search.hybrid_search = AsyncMock(return_value={
            "query": "What is RAG?",
            "results": [
                {
                    "id": "doc1",
                    "text": "RAG stands for Retrieval Augmented Generation.",
                    "score": 0.95,
                    "rerank_score": 0.98,
                    "source": "rag_paper.pdf",
                }
            ],
            "total_results": 1,
        })

        # Mock Neo4j entity extraction (no entities found)
        retriever.neo4j_client.execute_query = AsyncMock(return_value=[])

        # Mock LLM answer generation - patch the retriever's llm_proxy directly
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=MagicMock(
            content="RAG stands for Retrieval Augmented Generation.",
            provider="local_ollama",
            tokens_used=50,
        ))
        retriever.llm_proxy = mock_llm

        # Execute retrieval
        result = await retriever.retrieve(query="What is RAG?", max_hops=2)

        # Assertions
        assert isinstance(result, GraphRAGResult)
        assert result.query == "What is RAG?"
        assert result.query_type == QueryType.SIMPLE
        assert len(result.context.documents) == 1
        assert result.context.documents[0].id == "doc1"
        assert "RAG" in result.answer

    @pytest.mark.asyncio
    async def test_compound_query_routing(self, retriever, mock_query_decomposer, mock_hybrid_search):
        """Test COMPOUND query routing: parallel sub-query execution."""
        # Mock decomposition
        mock_query_decomposer.decompose = AsyncMock(return_value=DecompositionResult(
            original_query="What is RAG and BM25?",
            classification=QueryClassification(
                query_type=QueryType.COMPOUND,
                confidence=0.90,
                reasoning="Multiple independent questions",
            ),
            sub_queries=[
                SubQuery(query="What is RAG?", index=0, depends_on=[]),
                SubQuery(query="What is BM25?", index=1, depends_on=[]),
            ],
            execution_strategy="parallel",
        ))

        # Mock vector search (will be called twice)
        mock_hybrid_search.hybrid_search = AsyncMock(side_effect=[
            {
                "query": "What is RAG?",
                "results": [
                    {
                        "id": "doc1",
                        "text": "RAG stands for Retrieval Augmented Generation.",
                        "score": 0.95,
                        "rerank_score": 0.98,
                        "source": "rag_paper.pdf",
                    }
                ],
                "total_results": 1,
            },
            {
                "query": "What is BM25?",
                "results": [
                    {
                        "id": "doc2",
                        "text": "BM25 is a keyword-based ranking function.",
                        "score": 0.90,
                        "rerank_score": 0.92,
                        "source": "bm25_paper.pdf",
                    }
                ],
                "total_results": 1,
            },
        ])

        # Mock Neo4j entity extraction
        retriever.neo4j_client.execute_query = AsyncMock(return_value=[])

        # Mock LLM answer generation
        with patch("src.components.retrieval.graph_rag_retriever.get_aegis_llm_proxy") as mock_proxy:
            mock_llm = MagicMock()
            mock_llm.generate = AsyncMock(return_value=MagicMock(
                content="RAG is Retrieval Augmented Generation. BM25 is a keyword-based ranking function.",
                provider="local_ollama",
                tokens_used=75,
            ))
            mock_proxy.return_value = mock_llm

            # Execute retrieval
            result = await retriever.retrieve(query="What is RAG and BM25?", max_hops=2)

        # Assertions
        assert result.query_type == QueryType.COMPOUND
        assert len(result.sub_queries) == 2
        assert len(result.context.documents) == 2
        assert {d.id for d in result.context.documents} == {"doc1", "doc2"}

    @pytest.mark.asyncio
    async def test_multi_hop_query_routing(self, retriever, mock_query_decomposer, mock_hybrid_search):
        """Test MULTI_HOP query routing: sequential reasoning with context injection."""
        # Mock decomposition
        mock_query_decomposer.decompose = AsyncMock(return_value=DecompositionResult(
            original_query="Who founded the company that developed RAG?",
            classification=QueryClassification(
                query_type=QueryType.MULTI_HOP,
                confidence=0.85,
                reasoning="Multi-hop reasoning required",
            ),
            sub_queries=[
                SubQuery(query="Which company developed RAG?", index=0, depends_on=[]),
                SubQuery(query="Who founded that company?", index=1, depends_on=[0]),
            ],
            execution_strategy="sequential",
        ))

        # Mock vector search (sequential calls)
        mock_hybrid_search.hybrid_search = AsyncMock(side_effect=[
            {
                "query": "Which company developed RAG?",
                "results": [
                    {
                        "id": "doc1",
                        "text": "RAG was developed by Facebook AI Research (FAIR).",
                        "score": 0.95,
                        "rerank_score": 0.98,
                        "source": "rag_history.pdf",
                    }
                ],
                "total_results": 1,
            },
            {
                "query": "Who founded that company?",
                "results": [
                    {
                        "id": "doc2",
                        "text": "Facebook was founded by Mark Zuckerberg in 2004.",
                        "score": 0.92,
                        "rerank_score": 0.95,
                        "source": "facebook_history.pdf",
                    }
                ],
                "total_results": 1,
            },
        ])

        # Mock Neo4j - entity extraction returns entity info, graph expansion returns path data
        entity_extraction_response = [
            {"name": "Facebook", "type": "Organization", "properties": {}},
        ]
        graph_expansion_response = [
            {
                "name": "Mark Zuckerberg",
                "type": "Person",
                "hops": 1,
                "rel_types": ["FOUNDED"],
                "path_nodes": ["Facebook", "Mark Zuckerberg"],
            },
        ]
        # Use side_effect to return different data for different calls
        retriever.neo4j_client.execute_query = AsyncMock(side_effect=[
            entity_extraction_response,  # First call: entity extraction
            graph_expansion_response,    # Second call: graph expansion
            entity_extraction_response,  # Third call: entity extraction for second subquery
            graph_expansion_response,    # Fourth call: graph expansion
        ])

        # Mock LLM answer generation - patch retriever.llm_proxy directly
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=MagicMock(
            content="Facebook (now Meta) developed RAG through FAIR. Facebook was founded by Mark Zuckerberg.",
            provider="local_ollama",
            tokens_used=100,
        ))
        retriever.llm_proxy = mock_llm

        # Execute retrieval
        result = await retriever.retrieve(query="Who founded the company that developed RAG?", max_hops=2)

        # Assertions
        assert result.query_type == QueryType.MULTI_HOP
        assert len(result.sub_queries) == 2
        assert len(result.context.documents) == 2
        assert result.sub_queries[1].depends_on == [0]  # Second query depends on first

    @pytest.mark.asyncio
    async def test_extract_entities_from_results(self, retriever):
        """Test entity extraction from documents using Neo4j lookup."""
        documents = [
            Document(
                id="doc1",
                text="Alice works at Acme Corp as a software engineer.",
                score=0.95,
                source="company_db.txt",
            ),
        ]

        # Mock Neo4j response
        retriever.neo4j_client.execute_query = AsyncMock(return_value=[
            {"name": "Alice", "type": "Person", "properties": {"role": "Engineer"}},
            {"name": "Acme Corp", "type": "Organization", "properties": {"industry": "Tech"}},
        ])

        entities = await retriever._extract_entities_from_results(documents)

        assert len(entities) == 2
        assert {e.name for e in entities} == {"Alice", "Acme Corp"}
        assert {e.type for e in entities} == {"Person", "Organization"}

    @pytest.mark.asyncio
    async def test_graph_expand(self, retriever):
        """Test graph expansion with multi-hop traversal."""
        context = GraphContext()
        entity_names = ["Alice"]

        # Mock Neo4j multi-hop query
        retriever.neo4j_client.execute_query = AsyncMock(return_value=[
            {
                "name": "Acme Corp",
                "type": "Organization",
                "hops": 1,
                "rel_types": ["WORKS_AT"],
                "path_nodes": ["Alice", "Acme Corp"],
            },
            {
                "name": "Bob",
                "type": "Person",
                "hops": 2,
                "rel_types": ["WORKS_AT", "MANAGES"],
                "path_nodes": ["Alice", "Acme Corp", "Bob"],
            },
        ])

        await retriever._graph_expand(context=context, entity_names=entity_names, max_hops=2)

        # Assertions
        assert len(context.entities) == 2  # Acme Corp, Bob
        # Relationships are deduplicated: Alice->Acme appears in both paths, so only counted once
        # Total: Alice->Acme (from 1st path) + Acme->Bob (from 2nd path) = 2 unique relationships
        assert len(context.relationships) == 2
        assert len(context.paths) == 2  # 1-hop and 2-hop paths

    @pytest.mark.asyncio
    async def test_generate_answer(self, retriever):
        """Test answer generation from context."""
        context = GraphContext()
        context.add_entity(Entity(name="Alice", type="Person"))
        context.add_document(Document(
            id="doc1",
            text="Alice is a software engineer.",
            score=0.95,
            source="hr_db.txt",
        ))

        # Mock LLM answer generation - patch retriever.llm_proxy directly
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=MagicMock(
            content="Alice is a software engineer.",
            provider="local_ollama",
            tokens_used=50,
        ))
        retriever.llm_proxy = mock_llm

        answer = await retriever._generate_answer(query="What is Alice's job?", context=context)

        assert "Alice" in answer
        assert "engineer" in answer.lower()


# ============================================================================
# Test Singleton
# ============================================================================


def test_get_graph_rag_retriever_singleton():
    """Test singleton pattern for get_graph_rag_retriever()."""
    retriever1 = get_graph_rag_retriever()
    retriever2 = get_graph_rag_retriever()

    assert retriever1 is retriever2  # Same instance
