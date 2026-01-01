# Sprint 68 Deployment Guide

**Last Updated:** 2026-01-01
**Status:** Production Ready
**Target Platform:** DGX Spark (NVIDIA Blackwell GB10, CUDA 13.0, ARM64)

---

## Overview

This guide provides step-by-step instructions for deploying Sprint 68 features (Performance Optimization, Memory Management, Query Caching, Section Communities) to production. Sprint 68 introduced significant performance improvements:

- **75% reduction** in PDF ingestion memory consumption
- **93% reduction** in query latency for cached queries (680ms → 50ms)
- **40% faster** vector search (HNSW parameter optimization)
- **Two-tier query caching** (exact + semantic)
- **Section community detection** for improved graph reasoning

---

## Prerequisites

### System Requirements

- **OS:** Linux (preferably Ubuntu 22.04 LTS)
- **Docker:** 24.0+ with Docker Compose 2.20+
- **GPU:** NVIDIA A100+ with 80GB+ VRAM (or DGX Spark)
- **Storage:** 200GB+ free space (vector index + graph DB + cache)
- **Memory:** 64GB+ RAM minimum (128GB recommended)

### Environment Setup

```bash
# 1. Clone/pull repository
cd /home/admin/projects/aegisrag/AEGIS_Rag
git pull origin main

# 2. Create/update .env file
cp .env.template .env
nano .env  # Edit with your configuration
```

### Required Environment Variables

```bash
# Ollama (Primary LLM)
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL_GENERATION=nemotron-no-think

# Database Connections
QDRANT_HOST=qdrant
QDRANT_PORT=6333
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure_password>
REDIS_HOST=redis
REDIS_PORT=6379

# LLM Proxy (Multi-cloud routing)
ALIBABA_CLOUD_API_KEY=<your_api_key>
MONTHLY_BUDGET_ALIBABA_CLOUD=10.0

# Memory Configuration (Sprint 68)
REDIS_MAX_MEMORY=8GB
REDIS_EVICTION_POLICY=allkeys-lru

# Query Caching (Sprint 68)
ENABLE_QUERY_CACHE=true
QUERY_CACHE_TTL=3600

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<secure_password>
```

---

## Step 1: Docker Image Rebuild

All Docker images must be rebuilt to include Sprint 68 changes. This is critical for:
- Memory optimization code
- Query caching implementation
- Section community detection
- Permission fixes

### 1.1 Build Process

```bash
# Navigate to project root
cd /home/admin/projects/aegisrag/AEGIS_Rag

# Build API container (includes backend code)
docker compose -f docker-compose.dgx-spark.yml build --no-cache api

# Build CUDA-optimized variant
docker compose -f docker-compose.dgx-spark.yml build --no-cache api-cuda

# Build Test container
docker compose -f docker-compose.dgx-spark.yml build --no-cache test

# Optional: Build Docling container (only if changing ingestion code)
docker compose -f docker-compose.dgx-spark.yml build --no-cache docling
```

**Expected Duration:** 15-30 minutes per image (depending on hardware)

### 1.2 Verify Images

```bash
# Check image creation timestamps (should be recent)
docker images aegis-rag-api --format "table {{.Repository}}\t{{.CreatedAt}}\t{{.Size}}"

# Example output:
# aegis-rag-api:latest    2026-01-01 10:30:00    1.5GB
```

---

## Step 2: Redis Configuration

Sprint 68 implements **hard memory limits** for Redis cache with LRU eviction policy.

### 2.1 Verify Configuration

```bash
# Check Redis maxmemory setting
docker compose -f docker-compose.dgx-spark.yml config | grep -A10 "redis:"

# Should show:
# maxmemory 8589934592    (8GB in bytes)
# maxmemory-policy allkeys-lru
```

### 2.2 Apply Redis Configuration

