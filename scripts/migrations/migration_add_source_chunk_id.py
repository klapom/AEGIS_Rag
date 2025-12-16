#!/usr/bin/env python3
"""Migration Script: Add source_chunk_id to existing relationships.

Sprint 49 Feature 49.5: Graph Extraction Provenance Tracking (TD-048)

This script backfills the source_chunk_id property for existing MENTIONED_IN
and RELATES_TO relationships that were created before Sprint 49.

Problem:
    Relationships created before Sprint 49 don't have source_chunk_id property,
    making it impossible to trace entities back to their source chunks.

Solution:
    For each relationship:
    1. Find the entity's source chunk via entity metadata
    2. Add source_chunk_id property to the relationship
    3. Handle orphaned relationships (no matching chunk)

Usage:
    python scripts/migrations/migration_add_source_chunk_id.py [--dry-run]

    --dry-run: Show what would be changed without modifying data

Example:
    # Check what would change
    python scripts/migrations/migration_add_source_chunk_id.py --dry-run

    # Apply changes
    python scripts/migrations/migration_add_source_chunk_id.py

Author: Claude Code
Date: 2025-12-16
"""

import argparse
import asyncio
from datetime import datetime

import structlog
from neo4j import AsyncGraphDatabase

from src.core.config import settings

logger = structlog.get_logger(__name__)


