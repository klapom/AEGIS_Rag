# DGX Spark GB10 (sm_121) - Technische Referenz für Claude Code

## Hardware-Spezifikation
```
GPU:              NVIDIA GB10 (Blackwell Architecture)
CUDA Capability:  12.1 → sm_121 / sm_121a
Memory:           128GB Unified (CPU + GPU shared)
CPU:              20 ARM Cortex Cores (aarch64)
CUDA Version:     13.0
Driver:           580.95.05+
OS:               Ubuntu 24.04 LTS
```

---

## Kern-Problem: sm_121 Support

### Status der Framework-Unterstützung (Stand: Dezember 2025)

| Framework | Version | sm_121 Support | Anmerkung |
|-----------|---------|----------------|-----------|
| PyTorch cu130 | 2.9.0+cu130 | ⚠️ Warnung, funktioniert | Offizielle Wheels |
| PyTorch cu128 | 2.7.0+cu128 | ❌ Nur bis sm_120 | Deutlich langsamer |
| Triton | 3.5.0+git (main) | ✅ sm_121a | Muss von Source gebaut werden |
| TensorFlow | alle | ❌ | Offiziell nicht mehr unterstützt |
| TensorRT | 10.x | ❌ Nur sm_120 | Kein sm_121 |
| ONNX Runtime | - | ❌ | Muss selbst kompiliert werden |
| llama.cpp | aktuell | ✅ | Funktioniert nativ |

### Bekannte Fehlermeldungen
```
# PyTorch nvrtc Fehler
nvrtc: error: invalid value for --gpu-architecture (-arch)

# PyTorch Capability Warnung (ignorierbar mit cu130)
UserWarning: Found GPU0 NVIDIA GB10 which is of cuda capability 12.1.
PyTorch supports (8.0) - (12.0), not 12.1!

# Triton ptxas Fehler (alte Version)
ptxas fatal : Value 'sm_121a' is not defined for option 'gpu-name'

# Flash Attention Kernel Fehler
FATAL: kernel fmha_cutlassF_f16_aligned_64x128_rf_sm80 is for sm80-sm100, but was built for sm121
```

---

## Funktionierende Konfigurationen

### 1. PyTorch cu130 (Empfohlen für ML-Workloads)
```bash
# Umgebungsvariablen
export TORCH_CUDA_ARCH_LIST="12.1a"
export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas

# Installation
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
```

### 2. NGC Container (Offiziell unterstützt)
```bash
# PyTorch Container mit CUDA 13.0.1
docker run -it --gpus=all \
  -v /usr/local/cuda:/usr/local/cuda:ro \
  nvcr.io/nvidia/pytorch:25.09-py3 \
  bash

# CUDA Base Image
docker run -it --gpus=all \
  -v /usr/local/cuda:/usr/local/cuda:ro \
  nvcr.io/nvidia/cuda:13.0.1-devel-ubuntu24.04 \
  bash
```

### 3. Triton von Source (für vLLM/Custom Kernels)
```bash
git clone https://github.com/triton-lang/triton.git
cd triton
pip install pip cmake ninja pybind11
TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas python -m pip install --no-build-isolation .
```

### 4. ONNX Runtime selbst kompilieren
```bash
git clone --recursive https://github.com/Microsoft/onnxruntime.git
sudo apt-get -y install cudnn9-cuda-13

sh build.sh --config Release --build_dir build/cuda13 --parallel 20 --nvcc_threads 20 \
    --use_cuda --cuda_version 13.0 --cuda_home /usr/local/cuda-13.0/ \
    --cudnn_home /usr/local/cuda-13.0/ \
    --build_wheel --skip_tests \
    --cmake_generator Ninja \
    --use_binskim_compliant_compile_flags \
    --cmake_extra_defines CMAKE_CUDA_ARCHITECTURES=121 onnxruntime_BUILD_UNIT_TESTS=OFF

pip install build/cuda13/Release/dist/*.whl
```

### 5. llama.cpp (Funktioniert out-of-the-box)
```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp

cmake -B build -DGGML_CUDA=ON -DLLAMA_CURL=ON
cmake --build build --config Release -j 20

# Server starten
./build/bin/llama-server --no-mmap --jinja --host 0.0.0.0 --port 5000 \
  --ctx-size 32768 --model <model.gguf>
```

---

## vLLM Installation (Getestet)

### Automatisch (empfohlen)
```bash
curl -fsSL https://raw.githubusercontent.com/eelbaz/dgx-spark-vllm-setup/main/install.sh | bash
```

### Manuell
```bash
# 1. uv installieren
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 2. Virtual Environment
mkdir -p vllm-install && cd vllm-install
uv venv .vllm --python 3.12
source .vllm/bin/activate

# 3. PyTorch cu130
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

# 4. Triton von main
git clone https://github.com/triton-lang/triton.git
cd triton
uv pip install pip cmake ninja pybind11
TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas python -m pip install --no-build-isolation .
cd ..

# 5. Dependencies
uv pip install xgrammar setuptools-scm apache-tvm-ffi==0.1.0b15 --prerelease=allow

# 6. vLLM klonen und patchen
git clone --recursive https://github.com/vllm-project/vllm.git
cd vllm
git checkout v0.11.1rc3

# 7. KRITISCHER FIX: CMakeLists.txt patchen
# Zeile ~671: cuda_archs_loose_intersection(SCALED_MM_ARCHS "10.0f;11.0f;12.0f" "${CUDA_ARCHS}")
# Zeile ~673: cuda_archs_loose_intersection(SCALED_MM_ARCHS "10.0a;12.1a" "${CUDA_ARCHS}")
```

