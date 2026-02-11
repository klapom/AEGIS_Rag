#!/usr/bin/env python3
"""Sprint 129.6f: Table Ingestion E2E Benchmark.

Uploads PDFs from DP-Bench dataset through the frontend API,
measures table extraction quality, and reports results.

The upload endpoint is synchronous — each upload blocks until the full
ingestion pipeline (Docling → Chunking → Embedding → Graph) completes.

Usage:
    poetry run python scripts/benchmark_table_ingestion.py
    poetry run python scripts/benchmark_table_ingestion.py --max-docs 3
    poetry run python scripts/benchmark_table_ingestion.py --pdf-dir /path/to/pdfs
"""

import argparse
import json
import os
import sys
import time

import requests

# Configuration
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
NAMESPACE = "table_benchmark_sprint129"
DEFAULT_PDF_DIR = "data/evaluation/test_datasets/dp_bench_pdfs/dataset/pdfs"

# Table-containing PDFs from DP-Bench reference.json
TABLE_PDFS = [
    "01030000000045.pdf",
    "01030000000046.pdf",
    "01030000000047.pdf",
    "01030000000051.pdf",
    "01030000000052.pdf",
]


def authenticate() -> str:
    """Get JWT token for API access (register if needed, then login)."""
    username = "benchmark_bot"
    password = "benchmark_secure_123"  # pragma: allowlist secret

    # Try login first
    resp = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    if resp.status_code == 200:
        token = resp.json().get("access_token", "")
        print(f"Authenticated (existing user). Token: {token[:20]}...")
        return token

    # Register user, then login
    requests.post(
        f"{API_BASE}/api/v1/auth/register",
        json={
            "username": username,
            "password": password,
            "email": "benchmark@test.local",
            "role": "admin",
        },
        timeout=10,
    )
    resp = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"Auth failed: {resp.status_code} {resp.text[:200]}")
        sys.exit(1)
    token = resp.json().get("access_token", "")
    print(f"Authenticated (new user). Token: {token[:20]}...")
    return token


def upload_document(filepath: str, token: str) -> dict:
    """Upload a PDF via frontend API (synchronous — blocks until pipeline completes)."""
    headers = {"Authorization": f"Bearer {token}"}
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, "application/pdf")}
        data = {
            "namespace_id": NAMESPACE,  # Must match Form field name in retrieval.py
            "domain_id": "auto",
        }
        start = time.time()
        try:
            resp = requests.post(
                f"{API_BASE}/api/v1/retrieval/upload",
                headers=headers,
                files=files,
                data=data,
                timeout=600,  # 10 min — graph extraction can take 2-5 min
            )
        except requests.exceptions.Timeout:
            return {
                "file": os.path.basename(filepath),
                "status": "timeout",
                "upload_time_s": round(time.time() - start, 1),
            }
        upload_time = time.time() - start

    if resp.status_code not in (200, 201):
        return {
            "file": os.path.basename(filepath),
            "status": "failed",
            "error": resp.text[:300],
            "upload_time_s": round(upload_time, 1),
        }

    result = resp.json()
    return {
        "file": os.path.basename(filepath),
        "status": result.get("status", "unknown"),
        "upload_time_s": round(upload_time, 1),
        "chunks_created": result.get("chunks_created", 0),
        "neo4j_entities": result.get("neo4j_entities", 0),
        "neo4j_relationships": result.get("neo4j_relationships", 0),
        "points_indexed": result.get("points_indexed", 0),
        "duration_seconds": result.get("duration_seconds", 0),
        "response": result,
    }