```bash
# Start Redis container
docker compose -f docker-compose.dgx-spark.yml up -d redis

# Wait for Redis to be ready
sleep 5

# Verify configuration in running container
docker exec aegis-redis redis-cli CONFIG GET maxmemory
# Expected: "8589934592"

docker exec aegis-redis redis-cli CONFIG GET maxmemory-policy
# Expected: "allkeys-lru"

# Test Redis connectivity
docker exec aegis-redis redis-cli ping
# Expected: "PONG"
```

### 2.3 Monitor Redis Memory

```bash
# Check current Redis memory usage
docker exec aegis-redis redis-cli INFO memory

# Example output:
# used_memory:2147483648 (2GB)
# used_memory_human:2G
# maxmemory:8589934592
# maxmemory_human:8G
# maxmemory_policy:allkeys-lru
```

**Note:** Redis will evict old entries (LRU) when approaching 8GB limit. This is normal and expected.

---

## Step 3: Database Index Creation

Sprint 68 optimizes database indexes for significantly faster queries.

### 3.1 Neo4j Indexes

Neo4j indexes speed up graph queries by 30-50%.

```bash
# Start Neo4j (if not already running)
docker compose -f docker-compose.dgx-spark.yml up -d neo4j

# Wait for Neo4j to be ready (60+ seconds)
sleep 60

# Create indexes
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/optimize_neo4j_indexes.py

# You should see output like:
# Creating index on Entity.entity_id...
# Creating index on Relation.relation_id...
# Index creation completed in 2.34s
```

**What it creates:**

```cypher
CREATE INDEX entity_id_idx FOR (e:Entity) ON (e.entity_id);
CREATE INDEX relation_id_idx FOR (r:Relation) ON (r.relation_id);
CREATE INDEX community_id_idx FOR (c:Community) ON (c.community_id);
CREATE INDEX section_id_idx FOR (s:Section) ON (s.section_id);
```

### 3.2 Qdrant Vector Indexes

Qdrant HNSW parameter optimization for 40% faster vector search.

```bash
# Start Qdrant (if not already running)
docker compose -f docker-compose.dgx-spark.yml up -d qdrant

# Wait for Qdrant to be ready
sleep 10

# Optimize HNSW parameters
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/optimize_qdrant_params.py \
    --collection documents \
    --ef 64

# You should see output like:
# Optimizing HNSW parameters for collection: documents
# Setting ef: 64 (was 128)
# Setting ef_construction: 200
# Optimization completed: ~0.5s
```

**Parameter Changes:**

| Parameter | Before | After | Impact |
|-----------|--------|-------|--------|
| ef | 128 | 64 | 40% faster search |
| ef_construction | 200 | 200 | No change |
| m | 16 | 16 | No change |

### 3.3 Verify Indexes

```bash
# Neo4j: List indexes
docker exec aegis-neo4j cypher-shell \
    -u neo4j -p <password> \
    "SHOW INDEXES" | head -20

# Qdrant: List collections
curl http://localhost:6333/collections | jq '.result[].name'
# Expected: "documents"
```

---

## Step 4: Start All Services

Now start the complete AegisRAG stack with all Sprint 68 optimizations.

### 4.1 Full Stack Startup

```bash
# Start all services
docker compose -f docker-compose.dgx-spark.yml up -d

# Wait for services to stabilize (60 seconds)
sleep 60

# Check service status
docker compose -f docker-compose.dgx-spark.yml ps

# Expected output (all healthy):
# CONTAINER ID  IMAGE                    STATUS
# <id>          aegis-qdrant             Up 2 minutes (healthy)
# <id>          aegis-neo4j              Up 2 minutes (healthy)
# <id>          aegis-redis              Up 2 minutes (healthy)
# <id>          aegis-ollama             Up 2 minutes (healthy)
# <id>          aegis-api                Up 1 minute  (healthy)
# <id>          aegis-frontend           Up 1 minute  (running)
```

### 4.2 Health Check

