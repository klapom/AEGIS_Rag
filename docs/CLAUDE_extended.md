# CLAUDE_EXTENDED.md - Erweiterte Informationen

Diese Datei enthält Details, die nicht täglich benötigt werden, aber für tieferes Verständnis wichtig sind.

---

## DGX Spark Hardware Details

### Hardware-Spezifikationen
- **GPU:** NVIDIA GB10 (Blackwell, sm_121)
- **CUDA:** 13.0, Driver 580.95.05
- **Memory:** 128GB Unified Memory
- **CPU:** 20 ARM Cortex (aarch64)
- **OS:** Ubuntu 24.04

### Framework Compatibility
| Framework | Status | Notes |
|-----------|--------|-------|
| PyTorch cu130 | ✅ Works | `--index-url https://download.pytorch.org/whl/cu130` |
| NGC Container | ✅ Works | `nvcr.io/nvidia/pytorch:25.09-py3` oder neuer |
| llama.cpp | ✅ Works | Native CUDA compilation |
| Triton | ✅ Works | Muss von Source gebaut werden für sm_121a |
| PyTorch cu128 | ❌ Fails | `nvrtc: invalid value for --gpu-architecture` |
| TensorFlow | ❌ Unsupported | Offiziell nicht mehr unterstützt auf DGX Spark |
| TensorRT | ❌ Fails | Kein sm_121 Support (nur bis sm_120) |
| PaddlePaddle | ❌ Fails | Kein ARM64 Support |
| ONNX Runtime | ⚠️ Manual Build | Wheels müssen selbst kompiliert werden |

### Required Environment
```bash
export TORCH_CUDA_ARCH_LIST="12.1a"
export CUDACXX=/usr/local/cuda-13.0/bin/nvcc
export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas
```

### ONNX Runtime Compilation (falls benötigt)
```bash
git clone --recursive https://github.com/Microsoft/onnxruntime.git
cd onnxruntime

sh build.sh --config Release \
    --build_dir build/cuda13 \
    --parallel 20 \
    --use_cuda \
    --cuda_version 13.0 \
    --cuda_home /usr/local/cuda-13.0/ \
    --cudnn_home /usr/local/cuda-13.0/ \
    --build_wheel \
    --skip_tests \
    --cmake_generator Ninja \
    --cmake_extra_defines CMAKE_CUDA_ARCHITECTURES=121

pip install build/cuda13/Release/dist/*.whl
```

### Flash Attention Workaround
```python
import torch
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(True)
```

### nvcc Path Problem
Falls `/usr/bin/nvcc` (alte Version) statt `/usr/local/cuda/bin/nvcc`:
```bash
sudo apt remove nvidia-cuda-toolkit
# ODER
export CUDACXX=/usr/local/cuda-13.0/bin/nvcc
```

---

## Ollama auf DGX Spark (Sprint 120 Erkenntnisse)

### Ollama Version & New Engine

**Kritisch:** Ollama muss mindestens **v0.15.2** sein UND `OLLAMA_NEW_ENGINE=true` gesetzt haben, damit hybride Modellarchitekturen (Transformer+Mamba SSM, MoE) auf der GPU laufen.

```yaml
# docker-compose.dgx-spark.yml → ollama service
environment:
  - OLLAMA_NEW_ENGINE=true    # PFLICHT für Nemotron3, Jamba, etc.
  - OLLAMA_NUM_GPU=-1         # Alle Layers auf GPU
  - OLLAMA_FLASH_ATTENTION=false  # DGX Spark Blackwell Kompatibilität
```

**Problem mit Ollama ≤0.13.4:** Modelle mit `nemotron_h_moe`-Architektur wurden komplett als `CPU_Mapped` geladen — alle Tensors, KV-Cache, Recurrent State und Compute-Buffers auf CPU. Ergebnis: 3.1 tok/s statt 74 tok/s.

**Diagnose-Befehle:**
```bash
# Prüfe ob Modell auf GPU oder CPU läuft:
docker logs aegis-ollama 2>&1 | grep -E "load_tensors|CPU_Mapped|CUDA0"

# SCHLECHT (alles CPU):
# load_tensors:   CPU_Mapped model buffer size = 23139.98 MiB

# GUT (GPU):
# load_tensors: offloaded 53/53 layers to GPU
# load_tensors:        CUDA0 model buffer size = 22909.02 MiB

# Ollama Version prüfen:
docker exec aegis-ollama ollama --version
```

### Nemotron3 Nano — Hybrid MoE-Architektur

Nemotron3 Nano 30B/3B (`nemotron_h_moe`) ist KEIN normaler Transformer:

