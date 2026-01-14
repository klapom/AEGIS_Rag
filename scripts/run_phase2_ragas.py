#!/usr/bin/env python3
"""Sprint 88: RAGAS Evaluation for Phase 2 Samples (Tables + Code).

Runs RAGAS evaluation on the 10 Phase 2 samples:
- 5 T2-RAGBench (FinQA) - Financial table questions
- 5 Code QA (MBPP) - Programming questions

Usage:
    poetry run python scripts/run_phase2_ragas.py
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

logger = structlog.get_logger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
AUTH_URL = f"{API_BASE_URL}/api/v1/auth/login"
RETRIEVAL_URL = f"{API_BASE_URL}/api/v1/retrieval/query"

# Phase 2 metadata files
T2RAG_METADATA = Path("data/evaluation/phase2_samples/t2ragbench/t2ragbench_metadata.json")
CODE_METADATA = Path("data/evaluation/phase2_samples/codeqa/codeqa_metadata.json")


async def get_auth_token() -> str | None:
    """Get authentication token."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                AUTH_URL,
                json={"username": "admin", "password": "admin123"},
            )
            if response.status_code == 200:
                return response.json().get("access_token")
        except Exception as e:
            logger.error("Auth failed", error=str(e))
    return None


async def query_retrieval(question: str, token: str, mode: str = "hybrid") -> dict[str, Any]:
    """Query the retrieval API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                RETRIEVAL_URL,
                json={
                    "query": question,
                    "mode": mode,
                    "top_k": 5,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error("Query failed", error=str(e))
    return {}


def load_samples() -> list[dict]:
    """Load all Phase 2 samples from metadata files."""
    samples = []

    # Load T2-RAGBench
    if T2RAG_METADATA.exists():
        with open(T2RAG_METADATA) as f:
            data = json.load(f)
            for s in data.get("samples", []):
                s["dataset"] = "t2ragbench"
                samples.append(s)
        logger.info(f"Loaded {len(data.get('samples', []))} T2-RAGBench samples")

    # Load Code QA
    if CODE_METADATA.exists():
        with open(CODE_METADATA) as f:
            data = json.load(f)
            for s in data.get("samples", []):
                s["dataset"] = "codeqa"
                samples.append(s)
        logger.info(f"Loaded {len(data.get('samples', []))} Code QA samples")

    return samples


async def evaluate_sample(sample: dict, token: str) -> dict[str, Any]:
    """Evaluate a single sample with retrieval."""
    question = sample["question"]
    ground_truth = sample["answer"]

    start_time = time.time()
    result = await query_retrieval(question, token)
    latency_ms = (time.time() - start_time) * 1000

    # Extract contexts from retrieval result
    contexts = []
    if "results" in result:
        for r in result.get("results", []):
            if "content" in r:
                contexts.append(r["content"])
            elif "chunk" in r and "content" in r["chunk"]:
                contexts.append(r["chunk"]["content"])

    # Check if ground truth appears in contexts (simple recall check)
    gt_in_context = any(str(ground_truth)[:20] in ctx for ctx in contexts)

    return {
        "id": sample["id"],
        "dataset": sample["dataset"],
        "question": question[:80] + "..." if len(question) > 80 else question,
        "ground_truth": str(ground_truth)[:50],
        "contexts_retrieved": len(contexts),
        "gt_in_context": gt_in_context,
        "latency_ms": round(latency_ms, 0),
        "contexts": contexts[:3],  # First 3 for analysis
    }


async def run_ragas_metrics(samples: list[dict], results: list[dict]) -> dict[str, float]:
    """Calculate RAGAS-like metrics manually (simplified)."""
    try:
        from ragas import evaluate
        from ragas.metrics import (
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        )
        from datasets import Dataset

        # Prepare data for RAGAS
        ragas_data = {
            "question": [],
            "answer": [],  # We'll use ground truth as answer for now
            "contexts": [],
            "ground_truth": [],
        }

        for sample, result in zip(samples, results):
            ragas_data["question"].append(sample["question"])
            ragas_data["answer"].append(str(sample["answer"]))  # Use GT as answer
            ragas_data["contexts"].append(result["contexts"] or ["No context retrieved"])
            ragas_data["ground_truth"].append(str(sample["answer"]))

        dataset = Dataset.from_dict(ragas_data)

        # Run RAGAS evaluation
        logger.info("Running RAGAS evaluation...")
        ragas_result = evaluate(
            dataset,
            metrics=[context_precision, context_recall],
        )

        return {
            "context_precision": ragas_result.get("context_precision", 0),
            "context_recall": ragas_result.get("context_recall", 0),
        }

    except ImportError:
        logger.warning("RAGAS not installed, using simplified metrics")

        # Simplified metrics
        gt_found = sum(1 for r in results if r["gt_in_context"])
        total = len(results)

        return {
            "simplified_recall": gt_found / total if total > 0 else 0,
            "avg_contexts": sum(r["contexts_retrieved"] for r in results) / total if total > 0 else 0,
        }


async def main():
    """Main evaluation flow."""
    print("\n" + "=" * 60)
    print("SPRINT 88: Phase 2 RAGAS Evaluation")
    print("=" * 60 + "\n")

    # Authenticate
    print("🔐 Authenticating...")
    token = await get_auth_token()
    if not token:
        print("❌ Authentication failed!")
        return 1

    # Load samples
    print("\n📂 Loading Phase 2 samples...")
    samples = load_samples()
    if not samples:
        print("❌ No samples found!")
        return 1

    print(f"   Loaded {len(samples)} samples total")

    # Evaluate each sample
    print("\n🔍 Evaluating retrieval quality...")
    results = []

    for i, sample in enumerate(samples):
        result = await evaluate_sample(sample, token)
        results.append(result)

        status = "✅" if result["gt_in_context"] else "❌"
        print(f"   [{i+1}/{len(samples)}] {result['id']}: {result['contexts_retrieved']} contexts, {result['latency_ms']:.0f}ms {status}")

    # Calculate metrics
    print("\n📊 Calculating metrics...")
    metrics = await run_ragas_metrics(samples, results)

    # Summary by dataset
    t2rag_results = [r for r in results if r["dataset"] == "t2ragbench"]
    code_results = [r for r in results if r["dataset"] == "codeqa"]

    t2rag_recall = sum(1 for r in t2rag_results if r["gt_in_context"]) / len(t2rag_results) if t2rag_results else 0
    code_recall = sum(1 for r in code_results if r["gt_in_context"]) / len(code_results) if code_results else 0

    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print("\n📈 Metrics by Dataset:")
    print(f"   T2-RAGBench (Tables):  {t2rag_recall*100:.1f}% GT in context ({sum(1 for r in t2rag_results if r['gt_in_context'])}/{len(t2rag_results)})")
    print(f"   Code QA (MBPP):        {code_recall*100:.1f}% GT in context ({sum(1 for r in code_results if r['gt_in_context'])}/{len(code_results)})")

    print("\n📊 Overall Metrics:")
    for metric, value in metrics.items():
        print(f"   {metric}: {value:.4f}")

    avg_latency = sum(r["latency_ms"] for r in results) / len(results)
    print(f"\n⏱️  Avg Latency: {avg_latency:.0f}ms")

    # Save results
    output_path = Path(f"docs/ragas/phase2_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "samples": len(samples),
            "metrics": metrics,
            "t2rag_recall": t2rag_recall,
            "code_recall": code_recall,
            "avg_latency_ms": avg_latency,
            "results": results,
        }, f, indent=2)

    print(f"\n💾 Results saved to: {output_path}")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
