"""Quick standalone test for LightRAG Provenance implementation.

Sprint 14 Feature 14.1 - Phase 8: Testing & Validation

This script tests the new insert_documents_optimized() method without pytest infrastructure.
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase

from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper
from src.core.config import settings


async def test_chunking():
    """Test 1: Chunking with metadata."""
    print("\n" + "=" * 80)
    print("TEST 1: Chunking with metadata")
    print("=" * 80)

    wrapper = LightRAGWrapper()

    test_text = """
    AEGIS RAG is a hybrid retrieval system developed by Klaus Pommer.
    It combines vector search using Qdrant with graph reasoning via LightRAG and Neo4j.
    The system runs on Ollama with llama3.2 models for local, cost-free inference.
    Klaus Pommer designed the three-phase extraction pipeline for optimal performance.
    """

    chunks = wrapper._chunk_text_with_metadata(
        text=test_text,
        document_id="test_doc_001",
        chunk_token_size=50,  # Small for testing
        chunk_overlap_token_size=10,
    )

    print(f"✓ Created {len(chunks)} chunks")
    print(f"  - Chunk IDs: {[c['chunk_id'][:8] for c in chunks]}")
    print(f"  - Tokens per chunk: {[c['tokens'] for c in chunks]}")

    assert len(chunks) > 0, "Should create chunks"
    assert all("chunk_id" in c for c in chunks), "All chunks should have chunk_id"
    assert all("document_id" in c for c in chunks), "All chunks should have document_id"

    print("✓ TEST 1 PASSED\n")


async def test_insert_and_provenance():
    """Test 2: Full integration with provenance."""
    print("\n" + "=" * 80)
    print("TEST 2: Full integration with provenance tracking")
    print("=" * 80)

    wrapper = LightRAGWrapper()
    await wrapper._ensure_initialized()

    # Clean database
    print("Cleaning Neo4j database...")
    await wrapper._clear_neo4j_database()

    # Test document
    test_doc = {
        "id": "quick_test_001",
        "text": """
        Klaus Pommer developed AEGIS RAG system.
        AEGIS RAG uses Ollama for local LLM inference.
        The system integrates LightRAG with Neo4j for graph reasoning.
        """,
    }

    print(f"Inserting test document: {test_doc['id']}")
    print(f"Text length: {len(test_doc['text'])} chars")

    # Insert
    result = await wrapper.insert_documents_optimized([test_doc])

    print("\n✓ Insertion complete:")
    print(f"  - Total: {result['total']}")
    print(f"  - Success: {result['success']}")
    print(f"  - Failed: {result['failed']}")
    print(f"  - Time: {result['total_time_seconds']:.2f}s")

    stats = result["stats"]
    print("\n✓ Statistics:")
    print(f"  - Chunks: {stats['total_chunks']}")
    print(f"  - Entities: {stats['total_entities']}")
    print(f"  - Relations: {stats['total_relations']}")
    print(f"  - MENTIONED_IN: {stats['total_mentioned_in']}")

    assert result["success"] == 1, "Should insert successfully"
    assert stats["total_chunks"] > 0, "Should create chunks"
    assert stats["total_entities"] > 0, "Should extract entities"

    # Verify Neo4j schema
    print("\n✓ Verifying Neo4j schema...")

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value())
    )

    async with driver.session() as session:
        # Check :chunk nodes
        chunk_result = await session.run(
            "MATCH (c:chunk {document_id: $doc_id}) RETURN count(c) as count",
            doc_id="quick_test_001",
        )
        chunk_record = await chunk_result.single()
        chunk_count = chunk_record["count"]
        print(f"  - :chunk nodes: {chunk_count}")
        assert chunk_count > 0, "Should have chunk nodes"

        # Check :base entities
        entity_result = await session.run("MATCH (e:base) RETURN count(e) as count")
        entity_record = await entity_result.single()
        entity_count = entity_record["count"]
        print(f"  - :base entities: {entity_count}")
        assert entity_count > 0, "Should have entity nodes"

        # Check MENTIONED_IN relationships
        mention_result = await session.run(
            """
            MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk {document_id: $doc_id})
            RETURN count(r) as count
            """,
            doc_id="quick_test_001",
        )
        mention_record = await mention_result.single()
        mention_count = mention_record["count"]
        print(f"  - MENTIONED_IN relationships: {mention_count}")
        assert mention_count > 0, "Should have MENTIONED_IN relationships"

    await driver.close()

    print("\n✓ TEST 2 PASSED\n")


async def test_provenance_query():
    """Test 3: Provenance query."""
    print("\n" + "=" * 80)
    print("TEST 3: Provenance query - Find chunks mentioning entity")
    print("=" * 80)

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value())
    )

    async with driver.session() as session:
        # Find an entity
        entity_result = await session.run("MATCH (e:base) RETURN e.entity_id as name LIMIT 1")
        entity_record = await entity_result.single()

        if not entity_record:
            print("⚠ No entities found, skipping provenance query test")
            await driver.close()
            return

        entity_id = entity_record["name"]
        print(f"✓ Testing provenance for entity: {entity_id}")

        # Query provenance
        provenance_result = await session.run(
            """
            MATCH (e:base {entity_id: $entity_id})-[:MENTIONED_IN]->(c:chunk)
            RETURN c.text as chunk_text,
                   c.chunk_index as chunk_index,
                   c.tokens as tokens,
                   c.document_id as document_id
            """,
            entity_id=entity_id,
        )

        records = await provenance_result.fetch(10)

        print(f"\n✓ Found {len(records)} chunk(s) mentioning '{entity_id}':")
        for i, record in enumerate(records):
            print(f"\n  Chunk {i+1}:")
            print(f"    - Document: {record['document_id']}")
            print(f"    - Chunk Index: {record['chunk_index']}")
            print(f"    - Tokens: {record['tokens']}")
            print(f"    - Text Preview: {record['chunk_text'][:100]}...")

            # Verify entity is actually in the text
            assert (
                entity_id in record["chunk_text"]
            ), f"Entity '{entity_id}' should be in chunk text"

    await driver.close()

    print("\n✓ TEST 3 PASSED\n")


async def main():
    """Run all tests."""
    print("\n" + "#" * 80)
    print("# Sprint 14 Feature 14.1 - LightRAG Provenance Quick Test")
    print("#" * 80)

    try:
        await test_chunking()
        await test_insert_and_provenance()
        await test_provenance_query()

        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
