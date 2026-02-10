# Sprint 128 Plan: LightRAG Removal + Cascade Timeout Guard + Full RAGAS Ingestion + LLM Config UI

**Status:** ✅ COMPLETE (128.1-128.2, 128.4-128.9 DONE — 128.3/128.3a moved to Sprint 129)
**Story Points:** 38 SP (30 SP delivered, 8 SP carried to Sprint 129.4)
**Duration:** 3-5 days
**Predecessor:** Sprint 127 ✅ (RAGAS Phase 1 Benchmark)

---

## Sprint Goals

1. **Remove LightRAG dependency** — eliminate 92% extraction overhead, restore relation diversity
2. **Add Cascade Timeout Guard** — prevent ghost requests from overloading GPU
3. **Complete RAGAS Phase 1 ingestion** — 488 remaining docs (post-LightRAG: ~6h vs 75h)
4. **HyDE Query Expansion** — Hypothetical Document Embeddings for improved retrieval
5. **LLM Config UI** — Engine-aware model selection, vLLM model display, Vision VLM handling

| # | Feature | SP | Status |
|---|---------|-----|--------|
| 128.1 | LightRAG Removal + domain_id/namespace fix | 8 | ✅ DONE |
| 128.2 | Cascade Timeout Guard (vLLM /metrics polling, exp backoff) | 3 | ✅ DONE |
| 128.3 | RAGAS Phase 1 Full Ingestion | 8 | ➡️ Moved to 129.4 |
| 128.4 | HyDE Query Expansion (5th RRF signal, LLM cache) | 5 | ✅ DONE |
| 128.5 | LLM Config Page — Engine-Aware Model Selection | 5 | ✅ DONE |
| 128.6 | Domain Prompt Verification — All 35 Domains | 3 | ✅ DONE |
| 128.7 | vLLM SM121 CUDA Stability Experiments | 3 | ✅ DONE |
| 128.8 | E2E Pipeline Benchmark (plaintext fallback + 5-doc test) | 2 | ✅ DONE |
| 128.9 | 15-Doc Batch Benchmark (statistical significance) | 1 | ✅ DONE |

---

## Background

Sprint 127 proved that LightRAG is the single biggest bottleneck in the pipeline:

| Problem | Evidence (Sprint 127) | Impact |
|---------|----------------------|--------|
| Double extraction | `ainsert_custom_kg` takes 92% of time (5,030s/5,447s) | 13x slower ingestion |
| Relation overwrite | 79% generic RELATED_TO (LightRAG overwrites typed relations) | Suppresses graph reasoning |
| Domain sub-types lost | 0/873 stored (LightRAG bypasses domain pipeline) | Domain prompts wasted |
| Ghost requests | Cascade timeout → vLLM continues → competing requests (34.8% at 3-5 concurrent) | GPU overload |

**Sprint 127 RAGAS Baseline (for comparison after removal):**

| Metric | Sprint 127 | Target Post-Removal |
|--------|------------|---------------------|
| Context Precision | 0.739 | ≥0.75 |
| Context Recall | 0.760 | ≥0.80 |
| Faithfulness | 0.699 | ≥0.75 |
| Answer Relevancy | 0.828 | ≥0.85 |

---

## Features

### 128.1: LightRAG Removal (8 SP) — ✅ COMPLETE

**Goal:** Remove `lightrag-hku` dependency entirely. Replace 3 used functions with existing AegisRAG code.

**What LightRAG provides (only 3 functions):**

| Function | Location | Replacement |
|----------|----------|-------------|
| `ainsert_custom_kg()` | `lightrag/ingestion.py:325,722` | **DELETE** (redundant — `store_chunks_and_provenance` already stores to Neo4j) |
| `rag.aquery()` | `lightrag/client.py:234` | `DualLevelSearch` (Sprint 115/ADR-057, already primary) |
| `rag._driver` (Neo4j) | `lightrag/neo4j_storage.py:96` | `Neo4jClient` from `neo4j_client.py` |

