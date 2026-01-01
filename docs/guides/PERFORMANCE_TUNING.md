# Performance Tuning Guide

**Last Updated:** 2026-01-01
**Status:** Sprint 68 Complete
**Target:** P95 latency <500ms for hybrid queries

---

## Overview

This guide provides strategies for optimizing AegisRAG performance across the entire system stack. Sprint 68 introduced significant performance improvements:

- **Query Caching:** 93% latency reduction for cached queries
- **Memory Optimization:** 75% reduction in PDF ingestion memory
- **Vector Search:** 40% faster HNSW with ef=64
- **Graph Queries:** 30-50% faster with Neo4j indexes
- **Section Communities:** Enable community-based retrieval

This guide shows how to tune each component for your specific workload.

---

## 1. Query Caching Optimization

### 1.1 Two-Tier Caching Strategy

AegisRAG uses two cache layers:

```
User Query
    ↓
[Exact Cache] ← Match exact query + parameters?
    ↓ (miss)
[Semantic Cache] ← Match semantically similar queries?
    ↓ (miss)
[Full Retrieval] ← Execute vector + graph + memory search
    ↓
[Cache Result] → Store in both caches
    ↓
User Response (~50ms for cache hits, ~680ms for cache misses)
```

### 1.2 Configuration

```bash
# Edit .env
ENABLE_QUERY_CACHE=true                    # Master switch
QUERY_CACHE_TTL=3600                       # Cache validity (seconds)
QUERY_CACHE_MAX_SIZE=536870912             # 512MB cache

# Semantic caching (more flexible matching)
ENABLE_SEMANTIC_CACHE=true
SEMANTIC_CACHE_THRESHOLD=0.95              # 95% similarity = cache hit
SEMANTIC_CACHE_EMBEDDING_MODEL=BGE-M3

# Advanced: Cache bypass for specific queries
CACHE_BYPASS_PATTERNS="realtime,current,news"  # Comma-separated patterns
```

### 1.3 Tuning Cache TTL

```bash
# For stable knowledge base (documentation, policies):
QUERY_CACHE_TTL=7200          # 2 hours (aggressive caching)

# For mixed workloads:
QUERY_CACHE_TTL=3600          # 1 hour (balanced)

# For frequently updated data:
QUERY_CACHE_TTL=600           # 10 minutes (conservative)

# For real-time data:
QUERY_CACHE_TTL=0             # Disable caching (or use cache bypass)
```

### 1.4 Monitor Cache Performance

```bash
# Check cache statistics
curl http://localhost:8000/api/v1/admin/cache/stats | jq '.'

# Expected output:
# {
#   "total_requests": 5234,
#   "cache_hits": 3101,
#   "cache_hit_rate": 0.593,
#   "avg_hit_latency_ms": 52,
#   "avg_miss_latency_ms": 608,
#   "cache_size_mb": 312,
#   "evictions_total": 45
# }

# Acceptable ranges:
# - Cache hit rate: >50% (indicates good cache effectiveness)
# - Avg hit latency: <100ms (indicates working cache)
# - Cache size: <512MB (within memory budget)
```

### 1.5 Cache Tuning Tips

**Increase Cache Hit Rate:**

```python
# 1. Increase TTL for stable queries
QUERY_CACHE_TTL=7200  # 1 hour → 2 hours

# 2. Lower semantic similarity threshold
SEMANTIC_CACHE_THRESHOLD=0.90  # 0.95 → 0.90 (more matches)

# 3. Increase cache size
QUERY_CACHE_MAX_SIZE=1073741824  # 512MB → 1GB

# 4. Monitor what's missing
# Add logging to see cache misses:
LOG_CACHE_MISSES=true
CACHE_MISS_LOG_PATH=/tmp/cache_misses.log

# Then analyze:
cat /tmp/cache_misses.log | sort | uniq -c | sort -rn | head -20
# Shows most frequently missed queries
```

**Reduce Cache Size:**

```python
# If cache growing too large:

# 1. Lower TTL
QUERY_CACHE_TTL=1800  # 1 hour → 30 minutes

# 2. Reduce max size
QUERY_CACHE_MAX_SIZE=268435456  # 512MB → 256MB

# 3. Increase eviction aggressiveness
CACHE_EVICTION_POLICY=LRU  # Remove least recently used entries

# 4. Monitor evictions
curl http://localhost:8000/api/v1/admin/cache/stats | jq '.evictions_total'
```

---

## 2. Model Selection Tuning

### 2.1 LLM Generation Model

