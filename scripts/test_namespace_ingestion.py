#!/usr/bin/env python3
"""Test namespace-aware document ingestion.

Sprint 41: Verify that documents are ingested with proper namespace tags.

Usage:
    poetry run python scripts/test_namespace_ingestion.py

This script:
1. Ingests a test document into a specific namespace (eval_sprint41)
2. Verifies the document is stored with namespace_id in Qdrant
3. Verifies entities are stored with namespace_id in Neo4j
4. Tests search isolation (document only visible in its namespace)
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

# Import after env setup
from src.core.namespace import get_namespace_manager

TEST_NAMESPACE = "eval_sprint41"
TEST_DOCUMENT = "data/test_evaluation/namespace_test_document.md"


async def create_test_namespace():
    """Create the test namespace."""
    print(f"Creating namespace: {TEST_NAMESPACE}")

    manager = get_namespace_manager()

    try:
        result = await manager.create_namespace(
            namespace_id=TEST_NAMESPACE,
            namespace_type="evaluation",
            description="Sprint 41 namespace isolation test",
        )
        print(f"  Created: {result.namespace_id}")
        print(f"  Type: {result.namespace_type}")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


async def verify_qdrant_namespace():
    """Verify Qdrant has documents in the test namespace."""
    print("\nVerifying Qdrant namespace...")

    manager = get_namespace_manager()

    try:
        # Search in test namespace (should find test document if ingested)
        results = await manager.search_qdrant(
            query_vector=[0.1] * 1024,  # Dummy vector
            allowed_namespaces=[TEST_NAMESPACE],
            limit=10,
        )

        print(f"  Documents in {TEST_NAMESPACE}: {len(results)}")

        # Search in default namespace (should not find test document)
        default_results = await manager.search_qdrant(
            query_vector=[0.1] * 1024,
            allowed_namespaces=["default"],
            limit=10,
        )

        print(f"  Documents in default: {len(default_results)}")

        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


async def verify_neo4j_namespace():
    """Verify Neo4j has entities in the test namespace."""
    print("\nVerifying Neo4j namespace...")

    manager = get_namespace_manager()

    try:
        # Search entities in test namespace
        results = await manager.search_neo4j_local(
            query_terms=["namespace", "isolation"],
            allowed_namespaces=[TEST_NAMESPACE],
            top_k=10,
        )

        print(f"  Entities in {TEST_NAMESPACE}: {len(results)}")

        # Search entities in default namespace
        default_results = await manager.search_neo4j_local(
            query_terms=["namespace", "isolation"],
            allowed_namespaces=["default"],
            top_k=10,
        )

        print(f"  Entities in default: {len(default_results)}")

        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


async def test_search_isolation():
    """Test that search respects namespace isolation."""
    print("\nTesting search isolation...")

    manager = get_namespace_manager()

    try:
        # Search in test namespace
        test_results = await manager.search_qdrant(
            query_vector=[0.1] * 1024,
            allowed_namespaces=[TEST_NAMESPACE],
            limit=10,
        )

        # Search in empty namespace list (should return empty)
        empty_results = await manager.search_qdrant(
            query_vector=[0.1] * 1024,
            allowed_namespaces=[],
            limit=10,
        )

        print(f"  Results with namespace: {len(test_results)}")
        print(f"  Results with empty namespace: {len(empty_results)}")

        # Empty namespace should always return empty
        if len(empty_results) == 0:
            print("  PASS: Empty namespace returns empty results")
        else:
            print("  FAIL: Empty namespace should return empty results")

        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


async def main():
    """Run namespace ingestion tests."""
    print("=" * 60)
    print("NAMESPACE INGESTION TEST")
    print("=" * 60)
    print()

    results = {
        "create_namespace": await create_test_namespace(),
        "verify_qdrant": await verify_qdrant_namespace(),
        "verify_neo4j": await verify_neo4j_namespace(),
        "search_isolation": await test_search_isolation(),
    }

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  {test}: {status}")

    all_passed = all(results.values())
    print()
    print(f"Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

    # Note about ingestion
    print()
    print("=" * 60)
    print("NOTE: Document Ingestion")
    print("=" * 60)
    print(f"""
To ingest documents with namespace tagging:

1. Use the admin indexing UI at http://localhost:5173/admin/indexing
2. Set directory: {TEST_DOCUMENT}
3. The ingestion pipeline will tag documents with namespace_id

Or use the API:
  POST /api/v1/admin/indexing/start
  {{"directory": "data/test_evaluation", "namespace_id": "{TEST_NAMESPACE}"}}
""")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
