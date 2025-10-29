#!/usr/bin/env python3
"""Debug script to test admin stats endpoint.

Sprint 18 TD-41: Debug Admin Stats 404 issue.

This script:
1. Lists all registered routes in FastAPI
2. Tests the admin stats endpoint directly
3. Provides detailed debugging information
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def main():
    """Test admin stats endpoint and list all routes."""
    print("\n" + "=" * 80)
    print("SPRINT 18 TD-41: Admin Stats Endpoint Debugging")
    print("=" * 80 + "\n")

    # Import FastAPI app
    print("[1/4] Importing FastAPI app...")
    from src.api.main import app

    print(f"✓ App imported: {app.title} v{app.version}")

    # List all registered routes
    print("\n[2/4] Listing all registered routes:")
    print("-" * 80)

    admin_routes_found = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            path = route.path
            methods = ", ".join(route.methods) if route.methods else "N/A"
            name = route.name if hasattr(route, "name") else "N/A"

            # Highlight admin routes
            if "/admin" in path:
                admin_routes_found.append((path, methods, name))
                print(f"  🔍 ADMIN: {methods:6s} {path:40s} (name: {name})")
            else:
                print(f"      {methods:6s} {path:40s}")

    print("-" * 80)
    print(f"Total routes: {len(list(app.routes))}")
    print(f"Admin routes found: {len(admin_routes_found)}")

    if admin_routes_found:
        print("\n✓ Admin routes registered:")
        for path, methods, name in admin_routes_found:
            print(f"  - {methods} {path}")
    else:
        print("\n✗ WARNING: No admin routes found!")
        print("  Expected: GET /api/v1/admin/stats")
        print("  This indicates the admin router is not properly registered.")

    # Test endpoint directly (if found)
    print("\n[3/4] Testing admin stats endpoint directly...")

    stats_route_found = any("/admin/stats" in path for path, _, _ in admin_routes_found)

    if stats_route_found:
        print("✓ /api/v1/admin/stats route found in registry")

        # Try to call the endpoint function directly
        print("\n[4/4] Attempting direct endpoint call...")
        try:
            from src.api.v1.admin import get_system_stats

            print("  - Calling get_system_stats() directly...")
            stats = await get_system_stats()
            print(f"  ✓ Success! Stats retrieved:")
            print(f"    - Qdrant chunks: {stats.qdrant_total_chunks}")
            print(f"    - Collection: {stats.qdrant_collection_name}")
            print(f"    - Vector dim: {stats.qdrant_vector_dimension}")
            print(f"    - Embedding model: {stats.embedding_model}")
            if stats.neo4j_total_entities:
                print(f"    - Neo4j entities: {stats.neo4j_total_entities}")
            if stats.total_conversations:
                print(f"    - Conversations: {stats.total_conversations}")

        except Exception as e:
            print(f"  ✗ Error calling endpoint: {e}")
            print(f"  Error type: {type(e).__name__}")
            import traceback

            traceback.print_exc()
    else:
        print("✗ /api/v1/admin/stats route NOT found")
        print("\n[4/4] DIAGNOSIS:")
        print("  The route is not registered in FastAPI's route table.")
        print("  Possible causes:")
        print("  1. Router prefix mismatch (check APIRouter prefix in admin.py)")
        print("  2. Router not included in main.py (check app.include_router())")
        print("  3. Route decorator issue (check @router.get('/stats'))")

    # Check router prefix
    print("\n" + "=" * 80)
    print("ROUTER PREFIX CHECK:")
    print("=" * 80)

    from src.api.v1.admin import router as admin_router

    print(f"  Admin router prefix: {admin_router.prefix}")
    print(f"  Expected full path: {admin_router.prefix}/stats")

    # Check if prefix is being double-applied
    if admin_router.prefix == "/api/v1/admin":
        print("\n✓ Router prefix looks correct: /api/v1/admin")
        print("  Final route should be: /api/v1/admin/stats")
    else:
        print(f"\n⚠ Unexpected router prefix: {admin_router.prefix}")

    print("\n" + "=" * 80)
    print("END OF DEBUGGING")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
