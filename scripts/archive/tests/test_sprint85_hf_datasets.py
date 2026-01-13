#!/usr/bin/env python3
"""Sprint 85 ER Ratio Test - Huggingface Datasets.

Tests entity/relationship extraction across downloaded HF datasets:
1. CNN/DailyMail (DocRED alternative) - News articles
2. SQuAD (TACRED alternative) - QA contexts
3. Re-DocRED - Wikipedia with full relation annotations
4. ScienceQA (TutorQA alternative) - Educational content

Uses the Frontend API endpoint: POST /api/v1/retrieval/upload

Usage:
    poetry run python scripts/test_sprint85_hf_datasets.py
"""

import asyncio
import random
import time
from pathlib import Path

import httpx

API_BASE = "http://localhost:8000"
BASE_PATH = Path("/home/admin/projects/aegisrag/AEGIS_Rag")

# Huggingface Dataset configurations
DATASETS = {
    "cnn_dailymail": {
        "path": Path("data/hf_relation_datasets/docred"),
        "pattern": "cnn_*.txt",
        "description": "CNN/DailyMail (DocRED alternative)",
        "sample_size": 5,  # Reduced for faster testing
    },
    "squad": {
        "path": Path("data/hf_relation_datasets/tacred"),
        "pattern": "squad_*.txt",
        "description": "SQuAD (TACRED alternative)",
        "sample_size": 5,
    },
    "redocred": {
        "path": Path("data/hf_relation_datasets/redocred"),
        "pattern": "redocred_*.txt",
        "description": "Re-DocRED (Wikipedia Relations)",
        "sample_size": 5,
    },
    "scienceqa": {
        "path": Path("data/hf_relation_datasets/tutorqa"),
        "pattern": "scienceqa_*.txt",
        "description": "ScienceQA (TutorQA alternative)",
        "sample_size": 5,
    },
}


async def get_auth_token(client: httpx.AsyncClient) -> str:
    """Get authentication token from API."""
    response = await client.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=30.0,
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token", "")
    print(f"  Auth failed: {response.status_code} - {response.text}")
    return ""


async def upload_file(
    client: httpx.AsyncClient, file_path: Path, namespace: str, token: str
) -> dict:
    """Upload a file via the Frontend API endpoint."""
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "text/plain")}
        data = {"namespace": namespace, "domain": "hf_er_test"}
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            f"{API_BASE}/api/v1/retrieval/upload",  # Frontend API endpoint
            files=files,
            data=data,
            headers=headers,
            timeout=600.0,
        )
    return response.json()


async def test_dataset(
    client: httpx.AsyncClient,
    token: str,
    dataset_name: str,
    config: dict,
) -> dict:
    """Test a single dataset and return results."""
    print(f"\n{'='*60}")
    print(f"Dataset: {config['description']}")
    print(f"{'='*60}")

    # Find files
    data_path = BASE_PATH / config["path"]
    files = sorted(data_path.glob(config["pattern"]))

    if not files:
        print(f"  ERROR: No files found in {data_path}")
        return {"error": "No files found", "dataset": dataset_name}

    # Sample files
    sample_size = min(config["sample_size"], len(files))
    sample_files = random.sample(files, sample_size)

    print(f"Files found: {len(files)}")
    print(f"Testing with: {sample_size} files")

    # Create unique namespace
    namespace = f"hf_er_test_{dataset_name}_{int(time.time())}"
    print(f"Namespace: {namespace}")
    print("-" * 60)

    results = []
    total_entities = 0
    total_relations = 0

    for i, file_path in enumerate(sample_files, 1):
        file_size = file_path.stat().st_size
        print(f"\n[{i}/{sample_size}] {file_path.name} ({file_size} bytes)")

        try:
            result = await upload_file(client, file_path, namespace, token)

            status = result.get("status", "unknown")
            entities = result.get("neo4j_entities", 0)
            relations = result.get("neo4j_relationships", 0)
            er_ratio = relations / entities if entities > 0 else 0

            print(f"  Status: {status}")
            print(f"  Entities: {entities}, Relations: {relations}")
            print(f"  ER Ratio: {er_ratio:.2f}")

            if entities >= 1:  # Only count files with at least 1 entity
                total_entities += entities
                total_relations += relations

            results.append({
                "file": file_path.name,
                "size_bytes": file_size,
                "entities": entities,
                "relations": relations,
                "er_ratio": er_ratio,
            })

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "file": file_path.name,
                "error": str(e),
            })

    # Calculate summary
    overall_er = total_relations / total_entities if total_entities > 0 else 0

    print(f"\n{'-'*60}")
    print(f"SUMMARY: {config['description']}")
    print(f"  Total Entities: {total_entities}")
    print(f"  Total Relations: {total_relations}")
    print(f"  Overall ER Ratio: {overall_er:.2f}")

    if overall_er >= 1.0:
        print("  ✅ TARGET ACHIEVED (ER >= 1.0)")
    else:
        print("  ⚠️ Below target (ER < 1.0)")

    return {
        "dataset": dataset_name,
        "description": config["description"],
        "files_tested": len(results),
        "total_entities": total_entities,
        "total_relations": total_relations,
        "overall_er_ratio": overall_er,
        "results": results,
    }


async def main():
    """Main test runner."""
    print("=" * 60)
    print("Sprint 85 ER Ratio Test - Huggingface Datasets")
    print("=" * 60)
    print(f"API Endpoint: {API_BASE}/api/v1/retrieval/upload")
    print("=" * 60)

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

        # Test each dataset
        all_results = []
        for dataset_name, config in DATASETS.items():
            result = await test_dataset(client, token, dataset_name, config)
            all_results.append(result)

        # Final comparison
        print("\n" + "=" * 60)
        print("FINAL COMPARISON - Huggingface Datasets")
        print("=" * 60)
        print(f"{'Dataset':<35} {'Entities':>10} {'Relations':>10} {'ER Ratio':>10}")
        print("-" * 70)

        for r in all_results:
            if "error" not in r:
                er_icon = "✅" if r["overall_er_ratio"] >= 1.0 else "⚠️"
                print(
                    f"{r['description'][:35]:<35} "
                    f"{r['total_entities']:>10} "
                    f"{r['total_relations']:>10} "
                    f"{r['overall_er_ratio']:>9.2f} {er_icon}"
                )

        # Calculate overall
        total_e = sum(r.get("total_entities", 0) for r in all_results)
        total_r = sum(r.get("total_relations", 0) for r in all_results)
        overall = total_r / total_e if total_e > 0 else 0

        print("-" * 70)
        print(f"{'OVERALL':<35} {total_e:>10} {total_r:>10} {overall:>9.2f}")
        print("=" * 70)

        if overall >= 1.0:
            print("\n✅ SUCCESS: Overall ER Ratio >= 1.0")
            return 0
        else:
            print(f"\n⚠️ WARNING: Overall ER Ratio {overall:.2f} < 1.0 target")
            return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
