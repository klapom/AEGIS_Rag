# DGX Spark Deployment Guide

## AEGIS RAG on NVIDIA DGX Spark (Grace Blackwell)

**Last Updated:** 2025-12-05
**Target Hardware:** NVIDIA DGX Spark (Grace CPU + Blackwell GB10 GPU)
**Architecture:** ARM64 (aarch64)

---

## Overview

This guide covers deploying AEGIS RAG on NVIDIA DGX Spark with **local Qwen3 models** instead of cloud-based Alibaba Cloud DashScope. The DGX Spark's 128GB unified memory enables running multiple large models simultaneously.

### Why DGX Spark?

| Feature | DGX Spark | Cloud (Alibaba) |
|---------|-----------|-----------------|
| **Cost** | One-time hardware | ~$120/month API |
| **Latency** | <100ms local | 200-500ms network |
| **Privacy** | Data stays local | Data sent to cloud |
| **Models** | Full 32B models | API rate limits |
| **Offline** | Works without internet | Requires connectivity |

---

## Hardware Requirements

### NVIDIA DGX Spark Specifications

| Component | Specification |
|-----------|---------------|
| **CPU** | NVIDIA Grace (ARM64) |
| **GPU** | NVIDIA Blackwell GB10 |
| **Memory** | 128GB Unified (CPU+GPU shared) |
| **Storage** | NVMe SSD (recommend 500GB+) |
| **OS** | Ubuntu 22.04/24.04 (ARM64) |

### Memory Budget (128GB)

| Component | Memory | Notes |
|-----------|--------|-------|
| **Qwen3-32B** | ~20GB | Primary LLM for generation + extraction |
| **Qwen3-VL-32B** | ~20GB | Vision Language Model |
| **BGE-M3** | ~1.2GB | Embeddings (1024-dim) |
| **Docling** | ~4GB | Document parsing + OCR |
| **Neo4j** | ~4GB | Graph database |
| **Qdrant** | ~2GB | Vector database |
| **Redis** | ~1GB | Cache + session storage |
| **Monitoring** | ~1.5GB | Prometheus + Grafana |
| **Reserve** | ~74GB | Concurrent operations, buffers |

---

## Model Configuration

### Ollama Models for DGX Spark

Replace cloud Alibaba DashScope models with local Ollama:

| Use Case | Cloud Model | Local Model (DGX Spark) |
|----------|-------------|-------------------------|
| **Generation** | qwen-turbo/qwen-plus | qwen3:32b |
| **Entity Extraction** | qwen3-32b (DashScope) | qwen3:32b |
| **Vision (VLM)** | qwen3-vl-30b-a3b-instruct | qwen3-vl:32b |
| **Embeddings** | BGE-M3 (local) | bge-m3 (Ollama) |

### Pull Models

```bash
# SSH to DGX Spark
ssh admin@dgx-spark

# Pull models (total ~41GB)
ollama pull qwen3:32b      # 20GB - Primary LLM
ollama pull qwen3-vl:32b   # 20GB - Vision Language Model
ollama pull bge-m3         # 1.2GB - Embeddings

# Verify models
ollama list
```

---

## Docker Configuration

### docker-compose.dgx-spark.yml

The DGX Spark uses a dedicated compose file optimized for 128GB unified memory:

```yaml
# Key differences from standard docker-compose.yml:
# 1. Ollama with OLLAMA_MAX_LOADED_MODELS=2 (keep both Qwen3 models loaded)
# 2. Docling uses custom ARM64 image (aegis-docling-spark)
# 3. Memory limits adjusted for 128GB system
# 4. GPU runtime for all ML containers
```

### Start Services

```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag

# Start core services (without ingestion profile)
docker compose -f docker-compose.dgx-spark.yml up -d

# Start with Docling for document ingestion
docker compose -f docker-compose.dgx-spark.yml --profile ingestion up -d
```

### Verify Services

```bash
# Check all containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Expected output:
# aegis-ollama       Up (healthy)    0.0.0.0:11434->11434/tcp
# aegis-docling      Up (healthy)    0.0.0.0:8080->5001/tcp
# aegis-neo4j        Up (healthy)    0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
# aegis-redis        Up (healthy)    0.0.0.0:6379->6379/tcp
# aegis-qdrant       Up              0.0.0.0:6333-6334->6333-6334/tcp
# aegis-prometheus   Up (healthy)    0.0.0.0:9090->9090/tcp
# aegis-grafana      Up (healthy)    0.0.0.0:3000->3000/tcp
```

---

## Docling ARM64 Build

The official Docling image doesn't support ARM64. We build a custom image:

### Dockerfile.docling-spark

Key configurations for DGX Spark:

