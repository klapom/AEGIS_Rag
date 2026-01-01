# AegisRAG Troubleshooting Guide

**Last Updated:** 2026-01-01
**Status:** Sprint 68 Complete
**Common Issues:** 15+ scenarios with solutions

---

## Overview

This guide provides solutions for common problems encountered when running AegisRAG. Each issue includes:

1. **Symptoms** - How to identify the problem
2. **Root Causes** - Why it happens
3. **Diagnosis** - How to confirm the issue
4. **Solutions** - Step-by-step fixes
5. **Prevention** - How to avoid in future

---

## Category 1: E2E Test Failures

### Issue 1.1: E2E Tests Timing Out

**Symptoms:**
- Tests fail after 300-600 seconds
- Error: `TimeoutError: timeout waiting for...`
- Specific flaky tests (follow-ups, domain training)

**Root Causes:**
- Async operations not completing in time
- Race conditions in state management
- Slow LLM responses

**Diagnosis:**

```bash
# Run specific failing test with verbose output
poetry run pytest frontend/e2e/admin/test_follow_up_questions.py -vv -s

# Check test logs
docker compose logs -f | grep "ERROR\|TIMEOUT"

# Monitor during test
docker stats aegis-api --no-stream
docker stats aegis-ollama --no-stream
```

**Solutions:**

#### Solution 1: Increase Timeouts

```bash
# Edit test file
# frontend/e2e/admin/test_follow_up_questions.py

# Find: await page.locator("...").click(timeout=5000)
# Change to:
await page.locator("...").click(timeout=10000)  # 10 seconds

# Or globally in playwright.config.ts:
timeout: 30000,  // 30 seconds global timeout
navigationTimeout: 30000,
```

#### Solution 2: Add Wait Conditions

```python
# Before clicking element, wait for element to be ready
await page.wait_for_selector("[data-test='submit-button']")
await page.locator("[data-test='submit-button']").click()

# Or use explicit waits
from playwright.async_api import expect
await expect(page.locator("[data-test='response']")).to_be_visible(timeout=10000)
```

#### Solution 3: Add Retries

```python
# Wrap flaky operations in retry loop
import asyncio

async def click_with_retry(page, selector, max_retries=3):
    for attempt in range(max_retries):
        try:
            await page.locator(selector).click()
            return
        except TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            else:
                raise

# Usage:
await click_with_retry(page, "[data-test='submit-button']")
```

#### Solution 4: Check LLM Response Times

```bash
# Monitor Ollama response time during tests
curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"nemotron-no-think","prompt":"test","stream":false}' | jq '.eval_duration'

# If >3000ms (3 seconds):
# 1. Reduce context window: OLLAMA_NUM_CTX=4096 (was 8192)
# 2. Reduce model parameters: Use smaller model
# 3. Increase system memory
```

### Issue 1.2: Selector Not Found Errors

**Symptoms:**
- Error: `Locator.click: Target closed`
- Error: `Selector [data-test="..."] not found`
- Tests fail inconsistently (flaky)

**Root Causes:**
- Test selectors changed in frontend code
- DOM not fully loaded when test runs
- Dynamic class names (generated IDs)

**Diagnosis:**

```bash
# Check if selector exists in frontend
grep -r "data-test=\"submit-button\"" frontend/

# Take screenshot at failure point
# (add to test before assertion)
await page.screenshot(path="/tmp/failure.png")

# Check frontend code generation
grep -r "className=" frontend/src/ | grep -E "uuid|random|dynamic"
```

**Solutions:**

#### Solution 1: Update Selectors

```bash
# Review frontend test ID mapping
cat frontend/e2e/admin/TEST_ID_MAPPING.md

# Update selectors in test to match current frontend
# frontend/e2e/admin/test_example.py

# WRONG:
await page.locator('button:has-text("Submit")').click()

# RIGHT:
await page.locator('[data-test="admin-submit-button"]').click()
```

#### Solution 2: Use More Stable Selectors

