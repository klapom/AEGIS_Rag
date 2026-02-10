#!/usr/bin/env python3
"""Cross-sentence window benchmark v5 — Multi-document, multi-run determinism test.

4 documents (S/M/L/XL) × 4 configs × 3 runs = 48 total extractions.

Questions answered:
  1. Is extraction deterministic? (3 identical runs on same doc/config)
  2. What's the optimal window config across document sizes?

No monkey-patches — production code paths only.
Engine: vLLM only, 2 workers, 900s cascade timeout.

Usage (run inside API container):
    docker exec aegis-api python -u /app/scripts/benchmark_cross_sentence_v5.py
"""

import asyncio
import json
import math
import os
import re
import subprocess  # noqa: S404
import sys
import time
from collections import Counter
from pathlib import Path

# Force vLLM-only mode and 2 workers
os.environ["AEGIS_EXTRACTION_WORKERS"] = "2"
os.environ["AEGIS_USE_CROSS_SENTENCE"] = "1"

sys.path.insert(0, "/app")

# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

DOCUMENTS = {
    "S": "ragas_phase1_0398_ragbench_1384.txt",  # ~2.0KB (fresh)
    "M": "ragas_phase1_0386_ragbench_1062.txt",  # ~4.0KB (fresh)
    "L": "ragas_phase1_3490_hotpot_5adddd57.txt",  # ~5.6KB (fresh)
    "XL": "ragas_phase1_0267_ragbench_techqaTR.txt",  # ~10.7KB (fresh)
}

DATA_DIR = Path("/app/data/ragas_phase1_contexts")

# ---------------------------------------------------------------------------
# Window configs: (window_size, overlap)
# ---------------------------------------------------------------------------

CONFIGS = [
    (12, 2),  # w12_o2
    (12, 3),  # w12_o3
    (14, 2),  # w14_o2
    (14, 3),  # w14_o3 — v4 winner
]

RUNS_PER_CONFIG = 3
CASCADE_TIMEOUT_S = 900

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def config_key(window_size: int, overlap: int) -> str:
    return f"w{window_size}_o{overlap}"


def get_gpu_stats() -> dict:
    """Query nvidia-smi for GPU stats."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=5,
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        return {
            "gpu_util_pct": float(parts[0]),
            "gpu_mem_used_mb": float(parts[1]),
            "gpu_mem_total_mb": float(parts[2]),
            "gpu_temp_c": float(parts[3]),
        }
    except Exception as e:
        return {"error": str(e)}


async def clear_redis_cache() -> int:
    """Clear all prompt_cache keys. Returns number of keys deleted."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url("redis://redis:6379/0", decode_responses=True)
        keys = await r.keys("prompt_cache:*")
        count = 0
        if keys:
            count = await r.delete(*keys)
        await r.close()
        return count
    except Exception as e:
        print(f"  Warning: Could not clear cache: {e}")
        return 0


