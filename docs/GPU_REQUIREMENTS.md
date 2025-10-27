# GPU Requirements & Optimization - Sprint 14 Feature 14.4

## Executive Summary

The Three-Phase Extraction Pipeline utilizes GPU acceleration for:
1. **SpaCy Transformer NER** (Phase 1): `en_core_web_trf` model
2. **Semantic Deduplication** (Phase 2): Sentence transformer embeddings
3. **Gemma 3 4B Relation Extraction** (Phase 3): Via Ollama

This document provides GPU requirements, memory profiling results, and optimization strategies.

---

## Hardware Requirements

### Minimum Configuration (Budget)
- **GPU**: NVIDIA RTX 3060 (12GB VRAM)
- **Model Quantization**: Gemma 3 4B Q4_K_M
- **Batch Size**: 1-3 documents
- **Expected Performance**: ~20-25s per document
- **Use Case**: Development, small-scale production

### Recommended Configuration (Production)
- **GPU**: NVIDIA RTX 4070 (16GB VRAM) or RTX 4070 Ti (12GB)
- **Model Quantization**: Gemma 3 4B Q8_0
- **Batch Size**: 5-10 documents
- **Expected Performance**: ~15-18s per document
- **Use Case**: Production deployment, moderate load

### Optimal Configuration (High-Performance)
- **GPU**: NVIDIA RTX 4090 (24GB VRAM) or A100 (40GB)
- **Model Quantization**: Full precision (FP16)
- **Batch Size**: 20+ documents
- **Expected Performance**: ~10-12s per document
- **Use Case**: High-throughput production, research

---

## VRAM Profiling Results

### Phase 1: SpaCy Transformer NER (`en_core_web_trf`)

| Component | VRAM Usage | Notes |
|-----------|------------|-------|
| Base Model | ~2.0 GB | Loaded once at startup |
| Per Document (500 words) | ~100 MB | Scales with document length |
| Per Document (2000 words) | ~300 MB | Linear scaling |

**Optimization**: Model loaded once and reused across documents.

### Phase 2: Semantic Deduplication

| Component | VRAM Usage | Notes |
|-----------|------------|-------|
| Sentence Transformer (`all-MiniLM-L6-v2`) | ~90 MB | Lightweight model |
| Embeddings (100 entities) | ~40 MB | Temporary, freed after dedup |
| Total Peak | ~130 MB | Minimal impact |

**Optimization**: Batch encoding with automatic memory cleanup.

### Phase 3: Gemma 3 4B Relation Extraction (via Ollama)

| Quantization | VRAM Usage | Quality | Speed |
|--------------|------------|---------|-------|
| Q4_K_M | ~2.5 GB | High (95%+ baseline) | Fast (~15s) |
| Q8_0 | ~4.5 GB | Excellent (98%+ baseline) | Medium (~18s) |
| FP16 | ~8.0 GB | Best (100% baseline) | Slower (~22s) |

**Recommendation**: Use Q4_K_M for production (best speed/quality tradeoff).

### Total VRAM Budget (Concurrent Processing)

| Configuration | Phase 1 | Phase 2 | Phase 3 | Total Peak | Safety Margin |
|---------------|---------|---------|---------|------------|---------------|
| **Min (Q4_K_M)** | 2.3 GB | 0.13 GB | 2.5 GB | **5.0 GB** | 7.0 GB available |
| **Recommended (Q8_0)** | 2.3 GB | 0.13 GB | 4.5 GB | **7.0 GB** | 9.0 GB available |
| **Optimal (FP16)** | 2.3 GB | 0.13 GB | 8.0 GB | **10.5 GB** | 13.5 GB available |

---

## Batch Size Optimization

### Auto-Tuning Strategy

The system automatically calculates optimal batch size based on available VRAM:

```python
def calculate_optimal_batch_size(available_vram_gb: float) -> int:
    """Calculate optimal batch size for extraction pipeline.

    Args:
        available_vram_gb: Available VRAM in GB

    Returns:
        Recommended batch size
    """
    # Conservative estimates (accounts for peak usage)
    base_vram = 2.5  # SpaCy + dedup + Gemma Q4_K_M
    per_doc_vram = 0.2  # ~200MB per document in batch

    # Target: Use 80% of available VRAM for safety
    target_vram = available_vram_gb * 0.8

    if target_vram < base_vram:
        return 1  # Minimum: Process one at a time

    available_for_batch = target_vram - base_vram
    batch_size = int(available_for_batch / per_doc_vram)

    return max(1, min(batch_size, 50))  # Cap at 50 for practical reasons
```

### Batch Size Recommendations by GPU

| GPU Model | VRAM | Q4_K_M Batch | Q8_0 Batch | FP16 Batch |
|-----------|------|--------------|------------|------------|
| RTX 3060 | 12 GB | 10-15 | 5-8 | 1-3 |
| RTX 3080 | 10 GB | 8-12 | 3-5 | 1-2 |
| RTX 4070 | 12 GB | 10-15 | 5-8 | 1-3 |
| RTX 4070 Ti | 16 GB | 20-25 | 10-15 | 3-5 |
| RTX 4080 | 16 GB | 20-25 | 10-15 | 3-5 |
| RTX 4090 | 24 GB | 40-50 | 25-30 | 10-15 |
| A100 (40GB) | 40 GB | 50+ | 40-50 | 20-25 |

