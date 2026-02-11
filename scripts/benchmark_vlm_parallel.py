#!/usr/bin/env python3
"""Sprint 129.6g: VLM Parallel Pages A/B Benchmark.

Compares ingestion with VLM parallel enabled vs disabled.
Uses frontend API (same path as real users).

Test documents:
  - VM3.pdf: 13 pages, complex tables (5.9MB)
  - DP-Bench PDFs: Known table-containing documents
  - RAGAS TXT files: Text-only control (no tables, VLM should be no-op)

Usage:
    poetry run python scripts/benchmark_vlm_parallel.py
    poetry run python scripts/benchmark_vlm_parallel.py --phase A  # VLM enabled only
    poetry run python scripts/benchmark_vlm_parallel.py --phase B  # VLM disabled only
"""

import argparse
import json
import os
import sys
import time

import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# Test documents — mix of table-heavy PDFs and text-only TXT
PDF_DIR = "data/evaluation/test_datasets/dp_bench_pdfs/dataset/pdfs"
RAGAS_DIR = "data/ragas_phase1_contexts"

# Selected test files for benchmark
TEST_FILES = [
    # Table-heavy PDFs
    {"path": f"{PDF_DIR}/VM3.pdf", "type": "pdf", "desc": "VM3 - 13pg complex tables"},
    {"path": f"{PDF_DIR}/01030000000045.pdf", "type": "pdf", "desc": "DP-Bench 45 - tables"},
    {"path": f"{PDF_DIR}/01030000000046.pdf", "type": "pdf", "desc": "DP-Bench 46 - tables"},
    # Text-only control (TXT → VLM pipeline should be skipped)
    {
        "path": f"{RAGAS_DIR}/ragas_phase1_0003_hotpot_5a82171f.txt",
        "type": "txt",
        "desc": "RAGAS hotpot (text)",
    },
    {
        "path": f"{RAGAS_DIR}/ragas_phase1_0012_ragbench_techqaTR.txt",
        "type": "txt",
        "desc": "RAGAS techQA (text)",
    },
]


