"""Sprint 14 Feature 14.1 E2E Tests - LightRAG Graph-Based Provenance.

End-to-end tests validating the complete Feature 14.1 implementation:
- Three-Phase Pipeline per-chunk extraction
- LightRAG custom KG integration
- Neo4j :chunk nodes and MENTIONED_IN relationships
- Provenance queries for entity traceability
"""

import asyncio
import pytest
from neo4j import AsyncGraphDatabase

from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper
from src.core.config import settings

pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]


@pytest.fixture
async def lightrag_wrapper():
    """Create LightRAG wrapper for testing."""
    wrapper = LightRAGWrapper(
        llm_model=settings.lightrag_llm_model,
        embedding_model=settings.lightrag_embedding_model,
        working_dir=str(settings.lightrag_working_dir),
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password.get_secret_value(),
    )
    await wrapper._ensure_initialized()
    yield wrapper
    # Cleanup handled by cleanup_databases fixture


@pytest.fixture
async def cleanup_databases():
    """Clean up Neo4j database before and after tests."""
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value())
    )

    async def clean():
        async with driver.session() as session:
            # Delete all :chunk nodes and MENTIONED_IN relationships
            await session.run("MATCH (c:chunk) DETACH DELETE c")
            # Delete all :base entities and relationships
            await session.run("MATCH (e:base) DETACH DELETE e")

    # Clean before test
    await clean()

    yield

    # Clean after test
    await clean()
    await driver.close()


# ============================================================================
# Test 1: Full Pipeline E2E - Single Document
# ============================================================================


async def test_full_pipeline_single_document_e2e(lightrag_wrapper, cleanup_databases):
    """Test complete Feature 14.1 pipeline with a single document.

    Validates:
    - Document insertion using insert_documents_optimized()
    - Three-Phase extraction per-chunk
    - LightRAG custom KG insertion
    - Neo4j :chunk nodes created
    - MENTIONED_IN relationships created
    - Provenance query returns correct results
    """
    # Arrange
    test_doc = {
        "id": "e2e_test_001",
        "text": """
        Klaus Pommer developed AEGIS RAG, a hybrid retrieval system.
        AEGIS RAG integrates Ollama for local LLM inference.
        The system uses LightRAG for graph-based knowledge representation.
        Neo4j stores the knowledge graph with entity relationships.
        """
    }

    # Act - Insert document
    result = await lightrag_wrapper.insert_documents_optimized([test_doc])

    # Assert - Insertion successful
    assert result["success"] == 1, "Document insertion should succeed"
    assert result["stats"]["total_chunks"] > 0, "Should create at least one chunk"
    assert result["stats"]["total_entities"] > 0, "Should extract entities"
    assert result["stats"]["total_relations"] > 0, "Should extract relations"
    assert result["stats"]["total_mentioned_in"] > 0, "Should create MENTIONED_IN relationships"

    # Verify Neo4j schema
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value())
    )

    async with driver.session() as session:
        # Check :chunk nodes
        chunk_result = await session.run(
            "MATCH (c:chunk {document_id: $doc_id}) RETURN count(c) as count",
            doc_id="e2e_test_001"
        )
        chunk_record = await chunk_result.single()
        assert chunk_record["count"] > 0, "Should have :chunk nodes"

        # Check :base entities
        entity_result = await session.run(
            "MATCH (e:base) RETURN count(e) as count"
        )
        entity_record = await entity_result.single()
        assert entity_record["count"] >= 4, "Should have at least 4 entities (Klaus Pommer, AEGIS RAG, Ollama, LightRAG, Neo4j)"

        # Check MENTIONED_IN relationships
        mention_result = await session.run(
            """
            MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk {document_id: $doc_id})
            RETURN count(r) as count
            """,
            doc_id="e2e_test_001"
        )
        mention_record = await mention_result.single()
        assert mention_record["count"] > 0, "Should have MENTIONED_IN relationships"

        # Test provenance query: Find chunks mentioning "AEGIS RAG"
        provenance_result = await session.run(
            """
            MATCH (e:base {entity_id: $entity_id})-[:MENTIONED_IN]->(c:chunk)
            RETURN c.text as chunk_text,
                   c.chunk_index as chunk_index,
                   c.tokens as tokens,
                   c.document_id as document_id
            ORDER BY c.chunk_index
            """,
            entity_id="AEGIS RAG"
        )

        provenance_records = await provenance_result.fetch(10)
        assert len(provenance_records) > 0, "Should find chunks mentioning 'AEGIS RAG'"

        # Verify chunk text contains the entity
        for record in provenance_records:
            assert "AEGIS RAG" in record["chunk_text"] or "AEGIS" in record["chunk_text"], \
                "Chunk text should contain 'AEGIS RAG'"

    await driver.close()


