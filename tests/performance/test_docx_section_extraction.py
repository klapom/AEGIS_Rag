"""Test DOCX section extraction with formatting-based heading detection.

Sprint 33 - TD-044: Verify new DOCX heading detection via formatting.bold
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.components.ingestion.section_extraction import (
    _detect_heading_strategy,
    _extract_from_texts_array,
    _is_likely_heading_by_formatting,
)


@dataclass
class SectionMetadata:
    """Section metadata for testing."""

    heading: str
    level: int
    page_no: int
    bbox: dict
    text: str
    token_count: int
    metadata: dict = field(default_factory=dict)


def count_tokens(text: str) -> int:
    """Simple token counter for testing."""
    return len(text.split())


def main():
    """Test DOCX section extraction."""
    print("=" * 70)
    print("DOCX SECTION EXTRACTION TEST - Formatting-Based Heading Detection")
    print("=" * 70)

    # Load DOCX JSON
    json_path = (
        Path(__file__).parent
        / "results"
        / "multi_format_test"
        / "docx_DE-D-AdvancedAdministration_0368_raw.json"
    )
    print(f"\nLoading: {json_path.name}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    texts = data.get("texts", [])
    print(f"Total texts: {len(texts)}")

    # Test 1: Heading strategy detection
    print("\n" + "=" * 70)
    print("1. HEADING STRATEGY DETECTION")
    print("=" * 70)

    strategy = _detect_heading_strategy(texts)
    print(f"Detected strategy: {strategy}")

    # Test 2: Count formatting-based headings
    print("\n" + "=" * 70)
    print("2. FORMATTING-BASED HEADINGS")
    print("=" * 70)

    formatting_headings = [
        (i, t.get("text", "")[:60])
        for i, t in enumerate(texts)
        if _is_likely_heading_by_formatting(t)
    ]
    print(f"Found {len(formatting_headings)} formatting-based headings")
    print("\nFirst 30 detected headings:")
    for idx, text in formatting_headings[:30]:
        print(f"  [{idx:4d}] '{text}'")

    # Test 3: Full section extraction
    print("\n" + "=" * 70)
    print("3. FULL SECTION EXTRACTION")
    print("=" * 70)

    sections = _extract_from_texts_array(
        texts=texts,
        section_metadata_class=SectionMetadata,
        count_tokens_func=count_tokens,
    )

    print(f"\nTotal sections extracted: {len(sections)}")
    print(f"Sections with text: {sum(1 for s in sections if s.text.strip())}")

    # Show first 20 sections
    print("\nFirst 20 sections:")
    for i, s in enumerate(sections[:20]):
        text_preview = s.text[:40].replace("\n", " ") if s.text else "(empty)"
        source = s.metadata.get("heading_source", "?")
        print(f"  [{i+1:3d}] L{s.level} '{s.heading[:40]}' -> '{text_preview}...' ({source})")

    # Test 4: Compare with PPTX (which has labels)
    print("\n" + "=" * 70)
    print("4. COMPARISON WITH PPTX (LABEL-BASED)")
    print("=" * 70)

    pptx_path = (
        Path(__file__).parent
        / "results"
        / "multi_format_test"
        / "pptx_PerformanceTuning_textonly_raw.json"
    )
    if pptx_path.exists():
        with open(pptx_path, encoding="utf-8") as f:
            pptx_data = json.load(f)

        pptx_texts = pptx_data.get("texts", [])
        pptx_strategy = _detect_heading_strategy(pptx_texts)
        print(f"PPTX strategy: {pptx_strategy}")

        pptx_sections = _extract_from_texts_array(
            texts=pptx_texts,
            section_metadata_class=SectionMetadata,
            count_tokens_func=count_tokens,
        )
        print(f"PPTX sections: {len(pptx_sections)}")

        print("\nFirst 10 PPTX sections:")
        for i, s in enumerate(pptx_sections[:10]):
            source = s.metadata.get("heading_source", "?")
            print(f"  [{i+1:3d}] L{s.level} '{s.heading[:50]}' ({source})")

    # Summary
    print("\n" + "=" * 70)
    print("5. SUMMARY")
    print("=" * 70)
    print(
        f"""
DOCX Section Extraction Results:
- Strategy used: {strategy}
- Headings detected: {len(formatting_headings)}
- Sections extracted: {len(sections)}
- Sections with text: {sum(1 for s in sections if s.text.strip())}

STATUS: {"SUCCESS" if len(sections) > 0 else "FAILED"} - DOCX heading detection {'working' if len(sections) > 0 else 'not working'}!
"""
    )


if __name__ == "__main__":
    main()