def authenticate() -> str:
    """Get JWT token for API access."""
    username = "benchmark_bot"
    password = "benchmark_secure_123"  # pragma: allowlist secret

    resp = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("access_token", "")

    requests.post(
        f"{API_BASE}/api/v1/auth/register",
        json={
            "username": username,
            "password": password,
            "email": "bench@test.local",
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
        print(f"Auth failed: {resp.status_code}")
        sys.exit(1)
    return resp.json().get("access_token", "")


def set_vlm_parallel(enabled: bool, token: str) -> bool:
    """Toggle VLM parallel pages via API."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.put(
        f"{API_BASE}/api/v1/admin/vlm/parallel-pages",
        json={"enabled": enabled},
        headers=headers,
        timeout=10,
    )
    if resp.status_code == 200:
        result = resp.json()
        print(f"  VLM parallel: {'ENABLED' if result.get('enabled') else 'DISABLED'}")
        return True
    print(f"  Failed to set VLM parallel: {resp.status_code}")
    return False


def get_vlm_status(token: str) -> dict:
    """Get VLM parallel status."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"{API_BASE}/api/v1/admin/vlm/parallel-pages",
        headers=headers,
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else {}


def upload_document(filepath: str, namespace: str, token: str) -> dict:
    """Upload a document via frontend API."""
    headers = {"Authorization": f"Bearer {token}"}
    filename = os.path.basename(filepath)
    content_type = "application/pdf" if filepath.endswith(".pdf") else "text/plain"

    with open(filepath, "rb") as f:
        files = {"file": (filename, f, content_type)}
        data = {"namespace_id": namespace, "domain_id": "auto"}
        start = time.time()
        try:
            resp = requests.post(
                f"{API_BASE}/api/v1/retrieval/upload",
                headers=headers,
                files=files,
                data=data,
                timeout=1800,
            )
        except requests.exceptions.Timeout:
            return {
                "file": filename,
                "status": "timeout",
                "upload_time_s": round(time.time() - start, 1),
            }
        upload_time = time.time() - start

    if resp.status_code not in (200, 201):
        return {
            "file": filename,
            "status": "failed",
            "error": resp.text[:300],
            "upload_time_s": round(upload_time, 1),
        }

    result = resp.json()
    return {
        "file": filename,
        "status": result.get("status", "unknown"),
        "upload_time_s": round(upload_time, 1),
        "chunks_created": result.get("chunks_created", 0),
        "neo4j_entities": result.get("neo4j_entities", 0),
        "neo4j_relationships": result.get("neo4j_relationships", 0),
        "points_indexed": result.get("points_indexed", 0),
        "duration_seconds": result.get("duration_seconds", 0),
        "response": result,
    }


def run_phase(phase_name: str, vlm_enabled: bool, token: str, files: list[dict]) -> list[dict]:
    """Run one phase of the benchmark (A or B)."""
    namespace = f"vlm_bench_{phase_name.lower()}_{'on' if vlm_enabled else 'off'}"

    print(f"\n{'=' * 70}")
    print(f"Phase {phase_name}: VLM Parallel {'ENABLED' if vlm_enabled else 'DISABLED'}")
    print(f"Namespace: {namespace}")
    print(f"{'=' * 70}")

    set_vlm_parallel(vlm_enabled, token)
    time.sleep(2)  # Let Redis propagate

    # Verify state
    status = get_vlm_status(token)
    print(f"  Confirmed: enabled={status.get('enabled')}, vlm_healthy={status.get('vlm_healthy')}")

    results = []
    phase_start = time.time()

    for i, file_info in enumerate(files):
        filepath = file_info["path"]
        if not os.path.exists(filepath):
            print(f"\n  [{i + 1}/{len(files)}] SKIP - {filepath} not found")
            continue

        size_kb = os.path.getsize(filepath) / 1024
        print(f"\n  [{i + 1}/{len(files)}] {file_info['desc']} ({size_kb:.0f} KB)")
        sys.stdout.flush()

        result = upload_document(filepath, namespace, token)
        result["file_type"] = file_info["type"]
        result["description"] = file_info["desc"]

        status_str = result["status"]
        time_str = f"{result['upload_time_s']:.1f}s"
        print(f"    Status: {status_str} | Time: {time_str}")

        if status_str in ("success", "partial"):
            print(f"    Chunks: {result.get('chunks_created', 0)}")
            print(f"    Entities: {result.get('neo4j_entities', 0)}")
            print(f"    Relations: {result.get('neo4j_relationships', 0)}")

        results.append(result)

        # Re-authenticate every 2 docs to avoid JWT expiry
        if i > 0 and i % 2 == 0:
            token = authenticate()

    phase_time = time.time() - phase_start
    print(f"\n  Phase {phase_name} total: {phase_time:.1f}s ({phase_time / 60:.1f} min)")

    return results


def compare_results(results_a: list[dict], results_b: list[dict]) -> None:
    """Compare Phase A (VLM on) vs Phase B (VLM off)."""
    print(f"\n{'=' * 70}")
    print("COMPARISON: VLM ON vs VLM OFF")
    print(f"{'=' * 70}")

    # Align by filename
    b_by_file = {r["file"]: r for r in results_b}

    header = f"{'File':<35} {'Type':<5} {'VLM ON':<12} {'VLM OFF':<12} {'Speedup':<10} {'Entities':<12} {'Relations':<12}"
    print(f"\n{header}")
    print("-" * len(header))

    total_a, total_b = 0, 0
    for r_a in results_a:
        fname = r_a["file"]
        r_b = b_by_file.get(fname, {})

        time_a = r_a.get("upload_time_s", 0)
        time_b = r_b.get("upload_time_s", 0)
        total_a += time_a
        total_b += time_b

        speedup = f"{time_b / time_a:.2f}x" if time_a > 0 else "N/A"
        ent_a = r_a.get("neo4j_entities", "-")
        ent_b = r_b.get("neo4j_entities", "-")
        rel_a = r_a.get("neo4j_relationships", "-")
        rel_b = r_b.get("neo4j_relationships", "-")

        ftype = r_a.get("file_type", "?")
        print(
            f"{fname:<35} {ftype:<5} "
            f"{time_a:>7.1f}s    {time_b:>7.1f}s    {speedup:<10} "
            f"{ent_a:>3}/{ent_b:<3}      {rel_a:>3}/{rel_b:<3}"
        )

    print(f"\n{'TOTAL':<35} {'':5} {total_a:>7.1f}s    {total_b:>7.1f}s    ", end="")
    if total_a > 0:
        print(f"{total_b / total_a:.2f}x")
    else:
        print("N/A")

    print(
        f"\nVLM ON overhead: {total_a - total_b:+.1f}s ({(total_a - total_b) / max(total_b, 1) * 100:+.1f}%)"
    )


def main():
    parser = argparse.ArgumentParser(description="VLM Parallel Pages A/B Benchmark")
    parser.add_argument(
        "--phase",
        choices=["A", "B", "both"],
        default="both",
        help="Run phase A (VLM on), B (VLM off), or both",
    )
    parser.add_argument("--max-docs", type=int, default=5)
    args = parser.parse_args()

    # Filter to available files
    files = [f for f in TEST_FILES[: args.max_docs] if os.path.exists(f["path"])]
    if not files:
        print("No test files found!")
        sys.exit(1)

    print(f"Test files ({len(files)}):")
    for f in files:
        size = os.path.getsize(f["path"])
        print(f"  - {f['desc']}: {size:,} bytes")

    # Authenticate
    print("\n--- Authentication ---")
    token = authenticate()
    print(f"Token: {token[:20]}...")

    results_a, results_b = [], []

    if args.phase in ("A", "both"):
        results_a = run_phase("A", vlm_enabled=True, token=token, files=files)

    if args.phase in ("B", "both"):
        token = authenticate()  # Refresh token
        results_b = run_phase("B", vlm_enabled=False, token=token, files=files)

    if results_a and results_b:
        compare_results(results_a, results_b)

    # Save results
    outfile = "vlm_parallel_benchmark.json"
    with open(outfile, "w") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "phase_a_vlm_on": results_a,
                "phase_b_vlm_off": results_b,
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\nResults saved to: {outfile}")

    # Restore VLM to enabled (default state)
    token = authenticate()
    set_vlm_parallel(True, token)


if __name__ == "__main__":
    main()
