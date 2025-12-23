"""Integration tests for GraphRAG Multi-Hop Retriever.

Sprint 38 Feature 38.4: E2E tests with real Neo4j and Qdrant (if available).

These tests verify:
- Full GraphRAG retrieval flow with real databases
- Multi-hop graph traversal
- Entity extraction and expansion
- Answer generation quality

Note: These tests require Neo4j and Qdrant to be running.
They will be skipped if the services are unavailable.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.neo4j_client import Neo4jClient
from src.components.retrieval.graph_rag_retriever import (
    Document,
    GraphContext,
    GraphRAGRetriever,
    get_graph_rag_retriever,
)
from src.core.exceptions import DatabaseConnectionError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def check_neo4j_available():
    """Check if Neo4j is available and skip test if not."""
    import socket

    try:
        # Try to connect to Neo4j default port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", 7687))
        sock.close()
        if result != 0:
            pytest.skip("Neo4j not available on localhost:7687")
    except Exception as e:
        pytest.skip(f"Neo4j connection check failed: {e}")


@pytest.fixture
def check_qdrant_available():
    """Check if Qdrant is available and skip test if not."""
    import socket

    try:
        # Try to connect to Qdrant default port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", 6333))
        sock.close()
        if result != 0:
            pytest.skip("Qdrant not available on localhost:6333")
    except Exception as e:
        pytest.skip(f"Qdrant connection check failed: {e}")


@pytest.fixture
async def neo4j_with_test_data(check_neo4j_available):
    """Create Neo4j client and populate with test data.

    Creates a simple knowledge graph:
    - Alice (Person) --[WORKS_AT]--> Acme Corp (Organization)
    - Bob (Person) --[WORKS_AT]--> Acme Corp (Organization)
    - Acme Corp --[DEVELOPS]--> RAG System (Product)
    """
    client = Neo4jClient()

    try:
        # Check health
        await client.health_check()
    except DatabaseConnectionError:
        pytest.skip("Neo4j health check failed")

    # Clear previous test data
    await client.execute_write(
        query="MATCH (n) WHERE n.test_data = true DETACH DELETE n",
    )

    # Create test entities
    await client.execute_write(
        query="""
        CREATE (alice:base:Person {name: 'Alice', type: 'Person', test_data: true})
        CREATE (bob:base:Person {name: 'Bob', type: 'Person', test_data: true})
        CREATE (acme:base:Organization {name: 'Acme Corp', type: 'Organization', test_data: true})
        CREATE (rag:base:Product {name: 'RAG System', type: 'Product', test_data: true})
        CREATE (alice)-[:WORKS_AT]->(acme)
        CREATE (bob)-[:WORKS_AT]->(acme)
        CREATE (acme)-[:DEVELOPS]->(rag)
        """,
    )

    yield client

    # Cleanup
    await client.execute_write(
        query="MATCH (n) WHERE n.test_data = true DETACH DELETE n",
    )
    await client.close()


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_graph_expand_with_real_neo4j(neo4j_with_test_data):
    """Test graph expansion with real Neo4j database."""
    retriever = GraphRAGRetriever(neo4j_client=neo4j_with_test_data)
    context = GraphContext()

    # Expand from Alice
    await retriever._graph_expand(
        context=context,
        entity_names=["Alice"],
        max_hops=2,
    )

    # Assertions
    assert len(context.entities) > 0
    # Should find Acme Corp (1-hop) and possibly RAG System (2-hop)
    entity_names = {e.name for e in context.entities}
    assert "Acme Corp" in entity_names or "RAG System" in entity_names

    # Should have at least one path
    assert len(context.paths) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_extract_entities_from_results_with_real_neo4j(neo4j_with_test_data):
    """Test entity extraction with real Neo4j database."""
    retriever = GraphRAGRetriever(neo4j_client=neo4j_with_test_data)

    # Create documents mentioning test entities
    documents = [
        Document(
            id="doc1",
            text="Alice works at Acme Corp as a software engineer.",
            score=0.95,
            source="test_doc.txt",
        ),
    ]

    entities = await retriever._extract_entities_from_results(documents)

    # Should extract Alice and/or Acme Corp
    assert len(entities) > 0
    entity_names = {e.name for e in entities}
    assert "Alice" in entity_names or "Acme Corp" in entity_names


@pytest.mark.asyncio
@pytest.mark.integration
async def test_simple_retrieve_with_mocked_vector_search(neo4j_with_test_data):
    """Test simple retrieval flow with real Neo4j and mocked vector search."""
    # Mock hybrid search
    mock_hybrid_search = MagicMock()
    mock_hybrid_search.hybrid_search = AsyncMock(
        return_value={
            "query": "Who works at Acme Corp?",
            "results": [
                {
                    "id": "doc1",
                    "text": "Alice works at Acme Corp as a software engineer.",
                    "score": 0.95,
                    "rerank_score": 0.98,
                    "source": "test_doc.txt",
                },
            ],
            "total_results": 1,
        }
    )

    retriever = GraphRAGRetriever(
        neo4j_client=neo4j_with_test_data,
        hybrid_search=mock_hybrid_search,
    )

    # Execute simple retrieval
    context = await retriever._simple_retrieve(
        query="Who works at Acme Corp?",
        top_k=5,
        max_hops=1,
        use_graph_expansion=True,
    )

    # Assertions
    assert len(context.documents) == 1
    assert context.documents[0].id == "doc1"

    # Should extract entities (Alice and/or Acme Corp)
    assert len(context.entities) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_retrieve_flow_with_mocks(neo4j_with_test_data):
    """Test full retrieve flow with real Neo4j, mocked vector search and LLM."""
    # Mock query decomposer
    mock_decomposer = MagicMock()
    mock_decomposer.decompose = AsyncMock(
        return_value=MagicMock(
            classification=MagicMock(
                query_type="SIMPLE",
                confidence=0.95,
            ),
            sub_queries=[MagicMock(query="Who works at Acme Corp?", index=0, depends_on=[])],
            execution_strategy="direct",
        )
    )

    # Mock hybrid search
    mock_hybrid_search = MagicMock()
    mock_hybrid_search.hybrid_search = AsyncMock(
        return_value={
            "query": "Who works at Acme Corp?",
            "results": [
                {
                    "id": "doc1",
                    "text": "Alice and Bob work at Acme Corp.",
                    "score": 0.95,
                    "rerank_score": 0.98,
                    "source": "test_doc.txt",
                },
            ],
            "total_results": 1,
        }
    )

    retriever = GraphRAGRetriever(
        query_decomposer=mock_decomposer,
        hybrid_search=mock_hybrid_search,
        neo4j_client=neo4j_with_test_data,
    )

    # Mock LLM answer generation
    with patch("src.components.retrieval.graph_rag_retriever.get_aegis_llm_proxy") as mock_proxy:
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            return_value=MagicMock(
                content="Alice and Bob work at Acme Corp.",
                provider="local_ollama",
                tokens_used=50,
            )
        )
        mock_proxy.return_value = mock_llm

        # Execute full retrieval
        result = await retriever.retrieve(
            query="Who works at Acme Corp?",
            max_hops=1,
            top_k=5,
        )

    # Assertions
    assert result.query == "Who works at Acme Corp?"
    assert len(result.context.documents) == 1
    assert "Alice" in result.answer or "Bob" in result.answer


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires both Neo4j and Qdrant with real data")
async def test_end_to_end_with_real_databases():
    """Full E2E test with real Neo4j, Qdrant, and LLM.

    This test is skipped by default as it requires:
    - Neo4j running with real knowledge graph
    - Qdrant running with ingested documents
    - Working LLM (Ollama or cloud provider)

    To run this test:
    1. Ensure Neo4j and Qdrant are running
    2. Ingest test documents
    3. Run with: pytest -m integration -k test_end_to_end_with_real_databases
    """
    retriever = get_graph_rag_retriever()

    # Execute query
    result = await retriever.retrieve(
        query="What is RAG and how does it work?",
        max_hops=2,
        top_k=5,
    )

    # Basic assertions
    assert result.query == "What is RAG and how does it work?"
    assert len(result.answer) > 0
    assert len(result.context.documents) > 0


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_graph_expand_with_no_entities(neo4j_with_test_data):
    """Test graph expansion with non-existent entities."""
    retriever = GraphRAGRetriever(neo4j_client=neo4j_with_test_data)
    context = GraphContext()

    # Expand from non-existent entity
    await retriever._graph_expand(
        context=context,
        entity_names=["NonExistentEntity"],
        max_hops=2,
    )

    # Should not find any entities
    assert len(context.entities) == 0
    assert len(context.paths) == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_graph_expand_with_zero_hops(neo4j_with_test_data):
    """Test graph expansion with max_hops=0."""
    retriever = GraphRAGRetriever(neo4j_client=neo4j_with_test_data)
    context = GraphContext()

    # Should not expand (max_hops=0)
    await retriever._graph_expand(
        context=context,
        entity_names=["Alice"],
        max_hops=0,
    )

    # Should not find any entities (expansion skipped)
    assert len(context.entities) == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_extract_entities_empty_documents(neo4j_with_test_data):
    """Test entity extraction with empty document list."""
    retriever = GraphRAGRetriever(neo4j_client=neo4j_with_test_data)

    entities = await retriever._extract_entities_from_results([])

    assert len(entities) == 0
