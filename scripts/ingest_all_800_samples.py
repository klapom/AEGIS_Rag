#!/usr/bin/env python3
"""Sprint 88: Full Ingestion Pipeline (800 Samples) with Metrics Tracking.

Ingests:
- Phase 1: 500 plaintext samples (HotpotQA, RAGBench, LogQA)
- Phase 2a: 150 financial table samples (T2-RAGBench/FinQA)
- Phase 2b: 150 code samples (MBPP)

Usage:
    poetry run python scripts/ingest_all_800_samples.py
    poetry run python scripts/ingest_all_800_samples.py --phase 1 --max-samples 50
    poetry run python scripts/ingest_all_800_samples.py --phase 2 --max-samples 10
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

logger = structlog.get_logger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
AUTH_URL = f"{API_BASE_URL}/api/v1/auth/login"
UPLOAD_URL = f"{API_BASE_URL}/api/v1/retrieval/upload"
ADMIN_STATUS_URL = f"{API_BASE_URL}/api/v1/admin/upload-status"

# Data paths
PHASE1_CONTEXTS_DIR = Path("data/ragas_phase1_contexts")
PHASE2_T2RAG_DIR = Path("data/evaluation/phase2_samples_300/t2ragbench")
PHASE2_MBPP_DIR = Path("data/evaluation/phase2_samples_300/mbpp")

# Output
OUTPUT_DIR = Path("docs/ragas/sprint88_full_eval")

# Namespaces
NAMESPACE_PHASE1 = "ragas_phase1_sprint88"
NAMESPACE_T2RAG = "ragas_phase2_t2rag"
NAMESPACE_MBPP = "ragas_phase2_mbpp"


# Token management - refresh every 10 minutes to avoid 30-minute expiration
TOKEN_REFRESH_INTERVAL = 600  # 10 minutes in seconds
_token_timestamp: float = 0
_current_token: Optional[str] = None


async def get_auth_token(force_refresh: bool = False) -> Optional[str]:
    """Get authentication token with automatic refresh.

    Sprint 88 Fix: Token expires after 30 minutes. Refresh every 10 minutes
    to avoid 401 errors during long-running batch operations.
    """
    global _token_timestamp, _current_token

    # Check if we need to refresh
    if not force_refresh and _current_token:
        elapsed = time.time() - _token_timestamp
        if elapsed < TOKEN_REFRESH_INTERVAL:
            return _current_token
        print(f"   🔄 Token expired after {elapsed:.0f}s, refreshing...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                AUTH_URL,
                json={"username": "admin", "password": "admin123"},
            )
            if response.status_code == 200:
                _current_token = response.json().get("access_token")
                _token_timestamp = time.time()
                return _current_token
            logger.error("Auth failed", status=response.status_code)
        except Exception as e:
            logger.error("Auth exception", error=str(e))
    return None


async def upload_document(
    file_path: Path,
    namespace: str,
    domain: str = "research_papers",
) -> dict[str, Any]:
    """Upload a single document and track metrics.

    Sprint 88 Fix: Token is refreshed automatically via get_auth_token().
    """
    start_time = time.time()
    metrics = {
        "file": file_path.name,
        "namespace": namespace,
        "status": "pending",
        "ingestion_time_ms": 0,
        "characters_count": 0,
        "document_id": None,
        "error": None,
    }

    try:
        # Get fresh token (auto-refreshes if needed)
        token = await get_auth_token()
        if not token:
            metrics["status"] = "error"
            metrics["error"] = "Failed to get authentication token"
            return metrics

        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        metrics["characters_count"] = len(content)

        # Upload via Frontend API (increased timeout for full pipeline with entity extraction)
        # Sprint 100 Fix: SpaCy-First Pipeline can take 10-15 minutes per document
        # Increased timeout from 600s (10min) to 1800s (30min) to prevent premature failures
        async with httpx.AsyncClient(timeout=1800.0) as client:
            with open(file_path, "rb") as f:
                response = await client.post(
                    UPLOAD_URL,
                    files={"file": (file_path.name, f, "text/plain")},
                    data={"namespace_id": namespace, "domain": domain},
                    headers={"Authorization": f"Bearer {token}"},
                )

            if response.status_code == 200:
                result = response.json()
                metrics["document_id"] = result.get("document_id")
                metrics["status"] = "success"
            else:
                metrics["status"] = "failed"
                metrics["error"] = f"HTTP {response.status_code}: {response.text[:200]}"

    except Exception as e:
        metrics["status"] = "error"
        metrics["error"] = str(e)

    metrics["ingestion_time_ms"] = int((time.time() - start_time) * 1000)
    return metrics


async def ingest_phase(
    phase: int,
    max_samples: int = -1,
    output_file: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Ingest documents for a specific phase.

    Sprint 88 Fix: Token is now managed automatically by upload_document().
    """
    all_metrics = []

    if phase == 1:
        # Phase 1: Plaintext samples
        files = sorted(PHASE1_CONTEXTS_DIR.glob("*.txt"))
        namespace = NAMESPACE_PHASE1
        domain = "research_papers"
        phase_name = "Phase 1 (Plaintext)"
    elif phase == 2:
        # Phase 2a: T2-RAGBench + Phase 2b: MBPP
        files_t2rag = sorted(PHASE2_T2RAG_DIR.glob("*.txt"))
        files_mbpp = sorted(PHASE2_MBPP_DIR.glob("*.txt"))

        # Process T2-RAGBench
        print(f"\n📊 Processing T2-RAGBench ({len(files_t2rag)} files)...")
        for i, file_path in enumerate(files_t2rag):
            if max_samples > 0 and i >= max_samples // 2:
                break
            metrics = await upload_document(file_path, NAMESPACE_T2RAG, "financial")
            all_metrics.append(metrics)
            status = "✅" if metrics["status"] == "success" else "❌"
            print(f"   [{i+1}/{len(files_t2rag)}] {file_path.name}: {metrics['ingestion_time_ms']}ms {status}")

        # Process MBPP
        print(f"\n💻 Processing MBPP ({len(files_mbpp)} files)...")
        for i, file_path in enumerate(files_mbpp):
            if max_samples > 0 and i >= max_samples // 2:
                break
            metrics = await upload_document(file_path, NAMESPACE_MBPP, "programming")
            all_metrics.append(metrics)
            status = "✅" if metrics["status"] == "success" else "❌"
            print(f"   [{i+1}/{len(files_mbpp)}] {file_path.name}: {metrics['ingestion_time_ms']}ms {status}")

        return all_metrics
    else:
        print(f"❌ Unknown phase: {phase}")
        return []

    # Process files (Phase 1)
    if max_samples > 0:
        files = files[:max_samples]

    print(f"\n📁 Processing {phase_name} ({len(files)} files)...")
    for i, file_path in enumerate(files):
        metrics = await upload_document(file_path, namespace, domain)
        all_metrics.append(metrics)
        status = "✅" if metrics["status"] == "success" else "❌"
        print(f"   [{i+1}/{len(files)}] {file_path.name}: {metrics['ingestion_time_ms']}ms {status}")

        # Save progress every 50 documents
        if output_file and (i + 1) % 50 == 0:
            with open(output_file, "w", encoding="utf-8") as f:
                for m in all_metrics:
                    f.write(json.dumps(m) + "\n")
            print(f"   💾 Progress saved ({i+1} documents)")

    return all_metrics


