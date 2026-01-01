# RAG Pipeline Profiling Scripts

**Sprint 68 Feature 68.2**: Performance Profiling & Bottleneck Analysis

This directory contains comprehensive profiling scripts for the AegisRAG system, designed to identify performance bottlenecks and guide optimization efforts.

## Quick Start

```bash
# 1. Quick validation test
./scripts/test_profiling.sh

# 2. Profile a single query
python scripts/profile_pipeline.py --query "What is the project architecture?"

# 3. Generate full bottleneck report (takes 5-10 minutes)
python scripts/profile_report.py
```

## Scripts Overview

### 1. `profile_pipeline.py` - Pipeline Latency Profiling

Profiles the 5 stages of the RAG pipeline:

| Stage | Target | Description |
|-------|--------|-------------|
| 1. Intent Classification | 50ms | SetFit-based query intent detection |
| 2. Query Rewriting | 80ms | LLM-based query enhancement (optional) |
| 3. Retrieval | 180ms | 4-Way Hybrid Search (Vector + BM25 + Graph) |
| 4. Reranking | 50ms | Cross-encoder adaptive reranking |
| 5. Generation | 320ms | LLM answer generation |

**Usage:**

```bash
# Single query profiling
python scripts/profile_pipeline.py \
    --query "What is OMNITRACKER?" \
    --output single_query.json

# Intensive profiling (100 queries for p95/p99 statistics)
python scripts/profile_pipeline.py \
    --mode intensive \
    --output intensive_100q.json

# Function-level profiling with cProfile
python scripts/profile_pipeline.py \
    --query "How does authentication work?" \
    --cprofile
```

**Output:**

```json
{
  "query": "What is the project architecture?",
  "total_latency_ms": 450.2,
  "stages": {
    "1_intent_classification": {
      "latency_ms": 35.1,
      "intent": "exploratory",
      "method": "setfit",
      "target_ms": 50,
      "status": "PASS"
    },
    "3_retrieval": {
      "latency_ms": 165.3,
      "channels": {
        "vector_count": 10,
        "bm25_count": 8,
        "graph_local_count": 5,
        "graph_global_count": 3
      },
      "target_ms": 180,
      "status": "PASS"
    },
    ...
  },
  "summary": {
    "status": "PASS",
    "bottlenecks": [
      "generation: 250.0ms (target: 320ms, 55.6% of pipeline)"
    ]
  }
}
```

### 2. `profile_memory.py` - Memory Usage Profiling

Tracks memory usage across pipeline stages and detects memory leaks.

**Usage:**

```bash
# Single query memory profiling
python scripts/profile_memory.py \
    --query "What is the database schema?" \
    --output memory_single.json

# Memory profiling with detailed snapshot
python scripts/profile_memory.py \
    --query "How does vector search work?" \
    --snapshot

# Memory leak detection (50 iterations)
python scripts/profile_memory.py \
    --iterations 50 \
    --output leak_detection.json
```

**Output:**

```
Baseline Memory:  250.3 MB
Peak Memory:      380.5 MB
Total Delta:      130.2 MB
Target Delta:     512 MB
Status:           PASS

Stage Breakdown:
  intent_classification:   +15.2 MB (peak: 265.5 MB) [PASS]
  retrieval:               +85.3 MB (peak: 350.8 MB) [PASS]
  reranking:               +20.1 MB (peak: 370.9 MB) [PASS]
  generation:              +9.6 MB  (peak: 380.5 MB) [PASS]
```

**Memory Leak Detection:**

```
Leak Detection Results
=========================================
Initial Memory:    250.0 MB
Final Memory:      280.5 MB
Total Growth:      30.5 MB
Growth Rate:       0.610 MB/iteration
Leak Detected:     False

No significant memory leak detected.
```

### 3. `profile_report.py` - Comprehensive Bottleneck Report

Runs all profiling scripts and generates a comprehensive markdown report.

**Usage:**

```bash
# Generate full report (takes 5-10 minutes)
python scripts/profile_report.py \
    --output docs/analysis/PERF-002_Pipeline_Profiling.md \
    --json raw_data.json
```

**Report Contents:**

