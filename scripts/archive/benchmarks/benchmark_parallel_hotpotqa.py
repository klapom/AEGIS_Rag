#!/usr/bin/env python3
"""
Parallel Pipeline Benchmark using HotPotQA fullwiki dataset.

Tests the ParallelExtractor (gemma3:4b + qwen2.5:7b) against individual models
using the same HotPotQA samples from benchmark_chunking_smart.py.

Sprint 43 - Validating parallel extraction strategy with real evaluation data.
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


def load_smart_samples() -> dict:
    """Load same samples as benchmark_chunking_smart.py."""
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

    # Create combined large sample
    combined_context = ""
    combined_questions = []
    combined_ids = []

    for s in all_samples:
        if len(combined_context) < 15000:
            combined_context += "\n\n" + s['context'] if combined_context else s['context']
            combined_questions.append(s['question'])
            combined_ids.append(s['id'])

    large_sample = {
        'id': 'combined_large',
        'question': ' | '.join(combined_questions),
        'answer': 'Combined answers',
        'context': combined_context,
        'context_length': len(combined_context),
        'is_combined': True
    }

    print(f"Created large sample: {large_sample['context_length']} chars from {len(combined_ids)} samples")
    sys.stdout.flush()

    return {
        'medium': medium_samples,
        'large': [large_sample]
    }


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


async def benchmark_parallel_sample(
    extractor: ParallelExtractor,
    sample: dict,
    chunk_size: int
) -> dict:
    """Benchmark parallel extraction for a specific sample and chunk size."""
    text = sample['context']
    chunks = chunk_text(text, chunk_size)

    all_entities = []
    all_relations = []
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

        all_entities.extend(result.entities)
        all_relations.extend(result.relationships)
        total_time += chunk_time

        # Track per-model contributions
        for model in extractor.models:
            per_model_entities[model] += result.metrics.entities_per_model.get(model, 0)
            per_model_relations[model] += result.metrics.relations_per_model.get(model, 0)

        print(f"      Chunk {i+1}/{len(chunks)}: {len(result.entities)} merged ent, "
              f"{len(result.relationships)} merged rel ({chunk_time:.1f}s)")
        sys.stdout.flush()

    # Deduplicate merged entities by name
    unique_entities = {}
    for e in all_entities:
        name = e.name.lower()
        if name and name not in unique_entities:
            unique_entities[name] = e

    # Deduplicate merged relations by source+target+type
    unique_relations = {}
    for r in all_relations:
        key = f"{r.source.lower()}|{r.target.lower()}|{r.type.lower()}"
        if key not in unique_relations:
            unique_relations[key] = r

    return {
        "sample_id": sample['id'],
        "context_length": len(text),
        "chunk_size": chunk_size,
        "num_chunks": len(chunks),
        "total_entities_raw": len(all_entities),
        "unique_entities": len(unique_entities),
        "total_relations_raw": len(all_relations),
        "unique_relations": len(unique_relations),
        "total_time": total_time,
        "per_model_entities": per_model_entities,
        "per_model_relations": per_model_relations,
    }


async def main():
    # Load samples
    samples = load_smart_samples()

    print("\n" + "=" * 80)
    print("PARALLEL PIPELINE BENCHMARK (HotPotQA)")
    print("=" * 80)
    print("Models: gemma3:4b + qwen2.5:7b (parallel)")
    print(f"Medium samples: {len(samples['medium'])} samples")
    print(f"Large sample: {len(samples['large'])} samples")
    print("=" * 80)
    sys.stdout.flush()

    # Create parallel extractor
    extractor = ParallelExtractor()

    all_results = []

    # Test chunk sizes (focus on a few key sizes based on previous benchmark)
    chunk_sizes = [500, 1000, 2000, 4000]

    # Test medium samples
    for sample in samples['medium']:
        print(f"\n--- Medium Sample: {sample['id'][:30]}... ({sample['context_length']} chars) ---")
        print(f"    Question: {sample['question'][:50]}...")
        sys.stdout.flush()

        for chunk_size in chunk_sizes:
            print(f"  Chunk size {chunk_size}:")
            sys.stdout.flush()
            result = await benchmark_parallel_sample(extractor, sample, chunk_size)
            all_results.append(result)
            print(f"    -> {result['num_chunks']} chunks, {result['unique_entities']} unique entities, "
                  f"{result['unique_relations']} unique relations, {result['total_time']:.1f}s total")
            print(f"       Per model: gemma3:4b={result['per_model_entities'].get('gemma3:4b', 0)} ent, "
                  f"qwen2.5:7b={result['per_model_entities'].get('qwen2.5:7b', 0)} ent")
            sys.stdout.flush()

    # Test large sample with 10000 chunk size
    for sample in samples['large']:
        print(f"\n--- Large Sample: {sample['id']} ({sample['context_length']} chars) ---")
        print(f"    Question: {sample['question'][:80]}...")
        sys.stdout.flush()

        print("  Chunk size 10000:")
        sys.stdout.flush()
        result = await benchmark_parallel_sample(extractor, sample, 10000)
        all_results.append(result)
        print(f"    -> {result['num_chunks']} chunks, {result['unique_entities']} unique entities, "
              f"{result['unique_relations']} unique relations, {result['total_time']:.1f}s total")
        print(f"       Per model: gemma3:4b={result['per_model_entities'].get('gemma3:4b', 0)} ent, "
              f"qwen2.5:7b={result['per_model_entities'].get('qwen2.5:7b', 0)} ent")
        sys.stdout.flush()

    # Summary
    print("\n" + "=" * 100)
    print("PARALLEL BENCHMARK SUMMARY")
    print("=" * 100)

    print(f"\n{'Sample':<15} {'Chunk':<8} {'Chunks':<8} {'Entities':<10} {'Relations':<10} "
          f"{'Time (s)':<10} {'gemma3':<10} {'qwen2.5':<10}")
    print("-" * 100)

    for r in all_results:
        sample_id = r['sample_id'][:12] + "..." if len(r['sample_id']) > 15 else r['sample_id']
        print(f"{sample_id:<15} {r['chunk_size']:<8} {r['num_chunks']:<8} {r['unique_entities']:<10} "
              f"{r['unique_relations']:<10} {r['total_time']:<10.1f} "
              f"{r['per_model_entities'].get('gemma3:4b', 0):<10} "
              f"{r['per_model_entities'].get('qwen2.5:7b', 0):<10}")

    print("-" * 100)
    sys.stdout.flush()

    # Compare with individual model results
    print("\n" + "=" * 100)
    print("COMPARISON WITH INDIVIDUAL MODELS (at 500 char chunks)")
    print("=" * 100)

    # Get results for 500 chunk size
    results_500 = [r for r in all_results if r['chunk_size'] == 500]
    if results_500:
        total_parallel_ent = sum(r['unique_entities'] for r in results_500)
        total_parallel_rel = sum(r['unique_relations'] for r in results_500)
        total_parallel_time = sum(r['total_time'] for r in results_500)

        # Expected individual results from previous benchmarks
        # gemma3:4b at 500: 104+95=199 unique entities (across 2 samples)
        # qwen2.5:7b at 500: 92+68=160 unique entities (across 2 samples)
        print("\nParallel (gemma3:4b + qwen2.5:7b combined):")
        print(f"  Unique Entities: {total_parallel_ent}")
        print(f"  Unique Relations: {total_parallel_rel}")
        print(f"  Total Time: {total_parallel_time:.1f}s")

        print("\nExpected from individual benchmarks (500 chars, 2 medium samples):")
        print("  gemma3:4b alone: ~199 entities, ~185 relations, ~227s")
        print("  qwen2.5:7b alone: ~160 entities, ~124 relations, ~306s")

    # Save results
    output_file = f"reports/benchmark_parallel_hotpotqa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "strategy": "ParallelExtractor with gemma3:4b + qwen2.5:7b",
            "models": ["gemma3:4b", "qwen2.5:7b"],
            "chunk_sizes_tested": chunk_sizes + [10000],
            "results": all_results
        }, f, indent=2, default=str)

    print(f"\nResults saved to: {output_file}")
    sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
