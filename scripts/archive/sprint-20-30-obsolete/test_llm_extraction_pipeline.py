"""Test Script: LLM Extraction Pipeline (Option 3)

Sprint 20 Feature: Test pure LLM-based entity/relation extraction
via ExtractionService with Few-Shot prompts.

Compares:
- SpaCy (three_phase): Fast but lower quality
- LLM (llm_extraction): Slow but high quality

Author: Claude Code
Date: 2025-11-07
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from llama_index.core import SimpleDirectoryReader

from src.components.graph_rag.extraction_factory import ExtractionPipelineFactory
from src.core.config import settings

logger = structlog.get_logger(__name__)


async def main():
    print("=" * 80)
    print("LLM EXTRACTION PIPELINE TEST (Option 3)")
    print("=" * 80)

    # Test file: One slide from Performance Tuning
    test_file = (
        project_root
        / "data"
        / "sample_documents"
        / "9. Performance Tuning"
        / "EN-D-Performance Tuning.pptx"
    )

    print(f"\nTest File: {test_file.name}")
    print(f"Extraction Pipeline: {getattr(settings, 'extraction_pipeline', 'three_phase')}")

    if not test_file.exists():
        print(f"\n[ERROR] Test file not found: {test_file}")
        return

    try:
        # Load one page for testing
        print("\n[1/4] Loading document (first page only)...")
        loader = SimpleDirectoryReader(input_files=[str(test_file)])
        documents = loader.load_data()

        if not documents:
            print("\n[ERROR] No documents loaded")
            return

        # Take second page (first is just title)
        first_page = documents[1] if len(documents) > 1 else documents[0]
        text = first_page.get_content()
        doc_id = first_page.doc_id or "test_doc"

        print(f"      Loaded: 1 page ({len(text)} chars)")
        print(f"      Preview: {text[:200]}...")

        # Create extraction pipeline from config
        print("\n[2/4] Creating extraction pipeline...")
        pipeline = ExtractionPipelineFactory.create(settings)
        print(f"      Pipeline type: {type(pipeline).__name__}")

        # Extract entities and relations
        print("\n[3/4] Extracting entities and relations...")
        print("      (This may take 30-60s for LLM extraction)")

        start_time = time.time()
        entities, relations = await pipeline.extract(text, doc_id)
        elapsed_time = time.time() - start_time

        print(f"\n      [OK] Extraction complete in {elapsed_time:.1f}s")
        print(f"      Entities: {len(entities)}")
        print(f"      Relations: {len(relations)}")

        # Display results
        print("\n[4/4] Results:")
        print(f"\n{'='*80}")
        print(f"EXTRACTED ENTITIES ({len(entities)})")
        print(f"{'='*80}")

        # Group by type
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.get("entity_type", "UNKNOWN")
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        for entity_type, ents in sorted(entities_by_type.items()):
            print(f"\n{entity_type} ({len(ents)}):")
            for entity in ents[:5]:  # Show first 5 of each type
                name = entity.get("entity_name", "unnamed")
                desc = entity.get("description", "")
                desc_short = (desc[:60] + "...") if len(desc) > 60 else desc
                print(f"  - {name}: {desc_short}")
            if len(ents) > 5:
                print(f"  ... and {len(ents) - 5} more")

        print(f"\n{'='*80}")
        print(f"EXTRACTED RELATIONS ({len(relations)})")
        print(f"{'='*80}")

        for i, rel in enumerate(relations[:10], 1):  # Show first 10 relations
            source = rel.get("source", "?")
            target = rel.get("target", "?")
            desc = rel.get("description", "")
            strength = rel.get("strength", 0)
            desc_short = (desc[:50] + "...") if len(desc) > 50 else desc
            print(f"  {i}. {source} -> {target}")
            print(f"     {desc_short} (strength: {strength})")

        if len(relations) > 10:
            print(f"  ... and {len(relations) - 10} more")

        # Performance summary
        print(f"\n{'='*80}")
        print("PERFORMANCE SUMMARY")
        print(f"{'='*80}")
        print(f"Pipeline: {getattr(settings, 'extraction_pipeline', 'three_phase')}")
        print(f"Extraction Time: {elapsed_time:.1f}s")
        print(f"Text Length: {len(text)} chars")
        print(f"Entities Extracted: {len(entities)}")
        print(f"Relations Extracted: {len(relations)}")
        print(f"Speed: {len(text)/elapsed_time:.0f} chars/sec")

        # Quality assessment
        print(f"\n{'='*80}")
        print("QUALITY ASSESSMENT")
        print(f"{'='*80}")

        if len(entities) > 0:
            # Count numbers/generic concepts
            generic_count = sum(
                1
                for e in entities
                if e.get("entity_type") == "CONCEPT"
                and (
                    e.get("entity_name", "").isdigit()
                    or "%" in e.get("entity_name", "")
                    or "=" in e.get("entity_name", "")
                )
            )

            org_count = sum(1 for e in entities if e.get("entity_type") == "ORGANIZATION")
            product_count = sum(1 for e in entities if e.get("entity_type") == "PRODUCT")
            tech_count = sum(1 for e in entities if e.get("entity_type") == "TECHNOLOGY")

            print(
                f"Generic Numbers/Concepts: {generic_count} ({generic_count/len(entities)*100:.1f}%)"
            )
            print(f"Organizations: {org_count}")
            print(f"Products: {product_count}")
            print(f"Technologies: {tech_count}")

            if generic_count / len(entities) > 0.5:
                print("\n⚠️  HIGH NOISE: >50% generic entities (consider LLM extraction)")
            else:
                print("\n✅ GOOD QUALITY: <50% noise")
        else:
            print("⚠️  NO ENTITIES EXTRACTED (text too short or no entities found)")

        print(f"\n{'='*80}")
        print("TEST COMPLETE")
        print(f"{'='*80}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