def compute_determinism(runs_data: list[dict]) -> dict:
    """Compute determinism metrics across 3 runs of the same (doc, config).

    Args:
        runs_data: list of run dicts, each with 'raw_total', 'deduped_total',
                   'raw_type_distribution', and 'triples' (set of normalized triples).

    Returns:
        Dict with count variance, CV, triple overlap, type stability.
    """
    raw_counts = [r["raw_total"] for r in runs_data]
    dedup_counts = [r["deduped_total"] for r in runs_data]

    def _cv(values: list[int]) -> float:
        """Coefficient of variation (std/mean × 100)."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return round(math.sqrt(variance) / mean * 100, 1)

    # Triple overlap: triples that appear in ALL runs
    triple_sets = [r["triples"] for r in runs_data]
    if triple_sets:
        intersection = triple_sets[0]
        union = triple_sets[0]
        for ts in triple_sets[1:]:
            intersection = intersection & ts
            union = union | ts
        overlap_pct = round(len(intersection) / max(len(union), 1) * 100, 1)
    else:
        intersection = set()
        union = set()
        overlap_pct = 0.0

    # Type distribution stability: do all runs produce the same top-5 types?
    top_types_per_run = []
    for r in runs_data:
        dist = r.get("raw_type_distribution", {})
        sorted_types = sorted(dist.items(), key=lambda x: -x[1])
        top_types_per_run.append([t[0] for t in sorted_types[:5]])

    if len(top_types_per_run) >= 2:
        type_stable = all(set(top_types_per_run[0]) == set(t) for t in top_types_per_run[1:])
    else:
        type_stable = True

    return {
        "raw_count_values": raw_counts,
        "raw_count_cv_pct": _cv(raw_counts),
        "dedup_count_values": dedup_counts,
        "dedup_count_cv_pct": _cv(dedup_counts),
        "triple_overlap_count": len(intersection),
        "triple_union_count": len(union),
        "triple_overlap_pct": overlap_pct,
        "type_distribution_stable": type_stable,
    }


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------


async def run_benchmark():
    from src.components.graph_rag.extraction_service import ExtractionService
    from src.components.graph_rag.cross_sentence_extractor import get_cross_sentence_extractor
    from src.config.extraction_cascade import CascadeRankConfig, ExtractionMethod
    from src.core.config import settings
    from src.components.graph_rag.extraction_service import EXTRACTION_WORKERS

    workers = max(1, EXTRACTION_WORKERS)
    semaphore = asyncio.Semaphore(workers)

    print(f"{'=' * 80}")
    print(f"  Cross-Sentence Window Benchmark v5 — Determinism Test")
    print(f"  4 documents × 4 configs × 3 runs = 48 extractions")
    print(f"{'=' * 80}")
    print(f"Engine:  vLLM only ({workers} workers)")
    print(f"Configs: {', '.join(config_key(ws, ov) for ws, ov in CONFIGS)}")
    print(f"Runs:    {RUNS_PER_CONFIG} per (document, config)")
    print(f"Cascade: {CASCADE_TIMEOUT_S}s timeout")
    print(f"max_tokens: 8192 → vLLM gets min(8192×2, 32768) = 16384")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Baseline GPU stats
    gpu = get_gpu_stats()
    print(f"GPU Baseline: {gpu}")
    print()

    # Custom rank config with 900s timeout
    rank_config = CascadeRankConfig(
        rank=1,
        model=settings.extraction_llm_model,
        method=ExtractionMethod.LLM_ONLY,
        entity_timeout_s=CASCADE_TIMEOUT_S,
        relation_timeout_s=CASCADE_TIMEOUT_S,
        max_retries=3,
        retry_backoff_multiplier=1,
    )

    # ExtractionService with 8192 max_tokens (proxy doubles to 16384)
    service = ExtractionService(
        llm_model=settings.extraction_llm_model,
        temperature=0.1,
        max_tokens=8192,
    )

    # -----------------------------------------------------------------------
    # Outer loop: documents
    # -----------------------------------------------------------------------

    all_results = {}  # size -> full result dict
    all_raw_relations = {}  # "{size}_{config}_{run}" -> list of relation dicts
    benchmark_start = time.time()
    total_extraction_count = 0

    for size_label, filename in DOCUMENTS.items():
        doc_path = DATA_DIR / filename
        if not doc_path.exists():
            print(f"ERROR: {doc_path} not found — skipping {size_label}")
            continue

        text = doc_path.read_text()
        sentence_count = len(re.split(r"[.!?]+\s", text))

        print(f"\n{'#' * 80}")
        print(f"# Document: {size_label} — {filename}")
        print(f"# Size: {len(text)} bytes, ~{sentence_count} sentences")
        print(f"{'#' * 80}")

        # Phase 1: Entity extraction (ONCE per document, shared across configs/runs)
        print(f"\n--- Entity Extraction (shared for all {size_label} configs) ---")
        t0 = time.time()
        entities = await service.extract_entities(text=text, document_id=f"bench_v5_{size_label}")  # noqa: B023
        entity_time = time.time() - t0

        entity_types = Counter()
        for e in entities:
            etype = getattr(e, "type", None) or getattr(e, "entity_type", "UNKNOWN")
            entity_types[etype] += 1

        print(f"  Entities: {len(entities)} in {entity_time:.1f}s")
        print(f"  Types: {dict(entity_types)}")

        doc_result = {
            "file": filename,
            "size_bytes": len(text),
            "sentence_count": sentence_count,
            "entity_count": len(entities),
            "entity_types": dict(entity_types),
            "entity_extraction_time_s": round(entity_time, 1),
            "configs": {},
        }

        # -------------------------------------------------------------------
        # Config loop
        # -------------------------------------------------------------------

        for window_size, overlap in CONFIGS:
            ckey = config_key(window_size, overlap)

            # Generate windows once for this config
            extractor = get_cross_sentence_extractor(
                lang="en",
                window_size=window_size,
                overlap=overlap,
            )
            windows = list(extractor.create_windows(text))
            window_texts = [w.text for w in windows]
            avg_chars = (
                sum(len(wt) for wt in window_texts) / len(window_texts) if window_texts else 0
            )

            print(f"\n  --- Config {ckey}: {len(windows)} windows (avg {avg_chars:.0f} chars) ---")

            settings.cross_sentence_window_size = window_size
            settings.cross_sentence_overlap = overlap

            runs_data = []

            # ---------------------------------------------------------------
            # Run loop (3 runs per config)
            # ---------------------------------------------------------------

            for run_num in range(1, RUNS_PER_CONFIG + 1):
                run_label = f"{size_label}_{ckey}_run{run_num}"  # noqa: B023
                print(f"\n    Run {run_num}/{RUNS_PER_CONFIG} [{run_label}]")

                # Clear Redis cache before EVERY run
                cleared = await clear_redis_cache()
                print(f"      Cache cleared: {cleared} keys")

                # Extract relations
                raw_rels_all = []
                per_window_stats = []
                seen_triples = set()
                deduped_rels = []

                t0 = time.time()

                async def _extract_window(idx: int, win_text: str):
                    async with semaphore:
                        w_start = time.time()
                        try:
                            rels = await service._extract_relationships_with_rank(
                                text=win_text,
                                entities=entities,  # noqa: B023
                                rank_config=rank_config,
                                document_id=f"bench_v5_{run_label}_w{idx}",  # noqa: B023
                                domain=None,
                            )
                            return idx, rels, time.time() - w_start, None
                        except Exception as e:  # noqa: B023
                            return idx, [], time.time() - w_start, repr(e)  # noqa: B023

                tasks = [_extract_window(i, wt) for i, wt in enumerate(window_texts)]
                window_results = await asyncio.gather(*tasks)

                run_duration = time.time() - t0

                # Process results
                for idx, rels, w_dur, w_err in sorted(window_results, key=lambda x: x[0]):
                    per_window_stats.append(
                        {
                            "window_index": idx,
                            "window_chars": len(window_texts[idx]),
                            "raw_count": len(rels),
                            "duration_s": round(w_dur, 1),
                            "error": w_err,
                        }
                    )

                    unique_in_window = 0
                    for rel in rels:
                        raw_dict = {
                            "source": getattr(rel, "source", ""),
                            "target": getattr(rel, "target", ""),
                            "type": getattr(rel, "type", "RELATED_TO"),
                            "description": getattr(rel, "description", ""),
                            "strength": getattr(rel, "strength", 0),
                            "source_type": getattr(rel, "source_type", ""),
                            "target_type": getattr(rel, "target_type", ""),
                            "window_index": idx,
                        }
                        raw_rels_all.append(raw_dict)

                        triple = (
                            rel.source.lower().strip(),
                            rel.target.lower().strip(),
                            rel.type.upper().strip(),
                        )
                        if triple not in seen_triples:
                            seen_triples.add(triple)
                            deduped_rels.append(raw_dict)
                            unique_in_window += 1

                    status = "ERR" if w_err else "OK"
                    print(
                        f"      W{idx}: {len(rels)} raw → {unique_in_window} new ({w_dur:.0f}s) [{status}]"
                    )

                total_raw = len(raw_rels_all)
                total_deduped = len(deduped_rels)

                # Type distribution
                type_dist = Counter()
                for r in raw_rels_all:
                    type_dist[r["type"]] += 1

                specific = sum(
                    v
                    for k, v in type_dist.items()
                    if k not in ("RELATES_TO", "RELATED_TO", "UNKNOWN")
                )
                generic = total_raw - specific
                spec_pct = round(specific / max(total_raw, 1) * 100, 1)
                dedup_rate = round((1 - total_deduped / max(total_raw, 1)) * 100, 1)

                print(
                    f"      Total: {total_raw} raw → {total_deduped} deduped "
                    f"({spec_pct}% specific, {dedup_rate}% dedup) in {run_duration:.0f}s"
                )

                total_extraction_count += 1

                run_result = {
                    "run": run_num,
                    "duration_s": round(run_duration, 1),
                    "raw_total": total_raw,
                    "raw_specific": specific,
                    "raw_generic": generic,
                    "raw_specificity_pct": spec_pct,
                    "deduped_total": total_deduped,
                    "deduped_specific": sum(
                        1
                        for r in deduped_rels
                        if r["type"] not in ("RELATES_TO", "RELATED_TO", "UNKNOWN")
                    ),
                    "dedup_rate_pct": dedup_rate,
                    "raw_type_distribution": dict(type_dist.most_common(15)),
                    "per_window": per_window_stats,
                    # Internal — not serialized to JSON directly
                    "triples": seen_triples,
                }
                runs_data.append(run_result)

                # Store raw relations for BGE-M3 analysis
                raw_key = f"{size_label}_{ckey}_run{run_num}"
                all_raw_relations[raw_key] = raw_rels_all

            # Compute determinism metrics for this (doc, config)
            determinism = compute_determinism(runs_data)

            print(f"\n    Determinism [{size_label}/{ckey}]:")
            print(
                f"      Raw counts: {determinism['raw_count_values']} (CV={determinism['raw_count_cv_pct']}%)"
            )
            print(
                f"      Dedup counts: {determinism['dedup_count_values']} (CV={determinism['dedup_count_cv_pct']}%)"
            )
            print(
                f"      Triple overlap: {determinism['triple_overlap_count']}/{determinism['triple_union_count']} "
                f"({determinism['triple_overlap_pct']}%)"
            )
            print(f"      Top-5 types stable: {determinism['type_distribution_stable']}")

            # Build serializable runs (remove 'triples' set)
            serializable_runs = []
            for rd in runs_data:
                rd_copy = {k: v for k, v in rd.items() if k != "triples"}
                serializable_runs.append(rd_copy)

            doc_result["configs"][ckey] = {
                "window_size": window_size,
                "overlap": overlap,
                "window_count": len(windows),
                "avg_window_chars": int(avg_chars),
                "runs": serializable_runs,
                "determinism": determinism,
            }

        all_results[size_label] = doc_result

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    total_duration = time.time() - benchmark_start

    print(f"\n\n{'=' * 100}")
    print(f"  SUMMARY — v5 Determinism Benchmark")
    print(f"{'=' * 100}")
    print(f"Total extractions: {total_extraction_count}/48")
    print(f"Total duration: {total_duration:.0f}s ({total_duration / 3600:.1f}h)")
    print()

    # Summary table
    header = (
        f"{'Size':>4} {'Config':>8} {'Win':>4} {'AvgChr':>6} | "
        f"{'R1_raw':>6} {'R2_raw':>6} {'R3_raw':>6} {'CV%':>5} | "
        f"{'R1_ded':>6} {'R2_ded':>6} {'R3_ded':>6} {'CV%':>5} | "
        f"{'Spec%':>5} {'Ov%':>5} {'TypeOK':>6} | "
        f"{'AvgDur':>6}"
    )
    print(header)
    print("-" * len(header))

    best_config = None
    best_score = -1
    most_deterministic = None
    best_cv = 999

    for size_label, doc_result in all_results.items():
        for ckey, cfg_data in doc_result.get("configs", {}).items():
            det = cfg_data.get("determinism", {})
            runs = cfg_data.get("runs", [])

            raw_vals = det.get("raw_count_values", [])
            dedup_vals = det.get("dedup_count_values", [])
            avg_spec = sum(r.get("raw_specificity_pct", 0) for r in runs) / max(len(runs), 1)
            avg_dur = sum(r.get("duration_s", 0) for r in runs) / max(len(runs), 1)

            r1r = raw_vals[0] if len(raw_vals) > 0 else 0
            r2r = raw_vals[1] if len(raw_vals) > 1 else 0
            r3r = raw_vals[2] if len(raw_vals) > 2 else 0
            d1 = dedup_vals[0] if len(dedup_vals) > 0 else 0
            d2 = dedup_vals[1] if len(dedup_vals) > 1 else 0
            d3 = dedup_vals[2] if len(dedup_vals) > 2 else 0

            print(
                f"{size_label:>4} {ckey:>8} {cfg_data['window_count']:>4} {cfg_data['avg_window_chars']:>6} | "
                f"{r1r:>6} {r2r:>6} {r3r:>6} {det.get('raw_count_cv_pct', 0):>4.1f}% | "
                f"{d1:>6} {d2:>6} {d3:>6} {det.get('dedup_count_cv_pct', 0):>4.1f}% | "
                f"{avg_spec:>4.1f}% {det.get('triple_overlap_pct', 0):>4.1f}% "
                f"{'Y' if det.get('type_distribution_stable') else 'N':>6} | "
                f"{avg_dur:>5.0f}s"
            )

            # Track best specificity (across all docs)
            if avg_spec > best_score:
                best_score = avg_spec
                best_config = f"{size_label}/{ckey}"

            # Track most deterministic (lowest dedup CV)
            dcv = det.get("dedup_count_cv_pct", 999)
            if dcv < best_cv:
                best_cv = dcv
                most_deterministic = f"{size_label}/{ckey}"

    print("-" * len(header))
    print(f"\nBest specificity: {best_config} ({best_score:.1f}%)")
    print(f"Most deterministic: {most_deterministic} (CV={best_cv:.1f}%)")

    # Final GPU stats
    gpu_final = get_gpu_stats()
    print(f"\nGPU Final: {gpu_final}")

    # -----------------------------------------------------------------------
    # Find outlier runs (duration > 2× average for that config)
    # -----------------------------------------------------------------------

    outliers = []
    for size_label, doc_result in all_results.items():
        for ckey, cfg_data in doc_result.get("configs", {}).items():
            runs = cfg_data.get("runs", [])
            if not runs:
                continue
            avg_dur = sum(r["duration_s"] for r in runs) / len(runs)
            for r in runs:
                if r["duration_s"] > avg_dur * 2 and avg_dur > 0:
                    outliers.append(
                        {
                            "doc": size_label,
                            "config": ckey,
                            "run": r["run"],
                            "duration_s": r["duration_s"],
                            "avg_duration_s": round(avg_dur, 1),
                            "ratio": round(r["duration_s"] / avg_dur, 1),
                        }
                    )

    # -----------------------------------------------------------------------
    # Aggregate: best config across ALL documents
    # -----------------------------------------------------------------------

    config_aggregates = {}
    for ws, ov in CONFIGS:
        ck = config_key(ws, ov)
        specs = []
        cvs = []
        overlaps = []
        durations = []
        for size_label, doc_result in all_results.items():
            cfg = doc_result.get("configs", {}).get(ck)
            if not cfg:
                continue
            runs = cfg["runs"]
            det = cfg["determinism"]
            avg_spec = sum(r["raw_specificity_pct"] for r in runs) / len(runs)
            avg_dur = sum(r["duration_s"] for r in runs) / len(runs)
            specs.append(avg_spec)
            cvs.append(det["dedup_count_cv_pct"])
            overlaps.append(det["triple_overlap_pct"])
            durations.append(avg_dur)

        if specs:
            config_aggregates[ck] = {
                "avg_specificity_pct": round(sum(specs) / len(specs), 1),
                "avg_dedup_cv_pct": round(sum(cvs) / len(cvs), 1),
                "avg_triple_overlap_pct": round(sum(overlaps) / len(overlaps), 1),
                "avg_duration_s": round(sum(durations) / len(durations), 1),
                "docs_tested": len(specs),
            }

    print(f"\n{'=' * 60}")
    print("AGGREGATE ACROSS ALL DOCUMENTS")
    print(f"{'=' * 60}")
    print(f"{'Config':>8} {'Spec%':>6} {'CV%':>5} {'Ov%':>5} {'AvgDur':>7}")
    print("-" * 40)
    for ck, agg in sorted(config_aggregates.items(), key=lambda x: -x[1]["avg_specificity_pct"]):
        print(
            f"{ck:>8} {agg['avg_specificity_pct']:>5.1f}% {agg['avg_dedup_cv_pct']:>4.1f}% "
            f"{agg['avg_triple_overlap_pct']:>4.1f}% {agg['avg_duration_s']:>6.0f}s"
        )

    # -----------------------------------------------------------------------
    # Save results
    # -----------------------------------------------------------------------

    output_dir = Path("/app/data/evaluation/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean up triples from determinism (sets aren't JSON serializable)
    for size_label, doc_result in all_results.items():
        for ckey, cfg_data in doc_result.get("configs", {}).items():
            det = cfg_data.get("determinism", {})
            # Already computed as counts — but ensure no sets remain
            det.pop("__triples", None)

    summary_output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "engine": "vllm",
        "workers": workers,
        "max_tokens": 8192,
        "max_tokens_effective": 16384,
        "cascade_timeout_s": CASCADE_TIMEOUT_S,
        "runs_per_config": RUNS_PER_CONFIG,
        "documents": all_results,
        "config_aggregates": config_aggregates,
        "summary": {
            "total_extractions": total_extraction_count,
            "total_duration_s": round(total_duration, 1),
            "total_duration_h": round(total_duration / 3600, 2),
            "best_config_by_specificity": best_config,
            "best_specificity_pct": round(best_score, 1),
            "most_deterministic_config": most_deterministic,
            "most_deterministic_cv_pct": round(best_cv, 1),
            "outlier_runs": outliers,
            "config_aggregates": config_aggregates,
        },
    }

    summary_path = output_dir / "cross_sentence_benchmark_v5.json"
    summary_path.write_text(json.dumps(summary_output, indent=2, default=str))
    print(f"\nResults saved to: {summary_path}")

    raw_path = output_dir / "cross_sentence_raw_relations_v5.json"
    raw_path.write_text(json.dumps(all_raw_relations, indent=2, default=str))
    total_raw_count = sum(len(v) for v in all_raw_relations.values())
    print(
        f"Raw relations saved to: {raw_path} ({total_raw_count} total across {len(all_raw_relations)} keys)"
    )

    print(
        f"\nBenchmark complete. {total_extraction_count} extractions in {total_duration / 3600:.1f}h"
    )


if __name__ == "__main__":
    asyncio.run(run_benchmark())
