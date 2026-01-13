#!/usr/bin/env python3
"""Test VLM-Enhanced Directory Indexing - Sprint 30.

This script indexes the Performance Schulung directory with VLM image enrichment.

Usage:
    poetry run python scripts/test_vlm_indexing.py

Features:
- Docling CUDA Container parsing
- Qwen3-VL image descriptions
- BGE-M3 embeddings → Qdrant
- Neo4j graph extraction
- Progress tracking with detailed stats
"""

import asyncio
import time
from pathlib import Path

import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger(__name__)


async def test_vlm_indexing():
    """Test VLM indexing for Performance Schulung directory."""
    # Import here to ensure all dependencies are loaded
    from src.components.ingestion.langgraph_pipeline import run_batch_ingestion

    # Target directory
    base_dir = Path(
        r"C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\data\sample_documents\10. Performance Schulung"
    )

    print("\n" + "=" * 80)
    print("SPRINT 30: VLM-Enhanced Directory Indexing Test")
    print("=" * 80)
    print(f"\nTarget Directory: {base_dir}")
    print(f"Directory exists: {base_dir.exists()}\n")

    if not base_dir.exists():
        print(f"ERROR: Directory not found: {base_dir}")
        return

    # Discover documents
    print("Discovering documents...")
    doc_paths = []
    for ext in [".pdf", ".pptx", ".docx", ".txt", ".md"]:
        found = list(base_dir.glob(f"*{ext}"))
        if found:
            doc_paths.extend([str(p) for p in found])
            print(f"  {ext}: {len(found)} files")

    if not doc_paths:
        print(f"ERROR: No documents found in {base_dir}")
        return

    print(f"\nTotal documents to index: {len(doc_paths)}")
    for i, doc_path in enumerate(doc_paths, 1):
        print(f"  {i}. {Path(doc_path).name}")

    # Confirm before proceeding
    print("\n" + "-" * 80)
    print("This will:")
    print("  1. Parse all documents with Docling CUDA Container")
    print("  2. Extract and describe images with Qwen3-VL")
    print("  3. Create 1800-token chunks")
    print("  4. Generate BGE-M3 embeddings -> Qdrant")
    print("  5. Extract entities/relations -> Neo4j")
    print("-" * 80)

    # Start batch ingestion
    batch_id = f"sprint30_test_{int(time.time())}"
    print(f"\nStarting batch ingestion (batch_id={batch_id})...")
    print("=" * 80 + "\n")

    start_time = time.time()
    total_chunks = 0
    total_vlm_images = 0
    total_errors = 0
    successful_docs = 0
    failed_docs = 0

    try:
        async for result in run_batch_ingestion(doc_paths, batch_id):
            doc_id = result["document_id"]
            doc_path = result["document_path"]
            doc_name = Path(doc_path).name
            batch_index = result["batch_index"]
            batch_progress = result["batch_progress"]
            success = result["success"]

            print(
                f"\n[{batch_progress:.0%}] Document {batch_index + 1}/{len(doc_paths)}: {doc_name}"
            )
            print("-" * 80)

            if success and result.get("state"):
                state = result["state"]
                chunk_count = len(state.get("chunks", []))
                vlm_count = len(state.get("vlm_metadata", []))
                error_count = len(state.get("errors", []))

                total_chunks += chunk_count
                total_vlm_images += vlm_count
                total_errors += error_count
                successful_docs += 1

                print("STATUS: SUCCESS")
                print(f"  - Document ID: {doc_id}")
                print(f"  - Chunks created: {chunk_count}")
                print(f"  - VLM images processed: {vlm_count}")
                print(f"  - Errors (non-fatal): {error_count}")

                # Show VLM metadata
                if vlm_count > 0:
                    print("\n  VLM Image Details:")
                    for i, vlm_meta in enumerate(
                        state.get("vlm_metadata", [])[:3], 1
                    ):  # Show first 3
                        image_id = vlm_meta.get("image_id", "unknown")
                        description_preview = vlm_meta.get("description", "")[:80]
                        print(f"    {i}. {image_id}: {description_preview}...")
                    if vlm_count > 3:
                        print(f"    ... and {vlm_count - 3} more images")

                # Show errors if any
                if error_count > 0:
                    print("\n  Non-fatal Errors:")
                    for i, error in enumerate(state.get("errors", [])[:3], 1):
                        error_node = error.get("node", "unknown")
                        error_msg = error.get("message", "")[:80]
                        print(f"    {i}. [{error_node}] {error_msg}...")

            else:
                failed_docs += 1
                error_msg = result.get("error", "Unknown error")
                print("STATUS: FAILED")
                print(f"  - Document ID: {doc_id}")
                print(f"  - Error: {error_msg}")

            print("-" * 80)

    except Exception as e:
        logger.error("batch_ingestion_failed", error=str(e), exc_info=True)
        print(f"\nFATAL ERROR: {e}")
        return

    # Final summary
    total_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("BATCH INGESTION COMPLETED")
    print("=" * 80)
    print("\nStatistics:")
    print(f"  - Total documents: {len(doc_paths)}")
    print(f"  - Successful: {successful_docs}")
    print(f"  - Failed: {failed_docs}")
    print(f"  - Total chunks created: {total_chunks}")
    print(f"  - Total VLM images processed: {total_vlm_images}")
    print(f"  - Total errors (non-fatal): {total_errors}")
    print(f"  - Duration: {total_time:.1f}s")
    print(f"  - Average per document: {total_time / len(doc_paths):.1f}s")

    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Check Qdrant: http://localhost:6333/dashboard")
    print("2. Check Neo4j: http://localhost:7474 (neo4j/neo4j)")
    print("3. Check logs for detailed progress")
    print("4. Query via API: POST /api/v1/retrieval/query")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("Sprint 30: VLM-Enhanced Directory Indexing Test")
    print("=" * 80 + "\n")

    asyncio.run(test_vlm_indexing())
