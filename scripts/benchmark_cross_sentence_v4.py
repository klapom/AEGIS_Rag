#!/usr/bin/env python3
"""Cross-sentence window benchmark v4 — 64K tokens, 900s timeout, GPU/Memory/Cache monitoring.

Configs: w12_o3, w14_o3, w16_o4, w18_o4, w20_o5
Token budget: 64K (monkey-patches vLLM cap from 32768 → 65536)
Timeout: 900s (15 min) per cascade rank

Usage (run inside API container):
    docker exec aegis-api python /app/scripts/benchmark_cross_sentence_v4.py
"""

import asyncio
import json
import os
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
# Monkey-patches (applied at import time, before any Pydantic models are used)
# ---------------------------------------------------------------------------

# Patch 1: Use max_tokens=8192 (proven stable), proxy 2x→16384 effective.
# 64K infeasible: vLLM pre-allocates KV cache for max_tokens per request.
# 2 concurrent × 64K = 128K tokens KV cache → exceeds GPU memory at 0.45 util.
# 32K effective was proven stable in v3. Using 8192 base → 16384 effective.
print(">>> Patch 1: Using max_tokens=8192 → proxy cap min(16384, 32768) = 16384 tokens")

# Patch 2: No proxy patches needed — using production _call_vllm unchanged.
# Production: min(max_tokens*2, 32768) = min(16384, 32768) = 16384, timeout=600s, retry=3x
# Cascade timeout=900s covers the case where a window takes >600s (retry kicks in).
print(">>> Patch 2: Using PRODUCTION proxy (cap=32768, timeout=600s, retry=3x)")


# ---------------------------------------------------------------------------
# GPU / Memory / Cache monitoring helpers
# ---------------------------------------------------------------------------


def get_gpu_stats() -> dict:
    """Query nvidia-smi for GPU utilization, memory, temperature."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,memory.free,temperature.gpu,power.draw",
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
            "gpu_mem_free_mb": float(parts[3]),
            "gpu_temp_c": float(parts[4]),
            "gpu_power_w": float(parts[5]) if parts[5] != "[N/A]" else None,
        }
    except Exception as e:
        return {"error": str(e)}


def get_system_memory() -> dict:
    """Read /proc/meminfo for host RAM stats."""
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        info = {}
        for line in lines:
            k, v = line.split(":")
            info[k.strip()] = int(v.strip().split()[0])  # kB
        return {
            "ram_total_gb": round(info["MemTotal"] / 1048576, 1),
            "ram_available_gb": round(info["MemAvailable"] / 1048576, 1),
            "ram_used_gb": round((info["MemTotal"] - info["MemAvailable"]) / 1048576, 1),
        }
    except Exception as e:
        return {"error": str(e)}


async def get_redis_cache_stats() -> dict:
    """Count prompt_cache keys and total Redis memory."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url("redis://redis:6379/0", decode_responses=True)
        keys = await r.keys("prompt_cache:*")
        info = await r.info("memory")
        await r.close()
        return {
            "prompt_cache_keys": len(keys),
            "redis_used_memory_mb": round(info.get("used_memory", 0) / 1048576, 1),
            "redis_peak_memory_mb": round(info.get("used_memory_peak", 0) / 1048576, 1),
        }
    except Exception as e:
        return {"error": str(e)}


