#!/usr/bin/env python3
"""Clear all data from Neo4j, Qdrant, and BM25.

Sprint 41: Utility script for clearing evaluation data.

Usage:
    poetry run python scripts/clear_all_data.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment, then override with localhost for direct access
from dotenv import load_dotenv

load_dotenv(".env.dgx-spark")

# Override hostnames for running outside Docker
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"
os.environ["QDRANT_GRPC_PORT"] = "6334"


async def clear_neo4j():
    """Clear all nodes and relationships from Neo4j."""
    print("Clearing Neo4j...")

    try:
        from src.components.graph_rag.neo4j_client import Neo4jClient

        client = Neo4jClient()

        # Get count before
        result = await client.execute_query("MATCH (n) RETURN count(n) as count")
        count_before = result[0]["count"] if result else 0
        print(f"  Nodes before: {count_before}")

        if count_before > 0:
            # Delete all
            await client.execute_write("MATCH (n) DETACH DELETE n")

            # Verify
            result = await client.execute_query("MATCH (n) RETURN count(n) as count")
            count_after = result[0]["count"] if result else 0
            print(f"  Nodes after: {count_after}")
            print(f"  Deleted: {count_before - count_after} nodes")
        else:
            print("  Already empty")

        await client.close()
        return True

    except Exception as e:
        print(f"  Error: {e}")
        return False


async def clear_qdrant():
    """Clear all collections from Qdrant."""
    print("Clearing Qdrant...")

    try:
        from src.components.vector_search.qdrant_client import get_qdrant_client

        client = get_qdrant_client()

        # Get collections
        collections = await client.async_client.get_collections()
        collection_names = [c.name for c in collections.collections]
        print(f"  Collections: {collection_names}")

        for name in collection_names:
            # Get point count
            info = await client.async_client.get_collection(name)
            point_count = info.points_count
            print(f"  Deleting {name} ({point_count} points)...")

            # Delete collection
            await client.async_client.delete_collection(name)

        print(f"  Deleted {len(collection_names)} collections")
        return True

    except Exception as e:
        print(f"  Error: {e}")
        return False


def clear_bm25():
    """Clear BM25 index cache."""
    print("Clearing BM25...")

    cache_file = Path("data/cache/bm25_index.pkl")

    if cache_file.exists():
        size = cache_file.stat().st_size
        cache_file.unlink()
        print(f"  Deleted {cache_file} ({size} bytes)")
        return True
    else:
        print("  Cache file not found")
        return True


async def main():
    """Clear all data stores."""
    print("=" * 50)
    print("CLEARING ALL DATA")
    print("=" * 50)
    print()

    results = {
        "neo4j": await clear_neo4j(),
        "qdrant": await clear_qdrant(),
        "bm25": clear_bm25(),
    }

    print()
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for store, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {store}: {status}")

    all_success = all(results.values())
    print()
    print(f"Overall: {'SUCCESS' if all_success else 'SOME FAILURES'}")

    return 0 if all_success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
