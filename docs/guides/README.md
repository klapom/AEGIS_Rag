# AegisRAG Guides

Comprehensive guides for deploying, tuning, and troubleshooting AegisRAG.

---

## Available Guides

### 1. [Sprint 68 Deployment Guide](../deployment/SPRINT_68_DEPLOYMENT.md)

**Purpose:** Step-by-step instructions for deploying Sprint 68 to production

**For:** DevOps engineers, deployment teams, infrastructure managers

**Contents:**
- Prerequisites and environment setup
- Docker image rebuild procedure (10 steps)
- Redis configuration (8GB limit, LRU eviction)
- Database index creation (Neo4j, Qdrant)
- Full service startup and health checks
- Memory consolidation cron job setup
- Query cache verification
- Production deployment checklist
- Troubleshooting and rollback procedures

**Time Required:** 30-45 minutes for full deployment

**Quick Start:** Go to [Step 1: Docker Image Rebuild](../deployment/SPRINT_68_DEPLOYMENT.md#step-1-docker-image-rebuild)

---

### 2. [Performance Tuning Guide](PERFORMANCE_TUNING.md)

**Purpose:** Strategies for optimizing AegisRAG performance

**For:** Operations engineers, performance analysts, infrastructure teams

**Contents:**
- Query caching optimization (two-tier strategy)
- Model selection tuning strategies
- Memory budget optimization per service
- Database tuning (Neo4j, Qdrant, Redis)
- Profiling and benchmarking workflows
- Section community detection tuning
- Advanced optimization strategies
- Performance targets and SLOs
- Monitoring and alerting setup
- Performance troubleshooting

**Performance Baselines:**
- Cache hit latency: **52ms** (93% faster)
- Vector search: **40% faster** (ef=64)
- PDF memory: **75% reduction**
- Expected cache hit rate: **>50%**

**Quick Start:** Go to [Section 1: Query Caching Optimization](PERFORMANCE_TUNING.md#1-query-caching-optimization)

---

### 3. [Troubleshooting Guide](TROUBLESHOOTING.md)

**Purpose:** Solutions for common issues and problems

**For:** Support teams, operators, developers, QA engineers

**Contents:**
- 15+ common issues organized by category
- Each issue: Symptoms, Root Causes, Diagnosis, Solutions, Prevention
- Categories:
  1. E2E Test Failures (3 issues)
  2. Memory and Performance (2 issues)
  3. Database Connectivity (3 issues)
  4. API and Service Issues (2 issues)
  5. Permission and Configuration (2 issues)
  6. LLM and Ollama (2 issues)
  7. Frontend Issues (1 issue)

**Quick Start:** Go to [Category 1: E2E Test Failures](TROUBLESHOOTING.md#category-1-e2e-test-failures) or use the [Quick Troubleshooting Checklist](TROUBLESHOOTING.md#quick-troubleshooting-checklist)

---

## Quick Navigation

### By Role

**DevOps / Deployment Engineers:**
1. Start with [Deployment Guide](../deployment/SPRINT_68_DEPLOYMENT.md)
2. Use [Performance Tuning](PERFORMANCE_TUNING.md) for post-deployment optimization
3. Reference [Troubleshooting](TROUBLESHOOTING.md) for issues during deployment

**Operations / SRE:**
1. Use [Troubleshooting Guide](TROUBLESHOOTING.md) for incident response
2. Configure monitoring from [Performance Tuning](PERFORMANCE_TUNING.md#9-monitoring-and-alerting)
3. Schedule maintenance from [Deployment Guide](../deployment/SPRINT_68_DEPLOYMENT.md#step-5-memory-consolidation-cron-job)

**Developers:**
1. Review [Performance Tuning](PERFORMANCE_TUNING.md) for optimization ideas
2. Check [Troubleshooting](TROUBLESHOOTING.md) for debugging tips
3. Reference [Deployment Guide](../deployment/SPRINT_68_DEPLOYMENT.md) for environment setup

**QA / Testing:**
1. Review [Troubleshooting Category 1](TROUBLESHOOTING.md#category-1-e2e-test-failures) for E2E test fixes
2. Use performance baseline from [Performance Guide](PERFORMANCE_TUNING.md#81-query-latency-targets)

### By Task

**Deploying to Production:**
1. [Deployment Guide](../deployment/SPRINT_68_DEPLOYMENT.md) - Complete procedure
2. [Deployment Checklist](../deployment/SPRINT_68_DEPLOYMENT.md#step-8-production-deployment-checklist)

**Fixing Performance Issues:**
1. [Troubleshooting: Query Latency](TROUBLESHOOTING.md#issue-22-query-latency-degradation)
2. [Performance Tuning: Query Caching](PERFORMANCE_TUNING.md#1-query-caching-optimization)
3. [Performance Tuning: Database Tuning](PERFORMANCE_TUNING.md#4-database-tuning)

**Fixing Database Issues:**
1. [Troubleshooting: Qdrant Connection](TROUBLESHOOTING.md#issue-31-qdrant-connection-failures)
2. [Troubleshooting: Neo4j Connection](TROUBLESHOOTING.md#issue-32-neo4j-connection-failures)
3. [Troubleshooting: Redis Connection](TROUBLESHOOTING.md#issue-33-redis-connection-failures)

**Fixing Memory Issues:**
1. [Troubleshooting: Memory Leaks](TROUBLESHOOTING.md#issue-21-memory-leaks-during-pdf-ingestion)
2. [Performance Tuning: Memory Budget](PERFORMANCE_TUNING.md#3-memory-budget-optimization)
3. [Deployment: Redis Configuration](../deployment/SPRINT_68_DEPLOYMENT.md#step-2-redis-configuration)

**Fixing E2E Test Failures:**
1. [Troubleshooting: E2E Timeouts](TROUBLESHOOTING.md#issue-11-e2e-tests-timing-out)
2. [Troubleshooting: Selector Errors](TROUBLESHOOTING.md#issue-12-selector-not-found-errors)
3. [Troubleshooting: Memory/Domain Tests](TROUBLESHOOTING.md#issue-13-memorydomain-training-test-failures)

**Monitoring and Alerting:**
1. [Performance Tuning: Monitoring Section](PERFORMANCE_TUNING.md#9-monitoring-and-alerting)
2. [Deployment: Post-Deployment Operations](../deployment/SPRINT_68_DEPLOYMENT.md#step-10-post-deployment-operations)

---

## Key Concepts

### Two-Tier Query Caching

```
User Query
    ↓
[Exact Cache] ← 52ms (if match)
    ↓
[Semantic Cache] ← 100ms (if similar)
    ↓
[Full Retrieval] ← 612ms (if no match)
```

**Result:** 93% latency reduction for common queries, >50% cache hit rate

### Sprint 68 Performance Improvements

| Component | Improvement | Baseline | Target |
|-----------|-------------|----------|--------|
| Query latency (cache hit) | 93% faster | 680ms | 52ms |
| Query latency (cache miss) | 11% faster | 680ms | 612ms |
| Vector search | 40% faster | - | - |
| PDF memory | 75% reduction | 2GB+ | <500MB |
| Graph queries | 30-50% faster | - | - |

---

## Configuration Examples

### Enable Query Caching

```bash
# Edit .env
ENABLE_QUERY_CACHE=true
QUERY_CACHE_TTL=3600          # 1 hour (default)
```

### Configure Redis Memory

```bash
# .env
REDIS_MAX_MEMORY=8589934592   # 8GB hard limit
REDIS_EVICTION_POLICY=allkeys-lru
```

### Optimize Vector Search

```bash
python scripts/optimize_qdrant_params.py \
    --collection documents \
    --ef 64                    # 40% faster than 128
```

### Create Database Indexes

```bash
python scripts/optimize_neo4j_indexes.py   # Neo4j indexes
python scripts/optimize_qdrant_params.py   # Qdrant indexes
```

---

## Common Commands

### Health Check
```bash
curl http://localhost:8000/health
```

### Cache Statistics
```bash
curl http://localhost:8000/api/v1/admin/cache/stats
```

### Performance Metrics
```bash
curl http://localhost:8000/api/v1/admin/metrics
```

### Benchmark Query Latency
```bash
python scripts/benchmark_query_latency.py --iterations 30
```

### View Logs
```bash
docker compose logs -f api          # API logs
docker compose logs -f qdrant       # Vector DB logs
docker compose logs -f neo4j        # Graph DB logs
```

---

## Performance Targets (Sprint 68)

**Latency Targets:**
- Simple Query (Vector only): <200ms ✅
- Hybrid Query (cached): <100ms ✅
- Hybrid Query (no cache): <500ms ⚠️
- Complex Multi-hop: <1000ms ✅

**Throughput:**
- Sustained: 50 QPS ✅
- Peak: 100 QPS (with caching) ✅

**Memory:**
- API: <2GB ✅
- Qdrant: 8GB ✅
- Neo4j: 8GB ✅
- Redis: 8GB (hard limit) ✅

---

## Troubleshooting Quick Links

**E2E Tests:**
- [Timeouts](TROUBLESHOOTING.md#issue-11-e2e-tests-timing-out)
- [Selector errors](TROUBLESHOOTING.md#issue-12-selector-not-found-errors)
- [Memory test failures](TROUBLESHOOTING.md#issue-13-memorydomain-training-test-failures)

**Performance:**
- [Slow queries](TROUBLESHOOTING.md#issue-22-query-latency-degradation)
- [Memory leaks](TROUBLESHOOTING.md#issue-21-memory-leaks-during-pdf-ingestion)

**Database:**
- [Qdrant failures](TROUBLESHOOTING.md#issue-31-qdrant-connection-failures)
- [Neo4j failures](TROUBLESHOOTING.md#issue-32-neo4j-connection-failures)
- [Redis failures](TROUBLESHOOTING.md#issue-33-redis-connection-failures)

**API & Services:**
- [API not responding](TROUBLESHOOTING.md#issue-41-api-health-check-fails)
- [500 errors](TROUBLESHOOTING.md#issue-42-500-internal-server-errors)

**Configuration:**
- [Permission errors](TROUBLESHOOTING.md#issue-51-permission-denied-errors)
- [Missing variables](TROUBLESHOOTING.md#issue-52-missing-environment-variables)

---

## Additional Resources

**Related Documentation:**
- [Sprint 68 Summary](../sprints/SPRINT_68_SUMMARY.md) - Complete feature overview
- [CLAUDE.md](../../CLAUDE.md) - Project context and standards
- [TECH_STACK.md](../TECH_STACK.md) - Technology details
- [ADR Index](../adr/ADR_INDEX.md) - Architecture decisions

**External Resources:**
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [Docker Documentation](https://docs.docker.com/)

---

## How to Use These Guides

### For Your First Deployment
1. Read [Deployment Guide Introduction](../deployment/SPRINT_68_DEPLOYMENT.md#overview)
2. Follow steps 1-10 sequentially
3. Use [verification checklist](../deployment/SPRINT_68_DEPLOYMENT.md#step-7-verification-steps)
4. Bookmark [Troubleshooting Guide](TROUBLESHOOTING.md) for reference

### For Performance Optimization
1. Establish performance baseline (see [Performance Guide Section 5](PERFORMANCE_TUNING.md#5-profiling-and-benchmarking))
2. Identify bottleneck using profiling
3. Apply tuning from relevant section
4. Benchmark improvement
5. Monitor with metrics in [Section 9](PERFORMANCE_TUNING.md#9-monitoring-and-alerting)

### For Incident Response
1. Consult [Troubleshooting Checklist](TROUBLESHOOTING.md#quick-troubleshooting-checklist)
2. Find relevant issue category
3. Follow diagnosis and solution steps
4. Escalate if solution doesn't work

---

## Feedback and Updates

These guides are living documents based on Sprint 68 learnings. As you encounter new issues or optimizations:

1. Document your solution
2. Test thoroughly
3. Add to appropriate guide
4. Update this README

---

**Last Updated:** 2026-01-01
**Status:** Complete and production-ready
**Version:** 1.0

---

**Start here:** [Sprint 68 Deployment Guide](../deployment/SPRINT_68_DEPLOYMENT.md)
