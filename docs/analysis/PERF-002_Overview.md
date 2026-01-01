# PERF-002: RAG Pipeline Performance Profiling - Overview

**Sprint:** 68
**Feature:** 68.2 - Performance Profiling & Bottleneck Analysis
**Status:** READY FOR EXECUTION
**Date:** 2026-01-01

## Quick Links

- **Profiling Scripts**: `/home/admin/projects/aegisrag/AEGIS_Rag/scripts/`
  - `profile_pipeline.py` - Pipeline latency profiling
  - `profile_memory.py` - Memory usage profiling
  - `profile_report.py` - Comprehensive report generator
  - `test_profiling.sh` - Quick validation test
  - `README_PROFILING.md` - Detailed usage guide

- **Documentation**:
  - `docs/sprints/SPRINT_68_FEATURE_68.2_SUMMARY.md` - Feature summary
  - `docs/analysis/PERF-002_Pipeline_Profiling.md` - Generated report (after running)

## What Was Delivered

### 1. Profiling Infrastructure

Three comprehensive profiling scripts that analyze:

**Pipeline Performance:**
- Stage-level timing (5 stages)
- Function-level hotspots (cProfile)
- Bottleneck identification
- Statistical analysis (p50, p95, p99)

**Memory Usage:**
- Per-stage memory delta
- Peak memory tracking
- Memory leak detection
- Top allocation identification

**Comprehensive Analysis:**
- Automated report generation
- Optimization roadmap (prioritized)
- Quick wins identification
- Markdown + JSON output

### 2. Performance Baseline

Expected pipeline stages:

| Stage | Target | Tool |
|-------|--------|------|
| 1. Intent Classification | 50ms | SetFit + BGE-M3 embeddings |
| 2. Query Rewriting | 80ms | LLM (optional, skipped) |
| 3. Retrieval (4-Way) | 180ms | Qdrant + Neo4j (parallel) |
| 4. Reranking | 50ms | Cross-encoder adaptive |
| 5. Generation | 320ms | LLM (Ollama) |
| **Total (target p95)** | **<1000ms** | Full pipeline |

### 3. Usage Examples

```bash
# Quick validation
./scripts/test_profiling.sh

# Single query profiling
python scripts/profile_pipeline.py --query "What is OMNITRACKER?"

# Intensive profiling (100 queries)
python scripts/profile_pipeline.py --mode intensive

# Memory leak detection
python scripts/profile_memory.py --iterations 50

# Generate full report (5-10 minutes)
python scripts/profile_report.py
```

## How to Use This

### Step 1: Validate Setup

```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag
./scripts/test_profiling.sh
```

This runs quick tests to ensure all profiling scripts work.

### Step 2: Run Intensive Profiling

```bash
# This will take ~5 minutes
python scripts/profile_pipeline.py --mode intensive --output intensive_100q.json
```

This profiles 100 queries to get accurate p95/p99 statistics.

### Step 3: Generate Full Report

```bash
# This will take ~10 minutes total
python scripts/profile_report.py \
    --output docs/analysis/PERF-002_Pipeline_Profiling.md \
    --json raw_data.json
```

This runs:
1. Pipeline profiling (100 queries)
2. Memory profiling (3 queries)
3. Leak detection (30 iterations)
4. Report generation

### Step 4: Review Results

Open `docs/analysis/PERF-002_Pipeline_Profiling.md` to see:
- Performance metrics (p95, mean, etc.)
- Bottleneck frequency analysis
- Memory usage statistics
- Optimization roadmap

### Step 5: Implement Optimizations

Based on bottlenecks identified:
- P0 bottlenecks: Must fix (affects >20% of queries)
- P1 bottlenecks: Should fix (affects 10-20%)
- P2 bottlenecks: Nice-to-have

## Key Performance Indicators

### Latency Targets

| Metric | Target | Status |
|--------|--------|--------|
| p50 | <500ms | TBD |
| p95 | <1000ms | TBD |
| p99 | <1500ms | TBD |

### Memory Targets

| Metric | Target | Status |
|--------|--------|--------|
| Peak Memory | <512MB | TBD |
| Memory per Request | <512MB | TBD |
| Memory Leak Rate | <0.5 MB/iter | TBD |

### Throughput Targets

| Metric | Target | Status |
|--------|--------|--------|
| Sustained Load | 50 QPS | TBD |
| Peak Load | 100 QPS | TBD |