The generation model impacts latency and quality. Sprint 68 baseline uses **Nemotron3 Nano (30B/3a)**.

```bash
# Check current model
curl http://localhost:8000/api/v1/admin/config | jq '.llm_generation_model'

# Available models (with performance):
# nemotron-no-think:latest  (Nemotron3 Nano) - FAST (320ms)
#   - Tokens: 7B params
#   - Latency: 320ms average
#   - Memory: 15GB
#   - Quality: Excellent
#
# gpt-oss:20b                - BALANCED (450ms)
#   - Tokens: 20B params
#   - Latency: 450ms average
#   - Memory: 20GB
#   - Quality: Very Good
#
# qwen2.5:32b                - SLOW (600ms)
#   - Tokens: 32B params
#   - Latency: 600ms average
#   - Memory: 25GB
#   - Quality: Excellent
```

### 2.2 Adaptive Model Selection

Enable query-complexity-based model selection:

```bash
# Edit .env
ENABLE_ADAPTIVE_MODEL_SELECTION=true

# Configuration:
# Simple queries (1-3 sentences) → Nemotron3 Nano (320ms)
# Medium queries (4-10 sentences) → gpt-oss:20b (450ms)
# Complex queries (10+ sentences) → qwen2.5:32b (600ms)
```

### 2.3 Embedding Model Tuning

Embeddings run on CPU via sentence-transformers (no GPU needed).

```bash
# Check embedding model
curl http://localhost:8000/api/v1/admin/config | jq '.embedding_model'

# Current: BGE-M3 (1024-dim, multilingual)
# Latency: 50-80ms per batch

# Alternative models (if needed):
# - bge-small-en-v1.5        (384-dim) - FAST (20ms)
# - bge-base-en-v1.5         (768-dim) - BALANCED (40ms)
# - bge-large-en-v1.5        (1024-dim) - SLOW (80ms)

# Change in .env:
EMBEDDING_MODEL=bge-base-en-v1.5  # Smaller for faster embedding
```

### 2.4 Monitor Model Performance

```bash
# Check model latencies
curl http://localhost:8000/api/v1/admin/metrics | jq '.model_latencies'

# Expected output:
# {
#   "embedding": {"p50": 45, "p95": 75, "p99": 95},
#   "generation": {"p50": 280, "p95": 350, "p99": 420},
#   "reranking": {"p50": 35, "p95": 50, "p99": 65}
# }
```

---

## 3. Memory Budget Optimization

### 3.1 Container Memory Limits

Set appropriate memory limits for each service:

```yaml
# In docker-compose.dgx-spark.yml

services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G  # API container
        reservations:
          memory: 2G

  ollama:
    deploy:
      resources:
        limits:
          memory: 64G  # LLM server (uses GPU unified memory)

  qdrant:
    deploy:
      resources:
        limits:
          memory: 12G  # Vector DB (index + cache)

  neo4j:
    deploy:
      resources:
        limits:
          memory: 12G  # Graph DB

  redis:
    deploy:
      resources:
        limits:
          memory: 8G  # Cache layer
```

### 3.2 PDF Ingestion Memory

Sprint 68 reduced PDF memory by 75% through streaming + explicit GC.

```bash
# Verify streaming is enabled
curl http://localhost:8000/api/v1/admin/config | jq '.pdf_streaming_enabled'
# Should return: true

# Configure garbage collection
# Edit .env:
GC_INTERVAL_SECONDS=10      # Run GC every 10 seconds during ingestion
GC_GENERATION_THRESHOLD=512  # GC after 512MB allocated

# Monitor memory during ingestion
docker stats aegis-api --no-stream
# Should stay <2GB even with multiple documents
```

### 3.3 Embedding Cache Memory

```bash
# BGE-M3 embedding cache (Sprint 68 feature)
EMBEDDING_CACHE_MAX_SIZE=2147483648  # 2GB
EMBEDDING_CACHE_STRATEGY=content_hash  # Invalidate on content change

# Monitor cache
curl http://localhost:8000/api/v1/admin/cache/embedding_stats | jq '.'

# Expected:
# {
#   "cache_size_mb": 512,
#   "total_embeddings": 12345,
#   "hit_rate": 0.85,
#   "avg_latency_hit_ms": 15,
#   "avg_latency_miss_ms": 65
# }
```

### 3.4 Memory Profiling

Sprint 68 includes memory profiling utilities:

