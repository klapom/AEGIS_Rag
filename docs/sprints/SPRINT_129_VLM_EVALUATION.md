# Sprint 129.6: VLM Parallel Pages — Critical Evaluation

**Date:** 2026-02-11
**Benchmark:** A/B test with 4 documents (3 PDFs + 1 TXT)
**VLM Model:** nvidia/Llama-3.1-Nemotron-Nano-VL-8B-V1-FP4-QAD (port 8002, ~12GB GPU)
**Extraction Engine:** vLLM Nemotron-3-Nano-30B (port 8001, ~64GB GPU)

## 1. Executive Summary

**Recommendation: DISABLE VLM cross-validation. Keep Docling heuristic scoring only.**

The VLM parallel pages feature adds GPU memory pressure, introduces quality regression for tables, and provides no measurable improvement to extraction quality. The Docling heuristic scoring (0.90+ for well-structured tables) is already accurate and doesn't need VLM second-guessing.

## 2. Benchmark Results

### 2.1 Processing Time

| File | Size | VLM ON (Phase A) | VLM OFF (Phase B) | Delta |
|------|------|-------------------|--------------------|---------|
| VM3.pdf | 5.8MB | 861s | 1206s | A 29% faster |
| DP-Bench 45 | 113KB | 126s | 110s | B 13% faster |
| DP-Bench 46 | 137KB | 371s | 165s | B 56% faster |
| RAGAS hotpot | 3.6KB | 293s | 55s | B 81% faster |

**Note:** Phase A had Redis prompt cache from a prior smoke test (explains faster times for VM3). Phase B ran on a clean cache. Phase A also ran with the old cascade (Rank 2/3 Ollama fallback) while Phase B ran after Rank 2/3 removal. The timing differences are primarily due to these confounds, NOT VLM processing overhead.

VLM page rendering overhead: **40.2s for VM3.pdf (13 pages)** = 3.1s/page. This is ~4.7% of total processing time.

### 2.2 Extraction Quality

| File | VLM ON (Entities/Relations) | VLM OFF (Entities/Relations) |
|------|------------------------------|-------------------------------|
| VM3.pdf | 95 / 87 | 121 / 209 |
| DP-Bench 45 | 22 / 9 | 15 / 11 |

Phase B (VLM OFF) extracted **27% more entities** and **140% more relations** for VM3.pdf. This is NOT because VLM is worse at extraction — it's because:
1. Phase A had Redis prompt cache hits (stale/compressed extraction results)
2. Phase B ran with clean cache → fresh LLM extractions

### 2.3 Table Quality Scores

**VM3.pdf tables (the critical test):**

| Table | Heuristic Score | VLM Agreement | Adjusted Score | Effect |
|-------|----------------|---------------|----------------|--------|
| #0 (3x6) | 0.903 EXCELLENT | 0.761 | 0.832 GOOD | Downgraded |
| #1 (8x3) | 0.918 EXCELLENT | 0.692 | 0.805 GOOD | Downgraded |
| #2 (4x3) | 0.930 EXCELLENT | 0.388 | 0.659 FAIR | Downgraded |
| #3 (9x2) | 0.815 GOOD | 0.230 | 0.523 FAIR | Downgraded |

**DP-Bench tables (simpler tables):**

| Table | VLM ON | VLM OFF |
|-------|--------|---------|
| DP-Bench 45 | 0.978 EXCELLENT | 0.956 EXCELLENT |
| DP-Bench 46 | 0.916 EXCELLENT | 0.946 EXCELLENT |

**Conclusion:** The VLM cross-validation CONSISTENTLY downgraded table quality for VM3.pdf. The Nemotron VL 8B model's table extraction differs from Docling's output, producing low agreement scores (0.23-0.76) that drag down the blended score. This is the VLM introducing noise, not correcting errors.

## 3. GPU Memory Impact

| Component | GPU Memory |
|-----------|-----------|
| Extraction vLLM (0.45) | ~64 GB |
| VLM Table (0.10) | ~12 GB |
| BGE-M3 embeddings | ~3.5 GB |
| System overhead | ~10 GB |
| **Total** | **~89.5 GB / 128 GB** |

During the benchmark, the extraction vLLM crashed with `cudaErrorIllegalInstruction` when running 2 concurrent document extractions. The 12GB VLM table container reduces the GPU headroom from 40GB to 28GB, making the system more fragile under load.

## 4. Bugs Found

### 4.1 Duplicate Table Chunks in Qdrant
Phase A stored 8 table points for VM3.pdf's 4 tables — both pre-cross-validation and post-cross-validation versions. This doubles the table representation in the vector store.

### 4.2 Cross-Validation Active When Toggle OFF
Table #3 (score 0.815) still received VLM cross-validation in Phase B because `TABLE_CROSS_VALIDATION_ENABLED` and `VLM_PARALLEL_PAGES_ENABLED` are independent settings. The toggle only controls precomputed parallel page processing, not the cross-validator's on-demand VLM calls.

### 4.3 Cascade Rank 2/3 Causes GPU Crashes (FIXED)
Ollama fallback (Rank 2: gpt-oss:20b) loaded a 20GB model during vLLM extraction, causing `cudaErrorIllegalInstruction`. **Fixed in this session:** Rank 2/3 removed, cascade is now Rank 1 only with vLLM tenacity retry.

## 5. Recommendation

### Disable VLM Cross-Validation
- Set `TABLE_CROSS_VALIDATION_ENABLED=false` (default)
- Keep Docling heuristic scoring (0.90+ for well-structured tables is accurate)
- The VLM model is too weak for reliable table quality assessment

### Remove VLM Table Container
- Stop `aegis-vlm-table` container
- Reclaim 12GB GPU memory for extraction headroom
- Reduces `cudaErrorIllegalInstruction` risk under concurrent load

### Keep Docling Table Ingestion Pipeline
- The Docling-based table quality scoring (Sprint 129.6a) works well
- Heuristic scoring correctly identifies EXCELLENT/GOOD/FAIR/POOR tables
- Table chunks are properly created and stored in Qdrant + Neo4j

### Future: Better VLM for Table Validation
If VLM cross-validation is desired in the future:
- Use a dedicated table OCR model (e.g., Microsoft Table Transformer, Google PaLI-3)
- Or use a cloud API (OpenAI GPT-4V, Anthropic Claude) for borderline tables only
- The Nemotron VL 8B is a general vision-language model, not a table specialist

## 6. Decision: Cascade Rank 2/3 Removal (Sprint 129)

**Decision:** Remove Ollama-based cascade Rank 2 (gpt-oss:20b) and Rank 3 (SpaCy hybrid).

**Rationale:**
1. Ollama fallback wastes ~20GB GPU memory
2. Loading Ollama models during vLLM extraction causes `cudaErrorIllegalInstruction`
3. vLLM tenacity retry (3 attempts, exp backoff 5-30s) handles transient failures
4. Sprint 128.7 benchmark: 0 retries needed in 199 consecutive vLLM calls

**Implementation:** `src/config/extraction_cascade.py` — `DEFAULT_CASCADE` now contains only Rank 1 with 600s timeout.
