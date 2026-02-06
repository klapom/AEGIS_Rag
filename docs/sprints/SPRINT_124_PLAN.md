# Sprint 124 Plan: RAGAS Evaluation Reboot + Phase 2 Ingestion

**Date:** 2026-02-04
**Status:** 🔄 In Progress
**Total Story Points:** 24 SP (estimated)
**Predecessor:** Sprint 123 (E2E Test Stabilization)

---

## Sprint Goals

1. **Fix RAGAS evaluation accuracy** (context truncation, 128K context window)
2. **Clean-slate database reset** (remove stale test data)
3. **Ingest Phase 1 + Phase 2 datasets** (800 samples total)
4. **Run baseline RAGAS evaluation** with corrected settings

---

## Features

### 124.1: RAGAS Accuracy Fixes (5 SP) ✅ COMPLETE

**Problem:** Previous RAGAS evaluations were inaccurate due to:
- 500-char truncation in `eval_harness.py` (grounding check)
- 32K context window (vs. Ollama's 132K capability)
- BM25 deprecated code still running

**Fixes Applied:**

| File | Change | Impact |
|------|--------|--------|
| `src/adaptation/eval_harness.py` | Removed 500-char truncation | +10-20% Faithfulness |
| `src/evaluation/ragas_evaluator.py` | num_ctx 32K → 128K | Full context for evaluation |
| `src/api/v1/admin.py` | Removed BM25 stats code | Cleaner API response |
| `src/components/ingestion/job_tracker.py` | Phase "bm25" → "sparse" | Correct terminology |
| `docs/ragas/RAGAS_EVALUATION_GUIDE.md` | Removed BM25 references | Updated documentation |

**Commit:** `060c5f0` - `fix(sprint124): RAGAS accuracy fixes + BM25 cleanup`

---

### 124.2: Database Reset (2 SP) 🔄 IN PROGRESS

**Goal:** Clean-slate for accurate RAGAS baseline

**Steps:**
1. Stop containers
2. Clear Qdrant storage
3. Clear Neo4j data
4. Clear Redis cache
5. Clear LightRAG storage
6. Restart containers
7. Rebuild API container (to apply code fixes)

**Commands:**
```bash
# Stop containers
docker compose -f docker-compose.dgx-spark.yml down

# Clear data (Sprint 124: BM25 removed - using BGE-M3 sparse vectors)
rm -rf data/qdrant_storage/* data/neo4j_data/* data/redis_data/* data/lightrag_storage/*.*

# Rebuild API container (required for code fixes)
docker compose -f docker-compose.dgx-spark.yml build --no-cache api

# Restart all containers
docker compose -f docker-compose.dgx-spark.yml up -d
```

---

### 124.3: Phase 1 Ingestion (8 SP) 📝 PLANNED

**Dataset:** `ragas_phase1_500.jsonl` (500 samples)

| Aspect | Value |
|--------|-------|
| Sources | HotpotQA + LogQA |
| Doc Types | clean_text (333), log_ticket (167) |
| Question Types | multihop, lookup, howto, comparison, definition, policy |
| Difficulty | D1 (36%), D2 (31.6%), D3 (32.4%) |
| Namespace | `ragas_phase1_sprint124` |

**Ingestion Script:**
```bash
./scripts/upload_ragas_phase1.sh
```

**Expected Results:**
- ~500 vectors in Qdrant
- ~8,000+ entities in Neo4j
- ~15,000+ relationships

---

### 124.4: Phase 2 Ingestion - Tables + Code (5 SP) 📝 PLANNED

**Datasets:**

| Dataset | Samples | Format | Namespace |
|---------|---------|--------|-----------|
| T2-RAGBench | 150 | Financial Tables (Markdown) | `ragas_phase2_tables` |
| MBPP | 150 | Python Code (Fenced) | `ragas_phase2_code` |

**Features Already Implemented:**
- `table_to_markdown()` - Converts tables to Markdown format
- Code syntax preservation with ```python fencing
- Question + Answer + Test Cases structure

**Ingestion Script:**
```bash
poetry run python scripts/ingest_phase2_datasets.py --samples 150
```

**Expected Results:**
- ~300 additional vectors in Qdrant
- Enhanced entity types (FINANCIAL_METRIC, FUNCTION, PARAMETER)

---

### 124.5: RAGAS Baseline Evaluation (4 SP) 📝 PLANNED

**Evaluation Plan:**

| Mode | Description | Expected Metrics |
|------|-------------|------------------|
| Vector | Dense + Sparse RRF | CP ≥ 0.85, CR ≥ 0.75 |
| Graph | Entity→N-hop→Chunk | Better for entity-centric queries |
| Hybrid | Vector + Graph fusion | Best overall |

**Target Metrics (with fixes):**

| Metric | Previous (biased) | Target (corrected) |
|--------|-------------------|-------------------|
| Context Precision | 86.2% | ≥ 85% |
| Context Recall | 77.5% | ≥ 75% |
| **Faithfulness** | 73.7% | **≥ 85%** (+12%) |
| Answer Relevancy | 78.9% | ≥ 90% |

**Evaluation Script:**
```bash
poetry run python scripts/run_ragas_evaluation.py \
    --namespace ragas_phase1_sprint124 \
    --output reports/sprint124_ragas_baseline.json
```

---

## Timeline

| Day | Task | SP |
|-----|------|-----|
| Day 1 (Today) | 124.1 Fixes ✅ + 124.2 DB Reset | 7 |
| Day 2 | 124.3 Phase 1 Ingestion | 8 |
| Day 3 | 124.4 Phase 2 Ingestion | 5 |
| Day 4 | 124.5 RAGAS Evaluation + Documentation | 4 |

---

## Success Criteria

1. ✅ RAGAS accuracy fixes committed and pushed
2. ⏳ Clean Qdrant (0 vectors) and Neo4j (0 entities)
3. ⏳ 800 samples ingested (Phase 1 + Phase 2)
4. ⏳ Faithfulness ≥ 85% (up from 73.7%)
5. ⏳ Updated RAGAS_JOURNEY.md with Sprint 124 experiment

---

## Technical Notes

### Why Faithfulness Was Biased

The previous 73.7% Faithfulness score was artificially low because:

1. **Truncation (500 chars):** The grounding check only saw partial context
   ```python
   # BEFORE (biased)
   source_texts.append(f"[{i}] {text[:500]}")  # Truncated!

   # AFTER (correct)
   source_texts.append(f"[{i}] {text}")  # Full context
   ```

2. **Context Window (32K):** Long documents were cut off
   ```python
   # BEFORE
   num_ctx=32768  # 32K tokens

   # AFTER
   num_ctx=131072  # 128K tokens (matches Ollama capability)
   ```

### Phase 2 Data Formats

**Tables (T2-RAGBench):**
```markdown
## Data Table
| metric | Q1 | Q2 | Q3 | Q4 |
|--------|----|----|----|----|
| revenue | $1.2M | $1.5M | $1.8M | $2.1M |
```

**Code (MBPP):**
```markdown
## Solution Code
```python
def function_name(param):
    return result
```

## Test Cases
assert function_name(input) == expected
```

---

## References

- **ADR-048:** RAGAS 1000-Sample Benchmark Plan
- **RAGAS_EVALUATION_GUIDE.md:** Updated with Sprint 124 changes
- **Commit 060c5f0:** RAGAS accuracy fixes

---

**Sprint 124 Lead:** Claude Opus 4.5
**Last Updated:** 2026-02-04
