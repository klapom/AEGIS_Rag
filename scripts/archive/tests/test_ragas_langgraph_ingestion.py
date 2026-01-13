#!/usr/bin/env python3
"""Test RAGAS Ingestion via LangGraph Pipeline (Post-Parse Entry).

This script injects RAGAS dataset texts into LangGraph pipeline AFTER
the parsing stage, using the chunking → embedding → graph extraction nodes.

This verifies:
1. Unified chunk IDs between Qdrant and Neo4j
2. Full pipeline execution (not bypass like corpus_ingestion.py)
3. Graph extraction from evaluation data

Sprint 42: Pipeline integration test for unified IDs.
"""

import asyncio
import hashlib
import sys
import time
from pathlib import Path

import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.graph import END, StateGraph

from src.components.graph_rag.neo4j_client import Neo4jClient
from src.components.ingestion.ingestion_state import IngestionState
from src.components.ingestion.langgraph_nodes import (
    chunking_node,
    embedding_node,
    graph_extraction_node,
)
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


def create_post_parse_pipeline():
    """Create LangGraph pipeline starting AFTER parsing.

    Pipeline: chunking → embedding → graph_extraction → END

    This skips memory_check, docling_parse, image_enrichment nodes.
    """
    graph = StateGraph(IngestionState)

    # Add only post-parse nodes
    graph.add_node("chunking", chunking_node)
    graph.add_node("embedding", embedding_node)
    graph.add_node("graph", graph_extraction_node)

    # Define edges
    graph.set_entry_point("chunking")
    graph.add_edge("chunking", "embedding")
    graph.add_edge("embedding", "graph")
    graph.add_edge("graph", END)

    return graph.compile()


def create_state_from_text(
    text: str,
    document_id: str,
    namespace_id: str = "test_ragas",
    source: str = "ragas_test",
) -> IngestionState:
    """Create IngestionState with pre-parsed text content.

    Simulates the state AFTER docling parsing completes.
    """
    return IngestionState(
        # Input fields
        document_path=f"/virtual/{document_id}.txt",
        document_id=document_id,
        batch_id="ragas_test_batch",
        batch_index=0,
        total_documents=1,
        # Simulated parse output - this is what chunking_node expects
        parsed_content=text,
        parsed_metadata={
            "source": source,
            "namespace_id": namespace_id,
            "pages": 1,
            "size_bytes": len(text.encode()),
            "mime_type": "text/plain",
        },
        parsed_tables=[],
        parsed_images=[],
        parsed_layout={},
        docling_status="completed",  # Pretend parsing succeeded
        # Memory check (pretend it passed)
        current_memory_mb=1000.0,
        current_vram_mb=0.0,
        memory_check_passed=True,
        requires_container_restart=False,
        # VLM enrichment (skip)
        vlm_metadata=[],
        enrichment_status="completed",
        # Initialize output fields
        chunks=[],
        embedded_chunk_ids=[],
        entities=[],
        relations=[],
        relations_count=0,
        # Progress tracking
        overall_progress=0.35,  # Start at 35% (post-parse)
        errors=[],
        retry_count=0,
        max_retries=3,
        # Timestamps
        start_time=time.time(),
        docling_start_time=time.time(),
        docling_end_time=time.time(),
        chunking_start_time=0.0,
        chunking_end_time=0.0,
        embedding_start_time=0.0,
        embedding_end_time=0.0,
        graph_start_time=0.0,
        graph_end_time=0.0,
        end_time=0.0,
    )


# Sample RAGAS-style test data (simulating HotpotQA context)
RAGAS_TEST_SAMPLE = {
    "question_id": "test_amsterdam_001",
    "question": "Who is a famous kickboxer from Amsterdam?",
    "contexts": [
        """Amsterdam is the capital and largest city of the Netherlands.
        It is known for its artistic heritage, elaborate canal system, and
        narrow houses with gabled facades. The city has a population of
        about 900,000 people in the urban area.""",

        """Badr Hari is a Moroccan-Dutch super heavyweight kickboxer from Amsterdam.
        He is a former K-1 World Grand Prix finalist and has won multiple world
        championships. Known for his aggressive fighting style and powerful punches,
        Hari has been one of the most popular kickboxers in the sport's history.""",

        """The Anne Frank House is a museum in Amsterdam dedicated to the Jewish
        wartime diarist Anne Frank. The building is located on the Prinsengracht canal
        and is one of Amsterdam's most popular tourist attractions.""",
    ],
    "answer": "Badr Hari",
    "source": "hotpotqa_simulated",
}