```python
# AVOID: brittle selectors
await page.locator('.btn.btn-primary').click()
await page.locator('button:nth-of-type(3)').click()

# USE: explicit data-test attributes
await page.locator('[data-test="submit"]').click()

# OR: visible text with role
await page.get_by_role("button", name="Submit").click()

# OR: label association (for forms)
await page.get_by_label("Email").fill("test@example.com")
```

#### Solution 3: Add Explicit Waits

```python
# Wait for element to be visible AND stable
from playwright.async_api import expect

async def click_stable(page, selector):
    """Click element after ensuring it's visible and stable"""
    locator = page.locator(selector)

    # Wait for visibility
    await expect(locator).to_be_visible()

    # Wait for element to be enabled (clickable)
    await locator.click(force=False)

# Usage:
await click_stable(page, '[data-test="submit"]')
```

### Issue 1.3: Memory/Domain Training Test Failures

**Symptoms:**
- Memory consolidation tests timeout
- Domain training returns empty results
- Conversation history not persisting

**Root Causes:**
- Redis cache not initialized
- Memory consolidation script timing out
- Graphiti service unavailable

**Diagnosis:**

```bash
# Check if Redis is running
docker exec aegis-redis redis-cli ping
# Expected: PONG

# Check if Graphiti tables exist
docker exec aegis-redis redis-cli KEYS "graphiti:*" | head -10

# Check memory consolidation availability
curl http://localhost:8000/api/v1/admin/memory/consolidation_status | jq '.'

# Check for timeout errors in logs
docker logs aegis-api | grep -i "consolidation\|timeout\|memory"
```

**Solutions:**

#### Solution 1: Ensure Redis is Available

```bash
# Restart Redis if needed
docker compose -f docker-compose.dgx-spark.yml restart redis

# Wait for Redis to be ready
sleep 10

# Verify it's running
docker exec aegis-redis redis-cli ping
# Expected: PONG
```

#### Solution 2: Clear Corrupted Data

```bash
# Backup current data
docker exec aegis-redis redis-cli --rdb /tmp/redis_backup.rdb

# Clear Graphiti tables
docker exec aegis-redis redis-cli FLUSHALL

# Or selectively clear:
docker exec aegis-redis redis-cli DEL graphiti:*
docker exec aegis-redis redis-cli DEL conversation:*
```

#### Solution 3: Increase Test Timeout for Memory Tests

```python
# In test file, mark slow tests
import pytest

@pytest.mark.slow
@pytest.mark.timeout(600)  # 10 minute timeout
async def test_memory_consolidation(page):
    # Test code here
    pass
```

---

## Category 2: Memory and Performance Issues

### Issue 2.1: Memory Leaks During PDF Ingestion

**Symptoms:**
- PDF ingestion causes high memory usage (>4GB)
- Memory not released after ingestion completes
- OOM (Out of Memory) errors
- API becomes unresponsive

**Root Causes:**
- Large PDFs not using streaming parser
- Embedding cache growing unbounded
- Garbage collection not running frequently enough
- PDF metadata cached in memory

**Diagnosis:**

```bash
# Monitor memory during ingestion
docker stats aegis-api --no-stream

# Profile memory usage
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/profile_memory.py \
    --iterations 5 \
    --output memory_profile.json

# Check for unreleased memory
python -c "
import json
with open('memory_profile.json') as f:
    data = json.load(f)
    print(f'API: {data[\"api\"][\"peak_mb\"]}MB peak')
    print(f'Released: {data[\"api\"][\"peak_mb\"] - data[\"api\"][\"avg_mb\"]}MB')
"

# Check for memory leaks in application
docker exec aegis-api ps aux | grep python | grep -v grep
# Note: high memory usage after process stabilizes = potential leak
```

**Solutions:**

#### Solution 1: Enable PDF Streaming (Sprint 68)

```bash
# Edit .env
PDF_STREAMING_ENABLED=true          # Parse PDFs in chunks
GC_INTERVAL_SECONDS=10              # Run GC every 10 seconds
GC_GENERATION_THRESHOLD=512         # GC after 512MB allocated

# Restart API
docker compose -f docker-compose.dgx-spark.yml restart api
```

