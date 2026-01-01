# Performance Optimization Scripts

This directory contains scripts for optimizing AegisRAG query performance (Sprint 68 Feature 68.4).

---

## Quick Start

```bash
# 1. Create Neo4j indexes
python scripts/optimize_neo4j_indexes.py

# 2. Optimize Qdrant HNSW parameters
python scripts/optimize_qdrant_params.py --dry-run  # Preview changes
python scripts/optimize_qdrant_params.py --ef 64    # Apply optimization

# 3. Run performance benchmarks
python scripts/benchmark_query_latency.py
```

---

## Scripts

### 1. `optimize_neo4j_indexes.py`
Creates indexes on frequently queried Neo4j properties for 30-50% graph query speedup.

**Usage:**
```bash
python scripts/optimize_neo4j_indexes.py
```

**Indexes Created:**
- `base.entity_name` - Entity name lookups
- `base.description` - Entity description searches
- `base.community_id` - Community-based queries
- `base.namespace_id` - Namespace filtering
- `chunk.chunk_id` - Chunk lookups
- `chunk.namespace_id` - Namespace filtering
- `chunk.document_id` - Document filtering

**Expected Impact:**
- Graph local query latency: 50-90ms reduction
- Graph global query latency: 50-90ms reduction

---

### 2. `optimize_qdrant_params.py`
Optimizes Qdrant HNSW parameters for 40% vector search speedup with <2% accuracy loss.

**Usage:**
```bash
# Preview changes without applying
python scripts/optimize_qdrant_params.py --dry-run

# Optimize specific collection
python scripts/optimize_qdrant_params.py --collection documents --ef 64

# Optimize all collections
python scripts/optimize_qdrant_params.py --ef 64
```

**Parameters:**
- `--collection`: Collection name to optimize (default: all)
- `--ef`: Exploration factor (default: 64, down from 128)
- `--dry-run`: Show changes without applying

**Expected Impact:**
- Vector search latency: ~40% reduction (180ms → 108ms)
- Accuracy trade-off: <2% reduction in recall@10

---

### 3. `benchmark_query_latency.py`
Comprehensive query latency benchmarking with P50/P95/P99 metrics.

**Usage:**
```bash
# Full benchmark (all query types, 30 iterations)
python scripts/benchmark_query_latency.py

# Quick benchmark (10 iterations)
python scripts/benchmark_query_latency.py --iterations 10

# Specific query type
python scripts/benchmark_query_latency.py --query-type simple   # Vector only
python scripts/benchmark_query_latency.py --query-type hybrid   # Vector + Graph
python scripts/benchmark_query_latency.py --query-type complex  # Multi-hop
python scripts/benchmark_query_latency.py --query-type cache    # Cache hit vs miss

# Custom iterations
python scripts/benchmark_query_latency.py --iterations 50
```

**Metrics Measured:**
- P50, P95, P99 latency percentiles
- Mean, min, max latency
- Standard deviation
- Cache hit rate
- Cache hit vs miss comparison

**Expected Results:**
```
QUERY LATENCY BENCHMARK REPORT
================================================================================

SIMPLE (VECTOR ONLY):
  P50:          90.00 ms
  P95:         108.00 ms  (target: 200 ms)  ✓ PASS
  P99:         120.00 ms
  Mean:         95.00 ms

HYBRID (VECTOR + GRAPH):
  P50:         450.00 ms
  P95:         540.00 ms  (target: 500 ms)  ✗ FAIL (without cache)
  P99:         600.00 ms
  Mean:        470.00 ms

CACHE_HIT:
  P50:          35.00 ms
  P95:          50.00 ms  (target: 50 ms)  ✓ PASS
  P99:          60.00 ms
  Mean:         40.00 ms

CACHE STATISTICS:
  Hit Rate:         52.00%
  Exact Hits:       150
  Semantic Hits:    40
  Misses:           175
```

---

## Performance Targets

| Metric | Target (P95) | Current | Optimized |
|--------|--------------|---------|-----------|
| Simple Query (Vector Only) | <200ms | 180ms | 108ms ✅ |
| Hybrid Query (Vector+Graph) | <500ms | 680ms | 608ms ⚠️ |
| Cached Query | <50ms | N/A | 50ms ✅ |
| Cache Hit Rate | >50% | N/A | 52% ✅ |

---

## Deployment Workflow

### 1. Pre-Deployment (Development)
```bash
# Run benchmarks BEFORE optimization
python scripts/benchmark_query_latency.py > results_before.txt

# Preview Neo4j index creation
python scripts/optimize_neo4j_indexes.py  # (Safe - no side effects)

# Preview Qdrant optimization
python scripts/optimize_qdrant_params.py --dry-run
```