```bash
# Run memory profiler
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/profile_memory.py \
    --iterations 50 \
    --output memory_profile.json

# Analyze results
python -c "
import json
with open('memory_profile.json') as f:
    data = json.load(f)
    for component, stats in data.items():
        print(f'{component}: {stats[\"peak_mb\"]}MB (peak), {stats[\"avg_mb\"]}MB (avg)')
"

# Expected output:
# api: 2048MB (peak), 1024MB (avg)
# qdrant: 8192MB (peak), 6144MB (avg)
# neo4j: 4096MB (peak), 3072MB (avg)
# redis: 2048MB (peak), 1536MB (avg)
```

---

## 4. Database Tuning

### 4.1 Neo4j Graph Performance

```bash
# Check index status
docker exec aegis-neo4j cypher-shell \
    -u neo4j -p <password> \
    "CALL db.indexes()"

# Expected indexes from Sprint 68:
# ✓ entity_id_idx
# ✓ relation_id_idx
# ✓ community_id_idx
# ✓ section_id_idx

# If missing, create them:
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/optimize_neo4j_indexes.py
```

**Neo4j Configuration Tuning:**

```properties
# In neo4j.conf (if running standalone)

# Heap memory (32GB system)
dbms.memory.heap.initial_size=8g
dbms.memory.heap.max_size=16g

# Page cache (for index/data storage)
dbms.memory.pagecache.size=12g

# Transaction monitoring
dbms.transaction.timeout=30s

# Query timeout (prevent long-running queries)
dbms.transaction.timeout=30000ms
```

### 4.2 Qdrant Vector Search

```bash
# Current HNSW configuration (Sprint 68 optimized):
curl http://localhost:6333/collections/documents | jq '.result.config.hnsw_config'

# Expected:
# {
#   "ef": 64,              # Search parameter (40% faster, similar quality)
#   "ef_construction": 200,
#   "m": 16,
#   "full_scan_threshold": 10000
# }

# Tune for your workload:

# For accuracy (slower):
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/optimize_qdrant_params.py \
    --collection documents \
    --ef 128

# For speed (faster):
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/optimize_qdrant_params.py \
    --collection documents \
    --ef 32
```

**HNSW Parameter Guide:**

| Parameter | Value | Speed | Accuracy | When to Use |
|-----------|-------|-------|----------|------------|
| ef | 32 | Fastest | Lower | Speed critical |
| ef | 64 | Fast ✓ | Good ✓ | Balanced (default) |
| ef | 128 | Slower | Excellent | Accuracy critical |

```bash
# Test different ef values
for ef in 32 64 128; do
    python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/benchmark_query_latency.py \
        --ef $ef --iterations 10
done
```

### 4.3 Redis Cache Configuration

```bash
# Current Sprint 68 configuration:
docker exec aegis-redis redis-cli CONFIG GET "*" | grep -A1 "maxmemory"

# Expected:
# maxmemory: 8589934592 (8GB)
# maxmemory-policy: allkeys-lru

# Monitor eviction behavior
docker exec aegis-redis redis-cli INFO stats | grep -E "evicted|keyspace"

# If too many evictions:
# 1. Increase Redis memory
docker exec aegis-redis redis-cli CONFIG SET maxmemory 17179869184  # 16GB

# 2. Change eviction policy (for long TTLs)
docker exec aegis-redis redis-cli CONFIG SET maxmemory-policy volatile-lru
```

---

## 5. Profiling and Benchmarking

### 5.1 Pipeline Profiling

Sprint 68 includes comprehensive profiling scripts:

```bash
# Quick validation (2 minute run)
cd /home/admin/projects/aegisrag/AEGIS_Rag
./scripts/test_profiling.sh

# Detailed profiling (intensive mode)
python scripts/profile_pipeline.py --mode intensive

# Memory profiling
python scripts/profile_memory.py --iterations 50

# Query latency benchmarking
python scripts/benchmark_query_latency.py --iterations 30 --warmup 5
```

### 5.2 Reading Profiling Output

```bash
# Example output from profile_pipeline.py:
#
# Pipeline Performance Report
# ===========================
# Total Queries: 100
# Success Rate: 100%
#
# Stage Breakdown:
# ├─ Intent Classification: 45ms (6%)
# ├─ Query Rewriting: 0ms (0% - skipped)
# ├─ Retrieval (4-way): 180ms (25%) [BOTTLENECK]
# ├─ Reranking: 50ms (7%)
# └─ Generation: 380ms (53%) [BOTTLENECK]
#
# Total P95: 680ms
# Cache Hit Rate: 57.5%
# Speedup (with cache): 13.6x
```

