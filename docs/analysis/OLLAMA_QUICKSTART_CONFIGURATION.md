# Ollama Configuration Quick Start (Sprint 61)

**Purpose:** Implement high-impact Ollama optimizations in AEGIS RAG
**Effort:** 2 SP (configuration) + 1 SP (documentation)
**Expected Gain:** +30% throughput
**Risk:** Low (reversible parameter changes)

---

## Step 1: Update Environment Variables

### Location
File: `src/.env` (development) or `docker-compose.dgx-spark.yml` (production)

### Development Configuration (src/.env)

```bash
# Copy and paste this section
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=llama3.2:8b

# Performance Tuning (NEW - Add these)
OLLAMA_NUM_PARALLEL=4
OLLAMA_NUM_THREADS=8
OLLAMA_MAX_LOADED_MODELS=3
OLLAMA_KEEP_ALIVE=10m
OLLAMA_FLASH_ATTENTION=0
OLLAMA_MAX_QUEUE=512
```

### Production Configuration (docker-compose.dgx-spark.yml)

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    environment:
      # Existing
      - OLLAMA_BASE_URL=http://localhost:11434
      - OLLAMA_MODEL_GENERATION=llama3.2:8b

      # Performance Tuning (ADD THESE)
      - OLLAMA_NUM_PARALLEL=4
      - OLLAMA_NUM_THREADS=16
      - OLLAMA_MAX_LOADED_MODELS=3
      - OLLAMA_KEEP_ALIVE=30m
      - OLLAMA_FLASH_ATTENTION=0
      - OLLAMA_MAX_QUEUE=512
```

---

## Step 2: Parameter Reference

### OLLAMA_NUM_PARALLEL=4
- **What:** Maximum concurrent requests per model
- **Default:** 1-4 (auto-detected)
- **DGX Spark:** 4 (optimal for GB10 + 128GB memory)
- **Dev:** 2 (conservative for laptops)
- **Impact:** Processes 4 requests in parallel instead of queuing

### OLLAMA_NUM_THREADS=16 (Production) / 8 (Dev)
- **What:** CPU threads for attention computation
- **ARM64 DGX Spark:** 16 threads
- **Intel/AMD:** Match CPU core count
- **Impact:** 10-14% improvement when GPU layers offload to CPU

### OLLAMA_MAX_LOADED_MODELS=3
- **What:** Maximum models in memory simultaneously
- **Default:** 3 (good baseline)
- **DGX Spark:** Keep at 3 (supports llama3.2:8b + bge-m3 + 1 spare)
- **Impact:** Allows multi-model serving without reloading

### OLLAMA_KEEP_ALIVE=30m (Production) / 10m (Dev)
- **What:** How long to keep model in memory after last use
- **Default:** 5 minutes (aggressive unload)
- **Production:** 30 minutes (reduces reload penalty)
- **Dev:** 10 minutes (balance memory usage)
- **Impact:** Saves 3-5s on repeated queries by skipping model load

### OLLAMA_FLASH_ATTENTION=0
- **What:** Enable Flash Attention v2
- **DGX Spark Status:** NOT SUPPORTED (sm_121a limitation)
- **Required:** Set to 0 to use memory-efficient attention
- **Impact:** Prevents CUDA errors, 10-15% perf penalty but stable
- **Alternative:** No alternative for DGX Spark, keep at 0

### OLLAMA_MAX_QUEUE=512
- **What:** Maximum queued requests before returning 503
- **Default:** 512
- **DGX Spark:** Keep at 512 (adequate for <50 QPS)
- **Scale:** Increase to 1024+ only if handling 100+ QPS

---

## Step 3: Verify Configuration

### Check Ollama Status

```bash
# Test Ollama is running
curl -s http://localhost:11434/api/version | jq .

# Expected output:
# {
#   "version": "0.8.x"
# }

# Check loaded models
curl -s http://localhost:11434/api/ps | jq .

