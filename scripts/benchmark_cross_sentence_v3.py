#!/usr/bin/env python3
"""Cross-sentence window benchmark v3 — doubled timeout (600s per rank).

Re-run configs (10,2), (10,3), (12,2), (12,3) with 600s timeout instead of 300s.
Tracks relations BEFORE and AFTER dedup, saves raw relations for BGE-M3 mapping.

Usage (run inside API container):
    docker exec aegis-api python /app/scripts/benchmark_cross_sentence_v3.py
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
    """Run cross-sentence window benchmark v3 with doubled timeout."""
    from src.components.graph_rag.extraction_service import ExtractionService
    from src.components.graph_rag.cross_sentence_extractor import (
        get_cross_sentence_extractor,
    )
    from src.config.extraction_cascade import CascadeRankConfig, ExtractionMethod
    from src.core.config import settings

    # Load test file
    test_file = Path("/app/data/ragas_phase1_contexts/ragas_phase1_0050_ragbench_5041.txt")
    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return

    text = test_file.read_text()
    print(f"=== Cross-Sentence Window Benchmark v3 (Doubled Timeout) ===")
    print(f"File: {test_file.name} ({len(text)} bytes)")
    print(f"Engine mode: vLLM only (2 workers)")
    print(f"max_tokens: 8192 (ExtractionService) → vLLM gets min(8192*2, 32768) = 16384")
    print(f"Cascade timeout: 600s (doubled from 300s)")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Count sentences
    import re

    sentence_count = len(re.split(r"[.!?]+\s", text))
    print(f"Approximate sentence count: {sentence_count}")
    print()

    # Only 4 configs this time
    configs = [
        (10, 2),
        (10, 3),
        (12, 2),
        (12, 3),
    ]

    # Phase 1: Entity Extraction (shared across all configs)
    print("--- Phase 1: Entity Extraction (shared across all configs) ---")

    service = ExtractionService(
        llm_model=settings.extraction_llm_model,
        temperature=0.1,
        max_tokens=8192,
    )

    t0 = time.time()
    entities = await service.extract_entities(text=text, document_id="bench_v3_doc")
    entity_time = time.time() - t0
    print(f"Entities: {len(entities)} extracted in {entity_time:.1f}s")

    entity_types = Counter()
    for e in entities:
        etype = getattr(e, "type", None) or getattr(e, "entity_type", "UNKNOWN")
        entity_types[etype] += 1
    print(f"Entity types: {dict(entity_types)}")
    print()

    # Create a custom CascadeRankConfig with 600s timeout
    rank_config_600s = CascadeRankConfig(
        rank=1,
        model=settings.extraction_llm_model,
        method=ExtractionMethod.LLM_ONLY,
        entity_timeout_s=600,
        relation_timeout_s=600,
        max_retries=3,
        retry_backoff_multiplier=1,
    )

    # Phase 2: Relation Extraction per window config
    print("--- Phase 2: Relation Extraction (per window config) ---")
    print(f"--- Timeout: 600s per rank (doubled from 300s) ---")
    print(f"--- max_tokens: 8192 → vLLM gets 16384 ---")
    print()

    results = []
    all_raw_relations = {}

    from src.components.graph_rag.extraction_service import EXTRACTION_WORKERS

    workers = max(1, EXTRACTION_WORKERS)
    semaphore = asyncio.Semaphore(workers)

    for window_size, overlap in configs:
        config_key = f"w{window_size}_o{overlap}"  # noqa: B023
        print(f"{'=' * 70}")
        print(f"Config: window_size={window_size}, overlap={overlap} [{config_key}]")
        print(f"{'=' * 70}")

        # Clear prompt cache between runs
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

        # Generate windows
        extractor = get_cross_sentence_extractor(
            lang="en",
            window_size=window_size,
            overlap=overlap,
        )
        windows = list(extractor.create_windows(text))
        window_texts = [w.text for w in windows]
        print(f"  Windows generated: {len(windows)}")
        avg_len = sum(len(w.text) for w in windows) / len(windows) if windows else 0
        print(f"  Avg window length: {avg_len:.0f} chars")

        # Override settings for this run
        settings.cross_sentence_window_size = window_size
        settings.cross_sentence_overlap = overlap

        raw_per_window = []
        all_raw = []
        deduped = []
        seen_triples = set()

        t0 = time.time()

        async def _extract_one_window(idx, win_text):
            async with semaphore:
                try:
                    window_rels = await service._extract_relationships_with_rank(
                        text=win_text,
                        entities=entities,
                        rank_config=rank_config_600s,  # 600s timeout!  # noqa: B023
                        document_id=f"bench_v3_{config_key}_window_{idx}",  # noqa: B023
                        domain=None,
                    )
                    return idx, win_text, window_rels
                except Exception as e:
                    print(f"    Window {idx} ERROR: {repr(e)}")
                    return idx, win_text, []

        tasks = [_extract_one_window(i, wt) for i, wt in enumerate(window_texts)]
        window_results = await asyncio.gather(*tasks)

        for idx, win_text, window_rels in sorted(window_results, key=lambda x: x[0]):
            raw_rels_dicts = []
            for rel in window_rels:
                raw_dict = {
                    "source": getattr(rel, "source", ""),
                    "target": getattr(rel, "target", ""),
                    "type": getattr(rel, "type", "RELATED_TO"),
                    "description": getattr(rel, "description", ""),
                    "strength": getattr(rel, "strength", 0),
                    "source_type": getattr(rel, "source_type", ""),
                    "target_type": getattr(rel, "target_type", ""),
                    "window_index": idx,
                    "window_text_preview": win_text[:100],
                    "original_type": getattr(rel, "original_type", None),
                }
                raw_rels_dicts.append(raw_dict)
                all_raw.append(raw_dict)

            raw_per_window.append(
                {
                    "window_index": idx,
                    "window_chars": len(win_text),
                    "raw_count": len(window_rels),
                }
            )

            unique_count = 0
            for rel in window_rels:
                triple = (
                    rel.source.lower().strip(),
                    rel.target.lower().strip(),
                    rel.type.upper().strip(),
                )
                if triple not in seen_triples:
                    seen_triples.add(triple)
                    deduped.append(rel)
                    unique_count += 1

            print(
                f"    Window {idx}: {len(window_rels)} raw → {unique_count} unique (deduped {len(window_rels) - unique_count})"
            )

        duration = time.time() - t0
        total_raw = len(all_raw)
        total_deduped = len(deduped)
        dedup_rate = round((1 - total_deduped / max(total_raw, 1)) * 100, 1) if total_raw > 0 else 0

        rel_types_raw = Counter()
        rel_types_deduped = Counter()
        for r in all_raw:
            rel_types_raw[r["type"]] += 1
        for rel in deduped:
            rtype = getattr(rel, "type", "RELATED_TO")
            rel_types_deduped[rtype] += 1

        specific_raw = sum(
            v for k, v in rel_types_raw.items() if k not in ("RELATES_TO", "RELATED_TO", "UNKNOWN")
        )
        generic_raw = sum(
            v for k, v in rel_types_raw.items() if k in ("RELATES_TO", "RELATED_TO", "UNKNOWN")
        )
        specific_deduped = sum(
            v
            for k, v in rel_types_deduped.items()
            if k not in ("RELATES_TO", "RELATED_TO", "UNKNOWN")
        )
        generic_deduped = sum(
            v for k, v in rel_types_deduped.items() if k in ("RELATES_TO", "RELATED_TO", "UNKNOWN")
        )

        result = {
            "config_key": config_key,
            "window_size": window_size,
            "overlap": overlap,
            "windows": len(windows),
            "avg_window_chars": int(avg_len),
            "duration_s": round(duration, 1),
            "timeout_s": 600,
            "raw_total": total_raw,
            "raw_specific": specific_raw,
            "raw_generic": generic_raw,
            "raw_specificity_pct": round(specific_raw / max(total_raw, 1) * 100, 1),
            "deduped_total": total_deduped,
            "deduped_specific": specific_deduped,
            "deduped_generic": generic_deduped,
            "deduped_specificity_pct": round(specific_deduped / max(total_deduped, 1) * 100, 1),
            "dedup_removed": total_raw - total_deduped,
            "dedup_rate_pct": dedup_rate,
            "raw_type_distribution": dict(rel_types_raw.most_common(15)),
            "deduped_type_distribution": dict(rel_types_deduped.most_common(15)),
            "per_window": raw_per_window,
            "relations_per_second": round(total_deduped / max(duration, 0.1), 2),
        }
        results.append(result)
        all_raw_relations[config_key] = all_raw

        print(f"\n  Duration: {duration:.1f}s")
        print(
            f"  RAW:    {total_raw} total ({specific_raw} specific, {generic_raw} generic) — {result['raw_specificity_pct']}% specific"
        )
        print(
            f"  DEDUP:  {total_deduped} total ({specific_deduped} specific, {generic_deduped} generic) — {result['deduped_specificity_pct']}% specific"
        )
        print(f"  Dedup removed: {total_raw - total_deduped} ({dedup_rate}%)")
        print(f"  Raw types:   {dict(rel_types_raw.most_common(8))}")
        print(f"  Dedup types: {dict(rel_types_deduped.most_common(8))}")
        print()

    # Summary table
    print()
    print("=" * 120)
    print("SUMMARY TABLE (v3 — 600s timeout)")
    print("=" * 120)
    print(
        f"{'Config':>10} {'Windows':>7} {'Duration':>8} "
        f"{'Raw':>5} {'RawSpec':>7} {'RawGen':>6} {'RawSpec%':>8} "
        f"{'Dedup':>5} {'DedSpec':>7} {'DedGen':>6} {'DedSpec%':>8} "
        f"{'Removed':>7} {'Dedup%':>6}"
    )
    print("-" * 120)

    for r in results:
        print(
            f"{r['config_key']:>10} {r['windows']:>7} {r['duration_s']:>7.1f}s "
            f"{r['raw_total']:>5} {r['raw_specific']:>7} {r['raw_generic']:>6} {r['raw_specificity_pct']:>7.1f}% "
            f"{r['deduped_total']:>5} {r['deduped_specific']:>7} {r['deduped_generic']:>6} {r['deduped_specificity_pct']:>7.1f}% "
            f"{r['dedup_removed']:>7} {r['dedup_rate_pct']:>5.1f}%"
        )
    print("-" * 120)
    print(f"\nEntities: {len(entities)} ({entity_time:.1f}s)")
    print(f"Entity types: {dict(entity_types)}")

    # Save structured results
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "file": str(test_file.name),
        "file_size_bytes": len(text),
        "sentence_count": sentence_count,
        "engine": "vllm",
        "workers": 2,
        "max_tokens_extraction_service": 8192,
        "max_tokens_vllm_effective": 16384,
        "cascade_timeout_s": 600,
        "entity_count": len(entities),
        "entity_types": dict(entity_types),
        "entity_extraction_time_s": round(entity_time, 1),
        "window_benchmarks": results,
    }

    output_dir = Path("/app/data/evaluation/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "cross_sentence_benchmark_v3.json"
    summary_path.write_text(json.dumps(output, indent=2))
    print(f"\nBenchmark results saved to: {summary_path}")

    raw_path = output_dir / "cross_sentence_raw_relations_v3.json"
    raw_path.write_text(json.dumps(all_raw_relations, indent=2, default=str))
    print(
        f"Raw relations saved to: {raw_path} ({sum(len(v) for v in all_raw_relations.values())} total relations)"
    )


if __name__ == "__main__":
    asyncio.run(run_benchmark())