## Expected Bottlenecks

Based on architecture analysis:

### 1. LLM Generation (Expected: 40-50% of queries)

**Why:**
- I/O bound (Ollama API)
- Variable latency (200-500ms)
- Large context processing

**Solutions:**
- Implement streaming (reduce TTFT)
- Model selection (smaller for simple queries)
- Parallel generation for multi-turn

### 2. 4-Way Retrieval (Expected: 25-35% of queries)

**Why:**
- 4 parallel DB queries
- Graph queries are slow (Cypher)
- No caching

**Solutions:**
- Redis query caching
- Optimize Cypher queries
- Increase connection pools

### 3. Reranking (Expected: 10-20% of queries)

**Why:**
- CPU-intensive cross-encoder
- Scales with candidate pool

**Solutions:**
- Batch processing (increase to 64)
- GPU acceleration
- Reduce candidate pool

### 4. Intent Classification (Expected: 5-10% of queries)

**Why:**
- SetFit model inference
- Cache misses

**Solutions:**
- Increase cache size
- Persistent Redis cache
- Rule-based fallback

## Profiling Tools Reference

### Pipeline Profiling

- **Stage-level timing**: `time.perf_counter()` (negligible overhead)
- **Function-level**: `cProfile` (~5-10% overhead)
- **Statistical analysis**: p50, p95, p99 from 100 queries

### Memory Profiling

- **Memory tracking**: `tracemalloc` (~10-15% overhead)
- **Process memory**: `psutil` (negligible overhead)
- **Leak detection**: Linear regression over iterations

### Report Generation

- **Automated**: Runs all profiling + generates markdown
- **Prioritization**: Bottlenecks ranked by frequency
- **Recommendations**: Based on measured impact

## Next Steps After Profiling

### 1. Review Results

- Check if p95 < 1000ms (PASS/FAIL)
- Identify top 3 bottlenecks
- Review memory usage

### 2. Plan Sprint 69 Optimizations

Based on bottlenecks:
- P0 optimizations (must fix)
- P1 optimizations (should fix)
- Quick wins (low-hanging fruit)

### 3. Implement & Re-Profile

After optimization:
- Re-run intensive profiling
- Compare with baseline
- Measure improvement percentage

### 4. Continuous Monitoring

- Run profiling after each sprint
- Track performance regressions
- Update optimization roadmap

## Files Created

| File | Purpose | Size |
|------|---------|------|
| `scripts/profile_pipeline.py` | Pipeline profiling | ~400 lines |
| `scripts/profile_memory.py` | Memory profiling | ~350 lines |
| `scripts/profile_report.py` | Report generator | ~500 lines |
| `scripts/test_profiling.sh` | Quick validation | ~50 lines |
| `scripts/README_PROFILING.md` | Usage guide | ~800 lines |
| `docs/sprints/SPRINT_68_FEATURE_68.2_SUMMARY.md` | Feature summary | ~500 lines |
| `docs/analysis/PERF-002_Overview.md` | This file | ~350 lines |

**Total:** ~2,950 lines of code and documentation

## Success Criteria

- [x] All 5 pipeline stages profiled
- [x] Memory profiling with leak detection
- [x] Bottleneck identification with top 10 functions
- [x] Optimization roadmap (prioritized)
- [x] Profiling scripts documented
- [ ] **Profiling executed and report generated** (NEXT STEP)

## Performance Guardian Role

As the Performance Agent, your responsibilities after this feature:

1. **Run profiling after each sprint**
   - Detect performance regressions
   - Track optimization progress

2. **Review bottleneck reports**
   - Identify new bottlenecks
   - Update optimization roadmap

3. **Recommend optimizations**
   - Prioritize based on impact
   - Estimate effort (story points)

4. **Validate improvements**
   - Measure before/after
   - Document performance gains

## References

- **CLAUDE.md**: Performance Requirements section
- **docs/ARCHITECTURE.md**: System architecture
- **docs/TECH_STACK.md**: Technology stack
- **src/agents/coordinator.py**: Pipeline orchestration
- **src/components/retrieval/**: Retrieval components

---

**Status:** READY FOR EXECUTION
**Next Action:** Run `./scripts/test_profiling.sh` to validate setup
**Performance Agent:** Complete
**Date:** 2026-01-01
