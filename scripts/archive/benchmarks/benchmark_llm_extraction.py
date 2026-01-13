#!/usr/bin/env python3
"""Benchmark LLM Entity Extraction across different models.

Sprint 43: Compare extraction quality across LLMs:
- qwen3:32b (current default)
- sam860/qwen3:8b-Q4_K_M (quantized)
- nuextract:3.8b (specialized extraction model)

Uses RAGAS sample, goes through full pipeline AFTER Docling, BEFORE chunking.
Saves all entities/relations for analysis.

Usage:
    poetry run python scripts/benchmark_llm_extraction.py
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Models to benchmark
MODELS_TO_TEST = [
    "qwen3:32b",           # Current default (20GB)
    "sam860/qwen3:8b-Q4_K_M",  # Quantized 8B (5GB)
    "nuextract:3.8b",      # Specialized extraction (2.2GB)
]

# Chunk size for testing
CHUNK_SIZE = 500


class MockConfig:
    """Mock config to override LLM model for testing."""

    def __init__(self, model: str):
        self.lightrag_llm_model = model
        self.ollama_base_url = "http://localhost:11434"
        self.lightrag_llm_max_tokens = 4096
        self.extraction_pipeline = "llm_extraction"
        self.enable_legacy_extraction = False


async def extract_with_model(
    text: str,
    model: str,
    document_id: str,
) -> dict:
    """Extract entities/relations using specific LLM model.

    Uses ExtractionPipelineFactory (same as real pipeline) with custom model.
    """
    from src.components.graph_rag.extraction_factory import ExtractionPipelineFactory

    print(f"\n{'='*60}")
    print(f"Model: {model}")
    print(f"{'='*60}")

    start_time = time.time()

    # Create extraction pipeline with specific model via mock config
    mock_config = MockConfig(model)
    extractor = ExtractionPipelineFactory.create(mock_config)

    all_entities = []
    all_relations = []
    chunk_results = []

    # Chunk text
    chunks = []
    for i in range(0, len(text), CHUNK_SIZE):
        chunk_text = text[i:i + CHUNK_SIZE]
        if chunk_text.strip():
            chunks.append({
                "chunk_id": f"chunk_{i // CHUNK_SIZE}",
                "text": chunk_text,
                "chunk_index": i // CHUNK_SIZE,
            })

    print(f"Text length: {len(text)} chars")
    print(f"Chunks: {len(chunks)} x {CHUNK_SIZE} chars")

    # Extract from each chunk
    for chunk in chunks:
        chunk_start = time.time()
        print(f"\n  Chunk {chunk['chunk_index']}...")

        try:
            entities, relations = await extractor.extract(
                text=chunk["text"],
                document_id=f"{document_id}#{chunk['chunk_index']}",
            )

            chunk_time = time.time() - chunk_start

            # Annotate with chunk info
            for entity in entities:
                entity["chunk_id"] = chunk["chunk_id"]
                entity["chunk_index"] = chunk["chunk_index"]

            for relation in relations:
                relation["chunk_id"] = chunk["chunk_id"]
                relation["chunk_index"] = chunk["chunk_index"]

            all_entities.extend(entities)
            all_relations.extend(relations)

            chunk_results.append({
                "chunk_index": chunk["chunk_index"],
                "text_length": len(chunk["text"]),
                "entities": len(entities),
                "relations": len(relations),
                "time_seconds": round(chunk_time, 2),
            })

            print(f"    -> {len(entities)} entities, {len(relations)} relations ({chunk_time:.1f}s)")

        except Exception as e:
            print(f"    -> ERROR: {e}")
            chunk_results.append({
                "chunk_index": chunk["chunk_index"],
                "error": str(e),
            })

    total_time = time.time() - start_time

    # Summary
    print(f"\n  TOTAL: {len(all_entities)} entities, {len(all_relations)} relations")
    print(f"  Time: {total_time:.1f}s")

    return {
        "model": model,
        "chunk_size": CHUNK_SIZE,
        "total_chunks": len(chunks),
        "total_entities": len(all_entities),
        "total_relations": len(all_relations),
        "total_time_seconds": round(total_time, 2),
        "avg_time_per_chunk": round(total_time / len(chunks), 2) if chunks else 0,
        "chunk_results": chunk_results,
        "entities": all_entities,
        "relations": all_relations,
    }


async def main():
    """Run extraction benchmark across models."""
    print("=" * 80)
    print("Sprint 43: LLM Extraction Benchmark")
    print("=" * 80)

    # Load RAGAS sample - pick one with good entity density
    dataset_path = Path("reports/track_a_evaluation/datasets/hotpotqa_eval.jsonl")
    with open(dataset_path) as f:
        samples = [json.loads(line) for line in f if line.strip()]

    # Use sample 2 (Allie Goertz / Simpsons) - good entity variety
    # Plus add a few more for more text
    selected_samples = samples[0:3]  # First 3 samples

    print(f"\nUsing {len(selected_samples)} samples:")
    for i, s in enumerate(selected_samples):
        print(f"  {i+1}. {s['question'][:50]}...")

    # Combine contexts
    full_text = " ".join(
        ctx for sample in selected_samples for ctx in sample["contexts"]
    )
    print(f"\nTotal text: {len(full_text)} characters")

    # Run benchmark for each model
    results = {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "samples_used": [
            {"question": s["question"], "ground_truth": s["ground_truth"]}
            for s in selected_samples
        ],
        "full_text": full_text,
        "chunk_size": CHUNK_SIZE,
        "models": {},
    }

    for model in MODELS_TO_TEST:
        print(f"\n\n{'#'*80}")
        print(f"# BENCHMARKING: {model}")
        print(f"{'#'*80}")

        try:
            model_result = await extract_with_model(
                text=full_text,
                model=model,
                document_id=f"benchmark_{model.replace(':', '_').replace('/', '_')}",
            )
            results["models"][model] = model_result

        except Exception as e:
            print(f"\nERROR with {model}: {e}")
            results["models"][model] = {"error": str(e)}

    # Apply deduplication to each model's results
    print("\n\n" + "=" * 80)
    print("APPLYING DEDUPLICATION")
    print("=" * 80)

    from src.components.graph_rag.semantic_deduplicator import create_deduplicator_from_config
    from src.core.config import get_settings

    settings = get_settings()
    deduplicator = create_deduplicator_from_config(settings)

    for model, model_result in results["models"].items():
        if "error" in model_result:
            continue

        entities = model_result.get("entities", [])
        if entities:
            deduped = deduplicator.deduplicate(entities)
            model_result["deduplicated_entities"] = deduped
            model_result["dedup_stats"] = {
                "before": len(entities),
                "after": len(deduped),
                "removed": len(entities) - len(deduped),
                "reduction_pct": round(
                    (len(entities) - len(deduped)) / len(entities) * 100, 1
                ) if entities else 0,
            }
            print(f"\n{model}:")
            print(f"  Entities: {len(entities)} -> {len(deduped)} ({model_result['dedup_stats']['reduction_pct']}% reduction)")

    # Save results
    output_path = Path(f"reports/llm_extraction_benchmark_{results['timestamp']}.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n\n{'='*80}")
    print(f"Results saved to: {output_path}")
    print("=" * 80)

    # Print comparison table
    print("\n\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print(f"\n{'Model':<30} {'Entities':<12} {'Relations':<12} {'Deduped':<12} {'Time (s)':<12}")
    print("-" * 80)

    for model in MODELS_TO_TEST:
        r = results["models"].get(model, {})
        if "error" in r:
            print(f"{model:<30} ERROR: {r['error'][:40]}")
        else:
            dedup_count = r.get("dedup_stats", {}).get("after", r.get("total_entities", 0))
            print(f"{model:<30} {r.get('total_entities', 0):<12} {r.get('total_relations', 0):<12} {dedup_count:<12} {r.get('total_time_seconds', 0):<12}")

    print("\n" + "-" * 80)
    print("Deduped = after MultiCriteriaDeduplicator")


if __name__ == "__main__":
    asyncio.run(main())
