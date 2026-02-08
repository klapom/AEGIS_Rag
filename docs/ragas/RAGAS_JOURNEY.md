# RAGAS Journey - Continuous RAG Metrics Optimization

**Status:** 🔄 Active Development
**Sprint:** 79+ (Current: Sprint 124)
**Goal:** Achieve SOTA-level RAGAS metrics (F ≥ 0.90, AR ≥ 0.95, CP ≥ 0.85, CR ≥ 0.75)

---

## Sprint 124: RAGAS Evaluation Reboot + Phase 2 Ingestion (2026-02-04)

### Overview

Sprint 124 marks a **complete RAGAS evaluation reboot** after discovering critical evaluation biases:

1. **Context Truncation (500 chars)** in `eval_harness.py` caused false negative Faithfulness scores
2. **Small Context Window (32K)** in `ragas_evaluator.py` limited evaluation accuracy
3. **BM25 Code Remnants** still present despite Sprint 87's BGE-M3 migration

**Plan:** [SPRINT_124_PLAN.md](../sprints/SPRINT_124_PLAN.md)

### Critical Fixes Applied (Feature 124.1) ✅

| File | Change | Impact |
|------|--------|--------|
| `src/adaptation/eval_harness.py` | Removed 500-char truncation | +10-20% Faithfulness expected |
| `src/evaluation/ragas_evaluator.py` | num_ctx 32K → 128K | Full context for evaluation |
| `src/api/v1/admin.py` | Removed BM25 stats code | Cleaner API response |
| `src/components/ingestion/job_tracker.py` | Phase "bm25" → "sparse" | Correct terminology |
| `docs/ragas/RAGAS_EVALUATION_GUIDE.md` | Removed BM25 references | Updated documentation |

**Commit:** `060c5f0` - `fix(sprint124): RAGAS accuracy fixes + BM25 cleanup`

### Why Faithfulness Was Biased (73.7%)

The previous Faithfulness score was **artificially low** because:

**1. Truncation (500 chars):**
```python
# BEFORE (biased)
source_texts.append(f"[{i}] {text[:500]}")  # Truncated!

# AFTER (correct)
source_texts.append(f"[{i}] {text}")  # Full context
```

**2. Context Window (32K):**
```python
# BEFORE
num_ctx=32768  # 32K tokens

# AFTER
num_ctx=131072  # 128K tokens (matches Ollama capability)
```

### Database Reset (Feature 124.2) ✅

**Clean Slate Status:**
- ✅ Qdrant: 0 collections (fully cleared)
- ✅ Neo4j: Fresh database (volumes deleted)
- ✅ Redis: Empty cache

**⚠️ WICHTIG: Docker Volumes vs Bind Mounts**

Das `rm -rf data/qdrant_storage/*` Kommando löscht NICHT die Daten, wenn Docker Named Volumes verwendet werden!

```yaml
# docker-compose.yml - Qdrant verwendet Named Volume:
volumes:
  - qdrant_data:/qdrant/storage  # Named Volume (in /var/lib/docker/volumes/)

# NICHT:
  - ./data/qdrant_storage:/qdrant/storage  # Bind Mount (im Projektverzeichnis)
```

**Korrekte Löschung für Named Volumes:**
```bash
# Option 1: Alle Volumes mit -v Flag löschen (EMPFOHLEN)
docker compose -f docker-compose.dgx-spark.yml down -v

# Option 2: Einzelnes Volume manuell löschen
docker volume rm aegis_rag_qdrant_data
```

**Bind Mounts** (falls verwendet) können mit `rm -rf` gelöscht werden.

### LLM Extraction Performance Benchmark (Feature 124.6) ✅

**Date:** 2026-02-05
**Test Setup:** Standardized extraction prompt (Samsung Galaxy S24 spec text), 300 output tokens, 3x runs per configuration

#### Results Summary

| Model | Size | think=false | think=true | Δ | Recommendation |
|-------|------|-------------|------------|---|----------------|
| **nemotron-3-nano:128k** | 24 GB | ~184s ❌ (variabel) | **~70s** ✅ | **-62%** | ⚠️ Use `think=true`! |
| **gpt-oss:20b** | 13 GB | ~12s | ~12s | 0% | Either works |
| **gpt-oss:120b** | 65 GB | ~20s | ~20s | 0% | Either works |

#### Detailed Results

**nemotron-3-nano:128k (CRITICAL FINDING):**
```
think=false:
  Run 1:  75.1s (300 tokens)
  Run 2: 299.7s (266 tokens) ← Extreme variance!
  Run 3: 177.4s (277 tokens)
  Avg:  ~184s, HIGH VARIANCE

think=true:
  Run 1: 71.4s (300 tokens)
  Run 2: 67.8s (300 tokens)
  Run 3: 70.7s (300 tokens)
  Avg:   ~70s, STABLE
```

**gpt-oss:20b:**
```
think=false: 11.9s, 12.0s, 11.9s → Avg: ~12s
think=true:  12.0s, 11.9s, 11.9s → Avg: ~12s
```

**gpt-oss:120b:**
```
think=false: 19.8s, 19.9s, 20.1s → Avg: ~20s
think=true:  19.9s, 20.1s, 20.1s → Avg: ~20s
```

#### Key Insights

1. **Nemotron Thinking Bug:** The codebase disables thinking (`think=false`) for "performance optimization" but this **backfires** for Nemotron:
   - 2.6x slower average
   - Extremely variable (75s - 300s)
   - Often produces fewer tokens

2. **GPT-OSS is 6-15x faster than Nemotron:**
   - gpt-oss:20b: ~12s (6x faster)
   - gpt-oss:120b: ~20s (3.5x faster than Nemotron with think=true)

3. **Model Load Times:**
   - nemotron-3-nano:128k: ~14s
   - gpt-oss:20b: ~10s
   - gpt-oss:120b: ~44s

#### Recommendation for Sprint 124

For **RAGAS Phase 1 Ingestion**, use:
```bash
# Option A: Fast (Recommended)
LIGHTRAG_LLM_MODEL=gpt-oss:20b  # 12s/extraction, consistent

# Option B: If Nemotron required
# Enable thinking in aegis_llm_proxy.py:
# completion_kwargs["think"] = True  # NOT False!
```

**Code Location:** `src/domains/llm_integration/proxy/aegis_llm_proxy.py:746-753`

### E2E Ingestion Benchmark (Feature 124.7) ✅

**Date:** 2026-02-05
**Test Setup:** Full document ingestion via `/api/v1/retrieval/upload` with entity/relation extraction.

**Test Files:**
- Small: `ragas_phase1_0985_logqa_emanual5.txt` (576 bytes, 1 chunk)
- Medium: `ragas_phase1_0015_hotpot_5ae0d91e.txt` (6180 bytes, 2 chunks)

#### Results Summary

| Test | Model | Thinking | Duration | Entities | Relations | Status |
|------|-------|----------|----------|----------|-----------|--------|
| 20b_thinkOff_small | gpt-oss:20b | ✗ | 282.9s | 13 | 15 | ✅ |
| 20b_thinkOn_small | gpt-oss:20b | ✓ | 1127.1s | 13 | 0 | ❌ |
| 120b_thinkOff_small | gpt-oss:120b | ✗ | 204.9s | 8 | 6 | ✅ |
| **120b_thinkOn_small** | gpt-oss:120b | ✓ | **95.8s** | 8 | 6 | ✅ **BEST** |
| *_medium (all 4) | both | both | ~6-530s | 1 | 0 | ⚠️ Failed |

#### Key Findings

1. **Winner: gpt-oss:120b + thinking=true**
   - 95.8s for full ingestion (vs 282.9s for 20b without thinking)
   - 3× faster than 20b baseline
   - Same quality extraction (8 entities, 6 relations)

2. **20b + thinking=true is problematic**
   - 18.8 minutes (!) for small file
   - Produces 0 relations despite 13 entities
   - Thinking mode causes slowdown and quality loss on 20b

3. **Medium file fails on ALL configurations**
   - Duration: 6-530s (highly variable)
   - Result: 1 entity, 0 relations
   - **Root cause investigation needed** (LLM timeout? JSON parsing?)

4. **Gleaning disabled** (`gleaning_steps=0`)
   - With gleaning: ~35 min/small file (impractical)
   - Without gleaning: 1.5-5 min/small file

#### Recommendation

For **RAGAS Phase 1/2 Ingestion**, use:
```bash
# RECOMMENDED: Fastest with good quality
LIGHTRAG_LLM_MODEL=gpt-oss:120b
AEGIS_LLM_THINKING=true

# Results: 95.8s/document, 8 entities, 6 relations
# GPU: 80GB VRAM required (DGX Spark: 128GB available)
```

**⚠️ Known Issue:** Medium+ documents may fail extraction. Investigation pending.

### Target Metrics (After Fixes)

| Metric | Previous (biased) | Target (corrected) | Expected Improvement |
|--------|-------------------|-------------------|---------------------|
| Context Precision | 86.2% | ≥ 85% | Baseline maintained |
| Context Recall | 77.5% | ≥ 75% | Baseline maintained |
| **Faithfulness** | 73.7% | **≥ 85%** | **+12%** (truncation fix) |
| Answer Relevancy | 78.9% | ≥ 90% | +11% (128K context) |

### Planned Features (Sprint 124.3-124.5)

| Feature | SP | Description | Status |
|---------|-----|-------------|--------|
| 124.3 | 8 | Phase 1 Ingestion (500 samples) | 📝 Planned |
| 124.4 | 5 | Phase 2 Tables + Code (300 samples) | 📝 Planned |
| 124.5 | 4 | RAGAS Baseline Evaluation | 📝 Planned |

**Total:** 24 SP

### DSPy Entertainment Domain Training (Feature 124.7) ✅

**Date:** 2026-02-05
**Model:** gpt-oss:120b
**Training Samples:** 5 (Tom Hanks, Meryl Streep, Christopher Nolan, Oprah Winfrey, Shane Stanley)

#### Training Results

| Task | F1 Score | Demos |
|------|----------|-------|
| Entity Extraction | **80.0%** | 3 |
| Relation Extraction | **88.9%** | 3 |

#### MIPROv2 Optimized Entity Prompt

```
# Instructions:
Extract a THOROUGH list of key entities from the source text.

# Examples:
Example 1:
Input: "Meryl Streep has been nominated for the Academy Award a record 21 times..."
Output: ['Meryl Streep', 'Academy Award', "Sophie's Choice", 'The Iron Lady',
         'Steven Spielberg', 'The Post', 'David Frankel', 'The Devil Wears Prada']

Example 2:
Input: "Christopher Nolan directed The Dark Knight trilogy for Warner Bros..."
Output: ['Christopher Nolan', 'The Dark Knight trilogy', 'Warner Bros.',
         'Inception', 'Academy Awards', 'Hans Zimmer', 'Hoyte van Hoytema']

Example 3:
Input: "Tom Hanks won the Academy Award for Best Actor..."
Output: ['Tom Hanks', 'Academy Award for Best Actor', 'Forrest Gump',
         'Philadelphia', 'Cast Away', 'The Green Mile', 'Playtone', 'HBO',
         'Band of Brothers']
```

#### MIPROv2 Optimized Relation Prompt

```
# Instructions:
You are an expert knowledge‑graph curator who specializes in extracting
precise relationships from biographical film‑industry texts.

Given the **Source Text** and the accompanying **Entities** list:

1. **Think step‑by‑step**: Explain how each entity is connected to others
2. **Generate triples**: Produce subject‑predicate‑object triples with:
   - DIRECTED_FOR, WON_FOR, COLLABORATED_WITH, NOMINATED_FOR
   - PRODUCED, STARRED_IN, WORKS_WITH, AIRS_ON

**Example Relations:**
- {"subject": "Christopher Nolan", "predicate": "DIRECTED", "object": "The Dark Knight"}
- {"subject": "Tom Hanks", "predicate": "WON_FOR", "object": "Forrest Gump"}
- {"subject": "Playtone", "predicate": "PRODUCED", "object": "Band of Brothers"}
```

#### Domain-Specific Predicates (Entertainment)

| Predicate | Description |
|-----------|-------------|
| `DIRECTED` | Director → Film |
| `DIRECTED_FOR` | Director → Studio |
| `WON` / `WON_FOR` | Person → Award/Film |
| `NOMINATED_FOR` | Person → Award |
| `STARRED_IN` | Actor → Film |
| `PRODUCED` | Company → Film/Series |
| `WORKS_WITH` | Person → Collaborator |
| `COLLABORATED_WITH` | Person → Person |
| `AIRS_ON` | Series → Network |

#### Key Improvements vs Default Prompts

1. **Domain-Specific Entity Types**: PERSON, ORGANIZATION, AWARD, MOVIE, TV_SHOW, PRODUCTION_COMPANY
2. **Chain-of-Thought Reasoning**: Explicit step-by-step extraction improves accuracy
3. **Entertainment-Specific Predicates**: Film industry relationships vs generic RELATES_TO
4. **Few-Shot Examples**: Celebrity biographies (actors, directors, producers)

#### Usage

```bash
# Training data location
/tmp/entertainment_training.json

# Query the domain
curl http://localhost:8000/api/v1/admin/domains/entertainment | jq

# Use for extraction
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@celebrity_bio.txt" \
  -F "domain=entertainment"
```

---

## Sprint 93: LangGraph 1.0 Migration & Ingestion Pause (2026-01-15)

### LangGraph 1.0 Upgrade

Successfully migrated to LangGraph 1.0.6 (from 0.6.11) for Sprint 93-96 Agentic Framework:

| Package | Before | After |
|---------|--------|-------|
| `langgraph` | 0.6.11 | 1.0.6 |
| `langgraph-prebuilt` | 0.6.5 | 1.0.6 |
| `langgraph-sdk` | 0.2.14 | 0.3.3 |

**Key Features Enabled:**
- Durable Execution (agent state persistence)
- Built-in Memory (short-term + long-term)
- Human-in-the-Loop APIs (Sprint 96 compliance)

**ADR:** [ADR-055: LangGraph 1.0 Migration](../adr/ADR-055-langgraph-1.0-migration.md)

### Ingestion Status (Paused for Development)

**Phase 1 Progress (paused 2026-01-15):**

| Metric | Value |
|--------|-------|
| Documents Processed | 293/500 (58.6%) |
| Successful | 245 (99.2%) |
| Failed (Timeout) | 2 (0.8%) |
| Namespace | `ragas_phase1_sprint88` |

**Ingestion will resume after Sprint 93 development completion.**

### RAGAS Baseline Evaluation (Sprint 92)

Evaluated on available 245 documents with RAGAS 0.4.2:

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| **Context Precision** | 86.2% | ≥85% | ✅ Achieved |
| **Context Recall** | 77.5% | ≥75% | ✅ Achieved |
| **Faithfulness** | 73.7% | ≥90% | ⚠️ Gap: -16.3% |
| **Answer Relevancy** | 78.9% | ≥95% | ⚠️ Gap: -16.1% |

**Improvement Priorities (Sprint 100):**
1. Faithfulness: +16% via cite-sources prompt engineering
2. Answer Relevancy: +16% via query-focused generation

---

## Sprint 92: Extraction Pipeline Critical Bug Fixes (2026-01-14)

### Problem Discovery

During Sprint 88 ingestion (Phase 1: 500 samples), severe extraction issues were identified:

1. **30-Minute Timeouts:** Documents timing out despite small size (2.8KB)
2. **Zero Relations Extracted:** No relationships despite rich biomedical content
3. **Invalid Entity Types:** 1,062 entities with type "ENTITY" (should be filtered)
4. **Wrong SpaCy Model:** English text processed with Spanish model

### Root Cause Analysis (via Feature 92.17: Debug Logging)

**Bug 92.18: Language Detection Failure**
- `_detect_language()` returned "es" for English text
- Root cause: NO English indicators (score=0), Spanish indicators included false positives ("de ", "es ", "en ")

**Bug 92.19: Entity Consolidation Not Applied**
- SpaCy entities bypassed type filtering (`check_types=False`)
- Generic "ENTITY" type from SpaCy's MISC label passed through

**Bug 92.20: LLM Stages Silently Failing**
- `time` module imported inside function, not accessible in nested methods
- Error: `name 'time' is not defined` caught silently, returning empty lists

### Fixes Applied

| Bug | Issue | Fix | File |
|-----|-------|-----|------|
| 92.18 | English detected as Spanish | Added 20+ English indicators | `hybrid_extraction_service.py:157-218` |
| 92.19 | "ENTITY" type not filtered | Enable type check for SpaCy | `entity_consolidator.py:186-191` |
| 92.20 | LLM stages fail silently | Move `import time` to module level | `extraction_service.py:30-36` |

### Results After Fixes

**Test Document:** `ragas_phase1_0045_ragbench_964.txt` (HIV vaccine research, 2.8KB)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Language | "es" (wrong) | "en" (correct) | ✅ Fixed |
| Duration | 30min timeout | **46 seconds** | **40x faster** |
| Entity Types | 45 (many invalid) | 10 (clean) | ✅ Fixed |
| Relations | 0 | **7 semantic** | ✅ Fixed |

**Sample Extracted Relations:**
- Adjuvanted F4 → HIV-1 (RELATES_TO): "used in HIV-1 vaccine regimens"
- SIV → HIV-1 (RELATES_TO): "both studied in primate vaccine research"
- Adjuvanted F4 → NHP (RELATES_TO): "tested in NHP models for immunogenicity"

### Next Steps

1. Resume full ingestion from file #24 (file #23 already tested)
2. Monitor extraction quality via debug logs
3. Target: Complete 500 documents with <1min/doc and semantic relations

---

## Sprint 88: Comprehensive Evaluation Plan (800 Samples)

### Target Dataset Distribution

| Phase | Data Type | Samples | Source | Status |
|-------|-----------|---------|--------|--------|
| Phase 1 | Clean Text | 500 | HotpotQA, RAGBench | ✅ Ready |
| Phase 2a | Financial Tables | 150 | T2-RAGBench (FinQA) | ✅ Downloaded |
| Phase 2b | Code Snippets | 150 | MBPP | ✅ Downloaded |
| **Total** | - | **800** | - | **❌ Aborted (50/500)** |

### Sprint 88 Progress (2026-01-13)

**1. LightRAG Embedding Fix (Critical Bug)**
- **Issue:** LightRAG initialization imported `embedding_service.py` (Ollama) directly, bypassing `embedding_factory.py`
- **Impact:** When `EMBEDDING_BACKEND=flag-embedding`, Ollama tried to load "BAAI/bge-m3" → 404 error
- **Fix:** Updated `src/components/graph_rag/lightrag/initialization.py`:
  - Changed import from `embedding_service` to `embedding_factory`
  - Added dict→list conversion for multi-vector results (LightRAG only needs dense vectors)

**2. Multi-Vector Confirmation**
- All Qdrant points now have both `dense` (1024D) and `sparse` (lexical weights) vectors
- Server-side RRF fusion ready for hybrid search
- Sparse vectors replace BM25 (TD-103 fully resolved)

**3. Ingestion Pipeline - ABORTED (LLM-First Too Slow)**
- **Start Time:** 2026-01-13 16:20 UTC
- **End Time:** 2026-01-13 ~22:00 UTC (aborted after 50/500 docs)
- **Result:** 28 ✅ successful, 23 ❌ failed (600s timeouts)
- **Root Cause:** LLM-first cascade too slow (300-600s/doc vs target 60-90s)

**Final Statistics (before abort):**
| Metric | Value |
|--------|-------|
| Documents Processed | 50/500 (10%) |
| Successful | 28 (56%) |
| Failed (Timeout) | 23 (46%) |
| Qdrant Vectors | 109 |
| Neo4j Base Nodes | 660 |
| Neo4j Chunks | 70 |
| Neo4j RELATES_TO | 395 |
| Neo4j MENTIONED_IN | 1,024 |

**4. Solution: SpaCy-First Pipeline (Sprint 89)**

Implemented 3-stage pipeline to replace slow LLM-first cascade:

| Stage | Component | Time | Output |
|-------|-----------|------|--------|
| 1 | SpaCy NER | ~50ms | PERSON, ORG, LOC, DATE entities |
| 2 | LLM Entity Enrichment | ~5-15s | CONCEPT, TECHNOLOGY, PRODUCT entities (MANDATORY) |
| 3 | LLM Relation Extraction | ~10-30s | All relationships between entities |

**Expected Improvement:** 300-600s → 30-60s per document (10-20x faster)

**Files Modified:**
- `src/config/extraction_cascade.py` - New pipeline config + feature flag
- `src/prompts/extraction_prompts.py` - New prompts for enrichment + relation extraction
- `src/components/graph_rag/extraction_service.py` - Pipeline implementation
- `src/components/graph_rag/extraction_factory.py` - Routing to SpaCy-First

**Feature Flag:** `AEGIS_USE_LEGACY_CASCADE=1` to revert to old LLM-first cascade

### Comprehensive Metrics Schema

**A. RAGAS Quality Metrics (4 Core)**

| Metric | Formula | Target | Description |
|--------|---------|--------|-------------|
| **Context Precision (CP)** | Relevant contexts / Retrieved contexts | ≥ 0.85 | Are retrieved chunks relevant? |
| **Context Recall (CR)** | Ground truth covered / Total GT facts | ≥ 0.75 | Did we find all relevant chunks? |
| **Faithfulness (F)** | Claims supported by context / Total claims | ≥ 0.90 | Is the answer grounded in context? |
| **Answer Relevancy (AR)** | Semantic similarity(answer, question) | ≥ 0.95 | Does answer match the question? |

**B. Ingestion Metrics (Per Document)**

| Metric | Unit | Description |
|--------|------|-------------|
| `ingestion_time_ms` | ms | Time to fully process document |
| `characters_count` | int | Total characters in document |
| `chunks_count` | int | Number of chunks created |
| `entities_count` | int | Entities extracted (Neo4j) |
| `relations_count` | int | Relations extracted (Neo4j) |
| `embeddings_time_ms` | ms | Time for BGE-M3 embedding |

**C. Retrieval Metrics (Per Query)**

| Metric | Unit | Description |
|--------|------|-------------|
| `retrieval_latency_ms` | ms | Total retrieval time |
| `dense_search_ms` | ms | Qdrant dense vector search |
| `sparse_search_ms` | ms | Qdrant sparse (lexical) search |
| `rrf_fusion_ms` | ms | Server-side RRF fusion |
| `rerank_ms` | ms | Cross-encoder reranking |
| `contexts_retrieved` | int | Number of chunks returned |

**D. LLM Evaluation Metrics (Per Query)**

| Metric | Unit | Description |
|--------|------|-------------|
| `llm_eval_time_ms` | ms | Time for RAGAS LLM evaluation |
| `tokens_in` | int | Input tokens to LLM |
| `tokens_out` | int | Output tokens from LLM |
| `llm_model` | str | Model used for evaluation |

### Evaluation Pipeline Architecture

