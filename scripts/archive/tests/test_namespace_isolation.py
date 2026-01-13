"""Quick test script for namespace isolation verification.

Sprint 75 - Option C: Verify namespace isolation works correctly.

This script:
1. Creates a small test document in "test_ragas" namespace
2. Searches for content with namespace filter
3. Verifies only test_ragas documents are returned (not default namespace docs)
"""

import asyncio
import httpx
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

async def main():
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("🔐 Step 1: Login...")
        login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✅ Token: {token[:50]}...")

        print("\n📄 Step 2: Create test document...")
        test_content = """# Test Document for Namespace Isolation

## BGE-M3 Embedding Model

BGE-M3 is a 1024-dimensional multilingual embedding model used in AEGIS RAG.
It was selected in ADR-024 for system-wide standardization.

Key Features:
- 1024-dimensional vectors
- Multilingual support (100+ languages)
- Optimized for retrieval tasks
- State-of-the-art MTEB performance
"""

        # Save to temp file as .txt (avoids llama_index dependency)
        test_file = Path("/tmp/test_bge_m3.txt")
        test_file.write_text(test_content)

        print(f"   Uploading: {test_file}")
        print(f"   Namespace: test_ragas")

        with open(test_file, "rb") as f:
            upload_response = await client.post(
                f"{BASE_URL}/retrieval/upload",
                headers=headers,
                files={"file": ("test_bge_m3.txt", f, "text/plain")},
                data={"namespace": "test_ragas"}
            )

        if upload_response.status_code == 200:
            result = upload_response.json()
            print(f"✅ Upload successful!")
            print(f"   Document ID: {result.get('document_id', 'N/A')}")
            print(f"   Chunks: {result.get('chunk_count', 'N/A')}")
        else:
            print(f"❌ Upload failed: {upload_response.status_code}")
            print(f"   {upload_response.text}")
            return

        print("\n🔍 Step 3: Search with namespace filter...")
        print("   Query: 'BGE-M3 embedding model'")
        print("   Namespace: test_ragas")

        search_response = await client.post(
            f"{BASE_URL}/retrieval/search",
            headers=headers,
            json={
                "query": "BGE-M3 embedding model",
                "top_k": 5,
                "allowed_namespaces": ["test_ragas"]
            }
        )

        if search_response.status_code == 200:
            results = search_response.json()
            print(f"✅ Search successful!")
            print(f"   Results found: {len(results.get('results', []))}")

            print("\n📊 Result Analysis:")
            for i, result in enumerate(results.get("results", [])[:5], 1):
                namespace = result.get("metadata", {}).get("namespace", "N/A")
                doc_id = result.get("metadata", {}).get("document_id", "N/A")
                score = result.get("score", 0.0)
                text_preview = result.get("text", "")[:80]

                print(f"\n   Result {i}:")
                print(f"     Namespace: {namespace}")
                print(f"     Document: {doc_id}")
                print(f"     Score: {score:.4f}")
                print(f"     Text: {text_preview}...")

                # Verification
                if namespace != "test_ragas":
                    print(f"     ⚠️  WARNING: Document from wrong namespace!")

            # Final verification
            namespaces_found = set()
            for result in results.get("results", []):
                ns = result.get("metadata", {}).get("namespace", "unknown")
                namespaces_found.add(ns)

            print(f"\n🎯 Namespace Isolation Test:")
            print(f"   Namespaces in results: {namespaces_found}")

            if namespaces_found == {"test_ragas"}:
                print("   ✅ PASS: Only test_ragas namespace documents returned")
                print("   ✅ Namespace isolation working correctly!")
            elif "test_ragas" in namespaces_found and len(namespaces_found) > 1:
                print(f"   ❌ FAIL: Multiple namespaces found: {namespaces_found}")
                print("   ❌ BUG: Namespace isolation is NOT working!")
                print("   ❌ This is a critical security issue!")
            elif not namespaces_found:
                print("   ⚠️  No results found (upload may still be processing)")
            else:
                print(f"   ❌ FAIL: Wrong namespace: {namespaces_found}")

        else:
            print(f"❌ Search failed: {search_response.status_code}")
            print(f"   {search_response.text}")

if __name__ == "__main__":
    asyncio.run(main())
