"""Full End-to-End Ingestion Pipeline Benchmark.

This script runs the COMPLETE ingestion pipeline with detailed timing logs:
1. Docling Parsing (GPU-accelerated)
2. Section Extraction (ADR-039)
3. Adaptive Chunking
4. Embedding Generation (BGE-M3 via Ollama)
5. Qdrant Vector Storage
6. Neo4j Graph Storage (optional)

Usage:
    poetry run python tests/performance/full_pipeline_benchmark.py

All timing logs with prefix TIMING_* will be captured and summarized.
"""

import asyncio
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TimingLogCapture(logging.Handler):
    """Custom handler to capture TIMING_* log entries."""

    def __init__(self):
        super().__init__()
        self.timing_logs: list[dict[str, Any]] = []
        self.current_document: str = ""

    def emit(self, record: logging.LogRecord):
        msg = record.getMessage()
        # Check if this is a TIMING_ log (structlog format)
        if "TIMING_" in msg:
            self.timing_logs.append({
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "document": self.current_document,
                "message": msg,
                "level": record.levelname,
            })

    def get_timings_for_document(self, doc_name: str) -> list[dict]:
        return [t for t in self.timing_logs if t["document"] == doc_name]

    def clear(self):
        self.timing_logs = []


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Add timing capture handler to root logger
timing_capture = TimingLogCapture()
logging.getLogger().addHandler(timing_capture)

# Also add to structlog if available
try:
    import structlog
    # structlog logs go through standard logging, so our handler will catch them
except ImportError:
    pass

# Test documents (OneDrive paths)
ONEDRIVE_BASE = Path(
    r"C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\data\sample_documents"
)

TEST_DOCUMENTS = [
    # Text-only documents (should be fastest)
    ("99_pptx_text/PerformanceTuning_textonly.pptx", "text-only", "pptx"),
    ("99_pdf_text/PerformanceTuning_textonly.pdf", "text-only", "pdf"),
    # Graphics-heavy documents (OCR required)
    ("99_pptx_graphics/PerformanceTuning_graphics.pptx", "graphics", "pptx"),
    ("99_pdf_graphics/PerformanceTuning_graphics.pdf", "graphics", "pdf"),
    # Mixed content (real-world scenario)
    ("9. Performance Tuning/EN-D-Performance Tuning.pdf", "mixed", "pdf"),
]

# Results directory
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def parse_timing_from_log(log_msg: str) -> dict[str, Any]:
    """Extract timing values from structlog formatted message."""
    result = {}

    # Extract the event name (TIMING_*)
    timing_match = re.search(r'(TIMING_\w+)', log_msg)
    if timing_match:
        result["event"] = timing_match.group(1)

    # Extract simple key=value pairs (numbers, strings without spaces)
    simple_pattern = r'(\w+)=([\d.]+)(?:\s|$)'
    for match in re.finditer(simple_pattern, log_msg):
        key, value = match.groups()
        try:
            if "." in value:
                result[key] = float(value)
            else:
                result[key] = int(value)
        except ValueError:
            result[key] = value

    # Extract quoted string values
    quoted_pattern = r'(\w+)=["\']([^"\']+)["\']'
    for match in re.finditer(quoted_pattern, log_msg):
        key, value = match.groups()
        result[key] = value

    # Extract dict-like values (e.g., timing_breakdown={...})
    # structlog prints dicts as {'key': value, ...}
    dict_pattern = r"(\w+)=\{([^}]+)\}"
    for match in re.finditer(dict_pattern, log_msg):
        key, dict_content = match.groups()
        # Parse the dict content
        nested = {}
        # Handle both 'key': value and key=value formats
        item_pattern = r"['\"]?(\w+)['\"]?\s*[:=]\s*([\d.]+)"
        for item_match in re.finditer(item_pattern, dict_content):
            item_key, item_value = item_match.groups()
            try:
                if "." in item_value:
                    nested[item_key] = float(item_value)
                else:
                    nested[item_key] = int(item_value)
            except ValueError:
                nested[item_key] = item_value
        if nested:
            result[key] = nested

    return result


