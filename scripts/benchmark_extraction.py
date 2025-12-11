#!/usr/bin/env python3
"""Benchmark Entity/Relation Extraction Strategies.

Sprint 42: Performance Analysis for Entity/Relation Extraction.

This script compares different extraction strategies:
1. SEQUENTIAL (current): 3 LLM calls - entity, typed_rel, semantic_rel
2. UNIFIED (optimized): 1 LLM call - all in one prompt
3. PARALLEL: 2 LLM calls - entity+typed || semantic

Usage:
    poetry run python scripts/benchmark_extraction.py
    poetry run python scripts/benchmark_extraction.py --texts 5
    poetry run python scripts/benchmark_extraction.py --strategy unified
"""

import asyncio
import json
import sys
from pathlib import Path

import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.components.graph_rag.extraction_benchmark import (
    ExtractionBenchmark,
    ExtractionStrategy,
    run_benchmark,
)

logger = structlog.get_logger(__name__)


def load_ragas_texts(num_texts: int = 5) -> list[dict]:
    """Load texts from RAGAS dataset for benchmarking."""
    dataset_path = Path("reports/track_a_evaluation/datasets/hotpotqa_eval.jsonl")

    if not dataset_path.exists():
        logger.error(f"Dataset not found: {dataset_path}")
        return []

    texts = []
    with open(dataset_path) as f:
        for i, line in enumerate(f):
            if i >= num_texts:
                break
            data = json.loads(line)
            # Combine contexts into single text
            combined_text = "\n\n".join(data["contexts"])
            texts.append({
                "text": combined_text,
                "question_id": data["metadata"]["question_id"],
                "question": data["question"],
            })

    return texts


async def run_comparison_benchmark(num_texts: int = 3):
    """Run A/B comparison between SEQUENTIAL and UNIFIED strategies."""
    logger.info("=" * 70)
    logger.info("EXTRACTION PERFORMANCE BENCHMARK")
    logger.info("=" * 70)

    # Load test texts
    texts_data = load_ragas_texts(num_texts)
    if not texts_data:
        logger.error("No texts loaded for benchmark")
        return

    texts = [t["text"] for t in texts_data]
    logger.info(f"Loaded {len(texts)} texts for benchmarking")

    # Run benchmark comparing strategies
    strategies = [
        ExtractionStrategy.SEQUENTIAL,  # Current: 3 LLM calls
        ExtractionStrategy.UNIFIED,  # Optimized: 1 LLM call
    ]

    results = await run_benchmark(texts, strategies)

    # Detailed comparison
    print("\n" + "=" * 70)
    print("DETAILED COMPARISON")
    print("=" * 70)

    seq_metrics = results.get("sequential", [])
    uni_metrics = results.get("unified", [])

    if seq_metrics and uni_metrics:
        seq_avg_time = sum(m.total_time_ms for m in seq_metrics) / len(seq_metrics)
        uni_avg_time = sum(m.total_time_ms for m in uni_metrics) / len(uni_metrics)

        seq_avg_calls = sum(m.llm_calls for m in seq_metrics) / len(seq_metrics)
        uni_avg_calls = sum(m.llm_calls for m in uni_metrics) / len(uni_metrics)

        seq_avg_entities = sum(m.entities_extracted for m in seq_metrics) / len(seq_metrics)
        uni_avg_entities = sum(m.entities_extracted for m in uni_metrics) / len(uni_metrics)

        speedup = seq_avg_time / uni_avg_time if uni_avg_time > 0 else 0
        call_reduction = (seq_avg_calls - uni_avg_calls) / seq_avg_calls * 100 if seq_avg_calls > 0 else 0

        print(f"\n{'Metric':<25} {'Sequential':<15} {'Unified':<15} {'Improvement':<15}")
        print("-" * 70)
        print(f"{'Avg Time (ms)':<25} {seq_avg_time:<15.1f} {uni_avg_time:<15.1f} {speedup:.2f}x faster")
        print(f"{'Avg LLM Calls':<25} {seq_avg_calls:<15.1f} {uni_avg_calls:<15.1f} {call_reduction:.0f}% reduction")
        print(f"{'Avg Entities':<25} {seq_avg_entities:<15.1f} {uni_avg_entities:<15.1f}")

        # Quality comparison per text
        print("\n" + "-" * 70)
        print("PER-TEXT QUALITY COMPARISON")
        print("-" * 70)

        for i, (seq, uni) in enumerate(zip(seq_metrics, uni_metrics)):
            print(f"\nText {i+1} ({texts_data[i]['question_id']}):")
            print(f"  Sequential: {seq.entities_extracted} entities, "
                  f"{seq.typed_relations_extracted} typed rels, "
                  f"{seq.semantic_relations_extracted} semantic rels, "
                  f"{seq.total_time_ms:.0f}ms")
            print(f"  Unified:    {uni.entities_extracted} entities, "
                  f"{uni.typed_relations_extracted} typed rels, "
                  f"{uni.semantic_relations_extracted} semantic rels, "
                  f"{uni.total_time_ms:.0f}ms")

    return results