def check_namespace_neo4j() -> dict:
    """Query Neo4j for aggregate stats across the benchmark namespace."""
    try:
        from neo4j import GraphDatabase

        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        neo4j_password = "aegis-rag-neo4j-password"  # pragma: allowlist secret
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("NEO4J_PASSWORD="):
                        val = line.strip().split("=", 1)[1].strip('"').strip("'")
                        # Strip inline comments
                        if "#" in val:
                            val = val[: val.index("#")].strip()
                        neo4j_password = val

        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", neo4j_password),
        )
        with driver.session() as session:
            # Count all entities in namespace
            result = session.run(
                "MATCH (e:base) WHERE e.namespace_id = $ns "
                "RETURN count(e) as entities, "
                "count(DISTINCT e.entity_type) as entity_types",
                ns=NAMESPACE,
            )
            rec = result.single()
            entity_count = rec["entities"]
            entity_types = rec["entity_types"]

            # Count relations
            result = session.run(
                "MATCH (e1:base)-[r:RELATES_TO]->(e2:base) "
                "WHERE e1.namespace_id = $ns "
                "RETURN count(r) as total, "
                "count(CASE WHEN r.relation_type <> 'RELATED_TO' THEN 1 END) as specific, "
                "count(DISTINCT r.relation_type) as relation_types",
                ns=NAMESPACE,
            )
            rec = result.single()
            rel_total = rec["total"]
            rel_specific = rec["specific"]
            rel_types = rec["relation_types"]

            # Count chunks
            result = session.run(
                "MATCH (c:chunk) WHERE c.namespace_id = $ns RETURN count(c) as chunks",
                ns=NAMESPACE,
            )
            chunk_count = result.single()["chunks"]

        driver.close()
        return {
            "chunks": chunk_count,
            "entities": entity_count,
            "entity_types": entity_types,
            "relations": rel_total,
            "specific_relations": rel_specific,
            "relation_types": rel_types,
            "specificity_pct": (round(rel_specific / rel_total * 100, 1) if rel_total > 0 else 0),
        }
    except Exception as e:
        return {"error": str(e)}


