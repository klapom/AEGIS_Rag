#!/usr/bin/env python3
"""
Neo4j Relation Type Backfill & Orphan Cleanup

Fixes 1021 RELATES_TO relations with NULL relation_type from Sprint 124.

Strategy:
1. Re-type relations WITH descriptions using pattern matching (21 universal types)
2. Delete relations WITHOUT descriptions (no useful info)
3. Delete orphaned entities (no RELATES_TO or MENTIONED_IN relationships)

Usage:
    python scripts/backfill_relation_types.py              # Execute migration
    python scripts/backfill_relation_types.py --dry-run    # Preview changes
"""

import asyncio
import argparse
import re
from typing import Dict, List, Tuple
from neo4j import AsyncGraphDatabase
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Neo4j Connection
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "aegis-rag-neo4j-password"

# Universal Relation Types (21 types from ADR-040)
TYPE_PATTERNS: Dict[str, List[str]] = {
    "LOCATED_IN": [
        r"\blocated in\b", r"\bbased in\b", r"\bheadquartered in\b",
        r"\bsituated in\b", r"\bin the city of\b", r"\bin\b.*\b(city|country|state|region)\b"
    ],
    "WORKS_FOR": [
        r"\bworks for\b", r"\bemployed by\b", r"\bworks at\b",
        r"\bemployee of\b", r"\bstaff at\b", r"\bjob at\b"
    ],
    "PART_OF": [
        r"\bpart of\b", r"\bbelongs to\b", r"\bmember of\b",
        r"\bcomponent of\b", r"\bsubset of\b", r"\bwithin\b"
    ],
    "USES": [
        r"\buses\b", r"\butilizes\b", r"\bemploys\b",
        r"\bleverages\b", r"\brelies on\b", r"\bapplies\b"
    ],
    "CREATES": [
        r"\bcreates\b", r"\bproduces\b", r"\bgenerates\b",
        r"\bbuilds\b", r"\bdevelops\b", r"\bmade\b", r"\bmakes\b"
    ],
    "AUTHORED_BY": [
        r"\bauthored by\b", r"\bwritten by\b", r"\bcreated by\b",
        r"\bdeveloped by\b", r"\bpublished by\b"
    ],
    "MANAGES": [
        r"\bmanages\b", r"\bleads\b", r"\bdirects\b",
        r"\boversees\b", r"\bsupervises\b", r"\bheads\b"
    ],
    "FUNDED_BY": [
        r"\bfunded by\b", r"\bfinanced by\b", r"\bsponsored by\b",
        r"\binvested in by\b", r"\bgrant from\b"
    ],
    "DEPENDS_ON": [
        r"\bdepends on\b", r"\brequires\b", r"\bneeds\b",
        r"\brelies on\b", r"\bcontingent on\b"
    ],
    "CONTAINS": [
        r"\bcontains\b", r"\bincludes\b", r"\bcomprises\b",
        r"\bhas\b", r"\bconsists of\b"
    ],
    "INFLUENCES": [
        r"\binfluences\b", r"\baffects\b", r"\bimpacts\b",
        r"\bshapes\b", r"\bdrives\b", r"\bmotivates\b"
    ],
    "ASSOCIATED_WITH": [
        r"\bassociated with\b", r"\brelated to\b", r"\bconnected to\b",
        r"\blinked to\b", r"\btied to\b"
    ],
    "DERIVED_FROM": [
        r"\bderived from\b", r"\bbased on\b", r"\boriginated from\b",
        r"\bevolved from\b", r"\bstemmed from\b"
    ],
    "COMPETES_WITH": [
        r"\bcompetes with\b", r"\brival of\b", r"\bcompetitor of\b",
        r"\bopposes\b", r"\bvs\b", r"\bagainst\b"
    ],
    "REGULATES": [
        r"\bregulates\b", r"\bgoverns\b", r"\bcontrols\b",
        r"\boversees\b", r"\benforces\b"
    ],
    "SUPPORTS": [
        r"\bsupports\b", r"\bassists\b", r"\bhelps\b",
        r"\baids\b", r"\bfacilitates\b", r"\benables\b"
    ],
    "PRODUCES": [
        r"\bproduces\b", r"\bmanufactures\b", r"\boutputs\b",
        r"\byields\b", r"\bdelivers\b"
    ],
    "TEACHES": [
        r"\bteaches\b", r"\btrains\b", r"\beducates\b",
        r"\binstructs\b", r"\bmentors\b"
    ],
    "PRECEDED_BY": [
        r"\bpreceded by\b", r"\bafter\b", r"\bfollowing\b",
        r"\bsucceeded by\b", r"\blater than\b"
    ],
    "MEASURES": [
        r"\bmeasures\b", r"\bquantifies\b", r"\bevaluates\b",
        r"\bassesses\b", r"\bgauges\b"
    ],
}

