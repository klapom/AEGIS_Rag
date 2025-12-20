#!/usr/bin/env python3
"""Extended Benchmark: SEQUENTIAL vs UNIFIED Extraction with 30 Samples.

This script compares extraction strategies using 30 samples from RAGAS WikiQA dataset.

Usage:
    poetry run python scripts/benchmark_extraction_30.py
    poetry run python scripts/benchmark_extraction_30.py --samples 30
    poetry run python scripts/benchmark_extraction_30.py --strategy unified
"""

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.components.graph_rag.extraction_benchmark import (
    ExtractionBenchmark,
    ExtractionStrategy,
)

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkSample:
    """A single benchmark sample."""
    sample_id: str
    question: str
    context: str
    text_length: int
    domain: str = "general"


@dataclass
class StrategyResult:
    """Aggregated results for a single strategy."""
    strategy: str
    samples_processed: int
    total_time_ms: float
    avg_time_ms: float
    total_entities: int
    avg_entities: float
    total_typed_rels: int
    avg_typed_rels: float
    total_semantic_rels: int
    avg_semantic_rels: float
    total_llm_calls: int
    avg_llm_calls: float
    total_input_tokens: int
    total_output_tokens: int
    errors: list[str] = field(default_factory=list)
    per_sample_metrics: list[dict] = field(default_factory=list)