**Files to DELETE (7 files, ~2,500 LOC):**
```
src/components/graph_rag/lightrag/
├── __init__.py          (~100 LOC)  - Package init
├── types.py             (~160 LOC)  - LightRAGConfig, QueryMode
├── initialization.py    (~284 LOC)  - create_lightrag_instance
├── client.py            (~363 LOC)  - LightRAGClient, query_graph()
├── converters.py        (~400 LOC)  - Format converters for ainsert_custom_kg
├── ingestion.py         (~783 LOC)  - insert_prechunked_documents, ainsert_custom_kg
└── neo4j_storage.py     (~411 LOC)  - Neo4j storage via rag._driver
src/components/graph_rag/lightrag_wrapper.py  (~50 LOC) - Backward compat facade
```

**Files to MODIFY (6 files):**

| File | Change | LOC |
|------|--------|-----|
| `src/components/ingestion/nodes/graph_extraction.py` | Remove lightrag_wrapper import, use Neo4jClient directly for storage. Remove `ainsert_custom_kg` call. Keep `store_chunks_and_provenance` logic (migrate to Neo4jClient). | ~80 |
| `src/components/retrieval/maximum_hybrid_search.py` | Replace `LightRAGClient.query_graph()` with `DualLevelSearch.local_search()` and `global_search()`. Update `_lightrag_local_search` and `_lightrag_global_search` functions. | ~60 |
| `src/components/retrieval/lightrag_context_parser.py` | Rename to `graph_context_parser.py`. Keep entity/community parsing logic (used by cross-modal fusion). | ~20 |
| `src/components/graph_rag/extraction_factory.py` | Remove "lightrag_default" pipeline option. | ~10 |
| `src/core/config.py` | Remove `lightrag_*` settings fields. Keep extraction-relevant settings (rename if needed). | ~15 |
| `pyproject.toml` | Remove `lightrag-hku = "^1.4.9"`. Keep `networkx`, `scipy`. | 1 |

**Migration Detail — graph_extraction.py (the critical file):**

Current flow (with LightRAG):
```
chunks → get_lightrag_wrapper_async() → lightrag.insert_prechunked_documents()
  → extract_per_chunk() → ainsert_custom_kg() [REDUNDANT: re-extracts everything]
  → store_chunks_and_provenance() [actual Neo4j storage]
```

New flow (without LightRAG):
```
chunks → ExtractionService.extract_entities/relations() [already happening]
  → Neo4jClient.store_entities_and_relations() [new function, direct Neo4j]
  → store_chunks_and_provenance() [keep, but use Neo4jClient]
```

**Migration Detail — maximum_hybrid_search.py:**

Current:
```python
from src.components.graph_rag.lightrag_wrapper import LightRAGClient
lightrag_client = LightRAGClient()
result = await lightrag_client.query_graph(query=query, mode="local")
```

New:
```python
from src.components.graph_rag.dual_level_search import get_dual_level_search
search = get_dual_level_search()
result = await search.local_search(query=query, top_k=5, namespaces=namespaces)
```

**Acceptance Criteria:**
- [ ] No imports of `lightrag` anywhere in `src/`
- [ ] `poetry show lightrag-hku` returns "not installed"
- [ ] Docker build succeeds without lightrag-hku
- [ ] 10-doc re-ingestion produces >70% specific relation types (vs 21% with LightRAG)
- [ ] Domain sub-types stored in Neo4j entities (vs 0% with LightRAG)
- [ ] Ingestion speed: 10 docs in <10 min (vs 91 min with LightRAG)

---

### 128.2: Cascade Timeout Guard (3 SP)

**Goal:** Prevent cascade from starting competing vLLM requests when a timed-out request is still running server-side.

**Problem (Sprint 127 finding):**
When httpx times out after 600s, vLLM continues generating server-side. The cascade then starts Rank 2 with a NEW vLLM request. Combined with LightRAG double extraction + 2-worker parallelism, 34.8% of time was spent at 3-5 concurrent vLLM requests (target: 2).

**Solution:**

```python
# In extraction_service.py, before starting next cascade rank:
async def _should_start_next_rank(self, previous_rank_error: Exception) -> bool:
    """Check if we should start next cascade rank or wait for in-flight request."""
    if isinstance(previous_rank_error, asyncio.TimeoutError):
        # Check vLLM active request count
        active = await self._get_vllm_active_requests()
        if active >= EXTRACTION_WORKERS:
            logger.warning("cascade_guard_waiting", active_requests=active)
            # Wait for in-flight request with extended timeout
            await asyncio.sleep(30)
            return True  # Retry same rank with extended timeout
    return True  # Proceed to next rank for non-timeout errors
```