# Expected output shows:
# - llama3.2:8b model loaded
# - num_loaded_models: 1 or 2
# - memory usage ~4-5GB
```

### Test Performance

```bash
# Simple latency test
time curl -s -X POST http://localhost:11434/api/generate \
  -d '{
    "model": "llama3.2:8b",
    "prompt": "What is the capital of France?",
    "stream": false
  }' | jq '.response' | head -20
```

---

## Step 4: Update Documentation

### Update CLAUDE.md

Add to "Environment Variables" section:

```markdown
## Environment Variables

### Ollama Configuration (Optimized for Sprint 61)

**Performance Tuning Parameters:**
```bash
# Parallel Request Processing
OLLAMA_NUM_PARALLEL=4          # Process 4 requests simultaneously
OLLAMA_NUM_THREADS=16          # ARM64 CPU thread count
OLLAMA_MAX_LOADED_MODELS=3     # Max models in memory

# Memory & Timeout Management
OLLAMA_KEEP_ALIVE=30m          # Keep models in memory for 30min
OLLAMA_MAX_QUEUE=512           # Request queue size

# Hardware Workaround
OLLAMA_FLASH_ATTENTION=0       # sm_121a doesn't support FA2
```

**Rationale:** Configuration optimized for DGX Spark (GB10, 128GB RAM, single GPU) to achieve +30% throughput improvement while maintaining stability.
```

---

## Step 5: Implementation Checklist

- [ ] Stop running Ollama service
- [ ] Update .env file (development)
- [ ] Update docker-compose.dgx-spark.yml (production)
- [ ] Start Ollama with new configuration
- [ ] Verify with `curl http://localhost:11434/api/ps`
- [ ] Run baseline performance test (see Step 3)
- [ ] Update CLAUDE.md documentation
- [ ] Create git commit with changes
- [ ] Monitor for 24 hours in staging environment

---

## Step 6: Baseline Metrics (Before & After)

### Measurement Script

```bash
#!/bin/bash
# scripts/measure_ollama_performance.sh

echo "=== Ollama Performance Baseline ==="
echo "Date: $(date)"
echo ""

# Single request test (10 iterations)
echo "Single Request Test (10x):"
for i in {1..10}; do
  time curl -s -X POST http://localhost:11434/api/generate \
    -d '{
      "model": "llama3.2:8b",
      "prompt": "What is 2+2?",
      "stream": false
    }' > /dev/null
done

# Check memory usage
echo ""
echo "Memory Usage:"
curl -s http://localhost:11434/api/ps | jq '.models[].details.parameter_size'

echo ""
echo "Model Status:"
curl -s http://localhost:11434/api/ps | jq '.models[] | {name, size: (.size / 1e9 | floor) + "GB"}'
```

### Recording Template

| Metric | Before | After | Gain |
|--------|--------|-------|------|
| Single Query Latency | ___ms | ___ms | +__% |
| Concurrent (4 req) | ___ms | ___ms | +__% |
| Model Load Time | ___ms | ___ms | +__% |
| VRAM Usage | ___GB | ___GB | ±_GB |
| Notes | | | |

---

## Troubleshooting

### Ollama Won't Start with New Config

**Problem:** Service fails to start after environment variable change
**Solution:**
1. Check Ollama logs: `docker logs ollama` (if Docker)
2. Revert to defaults: Remove new environment variables
3. Start service, verify it works
4. Add variables one at a time to identify issue
5. Common: OLLAMA_NUM_PARALLEL too high for available VRAM

### High Memory Usage

**Problem:** VRAM usage >15GB after configuration
**Solution:**
1. Reduce OLLAMA_NUM_PARALLEL to 2
2. Reduce OLLAMA_MAX_LOADED_MODELS to 1-2
3. Monitor with: `curl http://localhost:11434/api/ps | jq`
4. DGX Spark has 128GB, should easily handle current config

### Model Takes Long Time to Load

**Problem:** Model load time increased
**Solution:**
1. Verify OLLAMA_KEEP_ALIVE is working (models should persist)
2. Check disk I/O: Model loading is I/O bound initially
3. Subsequent loads should be <1s (warm start)
4. First load after restart expected: 3-5s