1. **Executive Summary**: p95 latency, peak memory, status
2. **Performance Metrics**: Mean, p50, p95, p99 latencies
3. **Bottleneck Analysis**: Frequency and impact of bottlenecks
4. **Memory Analysis**: Peak usage, leak detection
5. **Optimization Roadmap**: Prioritized recommendations (P0, P1, P2)
6. **Quick Wins**: Low-effort, high-impact optimizations

**Example Output:**

```markdown
## Executive Summary

- **p95 Latency:** 650.3ms (target: <1000ms) [PASS]
- **Mean Latency:** 480.1ms
- **Peak Memory:** 380.5MB (target: <512MB) [PASS]

## Bottleneck Analysis

### Bottleneck Frequency (out of 100 queries)

| Stage | Frequency | Percentage |
|-------|-----------|------------|
| generation | 45 | 45% |
| retrieval | 30 | 30% |
| reranking | 15 | 15% |

### Top 3 Bottlenecks

1. **generation**: Exceeded target in 45% of queries
   - **Cause:** LLM generation is I/O bound
   - **Recommendation:** Implement streaming to reduce TTFT
   - **Recommendation:** Use smaller, faster models for simple queries
```

### 4. `test_profiling.sh` - Quick Validation Test

Validates all profiling scripts with single-query tests.

**Usage:**

```bash
# Run validation tests
./scripts/test_profiling.sh
```

## Performance Targets

From `CLAUDE.md`:

| Operation | Target (p95) |
|-----------|-------------|
| Simple Query (Vector Only) | <200ms |
| Hybrid Query (Vector + Graph) | <500ms |
| Complex Multi-Hop | <1000ms |
| Memory per Request | <512MB |
| Sustained Load | 50 QPS |
| Peak Load | 100 QPS |

## Profiling Tools Used

| Tool | Purpose | Overhead |
|------|---------|----------|
| `time.perf_counter()` | High-resolution timing | Negligible |
| `cProfile` | Function-level CPU profiling | ~5-10% |
| `tracemalloc` | Memory allocation tracking | ~10-15% |
| `psutil` | Process memory monitoring | Negligible |
| `asyncio` | Async profiling support | N/A |

## Best Practices

### 1. Run Profiling Regularly

- After each sprint (regression detection)
- Before major releases
- When adding performance-critical features

### 2. Use Intensive Mode for Accurate Metrics

Single-query profiling can be misleading due to:
- Cold start effects (model loading, cache warming)
- Network variability
- Query-specific optimizations

Intensive mode (100+ queries) provides:
- Statistical significance (p50, p95, p99)
- Bottleneck frequency analysis
- Cache hit rate impact

### 3. Profile in Production-Like Environment

Profiling in development may not reflect production:
- Different hardware (CPU, RAM)
- Different load patterns
- Different network latency

### 4. Combine Multiple Profiling Methods

- **Stage-level timing**: Identify which stage is slow
- **Function-level profiling (cProfile)**: Identify which function within a stage
- **Memory profiling**: Identify memory leaks and large allocations

### 5. Set Clear Baselines

Before optimization:
1. Run intensive profiling to establish baseline
2. Identify top 3 bottlenecks
3. Set improvement targets (e.g., "reduce p95 by 30%")
4. Optimize
5. Re-profile to measure improvement

## Common Bottlenecks

Based on AegisRAG architecture:

### 1. LLM Generation (most common)

**Symptoms:**
- High latency variance (200-500ms)
- I/O wait time

**Causes:**
- Network latency to Ollama API
- Model inference time
- Large context size

**Solutions:**
- Implement streaming (reduce TTFT)
- Use smaller models for simple queries
- Parallel generation for multi-turn

### 2. 4-Way Retrieval

**Symptoms:**
- Consistently high latency (150-250ms)
- All 4 channels contributing

**Causes:**
- 4 parallel DB queries (Qdrant, Neo4j)
- Graph queries are slow (Cypher execution)
- No query result caching

**Solutions:**
- Implement Redis query caching
- Optimize Cypher queries (EXPLAIN PLAN)
- Increase DB connection pools

### 3. Reranking

**Symptoms:**
- CPU-bound (high CPU usage)
- Scales with candidate pool size

**Causes:**
- Cross-encoder is CPU-intensive
- Small batch size (32)

**Solutions:**
- Increase batch size (64)
- Use GPU acceleration (if available)
- Reduce candidate pool before reranking

