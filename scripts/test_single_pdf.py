#!/usr/bin/env python3
"""Quick test for a single PDF with VLM indexing - Sprint 30."""

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


async def test_single_pdf(pdf_path: str):
    """Test VLM indexing for a single PDF."""
    from src.components.ingestion.langgraph_pipeline import run_batch_ingestion

    pdf_file = Path(pdf_path)

    print("\n" + "=" * 80)
    print("SPRINT 30: Single PDF VLM Indexing Test")
    print("=" * 80)
    print(f"\nPDF File: {pdf_file.name}")
    print(f"File Path: {pdf_file}")
    print(f"File exists: {pdf_file.exists()}")

    if not pdf_file.exists():
        print(f"ERROR: PDF not found: {pdf_file}")
        return

    # Get file size
    file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
    print(f"File size: {file_size_mb:.2f} MB")

    print("\n" + "-" * 80)
    print("This will:")
    print("  1. Parse PDF with Docling CUDA Container")
    print("  2. Extract and describe images with Qwen3-VL")
    print("  3. Create 1800-token chunks")
    print("  4. Generate BGE-M3 embeddings -> Qdrant")
    print("  5. Extract entities/relations -> Neo4j")
    print("-" * 80)

    # Start batch ingestion
    batch_id = f"single_pdf_test_{int(time.time())}"
    doc_paths = [str(pdf_file)]

    print(f"\nStarting batch ingestion (batch_id={batch_id})...")
    print("=" * 80 + "\n")

    start_time = time.time()

    try:
        async for result in run_batch_ingestion(doc_paths, batch_id):
            doc_id = result["document_id"]
            doc_name = Path(result["document_path"]).name
            success = result["success"]

            print(f"\nDocument: {doc_name}")
            print("-" * 80)

            if success and result.get("state"):
                state = result["state"]
                chunk_count = len(state.get("chunks", []))
                vlm_count = len(state.get("vlm_metadata", []))
                error_count = len(state.get("errors", []))

                print(f"STATUS: SUCCESS")
                print(f"  - Document ID: {doc_id}")
                print(f"  - Chunks created: {chunk_count}")
                print(f"  - VLM images processed: {vlm_count}")
                print(f"  - Errors (non-fatal): {error_count}")

                # Show VLM metadata
                if vlm_count > 0:
                    print(f"\n  VLM Image Details:")
                    for i, vlm_meta in enumerate(state.get("vlm_metadata", []), 1):
                        image_id = vlm_meta.get("image_id", "unknown")
                        description = vlm_meta.get("description", "")[:100]
                        print(f"    {i}. {image_id}: {description}...")

                # Show errors if any
                if error_count > 0:
                    print(f"\n  Non-fatal Errors:")
                    for i, error in enumerate(state.get("errors", [])[:3], 1):
                        error_node = error.get("node", "unknown")
                        error_msg = error.get("message", "")[:80]
                        print(f"    {i}. [{error_node}] {error_msg}...")
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"STATUS: FAILED")
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
    print("INGESTION COMPLETED")
    print("=" * 80)
    print(f"\nStatistics:")
    print(f"  - Duration: {total_time:.1f}s")
    print(f"  - File size: {file_size_mb:.2f} MB")
    print(f"  - Processing speed: {file_size_mb / (total_time / 60):.2f} MB/min")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python test_single_pdf.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    asyncio.run(test_single_pdf(pdf_path))