async def get_vllm_stats() -> dict:
    """Query vLLM /metrics for active requests and KV cache."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get("http://vllm:8001/metrics", timeout=5)
            text = resp.text
        stats = {}
        for line in text.split("\n"):
            if line.startswith("vllm:num_requests_running"):
                stats["vllm_active_requests"] = float(line.split()[-1])
            elif line.startswith("vllm:num_requests_waiting"):
                stats["vllm_queued_requests"] = float(line.split()[-1])
            elif line.startswith("vllm:gpu_cache_usage_perc"):
                stats["vllm_kv_cache_pct"] = round(float(line.split()[-1]) * 100, 1)
            elif line.startswith("vllm:num_requests_swapped"):
                stats["vllm_swapped_requests"] = float(line.split()[-1])
        return stats
    except Exception as e:
        return {"error": str(e)}


async def snapshot_all_metrics(label: str) -> dict:
    """Capture a full metrics snapshot."""
    gpu = get_gpu_stats()
    ram = get_system_memory()
    cache = await get_redis_cache_stats()
    vllm = await get_vllm_stats()
    return {
        "label": label,
        "timestamp": time.strftime("%H:%M:%S"),
        "gpu": gpu,
        "ram": ram,
        "cache": cache,
        "vllm": vllm,
    }


def print_snapshot(snap: dict):
    """Pretty-print a metrics snapshot."""
    gpu = snap.get("gpu", {})
    ram = snap.get("ram", {})
    cache = snap.get("cache", {})
    vllm = snap.get("vllm", {})
    parts = [f"[{snap['timestamp']}] {snap['label']}"]
    if "gpu_util_pct" in gpu:
        parts.append(
            f"GPU:{gpu['gpu_util_pct']:.0f}% Mem:{gpu['gpu_mem_used_mb']:.0f}/{gpu['gpu_mem_total_mb']:.0f}MB T:{gpu['gpu_temp_c']:.0f}°C"
        )
    if "ram_used_gb" in ram:
        parts.append(f"RAM:{ram['ram_used_gb']}/{ram['ram_total_gb']}GB")
    if "prompt_cache_keys" in cache:
        parts.append(f"Cache:{cache['prompt_cache_keys']}keys/{cache['redis_used_memory_mb']}MB")
    if "vllm_active_requests" in vllm:
        parts.append(
            f"vLLM:act={int(vllm['vllm_active_requests'])} q={int(vllm.get('vllm_queued_requests', 0))} KV={vllm.get('vllm_kv_cache_pct', '?')}%"
        )
    print("  " + " | ".join(parts))


# ---------------------------------------------------------------------------
# Background GPU monitor (samples every 10s during extraction)
# ---------------------------------------------------------------------------


class GpuMonitor:
    def __init__(self):
        self.samples = []
        self._task = None
        self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        while self._running:
            snap = get_gpu_stats()
            snap["ts"] = time.time()
            self.samples.append(snap)
            await asyncio.sleep(10)

    def summary(self) -> dict:
        if not self.samples:
            return {}
        utils = [s["gpu_util_pct"] for s in self.samples if "gpu_util_pct" in s]
        mems = [s["gpu_mem_used_mb"] for s in self.samples if "gpu_mem_used_mb" in s]
        temps = [s["gpu_temp_c"] for s in self.samples if "gpu_temp_c" in s]
        return {
            "sample_count": len(self.samples),
            "gpu_util_avg": round(sum(utils) / len(utils), 1) if utils else None,
            "gpu_util_max": max(utils) if utils else None,
            "gpu_mem_avg_mb": round(sum(mems) / len(mems)) if mems else None,
            "gpu_mem_max_mb": max(mems) if mems else None,
            "gpu_temp_avg_c": round(sum(temps) / len(temps), 1) if temps else None,
            "gpu_temp_max_c": max(temps) if temps else None,
        }


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------


async def run_benchmark():
    from src.components.graph_rag.extraction_service import ExtractionService
    from src.components.graph_rag.cross_sentence_extractor import get_cross_sentence_extractor
    from src.config.extraction_cascade import CascadeRankConfig, ExtractionMethod
    from src.core.config import settings

    # Load test file
    test_file = Path("/app/data/ragas_phase1_contexts/ragas_phase1_0050_ragbench_5041.txt")
    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return

    text = test_file.read_text()
    import re

    sentence_count = len(re.split(r"[.!?]+\s", text))

    print(f"{'=' * 80}")
    print(f"  Cross-Sentence Window Benchmark v4")
    print(f"  64K token budget | 900s timeout | GPU/Memory/Cache monitoring")
    print(f"{'=' * 80}")
    print(f"File: {test_file.name} ({len(text)} bytes, ~{sentence_count} sentences)")
    print(f"Engine: vLLM only (2 workers)")
    print(f"max_tokens: 8192 (ExtractionService) → vLLM gets min(8192*2, 32768) = 16384")
    print(f"Cascade timeout: 900s (15 min)")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Baseline snapshot
    snap = await snapshot_all_metrics("BASELINE")
    print_snapshot(snap)
    baseline_metrics = snap
    print()

    # Window configurations
    configs = [
        (12, 3),
        (14, 3),
        (16, 4),
        (18, 4),
        (20, 5),
    ]

    # Phase 1: Entity Extraction
    print("--- Phase 1: Entity Extraction ---")
    snap_pre = await snapshot_all_metrics("PRE_ENTITY")
    print_snapshot(snap_pre)

    # 8192 → vLLM gets min(8192*2, 32768) = 16384 (same as v3, proven stable)
    service = ExtractionService(
        llm_model=settings.extraction_llm_model,
        temperature=0.1,
        max_tokens=8192,
    )

    t0 = time.time()
    entities = await service.extract_entities(text=text, document_id="bench_v4_doc")
    entity_time = time.time() - t0

    snap_post = await snapshot_all_metrics("POST_ENTITY")
    print_snapshot(snap_post)
    print(f"Entities: {len(entities)} extracted in {entity_time:.1f}s")

    entity_types = Counter()
    for e in entities:
        etype = getattr(e, "type", None) or getattr(e, "entity_type", "UNKNOWN")
        entity_types[etype] += 1
    print(f"Entity types: {dict(entity_types)}")
    print()

    # Custom rank config with 900s timeout
    rank_config = CascadeRankConfig(
        rank=1,
        model=settings.extraction_llm_model,
        method=ExtractionMethod.LLM_ONLY,
        entity_timeout_s=900,
        relation_timeout_s=900,
        max_retries=3,
        retry_backoff_multiplier=1,
    )

    from src.components.graph_rag.extraction_service import EXTRACTION_WORKERS

    workers = max(1, EXTRACTION_WORKERS)
    semaphore = asyncio.Semaphore(workers)

    # Phase 2: Relation Extraction per config
    print("--- Phase 2: Relation Extraction (per config) ---")
    print(f"--- Token cap: 16384 (production) | Cascade timeout: 900s | Workers: {workers} ---")
    print()

    results = []
    all_raw_relations = {}
    all_snapshots = [baseline_metrics, snap_pre, snap_post]

    for window_size, overlap in configs:
        config_key = f"w{window_size}_o{overlap}"  # noqa: B023
        print(f"{'=' * 80}")
        print(f"Config: window_size={window_size}, overlap={overlap} [{config_key}]")
        print(f"{'=' * 80}")

        # Clear prompt cache
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

        # Pre-config snapshot
        snap_pre_cfg = await snapshot_all_metrics(f"PRE_{config_key}")
        print_snapshot(snap_pre_cfg)
        all_snapshots.append(snap_pre_cfg)

        # Generate windows
        extractor = get_cross_sentence_extractor(
            lang="en",
            window_size=window_size,
            overlap=overlap,
        )
        windows = list(extractor.create_windows(text))
        window_texts = [w.text for w in windows]
        avg_len = sum(len(w.text) for w in windows) / len(windows) if windows else 0
        print(f"  Windows: {len(windows)} (avg {avg_len:.0f} chars)")

        settings.cross_sentence_window_size = window_size
        settings.cross_sentence_overlap = overlap

        # Start GPU monitor
        gpu_mon = GpuMonitor()
        await gpu_mon.start()

        raw_per_window = []
        all_raw = []
        deduped = []
        seen_triples = set()
        window_token_stats = []

        t0 = time.time()

        async def _extract_one_window(idx, win_text):
            async with semaphore:
                w_start = time.time()
                try:
                    window_rels = await service._extract_relationships_with_rank(
                        text=win_text,
                        entities=entities,
                        rank_config=rank_config,  # noqa: B023
                        document_id=f"bench_v4_{config_key}_window_{idx}",  # noqa: B023
                        domain=None,
                    )
                    w_dur = time.time() - w_start
                    return idx, win_text, window_rels, w_dur, None
                except Exception as e:
                    w_dur = time.time() - w_start
                    print(f"    Window {idx} ERROR ({w_dur:.0f}s): {repr(e)}")
                    return idx, win_text, [], w_dur, repr(e)

        tasks = [_extract_one_window(i, wt) for i, wt in enumerate(window_texts)]
        window_results = await asyncio.gather(*tasks)

        # Stop GPU monitor
        await gpu_mon.stop()
        gpu_summary = gpu_mon.summary()

        for idx, win_text, window_rels, w_dur, w_err in sorted(window_results, key=lambda x: x[0]):
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
                    "original_type": getattr(rel, "original_type", None),
                }
                raw_rels_dicts.append(raw_dict)
                all_raw.append(raw_dict)

            raw_per_window.append(
                {
                    "window_index": idx,
                    "window_chars": len(win_text),
                    "raw_count": len(window_rels),
                    "duration_s": round(w_dur, 1),
                    "error": w_err,
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

            status = "ERROR" if w_err else "OK"
            print(
                f"    Window {idx}: {len(window_rels)} raw → {unique_count} unique ({w_dur:.0f}s) [{status}]"
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

        # Post-config snapshot
        snap_post_cfg = await snapshot_all_metrics(f"POST_{config_key}")
        print_snapshot(snap_post_cfg)
        all_snapshots.append(snap_post_cfg)

        # Post-config cache stats
        cache_post = await get_redis_cache_stats()

        result = {
            "config_key": config_key,
            "window_size": window_size,
            "overlap": overlap,
            "windows": len(windows),
            "avg_window_chars": int(avg_len),
            "duration_s": round(duration, 1),
            "timeout_s": 900,
            "max_tokens_effective": 16384,
            # Raw
            "raw_total": total_raw,
            "raw_specific": specific_raw,
            "raw_generic": generic_raw,
            "raw_specificity_pct": round(specific_raw / max(total_raw, 1) * 100, 1),
            # Dedup
            "deduped_total": total_deduped,
            "deduped_specific": specific_deduped,
            "deduped_generic": generic_deduped,
            "deduped_specificity_pct": round(specific_deduped / max(total_deduped, 1) * 100, 1),
            "dedup_removed": total_raw - total_deduped,
            "dedup_rate_pct": dedup_rate,
            # Types
            "raw_type_distribution": dict(rel_types_raw.most_common(15)),
            "deduped_type_distribution": dict(rel_types_deduped.most_common(15)),
            # Per-window
            "per_window": raw_per_window,
            # GPU monitoring
            "gpu_monitoring": gpu_summary,
            # Cache
            "cache_post": cache_post,
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
        ga, gm, gt = (
            gpu_summary.get("gpu_util_avg"),
            gpu_summary.get("gpu_mem_avg_mb"),
            gpu_summary.get("gpu_temp_avg_c"),
        )
        gpa, gpm, gpt = (
            gpu_summary.get("gpu_util_max"),
            gpu_summary.get("gpu_mem_max_mb"),
            gpu_summary.get("gpu_temp_max_c"),
        )
        print(f"  GPU avg: {ga or '?'}% util, {gm or '?'}MB, {gt or '?'}°C")
        print(f"  GPU peak: {gpa or '?'}% util, {gpm or '?'}MB, {gpt or '?'}°C")
        print(
            f"  Cache: {cache_post.get('prompt_cache_keys', '?')} keys, {cache_post.get('redis_used_memory_mb', '?')} MB"
        )
        print(f"  Raw types:   {dict(rel_types_raw.most_common(8))}")
        print(f"  Dedup types: {dict(rel_types_deduped.most_common(8))}")
        print()

    # Summary table
    print()
    print("=" * 140)
    print("SUMMARY TABLE (v4 — 16K tokens, 900s timeout, large windows)")
    print("=" * 140)
    print(
        f"{'Config':>10} {'Win':>4} {'AvgChr':>6} {'Dur':>6} "
        f"{'Raw':>5} {'RSpec%':>6} "
        f"{'Dedup':>5} {'DSpec%':>6} {'Dup%':>5} "
        f"{'GPUavg':>6} {'GPUpk':>6} {'MEMavg':>7} {'MEMpk':>7} {'Tavg':>5} {'Tpk':>4} "
        f"{'Cache':>5}"
    )
    print("-" * 140)

    def _fmt(val, fmt_str, fallback="—"):
        if val is None:
            return f"{fallback:>{len(fmt_str.format(0))}}"
        return fmt_str.format(val)

    for r in results:
        g = r.get("gpu_monitoring", {})
        c = r.get("cache_post", {})
        gpu_avg = g.get("gpu_util_avg")
        gpu_max = g.get("gpu_util_max")
        mem_avg = g.get("gpu_mem_avg_mb")
        mem_max = g.get("gpu_mem_max_mb")
        t_avg = g.get("gpu_temp_avg_c")
        t_max = g.get("gpu_temp_max_c")
        cache_k = c.get("prompt_cache_keys", 0)
        print(
            f"{r['config_key']:>10} {r['windows']:>4} {r['avg_window_chars']:>6} {r['duration_s']:>5.0f}s "
            f"{r['raw_total']:>5} {r['raw_specificity_pct']:>5.1f}% "
            f"{r['deduped_total']:>5} {r['deduped_specificity_pct']:>5.1f}% {r['dedup_rate_pct']:>4.1f}% "
            f"{_fmt(gpu_avg, '{:>5.0f}')}% {_fmt(gpu_max, '{:>5.0f}')}% "
            f"{_fmt(mem_avg, '{:>6.0f}')}M {_fmt(mem_max, '{:>6.0f}')}M "
            f"{_fmt(t_avg, '{:>4.0f}')}C {_fmt(t_max, '{:>3.0f}')}C "
            f"{cache_k:>5}"
        )
    print("-" * 140)
    print(f"\nEntities: {len(entities)} ({entity_time:.1f}s)")
    print(f"Entity types: {dict(entity_types)}")

    # Final snapshot
    snap_final = await snapshot_all_metrics("FINAL")
    print_snapshot(snap_final)
    all_snapshots.append(snap_final)

    # Save results
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "file": str(test_file.name),
        "file_size_bytes": len(text),
        "sentence_count": sentence_count,
        "engine": "vllm",
        "workers": 2,
        "max_tokens_extraction_service": 8192,
        "max_tokens_vllm_effective": 16384,
        "cascade_timeout_s": 900,
        "entity_count": len(entities),
        "entity_types": dict(entity_types),
        "entity_extraction_time_s": round(entity_time, 1),
        "window_benchmarks": results,
        "metrics_snapshots": all_snapshots,
    }

    output_dir = Path("/app/data/evaluation/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "cross_sentence_benchmark_v4.json"
    summary_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults saved to: {summary_path}")

    raw_path = output_dir / "cross_sentence_raw_relations_v4.json"
    raw_path.write_text(json.dumps(all_raw_relations, indent=2, default=str))
    print(
        f"Raw relations saved to: {raw_path} ({sum(len(v) for v in all_raw_relations.values())} total)"
    )


if __name__ == "__main__":
    asyncio.run(run_benchmark())