async def run_single_extraction(text: str, strategy: str = "unified"):
    """Run a single extraction with detailed output."""
    benchmark = ExtractionBenchmark()

    strategy_enum = ExtractionStrategy(strategy)

    logger.info(f"Running {strategy} extraction on text ({len(text)} chars)...")

    result = await benchmark.extract(
        text=text,
        chunk_id="test_chunk",
        document_id="test_doc",
        strategy=strategy_enum,
    )

    print("\n" + "=" * 70)
    print(f"EXTRACTION RESULT ({strategy.upper()})")
    print("=" * 70)

    print(f"\nMetrics:")
    print(f"  Total time: {result.metrics.total_time_ms:.1f}ms")
    print(f"  LLM calls: {result.metrics.llm_calls}")
    print(f"  Input tokens: {result.metrics.total_input_tokens}")
    print(f"  Output tokens: {result.metrics.total_output_tokens}")

    print(f"\nEntities ({len(result.entities)}):")
    for e in result.entities[:10]:
        print(f"  - {e.name} ({e.type}): {e.description[:50]}...")

    print(f"\nTyped Relationships ({len(result.typed_relationships)}):")
    for r in result.typed_relationships[:10]:
        print(f"  - {r.source} --[{r.type}]--> {r.target}")

    print(f"\nSemantic Relations ({len(result.semantic_relations)}):")
    for r in result.semantic_relations[:10]:
        print(f"  - {r.get('source')} --> {r.get('target')} "
              f"(strength: {r.get('strength')}) {r.get('description', '')[:40]}...")

    return result


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark extraction strategies")
    parser.add_argument("--texts", type=int, default=3, help="Number of texts to benchmark")
    parser.add_argument("--strategy", type=str, default=None, help="Single strategy to test")
    parser.add_argument("--single", action="store_true", help="Run single extraction test")

    args = parser.parse_args()

    if args.single:
        # Single extraction test
        test_text = """Arthur's Magazine (1844–1846) was an American literary periodical published
        in Philadelphia in the 19th century. First for Women is a woman's magazine
        published by Bauer Media Group in the USA. The magazine focuses on women's
        health, beauty, and lifestyle topics."""

        strategy = args.strategy or "unified"
        await run_single_extraction(test_text, strategy)

    elif args.strategy:
        # Test specific strategy
        texts_data = load_ragas_texts(args.texts)
        texts = [t["text"] for t in texts_data]

        strategy_enum = ExtractionStrategy(args.strategy)
        results = await run_benchmark(texts, [strategy_enum])

    else:
        # Full A/B comparison
        await run_comparison_benchmark(args.texts)


if __name__ == "__main__":
    asyncio.run(main())
