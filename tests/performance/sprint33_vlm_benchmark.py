"""Sprint 33: VLM Image Enrichment Benchmark.

Tests the full pipeline with VLM image processing after Sprint 33 fixes:
- PictureItemWrapper with get_image() method
- BBoxWrapper with l, t, r, b attributes
- Cloud VLM (qwen3-vl) for image description

Usage:
    poetry run python tests/performance/sprint33_vlm_benchmark.py
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging BEFORE imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Results directory
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Test documents (with correct paths)
TEST_FILES = [
    Path(r"C:\Projekte\AEGISRAG\data\sample_documents\1. Basic Admin\Web Gateway\DE-D-WebGW.pptx"),
    Path(r"C:\Projekte\AEGISRAG\data\sample_documents\30. GAC\OMNITRACKER GDPR Anonymization Center GAC.pdf"),
]


async def run_vlm_benchmark():
    """Run VLM benchmark."""
    print("=" * 70)
    print("SPRINT 33: VLM IMAGE ENRICHMENT BENCHMARK")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)

    # Verify cloud config
    print("\n[CONFIG] Verifying cloud routing...")
    from src.components.llm_proxy.config import LLMProxyConfig
    config = LLMProxyConfig.from_env()
    print(f"  prefer_cloud: {config.routing.get('prefer_cloud', False)}")
    print(f"  alibaba_cloud enabled: {config.is_provider_enabled('alibaba_cloud')}")

    results = []

    for test_file in TEST_FILES:
        if not test_file.exists():
            print(f"\n[SKIP] File not found: {test_file}")
            continue

        print(f"\n[FILE] {test_file.name}")
        print(f"[SIZE] {test_file.stat().st_size / 1024:.1f} KB")
        print("-" * 50)

        start_time = time.perf_counter()

        try:
            import uuid

            from src.components.ingestion.langgraph_pipeline import run_ingestion_pipeline

            document_id = f"vlm_bench_{uuid.uuid4().hex[:8]}"
            batch_id = f"sprint33_vlm_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            print(f"[INFO] Document ID: {document_id}")
            print("[INFO] Starting pipeline with VLM enrichment...")

            result = await run_ingestion_pipeline(
                document_path=str(test_file),
                document_id=document_id,
                batch_id=batch_id,
                batch_index=0,
                total_documents=1,
            )

            end_time = time.perf_counter()
            duration = end_time - start_time

            print(f"\n[SUCCESS] Pipeline completed in {duration:.2f}s")

            # Extract metrics
            output = {
                "timestamp": datetime.now().isoformat(),
                "file_name": test_file.name,
                "file_size_kb": test_file.stat().st_size / 1024,
                "success": True,
                "duration_seconds": duration,
                "document_id": document_id,
            }

            if isinstance(result, dict):
                output["chunks_created"] = result.get("chunks_created", "N/A")
                output["embedding_status"] = result.get("embedding_status", "N/A")
                output["graph_status"] = result.get("graph_status", "N/A")
                output["enrichment_status"] = result.get("enrichment_status", "N/A")
                output["vlm_images_processed"] = len(result.get("vlm_metadata", []))

            results.append(output)
            print(f"[VLM] Images processed: {output.get('vlm_images_processed', 0)}")

        except Exception as e:
            end_time = time.perf_counter()
            duration = end_time - start_time
            import traceback

            print(f"\n[ERROR] Pipeline failed after {duration:.2f}s")
            print(f"[ERROR] {type(e).__name__}: {e}")
            traceback.print_exc()

            results.append({
                "file_name": test_file.name,
                "success": False,
                "error": str(e),
                "duration_seconds": duration,
            })

    # Save results
    results_file = RESULTS_DIR / f"sprint33_vlm_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'=' * 70}")
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    for r in results:
        status = "SUCCESS" if r.get("success") else "FAILED"
        vlm = r.get("vlm_images_processed", "N/A")
        print(f"  {r['file_name']}: {status} ({r.get('duration_seconds', 0):.1f}s, VLM: {vlm} images)")
    print(f"\n[INFO] Results saved to: {results_file}")

    return results


if __name__ == "__main__":
    asyncio.run(run_vlm_benchmark())
