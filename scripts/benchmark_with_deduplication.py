#!/usr/bin/env python3
"""
Benchmark with MultiCriteriaDeduplicator applied.

This script re-runs extraction for selected samples and applies the production
MultiCriteriaDeduplicator to compare with simple lowercase deduplication.

Sprint 43 - Validating deduplication impact on benchmark results.
"""
import asyncio
import json
import sys
import time
from datetime import datetime

from datasets import load_dataset

# Add project root to path
sys.path.insert(0, '/home/admin/projects/aegisrag/AEGIS_Rag')

from src.components.graph_rag.parallel_extractor import ParallelExtractor
from src.components.graph_rag.semantic_deduplicator import MultiCriteriaDeduplicator


def load_smart_samples() -> dict:
    """Load same samples as other benchmarks."""
    print("Loading samples from HotPotQA fullwiki...")
    sys.stdout.flush()
    ds = load_dataset('hotpot_qa', 'fullwiki', split='validation[:20]')

    all_samples = []
    for sample in ds:
        contexts = sample.get('context', {})
        if isinstance(contexts, dict):
            sentences = contexts.get('sentences', [])
            total_text = ' '.join([' '.join(s) if isinstance(s, list) else s for s in sentences])
        else:
            total_text = str(contexts)

        all_samples.append({
            'id': sample.get('id', f'sample_{len(all_samples)}'),
            'question': sample.get('question', ''),
            'answer': sample.get('answer', ''),
            'context': total_text,
            'context_length': len(total_text)
        })

    # Find 2 samples in 5000-7500 range for medium testing
    medium_samples = sorted(
        [s for s in all_samples if 5000 <= s['context_length'] <= 7500],
        key=lambda x: x['context_length'],
        reverse=True
    )[:2]

    print(f"Found {len(medium_samples)} medium samples: {[s['context_length'] for s in medium_samples]}")
    sys.stdout.flush()

    return {'medium': medium_samples}


def chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split text into chunks (same logic as other benchmarks)."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            for boundary in ['. ', '.\n', '? ', '! ']:
                last_boundary = text.rfind(boundary, start + chunk_size // 2, end + 100)
                if last_boundary != -1:
                    end = last_boundary + len(boundary)
                    break
        chunks.append(text[start:end].strip())
        start = end

    return [c for c in chunks if c]


async def benchmark_with_deduplication(
    extractor: ParallelExtractor,
    deduplicator: MultiCriteriaDeduplicator,
    sample: dict,
    chunk_size: int
) -> dict:
    """Run parallel extraction and apply MultiCriteriaDeduplicator."""
    text = sample['context']
    chunks = chunk_text(text, chunk_size)

    # Collect all raw entities from all chunks
    all_raw_entities = []
    all_raw_relations = []
    total_time = 0
    per_model_entities = {}
    per_model_relations = {}

    for model in extractor.models:
        per_model_entities[model] = 0
        per_model_relations[model] = 0

    for i, chunk in enumerate(chunks):
        chunk_start = time.time()
        result = await extractor.extract(chunk, f"{sample['id']}_chunk_{i}")
        chunk_time = time.time() - chunk_start

        # Collect raw entities (before deduplication)
        for e in result.entities:
            all_raw_entities.append({
                "name": e.name,
                "type": e.type,
                "description": e.description or ""
            })

        # Collect raw relations
        for r in result.relationships:
            all_raw_relations.append({
                "source": r.source,
                "target": r.target,
                "type": r.type,
                "description": r.description or ""
            })

        total_time += chunk_time

        # Track per-model contributions
        for model in extractor.models:
            per_model_entities[model] += result.metrics.entities_per_model.get(model, 0)
            per_model_relations[model] += result.metrics.relations_per_model.get(model, 0)

        print(f"      Chunk {i+1}/{len(chunks)}: {len(result.entities)} ent, "
              f"{len(result.relationships)} rel ({chunk_time:.1f}s)")
        sys.stdout.flush()

    # === SIMPLE DEDUPLICATION (lowercase name only) ===
    simple_unique_entities = {}
    for e in all_raw_entities:
        name = e["name"].lower()
        if name and name not in simple_unique_entities:
            simple_unique_entities[name] = e
    simple_unique_count = len(simple_unique_entities)

    simple_unique_relations = {}
    for r in all_raw_relations:
        key = f"{r['source'].lower()}|{r['target'].lower()}|{r['type'].lower()}"
        if key not in simple_unique_relations:
            simple_unique_relations[key] = r
    simple_unique_rel_count = len(simple_unique_relations)

    # === MULTI-CRITERIA DEDUPLICATION ===
    multi_dedup_entities = deduplicator.deduplicate(all_raw_entities)
    multi_unique_count = len(multi_dedup_entities)

    # Relations: Apply same logic but with deduplicated entity names
    multi_unique_relations = {}
    for r in all_raw_relations:
        key = f"{r['source'].lower()}|{r['target'].lower()}|{r['type'].lower()}"
        if key not in multi_unique_relations:
            multi_unique_relations[key] = r
    multi_unique_rel_count = len(multi_unique_relations)

    return {
        "sample_id": sample['id'],
        "context_length": len(text),
        "chunk_size": chunk_size,
        "num_chunks": len(chunks),
        "raw_entities": len(all_raw_entities),
        "raw_relations": len(all_raw_relations),
        "simple_dedup_entities": simple_unique_count,
        "simple_dedup_relations": simple_unique_rel_count,
        "multi_dedup_entities": multi_unique_count,
        "multi_dedup_relations": multi_unique_rel_count,
        "dedup_reduction_pct": round(100 * (1 - multi_unique_count / simple_unique_count), 1) if simple_unique_count > 0 else 0,
        "total_time": total_time,
        "per_model_entities": per_model_entities,
        "per_model_relations": per_model_relations,
        "entity_names_raw": [e["name"] for e in all_raw_entities],
        "entity_names_dedup": [e["name"] for e in multi_dedup_entities],
    }


async def main():
    # Load samples
    samples = load_smart_samples()

    print("\n" + "=" * 80)
    print("PARALLEL BENCHMARK WITH MULTI-CRITERIA DEDUPLICATION")
    print("=" * 80)
    print(f"Models: gemma3:4b + qwen2.5:7b (parallel)")
    print(f"Samples: {len(samples['medium'])} medium samples")
    print(f"Chunk size: 500 (focus on highest coverage scenario)")
    print("=" * 80)
    sys.stdout.flush()

    # Create parallel extractor
    extractor = ParallelExtractor()

    # Create MultiCriteriaDeduplicator
    print("\nInitializing MultiCriteriaDeduplicator...")
    sys.stdout.flush()
    deduplicator = MultiCriteriaDeduplicator(
        threshold=0.93,
        edit_distance_threshold=3,
        min_length_for_edit=5,
        min_length_for_substring=6,
    )

    all_results = []

    # Test with 500 char chunks only (the most important case)
    chunk_size = 500

    for sample in samples['medium']:
        print(f"\n--- Sample: {sample['id'][:30]}... ({sample['context_length']} chars) ---")
        print(f"    Question: {sample['question'][:50]}...")
        print(f"  Chunk size {chunk_size}:")
        sys.stdout.flush()

        result = await benchmark_with_deduplication(extractor, deduplicator, sample, chunk_size)
        all_results.append(result)

        print(f"\n    Results:")
        print(f"      Raw entities: {result['raw_entities']}")
        print(f"      Simple dedup (lowercase): {result['simple_dedup_entities']}")
        print(f"      Multi-criteria dedup: {result['multi_dedup_entities']}")
        print(f"      Additional reduction: {result['dedup_reduction_pct']:.1f}%")
        sys.stdout.flush()

    # Summary
    print("\n" + "=" * 100)
    print("DEDUPLICATION COMPARISON SUMMARY")
    print("=" * 100)

    print(f"\n{'Sample':<20} {'Raw':<8} {'Simple':<10} {'Multi':<10} {'Reduction':<10}")
    print("-" * 60)

    for r in all_results:
        sample_id = r['sample_id'][:17] + "..." if len(r['sample_id']) > 20 else r['sample_id']
        print(f"{sample_id:<20} {r['raw_entities']:<8} {r['simple_dedup_entities']:<10} "
              f"{r['multi_dedup_entities']:<10} {r['dedup_reduction_pct']:<10.1f}%")

    # Save results
    output_file = f"reports/benchmark_with_dedup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "strategy": "ParallelExtractor with MultiCriteriaDeduplicator",
            "models": ["gemma3:4b", "qwen2.5:7b"],
            "chunk_size": chunk_size,
            "deduplicator_config": {
                "threshold": 0.93,
                "edit_distance_threshold": 3,
                "min_length_for_edit": 5,
                "min_length_for_substring": 6,
            },
            "results": all_results
        }, f, indent=2, default=str)

    print(f"\nResults saved to: {output_file}")
    sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