```dockerfile
# Base image: PyTorch 25.01+ required for GB10 GPU support
FROM nvcr.io/nvidia/pytorch:25.01-py3

# NumPy 2.x compatibility (NGC container uses NumPy 2.x)
# Must use RapidOCR instead of EasyOCR (EasyOCR requires NumPy 1.x)
ENV DOCLING_OCR_ENGINE=rapidocr

# Ubuntu 24.04 package fix
# libgl1-mesa-glx deprecated -> use libgl1
RUN apt-get install -y libgl1
```

### Build Custom Image

```bash
# Build ARM64 Docling image
docker build -f docker/Dockerfile.docling-spark -t aegis-docling-spark:latest .

# If rebuild needed (e.g., after Dockerfile changes)
docker build --no-cache -f docker/Dockerfile.docling-spark -t aegis-docling-spark:latest .
```

---

## Container Images

The DGX Spark deployment uses two separate container images for the AEGIS RAG application:

### Production vs Test Containers

| Container | Dockerfile | Image | Purpose |
|-----------|------------|-------|---------|
| **API (Production)** | `docker/Dockerfile.api` | `aegis-rag-api:latest` | FastAPI backend, core dependencies only |
| **Test** | `docker/Dockerfile.api-test` | `aegis-rag-test:latest` | Includes dev + reranking + ingestion groups |

### Dependency Groups

```yaml
# Production (Dockerfile.api)
poetry install --no-root --no-interaction

# Test (Dockerfile.api-test)
poetry install --no-root --with dev,reranking,ingestion --no-interaction
```

| Group | Contents | Size |
|-------|----------|------|
| **core** | FastAPI, Qdrant, Neo4j, Redis, LangGraph | ~500MB |
| **dev** | pytest, ruff, black, mypy, bandit | ~100MB |
| **reranking** | sentence-transformers, scikit-learn | ~400MB |
| **ingestion** | llama-index, python-pptx, docx2txt | ~300MB |

### Build Commands

```bash
# Build production API container
docker compose -f docker-compose.dgx-spark.yml build api

# Build test container (includes all test dependencies)
docker compose -f docker-compose.dgx-spark.yml build test

# Rebuild both after code changes
docker compose -f docker-compose.dgx-spark.yml build api test
```

### Running Tests

```bash
# Run all unit tests
docker compose -f docker-compose.dgx-spark.yml run --rm test python -m pytest tests/unit/ -v

# Run specific test file
docker compose -f docker-compose.dgx-spark.yml run --rm test python -m pytest tests/unit/api/test_chat_endpoints.py -v

# Run with coverage
docker compose -f docker-compose.dgx-spark.yml run --rm test python -m pytest tests/unit/ --cov=src --cov-report=term-missing
```

### When to Rebuild

| Change Type | Rebuild API? | Rebuild Test? |
|-------------|--------------|---------------|
| `src/**/*.py` changes | ✅ Yes | ✅ Yes |
| `tests/**/*.py` changes | ❌ No | ✅ Yes |
| `pyproject.toml` changes | ✅ Yes | ✅ Yes |
| `config/**` changes | ❌ No (mounted) | ❌ No (mounted) |

---

## Environment Configuration

### .env for DGX Spark

```bash
# Ollama (Local - Primary)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=qwen3:32b
OLLAMA_MODEL_EXTRACTION=qwen3:32b
OLLAMA_MODEL_VLM=qwen3-vl:32b
OLLAMA_MODEL_EMBEDDING=bge-m3

# Disable cloud LLM (using local models)
# ALIBABA_CLOUD_API_KEY=  # Comment out or remove
USE_LOCAL_LLM=true

# Databases (same as standard deployment)
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password
REDIS_HOST=localhost
REDIS_PORT=6379

# Docling
DOCLING_URL=http://localhost:8080
DOCLING_OCR_ENGINE=rapidocr
```

---

## Troubleshooting

### Issue: GB10 GPU Not Supported

**Symptom:**
```
WARNING: Detected NVIDIA GB10 GPU, which is not yet supported in this version
```

**Solution:** Use PyTorch NGC container 25.01 or later:
```dockerfile
FROM nvcr.io/nvidia/pytorch:25.01-py3  # NOT 24.08
```

### Issue: NumPy 2.x / OpenCV Conflict

**Symptom:**
```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.2.6
ImportError: numpy.core.multiarray failed to import
```

**Solution:** The NGC PyTorch 25.01 container uses NumPy 2.x. You cannot downgrade without breaking PyTorch. Instead:

1. Remove NGC's pre-compiled OpenCV:
```dockerfile
RUN pip uninstall -y opencv-python opencv-python-headless cv2 || true && \
    rm -rf /usr/local/lib/python3.12/dist-packages/cv2* || true
```