| Komponente | Layers | Beschreibung |
|-----------|--------|-------------|
| **Transformer Attention** | 6 | Standard Multi-Head Attention |
| **Mamba SSM** | 46 | State Space Model (rekurrent, kein Attention) |
| **Mixture-of-Experts** | alle | 128 Experten, 6 aktiv pro Token |
| **Total Parameter** | — | 31.6B (aber nur ~3B aktiv pro Token) |

**Konsequenzen:**
1. **Ollama New Engine PFLICHT** — Die alte llama.cpp Engine hatte keine CUDA-Kernels für Mamba SSM und MoE-Routing
2. **nvidia-smi zeigt 0% GPU** — Das ist ein Reporting-Bug auf DGX Spark (Unified Memory), nicht wirklich 0%
3. **`ollama ps` zeigt "100% GPU"** — Verlässlicherer Indikator als nvidia-smi
4. **Q4_K_M Quantisierung** — ~24GB VRAM, passt komfortabel in 128GB Unified Memory
5. **Kein Flash Attention** — `OLLAMA_FLASH_ATTENTION=false` wegen Blackwell-Kompatibilität

### Performance-Referenzwerte (Sprint 120, Januar 2026)

| Modell | Architektur | Größe | tok/s | Ollama Version |
|--------|------------|-------|-------|----------------|
| `nemotron-3-nano:latest` | nemotron_h_moe | 24GB | **74 tok/s** | ≥0.15.2 + NEW_ENGINE |
| `nemotron-no-think:latest` | nemotron_h_moe | 24GB | **74 tok/s** | ≥0.15.2 + NEW_ENGINE |
| `gpt-oss:20b` | Transformer | 13GB | **77 tok/s** | ≥0.13.4 (jede Version) |
| `nemotron-3-nano:latest` | nemotron_h_moe | 24GB | 3.1 tok/s ❌ | ≤0.13.4 (CPU_Mapped!) |

**Merke:** `gpt-oss:20b` lief auch mit altem Ollama schnell (Standard-Transformer). Nur hybride Architekturen (Mamba/MoE) waren betroffen.

---

## vLLM SM121 Stability & Performance

### Container Image & FlashInfer Regression (Sprint 126)

**Problem:** vLLM 26.01-py3 with FlashInfer 0.6.0 (stable) crashes with `cudaErrorIllegalInstruction` after 1-2 requests on DGX Spark (SM121).

**Root Cause:** FlashInfer 0.6.0 stable has SM121 regression — autotuner kernel selection broken for CUDA graph DECODE mode. Autotuner selects incompatible SM120 TMA WS grouped GEMM tactics, causing illegal instruction traps.

**Solution (Sprint 126):** Use earlier FlashInfer version from NGC container `25.12.post1-py3` (FlashInfer 0.6.0rc2) which correctly skips incompatible tactics.

```bash
# BEFORE (crashes):
nvcr.io/nvidia/vllm:26.01-py3  # FlashInfer 0.6.0 stable (SM121 regression)

# AFTER (stable):
nvcr.io/nvidia/vllm:25.12.post1-py3  # FlashInfer 0.6.0rc2 (SM121 safe)
```

### Updated Configuration (Sprint 126)

| Parameter | Old Value | New Value | Reason |
|-----------|-----------|-----------|--------|
| **Container Image** | 26.01-py3 | **25.12.post1-py3** | FlashInfer regression fix |
| **vLLM Version** | 0.12.1 | **0.12.0+nv25.12.post1** | NGC build |
| **FlashInfer** | 0.6.0 stable | **0.6.0rc2** | SM121 safe |
| **MOE Backend** | `latency` | **`throughput`** | Recommended for 25.12.post1 |
| **gpu-memory-utilization** | 0.40 | **0.75** | KV cache: 28 GB → 68 GB (4.7M tokens) |

### Performance Results (Sprint 126)

| Metric | Value |
|--------|-------|
| **Generation Throughput** | 49.7 tok/s (stable) |
| **TTFT Cold** | ~9 tok/s (first request: CUDA graph compile) |
| **TTFT Warm** | ~54 tok/s (subsequent requests) |
| **KV Cache Size** | 68 GiB / 4.7M tokens |
| **Stability** | ✅ Stable across 6+ consecutive requests (no crashes) |
| **Startup Time** | ~330s (model load 110s + kernel compile + CUDA graphs) |

**Previous Behavior:** 26.01-py3 crashed with `cudaErrorIllegalInstruction` after 1-2 requests, forcing container restart.

### Docker Compose Update

```yaml
# docker-compose.dgx-spark.yml
services:
  vllm:
    image: nvcr.io/nvidia/vllm:25.12.post1-py3  # Changed from 26.01-py3
    environment:
      - VLLM_USE_FLASHINFER_MOE_FP4=1
      - VLLM_FLASHINFER_MOE_BACKEND=throughput  # Changed from latency
      - VLLM_FASTSAFETENSORS_NOGDS=1
      - VLLM_GPU_MEMORY_UTILIZATION=0.75  # Changed from 0.40
```

