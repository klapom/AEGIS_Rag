# Sprint 14: Benchmarking & Performance Optimization

**Sprint Period**: 2025-10-24 to 2025-10-27
**Goal**: Comprehensive benchmarking suite and production pipeline optimization

## Context

Sprint 14 focused on:
- Creating production-ready benchmarking tools
- Comparing Gemma quantization levels (Q8_0 vs Q4_0)
- Profiling GPU utilization
- Measuring extraction pipeline performance

## Archived Scripts (8 total)

### Production Benchmarks

1. **benchmark_production_pipeline.py**: Full pipeline benchmarking with memory profiling
2. **benchmark_models.py**: Compare LLM models for extraction tasks
3. **benchmark_feature_14_1.py**: Benchmark Feature 14.1 (LightRAG Graph-Based Provenance)

### Model Comparisons

4. **compare_gemma_quantizations.py**: Q8_0 vs Q4_0 vs Q6_K quantization comparison
5. **compare_models_with_think_false.py**: Test models without chain-of-thought

### Specialized Tests

6. **comprehensive_model_benchmark.py**: Multi-metric model evaluation
7. **benchmark_relation_extraction_only.py**: Isolated relation extraction benchmarking
8. **quick_model_test.py**: Fast model validation

## Key Findings

### Gemma Quantization Decision

**Selected**: Gemma 3 4B **Q8_0** (ADR-018)

| Quantization | Speed | Accuracy | VRAM | Decision |
|--------------|-------|----------|------|----------|
| Q8_0 | Baseline | 100% | 5.2GB | ✅ **SELECTED** |
| Q6_K | +15% | 98% | 4.1GB | ❌ Accuracy loss |
| Q4_0 | +30% | 92% | 3.2GB | ❌ Too much accuracy loss |

**Rationale**:
- RTX 3060 (12GB VRAM) can easily handle Q8_0
- Accuracy is critical for entity/relation extraction
- Speed difference negligible in production (<1s difference per chunk)

### GPU Utilization

- **Ollama with GPU**: 15-20x speedup vs CPU
- **NVIDIA RTX 3060**: 85-95% utilization during extraction
- **Memory Usage**: ~5.2GB VRAM for Gemma 3 4B Q8_0

### Pipeline Performance

**Before Optimization** (Sprint 13 start):
- 100 documents: >300 seconds
- Memory: Unbounded growth

**After Optimization** (Sprint 14 end):
- 100 documents: <30 seconds (10x improvement)
- Memory: Stable at ~4GB RAM + 5GB VRAM

## Benchmark Metrics Tracked

1. **Extraction Quality**:
   - Entity precision/recall
   - Relation accuracy
   - Semantic deduplication effectiveness

2. **Performance**:
   - Chunks processed per second
   - GPU utilization %
   - Memory usage (RAM + VRAM)

3. **Latency**:
   - Entity extraction time
   - Relation extraction time
   - Total pipeline time

## Integration

Benchmark learnings integrated into:
- `scripts/benchmark_gpu.py` (production GPU profiling)
- `src/components/graph_rag/extraction_pipeline.py` (optimized pipeline)
- ADR-019 (Integration Tests as E2E Tests)

## Usage Example

```bash
# Run comprehensive benchmark (from archive)
poetry run python scripts/archive/sprint-14-benchmarks/benchmark_production_pipeline.py

# Compare quantizations
poetry run python scripts/archive/sprint-14-benchmarks/compare_gemma_quantizations.py
```

## Do Not Delete

These scripts are valuable for:
1. Re-validating model selection if we upgrade hardware
2. Testing new quantization formats (e.g., Q5_K_M)
3. Reproducing benchmark results for documentation

---

**Archived**: Sprint 19 (2025-10-30)