#### Solution 2: Clear Embedding Cache

```bash
# If embedding cache growing unbounded
curl -X POST http://localhost:8000/api/v1/admin/cache/clear \
  -H "Content-Type: application/json" \
  -d '{"cache_type": "embedding"}'

# Or clear all caches
curl -X POST http://localhost:8000/api/v1/admin/cache/clear \
  -H "Content-Type: application/json" \
  -d '{"cache_type": "all"}'
```

#### Solution 3: Reduce Batch Size

```bash
# If ingesting many large PDFs:
BATCH_SIZE=4                        # Process fewer documents in parallel
PREFETCH_FACTOR=1                   # Prefetch fewer batches

# Restart services
docker compose -f docker-compose.dgx-spark.yml restart api
```

#### Solution 4: Force Garbage Collection

```bash
# Manually trigger GC during ingestion
curl -X POST http://localhost:8000/api/v1/admin/gc \
  -H "Content-Type: application/json" \
  -d '{"verbose": true}'

# Response:
# {
#   "freed_mb": 512,
#   "current_memory_mb": 2048,
#   "peak_memory_mb": 4096
# }
```

### Issue 2.2: Query Latency Degradation

**Symptoms:**
- Queries getting slower over time
- P95 latency increases from 500ms to 1000ms+
- Cache hit rate declining
- CPU usage high

**Root Causes:**
- Cache not working effectively
- Database indexes degraded (fragmented)
- Memory pressure causing slowdowns
- Too many concurrent queries

**Diagnosis:**

```bash
# Check cache performance
curl http://localhost:8000/api/v1/admin/cache/stats | jq '.cache_hit_rate'
# Should be >50%

# Check database performance
curl http://localhost:8000/api/v1/admin/metrics | jq '.latencies'

# Check system resources
docker stats --no-stream

# Check query profile
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/benchmark_query_latency.py \
    --iterations 20
```

**Solutions:**

#### Solution 1: Verify Cache is Working

```bash
# Same query twice - second should be faster
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 10}' | jq '.latency_ms'
# Note: latency_ms

# Run again
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 10}' | jq '.latency_ms'
# Should be much faster (50-100ms)

# If not faster, cache is disabled or not working
curl http://localhost:8000/api/v1/admin/config | jq '.cache_enabled'
```

#### Solution 2: Rebuild Database Indexes

```bash
# Neo4j
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/optimize_neo4j_indexes.py

# Qdrant (may take time)
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/optimize_qdrant_params.py \
    --collection documents \
    --ef 64
```

#### Solution 3: Restart Services

```bash
# Full restart
docker compose -f docker-compose.dgx-spark.yml restart

# Wait for services to stabilize
sleep 60

# Test again
python /home/admin/projects/aegisrag/AEGIS_Rag/scripts/benchmark_query_latency.py \
    --iterations 20
```

---

## Category 3: Database Connectivity Issues

### Issue 3.1: Qdrant Connection Failures

**Symptoms:**
- Error: `Failed to connect to Qdrant`
- Error: `ConnectionError: Cannot reach Qdrant server`
- Vector search not working
- Admin UI shows "Qdrant: offline"

**Root Causes:**
- Qdrant container not running
- Port 6333 not accessible
- Network issues
- Qdrant disk full

**Diagnosis:**

```bash
# Check if Qdrant is running
docker ps | grep qdrant
# Should show running container

# Check port is listening
lsof -i :6333
# Should show qdrant process

# Test connectivity
curl http://localhost:6333/health
# Should return healthy status

# Check disk space
docker exec aegis-qdrant df -h /qdrant
# Should have >20GB free
```

**Solutions:**

#### Solution 1: Start Qdrant

```bash
# If not running:
docker compose -f docker-compose.dgx-spark.yml up -d qdrant

# Wait for startup
sleep 10

# Verify health
curl http://localhost:6333/health
```

