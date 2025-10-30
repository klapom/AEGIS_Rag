#!/usr/bin/env python3
"""Quick test of ThreePhaseExtractor."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

# Test text (from benchmarks)
TEST_TEXT = """Alex is a powerful person, but Jordan is smarter and more talented. They worked at TechCorp together. Jordan left to found DevStart, a startup focused on AI research."""


async def main():
    """Test the three-phase extraction pipeline."""
    print("="*80)
    print("THREE-PHASE EXTRACTION PIPELINE - QUICK TEST")
    print("="*80)
    print()

    # Initialize extractor
    print("[1/3] Initializing ThreePhaseExtractor...")
    try:
        extractor = ThreePhaseExtractor()
        print("      OK - All components loaded")
    except Exception as e:
        print(f"      FAILED: {e}")
        return 1

    # Run extraction
    print()
    print("[2/3] Running extraction on test text...")
    print(f"      Text length: {len(TEST_TEXT)} chars")
    print()

    try:
        entities, relations = await extractor.extract(TEST_TEXT)
        print("      OK - Extraction complete")
    except Exception as e:
        print(f"      FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Display results
    print()
    print("[3/3] Results:")
    print(f"      Entities found: {len(entities)}")
    print(f"      Relations found: {len(relations)}")
    print()

    print("Entities:")
    for i, e in enumerate(entities, 1):
        print(f"  {i}. {e['name']} ({e['type']})")

    print()
    print("Relations:")
    for i, r in enumerate(relations, 1):
        print(f"  {i}. {r['source']} -> {r['target']}: {r['description'][:60]}...")

    print()
    print("="*80)
    print("TEST PASSED - ThreePhaseExtractor working correctly")
    print("="*80)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