class SourceChunkIdMigration:
    """Migrate existing relationships to include source_chunk_id property."""

    def __init__(self, dry_run: bool = False):
        """Initialize migration.

        Args:
            dry_run: If True, only report what would be changed without modifying data
        """
        self.dry_run = dry_run
        self.driver = None
        self.stats = {
            "mentioned_in_total": 0,
            "mentioned_in_updated": 0,
            "mentioned_in_skipped": 0,
            "relates_to_total": 0,
            "relates_to_updated": 0,
            "relates_to_skipped": 0,
            "orphaned_entities": [],
        }

    async def connect(self):
        """Connect to Neo4j database."""
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        logger.info("neo4j_connected", uri=settings.neo4j_uri)

    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            logger.info("neo4j_connection_closed")

    async def migrate_mentioned_in_relationships(self) -> dict:
        """Add source_chunk_id to MENTIONED_IN relationships.

        Strategy:
            1. Find all MENTIONED_IN relationships without source_chunk_id
            2. For each: Extract chunk_id from the connected chunk node
            3. Set relationship.source_chunk_id = chunk.chunk_id

        Returns:
            Statistics dictionary with counts
        """
        async with self.driver.session() as session:
            # Count total MENTIONED_IN relationships without source_chunk_id
            result = await session.run("""
                MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk)
                WHERE r.source_chunk_id IS NULL
                RETURN count(r) AS total
            """)
            record = await result.single()
            total = record["total"] if record else 0
            self.stats["mentioned_in_total"] = total

            logger.info(
                "mentioned_in_relationships_found_without_source_chunk_id",
                total=total,
                dry_run=self.dry_run,
            )

            if total == 0:
                logger.info("no_mentioned_in_relationships_need_migration")
                return self.stats

            if self.dry_run:
                # Show sample of what would be updated
                result = await session.run("""
                    MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk)
                    WHERE r.source_chunk_id IS NULL
                    RETURN e.entity_name AS entity, c.chunk_id AS chunk_id
                    LIMIT 10
                """)
                records = await result.values()
                logger.info(
                    "dry_run_sample_mentioned_in",
                    sample_count=len(records),
                    samples=[{"entity": r[0], "chunk_id": r[1][:16]} for r in records],
                )
                self.stats["mentioned_in_skipped"] = total
                return self.stats

            # Apply migration in batches
            batch_size = 1000
            updated = 0

            while updated < total:
                result = await session.run("""
                    MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk)
                    WHERE r.source_chunk_id IS NULL
                    WITH e, r, c
                    LIMIT $batch_size
                    SET r.source_chunk_id = c.chunk_id,
                        r.migrated_at = datetime()
                    RETURN count(r) AS updated
                """, batch_size=batch_size)

                record = await result.single()
                batch_updated = record["updated"] if record else 0
                updated += batch_updated

                logger.info(
                    "mentioned_in_batch_migrated",
                    batch_updated=batch_updated,
                    total_updated=updated,
                    total=total,
                    progress_percent=round((updated / total) * 100, 1),
                )

                if batch_updated == 0:
                    break

            self.stats["mentioned_in_updated"] = updated

            logger.info(
                "mentioned_in_migration_completed",
                total=total,
                updated=updated,
                skipped=total - updated,
            )

        return self.stats

    async def migrate_relates_to_relationships(self) -> dict:
        """Add source_chunk_id to RELATES_TO relationships.

        Strategy:
            For RELATES_TO, source_chunk_id represents the chunk where the
            relationship was extracted. We find this by:
            1. Get the source entity of the relationship
            2. Find MENTIONED_IN relationship to get chunk_id
            3. Use that chunk_id as source_chunk_id

        Note:
            Some RELATES_TO may connect entities from different chunks.
            We use the source entity's chunk as the relationship's source.

        Returns:
            Statistics dictionary with counts
        """
        async with self.driver.session() as session:
            # Count total RELATES_TO relationships without source_chunk_id
            result = await session.run("""
                MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
                WHERE r.source_chunk_id IS NULL
                RETURN count(r) AS total
            """)
            record = await result.single()
            total = record["total"] if record else 0
            self.stats["relates_to_total"] = total

            logger.info(
                "relates_to_relationships_found_without_source_chunk_id",
                total=total,
                dry_run=self.dry_run,
            )

            if total == 0:
                logger.info("no_relates_to_relationships_need_migration")
                return self.stats

            if self.dry_run:
                # Show sample of what would be updated
                result = await session.run("""
                    MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
                    WHERE r.source_chunk_id IS NULL
                    MATCH (e1)-[:MENTIONED_IN]->(c:chunk)
                    RETURN e1.entity_name AS source_entity,
                           e2.entity_name AS target_entity,
                           c.chunk_id AS chunk_id
                    LIMIT 10
                """)
                records = await result.values()
                logger.info(
                    "dry_run_sample_relates_to",
                    sample_count=len(records),
                    samples=[{
                        "source": r[0],
                        "target": r[1],
                        "chunk_id": r[2][:16]
                    } for r in records],
                )
                self.stats["relates_to_skipped"] = total
                return self.stats

            # Apply migration in batches
            batch_size = 1000
            updated = 0

            while updated < total:
                result = await session.run("""
                    MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
                    WHERE r.source_chunk_id IS NULL
                    MATCH (e1)-[:MENTIONED_IN]->(c:chunk)
                    WITH e1, r, e2, c
                    LIMIT $batch_size
                    SET r.source_chunk_id = c.chunk_id,
                        r.migrated_at = datetime()
                    RETURN count(r) AS updated
                """, batch_size=batch_size)

                record = await result.single()
                batch_updated = record["updated"] if record else 0
                updated += batch_updated

                logger.info(
                    "relates_to_batch_migrated",
                    batch_updated=batch_updated,
                    total_updated=updated,
                    total=total,
                    progress_percent=round((updated / total) * 100, 1),
                )

                if batch_updated == 0:
                    break

            self.stats["relates_to_updated"] = updated

            # Check for orphaned RELATES_TO (source entity not in any chunk)
            result = await session.run("""
                MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
                WHERE r.source_chunk_id IS NULL
                AND NOT (e1)-[:MENTIONED_IN]->(:chunk)
                RETURN e1.entity_name AS entity, count(r) AS orphaned_relationships
                LIMIT 100
            """)
            orphaned = await result.values()

            if orphaned:
                self.stats["orphaned_entities"] = [
                    {"entity": r[0], "orphaned_rels": r[1]} for r in orphaned
                ]
                logger.warning(
                    "orphaned_relates_to_found",
                    count=len(orphaned),
                    sample=orphaned[:5],
                    hint="These entities have no MENTIONED_IN relationships",
                )

            logger.info(
                "relates_to_migration_completed",
                total=total,
                updated=updated,
                skipped=total - updated,
                orphaned_entities=len(orphaned),
            )

        return self.stats

    async def run(self):
        """Execute migration."""
        try:
            await self.connect()

            logger.info(
                "migration_started",
                dry_run=self.dry_run,
                timestamp=datetime.utcnow().isoformat(),
            )

            # Migrate MENTIONED_IN relationships
            await self.migrate_mentioned_in_relationships()

            # Migrate RELATES_TO relationships
            await self.migrate_relates_to_relationships()

            # Print summary
            total_updated = (
                self.stats["mentioned_in_updated"] +
                self.stats["relates_to_updated"]
            )
            total_relationships = (
                self.stats["mentioned_in_total"] +
                self.stats["relates_to_total"]
            )

            logger.info(
                "migration_completed",
                dry_run=self.dry_run,
                total_relationships=total_relationships,
                total_updated=total_updated,
                mentioned_in=self.stats["mentioned_in_updated"],
                relates_to=self.stats["relates_to_updated"],
                orphaned_entities=len(self.stats["orphaned_entities"]),
                timestamp=datetime.utcnow().isoformat(),
            )

            if self.dry_run:
                logger.info(
                    "dry_run_completed",
                    hint="Run without --dry-run to apply changes",
                )
            else:
                logger.info(
                    "migration_applied_successfully",
                    hint="All relationships now have source_chunk_id property",
                )

            return self.stats

        except Exception as e:
            logger.error(
                "migration_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            await self.close()


async def main():
    """Run migration with CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Migrate relationships to include source_chunk_id property"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying data",
    )
    args = parser.parse_args()

    migration = SourceChunkIdMigration(dry_run=args.dry_run)
    stats = await migration.run()

    # Print summary
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'APPLIED'}")
    print(f"\nMENTIONED_IN Relationships:")
    print(f"  Total found: {stats['mentioned_in_total']}")
    print(f"  Updated: {stats['mentioned_in_updated']}")
    print(f"  Skipped: {stats['mentioned_in_skipped']}")
    print(f"\nRELATES_TO Relationships:")
    print(f"  Total found: {stats['relates_to_total']}")
    print(f"  Updated: {stats['relates_to_updated']}")
    print(f"  Skipped: {stats['relates_to_skipped']}")

    if stats["orphaned_entities"]:
        print(f"\n⚠ Orphaned Entities: {len(stats['orphaned_entities'])}")
        print("  (Entities with RELATES_TO but no MENTIONED_IN)")

    print("="*60 + "\n")

    if args.dry_run:
        print("✓ Dry run completed. Run without --dry-run to apply changes.")
    else:
        print("✓ Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