### Ollama Thinking Optimization

Extraction model no longer uses thinking tokens (too slow for ingestion):

```bash
# .env
AEGIS_LLM_THINKING=false  # Disable thinking for extraction
```

**Impact:** 668s → 33s per document (~20x faster when thinking disabled)

---

## vLLM SM121 CUDA Crash Analysis (Sprint 128)

### The Problem

During Sprint 128.6 domain prompt verification (35 domains, 753 vLLM requests over ~36 hours), **49 requests failed (6.6%)** due to intermittent `cudaErrorIllegalInstruction`. Each crash kills vLLM's async engine, affecting all in-flight requests.

**Crash location (consistent):**
```
flashinfer-fused_moe-sm_121a/flashinfer_moe_grouped_gemm.cu:1253
in cutlass::gemm::collective::CollectiveMma<...>::load()
```

**Root cause:** DGX Spark (GB10) is SM121 architecture. NGC's vLLM image compiles CUTLASS kernels for SM120 and runs them on SM121 via PTX forward compatibility (`12.0+PTX`). Under concurrent load, some CUTLASS grouped GEMM instructions are illegal on SM121.

### Experiment 1: `VLLM_MOE_USE_DEEP_GEMM=0` (Applied 2026-02-09)

DeepGemm is an FP8-specific optimization. Our model (Nemotron-3-Nano-NVFP4) doesn't use FP8, so disabling it has ~0% performance impact. Added to `docker-compose.dgx-spark.yml`:

```yaml
- VLLM_MOE_USE_DEEP_GEMM=0
```

**Side effect:** Invalidates FlashInfer JIT cache → forces recompilation of 63 CUTLASS MoE kernels at startup (~90s with cached dependencies). Needs >20 GB RAM during compilation (`ninja -j 12`). OOM-killed when running concurrent with Docker builds.

### Experiment 2: eugr/spark-vllm-docker (Community Image)

Community Docker image that builds vLLM with **native SM121 compilation** (`TORCH_CUDA_ARCH_LIST=12.1a`, CUDA 13.1.1) instead of NGC's `12.0+PTX` forward compatibility. Uses latest vLLM release wheels for aarch64.