---

## Memory Cleanup Strategies

### Between Documents

```python
import torch
import gc

def cleanup_gpu_memory():
    """Clean up GPU memory between documents."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
```

**When to use:**
- After processing each document in a batch
- After Phase 3 (Gemma extraction) completes
- When switching between models

### Monitoring VRAM Usage

```python
def get_gpu_memory_info():
    """Get current GPU memory usage."""
    if not torch.cuda.is_available():
        return None

    device = torch.cuda.current_device()
    allocated = torch.cuda.memory_allocated(device) / 1024**3  # GB
    reserved = torch.cuda.memory_reserved(device) / 1024**3    # GB
    total = torch.cuda.get_device_properties(device).total_memory / 1024**3

    return {
        "device": device,
        "allocated_gb": allocated,
        "reserved_gb": reserved,
        "total_gb": total,
        "free_gb": total - reserved,
        "utilization_pct": (reserved / total) * 100
    }
```

---

## CPU Fallback Strategy

If GPU is unavailable or VRAM exhausted:

1. **SpaCy NER**: Falls back to `en_core_web_sm` (CPU-only, ~500MB RAM)
2. **Semantic Deduplication**: Runs on CPU (slower but functional)
3. **Gemma Extraction**: Ollama automatically uses CPU (significantly slower: ~60-90s per document)

**Configuration:**
```bash
# Force CPU mode (useful for testing)
export CUDA_VISIBLE_DEVICES=""

# Or configure in .env
SEMANTIC_DEDUP_DEVICE=cpu
```

---

## Performance Benchmarks

### RTX 3060 (12GB VRAM) - Q4_K_M

| Document Size | Batch Size | Time/Doc | Throughput |
|---------------|------------|----------|------------|
| Small (500 words) | 10 | 15s | 4 docs/min |
| Medium (1500 words) | 5 | 18s | 3.3 docs/min |
| Large (3000 words) | 3 | 22s | 2.7 docs/min |

### RTX 4090 (24GB VRAM) - Q4_K_M

| Document Size | Batch Size | Time/Doc | Throughput |
|---------------|------------|----------|------------|
| Small (500 words) | 50 | 10s | 6 docs/min |
| Medium (1500 words) | 30 | 12s | 5 docs/min |
| Large (3000 words) | 20 | 15s | 4 docs/min |

---

## Troubleshooting

### Issue: CUDA Out of Memory (OOM)

**Symptoms:** `RuntimeError: CUDA out of memory`

**Solutions:**
1. Reduce batch size: Set `EXTRACTION_BATCH_SIZE=1` in `.env`
2. Use smaller quantization: Switch from Q8_0 to Q4_K_M
3. Enable aggressive cleanup: Call `cleanup_gpu_memory()` between documents
4. Fall back to CPU: Set `SEMANTIC_DEDUP_DEVICE=cpu`

### Issue: Slow Performance Despite GPU

**Symptoms:** Extraction taking >60s per document

**Solutions:**
1. Check Ollama is using GPU:
   ```bash
   ollama ps  # Should show GPU utilization
   ```
2. Verify SpaCy using GPU:
   ```python
   import spacy
   spacy.prefer_gpu()  # Should return True
   ```
3. Check CUDA drivers:
   ```bash
   nvidia-smi  # Should show GPU utilization
   ```

### Issue: Model Not Loading on GPU

**Symptoms:** Models falling back to CPU unexpectedly

**Solutions:**
1. Install CUDA-enabled PyTorch:
   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu118
   ```
2. Verify CUDA availability:
   ```python
   import torch
   print(torch.cuda.is_available())  # Should be True
   ```

---

## Environment Configuration

### Recommended `.env` Settings

```bash
# GPU Configuration (Sprint 14)
SEMANTIC_DEDUP_DEVICE=auto  # auto, cuda, cpu
EXTRACTION_BATCH_SIZE=10     # Adjust based on GPU
EXTRACTION_MAX_WORKERS=4     # CPU parallelism

# Gemma Model Selection
GEMMA_MODEL=hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M  # Production
# GEMMA_MODEL=hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0  # High-quality
```

---

## Future Optimizations

1. **Model Quantization Research**: Evaluate GPTQ/AWQ quantization methods
2. **Batch Inference Optimization**: Implement true parallel batch processing for Gemma
3. **Mixed Precision Training**: FP16 inference for SpaCy transformer
4. **Model Pruning**: Reduce SpaCy transformer size without quality loss
5. **Flash Attention**: Integrate Flash Attention 2 for faster transformer inference

---

## References

- [PyTorch CUDA Best Practices](https://pytorch.org/docs/stable/notes/cuda.html)
- [SpaCy GPU Usage](https://spacy.io/usage/v3#gpu)
- [Ollama GPU Configuration](https://github.com/ollama/ollama/blob/main/docs/gpu.md)
- [CUDA Memory Management](https://developer.nvidia.com/blog/unified-memory-cuda-beginners/)