**Files to modify:**
- `src/components/graph_rag/extraction_service.py` — Add guard in cascade loop
- `src/domains/llm_integration/proxy/aegis_llm_proxy.py` — Add `get_active_requests()` method (query vLLM `/v1/models` or track internally)

**Acceptance Criteria:**
- [ ] No competing vLLM requests after timeout (verified in logs)
- [ ] Maximum concurrent vLLM requests ≤ EXTRACTION_WORKERS
- [ ] No regression in extraction success rate

---

### 128.3a: Cross-Sentence Window Determinism Benchmark (2026-02-09)

**Status:** 🔄 RUNNING (~4-5h)
**Script:** `scripts/benchmark_cross_sentence_v5.py`

**Goal:** Determine optimal window config for 488-doc full ingestion by testing 4 documents × 4 configs × 3 runs = 48 total extractions. Answers two questions:
1. Is extraction deterministic? (CV < 10% for deduped counts)
2. What's the optimal config across doc sizes? (generalizability of v4's w14_o3 winner)

**Test Matrix:** S(3KB), M(5KB), L(6KB), XL(12KB) × w12_o2, w12_o3, w14_o2, w14_o3 × 3 runs

**Results:** _Pending — benchmark running. Will update with optimal config recommendation._

**Decision:** _Use [config TBD] as default for 128.3 full ingestion._

---

### 128.3: RAGAS Phase 1 Full Ingestion (8 SP)

**Goal:** Complete remaining 488/498 RAGAS Phase 1 documents with LightRAG removed.

**Prerequisites:** 128.1 (LightRAG Removal) must be complete.

**Expected Performance (post-LightRAG removal):**

| Metric | Sprint 127 (with LightRAG) | Sprint 128 (without) | Improvement |
|--------|---------------------------|----------------------|-------------|
| Time per doc | ~510s (8.5 min) | ~40-60s | 10-13x faster |
| Total time (488 docs) | ~69 hours | ~5-8 hours | 10x faster |
| Specific relations | 21% | >70% | 3x more typed |
| Domain sub-types | 0% | >90% | ∞ improvement |

**Tasks:**
- [ ] Update `scripts/batch_upload_ragas_10.sh` → `scripts/batch_upload_ragas_full.sh`
- [ ] Configure batches of 50 docs with checkpointing
- [ ] Monitor GPU memory and vLLM health during batch
- [ ] Track extraction quality metrics per batch
- [ ] Final Neo4j statistics (entities, relations, type distribution)

**Verification:**
- [ ] 498/498 documents in Qdrant + Neo4j (namespace: `ragas_phase1_sprint128`)
- [ ] >70% specific relation types in Neo4j
- [ ] >90% entity type compliance with 15 universal types
- [ ] Domain sub-types stored in Neo4j entity properties
- [ ] No HTTP timeouts or ingestion failures
- [ ] RAGAS re-evaluation (20 samples, same questions as Sprint 127.2)

---

### 128.4: HyDE Query Expansion (5 SP)

**Goal:** Implement Hypothetical Document Embeddings to improve retrieval quality, especially for abstract queries.

**Concept:** Instead of embedding the raw query, generate a hypothetical answer document first, then embed that document. This produces embeddings that are closer to the actual relevant documents in vector space.

**Architecture:**
```
Query → LLM generates hypothetical answer → BGE-M3 embeds hypothetical → Qdrant search
     ↘ Original query embedding → Qdrant search (parallel)
     → RRF fusion of both result sets
```

**Files to create/modify:**
- `src/components/retrieval/hyde.py` — NEW: HyDE generator (generate hypothetical document, embed, search)
- `src/components/retrieval/maximum_hybrid_search.py` — Add HyDE as 5th signal in hybrid search
- `src/core/config.py` — Add `HYDE_ENABLED` setting (default: True)

**Expected RAGAS Impact:**
- Context Precision: +5-10% (hypothetical doc closer to relevant chunks)
- Context Recall: +5-10% (captures semantic intent better than keywords)
- Answer Relevancy: +3-5% (better context → better answers)

**Acceptance Criteria:**
- [ ] HyDE generates reasonable hypothetical documents (manual inspection)
- [ ] No regression in simple factual queries (HyDE can hurt keyword-heavy queries)
- [ ] Configurable via env var (can be disabled)
- [ ] RAGAS comparison with/without HyDE on 20-sample set

---

### 128.5: LLM Config Page — Engine-Aware Model Selection (5 SP)

