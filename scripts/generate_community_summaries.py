#!/usr/bin/env python3
"""Generate community summaries for all communities in a namespace.

Sprint 77 Feature 77.4 (TD-094): Community Summarization Batch Job

This script generates LLM-powered summaries for all communities detected
by graph extraction, enabling Graph-Global search mode.

Usage:
    # Regenerate all summaries (92 communities @ ~30s each = ~45min)
    poetry run python scripts/generate_community_summaries.py

    # Dry run (count communities only)
    poetry run python scripts/generate_community_summaries.py --dry-run

    # With custom batch size
    poetry run python scripts/generate_community_summaries.py --batch-size 5

    # Namespace-specific
    poetry run python scripts/generate_community_summaries.py --namespace hotpotqa_large

Example Output:
    ================================================================================
    Sprint 77 Community Summarization Batch Job
    ================================================================================

    1. Querying Neo4j for communities...
       ✓ Found 92 communities to summarize

    2. Generating summaries (batch size: 10)...
       [====================================] 92/92 (100%)
       ✓ Generated 92 summaries in 45min 23s

    3. Summary Statistics:
       Total communities: 92
       Summaries generated: 92
       Failed: 0
       Avg time per summary: 29.5s
       Total cost: $0.23 USD
"""

import argparse
import asyncio
import time
from datetime import timedelta

import structlog

from src.components.graph_rag.community_summarizer import get_community_summarizer
from src.components.graph_rag.neo4j_client import get_neo4j_client

logger = structlog.get_logger(__name__)


async def get_communities_without_summaries(namespace_id: str | None = None) -> list[int]:
    """Get all communities that don't have summaries yet.

    Args:
        namespace_id: Filter by namespace (optional)

    Returns:
        List of community IDs (integers)
    """
    neo4j = get_neo4j_client()

    # Query for communities WITHOUT summaries
    if namespace_id:
        cypher = """
        MATCH (e:base)
        WHERE e.community_id IS NOT NULL
          AND e.namespace = $namespace
        WITH DISTINCT e.community_id AS community_id
        WHERE NOT EXISTS {
            MATCH (cs:CommunitySummary {community_id: community_id})
        }
        RETURN community_id
        ORDER BY community_id
        """
        results = await neo4j.execute_read(cypher, {"namespace": namespace_id})
    else:
        cypher = """
        MATCH (e:base)
        WHERE e.community_id IS NOT NULL
        WITH DISTINCT e.community_id AS community_id
        WHERE NOT EXISTS {
            MATCH (cs:CommunitySummary {community_id: community_id})
        }
        RETURN community_id
        ORDER BY community_id
        """
        results = await neo4j.execute_read(cypher)

    community_ids = []
    for record in results:
        community_id_str = record.get("community_id")
        if community_id_str:
            # Parse "community_5" → 5
            try:
                community_id = int(community_id_str.split("_")[-1])
                community_ids.append(community_id)
            except (ValueError, IndexError):
                logger.warning("invalid_community_id_format_skipped", community_id=community_id_str)

    return community_ids


async def get_all_communities(namespace_id: str | None = None) -> list[int]:
    """Get all communities (with or without summaries).

    Args:
        namespace_id: Filter by namespace (optional)

    Returns:
        List of community IDs (integers)
    """
    neo4j = get_neo4j_client()

    if namespace_id:
        cypher = """
        MATCH (e:base)
        WHERE e.community_id IS NOT NULL
          AND e.namespace = $namespace
        RETURN DISTINCT e.community_id AS community_id
        ORDER BY community_id
        """
        results = await neo4j.execute_read(cypher, {"namespace": namespace_id})
    else:
        cypher = """
        MATCH (e:base)
        WHERE e.community_id IS NOT NULL
        RETURN DISTINCT e.community_id AS community_id
        ORDER BY community_id
        """
        results = await neo4j.execute_read(cypher)

    community_ids = []
    for record in results:
        community_id_str = record.get("community_id")
        if community_id_str:
            # Parse "community_5" → 5
            try:
                community_id = int(community_id_str.split("_")[-1])
                community_ids.append(community_id)
            except (ValueError, IndexError):
                logger.warning("invalid_community_id_format_skipped", community_id=community_id_str)

    return community_ids


