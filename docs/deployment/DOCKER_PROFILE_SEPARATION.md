# Docker Profile Separation: vLLM vs Ollama (Sprint 125.3)

## Problem Statement

The DGX Spark has limited GPU memory (128GB unified). Both vLLM and Ollama require GPU access, but they conflict during initialization:

1. **vLLM Initialization**: Performs GPU memory profiling during startup
2. **Ollama Unloading**: Detects increased GPU memory usage and unloads models
3. **Result**: vLLM fails with:
   ```
   AssertionError: Error in memory profiling. Initial free memory 30.27 GiB,
   current free memory 52.21 GiB. This happens when other processes sharing
   the same container release GPU memory while vLLM is profiling during initialization.
   ```

## Solution: Strict Profile-Based Separation

Run only ONE LLM server at a time:

| Mode | Ollama | vLLM | Docling | Use Case |
|------|--------|------|---------|----------|
| **CHAT** (default) | ✓ Running | ✗ Stopped | ✗ Stopped | Chat, Query, LLM requests |
| **INGESTION** | ✗ Stopped | ✓ Running | ✓ Running | High-concurrency extraction (256+ requests) |

## Implementation Details

### Docker Profiles

**File**: `docker-compose.dgx-spark.yml`

```yaml
services:
  ollama:
    profiles:
      - chat  # Only start in CHAT mode
    # ... rest of config

  vllm:
    profiles:
      - ingestion  # Only start in INGESTION mode
    # ... rest of config

  docling:
    profiles:
      - ingestion  # Only start in INGESTION mode
    # ... rest of config
```

**Note**: Empty `profiles` list means "always-on" (runs in both modes by default).

### Configuration

**File**: `.env`

```bash
# Sprint 125.3: Strict Docker profile separation
AEGIS_MODE=chat  # 'chat' or 'ingestion'
```

**File**: `src/core/config.py`

```python
aegis_mode: Literal["chat", "ingestion"] = Field(
    default="chat",
    description="LLM execution mode (chat or ingestion)"
)
```

**File**: `src/domains/llm_integration/proxy/aegis_llm_proxy.py`

```python
# Load AEGIS_MODE to determine which LLM server is running
self._aegis_mode = settings.aegis_mode
self._skip_ollama_fallback_in_ingestion = self._aegis_mode == "ingestion"

# In INGESTION mode, don't try Ollama fallback (it's stopped)
if self._skip_ollama_fallback_in_ingestion:
    raise LLMExecutionError(
        f"Provider {provider} failed in INGESTION mode. "
        f"Ollama is not available."
    )
```

## Usage Guide

### Switch Mode with Helper Script (Recommended)

```bash
# Switch to CHAT mode (Ollama only)
./scripts/switch_mode.sh chat

# Switch to INGESTION mode (vLLM + Docling only)
./scripts/switch_mode.sh ingestion

# Check current mode
./scripts/switch_mode.sh status
```

### Manual Mode Switching

#### Start CHAT Mode
```bash
# Start all default services (includes Ollama)
docker compose -f docker-compose.dgx-spark.yml up -d

# Verify Ollama is running
curl http://localhost:11434/api/tags

# Pull LLM models (once per setup)
docker exec aegis-ollama ollama pull nemotron-3-nano:128k
docker exec aegis-ollama ollama pull gpt-oss:20b
docker exec aegis-ollama ollama pull qwen3-vl:32b
```

#### Switch to INGESTION Mode
```bash
# Step 1: Stop Ollama
docker compose -f docker-compose.dgx-spark.yml stop ollama

# Step 2: Wait for GPU memory cleanup
sleep 5

# Step 3: Start vLLM and Docling with ingestion profile
docker compose -f docker-compose.dgx-spark.yml --profile ingestion up -d vllm docling

# Step 4: Wait for vLLM to initialize (2-7 minutes)
# Watch logs:
docker logs -f aegis-vllm

# Verify vLLM is ready:
curl http://localhost:8001/health
# Response: {"status":"ready"}
```

#### Return to CHAT Mode
```bash
# Step 1: Stop vLLM and Docling
docker compose -f docker-compose.dgx-spark.yml stop vllm docling

# Step 2: Wait for GPU memory cleanup
sleep 5

# Step 3: Start Ollama
docker compose -f docker-compose.dgx-spark.yml up -d ollama

# Step 4: Verify Ollama is ready
curl http://localhost:11434/api/tags
```

## Architecture

### CHAT Mode Architecture
```
User Request (Chat, Query)
    ↓
API (port 8000)
    ↓
AegisLLMProxy (routing logic)
    ↓
Route to: Ollama (port 11434)
    ↓
Response
```

### INGESTION Mode Architecture
```
User Request (Extract entities, relations)
    ↓
API (port 8000)
    ↓
AegisLLMProxy (routing logic)
    ↓
Route to: vLLM (port 8001) [256+ concurrent requests]
          OR Docling (port 8080) [GPU-accelerated OCR]
    ↓
Response
```