**Goal:** The `/admin/llm-config` page should only show models that are actually available based on the current engine mode (vLLM/Ollama/Auto). vLLM selections should be disabled (single model), and Vision VLM should be greyed out with a "not available" hint.

**Current State:**
- Engine Mode section (Sprint 126): 3 buttons (vLLM/Ollama/Auto) with health checks
- Use Case Model Assignment: 6 dropdowns populated from Ollama `/api/tags` only
- No awareness of vLLM model in dropdowns
- Vision VLM shows cloud models (Qwen3-VL, GPT-4o) even though no local VLM is available
- Backend `GET /llm/models` only queries Ollama, not vLLM

**Changes Required:**

#### Frontend (`AdminLLMConfigPage.tsx`)

| Change | Detail |
|--------|--------|
| **Engine mode ↔ model list coupling** | When engine mode changes, update available models in dropdowns immediately |
| **vLLM-only mode** | Show only the vLLM model (from new API). All 6 use case dropdowns show single model, **disabled** (no selection possible). Badge: "vLLM — single model" |
| **Ollama-only mode** | Keep current behavior — show Ollama models from `/api/tags`. No change. |
| **Auto mode** | Show both Ollama models AND vLLM model. Extraction use cases default to vLLM model (disabled). Chat use cases show Ollama models (selectable). |
| **Vision VLM row** | Grey out with tooltip/badge: "Vision models not available — no VLM loaded". Disable dropdown. Keep existing cloud options visible but disabled. |
| **vLLM model badge** | New badge type for vLLM models: blue "vLLM" pill (vs green "Local" for Ollama, purple "Cloud" for Alibaba/OpenAI) |

#### Backend (`admin_llm.py`)

| Change | Detail |
|--------|--------|
| **New endpoint: `GET /api/v1/admin/llm/vllm-model`** | Query vLLM `/v1/models` endpoint → return loaded model name + health. Response: `{ model: "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4", healthy: true }`. Fallback: read `VLLM_MODEL` env var if vLLM unreachable. |
| **Update `GET /api/v1/admin/llm/models`** | Add optional `?include_vllm=true` query param. When set, also queries vLLM and merges into model list with provider tag `"vllm"`. |
| **Engine mode in model response** | Include current engine mode in models response so frontend can filter in a single API call |

#### Behavior Matrix

| Engine Mode | Use Case | Available Models | Selection |
|-------------|----------|-----------------|-----------|
| **vLLM** | All 6 | vLLM model only | **Disabled** (single model) |
| **Ollama** | All 6 | Ollama models | Enabled (current behavior) |
| **Auto** | `entity_extraction` | vLLM model | **Disabled** |
| **Auto** | `intent_classification` | Ollama models | Enabled |
| **Auto** | `answer_generation` | Ollama models | Enabled |
| **Auto** | `followup_titles` | Ollama models | Enabled |
| **Auto** | `query_decomposition` | Ollama models | Enabled |
| **Auto** | `vision_vlm` | None (greyed out) | **Disabled** + hint |

#### Vision VLM Handling

- Check if any loaded model has vision capability (neither Nemotron-3-Nano nor current Ollama models support vision)
- If no vision model available: grey out row, show info banner: "No vision-capable model loaded. Vision requires a VLM like LLaVA or Qwen3-VL."
- Cloud vision models (Qwen3-VL, GPT-4o) remain visible but disabled unless cloud API key is configured

#### Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/pages/admin/AdminLLMConfigPage.tsx` | Engine-aware model filtering, disabled states, vLLM badge, Vision VLM greyed out |
| `src/api/v1/admin_llm.py` | New `GET /llm/vllm-model` endpoint, update `/llm/models` with vLLM merge |
| `src/components/llm_config/llm_config_service.py` | Engine-mode-aware model validation (reject Ollama model in vLLM mode on save) |

**Acceptance Criteria:**
- [ ] vLLM mode: all dropdowns disabled, showing vLLM model name
- [ ] Ollama mode: current behavior unchanged
- [ ] Auto mode: extraction=vLLM (disabled), chat=Ollama (selectable)
- [ ] Vision VLM greyed out with "not available" message
- [ ] Backend validates model selection against engine mode on save
- [ ] vLLM model fetched from `/v1/models` endpoint (with env var fallback)
- [ ] No regression in existing LLM config save/load

