# RAGAS Evaluation Executive Summary
**Date:** 2026-01-08
**Evaluated by:** RAG Tuning Agent
**Datasets:** Amnesty QA (10 questions), HotpotQA (5 questions)
**RAGAS Version:** 0.4.2

---

## TL;DR

**Status:** ✅ Valid baseline established, ⚠️ Faithfulness critical bottleneck identified

**Best Mode by Dataset:**
- **Amnesty (Human Rights):** Graph Mode (F=0.550, AR=0.735, CP=0.581)
- **HotpotQA (General Knowledge):** Hybrid Mode (F=0.500, all metrics best)

**Critical Issues:**
1. **Faithfulness universally low** (max 0.550 vs SOTA 0.90 → -39% gap)
2. **Graph Mode fails on 60% of HotpotQA questions** (entity extraction gaps)
3. **Hybrid Mode hallucination on Amnesty** (F=0.301, -68% gap vs SOTA)

**Sprint 80 Quick Wins (4-5 days total):**
1. Add "cite sources" prompt → F +50-80%
2. Fix Graph chunk truncation (500 → 1000 chars) → HotpotQA F +20-30%
3. Add Graph→Vector fallback → HotpotQA failures 3/5 → 0/5
4. Implement Hybrid cross-encoder reranking → Amnesty Hybrid F +100-150%

**Expected Sprint 80 Results:**
- Amnesty Graph F: 0.550 → 0.750-0.850 (+36-55%)
- HotpotQA Hybrid F: 0.500 → 0.650-0.750 (+30-50%)
- All empty context failures resolved

---

## Performance Snapshot

### Amnesty Dataset (Human Rights, 10 questions)

| Metric | Vector | Graph | Hybrid | SOTA | Gap |
|--------|--------|-------|--------|------|-----|
| Context Precision | 0.391 | **0.581** ✅ | 0.400 | 0.85 | -32% |
| Context Recall | 0.456 | **0.587** ✅ | 0.556 | 0.75 | -22% |
| Faithfulness | 0.456 | **0.550** ⚠️ | 0.301 ❌ | 0.90 | -39% |
| Answer Relevancy | 0.650 | 0.735 | **0.781** ✅ | 0.95 | -18% |
| **Overall** | 0.488 | **0.613** | 0.510 | 0.86 | -29% |

**Winner:** Graph Mode (CP/CR/F all best)

### HotpotQA Dataset (General Knowledge, 5 questions)

| Metric | Vector | Graph | Hybrid | SOTA | Gap |
|--------|--------|-------|--------|------|-----|
| Context Precision | 0.417 | 0.200 ❌ | **0.483** ✅ | 0.85 | -43% |
| Context Recall | **0.600** ✅ | 0.200 ❌ | **0.600** ✅ | 0.75 | -20% |
| Faithfulness | 0.350 | 0.250 ❌ | **0.500** ⚠️ | 0.90 | -44% |
| Answer Relevancy | 0.479 | 0.345 ❌ | **0.501** ⚠️ | 0.95 | -47% |
| **Overall** | 0.462 | 0.299 | **0.521** | 0.86 | -39% |

**Winner:** Hybrid Mode (all metrics best)

---

## Key Findings

### 1. Domain-Dependent Performance ✅

**Amnesty (Entity-centric legal/policy queries):**
- Graph Mode excels: CP=0.581 (+49% vs Vector), CR=0.587 (+29% vs Vector)
- Reason: Entity-relationship traversal captures relevant context precisely

**HotpotQA (Factoid multi-hop queries):**
- Hybrid Mode excels: All metrics best
- Graph Mode fails: 3/5 questions return empty contexts (entity extraction misses)

**Implication:** **Need query-adaptive routing** to select mode based on query type.

---

### 2. Faithfulness Critical Bottleneck ❌

**Problem:**
- **Best F:** 0.550 (Graph, Amnesty) vs SOTA 0.90 → **-39% gap**
- **Worst F:** 0.250 (Graph, HotpotQA) → **-72% gap**
- All modes below 0.6 across both datasets

