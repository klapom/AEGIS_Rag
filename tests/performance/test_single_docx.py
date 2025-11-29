"""Test single DOCX file for heading extraction.

Sprint 33 - Testing OT_requirements_FNT_Command_20221219.docx
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.components.ingestion.docling_client import DoclingContainerClient


async def main():
    doc_path = Path(r"C:\Projekte\AEGISRAG\data\sample_documents\OT_requirements_FNT_Command_20221219.docx")

    print(f"Testing: {doc_path.name}")
    print(f"File size: {doc_path.stat().st_size / 1024:.1f} KB")
    print()

    # Parse with Docling
    client = DoclingContainerClient()
    parsed = await client.parse_document(doc_path)

    if not parsed.json_content:
        print("ERROR: No json_content!")
        return

    # Save JSON for analysis
    output_path = Path(__file__).parent / "results" / "OT_requirements_docx_raw.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed.json_content, f, indent=2, ensure_ascii=False, default=str)
    print(f"Saved JSON to: {output_path}")

    # Analyze labels
    texts = parsed.json_content.get("texts", [])
    print(f"\nTotal texts: {len(texts)}")

    from collections import Counter
    labels = Counter(t.get("label", "NONE") for t in texts)
    print("\nLabel distribution:")
    for label, count in labels.most_common():
        print(f"  {label}: {count}x")

    # Check for section_header specifically
    section_headers = [t for t in texts if t.get("label") == "section_header"]
    print(f"\nSection headers found: {len(section_headers)}")

    if section_headers:
        print("\nFirst 20 section_header items:")
        for i, h in enumerate(section_headers[:20]):
            text = h.get("text", "")[:60]
            level = h.get("level", "?")
            print(f"  [{i+1}] L{level}: '{text}'")
    else:
        print("\nNo section_header labels found!")
        print("Checking for title labels...")
        titles = [t for t in texts if t.get("label") == "title"]
        print(f"Title labels: {len(titles)}")

        # Check formatting-based headings
        bold_short = [
            t for t in texts
            if t.get("label") == "paragraph"
            and t.get("formatting", {}).get("bold")
            and len(t.get("text", "")) < 100
        ]
        print(f"Bold short paragraphs: {len(bold_short)}")
        if bold_short:
            print("\nFirst 10 bold short paragraphs:")
            for i, t in enumerate(bold_short[:10]):
                text = t.get("text", "")[:50]
                print(f"  [{i+1}] '{text}'")


if __name__ == "__main__":
    asyncio.run(main())