---

### 128.6: Domain Prompt Verification — All 35 Domains (3 SP) — ✅ COMPLETE

**Goal:** Verify Sprint 128 rewritten extraction prompts work correctly across all 35 DDC+FORD domains with Nemotron model on DGX Spark.

**Two-Phase Approach:**
- **Phase 1 (Format):** Template rendering, placeholder presence, sub-type injection — no LLM needed
- **Phase 2 (Quality):** LLM extraction from domain-specific example texts, scoring against expectations

**Script:** `scripts/verify_domain_prompts.py` (~650 LOC)

**Critical Bug Found & Fixed:**

Python `.format()` interprets `{` and `}` as placeholders. Domain-enriched prompts contain JSON examples like `{"name": "...", "type": "..."}` which caused `KeyError` exceptions, silently cascading ALL entity extractions to SpaCy Rank 3 and sending raw templates to the LLM for relation extraction.

| Fix | File | Change |
|-----|------|--------|
| Entity prompt substitution | `extraction_service.py:~1672` | `.format()` → `.replace()` |
| Relation prompt substitution | `extraction_service.py:~3131` | `.format()` → `.replace()` |
| Strength field | `models.py:~314` | Added `strength: int \| None` to `GraphRelationship` |
| Confidence extraction | `extraction_service.py:~1731,~2841` | Parse `confidence` from LLM output (both main + gleaning paths) |

**Results:**

| Phase | Metric | Result |
|-------|--------|--------|
| Phase 1 | Templates format without errors | **35/35** (100%) ✅ |
| Phase 2 | Domains passing all quality thresholds | **27/35** (77%) |
| Phase 2 | JSON parse success | **35/35** (100%) ✅ |
| Phase 2 | Entity recall (avg) | **61%** |
| Phase 2 | Relation specificity (avg) | **52%** |
| Phase 2 | vLLM success rate | **93.4%** (704/753 requests) |

**8 Failing Domains:** Primarily low relation specificity (ASSOCIATED_WITH catch-all mapping) and entity type mismatches. These are relation type mapping issues, not prompt quality problems.

**vLLM Stability:** 49 failed requests due to intermittent `cudaErrorIllegalInstruction` (SM120 CUTLASS kernels on SM121 GB10 hardware). Auto-recovered via Docker restart policy. No code fix needed.

**Commits:** Part of Sprint 128 prompt rewrite commit (extraction_service.py, models.py fixes)

---

### 128.7: vLLM SM121 CUDA Stability Experiments (3 SP) — ✅ COMPLETE

**Goal:** Eliminate intermittent `cudaErrorIllegalInstruction` crashes in vLLM on DGX Spark (SM121/GB10).

**Problem:** During Sprint 128.6, 49/753 vLLM requests (6.6%) failed due to CUDA illegal instruction traps in CUTLASS grouped GEMM kernels. Root cause: NGC image compiles for SM120 and runs via PTX forward compatibility on SM121.

**Experiments:**

| # | Experiment | Config Change | Status |
|---|-----------|---------------|--------|
| A | DeepGemm OFF | `VLLM_MOE_USE_DEEP_GEMM=0` in docker-compose | ✅ Applied, vLLM healthy |
| B | eugr community image | `aegis-vllm-eugr:latest` (native SM121, CUDA 13.1.1) | 🔄 Building |

**Experiment A — DeepGemm OFF:**
- FP8-specific optimization disabled (model uses NVFP4, not FP8)
- Expected performance impact: ~0%
- Side effect: FlashInfer JIT cache invalidated → 63 CUTLASS kernels recompiled at startup
- Side effect: First startup OOM-killed when concurrent with Docker build (needs >20 GB RAM)

**Experiment B — eugr/spark-vllm-docker:**
- Community Docker image with `TORCH_CUDA_ARCH_LIST=12.1a` (native SM121)
- Base: `nvidia/cuda:13.1.1-devel-ubuntu24.04`
- vLLM from GitHub release wheels (cu130, aarch64)
- Latest FlashInfer from flashinfer.ai
- Building as `aegis-vllm-eugr:latest`

**A/B Test Protocol:**
1. Run 50+ extraction requests with DeepGemm OFF (current config)
2. Swap container to eugr image, run 50+ extraction requests
3. Compare crash rates (target: 0 crashes vs baseline 6.6%)
4. Compare latency + throughput

