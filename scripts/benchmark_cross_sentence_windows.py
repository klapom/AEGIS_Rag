#!/usr/bin/env python3
"""Benchmark cross-sentence window sizes for relation extraction.

Sprint 128: Systematic benchmark of window_size and overlap parameters.
Measures dedup rate, extraction duration, entity/relation counts, and quality.

Usage (run inside API container):
    docker exec aegis-api python /app/scripts/benchmark_cross_sentence_windows.py

Or from host:
    docker exec aegis-api python /app/scripts/benchmark_cross_sentence_windows.py
"""

import asyncio
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

# Force vLLM-only mode and 2 workers
os.environ["AEGIS_EXTRACTION_WORKERS"] = "2"
os.environ["AEGIS_USE_CROSS_SENTENCE"] = "1"

# Add project root to path
sys.path.insert(0, "/app")


async def run_benchmark():
    """Run cross-sentence window benchmark with varying parameters."""
    from src.components.graph_rag.cross_sentence_extractor import (
        get_cross_sentence_extractor,
    )
    from src.components.graph_rag.extraction_service import ExtractionService
    from src.core.config import settings

    # Load test file
    test_file = Path("/app/data/ragas_phase1_contexts/ragas_phase1_0050_ragbench_5041.txt")
    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return

    text = test_file.read_text()
    print(f"=== Cross-Sentence Window Benchmark ===")
    print(f"File: {test_file.name} ({len(text)} bytes)")
    print(f"Engine mode: vLLM only (2 workers)")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Count sentences first
    import re

    sentence_count = len(re.split(r"[.!?]+\s", text))
    print(f"Approximate sentence count: {sentence_count}")
    print()

    # Window configurations to test
    configs = [
        # (window_size, overlap)
        (2, 1),
        (4, 1),
        (6, 1),
        (8, 1),
        (10, 2),
        (12, 2),
        (16, 2),
        (20, 2),
    ]

    # First, extract entities (same for all configs — entities don't use windowing)
    print("--- Phase 1: Entity Extraction (shared across all configs) ---")
    service = ExtractionService(
        llm_model=settings.extraction_llm_model,
        temperature=0.1,
        max_tokens=4096,
    )

    t0 = time.time()
    entities = await service.extract_entities(text=text, document_id="bench_doc")
    entity_time = time.time() - t0
    print(f"Entities: {len(entities)} extracted in {entity_time:.1f}s")
    print()

    # Analyze entity types
    entity_types = Counter()
    for e in entities:
        etype = getattr(e, "type", None) or getattr(e, "entity_type", "UNKNOWN")
        entity_types[etype] += 1
    print(f"Entity types: {dict(entity_types)}")
    print()

    # Now benchmark each window config for relation extraction
    print("--- Phase 2: Relation Extraction (per window config) ---")
    print()

    results = []

    for window_size, overlap in configs:
        print(f"{'=' * 60}")
        print(f"Window Size: {window_size}, Overlap: {overlap}")
        print(f"{'=' * 60}")

        # Clear prompt cache between runs for fair comparison
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url("redis://redis:6379/0", decode_responses=True)
            keys = await r.keys("prompt_cache:*")
            if keys:
                await r.delete(*keys)
                print(f"  Cleared {len(keys)} cached prompts")
            await r.close()
        except Exception as e:
            print(f"  Warning: Could not clear cache: {e}")

        # Generate windows for this config
        extractor = get_cross_sentence_extractor(
            lang="en",
            window_size=window_size,
            overlap=overlap,
        )
        windows = list(extractor.create_windows(text))
        window_texts = [w.text for w in windows]
        print(f"  Windows generated: {len(windows)}")
        if windows:
            avg_len = sum(len(w.text) for w in windows) / len(windows)
            print(f"  Avg window length: {avg_len:.0f} chars")

        # Override settings for this run
        settings.cross_sentence_window_size = window_size
        settings.cross_sentence_overlap = overlap

        # Extract relations
        t0 = time.time()
        try:
            relations = await service._extract_relationships_windowed(
                text=text,
                entities=entities,
                document_id="bench_doc",
                domain=None,
            )
            duration = time.time() - t0
        except Exception as e:
            print(f"  ERROR: {repr(e)}")
            results.append(
                {
                    "window_size": window_size,
                    "overlap": overlap,
                    "windows": len(windows),
                    "error": str(e),
                }
            )
            continue

        # Count raw vs deduplicated relations
        # Dedup is done inside _extract_relationships_windowed via triple matching
        raw_count = len(relations)

        # Analyze relation types
        rel_types = Counter()
        specific_count = 0
        generic_count = 0
        for rel in relations:
            rtype = getattr(rel, "type", None) or getattr(rel, "relation_type", "RELATES_TO")
            rel_types[rtype] += 1
            if rtype in ("RELATES_TO", "RELATED_TO", "UNKNOWN"):
                generic_count += 1
            else:
                specific_count += 1

        # Quality metrics
        specificity_rate = specific_count / max(raw_count, 1) * 100

        result = {
            "window_size": window_size,
            "overlap": overlap,
            "windows": len(windows),
            "avg_window_chars": int(avg_len) if windows else 0,
            "duration_s": round(duration, 1),
            "relations_total": raw_count,
            "relations_specific": specific_count,
            "relations_generic": generic_count,
            "specificity_pct": round(specificity_rate, 1),
            "top_relation_types": dict(rel_types.most_common(10)),
            "relations_per_second": round(raw_count / max(duration, 0.1), 2),
        }
        results.append(result)

        print(f"  Duration: {duration:.1f}s")
        print(
            f"  Relations: {raw_count} total ({specific_count} specific, {generic_count} generic)"
        )
        print(f"  Specificity: {specificity_rate:.1f}%")
        print(f"  Top types: {dict(rel_types.most_common(5))}")
        print(f"  Relations/sec: {result['relations_per_second']}")
        print()

    # Summary table
    print()
    print("=" * 100)
    print("SUMMARY TABLE")
    print("=" * 100)
    print(
        f"{'WinSize':>7} {'Overlap':>7} {'Windows':>7} {'Duration':>8} {'Relations':>9} "
        f"{'Specific':>8} {'Generic':>7} {'Spec%':>6} {'Rel/s':>6}"
    )
    print("-" * 100)

    for r in results:
        if "error" in r:
            print(f"{r['window_size']:>7} {r['overlap']:>7} {r['windows']:>7} {'ERROR':>8}")
            continue
        print(
            f"{r['window_size']:>7} {r['overlap']:>7} {r['windows']:>7} "
            f"{r['duration_s']:>7.1f}s {r['relations_total']:>9} "
            f"{r['relations_specific']:>8} {r['relations_generic']:>7} "
            f"{r['specificity_pct']:>5.1f}% {r['relations_per_second']:>6.2f}"
        )

    print("-" * 100)

    # Entity summary
    print(f"\nEntities: {len(entities)} ({entity_time:.1f}s)")
    print(f"Entity types: {dict(entity_types)}")

    # Save results to JSON
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "file": str(test_file.name),
        "file_size_bytes": len(text),
        "sentence_count": sentence_count,
        "engine": "vllm",
        "workers": 2,
        "entity_count": len(entities),
        "entity_types": dict(entity_types),
        "entity_extraction_time_s": round(entity_time, 1),
        "window_benchmarks": results,
    }

    output_path = Path("/app/data/evaluation/results/cross_sentence_benchmark.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
