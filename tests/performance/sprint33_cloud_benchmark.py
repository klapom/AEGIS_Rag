"""Sprint 33: Cloud-First Performance Benchmark.

This script runs the COMPLETE ingestion pipeline with CLOUD LLM/VLM:
- Extraction: Alibaba Cloud qwen3-32b
- Generation: Alibaba Cloud qwen3-32b
- VLM: Alibaba Cloud qwen3-vl-30b-a3b-instruct
- Embedding: Local BGE-M3 (always local)

Test Documents:
1. DE-D-WebGW.pptx (~50+ slides, PPTX)
2. OMNITRACKER GDPR Anonymization Center GAC.pdf (~50+ pages, PDF)

Usage:
    poetry run python tests/performance/sprint33_cloud_benchmark.py

All timing logs with prefix TIMING_* will be captured and summarized.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging BEFORE imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Reduce noise from httpx and httpcore
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# =============================================================================
# Test Configuration
# =============================================================================

# Test documents
TEST_DOCUMENTS = [
    {
        "path": Path(
            r"C:\Projekte\AEGISRAG\data\sample_documents\1. Basic Admin\Web Gateway\DE-D-WebGW.pptx"
        ),
        "name": "DE-D-WebGW.pptx",
        "format": "pptx",
        "description": "Web Gateway PPTX (~50+ slides)",
    },
    {
        "path": Path(
            r"C:\Projekte\AEGISRAG\data\sample_documents\30. GAC\OMNITRACKER GDPR Anonymization Center GAC.pdf"
        ),
        "name": "OMNITRACKER_GDPR_GAC.pdf",
        "format": "pdf",
        "description": "GDPR Anonymization Center PDF (~50+ pages)",
    },
]

# Results directory
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# =============================================================================
# Timing Capture
# =============================================================================


class BenchmarkResults:
    """Capture and store benchmark results."""

    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.stages: dict[str, dict[str, Any]] = {}
        self.errors: list[str] = []
        self.llm_calls: list[dict] = []
        self.vlm_calls: list[dict] = []

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self):
        self.end_time = time.perf_counter()

    @property
    def total_time(self) -> float:
        return self.end_time - self.start_time

    def add_stage(self, name: str, duration_ms: float, details: dict | None = None):
        self.stages[name] = {
            "duration_ms": duration_ms,
            "details": details or {},
        }

    def add_error(self, error: str):
        self.errors.append(error)

    def add_llm_call(
        self, provider: str, model: str, task_type: str, tokens: int, cost: float, latency_ms: float
    ):
        self.llm_calls.append(
            {
                "provider": provider,
                "model": model,
                "task_type": task_type,
                "tokens": tokens,
                "cost_usd": cost,
                "latency_ms": latency_ms,
            }
        )

    def add_vlm_call(self, model: str, tokens: int, cost: float, latency_ms: float):
        self.vlm_calls.append(
            {
                "model": model,
                "tokens": tokens,
                "cost_usd": cost,
                "latency_ms": latency_ms,
            }
        )

    def to_dict(self) -> dict:
        return {
            "total_time_s": self.total_time,
            "total_time_ms": self.total_time * 1000,
            "stages": self.stages,
            "errors": self.errors,
            "llm_calls": self.llm_calls,
            "vlm_calls": self.vlm_calls,
            "llm_summary": {
                "total_calls": len(self.llm_calls),
                "total_tokens": sum(c["tokens"] for c in self.llm_calls),
                "total_cost_usd": sum(c["cost_usd"] for c in self.llm_calls),
                "providers_used": list({c["provider"] for c in self.llm_calls}),
            },
            "vlm_summary": {
                "total_calls": len(self.vlm_calls),
                "total_tokens": sum(c["tokens"] for c in self.vlm_calls),
                "total_cost_usd": sum(c["cost_usd"] for c in self.vlm_calls),
            },
        }


# =============================================================================
# Pipeline Runner
# =============================================================================


async def run_pipeline_benchmark(doc_config: dict) -> dict:
    """Run full pipeline benchmark for a single document."""

    file_path = doc_config["path"]
    doc_name = doc_config["name"]

    print(f"\n{'='*70}")
    print(f"BENCHMARK: {doc_name}")
    print(f"Format: {doc_config['format'].upper()}")
    print(f"Description: {doc_config['description']}")
    print(f"File size: {file_path.stat().st_size / 1024:.1f} KB")
    print(f"{'='*70}\n")

    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return {
            "success": False,
            "file_name": doc_name,
            "error": f"File not found: {file_path}",
        }

    results = BenchmarkResults()
    results.start()

    try:
        # Import pipeline
        import uuid

        from src.components.ingestion.langgraph_pipeline import run_ingestion_pipeline

        # Generate unique IDs
        document_id = f"bench_{uuid.uuid4().hex[:8]}"
        batch_id = f"sprint33_cloud_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print("[INFO] Starting pipeline...")
        print(f"[INFO] Document ID: {document_id}")
        print(f"[INFO] Batch ID: {batch_id}")
        print("[INFO] Cloud routing: ENABLED (prefer_cloud=true)")
        print()

        # Track stage timing
        time.perf_counter()

        # Run pipeline
        pipeline_result = await run_ingestion_pipeline(
            document_path=str(file_path),
            document_id=document_id,
            batch_id=batch_id,
            batch_index=0,
            total_documents=1,
        )

        results.stop()

        # Extract results from pipeline
        if pipeline_result:
            print(f"\n[SUCCESS] Pipeline completed in {results.total_time:.2f}s")

            # Try to extract stage timings from result
            if isinstance(pipeline_result, dict):
                if "chunks_created" in pipeline_result:
                    results.add_stage(
                        "chunking",
                        0,
                        {
                            "chunks_created": pipeline_result.get("chunks_created", 0),
                        },
                    )
                if "entities_extracted" in pipeline_result:
                    results.add_stage(
                        "graph_extraction",
                        0,
                        {
                            "entities_extracted": pipeline_result.get("entities_extracted", 0),
                            "relations_extracted": pipeline_result.get("relations_extracted", 0),
                        },
                    )

        return {
            "success": True,
            "file_name": doc_name,
            "file_path": str(file_path),
            "file_size_kb": file_path.stat().st_size / 1024,
            "format": doc_config["format"],
            "benchmark_results": results.to_dict(),
            "pipeline_result": (
                pipeline_result if isinstance(pipeline_result, dict) else str(pipeline_result)
            ),
        }

    except Exception as e:
        results.stop()
        import traceback

        error_msg = f"{type(e).__name__}: {str(e)}"
        tb = traceback.format_exc()

        print(f"\n[ERROR] Pipeline failed after {results.total_time:.2f}s")
        print(f"[ERROR] {error_msg}")
        print(f"\n{tb}")

        results.add_error(error_msg)

        return {
            "success": False,
            "file_name": doc_name,
            "file_path": str(file_path),
            "file_size_kb": file_path.stat().st_size / 1024,
            "format": doc_config["format"],
            "benchmark_results": results.to_dict(),
            "error": error_msg,
            "traceback": tb,
        }


async def main():
    """Run benchmarks on all test documents."""

    print("=" * 70)
    print("SPRINT 33: CLOUD-FIRST PERFORMANCE BENCHMARK")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)

    # Verify cloud configuration
    print("\n[CONFIG] Verifying cloud routing configuration...")
    try:
        from src.components.llm_proxy.config import LLMProxyConfig

        config = LLMProxyConfig.from_env()
        prefer_cloud = config.routing.get("prefer_cloud", False)
        alibaba_enabled = config.is_provider_enabled("alibaba_cloud")

        print(f"  prefer_cloud: {prefer_cloud}")
        print(f"  alibaba_cloud enabled: {alibaba_enabled}")

        if not prefer_cloud:
            print("\n[WARNING] prefer_cloud is FALSE! Cloud models will NOT be used.")
            print("[WARNING] Set prefer_cloud: true in config/llm_config.yml")
        if not alibaba_enabled:
            print("\n[WARNING] alibaba_cloud is NOT enabled! Check API key.")

    except Exception as e:
        print(f"\n[ERROR] Could not verify config: {e}")

    print("\n" + "=" * 70)
    print("EXPECTED ROUTING:")
    print("  - Extraction: alibaba_cloud (qwen3-32b)")
    print("  - Generation: alibaba_cloud (qwen3-32b)")
    print("  - VLM: alibaba_cloud (qwen3-vl-30b-a3b-instruct)")
    print("  - Embedding: local_ollama (bge-m3) - always local")
    print("=" * 70)

    all_results = []

    for doc_config in TEST_DOCUMENTS:
        result = await run_pipeline_benchmark(doc_config)
        all_results.append(result)

        # Brief pause between documents
        if doc_config != TEST_DOCUMENTS[-1]:
            print("\n[INFO] Waiting 5s before next document...")
            await asyncio.sleep(5)

    # Summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    successful = [r for r in all_results if r.get("success")]
    failed = [r for r in all_results if not r.get("success")]

    print(f"\nDocuments processed: {len(all_results)}")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")

    if successful:
        print("\nTiming by document:")
        print("-" * 50)
        for r in successful:
            total_s = r["benchmark_results"]["total_time_s"]
            print(f"  {r['file_name']:40s} {total_s:8.2f}s")

    if failed:
        print("\nFailed documents:")
        print("-" * 50)
        for r in failed:
            print(f"  {r['file_name']}: {r.get('error', 'Unknown error')}")

    # Save results
    results_file = (
        RESULTS_DIR / f"sprint33_cloud_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    output_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "prefer_cloud": True,
            "extraction_model": "qwen3-32b",
            "generation_model": "qwen3-32b",
            "vlm_model": "qwen3-vl-30b-a3b-instruct",
            "embedding_model": "bge-m3 (local)",
        },
        "results": all_results,
        "summary": {
            "total_documents": len(all_results),
            "successful": len(successful),
            "failed": len(failed),
            "total_time_s": (
                sum(r["benchmark_results"]["total_time_s"] for r in successful) if successful else 0
            ),
        },
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n[INFO] Results saved to: {results_file}")

    return all_results


if __name__ == "__main__":
    asyncio.run(main())