## API Behavior by Mode

### CHAT Mode (Ollama)
- **Extraction**: Routes to Ollama (slower, single-threaded, ~4 concurrent max)
- **Query**: Routes to Ollama (optimized for chat)
- **Fallback**: Works (Ollama always available)
- **Performance**: Lower for concurrent extraction

### INGESTION Mode (vLLM)
- **Extraction**: Routes to vLLM (fast, parallelized, 256+ concurrent)
- **Query**: NOT AVAILABLE (chat mode disabled)
- **Fallback**: DISABLED (Ollama not running, skip fallback)
- **Performance**: High for concurrent extraction

## Performance Comparison

| Operation | CHAT (Ollama) | INGESTION (vLLM) |
|-----------|---------------|------------------|
| Single Extraction | ~5-10s | ~3-5s |
| 100 Concurrent Extractions | ~300s+ (queue) | ~30-50s (batched) |
| Latency (p95) | ~2-5s | ~1-3s |
| Memory Usage | 80-100GB | 60-80GB |

## Troubleshooting

### vLLM Fails with Memory Profiling Error
**Cause**: Ollama is still running or GPU memory not fully released

**Solution**:
```bash
# Ensure Ollama is completely stopped
docker compose -f docker-compose.dgx-spark.yml stop ollama
docker compose -f docker-compose.dgx-spark.yml rm ollama  # Remove container

# Wait longer for GPU memory cleanup
sleep 10

# Check GPU memory
nvidia-smi

# Start vLLM
docker compose -f docker-compose.dgx-spark.yml --profile ingestion up -d vllm
```

### Both Ollama and vLLM Running
**Cause**: Accidentally started both services

**Status Check**:
```bash
./scripts/switch_mode.sh status
# Output: WARNING: Both Ollama and vLLM are running!
```

**Fix**:
```bash
# Choose one mode and stick with it
./scripts/switch_mode.sh chat     # Stop vLLM, start Ollama
# OR
./scripts/switch_mode.sh ingestion # Stop Ollama, start vLLM
```

### vLLM Takes Too Long to Start (30+ minutes)
**Cause**: Model is being downloaded from Hugging Face

**Solution**:
```bash
# Watch the logs
docker logs -f aegis-vllm

# Check disk space
df -h ~/.cache/huggingface

# If stuck, restart with fresh cache
docker compose -f docker-compose.dgx-spark.yml down
rm -rf ~/.cache/huggingface/hub/*vllm*
docker compose -f docker-compose.dgx-spark.yml --profile ingestion up -d vllm
```

### API Returns Ollama Connection Error in INGESTION Mode
**Cause**: Trying to use Ollama while in INGESTION mode

**Solution**:
```bash
# Check current mode
./scripts/switch_mode.sh status

# If in INGESTION mode, use vLLM endpoints only
# vLLM health: curl http://localhost:8001/health
# Ollama health: NOT AVAILABLE in INGESTION mode
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AEGIS_MODE` | `chat` | Current execution mode (chat or ingestion) |
| `VLLM_ENABLED` | `false` | Enable vLLM provider (set by script) |
| `VLLM_BASE_URL` | `http://vllm:8001` | vLLM endpoint URL |
| `VLLM_MODEL` | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4` | vLLM model name |

## Related Files

- **Docker Compose**: `docker-compose.dgx-spark.yml` (profiles section)
- **Helper Script**: `scripts/switch_mode.sh` (mode switching)
- **Configuration**: `src/core/config.py` (AEGIS_MODE field)
- **LLM Proxy**: `src/domains/llm_integration/proxy/aegis_llm_proxy.py` (mode-aware routing)
- **Environment**: `.env.template` (AEGIS_MODE variable)

## Decision Log

### Sprint 125 Feature 125.3: Strict Docker Profile Separation

**Problem**: vLLM crashes during GPU memory profiling when Ollama is also running

**Decision**: Implement Docker profiles to run only one LLM server at a time

**Reasoning**:
1. **Profiles over Flags**: Docker profiles are declarative, explicit, and prevent accidental conflicts
2. **Helper Script**: Makes mode switching safe and idempotent (can call multiple times)
3. **Health Checks**: Script verifies service readiness before returning
4. **GPU Memory Cleanup**: 5-second pause ensures complete GPU memory release
5. **Backward Compatibility**: Default CHAT mode keeps existing workflows working

**Alternatives Considered**:
- Memory limits for vLLM: Doesn't work (vLLM needs full GPU)
- Sequential startup: Error-prone (timing issues)
- Process-level separation: Requires Linux cgroup management (too complex)
- Shared GPU: Tested, still causes conflicts during profiling

## References

- [Docker Compose Profiles](https://docs.docker.com/compose/profiles/)
- [vLLM GPU Memory Documentation](https://docs.vllm.ai/en/latest/getting_started/installation.html)
- [Ollama GPU Support](https://github.com/ollama/ollama/blob/main/docs/gpu.md)
- ADR-053: vLLM Integration for High-Concurrency Extraction
