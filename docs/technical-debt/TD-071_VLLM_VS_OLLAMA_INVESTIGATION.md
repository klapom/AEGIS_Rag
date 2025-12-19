# TD-071: vLLM vs Ollama Investigation

**Status:** OPEN (Investigation)
**Priority:** LOW
**Story Points:** 5
**Created:** Sprint 60 Planning
**Target:** Sprint 60 (Investigation Only)

---

## Problem Statement

Ollama wird aktuell für LLM Inference verwendet. vLLM bietet potenziell bessere Performance
für Production-Workloads. Eine Voruntersuchung soll klären, ob ein Wechsel sinnvoll ist.

---

## Investigation Questions

### 1. Performance
- [ ] Throughput (tokens/sec) Vergleich
- [ ] Latency (TTFT, TPS) Vergleich
- [ ] Memory Efficiency
- [ ] Batch Processing Capabilities

### 2. Compatibility
- [ ] Unterstützte Models (Llama, Qwen, etc.)
- [ ] DGX Spark (sm_121) Kompatibilität
- [ ] CUDA 13.0 Support
- [ ] Docker Integration

### 3. Features
- [ ] Streaming Support
- [ ] Function Calling / Tool Use
- [ ] Embeddings Generation
- [ ] Multi-Model Serving

### 4. Operations
- [ ] Setup Complexity
- [ ] Monitoring/Metrics
- [ ] Model Loading Time
- [ ] Hot-Swapping Models

---

## Benchmark Plan

### Test Setup
```yaml
Hardware: DGX Spark (GB10, 128GB, CUDA 13.0)
Models: llama3.2:8b, qwen2.5:7b
Workloads:
  - Single Request Latency
  - Concurrent Requests (10, 50, 100)
  - Long Context (8k, 16k, 32k tokens)
  - Streaming vs Non-Streaming
```

### Metrics to Collect
| Metric | Description |
|--------|-------------|
| TTFT | Time to First Token |
| TPS | Tokens Per Second |
| P50/P95/P99 Latency | Percentile Latencies |
| Throughput | Requests/Second |
| VRAM Usage | Peak Memory |
| CPU Usage | During Inference |

---

## Expected Outcomes

### TD Creation Based on Results

| Finding | Action |
|---------|--------|
| vLLM significantly faster | Create TD for Migration |
| Similar performance | Keep Ollama (simpler) |
| vLLM incompatible | Document findings, close TD |
| Mixed results | Create TD for Hybrid Approach |

---

## Investigation Tasks

1. [ ] vLLM auf DGX Spark installieren (cu130 Kompatibilität prüfen)
2. [ ] Benchmark-Suite erstellen
3. [ ] Ollama Baseline messen
4. [ ] vLLM Benchmarks ausführen
5. [ ] Ergebnisse dokumentieren
6. [ ] Empfehlung aussprechen
7. [ ] Ggf. Follow-up TD erstellen

---

## Acceptance Criteria

- [ ] Benchmark-Ergebnisse dokumentiert
- [ ] Kompatibilität mit DGX Spark geprüft
- [ ] Empfehlung (migrate/keep) mit Begründung
- [ ] Falls Migration empfohlen: Follow-up TD erstellt

---

## References

- [vLLM Documentation](https://docs.vllm.ai/)
- [Ollama Documentation](https://ollama.com/docs)
- CLAUDE.md: DGX Spark Configuration
