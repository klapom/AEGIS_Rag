#!/usr/bin/env python3
"""Sprint 85 ER Ratio Test Script.

Test ingestion with 5 files and verify ER (Entity-Relation) ratio.
Target: ER ratio >= 1.0 (at least 1 relation per entity)

Usage:
    poetry run python scripts/test_sprint85_er_ratio.py
"""

import asyncio
import sys
import time
from pathlib import Path

import httpx

API_BASE = "http://localhost:8000"
TEST_FILES_DIR = Path("data/ragas_eval_txt")
NAMESPACE = f"sprint85_test_{int(time.time())}"
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "admin123"


async def get_auth_token(client: httpx.AsyncClient) -> str:
    """Get authentication token."""
    response = await client.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
        timeout=30.0,
    )
    data = response.json()
    return data.get("access_token", "")


async def upload_file(client: httpx.AsyncClient, file_path: Path, token: str) -> dict:
    """Upload a file via the API."""
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "text/plain")}
        data = {"namespace_id": NAMESPACE}

        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            f"{API_BASE}/api/v1/retrieval/upload",
            files=files,
            data=data,
            headers=headers,
            timeout=300.0,
        )

        return response.json()


async def check_upload_status(client: httpx.AsyncClient, document_id: str, token: str) -> dict:
    """Check upload status."""
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(
        f"{API_BASE}/api/v1/admin/upload-status/{document_id}",
        headers=headers,
        timeout=30.0,
    )
    return response.json()


async def wait_for_completion(
    client: httpx.AsyncClient, document_id: str, token: str, max_wait: int = 600
) -> dict:
    """Wait for document processing to complete."""
    start = time.time()
    while time.time() - start < max_wait:
        status = await check_upload_status(client, document_id, token)

        if status.get("status") in ("completed", "failed"):
            return status

        print(f"  ... waiting ({int(time.time() - start)}s): {status.get('status', 'unknown')}")
        await asyncio.sleep(5)

    return {"status": "timeout", "error": f"Exceeded {max_wait}s wait time"}


async def run_test():
    """Run the ER ratio test."""
    print("=" * 60)
    print("Sprint 85 ER Ratio Test")
    print("=" * 60)
    print(f"Namespace: {NAMESPACE}")
    print()

    # Find test files
    txt_files = sorted(TEST_FILES_DIR.glob("hotpot_*.txt"))[:5]

    if not txt_files:
        print(f"ERROR: No test files found in {TEST_FILES_DIR}")
        return 1

    print(f"Test files ({len(txt_files)}):")
    for f in txt_files:
        print(f"  - {f.name}")
    print()

    # Results tracking
    results = []
    total_entities = 0
    total_relations = 0

    async with httpx.AsyncClient() as client:
        # Check API health
        try:
            health = await client.get(f"{API_BASE}/health", timeout=10.0)
            if health.status_code != 200:
                print(f"ERROR: API not healthy: {health.status_code}")
                return 1
            print("API is healthy.")
        except Exception as e:
            print(f"ERROR: Cannot connect to API: {e}")
            return 1

        # Get authentication token
        try:
            token = await get_auth_token(client)
            if not token:
                print("ERROR: Failed to get authentication token")
                return 1
            print("Authentication successful.")
        except Exception as e:
            print(f"ERROR: Authentication failed: {e}")
            return 1

        print()
        print("-" * 60)

        # Upload each file
        for i, file_path in enumerate(txt_files, 1):
            print(f"\n[{i}/{len(txt_files)}] Uploading: {file_path.name}")

            try:
                upload_result = await upload_file(client, file_path, token)

                # API returns results synchronously (no polling needed)
                status = upload_result.get("status", "unknown")

                # Get entity/relation counts from synchronous response
                entities = upload_result.get("neo4j_entities", 0)
                relations = upload_result.get("neo4j_relationships", 0)

                # If async polling is needed (document_id returned)
                document_id = upload_result.get("document_id", "")
                if document_id and status != "success":
                    print(f"  Document ID: {document_id[:12]}... (polling for completion)")
                    final_status = await wait_for_completion(client, document_id, token)
                    status = final_status.get("status", "unknown")
                    entities = final_status.get("entities_count", entities)
                    relations = final_status.get("relations_count", relations)

                print(f"  Status: {status}")
                print(f"  Entities: {entities}")
                print(f"  Relations: {relations}")

                total_entities += entities
                total_relations += relations

                # Normalize status (success = completed)
                normalized_status = "completed" if status == "success" else status

                results.append({
                    "file": file_path.name,
                    "status": normalized_status,
                    "entities": entities,
                    "relations": relations,
                    "er_ratio": relations / entities if entities > 0 else 0,
                })

            except Exception as e:
                print(f"  ERROR: {e}")
                results.append({"file": file_path.name, "status": "error", "error": str(e)})

        print()
        print("=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)

        for r in results:
            er = r.get("er_ratio", 0)
            status_icon = "✅" if r["status"] == "completed" and er >= 1.0 else "⚠️" if r["status"] == "completed" else "❌"
            print(f"{status_icon} {r['file']}: E={r.get('entities', 0)}, R={r.get('relations', 0)}, ER={er:.2f}")

        print()
        print("-" * 60)
        overall_er = total_relations / total_entities if total_entities > 0 else 0
        print(f"TOTAL Entities: {total_entities}")
        print(f"TOTAL Relations: {total_relations}")
        print(f"OVERALL ER Ratio: {overall_er:.2f}")
        print()

        if overall_er >= 1.0:
            print("✅ SUCCESS: ER Ratio >= 1.0")
            return 0
        else:
            print(f"⚠️ WARNING: ER Ratio {overall_er:.2f} < 1.0 target")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_test())
    sys.exit(exit_code)
