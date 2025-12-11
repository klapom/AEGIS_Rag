#!/usr/bin/env python3
"""Test MultiCriteriaDeduplicator in normal LangGraph pipeline.

Sprint 43: Test deduplication with RAGAS sample using 500-char chunks.
Uses the normal extraction pipeline (ExtractionService) - same as graph_extraction_node.

Saves original entities/relations for parameter tuning.

Usage:
    poetry run python scripts/test_dedup_pipeline.py
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Run deduplication test with RAGAS sample."""
    from src.components.graph_rag.extraction_factory import create_extraction_pipeline_from_config
    from src.components.graph_rag.semantic_deduplicator import (
        MultiCriteriaDeduplicator,
        SemanticDeduplicator,
        create_deduplicator_from_config,
    )
    from src.core.config import get_settings

    print("=" * 80)
    print("Sprint 43: MultiCriteriaDeduplicator Pipeline Test")
    print("=" * 80)

    # Load RAGAS samples
    dataset_path = Path("reports/track_a_evaluation/datasets/hotpotqa_eval.jsonl")
    with open(dataset_path) as f:
        samples = [json.loads(line) for line in f if line.strip()]

    # Use MULTIPLE samples to get more text and more chances for duplicate entities
    # Take first 5 samples to get ~2000-3000 chars
    selected_samples = samples[:5]
    print(f"\nUsing {len(selected_samples)} samples for more entities & duplicate chances")
    for i, s in enumerate(selected_samples):
        print(f"  {i+1}. {s['question'][:60]}...")

    # Combine all contexts from all samples
    full_text = " ".join(
        ctx for sample in selected_samples for ctx in sample["contexts"]
    )
    print(f"\nFull text ({len(full_text)} chars):")
    print(f"  {full_text[:200]}...")

    # Chunk into 500-char pieces (simulating post-Docling chunking)
    CHUNK_SIZE = 500
    chunks = []
    for i in range(0, len(full_text), CHUNK_SIZE):
        chunk_text = full_text[i : i + CHUNK_SIZE]
        if chunk_text.strip():
            chunks.append({
                "chunk_id": f"test_chunk_{i // CHUNK_SIZE}",
                "text": chunk_text,
                "chunk_index": i // CHUNK_SIZE,
            })

    print(f"\nChunked into {len(chunks)} chunks of ~{CHUNK_SIZE} chars each")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i}: {len(chunk['text'])} chars")

    # Create extraction pipeline (same as graph_extraction_node uses)
    settings = get_settings()
    extractor = create_extraction_pipeline_from_config(settings)
    print(f"\nExtraction pipeline: {type(extractor).__name__}")

    # Extract entities and relations from each chunk
    all_entities = []
    all_relations = []

    print("\n" + "-" * 40)
    print("Extracting entities/relations per chunk...")
    print("-" * 40)

    for chunk in chunks:
        print(f"\nProcessing chunk {chunk['chunk_index']}...")
        try:
            entities, relations = await extractor.extract(
                text=chunk["text"],
                document_id=f"test_doc#{chunk['chunk_index']}",
            )

            # Annotate with chunk info
            for entity in entities:
                entity["chunk_id"] = chunk["chunk_id"]
                entity["chunk_index"] = chunk["chunk_index"]

            for relation in relations:
                relation["chunk_id"] = chunk["chunk_id"]
                relation["chunk_index"] = chunk["chunk_index"]

            all_entities.extend(entities)
            all_relations.extend(relations)

            print(f"  -> {len(entities)} entities, {len(relations)} relations")

        except Exception as e:
            print(f"  -> ERROR: {e}")

    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE - BEFORE DEDUPLICATION")
    print("=" * 80)
    print(f"Total entities: {len(all_entities)}")
    print(f"Total relations: {len(all_relations)}")

    # Show all entities with details
    print("\n--- Original Entities (for tuning) ---")
    for i, entity in enumerate(all_entities):
        name = entity.get("name", entity.get("entity_name", "?"))
        etype = entity.get("type", entity.get("entity_type", "?"))
        desc = entity.get("description", "")[:50]
        print(f"  {i + 1}. [{etype}] {name} - {desc}...")

    # Save original data for tuning
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"reports/dedup_test_{timestamp}.json")

    original_data = {
        "timestamp": timestamp,
        "samples_used": [
            {"question": s["question"], "ground_truth": s["ground_truth"]}
            for s in selected_samples
        ],
        "chunk_size": CHUNK_SIZE,
        "chunks": chunks,
        "original_entities": all_entities,
        "original_relations": all_relations,
        "stats_before_dedup": {
            "total_entities": len(all_entities),
            "total_relations": len(all_relations),
        },
    }

    # Apply deduplication
    print("\n" + "=" * 80)
    print("APPLYING MULTI-CRITERIA DEDUPLICATION")
    print("=" * 80)

    deduplicator = create_deduplicator_from_config(settings)
    print(f"Deduplicator type: {type(deduplicator).__name__}")

    if isinstance(deduplicator, MultiCriteriaDeduplicator):
        print(f"  - Edit distance threshold: {deduplicator.edit_distance_threshold}")
        print(f"  - Min length for edit: {deduplicator.min_length_for_edit}")
        print(f"  - Min length for substring: {deduplicator.min_length_for_substring}")
        print(f"  - Similarity threshold: {deduplicator.threshold}")

    # Deduplicate
    deduped_entities = deduplicator.deduplicate(all_entities)

    print(f"\n--- After Deduplication ---")
    print(f"Entities: {len(all_entities)} -> {len(deduped_entities)}")
    print(f"Removed: {len(all_entities) - len(deduped_entities)} duplicates")

    # Show deduplicated entities
    print("\n--- Deduplicated Entities ---")
    for i, entity in enumerate(deduped_entities):
        name = entity.get("name", entity.get("entity_name", "?"))
        etype = entity.get("type", entity.get("entity_type", "?"))
        desc = entity.get("description", "")[:50]
        print(f"  {i + 1}. [{etype}] {name} - {desc}...")

    # Add dedup results to output
    original_data["deduplicated_entities"] = deduped_entities
    original_data["stats_after_dedup"] = {
        "total_entities": len(deduped_entities),
        "removed": len(all_entities) - len(deduped_entities),
        "dedup_rate": round(
            (len(all_entities) - len(deduped_entities)) / max(len(all_entities), 1) * 100, 2
        ),
    }

    # Find which entities were merged (for analysis)
    original_names = {e.get("name", e.get("entity_name", "")) for e in all_entities}
    deduped_names = {e.get("name", e.get("entity_name", "")) for e in deduped_entities}
    removed_names = original_names - deduped_names

    if removed_names:
        print("\n--- Entities Removed as Duplicates ---")
        for name in sorted(removed_names):
            print(f"  - {name}")
        original_data["removed_entity_names"] = list(removed_names)

    # Save to JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(original_data, f, indent=2, default=str)

    print(f"\n" + "=" * 80)
    print(f"Results saved to: {output_path}")
    print("=" * 80)

    # Summary
    print("\n--- SUMMARY ---")
    print(f"Chunk size: {CHUNK_SIZE} chars")
    print(f"Chunks: {len(chunks)}")
    print(f"Entities before: {len(all_entities)}")
    print(f"Entities after: {len(deduped_entities)}")
    print(f"Dedup rate: {original_data['stats_after_dedup']['dedup_rate']}%")

    # =========================================================================
    # SYNTHETIC TEST: Verify dedup logic works with known duplicates
    # =========================================================================
    print("\n" + "=" * 80)
    print("SYNTHETIC DEDUP TEST (verifying algorithm)")
    print("=" * 80)

    synthetic_entities = [
        # Exact case variation
        {"name": "Nicolas Cage", "type": "PERSON", "description": "Actor 1"},
        {"name": "nicolas cage", "type": "PERSON", "description": "Actor 2"},
        {"name": "NICOLAS CAGE", "type": "PERSON", "description": "Actor 3"},
        # Typo (edit distance)
        {"name": "Nicholas Cage", "type": "PERSON", "description": "Typo variant"},
        # Different person (should NOT be merged)
        {"name": "Matt Groening", "type": "PERSON", "description": "Simpsons creator"},
        # Substring test
        {"name": "The Simpsons", "type": "PRODUCT", "description": "TV show"},
        {"name": "Simpsons", "type": "PRODUCT", "description": "Short name"},
        # Short names (should NOT match due to min-length)
        {"name": "AI", "type": "CONCEPT", "description": "Artificial Intelligence"},
        {"name": "UI", "type": "CONCEPT", "description": "User Interface"},
    ]

    print(f"\nSynthetic test entities: {len(synthetic_entities)}")
    for e in synthetic_entities:
        print(f"  - [{e['type']}] {e['name']}")

    synthetic_deduped = deduplicator.deduplicate(synthetic_entities)

    print(f"\nAfter deduplication: {len(synthetic_deduped)}")
    for e in synthetic_deduped:
        name = e.get("name", e.get("entity_name", "?"))
        print(f"  - [{e['type']}] {name}")

    print(f"\nSynthetic dedup: {len(synthetic_entities)} -> {len(synthetic_deduped)}")
    print(f"Expected: 9 -> 5 (Nicolas variants merged, Simpsons variants merged)")
    print(f"AI/UI should remain separate (too short for edit/substring)")


if __name__ == "__main__":
    asyncio.run(main())
