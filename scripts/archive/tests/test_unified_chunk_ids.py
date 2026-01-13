#!/usr/bin/env python3
"""Test Unified Chunk IDs between Qdrant and Neo4j.

This script ingests a test document via LangGraph pipeline and verifies
that chunk IDs are consistent between Qdrant (vector) and Neo4j (graph).

Sprint 42: Verify ID alignment for true hybrid search.
"""

import asyncio
import hashlib
import sys
from pathlib import Path

import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.components.graph_rag.neo4j_client import Neo4jClient
from src.components.ingestion.langgraph_pipeline import run_ingestion_pipeline
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.config import settings

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)

logger = structlog.get_logger(__name__)


async def main():
    """Main test function."""
    document_path = "/tmp/test_unified_ids.txt"

    # Generate document_id from content hash
    with open(document_path) as f:
        content = f.read()
    document_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    logger.info("=" * 60)
    logger.info("TEST: Unified Chunk IDs (Qdrant ↔ Neo4j)")
    logger.info("=" * 60)
    logger.info(f"Document: {document_path}")
    logger.info(f"Document ID: {document_id}")

    # Step 1: Run LangGraph Ingestion Pipeline
    logger.info("\n[1] Running LangGraph Ingestion Pipeline...")

    try:
        final_state = await run_ingestion_pipeline(
            document_path=document_path,
            document_id=document_id,
            batch_id="test_unified_ids",
            batch_index=0,
            total_documents=1,
        )

        logger.info(f"Pipeline status: {final_state.get('graph_status', 'unknown')}")
        logger.info(f"Chunks created: {len(final_state.get('chunks', []))}")
        logger.info(f"Entities extracted: {len(final_state.get('entities', []))}")

        if final_state.get("errors"):
            for error in final_state["errors"]:
                logger.error(f"Error: {error}")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return

    # Step 2: Get chunk IDs from pipeline state
    logger.info("\n[2] Chunk IDs from Pipeline State:")
    pipeline_chunk_ids = set()
    for chunk in final_state.get("chunks", []):
        chunk_id = chunk.get("chunk_id") or chunk.get("id")
        if chunk_id:
            pipeline_chunk_ids.add(chunk_id)
            logger.info(f"  - Pipeline chunk: {chunk_id}")

    # Step 3: Query Qdrant for chunk IDs
    logger.info("\n[3] Chunk IDs in Qdrant:")
    qdrant_client = get_qdrant_client()
    qdrant_chunk_ids = set()

    try:
        # Search by document_id in payload
        results = await qdrant_client.async_client.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter={
                "must": [
                    {"key": "document_id", "match": {"value": document_id}}
                ]
            },
            limit=100,
            with_payload=True,
        )

        for point in results[0]:
            chunk_id = point.payload.get("chunk_id")
            if chunk_id:
                qdrant_chunk_ids.add(chunk_id)
                logger.info(f"  - Qdrant chunk: {chunk_id}")
                logger.info(f"    → document_id: {point.payload.get('document_id')}")
                logger.info(f"    → text preview: {point.payload.get('text', '')[:50]}...")
    except Exception as e:
        logger.error(f"Qdrant query failed: {e}")

    # Step 4: Query Neo4j for chunk IDs
    logger.info("\n[4] Chunk IDs in Neo4j:")
    neo4j_chunk_ids = set()

    try:
        neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password.get_secret_value(),
        )

        # Query for chunks linked to our document
        cypher = """
        MATCH (c:Chunk)
        WHERE c.document_id = $document_id OR c.file_path = $document_id
        RETURN c.chunk_id AS chunk_id, c.source_id AS source_id,
               c.document_id AS document_id, c.text AS text
        LIMIT 100
        """

        results = await neo4j_client.execute_read(cypher, {"document_id": document_id})

        for record in results:
            chunk_id = record.get("chunk_id") or record.get("source_id")
            if chunk_id:
                neo4j_chunk_ids.add(chunk_id)
                logger.info(f"  - Neo4j chunk: {chunk_id}")
                logger.info(f"    → document_id: {record.get('document_id')}")

        # Also check for entities with source_id
        cypher_entities = """
        MATCH (e:base)
        WHERE e.file_path = $document_id
        RETURN e.entity_name AS name, e.source_id AS source_id
        LIMIT 20
        """

        entity_results = await neo4j_client.execute_read(cypher_entities, {"document_id": document_id})

        logger.info("\n[4b] Entities in Neo4j (with source_id):")
        for record in entity_results:
            source_id = record.get("source_id")
            logger.info(f"  - Entity: {record.get('name')}")
            logger.info(f"    → source_id: {source_id}")
            if source_id:
                neo4j_chunk_ids.add(source_id)

        await neo4j_client.close()
    except Exception as e:
        logger.error(f"Neo4j query failed: {e}")

    # Step 5: Compare IDs
    logger.info("\n" + "=" * 60)
    logger.info("COMPARISON RESULTS")
    logger.info("=" * 60)

    logger.info(f"\nPipeline chunks: {len(pipeline_chunk_ids)}")
    logger.info(f"Qdrant chunks:   {len(qdrant_chunk_ids)}")
    logger.info(f"Neo4j chunks:    {len(neo4j_chunk_ids)}")

    # Find overlaps
    qdrant_neo4j_overlap = qdrant_chunk_ids & neo4j_chunk_ids
    logger.info(f"\nQdrant ∩ Neo4j: {len(qdrant_neo4j_overlap)} matching IDs")

    if qdrant_neo4j_overlap:
        logger.info("✅ SUCCESS: Chunk IDs are aligned!")
        for chunk_id in qdrant_neo4j_overlap:
            logger.info(f"  ✓ {chunk_id}")
    else:
        logger.warning("❌ MISMATCH: No overlapping chunk IDs found!")

        if qdrant_chunk_ids:
            logger.info("\nQdrant-only IDs:")
            for cid in list(qdrant_chunk_ids)[:5]:
                logger.info(f"  - {cid}")

        if neo4j_chunk_ids:
            logger.info("\nNeo4j-only IDs:")
            for cid in list(neo4j_chunk_ids)[:5]:
                logger.info(f"  - {cid}")


if __name__ == "__main__":
    asyncio.run(main())