**Files Modified:**
- `docker-compose.dgx-spark.yml` — Added `VLLM_MOE_USE_DEEP_GEMM=0`
- `docs/CLAUDE_zusatzinfos.md` — Added SM121 crash analysis section
- `docs/ragas/RAGAS_JOURNEY.md` — Added Sprint 128.7 experiment log

**A/B Test Results (2026-02-09):**

| Metrik | Baseline (128.6) | Test A (DeepGemm OFF) | Test B (eugr SM121) |
|--------|-----------------|----------------------|---------------------|
| `cudaError` | 49 | **0** | **0** |
| Container Restarts | 22 | 1 | 1 |
| Phase 2 Pass | 27/35 (77%) | 30/35 (86%) | 29/35 (83%) |
| Duration | ~40-60 min | 441s (7.3 min) | **404s (6.7 min)** |
| Failed Requests | 49 (lost) | 52 (recovered) | 23 (recovered) |

**Winner:** eugr image (`aegis-vllm-eugr:latest`) — 0 CUDA crashes, fastest, fewest errors.

**Acceptance Criteria:**
- [x] At least one experiment achieves 0 crashes in 50+ requests ✅ (both achieved 0)
- [x] No performance regression (tok/s within 10% of baseline) ✅ (actually faster: 404s vs ~2400s)
- [x] Winning config documented and set as default in docker-compose ✅ (eugr container active)
- [ ] Forum post with findings (if community-relevant)

---

### 128.8: E2E Pipeline Benchmark — Plaintext Fallback + 5-Doc Test (2 SP) — ✅ COMPLETE

**Goal:** Validate full production pipeline (upload → parse → chunk → extract → store → embed) with the eugr vLLM image, LightRAG removed, and no Ollama.

**Pipeline Fixes (3 code changes):**

| Fix | File | Issue |
|-----|------|-------|
| Plaintext fallback | `document_parsers.py` | `.txt`/`.md` files couldn't parse without Docling or llama_index |
| Chunking guard | `adaptive_chunking.py` | `enriched_doc=None` check required `parsed_content` fallback |
| Benchmark script | `scripts/e2e_pipeline_benchmark.py` | NEW: Production upload + Neo4j/Qdrant metrics |

**Results (2026-02-10, namespace: `e2e_bench_128c`):**

| File | Size | Time | Entities | Relations (extracted→stored) |
|------|------|------|----------|------------------------------|
| hotpot_000017.txt | 950B | 256.9s | 10 | 45→25 |
| hotpot_000014.txt | 1,277B | 27.4s | 4 | 17→7 |
| hotpot_000008.txt | 1,775B | 152.6s | 2 | 50→1 |
| hotpot_000005.txt | 2,084B | 159.9s | 5 | 66→14 |
| hotpot_000006.txt | 3,252B | 216.7s | 2 | 68→10 |
| **TOTAL** | **9,338B** | **814.5s** | **22** | **246→51** |

**Quality Metrics:**
- **Relation specificity: 76.5%** (39/51 non-RELATED_TO) — vs 21% Sprint 127
- **Entity types: 7 distinct** (PERSON, ORGANIZATION, LOCATION, DATE_TIME, CONCEPT, QUANTITY, PROCESS)
- **Relation types: 14 distinct** (LOCATED_IN, PART_OF, FOUNDED_BY, BORN_IN, WORKS_FOR, etc.)
- **CUDA crashes: 0** — eugr + DeepGemm OFF rock solid
- **Cascade: 100% Rank 1** — all extractions succeeded on first try (Ollama not needed)
- **Avg 163s/doc** — 68% faster than Sprint 127 (510s/doc, LightRAG removed)

**Timing Insight:**
Entity count drives cross-sentence window count → drives total extraction time. File size is NOT the primary driver. hotpot_000017.txt (950B, 10 entities) takes 257s while hotpot_000014.txt (1.3KB, 4 entities) takes 27s.

---

### 128.9: 15-Doc Batch Benchmark — Statistical Significance (1 SP) — ✅ COMPLETE

**Goal:** Run a larger 15-document batch to get statistically significant performance data and confirm timing patterns from 128.8.

**Results (2026-02-10, namespace: `e2e_bench_15doc`):**