#### Solution 2: Check Network

```bash
# If connection still fails, check network
docker compose -f docker-compose.dgx-spark.yml exec api \
    curl http://qdrant:6333/health

# If fails, network issue (containers can't reach each other)
docker network ls
docker network inspect aegis-network | grep "Containers" -A 20
```

#### Solution 3: Clear Corrupted Data

```bash
# If Qdrant corrupted:
docker compose -f docker-compose.dgx-spark.yml stop qdrant

# Backup existing data
docker run --rm -v aegis_qdrant:/qdrant \
    ubuntu tar czf /tmp/qdrant_backup.tar.gz /qdrant

# Remove corrupted container
docker compose -f docker-compose.dgx-spark.yml rm -f qdrant

# Restart (will start fresh)
docker compose -f docker-compose.dgx-spark.yml up -d qdrant
```

### Issue 3.2: Neo4j Connection Failures

**Symptoms:**
- Error: `AuthError: Invalid credentials`
- Error: `Failed to connect to Neo4j`
- Graph search not working

**Root Causes:**
- Wrong password in .env
- Neo4j not running
- Port 7687 not accessible
- Authentication service down

**Diagnosis:**

```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Test connection with correct credentials
docker exec aegis-neo4j cypher-shell \
    -u neo4j -p <password> \
    "MATCH (n) RETURN count(n) LIMIT 1"

# If error: authentication failed
# If success: connection working

# Check password in .env
grep NEO4J_PASSWORD /home/admin/projects/aegisrag/AEGIS_Rag/.env
```

**Solutions:**

#### Solution 1: Verify Credentials

```bash
# Check password matches
docker exec aegis-neo4j cypher-shell \
    -u neo4j -p <password_from_.env> \
    "CALL dbms.info()"

# If password wrong, reset it
docker compose -f docker-compose.dgx-spark.yml down neo4j
# Remove volume
docker volume rm aegis_neo4j

# Restart (will reset password to default: neo4j)
docker compose -f docker-compose.dgx-spark.yml up -d neo4j

# Update .env with new password
sed -i 's/NEO4J_PASSWORD=.*/NEO4J_PASSWORD=neo4j/' .env
```

#### Solution 2: Restart Neo4j

```bash
docker compose -f docker-compose.dgx-spark.yml restart neo4j

# Wait for startup (can take 30+ seconds)
sleep 30

# Test connection
docker exec aegis-neo4j cypher-shell \
    -u neo4j -p neo4j \
    "MATCH (n) RETURN count(n) LIMIT 1"
```

### Issue 3.3: Redis Connection Failures

**Symptoms:**
- Error: `ConnectionError: Cannot reach Redis`
- Cache not working
- Memory consolidation fails

**Root Causes:**
- Redis not running
- Port 6379 not accessible
- Redis memory exhausted

**Diagnosis:**

```bash
# Check if Redis running
docker ps | grep redis

# Test connection
docker exec aegis-redis redis-cli ping
# Should return PONG

# Check memory
docker exec aegis-redis redis-cli INFO memory | grep used_memory_human
```

**Solutions:**

#### Solution 1: Start Redis

```bash
docker compose -f docker-compose.dgx-spark.yml up -d redis

# Wait for startup
sleep 5

# Verify
docker exec aegis-redis redis-cli ping
```

#### Solution 2: Increase Memory Limit

```bash
# If Redis memory exhausted:
docker exec aegis-redis redis-cli CONFIG SET maxmemory 17179869184  # 16GB

# Or edit docker-compose.yml:
# redis:
#   environment:
#     - REDIS_MAX_MEMORY=17179869184
```

---

## Category 4: API and Service Issues

### Issue 4.1: API Health Check Fails

**Symptoms:**
- Error: `Connection refused` when hitting localhost:8000
- Frontend shows "Backend unavailable"
- Health check returns 500 error

**Root Causes:**
- API container not running
- Port 8000 not exposed
- API failed to start (startup errors)
- Services not initialized

**Diagnosis:**

