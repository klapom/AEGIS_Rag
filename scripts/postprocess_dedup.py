#!/usr/bin/env python3
"""
Post-process existing benchmark JSON files with MultiCriteriaDeduplicator.

This script:
1. Reads existing benchmark JSON files that contain entity data
2. Applies the MultiCriteriaDeduplicator to all entities
3. Saves new JSON files with "_dedup" suffix

Sprint 43 - Validating deduplication impact on benchmark results.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, '/home/admin/projects/aegisrag/AEGIS_Rag')

from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator


def process_round2_benchmark(input_file: str, output_file: str, deduplicator: MultiCriteriaDeduplicator):
    """Process Round 2 benchmark file (llm_extraction_benchmark_round2_*.json)."""
    print(f"\n{'='*80}")
    print(f"Processing: {input_file}")
    print(f"{'='*80}")

    with open(input_file, 'r') as f:
        data = json.load(f)

    # Process each model's results
    for model_result in data.get('results', []):
        model_name = model_result.get('model', 'unknown')
        print(f"\n--- Model: {model_name} ---")

        # Collect all entities from all chunks
        all_entities = []
        for chunk in model_result.get('chunks', []):
            for entity in chunk.get('entities', []):
                all_entities.append({
                    "name": entity.get("name", ""),
                    "type": entity.get("type", "OTHER"),
                    "description": entity.get("description", "")
                })

        raw_count = len(all_entities)

        # Simple lowercase dedup
        simple_unique = {}
        for e in all_entities:
            key = e["name"].lower()
            if key and key not in simple_unique:
                simple_unique[key] = e
        simple_count = len(simple_unique)

        # Multi-criteria dedup
        if all_entities:
            deduped = deduplicator.deduplicate(all_entities)
            multi_count = len(deduped)
        else:
            deduped = []
            multi_count = 0

        print(f"  Raw entities: {raw_count}")
        print(f"  Simple dedup (lowercase): {simple_count}")
        print(f"  Multi-criteria dedup: {multi_count}")

        reduction = 100 * (1 - multi_count / simple_count) if simple_count > 0 else 0
        print(f"  Additional reduction: {reduction:.1f}%")

        # Add dedup stats to model result
        model_result['dedup_stats'] = {
            'raw_entities': raw_count,
            'simple_dedup_entities': simple_count,
            'multi_dedup_entities': multi_count,
            'additional_reduction_pct': round(reduction, 1)
        }
        model_result['deduplicated_entities'] = [
            {"name": e.get("name"), "type": e.get("type")} for e in deduped
        ]

    # Add processing metadata
    data['dedup_processing'] = {
        'timestamp': datetime.now().isoformat(),
        'deduplicator': 'MultiCriteriaDeduplicator',
        'config': {
            'threshold': 0.93,
            'edit_distance_threshold': 3,
            'min_length_for_edit': 5,
            'min_length_for_substring': 6
        }
    }

    # Save result
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\nSaved to: {output_file}")


def main():
    print("=" * 80)
    print("MULTI-CRITERIA DEDUPLICATION POST-PROCESSING")
    print("=" * 80)

    # Initialize deduplicator
    print("\nInitializing MultiCriteriaDeduplicator...")
    deduplicator = MultiCriteriaDeduplicator(
        threshold=0.93,
        edit_distance_threshold=3,
        min_length_for_edit=5,
        min_length_for_substring=6,
    )

    reports_dir = Path('/home/admin/projects/aegisrag/AEGIS_Rag/reports')

    # Process Round 2 benchmark
    round2_file = reports_dir / 'llm_extraction_benchmark_round2_20251211_071122.json'
    if round2_file.exists():
        output_file = reports_dir / 'llm_extraction_benchmark_round2_20251211_071122_dedup.json'
        process_round2_benchmark(str(round2_file), str(output_file), deduplicator)
    else:
        print(f"File not found: {round2_file}")

    # Print summary
    print("\n" + "=" * 100)
    print("DEDUPLICATION SUMMARY")
    print("=" * 100)


if __name__ == "__main__":
    main()