def check_namespace_qdrant() -> dict:
    """Check Qdrant for vectors in the benchmark namespace."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client = QdrantClient(host="localhost", port=6333)
        result = client.scroll(
            collection_name="documents_v1",
            scroll_filter=Filter(
                must=[FieldCondition(key="namespace_id", match=MatchValue(value=NAMESPACE))]
            ),
            limit=500,
        )
        points = result[0]
        table_chunks = [
            p
            for p in points
            if p.payload.get("is_table") is True
            or p.payload.get("metadata", {}).get("is_table") is True
        ]
        return {
            "total_vectors": len(points),
            "table_vectors": len(table_chunks),
            "table_quality_scores": [
                p.payload.get("table_quality_score")
                or p.payload.get("metadata", {}).get("table_quality_score")
                for p in table_chunks
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def run_benchmark(pdf_dir: str, max_docs: int = 5) -> dict:
    """Run the full table ingestion benchmark."""
    print("=" * 70)
    print("Sprint 129.6f: Table Ingestion E2E Benchmark")
    print("=" * 70)

    # Find PDF files
    pdf_files = []
    for pdf_name in TABLE_PDFS[:max_docs]:
        path = os.path.join(pdf_dir, pdf_name)
        if os.path.exists(path):
            pdf_files.append(path)
        else:
            print(f"WARNING: {path} not found")

    if not pdf_files:
        for f in sorted(os.listdir(pdf_dir))[:max_docs]:
            if f.endswith(".pdf"):
                pdf_files.append(os.path.join(pdf_dir, f))

    print(f"\nFound {len(pdf_files)} PDFs to test")
    for f in pdf_files:
        size = os.path.getsize(f)
        print(f"  - {os.path.basename(f)}: {size:,} bytes")

    # Authenticate
    print("\n--- Authentication ---")
    token = authenticate()

    # Upload and process
    results = []
    total_start = time.time()
    for i, filepath in enumerate(pdf_files):
        filename = os.path.basename(filepath)
        print(f"\n--- [{i + 1}/{len(pdf_files)}] Uploading {filename} ---")
        sys.stdout.flush()

        result = upload_document(filepath, token)
        status = result["status"]
        print(f"  Status: {status}")
        print(f"  Time: {result['upload_time_s']}s")

        if status in ("success", "partial"):
            print(f"  Chunks: {result.get('chunks_created', 0)}")
            print(f"  Entities: {result.get('neo4j_entities', 0)}")
            print(f"  Relations: {result.get('neo4j_relationships', 0)}")
            print(f"  Qdrant vectors: {result.get('points_indexed', 0)}")
        elif status in ("failed", "timeout"):
            print(f"  Error: {result.get('error', 'unknown')[:200]}")

        results.append(result)

        # Re-authenticate before token expires (30min TTL)
        if i > 0 and i % 2 == 0:
            print("  (Re-authenticating...)")
            token = authenticate()

    total_time = time.time() - total_start

    # Aggregate checks
    print("\n--- Database Verification ---")
    neo4j_data = check_namespace_neo4j()
    qdrant_data = check_namespace_qdrant()

    # Summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    completed = [r for r in results if r.get("status") in ("success", "partial")]
    failed = [r for r in results if r.get("status") in ("failed", "timeout")]

    print(f"\nDocuments: {len(results)} total, {len(completed)} completed, {len(failed)} failed")
    print(f"Total time: {total_time:.1f}s ({total_time / 60:.1f} min)")

    if completed:
        avg_time = sum(r.get("upload_time_s", 0) for r in completed) / len(completed)
        total_entities = sum(r.get("neo4j_entities", 0) for r in completed)
        total_relations = sum(r.get("neo4j_relationships", 0) for r in completed)
        print(f"\nPer-document (from API response):")
        print(f"  Avg processing time: {avg_time:.1f}s")
        print(f"  Total entities (API): {total_entities}")
        print(f"  Total relations (API): {total_relations}")

    print(f"\nNeo4j namespace '{NAMESPACE}':")
    if "error" not in neo4j_data:
        print(f"  Chunks: {neo4j_data.get('chunks', 0)}")
        print(
            f"  Entities: {neo4j_data.get('entities', 0)} ({neo4j_data.get('entity_types', 0)} types)"
        )
        print(
            f"  Relations: {neo4j_data.get('relations', 0)} ({neo4j_data.get('relation_types', 0)} types)"
        )
        print(f"  Specificity: {neo4j_data.get('specificity_pct', 0)}%")
    else:
        print(f"  Error: {neo4j_data['error']}")

    print(f"\nQdrant namespace '{NAMESPACE}':")
    if "error" not in qdrant_data:
        print(f"  Total vectors: {qdrant_data.get('total_vectors', 0)}")
        print(f"  Table vectors: {qdrant_data.get('table_vectors', 0)}")
        if qdrant_data.get("table_quality_scores"):
            scores = [s for s in qdrant_data["table_quality_scores"] if s is not None]
            if scores:
                print(f"  Table quality scores: {scores}")
    else:
        print(f"  Error: {qdrant_data['error']}")

    # Per-document detail table
    print("\n--- Per-Document Results ---")
    print(
        f"{'File':<30} {'Status':<10} {'Time(s)':<10} {'Chunks':<8} {'Entities':<10} {'Relations':<10}"
    )
    print("-" * 78)
    for r in results:
        print(
            f"{r['file']:<30} "
            f"{r.get('status', '?'):<10} "
            f"{r.get('upload_time_s', 0):<10.1f} "
            f"{r.get('chunks_created', '-'):<8} "
            f"{r.get('neo4j_entities', '-'):<10} "
            f"{r.get('neo4j_relationships', '-'):<10}"
        )

    # Save results
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    outfile = os.path.join(project_root, "table_ingestion_benchmark_sprint129.json")
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    with open(outfile, "w") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "namespace": NAMESPACE,
                "pdf_count": len(pdf_files),
                "completed": len(completed),
                "failed": len(failed),
                "total_time_s": round(total_time, 1),
                "neo4j_aggregate": neo4j_data,
                "qdrant_aggregate": qdrant_data,
                "results": results,
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\nResults saved to: {outfile}")

    return {"completed": len(completed), "failed": len(failed), "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Table Ingestion E2E Benchmark")
    parser.add_argument("--max-docs", type=int, default=5)
    parser.add_argument("--pdf-dir", type=str, default=DEFAULT_PDF_DIR)
    args = parser.parse_args()

    run_benchmark(args.pdf_dir, args.max_docs)