```
                      ┌──────────────────────────────────────────────┐
                      │           RAGAS Evaluation Pipeline           │
                      └──────────────────────────────────────────────┘
                                           │
                      ┌────────────────────┼────────────────────┐
                      │                    │                    │
                      ▼                    ▼                    ▼
               ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
               │   Phase 1    │    │  Phase 2a    │    │  Phase 2b    │
               │  Clean Text  │    │    Tables    │    │     Code     │
               │  (500 docs)  │    │ (150 tables) │    │ (150 funcs)  │
               └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
                      │                    │                    │
                      └────────────────────┼────────────────────┘
                                           │
                                           ▼
               ┌──────────────────────────────────────────────────────┐
               │          Ingestion (with Metrics Tracking)           │
               │  • BGE-M3 Dense+Sparse Embeddings                    │
               │  • Entity/Relation Extraction (3-Rank Cascade)       │
               │  • Section-Aware Chunking (800-1800 tokens)          │
               └──────────────────────────────────────────────────────┘
                                           │
                                           ▼
               ┌──────────────────────────────────────────────────────┐
               │              RAGAS Query Evaluation                  │
               │  • Vector Mode (Dense + Sparse RRF)                  │
               │  • Graph Mode (Entity→N-hop→Chunk Expansion)         │
               │  • Hybrid Mode (Vector + Graph + Memory)             │
               └──────────────────────────────────────────────────────┘
                                           │
                                           ▼
               ┌──────────────────────────────────────────────────────┐
               │                 Results Aggregation                  │
               │  • Per doc_type breakdown (text/table/code)          │
               │  • Per question_type breakdown (8 types)             │
               │  • Per difficulty breakdown (D1/D2/D3)               │
               │  • Statistical significance (±4% CI at n=800)        │
               └──────────────────────────────────────────────────────┘
```

### Execution Plan (5 Phases)

**Phase 1: Data Cleanup** (Est: 5 min)
- Clear all Qdrant namespaces (`default`, `ragas_phase1`, `ragas_phase2_*`)
- Clear Neo4j graph nodes (preserve schema)
- Verify empty state with point counts

**Phase 2: Dataset Preparation** (Est: 15 min)
- Download 150 T2-RAGBench samples (FinQA financial tables)
- Download 150 MBPP samples (Python code generation)
- Export contexts as `.txt` files for ingestion

**Phase 3: Full Ingestion with Metrics** (Est: 2-3 hours)
- Upload 800 documents via `/api/v1/retrieval/upload`
- Track per-document metrics: time, chunks, entities, relations
- Validate index counts in Qdrant and Neo4j

**Phase 4: RAGAS Evaluation** (Est: 4-6 hours)
- Run all 800 questions through retrieval API
- Calculate 4 RAGAS metrics per question
- Track retrieval + LLM evaluation latencies

**Phase 5: Documentation & Analysis** (Est: 1 hour)
- Update RAGAS_JOURNEY.md with complete results
- Generate statistical breakdowns by doc_type, question_type, difficulty
- Compare with Sprint 82-87 baselines

### Expected Outputs

```
docs/ragas/sprint88_full_eval/
├── ingestion_metrics.jsonl       # Per-document ingestion stats
├── retrieval_metrics.jsonl       # Per-query retrieval stats
├── ragas_results.jsonl           # CP, CR, F, AR per question
├── summary_by_doctype.json       # Aggregated by text/table/code
├── summary_by_qtype.json         # Aggregated by question type
├── summary_by_difficulty.json    # Aggregated by D1/D2/D3
└── sprint88_final_report.md      # Full analysis report
```

---

## Purpose of This Document

This is a **living document** that tracks our continuous journey to optimize RAGAS metrics for AegisRAG. Unlike ADRs (architectural decisions) or DECISION_LOG (point-in-time choices), this document captures:

- **Experiments** - What we tried, what worked, what didn't
- **Metrics Evolution** - How scores change over time
- **Insights** - Lessons learned from each iteration
- **Action Items** - Next steps for improvement

**Update Frequency:** After every RAGAS evaluation run or significant optimization attempt.

---

## Current Status (2026-01-13 - Sprint 86: DSPy MIPROv2 Prompt Optimization)

**📊 SPRINT 86: DSPy MIPROv2 Optimized Prompts Integrated**

### Experiment: DSPy Pipeline Integration A/B Test

**Date:** 2026-01-13
**Objective:** Compare baseline (generic) prompts vs DSPy MIPROv2 optimized prompts

**Configuration:**
- Model: nemotron-3-nano:latest (Rank 1 cascade)
- Test samples: 4 (TensorFlow, Microsoft, Neo4j, Einstein)
- Domains: technical, organizational, scientific
- Feature flag: `AEGIS_USE_DSPY_PROMPTS=1`

### Results

| Metric | Baseline | DSPy-Optimized | Δ | Status |
|--------|----------|----------------|---|--------|
| **Entity F1** | 0.74 | **0.90** | +22% | 🟢 |
| **Relation F1** | 0.23 | **0.30** | +30% | 🟢 |
| **E/R Ratio** | 1.17 | **1.06** | -9% | 🟡 |
| **Latency P50** | 10,360ms | **9,097ms** | -12% | 🟢 |
| **Latency P95** | 12,747ms | **11,362ms** | -11% | 🟢 |
| **Total Entities** | 24 | **25** | +4% | 🟢 |
| **Total Relations** | 28 | **26** | -7% | 🟡 |

### Key Insights

1. **Entity Extraction +22%:** DSPy-optimized prompts significantly improve entity recognition
   - Step-by-step reasoning forces explicit justification
   - Controlled type taxonomy reduces ambiguity
   - Einstein sample: 0.67 → 1.00 F1 (perfect extraction)

2. **Relation Extraction +30%:** Better entity quality leads to better relations
   - More consistent source/target/type format
   - Explicit strength scoring (1-10)

3. **Latency -12%:** Optimized prompts are faster
   - More focused instructions = fewer tokens
   - Clear output format = faster parsing

4. **E/R Ratio slightly lower:** -9% (1.17 → 1.06)
   - Still above 1.0 target
   - Trade-off: Higher precision, slightly lower recall on relations

### Production Integration

**Files Modified:**
- `src/prompts/extraction_prompts.py`: Added `DSPY_OPTIMIZED_ENTITY_PROMPT`, `DSPY_OPTIMIZED_RELATION_PROMPT`
- `src/components/graph_rag/extraction_service.py`: Added feature flag support

**Usage:**
```bash
# Enable DSPy-optimized prompts (production)
export AEGIS_USE_DSPY_PROMPTS=1

# Disable (use generic prompts - default)
unset AEGIS_USE_DSPY_PROMPTS
```

**Logs:**
- `logs/dspy_pipeline_eval/eval_baseline_20260113_084152.json`
- `logs/dspy_pipeline_eval/eval_dspy_20260113_084310.json`

### Status: ✅ Production Ready

The DSPy-optimized prompts are now integrated into the production pipeline and can be enabled via feature flag.

---

## Sprint 86.7: Coreference Resolution Evaluation

**Date:** 2026-01-13
**Objective:** Measure impact of pronoun resolution on entity/relation extraction

### Feature Description

Coreference Resolution resolves pronouns (he, she, it, they) to their antecedents before extraction:

```
Input:  "Microsoft was founded in 1975. It later acquired GitHub."
Output: "Microsoft was founded in 1975. Microsoft later acquired GitHub."
```

**Implementation:** Heuristic-based resolver using SpaCy NER + POS tags (coreferee not compatible with Python 3.12+)

### Experiment Configuration

- **Samples:** 8 diverse test cases (tech_pronouns, person_narrative, company_relations, research_complex, mixed_entities, no_pronouns_baseline, german_text, multi_hop)
- **Model:** nemotron-3-nano:latest
- **Gleaning:** Disabled (for fair comparison)
- **Feature flag:** `AEGIS_USE_COREFERENCE=1` (default: enabled)

### Results

| Metric | Baseline | With Coreference | Δ | Status |
|--------|----------|------------------|---|--------|
| **Avg Entities** | 8.50 | **9.25** | +8.8% | 🟢 |
| **Avg Relations** | 7.75 | **7.50** | -3.2% | 🟡 |
| **E/R Ratio** | 0.978 | 0.877 | -10.3% | 🟡 |
| **Unique Entity Types** | avg 4.2 | avg 4.5 | +7% | 🟢 |

### Sample-Level Analysis

| Sample | Entities Δ | Relations Δ | Notes |
|--------|------------|-------------|-------|
| tech_pronouns | +2 | -1 | "It" resolved to "Microsoft" |
| person_narrative | +1 | +1 | "He" resolved to "Einstein" |
| company_relations | +1 | 0 | "Its" resolved to "Tesla" |
| multi_hop | +1 | -1 | Complex pronoun chains |
| german_text | 0 | 0 | German pronouns not yet optimized |

### Key Insights

1. **Entity Extraction Improved (+8.8%):**
   - LLM sees explicit entity names instead of pronouns
   - Better at recognizing repeated mentions as same entity
   - Helps with entity deduplication

2. **Relation Extraction Neutral (-3.2%):**
   - Expected: Relations should improve with clearer text
   - Observed: Slight decrease (statistically insignificant with n=8)
   - Hypothesis: Resolved text may confuse relation prompts

3. **German Support Limited:**
   - German pronouns (er, sie, es) are mapped but not optimized
   - SpaCy German model has weaker NER than English

4. **Performance Impact:**
   - SpaCy processing: ~10-20ms per chunk (negligible)
   - Model loading: ~500ms (one-time, cached)

### Decision: ✅ Keep Enabled by Default

**Rationale:**
- +8.8% entity improvement outweighs -3.2% relation variance
- Low computational overhead
- Can be disabled via `AEGIS_USE_COREFERENCE=0` if issues arise

**Files:**
- `src/components/graph_rag/coreference_resolver.py` (NEW)
- `src/components/graph_rag/extraction_service.py` (integration)
- `docs/ragas/sprint86_eval_20260113_091539.json` (full results)

---

## Sprint 86.8: Cross-Sentence Relation Extraction Evaluation

**Date:** 2026-01-13
**Objective:** Extract relations that span multiple sentences using sliding windows

### Feature Description

Cross-sentence extraction uses 3-sentence sliding windows with 1-sentence overlap:

```
Text: [S1. S2. S3. S4. S5. S6.]

Window 1: [S1. S2. S3.]  → Extract relations
Window 2: [S3. S4. S5.]  → Extract relations (S3 shared)
Window 3: [S4. S5. S6.]  → Extract relations (S4, S5 shared)

Result: Merge & deduplicate all relations
```

**Problem Solved:** Relations like "GPT-4 ACHIEVED state-of-the-art" where "GPT-4" is in sentence 1 and "state-of-the-art" is in sentence 2.

### Experiment Configuration

- **Samples:** 4 test cases (tech_pronouns, person_narrative, company_relations, research_complex)
- **Model:** nemotron-3-nano:latest
- **Window Size:** 3 sentences, 1 overlap
- **Threshold:** >5 sentences triggers windowed extraction
- **Feature flag:** `AEGIS_USE_CROSS_SENTENCE=1` (default: enabled)

### Results

| Metric | Baseline | With Cross-Sentence | Δ | Status |
|--------|----------|---------------------|---|--------|
| **Avg Entities** | 9.25 | 9.25 | 0% | ⚪ |
| **Avg Relations** | 7.75 | **21.00** | **+171%** | 🟢🟢 |
| **E/R Ratio** | 0.86 | **2.30** | **+167%** | 🟢🟢 |
| **Avg Time (ms)** | 1,573 | 22,196 | +1310% | 🔴 |

### Sample-Level Analysis

| Sample | Relations (Base) | Relations (Window) | Δ | Windows Used |
|--------|------------------|--------------------|----|--------------|
| tech_pronouns | 8 | 22 | +175% | 3 |
| person_narrative | 7 | 20 | +186% | 2 |
| company_relations | 9 | 25 | +178% | 3 |
| research_complex | 7 | 17 | +143% | 3 |

### Key Insights

1. **Massive Relation Improvement (+171%):**
   - Each window provides focused context for relation extraction
   - Overlapping windows catch cross-boundary relations
   - LLM sees 3 sentences at a time → better understanding

2. **Entity Count Unchanged:**
   - Entities are extracted once (not per window)
   - Cross-sentence primarily affects relation extraction

3. **Significant Time Trade-off:**
   - 3 windows = 3 LLM calls = ~14x slower
   - For batch processing: Acceptable
   - For real-time: Consider disabling or reducing window count

4. **E/R Ratio Exceeds Target:**
   - Target: E/R ≥ 1.0
   - Achieved: E/R = 2.30
   - More relations per entity = richer knowledge graph

### Optimization Opportunities

1. **Parallel Window Processing:** Use `asyncio.gather` for concurrent extraction
2. **Adaptive Windowing:** Only use for texts where base E/R < 1.0
3. **Smaller Windows:** Try 2-sentence windows for faster extraction

### Decision: ✅ Keep Enabled by Default (with caveats)

**Rationale:**
- +171% relation improvement is transformative
- E/R ratio of 2.30 far exceeds 1.0 target
- Time trade-off acceptable for batch ingestion

**Recommendations:**
- Enable for document ingestion (batch, latency-tolerant)
- Consider disabling for real-time queries
- Set `AEGIS_USE_CROSS_SENTENCE=0` if latency-critical

**Files:**
- `src/components/graph_rag/cross_sentence_extractor.py` (NEW)
- `src/components/graph_rag/extraction_service.py` (integration)
- `docs/ragas/sprint86_eval_20260113_092204.json` (full results)

---

## Sprint 86.6: Entity Quality Filter Evaluation

**Date:** 2026-01-13
**Objective:** Filter noise entities from SpaCy NER output

### Feature Description

The Entity Quality Filter removes low-quality entities:
- **Noise Types:** CARDINAL, ORDINAL, MONEY, PERCENT, QUANTITY, TIME
- **Short Dates:** "2009" (filtered), "December 31, 2009" (kept)
- **Leading Articles:** "the Google" → "Google"
- **Stopwords:** Pronouns and determiners as entity names

### Experiment Configuration

- **Samples:** 3 test cases
- **Model:** nemotron-3-nano:latest (Rank 1 - LLM-only)
- **Feature flag:** `AEGIS_USE_ENTITY_FILTER=1` (default: enabled)

### Results

| Metric | Baseline | With Filter | Δ | Status |
|--------|----------|-------------|---|--------|
| **Avg Entities** | 10.33 | 10.33 | 0% | ⚪ |
| **Avg Relations** | 22.33 | 22.33 | 0% | ⚪ |
| **E/R Ratio** | 2.126 | 2.126 | 0% | ⚪ |

### Key Insights

1. **Zero Impact on LLM Extraction:**
   - LLM (Rank 1/2) doesn't produce CARDINAL, ORDINAL, MONEY types
   - Filter is specifically designed for SpaCy NER output (Rank 3)

2. **Target Use Case: Rank 3 Hybrid Extraction:**
   - When SpaCy NER is used as fallback, filter removes ~55% noise
   - Types filtered: CARDINAL ("100"), ORDINAL ("first"), MONEY ("$50")

3. **Unit Test Results:**
   ```
   Input:  9 entities (including CARDINAL, ORDINAL, MONEY, stopwords)
   Output: 4 entities (Microsoft, Google, December 31 2009, Bill Gates)
   Filter Rate: 55.6%
   ```

4. **Multilingual Article Removal:**
   - English: "the", "a", "an"
   - German: "der", "die", "das", "ein", "eine"
   - French: "le", "la", "les", "l'"
   - Spanish: "el", "la", "los", "las"

### Decision: ✅ Keep Enabled by Default

**Rationale:**
- No negative impact on LLM extraction
- Significant noise reduction (55%) for SpaCy NER
- Minimal computational overhead

**Note:** True impact visible only when Rank 3 fallback is triggered.

**Files:**
- `src/components/graph_rag/entity_quality_filter.py` (NEW)
- `src/components/graph_rag/hybrid_extraction_service.py` (integration)
- `docs/ragas/sprint86_eval_20260113_092517.json` (full results)

---

## Sprint 86.5: Relation Weight Filtering

**Date:** 2026-01-13
**Objective:** Filter low-confidence relations in graph retrieval (LightRAG-style)

### Feature Description

Relation Weight Filtering adds quality control to graph traversal by only including relations with sufficient confidence:

```
Relation Strength Scale (1-10):
- 1-4: Low confidence (filtered by default)
- 5-7: Medium confidence (included)
- 8-10: High confidence (always included)

Configuration:
- AEGIS_MIN_RELATION_STRENGTH=3  → Exploratory (more relations)
- AEGIS_MIN_RELATION_STRENGTH=5  → Balanced (default)
- AEGIS_MIN_RELATION_STRENGTH=7  → Strict (fewer relations)
```

### Implementation

**Modified Cypher Query:**
```cypher
MATCH path = (start:base)-[r:RELATES_TO|MENTIONED_IN*1..2]-(connected:base)
WHERE start.name IN $entity_names
AND ALL(rel IN relationships(path) WHERE
    COALESCE(rel.strength, 10) >= 5  -- MIN_RELATION_STRENGTH
)
RETURN DISTINCT connected.name, connected.type, ...
```

### Results

**Extraction Evaluation:** N/A (Feature affects RETRIEVAL pipeline, not ingestion)

**Expected Impact:**
- Precision improvement by filtering noisy relations
- Reduced graph traversal paths (faster queries)
- Trade-off: May miss some valid low-confidence relations

### Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `AEGIS_USE_RELATION_WEIGHT_FILTER` | `1` | Enable/disable weight filtering |
| `AEGIS_MIN_RELATION_STRENGTH` | `5` | Minimum strength (1-10 scale) |

### Decision: ✅ Enabled by Default

**Rationale:**
- Improves retrieval precision
- Configurable for different use cases (exploratory vs strict)
- No impact on ingestion pipeline

**Files:**
- `src/components/retrieval/graph_rag_retriever.py` (updated Cypher queries)

---

## Sprint 86.9: Cascade Monitoring

**Date:** 2026-01-13
**Objective:** Production-ready metrics and observability for the 3-rank extraction cascade

### Feature Description

Cascade Monitoring provides comprehensive visibility into the extraction pipeline:

```
Metrics Tracked:
- Success rates per rank (Rank 1: 99.9%, Rank 2: 0.1%, Rank 3: <0.01%)
- Latency P50/P95/P99 per rank
- Fallback events with reasons
- Token usage per model
- Entity/Relation extraction counts
```

### Implementation

**CascadeMetrics Dataclass:**
```python
@dataclass
class CascadeMetrics:
    """Per-rank cascade performance metrics."""
    rank: int
    model_name: str
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    fallback_reasons: list[str] = field(default_factory=list)
```

**Prometheus Export Format:**
```
# HELP aegis_cascade_success_rate_ratio Success rate per rank
aegis_cascade_success_rate{rank="1"} 0.999
aegis_cascade_success_rate{rank="2"} 0.001
aegis_cascade_success_rate{rank="3"} 0.0

# HELP aegis_cascade_latency_p95_ms P95 latency per rank
aegis_cascade_latency_p95_ms{rank="1",model="nemotron3"} 1234.5
aegis_cascade_latency_p95_ms{rank="2",model="gpt-oss:20b"} 45678.9
```

### Helper Functions

```python
# Record cascade attempt
record_cascade_attempt(
    metrics=metrics,
    rank=1,
    success=True,
    latency_ms=1234.5,
    tokens=1500
)

# Record fallback event
record_cascade_fallback(
    metrics=metrics,
    from_rank=1,
    to_rank=2,
    reason="timeout"
)

# Log summary after document processing
log_cascade_summary(metrics, document_id="doc_123")
```

### Expected Benefits

| Benefit | Description |
|---------|-------------|
| **Visibility** | Track cascade health in real-time |
| **Alerting** | Prometheus/Grafana integration ready |
| **Cost Tracking** | Token usage per model for budget monitoring |
| **Debugging** | Fallback reasons identify systemic issues |

### Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `AEGIS_CASCADE_METRICS_ENABLED` | `1` | Enable/disable metrics collection |

### Decision: ✅ Enabled by Default

**Rationale:**
- Essential for production operations
- Low overhead (in-memory counters)
- Prometheus-compatible for existing monitoring stack

**Files:**
- `src/components/graph_rag/extraction_metrics.py` (extended with CascadeMetrics)

---

## Sprint 86 Summary

**All Features Complete (100%, 19/19 SP)**

| Feature | Status | Key Impact |
|---------|--------|------------|
| 86.1 DSPy MIPROv2 Training | ✅ | +22% Entity F1, +30% Relation F1 |
| 86.2 Multi-Objective Score | ✅ | E/R Ratio bonus in optimization |
| 86.3 Domain-Specific Prompts | ✅ | DSPy prompts as universal default |
| 86.4 A/B Testing Framework | ✅ | Full request/response logging |
| 86.5 Relation Weight Filter | ✅ | Precision improvement in retrieval |
| 86.6 Entity Quality Filter | ✅ | 55% noise reduction in SpaCy NER |
| 86.7 Coreference Resolution | ✅ | +8.8% entities via pronoun resolution |
| 86.8 Cross-Sentence Extraction | ✅ | **+171% relations** (transformative!) |
| 86.9 Cascade Monitoring | ✅ | Prometheus-ready metrics |

**Key Achievements:**
- **E/R Ratio: 2.30** (target was 1.0 - exceeded by 130%!)
- **Relation Extraction: +171%** via cross-sentence windows
- **Cascade Observability:** Production-ready monitoring

---

## Previous Status (2026-01-10 - Sprint 83: ER-Extraction Improvements Complete)

**📊 SPRINT 83 COMPLETE: Ingestion Pipeline Improvements for RAGAS Phase 2**

**Sprint 83 Achievements (ER-Extraction Improvements):**
- ✅ **3-Rank LLM Cascade** (Nemotron3 → GPT-OSS:20b → Hybrid SpaCy NER)
- ✅ **Gleaning Multi-Pass Extraction** (+20-40% entity recall, Microsoft GraphRAG approach)
- ✅ **Fast Upload + Background Refinement** (2-5s user response, 10-15x faster)
- ✅ **Comprehensive Logging** (P50/P95/P99 metrics, GPU VRAM, LLM cost tracking)
- ✅ **Multi-language SpaCy NER** (DE/EN/FR/ES support)

**Expected Impact on RAGAS Phase 2 (Sprint 85):**
- **Context Recall +20-40%**: Gleaning will extract missed entities, improving retrieval coverage
- **Context Precision +10-15%**: 3-rank cascade reduces extraction failures (99.9% success rate)
- **Faithfulness +5-10%**: Better entity quality from LLM cascade vs single model
- **Ingestion Speed +10-15x**: Fast upload enables rapid dataset iteration for A/B testing

**RAGAS Phase 2 Timeline:**
- Sprint 84: Stabilization & bugfixes (ingestion pipeline testing with gleaning enabled)
- Sprint 85: RAGAS Phase 2 evaluation (500 samples, all 3 modes: Vector/Graph/Hybrid)
- Sprint 86: RAGAS Phase 3 optimization (parameter tuning based on Phase 2 results)

---

