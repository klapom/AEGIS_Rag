#!/usr/bin/env python3
"""Benchmark UNIFIED extraction with proper chunking.

Sprint 42: Re-test UNIFIED strategy with production-sized chunks (800-1800 tokens).

The previous benchmark used raw WikiQA texts (7000-8000 chars) which caused over-extraction.
This script chunks the texts first using the LangGraph chunking parameters.

Usage:
    poetry run python scripts/benchmark_unified_chunked.py
    poetry run python scripts/benchmark_unified_chunked.py --samples 10
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


# Chunking parameters from ADR-039
MIN_CHUNK_TOKENS = 800
MAX_CHUNK_TOKENS = 1800
CHARS_PER_TOKEN = 4  # Approximate for English text


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count."""
    return len(text) // CHARS_PER_TOKEN


def chunk_text(text: str, min_tokens: int = MIN_CHUNK_TOKENS, max_tokens: int = MAX_CHUNK_TOKENS) -> list[str]:
    """Chunk text into production-sized pieces (800-1800 tokens).

    Uses paragraph boundaries when possible.
    """
    min_chars = min_tokens * CHARS_PER_TOKEN
    max_chars = max_tokens * CHARS_PER_TOKEN

    # Split by double newlines (paragraphs)
    paragraphs = text.split("\n\n")

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If adding this paragraph exceeds max, start new chunk
        if len(current_chunk) + len(para) > max_chars and current_chunk:
            if len(current_chunk) >= min_chars:
                chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                # Current chunk is too small, force add
                current_chunk += "\n\n" + para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # If we have chunks that are still too large, split them further
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > max_chars:
            # Split by single newlines or sentences
            words = chunk.split()
            sub_chunk = ""
            for word in words:
                if len(sub_chunk) + len(word) + 1 > max_chars and sub_chunk:
                    if len(sub_chunk) >= min_chars:
                        final_chunks.append(sub_chunk.strip())
                        sub_chunk = word
                    else:
                        sub_chunk += " " + word
                else:
                    sub_chunk = sub_chunk + " " + word if sub_chunk else word
            if sub_chunk.strip():
                final_chunks.append(sub_chunk.strip())
        else:
            final_chunks.append(chunk)

    return final_chunks


@dataclass
class ChunkedSample:
    """A sample with chunked text."""
    sample_id: str
    question: str
    original_text: str
    chunks: list[str]
    original_chars: int
    total_chunks: int


@dataclass
class ChunkedBenchmarkResult:
    """Results from chunked benchmark."""
    strategy: str
    samples_processed: int
    total_chunks_processed: int
    total_time_ms: float
    avg_time_per_chunk_ms: float
    total_entities: int
    avg_entities_per_chunk: float
    total_relationships: int
    avg_relationships_per_chunk: float
    per_sample_results: list[dict] = field(default_factory=list)