### 503 Errors / Queue Full

**Problem:** Receiving "503 Service Unavailable" responses
**Solution:**
1. Check queue: `curl http://localhost:11434/api/ps | jq '.queue_length'`
2. If queue > 512: Too many concurrent requests
3. Increase OLLAMA_NUM_PARALLEL (if VRAM available)
4. Or increase OLLAMA_MAX_QUEUE (but address root cause)

---

## Rollback Instructions

If configuration causes issues:

```bash
# 1. Stop Ollama
docker-compose down ollama

# 2. Remove environment variables from config
# Edit docker-compose.dgx-spark.yml, remove OLLAMA_* lines

# 3. Restart with defaults
docker-compose up -d ollama

# 4. Verify
curl http://localhost:11434/api/version

# 5. Commit rollback
git commit -m "fix: Revert Ollama optimization (Sprint 61 investigation)"
```

---

## Next Steps

### After Sprint 61 Configuration

1. **Monitor for 1-2 weeks:**
   - Track P95 latency
   - Monitor VRAM usage
   - Check error logs

2. **Evaluate Impact:**
   - Measure +30% throughput gain
   - Identify any regressions
   - Collect metrics for report

3. **Plan Sprint 62:**
   - Decide on Request Batching (if concurrent load >5 users)
   - Decide on Redis Caching (if repeated queries >40%)

4. **Document Results:**
   - Create Sprint 61 completion report
   - Update performance target in CLAUDE.md
   - Archive baseline metrics

---

## Additional Resources

- [Detailed Optimization Guide](/home/admin/projects/aegisrag/AEGIS_Rag/docs/analysis/OLLAMA_OPTIMIZATION_OPPORTUNITIES_SPRINT61.md)
- [Research Summary](/home/admin/projects/aegisrag/AEGIS_Rag/docs/analysis/OLLAMA_RESEARCH_SUMMARY.md)
- [Ollama Official FAQ](https://docs.ollama.com/faq)
- [2025 Best Practices](https://www.glukhov.org/post/2025/05/how-ollama-handles-parallel-requests/)

---

## ✅ Deployed Configuration (Sprint 61 Feature 61.3)

**Deployed:** 2025-12-23
**Status:** Active in docker-compose.dgx-spark.yml

### Production Configuration (DGX Spark)

```yaml
ollama:
  environment:
    # DGX Spark optimized settings (+30% throughput)
    - OLLAMA_NUM_PARALLEL=4          # Parallel requests (128GB RAM allows it)
    - OLLAMA_MAX_QUEUE=512           # Request queue size
    - OLLAMA_KEEP_ALIVE=60m          # Keep models in memory (better than 5m default)
    - OLLAMA_MAX_LOADED_MODELS=2     # Nemotron + GPT-OSS or Qwen3-VL
    - OLLAMA_NUM_CTX=8192            # Context window
    - OLLAMA_NUM_THREAD=20           # CPU threads for ARM64
    - OLLAMA_NUM_GPU=-1              # Force all layers to GPU
```

### Verification Commands

```bash
# Check Ollama configuration is active
docker exec aegis-ollama env | grep OLLAMA_NUM_PARALLEL
# Should output: OLLAMA_NUM_PARALLEL=4

# Check queue capacity
docker exec aegis-ollama env | grep OLLAMA_MAX_QUEUE
# Should output: OLLAMA_MAX_QUEUE=512

# Test parallel processing
for i in {1..4}; do
  curl -s -X POST http://localhost:11434/api/generate \
    -d '{"model": "nemotron-no-think:latest", "prompt": "Test", "stream": false}' &
done
wait
```

**Expected Performance:**
- Throughput: >2 QPS (10 parallel requests)
- P95 latency: <2s for simple queries
- Memory: 15-20GB for 2 loaded models

---

**Document Status:** ✅ Deployed (Sprint 61 Feature 61.3 Complete)
**Last Updated:** 2025-12-23
