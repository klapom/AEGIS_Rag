#!/usr/bin/env python3
"""Graphiti Memory Consolidation Script - Sprint 68 Feature 68.3.

This script consolidates episodic memory in Graphiti by:
1. Merging duplicate entities and relationships
2. Removing episodic facts older than TTL (default: 30 days)
3. Compacting the temporal graph to reduce memory footprint
4. Optimizing Neo4j indexes for memory queries

Usage:
    # Consolidate all memory (remove facts older than 30 days)
    python scripts/consolidate_graphiti_memory.py

    # Custom TTL in days
    python scripts/consolidate_graphiti_memory.py --ttl-days 60

    # Dry run (show what would be deleted without deleting)
    python scripts/consolidate_graphiti_memory.py --dry-run

    # Force consolidation (skip confirmation)
    python scripts/consolidate_graphiti_memory.py --force

Schedule:
    Run weekly via cron for optimal memory management:
    0 2 * * 0 /path/to/venv/bin/python /path/to/scripts/consolidate_graphiti_memory.py
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.graph_rag.neo4j_client import get_neo4j_client  # noqa: E402

logger = structlog.get_logger(__name__)


async def consolidate_memory(ttl_days: int, dry_run: bool = False, force: bool = False) -> None:
    """Consolidate Graphiti episodic memory.

    Args:
        ttl_days: Time-to-live in days for episodic facts
        dry_run: If True, show what would be deleted without deleting
        force: If True, skip confirmation prompt
    """
    logger.info(
        "graphiti_consolidation_start",
        ttl_days=ttl_days,
        dry_run=dry_run,
        force=force,
    )

    # Calculate cutoff timestamp
    cutoff_date = datetime.now(UTC) - timedelta(days=ttl_days)
    cutoff_timestamp = int(cutoff_date.timestamp())

    logger.info(
        "graphiti_consolidation_cutoff",
        cutoff_date=cutoff_date.isoformat(),
        cutoff_timestamp=cutoff_timestamp,
    )

    # Connect to Neo4j
    neo4j_client = get_neo4j_client()

    try:
        # Step 1: Count episodic facts older than TTL
        count_query = """
        MATCH (e:Episode)
        WHERE e.timestamp < $cutoff_timestamp
        RETURN count(e) as old_episodes
        """

        result = await neo4j_client.execute_read(count_query, {"cutoff_timestamp": cutoff_timestamp})
        old_episodes_count = result[0]["old_episodes"] if result else 0

        logger.info("graphiti_old_episodes_found", count=old_episodes_count)

        if old_episodes_count == 0:
            logger.info("graphiti_consolidation_nothing_to_do")
            return

        # Prompt for confirmation (unless force or dry_run)
        if not force and not dry_run:
            response = input(
                f"\nWARNING: This will delete {old_episodes_count} episodes older than {ttl_days} days.\n"
                f"Cutoff date: {cutoff_date.isoformat()}\n"
                f"Continue? [y/N]: "
            )
            if response.lower() != "y":
                logger.info("graphiti_consolidation_cancelled")
                return

        if dry_run:
            # Dry run: Show what would be deleted
            logger.info(
                "graphiti_consolidation_dry_run",
                episodes_to_delete=old_episodes_count,
                cutoff_date=cutoff_date.isoformat(),
            )
            print(f"\nDRY RUN: Would delete {old_episodes_count} episodes older than {ttl_days} days")
            print(f"Cutoff date: {cutoff_date.isoformat()}")
            return

        # Step 2: Delete old episodes (cascade to relationships)
        delete_query = """
        MATCH (e:Episode)
        WHERE e.timestamp < $cutoff_timestamp
        DETACH DELETE e
        RETURN count(*) as deleted
        """

        logger.info("graphiti_deleting_old_episodes", count=old_episodes_count)
        result = await neo4j_client.execute_write(delete_query, {"cutoff_timestamp": cutoff_timestamp})
        deleted_count = result[0]["deleted"] if result else 0

        logger.info("graphiti_old_episodes_deleted", count=deleted_count)

        # Step 3: Find and merge duplicate entities (same name, same type)
        merge_duplicates_query = """
        MATCH (e1:Entity), (e2:Entity)
        WHERE e1.name = e2.name
          AND e1.type = e2.type
          AND id(e1) < id(e2)
        WITH e1, e2
        CALL apoc.refactor.mergeNodes([e1, e2], {
          properties: 'combine',
          mergeRels: true
        })
        YIELD node
        RETURN count(node) as merged
        """

        try:
            result = await neo4j_client.execute_write(merge_duplicates_query, {})
            merged_count = result[0]["merged"] if result else 0
            logger.info("graphiti_entities_merged", count=merged_count)
        except Exception as e:
            # APOC might not be available, skip merge
            logger.warning("graphiti_merge_skipped", error=str(e), note="APOC plugin required")

        # Step 4: Delete orphaned entities (no relationships)
        delete_orphans_query = """
        MATCH (e:Entity)
        WHERE NOT (e)-[]-()
        DELETE e
        RETURN count(*) as deleted
        """

        result = await neo4j_client.execute_write(delete_orphans_query, {})
        orphans_deleted = result[0]["deleted"] if result else 0
        logger.info("graphiti_orphaned_entities_deleted", count=orphans_deleted)

        # Step 5: Optimize Neo4j indexes
        logger.info("graphiti_optimizing_indexes")

        # Rebuild Episode timestamp index
        optimize_queries = [
            "DROP INDEX episode_timestamp_index IF EXISTS",
            "CREATE INDEX episode_timestamp_index FOR (e:Episode) ON (e.timestamp)",
            # Entity name index
            "DROP INDEX entity_name_index IF EXISTS",
            "CREATE INDEX entity_name_index FOR (e:Entity) ON (e.name)",
        ]

        for query in optimize_queries:
            try:
                await neo4j_client.execute_write(query, {})
            except Exception as e:
                logger.warning("graphiti_index_optimization_failed", query=query[:50], error=str(e))

        logger.info("graphiti_indexes_optimized")

        # Step 6: Summary
        logger.info(
            "graphiti_consolidation_complete",
            episodes_deleted=deleted_count,
            entities_merged=merged_count,
            orphans_deleted=orphans_deleted,
            ttl_days=ttl_days,
        )

        print("\nGraphiti Memory Consolidation Complete:")
        print(f"  Episodes deleted: {deleted_count}")
        print(f"  Entities merged: {merged_count}")
        print(f"  Orphans deleted: {orphans_deleted}")
        print(f"  TTL: {ttl_days} days")

    except Exception as e:
        logger.error("graphiti_consolidation_failed", error=str(e), exc_info=True)
        raise
    finally:
        await neo4j_client.close()


async def get_memory_stats() -> dict:
    """Get current Graphiti memory statistics.

    Returns:
        Dictionary with episode count, entity count, relationship count, memory size
    """
    neo4j_client = get_neo4j_client()

    try:
        stats_query = """
        MATCH (e:Episode)
        WITH count(e) as episode_count
        MATCH (ent:Entity)
        WITH episode_count, count(ent) as entity_count
        MATCH ()-[r]->()
        RETURN episode_count, entity_count, count(r) as relationship_count
        """

        result = await neo4j_client.execute_read(stats_query, {})

        if not result:
            return {
                "episode_count": 0,
                "entity_count": 0,
                "relationship_count": 0,
                "memory_size_mb": 0.0,
            }

        stats = result[0]

        # Estimate memory size (rough approximation)
        # Each episode ~1KB, each entity ~500B, each relationship ~300B
        memory_size_mb = (
            stats["episode_count"] * 1.0
            + stats["entity_count"] * 0.5
            + stats["relationship_count"] * 0.3
        ) / 1024

        return {
            "episode_count": stats["episode_count"],
            "entity_count": stats["entity_count"],
            "relationship_count": stats["relationship_count"],
            "memory_size_mb": round(memory_size_mb, 2),
        }

    except Exception as e:
        logger.error("graphiti_stats_failed", error=str(e))
        return {
            "episode_count": 0,
            "entity_count": 0,
            "relationship_count": 0,
            "memory_size_mb": 0.0,
        }
    finally:
        await neo4j_client.close()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Consolidate Graphiti episodic memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--ttl-days",
        type=int,
        default=30,
        help="Time-to-live in days for episodic facts (default: 30)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without deleting",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show memory statistics and exit",
    )

    args = parser.parse_args()

    # Show stats
    if args.stats:
        print("\nGraphiti Memory Statistics:")
        print("-" * 50)
        stats = await get_memory_stats()
        print(f"  Episodes: {stats['episode_count']:,}")
        print(f"  Entities: {stats['entity_count']:,}")
        print(f"  Relationships: {stats['relationship_count']:,}")
        print(f"  Estimated Size: {stats['memory_size_mb']:.2f} MB")
        print()
        return

    # Run consolidation
    await consolidate_memory(
        ttl_days=args.ttl_days,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    asyncio.run(main())
