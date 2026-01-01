#!/usr/bin/env python3
"""Daily Memory Consolidation + Forgetting Cron Job.

Sprint 68 Feature 68.6: Memory-Write Policy + Forgetting

This script runs daily maintenance on Graphiti episodic memory:
1. Forget stale facts (decay-based)
2. Consolidate related facts (merge duplicates)
3. Report statistics to logging

Recommended cron schedule:
0 2 * * * /path/to/consolidate_memory.py

Or use systemd timer for more robust scheduling.
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

import structlog

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.memory.forgetting import get_forgetting_mechanism
from src.core.config import settings
from src.core.logging import setup_logging

logger = structlog.get_logger(__name__)


async def run_daily_maintenance() -> dict:
    """Run daily memory consolidation and forgetting.

    Returns:
        Maintenance statistics
    """
    logger.info("Starting daily memory maintenance job")

    try:
        # Get forgetting mechanism
        forgetting = get_forgetting_mechanism()

        # Run maintenance (forget + consolidate)
        results = await forgetting.run_daily_maintenance()

        logger.info(
            "Daily maintenance completed successfully",
            facts_removed=results.get("forgetting", {}).get("removed", 0),
            facts_consolidated=results.get("consolidation", {}).get("consolidated", 0),
            duration_seconds=(
                (
                    datetime.fromisoformat(results["completed_at"])
                    - datetime.fromisoformat(results["started_at"])
                ).total_seconds()
            ),
        )

        return results

    except Exception as e:
        logger.error("Daily maintenance failed", error=str(e), exc_info=True)
        raise


async def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    # Setup logging
    setup_logging()

    logger.info(
        "Memory consolidation job starting",
        timestamp=datetime.now(UTC).isoformat(),
        graphiti_enabled=settings.graphiti_enabled,
    )

    if not settings.graphiti_enabled:
        logger.warning("Graphiti disabled in settings, skipping maintenance")
        return 0

    try:
        results = await run_daily_maintenance()

        # Print summary
        forgetting_stats = results.get("forgetting", {})
        consolidation_stats = results.get("consolidation", {})

        print("\n=== Daily Memory Maintenance Summary ===")
        print(f"Started:  {results.get('started_at')}")
        print(f"Completed: {results.get('completed_at')}")
        print()
        print("Forgetting:")
        print(f"  Processed: {forgetting_stats.get('processed', 0)}")
        print(f"  Removed:   {forgetting_stats.get('removed', 0)}")
        print(f"  Retained:  {forgetting_stats.get('retained', 0)}")
        print()
        print("Consolidation:")
        print(f"  Processed:     {consolidation_stats.get('processed', 0)}")
        print(f"  Clusters:      {consolidation_stats.get('clusters', 0)}")
        print(f"  Consolidated:  {consolidation_stats.get('consolidated', 0)}")
        print(f"  Removed:       {consolidation_stats.get('removed', 0)}")
        print()

        return 0

    except Exception as e:
        logger.error("Maintenance job failed", error=str(e))
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