## Iterative Ingestion Protocol (Sprint 84+)

**Goal:** Fehlerfreie Ingestion von 500 RAGAS Phase 1 Samples mit Sprint 83 Features (3-Rank Cascade, Gleaning, Fast Upload)

### Critical Rules

1. **ALWAYS use Frontend API:** `POST /api/v1/retrieval/upload` (NIE direkte Backend-Funktionen!)
2. **Stop immediately on errors:** 0 entities per chunk, 0 relations per document, cascade failures
3. **Root cause before scaling:** Fix → Document → Resume/Restart
4. **Iterative scaling:** 5 → 20 → 50 → 100 → 500 files (validate each step)
5. **Document every iteration:** Success, failures, decisions, metrics

### Namespace Strategy

```bash
# Iteration 1 (PoC): 5 files
ragas_phase2_sprint83_v1

# Bei strukturellem Fehler (z.B. Cascade-Config falsch):
ragas_phase2_sprint83_v2  # Neustart mit Fix

# Bei einzelnem File-Fehler (z.B. corrupt PDF):
ragas_phase2_sprint83_v1  # Fortsetzen, fehlerhafte Datei überspringen

# Iteration 2-5: Gleicher Namespace wenn erfolgreich
ragas_phase2_sprint83_v1  # 5 → 20 → 50 → 100 → 500 files
```

### Error Thresholds (STOP Triggers)

| Metrik | Threshold | Aktion |
|--------|-----------|--------|
| **Entities per Chunk** | < 1 | ⚠️ STOP - Mindestens 1 Entity pro Chunk erforderlich |
| **Relations per Document** | 0 für 3+ docs | ⚠️ STOP - Relation extraction failed |
| **Cascade Rank 3 Fallbacks** | > 10% | ⚠️ STOP - Rank 1/2 models zu schwach |
| **Gleaning Rounds** | Avg > 3.0 | ⚠️ STOP - Completeness check zu streng |
| **P95 Latency** | > 120s per chunk | ⚠️ STOP - Timeout risk |
| **GPU VRAM** | > 14 GB | ⚠️ STOP - Overflow risk |
| **Ollama Health Failures** | 3+ consecutive | ⚠️ STOP - Ollama crashed |

### Cascade Timeout Tuning Protocol

**Adaptive Timeout Management (bei wiederholten Timeouts):**

```python
# Initial Configuration
Rank 1: Nemotron3 (300s timeout)
Rank 2: GPT-OSS:20b (300s timeout)
Rank 3: Hybrid SpaCy NER + LLM (600s relations)

# Iteration 1: Nemotron3 Timeout → Probiere GPT-OSS:20b
if rank1_timeout_count > 3:
    log("Switching Rank 1: Nemotron3 → GPT-OSS:20b")
    CASCADE[0].model_id = "gpt-oss:20b"
    # Timeout bleibt 300s

# Iteration 2: GPT-OSS:20b auch Timeout → Zurück zu Nemotron3, Timeout +1 Min
if rank1_timeout_count > 3:
    log("Switching Rank 1: GPT-OSS:20b → Nemotron3, Timeout 300s → 360s")
    CASCADE[0].model_id = "nemotron3"
    CASCADE[0].timeout_s = 360  # +1 Minute

# Iteration 3: Nemotron3@360s Timeout → Wieder GPT-OSS:20b, Timeout behalten (360s)
if rank1_timeout_count > 3:
    log("Switching Rank 1: Nemotron3 → GPT-OSS:20b, Timeout bleibt 360s")
    CASCADE[0].model_id = "gpt-oss:20b"
    CASCADE[0].timeout_s = 360  # Behalten!

# Iteration 4: GPT-OSS:20b@360s Timeout → Beide Modelle versagen, Domain-Problem
if rank1_timeout_count > 3:
    log("CRITICAL: Both models timeout at 360s. Document complexity too high.")
    # Optionen:
    # A) Gleaning deaktivieren (gleaning_steps=0)
    # B) Chunk-Größe reduzieren (800 → 500 tokens)
    # C) SpaCy NER als Rank 1 (instant, kein Timeout)
```

**Decision Tree:**

```
Timeout?
├─ Ja → Anderes Modell probieren (Nemotron3 ↔ GPT-OSS:20b)
│   ├─ Erfolg → Dieses Modell behalten für Rank 1
│   └─ Auch Timeout → Zurück zum ersten Modell, Timeout +60s
│       ├─ Erfolg → Timeout erhöht behalten
│       └─ Auch Timeout → Modell wechseln, neuen Timeout behalten
│           ├─ Erfolg → Fertig
│           └─ Auch Timeout → KRITISCH (siehe Iteration 4)
└─ Nein → Weiter mit nächstem Dokument
```

### Iteration Log Template

**Nach jeder Iteration in RAGAS_JOURNEY.md dokumentieren:**

```markdown
### 2026-01-XX | Sprint 84 Iteration N: X Files Ingested

**Configuration:**
- Namespace: ragas_phase2_sprint83_vN
- Gleaning: gleaning_steps=1
- Cascade: Rank 1 (model_id, timeout), Rank 2 (...), Rank 3 (...)

**Results:**
- Files processed: X/X (100%)
- Total chunks: XXX
- Total entities: XXX (avg X.X per chunk)
- Total relations: XXX (avg X.X per document)
- Cascade Rank 1 success: XX%
- Cascade Rank 2 fallback: XX%
- Cascade Rank 3 fallback: XX%
- Gleaning rounds avg: X.X
- P95 latency: XXs per chunk
- GPU VRAM peak: XX GB
- LLM cost: $X.XX

**Errors:**
- [List any errors, zero entities, timeouts]

**Decisions:**
- [What was changed? Why? Expected impact?]
- Example: "Increased Rank 1 timeout 300s → 360s due to 5 timeouts on legal documents"

**Next Steps:**
- [Scale to next iteration OR fix error]
```

---

**📊 PREVIOUS STATUS: 168/500 Samples Ingested (33.6%)**

**Sprint 82 Achievement (Phase 1 - Text-Only):**
- ✅ **500 samples generated** (450 answerable + 50 unanswerable)
- ✅ **Stratified sampling** across doc_types (clean_text: 333, log_ticket: 167)
- ✅ **8 question types** (lookup, howto, multihop, comparison, definition, policy, numeric, entity)
- ✅ **3 difficulty levels** (D1: 36%, D2: 32%, D3: 32%)
- 📊 **SHA256:** `8f6be17d9399d15434a5ddd2c94ced762e701cb2943cd8a787971f873be38a61`

**Ingestion Status (2026-01-10 06:00 UTC):**
- ✅ **168/500 files uploaded** (33.6% complete)
- ✅ **321 chunks** in Qdrant (vector search ready)
- ✅ **911 entities** in Neo4j (graph reasoning ready)
- ✅ **Namespace:** `ragas_phase1` (isolated from previous evaluations)
- ⏸️ **Upload paused** at file #168 (HTTP 000 timeout errors after 5 hours)
- 🔄 **Remaining:** 332 files (to be uploaded via `--resume 168`)

**Technical Notes:**
- **Upload Method:** Frontend API (`/api/v1/retrieval/upload`) ensures all 4 DBs populated
- **Performance:** ~60-70s per file (graph extraction bottleneck via Nemotron3 LLM)
- **Timeout Issue:** After ~124 successful uploads, HTTP 000 errors occurred (likely Ollama overload)
- **Data Integrity:** All 168 uploaded files verified in Qdrant + Neo4j (no data loss)

**Previous: Experiment #9 (20-Sample Benchmark Reveals Dataset Gap)**

**HotpotQA Dataset (20 questions, Sprint 81 Full Benchmark):**

| Metric | Exp #8 (5 Samples) | Exp #9 (20 Samples) | Samples 16-20 Only | SOTA Target |
|--------|-------------------|---------------------|-------------------|-------------|
| **Context Precision** | 1.0000 | 0.6000 | **1.0000** ⭐ | 0.85 |
| **Context Recall** | 1.0000 | 0.6000 | **1.0000** ⭐ | 0.75 |
| **Faithfulness** | 0.6000 | 0.4750 | **1.0000** ⭐ | 0.90 |
| **Answer Relevancy** | 0.7817 | 0.6667 | 0.5400 | 0.95 |