**Source:** [`eugr/spark-vllm-docker`](https://github.com/eugr/spark-vllm-docker) — `Dockerfile.wheels`
**Local tag:** `aegis-vllm-eugr:latest`

**Key advantages:**
- Native SM121 CUTLASS kernels (no PTX translation)
- Latest vLLM release (potential SM121-specific fixes)
- Latest FlashInfer (potential autotuner improvements)
- Smaller image (~15-20 GB vs NGC ~30 GB)

### A/B Test Protocol

| Test | Image | Config | Target |
|------|-------|--------|--------|
| Baseline | NGC 25.12.post1-py3 | DeepGemm ON | 93.4% success (Sprint 128.6) |
| Test A | NGC 25.12.post1-py3 | DeepGemm OFF | 0 crashes / 50 requests |
| Test B | aegis-vllm-eugr | Default | 0 crashes / 50 requests |

### FlashInfer JIT Cache Notes

- **Cache location:** `~/.cache/flashinfer/0.6.0+.../121a/cached_ops/fused_moe_120/`
- **63 CUTLASS MoE kernels** compiled at startup via ninja
- **Parallelism:** `ninja -j 12` — requires >20 GB RAM
- **Cache invalidation triggers:** Changing `VLLM_MOE_USE_DEEP_GEMM`, FlashInfer version update, clearing `~/.cache/flashinfer/`
- **OOM protection:** Don't run Docker builds concurrently with FlashInfer JIT compilation

### Relevant Links

- **eugr image:** https://github.com/eugr/spark-vllm-docker
- **eelbaz setup:** https://github.com/eelbaz/dgx-spark-vllm-setup
- **avarok NVFP4:** https://github.com/avarok/vllm-nvfp4-gb10-sm120
- **NVIDIA Playbooks:** https://build.nvidia.com/spark
- **Forum:** https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719

---

## LangSmith Tracing (Sprint 115+)

### Setup Details

**KRITISCH:** `.env` Variablen müssen beim Container-Start gesetzt sein (nicht zur Laufzeit), da LangGraph diese beim Import liest.

```bash
# In .env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=aegis-rag-sprint115

# Docker-Compose setzt automatisch:
LANGCHAIN_TRACING_V2=${LANGSMITH_TRACING}
LANGCHAIN_API_KEY=${LANGSMITH_API_KEY}
LANGCHAIN_PROJECT=${LANGSMITH_PROJECT}
```

### Container Restart bei Env-Änderungen

**WICHTIG:** `docker compose restart` lädt `.env` NICHT neu!

```bash
# ✅ RICHTIG
docker compose -f docker-compose.dgx-spark.yml up -d --force-recreate api

# ❌ FALSCH
docker compose restart api
```

### LangSmith API Queries

```bash
# API Key (aus .env)
API_KEY="lsv2_pt_..."

# Projekte auflisten
curl -s "https://api.smith.langchain.com/api/v1/sessions" \
  -H "x-api-key: $API_KEY"

# Einzelnen Trace abrufen (funktioniert immer)
curl -s "https://api.smith.langchain.com/api/v1/runs/{run_id}" \
  -H "x-api-key: $API_KEY"

# Traces per trace_id (funktioniert)
curl -s -X POST "https://api.smith.langchain.com/api/v1/runs/query" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"trace": "{trace_id}", "limit": 10}'
```

**ACHTUNG:** Query mit `session` Filter funktioniert NICHT zuverlässig! UI verwenden: https://smith.langchain.com

### Bekannte Einschränkungen

| Feature | Status | Workaround |
|---------|--------|------------|
| `/runs/query` mit `session` Filter | ❌ Bug | UI verwenden |
| `/runs/{id}` einzelner Trace | ✅ Funktioniert | - |
| LangGraph Auto-Tracing | ✅ Funktioniert | `LANGCHAIN_*` vars beim Start |
| `@traceable` Decorator | ✅ Funktioniert | Für custom Functions |

---

## E2E Testing mit Playwright (Sprint 108+)

### Test Execution
```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --reporter=list
```

### Test Groups (200 Tests)
- **Group 01-03:** MCP Tools, Bash, Python (38 tests)
- **Group 04-06:** Browser Tools, Skills (23 tests skipped - need data-testids)
- **Group 07:** Memory Management (11 failures - missing data-testids)
- **Group 08-09:** Deep Research, Long Context (22 tests)
- **Group 10-12:** Hybrid Search, Upload, Graph (35 tests)
- **Group 13-15:** Agent Hierarchy, GDPR, Explainability (48 tests)
- **Group 16:** MCP Marketplace (12 tests)

### Current Status (Sprint 108)
- **Pass Rate:** 65% (130/200)
- **Failed:** 39 tests (19.5%)
- **Skipped:** 31 tests (15.5%)

### Testing Strategy
1. **Nach jedem Code-Change:** Container mit `--no-cache` rebuilden
2. **Dokumentation:** `docs/e2e/PLAYWRIGHT_E2E.md` aktualisieren
3. **Temp Docs:** Während Test-Runs in `docs/e2e/` erstellen
4. **Sprint Planning:** Test-Tasks in Sprint-Plan dokumentieren
5. **Archivierung:** Alte Docs nach `docs/e2e/archive/`

### Common E2E Issues & Fixes
- **Timing:** 50-100% overhead vs API-only tests
- **Selectors:** Scoped selectors (`.within()`, `parent.getByTestId()`)
- **Mock APIs:** Graceful fallbacks (components cache data)
- **File Inputs:** Hidden inputs need `.count()` not `.toBeVisible()`
- **TypeScript:** Never export interfaces from runtime code

### Lazy Import Patching (KRITISCH!)
```python
# ❌ FALSCH
patch("src.api.v1.chat.get_redis_memory")

# ✅ RICHTIG - patch at source module
patch("src.components.memory.get_redis_memory")
```

---



---

## Repository-Struktur

```
aegis-rag/
├── src/
│   ├── agents/              # LangGraph Agents
│   ├── domains/             # Domain-driven modules
│   │   ├── document_processing/
│   │   ├── knowledge_graph/
│   │   ├── vector_search/
│   │   ├── memory/
│   │   └── llm_integration/
│   ├── core/                # Config, Logging
│   └── api/                 # FastAPI Endpoints
├── tests/                   # Unit, Integration, E2E
├── frontend/                # React 19 Frontend
├── docs/                    # Dokumentation
│   ├── adr/                 # Architecture Decisions
│   ├── sprints/             # Sprint Plans
│   └── technical-debt/      # TD Items
└── docker/                  # Docker configs
```

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Simple Query (Vector) | <200ms p95 |
| Hybrid Query (Vector+Graph) | <500ms p95 |
| Complex Multi-Hop | <1000ms p95 |
| Sustained Load | 50 QPS |

---

## Links zu erweiterten Ressourcen

**Externe Dokumentation:**
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [BGE-M3 Paper](https://arxiv.org/abs/2402.03216)
- [RAGAS Documentation](https://docs.ragas.io/)

**Interne Deep-Dives:**
- [RAGAS Journey](docs/ragas/RAGAS_JOURNEY.md)
- [Playwright E2E Guide](docs/e2e/PLAYWRIGHT_E2E.md)
- [Context Refresh](docs/CONTEXT_REFRESH.md)
- [Conventions](docs/CONVENTIONS.md)
