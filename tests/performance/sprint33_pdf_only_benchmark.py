"""Sprint 33: PDF-Only Performance Benchmark.

Tests the PDF document after fixing Unicode logging issues.

Usage:
    poetry run python tests/performance/sprint33_pdf_only_benchmark.py
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

# Test document
PDF_PATH = Path(
    r"C:\Projekte\AEGISRAG\data\sample_documents\30. GAC\OMNITRACKER GDPR Anonymization Center GAC.pdf"
)


async def run_pdf_benchmark():
    """Run PDF benchmark."""

    print("=" * 70)
    print("SPRINT 33: PDF BENCHMARK (after Unicode fix)")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)

    if not PDF_PATH.exists():
        print(f"[ERROR] File not found: {PDF_PATH}")
        return

    print(f"\n[INFO] File: {PDF_PATH.name}")
    print(f"[INFO] Size: {PDF_PATH.stat().st_size / 1024:.1f} KB")

    # Verify cloud config
    print("\n[CONFIG] Verifying cloud routing...")
    from src.components.llm_proxy.config import LLMProxyConfig

    config = LLMProxyConfig.from_env()
    print(f"  prefer_cloud: {config.routing.get('prefer_cloud', False)}")
    print(f"  alibaba_cloud enabled: {config.is_provider_enabled('alibaba_cloud')}")

    print("\n[INFO] Starting pipeline...")
    start_time = time.perf_counter()

    try:
        import uuid

        from src.components.ingestion.langgraph_pipeline import run_ingestion_pipeline

        document_id = f"bench_pdf_{uuid.uuid4().hex[:8]}"
        batch_id = f"sprint33_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"[INFO] Document ID: {document_id}")
        print(f"[INFO] Batch ID: {batch_id}")

        result = await run_ingestion_pipeline(
            document_path=str(PDF_PATH),
            document_id=document_id,
            batch_id=batch_id,
            batch_index=0,
            total_documents=1,
        )

        end_time = time.perf_counter()
        duration = end_time - start_time

        print(f"\n[SUCCESS] Pipeline completed in {duration:.2f}s")

        # Save minimal results
        results_file = (
            RESULTS_DIR / f"sprint33_pdf_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        output = {
            "timestamp": datetime.now().isoformat(),
            "file_name": PDF_PATH.name,
            "file_size_kb": PDF_PATH.stat().st_size / 1024,
            "success": True,
            "duration_seconds": duration,
            "document_id": document_id,
        }

        # Extract key metrics if available
        if isinstance(result, dict):
            output["chunks_created"] = result.get("chunks_created", "N/A")
            output["embedding_status"] = result.get("embedding_status", "N/A")
            output["graph_status"] = result.get("graph_status", "N/A")

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        print(f"[INFO] Results saved to: {results_file}")

        return output

    except Exception as e:
        end_time = time.perf_counter()
        duration = end_time - start_time
        import traceback

        print(f"\n[ERROR] Pipeline failed after {duration:.2f}s")
        print(f"[ERROR] {type(e).__name__}: {e}")
        print(traceback.format_exc())

        return {
            "success": False,
            "error": str(e),
            "duration_seconds": duration,
        }


if __name__ == "__main__":
    asyncio.run(run_pdf_benchmark())