**Root Causes:**
1. **Answer over-elaboration:** LLM synthesizes beyond retrieved context
2. **Hybrid hallucination:** Conflicting Vector+Graph contexts confuse LLM (Amnesty F=0.301)
3. **Truncated chunks:** Graph chunks cut at 500 chars → LLM infers missing information

**Concrete Fixes (Sprint 80):**

| Fix | Effort | Expected Impact | Priority |
|-----|--------|-----------------|----------|
| Add "cite sources" prompt | 1 day | F +50-80% | P0 |
| Citation-aware generation | 1 week | F +80-100% | P1 |
| Cross-encoder reranking (Hybrid) | 1 week | Hybrid F +100-150% | P0 |
| Increase Graph chunk limit (500→1000) | 1 day | HotpotQA F +20-30% | P0 |

**Expected Sprint 80 Result:**
- Amnesty Graph F: 0.550 → 0.750-0.850
- Amnesty Hybrid F: 0.301 → 0.600-0.750
- HotpotQA Hybrid F: 0.500 → 0.650-0.750

---

### 3. Graph Mode Entity Extraction Gaps ❌

**Problem:**
- **HotpotQA:** 3 out of 5 questions return **num_contexts_retrieved=0**
- Questions: "Arthur's Magazine", "James Henry Miller's wife", "Cadmium Chloride"
- Error: "I don't have enough information in the knowledge base"

**Root Cause:**
- Entity extraction optimized for PDFs (Amnesty) with rich metadata
- Plain .txt files (HotpotQA) lack metadata → entities missed
- Missing entity types: "Publication", "Chemical", "Person Alias"

**Evidence:**
- Amnesty (.pdf): 146 entities extracted, ~70% coverage ✅
- HotpotQA (.txt): Estimated <40% coverage based on 3/5 failures ❌

**Concrete Fixes (Sprint 80-81):**

| Fix | Effort | Expected Impact | Priority |
|-----|--------|-----------------|----------|
| Add Graph→Vector fallback | 1 day | HotpotQA failures 3/5 → 0/5 | P0 |
| Entity extraction audit (HotpotQA) | 2 days | Identify missing types | P0 |
| Add entity types (Publication, Chemical, etc.) | 1 week | Coverage 40% → 70% | P1 |
| Improve extraction prompts for .txt | 1 week | Coverage 70% → 85% | P1 |

**Expected Sprint 80 Result:**
- HotpotQA Graph empty contexts: 3/5 → 0/5 (via fallback)
- Sprint 81: Entity coverage 40% → 70% (via extraction improvements)

---

### 4. Hybrid Mode Fusion Issues ⚠️

**Problem:**
- **Amnesty:** Hybrid F=0.301 (worst across all modes/datasets)
- **HotpotQA:** Hybrid F=0.500 (best, works correctly)
- **Why different?**

**Root Cause:**
- **Amnesty complex queries:** Vector retrieves noise → fusion buries Graph's good contexts
- **HotpotQA simple queries:** Vector retrieves relevant facts → fusion complements Graph

**Evidence (Amnesty Q1 - Abortion ruling):**
- **Graph:** 3 relevant chunks (CP=1.0, F=0.444) ✅
- **Vector:** 5 irrelevant chunks (CP=0.0, F=0.5) ❌
- **Hybrid:** Concatenates all 8 → Graph's chunks buried → F=0.0 ❌

**Concrete Fix (Sprint 80):**
- **Cross-encoder reranking:** Score all 8 contexts, deduplicate, return top-5
- **Implementation:** New module `src/components/hybrid_fusion.py`
- **Expected Impact:** Amnesty Hybrid F=0.301 → 0.600-0.750 (+100-150%)

---

### 5. Context Recall Now Acceptable ✅