### 4. Intent Classification

**Symptoms:**
- Occasional spikes (20-50ms)
- Cache miss impact

**Causes:**
- SetFit model inference
- Low cache hit rate

**Solutions:**
- Increase cache size (1000 → 10,000)
- Persistent cache (Redis)
- Fallback to rule-based for cache misses

## Interpreting Results

### Latency Analysis

- **p50 (median)**: Typical query performance
- **p95**: 95% of queries complete within this time (SLA target)
- **p99**: Worst-case performance (exclude outliers)

**Good:** p95 < 1000ms, p50 < 500ms
**Needs Work:** p95 > 1000ms
**Critical:** p95 > 2000ms

### Memory Analysis

- **Baseline**: Memory before processing
- **Peak**: Maximum memory during processing
- **Delta**: Memory allocated for this request

**Good:** Delta < 512MB, no leaks
**Needs Work:** Delta > 512MB, slow leak (<0.5 MB/iter)
**Critical:** Delta > 1GB, fast leak (>1 MB/iter)

### Bottleneck Frequency

- **>50%**: Critical bottleneck, must fix (P0)
- **20-50%**: Major bottleneck, should fix (P1)
- **<20%**: Minor bottleneck, consider fixing (P2)

## Example Workflow

```bash
# Sprint N: Before optimization
python scripts/profile_report.py --output baseline_sprint_N.md

# Result: p95 = 850ms, bottleneck = generation (60%)

# Sprint N+1: Implement optimization (streaming generation)
# ... code changes ...

# Sprint N+1: After optimization
python scripts/profile_report.py --output optimized_sprint_N1.md

# Result: p95 = 520ms, bottleneck = retrieval (40%)
# Improvement: -330ms (38.8% faster)

# Sprint N+2: Focus on new bottleneck (retrieval caching)
```

## Troubleshooting

### Issue: "ImportError: No module named 'sentence_transformers'"

**Cause:** Reranking dependency not installed

**Solution:**
```bash
poetry install --with reranking
```

### Issue: "MemoryError: tracemalloc start() failed"

**Cause:** Insufficient memory for tracemalloc overhead

**Solution:**
- Reduce query iterations
- Profile without `--snapshot`
- Increase system memory

### Issue: "Profiling results are inconsistent"

**Cause:** Cold start effects, cache warming

**Solution:**
- Use `--mode intensive` (100 queries)
- Discard first 10 results (warm-up)
- Run multiple times and average

### Issue: "Neo4j connection timeout during profiling"

**Cause:** Connection pool exhausted

**Solution:**
```python
# src/components/graph_rag/neo4j_client.py
driver = AsyncGraphDatabase.driver(
    uri, auth=(user, password),
    max_connection_pool_size=100,  # Increase from 50
    connection_acquisition_timeout=60  # Increase from 30
)
```

## Advanced Usage

### Custom Profiling Functions

```python
# Add custom stage profiling
from scripts.profile_pipeline import PipelineProfiler

class CustomProfiler(PipelineProfiler):
    async def profile_stage_custom(self, query: str) -> dict[str, Any]:
        """Profile custom stage."""
        start = time.perf_counter()
        result = await my_custom_function(query)
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "latency_ms": latency_ms,
            "target_ms": 100,
            "status": "PASS" if latency_ms < 100 else "FAIL",
        }
```

### Integration with CI/CD

```yaml
# .github/workflows/performance.yml
name: Performance Regression Tests

on:
  pull_request:
    branches: [main]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run profiling
        run: |
          python scripts/profile_pipeline.py --mode intensive --output pr_results.json
      - name: Compare with baseline
        run: |
          python scripts/compare_baselines.py \
            --baseline baseline.json \
            --current pr_results.json \
            --threshold 10  # Fail if p95 increases >10%
```

## References

- **CLAUDE.md**: Performance Requirements
- **docs/ARCHITECTURE.md**: System architecture
- **docs/TECH_STACK.md**: Technology stack
- **docs/sprints/SPRINT_68_FEATURE_68.2_SUMMARY.md**: Feature summary

---

**Created:** Sprint 68 Feature 68.2
**Maintained by:** Performance Agent
**Last Updated:** 2026-01-01