```bash
# Check API is running
docker ps | grep aegis-api

# Check port is listening
lsof -i :8000
# If nothing, API not running

# Check startup logs
docker logs aegis-api | tail -50

# Check dependencies
curl http://localhost:8000/health
```

**Solutions:**

#### Solution 1: Start API

```bash
docker compose -f docker-compose.dgx-spark.yml up -d api

# Wait for startup
sleep 15

# Check health
curl http://localhost:8000/health
```

#### Solution 2: Check Startup Logs

```bash
# Detailed startup log
docker logs aegis-api --tail 100

# If error like "ImportError: cannot import..."
# 1. Rebuild image: docker build -t aegis-rag-api .
# 2. Or restart: docker compose up --no-deps --build api

# If error like "Cannot connect to database"
# 1. Verify all services running: docker ps
# 2. Verify database connectivity: see section 3
```

#### Solution 3: Rebuild and Restart

```bash
# Full rebuild
docker compose -f docker-compose.dgx-spark.yml build --no-cache api

# Start fresh
docker compose -f docker-compose.dgx-spark.yml up -d api

# Verify
curl http://localhost:8000/health
```

### Issue 4.2: 500 Internal Server Errors

**Symptoms:**
- Random API calls return 500 errors
- Error: `Internal Server Error`
- Errors only on specific endpoints

**Root Causes:**
- Unhandled exception in code
- Missing configuration
- Database constraint violation
- LLM API failure

**Diagnosis:**

```bash
# Check API logs for error
docker logs aegis-api | grep ERROR

# Get detailed error from specific endpoint
curl -v http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}' 2>&1 | tail -20

# Check which endpoint fails
for endpoint in /health /api/v1/search /api/v1/admin/stats; do
    echo "Testing $endpoint"
    curl -s http://localhost:8000$endpoint | head -c 50
done
```

**Solutions:**

#### Solution 1: Check API Logs

```bash
# Stream logs while reproducing error
docker logs -f aegis-api &

# Run operation that causes error
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'

# Stop log stream
jobs
kill %1

# Look for Traceback or ERROR in output
```

#### Solution 2: Verify Configuration

```bash
# Check required env vars are set
curl http://localhost:8000/api/v1/admin/config | jq '.configured_providers'

# Should show all configured LLM providers
# If empty/missing, restart API with proper .env

# Verify .env
docker exec aegis-api env | grep -E "OLLAMA|NEO4J|QDRANT" | head -10
```

#### Solution 3: Restart API Service

```bash
docker compose -f docker-compose.dgx-spark.yml restart api

sleep 10

# Test again
curl http://localhost:8000/health
```

---

## Category 5: Permission and Configuration Issues

### Issue 5.1: Permission Denied Errors

**Symptoms:**
- Error: `[Errno 13] Permission denied`
- Error: `Cannot write to /app/data/lightrag`
- Graph extraction fails
- Document upload fails

**Root Causes:**
- Container user lacks permissions
- Directory ownership wrong
- File permissions too restrictive

**Diagnosis:**

```bash
# Check who owns the data directory
docker exec aegis-api ls -la /app/data/

# Should show: aegis aegis (not root or other user)
# Expected: drwxr-xr-x  2 aegis aegis

# Check if user can write
docker exec aegis-api touch /app/data/test_file.txt
# If error: permission denied

# Check current user in container
docker exec aegis-api whoami
# Should return: aegis
```

**Solutions:**

#### Solution 1: Fix Directory Permissions

```bash
# Fix ownership (run as root)
docker exec -u root aegis-api \
    chown -R aegis:aegis /app/data

# Fix permissions
docker exec -u root aegis-api \
    chmod -R 755 /app/data

# Verify
docker exec aegis-api ls -la /app/data/
```

#### Solution 2: Rebuild with Sprint 68 Fixes

```bash
# Sprint 68 includes permission fixes in Dockerfiles
# Rebuild and redeploy

docker compose -f docker-compose.dgx-spark.yml build --no-cache api

docker compose -f docker-compose.dgx-spark.yml restart api
```