def extract_stage_timings(timing_logs: list[dict]) -> dict[str, dict]:
    """Extract and organize timing data by pipeline stage."""
    stages = {
        "docling_parse": {"duration_ms": None, "details": {}},
        "chunking": {"duration_ms": None, "details": {}},
        "embedding": {"duration_ms": None, "details": {}},
        "graph_extraction": {"duration_ms": None, "details": {}},
        "pipeline_total": {"duration_ms": None, "details": {}},
    }

    for log_entry in timing_logs:
        parsed = parse_timing_from_log(log_entry["message"])
        event = parsed.get("event", "")

        # Map events to stages and extract timing
        if event == "TIMING_docling_parse_complete":
            stages["docling_parse"]["duration_ms"] = parsed.get("duration_ms")
            # Extract nested timing_breakdown if available
            timing_breakdown = parsed.get("timing_breakdown", {})
            stages["docling_parse"]["details"] = {
                "file_upload_ms": timing_breakdown.get("file_upload_ms"),
                "task_polling_ms": timing_breakdown.get("task_polling_ms"),
                "result_download_ms": timing_breakdown.get("result_download_ms"),
                "throughput_kb_per_sec": parsed.get("throughput_kb_per_sec"),
                "text_length": parsed.get("text_length"),
                "tables_count": parsed.get("tables_count"),
                "images_count": parsed.get("images_count"),
            }

        elif event == "TIMING_chunking_complete":
            stages["chunking"]["duration_ms"] = parsed.get("duration_ms")
            timing_breakdown = parsed.get("timing_breakdown", {})
            stages["chunking"]["details"] = {
                "final_chunks": parsed.get("final_chunks"),
                "adaptive_chunks": parsed.get("adaptive_chunks"),
                "original_sections": parsed.get("original_sections"),
                "total_tokens": parsed.get("total_tokens"),
                "avg_tokens_per_chunk": parsed.get("avg_tokens_per_chunk"),
                "section_extraction_ms": timing_breakdown.get("section_extraction_ms"),
                "adaptive_merge_ms": timing_breakdown.get("adaptive_merge_ms"),
            }

        elif event == "TIMING_embedding_complete":
            stages["embedding"]["duration_ms"] = parsed.get("duration_ms")
            timing_breakdown = parsed.get("timing_breakdown", {})
            stages["embedding"]["details"] = {
                "points_uploaded": parsed.get("points_uploaded"),
                "points_with_images": parsed.get("points_with_images"),
                "embedding_generation_ms": timing_breakdown.get("embedding_generation_ms"),
                "qdrant_upsert_ms": timing_breakdown.get("qdrant_upsert_ms"),
            }

        elif event == "TIMING_graph_extraction_complete":
            stages["graph_extraction"]["duration_ms"] = parsed.get("duration_ms")
            timing_breakdown = parsed.get("timing_breakdown", {})
            stages["graph_extraction"]["details"] = {
                "total_entities": parsed.get("total_entities"),
                "total_relations": parsed.get("total_relations"),
                "total_chunks": parsed.get("total_chunks"),
                "section_nodes_created": parsed.get("section_nodes_created"),
                "lightrag_insert_ms": timing_breakdown.get("lightrag_insert_ms"),
                "section_nodes_ms": timing_breakdown.get("section_nodes_ms"),
            }

        elif event == "TIMING_pipeline_complete":
            stages["pipeline_total"]["duration_ms"] = parsed.get("total_ms")
            performance_summary = parsed.get("performance_summary", {})
            node_timings = parsed.get("node_timings_ms", {})
            stages["pipeline_total"]["details"] = {
                "total_seconds": parsed.get("total_seconds"),
                "throughput_mb_per_sec": parsed.get("throughput_mb_per_sec"),
                "chunks_created": parsed.get("chunks_created"),
                "entities_extracted": parsed.get("entities_extracted"),
                "sections_created": parsed.get("sections_created"),
                "slowest_node": parsed.get("slowest_node"),
                "slowest_duration_ms": parsed.get("slowest_duration_ms"),
                "parse_ms": performance_summary.get("parse_ms") or node_timings.get("parse"),
                "chunk_ms": performance_summary.get("chunk_ms") or node_timings.get("chunking"),
                "embed_ms": performance_summary.get("embed_ms") or node_timings.get("embedding"),
                "graph_ms": performance_summary.get("graph_ms") or node_timings.get("graph"),
            }

    return stages