# Generic fallback for unmatched descriptions
GENERIC_TYPE = "RELATED_TO"


def infer_relation_type(description: str) -> str:
    """
    Infer relation type from description text using pattern matching.

    Args:
        description: Relation description text

    Returns:
        Inferred relation type (e.g., "LOCATED_IN") or "RELATED_TO" if no match
    """
    if not description:
        return GENERIC_TYPE

    desc_lower = description.lower()

    # Check each type's patterns
    for relation_type, patterns in TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, desc_lower):
                return relation_type

    # No pattern matched
    return GENERIC_TYPE


async def analyze_null_relations(tx) -> Tuple[int, int, int]:
    """
    Count NULL relation_types by description status.

    Returns:
        (total_null, with_desc, without_desc)
    """
    result = await tx.run("""
        MATCH ()-[r:RELATES_TO]->()
        WHERE r.relation_type IS NULL
        RETURN
          count(CASE WHEN r.description IS NOT NULL AND r.description <> '' THEN 1 END) AS with_desc,
          count(CASE WHEN r.description IS NULL OR r.description = '' THEN 1 END) AS without_desc,
          count(*) AS total
    """)
    record = await result.single()
    return record["total"], record["with_desc"], record["without_desc"]


async def fetch_relations_with_descriptions(tx, batch_size: int = 100) -> List[Dict]:
    """
    Fetch batch of NULL-typed relations that have descriptions.

    Returns:
        List of {id: rel_id, description: str}
    """
    result = await tx.run("""
        MATCH ()-[r:RELATES_TO]->()
        WHERE r.relation_type IS NULL
          AND r.description IS NOT NULL
          AND r.description <> ''
        RETURN elementId(r) AS rel_id, r.description AS description
        LIMIT $batch_size
    """, batch_size=batch_size)

    relations = []
    async for record in result:
        relations.append({
            "id": record["rel_id"],
            "description": record["description"]
        })
    return relations


async def update_relation_types(tx, updates: List[Tuple[str, str]]) -> int:
    """
    Update relation_type for given relation IDs.

    Args:
        updates: List of (relation_element_id, new_type) tuples

    Returns:
        Number of relations updated
    """
    if not updates:
        return 0

    result = await tx.run("""
        UNWIND $updates AS update
        MATCH ()-[r:RELATES_TO]->()
        WHERE elementId(r) = update.id
        SET r.relation_type = update.type
        RETURN count(r) AS updated
    """, updates=[{"id": rel_id, "type": new_type} for rel_id, new_type in updates])

    record = await result.single()
    return record["updated"]


async def delete_null_relations_without_desc(tx) -> int:
    """
    Delete relations with NULL relation_type and no description.

    Returns:
        Number of relations deleted
    """
    result = await tx.run("""
        MATCH ()-[r:RELATES_TO]->()
        WHERE r.relation_type IS NULL
          AND (r.description IS NULL OR r.description = '')
        DELETE r
        RETURN count(r) AS deleted
    """)
    record = await result.single()
    return record["deleted"]


async def delete_orphaned_entities(tx) -> int:
    """
    Delete entities with NO RELATES_TO or MENTIONED_IN relationships.

    Returns:
        Number of entities deleted
    """
    result = await tx.run("""
        MATCH (e:base)
        WHERE NOT (e)-[:RELATES_TO]-()
          AND NOT (e)-[:MENTIONED_IN]->()
        DELETE e
        RETURN count(e) AS deleted
    """)
    record = await result.single()
    return record["deleted"]