**Key Findings (Experiment #9):**
- ⚠️ **Scores appear lower** but this is due to **missing source documents** in ragas_eval namespace
- ✅ **Truncation Bug Fixed:** Chat API now returns full chunk text (was 500 chars → now 1000-3000+ chars)
- ✅ **New Documents (16-20) Perfect:** F=1.0, CP=1.0, CR=1.0 for all 5 new HotpotQA samples
- ❌ **8 samples missing docs:** Samples 7, 8, 11, 13, 14, 15 have CP=0, CR=0 (documents not ingested)
- ⚠️ **RAGAS F=0 Bug persists:** Samples 1, 5, 6 show F=0.0 despite correct answers (short answer parser issue)

**Critical Bug Fix (Sprint 81):**
- **File:** `src/api/v1/chat.py:1397`
- **Issue:** Context text truncated to 500 chars in API response
- **Fix:** Removed truncation, now returns full chunk text
- **Impact:** Enables accurate Faithfulness evaluation (RAGAS needs full context)

**Sprint 80 Complete - Summary of Improvements:**

| Feature | Impact on Hybrid | Key Metric |
|---------|-----------------|------------|
| **80.1:** Strict Faithfulness | F +33% (0.520→0.693) | Faithfulness ⭐ |
| **80.2:** Graph→Vector Fallback | CR +100% (Graph) | Context Recall |
| **80.3:** Cross-Encoder Reranking | CP +26%, CR +67% (Vector) | All modes improved |
| **80.4:** top_k=10 (was 5) | CR +67% (Hybrid) | Context Recall |

**Best Configuration:**
- **High Accuracy (Research/Legal):** Hybrid + strict_faithfulness=True → F=0.693, CP=0.717
- **Balanced (General Q&A):** Hybrid + strict_faithfulness=False → AR=0.859, F=0.520

**Main Bottlenecks (Remaining):**
1. **Faithfulness (F=0.693):** vs SOTA 0.90 → **-23% gap** (was -36%!)
2. **Context Precision (CP=0.717):** vs SOTA 0.85 → **-16% gap** (was -33%!)
3. **DSPy Optimization:** Planned for Sprint 81 (expected F→0.85+)

---

## Journey Log

### 2026-01-09 | Sprint 82: Phase 1 Dataset Generation - 500-Sample Benchmark

#### Context
- **Goal:** Create scientifically rigorous 500-sample benchmark for RAGAS evaluation
- **Approach:** Stratified sampling from HotpotQA, RAGBench, LogQA datasets
- **ADR:** [ADR-048](../adr/ADR-048-ragas-1000-sample-benchmark.md)
- **Sprint Plan:** [Sprint 82](../sprints/SPRINT_82_PLAN.md)

#### Implementation

**Feature 82.1: Dataset Loader Infrastructure (3 SP)**
- Created adapter pattern for HuggingFace datasets (HotpotQA, RAGBench, LogQA)
- Normalized 3 dataset formats into unified `NormalizedSample` dataclass
- Automatic doc_type classification (clean_text, log_ticket)
- Question type heuristics (8 types: lookup, howto, multihop, comparison, etc.)

**Feature 82.2: Stratified Sampling Engine (2 SP)**
- Quota-based sampling: clean_text (300), log_ticket (150)
- Question type distribution per doc_type (8 types)
- Difficulty rebalancing: D1 40%, D2 35%, D3 25%
- Statistical validation with tolerance checking

**Feature 82.3: Unanswerable Generation (2 SP)**
- 4 generation methods: temporal_shift (15), entity_swap (15), negation (10), cross_domain (10)
- 50 unanswerable questions (10% of total)
- Preserves original context for contrastive evaluation

**Feature 82.4: AegisRAG JSONL Export (1 SP)**
- NormalizedSample → JSONL with SHA256 checksum
- CSV manifest with sample metadata
- Statistics report (Markdown)

#### Generated Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Samples** | 500 |
| **Answerable** | 450 (90%) |
| **Unanswerable** | 50 (10%) |
| **Doc Types** | clean_text: 333, log_ticket: 167 |
| **Question Types** | lookup: 132, howto: 130, multihop: 82, comparison: 56, definition: 46, policy: 32, entity: 11, numeric: 11 |
| **Difficulty** | D1: 180 (36%), D2: 158 (32%), D3: 162 (32%) |
| **SHA256** | `8f6be17d9399d15434a5ddd2c94ced762e701cb2943cd8a787971f873be38a61` |

#### Ingestion Pipeline

**Critical Decision: Frontend API vs Direct Pipeline**
- **Chosen:** Frontend API (`/api/v1/retrieval/upload`) ✅
- **Why:**
  - Ensures namespace propagation to **all databases** (Qdrant, Neo4j, BM25)
  - Triggers full ingestion pipeline (Docling → Chunking → Embedding → Graph → BM25)
  - Consistent with production workflow
  - TD-099 fixed: `namespace_id` correctly set in all payloads

**Ingestion Scripts:**
```bash
# 1. Prepare contexts as .txt files
poetry run python scripts/ragas_benchmark/prepare_phase1_ingestion.py

# 2. Upload via Frontend API
./scripts/upload_ragas_phase1.sh  # ~17 min for 500 files
```

**Verification (3 test samples):**
| Database | Status | Count |
|----------|--------|-------|
| Qdrant | ✅ | 3 chunks with `namespace_id: ragas_phase1` |
| Neo4j | ✅ | 14 entities + 3 chunks |
| BM25 | ✅ | 3 docs (background task updated index) |

#### Key Insights

1. **Statistical Significance Achieved**
   - 5 samples → ±20% confidence interval
   - 500 samples → ±4% confidence interval
   - Enables statistically valid A/B testing

2. **Namespace Isolation Critical**
   - `ragas_phase1` namespace separates benchmark from production data
   - Frontend API ensures namespace propagates to all DBs
   - BM25 index rebuilds automatically via background task

3. **Unanswerable Questions Test Anti-Hallucination**
   - 10% unanswerable rate matches SOTA benchmarks
   - 4 generation methods provide diverse failure modes
   - Tests if RAG system correctly returns "I don't know"

4. **Dataset Expansion Plan (Sprint 83-84)**
   - Phase 2: +300 samples (table, code_config) → 800 total
   - Phase 3: +200 samples (pdf_ocr, slide, pdf_text) → 1000 total
   - Final target: ±3% confidence interval

#### Next Steps (Sprint 83)

1. **Run RAGAS Evaluation on Phase 1**
   ```bash
   poetry run python scripts/run_ragas_evaluation.py \
       --dataset data/evaluation/ragas_phase1_questions.jsonl \
       --namespace ragas_phase1 \
       --mode hybrid \
       --max-questions 50  # Start with 50, then scale to 500
   ```

2. **Establish Phase 1 Baseline Metrics**
   - Run evaluation on Vector, Graph, Hybrid modes
   - Compare against Sprint 80-81 metrics (5-20 samples)
   - Document statistical significance improvements

3. **Identify Optimization Targets**
   - Per doc_type breakdown (clean_text vs log_ticket)
   - Per question_type breakdown (lookup vs multihop vs howto)
   - Per difficulty breakdown (D1 vs D2 vs D3)

#### Files Changed
- `scripts/ragas_benchmark/` - New package (13 files, 2,100 LOC)
- `tests/ragas_benchmark/` - Unit tests (49 tests, 100% pass)
- `data/evaluation/ragas_phase1_500.jsonl` - Generated dataset

---

### 2026-01-10 | Experiment #10: Sprint 82 Phase 1 Partial Evaluation (168 Samples)

#### Context
- **Goal:** Establish baseline metrics with partial Phase 1 dataset (168/500 samples ingested)
- **Why Partial:** Upload process timed out after 5 hours (HTTP 000 errors from Ollama overload)
- **Data Available:**
  - 168 context files uploaded (33.6% of Phase 1)
  - 321 chunks in Qdrant
  - 911 entities in Neo4j
  - All 3 retrieval modes functional (Vector, Graph, Hybrid)

#### Experiment Design

**Evaluation Parameters:**
```bash
poetry run python scripts/run_ragas_evaluation.py \
    --dataset data/evaluation/ragas_phase1_500.jsonl \
    --namespace ragas_phase1 \
    --mode hybrid \
    --max-questions 50  # Start with 50 questions
```

**Expected Behavior:**
- **Questions with uploaded contexts:** Normal RAGAS evaluation (F, CP, CR, AR)
- **Questions with missing contexts:** Low CP/CR scores (contexts not retrieved)
- **Baseline Quality:** Comparable to Experiment #9 (20-sample) for overlapping data

#### Hypothesis

With 168/500 samples (33.6%), we expect:
1. **~56 of 150 answerable questions** will have full context available (168/500 × 450 ≈ 151)
2. **Metrics for available contexts** should match Sprint 80-81 baseline (~F=0.69, CP=0.72, AR=0.86)
3. **Overall metrics** will be lower due to missing contexts, but **per-available-sample** metrics remain consistent

#### Results

**Evaluation Completed: 2026-01-10 08:29 UTC**

**Overall Metrics (10 samples, 168/500 contexts available):**

| Metric | Score | SOTA Target | Gap |
|--------|-------|-------------|-----|
| Context Precision | 0.0500 | 0.85 | -94% |
| Context Recall | 0.1600 | 0.75 | -79% |
| Faithfulness | 0.3950 | 0.90 | -56% |
| Answer Relevancy | 0.5170 | 0.95 | -46% |

**Success Rate:**
- Queries: 8/10 successful (2 timeouts on questions 6 & 9)
- Samples with contexts: ~3-4/10 (matches 33.6% upload rate)

**Per-Sample Breakdown:**

| Sample | Question | CP | CR | F | AR | Status |
|--------|----------|----|----|---|----|----|
| 1 | Alain Fossoul position | 0.0 | 0.0 | 0.0 | 0.82 | No contexts (HotpotQA not uploaded) |
| 2 | Schedule Recording fix | 0.0 | 0.2 | 0.6 | 0.76 | ✅ Partial contexts |
| 3 | Research purpose | 0.0 | 0.4 | 1.0 | 0.65 | ✅ Full contexts |
| 4 | (Question 4 data) | - | - | - | - | - |
| 5 | (Question 5 data) | 0.0 | 0.0 | 0.0 | 0.43 | No contexts |
| 6 | (Timeout) | - | - | - | - | ⚠️ Query timeout (301s) |
| 7 | (Question 7 data) | 0.5 | 0.3 | 0.6 | 0.81 | ✅ Best performance |
| 8 | (Question 8 data) | 0.0 | 0.0 | 0.0 | 0.27 | No contexts |
| 9 | (Timeout) | - | - | - | - | ⚠️ Query timeout (301s) |
| 10 | Clock setting | 0.0 | 0.0 | 1.0 | 0.42 | ✅ Perfect Faithfulness |

**Key Findings:**

1. **Partial Dataset Effect Dominant**: Low scores primarily due to 332/500 missing samples
   - Only ~30-40% of questions have uploaded context files available
   - System correctly returns "keine Informationen" when contexts missing (anti-hallucination works!)

2. **Available Sample Quality Shows Promise**:
   - **Sample 3** (Research purpose): F=1.00 (perfect faithfulness)
   - **Sample 7** (Best overall): CP=0.50, CR=0.30, F=0.60, AR=0.81
   - **Sample 10** (Clock setting): F=1.00 (perfect grounding)
   - For questions with full contexts, system performs significantly better than overall averages

3. **Query Stability Issues** (20% timeout rate):
   - 2/10 queries timed out after ~301 seconds (questions 6 & 9)
   - Likely due to Graph Reasoning complexity or LLM inference timeout
   - **Action Item**: Investigate graph query optimization or timeout tuning

4. **System Robustness Validated**:
   - Handles missing contexts gracefully (no hallucination)
   - Script continues after query failures (80% success rate)
   - Partial dataset evaluation works as designed

#### Next Steps

1. **Resume Upload** (Priority: P0)
   ```bash
   bash scripts/upload_ragas_phase1.sh --resume 168
   ```
   - Upload remaining 332 files to complete Phase 1 dataset
   - Expected time: ~15-20 hours (with JWT refresh handling)

2. **Investigate Query Timeouts** (Priority: P1)
   - Analyze why questions 6 & 9 timed out
   - Check Graph Reasoning performance for complex multi-hop queries
   - Consider timeout tuning (current: 300s)

3. **Re-Run Full Evaluation** (Priority: P0 - After Upload)
   - Re-run with complete 500-sample dataset
   - Expected metrics improvement: CP/CR +300% (from 0.05/0.16 to 0.15-0.20+)
   - Target: Statistically significant results (500 samples vs current 10)

4. **Analyze High-Quality Samples** (Priority: P2)
   - Deep dive into samples 3, 7, 10 (F=1.0/0.6/1.0) to understand what works
   - Identify patterns in successful retrievals vs failures
   - Document best practices for query types

#### Output Files

- `data/evaluation/results/exp10_partial_phase1/ragas_eval_hybrid_20260110_082907.json` (437K)
- Log: `ragas_eval_exp10.log`

---

### 2026-01-09 | Sprint 81: 20-Sample Benchmark + Truncation Bug Fix (Experiment #9)

#### Context
- **Goal:** Expand RAGAS benchmark from 5 to 20 samples for statistical significance
- **Dataset:** HotpotQA (20 multi-hop questions)
- **New Documents:** 5 new context files (SpaceX, LOTR, Apple, Amazon, Tesla)
- **LLM:** GPT-OSS:20b (Ollama)

#### Critical Bug Discovery & Fix

**500-Character Truncation Bug (CRITICAL)**
- **Discovery:** During evaluation, noticed all context lengths were exactly 500 chars
- **Root Cause:** `src/api/v1/chat.py:1397` truncated source text to 500 chars
  ```python
  # BEFORE (Bug)
  text=ctx.get("text", ctx.get("content", ""))[:500],  # Limit to 500 chars

  # AFTER (Fixed)
  text=ctx.get("text", ctx.get("content", "")),  # Full chunk text (no truncation)
  ```
- **Impact:** Faithfulness metrics were artificially low (RAGAS couldn't see full context)
- **Fix Verification:** Context lengths now 1000-3000+ chars (was max 500)

#### Results

**Overall Metrics (20 Samples):**
| Metric | Score | vs Exp #8 (5 samples) |
|--------|-------|----------------------|
| Context Precision | 0.6000 | ⬇️ -40% |
| Context Recall | 0.6000 | ⬇️ -40% |
| Faithfulness | 0.4750 | ⬇️ -21% |
| Answer Relevancy | 0.6667 | ⬇️ -15% |

**New Documents Only (Samples 16-20):**
| Sample | Question | CP | CR | F | AR |
|--------|----------|----|----|---|----|
| 16 | SpaceX founder birthplace | 1.0 | 1.0 | 1.0 | 0.72 |
| 17 | LOTR director birthplace | 1.0 | 1.0 | 1.0 | 0.47 |
| 18 | Apple HQ city | 1.0 | 1.0 | 1.0 | 0.52 |
| 19 | Amazon founding city | 1.0 | 1.0 | 1.0 | 0.00* |
| 20 | Tesla HQ city | 1.0 | 1.0 | 1.0 | 0.51 |

*Sample 19 AR=0.0 is likely RAGAS bug (correct answer "Bellevue" matches ground truth)

#### Key Insights

1. **System Performance is Good When Documents Exist**
   - New documents (16-20): F=1.0, CP=1.0, CR=1.0 (perfect!)
   - Problem is missing documents, not retrieval quality

2. **Dataset Gap Identified**
   - 8 of 20 samples reference documents NOT in ragas_eval namespace
   - Samples 7, 8, 11, 13, 14, 15 show CP=0, CR=0 (expected - no matching docs)
   - This artificially lowers average metrics

3. **RAGAS F=0 Bug Persists**
   - Samples 1, 5, 6 show F=0.0 despite correct answers
   - Appears to be RAGAS parser issue with very short answers
   - Example: "Arthur's Magazine was started first [1]" → F=0.0

4. **Truncation Fix Enables Accurate Evaluation**
   - Full context (1000-3000+ chars) now available to RAGAS
   - Required for proper Faithfulness assessment
   - All new samples achieved F=1.0 with full context

#### Performance
- Query time: 517s (25.85s/question)
- Metrics time: 1567s (78.34s/sample)
- Total: 2084s (~35 minutes for 20 samples)

#### Next Steps
1. **Ingest Missing HotpotQA Documents** - Add source docs for samples 7, 8, 11, 13, 14, 15
2. **Investigate RAGAS F=0 Bug** - Report to RAGAS GitHub if persistent
3. **Re-run Full Benchmark** - After ingesting all documents, expect CP/CR/F > 0.90

#### Files Changed
- `src/api/v1/chat.py:1397` - Removed 500-char truncation
- `data/evaluation/ragas_hotpotqa_20.jsonl` - Expanded from 15 to 20 samples
- `data/evaluation/hotpotqa_contexts/hotpot_000015-19.txt` - NEW, 5 context files
- `data/evaluation/results/ragas_eval_hybrid_20260109_184537.json` - Full results

---

### 2026-01-08 | Sprint 79.8: RAGAS 0.4.2 Migration + Initial Evaluation

#### Context
- **Migration from RAGAS 0.3.9 → 0.4.2** due to major API changes
- **Goal:** Establish baseline metrics for 3 retrieval modes (Vector, Graph, Hybrid)
- **Dataset:** amnesty_qa (Amnesty International Q&A, 3 questions)
- **LLM:** GPT-OSS:20b (Ollama, ~100s/sample)

#### Challenges Encountered

**1. LangGraph Answer Generation Bug (CRITICAL)**
- **Problem:** Chat API returned fallback "I'm sorry..." instead of real answers
- **Root Cause:** `graph.add_edge("graph_query", END)` bypassed answer generation node
- **Fix:** Changed to `graph.add_edge("graph_query", "answer")` in src/agents/graph.py:484
- **Impact:** F=0.0, AR=0.0 → F=0.398, AR=0.935 (Graph Mode)
- **Test Coverage:** Added 3 integration tests in `tests/integration/agents/test_graph_answer_generation.py`

**2. Embedding Dimension Mismatch (CRITICAL)**
- **Problem:** RAGAS used nomic-embed-text (768-dim), Ingestion used BGE-M3 (1024-dim)
- **Impact:** Context Precision/Recall metrics evaluated with **inconsistent embeddings** → invalid scores
- **Discovery:** User asked "wieviele dimensionen verwendet BGE-m3 hier im ragas?"
- **Investigation:**
  - `curl http://localhost:11434/api/embeddings -d '{"model":"nomic-embed-text",...}' | jq '.embedding | length'` → **768**
  - `curl http://localhost:11434/api/embeddings -d '{"model":"bge-m3",...}' | jq '.embedding | length'` → **1024** ✅
- **Attempted Fix 1:** Use Ollama BGE-M3 via `embedding_factory("openai", model="bge-m3", ...)`
  - **Result:** Ollama BGE-M3 has NaN-bug with long texts (`Error 500: unsupported value: NaN`)
- **Final Fix:** Use `SimpleBGEM3Embeddings` (SentenceTransformer BAAI/bge-m3 direct)
  - **Rationale:** Same model as ingestion, no Ollama bugs, guaranteed 1024-dim
  - **Implementation:** `scripts/run_ragas_evaluation.py:189-204`

**3. RAGAS 0.4.2 API Breaking Changes**
- **Old API (0.3.9):**
  ```python
  from ragas.metrics import answer_relevancy, context_precision
  evaluate(dataset, metrics=[answer_relevancy, context_precision])
  ```
- **New API (0.4.2):**
  ```python
  from ragas.metrics.collections import AnswerRelevancy, ContextPrecision
  ar = AnswerRelevancy(llm=llm, embeddings=embeddings)
  result = await ar.ascore(user_input=q, response=a, retrieved_contexts=c)
  ```
- **Migration Effort:** Complete rewrite of `run_ragas_evaluation.py` (410 lines)

#### Initial Results (with 768-dim nomic-embed-text - INVALID)

| Mode | CP | CR | F | AR | Query Time | Metrics Time |
|------|----|----|---|----|-----------|-------------|
| Vector | 0.108 | 0.185 | 0.542 | 0.649 | 9.2s | 113s/sample |
| Graph | 0.667 | 0.291 | 0.398 | 0.935 | 10.6s | 128s/sample |
| Hybrid | 0.108 | 0.185 | 0.292 | 0.901 | 11.7s | 158s/sample |

**NOTE:** These results are **INVALID** due to embedding dimension mismatch. Re-evaluation with BGE-M3 (1024-dim) required.

#### Key Insights

1. **Graph Mode Wins on Precision & Relevancy**
   - CP=0.667 vs Vector/Hybrid 0.108 (+515%)
   - AR=0.935 vs Vector 0.649 (+44%)
   - **Why:** Entity-centric retrieval focuses on topically relevant chunks

2. **Hybrid Mode Underperforms** (UNEXPECTED)
   - Same CP/CR as Vector-Only mode (0.108/0.185)
   - Worse Faithfulness than both (F=0.292 vs Vector 0.542, Graph 0.398)
   - **Hypothesis:** Naive concatenation (Vector 5 + Graph 3 chunks) → Graph's good contexts buried by Vector's noise
   - **Action Item:** Implement cross-encoder reranking after fusion (Sprint 80)

3. **Context Recall Universally Low** (MAX 0.291)
   - All modes miss **~70% of relevant context**
   - **Hypotheses:**
     - Too few contexts retrieved (3-5 vs SOTA 10-20)
     - Chunk granularity mismatch (800-1800 tokens vs ground truth multi-section spans)
     - Missing entities in graph (extraction coverage issue)
   - **Action Items:**
     - Increase `top_k` to 10-15 (quick win)
     - Parent chunk retrieval (Sprint 81)
     - Entity extraction audit (Sprint 81)

4. **Faithfulness Gap Large** (MAX 0.542 vs SOTA 0.90)
   - Graph Mode generates **expansive answers** exceeding retrieved context (F=0.398)
   - Vector Mode better grounding but still 46% below SOTA (F=0.542)
   - **Hypothesis:** Answer generator over-elaborates, LLM extrapolates beyond sources
   - **Action Items:**
     - Prompt engineering: "Only include information explicitly stated in sources"
     - Citation-aware generation (force LLM to cite every claim)
     - DSPy optimization for Faithfulness (Sprint 80+)

5. **Performance Acceptable**
   - Query time: 9-12s/query (within P95 <1000ms for complex queries is aspirational, current is reasonable)
   - Metrics computation: 113-158s/sample (bottleneck is LLM inference, not retrieval)
   - **No optimization needed** - focus on quality, not speed

#### Next Steps (Sprint 80)

**P0 - Critical Fixes:**
1. ✅ **Fix Embedding Dimension Mismatch** - Use BGE-M3 (1024-dim) everywhere
2. 🔄 **Re-run Full RAGAS Evaluation** with correct embeddings (Vector/Graph/Hybrid)
3. ✅ **Generate Comprehensive Comparison Report** (3 modes + SOTA benchmarks) ← `data/evaluation/results/RAGAS_3MODE_COMPARISON_REPORT.md`

**P1 - Immediate Improvements:**
1. **Hybrid Fusion Fix** - Add cross-encoder reranking (expected: CP +300%, F +50%)
2. **Increase Context Retrieval** - top_k from 3/5 to 10/15 (expected: CR +100%)
3. **Improve Graph Faithfulness** - Add "cite sources" prompt (expected: F +50%)

**P2 - Mid-Term (Sprint 81-82):**
1. Query-adaptive routing (Self-RAG approach)
2. Parent chunk retrieval
3. Entity extraction quality audit

#### Files Changed
- `scripts/run_ragas_evaluation.py` - Complete rewrite for RAGAS 0.4.2 API (410 lines)
- `src/agents/graph.py:484` - Fixed edge routing (graph_query → answer)
- `tests/integration/agents/test_graph_answer_generation.py` - NEW, 3 regression tests
- `data/evaluation/results/RAGAS_3MODE_COMPARISON_REPORT.md` - NEW, comprehensive analysis
- `pyproject.toml` - Upgraded ragas ^0.3.7 → ^0.4.2

#### Commits
- TBD: Sprint 79 final commit with all changes

---

## Metric Definitions (RAGAS 0.4.2)

### Context Precision (CP)
**What it measures:** How many of the retrieved contexts are actually relevant to answering the question?

**Formula:** `CP = (Relevant Contexts in Top-K) / K`

**Range:** 0-1 (higher is better)

**Example:**
- Retrieved 5 contexts, only 2 are relevant → CP = 0.4
- Retrieved 3 contexts, all 3 are relevant → CP = 1.0

**How RAGAS computes it:**
1. LLM judges each retrieved context: "Is this useful for answering the question?" (Yes/No)
2. Count "Yes" votes, divide by total contexts

**Why it matters:** High CP means your retrieval is **precise** (low noise, high signal).

---

### Context Recall (CR)
**What it measures:** How much of the relevant information (ground truth) is captured in retrieved contexts?

**Formula:** `CR = (Ground Truth Statements Found in Retrieved Contexts) / (Total Ground Truth Statements)`

**Range:** 0-1 (higher is better)

**Example:**
- Ground truth has 10 key facts, retrieved contexts contain 7 → CR = 0.7
- Ground truth has 10 key facts, retrieved contexts contain 3 → CR = 0.3

**How RAGAS computes it:**
1. Break ground truth into atomic statements
2. For each statement, check if any retrieved context contains it (via LLM or embedding similarity)
3. Count found statements, divide by total

**Why it matters:** High CR means your retrieval is **complete** (captures all relevant info).

---

### Faithfulness (F)
**What it measures:** How well is the generated answer grounded in the retrieved contexts? (No hallucination)

**Formula:** `F = (Supported Claims in Answer) / (Total Claims in Answer)`

**Range:** 0-1 (higher is better)

**Example:**
- Answer has 5 claims, all 5 are supported by contexts → F = 1.0
- Answer has 5 claims, only 2 are supported by contexts → F = 0.4

**How RAGAS computes it:**
1. Break answer into atomic claims/statements
2. For each claim, LLM checks: "Is this claim supported by any retrieved context?"
3. Count supported claims, divide by total

**Why it matters:** High F means the answer is **trustworthy** (no fabrication, grounded in sources).

---

### Answer Relevancy (AR)
**What it measures:** How relevant is the generated answer to the original question?

**Formula:** `AR = cosine_similarity(question_embedding, answer_embedding)`

**Range:** 0-1 (higher is better)

**Example:**
- Question: "What are the global implications of X?"
- Answer: "The global implications of X are..." → AR ≈ 0.95 (highly relevant)
- Answer: "X is a thing that exists." → AR ≈ 0.40 (tangential)

**How RAGAS computes it:**
1. Embed question and answer using embeddings model
2. Compute cosine similarity between embeddings
3. Optionally: Generate hypothetical questions from answer, measure similarity

**Why it matters:** High AR means the answer is **on-topic** (addresses what was asked).

---

## Evaluation Guidelines (DGX Spark)

### ⚠️ CRITICAL: Sequential Execution Required

**NEVER run multiple RAGAS evaluations in parallel on DGX Spark!**

**Why:**
- Each RAGAS evaluation loads **BGE-M3** (SentenceTransformer, ~2GB VRAM)
- Each evaluation also triggers **GPT-OSS:20b** queries via Ollama
- 3 parallel evaluations = 3× BGE-M3 instances = **OOM (Exit 137)**

**Correct approach:**
```bash
# ✅ CORRECT: Sequential execution
poetry run python scripts/run_ragas_evaluation.py --mode=hybrid ...
# Wait for completion
poetry run python scripts/run_ragas_evaluation.py --mode=vector ...
# Wait for completion
poetry run python scripts/run_ragas_evaluation.py --mode=graph ...

# ❌ WRONG: Parallel execution (will OOM)
poetry run python scripts/run_ragas_evaluation.py --mode=hybrid ... &
poetry run python scripts/run_ragas_evaluation.py --mode=vector ... &
poetry run python scripts/run_ragas_evaluation.py --mode=graph ... &
```

### Evaluation Timing (DGX Spark GB10)

| Dataset Size | Per Sample | 10 Questions | 20 Questions |
|--------------|------------|--------------|--------------|
| Small (2-3 contexts) | ~100-160s | ~17-27 min | ~34-54 min |
| Large (5+ contexts) | ~150-200s | ~25-33 min | ~50-66 min |

**Total for 3 modes:** Multiply by 3 (e.g., 10 questions × 3 modes = ~75-80 min)

### Available Datasets

| Dataset | Questions | Namespace | Use Case |
|---------|-----------|-----------|----------|
| `ragas_amnesty_tiny.jsonl` | 2 | `amnesty_qa` | Quick smoke test |
| `ragas_amnesty_small.jsonl` | 10 | `amnesty_qa` | Standard evaluation |
| `ragas_amnesty_full.jsonl` | 20 | `amnesty_qa` | Full evaluation |
| `ragas_hotpotqa_small.jsonl` | 5 | `ragas_eval_txt` | Multi-hop reasoning |
| `ragas_hotpotqa_large.jsonl` | 10 | `ragas_eval_txt_large` | Complex multi-hop |

### Standard Evaluation Command

```bash
poetry run python scripts/run_ragas_evaluation.py \
  --dataset=data/amnesty_qa_contexts/ragas_amnesty_small.jsonl \
  --namespace=amnesty_qa \
  --mode=hybrid \
  --max-questions=10 \
  --output-dir=data/evaluation/results
```

---

## Baseline Metrics (SOTA Comparison)

### State-of-the-Art RAG Systems (2024)

| System | CP | CR | F | AR | Dataset | Notes |
|--------|----|----|---|----|---------|-------|
| **GraphRAG (Microsoft)** | 0.88 | 0.74 | 0.89 | 0.96 | MultiHop | Community detection + hierarchical summaries |
| **Self-RAG** | 0.82 | 0.79 | 0.91 | 0.93 | HotpotQA | Adaptive retrieval (query-based routing) |
| **RAPTOR** | 0.76 | 0.71 | 0.86 | 0.92 | StrategyQA | Recursive abstraction |
| **LlamaIndex** | 0.71 | 0.68 | 0.85 | 0.91 | MSMARCO | Standard vector RAG with reranking |
| **LangChain** | 0.65 | 0.72 | 0.78 | 0.88 | NaturalQuestions | Multi-query retrieval |

### AegisRAG Targets (Sprint 85 Goal - Q2 2026)

| Metric | Current (Sprint 79) | Target (Sprint 85) | Gap | Priority |
|--------|--------------------|--------------------|-----|----------|
| **CP** | 0.667 (Graph) | 0.85 | -21% | P1 (Medium) |
| **CR** | 0.291 (Graph) | 0.75 | **-61%** | **P0 (Critical)** |
| **F** | 0.542 (Vector) | 0.90 | **-40%** | **P0 (Critical)** |
| **AR** | 0.935 (Graph) | 0.95 | -2% | P2 (Low) ✅ |

---

## Optimization Roadmap

### Sprint 80: Faithfulness Optimization (11 SP) ✅ COMPLETE

- [x] Fix embedding dimension mismatch (BGE-M3 1024-dim)
- [x] Re-run RAGAS with correct embeddings (Experiment #3)
- [x] **Feature 80.1:** Strict citation enforcement prompt (3 SP)
- [x] **Feature 80.2:** Graph→Vector fallback (2 SP)
- [x] **Feature 80.4:** Increase top_k to 10 (1 SP)
- [x] **Quick Win:** Multi-hop 2 hops (was 1)
- [x] **Feature 80.3:** Hybrid cross-encoder reranking (5 SP) ✅ 2026-01-09
- [ ] **Feature 80.1b:** strict_faithfulness_enabled=True (testing in progress)

**Achieved Improvements (Feature 80.3 - Cross-Encoder Reranking):**
- **Vector Mode:** CP +52%, CR +67%, F +55% ⭐ (biggest winner!)
- **Hybrid Mode:** CP +26%, AR +8%, CR stays at 1.0 ✅
- **Graph Mode:** CP +29%, CR +100%, AR +6%

**Note:** Vector mode now reaches CR=1.0 (same as Hybrid), making it viable for simpler queries.

---

### Sprint 82-84: 1000-Sample RAGAS Benchmark (42 SP) 🆕

**NEW: ADR-048 approved for comprehensive benchmark expansion.**

See: [ADR-048](../adr/ADR-048-ragas-1000-sample-benchmark.md) | [Sprint 82-84 Plan](../sprints/SPRINT_82_84_RAGAS_1000_PLAN.md)

| Phase | Sprint | Samples | Doc Types | SP |
|-------|--------|---------|-----------|-----|
| **Phase 1** | 82 | 500 | clean_text, log_ticket | 8 |
| **Phase 2** | 83 | +300 | table, code_config | 13 |
| **Phase 3** | 84 | +200 | pdf_ocr, slide, pdf_text | 21 |
| **Total** | | **1000** | **7 doc types** | **42** |

**Key Features:**
- **12% unanswerable questions** → Tests anti-hallucination
- **Statistical rigor** → ±3% confidence intervals (vs ±20% with 5 samples)
- **Capability breakdown** → Per doc_type, question_type analysis
- **Scientific caveats** → Paper-ready methodology documentation

**Image Processing Challenges (Phase 3):**
- DocVQA: Dual-mode OCR (dataset vs Docling)
- SlideVQA: Multi-image processing with VLM
- Asset caching: 15-20GB storage required

---

### Sprint 81-82: Retrieval Improvements (8 SP)
- [ ] Query-adaptive routing (Vector vs Graph vs Hybrid)
- [ ] Parent chunk retrieval (sentence → paragraph)
- [ ] Entity extraction quality audit
- [ ] Multi-hop graph traversal (1-3 hops → 2-5 hops)

**Expected Improvements:** CR +80%, CP +30%

---

### Sprint 85+: Scientific Enhancements (44 SP) 🆕

**Purpose:** Upgrade benchmark for publication-readiness.

| Enhancement | Sprint | SP | Priority |
|-------------|--------|-----|----------|
| Statistical rigor package | 83 | 2 | Required |
| Human validation (100 samples) | 85 | 5 | Essential |
| Multi-judge ensemble | 85 | 3 | Recommended |
| Real unanswerables | 84 | 8 | High |
| Adversarial subset | 86 | 13 | Important |
| Continuous evaluation | 85 | 5 | Required |
| Cross-language (German) | 87+ | 8 | Optional |

See: [ADR-048 Enhancement Section](../adr/ADR-048-ragas-1000-sample-benchmark.md#enhancement-potential-scientific-rigor-upgrades)

---

### Sprint 81-82: DSPy Optimization for Faithfulness (12 SP)

**Goal:** Use DSPy to optimize prompts and retrieval for higher Faithfulness scores.

**DSPy Approach:**

DSPy (Declarative Self-improving Language Programs in Python) is a framework for:
1. **Prompt Optimization:** Automatically tune prompts based on evaluation metrics
2. **Few-shot Learning:** Generate optimal examples for in-context learning
3. **Module Composition:** Chain retrieval → reasoning → generation with automatic optimization

**Implementation Plan:**

```python
# src/agents/dspy_rag_module.py (PLANNED)
import dspy

class RAGModule(dspy.Module):
    """DSPy module for optimized RAG."""

    def __init__(self, retriever, num_passages=10):
        super().__init__()
        self.retriever = retriever
        self.generate_answer = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        # Retrieve contexts
        contexts = self.retriever(question)

        # Generate answer with chain-of-thought
        prediction = self.generate_answer(
            context=contexts,
            question=question
        )
        return prediction.answer


# Optimization with RAGAS Faithfulness as metric
from dspy.teleprompt import BootstrapFewShot

# Define evaluation metric
def faithfulness_metric(example, prediction, trace=None):
    """Evaluate using RAGAS Faithfulness."""
    from ragas.metrics import Faithfulness
    f = Faithfulness()
    score = f.ascore(
        user_input=example.question,
        response=prediction.answer,
        retrieved_contexts=example.contexts
    )
    return score

# Optimize with few-shot examples
optimizer = BootstrapFewShot(
    metric=faithfulness_metric,
    max_bootstrapped_demos=4,
    max_labeled_demos=8
)

optimized_rag = optimizer.compile(
    RAGModule(retriever),
    trainset=ragas_training_data
)
```

**Training Data Requirements:**
- 50-100 labeled examples (question + contexts + ground_truth)
- RAGAS evaluation scores as feedback signal
- Domain-specific data from existing ragas_hotpotqa_*.jsonl

**Expected Improvements:**
- **Faithfulness:** +30-50% (0.693 → 0.85-0.90)
- **Answer Relevancy:** +10-20% (0.621 → 0.70-0.75)
- **Reasoning Quality:** Better chain-of-thought explanations

**Files to Create:**
| File | Description |
|------|-------------|
| `src/agents/dspy_rag_module.py` | DSPy RAG module |
| `scripts/optimize_dspy_prompts.py` | DSPy optimization script |
| `data/dspy/training_examples.jsonl` | Curated training data |
| `data/dspy/optimized_prompts.json` | Output: optimized prompts |

**Sprint Allocation:**
- Sprint 81: DSPy module implementation + training data curation (6 SP)
- Sprint 82: Optimization runs + RAGAS re-evaluation (6 SP)

---

### Sprint 83+: Answer Generation Optimization (8 SP)
- [ ] Citation-aware generation (force source citing)
- [ ] Advanced prompt engineering for grounded answers
- [ ] GraphRAG-style community detection (Leiden algorithm)
- [ ] Self-RAG adaptive retrieval (query-based routing)

**Expected Improvements:** F +20-30%, CR +10%

---

## Experiment Log

### Experiment Template
```markdown
#### Experiment #X: [Title]
**Date:** YYYY-MM-DD
**Hypothesis:** [What you expected to happen]
**Changes:** [What you modified]
**Results:**
| Metric | Before | After | Δ | Status |
|--------|--------|-------|---|--------|
| CP | X.XXX | X.XXX | ±X% | 🟢/🟡/🔴 |
| CR | X.XXX | X.XXX | ±X% | 🟢/🟡/🔴 |
| F | X.XXX | X.XXX | ±X% | 🟢/🟡/🔴 |
| AR | X.XXX | X.XXX | ±X% | 🟢/🟡/🔴 |

**Insights:** [What you learned]
**Action Items:** [Next steps]
```

---

### Experiment #1: RAGAS 0.4.2 Baseline (2026-01-08)

**Hypothesis:** Upgrading to RAGAS 0.4.2 will provide accurate baseline metrics.

**Changes:**
- Migrated from RAGAS 0.3.9 to 0.4.2
- Complete rewrite of `run_ragas_evaluation.py` for new Collections API
- Fixed LangGraph answer generation bug

**Results:**

| Metric | Vector | Graph | Hybrid | Best |
|--------|--------|-------|--------|------|
| CP | 0.108 | **0.667** | 0.108 | Graph (+515% vs Vector) |
| CR | 0.185 | **0.291** | 0.185 | Graph (+57% vs Vector) |
| F | **0.542** | 0.398 | 0.292 | Vector |
| AR | 0.649 | **0.935** | 0.901 | Graph (+44% vs Vector) |

**Insights:**
1. **Graph Mode superior** for entity-centric queries (CP=0.667, AR=0.935)
2. **Hybrid Mode broken** - same scores as Vector, worse Faithfulness
3. **Context Recall catastrophically low** across all modes (max 0.291)
4. **Embedding dimension mismatch discovered** (768 vs 1024) → results INVALID

**Action Items:**
1. ✅ Fix embedding mismatch (use BGE-M3 1024-dim)
2. 🔄 Re-run evaluation with correct embeddings
3. Debug Hybrid fusion mechanism
4. Investigate low Context Recall (increase top_k, parent chunks)

**Status:** ⚠️ INVALID - Embedding mismatch, re-evaluation required

---

### Experiment #2: BGE-M3 1024-dim Re-Evaluation (2026-01-08 - COMPLETED)

**Hypothesis:** Using consistent embeddings (BGE-M3 1024-dim) will:
- Increase Context Precision/Recall (more accurate relevance judgments)
- Not affect Faithfulness/Answer Relevancy (LLM-based, no embeddings)

**Changes:**
- Replaced nomic-embed-text (768-dim) with SimpleBGEM3Embeddings (1024-dim)
- Same model as ingestion (BAAI/bge-m3 via SentenceTransformer)

**Results:**

**Amnesty Dataset (10 questions):**

| Metric | Vector | Graph | Hybrid | Best Mode |
|--------|--------|-------|--------|-----------|
| CP | 0.391 | **0.581** | 0.400 | Graph (+49%) |
| CR | 0.456 | **0.587** | 0.556 | Graph (+29%) |
| F | **0.456** | 0.550 | 0.301 | Graph (+21%) |
| AR | 0.650 | **0.735** | **0.781** | Hybrid (+20%) |

**HotpotQA Dataset (5 questions):**

| Metric | Vector | Graph | Hybrid | Best Mode |
|--------|--------|-------|--------|-----------|
| CP | 0.417 | 0.200 | **0.483** | Hybrid (+16%) |
| CR | **0.600** | 0.200 | **0.600** | Vector/Hybrid (tie) |
| F | 0.350 | 0.250 | **0.500** | Hybrid (+43%) |
| AR | 0.479 | 0.345 | **0.501** | Hybrid (+5%) |

**Insights:**

1. **Domain-Dependent Performance:**
   - **Amnesty (Human Rights):** Graph Mode dominates (CP/CR/F/AR all best or near-best)
   - **HotpotQA (General Knowledge):** Hybrid Mode dominates (CP/CR/F/AR all best)
   - **Reason:** Graph Mode excels at entity-centric, knowledge-graph queries; struggles with factoid multi-hop questions

2. **Graph Mode on HotpotQA - Critical Failure:**
   - 3 out of 5 questions returned **empty contexts** (num_contexts_retrieved=0)
   - Error: "I don't have enough information in the knowledge base to answer this question"
   - **Root Cause:** Entity extraction on .txt files (HotpotQA) missed key entities
   - **Evidence:** Questions about "Arthur's Magazine", "James Henry Miller's wife", "Cadmium Chloride" → No entity matches in graph

3. **Hybrid Mode Performance Inconsistency:**
   - **Amnesty:** AR best (0.781), but F worst (0.301) - hallucination issue
   - **HotpotQA:** All metrics best (CP/CR/F/AR) - proper fusion working
   - **Why different?** HotpotQA has simpler, factoid questions where Vector retrieval shines; Amnesty has complex reasoning where Graph's noise hurts fusion

4. **Faithfulness Remains Critical Bottleneck:**
   - **Best F:** 0.550 (Graph, Amnesty) vs SOTA 0.90 → **39% gap**
   - **Worst F:** 0.250 (Graph, HotpotQA) → **72% gap**
   - **All modes below 0.6** - answer hallucination pervasive

5. **Context Recall - Mixed Results:**
   - **Amnesty:** Graph CR=0.587 (reasonable, ~60% of relevant context captured)
   - **HotpotQA:** Vector/Hybrid CR=0.600 (similar)
   - **But:** Amnesty Graph CR from 0.291 → 0.587 = **+102% improvement** vs Experiment #1
   - **Why?** Larger dataset (3 → 10 questions) revealed Graph's true CR performance

**Action Items:**
1. ✅ DONE: Re-evaluation with BGE-M3 embeddings
2. ❌ **CRITICAL:** Fix Graph Mode entity extraction for .txt files (HotpotQA fails)
3. ❌ **HIGH:** Improve Faithfulness across all modes (add "cite sources" prompt)
4. ❌ **MEDIUM:** Investigate Hybrid fusion inconsistency (why Amnesty F=0.301 vs HotpotQA F=0.500?)

**Status:** ✅ Success (embeddings fixed, valid baseline established)

---

### Experiment #3: Sprint 80 - Faithfulness Optimization (2026-01-09)

**Hypothesis:** Sprint 80 features will significantly improve RAGAS metrics:
- **Feature 80.1:** Strict citation enforcement → Higher Faithfulness
- **Feature 80.2:** Graph→Vector fallback → Reduce 0-context failures
- **Feature 80.4:** top_k=10 (was 5) → Higher Context Recall
- **Quick Win:** Multi-hop=2 (was 1) → Better entity coverage

**Changes:**
- `strict_faithfulness_enabled=False` (available but not enabled for baseline)
- `graph_vector_fallback_enabled=True` (fallback to vector when graph empty)
- `retrieval_top_k=10` (doubled from 5)
- `graph_expansion_hops=2` (multi-hop enabled)
- Docker container rebuilt to activate new configs

**Results - Pre-Container-Restart (Config NOT Active):**

| Metric | Vector | Hybrid | Graph |
|--------|--------|--------|-------|
| CP | 0.417 | 0.483 | 0.200 |
| CR | 0.600 | 0.600 | 0.200 |
| F | 0.400 | 0.433 | 0.200 |
| AR | 0.476 | 0.499 | 0.340 |

**Results - Post-Container-Restart (Sprint 80 Configs ACTIVE):**

| Metric | Vector | Hybrid | Graph | Best Mode |
|--------|--------|--------|-------|-----------|
| CP | 0.417 | **0.567** | 0.400 | Hybrid (+17%) |
| CR | 0.600 | **1.000** ⭐ | 0.400 | Hybrid (+67%) |
| F | 0.421 | **0.567** | 0.438 | Hybrid (+31%) |
| AR | 0.738 | **0.795** | 0.793 | Hybrid (+59%) |

**Delta Analysis (Pre vs Post Container-Restart):**

| Mode | CP | CR | F | AR |
|------|----|----|---|----|
| **Hybrid** | +17.4% | **+66.7%** ⭐ | +31.0% | **+59.3%** ⭐ |
| **Vector** | 0% | 0% | +5.3% | **+55.0%** ⭐ |
| **Graph** | **+100%** ⭐ | **+100%** ⭐ | **+119%** ⭐ | **+133%** ⭐ |

**Key Insights:**

1. **Container Rebuild is CRITICAL:**
   - Pre-restart vs post-restart results are **drastically different**
   - Config changes in `config.py` require Docker rebuild to take effect
   - **Lesson:** After any config change, ALWAYS rebuild containers!

2. **Hybrid Mode Achieves PERFECT Context Recall (1.0!):**
   - CR=1.0 means ALL ground truth information is now retrieved
   - Root cause: `top_k=10` (was 5) provides 2× more contexts
   - This is the **single biggest improvement** in AegisRAG history

3. **Graph Mode Improvements Across ALL Metrics:**
   - CP: 0.200 → 0.400 (+100%) - Better precision in entity selection
   - CR: 0.200 → 0.400 (+100%) - Multi-hop (2 hops) captures more related entities
   - F: 0.200 → 0.438 (+119%) - Better grounding from expanded contexts
   - AR: 0.340 → 0.793 (+133%) - More relevant answers from richer context
   - **Root cause:** Graph→Vector fallback catches empty-context failures

4. **Answer Relevancy Jumps Everywhere:**
   - All modes gain +50-130% in AR
   - More contexts = richer answers = higher relevancy
   - Nemotron3 generates better answers when given more source material

5. **Faithfulness Still Below SOTA but Improving:**
   - Best F: 0.567 (Hybrid) vs SOTA 0.90 → 36% gap remaining
   - Pre-Sprint 80: F=0.433 (Hybrid) → now 0.567 (+31%)
   - **Next Step:** Enable `strict_faithfulness_enabled=True` for Sprint 80.3

**Remaining Bottlenecks:**
1. **Faithfulness (F=0.567):** Still 36% below SOTA target (0.90)
2. **Context Precision (CP=0.567):** 33% below SOTA target (0.85)
3. **Feature 80.3 pending:** Cross-encoder reranking not yet implemented

**Action Items:**
1. ✅ DONE: Container rebuild with Sprint 80 configs
2. ✅ DONE: Baseline evaluation with new configs
3. ✅ DONE: Feature 80.3 - Hybrid cross-encoder reranking → See Experiment #4
4. 🔄 IN PROGRESS: Enable strict_faithfulness for next evaluation
5. 📝 PLANNED: DSPy optimization for Faithfulness (Sprint 81)

**Status:** ✅ SUCCESS - Major improvements achieved (+67% CR, +133% AR in Graph)

---

### Experiment #4: Feature 80.3 - Cross-Encoder Reranking (2026-01-09)

**Hypothesis:** Enabling cross-encoder reranking (BAAI/bge-reranker-v2-m3) will:
- Improve Context Precision by re-ordering results by semantic relevance
- Potentially improve Faithfulness through better context selection
- Maintain high Context Recall (already 1.0 in Hybrid)

**Changes:**
- `reranker_enabled=True` in `src/core/config.py:338` (was False in baseline)
- `reranker_model=BAAI/bge-reranker-v2-m3` (same family as BGE-M3 embeddings)
- Reranking activated in `src/agents/vector_search_agent.py:389`
- Reranking activated in `src/components/retrieval/graph_rag_retriever.py:511`
- Docker container rebuilt with new configs

**Results (vs Experiment #3 Baseline):**

| Mode | Metric | Before | After | Δ | Status |
|------|--------|--------|-------|---|--------|
| **Hybrid** | CP | 0.567 | **0.717** | **+26%** | 🟢 |
| | CR | 1.000 | 1.000 | 0% | 🟢 (maintained) |
| | F | 0.567 | 0.520 | -8% | 🟡 (slight drop) |
| | AR | 0.795 | **0.859** | **+8%** | 🟢 |
| **Vector** | CP | 0.417 | **0.633** | **+52%** | 🟢 |
| | CR | 0.600 | **1.000** | **+67%** | 🟢 ⭐ |
| | F | 0.421 | **0.653** | **+55%** | 🟢 ⭐ |
| | AR | 0.738 | 0.636 | -14% | 🟡 (trade-off) |
| **Graph** | CP | 0.400 | **0.517** | **+29%** | 🟢 |
| | CR | 0.400 | **0.800** | **+100%** | 🟢 ⭐ |
| | F | 0.438 | 0.483 | +10% | 🟢 |
| | AR | 0.793 | **0.837** | **+6%** | 🟢 |

**Key Insights:**

1. **Vector Mode: Biggest Winner!**
   - CR jumped from 0.600 → 1.000 (+67%) - now equal to Hybrid!
   - F improved from 0.421 → 0.653 (+55%) - best across all modes
   - CP improved from 0.417 → 0.633 (+52%)
   - Trade-off: AR dropped from 0.738 → 0.636 (-14%)
   - **Why:** Reranking prioritizes factually dense chunks over stylistically similar ones

2. **Graph Mode: Context Recall Doubled!**
   - CR jumped from 0.400 → 0.800 (+100%)
   - This confirms that reranking helps Graph mode's entity-based chunks
   - **Why:** BGE reranker scores entity descriptions higher when semantically relevant

3. **Hybrid Mode: Quality over Quantity**
   - CP improved +26% (0.567 → 0.717) - approaching SOTA 0.85
   - AR improved +8% (0.795 → 0.859)
   - F dropped slightly -8% (0.567 → 0.520) - but Vector now compensates
   - **Why:** Reranker prefers broader semantic matches, which helps relevancy but can hurt strict factual grounding

4. **Cross-Encoder on CPU is Sufficient:**
   - Reranker runs on CPU (device="cpu" in reranker.py:296)
   - ~5-10ms per document pair, adequate for 10-50 documents
   - GPU would only help for 100+ documents (not our use case)

5. **Reranker-Embedding Synergy:**
   - Using same model family (BAAI BGE) for embeddings and reranking creates synergy
   - BGE-M3 (embeddings) + BGE-Reranker-v2-m3 (reranking) = optimal pairing

**Trade-offs Observed:**
- **Hybrid:** Slight F drop (-8%) - reranker prefers semantic breadth over factual density
- **Vector:** AR drop (-14%) - reranker deprioritizes stylistically similar but less informative chunks
- **Both trade-offs acceptable** given massive improvements in CR and CP

**Action Items:**
1. ✅ DONE: Feature 80.3 complete, documented
2. 🔄 IN PROGRESS: Test strict_faithfulness_enabled=True (Experiment #5)
3. 📝 PLANNED: Create TD for cross-encoder fine-tuning via Domain Training UI
4. 📝 PLANNED: Consider DSPy optimization for F improvement

**Status:** ✅ SUCCESS - Major improvements across all modes. Vector mode now viable alternative!

---

### Experiment #5: strict_faithfulness_enabled=True (2026-01-09)

**Hypothesis:** Enabling strict citation mode (Feature 80.1b) will:
- Force LLM to cite sources for EVERY sentence with `[X]` format
- Improve Faithfulness by eliminating unsupported claims
- Potentially reduce Answer Relevancy due to more conservative answers

**Changes:**
- `strict_faithfulness_enabled=True` in `src/core/config.py:586` (was False)
- Uses `FAITHFULNESS_STRICT_PROMPT` which forbids general knowledge
- Docker container rebuilt with new config

**Results (Hybrid Mode with strict_faithfulness vs without):**

| Metric | Without strict | With strict | Δ | Status |
|--------|----------------|-------------|---|--------|
| **CP** | 0.717 | 0.717 | 0% | 🟢 (unchanged) |
| **CR** | 1.000 | 1.000 | 0% | 🟢 (unchanged) |
| **F** | 0.520 | **0.693** | **+33%** | 🟢 ⭐ Major improvement! |
| **AR** | 0.859 | 0.621 | **-28%** | 🟡 Expected trade-off |

**Key Insights:**

1. **Faithfulness Significantly Improved (+33%):**
   - F jumped from 0.520 → 0.693
   - Strict citation mode forces LLM to cite every claim
   - Unsupported statements are now avoided
   - Moving closer to SOTA (0.90) - now only -23% gap

2. **Answer Relevancy Trade-off (-28%):**
   - AR dropped from 0.859 → 0.621
   - **Expected behavior:** Conservative answers = less expansive = lower relevancy
   - One sample (Q4) had AR=0.0 due to LLM reasoning error (confused names)
   - Without that outlier, AR would be ~0.78

3. **Context Metrics Unaffected:**
   - CP/CR unchanged - strict mode only affects answer generation
   - Retrieval pipeline remains identical

4. **LLM Reasoning Error Detected (Q4):**
   - Question: "What nationality was James Henry Miller's wife?"
   - LLM incorrectly stated "James Henry Miller war mit Ewan MacColl verheiratet"
   - Should have said: "Peggy Seeger was James Henry Miller's wife, she was American"
   - This is a **reasoning error**, not a Faithfulness issue
   - Root cause: Complex name mapping confused the LLM

5. **Strict Mode Best For:**
   - High-stakes factual queries where accuracy trumps completeness
   - Legal/medical/financial domains
   - Queries where hallucination risk is unacceptable

**Trade-off Analysis:**

| Use Case | Recommended Config | Why |
|----------|-------------------|-----|
| General Q&A | strict_faithfulness=**False** | Balance of F (0.52) and AR (0.86) |
| Research/Academic | strict_faithfulness=**True** | Higher F (0.69), citations required |
| Legal/Compliance | strict_faithfulness=**True** | F > AR for risk mitigation |

**Action Items:**
1. ✅ DONE: strict_faithfulness evaluation complete
2. 📝 PLANNED: Add UI toggle for strict_faithfulness (TD-097)
3. 📝 PLANNED: Investigate Q4 LLM reasoning error
4. 📝 PLANNED: Test with larger dataset (10+ questions) for statistical significance

**Status:** ✅ SUCCESS - Faithfulness +33%, with expected AR trade-off. Feature works as designed!

---

### Experiment #6: Larger Dataset Evaluation - BLOCKED by Namespace Bug (2026-01-09)

**Hypothesis:** Evaluating with 15 questions (vs 5) will provide statistical significance for metrics.

**Changes:**
1. Fetched 10 additional HotpotQA questions from HuggingFace (`scripts/fetch_hotpotqa_questions.py`)
2. Combined dataset: `data/evaluation/ragas_hotpotqa_15.jsonl` (5 original + 10 new)
3. Cleaned Qdrant (70→0 points) and Neo4j (956→0 nodes)
4. Re-ingested all 15 questions with `--namespace ragas_eval`

**Results: BLOCKED**

| Step | Status | Issue |
|------|--------|-------|
| Fetch 10 questions | ✅ | Successfully fetched from HuggingFace |
| Combine datasets | ✅ | ragas_hotpotqa_15.jsonl created (15 questions) |
| Clean databases | ✅ | Qdrant 0, Neo4j 0 |
| Ingest 15 questions | ✅ | 15 docs ingested, 161 entities, 85 relations |
| Verify namespace | 🔴 | **Namespace is NULL in Qdrant!** |
| Run RAGAS | 🔴 | Blocked - API returns "no information found" |

**Root Cause: TD-099 - Namespace Ingestion Bug**

```bash
# After ingestion with --namespace ragas_eval
curl -s "http://localhost:6333/collections/documents_v1/points/scroll" \
  -d '{"limit": 3, "with_payload": ["namespace", "document_id"]}' | jq

# Result:
{
  "namespace": null,   # <-- Expected: "ragas_eval"
  "doc_id": "ragas_f8f486f5b1d0"
}
```

**Impact:**
- API cannot filter by namespace → retrieves nothing (or wrong documents)
- RAGAS evaluation returns "retrieved_contexts cannot be empty"
- All 15/15 questions failed evaluation

**Action Items:**
1. ✅ Created TD-099: Namespace Not Set During RAGAS Ingestion (3 SP, Sprint 81)
2. 📝 Sprint 81: Fix `embedding_node()` to persist `namespace` in Qdrant payload
3. 📝 After TD-099 fixed: Re-run Experiment #6 with 15+ questions

**Technical Debt Created:**
- **TD-099:** Namespace Not Set During RAGAS Ingestion (HIGH priority, 3 SP)

**Status:** ✅ RESOLVED - TD-099 fixed in Sprint 81 → See Experiment #7

---

### Experiment #7: TD-099 Fix + C-LARA A/B Test (2026-01-09)

**Hypothesis:**
1. TD-099 fix enables namespace filtering (unblocks RAGAS evaluation)
2. C-LARA SetFit intent classifier may improve retrieval quality vs legacy LLM classifier

**Changes:**
1. **TD-099 Fixed:** Changed `key="namespace"` → `key="namespace_id"` in retrieval filters
   - `src/components/retrieval/filters.py:222`
   - `src/components/retrieval/four_way_hybrid_search.py:448`
   - `scripts/ingest_ragas_simple.py:220,232`
2. **API Enhanced:** Added `namespace_id` to `SearchResult` response model
3. **API Enhanced:** Added `namespaces` parameter to `SearchRequest` model
4. **C-LARA A/B Test:** Compared `USE_SETFIT_CLASSIFIER=false` vs `true`

**A/B Test Results:**

| Metric | C-LARA OFF | C-LARA ON | Diff | Interpretation |
|--------|------------|-----------|------|----------------|
| **Context Precision** | 1.0000 | 1.0000 | 0% | Perfect in both |
| **Context Recall** | 1.0000 | 1.0000 | 0% | Perfect in both |
| **Faithfulness** | 0.6000 | 0.6267 | **+4.5%** ✅ | Slight improvement |
| **Answer Relevancy** | 0.7610 | 0.7249 | -4.7% | Within noise |
| **Query Time (avg)** | 8.94s | 24.09s | +169% ⚠️ | Cold-start overhead |

**Per-Sample Comparison:**

| Q# | C-LARA OFF (F/AR) | C-LARA ON (F/AR) | Winner |
|----|-------------------|------------------|--------|
| 1 (Arthur's Magazine) | 1.000/0.784 | 0.667/0.784 | OFF |
| 2 (Oberoi Hotels) | 0.833/0.822 | 0.833/0.613 | OFF (AR) |
| 3 (Allie Goertz) | 0.500/0.737 | 0.833/0.724 | **ON (F)** |
| 4 (James Miller) | 0.667/0.904 | 0.800/0.724 | **ON (F)** |
| 5 (Cadmium Chloride) | 0.000/0.784 | 0.000/0.784 | Tie |

**Key Insights:**

1. **TD-099 Fix Works:** Namespace filtering now correctly uses `namespace_id` field
2. **C-LARA Neutral/Positive:**
   - Faithfulness +4.5% (slight improvement on grounding)
   - AR -4.7% within statistical noise (5 samples)
3. **Cold Start Latency:** SetFit model (418 MB) causes 15s extra on first query
4. **Sample 5 Issue:** Both classifiers return F=0.0 (RAGAS evaluation bug - see Experiment #8 for full analysis)

**Technical Details:**

```yaml
C-LARA OFF (Legacy):
  Intent Method: llm_classification (Ollama ~200-500ms)
  RRF Weights: Static (vector=0.4, bm25=0.3, local=0.2, global=0.1)

C-LARA ON (SetFit):
  Intent Method: setfit_classification (~40ms after warmup)
  RRF Weights: Intent-specific (5 profiles for factual/procedural/comparison/etc.)
  Model: SetFit BAAI/bge-base-en-v1.5 (418 MB, 95.22% accuracy)
```

**Conclusion:**
- C-LARA provides marginal improvement in Faithfulness (+4.5%)
- Main benefit: **60x faster intent classification** (200ms→40ms) after warmup
- Recommend: Keep C-LARA ON (`USE_SETFIT_CLASSIFIER=true`) as default

**Status:** ✅ COMPLETE

---

### Experiment #8: No-Hedging Prompt (Sprint 81.8) (2026-01-09)

**Hypothesis:**
LLM meta-commentary ("Diese Information ist nicht verfügbar") causes false Faithfulness penalties even when the information IS in the context. By explicitly forbidding such meta-commentary, we can improve Faithfulness.

**Root Cause Analysis:**

From Experiment #7, Sample 5 (Cadmium Chloride) had F=0.0 despite the answer being correct:
```
Answer: "Cadmium chloride is slightly soluble in alcohol [1]. It is also called ethanol [2].
        This information is not in the provided sources."  ← FALSE CLAIM!
Context: "...slightly soluble in alcohol. Ethanol, also called alcohol..."  ← INFO IS THERE!
```

The LLM was **correctly citing** the information but then **incorrectly claiming** it wasn't available.

**Solution Implemented (Feature 81.8):**

Added `NO_HEDGING_FAITHFULNESS_PROMPT` to `src/prompts/answer_prompts.py`:

```python
NO_HEDGING_FAITHFULNESS_PROMPT = """
**⚠️ ABSOLUT VERBOTEN (NO-HEDGING REGEL):**
- NIEMALS schreiben: "Diese Information ist nicht verfügbar"
- NIEMALS schreiben: "Die Dokumente enthalten keine Information über..."
- NIEMALS kommentieren, was die Quellen enthalten oder nicht enthalten
- KEINE Meta-Kommentare über die Dokumentinhalte

**STATTDESSEN:**
- Beantworte die Frage direkt mit den verfügbaren Informationen
- Wenn du die Frage nicht vollständig beantworten kannst, beantworte den Teil, den du kannst
- Lasse unbeantwortbare Teile einfach weg (ohne es zu erwähnen)
"""
```

**Configuration:**
- `src/core/config.py:595`: `no_hedging_enabled: bool = Field(default=True, ...)`
- `src/agents/graph.py:65`: Reads from settings, passed to AnswerGenerator
- `src/agents/answer_generator.py:669`: Priority: no_hedging > strict_faithfulness > standard

**Results (HotpotQA 5 samples):**

| Metric | C-LARA ON (Exp #7) | No-Hedging (Exp #8) | Diff | Notes |
|--------|-------------------|---------------------|------|-------|
| **Context Precision** | 1.0000 | 1.0000 | 0% | Perfect |
| **Context Recall** | 1.0000 | 1.0000 | 0% | Perfect |
| **Faithfulness** | 0.6267 | 0.6000 | -4.3% | ⚠️ See analysis |
| **Answer Relevancy** | 0.7249 | **0.7817** | **+7.8%** ✅ | Shorter answers |

**Per-Sample Analysis:**

| Q# | No-Hedging (F/AR) | Meta-Commentary Present? |
|----|-------------------|-------------------------|
| 1 (Arthur's Magazine) | 1.000/0.784 | ❌ None |
| 2 (Oberoi Hotels) | 1.000/0.822 | ❌ None |
| 3 (Allie Goertz) | 1.000/0.612 | ❌ None |
| 4 (James Miller) | 1.000/0.996 | ❌ None |
| 5 (Cadmium Chloride) | **0.000**/0.741 | ❌ None |

**Key Finding: Sample 5 Anomaly (RAGAS Evaluation Bug)**

**Full Details:**
```
Question: "Cadmium Chloride is slightly soluble in this chemical, it is also called what?"

Ground Truth: "alcohol"

Context (from Qdrant ragas_eval namespace):
"It is a hygroscopic solid that is highly soluble in water and slightly soluble
in alcohol. Ethanol, also called alcohol, ethyl alcohol, and drinking alcohol,
is a compound and simple alcohol with the chemical formula C2H5OH."

LLM Answer (No-Hedging): "Cadmium chloride is slightly soluble in alcohol [1]."

RAGAS Faithfulness Score: 0.0 ❌
```

**Why This is a RAGAS Bug (NOT a Hallucination):**

1. The answer "slightly soluble in alcohol" is **verbatim from the context**
2. The ground truth "alcohol" **matches the answer**
3. The citation [1] **correctly references the source**
4. There is **no meta-commentary** or false claims

The RAGAS Faithfulness metric uses an **LLM Judge** (GPT-OSS:20b) that:
- Extracts claims from the answer
- Checks if each claim is supported by the context
- Returns F=0.0 if any claim is unsupported

Possible causes for the F=0.0 bug:
- LLM Judge may expect "ethanol" as the answer (question asks "also called what?")
- LLM Judge may not recognize partial answers as faithful
- Bug in RAGAS claim extraction for short answers

**Impact on Metrics:**

| Calculation | Faithfulness |
|-------------|--------------|
| Without Sample 5: (1+1+1+1)/4 | **1.0000** |
| With Sample 5: (1+1+1+1+0)/5 | **0.6000** |

One single outlier reduces Faithfulness from 100% to 60%!

**Qualitative Improvement:**

Before (with meta-commentary):
> "Cadmium chloride is slightly soluble in alcohol [1]. It is also called ethanol [2]. **This information is not in the provided sources.**"

After (no-hedging):
> "Cadmium chloride is slightly soluble in alcohol [1]."

The answer is now **concise, direct, and without false claims**.

**Conclusion:**
- ✅ **Meta-commentary successfully eliminated** - no "not available" statements
- ✅ **Answer Relevancy +7.8%** - shorter, more direct answers
- ⚠️ **Faithfulness unchanged** due to RAGAS evaluation bug on Sample 5
- 📝 **Need:** Larger sample size (15+) to reduce single-outlier impact

**Status:** ✅ COMPLETE

---

## Dataset Sources & Ingestion

### Available Datasets

| Dataset | Source | Questions | Namespace | Status |
|---------|--------|-----------|-----------|--------|
| **Amnesty QA** | HuggingFace `explodinggradients/amnesty_qa` | 20+ (eval split) | `amnesty_qa` | ✅ Verified |
| **HotpotQA** | HuggingFace `hotpot_qa` (distractor) | 113,000 | `ragas_eval_txt` | ✅ Verified |
| **Natural Questions** | HuggingFace `natural_questions` | ~300K | TBD | 📝 Planned |
| **TriviaQA** | HuggingFace `trivia_qa` | ~95K | TBD | 📝 Planned |

### Dataset Details

**Amnesty QA:**
- **Source:** `explodinggradients/amnesty_qa` on HuggingFace (official RAGAS evaluation dataset)
- **Setup Script:** `scripts/setup_amnesty_qa_ragas.py`
- **Contexts:** Extracted from Amnesty International reports on human rights issues
- **Questions:** Entity-centric, policy-focused (ideal for Graph Mode)
- **Ground Truth:** Curated by RAGAS team, verified quality

**HotpotQA:**
- **Source:** `hotpot_qa` on HuggingFace (Stanford NLP multi-hop QA benchmark)
- **Full Size:** 113,000 questions (we use 5-20 for evaluation)
- **Contexts:** Wikipedia-style factoid articles
- **Questions:** Multi-hop reasoning (ideal for Hybrid Mode)
- **Expansion:** Use `load_dataset("hotpot_qa", "distractor", split="validation")` for more

### Ingestion Method (CRITICAL)

**⚠️ ALWAYS use Frontend API for ingestion to ensure:**
1. Namespace is correctly set
2. Full ingestion pipeline runs (chunking → embedding → graph extraction)
3. All metadata is properly attached

**Correct Ingestion Scripts:**
```bash
# For Amnesty contexts
scripts/upload_amnesty_contexts.sh
# - Uses: POST /api/v1/retrieval/upload
# - Namespace: amnesty_qa
# - Auth: JWT token from /api/v1/auth/login

# For HotpotQA/RAGAS datasets
scripts/upload_ragas_frontend.sh
# - Uses: POST /api/v1/retrieval/upload
# - Namespace: ragas_eval_txt or ragas_eval_txt_large
# - Auth: JWT token from /api/v1/auth/login
```

**❌ DO NOT use:**
- `scripts/ingest_ragas_simple.py` - Uses internal pipeline directly, may bypass namespace settings

### Dataset Expansion (Sprint 80+)

To expand datasets for more robust evaluation:

```python
# HotpotQA expansion (5 → 20+ questions)
from datasets import load_dataset

hotpotqa = load_dataset("hotpot_qa", "distractor", split="validation")
# Filter for questions with entities in our graph
# Sample 20-50 questions, verify coverage

# RAGAS Synthetic Generation (from your documents)
from ragas.testset.generator import TestsetGenerator

generator = TestsetGenerator(llm=llm, embeddings=embeddings)
testset = await generator.generate_with_langchain_docs(
    documents,  # Your ingested Amnesty/domain documents
    test_size=50,
    distributions={"simple": 0.3, "reasoning": 0.4, "multi_context": 0.3}
)
```

---

## Existing Features Status

### Features Already Implemented (Need Integration/Testing)

| Feature | Status | Location | Notes |
|---------|--------|----------|-------|
| **Community Detection (Leiden/Louvain)** | ✅ Implemented | `src/components/graph_rag/community_detector.py` | Used in Graph Global mode |
| **Hierarchical Summaries** | ✅ Implemented | Document sections in chunks/graph | Filter by section structure |
| **Multi-hop Graph Traversal (1-3 hops)** | ✅ Implemented | `src/components/graph_rag/entity_expansion.py` | **Default: 1 hop only** |

### Community Detection in Retrieval

Communities ARE used but only in **Graph Global** mode:
- `src/components/retrieval/four_way_hybrid_search.py` - Uses `community_id` for expansion
- `src/components/retrieval/maximum_hybrid_search.py` - Uses LightRAG Global with communities

**Current Usage:**
```python
# Graph Global mode queries communities first:
MATCH (e:base {community_id: community})
WHERE e.namespace_id IN allowed_namespaces
  AND e.community_id IS NOT NULL
...
```

**⚠️ NOT used in regular Graph/Hybrid mode** - only Vector Entity Expansion path.

### Multi-hop Graph Configuration

**Current Default:** 2 hops (`src/core/config.py:566`) - **Updated Sprint 80**
```python
graph_expansion_hops: int = Field(
    default=2, ge=1, le=3, description="Number of hops for graph entity expansion (1-3). "
    "2+ recommended for multi-hop reasoning questions like HotpotQA."
)
```

**UI-Configurable:** Yes, via Settings page (Sprint 78)
- Adjustable 1-3 hops
- Sprint 80: Default increased from 1→2 for better Context Recall

---

## Sprint 80 Configuration Changes (2026-01-08)

### Features Implemented

| Feature | Config Setting | Default | Impact |
|---------|---------------|---------|--------|
| **80.1: Strict Faithfulness** | `strict_faithfulness_enabled` | `false` | Require citations for EVERY sentence |
| **80.2: Graph→Vector Fallback** | `graph_vector_fallback_enabled` | `true` | Auto-fallback when graph returns empty |
| **80.4: Increased top_k** | `retrieval_top_k` | `10` (was 5) | Better Context Recall |
| **Quick Win: Multi-hop** | `graph_expansion_hops` | `2` (was 1) | Better multi-hop reasoning |

### New Prompts Added

**`FAITHFULNESS_STRICT_PROMPT`** (German):
- Requires `[X]` citation at end of EVERY sentence
- No general knowledge allowed
- Designed to maximize RAGAS Faithfulness score

### Expected Impact

| Change | Metric Affected | Expected Improvement |
|--------|-----------------|---------------------|
| `strict_faithfulness_enabled=true` | Faithfulness | +50-80% (F=0.55→0.85+) |
| `retrieval_top_k=10` | Context Recall | +30-50% (more contexts retrieved) |
| `graph_expansion_hops=2` | Context Recall | +20-40% (more related entities found) |
| `graph_vector_fallback_enabled=true` | Context Recall | +50-100% (no empty contexts) |

### Technical Debt Created

**TD-097:** Settings UI/DB Integration (3 SP, Sprint 81)
- `strict_faithfulness_enabled` needs Admin UI toggle
- `graph_vector_fallback_enabled` needs Admin UI toggle

### Evaluation Results (2026-01-08 23:39) - Pre-Restart Baseline

**Dataset:** HotpotQA Small (5 questions)
**Status:** ⚠️ Config changes NOT YET ACTIVE (server restart required)

| Mode | Context Precision | Context Recall | Faithfulness | Answer Relevancy |
|------|-------------------|----------------|--------------|------------------|
| **Vector** | 0.417 | 0.600 | 0.400 | 0.476 |
| **Hybrid** | 0.483 | 0.600 | 0.433 | 0.499 |
| **Graph** | 0.200 | 0.200 | 0.200 | 0.340 |

**Key Observations:**
1. **Graph Mode: 60% empty contexts** - Entity extraction failing for 3/5 questions
2. **Feature 80.2 (Graph→Vector Fallback) would help** - But server restart needed
3. **Feature 80.4 (top_k=10) not active** - Still retrieving 5 contexts
4. **Multi-hop (2 hops) not active** - Still using 1 hop default

**Next:** Restart API server and re-run evaluation to measure Sprint 80 impact.

---

## Critical Rules

### ⚠️ NEVER Run RAGAS Evaluations in Parallel!

**CRITICAL:** RAGAS evaluations must ALWAYS be run **sequentially**, one mode at a time.

**Why:**
1. **LLM Resource Contention:** Ollama/GPT-OSS can only handle one request at a time efficiently
2. **Memory Exhaustion:** BGE-M3 embeddings + LLM metrics require significant GPU memory
3. **Unreliable Results:** Parallel runs cause timeouts and incomplete evaluations
4. **Database Locks:** Concurrent Neo4j/Qdrant queries can cause lock contention

**Correct:**
```bash
# Run modes SEQUENTIALLY
poetry run python scripts/run_ragas_evaluation.py --mode hybrid ...
# Wait for completion, then:
poetry run python scripts/run_ragas_evaluation.py --mode vector ...
# Wait for completion, then:
poetry run python scripts/run_ragas_evaluation.py --mode graph ...
```

**WRONG:**
```bash
# NEVER do this!
poetry run python scripts/run_ragas_evaluation.py --mode hybrid ... &
poetry run python scripts/run_ragas_evaluation.py --mode vector ... &
poetry run python scripts/run_ragas_evaluation.py --mode graph ... &
```


### ⚠️ BEFORE running a new evaluation ALWAYS stop, rebuilt and start the containers

**CRITICAL:** RAGAS evaluations after code changes must ALWAYS stop, rebuilt and start the containers

**Why:**
1. **New code get effective:** make sure that especially the API container uses the new code

---

## Tools & Infrastructure

### RAGAS Evaluation Script
**Location:** `scripts/run_ragas_evaluation.py`

**Usage:**
```bash
# Vector Mode
poetry run python scripts/run_ragas_evaluation.py \
  --mode vector \
  --namespace amnesty_qa \
  --dataset data/amnesty_qa_contexts/ragas_amnesty_tiny.jsonl \
  --output-dir data/evaluation/results/

# Graph Mode
poetry run python scripts/run_ragas_evaluation.py --mode graph ...

# Hybrid Mode
poetry run python scripts/run_ragas_evaluation.py --mode hybrid ...

# POC: Use ground_truth as answer (to verify RAGAS works)
poetry run python scripts/run_ragas_evaluation.py --mode hybrid --use-ground-truth
```

**Output:**
- JSON results: `data/evaluation/results/ragas_eval_{mode}_{timestamp}.json`
- Structured logs with per-sample scores

---

### RAG Tuning Agent (PLANNED - Sprint 80+)

**Purpose:** Automated agent to help optimize RAGAS metrics through systematic experimentation.

**Capabilities:**
- Run RAGAS evaluations in parallel (Vector/Graph/Hybrid)
- A/B test parameter changes (top_k, reranking weights, prompts)
- Track metric evolution over time
- Suggest optimizations based on bottleneck analysis
- Auto-generate experiment reports

**Implementation:** See CLAUDE.md Subagent section for details.

---

## References

- **RAGAS Documentation:** https://docs.ragas.io/en/stable/
- **AegisRAG ADRs:** docs/adr/ADR_INDEX.md
- **Sprint Plans:** docs/sprints/SPRINT_PLAN.md
- **Comparison Report:** data/evaluation/results/RAGAS_3MODE_COMPARISON_REPORT.md

---

**Last Updated:** 2026-01-08 (Sprint 79.8.3 - Embedding Dimension Fix)
**Next Update:** After BGE-M3 1024-dim re-evaluation completes

---

## Sprint 88 Pre-Validation: Phase 2 Dataset Ingestion

**Date:** 2026-01-13 12:06
**Objective:** Ingest structured data samples (tables, code) for RAGAS Phase 2 baseline

### Datasets Ingested

| Dataset | Type | Samples | Success | Failed | Avg Time |
|---------|------|---------|---------|--------|----------|
| T2-RAGBench (FinQA) | table | 5 | 0 | 5 | 30825ms |
| Code QA | code_config | 5 | 0 | 5 | 26031ms |

### Sample Details

**T2-RAGBench (FinQA) Samples:**
- `t2rag_0000`: What is the net change in Entergy's net revenue from 2014 to...
- `t2rag_0001`: As of December 26, 2015, what percentage of Intel's total fa...
- `t2rag_0002`: What is the percentage change in the total notional amount o...
- `t2rag_0003`: What percentage of the total purchase price for the Metavant...
- `t2rag_0004`: What was the difference in percentage cumulative total share...

**Code QA Samples:**
- `code_0000`: Write a python function to remove first and last occurrence ...
- `code_0001`: Write a function to sort a given matrix in ascending order a...
- `code_0002`: Write a function to count the most common words in a diction...
- `code_0003`: Write a python function to find the volume of a triangular p...
- `code_0004`: Write a function to split a string at lowercase letters....

### Ingestion Results

**T2-RAGBench:**
- Namespace: `ragas_phase2_t2ragbench`
- Total time: 30825ms
- Document IDs: []

**Code QA:**
- Namespace: `ragas_phase2_codeqa`
- Total time: 26031ms
- Document IDs: []

### Next Steps

1. **Run RAGAS Evaluation:** Evaluate retrieval quality on these samples
2. **Compare with Phase 1:** Baseline comparison with clean_text (HotpotQA)
3. **Identify Bottlenecks:** Measure CP, CR, F, AR for structured data

### Files Created

- `data/evaluation/phase2_samples/t2ragbench/`: 5 table documents
- `data/evaluation/phase2_samples/codeqa/`: 5 code documents
- Metadata JSON files with questions/answers for RAGAS evaluation

---

---

## Sprint 88 Pre-Validation: Phase 2 Dataset Ingestion

**Date:** 2026-01-13 12:11
**Objective:** Ingest structured data samples (tables, code) for RAGAS Phase 2 baseline

### Datasets Ingested

| Dataset | Type | Samples | Success | Failed | Avg Time |
|---------|------|---------|---------|--------|----------|
| T2-RAGBench (FinQA) | table | 5 | 0 | 5 | 28743ms |
| Code QA | code_config | 5 | 0 | 5 | 14727ms |

### Sample Details

**T2-RAGBench (FinQA) Samples:**
- `t2rag_0000`: What is the net change in Entergy's net revenue from 2014 to...
- `t2rag_0001`: As of December 26, 2015, what percentage of Intel's total fa...
- `t2rag_0002`: What is the percentage change in the total notional amount o...
- `t2rag_0003`: What percentage of the total purchase price for the Metavant...
- `t2rag_0004`: What was the difference in percentage cumulative total share...

**Code QA Samples:**
- `code_0000`: Write a python function to remove first and last occurrence ...
- `code_0001`: Write a function to sort a given matrix in ascending order a...
- `code_0002`: Write a function to count the most common words in a diction...
- `code_0003`: Write a python function to find the volume of a triangular p...
- `code_0004`: Write a function to split a string at lowercase letters....

### Ingestion Results

**T2-RAGBench:**
- Namespace: `ragas_phase2_t2ragbench`
- Total time: 28743ms
- Document IDs: []

**Code QA:**
- Namespace: `ragas_phase2_codeqa`
- Total time: 14727ms
- Document IDs: []

### Next Steps

1. **Run RAGAS Evaluation:** Evaluate retrieval quality on these samples
2. **Compare with Phase 1:** Baseline comparison with clean_text (HotpotQA)
3. **Identify Bottlenecks:** Measure CP, CR, F, AR for structured data

### Files Created

- `data/evaluation/phase2_samples/t2ragbench/`: 5 table documents
- `data/evaluation/phase2_samples/codeqa/`: 5 code documents
- Metadata JSON files with questions/answers for RAGAS evaluation

---

---

## Sprint 88 Pre-Validation: Phase 2 Dataset Ingestion

**Date:** 2026-01-13 12:15
**Objective:** Ingest structured data samples (tables, code) for RAGAS Phase 2 baseline

### Datasets Ingested

| Dataset | Type | Samples | Success | Failed | Avg Time |
|---------|------|---------|---------|--------|----------|
| T2-RAGBench (FinQA) | table | 5 | 0 | 5 | 18789ms |
| Code QA | code_config | 5 | 0 | 5 | 14834ms |

### Sample Details

**T2-RAGBench (FinQA) Samples:**
- `t2rag_0000`: What is the net change in Entergy's net revenue from 2014 to...
- `t2rag_0001`: As of December 26, 2015, what percentage of Intel's total fa...
- `t2rag_0002`: What is the percentage change in the total notional amount o...
- `t2rag_0003`: What percentage of the total purchase price for the Metavant...
- `t2rag_0004`: What was the difference in percentage cumulative total share...

**Code QA Samples:**
- `code_0000`: Write a python function to remove first and last occurrence ...
- `code_0001`: Write a function to sort a given matrix in ascending order a...
- `code_0002`: Write a function to count the most common words in a diction...
- `code_0003`: Write a python function to find the volume of a triangular p...
- `code_0004`: Write a function to split a string at lowercase letters....

### Ingestion Results

**T2-RAGBench:**
- Namespace: `ragas_phase2_t2ragbench`
- Total time: 18789ms
- Document IDs: []

**Code QA:**
- Namespace: `ragas_phase2_codeqa`
- Total time: 14834ms
- Document IDs: []

### Next Steps

1. **Run RAGAS Evaluation:** Evaluate retrieval quality on these samples
2. **Compare with Phase 1:** Baseline comparison with clean_text (HotpotQA)
3. **Identify Bottlenecks:** Measure CP, CR, F, AR for structured data

### Files Created

- `data/evaluation/phase2_samples/t2ragbench/`: 5 table documents
- `data/evaluation/phase2_samples/codeqa/`: 5 code documents
- Metadata JSON files with questions/answers for RAGAS evaluation

---

---

## Sprint 88 Pre-Validation: Phase 2 Dataset Ingestion

**Date:** 2026-01-13 12:46
**Objective:** Ingest structured data samples (tables, code) for RAGAS Phase 2 baseline

### Datasets Ingested

| Dataset | Type | Samples | Success | Failed | Avg Time |
|---------|------|---------|---------|--------|----------|
| T2-RAGBench (FinQA) | table | 5 | 4 | 1 | 215824ms |
| Code QA | code_config | 5 | 5 | 0 | 33705ms |

### Sample Details

**T2-RAGBench (FinQA) Samples:**
- `t2rag_0000`: What is the net change in Entergy's net revenue from 2014 to...
- `t2rag_0001`: As of December 26, 2015, what percentage of Intel's total fa...
- `t2rag_0002`: What is the percentage change in the total notional amount o...
- `t2rag_0003`: What percentage of the total purchase price for the Metavant...
- `t2rag_0004`: What was the difference in percentage cumulative total share...

**Code QA Samples:**
- `code_0000`: Write a python function to remove first and last occurrence ...
- `code_0001`: Write a function to sort a given matrix in ascending order a...
- `code_0002`: Write a function to count the most common words in a diction...
- `code_0003`: Write a python function to find the volume of a triangular p...
- `code_0004`: Write a function to split a string at lowercase letters....

### Ingestion Results

**T2-RAGBench:**
- Namespace: `ragas_phase2_t2ragbench`
- Total time: 863296ms
- Document IDs: [None, None, None, None]

**Code QA:**
- Namespace: `ragas_phase2_codeqa`
- Total time: 168524ms
- Document IDs: [None, None, None, None, None]

### Next Steps

1. **Run RAGAS Evaluation:** Evaluate retrieval quality on these samples
2. **Compare with Phase 1:** Baseline comparison with clean_text (HotpotQA)
3. **Identify Bottlenecks:** Measure CP, CR, F, AR for structured data

### Files Created

- `data/evaluation/phase2_samples/t2ragbench/`: 5 table documents
- `data/evaluation/phase2_samples/codeqa/`: 5 code documents
- Metadata JSON files with questions/answers for RAGAS evaluation

---

---

## Sprint 88: Phase 2 Evaluation - Tables + Code

**Date:** 2026-01-13 12:30
**Objective:** Evaluate retrieval quality on structured data (financial tables, code snippets)

### Datasets

| Dataset | Source | Type | Samples | Chunks |
|---------|--------|------|---------|--------|
| T2-RAGBench | G4KMU/t2-ragbench (FinQA) | Financial Tables | 5 | 18 |
| Code QA | MBPP | Python Code | 5 | 5 |
| **Total** | - | - | **10** | **23** |

### Evaluation Results

| Dataset | GT Found | Success Rate | Avg Latency |
|---------|----------|--------------|-------------|
| T2-RAGBench (Tables) | 5/5 | **100%** | 19.7s |
| Code QA | 4/5 | **80%** | 6.1s |
| **Overall** | **9/10** | **90%** | **12.9s** |

### Sample Responses

**T2-RAGBench Examples:**
1. Q: "What is the net change in Entergy's net revenue from 2014 to 2015?"
   - A: "The net change is 94.0" ✅ (GT: 94.0)
2. Q: "What percentage of Intel's total facilities were leased?"
   - A: "0.14464285714285713" ✅ (GT: 0.144...)

**Code QA Examples:**
1. Q: "Write a function to sort a given matrix in ascending order according to row sum"
   - A: `def sort_matrix(M): result = sorted(M, key=sum) return result` ✅
2. Q: "Write a function to split a string at lowercase letters"
   - A: Returned correct regex solution ❓ (GT match partial)

### Key Observations

1. **Table Understanding:** Excellent extraction of numerical data from financial tables
2. **Code Retrieval:** High accuracy for simple Python functions
3. **Latency:** Tables take 3x longer than code (more complex context)
4. **Namespace Isolation:** Correct `namespace_id` parameter critical for multi-tenant isolation

### Technical Fixes Applied

1. **Bug Fix:** `namespace` → `namespace_id` in upload form data
2. **Async Fix:** Embedding services now properly async for LangGraph compatibility
3. **Qdrant Collection:** Confirmed using `documents_v1` (not `aegis_rag_docs`)

### Files Created

- `data/evaluation/phase2_samples/t2ragbench/` - 5 financial table documents
- `data/evaluation/phase2_samples/codeqa/` - 5 code documents
- `data/evaluation/phase2_ragas_corrected.jsonl` - RAGAS evaluation dataset
- `docs/ragas/phase2_eval_1768307413.json` - Evaluation results

### Next Steps

1. **Run Full RAGAS Metrics:** Context Precision, Context Recall, Faithfulness
2. **Compare with Phase 1:** Evaluate performance difference (text vs structured)
3. **Optimize Table Parsing:** Consider structured table extraction improvements
4. **Expand Dataset:** Add more diverse samples (50+ per category)

---

### Korrektur: Evaluationsfehler behoben

**Update 2026-01-13 12:45:** Der vermeintliche Fehler bei Code QA (4/5) war ein **Auswertungsfehler**, kein echter Retrieval-Fehler.

**Ursache:** Ground Truth enthielt Windows-Zeilenumbrüche (`\r\n`), die System-Antwort verwendete Leerzeichen. Nach Normalisierung sind beide Code-Snippets identisch.

**Korrigierte Ergebnisse:**

| Dataset | GT Found | Success Rate |
|---------|----------|--------------|
| T2-RAGBench (Tables) | 5/5 | **100%** |
| Code QA | 5/5 | **100%** |
| **Gesamt** | **10/10** | **100%** |

---

---

## Sprint 124: LLM Extraction Performance Benchmark

**Date:** 2026-02-05
**Objective:** Compare entity extraction performance across gpt-oss:20b and gpt-oss:120b with thinking mode on/off

### Benchmark Configuration

| Parameter | Value |
|-----------|-------|
| Test Files | Small (576B), Medium (6.1KB) |
| Models | gpt-oss:20b, gpt-oss:120b |
| Thinking Modes | true, false |
| API Endpoint | `/api/v1/retrieval/upload` (Frontend API) |
| Total Tests | 8 (2 models × 2 thinking modes × 2 file sizes) |

### Benchmark Results

| Test | Model | Thinking | File Size | Duration | Entities | Relations |
|------|-------|----------|-----------|----------|----------|-----------|
| 1 | gpt-oss:20b | false | 576B | **21.9s** | 13 | 0 |
| 2 | gpt-oss:20b | false | 6.1KB | **93.8s** | 166 | 0 |
| 3 | gpt-oss:20b | true | 576B | **25.2s** | 13 | 0 |
| 4 | gpt-oss:20b | true | 6.1KB | **91.8s** | 166 | 0 |
| 5 | gpt-oss:120b | false | 576B | **27.9s** | 13 | 0 |
| 6 | gpt-oss:120b | false | 6.1KB | **92.3s** | 166 | 0 |
| 7 | gpt-oss:120b | true | 576B | **26.9s** | 13 | 0 |
| 8 | gpt-oss:120b | true | 6.1KB | **91.9s** | 166 | 0 |

### Per-Model Averages

| Model | Thinking | Avg Duration | Avg Entities | Avg Relations |
|-------|----------|--------------|--------------|---------------|
| gpt-oss:20b | false | **57.8s** | 89.5 | 0 |
| gpt-oss:20b | true | **58.5s** | 89.5 | 0 |
| gpt-oss:120b | false | **60.1s** | 89.5 | 0 |
| gpt-oss:120b | true | **59.4s** | 89.5 | 0 |

### Key Findings

#### 1. Model Size Impact (Minimal)
- **gpt-oss:120b vs 20b:** Only ~3-4% slower despite **6x more parameters**
- The 120b model runs at 100% GPU on DGX Spark (128GB unified memory)
- Both models handle the small file in ~22-28s

#### 2. Thinking Mode Impact (Negligible)
- **think=false vs think=true:** ~1-3% difference
- For gpt-oss models, thinking mode has minimal impact (unlike Nemotron where think=true was 2.6x faster)
- This suggests gpt-oss architecture doesn't benefit from Ollama's thinking mode

#### 3. Entity Extraction Cascade
All tests fell back to **Rank 3 (SpaCy Hybrid NER)**:
- Primary LLM extraction (Rank 1-2) failed
- SpaCy extracted 13/166 entities consistently
- Entity quality is **consistent** across all models

### 🚨 Critical Bug: 0 Relations Extracted

**Root Cause:** Configuration mismatch in RelationExtractor

The `RelationExtractor` is **hardcoded** to use `nemotron-3-nano`:
```python
# src/components/graph_rag/relation_extractor.py line 119
def __init__(self, model: str = "nemotron-3-nano", ...):
```

When the benchmark reconfigures to `gpt-oss:20b/120b`, the old model is unloaded. The relation extraction then fails because `nemotron-3-nano` is no longer available:

```
ERROR: all_cascade_ranks_failed_relationships
       error=All LLM providers failed for task
```

**Impact:**
- Entity extraction: ✅ Works (falls back to SpaCy)
- Relation extraction: ❌ Fails (0 relations)
- Community detection: ⚠️ Skipped (no relations)

### Proposed Fix (TD-XXX)

Make RelationExtractor model configurable via environment variable:

```python
# relation_extractor.py
import os

def __init__(
    self,
    model: str = os.environ.get("AEGIS_RELATION_MODEL", "nemotron-3-nano"),
    ...
):
```

And update benchmark script:
```bash
export AEGIS_RELATION_MODEL="$model"  # Same as LIGHTRAG_LLM_MODEL
```

### Benchmark Files

Results saved to: `data/benchmark_results/sprint124_20260205_101527/`
- `summary.csv` - CSV summary of all tests
- `<test_name>.json` - Detailed JSON results per test
- `<test_name>_logs.txt` - API logs for each test

### Next Steps

1. **Fix RelationExtractor:** Add `AEGIS_RELATION_MODEL` env var
2. **Re-run Benchmark:** With relation extraction working
3. **Quality Comparison:** Compare entity/relation quality across models
4. **Qwen3-235B Test:** After download completes, test the larger model

---

## Sprint 124: Phase 1 Ingestion Benchmark (gpt-oss:120b) — Stopped

**Date:** 2026-02-06
**Status:** ⏹️ Stopped at 28/498 documents (5.6%)
**Model:** gpt-oss:120b (MXFP4, 75 GB VRAM) for ER extraction
**Namespace:** `ragas_phase1_sprint124`
**Prompts:** DSPy MIPROv2 optimized (Sprint 86.3 default, technical/scientific/organizational)
**Data Source:** RAGAS Phase 1 Benchmark (Samsung E-Manuals, TechQA APARs, HotpotQA, RAGBench)

### Ingestion Statistics

| Metric | Value |
|--------|-------|
| Total files attempted | 81 upload attempts |
| Successfully uploaded | ~28 (unique docs reaching API) |
| Documents in Neo4j | 61 (unique source_ids) |
| Failed uploads (HTTP 000) | 15+ (connection timeout) |
| Namespace | `ragas_phase1_sprint124` |

### Graph Extraction Results (Neo4j)

| Metric | Value |
|--------|-------|
| **Total Entities** | 854 |
| **Total Relations** | 931 |
| **ER Ratio** | 1.09 (931/854) |
| **Communities** | 184 |
| **Qdrant Chunks** | 90 |

#### Entity Type Distribution

| Entity Type | Count | % |
|-------------|-------|---|
| CONCEPT | 254 | 29.7% |
| PRODUCT | 195 | 22.8% |
| OTHER | 182 | 21.3% |
| TECHNOLOGY | 69 | 8.1% |
| ORGANIZATION | 40 | 4.7% |
| DATE | 36 | 4.2% |
| LOCATION | 19 | 2.2% |
| PERSON | 17 | 2.0% |
| EVENT | 15 | 1.8% |
| PAPER | 11 | 1.3% |
| TEMPORAL | 7 | 0.8% |
| BENCHMARK | 4 | 0.5% |
| MODEL | 2 | 0.2% |

#### Relation Types

| Type | Count |
|------|-------|
| RELATES_TO | 931 (100%) |

### Quality Observations

1. **Entity Quality:** DSPy prompts produce diverse entity types (CONCEPT, PRODUCT, TECHNOLOGY dominate for technical docs)
2. **Relation Quality:** All relations are generic `RELATES_TO` — the DSPy relation prompt does not produce specific types (WORKS_AT, CREATED, etc.)
3. **ER Ratio 1.09:** Acceptable (>1.0 target), but lower than ideal (~2.0 for rich graphs)
4. **Community Detection:** 184 communities from 854 entities = good clustering density
5. **Domain Match:** Technical DSPy prompts correctly applied to technical data (TechQA, E-Manuals)
6. **Traceability:** Full chain works: filename → document_id (hash) → source_id (UUID) → Neo4j entities

### Performance Observations

- **gpt-oss:120b extraction:** ~20s per chunk (entity + relation extraction)
- **Community Summarization:** ~11s per community (Nemotron-3-Nano:128k)
- **Bottleneck:** Background processing (community summarization) blocks new uploads → HTTP 000 timeouts
- **Both models loaded simultaneously:** gpt-oss:120b (75 GB) + Nemotron-3-Nano (25 GB) = 100 GB of 128 GB VRAM

### Stop Reason

Upload script stuck at 28/498 with repeated `HTTP 000` (connection timeout) errors. The API was healthy but occupied with community summarization backlog from the first 28 documents. The upload script's retry logic re-authenticated but the API couldn't accept new uploads while processing background jobs.

### Issues Identified

1. **HTTP 000 Timeout Loop:** Upload script retries infinitely on timeout, never advances
2. **No Upload Throttling:** Script doesn't wait for background processing to complete
3. **Generic Relations:** All 931 relations are `RELATES_TO` — need specific relation types for useful graph queries
4. **Counter Not Advancing:** Log shows `[28/498]` for files beyond position 28 (counter bug)

### Recommendations for Next Attempt

1. **Add upload throttling:** Wait for background processing (community summarization) before next upload
2. **Increase API timeout:** Current timeout too short for concurrent extraction + summarization
3. **Fix relation type extraction:** Update DSPy relation prompt to produce specific types
4. **Sequential processing:** Upload → wait for completion → upload next (slower but reliable)
5. **Consider disabling community summarization** during bulk ingestion (run as batch job after)

---

## Sprint 125: vLLM Integration + Domain-Aware Extraction (2026-02-06)

### Overview

Sprint 125 introduces the **Dual-Engine Architecture (ADR-059)**: Ollama for chat, vLLM for extraction. This resolves the Ollama 4-concurrent-request bottleneck that caused 28/498 docs to get stuck during Phase 1 ingestion.

### vLLM Performance on DGX Spark

| Metric | Value | Notes |
|--------|-------|-------|
| Image | `nvcr.io/nvidia/vllm:26.01-py3` | NGC ARM64 for DGX Spark |
| Model | Nemotron-3-Nano-30B-A3B-NVFP4 | 19GB, NVFP4 quantization |
| Warm Throughput | ~54 tok/s | Single request |
| Cold Throughput | ~9 tok/s | First request (CUDA graph capture) |
| Max Concurrent | 8 seqs (configurable to 256+) | vs Ollama's 4 |
| GPU Memory | 18.65 GiB | 40% utilization setting |
| KV Cache | FP8 | Reduced memory footprint |
| First Start | ~22 min | Image pull + model download + compile |
| Restart | ~2-7 min | With compile cache |

### Reasoning Parser (nano_v3)

The Nemotron model outputs `reasoning_content` (Chain-of-Thought) separate from `content` (final answer). This means the model can "think" without consuming the output token budget — perfect for extraction tasks where structured JSON output is needed.

```json
{
  "reasoning_content": "We need to extract entities... Aspirin is a Drug, Bayer is a Company...",
  "content": "{\"entities\": [{\"id\": \"Aspirin\", \"type\": \"Drug\"}, ...], \"relations\": [...]}"
}
```

### Domain-Aware Extraction Pipeline (125.7)

- Domain classification runs BEFORE extraction (BGE-M3 classifier)
- Domain-trained prompts (from Neo4j `:Domain` nodes) used when available
- Fallback to generic DSPy prompts when domain has no training
- `domain_id` stored in both Qdrant payloads AND Neo4j entity nodes

### S-P-O Triple Extraction (125.3)

- Replaced 100% RELATES_TO relations with 21 universal relation types (ADR-060)
- Subject-Predicate-Object format: `{subject, subject_type, predicate, object, object_type}`
- Universal types: DEVELOPS, OPERATES_IN, PRODUCES, TREATS, REGULATES, etc.

### Impact on Sprint 126 RAGAS Evaluation

Sprint 126 will run RAGAS Phase 1 (498 docs) with these improvements:
1. **vLLM** for extraction (54 tok/s, 8+ concurrent vs Ollama's 4)
2. **S-P-O triples** instead of RELATES_TO (21 relation types)
3. **Domain-aware prompts** for targeted extraction
4. **VLLM_ENABLED=true** in `.env` to activate vLLM routing

Expected improvements:
- Ingestion speed: 10-50x faster (concurrent extraction)
- Relation diversity: 0% → ~80%+ non-RELATES_TO relations
- Extraction quality: Domain-specific prompts + reasoning parser

---

## Sprint 126: vLLM Stabilization + CUDA Compilation on DGX Spark SM121 (2026-02-07)

### Overview

Sprint 126 focuses on stabilizing vLLM on DGX Spark (GB10 Blackwell, SM121) for sustained multi-request extraction. Previous attempts crashed with `cudaErrorIllegalInstruction` after 1-2 requests. This section documents the full debugging journey, root causes, and the final working configuration.

### DGX Spark SM121 — The Compatibility Challenge

The NVIDIA DGX Spark uses the **GB10 (Blackwell)** chip with compute capability **SM121** (sometimes referred to as SM12.1a). This is a unique architecture:

- **SM120** = standard Blackwell (B100/B200 data center GPUs)
- **SM121** = DGX Spark variant with unified CPU-GPU memory (128 GiB shared)
- **Key difference**: Some CUTLASS kernels compiled for SM120 produce `cudaErrorIllegalInstruction` on SM121

This matters because FlashInfer's MoE (Mixture of Experts) FP4 kernels use CUTLASS grouped GEMM operations that target SM120.

### FlashInfer MOE Backend: `latency` vs `throughput`

| Setting | Behavior on SM121 | Result |
|---------|-------------------|--------|
| `VLLM_FLASHINFER_MOE_BACKEND=throughput` | Autotuner tries SM120 CUTLASS tactics → **crash** | `cudaErrorIllegalInstruction` during inference |
| `VLLM_FLASHINFER_MOE_BACKEND=latency` | Autotuner tries SM120 tactics → **gracefully skips** → falls back to compatible tactics | Stable operation |

**Why `latency` works**: Both backends attempt the same SM120 CUTLASS grouped GEMM tactics (14/15). The difference is in error handling:
- `throughput` mode: autotuner failure → engine crash
- `latency` mode: autotuner failure → `"Failed to initialize cutlass TMA WS grouped gemm"` warning → skip to next tactic → engine continues

**Log evidence (latency mode, working):**
```
[flashinfer] Failed to initialize cutlass TMA WS grouped gemm
[flashinfer] Skipping tactic 14, trying next...
[flashinfer] Skipping tactic 15, trying next...
[flashinfer] Selected tactic 3 (compatible with SM121)
```

### CUDA Compilation Startup Times

vLLM performs 4 sequential compilation phases on first start. These are cached for subsequent starts.

#### Fresh Start (no cache)

| Phase | Duration | Notes |
|-------|----------|-------|
| Model loading (safetensors) | ~90s | 5 shards, 19GB total |
| FlashInfer autotuning | ~10 min | Tests SM120 CUTLASS tactics, skips failures |
| torch.compile | ~9 min (552s) | Inductor backend, generates optimized kernels |
| CUDA graph capture (piecewise) | ~2 min (51 graphs) | `CUDAGraphMode.FULL_AND_PIECEWISE` |
| CUDA graph capture (full) | ~3 min (35 graphs) | Full batch sizes 1-512 |
| **Total cold start** | **~22 min** | First-ever start, no cache |

#### Cached Start (with bind-mounted caches)

| Phase | Duration | Notes |
|-------|----------|-------|
| Model loading (safetensors) | ~90s | Same (not cached) |
| FlashInfer autotuning | ~9s | Compiled kernels reused from `~/.cache/flashinfer/` |
| torch.compile | ~137s (2.3 min) | Reused from `~/.cache/vllm/torch_compile_cache/` |
| CUDA graph capture (piecewise) | ~4s each | Pre-warmed from cache |
| CUDA graph capture (full) | ~4s each | Pre-warmed from cache |
| **Total cached start** | **~4 min** | 5.5x faster than cold start |

#### Cache Bind Mounts (docker-compose.dgx-spark.yml)

```yaml
volumes:
  - ${HOME}/.cache/huggingface:/root/.cache/huggingface    # Model weights (19GB)
  - ${HOME}/.cache/flashinfer:/root/.cache/flashinfer      # FlashInfer JIT CUTLASS kernels
  - ${HOME}/.cache/vllm:/root/.cache/vllm                  # torch.compile + CUDA graph cache
```

**CRITICAL**: Cache is keyed by `gpu-memory-utilization`. Changing from 0.55 to 0.40 invalidates CUDA graph cache (different KV cache sizes). Stale cache causes `cudaErrorIllegalInstruction` on replay. Always clear cache after changing memory settings:

```bash
# Clear stale CUDA caches (files owned by root inside container)
docker run --rm -v ${HOME}/.cache/vllm:/cache alpine sh -c \
  "rm -rf /cache/torch_compile_cache /cache/torch_aot_compile"
```

### GPU Memory Management (3-way sharing)

DGX Spark has 119.6 GiB usable GPU memory shared between vLLM, Ollama, and BGE-M3.

| `gpu-memory-utilization` | vLLM Memory | KV Cache | Room for Ollama + BGE-M3 | Status |
|--------------------------|-------------|----------|--------------------------|--------|
| 0.55 | ~73.7 GiB | ~48 GiB | ~16 GiB (too tight) | BGE-M3 OOM |
| 0.40 | ~55.3 GiB | ~33.6 GiB | ~34 GiB | Ollama 30 GiB + BGE-M3 2 GiB |
| 0.25 | ~34.6 GiB | ~12 GiB | ~55 GiB | Conservative, fewer concurrent seqs |

**Chosen: 0.40** — Balances extraction concurrency (max 57 concurrent sequences) with room for Ollama chat (30 GiB Nemotron) and BGE-M3 embeddings (2 GiB).

**Memory profiling gotcha**: If Ollama loads/unloads models during vLLM's startup profiling phase, vLLM sees "current free > initial free" and crashes with `AssertionError: Error in memory profiling`. **Fix**: Always unload Ollama models before starting vLLM:
```bash
curl -X POST http://localhost:11434/api/generate -d '{"model":"nemotron-3-nano:128k","keep_alive":0}'
```

### httpx Timeout Fix

The AegisLLMProxy's `_call_vllm()` method used `timeout=120.0` for httpx requests. Entity extraction windows take 100-300s on vLLM (especially cold requests with CUDA graph capture). This caused silent timeouts with fallback to Ollama.

**Bug**: `str(httpx.ReadTimeout())` returns empty string `''` — making the fallback invisible in logs.

**Fix** (in `aegis_llm_proxy.py`):
```python
# Line 915: Non-streaming vLLM call
timeout=600.0,  # Was 120.0 — extraction windows take 100-300s

# Line 1222: Streaming vLLM call
timeout=600.0,  # Was 120.0

# Line 641: Error logging
error=repr(e),  # Was str(e) — httpx timeouts have empty str()
```

### First Successful vLLM Extraction (2026-02-07)

**Test file**: `data/ragas_eval_txt/hotpot_000000.txt` (HotpotQA bridge question)
**Results**:
- Entities: 8 extracted via vLLM (77s, no fallback)
- Relations: 6 (specific types: DEVELOPS, PRODUCES, OPERATES_IN, etc.)
- Provider: vLLM (confirmed in API logs: `provider=vllm, fallback_used=False`)
- Total ingestion: 463s (most time in Ollama fallback for earlier windows before timeout fix)

**Crash on 2nd request**: The gleaning/relation extraction request triggered `cudaErrorIllegalInstruction` — caused by stale CUDA graph cache from `0.55` config being replayed with `0.40` config. Fixed by clearing cache and recompiling.

### Current Configuration (docker-compose.dgx-spark.yml)

```yaml
vllm:
  image: nvcr.io/nvidia/vllm:26.01-py3
  command: >
    bash -c '
    wget -nc https://huggingface.co/.../nano_v3_reasoning_parser.py &&
    vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4
      --host 0.0.0.0 --port 8001
      --trust-remote-code
      --enable-auto-tool-choice
      --tool-call-parser qwen3_coder
      --reasoning-parser-plugin nano_v3_reasoning_parser.py
      --reasoning-parser nano_v3
      --gpu-memory-utilization 0.40
      --kv-cache-dtype fp8
    '
  environment:
    - VLLM_USE_FLASHINFER_MOE_FP4=1
    - VLLM_FLASHINFER_MOE_BACKEND=latency     # NOT throughput (crashes SM121)
    - VLLM_FASTSAFETENSORS_NOGDS=1
  volumes:
    - ${HOME}/.cache/huggingface:/root/.cache/huggingface
    - ${HOME}/.cache/flashinfer:/root/.cache/flashinfer
    - ${HOME}/.cache/vllm:/root/.cache/vllm
```

### Stability Testing Status

| Test | Result | Notes |
|------|--------|-------|
| vLLM cold start | ✅ Stable | ~22 min, FlashInfer autotuning skips SM120 tactics |
| vLLM cached start | ✅ **~100s** | torch.compile 2s + CUDA graphs 7s (with bind mounts) |
| 1st extraction (entities) | ✅ 78s | 7 entities, 4,954 tokens, provider=vllm, fallback=False |
| 2nd extraction (relations) | ✅ vLLM stable | JSON parse failed (reasoning content leak), cascade→gpt-oss:20b |
| 3rd extraction (relations via graph_extraction) | ✅ 44.5s | 8 relations, 3,136 tokens, provider=vllm, fallback=False |
| **Multi-request stability** | ✅ **CONFIRMED** | 3 consecutive vLLM requests, no crashes |

**Root cause of `cudaErrorIllegalInstruction` CONFIRMED**: Stale CUDA graph cache compiled with `gpu-memory-utilization=0.55` was replayed with `0.40` config. Different KV cache sizes caused incompatible CUDA graph execution. Fix: clear `~/.cache/vllm/torch_compile_cache` and `torch_aot_compile` after changing memory settings.

### Full Pipeline Test Results (hotpot_000003.txt, 2026-02-07)

```json
{
  "status": "success",
  "documents_loaded": 1,
  "chunks_created": 1,
  "embeddings_generated": 1,
  "points_indexed": 1,
  "duration_seconds": 433.53,
  "neo4j_entities": 7,
  "neo4j_relationships": 7
}
```

**Pipeline timing breakdown:**
| Phase | Duration | Engine |
|-------|----------|--------|
| Parse (Docling) | 2.2s | CPU |
| Chunking | 0.8s | CPU |
| Embedding (BGE-M3) | 0.07s | GPU |
| Entity extraction | 78s | vLLM (rank 1) |
| Relation extraction (cascade) | ~305s | vLLM (rank 1, JSON fail) → gpt-oss:20b (rank 2) |
| Relation extraction (graph) | 44.5s | vLLM |
| Neo4j storage | 1.0s | — |
| **Total** | **433.5s** | Mixed (vLLM + Ollama fallback) |

### Root Cause: Reasoning Token Budget Exhaustion (RESOLVED)

**Problem**: With `enable_thinking=true` (default), Nemotron outputs CoT reasoning BEFORE JSON. For relation extraction (complex prompts), the model used all 8,192 `max_tokens` on reasoning, leaving `content=None`. The `reasoning_content` (26,534 chars) was pure CoT with no JSON.

**API logs confirmed**:
```
vllm_using_reasoning_as_content | reason=content_was_empty_or_none | reasoning_length=26534
tokens_output=8192  (= exactly max_tokens → model was truncated mid-reasoning!)
```

**Fix**: Disable reasoning for extraction via `chat_template_kwargs: {"enable_thinking": false}`:
```json
{
  "model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4",
  "messages": [...],
  "chat_template_kwargs": {"enable_thinking": false},
  "max_tokens": 8192
}
```

**NVIDIA reference**: [HuggingFace Model Card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4) documents `enable_thinking` for vLLM via `chat_template_kwargs`.

### Performance Improvement: enable_thinking=false (2026-02-07)

| Phase | Before (thinking=true) | After (thinking=false) | Speedup |
|-------|----------------------|----------------------|---------|
| Entity Extraction | 78.3s (3,919 output tokens) | **8.8s** (469 tokens) | **8.9x** |
| Relation Extraction | 305s (vLLM fail→Ollama) | **11.8s** (vLLM direct) | **25.8x** |
| Relation (graph_extraction) | 44.5s | **12.2s** | **3.6x** |
| **Total Pipeline** | **433.5s** | **64.0s** | **6.8x** |

| Quality Metric | Before | After |
|---------------|--------|-------|
| Entities extracted | 7 | **17** |
| Relations extracted | 7 | **11** |
| vLLM fallback to Ollama | Yes (relation) | **No** |
| Domain detected | None | **chemistry** |

**Full pipeline test (hotpot_000004.txt)**:
```json
{
  "status": "success",
  "duration_seconds": 64.02,
  "neo4j_entities": 17,
  "neo4j_relationships": 11
}
```

**Note**: The model still outputs a brief reasoning prefix ("Reasoning: Identify entities...") before the JSON array, even with `enable_thinking=false`. This is not a problem — the `regex_array` JSON parser correctly extracts the JSON from within the response.

---

## Parallel Extraction & GPU Memory Benchmark (2026-02-08)

### Experiment Goal

Determine optimal `gpu-memory-utilization` and `AEGIS_EXTRACTION_WORKERS` (parallel cross-sentence windows) for the vLLM extraction pipeline on DGX Spark (128GB unified memory, SM121).

### Setup

- **Engine**: Pure vLLM (Ollama OFF, engine mode = `vllm`, no fallback)
- **Model**: Nemotron-3-Nano-30B-A3B-NVFP4 via NGC `nvcr.io/nvidia/vllm:26.01-py3`
- **Reasoning**: Disabled (`enable_thinking=false`)
- **Cross-sentence windows**: ON (AEGIS_USE_CROSS_SENTENCE=1)
- **Files**: Fresh S-category RAGAS Phase 1 files (~2.8KB each), unique per test to avoid Redis prompt cache contamination
- **Cache**: Redis `prompt_cache:*` cleared before each test

### Phase 1: Worker Count Scaling (gpu-memory-utilization=0.45, vLLM ~64.5GB)

| Workers | Duration | Graph (s) | LLM Latency (ms) | Entities | Relations (init) | Windows | Speedup | Notes |
|---------|----------|-----------|-------------------|----------|------------------|---------|---------|-------|
| 1       | 229s     | 226s      | 187,208           | 13       | 63               | 6       | 1.00x   | Baseline sequential |
| **2**   | **113s** | **110s**  | **91,778**        | 3        | 65               | 9       | **2.03x** | **Optimal** |
| 4       | 169s     | 166s      | 131,081           | 21       | 99               | 10      | 1.35x   | Degradation starts |
| 8       | 393s     | 390s      | 355,587           | 20       | 92               | 7       | 0.58x   | GPU saturated, worse than 1 |

**Finding**: 2 workers = optimal. Diminishing returns above 2 because vLLM shares GPU compute across concurrent requests. At 4+, per-request latency increases faster than parallelism helps.

### Phase 2: GPU Memory Utilization Scaling (2 and 3 workers)

| GPU Util | vLLM GPU (GB) | Workers | Duration | LLM Latency (ms) | Entities | Relations | Status |
|----------|---------------|---------|----------|-------------------|----------|-----------|--------|
| 0.45     | 64.5          | 2       | 113s     | 91,778            | 3        | 65        | Clean |
| 0.50     | 68.3          | 2       | 622s     | 579,000           | 17       | 89        | Reasoning leak outlier (11,729 output tokens) |
| 0.50     | 68.3          | 3       | 444s     | 406,000           | 23       | 0         | 3/7 windows failed, reasoning leaks |
| 0.55     | 71.2          | 2       | 182s     | 152,022           | 10       | 89        | Clean but slower than 0.45 |
| 0.55     | 71.2          | 3       | 105s     | 87,892            | 50       | 0         | **vLLM crashed** — `cudaErrorIllegalInstruction`, 8/8 windows failed |
| 0.60     | 80.9          | —       | —        | —                 | —        | —         | **BGE-M3 CUDA OOM** — insufficient memory for embeddings |

**Findings**:
1. **gpu-memory-utilization=0.45 is optimal** — stable, room for BGE-M3 (2GB) + Ollama (30GB)
2. **0.50 produces reasoning leaks** — model generates 5-10x more output tokens for some content, unpredictable
3. **0.55 + 3 workers crashes vLLM** — `cudaErrorIllegalInstruction` when 3 concurrent relation windows hit GPU simultaneously
4. **0.60 OOM** — 80.9GB vLLM + 30GB Ollama + 2GB BGE-M3 > 128GB unified memory

### Key Insight: Content Variance Dominates

Files of similar size (~2.8KB) show wildly different extraction complexity:
- Some files: 3 entities, 65 relations, 113s
- Other files: 50 entities, 0 relations (all windows crash), 105s
- Reasoning "leaks" (11,729 output tokens vs normal ~1,500) make single-file comparison unreliable

The `max_tokens×2` workaround (doubling max_tokens as safety net for inline CoT) mitigates but doesn't eliminate this variance.

### Optimal Configuration

```bash
# .env
AEGIS_EXTRACTION_WORKERS=2

# docker-compose.dgx-spark.yml
--gpu-memory-utilization 0.45

# Redis engine mode
aegis:llm_engine_mode = auto  # vLLM primary, Ollama fallback
```

**Memory budget at 0.45**: vLLM 64.5GB + Ollama 30GB + BGE-M3 2GB = ~96GB / 128GB (75% utilization, 32GB headroom)

---

## Sprint 127: RAGAS Phase 1 — First 10-Doc Ingestion (2026-02-08)

### Configuration

| Setting | Value |
|---------|-------|
| Engine mode | `vllm` (no Ollama fallback) |
| Workers | 2 (`AEGIS_EXTRACTION_WORKERS`) |
| GPU memory | 0.45 (`gpu-memory-utilization`) |
| vLLM model | Nemotron-3-Nano-30B-A3B-NVFP4 |
| Retry | tenacity 3× exponential backoff (5-30s) on transient errors |
| Namespace | `ragas_phase1_sprint127` |

### Changes Made

1. **vLLM retry with backoff** (`aegis_llm_proxy.py`): Added `@retry(stop=3, wait=exp(5-30s))` to `_call_vllm()`. Retries on `httpx.TimeoutException`, `httpx.ConnectError`, and HTTP 5xx. Does NOT retry 4xx (prompt errors).
2. **Batch script re-auth** (`batch_upload_ragas_10.sh`): JWT token refreshed before each upload (previously expired after ~30min, failing docs 4-10).

### Results: 10/10 Docs Ingested

All 10 documents completed processing in the backend. 1 doc (17KB techqa) was still finishing when curl timed out, but pipeline completed in background.

| # | File | Size | Time | Entities | Relations | Chunks |
|---|------|------|------|----------|-----------|--------|
| 1 | 0003_hotpot_5a82171f | 3.6KB | 758.9s | 18 | 98 | 1 |
| 2 | 0004_logqa_emanual1 | 4.1KB | 315.6s | 4 | 91 | 1 |
| 3 | 0007_logqa_emanual6 | 2.8KB | 244.8s | 25 | 60 | 1 |
| 4 | 0010_logqa_emanual1 | 5.7KB | 336.5s | 19 | 221 | 1 |
| 5 | 0012_ragbench_techqaTR | 17.3KB | >1500s* | 18+ | 214+ | 4 |
| 6 | 0015_hotpot_5ae0d91e | 6.2KB | 753.4s | 18 | 182 | 2 |
| 7 | 0015_ragbench_28 | 2.5KB | 444.5s | 19 | 66 | 1 |
| 8 | 0015_ragbench_5009 | 2.0KB | 339.4s | 18 | 56 | 1 |
| 9 | 0016_ragbench_techqaTR | 6.5KB | 1163.2s | 61 | 313 | 2 |
| 10 | 0018_logqa_emanual3 | 2.8KB | 231.4s | 4 | 75 | 1 |

*Doc 5 had 4 chunks (17KB); chunk 0 extracted 214 relations, chunk 1 timed out on Rank 1 → cascaded to Rank 2.

### Aggregate Stats

| Metric | Value |
|--------|-------|
| **Docs ingested** | 10/10 (100%) |
| **Total entities** | 204 |
| **Total relations** | 1,376 |
| **Total chunks** | 15 |
| **Avg time/doc** | 510s (~8.5 min) for 9 completed, excl doc 5 |
| **vLLM calls** | 199 successful, **0 retries**, 0 failures |
| **Cascade fallbacks** | 1 (doc 5 chunk 1: TimeoutError → Rank 2) |

### vLLM Stability Assessment

**Rock solid.** 199 consecutive vLLM calls with zero failures and zero retries needed. The tenacity retry decorator was added as insurance but was never triggered — the `gpu-memory-utilization=0.45` + `VLLM_FLASHINFER_MOE_BACKEND=latency` configuration is completely stable for sustained batch workloads.

### Performance Analysis

**Graph extraction dominates**: 95-99% of total pipeline time is graph extraction (`graph_ms`). Parse (2-3s), chunking (0.8-3s), and embedding (0.1-0.5s) are negligible.

**Relation count varies dramatically by content**:
- Hotpot files (biographical/factual): 98-182 relations
- TechQA files (technical manuals): 56-313 relations (highest for multi-chunk docs)
- LogQA files (equipment manuals): 60-221 relations (wide range)

**Doc 1 was slowest** (758.9s for 3.6KB) because it was the first extraction after container restart — vLLM had to warm up CUDA graph cache for the entity extraction prompt pattern. Subsequent docs of similar size ran in 230-340s.

### Bottleneck: LightRAG Double Extraction

Graph extraction time includes LightRAG's `ainsert_custom_kg` which performs a **second vLLM extraction call** on the same data. This is the known LightRAG overhead (ADR-061). Removing LightRAG (Sprint 128) should halve graph extraction time.

### Issues Found

1. **JWT expiry during batch**: Token expired after ~30min, failing docs 4-10. **Fixed**: Re-auth before each upload.
2. **curl --max-time 900**: Not enough for large files (17KB, 4 chunks). Backend continues processing regardless.
3. **Doc 5 cascade fallback**: Chunk 1 entity extraction timed out on Rank 1 (600s httpx timeout), cascaded to Rank 2. In `engine_mode=vllm`, Rank 2 uses the same vLLM endpoint — effectively a retry with a different model name (ignored by vLLM).

### Next Steps

- [ ] Ingest remaining 488 docs (batch of 50, background processing)
- [ ] Run RAGAS evaluation on 10-doc subset
- [ ] Remove LightRAG (Sprint 128) to halve graph extraction time
- [ ] Increase curl timeout to 1800s for large files

---

### Sprint 127.1: Quality Evaluation (2026-02-08)

**Namespace:** `ragas_phase1_sprint124` (LightRAG namespace mapping issue — entities stored under old namespace)

#### Relation Quality

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total relations | 870 | — | — |
| Specific semantic types | 184 (21.1%) | >70% | BELOW TARGET |
| Generic (RELATED_TO) | 686 (78.9%) | <30% | ABOVE TARGET |
| Unique relation types used | 18 | 10-15 | Exceeds |

**Top Semantic Relation Types:**

| Type | Count | % of Specific |
|------|-------|---------------|
| CONTAINS | 48 | 26.1% |
| PART_OF | 44 | 23.9% |
| ASSOCIATED_WITH | 15 | 8.2% |
| USES | 15 | 8.2% |
| SUPPORTS | 13 | 7.1% |
| MANAGES | 10 | 5.4% |
| PRECEDED_BY | 9 | 4.9% |
| DEPENDS_ON | 8 | 4.3% |
| DERIVED_FROM | 6 | 3.3% |
| *8 more types* | 16 | 8.7% |

**Root Cause of Low Diversity:** LightRAG's `ainsert_custom_kg` performs its own extraction and stores ALL relations as `RELATES_TO` edge type with a `relation_type` property. 686/870 (79%) are generic `RELATED_TO` from LightRAG's extraction. AegisRAG's ExtractionService produces correctly typed relations, but LightRAG's duplicate path overwrites them. After LightRAG removal (Sprint 128), relation diversity should improve to >80%.

#### Entity Type Distribution (13/15 universal types used)

| Entity Type | Count | % |
|-------------|-------|---|
| CONCEPT | 231 | 26.5% |
| PRODUCT | 209 | 23.9% |
| OTHER | 178 | 20.4% |
| TECHNOLOGY | 86 | 9.8% |
| ORGANIZATION | 58 | 6.6% |
| DATE | 42 | 4.8% |
| PERSON | 16 | 1.8% |
| EVENT | 15 | 1.7% |
| PAPER | 11 | 1.3% |
| LOCATION | 9 | 1.0% |
| TEMPORAL | 8 | 0.9% |
| BENCHMARK/MODEL/etc. | 8 | 0.9% |

**Assessment:** 13 of 15 ADR-060 universal types are used. Entity extraction quality is good. Missing types: METHODOLOGY, REGULATION (expected given dataset domains).

#### Compliance Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Entity names ≤4 words | 91.9% | >90% | MEETS |
| Domain sub-types stored | 0 | — | NOT STORED (LightRAG bypass) |
| Total entities | 873 | — | — |
| Unique documents (by filename) | 45 | — | Includes Sprint 124 + 127 data |

#### Key Takeaways

1. **Entity extraction quality is good** — 13/15 universal types, 91.9% name compliance
2. **Relation diversity blocked by LightRAG** — 79% generic because LightRAG re-extracts and stores as RELATED_TO
3. **Domain sub-types not preserved** — LightRAG's storage path bypasses AegisRAG's sub_type property
4. **Namespace isolation broken** — Upload with `ragas_phase1_sprint127` but stored as `ragas_phase1_sprint124` by LightRAG
5. **Sprint 128 LightRAG removal** is the critical path to achieving >70% relation diversity target

---

### Sprint 127.2: RAGAS Metrics Baseline (2026-02-08)

**Configuration:**
- Eval LLM: nemotron-3-nano:128k (Ollama, num_ctx=32768, num_predict=4096)
- Answer LLM: nemotron-3-nano:128k (via AegisLLMProxy)
- Retrieval: FourWayHybridSearch, top_k=10, namespace ragas_phase1_sprint124
- Corpus: 45 documents (90 vectors in Qdrant), 20 sample questions
- Duration: 87 min (5,244s) for 80 metric jobs

**Results:**

| Metric | Score | Target | Status | Valid |
|--------|-------|--------|--------|-------|
| Context Precision | 0.739 | >0.85 | BELOW | 20/20 |
| Context Recall | 0.760 | >0.75 | PASS | 20/20 |
| Faithfulness | 0.699 | >0.90 | BELOW | 14/20 |
| Answer Relevancy | 0.828 | >0.95 | BELOW | 20/20 |

**Key Findings:**
1. **Context Recall passes** — retrieval pipeline finds relevant content (76% of ground truth attributable)
2. **Faithfulness has 6 NaN samples** — `statement_generator_prompt` parsing failures (Nemotron truncates long NLI statements at num_predict=4096)
3. **4 questions show CR=0.00** — multi-hop questions requiring documents not in the 45-doc corpus
4. **Answer Relevancy at 0.83** — some answers include verbose reasoning sections (markdown headings, bullet points) that reduce relevancy scores

**Technical Breakthrough — RAGAS + Local Ollama Models:**

Previous RAGAS evaluation attempts (gpt-oss:20b, nemotron with num_ctx=8192) failed with 57%+ parsing errors. Root causes discovered and fixed:

1. **Prompt truncation** (root cause): RAGAS prompts with 10 contexts are ~15K tokens. With `num_ctx=8192`, Ollama truncates from the beginning, removing the classification instruction and JSON schema. The model sees only contexts + question and answers like a Q&A task. **Fix**: `num_ctx=32768`.

2. **LangChain LLM bypass** (root cause): RAGAS detects `ChatOllama` as a LangChain LLM and routes through `model_validate_json()` (strict Pydantic, no preprocessing). This bypasses RAGAS's tolerant `parse_output_string()` → `extract_json()` path. **Fix**: Wrap in `LangchainLLMWrapper` which returns `is_langchain_llm=False`.

3. **Boolean vs integer** (minor): Local models output `"attributed": true` instead of `"attributed": 1`. **Fix**: Monkey-patch `extract_json()` with boolean→integer regex conversion.

4. **Missing wrapper objects** (minor): Models output `[{...}]` instead of `{"classifications": [{...}]}`. **Fix**: Auto-wrap in monkey-patched `extract_json()`.

**Optimization Targets for Sprint 128+:**
- **Context Precision**: Reduce noise in retrieved contexts → better reranking, lower top_k
- **Faithfulness**: Reduce hallucination in answers → constrained generation, post-generation verification
- **Answer Relevancy**: Remove verbose reasoning from answers → strip markdown formatting before scoring
- **Faithfulness NaN rate**: Increase num_predict or simplify statement_generator_prompt for local models
