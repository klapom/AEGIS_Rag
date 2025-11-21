"""Test script to analyze Docling JSON structure and show heading examples.

This script demonstrates:
1. How headings are structured in Docling JSON
2. How a chunk looks before embedding (with and without heading metadata)
3. The concrete improvement from Option 3
"""

import json
from pathlib import Path


def analyze_docling_structure():
    """Analyze Docling JSON structure from sample PowerPoint."""

    # Sample Docling JSON structure (from actual PowerPoint parse)
    sample_json = {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "name": "PerformanceTuning_textonly.pptx",
        "pages": [
            {
                "page_no": 1,
                "size": {"width": 720, "height": 540},
                "cells": [
                    {
                        "self_ref": "#/texts/0",
                        "type": "title",
                        "text": "Multi Server Architecture",
                        "prov": [{"page_no": 1, "bbox": {"l": 50, "t": 30, "r": 670, "b": 80}}],
                    },
                    {
                        "self_ref": "#/texts/1",
                        "type": "text",
                        "text": "Distributing load across multiple servers improves performance and availability.",
                        "prov": [{"page_no": 1, "bbox": {"l": 50, "t": 100, "r": 670, "b": 140}}],
                    },
                ],
            },
            {
                "page_no": 2,
                "size": {"width": 720, "height": 540},
                "cells": [
                    {
                        "self_ref": "#/texts/2",
                        "type": "subtitle-level-1",
                        "text": "Load Balancing Strategies",
                        "prov": [{"page_no": 2, "bbox": {"l": 50, "t": 30, "r": 670, "b": 80}}],
                    },
                    {
                        "self_ref": "#/texts/3",
                        "type": "text",
                        "text": "Round-robin, least connections, and IP hash are common load balancing algorithms.",
                        "prov": [{"page_no": 2, "bbox": {"l": 50, "t": 100, "r": 670, "b": 140}}],
                    },
                ],
            },
        ],
        "texts": [
            {
                "self_ref": "#/texts/0",
                "text": "Multi Server Architecture",
                "label": "title",
            },
            {
                "self_ref": "#/texts/1",
                "text": "Distributing load across multiple servers improves performance and availability.",
                "label": "text",
            },
            {
                "self_ref": "#/texts/2",
                "text": "Load Balancing Strategies",
                "label": "subtitle-level-1",
            },
            {
                "self_ref": "#/texts/3",
                "text": "Round-robin, least connections, and IP hash are common load balancing algorithms.",
                "label": "text",
            },
        ],
    }

    print("=" * 80)
    print("DOCLING JSON STRUCTURE - HEADING ANALYSIS")
    print("=" * 80)
    print()

    print("1. PAGE-BASED STRUCTURE:")
    print("-" * 80)
    for page in sample_json["pages"]:
        print(f"\n  Page {page['page_no']}:")
        for cell in page["cells"]:
            cell_type = cell.get("type", "unknown")
            text_preview = cell.get("text", "")[:60]
            print(f"    - Type: {cell_type:20s} | Text: {text_preview}")

    print("\n")
    print("2. HEADING TYPES IN DOCLING:")
    print("-" * 80)
    heading_types = {
        "title": "Main slide title (H1 equivalent)",
        "subtitle-level-1": "First-level subtitle (H2 equivalent)",
        "subtitle-level-2": "Second-level subtitle (H3 equivalent)",
        "text": "Body text (not a heading)",
        "list-item": "Bulleted or numbered list item",
        "table": "Table content",
        "caption": "Image or table caption",
    }

    for heading_type, description in heading_types.items():
        print(f"  {heading_type:20s} → {description}")

    print("\n")
    print("3. HEADING HIERARCHY EXTRACTION:")
    print("-" * 80)

    # Simulate heading extraction logic
    heading_by_page = {}
    current_heading = None

    for page in sample_json["pages"]:
        page_no = page["page_no"]
        for cell in page["cells"]:
            cell_type = cell.get("type", "text")
            if cell_type in ("title", "subtitle-level-1", "subtitle-level-2"):
                current_heading = cell.get("text", "")
                heading_by_page[page_no] = current_heading
                print(f"  Page {page_no}: Heading = '{current_heading}'")

    print("\n")
    print("4. EXAMPLE CHUNKS - BEFORE & AFTER HEADING METADATA:")
    print("=" * 80)
    print()

    # BEFORE: Current chunk structure (NO heading metadata)
    chunk_before = {
        "chunk_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
        "document_id": "c0c2bd038dead5c6",
        "chunk_index": 0,
        "content": (
            "Distributing load across multiple servers improves performance and availability. "
            "This approach ensures high availability and fault tolerance. "
            "Round-robin, least connections, and IP hash are common load balancing algorithms. "
            "Each algorithm has different use cases and performance characteristics."
        ),
        "start_char": 0,
        "end_char": 245,
        "token_count": 52,
        "metadata": {
            "source": "PerformanceTuning_textonly.pptx",
            "file_type": "pptx",
            "total_pages": 15,
        },
    }

    print("BEFORE (Current Implementation - No Heading):")
    print("-" * 80)
    print(json.dumps(chunk_before, indent=2))

    print("\n\n")

    # AFTER: With heading metadata (Option 3)
    chunk_after = {
        "chunk_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
        "document_id": "c0c2bd038dead5c6",
        "chunk_index": 0,
        "content": (
            "Distributing load across multiple servers improves performance and availability. "
            "This approach ensures high availability and fault tolerance. "
            "Round-robin, least connections, and IP hash are common load balancing algorithms. "
            "Each algorithm has different use cases and performance characteristics."
        ),
        "start_char": 0,
        "end_char": 245,
        "token_count": 52,
        "metadata": {
            "source": "PerformanceTuning_textonly.pptx",
            "file_type": "pptx",
            "total_pages": 15,
            # NEW: Heading metadata from Option 3
            "section_heading": "Multi Server Architecture",
            "page_no": 1,
            "bbox": {"l": 50, "t": 100, "r": 670, "b": 140},
        },
    }

    print("AFTER (Option 3 - With Heading & Provenance):")
    print("-" * 80)
    print(json.dumps(chunk_after, indent=2))

    print("\n\n")
    print("5. IMPACT ON CITATIONS:")
    print("=" * 80)
    print()

    print("BEFORE (Current):")
    print("  User: 'What is multi server architecture?'")
    print("  Citation: [1] PerformanceTuning_textonly.pptx")
    print()

    print("AFTER (Option 3):")
    print("  User: 'What is multi server architecture?'")
    print("  Citation: [1] PerformanceTuning_textonly.pptx - Section: 'Multi Server Architecture' (Page 1)")
    print()

    print("IMPROVEMENT:")
    print("  ✓ User sees WHICH section of document (better context)")
    print("  ✓ Better grounding (page number + section)")
    print("  ✓ Aligns with LangChain standard ('passage headings')")
    print()

    print("=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    print()
    print("Option 3 adds 3 fields to chunk metadata:")
    print("  1. section_heading: str - The heading of the section where chunk appears")
    print("  2. page_no: int - Page number (already extracted, but not used)")
    print("  3. bbox: dict - Bounding box coordinates (for precise location)")
    print()
    print("Effort: ~50 LOC in langgraph_nodes.py")
    print("Impact: Better citations, better retrieval context, LangChain alignment")
    print()


if __name__ == "__main__":
    analyze_docling_structure()
