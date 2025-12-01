"""Multi-Format Performance Test.

Sprint 33: Test ingestion performance across all supported formats.
Tests: PDF, DOCX, PPTX, XLSX (Docling-supported formats)
"""

import asyncio
import sys
import time
from pathlib import Path
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class FormatTestResult:
    """Result of testing a single format."""
    format: str
    file_name: str
    file_size_kb: float
    parse_time_s: float
    sections_extracted: int
    chunks_created: int
    tokens_total: int
    status: str
    error: str | None = None


@dataclass
class SectionMetadata:
    """Section metadata for testing."""
    heading: str
    level: int
    page_no: int
    bbox: dict
    text: str
    token_count: int
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


async def test_single_file(file_path: Path) -> FormatTestResult:
    """Test ingestion of a single file."""
    from src.components.ingestion.docling_client import DoclingContainerClient
    from src.components.ingestion.section_extraction import extract_section_hierarchy

    file_ext = file_path.suffix.lower()
    file_size_kb = file_path.stat().st_size / 1024

    print(f"\n{'='*60}")
    print(f"Testing: {file_path.name}")
    print(f"Format: {file_ext}, Size: {file_size_kb:.1f} KB")
    print(f"{'='*60}")

    try:
        # Step 1: Parse with Docling
        print("  [1/2] Parsing with Docling...")
        start_time = time.perf_counter()

        client = DoclingContainerClient()
        parsed = await client.parse_document(file_path)

        parse_time = time.perf_counter() - start_time
        print(f"        Parsing completed in {parse_time:.2f}s")

        if not parsed.json_content:
            return FormatTestResult(
                format=file_ext,
                file_name=file_path.name,
                file_size_kb=file_size_kb,
                parse_time_s=parse_time,
                sections_extracted=0,
                chunks_created=0,
                tokens_total=0,
                status="FAILED",
                error="No JSON content returned"
            )

        # Step 2: Extract sections
        print("  [2/2] Extracting sections...")
        sections = extract_section_hierarchy(parsed, SectionMetadata)

        # Calculate totals
        total_tokens = sum(s.token_count for s in sections)

        print(f"        Sections: {len(sections)}")
        print(f"        Total tokens: {total_tokens}")

        # Show first 5 sections
        if sections:
            print("\n        First 5 sections:")
            for i, s in enumerate(sections[:5]):
                heading_short = s.heading[:40] if s.heading else "(no heading)"
                source = s.metadata.get("heading_source", "?")
                print(f"          [{i+1}] L{s.level} '{heading_short}...' ({s.token_count} tokens, {source})")

        return FormatTestResult(
            format=file_ext,
            file_name=file_path.name,
            file_size_kb=file_size_kb,
            parse_time_s=parse_time,
            sections_extracted=len(sections),
            chunks_created=len(sections),  # 1:1 for now
            tokens_total=total_tokens,
            status="SUCCESS"
        )

    except Exception as e:
        return FormatTestResult(
            format=file_ext,
            file_name=file_path.name,
            file_size_kb=file_size_kb,
            parse_time_s=0,
            sections_extracted=0,
            chunks_created=0,
            tokens_total=0,
            status="ERROR",
            error=str(e)
        )


async def main():
    """Run multi-format performance test."""
    print("="*70)
    print("MULTI-FORMAT PERFORMANCE TEST")
    print("Sprint 33: Testing all Docling-supported formats")
    print("="*70)

    # Define test files - one per format
    base_path = Path("C:/Projekte/AEGISRAG/data/sample_documents")

    test_files = [
        # PDF - small
        base_path / "retired_13.pdf",
        # PDF - medium
        base_path / "OTByteArray.pdf",
        # DOCX - with Word heading styles
        base_path / "OT_requirements_FNT_Command_20221219.docx",
        # DOCX - without heading styles (formatting-based)
        base_path / "2. Advanced Admin" / "DE-D-AdvancedAdministration_0368.docx",
        # PPTX - text only
        base_path / "99_pptx_text" / "PerformanceTuning_textonly.pptx",
        # PPTX - with graphics
        base_path / "99_pptx_graphics" / "PerformanceTuning_graphics.pptx",
        # XLSX
        base_path / "Phoenix_InstalledBase_NTT.xlsx",
    ]

    # Filter to existing files
    existing_files = [f for f in test_files if f.exists()]
    missing_files = [f for f in test_files if not f.exists()]

    if missing_files:
        print(f"\nWARNING: {len(missing_files)} files not found:")
        for f in missing_files:
            print(f"  - {f}")

    print(f"\nTesting {len(existing_files)} files...")

    # Run tests
    results: list[FormatTestResult] = []
    total_start = time.perf_counter()

    for file_path in existing_files:
        result = await test_single_file(file_path)
        results.append(result)

    total_time = time.perf_counter() - total_start

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    print(f"\n{'Format':<8} {'File':<45} {'Size':>8} {'Time':>8} {'Sections':>10} {'Tokens':>10} {'Status':<10}")
    print("-"*110)

    for r in results:
        file_short = r.file_name[:42] + "..." if len(r.file_name) > 45 else r.file_name
        print(f"{r.format:<8} {file_short:<45} {r.file_size_kb:>7.1f}K {r.parse_time_s:>7.2f}s {r.sections_extracted:>10} {r.tokens_total:>10} {r.status:<10}")

    print("-"*110)

    # Aggregates
    success_count = sum(1 for r in results if r.status == "SUCCESS")
    total_sections = sum(r.sections_extracted for r in results)
    total_tokens = sum(r.tokens_total for r in results)
    total_size_kb = sum(r.file_size_kb for r in results)
    total_parse_time = sum(r.parse_time_s for r in results)

    print(f"\nResults:")
    print(f"  Files tested:     {len(results)}")
    print(f"  Successful:       {success_count}/{len(results)}")
    print(f"  Total size:       {total_size_kb/1024:.2f} MB")
    print(f"  Total parse time: {total_parse_time:.2f}s")
    print(f"  Total sections:   {total_sections}")
    print(f"  Total tokens:     {total_tokens}")
    print(f"  Overall time:     {total_time:.2f}s")

    # Performance metrics
    if total_parse_time > 0:
        print(f"\nPerformance:")
        print(f"  Throughput:       {total_size_kb/total_parse_time:.1f} KB/s")
        print(f"  Avg time/file:    {total_parse_time/len(results):.2f}s")

    # Format breakdown
    print(f"\nBy Format:")
    format_stats = {}
    for r in results:
        if r.format not in format_stats:
            format_stats[r.format] = {"count": 0, "success": 0, "time": 0, "sections": 0}
        format_stats[r.format]["count"] += 1
        format_stats[r.format]["time"] += r.parse_time_s
        format_stats[r.format]["sections"] += r.sections_extracted
        if r.status == "SUCCESS":
            format_stats[r.format]["success"] += 1

    for fmt, stats in sorted(format_stats.items()):
        print(f"  {fmt}: {stats['success']}/{stats['count']} success, {stats['time']:.2f}s, {stats['sections']} sections")

    # Errors
    errors = [r for r in results if r.error]
    if errors:
        print(f"\nErrors:")
        for r in errors:
            print(f"  {r.file_name}: {r.error}")

    print(f"\n{'='*70}")
    print(f"TEST COMPLETE: {success_count}/{len(results)} formats working")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