async def main():
    """Main test function."""
    logger.info("=" * 70)
    logger.info("TEST: RAGAS → LangGraph Pipeline (Post-Parse Entry)")
    logger.info("=" * 70)

    # Create pipeline (chunking → embedding → graph)
    logger.info("\n[1] Creating post-parse LangGraph pipeline...")
    pipeline = create_post_parse_pipeline()
    logger.info("Pipeline created: chunking → embedding → graph → END")

    # Combine all contexts into one document
    combined_text = "\n\n".join(RAGAS_TEST_SAMPLE["contexts"])
    document_id = hashlib.sha256(combined_text.encode()).hexdigest()[:16]

    logger.info("\n[2] Test document:")
    logger.info(f"  Question ID: {RAGAS_TEST_SAMPLE['question_id']}")
    logger.info(f"  Document ID: {document_id}")
    logger.info(f"  Text length: {len(combined_text)} chars")
    logger.info(f"  Contexts: {len(RAGAS_TEST_SAMPLE['contexts'])}")

    # Create state with pre-parsed content
    state = create_state_from_text(
        text=combined_text,
        document_id=document_id,
        namespace_id="test_ragas_langgraph",
        source=RAGAS_TEST_SAMPLE["source"],
    )

    # Run pipeline
    logger.info("\n[3] Running LangGraph pipeline...")
    try:
        final_state = await pipeline.ainvoke(state)

        logger.info("\n[4] Pipeline Results:")
        logger.info(f"  Chunking status: {final_state.get('chunking_status', 'unknown')}")
        logger.info(f"  Embedding status: {final_state.get('embedding_status', 'unknown')}")
        logger.info(f"  Graph status: {final_state.get('graph_status', 'unknown')}")
        logger.info(f"  Chunks created: {len(final_state.get('chunks', []))}")
        logger.info(f"  Entities extracted: {len(final_state.get('entities', []))}")
        logger.info(f"  Relations created: {final_state.get('relations_count', 0)}")

        if final_state.get("errors"):
            logger.warning(f"  Errors: {len(final_state['errors'])}")
            for error in final_state["errors"]:
                logger.error(f"    - {error}")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Collect chunk IDs from pipeline state (embedded_chunk_ids)
    logger.info("\n[5] Chunk IDs from Pipeline State (embedded_chunk_ids):")
    pipeline_chunk_ids = set()

    # Sprint 42: Use embedded_chunk_ids from state
    embedded_chunk_ids = final_state.get("embedded_chunk_ids", [])
    for chunk_id in embedded_chunk_ids:
        if chunk_id:
            pipeline_chunk_ids.add(chunk_id)
            logger.info(f"  - {chunk_id}")

    logger.info(f"  Total embedded_chunk_ids: {len(pipeline_chunk_ids)}")

    # Query Qdrant for stored chunk IDs
    logger.info("\n[6] Querying Qdrant for chunk IDs...")
    qdrant_chunk_ids = set()

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        qdrant_sync = QdrantClient(host="localhost", port=6333)

        # Scroll through points with our document_id
        results, _ = qdrant_sync.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            ),
            limit=100,
            with_payload=True,
        )

        for point in results:
            chunk_id = point.payload.get("chunk_id")
            if chunk_id:
                qdrant_chunk_ids.add(chunk_id)
                logger.info(f"  - Qdrant: {chunk_id}")
                logger.info(f"    document_id: {point.payload.get('document_id')}")

        logger.info(f"  Total in Qdrant: {len(qdrant_chunk_ids)}")

    except Exception as e:
        logger.error(f"Qdrant query failed: {e}")
        import traceback
        traceback.print_exc()

    # Query Neo4j for stored chunk/entity IDs
    logger.info("\n[7] Querying Neo4j for source_ids...")
    neo4j_source_ids = set()

    try:
        neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password.get_secret_value(),
        )

        # Query entities with our document's file_path
        cypher = """
        MATCH (e:base)
        WHERE e.file_path = $document_id
        RETURN e.entity_name AS name, e.source_id AS source_id,
               e.entity_type AS type
        LIMIT 50
        """

        results = await neo4j_client.execute_read(cypher, {"document_id": document_id})

        for record in results:
            source_id = record.get("source_id")
            if source_id:
                neo4j_source_ids.add(source_id)
                logger.info(f"  - Neo4j entity: {record.get('name')} ({record.get('type')})")
                logger.info(f"    source_id: {source_id}")

        # Also check for chunk nodes (lowercase label)
        chunk_cypher = """
        MATCH (c:chunk)
        WHERE c.document_id = $document_id
        RETURN c.chunk_id AS chunk_id, substring(c.text, 0, 80) AS text
        LIMIT 50
        """

        chunk_results = await neo4j_client.execute_read(chunk_cypher, {"document_id": document_id})

        for record in chunk_results:
            chunk_id = record.get("chunk_id")
            if chunk_id:
                neo4j_source_ids.add(chunk_id)
                logger.info(f"  - Neo4j chunk: {chunk_id}")

        logger.info(f"  Total source_ids in Neo4j: {len(neo4j_source_ids)}")

        await neo4j_client.close()

    except Exception as e:
        logger.error(f"Neo4j query failed: {e}")

    # Compare IDs
    logger.info("\n" + "=" * 70)
    logger.info("COMPARISON RESULTS")
    logger.info("=" * 70)

    logger.info(f"\nPipeline chunks: {len(pipeline_chunk_ids)}")
    logger.info(f"Qdrant chunks:   {len(qdrant_chunk_ids)}")
    logger.info(f"Neo4j source_ids: {len(neo4j_source_ids)}")

    # Find overlaps
    qdrant_neo4j_overlap = qdrant_chunk_ids & neo4j_source_ids
    pipeline_qdrant_overlap = pipeline_chunk_ids & qdrant_chunk_ids

    logger.info(f"\nPipeline ∩ Qdrant: {len(pipeline_qdrant_overlap)}")
    logger.info(f"Qdrant ∩ Neo4j:    {len(qdrant_neo4j_overlap)}")

    if qdrant_neo4j_overlap:
        logger.info("\n✅ SUCCESS: Chunk IDs are aligned between Qdrant and Neo4j!")
        for chunk_id in list(qdrant_neo4j_overlap)[:5]:
            logger.info(f"  ✓ {chunk_id}")
    elif qdrant_chunk_ids and neo4j_source_ids:
        logger.warning("\n❌ MISMATCH: No overlapping IDs found!")
        logger.info("\nQdrant chunk_id format:")
        for cid in list(qdrant_chunk_ids)[:3]:
            logger.info(f"  {cid}")
        logger.info("\nNeo4j source_id format:")
        for sid in list(neo4j_source_ids)[:3]:
            logger.info(f"  {sid}")
    else:
        logger.warning("\n⚠️  Missing data - check if ingestion completed")


if __name__ == "__main__":
    asyncio.run(main())