# ============================================================================
# Test 2: Batch Document Processing E2E
# ============================================================================


async def test_batch_document_processing_e2e(lightrag_wrapper, cleanup_databases):
    """Test Feature 14.1 with multiple documents processed in batch.

    Validates:
    - Batch document insertion
    - Correct chunk_id assignment per document
    - No cross-document entity confusion
    - Provenance links to correct document
    """
    # Arrange
    test_docs = [
        {
            "id": "batch_001",
            "text": "Alice works at TechCorp. TechCorp develops AI systems."
        },
        {
            "id": "batch_002",
            "text": "Bob works at DataCo. DataCo specializes in data analytics."
        },
        {
            "id": "batch_003",
            "text": "Alice and Bob collaborate on AI analytics projects."
        }
    ]

    # Act
    result = await lightrag_wrapper.insert_documents_optimized(test_docs)

    # Assert
    assert result["success"] == 3, "All 3 documents should be inserted successfully"
    assert result["stats"]["total_chunks"] >= 3, "Should have at least 3 chunks (1 per doc)"
    assert result["stats"]["total_entities"] >= 4, "Should extract Alice, Bob, TechCorp, DataCo"

    # Verify provenance for each document
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value())
    )

    async with driver.session() as session:
        # Check Alice is linked to batch_001 and batch_003
        alice_result = await session.run(
            """
            MATCH (e:base {entity_id: $entity_id})-[:MENTIONED_IN]->(c:chunk)
            RETURN c.document_id as doc_id
            ORDER BY c.document_id
            """,
            entity_id="Alice"
        )
        alice_records = await alice_result.fetch(10)
        alice_docs = [r["doc_id"] for r in alice_records]

        assert "batch_001" in alice_docs, "Alice should be in batch_001"
        assert "batch_003" in alice_docs, "Alice should be in batch_003"
        assert "batch_002" not in alice_docs, "Alice should NOT be in batch_002"

        # Check Bob is linked to batch_002 and batch_003
        bob_result = await session.run(
            """
            MATCH (e:base {entity_id: $entity_id})-[:MENTIONED_IN]->(c:chunk)
            RETURN c.document_id as doc_id
            ORDER BY c.document_id
            """,
            entity_id="Bob"
        )
        bob_records = await bob_result.fetch(10)
        bob_docs = [r["doc_id"] for r in bob_records]

        assert "batch_002" in bob_docs, "Bob should be in batch_002"
        assert "batch_003" in bob_docs, "Bob should be in batch_003"
        assert "batch_001" not in bob_docs, "Bob should NOT be in batch_001"

    await driver.close()


# ============================================================================
# Test 3: Chunking and Provenance Accuracy E2E
# ============================================================================


async def test_chunking_and_provenance_accuracy_e2e(lightrag_wrapper, cleanup_databases):
    """Test Feature 14.1 chunking produces accurate provenance.

    Validates:
    - Chunks have correct token boundaries
    - Entities linked to correct chunk (not adjacent chunks)
    - Chunk text contains entities it claims to mention
    """
    # Arrange - Long document that will be split into multiple chunks
    test_doc = {
        "id": "chunking_test",
        "text": " ".join([f"Sentence {i} mentions Entity{i % 3}." for i in range(100)])
    }

    # Act
    result = await lightrag_wrapper.insert_documents_optimized([test_doc])

    # Assert
    assert result["success"] == 1
    assert result["stats"]["total_chunks"] > 1, "Long document should be split into multiple chunks"

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value())
    )

    async with driver.session() as session:
        # Verify all MENTIONED_IN relationships point to correct chunks
        verify_result = await session.run(
            """
            MATCH (e:base)-[:MENTIONED_IN]->(c:chunk)
            RETURN e.entity_id as entity,
                   c.text as chunk_text,
                   c.chunk_index as chunk_index
            """
        )

        verify_records = await verify_result.fetch(100)

        for record in verify_records:
            entity_id = record["entity"]
            chunk_text = record["chunk_text"]

            # Verify entity is actually in the chunk text
            # (Case-insensitive check for robustness)
            assert entity_id.lower() in chunk_text.lower() or \
                   any(word.lower() in chunk_text.lower() for word in entity_id.split()), \
                   f"Entity '{entity_id}' should be mentioned in chunk: {chunk_text[:100]}"

    await driver.close()


