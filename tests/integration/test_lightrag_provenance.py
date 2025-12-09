"""Integration tests for LightRAG Three-Phase Pipeline with Provenance.

Sprint 14 Feature 14.1 - Phase 8: Testing & Validation

Tests the new insert_documents_optimized() method that provides:
- Per-chunk extraction with Three-Phase Pipeline
- Graph-based provenance tracking (:chunk nodes + MENTIONED_IN relationships)
- LightRAG compatibility (embeddings + query)

Note: These tests require real Ollama/LLM and Neo4j, skipped in CI.
Run locally with: pytest tests/integration/test_lightrag_provenance.py -v
"""

import pytest

# Mark all tests in this module as requiring real LLM
pytestmark = pytest.mark.requires_llm
from neo4j import AsyncGraphDatabase

from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper
from src.core.config import settings


@pytest.mark.integration
@pytest.mark.asyncio
class TestLightRAGProvenance:
    """Integration tests for LightRAG with graph-based provenance tracking."""

    @pytest.fixture
    async def lightrag_wrapper(self):
        """Create LightRAGWrapper instance with cleanup."""
        wrapper = LightRAGWrapper()
        await wrapper._ensure_initialized()

        # Clean database before test
        await wrapper._clear_neo4j_database()

        yield wrapper

        # Clean database after test
        await wrapper._clear_neo4j_database()

    async def test_insert_documents_optimized_basic(self, lightrag_wrapper):
        """Test basic document insertion with optimized pipeline."""
        # Arrange
        test_doc = {
            "id": "test_doc_001",
            "text": """
            AEGIS RAG is a hybrid retrieval system developed by Klaus Pommer.
            It combines vector search using Qdrant with graph reasoning via LightRAG and Neo4j.
            The system runs on Ollama with llama3.2 models for local, cost-free inference.
            Klaus Pommer designed the three-phase extraction pipeline for optimal performance.
            """,
        }

        # Act
        result = await lightrag_wrapper.insert_documents_optimized([test_doc])

        # Assert
        assert result["total"] == 1
        assert result["success"] == 1
        assert result["failed"] == 0

        stats = result["stats"]
        assert stats["total_chunks"] > 0, "Should create at least one chunk"
        assert stats["total_entities"] > 0, "Should extract entities"
        assert stats["total_relations"] >= 0, "Should extract relations"

        doc_result = result["results"][0]
        assert doc_result["status"] == "success"
        assert doc_result["doc_id"] == "test_doc_001"
        assert doc_result["chunks"] > 0
        assert doc_result["entities"] > 0

    async def test_chunk_nodes_created_in_neo4j(self, lightrag_wrapper):
        """Test that :chunk nodes are created in Neo4j."""
        # Arrange
        test_doc = {
            "id": "test_doc_002",
            "text": "This is a short test document about AEGIS RAG and LightRAG integration.",
        }

        # Act
        await lightrag_wrapper.insert_documents_optimized([test_doc])

        # Assert - Verify :chunk nodes exist in Neo4j
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )

        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (c:chunk {document_id: $doc_id})
                RETURN count(c) as chunk_count,
                       collect(c.chunk_index) as chunk_indices,
                       collect(c.tokens) as token_counts
                """,
                doc_id="test_doc_002",
            )
            record = await result.single()

            assert record is not None, "Should find chunk nodes"
            assert record["chunk_count"] > 0, "Should have at least one chunk"
            assert len(record["chunk_indices"]) > 0, "Should have chunk indices"

        await driver.close()

    async def test_mentioned_in_relationships_created(self, lightrag_wrapper):
        """Test that MENTIONED_IN relationships are created."""
        # Arrange
        test_doc = {
            "id": "test_doc_003",
            "text": """
            Klaus Pommer is the developer of AEGIS RAG.
            AEGIS RAG uses Ollama for local LLM inference.
            """,
        }

        # Act
        await lightrag_wrapper.insert_documents_optimized([test_doc])

        # Assert - Verify MENTIONED_IN relationships exist
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )

        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk {document_id: $doc_id})
                RETURN count(r) as mention_count,
                       collect(DISTINCT e.entity_id) as entities,
                       collect(DISTINCT c.chunk_id) as chunks
                """,
                doc_id="test_doc_003",
            )
            record = await result.single()

            assert record is not None, "Should find MENTIONED_IN relationships"
            assert record["mention_count"] > 0, "Should have mentions"
            assert len(record["entities"]) > 0, "Should have entities"

        await driver.close()

    async def test_provenance_query_example(self, lightrag_wrapper):
        """Test provenance query: Find all chunks mentioning an entity."""
        # Arrange
        test_doc = {
            "id": "test_doc_004",
            "text": """
            Ollama is a local LLM inference platform.
            Ollama supports models like llama3.2 and qwen2.5.
            The AEGIS RAG system uses Ollama for cost-free inference.
            """,
        }

        await lightrag_wrapper.insert_documents_optimized([test_doc])

        # Act - Query: "Where is Ollama mentioned?"
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )

        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (e:base {entity_id: $entity_id})-[:MENTIONED_IN]->(c:chunk)
                RETURN c.text as chunk_text,
                       c.chunk_index as chunk_index,
                       c.document_id as document_id
                ORDER BY c.chunk_index
                """,
                entity_id="Ollama",
            )

            records = await result.fetch(10)

            # Assert
            assert len(records) > 0, "Should find chunks mentioning Ollama"

            for record in records:
                chunk_text = record["chunk_text"]
                assert "Ollama" in chunk_text, "Chunk should contain the entity"
                assert record["document_id"] == "test_doc_004"

        await driver.close()

    async def test_multiple_documents_batch(self, lightrag_wrapper):
        """Test batch processing of multiple documents."""
        # Arrange
        test_docs = [
            {"id": "doc_batch_001", "text": "Document 1 about AEGIS RAG and Klaus Pommer."},
            {"id": "doc_batch_002", "text": "Document 2 about LightRAG and Neo4j integration."},
            {"id": "doc_batch_003", "text": "Document 3 about Ollama and llama3.2 models."},
        ]

        # Act
        result = await lightrag_wrapper.insert_documents_optimized(test_docs)

        # Assert
        assert result["total"] == 3
        assert result["success"] == 3
        assert result["failed"] == 0

        stats = result["stats"]
        assert stats["total_chunks"] >= 3, "Should have chunks from all docs"
        assert stats["total_entities"] > 0, "Should extract entities"

        # Verify each document was processed
        for i, doc_result in enumerate(result["results"]):
            assert doc_result["status"] == "success"
            assert doc_result["doc_id"] == test_docs[i]["id"]
            assert doc_result["chunks"] > 0

    async def test_empty_document_handling(self, lightrag_wrapper):
        """Test handling of empty documents."""
        # Arrange
        test_docs = [
            {"id": "empty_doc", "text": ""},
            {"id": "valid_doc", "text": "This is valid content about AEGIS RAG."},
        ]

        # Act
        result = await lightrag_wrapper.insert_documents_optimized(test_docs)

        # Assert
        assert result["total"] == 2
        assert result["success"] == 1, "Only valid doc should succeed"
        assert result["failed"] == 0, "Empty doc is skipped, not failed"

        # Check results
        empty_result = result["results"][0]
        assert empty_result["status"] == "skipped"
        assert empty_result["reason"] == "empty_text"

        valid_result = result["results"][1]
        assert valid_result["status"] == "success"
