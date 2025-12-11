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

## Referenz-Dateien
- `docker-compose.dgx-spark.yml` - Aktuelle CPU-Mode Konfiguration
- `docker/Dockerfile.docling-spark` - Production Dockerfile
- `DGX_SPARK_SM121_REFERENCE.md` - Vollständige technische Referenz

## Links
- vLLM Setup: https://github.com/eelbaz/dgx-spark-vllm-setup
- NVIDIA Playbooks: https://build.nvidia.com/spark
- Forum: https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719