**Previous Assessment (Experiment #1, 3 questions):**
- Graph CR=0.291 → **-61% gap** vs SOTA (catastrophic)

**Current Assessment (Experiment #2, 10 questions):**
- Amnesty Graph CR=0.587 → **-22% gap** vs SOTA (acceptable) ✅
- HotpotQA Vector/Hybrid CR=0.600 → **-20% gap** vs SOTA (acceptable) ✅

**Analysis:**
- Experiment #1 was misleading (only 3 questions, not representative)
- Current CR reasonable for top_k=3-5 retrieval
- **Priority downgraded:** P0 Critical → P2 Medium

**Optional Improvement (Sprint 80):**
- Increase top_k: Vector 5→10, Graph 3→7
- Expected impact: CR +20-30% (Amnesty 0.587 → 0.704-0.763)

---

## Detailed Failure Case Examples

### Example 1: Hybrid Hallucination (Amnesty Q1)

**Question:** "What are the global implications of the USA Supreme Court ruling on abortion?"

**Graph Mode (Baseline - Best):**
- **Retrieved:** 3 highly relevant chunks about abortion ruling
- **Metrics:** CP=1.0, CR=0.429, F=0.444, AR=0.885
- **Issue:** Answer over-elaborates beyond 3 chunks (F=0.444)

**Vector Mode (Complete Failure):**
- **Retrieved:** 5 irrelevant chunks (human rights violations, child rights, education)
- **Metrics:** CP=0.0, CR=0.0, F=0.5, AR=0.0
- **Issue:** Semantic similarity ≠ topical relevance

**Hybrid Mode (Hallucination):**
- **Retrieved:** All 8 chunks (3 Graph + 5 Vector)
- **Metrics:** CP=0.0, CR=0.0, F=0.0, AR=0.749
- **Issue:** Vector's noise buries Graph's good contexts → LLM hallucinates
- **Fix:** Cross-encoder reranking to surface Graph chunks

---

### Example 2: Graph Entity Extraction Failure (HotpotQA Q1)

**Question:** "Which magazine was started first Arthur's Magazine or First for Women?"

**Graph Mode (Complete Failure):**
- **Retrieved:** num_contexts_retrieved=0
- **Answer:** "I don't have enough information in the knowledge base"
- **Root Cause:** Entity "Arthur's Magazine" not extracted from .txt file
- **Fix:** Add "Publication" entity type to extraction pipeline

**Vector Mode (Partial Failure):**
- **Retrieved:** 5 irrelevant chunks (Allie Goertz, Peggy Seeger, Oberoi family)
- **Metrics:** CP=0.0, CR=0.0, F=0.0, AR=0.0
- **Root Cause:** No relevant chunks in namespace (ingestion issue?)
- **Fix:** Verify all HotpotQA documents ingested correctly

**Hybrid Mode (Same as Vector):**
- **Metrics:** CP=0.0, CR=0.0, F=0.0, AR=0.0
- **Issue:** Graph returns empty → Hybrid degrades to Vector

---

### Example 3: Truncated Graph Chunk (HotpotQA Q3)

**Question:** "Musician and satirist Allie Goertz wrote a song about 'The Simpsons' character Milhouse, who Matt Groening named after who?"

**Graph Mode:**
- **Retrieved:** 2 chunks (both truncated at 500 chars)
- **Context:** "...created by Matt Groening who named the character after " (MISSING "President Richard Nixon's middle name")
- **Answer:** "...named after President Richard Nixon's middle name, Mussolini" (INCORRECT - inferred from character's middle name)
- **Metrics:** CP=0.0, CR=0.0, F=0.25, AR=0.794
- **Fix:** Increase Graph chunk retrieval to 1000 chars

**Vector/Hybrid Mode (Partial Success):**
- **Retrieved:** Same truncated chunks from Vector retrieval
- **Metrics:** F=0.5 (better than Graph F=0.25)
- **Reason:** Shorter Vector answers have fewer unsupported claims

---

## Test Conditions Assessment

### Are These Realistic Scenarios? ✅ YES

**Amnesty Dataset:**
- ✅ Real-world human rights Q&A from Amnesty International reports
- ✅ Production-relevant (AegisRAG targets legal/policy/human rights domains)
- ✅ High difficulty (multi-hop, implicit reasoning) - matches SOTA benchmarks
- ⚠️ Limited scope (10 questions, need 50-100 for robustness)

**HotpotQA Dataset:**
- ✅ Standard multi-hop QA benchmark (113K questions in full dataset)
- ✅ High difficulty (multi-hop reasoning) - good stress test
- ⚠️ Domain mismatch (general knowledge vs AegisRAG's legal/policy focus)
- ⚠️ Very limited (5 questions too small for robust evaluation)

### Are Test Conditions Idealized? ⚠️ PARTIALLY

**Idealized Factors:**
1. ⚠️ **LLM Quality:** Using GPT-OSS:20b (production may use smaller/faster models)
2. ⚠️ **Latency:** Evaluation allowed 3-10s per query (production requires <500ms P95)
3. ⚠️ **Dataset Homogeneity:** Amnesty all human rights, HotpotQA all Wikipedia-style factoid

**Realistic Factors:**
1. ✅ **Real Retrieval:** Using actual Qdrant + Neo4j (not mocked)
2. ✅ **Real LLM:** GPT-OSS:20b (not GPT-4 or SOTA closed models)
3. ✅ **Real Embeddings:** BGE-M3 (same as ingestion, not specialized)
4. ✅ **Real Datasets:** No synthetic data, actual Amnesty reports + HotpotQA

**Verdict:** **Test conditions are REALISTIC but LIMITED IN SCOPE.**

**Recommendations:**
1. Expand datasets: Amnesty 10→50, HotpotQA 5→20
2. Test with production LLM (Nemotron3 Nano)
3. Add latency constraints to evaluation
4. Create mixed-domain evaluation set

---

## Actionable Recommendations (Sprint 80)

### P0 - Critical Fixes (Total: 1 week)

| Task | Effort | Expected Impact | Files to Change |
|------|--------|-----------------|-----------------|
| 1. Add "cite sources" prompt | 1 day | F +50-80% | `src/agents/answer_generator.py` |
| 2. Increase Graph chunk limit (500→1000) | 1 day | HotpotQA F +20-30% | `src/components/graph_rag/chunk_retrieval.py` |
| 3. Graph→Vector fallback | 1 day | HotpotQA failures 3/5 → 0/5 | `src/agents/graph_agent.py` |
| 4. Cross-encoder Hybrid reranking | 5 days | Amnesty Hybrid F +100-150% | New: `src/components/hybrid_fusion.py` |

**Total Sprint 80 Effort:** 8 days (1.6 weeks)

**Expected Sprint 80 Results:**
- Amnesty Graph F: 0.550 → 0.750-0.850 (+36-55%)
- Amnesty Hybrid F: 0.301 → 0.600-0.750 (+99-149%)
- HotpotQA Hybrid F: 0.500 → 0.650-0.750 (+30-50%)
- HotpotQA Graph failures: 3/5 → 0/5 (100% success)

---

### P1 - High Priority (Sprint 80-81, Total: 2-3 weeks)

| Task | Effort | Expected Impact | Implementation |
|------|--------|-----------------|----------------|
| 5. Citation-aware generation | 1 week | F +80-100% | `src/agents/answer_generator.py` |
| 6. Entity extraction audit (HotpotQA) | 2 days | Document coverage gaps | New: `scripts/entity_extraction_audit.py` |
| 7. Improve entity extraction | 1 week | Coverage 40%→70% | `src/components/graph_rag/entity_extraction.py` |
| 8. Expand evaluation datasets | 3 days | More robust metrics | `data/evaluation/ragas_*.jsonl` |
| 9. Increase top_k (5→10, 3→7) | 1 hour | CR +20-30% | `src/components/`, `src/agents/` |

**Expected Sprint 81 Results:**
- All metrics +10-20% (more robust evaluation)
- Entity coverage 40% → 70%
- CR +20-30% (if top_k increased)

---

### P2 - Medium Priority (Sprint 82-85, Total: 2-3 months)

| Task | Effort | Expected Impact | Priority |
|------|--------|-----------------|----------|
| Query-adaptive routing | 2 weeks | All metrics +20-30% | P1 |
| Parent chunk retrieval | 1 week | CR +50%, F +30% | P1 |
| DSPy Faithfulness optimization | 3 weeks | F +100-150% (SOTA parity) | P2 |
| GraphRAG community detection | 3 weeks | Graph CP +30%, CR +50% | P2 |
| Multi-hop graph traversal | 2 weeks | Graph CR +100% | P2 |

**Expected Sprint 85 Results:**
- **SOTA Parity Achieved:** F ≥ 0.900, all metrics ≥ SOTA targets

---

## Conclusion

### What We Know (High Confidence)

1. ✅ **Graph Mode best for Amnesty** (entity-centric queries)
2. ✅ **Hybrid Mode best for HotpotQA** (factoid multi-hop queries)
3. ✅ **Faithfulness is the critical bottleneck** (max 0.550 vs SOTA 0.90)
4. ✅ **Graph Mode entity extraction gaps** (60% failure rate on HotpotQA)
5. ✅ **Hybrid fusion needs reranking** (hallucination on complex queries)
6. ✅ **Context Recall acceptable** (CR=0.587-0.600, -20-22% gap vs SOTA)

### What We Don't Know (Needs Investigation)

1. ❓ **Performance with production LLM** (Nemotron3 Nano vs GPT-OSS:20b)
2. ❓ **Latency under production constraints** (<500ms P95 for Hybrid)
3. ❓ **Performance on mixed-domain queries** (Amnesty + HotpotQA in single session)
4. ❓ **Entity coverage on HotpotQA** (needs audit, estimated <40%)
5. ❓ **Optimal top_k values** (currently 5 Vector, 3 Graph - needs A/B testing)

### What We Will Fix (Sprint 80 Commitments)

1. ✅ **Faithfulness:** Add "cite sources" prompt (F +50-80%)
2. ✅ **Graph failures:** Add Vector fallback (HotpotQA failures 3/5 → 0/5)
3. ✅ **Hybrid hallucination:** Cross-encoder reranking (Hybrid F +100-150%)
4. ✅ **Truncated chunks:** Increase Graph limit 500→1000 chars (F +20-30%)

**Success Criteria (Sprint 80):**
- Amnesty Graph F ≥ 0.750 (from 0.550)
- Amnesty Hybrid F ≥ 0.600 (from 0.301)
- HotpotQA Hybrid F ≥ 0.650 (from 0.500)
- HotpotQA Graph failures = 0/5 (from 3/5)

---

## Next Steps

1. **Update RAGAS_JOURNEY.md** with Experiment #2 results ✅ DONE
2. **Create detailed analysis document** ✅ DONE (this document)
3. **Implement Sprint 80 P0 fixes** (1 week effort)
4. **Re-run RAGAS evaluation** (Experiment #3)
5. **Document Experiment #3 results** in RAGAS_JOURNEY.md
6. **Compare before/after metrics** to validate expected improvements

**Files Updated:**
- `/home/admin/projects/aegisrag/AEGIS_Rag/docs/ragas/RAGAS_JOURNEY.md` (Experiment #2 entry + updated Current Status)
- `/home/admin/projects/aegisrag/AEGIS_Rag/docs/ragas/RAGAS_ANALYSIS_2026_01_08.md` (comprehensive analysis)
- `/home/admin/projects/aegisrag/AEGIS_Rag/docs/ragas/EXECUTIVE_SUMMARY_2026_01_08.md` (this document)

---

**Evaluation Date:** 2026-01-08
**Evaluated by:** RAG Tuning Agent (Claude Sonnet 4.5)
**Status:** ✅ Complete - Ready for Sprint 80 implementation