async def run_full_pipeline(file_path: Path, timing_capture: TimingLogCapture) -> dict:
    """Run the complete ingestion pipeline for a single document."""
    import uuid
    from src.components.ingestion.langgraph_pipeline import run_ingestion_pipeline

    timing_capture.current_document = file_path.name

    print(f"\n{'='*70}")
    print(f"FULL PIPELINE BENCHMARK: {file_path.name}")
    print(f"File size: {file_path.stat().st_size / 1024:.1f} KB")
    print(f"{'='*70}\n")

    start_time = time.perf_counter()

    # Generate unique IDs for this benchmark run
    document_id = f"bench_{uuid.uuid4().hex[:8]}"
    batch_id = f"perf_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        # Run the full pipeline with required parameters
        result = await run_ingestion_pipeline(
            document_path=str(file_path),
            document_id=document_id,
            batch_id=batch_id,
            batch_index=0,
            total_documents=1,
        )

        total_time = time.perf_counter() - start_time

        # Extract timing data from captured logs
        doc_timings = timing_capture.get_timings_for_document(file_path.name)
        stage_timings = extract_stage_timings(doc_timings)

        print(f"\n{'='*70}")
        print(f"BENCHMARK COMPLETE: {file_path.name}")
        print(f"Total time: {total_time:.2f}s ({total_time*1000:.0f}ms)")
        print(f"{'='*70}")

        # Print stage breakdown
        print("\nSTAGE BREAKDOWN:")
        print("-" * 50)
        for stage_name, stage_data in stage_timings.items():
            duration = stage_data.get("duration_ms")
            if duration is not None:
                pct = (duration / (total_time * 1000)) * 100 if total_time > 0 else 0
                print(f"  {stage_name:25s}: {duration:8.1f}ms ({pct:5.1f}%)")
                for detail_key, detail_val in stage_data.get("details", {}).items():
                    if detail_val is not None:
                        print(f"    - {detail_key}: {detail_val}")
        print("-" * 50)

        return {
            "success": True,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size_kb": file_path.stat().st_size / 1024,
            "total_time_s": total_time,
            "total_time_ms": total_time * 1000,
            "stage_timings": stage_timings,
            "timing_logs_count": len(doc_timings),
        }

    except Exception as e:
        total_time = time.perf_counter() - start_time
        print(f"\n[ERROR] Pipeline failed after {total_time:.2f}s: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size_kb": file_path.stat().st_size / 1024,
            "total_time_s": total_time,
            "total_time_ms": total_time * 1000,
            "error": str(e),
        }


def identify_bottlenecks(results: list[dict]) -> dict:
    """Analyze results to identify performance bottlenecks."""
    bottlenecks = {
        "slowest_stage_overall": None,
        "slowest_stage_by_category": {},
        "recommendations": [],
    }

    # Aggregate stage timings across all documents
    stage_totals: dict[str, list[float]] = {}
    category_stage_totals: dict[str, dict[str, list[float]]] = {}

    for r in results:
        if not r.get("success"):
            continue

        category = r.get("category", "unknown")
        if category not in category_stage_totals:
            category_stage_totals[category] = {}

        stage_timings = r.get("stage_timings", {})
        for stage_name, stage_data in stage_timings.items():
            duration = stage_data.get("duration_ms")
            if duration is not None:
                if stage_name not in stage_totals:
                    stage_totals[stage_name] = []
                stage_totals[stage_name].append(duration)

                if stage_name not in category_stage_totals[category]:
                    category_stage_totals[category][stage_name] = []
                category_stage_totals[category][stage_name].append(duration)

    # Find slowest stage overall
    if stage_totals:
        avg_by_stage = {
            stage: sum(times) / len(times)
            for stage, times in stage_totals.items()
        }
        slowest = max(avg_by_stage, key=avg_by_stage.get)
        bottlenecks["slowest_stage_overall"] = {
            "stage": slowest,
            "avg_ms": avg_by_stage[slowest],
            "all_stages_avg": avg_by_stage,
        }

        # Generate recommendations
        if slowest == "docling_parse":
            bottlenecks["recommendations"].append(
                "Docling parsing is the bottleneck. Consider: "
                "1) Ensure CUDA container is running, "
                "2) Check VRAM availability (>5.5GB needed), "
                "3) Pre-process large PDFs into smaller chunks"
            )
        elif slowest == "embedding":
            bottlenecks["recommendations"].append(
                "Embedding generation is the bottleneck. Consider: "
                "1) Increase batch size, "
                "2) Enable embedding cache, "
                "3) Use GPU-accelerated embedding model"
            )
        elif slowest == "graph_extraction":
            bottlenecks["recommendations"].append(
                "Graph extraction is the bottleneck. Consider: "
                "1) Use faster LLM model for extraction, "
                "2) Reduce entity extraction scope, "
                "3) Batch entity extraction calls"
            )

    # Find slowest stage by category
    for category, stages in category_stage_totals.items():
        if stages:
            avg_by_stage = {
                stage: sum(times) / len(times)
                for stage, times in stages.items()
            }
            slowest = max(avg_by_stage, key=avg_by_stage.get)
            bottlenecks["slowest_stage_by_category"][category] = {
                "stage": slowest,
                "avg_ms": avg_by_stage[slowest],
            }

    return bottlenecks