2. Install fresh OpenCV compatible with NumPy 2.x:
```dockerfile
RUN pip install --force-reinstall "opencv-python-headless>=4.10"
```

3. Use RapidOCR instead of EasyOCR (EasyOCR requires NumPy 1.x):
```dockerfile
ENV DOCLING_OCR_ENGINE=rapidocr
RUN pip install rapidocr-onnxruntime
```

### Issue: libgl1-mesa-glx Not Found

**Symptom:**
```
Package 'libgl1-mesa-glx' has no installation candidate
```

**Solution:** Ubuntu 24.04 (Noble) deprecated this package. Use `libgl1`:
```dockerfile
RUN apt-get install -y libgl1  # NOT libgl1-mesa-glx
```

### Issue: docling_serve Module Not Found

**Symptom:**
```
No module named 'docling_serve'
```

**Solution:** The package is `docling-serve` (hyphen), not `docling_serve` (underscore). Use CLI command:
```dockerfile
CMD ["docling-serve", "run", "--host", "0.0.0.0", "--port", "5001"]
```

### Issue: Qdrant Shows "unhealthy"

**Symptom:** Qdrant container shows `(unhealthy)` but service works.

**Cause:** Qdrant image doesn't include `wget` for health checks.

**Solution:** This is cosmetic - the service is functional. Verify with:
```bash
curl http://localhost:6333/health
# Should return: {"title":"qdrant - vector search engine","version":"..."}
```

---

## Performance Tuning

### Ollama Multi-Model Loading

Keep both Qwen3 models loaded in memory:

```yaml
# docker-compose.dgx-spark.yml
ollama:
  environment:
    - OLLAMA_MAX_LOADED_MODELS=2  # Keep qwen3:32b AND qwen3-vl:32b loaded
    - OLLAMA_NUM_PARALLEL=4       # Parallel request handling
```

### Memory Monitoring

```bash
# Monitor GPU/unified memory usage
nvidia-smi

# Monitor container memory
docker stats --no-stream
```

---

## Migration from Cloud to Local

### Step 1: Update AegisLLMProxy Configuration

The `AegisLLMProxy` automatically routes to local Ollama when configured:

```python
# src/components/llm_proxy/aegis_llm_proxy.py
# Routing priority: Local Ollama -> Alibaba Cloud -> OpenAI

# With USE_LOCAL_LLM=true and OLLAMA_BASE_URL set,
# all requests route to local Qwen3 models
```

### Step 2: Update Environment Variables

```bash
# Remove or comment out cloud API keys
# ALIBABA_CLOUD_API_KEY=sk-...

# Enable local mode
USE_LOCAL_LLM=true
OLLAMA_BASE_URL=http://localhost:11434
```

### Step 3: Verify Routing

```bash
# Check which model is being used
curl http://localhost:11434/api/tags | jq '.models[].name'

# Test generation
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:32b",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

---

## Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| **AEGIS RAG API** | http://localhost:8000 | Main application |
| **Ollama API** | http://localhost:11434 | LLM inference |
| **Docling API** | http://localhost:8080 | Document parsing |
| **Neo4j Browser** | http://localhost:7474 | Graph database UI |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | Vector DB UI |
| **Grafana** | http://localhost:3000 | Monitoring dashboards |
| **Prometheus** | http://localhost:9090 | Metrics |

---

## Cost Comparison

### Monthly Cost: Cloud vs. Local

| Component | Cloud (Alibaba) | Local (DGX Spark) |
|-----------|-----------------|-------------------|
| **LLM Generation** | ~$80/month | $0 |
| **Entity Extraction** | ~$30/month | $0 |
| **VLM Processing** | ~$10/month | $0 |
| **Embeddings** | $0 (local BGE-M3) | $0 |
| **Total** | **~$120/month** | **$0** |

### Break-Even Analysis

- DGX Spark hardware cost: ~$3,000 (estimated)
- Monthly cloud savings: ~$120
- Break-even: ~25 months

**Note:** This doesn't account for:
- Lower latency (local inference)
- Data privacy (no cloud transmission)
- Offline capability
- No rate limits

---

## Related Documentation

- [TECH_STACK.md](../TECH_STACK.md) - Technology stack overview
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - General quick start
- [MONITORING_GUIDE.md](MONITORING_GUIDE.md) - Prometheus/Grafana setup
- [ADR-027](../adr/ADR-027-docling-container-architecture.md) - Docling architecture
- [ADR-033](../adr/ADR-033-any-llm-integration.md) - ANY-LLM integration

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-05 | Initial DGX Spark deployment guide |
| 2025-12-05 | NumPy 2.x compatibility fixes (RapidOCR) |
| 2025-12-05 | PyTorch 25.01 for GB10 support |