async def generate_summaries_batch(
    community_ids: list[int],
    batch_size: int = 10,
    dry_run: bool = False,
) -> dict:
    """Generate summaries for communities in batches.

    Args:
        community_ids: List of community IDs to summarize
        batch_size: Number of communities to process concurrently
        dry_run: If True, only count communities without generating

    Returns:
        Statistics dictionary with counts and timing
    """
    summarizer = get_community_summarizer()

    stats = {
        "total_communities": len(community_ids),
        "summaries_generated": 0,
        "failed": 0,
        "total_time_s": 0,
        "avg_time_per_summary_s": 0,
    }

    if dry_run:
        print(f"\n✓ Dry run: Would generate {len(community_ids)} summaries")
        return stats

    if not community_ids:
        print("\n✓ No communities to summarize")
        return stats

    start_time = time.time()
    failed_communities = []

    print(f"\n2. Generating summaries (batch size: {batch_size})...")
    print(f"   Total communities: {len(community_ids)}")
    print()

    # Process in batches to avoid overwhelming the LLM
    for i in range(0, len(community_ids), batch_size):
        batch = community_ids[i : i + batch_size]
        batch_start = time.time()

        print(f"   Batch {i // batch_size + 1}/{(len(community_ids) + batch_size - 1) // batch_size}:")

        # Process batch sequentially (parallel would overwhelm LLM)
        for community_id in batch:
            try:
                # Fetch community data
                entities = await summarizer._get_community_entities(community_id)
                relationships = await summarizer._get_community_relationships(community_id)

                # Generate summary
                summary = await summarizer.generate_summary(community_id, entities, relationships)

                # Store summary
                await summarizer._store_summary(community_id, summary)

                stats["summaries_generated"] += 1

                # Progress indicator
                progress_pct = (stats["summaries_generated"] / len(community_ids)) * 100
                print(f"     ✓ Community {community_id}: {len(summary)} chars ({progress_pct:.1f}%)")

            except Exception as e:
                logger.error(
                    "failed_to_generate_community_summary",
                    community_id=community_id,
                    error=str(e),
                )
                failed_communities.append(community_id)
                stats["failed"] += 1
                print(f"     ✗ Community {community_id}: FAILED ({str(e)})")

        batch_time = time.time() - batch_start
        print(f"     Batch completed in {batch_time:.1f}s")
        print()

    stats["total_time_s"] = time.time() - start_time
    stats["avg_time_per_summary_s"] = (
        stats["total_time_s"] / stats["summaries_generated"] if stats["summaries_generated"] > 0 else 0
    )

    if failed_communities:
        print(f"\n⚠️  Failed communities: {failed_communities}")

    return stats


async def main():
    """Main entry point for community summarization batch job."""
    parser = argparse.ArgumentParser(
        description="Generate community summaries for Graph-Global search (Sprint 77 Feature 77.4)"
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default=None,
        help="Filter by namespace (e.g., hotpotqa_large)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of communities to process concurrently (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count communities without generating summaries",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate ALL summaries (including existing ones)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Sprint 77 Community Summarization Batch Job")
    print("=" * 80)
    print()

    # Get communities to summarize
    print("1. Querying Neo4j for communities...")

    if args.force:
        community_ids = await get_all_communities(args.namespace)
        print(f"   ✓ Found {len(community_ids)} communities (force mode: regenerate all)")
    else:
        community_ids = await get_communities_without_summaries(args.namespace)
        print(f"   ✓ Found {len(community_ids)} communities without summaries")

    if args.namespace:
        print(f"   Namespace filter: {args.namespace}")

    # Generate summaries
    stats = await generate_summaries_batch(
        community_ids,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    # Print summary
    print()
    print("=" * 80)
    print("Summary Statistics:")
    print("=" * 80)
    print(f"Total communities: {stats['total_communities']}")
    print(f"Summaries generated: {stats['summaries_generated']}")
    print(f"Failed: {stats['failed']}")

    if not args.dry_run and stats["summaries_generated"] > 0:
        total_time_str = str(timedelta(seconds=int(stats["total_time_s"])))
        print(f"Total time: {total_time_str}")
        print(f"Avg time per summary: {stats['avg_time_per_summary_s']:.1f}s")

    print()

    if stats["failed"] > 0:
        print("⚠️  Some summaries failed - check logs for details")
        return 1
    elif stats["summaries_generated"] == 0 and not args.dry_run:
        print("✅ No summaries needed - all communities already have summaries!")
        print("   Use --force to regenerate all summaries")
        return 0
    else:
        print("✅ Community summarization complete!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