```bash
# Check API health endpoint
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "services": {
#     "qdrant": "ok",
#     "neo4j": "ok",
#     "redis": "ok",
#     "ollama": "ok"
#   },
#   "cache": {
#     "enabled": true,
#     "memory_usage_mb": 128
#   }
# }
```

### 4.3 Service Endpoints

After successful startup:

```
Backend API:  http://localhost:8000
Frontend:     http://localhost:5179
Qdrant UI:    http://localhost:6333/dashboard
Neo4j Browser: http://localhost:7474
Prometheus:   http://localhost:9090
Redis CLI:    docker exec aegis-redis redis-cli
```

---

## Step 5: Memory Consolidation Cron Job

Sprint 68 includes automated **memory consolidation** for Graphiti (temporal memory system).

### 5.1 Schedule Weekly Consolidation

```bash
# Edit crontab
crontab -e

# Add the following line (runs every Sunday at 2:00 AM)
0 2 * * 0 cd /home/admin/projects/aegisrag/AEGIS_Rag && poetry run python scripts/consolidate_graphiti_memory.py

# Save with Ctrl+O, Enter, Ctrl+X
```

### 5.2 Manual Consolidation

```bash
# Consolidate memory manually anytime
cd /home/admin/projects/aegisrag/AEGIS_Rag
poetry run python scripts/consolidate_graphiti_memory.py

# Expected output:
# Memory consolidation started...
# Consolidating 2,345 memory items...
# Merged 234 related facts
# Pruned 89 expired items
# Freed 120MB
# Consolidation completed in 45.2s
```

### 5.3 Consolidation Details

The consolidation script:
1. **Identifies related facts** - Groups facts by topic/entities
2. **Merges duplicates** - Combines similar information
3. **Removes expired items** - Prunes facts older than 90 days with low importance
4. **Compresses storage** - Reduces Graphiti database size

**What it consolidates:**

- Facts about the same entity (merged into composite fact)
- Redundant information (deduplication)
- Low-importance expired facts (based on decay score)
- Orphaned relationships

---

## Step 6: Query Caching Verification

Sprint 68 implements **two-tier query caching** for massive latency reduction.

### 6.1 Exact Cache Testing

```bash
# First query (cache miss)
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is hybrid search?",
    "top_k": 10
  }' | jq '.latency_ms'

# Expected: ~680ms (first time)

# Second query (exact match in cache)
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is hybrid search?",
    "top_k": 10
  }' | jq '.latency_ms'

# Expected: ~50ms (93% faster!)
```

### 6.2 Monitor Cache Performance

```bash
# Get cache statistics
curl http://localhost:8000/api/v1/admin/cache/stats | jq '.'

# Expected response:
# {
#   "total_requests": 1523,
#   "cache_hits": 876,
#   "cache_hit_rate": 0.575,
#   "avg_hit_latency_ms": 52,
#   "avg_miss_latency_ms": 612,
#   "cache_size_mb": 256
# }
```

### 6.3 Cache Configuration

```bash
# Check cache configuration
cat /home/admin/projects/aegisrag/AEGIS_Rag/.env | grep -i cache

# To adjust cache behavior, edit .env:
QUERY_CACHE_TTL=3600              # Cache validity (seconds)
QUERY_CACHE_MAX_SIZE=512000000    # Max cache size (bytes)
ENABLE_SEMANTIC_CACHE=true        # Semantic caching
SEMANTIC_CACHE_THRESHOLD=0.95     # Similarity threshold for semantic matches
```

---

## Step 7: Verification Steps

Complete these steps to ensure Sprint 68 is deployed correctly.

### 7.1 Database Verification

```bash
# Check Qdrant points (vector embeddings)
curl http://localhost:6333/collections/documents/points/count | jq '.result.count'
# Should show >1000 (depends on your indexed documents)

# Check Neo4j entities
docker exec aegis-neo4j cypher-shell \
    -u neo4j -p <password> \
    "MATCH (e:Entity) RETURN count(e)" | tail -1
# Should show >500 (depends on your indexed documents)

# Check Redis cache size
docker exec aegis-redis redis-cli INFO memory | grep used_memory_human
# Should show <8GB
```

