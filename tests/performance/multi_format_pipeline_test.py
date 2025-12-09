"""Multi-Format Pipeline Test - Analyze Docling JSON for different document formats.

This script tests the ingestion pipeline with different document formats (PPTX, PPT, DOCX, DOC)
and saves the raw Docling JSON for analysis.

Sprint 33 - TD-044 Verification
"""

import asyncio
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.components.ingestion.docling_client import DoclingContainerClient
from src.components.ingestion.langgraph_nodes import SectionMetadata
from src.components.ingestion.section_extraction import extract_section_hierarchy

# Test documents - one of each format
TEST_DOCUMENTS = {
    "pptx": Path(r"C:\Projekte\AEGISRAG\data\sample_documents\99_pptx_text\PerformanceTuning_textonly.pptx"),
    "ppt": Path(r"C:\Projekte\AEGISRAG\data\sample_documents\3. Basic Scripting\DE-D-OTAutBasic.ppt"),
    "docx": Path(r"C:\Projekte\AEGISRAG\data\sample_documents\2. Advanced Admin\DE-D-AdvancedAdministration_0368.docx"),
}

# Output directory
OUTPUT_DIR = Path(__file__).parent / "results" / "multi_format_test"


def analyze_json_structure(json_content: dict, format_name: str) -> dict:
    """Analyze the Docling JSON structure and return analysis results."""
    analysis = {
        "format": format_name,
        "timestamp": datetime.now().isoformat(),
        "top_level_keys": list(json_content.keys()),
        "has_body": "body" in json_content,
        "has_texts": "texts" in json_content,
        "has_groups": "groups" in json_content,
        "has_pages": "pages" in json_content,
    }

    # Analyze texts array
    if "texts" in json_content:
        texts = json_content["texts"]
        analysis["texts_count"] = len(texts)

        # Count labels
        labels = Counter(t.get("label", "NONE") for t in texts)
        analysis["text_labels"] = dict(labels)

        # Check for headings
        heading_labels = {"title", "subtitle-level-1", "subtitle-level-2"}
        analysis["heading_count"] = sum(labels.get(h, 0) for h in heading_labels)

        # Sample first 5 texts
        analysis["sample_texts"] = []
        for t in texts[:5]:
            analysis["sample_texts"].append({
                "label": t.get("label", "?"),
                "text_preview": t.get("text", "")[:80],
                "has_prov": bool(t.get("prov")),
            })
    else:
        analysis["texts_count"] = 0
        analysis["text_labels"] = {}
        analysis["heading_count"] = 0

    # Analyze groups
    if "groups" in json_content:
        groups = json_content["groups"]
        analysis["groups_count"] = len(groups)

        # Count group labels
        group_labels = Counter(g.get("label", "NONE") for g in groups)
        analysis["group_labels"] = dict(group_labels)
    else:
        analysis["groups_count"] = 0
        analysis["group_labels"] = {}

    # Analyze pages
    if "pages" in json_content:
        pages = json_content["pages"]
        if isinstance(pages, dict):
            analysis["pages_type"] = "dict"
            analysis["pages_count"] = len(pages)
        elif isinstance(pages, list):
            analysis["pages_type"] = "list"
            analysis["pages_count"] = len(pages)
        else:
            analysis["pages_type"] = type(pages).__name__
            analysis["pages_count"] = 0
    else:
        analysis["pages_type"] = "missing"
        analysis["pages_count"] = 0

    # Analyze body structure
    if "body" in json_content:
        body = json_content["body"]
        if isinstance(body, dict):
            children = body.get("children", [])
            analysis["body_children_count"] = len(children)

            # Check if children are $ref pointers
            ref_count = sum(1 for c in children if isinstance(c, dict) and "$ref" in c)
            analysis["body_children_refs"] = ref_count
            analysis["body_uses_refs"] = ref_count > 0
        else:
            analysis["body_children_count"] = 0
            analysis["body_uses_refs"] = False

    # Check pictures and tables
    analysis["pictures_count"] = len(json_content.get("pictures", []))
    analysis["tables_count"] = len(json_content.get("tables", []))

    return analysis