### 5.3 Identify Bottlenecks

```bash
# Find slowest stage
python scripts/profile_pipeline.py --mode intensive --output json | \
    jq '.stages | sort_by(.duration_ms) | reverse | .[0]'

# If retrieval is slow:
python scripts/profile_pipeline.py --focus retrieval

# If generation is slow:
python scripts/profile_pipeline.py --focus generation
```

### 5.4 Compare Before/After

```bash
# Save baseline
python scripts/benchmark_query_latency.py \
    --iterations 30 > /tmp/baseline.txt

# Make optimization change
# ... Edit config, restart services ...

# Compare
python scripts/benchmark_query_latency.py \
    --iterations 30 > /tmp/after.txt

# Diff
diff /tmp/baseline.txt /tmp/after.txt
```

---

## 6. Section Community Detection

Sprint 68 introduces section communities for better graph reasoning.

### 6.1 Enable Community Detection

```bash
# Configuration
ENABLE_SECTION_COMMUNITIES=true
COMMUNITY_DETECTION_ALGORITHM=louvain
COMMUNITY_DETECTION_RESOLUTION=1.0  # Higher = more communities
```

### 6.2 Community-Based Retrieval

```bash
# Query with community search
curl -X POST http://localhost:8000/api/v1/graph/community_search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication methods",
    "top_k": 5
  }' | jq '.results'

# Expected: Returns 5 sections from the same community
# (faster and more coherent than random vector matches)
```

### 6.3 Tuning Community Resolution

```bash
# More granular communities (smaller communities):
COMMUNITY_DETECTION_RESOLUTION=1.5  # More communities, narrower topics

# Broader communities (larger communities):
COMMUNITY_DETECTION_RESOLUTION=0.5  # Fewer communities, wider topics

# Balanced (recommended):
COMMUNITY_DETECTION_RESOLUTION=1.0  # Default, good results
```

---

## 7. Advanced Optimization Strategies

### 7.1 Query Complexity-Based Routing

```bash
# Automatically choose search strategy based on query complexity:
ENABLE_QUERY_COMPLEXITY_ROUTING=true

# Simple queries (1-3 words): Vector search only
# Medium queries (4-10 words): Vector + Graph
# Complex queries (10+ words, multiple entities): Full 4-way + Reranking
```

### 7.2 Batch Processing Optimization

```bash
# For high-volume ingestion:
BATCH_SIZE=32              # Process 32 documents in parallel
PREFETCH_FACTOR=4          # Prefetch 4 batches ahead
NUM_WORKERS=8              # Use 8 parallel workers

# Monitor batch throughput
curl http://localhost:8000/api/v1/admin/metrics | jq '.batch_throughput'
```

### 7.3 Early Termination

```bash
# Stop expensive operations early if possible
ENABLE_EARLY_TERMINATION=true
EARLY_TERMINATION_THRESHOLD=0.95  # Stop at 95% confidence

# Example: Stop reranking after top 10 results if score gap large
```

### 7.4 Result Deduplication

```bash
# Deduplicate results across retrieval methods
ENABLE_RESULT_DEDUPLICATION=true
DEDUPLICATION_THRESHOLD=0.85  # 85% similar = duplicates

# Reduces processing time by eliminating redundant results
```

---

## 8. Performance Targets and SLOs

### 8.1 Query Latency Targets

**Sprint 68 Baseline:**

| Query Type | Target | Baseline | Status |
|------------|--------|----------|--------|
| Simple Vector | <200ms | 108ms | ✅ PASS |
| Hybrid (cache hit) | <100ms | 52ms | ✅ PASS |
| Hybrid (cache miss) | <500ms | 612ms | ⚠️ CLOSE |
| Complex Multi-hop | <1000ms | 950ms | ✅ PASS |
| P95 Latency | <500ms | 612ms (no cache) | ⚠️ Target |

### 8.2 Throughput Targets

```bash
# Current capabilities
- Sustained throughput: 50 QPS (queries per second)
- Peak throughput: 100 QPS (with caching)
- Concurrent users: 100+ (depends on query complexity)

# Monitor throughput
curl http://localhost:8000/api/v1/admin/metrics | jq '.throughput_qps'
```

### 8.3 Memory Targets

```bash
# Sprint 68 memory budgets (DGX Spark 128GB)
API:      <2GB (down from 3GB)
Qdrant:   8GB
Neo4j:    8GB
Redis:    8GB
Ollama:   64GB (multi-model)
System:   40GB reserve

Total: 128GB (fits within DGX Spark)
```

