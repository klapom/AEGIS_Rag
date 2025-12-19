# TD-073: Sentence-Transformers Embeddings Investigation

**Status:** OPEN (Investigation)
**Priority:** LOW
**Story Points:** 5
**Created:** Sprint 60 Planning
**Target:** Sprint 60 (Investigation Only)

---

## Problem Statement

Embeddings werden aktuell über Ollama generiert (BGE-M3 via Ollama).
Direkte Sentence-Transformers Integration könnte schneller sein.

**Hinweis:** Laut TD_INDEX.md wurde Embedding bereits auf BGE-M3 konsolidiert (sentence-transformers removed).
Diese Investigation prüft, ob eine **direkte** sentence-transformers Nutzung (ohne Ollama) Vorteile bringt.

---

## Current Implementation

```python
# Ollama-based Embeddings (BGE-M3)
# src/components/shared/embedding_service.py
class EmbeddingService:
    async def embed(self, text: str) -> list[float]:
        response = await ollama.embeddings(
            model="bge-m3",
            prompt=text
        )
        return response["embedding"]
```

---

## Proposed Alternative

```python
# Direct Sentence-Transformers (Native PyTorch)
from sentence_transformers import SentenceTransformer

class NativeEmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer("BAAI/bge-m3")
        self.model.to("cuda")  # GPU

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=True)
```

---

## Investigation Questions

### 1. Performance
- [ ] Single Text Latency
- [ ] Batch Processing Speed
- [ ] Throughput (texts/sec)
- [ ] Memory Efficiency

### 2. Compatibility
- [ ] DGX Spark (sm_121) CUDA Support
- [ ] Flash Attention Workaround nötig?
- [ ] PyTorch cu130 Kompatibilität

### 3. Quality
- [ ] Embedding Consistency (Ollama vs Native)
- [ ] Cosine Similarity Correlation
- [ ] Downstream Task Performance

### 4. Operations
- [ ] Model Loading Time
- [ ] Memory Management
- [ ] Multi-GPU Support
- [ ] Integration Complexity

---

## Benchmark Plan

### Test Setup
```yaml
Hardware: DGX Spark (GB10, 128GB, CUDA 13.0)
Model: BAAI/bge-m3 (1024-dim, multilingual)
Test Data:
  - 1000 short texts (avg 50 tokens)
  - 1000 long texts (avg 500 tokens)
  - 100 documents (avg 2000 tokens)
```

### Metrics
| Metric | Description |
|--------|-------------|
| Latency | Time per embedding |
| Batch Latency | Time for 100 embeddings |
| Throughput | Embeddings/second |
| VRAM | Peak memory usage |
| Quality | Cosine sim correlation |

---

## Expected Outcomes

| Finding | Action |
|---------|--------|
| Native 2x+ faster, compatible | Create Migration TD |
| Native faster but issues | Document workarounds, conditional TD |
| Similar performance | Keep Ollama (simpler architecture) |
| Native incompatible (sm_121) | Close TD, document findings |

---

## DGX Spark Considerations

Aus CLAUDE.md:
```python
# Flash Attention Workaround may be needed
import torch
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(True)
```

```bash
# Required Environment
export TORCH_CUDA_ARCH_LIST="12.1a"
export CUDACXX=/usr/local/cuda-13.0/bin/nvcc
```

---

## Investigation Tasks

1. [ ] Sentence-Transformers mit PyTorch cu130 installieren
2. [ ] BGE-M3 Model laden und testen
3. [ ] DGX Spark Kompatibilität prüfen
4. [ ] Benchmark-Suite erstellen
5. [ ] Ollama Baseline messen
6. [ ] Native Benchmarks
7. [ ] Quality-Vergleich (Embedding Similarity)
8. [ ] Ergebnisse dokumentieren

---

## Acceptance Criteria

- [ ] DGX Spark Kompatibilität geprüft
- [ ] Benchmark-Ergebnisse dokumentiert
- [ ] Quality-Vergleich durchgeführt
- [ ] Empfehlung mit Begründung
- [ ] Falls Migration empfohlen: Follow-up TD

---

## References

- [Sentence-Transformers BGE-M3](https://huggingface.co/BAAI/bge-m3)
- ADR-024: BGE-M3 Embeddings
- CLAUDE.md: DGX Spark Configuration
- TD_INDEX.md Note: "Embedding consolidation: All embedding tasks now use BGE-M3"