async def backfill_relation_types(dry_run: bool = False):
    """
    Main migration function: backfill NULL relation types and clean up orphans.

    Args:
        dry_run: If True, only report what would be done without making changes
    """
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        async with driver.session() as session:
            # Step 0: Analyze current state
            logger.info("=" * 60)
            logger.info("STEP 0: Analyzing current state...")
            logger.info("=" * 60)

            total_null, with_desc, without_desc = await session.execute_read(analyze_null_relations)
            logger.info(f"NULL relation_type analysis:")
            logger.info(f"  Total NULL relations: {total_null}")
            logger.info(f"  With descriptions: {with_desc}")
            logger.info(f"  Without descriptions: {without_desc}")

            if total_null == 0:
                logger.info("✅ No NULL relation_types found. Migration not needed.")
                return

            # Step A: Re-type relations WITH descriptions
            logger.info("\n" + "=" * 60)
            logger.info("STEP A: Re-typing relations with descriptions...")
            logger.info("=" * 60)

            # Fetch ALL relations with descriptions at once (faster than batching)
            logger.info("Fetching all NULL-typed relations with descriptions...")
            result = await session.run("""
                MATCH ()-[r:RELATES_TO]->()
                WHERE r.relation_type IS NULL
                  AND r.description IS NOT NULL
                  AND r.description <> ''
                RETURN elementId(r) AS rel_id, r.description AS description
            """)

            relations = []
            async for record in result:
                relations.append({
                    "id": record["rel_id"],
                    "description": record["description"]
                })

            logger.info(f"Found {len(relations)} relations to re-type")

            # Infer types for all relations
            updates = []
            type_distribution = {}
            for rel in relations:
                inferred_type = infer_relation_type(rel["description"])
                updates.append((rel["id"], inferred_type))
                type_distribution[inferred_type] = type_distribution.get(inferred_type, 0) + 1

            # Update database (or skip if dry-run)
            if not dry_run and updates:
                logger.info(f"Updating {len(updates)} relations...")
                # Process in batches of 500 for safer transaction sizes
                batch_size = 500
                total_updated = 0
                for i in range(0, len(updates), batch_size):
                    batch = updates[i:i+batch_size]
                    updated = await session.execute_write(update_relation_types, batch)
                    total_updated += updated
                    logger.info(f"  Batch {i//batch_size + 1}/{(len(updates)-1)//batch_size + 1}: {updated} relations updated")

                logger.info(f"Re-typed {total_updated} relations")
            else:
                logger.info(f"[DRY-RUN] Would re-type {len(updates)} relations")

            logger.info("\nType distribution:")
            for rel_type, count in sorted(type_distribution.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {rel_type}: {count}")

            # Step B: Delete relations WITHOUT descriptions
            logger.info("\n" + "=" * 60)
            logger.info("STEP B: Deleting relations without descriptions...")
            logger.info("=" * 60)

            if not dry_run:
                deleted_rels = await session.execute_write(delete_null_relations_without_desc)
                logger.info(f"Deleted {deleted_rels} relations without descriptions")
            else:
                logger.info(f"[DRY-RUN] Would delete {without_desc} relations without descriptions")

            # Step C: Delete orphaned entities
            logger.info("\n" + "=" * 60)
            logger.info("STEP C: Deleting orphaned entities...")
            logger.info("=" * 60)

            if not dry_run:
                deleted_entities = await session.execute_write(delete_orphaned_entities)
                logger.info(f"Deleted {deleted_entities} orphaned entities")
            else:
                # Count orphans for dry-run report
                result = await session.run("""
                    MATCH (e:base)
                    WHERE NOT (e)-[:RELATES_TO]-()
                      AND NOT (e)-[:MENTIONED_IN]->()
                    RETURN count(e) AS orphan_count
                """)
                record = await result.single()
                logger.info(f"[DRY-RUN] Would delete {record['orphan_count']} orphaned entities")

            # Final summary
            logger.info("\n" + "=" * 60)
            logger.info("MIGRATION COMPLETE" if not dry_run else "DRY-RUN COMPLETE")
            logger.info("=" * 60)

            if not dry_run:
                # Verify all NULL relation_types are gone
                total_null_after, _, _ = await session.execute_read(analyze_null_relations)
                logger.info(f"NULL relation_types remaining: {total_null_after}")
                if total_null_after == 0:
                    logger.info("✅ All NULL relation_types successfully backfilled!")
                else:
                    logger.warning(f"⚠️ {total_null_after} NULL relation_types remain (may need re-run)")

    finally:
        await driver.close()


async def main():
    parser = argparse.ArgumentParser(
        description="Backfill NULL relation_types and clean up orphaned data in Neo4j",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes without modifying database
  python scripts/backfill_relation_types.py --dry-run

  # Execute migration
  python scripts/backfill_relation_types.py
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying database"
    )

    args = parser.parse_args()

    if args.dry_run:
        logger.info("🔍 Running in DRY-RUN mode (no changes will be made)")
    else:
        logger.info("🚀 Running migration (database will be modified)")

    await backfill_relation_types(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
