#!/usr/bin/env python3
"""
E2E Pipeline Benchmark — Upload documents via Frontend API (production path).

Measures full pipeline: upload → parsing → chunking → extraction → storage
Tracks: duration, entities, relations, quality metrics.

Usage:
    python scripts/e2e_pipeline_benchmark.py              # default 15 files
    python scripts/e2e_pipeline_benchmark.py --count 5    # 5 files
    python scripts/e2e_pipeline_benchmark.py --count 15 --namespace bench_15doc

Requires: aegis-api, aegis-neo4j, aegis-qdrant, aegis-redis, vLLM running.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import datetime
import requests
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"
DEFAULT_NAMESPACE = "e2e_bench_15doc"
DOMAIN = "auto"

# All 15 HotpotQA files sorted by size (ascending)
ALL_FILES = [
    "hotpot_000017.txt",  # 950B  (XS)
    "hotpot_000018.txt",  # 1.0KB (XS)
    "hotpot_000019.txt",  # 1.0KB (XS)
    "hotpot_000015.txt",  # 1.1KB (S)
    "hotpot_000016.txt",  # 1.1KB (S)
    "hotpot_000014.txt",  # 1.3KB (S)
    "hotpot_000013.txt",  # 1.8KB (M)
    "hotpot_000008.txt",  # 1.8KB (M)
    "hotpot_000005.txt",  # 2.1KB (M+)
    "hotpot_000012.txt",  # 2.3KB (M+)
    "hotpot_000011.txt",  # 2.4KB (L)
    "hotpot_000007.txt",  # 2.5KB (L)
    "hotpot_000009.txt",  # 2.6KB (L)
    "hotpot_000010.txt",  # 3.2KB (XL)
    "hotpot_000006.txt",  # 3.3KB (XL)
]
DATA_DIR = Path(__file__).parent.parent / "data" / "evaluation" / "hotpotqa_contexts"

# Upload timeout: synchronous endpoint, may take 5-15 minutes for large files
UPLOAD_TIMEOUT = 1800  # 30 min max per document


def get_token() -> str:
    """Register (if needed) and login to get JWT token."""
    r = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"username": "e2e_benchmark", "password": "benchmark1234"},  # pragma: allowlist secret
        timeout=10,
    )

    if r.status_code == 200:
        return r.json()["access_token"]

    # Register if login fails
    requests.post(
        f"{API_BASE}/api/v1/auth/register",
        json={
            "username": "e2e_benchmark",
            "email": "bench@test.com",
            "password": "benchmark1234",  # pragma: allowlist secret
        },
        timeout=10,
    )

    r = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"username": "e2e_benchmark", "password": "benchmark1234"},  # pragma: allowlist secret
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def upload_document(filepath: Path, token: str, namespace: str) -> dict:
    """Upload document via production API endpoint (synchronous)."""
    headers = {"Authorization": f"Bearer {token}"}

    with open(filepath, "rb") as f:
        r = requests.post(
            f"{API_BASE}/api/v1/retrieval/upload",
            files={"file": (filepath.name, f, "text/plain")},
            data={"namespace_id": namespace, "domain_id": DOMAIN},
            headers=headers,
            timeout=UPLOAD_TIMEOUT,
        )

    return {"status_code": r.status_code, "body": r.json() if r.status_code == 200 else r.text}


def query_neo4j(query: str) -> str:
    """Run a Cypher query via docker exec."""
    cmd = f'docker exec aegis-neo4j cypher-shell -u neo4j -p "aegis-rag-neo4j-password" "{query}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout.strip()


def get_neo4j_stats_by_namespace(namespace: str) -> dict:
    """Query Neo4j for aggregate entity/relation counts by namespace.

    Uses the correct AegisRAG schema:
    - Entities: :base nodes with entity_name, entity_type, namespace_id
    - Relations: :RELATES_TO edges with relation_type, namespace_id
    - Chunks: :chunk nodes with namespace_id
    """
    stats = {}

    # Entity count
    out = query_neo4j(f"MATCH (e:base) WHERE e.namespace_id = '{namespace}' RETURN count(e) as cnt")
    stats["entity_count"] = _parse_count(out)

    # Relation count
    out = query_neo4j(
        f"MATCH ()-[r:RELATES_TO]->() WHERE r.namespace_id = '{namespace}' RETURN count(r) as cnt"
    )
    stats["relation_count"] = _parse_count(out)

    # Chunk count
    out = query_neo4j(
        f"MATCH (c:chunk) WHERE c.namespace_id = '{namespace}' RETURN count(c) as cnt"
    )
    stats["chunk_count"] = _parse_count(out)

    # Entity types breakdown
    out = query_neo4j(
        f"MATCH (e:base) WHERE e.namespace_id = '{namespace}' "
        f"RETURN e.entity_type as t, count(*) as c ORDER BY c DESC LIMIT 15"
    )
    stats["entity_types_raw"] = out

    # Relation types breakdown (from relation_type property, NOT Neo4j edge type)
    out = query_neo4j(
        f"MATCH ()-[r:RELATES_TO]->() WHERE r.namespace_id = '{namespace}' "
        f"RETURN r.relation_type as t, count(*) as c ORDER BY c DESC LIMIT 20"
    )
    stats["relation_types_raw"] = out

    # Sample entities (top 15)
    out = query_neo4j(
        f"MATCH (e:base) WHERE e.namespace_id = '{namespace}' "
        f"RETURN e.entity_name as name, e.entity_type as type, e.description as desc LIMIT 15"
    )
    stats["sample_entities_raw"] = out

    # Sample relations (top 10)
    out = query_neo4j(
        f"MATCH (a:base)-[r:RELATES_TO]->(b:base) WHERE r.namespace_id = '{namespace}' "
        f"RETURN a.entity_name as subj, r.relation_type as rel, b.entity_name as obj LIMIT 10"
    )
    stats["sample_relations_raw"] = out

    # Entities per document
    out = query_neo4j(
        f"MATCH (e:base) WHERE e.namespace_id = '{namespace}' "
        f"RETURN e.file_path as doc_id, count(e) as cnt ORDER BY cnt DESC"
    )
    stats["entities_per_doc_raw"] = out

    return stats


def get_qdrant_stats(namespace: str) -> dict:
    """Query Qdrant for vector count in namespace."""
    try:
        r = requests.post(
            "http://localhost:6333/collections/documents_v1/points/count",
            json={
                "filter": {
                    "must": [
                        {"key": "namespace_id", "match": {"value": namespace}},
                    ]
                },
                "exact": True,
            },
            timeout=10,
        )
        if r.status_code == 200:
            return {"vector_count": r.json().get("result", {}).get("count", 0)}
    except Exception as e:
        return {"error": str(e)}
    return {"vector_count": 0}


def _parse_count(output: str) -> int:
    """Parse count from cypher-shell output."""
    for line in output.strip().split("\n"):
        line = line.strip()
        if line.isdigit():
            return int(line)
    return 0


def _parse_relation_types(raw: str) -> dict:
    """Parse relation type breakdown from cypher-shell output."""
    types = {}
    for line in raw.strip().split("\n"):
        parts = [p.strip().strip('"') for p in line.split(",") if p.strip()]
        if len(parts) >= 2 and parts[-1].isdigit():
            types[parts[0].strip('"')] = int(parts[-1])
    return types


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="E2E Pipeline Benchmark")
    parser.add_argument(
        "--count", type=int, default=15, help="Number of files to process (default: 15)"
    )
    parser.add_argument(
        "--namespace", type=str, default=DEFAULT_NAMESPACE, help="Qdrant/Neo4j namespace"
    )
    parser.add_argument(
        "--ollama", action="store_true", help="Set if Ollama is running (affects config display)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    NAMESPACE = args.namespace
    TEST_FILES = ALL_FILES[: args.count]
    ollama_status = "running" if args.ollama else "stopped"

    print("=" * 80)
    print("  E2E Pipeline Benchmark — Sprint 128 (eugr + DeepGemm OFF)")
    print(f"  Config: vLLM eugr image, VLLM_MOE_USE_DEEP_GEMM=0, gpu-memory-utilization=0.45")
    print(f"  Namespace: {NAMESPACE}")
    print(f"  Documents: {len(TEST_FILES)}")
    print(f"  Ollama: {ollama_status}")
    print(f"  Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    sys.stdout.flush()

    # ── Auth ────────────────────────────────────────────────────────────────
    print("\n[1/3] Authenticating...")
    token = get_token()
    print(f"  Token: {token[:20]}...")
    sys.stdout.flush()

    # ── Upload ──────────────────────────────────────────────────────────────
    print(f"\n[2/3] Uploading {len(TEST_FILES)} documents (sequential, synchronous)...\n")
    sys.stdout.flush()
    results = []
    total_start = time.time()

    for i, filename in enumerate(TEST_FILES, 1):
        filepath = DATA_DIR / filename
        filesize = filepath.stat().st_size

        print(f"  ── [{i}/{len(TEST_FILES)}] {filename} ({filesize:,}B) ──")
        sys.stdout.flush()

        # Re-auth before each upload (JWT expiry protection, learned Sprint 127)
        try:
            token = get_token()
        except Exception:
            pass

        t0 = time.time()
        resp = upload_document(filepath, token, NAMESPACE)
        duration = time.time() - t0

        if resp["status_code"] == 200:
            body = resp["body"]
            print(f"    Status: {body.get('status', '?')} in {duration:.1f}s")
            print(
                f"    Chunks: {body.get('chunks_created', '?')}, "
                f"Entities: {body.get('neo4j_entities', '?')}, "
                f"Relations: {body.get('neo4j_relationships', '?')}"
            )

            results.append(
                {
                    "filename": filename,
                    "filesize": filesize,
                    "duration_s": round(duration, 1),
                    "status": body.get("status", "unknown"),
                    "chunks_created": body.get("chunks_created", 0),
                    "api_entities": body.get("neo4j_entities", 0),
                    "api_relations": body.get("neo4j_relationships", 0),
                    "embeddings": body.get("embeddings_generated", 0),
                    "api_duration_s": body.get("duration_seconds", 0),
                }
            )
        else:
            print(f"    FAILED ({resp['status_code']}): {str(resp['body'])[:200]}")
            results.append(
                {
                    "filename": filename,
                    "filesize": filesize,
                    "duration_s": round(duration, 1),
                    "status": "failed",
                    "error": str(resp["body"])[:200],
                }
            )
        sys.stdout.flush()

    total_duration = time.time() - total_start

    # ── Neo4j + Qdrant stats (namespace-level) ──────────────────────────────
    print(f"\n[3/3] Querying Neo4j + Qdrant for namespace stats...\n")
    sys.stdout.flush()

    neo4j_ns = get_neo4j_stats_by_namespace(NAMESPACE)
    print(
        f"  Neo4j namespace '{NAMESPACE}': "
        f"{neo4j_ns['entity_count']}e / {neo4j_ns['relation_count']}r / {neo4j_ns['chunk_count']}c"
    )

    qdrant = get_qdrant_stats(NAMESPACE)
    print(f"  Qdrant namespace '{NAMESPACE}': {qdrant.get('vector_count', '?')} vectors")

    # ══════════════════════════════════════════════════════════════════════════
    # Summary
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  RESULTS SUMMARY")
    print("=" * 80)

    print(
        f"\n{'File':<22} {'Size':>6} {'Time':>8} {'Status':<9} {'Chunks':>6} {'Ent':>5} {'Rel':>5}"
    )
    print("-" * 80)

    # Use Neo4j namespace-level stats (correct schema)
    total_ent = neo4j_ns["entity_count"]
    total_rel = neo4j_ns["relation_count"]
    total_chunks = neo4j_ns["chunk_count"]
    completed = sum(1 for r in results if r["status"] != "failed")

    # Per-file summary (from API response)
    for r in results:
        s = r["status"][:9]
        ent = r.get("api_entities", 0)
        rel = r.get("api_relations", 0)
        chunks = r.get("chunks_created", 0)
        dur = r["duration_s"]
        print(
            f"{r['filename']:<22} {r['filesize']:>5}B {dur:>7.1f}s {s:<9} {chunks:>6} {ent:>5} {rel:>5}"
        )

    print("-" * 80)
    total_size = sum(r["filesize"] for r in results)
    api_ent = sum(r.get("api_entities", 0) for r in results)
    api_rel = sum(r.get("api_relations", 0) for r in results)
    print(
        f"{'API TOTAL':<22} {total_size:>5}B {total_duration:>7.1f}s {completed}/{len(TEST_FILES):<8} "
        f"{'':>6} {api_ent:>5} {api_rel:>5}"
    )
    print(
        f"{'Neo4j TOTAL':<22} {'':>6} {'':>8} {'':>9} {total_chunks:>6} {total_ent:>5} {total_rel:>5}"
    )
    print(
        f"{'Qdrant vectors':<22} {'':>6} {'':>8} {'':>9} {'':>6} {'':>5} {qdrant.get('vector_count', 0):>5}"
    )

    # ── Entity Type Breakdown (namespace-level) ──────────────────────────────
    print(f"\n── Entity Types (namespace: {NAMESPACE}) ──")
    if neo4j_ns.get("entity_types_raw"):
        for line in neo4j_ns["entity_types_raw"].split("\n"):
            line = line.strip()
            if line and not line.startswith("+") and not line.startswith("t,"):
                print(f"  {line}")

    # ── Relation Type Breakdown ───────────────────────────────────────────────
    print(f"\n── Relation Types (namespace: {NAMESPACE}) ──")
    total_related_to = 0
    if neo4j_ns.get("relation_types_raw"):
        for line in neo4j_ns["relation_types_raw"].split("\n"):
            line = line.strip()
            if line and not line.startswith("+") and not line.startswith("t,"):
                print(f"  {line}")
                if '"RELATED_TO"' in line or line.startswith('"RELATED_TO"'):
                    parts = [p.strip().strip('"') for p in line.split(",")]
                    for p in parts:
                        if p.isdigit():
                            total_related_to += int(p)

    total_specific = total_rel - total_related_to

    # ── Entities per Document ──────────────────────────────────────────────────
    print(f"\n── Entities per Document (Neo4j) ──")
    if neo4j_ns.get("entities_per_doc_raw"):
        for line in neo4j_ns["entities_per_doc_raw"].split("\n"):
            line = line.strip()
            if line and not line.startswith("+") and not line.startswith("doc_id,"):
                print(f"  {line}")

    # ── Sample Entities ───────────────────────────────────────────────────────
    print(f"\n── Sample Entities ──")
    if neo4j_ns.get("sample_entities_raw"):
        for line in neo4j_ns["sample_entities_raw"].split("\n"):
            line = line.strip()
            if line and not line.startswith("+") and not line.startswith("name,"):
                print(f"  {line}")

    # ── Sample Relations ──────────────────────────────────────────────────────
    print(f"\n── Sample Relations ──")
    if neo4j_ns.get("sample_relations_raw"):
        for line in neo4j_ns["sample_relations_raw"].split("\n"):
            line = line.strip()
            if line and not line.startswith("+") and not line.startswith("subj,"):
                print(f"  {line}")

    # ── Quality Metrics ───────────────────────────────────────────────────────
    print(f"\n── Quality Metrics ──")
    if total_rel > 0:
        specificity = total_specific / total_rel * 100
        print(
            f"  Relation Specificity: {specificity:.1f}% ({total_specific}/{total_rel} non-RELATED_TO)"
        )
    if total_ent > 0:
        print(f"  Relations/Entity: {total_rel / total_ent:.1f}")
    print(f"  Entities/KB: {total_ent / total_size * 1024:.1f}")

    # ── Timing ────────────────────────────────────────────────────────────────
    completed_times = [r["duration_s"] for r in results if r["status"] != "failed"]
    if completed_times:
        print(f"\n── Timing ──")
        print(f"  Min: {min(completed_times):.1f}s")
        print(f"  Max: {max(completed_times):.1f}s")
        print(f"  Avg: {sum(completed_times) / len(completed_times):.1f}s")
        print(f"  Total: {total_duration:.1f}s")
        throughput_kb_per_min = (total_size / 1024) / (total_duration / 60)
        print(f"  Throughput: {throughput_kb_per_min:.2f} KB/min")

    # ── Config ────────────────────────────────────────────────────────────────
    print(f"\n── Configuration ──")
    print(f"  vLLM Image: eugr/spark-vllm-docker (vLLM 0.15.1, FlashInfer 0.6.3)")
    print(f"  VLLM_MOE_USE_DEEP_GEMM: 0 (OFF)")
    print(f"  gpu-memory-utilization: 0.45")
    print(f"  Engine Mode: auto (vLLM primary, Ollama {ollama_status})")
    print(f"  Cross-sentence windows: ON")
    print(f"  Finished: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ── Save JSON ─────────────────────────────────────────────────────────────
    output_dir = Path("/tmp/e2e_benchmark")
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"e2e_pipeline_benchmark_{ts}.json"

    # Clean raw fields for JSON serialization
    json_results = []
    for r in results:
        jr = {k: v for k, v in r.items() if not k.endswith("_raw")}
        json_results.append(jr)

    with open(output_file, "w") as f:
        json.dump(
            {
                "config": {
                    "vllm_image": "eugr/spark-vllm-docker",
                    "vllm_version": "0.15.1",
                    "deep_gemm": False,
                    "ollama": ollama_status,
                    "namespace": NAMESPACE,
                    "engine_mode": "auto (vLLM only)",
                    "gpu_memory_utilization": 0.45,
                    "cross_sentence": True,
                },
                "documents": json_results,
                "totals": {
                    "files": len(TEST_FILES),
                    "completed": completed,
                    "total_time_s": round(total_duration, 1),
                    "total_entities": total_ent,
                    "total_relations": total_rel,
                    "total_chunks": total_chunks,
                    "qdrant_vectors": qdrant.get("vector_count", 0),
                    "relation_specificity_pct": round(total_specific / total_rel * 100, 1)
                    if total_rel > 0
                    else 0,
                },
                "timestamp": datetime.datetime.now().isoformat(),
            },
            f,
            indent=2,
            default=str,
        )

    print(f"\n  Results saved: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