### Issue 5.2: Missing Environment Variables

**Symptoms:**
- Error: `Key error: OLLAMA_BASE_URL`
- Error: `NEO4J_PASSWORD not configured`
- Features not available/disabled

**Root Causes:**
- .env file missing variables
- .env not loaded into container
- Wrong container image (built without .env)

**Diagnosis:**

```bash
# Check .env file exists
ls -la /home/admin/projects/aegisrag/AEGIS_Rag/.env

# Check variables are set
grep "OLLAMA_BASE_URL" /home/admin/projects/aegisrag/AEGIS_Rag/.env

# Check what API sees
docker exec aegis-api env | grep OLLAMA_BASE_URL
```

**Solutions:**

#### Solution 1: Create Missing Variables

```bash
# Copy template
cp /home/admin/projects/aegisrag/AEGIS_Rag/.env.template \
   /home/admin/projects/aegisrag/AEGIS_Rag/.env

# Edit with required values
nano /home/admin/projects/aegisrag/AEGIS_Rag/.env

# Required variables:
# OLLAMA_BASE_URL=http://ollama:11434
# OLLAMA_MODEL_GENERATION=nemotron-no-think
# NEO4J_URI=bolt://neo4j:7687
# NEO4J_PASSWORD=neo4j
# QDRANT_HOST=qdrant
# REDIS_HOST=redis
```

#### Solution 2: Reload Configuration

```bash
# Restart all services to load new .env
docker compose -f docker-compose.dgx-spark.yml up -d

# Verify API loaded config
docker exec aegis-api env | grep OLLAMA_BASE_URL
```

---

## Category 6: LLM and Ollama Issues

### Issue 6.1: Ollama Not Responding

**Symptoms:**
- Error: `Failed to connect to Ollama`
- Error: `Ollama server not responding`
- Generation timeout

**Root Causes:**
- Ollama container crashed
- Model not loaded
- GPU memory exhausted
- Port not accessible

**Diagnosis:**

```bash
# Check Ollama container
docker ps | grep ollama

# Test connectivity
curl http://localhost:11434/api/tags
# Should list available models

# Check if model is loaded
docker exec aegis-ollama ollama list
# Should show nemotron-no-think, qwen2.5, etc.

# Check GPU usage
docker exec aegis-ollama nvidia-smi
```

**Solutions:**

#### Solution 1: Start Ollama

```bash
docker compose -f docker-compose.dgx-spark.yml up -d ollama

# Wait for startup (can take 60+ seconds)
sleep 60

# Verify
curl http://localhost:11434/api/tags
```

#### Solution 2: Pull Missing Models

```bash
# Check what models are needed
cat /home/admin/projects/aegisrag/AEGIS_Rag/.env | grep OLLAMA_MODEL

# Pull models if missing
docker exec aegis-ollama ollama pull nemotron-no-think
docker exec aegis-ollama ollama pull qwen2.5

# Verify models loaded
docker exec aegis-ollama ollama list
```

#### Solution 3: Free GPU Memory

```bash
# If GPU memory exhausted:

# 1. Check GPU usage
nvidia-smi

# 2. Reduce concurrent models
docker exec aegis-ollama \
    ollama config set OLLAMA_MAX_LOADED_MODELS 1

# 3. Restart
docker compose restart ollama
```

### Issue 6.2: LLM Generation Too Slow

**Symptoms:**
- Generation takes >500ms
- User-facing latency targets not met
- Queries timeout

**Root Causes:**
- Model too large for available resources
- GPU underutilized
- CPU bottleneck
- Model not using GPU

**Diagnosis:**

```bash
# Check which model is loaded
curl http://localhost:11434/api/tags | jq '.models[].name'

# Benchmark model speed
time curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"nemotron-no-think","prompt":"test","stream":false}' | jq '.eval_duration'

# If >3000ms: too slow

# Check GPU usage
nvidia-smi dmon 5  # Sample for 5 seconds
```

