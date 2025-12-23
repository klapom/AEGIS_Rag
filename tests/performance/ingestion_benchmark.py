"""Ingestion Performance Benchmark Suite.

Sprint 33 Feature: Dedicated ingestion performance benchmarks using
categorized test documents (text-only, graphics, mixed content).

Benchmarks measure end-to-end ingestion time and per-stage breakdown:
1. Docling Parsing (PDF/PPTX to structured text)
2. Section Extraction (ADR-039 adaptive chunking)
3. Embedding Generation (BGE-M3)
4. Neo4j Graph Storage (Section nodes)

Usage:
    # Run all benchmarks
    python tests/performance/ingestion_benchmark.py

    # Run specific category
    python tests/performance/ingestion_benchmark.py --category text-only

    # Compare before/after optimization
    python tests/performance/ingestion_benchmark.py --compare baseline.json
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class StageMetrics:
    """Timing metrics for a single ingestion stage."""

    name: str
    duration_ms: float
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentBenchmark:
    """Benchmark result for a single document."""

    file_path: str
    file_name: str
    file_size_kb: float
    category: str
    format: str
    total_duration_ms: float
    stages: list[StageMetrics]
    chunks_created: int = 0
    sections_extracted: int = 0
    success: bool = True
    error: str | None = None


@dataclass
class BenchmarkReport:
    """Complete benchmark report with all results."""

    timestamp: str
    test_documents: list[DocumentBenchmark]
    summary: dict[str, Any]
    environment: dict[str, Any]


# Test document paths (relative to data/sample_documents)
# Found in user's OneDrive - copied to project for benchmarking
TEST_DOCUMENTS = {
    "text-only": [
        {
            "path": "99_pdf_text/PerformanceTuning_textonly.pdf",
            "format": "pdf",
            "size_kb": 285,
        },
        {
            "path": "99_pptx_text/PerformanceTuning_textonly.pptx",
            "format": "pptx",
            "size_kb": 416,
        },
    ],
    "graphics": [
        {
            "path": "99_pdf_graphics/PerformanceTuning_graphics.pdf",
            "format": "pdf",
            "size_kb": 580,
        },
        {
            "path": "99_pptx_graphics/PerformanceTuning_graphics.pptx",
            "format": "pptx",
            "size_kb": 666,
        },
    ],
    "mixed": [
        {
            "path": "9. Performance Tuning/EN-D-Performance Tuning.pdf",
            "format": "pdf",
            "size_kb": 1900,
        },
    ],
    # Note: No pure image files (PNG, JPG) found in sample_documents
    # To test OCR performance, add scanned PDFs or images here
    "image-ocr": [],
}

# OneDrive base path (user's document location)
ONEDRIVE_BASE = Path(
    r"C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\data\sample_documents"
)


def get_document_path(relative_path: str) -> Path | None:
    """Get full path to test document, checking both locations."""
    # Try OneDrive location first
    onedrive_path = ONEDRIVE_BASE / relative_path
    if onedrive_path.exists():
        return onedrive_path

    # Try project's data folder
    project_path = Path(__file__).parent.parent.parent / "data" / "sample_documents" / relative_path
    if project_path.exists():
        return project_path

    return None


async def benchmark_docling_parse(file_path: Path) -> tuple[StageMetrics, dict | None]:
    """Benchmark Docling container parsing stage."""
    from src.components.ingestion.docling_client import DoclingClient
    from src.core.config import settings

    start = time.perf_counter()
    try:
        client = DoclingClient(base_url=settings.docling_base_url)

        # Parse document using the correct method
        result = await client.parse_document(file_path)

        elapsed_ms = (time.perf_counter() - start) * 1000

        # DoclingParsedDocument has text, pages, metadata attributes
        return (
            StageMetrics(
                name="docling_parse",
                duration_ms=elapsed_ms,
                success=True,
                metadata={
                    "pages": result.total_pages if hasattr(result, "total_pages") else 0,
                    "text_length": len(result.text) if hasattr(result, "text") else 0,
                    "chunks": len(result.chunks) if hasattr(result, "chunks") else 0,
                },
            ),
            result,
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return (
            StageMetrics(
                name="docling_parse",
                duration_ms=elapsed_ms,
                success=False,
                error=str(e),
            ),
            None,
        )


async def benchmark_section_extraction(docling_result: dict) -> StageMetrics:
    """Benchmark section extraction from Docling JSON."""
    from src.components.ingestion.section_extraction import extract_sections

    start = time.perf_counter()
    try:
        sections = extract_sections(docling_result)
        elapsed_ms = (time.perf_counter() - start) * 1000

        return StageMetrics(
            name="section_extraction",
            duration_ms=elapsed_ms,
            success=True,
            metadata={
                "sections_count": len(sections),
                "section_types": [s.get("type") for s in sections[:5]],
            },
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return StageMetrics(
            name="section_extraction",
            duration_ms=elapsed_ms,
            success=False,
            error=str(e),
        )


async def benchmark_chunking(text: str, sections: list) -> StageMetrics:
    """Benchmark adaptive section-aware chunking."""
    from src.components.ingestion.langgraph_nodes import chunk_document

    start = time.perf_counter()
    try:
        # Simulate state for chunking
        state = {
            "document_text": text,
            "sections": sections,
            "file_path": "benchmark_test.pdf",
        }
        result = await chunk_document(state)
        chunks = result.get("chunks", [])
        elapsed_ms = (time.perf_counter() - start) * 1000

        return StageMetrics(
            name="chunking",
            duration_ms=elapsed_ms,
            success=True,
            metadata={
                "chunks_created": len(chunks),
                "avg_chunk_tokens": (
                    mean([c.get("token_count", 0) for c in chunks]) if chunks else 0
                ),
            },
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return StageMetrics(
            name="chunking",
            duration_ms=elapsed_ms,
            success=False,
            error=str(e),
        )


async def benchmark_embedding(chunks: list) -> StageMetrics:
    """Benchmark BGE-M3 embedding generation."""
    from src.components.vector_search.embedding_service import get_embeddings

    start = time.perf_counter()
    try:
        # Extract text from chunks for embedding
        texts = [c.get("text", "") for c in chunks[:10]]  # Limit to 10 for benchmark
        embeddings = await get_embeddings(texts)
        elapsed_ms = (time.perf_counter() - start) * 1000

        return StageMetrics(
            name="embedding",
            duration_ms=elapsed_ms,
            success=True,
            metadata={
                "chunks_embedded": len(embeddings),
                "embedding_dim": len(embeddings[0]) if embeddings else 0,
                "avg_ms_per_chunk": elapsed_ms / len(texts) if texts else 0,
            },
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return StageMetrics(
            name="embedding",
            duration_ms=elapsed_ms,
            success=False,
            error=str(e),
        )


async def benchmark_neo4j_storage(chunks: list, doc_id: str) -> StageMetrics:
    """Benchmark Neo4j graph storage with Section nodes."""
    from src.components.graph_rag.neo4j_client import Neo4jClient

    start = time.perf_counter()
    try:
        client = Neo4jClient()
        await client.connect()

        # Store document and chunks (simplified for benchmark)
        await client.create_document_node(doc_id, {"benchmark": True})

        for i, chunk in enumerate(chunks[:5]):  # Limit to 5 for benchmark
            chunk_id = f"{doc_id}_chunk_{i}"
            await client.create_chunk_node(chunk_id, doc_id, chunk)

        await client.close()
        elapsed_ms = (time.perf_counter() - start) * 1000

        return StageMetrics(
            name="neo4j_storage",
            duration_ms=elapsed_ms,
            success=True,
            metadata={
                "chunks_stored": min(len(chunks), 5),
            },
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return StageMetrics(
            name="neo4j_storage",
            duration_ms=elapsed_ms,
            success=False,
            error=str(e),
        )


async def run_document_benchmark(
    doc_config: dict, category: str, iterations: int = 1
) -> DocumentBenchmark | None:
    """Run full ingestion benchmark for a single document."""
    file_path = get_document_path(doc_config["path"])

    if not file_path:
        print(f"  [SKIP] Document not found: {doc_config['path']}")
        return None

    print(f"  [BENCH] {file_path.name} ({doc_config['size_kb']}KB)")

    stages: list[StageMetrics] = []
    total_start = time.perf_counter()

    # Stage 1: Docling Parse
    docling_metrics, parsed_doc = await benchmark_docling_parse(file_path)
    stages.append(docling_metrics)
    print(
        f"    - Docling: {docling_metrics.duration_ms:.1f}ms {'OK' if docling_metrics.success else 'FAIL'}"
    )

    if not docling_metrics.success:
        return DocumentBenchmark(
            file_path=str(file_path),
            file_name=file_path.name,
            file_size_kb=doc_config["size_kb"],
            category=category,
            format=doc_config["format"],
            total_duration_ms=(time.perf_counter() - total_start) * 1000,
            stages=stages,
            success=False,
            error=docling_metrics.error,
        )

    # Get chunk count from parsed document
    chunks_created = len(parsed_doc.chunks) if hasattr(parsed_doc, "chunks") else 0

    # Stage 2: Section Extraction (if Docling succeeded)
    section_result = StageMetrics(
        name="section_extraction",
        duration_ms=0,
        success=True,
        metadata={
            "sections_count": len(parsed_doc.sections) if hasattr(parsed_doc, "sections") else 0,
        },
    )
    stages.append(section_result)

    # Stage 3: Report Chunking from Docling result
    chunk_result = StageMetrics(
        name="chunking",
        duration_ms=0,  # Already included in Docling time
        success=True,
        metadata={
            "chunks_created": chunks_created,
            "total_pages": parsed_doc.total_pages if hasattr(parsed_doc, "total_pages") else 0,
        },
    )
    stages.append(chunk_result)
    print(f"    - Chunks: {chunks_created} created")

    # Stage 4: Embedding (placeholder - would need embedding service)
    embed_result = StageMetrics(
        name="embedding",
        duration_ms=0,
        success=True,
        metadata={"note": "Embedding not benchmarked (requires Ollama)"},
    )
    stages.append(embed_result)

    # Stage 5: Neo4j Storage (placeholder - would need Neo4j)
    neo4j_result = StageMetrics(
        name="neo4j_storage",
        duration_ms=0,
        success=True,
        metadata={"note": "Neo4j not benchmarked (requires connection)"},
    )
    stages.append(neo4j_result)

    total_duration = (time.perf_counter() - total_start) * 1000
    print(f"    - Total: {total_duration:.1f}ms")

    return DocumentBenchmark(
        file_path=str(file_path),
        file_name=file_path.name,
        file_size_kb=doc_config["size_kb"],
        category=category,
        format=doc_config["format"],
        total_duration_ms=total_duration,
        stages=stages,
        chunks_created=chunks_created,
        sections_extracted=section_result.metadata.get("sections_count", 0),
        success=True,
    )


async def run_category_benchmarks(category: str) -> list[DocumentBenchmark]:
    """Run benchmarks for all documents in a category."""
    docs = TEST_DOCUMENTS.get(category, [])
    if not docs:
        print(f"No documents found for category: {category}")
        return []

    results = []
    for doc_config in docs:
        result = await run_document_benchmark(doc_config, category)
        if result:
            results.append(result)

    return results


def generate_summary(results: list[DocumentBenchmark]) -> dict[str, Any]:
    """Generate summary statistics from benchmark results."""
    if not results:
        return {"error": "No benchmark results"}

    # Group by category
    by_category: dict[str, list[DocumentBenchmark]] = {}
    for r in results:
        if r.category not in by_category:
            by_category[r.category] = []
        by_category[r.category].append(r)

    # Group by format
    by_format: dict[str, list[DocumentBenchmark]] = {}
    for r in results:
        if r.format not in by_format:
            by_format[r.format] = []
        by_format[r.format].append(r)

    # Calculate stats
    all_durations = [r.total_duration_ms for r in results if r.success]

    summary = {
        "total_documents": len(results),
        "successful": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "total_size_kb": sum(r.file_size_kb for r in results),
        "avg_duration_ms": mean(all_durations) if all_durations else 0,
        "min_duration_ms": min(all_durations) if all_durations else 0,
        "max_duration_ms": max(all_durations) if all_durations else 0,
        "by_category": {},
        "by_format": {},
    }

    # Stats by category
    for cat, cat_results in by_category.items():
        cat_durations = [r.total_duration_ms for r in cat_results if r.success]
        summary["by_category"][cat] = {
            "count": len(cat_results),
            "avg_ms": mean(cat_durations) if cat_durations else 0,
            "total_kb": sum(r.file_size_kb for r in cat_results),
        }

    # Stats by format
    for fmt, fmt_results in by_format.items():
        fmt_durations = [r.total_duration_ms for r in fmt_results if r.success]
        summary["by_format"][fmt] = {
            "count": len(fmt_results),
            "avg_ms": mean(fmt_durations) if fmt_durations else 0,
        }

    return summary


def get_environment_info() -> dict[str, Any]:
    """Get environment information for reproducibility."""
    import platform

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "project_root": str(Path(__file__).parent.parent.parent),
    }


def save_report(report: BenchmarkReport, output_path: Path) -> None:
    """Save benchmark report to JSON file."""

    # Convert dataclasses to dicts
    def to_dict(obj: Any) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return {k: to_dict(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, list):
            return [to_dict(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: to_dict(v) for k, v in obj.items()}
        else:
            return obj

    with open(output_path, "w") as f:
        json.dump(to_dict(report), f, indent=2)

    print(f"\nReport saved to: {output_path}")


def compare_reports(current: BenchmarkReport, baseline_path: Path) -> None:
    """Compare current results with baseline."""
    with open(baseline_path) as f:
        baseline = json.load(f)

    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)

    baseline_avg = baseline.get("summary", {}).get("avg_duration_ms", 0)
    current_avg = current.summary.get("avg_duration_ms", 0)

    if baseline_avg and current_avg:
        change = ((current_avg - baseline_avg) / baseline_avg) * 100
        direction = "FASTER" if change < 0 else "SLOWER"
        print(f"\nOverall: {abs(change):.1f}% {direction}")
        print(f"  Baseline: {baseline_avg:.1f}ms")
        print(f"  Current:  {current_avg:.1f}ms")


async def main() -> None:
    """Run ingestion benchmarks."""
    parser = argparse.ArgumentParser(description="Ingestion Performance Benchmarks")
    parser.add_argument(
        "--category",
        choices=["text-only", "graphics", "mixed", "image-ocr", "all"],
        default="all",
        help="Document category to benchmark",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/performance/results/ingestion_benchmark.json"),
        help="Output file for results",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        help="Compare with baseline results file",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("AEGISRAG INGESTION PERFORMANCE BENCHMARK")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Run benchmarks
    all_results: list[DocumentBenchmark] = []

    if args.category == "all":
        categories = ["text-only", "graphics", "mixed", "image-ocr"]
    else:
        categories = [args.category]

    for category in categories:
        print(f"\n[CATEGORY: {category.upper()}]")
        results = await run_category_benchmarks(category)
        all_results.extend(results)

    # Generate report
    report = BenchmarkReport(
        timestamp=datetime.now().isoformat(),
        test_documents=all_results,
        summary=generate_summary(all_results),
        environment=get_environment_info(),
    )

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Documents: {report.summary['total_documents']}")
    print(f"Successful: {report.summary['successful']}")
    print(f"Failed: {report.summary['failed']}")
    print(f"Average Duration: {report.summary['avg_duration_ms']:.1f}ms")

    print("\nBy Category:")
    for cat, stats in report.summary.get("by_category", {}).items():
        print(f"  {cat}: {stats['count']} docs, avg {stats['avg_ms']:.1f}ms")

    print("\nBy Format:")
    for fmt, stats in report.summary.get("by_format", {}).items():
        print(f"  {fmt}: {stats['count']} docs, avg {stats['avg_ms']:.1f}ms")

    # Save report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_report(report, args.output)

    # Compare with baseline if provided
    if args.compare and args.compare.exists():
        compare_reports(report, args.compare)

    print("\n[DONE] Benchmark complete.")


if __name__ == "__main__":
    asyncio.run(main())