def load_wikiqa_samples(num_samples: int = 10) -> list[ChunkedSample]:
    """Load and chunk WikiQA samples."""
    try:
        from datasets import load_dataset
        ds = load_dataset('explodinggradients/ragas-wikiqa', split='train')

        samples = []
        step = max(1, len(ds) // num_samples)

        for i in range(0, min(len(ds), num_samples * step), step):
            if len(samples) >= num_samples:
                break

            item = ds[i]
            contexts = item.get('context', [])
            if isinstance(contexts, list):
                context_text = "\n\n".join(contexts)
            else:
                context_text = str(contexts)

            # Chunk the text
            chunks = chunk_text(context_text)

            samples.append(ChunkedSample(
                sample_id=item.get('question_id', f'Q{i}'),
                question=item.get('question', ''),
                original_text=context_text,
                chunks=chunks,
                original_chars=len(context_text),
                total_chunks=len(chunks),
            ))

        return samples

    except Exception as e:
        logger.error(f"Failed to load WikiQA dataset: {e}")
        return []


async def run_chunked_benchmark(
    samples: list[ChunkedSample],
    strategy: ExtractionStrategy = ExtractionStrategy.UNIFIED,
) -> ChunkedBenchmarkResult:
    """Run benchmark on chunked samples."""

    # Use higher max_tokens since we discovered that was the issue
    benchmark = ExtractionBenchmark(max_tokens=8192)

    result = ChunkedBenchmarkResult(
        strategy=strategy.value,
        samples_processed=0,
        total_chunks_processed=0,
        total_time_ms=0,
        avg_time_per_chunk_ms=0,
        total_entities=0,
        avg_entities_per_chunk=0,
        total_relationships=0,
        avg_relationships_per_chunk=0,
    )

    for sample_idx, sample in enumerate(samples):
        print(f"\n{'='*60}")
        print(f"Sample {sample_idx + 1}/{len(samples)}: {sample.sample_id}")
        print(f"Original: {sample.original_chars} chars → {sample.total_chunks} chunks")
        print(f"Question: {sample.question[:80]}...")
        print(f"{'='*60}")

        sample_entities = 0
        sample_relationships = 0
        sample_time_ms = 0
        chunk_results = []

        for chunk_idx, chunk_text in enumerate(sample.chunks):
            chunk_tokens = estimate_tokens(chunk_text)
            print(f"\n  Chunk {chunk_idx + 1}/{sample.total_chunks}: {len(chunk_text)} chars (~{chunk_tokens} tokens)")

            try:
                extraction_result = await benchmark.extract(
                    text=chunk_text,
                    chunk_id=f"{sample.sample_id}_chunk_{chunk_idx}",
                    document_id=f"bench_{sample.sample_id}",
                    strategy=strategy,
                )

                metrics = extraction_result.metrics
                chunk_entities = metrics.entities_extracted
                chunk_rels = metrics.typed_relations_extracted

                sample_entities += chunk_entities
                sample_relationships += chunk_rels
                sample_time_ms += metrics.total_time_ms
                result.total_chunks_processed += 1

                print(f"    → Entities: {chunk_entities}, Rels: {chunk_rels}, Time: {metrics.total_time_ms:.0f}ms")

                # Show first few extracted entities for quality check
                if extraction_result.entities[:3]:
                    print(f"    → Sample entities: {[e.name for e in extraction_result.entities[:3]]}")

                chunk_results.append({
                    'chunk_idx': chunk_idx,
                    'chars': len(chunk_text),
                    'tokens': chunk_tokens,
                    'entities': chunk_entities,
                    'relationships': chunk_rels,
                    'time_ms': metrics.total_time_ms,
                })

            except Exception as e:
                print(f"    → ERROR: {e}")
                chunk_results.append({
                    'chunk_idx': chunk_idx,
                    'error': str(e),
                })

        # Aggregate sample results
        result.samples_processed += 1
        result.total_entities += sample_entities
        result.total_relationships += sample_relationships
        result.total_time_ms += sample_time_ms

        result.per_sample_results.append({
            'sample_id': sample.sample_id,
            'original_chars': sample.original_chars,
            'num_chunks': sample.total_chunks,
            'total_entities': sample_entities,
            'total_relationships': sample_relationships,
            'total_time_ms': sample_time_ms,
            'chunks': chunk_results,
        })

        print(f"\n  Sample Total: {sample_entities} entities, {sample_relationships} rels, {sample_time_ms:.0f}ms")

    # Calculate averages
    if result.total_chunks_processed > 0:
        result.avg_time_per_chunk_ms = result.total_time_ms / result.total_chunks_processed
        result.avg_entities_per_chunk = result.total_entities / result.total_chunks_processed
        result.avg_relationships_per_chunk = result.total_relationships / result.total_chunks_processed

    return result


def print_summary(result: ChunkedBenchmarkResult, samples: list[ChunkedSample]):
    """Print benchmark summary."""
    print("\n" + "=" * 80)
    print("CHUNKED BENCHMARK SUMMARY")
    print(f"Strategy: {result.strategy.upper()}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    print(f"\n--- OVERVIEW ---")
    print(f"Samples processed: {result.samples_processed}")
    print(f"Total chunks processed: {result.total_chunks_processed}")
    print(f"Total time: {result.total_time_ms/1000:.1f}s ({result.total_time_ms/60000:.1f}min)")

    print(f"\n--- PERFORMANCE ---")
    print(f"Avg time per chunk: {result.avg_time_per_chunk_ms:.0f}ms")
    print(f"Avg entities per chunk: {result.avg_entities_per_chunk:.1f}")
    print(f"Avg relationships per chunk: {result.avg_relationships_per_chunk:.1f}")

    print(f"\n--- TOTALS ---")
    print(f"Total entities extracted: {result.total_entities}")
    print(f"Total relationships extracted: {result.total_relationships}")

    # Compare with raw (unchunked) baseline from previous benchmark
    print(f"\n--- COMPARISON WITH RAW BENCHMARK ---")
    print(f"Previous RAW UNIFIED (7000-8000 chars per sample):")
    print(f"  Avg time: 881,200ms (~881s)")
    print(f"  Avg entities: 74.6 per sample")
    print(f"")
    print(f"Current CHUNKED UNIFIED (800-1800 tokens per chunk):")
    print(f"  Avg time per chunk: {result.avg_time_per_chunk_ms:.0f}ms")
    print(f"  Avg entities per chunk: {result.avg_entities_per_chunk:.1f}")

    # Per-sample breakdown
    print(f"\n--- PER-SAMPLE BREAKDOWN ---")
    for sample_result in result.per_sample_results:
        print(f"\n{sample_result['sample_id']}:")
        print(f"  Original: {sample_result['original_chars']} chars → {sample_result['num_chunks']} chunks")
        print(f"  Entities: {sample_result['total_entities']}, Rels: {sample_result['total_relationships']}")
        print(f"  Time: {sample_result['total_time_ms']:.0f}ms ({sample_result['total_time_ms']/1000:.1f}s)")


def save_results(result: ChunkedBenchmarkResult, output_path: Path):
    """Save results to JSON."""
    data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'strategy': result.strategy,
            'chunking_params': {
                'min_tokens': MIN_CHUNK_TOKENS,
                'max_tokens': MAX_CHUNK_TOKENS,
                'chars_per_token': CHARS_PER_TOKEN,
            },
        },
        'summary': {
            'samples_processed': result.samples_processed,
            'total_chunks_processed': result.total_chunks_processed,
            'total_time_ms': result.total_time_ms,
            'avg_time_per_chunk_ms': result.avg_time_per_chunk_ms,
            'total_entities': result.total_entities,
            'avg_entities_per_chunk': result.avg_entities_per_chunk,
            'total_relationships': result.total_relationships,
            'avg_relationships_per_chunk': result.avg_relationships_per_chunk,
        },
        'per_sample': result.per_sample_results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved to: {output_path}")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Chunked UNIFIED benchmark")
    parser.add_argument("--samples", type=int, default=10, help="Number of samples")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("CHUNKED UNIFIED EXTRACTION BENCHMARK")
    print(f"Samples: {args.samples}")
    print(f"Chunking: {MIN_CHUNK_TOKENS}-{MAX_CHUNK_TOKENS} tokens")
    print("=" * 80)

    # Load and chunk samples
    print("\nLoading and chunking samples...")
    samples = load_wikiqa_samples(args.samples)

    if not samples:
        print("Failed to load samples!")
        return

    total_chunks = sum(s.total_chunks for s in samples)
    print(f"Loaded {len(samples)} samples → {total_chunks} total chunks")

    # Show chunking distribution
    print("\nChunk distribution:")
    for s in samples:
        chunk_sizes = [len(c) for c in s.chunks]
        print(f"  {s.sample_id}: {s.original_chars} chars → {s.total_chunks} chunks "
              f"(avg {sum(chunk_sizes)//len(chunk_sizes)} chars/chunk)")

    # Run benchmark
    start_time = time.time()
    result = await run_chunked_benchmark(samples, ExtractionStrategy.UNIFIED)
    total_time = time.time() - start_time

    # Print summary
    print_summary(result, samples)

    # Save results
    output_path = Path(args.output) if args.output else Path(
        f"reports/chunked_unified_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    save_results(result, output_path)

    print(f"\nTotal benchmark time: {total_time:.1f}s ({total_time/60:.1f}min)")


if __name__ == "__main__":
    asyncio.run(main())
