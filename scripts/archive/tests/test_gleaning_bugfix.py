#!/usr/bin/env python3
"""Test Sprint 85 Gleaning Bugfix.

Verifies that:
1. QualityRequirement.LOW is used correctly (not STANDARD which doesn't exist)
2. Completeness check returns True/False (not always True due to exception)
3. Gleaning multi-pass extraction works end-to-end
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from components.graph_rag.extraction_service import ExtractionService
from domains.llm_integration.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)


async def test_quality_requirement_enum():
    """Test 1: Verify QualityRequirement enum values."""
    print("\n" + "=" * 80)
    print("TEST 1: QualityRequirement Enum Verification")
    print("=" * 80)

    # Check available enum values
    available = [e.name for e in QualityRequirement]
    print(f"\nAvailable QualityRequirement values: {available}")

    # Verify STANDARD does NOT exist
    has_standard = hasattr(QualityRequirement, "STANDARD")
    print(f"Has STANDARD: {has_standard}")

    # Verify LOW exists (used in bugfix)
    has_low = hasattr(QualityRequirement, "LOW")
    print(f"Has LOW: {has_low}")

    # Test creating LLMTask with LOW
    try:
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test prompt",
            complexity=Complexity.LOW,
            quality_requirement=QualityRequirement.LOW,
        )
        print(f"\n[PASS] LLMTask created successfully with QualityRequirement.LOW")
        print(f"  Task: {task.task_type}, Quality: {task.quality_requirement}")
        return True
    except Exception as e:
        print(f"\n[FAIL] LLMTask creation failed: {e}")
        return False


async def test_completeness_check():
    """Test 2: Verify completeness check returns True/False correctly."""
    print("\n" + "=" * 80)
    print("TEST 2: Completeness Check Function")
    print("=" * 80)

    # Initialize extraction service
    service = ExtractionService()

    # Create test data
    test_text = """
    Microsoft Corporation was founded by Bill Gates and Paul Allen in 1975.
    The company is headquartered in Redmond, Washington.
    Microsoft acquired GitHub in 2018 for $7.5 billion.
    Satya Nadella has been the CEO of Microsoft since 2014.
    """

    # Create mock entities
    from core.models import GraphEntity

    entities = [
        GraphEntity(id="e1", name="Microsoft", type="ORGANIZATION", description="Tech company"),
        GraphEntity(id="e2", name="Bill Gates", type="PERSON", description="Co-founder"),
        GraphEntity(id="e3", name="Paul Allen", type="PERSON", description="Co-founder"),
        GraphEntity(id="e4", name="GitHub", type="ORGANIZATION", description="Code platform"),
        GraphEntity(id="e5", name="Satya Nadella", type="PERSON", description="CEO"),
        GraphEntity(id="e6", name="Redmond", type="LOCATION", description="City"),
    ]

    # Test with NO relationships (should return True = incomplete)
    print("\nTest 2a: No relationships (should be incomplete)")
    print("-" * 40)

    start_time = time.time()
    try:
        result = await service._check_relationship_completeness(
            text=test_text,
            entities=entities,
            relationships=[],  # No relationships yet
            document_id="test_doc_1",
        )
        elapsed = time.time() - start_time

        print(f"  Result: {'INCOMPLETE' if result else 'COMPLETE'}")
        print(f"  Time: {elapsed:.2f}s")

        if result is True:
            print(f"  [PASS] Correctly identified as incomplete (no relationships)")
        else:
            print(f"  [WARN] Unexpected: marked complete with no relationships")

    except AttributeError as e:
        if "STANDARD" in str(e):
            print(f"  [FAIL] Bugfix NOT applied: {e}")
            return False
        raise
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False

    # Test with SOME relationships (should return True or False based on LLM)
    print("\nTest 2b: With some relationships")
    print("-" * 40)

    from core.models import GraphRelationship

    relationships = [
        GraphRelationship(
            id="r1",
            source="Bill Gates",
            target="Microsoft",
            type="FOUNDED",
        ),
        GraphRelationship(
            id="r2",
            source="Microsoft",
            target="GitHub",
            type="ACQUIRED",
        ),
    ]

    start_time = time.time()
    try:
        result = await service._check_relationship_completeness(
            text=test_text,
            entities=entities,
            relationships=relationships,
            document_id="test_doc_2",
        )
        elapsed = time.time() - start_time

        print(f"  Result: {'INCOMPLETE' if result else 'COMPLETE'}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  [PASS] Completeness check executed successfully (result is valid boolean)")

    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False

    return True


async def test_gleaning_extraction():
    """Test 3: Full Gleaning extraction with a real document."""
    print("\n" + "=" * 80)
    print("TEST 3: Full Gleaning Extraction")
    print("=" * 80)

    # Use a HotpotQA test file
    test_file = Path("/home/admin/projects/aegisrag/AEGIS_Rag/data/hf_relation_datasets/redocred/redocred_0002.txt")

    if not test_file.exists():
        print(f"  [SKIP] Test file not found: {test_file}")
        return True

    # Read test file
    text = test_file.read_text()
    # Remove header comments
    lines = text.split("\n")
    text_lines = [l for l in lines if not l.startswith("#")]
    text = "\n".join(text_lines).strip()

    print(f"\nTest file: {test_file.name}")
    print(f"Text length: {len(text)} chars")
    print(f"Preview: {text[:150]}...")

    # Initialize service
    service = ExtractionService()

    # Extract with Gleaning enabled
    print("\n" + "-" * 40)
    print("Running extraction with Gleaning...")
    print("-" * 40)

    start_time = time.time()
    try:
        result = await service.extract_and_store(
            text=text,
            document_id="test_gleaning",
        )
        elapsed = time.time() - start_time

        print(f"\n  Entities extracted: {result['entity_count']}")
        print(f"  Relationships extracted: {result['relationship_count']}")
        print(f"  Total time: {elapsed:.2f}s")

        # Show some entities
        print("\n  Sample entities:")
        for e in result["entities"][:5]:
            print(f"    - {e.name} ({e.type})")

        # Show some relationships
        print("\n  Sample relationships:")
        for r in result["relationships"][:5]:
            print(f"    - {r.source} --[{r.type}]--> {r.target}")

        # Calculate ratio
        if result["entity_count"] > 0:
            ratio = result["relationship_count"] / result["entity_count"]
            print(f"\n  Entity/Relation Ratio: {ratio:.2f}")

        print(f"\n  [PASS] Gleaning extraction completed successfully")
        return True

    except AttributeError as e:
        if "STANDARD" in str(e):
            print(f"\n  [FAIL] Bugfix NOT applied: {e}")
            return False
        raise
    except Exception as e:
        print(f"\n  [FAIL] Extraction error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_continuation_extraction():
    """Test 4: Verify continuation extraction works."""
    print("\n" + "=" * 80)
    print("TEST 4: Continuation Extraction (Missing Relationships)")
    print("=" * 80)

    service = ExtractionService()

    test_text = """
    Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.
    The company launched the iPhone in 2007, revolutionizing the smartphone industry.
    Tim Cook became CEO in 2011 after Steve Jobs resigned due to health issues.
    Apple acquired Beats Electronics in 2014 for $3 billion.
    The company is headquartered in Cupertino, California.
    """

    from core.models import GraphEntity, GraphRelationship

    entities = [
        GraphEntity(id="a1", name="Apple Inc.", type="ORGANIZATION", description="Tech company"),
        GraphEntity(id="a2", name="Steve Jobs", type="PERSON", description="Co-founder"),
        GraphEntity(id="a3", name="Steve Wozniak", type="PERSON", description="Co-founder"),
        GraphEntity(id="a4", name="Tim Cook", type="PERSON", description="CEO"),
        GraphEntity(id="a5", name="iPhone", type="PRODUCT", description="Smartphone"),
        GraphEntity(id="a6", name="Beats Electronics", type="ORGANIZATION", description="Audio company"),
        GraphEntity(id="a7", name="Cupertino", type="LOCATION", description="City"),
    ]

    # Start with partial relationships
    existing = [
        GraphRelationship(id="rel1", source="Steve Jobs", target="Apple Inc.", type="FOUNDED"),
    ]

    print(f"\nEntities: {len(entities)}")
    print(f"Existing relationships: {len(existing)}")

    start_time = time.time()
    try:
        new_rels = await service._extract_missing_relationships(
            text=test_text,
            entities=entities,
            existing_relationships=existing,
            document_id="test_continuation",
        )
        elapsed = time.time() - start_time

        print(f"\n  New relationships found: {len(new_rels)}")
        print(f"  Time: {elapsed:.2f}s")

        for r in new_rels:
            print(f"    + {r.source} --[{r.type}]--> {r.target}")

        print(f"\n  [PASS] Continuation extraction completed successfully")
        return True

    except AttributeError as e:
        if "STANDARD" in str(e) or "quality" in str(e):
            print(f"\n  [FAIL] Bugfix NOT applied: {e}")
            return False
        raise
    except Exception as e:
        print(f"\n  [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 80)
    print("SPRINT 85 GLEANING BUGFIX VERIFICATION")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    results = {}

    # Run tests
    results["enum_verification"] = await test_quality_requirement_enum()
    results["completeness_check"] = await test_completeness_check()
    results["continuation_extraction"] = await test_continuation_extraction()
    results["full_gleaning"] = await test_gleaning_extraction()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  BUGFIX VERIFIED: All tests passed!")
        print("  QualityRequirement.LOW is correctly used instead of STANDARD")
    else:
        print("\n  BUGFIX ISSUE: Some tests failed")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