### 7.2 Performance Verification

```bash
# Run performance benchmark
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/benchmark_query_latency.py \
    --iterations 20 \
    --warmup 5

# Expected output:
# Benchmark Results:
# Cache hit latency: 52ms (p95)
# Cache miss latency: 612ms (p95)
# Cache hit rate: 57.5%
# Speedup (cache): 11.8x
```

### 7.3 Memory Verification

```bash
# Check API container memory usage
docker stats aegis-api --no-stream | tail -1
# Should show <2GB (down from 3GB+ before Sprint 68)

# Check Ollama memory usage
docker stats aegis-ollama --no-stream | tail -1
# Should show 15-20GB (varies with loaded models)

# Check Redis memory
docker exec aegis-redis redis-cli INFO memory | grep used_memory_human
# Should show 1-3GB under normal load
```

### 7.4 Section Community Detection

```bash
# Test section community detection
curl -X POST http://localhost:8000/api/v1/graph/community_search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication patterns",
    "top_k": 5
  }' | jq '.results | length'

# Should return 5 sections from related communities
```

---

## Step 8: Production Deployment Checklist

Before going live, complete this checklist:

- [ ] All Docker images rebuilt and tagged (image timestamps recent)
- [ ] Redis configuration verified (8GB limit, allkeys-lru policy)
- [ ] Neo4j indexes created (`optimize_neo4j_indexes.py` ran successfully)
- [ ] Qdrant HNSW parameters optimized (`optimize_qdrant_params.py` ran successfully)
- [ ] All services healthy (`docker compose ps` shows all healthy)
- [ ] API health endpoint returns 200 OK
- [ ] Query caching working (cache hit latency < 100ms)
- [ ] Memory consolidation cron job scheduled
- [ ] Performance benchmarks meet targets (see Step 7.2)
- [ ] No critical errors in Docker logs
- [ ] Database backups created (optional but recommended)

---

## Step 9: Troubleshooting

### Issue: "Service fails to start"

**Symptoms:** Container exits immediately, Docker compose shows errors

**Solution:**

```bash
# Check container logs
docker logs aegis-api

# If permission errors:
docker exec aegis-api ls -la /app/data/lightrag/
# Should show: drwxr-xr-x  2 aegis aegis

# If permissions wrong:
docker exec -u root aegis-api chown -R aegis:aegis /app/data
```

### Issue: "Queries still slow (>500ms)"

**Symptoms:** Query latency hasn't improved despite optimization

**Solution:**

```bash
# Check if caching is enabled
curl http://localhost:8000/api/v1/admin/cache/stats | jq '.total_requests'

# If cache_hits = 0:
# 1. Run same query twice to populate cache
# 2. Check ENABLE_QUERY_CACHE in .env (should be true)

# 2. Verify HNSW optimization
curl http://localhost:6333/collections/documents | jq '.result.config.hnsw_config.ef'
# Should show 64 (not 128)
```

### Issue: "Redis evicting too much data"

**Symptoms:** Cache hit rate dropping over time

**Solution:**

```bash
# Check Redis eviction count
docker exec aegis-redis redis-cli INFO stats | grep evicted_keys
# If high: increase REDIS_MAX_MEMORY in .env

# Temporary workaround:
docker exec aegis-redis redis-cli FLUSHALL  # Clear cache
docker exec aegis-redis redis-cli CONFIG SET maxmemory 17179869184  # 16GB
```

### Issue: "Memory consolidation fails"

**Symptoms:** Cron job doesn't run or produces errors

**Solution:**

```bash
# Verify Python environment
which poetry
# Should show path to poetry

# Run consolidation manually to debug
cd /home/admin/projects/aegisrag/AEGIS_Rag
poetry run python scripts/consolidate_graphiti_memory.py -v

# If error: Check crontab job
crontab -l | grep consolidate
# Should show the scheduled job

# Fix crontab:
crontab -e
# Ensure full path: /usr/bin/poetry or /path/to/poetry
```

