#!/usr/bin/env python
"""Sprint 34: Re-index Knowledge Graph with RELATES_TO Relationships.

This script clears the Neo4j graph and re-indexes all documents using
the updated pipeline that extracts RELATES_TO relationships.

Usage:
    poetry run python scripts/reindex_knowledge_graph.py --source-dir data/sample_documents
    poetry run python scripts/reindex_knowledge_graph.py --clear-only  # Just clear, don't re-index
    poetry run python scripts/reindex_knowledge_graph.py --dry-run     # Show what would be done
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

logger = structlog.get_logger(__name__)


async def clear_neo4j_graph(dry_run: bool = False) -> dict:
    """Clear all nodes and relationships from Neo4j.

    Returns:
        Statistics about what was deleted
    """
    from src.components.graph_rag.neo4j_client import get_neo4j_client

    client = get_neo4j_client()

    if dry_run:
        # Count what would be deleted
        count_query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]-()
        RETURN count(DISTINCT n) AS nodes, count(DISTINCT r) AS relationships
        """
        result = await client.execute_query(count_query)
        stats = result[0] if result else {"nodes": 0, "relationships": 0}
        logger.info("dry_run_would_delete", nodes=stats["nodes"], relationships=stats["relationships"])
        return {"nodes_deleted": 0, "relationships_deleted": 0, "dry_run": True, **stats}

    # Get counts before deletion
    count_result = await client.execute_query(
        "MATCH (n) OPTIONAL MATCH (n)-[r]-() RETURN count(DISTINCT n) AS nodes, count(DISTINCT r) AS rels"
    )
    before_stats = count_result[0] if count_result else {"nodes": 0, "rels": 0}

    # Delete all relationships first
    await client.execute_write("MATCH ()-[r]->() DELETE r")

    # Delete all nodes
    await client.execute_write("MATCH (n) DELETE n")

    logger.info(
        "neo4j_graph_cleared",
        nodes_deleted=before_stats["nodes"],
        relationships_deleted=before_stats["rels"],
    )

    return {
        "nodes_deleted": before_stats["nodes"],
        "relationships_deleted": before_stats["rels"],
    }


async def clear_qdrant_collection(dry_run: bool = False) -> dict:
    """Clear the Qdrant vector collection.

    Returns:
        Statistics about what was deleted
    """
    from src.components.vector_search.qdrant_client import get_qdrant_client
    from src.core.config import settings

    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    try:
        # Get current point count
        info = await client.get_collection_info(collection_name)
        points_count = info.get("points_count", 0) if info else 0

        if dry_run:
            logger.info("dry_run_would_delete_qdrant", collection=collection_name, points=points_count)
            return {"points_deleted": 0, "dry_run": True, "would_delete": points_count}

        # Delete and recreate collection
        await client.delete_collection(collection_name)
        await client.create_collection(collection_name, vector_size=1024)  # BGE-M3 dimension

        logger.info("qdrant_collection_cleared", collection=collection_name, points_deleted=points_count)
        return {"points_deleted": points_count}

    except Exception as e:
        logger.warning("qdrant_clear_failed", error=str(e))
        return {"points_deleted": 0, "error": str(e)}


async def reindex_documents(source_dir: Path, batch_size: int = 5) -> dict:
    """Re-index all documents from source directory.

    Args:
        source_dir: Directory containing documents to index
        batch_size: Number of documents to process in parallel

    Returns:
        Indexing statistics
    """
    import uuid
    from datetime import datetime

    from src.components.ingestion.langgraph_pipeline import run_ingestion_pipeline

    # Find all supported documents
    supported_extensions = {".pdf", ".pptx", ".docx", ".txt", ".md"}
    documents = []

    for ext in supported_extensions:
        documents.extend(source_dir.rglob(f"*{ext}"))

    # Filter out unsupported legacy formats
    legacy_extensions = {".doc", ".ppt", ".xls"}
    documents = [d for d in documents if d.suffix.lower() not in legacy_extensions]

    logger.info("found_documents", count=len(documents), source_dir=str(source_dir))

    if not documents:
        return {"documents_indexed": 0, "error": "No documents found"}

    stats = {
        "documents_indexed": 0,
        "documents_failed": 0,
        "total_chunks": 0,
        "total_entities": 0,
        "total_relations": 0,
        "errors": [],
    }

    batch_id = f"reindex_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    for i, doc_path in enumerate(documents):
        document_id = f"reindex_{uuid.uuid4().hex[:8]}"

        logger.info(
            "indexing_document",
            index=i + 1,
            total=len(documents),
            file=doc_path.name,
            document_id=document_id,
        )

        try:
            result = await run_ingestion_pipeline(
                document_path=str(doc_path),
                document_id=document_id,
                batch_id=batch_id,
                batch_index=i,
                total_documents=len(documents),
            )

            if isinstance(result, dict):
                stats["documents_indexed"] += 1
                stats["total_chunks"] += result.get("chunks_created", 0)
                stats["total_entities"] += result.get("entities_count", 0)
                stats["total_relations"] += result.get("relations_count", 0)
            else:
                stats["documents_indexed"] += 1

        except Exception as e:
            stats["documents_failed"] += 1
            stats["errors"].append({"file": doc_path.name, "error": str(e)})
            logger.error("document_indexing_failed", file=doc_path.name, error=str(e))

    return stats


async def main():
    parser = argparse.ArgumentParser(description="Re-index Knowledge Graph with RELATES_TO")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("data/sample_documents"),
        help="Directory containing documents to index",
    )
    parser.add_argument(
        "--clear-only",
        action="store_true",
        help="Only clear the graph, don't re-index",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--skip-qdrant",
        action="store_true",
        help="Skip clearing Qdrant (only clear Neo4j)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of documents to process in parallel",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("SPRINT 34: RE-INDEX KNOWLEDGE GRAPH WITH RELATES_TO")
    print("=" * 70)

    if args.dry_run:
        print("[DRY RUN] No changes will be made\n")

    # Step 1: Clear Neo4j
    print("\n[1/3] Clearing Neo4j graph...")
    neo4j_stats = await clear_neo4j_graph(dry_run=args.dry_run)
    print(f"  Nodes: {neo4j_stats.get('nodes_deleted', 0)} deleted")
    print(f"  Relationships: {neo4j_stats.get('relationships_deleted', 0)} deleted")

    # Step 2: Clear Qdrant (optional)
    if not args.skip_qdrant:
        print("\n[2/3] Clearing Qdrant collection...")
        qdrant_stats = await clear_qdrant_collection(dry_run=args.dry_run)
        print(f"  Points: {qdrant_stats.get('points_deleted', 0)} deleted")
    else:
        print("\n[2/3] Skipping Qdrant (--skip-qdrant)")

    # Step 3: Re-index (unless clear-only)
    if args.clear_only:
        print("\n[3/3] Skipping re-indexing (--clear-only)")
    elif args.dry_run:
        print(f"\n[3/3] Would re-index documents from: {args.source_dir}")
    else:
        print(f"\n[3/3] Re-indexing documents from: {args.source_dir}")
        index_stats = await reindex_documents(args.source_dir, batch_size=args.batch_size)
        print(f"  Documents indexed: {index_stats['documents_indexed']}")
        print(f"  Documents failed: {index_stats['documents_failed']}")
        print(f"  Total chunks: {index_stats['total_chunks']}")
        print(f"  Total entities: {index_stats['total_entities']}")
        print(f"  Total relations: {index_stats['total_relations']}")

        if index_stats["errors"]:
            print("\n  Errors:")
            for err in index_stats["errors"][:5]:
                print(f"    - {err['file']}: {err['error'][:50]}...")

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