async def main():
    """Main ingestion flow."""
    parser = argparse.ArgumentParser(description="Ingest RAGAS benchmark samples")
    parser.add_argument("--phase", type=int, default=0, help="Phase to ingest (1, 2, or 0 for all)")
    parser.add_argument("--max-samples", type=int, default=-1, help="Max samples per phase (-1 for all)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("SPRINT 88: Full Ingestion Pipeline (800 Samples)")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"ingestion_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    # Initial authentication (token will auto-refresh during processing)
    print("\n🔐 Authenticating...")
    token = await get_auth_token(force_refresh=True)
    if not token:
        print("❌ Authentication failed!")
        return 1
    print("✅ Token obtained (will auto-refresh every 10 minutes)")

    all_metrics = []

    # Phase 1
    if args.phase in [0, 1]:
        print("\n" + "=" * 40)
        print("PHASE 1: Plaintext Documents (500)")
        print("=" * 40)
        phase1_metrics = await ingest_phase(1, args.max_samples, output_file)
        all_metrics.extend(phase1_metrics)

    # Phase 2
    if args.phase in [0, 2]:
        print("\n" + "=" * 40)
        print("PHASE 2: Structured Documents (300)")
        print("=" * 40)
        phase2_metrics = await ingest_phase(2, args.max_samples, output_file)
        all_metrics.extend(phase2_metrics)

    # Save final results
    with open(output_file, "w", encoding="utf-8") as f:
        for m in all_metrics:
            f.write(json.dumps(m) + "\n")

    # Summary
    successful = sum(1 for m in all_metrics if m["status"] == "success")
    failed = sum(1 for m in all_metrics if m["status"] != "success")
    total_time = sum(m["ingestion_time_ms"] for m in all_metrics)
    total_chars = sum(m["characters_count"] for m in all_metrics)

    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"📊 Total Documents:    {len(all_metrics)}")
    print(f"✅ Successful:         {successful}")
    print(f"❌ Failed:             {failed}")
    print(f"⏱️  Total Time:         {total_time / 1000:.1f}s")
    print(f"📝 Total Characters:   {total_chars:,}")
    print(f"💾 Metrics saved to:   {output_file}")

    # Save summary JSON
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_documents": len(all_metrics),
        "successful": successful,
        "failed": failed,
        "total_time_ms": total_time,
        "total_characters": total_chars,
        "avg_time_ms": total_time / len(all_metrics) if all_metrics else 0,
    }
    summary_file = OUTPUT_DIR / "ingestion_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
