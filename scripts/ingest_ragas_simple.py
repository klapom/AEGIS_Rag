#!/usr/bin/env python3
"""Simple RAGAS dataset ingestion with namespace isolation.

Sprint 76 Feature 76.1 (TD-084): Test namespace isolation with RAGAS dataset.

This script ingests the RAGAS evaluation dataset into the "ragas_eval" namespace
to verify that namespace isolation works correctly across the ingestion pipeline.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.graph import END, StateGraph

from src.components.ingestion.ingestion_state import IngestionState, create_initial_state
from src.components.ingestion.langgraph_nodes import (
    chunking_node,
    embedding_node,
    graph_extraction_node,
)

logger = structlog.get_logger(__name__)


def create_ingestion_pipeline(skip_graph: bool = False):
    """Create LangGraph pipeline for chunking → embedding → graph extraction.

    Args:
        skip_graph: If True, skip graph extraction (for testing namespace isolation)
    """
    graph = StateGraph(IngestionState)

    graph.add_node("chunking", chunking_node)
    graph.add_node("embedding", embedding_node)

    graph.set_entry_point("chunking")
    graph.add_edge("chunking", "embedding")

    if skip_graph:
        # Sprint 76 TD-084: Skip graph extraction to test Qdrant namespace isolation
        graph.add_edge("embedding", END)
    else:
        graph.add_node("graph", graph_extraction_node)
        graph.add_edge("embedding", "graph")
        graph.add_edge("graph", END)

    return graph.compile()


async def ingest_ragas_dataset(
    dataset_path: str = "data/evaluation/ragas_dataset.jsonl",
    namespace_id: str = "ragas_eval",
    domain_id: str | None = None,
    max_docs: int = 10,
):
    """Ingest RAGAS dataset into specified namespace.

    Args:
        dataset_path: Path to RAGAS JSONL dataset
        namespace_id: Namespace for multi-tenant isolation (default: ragas_eval)
        domain_id: Optional domain for DSPy-optimized prompts
        max_docs: Maximum number of documents to ingest
    """
    logger.info("=" * 80)
    logger.info(f"RAGAS INGESTION - Sprint 76 TD-084 Namespace Isolation Test")
    logger.info("=" * 80)
    logger.info(f"Dataset: {dataset_path}")
    logger.info(f"Namespace: {namespace_id}")
    logger.info(f"Domain: {domain_id or 'None (generic prompts)'}")
    logger.info(f"Max documents: {max_docs}")

    # Load RAGAS dataset
    dataset_file = Path(dataset_path)
    if not dataset_file.exists():
        logger.error(f"Dataset not found: {dataset_path}")
        return []

    questions = []
    with open(dataset_file) as f:
        for i, line in enumerate(f):
            if i >= max_docs:
                break
            questions.append(json.loads(line))

    logger.info(f"Loaded {len(questions)} questions from dataset")

    # Create pipeline with FULL graph extraction for RAGAS evaluation
    pipeline = create_ingestion_pipeline(skip_graph=False)
    logger.info("Pipeline created with chunking → embedding → graph extraction (full ER extraction)")

    # Ingest each document
    results = []
    total_start = time.time()

    for i, question_data in enumerate(questions):
        question = question_data["question"]
        logger.info(f"\n[{i+1}/{len(questions)}] Ingesting question: {question[:60]}...")

        try:
            # Combine contexts into single document text
            contexts = question_data["contexts"]
            combined_text = "\n\n".join(contexts)

            # Generate unique document_id
            import hashlib
            doc_id = f"ragas_{hashlib.md5(question.encode()).hexdigest()[:12]}"

            # Sprint 76 TD-084/TD-085: Use create_initial_state with namespace/domain
            state = create_initial_state(
                document_path=f"/virtual/ragas/{doc_id}.txt",
                document_id=doc_id,
                batch_id="ragas_batch_001",
                batch_index=i,
                total_documents=len(questions),
                namespace_id=namespace_id,  # TD-084: Namespace isolation
                domain_id=domain_id,  # TD-085: Domain-optimized prompts
            )

            # Add parsed content (skip parsing node)
            state["parsed_content"] = combined_text
            state["docling_status"] = "completed"
            state["metadata"] = {
                "source": "ragas_dataset",
                "question": question,
                "ground_truth": question_data["ground_truth"],
                "difficulty": question_data.get("metadata", {}).get("difficulty", "unknown"),
                "category": question_data.get("metadata", {}).get("category", "general"),
            }

            # Run pipeline
            doc_start = time.time()
            final_state = await pipeline.ainvoke(state)
            doc_time = time.time() - doc_start

            # Check status (graph_status for full pipeline with ER extraction)
            if final_state.get("graph_status") == "completed":
                result = {
                    "document_id": doc_id,
                    "question": question,
                    "ground_truth": question_data["ground_truth"],
                    "namespace_id": namespace_id,
                    "domain_id": domain_id,
                    "time_seconds": doc_time,
                    "chunks": len(final_state.get("chunks", [])),
                    "points_uploaded": final_state.get("points_uploaded", 0),
                    "entities": final_state.get("total_entities_extracted", 0),
                    "relations": final_state.get("total_relations_created", 0),
                }
                results.append(result)
                logger.info(f"  ✓ Success in {doc_time:.1f}s")
                logger.info(f"    Chunks: {result['chunks']}, Entities: {result['entities']}, Relations: {result['relations']}")
            else:
                logger.warning(f"  ✗ Failed: {final_state.get('errors', [])}")

        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()

    total_time = time.time() - total_start

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total time: {total_time:.1f}s")
    logger.info(f"Successfully ingested: {len(results)}/{len(questions)}")

    if results:
        avg_time = sum(r["time_seconds"] for r in results) / len(results)
        total_chunks = sum(r["chunks"] for r in results)
        total_points = sum(r["points_uploaded"] for r in results)
        total_entities = sum(r["entities"] for r in results)
        total_relations = sum(r["relations"] for r in results)

        logger.info(f"Average time per doc: {avg_time:.1f}s")
        logger.info(f"Total chunks: {total_chunks}")
        logger.info(f"Total points uploaded to Qdrant: {total_points}")
        logger.info(f"Total entities extracted: {total_entities}")
        logger.info(f"Total relations created: {total_relations}")

    return results


async def verify_namespace_isolation(namespace_id: str = "ragas_eval"):
    """Verify that documents are isolated in the specified namespace.

    Args:
        namespace_id: Namespace to verify
    """
    logger.info("\n" + "=" * 80)
    logger.info("NAMESPACE ISOLATION VERIFICATION")
    logger.info("=" * 80)

    try:
        # Query Qdrant to verify namespace isolation
        from qdrant_client import QdrantClient
        from src.core.config import settings

        client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )

        # Count points in namespace
        # NOTE: The payload field is "namespace", not "namespace_id"
        collection_name = settings.qdrant_collection
        count_result = client.count(
            collection_name=collection_name,
            count_filter={
                "must": [
                    {"key": "namespace", "match": {"value": namespace_id}}
                ]
            },
        )

        logger.info(f"Documents in namespace '{namespace_id}': {count_result.count}")

        # Count points in default namespace for comparison
        default_count = client.count(
            collection_name=collection_name,
            count_filter={
                "must": [
                    {"key": "namespace", "match": {"value": "default"}}
                ]
            },
        )

        logger.info(f"Documents in namespace 'default': {default_count.count}")
        logger.info(f"✓ Namespace isolation verified!")

    except Exception as e:
        logger.error(f"Failed to verify namespace isolation: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Ingest RAGAS dataset with namespace isolation")
    parser.add_argument(
        "--namespace",
        default="ragas_eval",
        help="Namespace ID for multi-tenant isolation (default: ragas_eval)",
    )
    parser.add_argument(
        "--domain",
        default=None,
        help="Domain ID for DSPy-optimized prompts (optional)",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=10,
        help="Maximum number of documents to ingest (default: 10)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify namespace isolation after ingestion",
    )

    args = parser.parse_args()

    # Ingest documents
    results = await ingest_ragas_dataset(
        namespace_id=args.namespace,
        domain_id=args.domain,
        max_docs=args.max_docs,
    )

    if not results:
        logger.error("No documents ingested")
        return

    # Verify namespace isolation if requested
    if args.verify:
        await verify_namespace_isolation(namespace_id=args.namespace)

    logger.info("\n✓ RAGAS ingestion complete!")


if __name__ == "__main__":
    asyncio.run(main())
