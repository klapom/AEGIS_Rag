# CLAUDE.md - DGX Spark Projekt-Kontext

## Projekt-Übersicht
Document Layout Detection auf NVIDIA DGX Spark (GB10, sm_121).
Aktuelles Problem: Framework-Kompatibilität mit CUDA capability 12.1.

## Hardware-Kontext
- GPU: NVIDIA GB10 (Blackwell, sm_121)
- CUDA: 13.0, Driver 580.95.05
- Memory: 128GB Unified
- CPU: 20 ARM Cortex (aarch64)
- OS: Ubuntu 24.04

## Kritische Erkenntnisse

### Was funktioniert
1. **PyTorch cu130** - `pip install torch --index-url https://download.pytorch.org/whl/cu130`
2. **NGC Container** - `nvcr.io/nvidia/pytorch:25.09-py3` oder neuer
3. **llama.cpp** - Native CUDA Kompilierung funktioniert
4. **Triton von main** - Muss von Source gebaut werden für sm_121a

### Was NICHT funktioniert
1. PyTorch cu128 oder älter → `nvrtc: error: invalid value for --gpu-architecture`
2. TensorFlow → Offiziell nicht mehr unterstützt auf DGX Spark
3. TensorRT → Kein sm_121 Support (nur bis sm_120)
4. PaddlePaddle → Kein ARM64 Support
5. ONNX Runtime Wheels → Müssen selbst kompiliert werden

### Wichtige Umgebungsvariablen
```bash
export TORCH_CUDA_ARCH_LIST="12.1a"
export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas
export CUDACXX=/usr/local/cuda-13.0/bin/nvcc
```

## Aufgaben für Claude Code

### Priorität 1: Docling mit cu130 testen
```bash
# Erstelle venv mit cu130
python3.12 -m venv ~/docling-cu130
source ~/docling-cu130/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
pip install docling

# Test
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

### Priorität 2: Falls ONNX benötigt - selbst kompilieren
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

### Priorität 3: Docker-basierte Lösung
```dockerfile
FROM nvcr.io/nvidia/pytorch:25.09-py3
RUN pip install --break-system-packages docling
WORKDIR /workspace
```

## Bekannte Workarounds

### Flash Attention Fehler
```python
# In Python Code vor Model-Load:
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

## Referenz-Dateien
- `docker-compose.dgx-spark.yml` - Docker Konfiguration inkl. Ollama
- `docker/Dockerfile.docling-spark` - Production Dockerfile
- `DGX_SPARK_SM121_REFERENCE.md` - Vollständige technische Referenz

## vLLM SM121 Stability Fix (Sprint 126)

### Container Image & FlashInfer Regression

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

**Forum Reference:** https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4/359074

---

## Links
- vLLM Setup: https://github.com/eelbaz/dgx-spark-vllm-setup
- NVIDIA Playbooks: https://build.nvidia.com/spark
- Forum: https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719