---

## 9. Monitoring and Alerting

### 9.1 Key Metrics to Monitor

```bash
# Check metrics dashboard
curl http://localhost:8000/api/v1/admin/metrics | jq '.'

# Critical metrics:
# 1. API latency p95 (target: <500ms)
# 2. Cache hit rate (target: >50%)
# 3. Memory usage (target: <8GB per service)
# 4. Error rate (target: <0.1%)
# 5. Throughput (target: >50 QPS)
```

### 9.2 Set Up Alerts

```bash
# If using Prometheus + Grafana:

# Alert 1: High latency
ALERT HighAPILatency
  IF histogram_quantile(0.95, api_latency_ms) > 500
  FOR 5m
  THEN send_alert("API latency >500ms")

# Alert 2: Low cache hit rate
ALERT LowCacheHitRate
  IF cache_hit_rate < 0.5
  FOR 10m
  THEN send_alert("Cache hit rate dropped")

# Alert 3: High memory usage
ALERT HighMemoryUsage
  IF container_memory_usage_bytes / container_memory_limit_bytes > 0.8
  FOR 5m
  THEN send_alert("Container memory >80%")
```

### 9.3 Performance Dashboard

Create a Grafana dashboard with:

```
Row 1: Query Latency
├─ P50, P95, P99 latency
├─ Cache hit rate
└─ Latency by stage (retrieval, generation, etc.)

Row 2: Resource Usage
├─ CPU usage (%)
├─ Memory usage (GB)
├─ Disk I/O (MB/s)
└─ Network I/O (MB/s)

Row 3: Throughput
├─ Queries per second
├─ Cache hits per second
└─ Errors per second

Row 4: Database Performance
├─ Qdrant points
├─ Neo4j entities
├─ Redis memory
└─ Query execution time
```

---

## 10. Troubleshooting Performance Issues

### Issue: High Latency (>500ms)

**Diagnosis:**

```bash
# 1. Check cache hit rate
curl http://localhost:8000/api/v1/admin/cache/stats | jq '.cache_hit_rate'

# 2. Profile pipeline
python scripts/profile_pipeline.py --mode intensive

# 3. Check resource usage
docker stats
```

**Solutions:**

```bash
# If cache hit rate low:
# - Increase cache TTL
# - Increase cache size
# - Lower semantic similarity threshold

# If retrieval slow:
# - Check Qdrant indexes
# - Verify ef parameter (target: 64)
# - Check Neo4j indexes

# If generation slow:
# - Switch to faster model (Nemotron3 Nano)
# - Enable result deduplication
# - Reduce context size
```

### Issue: High Memory Usage

**Diagnosis:**

```bash
# Check each service
docker stats --no-stream

# If API high:
python scripts/profile_memory.py

# If Redis high:
docker exec aegis-redis redis-cli INFO memory
```

**Solutions:**

```bash
# API memory high:
# - Enable streaming for PDFs
# - Reduce batch size
# - Clear embedding cache

# Redis memory high:
# - Reduce cache TTL
# - Increase eviction aggressiveness
# - Reduce cache size limit

# Qdrant memory high:
# - Verify index size
# - Check for duplicate points
```

---

## 11. Performance Checklist

- [ ] Query cache enabled with >50% hit rate
- [ ] Query latency P95 <500ms (or target)
- [ ] Memory usage <8GB per service
- [ ] Throughput >50 QPS sustained
- [ ] Error rate <0.1%
- [ ] Neo4j indexes created
- [ ] Qdrant HNSW optimized (ef=64)
- [ ] Redis memory limited (8GB)
- [ ] PDF ingestion streaming enabled
- [ ] Embedding cache working (>80% hit rate)
- [ ] Section communities enabled
- [ ] Monitoring/alerts configured
- [ ] Baseline performance documented

---

## Related Documentation

- [Deployment Guide](../deployment/SPRINT_68_DEPLOYMENT.md) - How to deploy
- [Troubleshooting Guide](../guides/TROUBLESHOOTING.md) - Common issues
- [Sprint 68 Summary](../sprints/SPRINT_68_SUMMARY.md) - Feature details
- [Profiling Scripts README](../../scripts/README_PROFILING.md) - Script usage

---

**Performance Tuning Complete!**

Start with the deployment baseline, then apply tuning strategies based on your specific workload monitoring.

---

**Author:** Documentation Agent (Claude)
**Date:** 2026-01-01
**Version:** 1.0