def load_wikiqa_samples(num_samples: int = 30) -> list[BenchmarkSample]:
    """Load samples from RAGAS WikiQA dataset."""
    try:
        from datasets import load_dataset
        ds = load_dataset('explodinggradients/ragas-wikiqa', split='train')

        samples = []
        # Distribute samples evenly across dataset
        step = max(1, len(ds) // num_samples)

        for i in range(0, min(len(ds), num_samples * step), step):
            if len(samples) >= num_samples:
                break

            item = ds[i]
            # Combine contexts into single text
            contexts = item.get('context', [])
            if isinstance(contexts, list):
                context_text = "\n\n".join(contexts)
            else:
                context_text = str(contexts)

            # Determine domain from question content
            question = item.get('question', '')
            domain = _classify_domain(question)

            samples.append(BenchmarkSample(
                sample_id=item.get('question_id', f'Q{i}'),
                question=question,
                context=context_text,
                text_length=len(context_text),
                domain=domain,
            ))

        return samples

    except Exception as e:
        logger.error(f"Failed to load WikiQA dataset: {e}")
        return []


def _classify_domain(question: str) -> str:
    """Classify question into a domain category."""
    question_lower = question.lower()

    if any(kw in question_lower for kw in ['war', 'battle', 'military', 'army', 'navy']):
        return 'history_military'
    elif any(kw in question_lower for kw in ['president', 'government', 'election', 'political', 'congress']):
        return 'politics'
    elif any(kw in question_lower for kw in ['science', 'research', 'study', 'experiment', 'theory']):
        return 'science'
    elif any(kw in question_lower for kw in ['company', 'business', 'market', 'economy', 'trade']):
        return 'business'
    elif any(kw in question_lower for kw in ['sport', 'game', 'team', 'player', 'championship']):
        return 'sports'
    elif any(kw in question_lower for kw in ['music', 'film', 'movie', 'actor', 'singer', 'art']):
        return 'entertainment'
    elif any(kw in question_lower for kw in ['country', 'city', 'nation', 'population', 'geography']):
        return 'geography'
    else:
        return 'general'


async def run_strategy_benchmark(
    samples: list[BenchmarkSample],
    strategy: ExtractionStrategy,
    progress_callback=None,
) -> StrategyResult:
    """Run benchmark for a single strategy across all samples."""

    benchmark = ExtractionBenchmark()

    result = StrategyResult(
        strategy=strategy.value,
        samples_processed=0,
        total_time_ms=0,
        avg_time_ms=0,
        total_entities=0,
        avg_entities=0,
        total_typed_rels=0,
        avg_typed_rels=0,
        total_semantic_rels=0,
        avg_semantic_rels=0,
        total_llm_calls=0,
        avg_llm_calls=0,
        total_input_tokens=0,
        total_output_tokens=0,
    )

    for i, sample in enumerate(samples):
        try:
            logger.info(f"[{strategy.value}] Processing {i+1}/{len(samples)}: {sample.sample_id} ({sample.text_length} chars)")

            if progress_callback:
                progress_callback(strategy.value, i + 1, len(samples))

            extraction_result = await benchmark.extract(
                text=sample.context,
                chunk_id=sample.sample_id,
                document_id=f"bench_{sample.sample_id}",
                strategy=strategy,
            )

            metrics = extraction_result.metrics

            # Aggregate metrics
            result.samples_processed += 1
            result.total_time_ms += metrics.total_time_ms
            result.total_entities += metrics.entities_extracted
            result.total_typed_rels += metrics.typed_relations_extracted
            result.total_semantic_rels += metrics.semantic_relations_extracted
            result.total_llm_calls += metrics.llm_calls
            result.total_input_tokens += metrics.total_input_tokens
            result.total_output_tokens += metrics.total_output_tokens

            # Store per-sample metrics
            result.per_sample_metrics.append({
                'sample_id': sample.sample_id,
                'domain': sample.domain,
                'text_length': sample.text_length,
                'time_ms': metrics.total_time_ms,
                'entities': metrics.entities_extracted,
                'typed_rels': metrics.typed_relations_extracted,
                'semantic_rels': metrics.semantic_relations_extracted,
                'llm_calls': metrics.llm_calls,
                'input_tokens': metrics.total_input_tokens,
                'output_tokens': metrics.total_output_tokens,
            })

            if metrics.errors:
                result.errors.extend(metrics.errors)

        except Exception as e:
            logger.error(f"Error processing {sample.sample_id}: {e}")
            result.errors.append(f"{sample.sample_id}: {str(e)}")

    # Calculate averages
    if result.samples_processed > 0:
        result.avg_time_ms = result.total_time_ms / result.samples_processed
        result.avg_entities = result.total_entities / result.samples_processed
        result.avg_typed_rels = result.total_typed_rels / result.samples_processed
        result.avg_semantic_rels = result.total_semantic_rels / result.samples_processed
        result.avg_llm_calls = result.total_llm_calls / result.samples_processed

    return result


def print_comparison_report(
    sequential_result: StrategyResult,
    unified_result: StrategyResult,
    samples: list[BenchmarkSample],
):
    """Print detailed comparison report."""

    print("\n" + "=" * 80)
    print("EXTRACTION BENCHMARK COMPARISON REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Sample Summary
    print("\n📊 SAMPLES SUMMARY")
    print("-" * 40)
    print(f"Total samples: {len(samples)}")

    domains = {}
    for s in samples:
        domains[s.domain] = domains.get(s.domain, 0) + 1

    print("Domain distribution:")
    for domain, count in sorted(domains.items(), key=lambda x: -x[1]):
        print(f"  • {domain}: {count}")

    avg_text_length = sum(s.text_length for s in samples) / len(samples)
    print(f"Average text length: {avg_text_length:.0f} chars")

    # Strategy Comparison
    print("\n⚡ PERFORMANCE COMPARISON")
    print("-" * 80)

    seq = sequential_result
    uni = unified_result

    # Calculate improvements
    speedup = seq.avg_time_ms / uni.avg_time_ms if uni.avg_time_ms > 0 else 0
    call_reduction = ((seq.avg_llm_calls - uni.avg_llm_calls) / seq.avg_llm_calls * 100) if seq.avg_llm_calls > 0 else 0
    token_reduction = ((seq.total_input_tokens + seq.total_output_tokens) - (uni.total_input_tokens + uni.total_output_tokens)) / (seq.total_input_tokens + seq.total_output_tokens) * 100 if (seq.total_input_tokens + seq.total_output_tokens) > 0 else 0

    headers = f"{'Metric':<30} {'SEQUENTIAL':<18} {'UNIFIED':<18} {'Improvement':<15}"
    print(headers)
    print("-" * 80)

    # Time metrics
    print(f"{'Samples Processed':<30} {seq.samples_processed:<18} {uni.samples_processed:<18}")
    print(f"{'Total Time (s)':<30} {seq.total_time_ms/1000:<18.1f} {uni.total_time_ms/1000:<18.1f} {(seq.total_time_ms - uni.total_time_ms)/1000:.1f}s saved")
    print(f"{'Avg Time/Sample (ms)':<30} {seq.avg_time_ms:<18.1f} {uni.avg_time_ms:<18.1f} {speedup:.2f}x faster")

    # LLM calls
    print(f"{'Total LLM Calls':<30} {seq.total_llm_calls:<18} {uni.total_llm_calls:<18} {seq.total_llm_calls - uni.total_llm_calls} fewer")
    print(f"{'Avg LLM Calls/Sample':<30} {seq.avg_llm_calls:<18.1f} {uni.avg_llm_calls:<18.1f} {call_reduction:.0f}% reduction")

    # Quality metrics
    print(f"\n{'--- QUALITY METRICS ---':<30}")
    print(f"{'Total Entities':<30} {seq.total_entities:<18} {uni.total_entities:<18}")
    print(f"{'Avg Entities/Sample':<30} {seq.avg_entities:<18.1f} {uni.avg_entities:<18.1f}")
    print(f"{'Total Typed Relations':<30} {seq.total_typed_rels:<18} {uni.total_typed_rels:<18}")
    print(f"{'Avg Typed Rels/Sample':<30} {seq.avg_typed_rels:<18.1f} {uni.avg_typed_rels:<18.1f}")
    print(f"{'Total Semantic Relations':<30} {seq.total_semantic_rels:<18} {uni.total_semantic_rels:<18}")
    print(f"{'Avg Semantic Rels/Sample':<30} {seq.avg_semantic_rels:<18.1f} {uni.avg_semantic_rels:<18.1f}")

    # Token usage
    print(f"\n{'--- TOKEN USAGE ---':<30}")
    print(f"{'Total Input Tokens':<30} {seq.total_input_tokens:<18} {uni.total_input_tokens:<18}")
    print(f"{'Total Output Tokens':<30} {seq.total_output_tokens:<18} {uni.total_output_tokens:<18}")
    seq_total = seq.total_input_tokens + seq.total_output_tokens
    uni_total = uni.total_input_tokens + uni.total_output_tokens
    print(f"{'Total Tokens':<30} {seq_total:<18} {uni_total:<18} {token_reduction:.1f}% reduction")

    # Errors
    if seq.errors or uni.errors:
        print(f"\n{'--- ERRORS ---':<30}")
        if seq.errors:
            print(f"SEQUENTIAL errors: {len(seq.errors)}")
        if uni.errors:
            print(f"UNIFIED errors: {len(uni.errors)}")

    # Key Findings
    print("\n" + "=" * 80)
    print("📈 KEY FINDINGS")
    print("=" * 80)

    print(f"\n✅ UNIFIED is {speedup:.2f}x faster ({seq.avg_time_ms:.0f}ms → {uni.avg_time_ms:.0f}ms)")
    print(f"✅ {call_reduction:.0f}% fewer LLM calls ({seq.avg_llm_calls:.1f} → {uni.avg_llm_calls:.1f})")
    print(f"✅ {token_reduction:.1f}% token reduction")

    entity_ratio = uni.avg_entities / seq.avg_entities if seq.avg_entities > 0 else 1.0
    rel_ratio = (uni.avg_typed_rels + uni.avg_semantic_rels) / (seq.avg_typed_rels + seq.avg_semantic_rels) if (seq.avg_typed_rels + seq.avg_semantic_rels) > 0 else 1.0

    if entity_ratio >= 0.9:
        print(f"✅ Entity quality maintained ({entity_ratio:.0%} of SEQUENTIAL)")
    else:
        print(f"⚠️ Entity extraction reduced ({entity_ratio:.0%} of SEQUENTIAL)")

    if rel_ratio >= 0.9:
        print(f"✅ Relationship quality maintained ({rel_ratio:.0%} of SEQUENTIAL)")
    else:
        print(f"⚠️ Relationship extraction reduced ({rel_ratio:.0%} of SEQUENTIAL)")

    # Recommendation
    print("\n" + "-" * 80)
    print("📋 RECOMMENDATION")
    print("-" * 80)

    if speedup >= 1.3 and entity_ratio >= 0.85 and rel_ratio >= 0.85:
        print("✅ UNIFIED recommended for production use:")
        print(f"   • Significant speedup ({speedup:.1f}x) with acceptable quality trade-off")
        print(f"   • Lower LLM costs ({call_reduction:.0f}% fewer calls)")
        print("   • Better throughput for bulk ingestion")
    elif speedup >= 1.1:
        print("⚠️ UNIFIED provides marginal improvement:")
        print(f"   • Moderate speedup ({speedup:.1f}x)")
        print("   • Consider quality requirements before switching")
    else:
        print("❌ SEQUENTIAL recommended:")
        print(f"   • Minimal speedup ({speedup:.1f}x)")
        print("   • Better extraction quality")


def save_results_json(
    sequential_result: StrategyResult,
    unified_result: StrategyResult,
    samples: list[BenchmarkSample],
    output_path: Path,
):
    """Save detailed results to JSON."""

    results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_samples': len(samples),
            'domains': list(set(s.domain for s in samples)),
        },
        'samples': [
            {
                'sample_id': s.sample_id,
                'domain': s.domain,
                'text_length': s.text_length,
                'question': s.question[:100],
            }
            for s in samples
        ],
        'sequential': {
            'strategy': sequential_result.strategy,
            'samples_processed': sequential_result.samples_processed,
            'total_time_ms': sequential_result.total_time_ms,
            'avg_time_ms': sequential_result.avg_time_ms,
            'total_entities': sequential_result.total_entities,
            'avg_entities': sequential_result.avg_entities,
            'total_typed_rels': sequential_result.total_typed_rels,
            'avg_typed_rels': sequential_result.avg_typed_rels,
            'total_semantic_rels': sequential_result.total_semantic_rels,
            'avg_semantic_rels': sequential_result.avg_semantic_rels,
            'total_llm_calls': sequential_result.total_llm_calls,
            'avg_llm_calls': sequential_result.avg_llm_calls,
            'total_input_tokens': sequential_result.total_input_tokens,
            'total_output_tokens': sequential_result.total_output_tokens,
            'errors': sequential_result.errors,
            'per_sample': sequential_result.per_sample_metrics,
        },
        'unified': {
            'strategy': unified_result.strategy,
            'samples_processed': unified_result.samples_processed,
            'total_time_ms': unified_result.total_time_ms,
            'avg_time_ms': unified_result.avg_time_ms,
            'total_entities': unified_result.total_entities,
            'avg_entities': unified_result.avg_entities,
            'total_typed_rels': unified_result.total_typed_rels,
            'avg_typed_rels': unified_result.avg_typed_rels,
            'total_semantic_rels': unified_result.total_semantic_rels,
            'avg_semantic_rels': unified_result.avg_semantic_rels,
            'total_llm_calls': unified_result.total_llm_calls,
            'avg_llm_calls': unified_result.avg_llm_calls,
            'total_input_tokens': unified_result.total_input_tokens,
            'total_output_tokens': unified_result.total_output_tokens,
            'errors': unified_result.errors,
            'per_sample': unified_result.per_sample_metrics,
        },
        'comparison': {
            'speedup': sequential_result.avg_time_ms / unified_result.avg_time_ms if unified_result.avg_time_ms > 0 else 0,
            'call_reduction_pct': ((sequential_result.avg_llm_calls - unified_result.avg_llm_calls) / sequential_result.avg_llm_calls * 100) if sequential_result.avg_llm_calls > 0 else 0,
            'entity_ratio': unified_result.avg_entities / sequential_result.avg_entities if sequential_result.avg_entities > 0 else 1.0,
            'relation_ratio': (unified_result.avg_typed_rels + unified_result.avg_semantic_rels) / (sequential_result.avg_typed_rels + sequential_result.avg_semantic_rels) if (sequential_result.avg_typed_rels + sequential_result.avg_semantic_rels) > 0 else 1.0,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved to {output_path}")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Extended extraction benchmark")
    parser.add_argument("--samples", type=int, default=30, help="Number of samples to benchmark")
    parser.add_argument("--strategy", type=str, default=None, help="Single strategy to test (sequential/unified)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("EXTRACTION BENCHMARK: SEQUENTIAL vs UNIFIED")
    print(f"Samples: {args.samples}")
    print("=" * 80)

    # Load samples
    print("\n📥 Loading samples from WikiQA dataset...")
    samples = load_wikiqa_samples(args.samples)

    if not samples:
        logger.error("No samples loaded!")
        return

    print(f"✅ Loaded {len(samples)} samples")

    # Progress tracking
    start_time = time.time()

    def progress(strategy, current, total):
        elapsed = time.time() - start_time
        print(f"  [{strategy}] {current}/{total} - Elapsed: {elapsed:.0f}s")

    if args.strategy:
        # Single strategy test
        strategy = ExtractionStrategy(args.strategy)
        print(f"\n🔬 Running {strategy.value.upper()} benchmark...")
        result = await run_strategy_benchmark(samples, strategy, progress)
        print(f"\n✅ {strategy.value.upper()} complete: {result.avg_time_ms:.0f}ms avg, {result.avg_entities:.1f} entities avg")

    else:
        # Full comparison
        print("\n🔬 Running SEQUENTIAL benchmark...")
        sequential_result = await run_strategy_benchmark(
            samples,
            ExtractionStrategy.SEQUENTIAL,
            progress,
        )

        print("\n🔬 Running UNIFIED benchmark...")
        unified_result = await run_strategy_benchmark(
            samples,
            ExtractionStrategy.UNIFIED,
            progress,
        )

        # Print comparison report
        print_comparison_report(sequential_result, unified_result, samples)

        # Save results
        output_path = Path(args.output) if args.output else Path(f"reports/extraction_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        save_results_json(sequential_result, unified_result, samples, output_path)

    total_time = time.time() - start_time
    print(f"\n⏱️ Total benchmark time: {total_time:.1f}s ({total_time/60:.1f}min)")


if __name__ == "__main__":
    asyncio.run(main())