| File | Size | Time | Entities | Relations |
|------|------|------|----------|-----------|
| hotpot_000017.txt | 950B | 483.6s | 32 | 15 |
| hotpot_000018.txt | 1.0KB | 397.5s | 29 | 57 |
| hotpot_000019.txt | 1.0KB | 205.3s | 9 | 11 |
| hotpot_000015.txt | 1.0KB | 358.6s | 32 | 30 |
| hotpot_000016.txt | 1.1KB | 481.6s | 16 | 0 |
| hotpot_000014.txt | 1.3KB | 18.9s | 4 | 3 |
| hotpot_000013.txt | 1.8KB | 199.0s | 13 | 10 |
| hotpot_000008.txt | 1.8KB | 292.6s | 29 | 1 |
| hotpot_000005.txt | 2.1KB | 323.2s | 4 | 3 |
| hotpot_000012.txt | 2.3KB | 332.1s | 3 | 5 |
| hotpot_000011.txt | 2.4KB | 72.4s | 1 | 0 |
| hotpot_000007.txt | 2.5KB | 538.8s | 62 | 7 |
| hotpot_000009.txt | 2.6KB | 216.9s | 14 | 9 |
| hotpot_000010.txt | 3.2KB | 321.5s | 5 | 10 |
| hotpot_000006.txt | 3.3KB | 341.8s | 2 | 1 |
| **TOTAL** | **28.4KB** | **4,587s** | **212** | **626** |

**Quality Metrics (Neo4j namespace-level):**
- **Relation specificity: 84.5%** (529/626 non-RELATED_TO) — up from 76.5% (5-doc)
- **Entity types: 15 distinct** (ORGANIZATION:50, LOCATION:44, PERSON:26, PRODUCT:18, CONCEPT:14, PROCESS:12, etc.)
- **Relation types: 20+ distinct** (PART_OF:249, LOCATED_IN:110, EMPLOYS:29, CONTAINS:24, FOUNDED_BY:21, etc.)
- **Entity dedup rate: 17%** (255 API-reported → 212 Neo4j nodes)
- **Relations/Entity: 3.0** — healthy graph density
- **CUDA crashes: 0** — 15/15 success, eugr image rock solid
- **Cascade: 100% Rank 1** — all via vLLM, zero Ollama fallbacks

**Timing Analysis (15 data points):**
- **Min: 18.9s** (4 entities), **Max: 538.8s** (62 entities), **Avg: 305.6s**
- **Throughput: 0.36 KB/min** (lower than 5-doc due to cache-free richer extraction)
- **Entity count drives time** (confirmed statistically): Correlation coefficient ~0.65 between entity count and duration
- **File size NOT correlated with time**: 950B → 484s, 3.3KB → 342s

**Key Discovery — Redis Prompt Cache Impact:**
5-doc run (with cached prompts): avg 10.4 entities/doc, avg 163s/doc
15-doc run (clean cache): avg 17.0 entities/doc, avg 306s/doc
Clean cache → 63% more entities extracted → richer knowledge graph → 88% longer processing time. The tradeoff is quality vs speed.

---

## Dependency Graph

```
128.1 (LightRAG Removal) ──→ 128.3 (Full Ingestion) ──→ RAGAS Re-evaluation
                          ↘
128.2 (Cascade Guard) ─────→ 128.3 (Full Ingestion)

128.4 (HyDE) ─────────────→ RAGAS comparison

128.5 (LLM Config UI) ────→ independent (can be done anytime)

128.7 (vLLM Stability) ───→ 128.3 (Full Ingestion)  [crash-free extraction]
```

128.1 and 128.2 can be done in parallel.
128.3 depends on 128.1, 128.2, and ideally 128.7 (stable vLLM for 488-doc batch).
128.4, 128.5, and 128.7 are independent.

---

## VRAM Budget (Post-LightRAG)

```
DGX Spark: 128 GB Unified Memory

Post-LightRAG Ingestion Mode:
  vLLM NVFP4 (0.45 util)         64.5 GB   (Extraction — no change)
  Ollama Nemotron-3-Nano         ~30 GB    (Chat fallback — no change)
  BGE-M3 Embeddings               2 GB    (No change)
  OS + CUDA Overhead             ~10 GB
  ─────────────────────────────────────
  Total (all loaded):            ~107 GB
  Free:                          ~21 GB

Note: LightRAG removal does NOT change VRAM — it removes CPU/IO overhead,
not GPU allocation. The savings are in wall-clock time (13x) and relation quality.
```

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Neo4j storage migration breaks entity linking | RAGAS CR drops | Medium | Test with 10-doc subset before full ingestion |
| DualLevelSearch returns different format than LightRAG query | Retrieval quality regression | Low | Sprint 115 already validated DualLevelSearch |
| 488-doc batch overloads system | Partial ingestion failure | Medium | Checkpoint every 50 docs, retry from last checkpoint |
| HyDE generates irrelevant hypothetical docs | CP/CR regression | Low | A/B test, disable flag |
| Cascade guard too conservative | Slower extraction | Low | Configurable wait time, log-only mode for initial deployment |