# ============================================================================
# Test 4: Provenance Query Performance E2E
# ============================================================================


async def test_provenance_query_performance_e2e(lightrag_wrapper, cleanup_databases):
    """Test Feature 14.1 provenance queries perform efficiently.

    Validates:
    - Provenance queries complete in <1s
    - Results sorted by chunk_index
    - Full chunk text + metadata returned
    """
    # Arrange
    test_doc = {
        "id": "performance_test",
        "text": """
        Machine Learning is a subset of Artificial Intelligence.
        Artificial Intelligence enables computers to learn from data.
        Deep Learning is a type of Machine Learning using neural networks.
        Neural networks are inspired by biological neural networks.
        """ * 10  # Repeat to create multiple chunks
    }

    await lightrag_wrapper.insert_documents_optimized([test_doc])

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value())
    )

    async with driver.session() as session:
        # Act - Measure query performance
        import time
        start = time.time()

        result = await session.run(
            """
            MATCH (e:base)-[:MENTIONED_IN]->(c:chunk {document_id: $doc_id})
            RETURN e.entity_id as entity,
                   c.text as chunk_text,
                   c.chunk_index as chunk_index,
                   c.tokens as tokens,
                   c.start_token as start_token,
                   c.end_token as end_token
            ORDER BY c.chunk_index, e.entity_id
            """,
            doc_id="performance_test"
        )

        records = await result.fetch(100)
        elapsed = time.time() - start

        # Assert
        assert len(records) > 0, "Should find provenance results"
        assert elapsed < 1.0, f"Provenance query should complete in <1s (took {elapsed:.2f}s)"

        # Verify results are sorted
        chunk_indices = [r["chunk_index"] for r in records]
        assert chunk_indices == sorted(chunk_indices), "Results should be sorted by chunk_index"

        # Verify all required metadata present
        for record in records:
            assert record["entity"] is not None
            assert record["chunk_text"] is not None
            assert record["chunk_index"] is not None
            assert record["tokens"] is not None
            assert record["start_token"] is not None
            assert record["end_token"] is not None

    await driver.close()


# ============================================================================
# Test 5: Integration with LightRAG Query E2E
# ============================================================================


async def test_integration_with_lightrag_query_e2e(lightrag_wrapper, cleanup_databases):
    """Test Feature 14.1 works alongside normal LightRAG queries.

    Validates:
    - insert_documents_optimized() doesn't break LightRAG query
    - Both provenance and regular queries work
    - No data corruption
    """
    # Arrange
    test_doc = {
        "id": "integration_test",
        "text": """
        LangGraph is a framework for building stateful multi-agent systems.
        It provides tools for orchestrating complex agentic workflows.
        """
    }

    await lightrag_wrapper.insert_documents_optimized([test_doc])

    # Act - Regular LightRAG query
    query_result = await lightrag_wrapper.query_graph(
        query="What is LangGraph?",
        mode="local"
    )

    # Assert
    assert query_result.answer is not None, "LightRAG query should return an answer"
    assert "LangGraph" in query_result.answer or "langgraph" in query_result.answer.lower(), \
        "Answer should mention LangGraph"

    # Verify provenance still works
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value())
    )

    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (e:base {entity_id: $entity_id})-[:MENTIONED_IN]->(c:chunk)
            RETURN count(c) as count
            """,
            entity_id="LangGraph"
        )
        record = await result.single()
        assert record["count"] > 0, "Provenance should still work after query"

    await driver.close()