async def main():
    """Run benchmarks on all test documents."""
    print("=" * 70)
    print("AEGISRAG FULL PIPELINE PERFORMANCE BENCHMARK")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Results will be saved to: {RESULTS_DIR}")
    print("=" * 70)

    results = []

    for doc_path, category, format_type in TEST_DOCUMENTS:
        full_path = ONEDRIVE_BASE / doc_path

        if not full_path.exists():
            print(f"\n[SKIP] Document not found: {full_path}")
            continue

        print(f"\n[{category.upper()} / {format_type.upper()}] Processing {full_path.name}...")
        result = await run_full_pipeline(full_path, timing_capture)
        result["category"] = category
        result["format"] = format_type
        results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    print(f"\nDocuments processed: {len(results)}")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")

    if successful:
        print("\nTiming by document:")
        print("-" * 50)
        for r in successful:
            print(f"  {r['file_name']:45s} {r['total_time_s']:6.2f}s")

        # Category breakdown
        print("\nTiming by category:")
        print("-" * 50)
        categories = {}
        for r in successful:
            cat = r.get("category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r["total_time_s"])

        for cat, times in sorted(categories.items()):
            avg = sum(times) / len(times)
            print(f"  {cat:15s}: avg {avg:6.2f}s (n={len(times)})")

        # Format breakdown
        print("\nTiming by format:")
        print("-" * 50)
        formats = {}
        for r in successful:
            fmt = r.get("format", "unknown")
            if fmt not in formats:
                formats[fmt] = []
            formats[fmt].append(r["total_time_s"])

        for fmt, times in sorted(formats.items()):
            avg = sum(times) / len(times)
            print(f"  {fmt:15s}: avg {avg:6.2f}s (n={len(times)})")

    # Bottleneck analysis
    print("\n" + "=" * 70)
    print("BOTTLENECK ANALYSIS")
    print("=" * 70)

    bottlenecks = identify_bottlenecks(results)

    if bottlenecks["slowest_stage_overall"]:
        slowest = bottlenecks["slowest_stage_overall"]
        print(f"\nSlowest stage overall: {slowest['stage']}")
        print(f"  Average time: {slowest['avg_ms']:.1f}ms")
        print("\n  All stages (avg ms):")
        for stage, avg in sorted(slowest["all_stages_avg"].items(), key=lambda x: -x[1]):
            print(f"    {stage:25s}: {avg:8.1f}ms")

    if bottlenecks["recommendations"]:
        print("\nRecommendations:")
        for rec in bottlenecks["recommendations"]:
            print(f"  - {rec}")

    # Save results
    results_file = RESULTS_DIR / f"full_pipeline_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Convert results to JSON-serializable format
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(v) for v in obj]
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)

    output_data = {
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "python_version": sys.version.split()[0],
            "project_root": str(Path(__file__).parent.parent.parent),
        },
        "results": make_serializable(results),
        "bottleneck_analysis": make_serializable(bottlenecks),
        "summary": {
            "total_documents": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "avg_time_s": sum(r["total_time_s"] for r in successful) / len(successful) if successful else 0,
        },
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
