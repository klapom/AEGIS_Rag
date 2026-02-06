# Sprint 126 Plan: RAGAS Phase 1 Benchmark with vLLM Extraction

**Status:** 📝 PLANNED
**Story Points:** 13 SP
**Duration:** 1-2 days (estimated)
**Predecessor:** Sprint 125 (vLLM Integration + Domain-Aware Extraction)

---

## Sprint Goals

1. **Complete RAGAS Phase 1 Ingestion** with vLLM extraction engine (498 documents)
2. **Benchmark extraction performance** (vLLM vs Ollama, throughput, quality)
3. **Evaluate RAGAS metrics** with new extraction improvements
4. **Document S-P-O relation quality** (target: >70% specific types)
5. **Validate domain-aware extraction** (domain classification → trained prompts)

---

## Background

Sprint 125 delivered critical extraction improvements but deferred RAGAS evaluation to Sprint 126:

| Sprint 124 Issue | Sprint 125 Solution | Sprint 126 Validation |
|------------------|---------------------|----------------------|
| HTTP 000 timeout at 28/498 docs | vLLM dual-engine (8+ concurrent vs Ollama's 4) | Complete 498 doc ingestion |
| 100% RELATES_TO relations | S-P-O schema + 21 universal relation types | Measure relation diversity |
| Generic extraction prompts | Domain-aware pipeline (BGE-M3 → domain prompts) | Compare domain vs generic |
| No performance baseline | N/A | Benchmark vLLM vs Ollama |

**Rationale for Sprint 126:** Benchmark AFTER all extraction improvements are complete. Sprint 124's baseline with generic RELATES_TO relations would produce misleading metrics.

---

## Features

### 126.1: RAGAS Phase 1 Ingestion Completion (8 SP)

**Goal:** Ingest all 498 RAGAS Phase 1 documents with vLLM extraction engine.

**Data Source:**
- `data/ragas_phase1_contexts/` (498 .txt files)
- Domains: Research Papers, Technical QA, E-Manuals, HotpotQA

**Tasks:**
- [ ] Start vLLM container with `--profile ingestion`
- [ ] Verify vLLM health and model loaded (Nemotron-3-Nano-30B-A3B-NVFP4)
- [ ] Run upload script: `scripts/upload_ragas_phase1.sh`
- [ ] Monitor ingestion progress (log every 10 docs)
- [ ] Track extraction performance (tok/s, time per doc, concurrent requests)
- [ ] Verify domain classification runs for each document
- [ ] Check domain-trained prompts used when available
- [ ] Capture structured logs for analysis
- [ ] Stop vLLM after ingestion completes

**Upload Script Configuration:**
```bash
# scripts/upload_ragas_phase1.sh
NAMESPACE="ragas_phase1_sprint126"
BACKEND_URL="http://localhost:8000"
FILES_DIR="data/ragas_phase1_contexts"
BATCH_SIZE=10  # Concurrent uploads (vLLM supports 8+)
DOMAIN="auto"  # BGE-M3 classification
```

**Expected Results:**
- All 498 documents ingested successfully
- ~1,500-2,000 entities extracted
- ~2,000-3,000 relations (ER ratio ~1.2-1.5)
- >70% specific relation types (down from 100% RELATES_TO)
- Domain classification visible in logs for each doc

**Acceptance Criteria:**
- [ ] 498/498 documents in Qdrant + Neo4j
- [ ] No HTTP 000 timeouts (vLLM concurrent batching)
- [ ] Ingestion completes in <4 hours (vs 28/498 in 6+ hours with Ollama)
- [ ] Domain classification runs for all documents
- [ ] `domain_id` stored in Qdrant payloads and Neo4j entities
- [ ] Structured logs saved to `data/ingestion_logs/sprint126/`

---

### 126.2: Performance Benchmark + RAGAS Evaluation (5 SP)

**Goal:** Benchmark extraction performance and evaluate RAGAS metrics.

**Benchmarks:**

#### A. Extraction Performance (vLLM vs Ollama)

| Metric | Ollama (Sprint 124) | vLLM (Sprint 126) | Target |
|--------|---------------------|-------------------|--------|
| Throughput | ~20 tok/s | ~54 tok/s | 2-3× improvement |
| Time per doc | ~20s | <10s | 50%+ reduction |
| Max concurrent | 4 | 8-16 | 2-4× improvement |
| HTTP 000 errors | 15+ (at 28 docs) | 0 | No timeouts |
| Total time (498 docs) | Projected 2.75 hours | <2 hours | <4 hours |

#### B. Relation Quality (S-P-O vs RELATES_TO)

| Metric | Sprint 124 | Sprint 126 Target |
|--------|------------|-------------------|
| RELATES_TO relations | 931/931 (100%) | <30% |
| Specific relation types | 0/931 (0%) | >70% |
| Universal relation types used | 1 | 10-15 |
| Entity types from universal | ~60% | >95% |
| Entity names < 4 words | ~70% | >90% |
| Relation names 1-3 words | ~50% | >95% |

#### C. Domain-Aware Extraction

| Metric | Target |
|--------|--------|
| Documents with domain classification | 498/498 (100%) |
| Domain-trained prompts used | >20% (domains with DSPy training) |
| Generic prompts fallback | <80% (untrained domains) |
| Classification accuracy | >80% (vs manual labels) |

#### D. RAGAS Metrics (Updated Baseline)

| Metric | Sprint 82 Baseline | Sprint 126 Target | Notes |
|--------|-------------------|-------------------|-------|
| Faithfulness | 0.91 | ≥0.90 | Maintain |
| Answer Relevancy | 0.94 | ≥0.93 | Maintain |
| Context Precision | 0.58 | ≥0.60 | +3% improvement |
| Context Recall | 0.29 | ≥0.35 | +20% improvement (S-P-O relations) |

**Tasks:**
- [ ] Extract ingestion metrics from logs (total time, throughput, errors)
- [ ] Query Neo4j for relation type distribution
- [ ] Validate entity types against 15 universal types
- [ ] Measure entity/relation name length compliance
- [ ] Count domain-trained vs generic prompt usage
- [ ] Run RAGAS evaluation on 50-sample subset
- [ ] Compare RAGAS metrics to Sprint 82 baseline
- [ ] Generate benchmark report
- [ ] Update `docs/ragas/RAGAS_JOURNEY.md` with Sprint 126 results

**Acceptance Criteria:**
- [ ] Benchmark report saved to `data/benchmark_results/sprint126/`
- [ ] Relation diversity >70% specific types
- [ ] Entity type compliance >95% universal types
- [ ] RAGAS metrics documented in RAGAS_JOURNEY.md
- [ ] Performance improvements quantified (vLLM vs Ollama)

---

## VRAM Budget (Ingestion Mode)

```
DGX Spark: 128 GB Unified Memory

Ingestion Mode (Sprint 126):
  Ollama Nemotron-3-Nano:128k   25 GB   (Chat fallback)
  vLLM Nemotron NVFP4           ~18 GB   (Extraction primary)
  BGE-M3 Embeddings              2 GB
  Reranker (cross-encoder)        1 GB
  OS + CUDA Overhead             10 GB
  ─────────────────────────────────────
  Total:                         56 GB
  Free:                          72 GB
```

Both LLMs can run simultaneously without conflict.

---

## Environment Configuration

**Required .env Settings:**
```bash
# vLLM Configuration
VLLM_ENABLED=true
VLLM_BASE_URL=http://localhost:8001
VLLM_MODEL=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4

# Ollama (Fallback)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=Nemotron3

# Extraction Pipeline
AEGIS_USE_DSPY_PROMPTS=true
AEGIS_USE_DOMAIN_PROMPTS=true
EXTRACTION_BACKEND=vllm  # Routes extraction to vLLM

# Domain Classification
DOMAIN_CLASSIFIER_ENABLED=true
DOMAIN_CLASSIFIER_BACKEND=bge_m3
```

**Start Services:**
```bash
# Start vLLM + all services
docker compose -f docker-compose.dgx-spark.yml --profile ingestion up -d

# Verify vLLM health
curl http://localhost:8001/health

# Verify model loaded
curl http://localhost:8001/v1/models
```

---

## Success Criteria

Sprint 126 is complete when:

- [x] All 498 RAGAS Phase 1 documents ingested
- [x] No HTTP 000 timeouts or ingestion failures
- [x] >70% specific relation types (measured in Neo4j)
- [x] >95% entity type compliance with 15 universal types
- [x] Domain classification runs for all documents
- [x] Performance benchmark shows 2-3× throughput improvement
- [x] RAGAS metrics evaluated and documented
- [x] Benchmark report saved to `data/benchmark_results/sprint126/`
- [x] RAGAS_JOURNEY.md updated with Sprint 126 results

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| vLLM crashes during ingestion | Partial data loss | Checkpoint every 50 docs, restart from last checkpoint |
| VRAM OOM (vLLM + Ollama + BGE-M3) | Service crash | Monitor VRAM, stop Ollama if needed (vLLM primary) |
| S-P-O prompts produce low-quality relations | RAGAS metrics worse than baseline | Fall back to generic prompts, iterate prompt engineering |
| Domain classification too slow | Ingestion bottleneck | Cache classification results, use batch classification |
| RAGAS evaluation timeouts | Incomplete metrics | Increase timeout, use smaller sample subset (20 questions) |

---

## Next Steps (Sprint 127)

**Focus:** LightRAG Removal — Direct Neo4j Architecture

Sprint 126's RAGAS evaluation will inform Sprint 127 decisions:
- If Context Recall improves: Keep S-P-O extraction, remove LightRAG abstraction
- If Context Precision stagnates: Investigate reranking weights
- If Faithfulness drops: Audit LLM response generation prompts

---

## References

- [Sprint 125 Plan](SPRINT_125_PLAN.md) - vLLM integration details
- [RAGAS Journey](../ragas/RAGAS_JOURNEY.md) - Metrics evolution
- [ADR-059](../adr/ADR-059-vllm-dual-engine.md) - Dual-engine architecture
- [ADR-060](../adr/ADR-060-domain-taxonomy.md) - Domain taxonomy
- [upload_ragas_phase1.sh](../../scripts/upload_ragas_phase1.sh) - Upload script