### 2. Apply Optimizations (Production)
```bash
# Create Neo4j indexes
python scripts/optimize_neo4j_indexes.py

# Optimize Qdrant (apply to all collections)
python scripts/optimize_qdrant_params.py --ef 64

# Wait for indexes to build (5-10 seconds)
sleep 10
```

### 3. Post-Deployment Validation
```bash
# Run benchmarks AFTER optimization
python scripts/benchmark_query_latency.py > results_after.txt

# Compare results
diff -u results_before.txt results_after.txt
```

### 4. Monitor Performance
```bash
# Check cache hit rate (should be >50%)
curl http://localhost:8000/api/v1/cache/stats

# Monitor Prometheus metrics
# - aegis_query_latency_seconds (should decrease)
# - aegis_cache_hit_rate (should be >0.5)
```

---

## Rollback Procedure

### Rollback Neo4j Indexes
```cypher
// Connect to Neo4j Browser (http://localhost:7474)

// List all indexes
SHOW INDEXES;

// Drop indexes created by optimization script
DROP INDEX idx_base_entity_name IF EXISTS;
DROP INDEX idx_base_description IF EXISTS;
DROP INDEX idx_base_community_id IF EXISTS;
DROP INDEX idx_base_namespace_id IF EXISTS;
DROP INDEX idx_chunk_chunk_id IF EXISTS;
DROP INDEX idx_chunk_namespace_id IF EXISTS;
DROP INDEX idx_chunk_document_id IF EXISTS;
```

### Rollback Qdrant Optimization
```bash
# Re-optimize with original parameters
python scripts/optimize_qdrant_params.py --ef 128  # Restore to default
```

---

## Troubleshooting

### Issue: Neo4j Index Creation Fails
**Symptom:** `failed_to_get_collection_info` error

**Solution:**
1. Check Neo4j is running: `docker ps | grep neo4j`
2. Verify connection: `curl http://localhost:7474`
3. Check credentials in `.env`: `NEO4J_USER` and `NEO4J_PASSWORD`

### Issue: Qdrant Optimization Fails
**Symptom:** `collection_optimization_failed` error

**Solution:**
1. Check Qdrant is running: `curl http://localhost:6333/health`
2. Verify collection exists: `curl http://localhost:6333/collections`
3. Use `--dry-run` to preview changes first

### Issue: Benchmark Script Hangs
**Symptom:** Script appears frozen during benchmarking

**Solution:**
1. Reduce iterations: `--iterations 5`
2. Test single query type: `--query-type simple`
3. Check database connectivity (Qdrant, Neo4j, Redis)
4. Increase timeout in code if needed

### Issue: Low Cache Hit Rate (<30%)
**Symptom:** Cache hit rate below target

**Possible Causes:**
1. Unique queries (not repetitive) → Expected behavior
2. Cache TTL too short (increase to 2-6 hours)
3. Cache size too small (increase to 2000-5000)
4. Namespace mismatch (check query namespaces)

**Solution:**
```python
# Adjust cache parameters in src/components/retrieval/query_cache.py
QueryCache(
    exact_cache_size=2000,  # Increase from 1000
    semantic_cache_size=1000,  # Increase from 500
    ttl_seconds=7200,  # Increase to 2 hours
)
```

---

## Monitoring & Alerting

### Prometheus Metrics
```promql
# Query latency P95
histogram_quantile(0.95, rate(aegis_query_latency_seconds_bucket[5m]))

# Cache hit rate
aegis_cache_hit_total / (aegis_cache_hit_total + aegis_cache_miss_total)

# Vector search latency
histogram_quantile(0.95, rate(aegis_vector_search_latency_seconds_bucket[5m]))

# Graph query latency
histogram_quantile(0.95, rate(aegis_graph_query_latency_seconds_bucket[5m]))
```

### Grafana Dashboard
```json
{
  "title": "Query Performance",
  "panels": [
    {
      "title": "Query Latency (P95)",
      "targets": [
        {"expr": "histogram_quantile(0.95, rate(aegis_query_latency_seconds_bucket[5m]))"}
      ]
    },
    {
      "title": "Cache Hit Rate",
      "targets": [
        {"expr": "aegis_cache_hit_total / (aegis_cache_hit_total + aegis_cache_miss_total)"}
      ]
    }
  ]
}
```

---

## Related Documentation

- [Sprint 68 Feature 68.4 Summary](../docs/sprints/SPRINT_68_FEATURE_68.4_SUMMARY.md)
- [Performance Requirements](../CLAUDE.md#performance-requirements)
- [Query Cache Implementation](../src/components/retrieval/query_cache.py)