async def test_document(doc_path: Path, format_name: str, output_dir: Path) -> dict:
    """Test a single document through the Docling pipeline."""
    print(f"\n{'='*70}")
    print(f"Testing {format_name.upper()}: {doc_path.name}")
    print(f"{'='*70}")

    if not doc_path.exists():
        print(f"  ERROR: File not found: {doc_path}")
        return {"error": "File not found", "format": format_name}

    result = {
        "format": format_name,
        "file_name": doc_path.name,
        "file_size_kb": doc_path.stat().st_size / 1024,
    }

    try:
        # Parse with Docling
        print("  Parsing with Docling...")
        client = DoclingContainerClient()
        parsed = await client.parse_document(doc_path)

        # Check if we got json_content
        if not hasattr(parsed, "json_content") or not parsed.json_content:
            print("  ERROR: No json_content in parsed document!")
            result["error"] = "No json_content"
            return result

        json_content = parsed.json_content
        result["has_json_content"] = True

        # Save raw JSON
        json_filename = f"{format_name}_{doc_path.stem}_raw.json"
        json_path = output_dir / json_filename
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_content, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Saved JSON to: {json_path.name} ({json_path.stat().st_size / 1024:.1f} KB)")
        result["json_file"] = str(json_path)
        result["json_size_kb"] = json_path.stat().st_size / 1024

        # Analyze JSON structure
        print("  Analyzing JSON structure...")
        analysis = analyze_json_structure(json_content, format_name)
        result["analysis"] = analysis

        # Print analysis summary
        print("\n  === JSON Structure Analysis ===")
        print(f"  Top-level keys: {', '.join(analysis['top_level_keys'])}")
        print(f"  Pages: {analysis['pages_count']} ({analysis['pages_type']})")
        print(f"  Texts: {analysis['texts_count']} items")
        print(f"  Groups: {analysis['groups_count']} items")
        print(f"  Pictures: {analysis['pictures_count']}, Tables: {analysis['tables_count']}")

        if analysis.get("text_labels"):
            print("\n  === Text Labels ===")
            for label, count in sorted(analysis["text_labels"].items(), key=lambda x: -x[1]):
                print(f"    {label}: {count}x")

        if analysis.get("body_uses_refs"):
            print(f"\n  WARNING: body.children uses $ref pointers ({analysis['body_children_refs']} refs)")
            print("           Section extraction must use 'texts' array!")

        # Test section extraction
        print("\n  === Section Extraction Test ===")
        try:
            sections = extract_section_hierarchy(parsed, SectionMetadata)
            result["sections_extracted"] = len(sections)
            result["sections_with_text"] = sum(1 for s in sections if s.text.strip())

            print(f"  Sections found: {len(sections)}")
            print(f"  Sections with text: {result['sections_with_text']}")

            if sections:
                print("\n  First 5 sections:")
                for i, s in enumerate(sections[:5]):
                    text_preview = s.text[:50].replace("\n", " ") if s.text else "(empty)"
                    print(f"    [{i+1}] L{s.level} p{s.page_no}: '{s.heading[:40]}' -> '{text_preview}...'")
            else:
                print("  WARNING: No sections extracted!")

                # Debug: Check if texts array has headings
                if analysis["heading_count"] > 0:
                    print(f"  ISSUE: texts array has {analysis['heading_count']} headings but extraction failed!")
                else:
                    print("  Note: No heading labels found in texts array")

        except Exception as e:
            print(f"  ERROR in section extraction: {e}")
            result["section_extraction_error"] = str(e)

        # Check for expected structure
        print("\n  === Structure Validation ===")
        issues = []

        if not analysis["has_texts"]:
            issues.append("Missing 'texts' array")
        elif analysis["texts_count"] == 0:
            issues.append("Empty 'texts' array")

        if analysis["heading_count"] == 0:
            issues.append("No heading labels (title/subtitle-level-*) found")

        if analysis.get("body_uses_refs") and not analysis["has_texts"]:
            issues.append("body uses $ref but no texts array available")

        if issues:
            print("  ISSUES FOUND:")
            for issue in issues:
                print(f"    - {issue}")
            result["issues"] = issues
        else:
            print("  OK: Structure looks correct")
            result["issues"] = []

        result["success"] = True

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        result["error"] = str(e)
        result["success"] = False

    return result


async def main():
    """Run multi-format pipeline tests."""
    print("="*70)
    print("MULTI-FORMAT PIPELINE TEST")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*70)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")

    # Test each format
    results = []
    for format_name, doc_path in TEST_DOCUMENTS.items():
        result = await test_document(doc_path, format_name, OUTPUT_DIR)
        results.append(result)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    for r in results:
        status = "OK" if r.get("success") else "FAILED"
        sections = r.get("sections_extracted", 0)
        issues = len(r.get("issues", []))
        print(f"  {r['format'].upper():6s}: {status:6s} | Sections: {sections:3d} | Issues: {issues}")

    # Save summary
    summary_path = OUTPUT_DIR / "test_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSummary saved to: {summary_path}")

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
