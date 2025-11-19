"""Setup Demo Data Script for AEGIS RAG.

This script indexes all *.md documents in the project for demo purposes.
Run this before starting the Gradio UI to have pre-loaded content.

Usage:
    python scripts/setup_demo_data.py

Or with custom options:
    python scripts/setup_demo_data.py --force  # Re-index even if data exists
"""

import asyncio
import sys
from pathlib import Path

import structlog

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.components.vector_search.ingestion import DocumentIngestionPipeline
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import settings

logger = structlog.get_logger(__name__)


async def check_collection_exists() -> tuple[bool, int]:
    """Check if collection exists and has documents.

    Returns:
        Tuple of (exists, document_count)
    """
    try:
        qdrant = QdrantClientWrapper()
        info = await qdrant.get_collection_info(settings.qdrant_collection)

        if info:
            return True, info.points_count or 0
        return False, 0
    except Exception:
        return False, 0


async def setup_demo_data(force: bool = False) -> dict:
    """Index all *.md documents in the project.

    Args:
        force: Re-index even if data exists

    Returns:
        Dictionary with indexing statistics
    """
    logger.info("=== AEGIS RAG Demo Data Setup ===")

    # Check if collection already has documents
    exists, doc_count = await check_collection_exists()

    if exists and doc_count > 0 and not force:
        logger.info(
            "[OK] Demo data already exists, skipping indexing",
            collection=settings.qdrant_collection,
            documents_count=doc_count,
        )
        logger.info("[INFO] Use --force flag to re-index")
        return {"status": "skipped", "reason": "data_exists", "existing_documents": doc_count}

    if force and doc_count > 0:
        logger.warning(
            "[WARN] Force flag set, will re-index over existing data", existing_documents=doc_count
        )

    # Find project root
    project_root = PROJECT_ROOT.resolve()
    logger.info("[INFO] Project root", path=str(project_root))

    # Initialize ingestion pipeline with project root as allowed base path
    # This allows indexing all *.md files in the project
    pipeline = DocumentIngestionPipeline(
        allowed_base_path=project_root,  # Override security boundary
        chunk_size=512,
        chunk_overlap=128,
        use_adaptive_chunking=False,  # Use standard chunking for consistency
    )

    logger.info("[INFO] Indexing all *.md documents in project...")
    logger.info("[INFO] This includes: docs/, src/, tests/, and root directory")

    # Index documents - only *.md files
    try:
        stats = await pipeline.index_documents(
            input_dir=project_root, required_exts=[".md"], batch_size=50  # Only markdown files
        )

        logger.info("=" * 60)
        logger.info("[SUCCESS] Demo data indexing completed!")
        logger.info("=" * 60)
        logger.info(f"[STATS] Documents loaded:      {stats['documents_loaded']}")
        logger.info(f"[STATS] Chunks created:        {stats['chunks_created']}")
        logger.info(f"[STATS] Embeddings generated:  {stats['embeddings_generated']}")
        logger.info(f"[STATS] Points indexed:        {stats['points_indexed']}")
        logger.info(f"[STATS] Duration:              {stats['duration_seconds']}s")
        logger.info(f"[STATS] Avg chunks/document:   {stats['chunks_per_document']}")
        logger.info(f"[STATS] Collection:            {stats['collection_name']}")
        logger.info("=" * 60)

        # Show example queries
        logger.info("[INFO] Try asking the Gradio UI:")
        logger.info("[INFO]    - 'Was ist AEGIS RAG?'")
        logger.info("[INFO]    - 'Erklaere die Memory-Architektur'")
        logger.info("[INFO]    - 'Welche Komponenten hat das System?'")
        logger.info("[INFO]    - 'Was wurde in Sprint 9 implementiert?'")
        logger.info("[INFO]    - 'Wie funktioniert der QueryAgent?'")

        stats["status"] = "success"
        return stats

    except Exception as e:
        logger.error("[ERROR] Demo data indexing failed", error=str(e))
        return {"status": "failed", "error": str(e)}


async def get_collection_stats() -> None:
    """Print current collection statistics."""
    logger.info("[INFO] Fetching current collection stats...")

    pipeline = DocumentIngestionPipeline()
    stats = await pipeline.get_collection_stats()

    if stats:
        logger.info("Current collection status:")
        logger.info(f"  Collection: {stats['collection_name']}")
        logger.info(f"  Points: {stats['points_count']}")
        logger.info(f"  Vectors: {stats['vectors_count']}")
        logger.info(f"  Status: {stats['status']}")
    else:
        logger.info("[WARN] Collection does not exist or is empty")


async def clear_collection() -> None:
    """Clear the collection (delete and recreate)."""
    logger.warning("[WARN] Clearing collection...")

    qdrant = QdrantClientWrapper()

    try:
        # Delete collection
        await qdrant.delete_collection(settings.qdrant_collection)
        logger.info(f"[OK] Collection '{settings.qdrant_collection}' deleted")

        # Recreate collection
        from src.components.vector_search.embeddings import EmbeddingService

        embedding_service = EmbeddingService()

        await qdrant.create_collection(
            collection_name=settings.qdrant_collection,
            vector_size=embedding_service.get_embedding_dimension(),
        )
        logger.info(f"[OK] Collection '{settings.qdrant_collection}' recreated")

    except Exception as e:
        logger.error("[ERROR] Failed to clear collection", error=str(e))


def main():
    """Main entry point with CLI argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup AEGIS RAG demo data by indexing all *.md files"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-indexing even if data exists"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show current collection statistics and exit"
    )
    parser.add_argument(
        "--clear", action="store_true", help="Clear the collection (DELETE all data)"
    )

    args = parser.parse_args()

    # Configure logging
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )

    # Run async function
    if args.stats:
        asyncio.run(get_collection_stats())
    elif args.clear:
        confirm = input("[WARN] This will DELETE all indexed documents. Continue? (yes/no): ")
        if confirm.lower() == "yes":
            asyncio.run(clear_collection())
        else:
            logger.info("[INFO] Aborted")
    else:
        result = asyncio.run(setup_demo_data(force=args.force))

        # Exit code based on result
        if result["status"] == "success":
            sys.exit(0)
        elif result["status"] == "skipped":
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    import logging

    main()