### vLLM CMakeLists.txt Patch
```diff
# CUDA 13.0+ path (Zeile ~671)
- cuda_archs_loose_intersection(SCALED_MM_ARCHS "10.0f;11.0f" "${CUDA_ARCHS}")
+ cuda_archs_loose_intersection(SCALED_MM_ARCHS "10.0f;11.0f;12.0f" "${CUDA_ARCHS}")

# Older CUDA path (Zeile ~673)
- cuda_archs_loose_intersection(SCALED_MM_ARCHS "10.0a" "${CUDA_ARCHS}")
+ cuda_archs_loose_intersection(SCALED_MM_ARCHS "10.0a;12.1a" "${CUDA_ARCHS}")
```

---

## AI Toolkit (Ostris) Installation

```bash
# 1. Node.js ARM64
wget https://nodejs.org/dist/v24.11.1/node-v24.11.1-linux-arm64.tar.xz
tar -xf node-v24.11.1-linux-arm64.tar.xz
export PATH="/opt/node-v24.11.1-linux-arm64/bin:$PATH"

# 2. Miniconda mit Python 3.11
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh
chmod u+x Miniconda3-latest-Linux-aarch64.sh
./Miniconda3-latest-Linux-aarch64.sh
conda create --name ai-toolkit python=3.11
conda activate ai-toolkit

# 3. PyTorch cu130 (WICHTIG: nicht cu128!)
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

# 4. ai-toolkit klonen
git clone https://github.com/ostris/ai-toolkit.git
cd ai-toolkit

# 5. requirements.txt anpassen - ENTFERNEN:
#    git+https://github.com/jaretburkett/easy_dwpose.git
# HINZUFÜGEN:
#    scipy==1.16.0
#    tifffile==2025.6.11
#    imageio==2.37.0
#    scikit_image==0.25.2
#    clean_fid==0.1.35
#    pywavelets==1.9.0
#    contourpy==1.3.3
#    opencv_python_headless==4.11.0.86

pip3 install -r requirements.txt

# 6. UI bauen
cd ui
npm run build_and_start
```

---

## Docker Best Practices

### Basis-Dockerfile für DGX Spark
```dockerfile
FROM nvcr.io/nvidia/pytorch:25.09-py3

# ODER für manuelle Installation:
# FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# System-Dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential wget curl ca-certificates git \
    python3 python3-pip python3-venv \
    libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# PyTorch cu130 (falls nicht NGC Container)
RUN pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu130

WORKDIR /app
```

### Docker Run Kommando
```bash
docker run -it --gpus=all \
  -v /usr/local/cuda:/usr/local/cuda:ro \
  -v $(pwd):/workspace \
  -p 8000:8000 \
  <image_name> bash
```

---

## Umgebungsvariablen (Vollständig)

```bash
# CUDA/PyTorch
export TORCH_CUDA_ARCH_LIST="12.1a"
export CUDA_HOME=/usr/local/cuda-13.0
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# Triton
export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas

# vLLM
export VLLM_USE_FLASHINFER_MXFP4_MOE=1

# nvcc Path Fix (falls nötig)
export CUDACXX=/usr/local/cuda-13.0/bin/nvcc

# CPU-Fallback deaktivieren (für Debugging)
# export CUDA_VISIBLE_DEVICES=0
```

---

## Performance-Hinweise

### cu130 vs cu128
- cu130: ~10-12 sec/iteration (Training)
- cu128: ~30+ sec/iteration (Training)
- Sample Generation: cu130 ~5min, cu128 ~30min

### Speicher-Management
- 128GB Unified Memory (CPU + GPU shared)
- ~119GB nutzbar (OS/System reserviert ~9GB)
- Bei OOM: Caches leeren mit `sudo sh -c "sync; echo 3 > /proc/sys/vm/drop_caches"`

### llama.cpp Benchmark
- Qwen3-235B (IQ3_M): ~15 tok/s
- Memory: ~107GB

---

## Häufige Probleme und Lösungen

### Problem: `/usr/bin/nvcc` statt `/usr/local/cuda/bin/nvcc`
```bash
# Prüfen
which nvcc
/usr/bin/nvcc --version  # Falls alt (12.0)

# Lösung: Alte Version entfernen
sudo apt remove nvidia-cuda-toolkit

# ODER: cmake mit explizitem Pfad
cmake -DCMAKE_CUDA_COMPILER=/usr/local/cuda-13.0/bin/nvcc ...
```

### Problem: Flash Attention kompiliert nicht
```bash
# Lösung: cuDNN SDPA Backend verwenden
# In Python Code:
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(True)
```

### Problem: PEP 668 "externally-managed-environment"
```bash
pip install --break-system-packages <package>
```

---

## Referenz-Links

- **Playbooks**: https://build.nvidia.com/spark
- **Forum**: https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719
- **vLLM Setup**: https://github.com/eelbaz/dgx-spark-vllm-setup
- **NGC PyTorch**: https://catalog.ngc.nvidia.com/orgs/nvidia/containers/pytorch
- **Porting Guide**: https://docs.nvidia.com/dgx/dgx-spark-porting-guide/

---

## Für Document Layout Detection (Docling)

### Aktueller Status
- PyTorch-basierte Modelle: ⚠️ Mit cu130 möglich, aber nicht getestet
- ONNX Runtime: Muss selbst kompiliert werden mit `CMAKE_CUDA_ARCHITECTURES=121`
- TensorRT: ❌ Kein sm_121 Support
- PaddlePaddle: ❌ Kein ARM64 Support

### Empfohlene Vorgehensweise
1. Docling mit PyTorch cu130 testen
2. Falls ONNX benötigt: selbst kompilieren
3. Alternativ: LLM-basierte Dokumentenverarbeitung (funktioniert mit llama.cpp/vLLM)

---

*Erstellt: Dezember 2025 | Quellen: NVIDIA Forums, GitHub, PyTorch Forums*