**Solutions:**

#### Solution 1: Switch to Faster Model

```bash
# Check model sizes and speeds:
# nemotron-no-think (7B) - FAST (320ms) ← Recommended
# gpt-oss:20b (20B) - BALANCED (450ms)
# qwen2.5:32b (32B) - SLOW (600ms)

# Edit .env
OLLAMA_MODEL_GENERATION=nemotron-no-think  # Switch to faster model

# Restart API
docker compose restart api
```

#### Solution 2: Reduce Context Window

```bash
# Smaller context = faster generation
docker exec aegis-ollama \
    ollama config set OLLAMA_NUM_CTX 4096  # Was 8192

docker compose restart ollama
```

#### Solution 3: Enable GPU Acceleration

```bash
# Verify GPU is being used
docker exec aegis-ollama nvidia-smi

# If GPU usage is 0%:
# 1. Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.0-runtime nvidia-smi

# 2. Rebuild with GPU support
docker compose -f docker-compose.dgx-spark.yml build --no-cache ollama
```

---

## Category 7: Frontend Issues

### Issue 7.1: Frontend Not Loading

**Symptoms:**
- Page blank or shows error
- Frontend not accessible at localhost:5179
- Error: `Cannot connect to backend`

**Root Causes:**
- Frontend container not running
- Port 5179 not exposed
- Backend API not accessible from frontend
- Missing environment variables

**Diagnosis:**

```bash
# Check frontend container
docker ps | grep frontend

# Test frontend server
curl http://localhost:5179
# Should return HTML

# Check backend connectivity
curl http://localhost:8000/health
# Should return health status
```

**Solutions:**

#### Solution 1: Start Frontend

```bash
docker compose -f docker-compose.dgx-spark.yml up -d frontend

# Wait for startup
sleep 10

# Verify
curl http://localhost:5179 | head -20
```

#### Solution 2: Check Backend Connection

```bash
# From frontend container, can it reach backend?
docker exec aegis-frontend curl http://api:8000/health

# If fails, network issue:
docker network inspect aegis-network | grep -A5 "\"api\""
```

---

## Quick Troubleshooting Checklist

- [ ] Check Docker services: `docker compose ps`
- [ ] Check logs: `docker compose logs -f api`
- [ ] Check health: `curl http://localhost:8000/health`
- [ ] Verify all databases running
- [ ] Check .env file exists and has required variables
- [ ] Verify network connectivity between containers
- [ ] Check disk space and memory
- [ ] Review error messages carefully for clues
- [ ] Restart problematic service
- [ ] Full restart if many issues

---

## Getting Help

If issue not resolved:

1. **Collect diagnostic information:**
   ```bash
   docker compose logs > /tmp/logs.txt
   docker stats --no-stream > /tmp/stats.txt
   docker compose ps > /tmp/status.txt
   ```

2. **Document the issue:**
   - When it started
   - What triggers it (reproducible?)
   - Error messages (exact text)
   - What you've tried

3. **Check relevant documentation:**
   - [Deployment Guide](../deployment/SPRINT_68_DEPLOYMENT.md)
   - [Performance Tuning](../guides/PERFORMANCE_TUNING.md)
   - [Sprint 68 Summary](../sprints/SPRINT_68_SUMMARY.md)

4. **Review logs for patterns:**
   ```bash
   docker compose logs api | grep -i error | tail -20
   ```

---

## Related Documentation

- [Deployment Guide](../deployment/SPRINT_68_DEPLOYMENT.md) - How to deploy
- [Performance Tuning Guide](PERFORMANCE_TUNING.md) - Optimization strategies
- [Sprint 68 Summary](../sprints/SPRINT_68_SUMMARY.md) - Feature details
- [CLAUDE.md](../../CLAUDE.md) - Project context

---

**Troubleshooting Complete!**

Most common issues have step-by-step solutions. Start with diagnosis, then try solutions in order.

---

**Author:** Documentation Agent (Claude)
**Date:** 2026-01-01
**Version:** 1.0