---

## Success Criteria

Sprint 128 is complete when:

- [x] `lightrag-hku` removed from pyproject.toml and environment ✅ (128.1)
- [x] No `lightrag` imports in `src/` (grep returns 0 results) ✅ (128.1)
- [ ] 10-doc re-ingestion: >70% specific relations, <10 min total
- [ ] 498/498 RAGAS Phase 1 docs ingested
- [ ] RAGAS metrics stable or improved vs Sprint 127 baseline
- [ ] Cascade timeout guard prevents competing requests
- [ ] HyDE implemented and A/B tested
- [ ] LLM Config page shows engine-aware models (vLLM disabled, Vision greyed out)
- [ ] All tests pass (unit, integration)
- [ ] Docker build succeeds
- [ ] Documentation updated (TECH_STACK.md, ARCHITECTURE.md, ADR-061)

---

## Sprint 129 — Backlog / Vorplanung

| # | Feature | SP (est.) | Priority | Origin |
|---|---------|-----------|----------|--------|
| 129.1 | Cross-Sentence Window Bisection Fallback | 3 | HIGH | Sprint 128.3a Benchmark (0-relation windows) |

### 129.1: Cross-Sentence Window Bisection Fallback (3 SP)

**Problem:** During Sprint 128.3a Cross-Sentence Window Benchmark, some windows return **0 relations** from the LLM. This happens especially with medium-to-large documents (Doc M: `w12_o3` produced [0, 0, 0] across 3 runs). The content is valid — the window is simply too large or too complex for the model to extract relations in a single call.

**Solution:** If a cross-sentence window returns 0 relations, **bisect the window** into two halves and retry extraction on each half. This ensures no content is silently dropped from the knowledge graph.

**Algorithm:**
```
extract_relations(window) → results
if len(results) == 0 AND len(window.sentences) >= 4:
    mid = len(window.sentences) // 2
    left_window  = window.sentences[:mid + overlap]
    right_window = window.sentences[mid - overlap:]
    results = extract_relations(left_window) + extract_relations(right_window)
    deduplicate(results)
```

**Constraints:**
- Only bisect once (no recursive splitting) — avoids exponential LLM calls
- Minimum window size for bisection: 4 sentences (smaller windows are genuinely empty)
- Preserve sentence overlap between halves (e.g., 1-2 sentences) to avoid missing cross-boundary relations
- Log bisection events for monitoring: `window_bisected count=1 original_sentences=12 left=7 right=7`
- Count bisected extractions separately in metrics (don't inflate normal window stats)

**Files to Modify:**
- `src/components/graph_rag/extraction_service.py` — `_extract_relations_for_window()` or equivalent
- `src/components/graph_rag/cross_sentence_extractor.py` — Window splitting logic

**Acceptance Criteria:**
- [ ] 0-relation windows trigger automatic bisection retry
- [ ] Bisected halves include configurable sentence overlap
- [ ] No recursive bisection (max 1 split per window)
- [ ] Windows with <4 sentences are NOT bisected
- [ ] Bisection events logged with structured fields
- [ ] Unit tests for bisection logic (empty window, small window skip, overlap correctness)
- [ ] Re-run Doc M benchmark: 0-relation configs should now produce >0 relations

---

## References

- [Sprint 127 Plan](SPRINT_127_PLAN.md) — RAGAS baseline (comparison point)
- [ADR-057](../adr/ADR-057-disable-smart-entity-expander.md) — DualLevelSearch as primary query
- [ADR-059](../adr/ADR-059-vllm-dual-engine.md) — Dual-engine architecture
- [ADR-061](../adr/ADR-061-lightrag-removal.md) — LightRAG removal decision
- [RAGAS Journey](../ragas/RAGAS_JOURNEY.md) — Metrics evolution
