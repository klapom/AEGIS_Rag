# TD-072: Sentence-Transformers Reranking Investigation

**Status:** OPEN (Investigation)
**Priority:** LOW
**Story Points:** 5
**Created:** Sprint 60 Planning
**Target:** Sprint 60 (Investigation Only)

---

## Problem Statement

Reranking wird aktuell über Ollama (LLM-based) durchgeführt (TD-059, Sprint 48).
Sentence-Transformers Cross-Encoders könnten schneller und effizienter sein.

Eine Voruntersuchung soll klären:
1. Performance-Unterschiede (Latency, Throughput)
2. Qualitäts-Unterschiede (Ranking Accuracy)
3. Resource-Nutzung (VRAM, CPU)

---

## Current Implementation

```python
# Ollama-based Reranking (TD-059)
# src/components/retrieval/reranker.py
class OllamaReranker:
    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        # LLM generates relevance scores
        ...
```

---

## Proposed Alternative

```python
# Sentence-Transformers Cross-Encoder
from sentence_transformers import CrossEncoder

class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        pairs = [(query, doc) for doc in documents]
        scores = self.model.predict(pairs)
        return scores
```

---

## Investigation Questions

### 1. Performance
- [ ] Latency per Document
- [ ] Batch Processing Speed
- [ ] Throughput (docs/sec)
- [ ] Scaling with Document Count

### 2. Quality
- [ ] Ranking Accuracy (NDCG, MRR)
- [ ] Correlation mit LLM-based Ranking
- [ ] Edge Cases (short docs, technical content)

### 3. Resources
- [ ] VRAM Usage
- [ ] CPU Usage
- [ ] Model Loading Time
- [ ] DGX Spark Kompatibilität

### 4. Models to Evaluate
| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| ms-marco-MiniLM-L-6-v2 | 90MB | Fast | Good |
| ms-marco-MiniLM-L-12-v2 | 135MB | Medium | Better |
| bge-reranker-base | 300MB | Medium | Best |
| bge-reranker-large | 1.3GB | Slow | Excellent |

---

## Benchmark Plan

### Test Setup
```yaml
Hardware: DGX Spark (GB10, 128GB)
Query Set: 100 diverse queries
Document Set: 20 candidates per query
Baseline: Ollama Reranker (current)
```

### Metrics
| Metric | Description |
|--------|-------------|
| Latency | Time to rerank 20 docs |
| Quality | NDCG@10 vs ground truth |
| Memory | Peak VRAM usage |
| Throughput | Queries/second |

---

## Expected Outcomes

| Finding | Action |
|---------|--------|
| ST significantly faster, quality similar | Create Migration TD |
| ST faster but quality lower | Hybrid approach TD |
| ST slower or incompatible | Keep Ollama, close TD |
| ST better in all metrics | Urgent Migration TD |

---

## Investigation Tasks

1. [ ] Sentence-Transformers auf DGX Spark installieren
2. [ ] Benchmark-Suite erstellen
3. [ ] Ollama Reranker Baseline messen
4. [ ] Cross-Encoder Benchmarks
5. [ ] Quality-Vergleich (A/B Test)
6. [ ] Ergebnisse dokumentieren
7. [ ] Empfehlung aussprechen

---

## Acceptance Criteria

- [ ] Benchmark-Ergebnisse dokumentiert
- [ ] Quality-Vergleich durchgeführt
- [ ] Resource-Usage analysiert
- [ ] Empfehlung mit Begründung
- [ ] Falls Migration empfohlen: Follow-up TD

---

## References

- [Sentence-Transformers Cross-Encoders](https://www.sbert.net/docs/cross_encoder/pretrained_models.html)
- TD-059: Reranking via Ollama (Sprint 48)
- docs/components/OLLAMA_RERANKER.md