---

## Step 10: Post-Deployment Operations

### 10.1 Monitoring

Monitor these metrics daily:

```bash
# Check cache hit rate (should be >50%)
curl http://localhost:8000/api/v1/admin/cache/stats | jq '.cache_hit_rate'

# Check memory usage (should be <8GB)
docker exec aegis-redis redis-cli INFO memory | grep used_memory_human

# Check API response time (should be <200ms avg)
curl http://localhost:8000/api/v1/admin/metrics | jq '.api_latency_p95_ms'
```

### 10.2 Regular Backups

```bash
# Backup Qdrant vectors
docker exec aegis-qdrant tar czf /tmp/qdrant_backup.tar.gz /qdrant/storage/collections/

# Backup Neo4j graph
docker exec aegis-neo4j /var/lib/neo4j/bin/neo4j-admin dump --database=neo4j --to=/tmp/neo4j_backup.dump

# Copy to external storage
cp /tmp/qdrant_backup.tar.gz /backup/location/
cp /tmp/neo4j_backup.dump /backup/location/
```

### 10.3 Version Tracking

Document your deployment:

```bash
# Create deployment record
cat > /home/admin/projects/aegisrag/AEGIS_Rag/DEPLOYMENT_RECORD_SPRINT_68.txt <<EOF
Deployment Date: 2026-01-01
Sprint: 68
Deployed By: [Your Name]
Environment: Production (DGX Spark)

Key Components:
- Docker images: aegis-rag-api:latest (built 2026-01-01 10:30)
- Redis maxmemory: 8GB with allkeys-lru
- Neo4j indexes: Created
- Qdrant HNSW ef: 64
- Query caching: Enabled with 3600s TTL

Baseline Performance:
- Cache hit latency: 52ms
- Cache miss latency: 612ms
- Vector search: ~40% faster
- PDF ingestion: 75% less memory

Next Steps:
- Monitor cache hit rate (target >50%)
- Schedule weekly memory consolidation
- Review metrics in Prometheus/Grafana weekly
EOF

cat /home/admin/projects/aegisrag/AEGIS_Rag/DEPLOYMENT_RECORD_SPRINT_68.txt
```

---

## Rollback Procedure

If issues arise, rollback to previous Sprint 67 deployment:

```bash
# 1. Stop current services
docker compose -f docker-compose.dgx-spark.yml down

# 2. Restore previous images
docker images | grep aegis-rag-api
# Identify Sprint 67 image (created date)
docker tag <sprint67_image_id> aegis-rag-api:latest

# 3. Restart services
docker compose -f docker-compose.dgx-spark.yml up -d

# 4. Verify rollback
docker compose -f docker-compose.dgx-spark.yml ps
```

---

## Related Documentation

- [Performance Tuning Guide](../guides/PERFORMANCE_TUNING.md) - Advanced optimization
- [Troubleshooting Guide](../guides/TROUBLESHOOTING.md) - Common issues and solutions
- [Sprint 68 Summary](../sprints/SPRINT_68_SUMMARY.md) - Feature details
- [CLAUDE.md](../../CLAUDE.md) - Project context

---

## Support

For deployment issues:

1. Check Docker logs: `docker compose logs -f api`
2. Verify services: `docker compose ps`
3. Test connectivity: `curl http://localhost:8000/health`
4. Review [Troubleshooting Guide](../guides/TROUBLESHOOTING.md)

---

**Deployment Status:** PRODUCTION READY

Sprint 68 brings major performance improvements with zero breaking changes. All optimizations are backward compatible and can be deployed safely to production.

**Estimated Deployment Time:** 30-45 minutes

---

**Author:** Documentation Agent (Claude)
**Date:** 2026-01-01
**Version:** 1.0
