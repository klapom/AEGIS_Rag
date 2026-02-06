# Sprint 125 Plan: vLLM Integration + RAGAS Phase 1 Completion

**Date:** 2026-02-06
**Status:** 📝 Planned
**Total Story Points:** 40 SP (estimated, +6 SP from txt2kg alignment)
**Predecessor:** Sprint 124 (RAGAS Evaluation Reboot + gpt-oss:120b Benchmark)

---

## Sprint Goals

1. **Integrate vLLM as extraction inference engine** (replace Ollama for bulk ingestion)
2. **Deploy Nemotron-3-Nano-30B-A3B-NVFP4** for high-quality ER extraction
3. **Complete RAGAS Phase 1 ingestion** (500 samples, currently 28/498)
4. **Fix generic RELATES_TO relations** (S-P-O triples aligned with NVIDIA txt2kg)
5. **Add Entity Deduplication** (inspired by txt2kg's EntityRelationNormalizer)

---

## Background & Motivation

### Sprint 124 Findings

Sprint 124's gpt-oss:120b ingestion run revealed critical bottlenecks:

| Issue | Impact | Root Cause |
|-------|--------|------------|
| HTTP 000 Timeout Loop | Ingestion stuck at 28/498 | Ollama max 4 parallel requests |
| 100% RELATES_TO Relations | Poor graph query quality | Generic relation extraction prompt |
| Community Summarization Backlog | Blocks new uploads | Sequential Ollama processing |

### NVIDIA txt2kg Cookbook Learnings

The [NVIDIA DGX Spark txt2kg playbook](https://github.com/NVIDIA/dgx-spark-playbooks/tree/main/nvidia/txt2kg) provides a reference architecture:

- **vLLM** for GPU-optimized inference (19× throughput vs Ollama)
- **Neo4j 5 Community** for graph storage (same as AegisRAG)
- **Subject-Predicate-Object triples** for specific relation types
- **Docker profiles** for on-demand service start

### vLLM Performance Advantage (Red Hat Benchmark, A100 40GB)

| Metric | Ollama | vLLM | Factor |
|--------|--------|------|--------|
| Peak Throughput | 41 tok/s | 793 tok/s | 19.3× |
| TTFT P99 | 673 ms | 80 ms | 8.4× |
| Max Concurrent | 4 | 256+ | 64× |

Source: [Red Hat Benchmark](https://developers.redhat.com/articles/2025/08/08/ollama-vs-vllm-deep-dive-performance-benchmarking)

### DGX Spark Specific Performance (Forum Benchmark)

| Model | tok/s | Format | Backend |
|-------|-------|--------|---------|
| GPT-OSS-120B | 36 | MXFP4 | vLLM |
| GPT-OSS-120B | 53 | MXFP4 | SGLang |
| Qwen3-30B-A3B | 64 | NVFP4 | vLLM |
| Qwen3-VL-30B-A3B | 82 | AWQ | vLLM |

Source: [NVIDIA Forum: Performance Bottleneck Investigation](https://forums.developer.nvidia.com/t/investigating-performance-issue-bottleneck/359200)

---

## Model: Nemotron-3-Nano-30B-A3B-NVFP4

**Why this model over gpt-oss:120b or Nemotron-3-Nano Q4_K_M:**

| Spec | Nemotron Q4_K_M (current) | gpt-oss:120b (Sprint 124) | Nemotron NVFP4 (planned) |
|------|---------------------------|---------------------------|--------------------------|
| **Total Params** | 31.6B | 116.8B | 30B |
| **Active Params** | ~31.6B (dense) | ~116.8B (dense) | **3.5B (MoE)** |
| **Architecture** | Mamba SSM + MoE | Dense GPT | **Mamba2 + MoE + Attention** |
| **Quantization** | Q4_K_M (GGUF) | MXFP4 (GGUF) | **NVFP4 (HuggingFace)** |
| **VRAM** | 25 GB | 75 GB | **~18 GB** |
| **Backend** | Ollama | Ollama | **vLLM** |
| **Context** | 128K (32K active) | 32K | **256K (up to 1M)** |
| **AIME 2025** | N/A | N/A | **86.7%** |
| **Expected tok/s** | 74 (Ollama) | 20 (Ollama) | **60-80 (vLLM)** |
| **Batching** | Max 4 | Max 4 | **256+ continuous** |
| **Relation Quality** | RELATES_TO only | RELATES_TO only | Specific types (S-P-O) |

**Key Advantage:** Only 3.5B active parameters per token (10% activation) → 3.3× throughput vs dense models on same hardware. Plus NVFP4 is optimized for Blackwell's FP4 tensor cores (4× FLOPS over BF16).

### vLLM Configuration for DGX Spark

```bash
VLLM_USE_FLASHINFER_MOE_FP4=1 \
VLLM_FLASHINFER_MOE_BACKEND=throughput \
vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4 \
  --max-num-seqs 8 \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --port 8001 \
  --trust-remote-code \
  --kv-cache-dtype fp8
```

---

## Features

### 125.1: vLLM Container Integration (8 SP)

**Goal:** Add vLLM as extraction inference engine alongside Ollama.

**Tasks:**
- [ ] Add `vllm` service to `docker-compose.dgx-spark.yml` with Docker profile `ingestion`
- [ ] Configure GPU memory allocation (vLLM 40%, Ollama 20%)
- [ ] Download Nemotron-3-Nano-30B-A3B-NVFP4 from HuggingFace
- [ ] Verify vLLM starts and serves OpenAI-compatible API on port 8001
- [ ] Health check integration (vLLM `/health` endpoint)

**Docker Compose Addition:**
```yaml
vllm:
  image: vllm/vllm-openai:latest
  ports:
    - "8001:8001"
  environment:
    - VLLM_USE_FLASHINFER_MOE_FP4=1
    - VLLM_FLASHINFER_MOE_BACKEND=throughput
    - HF_HOME=/root/.cache/huggingface
  command: >
    --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4
    --max-model-len 32768
    --max-num-seqs 8
    --gpu-memory-utilization 0.4
    --port 8001
    --trust-remote-code
    --kv-cache-dtype fp8
  volumes:
    - huggingface_cache:/root/.cache/huggingface
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
  profiles:
    - ingestion
```

**Start/Stop:**
```bash
# Normal mode (Chat only): Ollama
docker compose -f docker-compose.dgx-spark.yml up -d

# Ingestion mode: Ollama + vLLM
docker compose -f docker-compose.dgx-spark.yml --profile ingestion up -d

# Stop vLLM after ingestion
docker compose -f docker-compose.dgx-spark.yml stop vllm
```

**Acceptance Criteria:**
- [ ] vLLM serves `/v1/chat/completions` on port 8001
- [ ] Nemotron NVFP4 model loaded successfully
- [ ] Health check passes
- [ ] VRAM usage < 55 GB (leaves room for Ollama + embeddings)

---

### 125.2: AegisLLMProxy vLLM Routing (5 SP)

**Goal:** Route EXTRACTION tasks to vLLM, CHAT tasks to Ollama.

**Tasks:**
- [ ] Add `vllm` provider to `AegisLLMProxy`
- [ ] Add `VLLM_BASE_URL` environment variable
- [ ] Route `TaskType.EXTRACTION` → vLLM when available
- [ ] Fallback to Ollama if vLLM unavailable
- [ ] Health check vLLM before routing
- [ ] Unit tests for routing logic

**Routing Logic:**
```python
# In aegis_llm_proxy.py
async def _select_provider(self, task: LLMTask) -> str:
    if task.task_type == TaskType.EXTRACTION and self._vllm_available:
        return "vllm"
    return "local_ollama"
```

**Acceptance Criteria:**
- [ ] Extraction tasks route to vLLM when running
- [ ] Chat/generation tasks always route to Ollama
- [ ] Graceful fallback to Ollama when vLLM is down
- [ ] Unit tests pass (routing, fallback, health check)

---

### 125.3: S-P-O Triple Extraction (Aligned with NVIDIA txt2kg) (8 SP)

**Goal:** Replace generic `RELATES_TO` with specific S-P-O triples, adopting NVIDIA txt2kg's structured extraction schema.

**Problem:** Sprint 124 benchmark showed 100% `RELATES_TO` relations (931/931).

**Reference:** NVIDIA txt2kg playbook uses strict JSON schema with predefined entity categories and relation verbs. This approach ensures graph query quality.

**Tasks:**
- [ ] Update `DSPY_OPTIMIZED_RELATION_PROMPT` to enforce S-P-O triple JSON schema
- [ ] Define predefined entity categories (aligned with txt2kg: ORG, PERSON, GPE, PRODUCT, EVENT, etc.)
- [ ] Define predefined relation vocabulary (aligned with txt2kg + domain-specific)
- [ ] Enforce entity length constraint (< 4 words)
- [ ] Enforce relation length constraint (1-3 words max, ideally 1-2)
- [ ] Add relation type validation in `relation_extractor.py`
- [ ] Map extracted types to Neo4j relationship types
- [ ] Benchmark: compare relation quality before/after

**S-P-O JSON Schema (from txt2kg):**
```json
{
  "subject": "string (< 4 words)",
  "subject_type": "ORG | PERSON | GPE | INSTITUTION | PRODUCT | EVENT | FIELD | METRIC | TOOL | CONCEPT",
  "relation": "string (1-3 words max)",
  "object": "string (< 4 words)",
  "object_type": "string (same categories as subject_type)"
}
```

**Predefined Relation Vocabulary:**
```
# txt2kg core verbs
HAS, ANNOUNCES, OPERATES_IN, INTRODUCES, PRODUCES, CONTROLS
PARTICIPATES_IN, IMPACTS, INVESTS_IN, IS_MEMBER_OF

# AegisRAG domain-specific additions
WORKS_AT, CREATED, DEVELOPED, FOUNDED, DIRECTED
LOCATED_IN, PART_OF, CONTAINS, BELONGS_TO
USES, IMPLEMENTS, DEPENDS_ON, SUPPORTS
MANAGES, OWNS, EMPLOYS
BASED_ON, DERIVED_FROM, EXTENDS, VERSION_OF
EVALUATED_ON, TRAINED_ON, TESTED_WITH
COMPETES_WITH, COLLABORATES_WITH
```

**Acceptance Criteria:**
- [ ] <30% `RELATES_TO` relations (down from 100%)
- [ ] >70% specific relation types
- [ ] Entity names < 4 words (90%+ compliance)
- [ ] Relation names 1-3 words (100% compliance)
- [ ] Neo4j stores specific types as relationship labels
- [ ] No regression in entity extraction quality

---

### 125.3b: Entity Deduplication & Normalization (3 SP)

**Goal:** Add post-extraction entity normalization (inspired by txt2kg's EntityRelationNormalizer).

**Problem:** Without deduplication, the same entity appears as multiple nodes (e.g., "MIT", "Massachusetts Institute of Technology", "M.I.T.").

**Reference:** txt2kg uses an EntityRelationNormalizer that consolidates entity variations and normalizes relation types.

**Tasks:**
- [ ] Implement `EntityRelationNormalizer` in `src/components/graph_rag/`
- [ ] Exact match deduplication (case-insensitive, punctuation-stripped)
- [ ] Acronym resolution (optional: LLM-based for complex cases)
- [ ] Relation normalization (merge semantically similar relations)
- [ ] Integration point: post-extraction, pre-Neo4j storage
- [ ] Unit tests

**Acceptance Criteria:**
- [ ] Duplicate entities reduced by >30%
- [ ] Acronym variations consolidated (e.g., "SQL Server" = "Microsoft SQL Server")
- [ ] Graph connectivity improved (fewer orphan nodes)

---

### 125.4: RAGAS Phase 1 Ingestion Completion (8 SP)

**Goal:** Ingest remaining 470/498 documents using vLLM.

**Tasks:**
- [ ] Update `upload_ragas_phase1.sh` with upload throttling (wait for background processing)
- [ ] Add `--resume` flag to skip already-ingested documents
- [ ] Configure vLLM for extraction, Ollama for community summarization
- [ ] Monitor and log ingestion progress
- [ ] Verify all 498 documents in Qdrant + Neo4j

**Upload Script Improvements:**
```bash
# New: Throttle uploads (wait for completion)
UPLOAD_DELAY="${UPLOAD_DELAY:-30}"  # 30s between uploads
WAIT_FOR_PROCESSING=true            # Check API processing status

# New: Skip already ingested
SKIP_EXISTING=true
```

**Expected Performance (vLLM):**
| Metric | Ollama (Sprint 124) | vLLM (Sprint 125) |
|--------|--------------------|--------------------|
| Extraction per doc | ~50s | ~10s |
| Total 498 docs | ~7 hours (stuck at 28) | ~1.5 hours |
| Concurrent processing | 1 | 8 |
| HTTP 000 errors | Frequent | None (batching) |

**Acceptance Criteria:**
- [ ] All 498 documents ingested without HTTP 000 errors
- [ ] Qdrant: 498+ vectors in `ragas_phase1_sprint125` namespace
- [ ] Neo4j: 2000+ entities, 2000+ relations with specific types
- [ ] Community detection completed for all documents

---

### 125.5: Performance Benchmark & RAGAS Evaluation (5 SP)

**Goal:** Benchmark vLLM performance and run RAGAS evaluation.

**Tasks:**
- [ ] vLLM throughput benchmark (tok/s, latency, concurrent requests)
- [ ] Compare extraction quality: Ollama vs vLLM (same prompts)
- [ ] Run RAGAS Phase 1 evaluation (500 samples)
- [ ] Document results in RAGAS_JOURNEY.md

**Benchmark Targets:**

| Metric | Sprint 124 (Ollama) | Sprint 125 Target (vLLM) |
|--------|--------------------|-----------------------|
| Throughput | 74 tok/s (Nemotron) | 60-80 tok/s (NVFP4) |
| Extraction/doc | ~50s | <15s |
| Total ingestion | Stuck at 28/498 | 498/498 complete |
| ER Ratio | 1.09 | >1.5 |
| Specific Relations | 0% | >70% |
| RAGAS Faithfulness | TBD | >0.80 |
| RAGAS Context Recall | TBD | >0.50 |

**Acceptance Criteria:**
- [ ] vLLM benchmark results documented
- [ ] RAGAS Phase 1 evaluation completed
- [ ] Results in RAGAS_JOURNEY.md
- [ ] Performance comparison table (Ollama vs vLLM)

---

### 125.6: Documentation & ADR (3 SP)

**Goal:** Document architecture decisions and update project docs.

**Tasks:**
- [ ] ADR-058: vLLM Integration for Extraction Pipeline
- [ ] Update TECH_STACK.md with vLLM + NVFP4
- [ ] Update ARCHITECTURE.md with dual-engine diagram
- [ ] Update CLAUDE.md with Sprint 125 summary

---

## VRAM Budget

```
DGX Spark: 128 GB Unified Memory

Normal Mode (Chat):
  Ollama Nemotron-3-Nano:128k   25 GB
  BGE-M3 Embeddings              2 GB
  Reranker (cross-encoder)        1 GB
  OS + CUDA Overhead             10 GB
  ─────────────────────────────────────
  Total:                         38 GB
  Free:                          90 GB

Ingestion Mode (Chat + vLLM):
  Ollama Nemotron-3-Nano:128k   25 GB
  vLLM Nemotron NVFP4           ~18 GB  (up to 51 GB with 256K context)
  BGE-M3 Embeddings              2 GB
  Reranker (cross-encoder)        1 GB
  OS + CUDA Overhead             10 GB
  ─────────────────────────────────────
  Total:                      56-82 GB
  Free:                      46-72 GB
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| vLLM doesn't support sm_121 (Blackwell) | Build failure | Check NVIDIA forum, build from source if needed |
| NVFP4 quality degradation | Poor ER extraction | Fall back to FP8 or BF16 quantization |
| VRAM conflict Ollama + vLLM | OOM crashes | Docker profiles, stop one before starting other |
| vLLM cold start slow (~60s) | User impatience | Pre-warm during ingestion mode start |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| vLLM Docker image | ✅ Available | `vllm/vllm-openai:latest` |
| Nemotron NVFP4 model | 📥 Download needed | ~18 GB from HuggingFace |
| DGX Spark sm_121 support | ⚠️ Verify | Check vLLM CUDA 13.0 compatibility |
| RAGAS Phase 1 dataset | ✅ Available | 498 files in `data/ragas_phase1_contexts/` |

---

## txt2kg Gap Analysis (Research Findings)

**Source:** NVIDIA DGX Spark txt2kg Playbook ([GitHub](https://github.com/NVIDIA/dgx-spark-playbooks/tree/main/nvidia/txt2kg))

### What txt2kg Does That AegisRAG Doesn't (Yet)

| Feature | txt2kg | AegisRAG (Sprint 124) | Sprint 125 Action |
|---------|--------|----------------------|-------------------|
| **S-P-O JSON Schema** | Strict: subject, subject_type, relation, object, object_type | Free-form entity/relation | 125.3: Adopt schema |
| **Predefined Relations** | 15 verbs (Has, Produce, Control, etc.) | 100% RELATES_TO | 125.3: Add vocabulary |
| **Entity Length** | < 4 words enforced | No constraint | 125.3: Add constraint |
| **Relation Length** | 1-3 words max | No constraint | 125.3: Add constraint |
| **Entity Dedup** | EntityRelationNormalizer (exact+fuzzy) | None | 125.3b: NEW feature |
| **vLLM Engine** | docker-compose.vllm.yml with Nemotron-Super-49B | Ollama only | 125.1-2: Add vLLM |

### What AegisRAG Already Does Better

| Feature | AegisRAG | txt2kg |
|---------|----------|--------|
| **Graph DB** | Neo4j 5 Community (Cypher, GDS, communities) | ArangoDB (basic traversal) |
| **Embeddings** | BGE-M3 1024-dim (Dense+Sparse) | MiniLM-L6-v2 384-dim (planned) |
| **Chunking** | Section-aware 800-1800 tokens | 2048 char recursive |
| **Entity Types** | 15 DSPy-trained types | 12 predefined |
| **Community Detection** | GDS-based Leiden algorithm | Not implemented |
| **RAG Pipeline** | Hybrid Vector+Graph+Memory | KG-only (no vector search yet) |
| **Evaluation** | RAGAS 0.4.2 (4 metrics) | None |

### txt2kg Model: NOT Nemotron-3-Nano-30B-A3B-NVFP4

The txt2kg playbook currently uses:
- **Default mode:** `llama3.1:8b` via Ollama (basic, 4K context)
- **vLLM mode:** `nvidia/Llama-3.3-Nemotron-Super-49B-v1.5-FP8` (128K context, 4.9B active MoE)

The NVFP4 model is newer (Feb 2026) and not yet integrated into the playbook. Sprint 125 will use the NVFP4 model which is more efficient (3.5B active, 1M context, ~18GB VRAM).

---

## References

- [NVIDIA txt2kg Playbook](https://github.com/NVIDIA/dgx-spark-playbooks/tree/main/nvidia/txt2kg)
- [NVIDIA txt2kg Build Page](https://build.nvidia.com/spark/txt2kg)
- [Nemotron-3-Nano-30B-A3B-NVFP4 (HuggingFace)](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4)
- [Nemotron NVFP4 QAD Blog](https://www.marktechpost.com/2026/02/01/nvidia-ai-brings-nemotron-3-nano-30b-to-nvfp4-with-quantization-aware-distillation-qad-for-efficient-reasoning-inference/)
- [Red Hat: Ollama vs vLLM Benchmark](https://developers.redhat.com/articles/2025/08/08/ollama-vs-vllm-deep-dive-performance-benchmarking)
- [NVIDIA Forum: DGX Spark Performance](https://forums.developer.nvidia.com/t/investigating-performance-issue-bottleneck/359200)
- [vLLM for DGX Spark](https://build.nvidia.com/spark/vllm)
- [vLLM: Run Nemotron 3 Nano Recipe](https://docs.vllm.ai/projects/recipes/en/latest/NVIDIA/Nemotron-3-Nano-30B-A3B.html)
- [NVIDIA: LLM-Driven Knowledge Graphs](https://developer.nvidia.com/blog/insights-techniques-and-evaluation-for-llm-driven-knowledge-graphs/)
- [RAGAS_JOURNEY.md](../ragas/RAGAS_JOURNEY.md)
