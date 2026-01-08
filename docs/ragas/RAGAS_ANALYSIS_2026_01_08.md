# RAGAS Evaluation Analysis & Recommendations
**Date:** 2026-01-08
**Datasets:** Amnesty QA (10 questions), HotpotQA (5 questions)
**RAGAS Version:** 0.4.2
**Embeddings:** BGE-M3 (1024-dim, consistent with ingestion)

---

## Executive Summary

The RAGAS evaluation reveals **domain-dependent performance characteristics** across AegisRAG's three retrieval modes (Vector, Graph, Hybrid), with **Faithfulness as the critical bottleneck** across all modes and datasets.

**Key Findings:**
1. **Graph Mode excels** on entity-centric datasets (Amnesty: CP=0.581, CR=0.587, F=0.550)
2. **Hybrid Mode excels** on factoid multi-hop datasets (HotpotQA: all metrics best)
3. **Faithfulness universally low** (max 0.550 vs SOTA 0.90 → 39% gap)
4. **Graph Mode fails** on 60% of HotpotQA questions (empty contexts due to entity extraction gaps)

**Production Recommendation:**
- **Amnesty-like datasets (human rights, legal, policy):** Use Graph Mode
- **HotpotQA-like datasets (general knowledge, factoid):** Use Hybrid Mode
- **Implement query-adaptive routing** to automatically select mode based on query characteristics

---

## 1. Bottleneck Analysis

### 1.1 Faithfulness (CRITICAL - P0)

**Problem:**
- **Amnesty Best:** F=0.550 (Graph) vs SOTA 0.90 → **-39% gap**
- **HotpotQA Best:** F=0.500 (Hybrid) vs SOTA 0.90 → **-44% gap**
- **All modes below 0.6** across both datasets

**Root Causes:**

1. **Answer Over-Elaboration:**
   - Graph Mode generates comprehensive, synthesis-heavy answers that **exceed retrieved context**
   - Example: Milhouse question (HotpotQA) - answer states "Mussolini" when ground truth is "President Richard Nixon" (partial answer from truncated graph chunk)
   - LLM extrapolates beyond sources when contexts are incomplete

2. **Hybrid Mode Hallucination (Amnesty):**
   - F=0.301 (worst across all modes/datasets)
   - **2 out of 10 questions have F=0.0** (complete hallucination)
   - **Hypothesis:** Conflicting Vector + Graph contexts confuse LLM, triggering hallucination

3. **Incomplete Context Chunks:**
   - **HotpotQA Graph chunks truncated** at 500 characters
   - Example: "...created by Matt Groening who named the character after " (missing "President Richard Nixon's middle name")
   - LLM fills gaps with incorrect inference (says "Mussolini" based on character's middle name)

**Evidence from Per-Sample Analysis:**

**Amnesty Dataset (10 questions):**
- **Q1 (Abortion ruling):** Graph F=0.444, Hybrid F=0.00 (hallucination)
- **Q3 (Private companies):** Graph F=0.25, Hybrid F=0.00 (hallucination)
- **Hybrid Mode:** 2 complete failures (F=0.0) vs Graph Mode 0 failures

**HotpotQA Dataset (5 questions):**
- **Q1 (Arthur's Magazine):** All modes F=0.0 (no relevant context retrieved)
- **Q2 (Oberoi family):** Vector F=0.25 (over-elaboration)
- **Q3 (Milhouse):** Vector/Hybrid F=0.5 (partial hallucination from truncated context)

**Concrete Recommendations:**

1. **Prompt Engineering (Quick Win - 1 day):**
   ```python
   # Add to answer generation prompt
   FAITHFULNESS_PROMPT = """
   CRITICAL: Only include information EXPLICITLY stated in the provided sources.
   If information is not in the sources, say "This information is not available."
   For EVERY claim, cite the source number in [brackets].
   DO NOT infer, extrapolate, or synthesize beyond what is written.
   """
   ```
   - **Expected Impact:** F +50-80% (based on SOTA prompt engineering studies)
   - **Implementation:** `src/agents/answer_generator.py` or LangGraph prompt templates
   - **Test:** Re-run RAGAS on same datasets, expect Amnesty F=0.550 → 0.825-0.990

2. **Citation-Aware Generation (Medium Win - 3-5 days):**
   - Force LLM to cite `[Source X]` for every sentence
   - RAGAS Faithfulness will validate citations against retrieved contexts
   - **Expected Impact:** F +80-100%
   - **Implementation:** Add citation verification layer in answer generation node

3. **Fix Graph Chunk Truncation (Critical for HotpotQA - 1 day):**
   - Current: Graph chunks truncated at 500 chars
   - **Fix:** Increase to 1000 chars OR retrieve full chunk when entity matched
   - **Implementation:** `src/components/graph_rag/chunk_retrieval.py`
   - **Expected Impact:** HotpotQA Graph F=0.250 → 0.500-0.600

4. **Hybrid Fusion Deconfliction (High Priority - 1 week):**
   - **Problem:** Vector + Graph contexts may contradict each other
   - **Solution:** Add conflict detection + resolution layer
   - **Implementation:**
     ```python
     def resolve_conflicts(vector_contexts, graph_contexts):
         # Use cross-encoder to score all contexts
         all_contexts = vector_contexts + graph_contexts
         scores = cross_encoder.predict([(query, ctx) for ctx in all_contexts])
         # Deduplicate + keep top-k by score
         return deduplicate_and_rank(all_contexts, scores, top_k=10)
     ```
   - **Expected Impact:** Amnesty Hybrid F=0.301 → 0.600-0.750

5. **DSPy Optimization (Long-term - 2-3 weeks):**
   - Optimize LLM prompts specifically for Faithfulness metric
   - Use RAGAS Faithfulness as reward signal during DSPy optimization
   - **Expected Impact:** F +100-150% (F=0.550 → 0.825-0.990)
   - **Implementation:** New module `src/optimization/dspy_optimizer.py`
   - **Note:** Feature 79.9 deferred to Sprint 80+

---

### 1.2 Graph Mode HotpotQA Failures (CRITICAL - P0)

**Problem:**
- **3 out of 5 questions** return empty contexts (num_contexts_retrieved=0)
- Questions: "Arthur's Magazine", "James Henry Miller's wife", "Cadmium Chloride"
- Error: "I don't have enough information in the knowledge base to answer this question"

**Root Cause:**
- **Entity extraction on .txt files (HotpotQA) missed key entities**
- Amnesty dataset (PDF) has richer metadata → better entity extraction
- HotpotQA dataset (plain .txt) has minimal metadata → entities missed

**Evidence:**
- **Successful question (Oberoi family):** Entity "The Oberoi family" extracted → graph retrieval works
- **Failed question (Arthur's Magazine):** Entity "Arthur's Magazine" NOT extracted → graph empty
- **Failed question (James Henry Miller):** Entity "James Henry Miller" NOT extracted (stage name "Ewan MacColl" used instead)

**Entity Extraction Coverage Analysis:**

**Amnesty Dataset (.pdf files):**
- 146 entities extracted
- 38 entity types
- Success rate: ~70% of relevant entities captured

**HotpotQA Dataset (.txt files):**
- Unknown entity count (needs audit)
- **Hypothesis:** <40% entity coverage based on 3/5 failures

**Concrete Recommendations:**

1. **Entity Extraction Audit (High Priority - 2-3 days):**
   ```bash
   # Run entity extraction analysis on HotpotQA
   poetry run python scripts/entity_extraction_audit.py \
     --dataset data/evaluation/ragas_hotpotqa_small.jsonl \
     --namespace ragas_eval_txt \
     --output data/evaluation/results/entity_coverage_hotpotqa.json
   ```
   - **Goal:** Identify missing entity types (e.g., "Magazine", "Chemical")
   - **Output:** Coverage report showing % of ground truth entities extracted

2. **Improve Entity Extraction Prompts (Medium Priority - 3-5 days):**
   - Current prompt may be optimized for legal/policy documents (Amnesty)
   - **Add domain-agnostic entity types:**
     ```python
     ENTITY_TYPES = [
         "Person", "Organization", "Location", "Date",
         "Product", "Event", "Concept", "Publication",  # Add these
         "Chemical", "Scientific Term", "Proper Noun"   # Add these
     ]
     ```
   - **Implementation:** `src/components/graph_rag/entity_extraction.py`
   - **Expected Impact:** HotpotQA Graph empty contexts 3/5 → 1/5

3. **Fallback to Vector Mode (Quick Win - 1 day):**
   - If Graph retrieval returns 0 contexts, fallback to Vector retrieval
   - **Implementation:**
     ```python
     def graph_query_with_fallback(query, namespace):
         graph_contexts = graph_retrieval(query, namespace)
         if len(graph_contexts) == 0:
             logger.warning(f"Graph retrieval empty, falling back to Vector")
             return vector_retrieval(query, namespace, top_k=5)
         return graph_contexts
     ```
   - **Expected Impact:** HotpotQA Graph failures 3/5 → 0/5 (but with Vector-level quality)

4. **Hybrid Mode as Default for HotpotQA (Quick Win - Already Implemented):**
   - Hybrid Mode already succeeds on all 5 HotpotQA questions
   - **Reason:** Vector retrieval compensates for Graph failures
   - **Action:** Document query routing logic: "Use Hybrid for general knowledge queries"

---

### 1.3 Hybrid Mode Inconsistency (HIGH PRIORITY - P1)

**Problem:**
- **Amnesty:** AR best (0.781), but F worst (0.301) - hallucination
- **HotpotQA:** All metrics best (CP/CR/F/AR) - proper fusion
- **Why different?**

**Root Cause Analysis:**

1. **Query Complexity Mismatch:**
   - **Amnesty queries:** Complex, multi-faceted (e.g., "global implications of abortion ruling")
   - **HotpotQA queries:** Simpler, factoid (e.g., "What city is the head office in?")
   - **Hypothesis:** Complex queries → Vector retrieves tangentially related noise → fusion dilutes Graph's good contexts

2. **Evidence from Per-Sample Breakdown:**

   **Amnesty Q1 (Abortion ruling):**
   - **Graph:** 3 highly relevant chunks (CP=1.0, F=0.444)
   - **Vector:** 5 irrelevant chunks about human rights violations, child rights (CP=0.0)
   - **Hybrid:** Concatenates all 8 → Graph's good contexts **buried** → F=0.0 (hallucination)

   **HotpotQA Q2 (Oberoi family):**
   - **Graph:** 2 duplicate chunks (same text) (CP=1.0, F=1.0)
   - **Vector:** 4 chunks (2 irrelevant Allie Goertz/Peggy Seeger, 2 relevant Oberoi) (CP=0.33)
   - **Hybrid:** 4 chunks total → Vector's Oberoi chunks complement Graph → F=1.0 (success)

3. **Fusion Mechanism Analysis:**
   - **Current:** Simple concatenation (Vector top-5 + Graph top-3 = 8 contexts)
   - **No deduplication:** HotpotQA Q2 shows duplicate chunks (Graph returns same chunk twice)
   - **No relevance-based ranking:** Irrelevant Vector chunks listed first → LLM focuses on noise

**Concrete Recommendations:**

1. **Cross-Encoder Reranking After Fusion (High Priority - 1 week):**
   ```python
   from sentence_transformers import CrossEncoder

   def hybrid_fusion_with_reranking(query, vector_contexts, graph_contexts, top_k=10):
       # Concatenate all contexts
       all_contexts = vector_contexts + graph_contexts

       # Deduplicate by text similarity
       unique_contexts = deduplicate_by_similarity(all_contexts, threshold=0.95)

       # Rerank with cross-encoder
       cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
       pairs = [(query, ctx['text']) for ctx in unique_contexts]
       scores = cross_encoder.predict(pairs)

       # Sort by score and return top-k
       ranked = sorted(zip(unique_contexts, scores), key=lambda x: x[1], reverse=True)
       return [ctx for ctx, score in ranked[:top_k]]
   ```
   - **Expected Impact:**
     - Amnesty Hybrid F=0.301 → 0.600-0.750 (+100-150%)
     - Amnesty Hybrid CP=0.400 → 0.650-0.800 (+63-100%)
   - **Implementation:** `src/components/hybrid_fusion.py` (create new module)
   - **Latency Impact:** +50-100ms per query (acceptable)

2. **Query-Adaptive Routing (Medium Priority - 2 weeks):**
   - Classify queries as "Entity-centric" vs "Factoid" vs "Complex reasoning"
   - **Entity-centric → Graph Mode** (Amnesty-like)
   - **Factoid → Hybrid Mode** (HotpotQA-like)
   - **Complex reasoning → Hybrid with reranking**
   - **Implementation:**
     ```python
     def classify_query(query):
         # Use LLM to classify
         prompt = f"Is this query entity-centric, factoid, or complex reasoning? Query: {query}"
         classification = llm(prompt)
         return classification  # "entity" | "factoid" | "complex"

     def adaptive_retrieval(query, namespace):
         query_type = classify_query(query)
         if query_type == "entity":
             return graph_retrieval(query, namespace)
         elif query_type == "factoid":
             return hybrid_retrieval_with_reranking(query, namespace)
         else:  # complex
             return hybrid_retrieval_with_reranking(query, namespace, top_k=15)
     ```
   - **Expected Impact:** Overall metrics +20-30% across all datasets

---

### 1.4 Context Recall - Now Acceptable (Updated Assessment)

**Previous Status (Experiment #1, 3 questions):**
- Graph CR=0.291 (71% of relevant context missing)

**Current Status (Experiment #2, 10 questions):**
- **Amnesty Graph CR=0.587** (only 41% missing) ✅
- **HotpotQA Vector/Hybrid CR=0.600** (only 40% missing) ✅

**Analysis:**
- **Experiment #1 was misleading** - only 3 questions, not representative
- **Current CR is reasonable** for top_k=3-5 retrieval
- **Still below SOTA (0.75)** but gap reduced to 22% (was 61%)

**Updated Priority:**
- **Previous:** P0 Critical (CR=0.291 catastrophic)
- **Current:** P2 Medium (CR=0.587 acceptable, focus on F instead)

**Recommendations:**

1. **Increase top_k (Low Priority - Quick Win - 1 hour):**
   - Current: Vector top_k=5, Graph top_k=3
   - **Increase to:** Vector top_k=10, Graph top_k=7
   - **Expected Impact:** CR +20-30% (Amnesty 0.587 → 0.704-0.763)
   - **Trade-off:** May degrade CP (more noise)
   - **Mitigation:** Combine with cross-encoder reranking

2. **Parent Chunk Retrieval (Medium Priority - 1 week):**
   - **Current:** Retrieve chunk, return same chunk
   - **Proposed:** Retrieve sentence-level chunk, return parent section
   - **Expected Impact:** CR +50%, F +30%
   - **Implementation:** `src/components/vector_search/chunk_retrieval.py`

---

## 2. Test Conditions Assessment

### 2.1 Are These Realistic Test Scenarios?

**Amnesty Dataset:**
- ✅ **Realistic:** Real-world human rights Q&A from Amnesty International reports
- ✅ **Production-relevant:** AegisRAG targets legal/policy/human rights domains
- ⚠️ **Limited:** Only 10 questions, may not capture edge cases
- ✅ **Difficulty:** High (multi-hop, implicit reasoning) - matches SOTA benchmarks

**HotpotQA Dataset:**
- ✅ **Realistic:** Standard multi-hop QA benchmark (113K questions in full dataset)
- ⚠️ **Domain mismatch:** General knowledge (Wikipedia) vs AegisRAG's legal/policy focus
- ⚠️ **Limited:** Only 5 questions from full dataset
- ✅ **Difficulty:** High (multi-hop reasoning) - good stress test

**Dataset Quality Issues:**

1. **Small Sample Size:**
   - Amnesty: 10 questions (better, but still small)
   - HotpotQA: 5 questions (too small for robust evaluation)
   - **Recommendation:** Expand to 50-100 questions per dataset

2. **Ground Truth Quality (Amnesty):**
   - Some questions have multiple valid answers (e.g., "global implications" can be interpreted many ways)
   - RAGAS Context Recall may penalize valid alternative answers
   - **Mitigation:** Use multi-reference ground truths

3. **Entity Extraction Mismatch (HotpotQA):**
   - Dataset designed for dense retrieval, not graph RAG
   - Many entities not extractable from plain text (e.g., "Arthur's Magazine")
   - **Recommendation:** Add metadata-rich datasets (e.g., legal cases with structured entities)

### 2.2 Are Test Conditions Idealized?

**Factors Suggesting Idealized Conditions:**

1. **LLM Quality:**
   - Using GPT-OSS:20b (Ollama) for both retrieval and answer generation
   - Production may use smaller/faster models → metrics may degrade
   - **Recommendation:** Test with Nemotron3 Nano (production model)

2. **Retrieval Speed:**
   - Evaluation allowed 3-10s per query (acceptable for offline testing)
   - Production requirement: <500ms P95 for Hybrid queries
   - **Recommendation:** Add latency constraints to RAGAS evaluation

3. **Dataset Homogeneity:**
   - Amnesty: All human rights domain → Graph Mode optimized for this
   - HotpotQA: All Wikipedia-style factoid → Vector Mode optimized for this
   - **Production reality:** Mixed domains, unpredictable queries
   - **Recommendation:** Create mixed-domain evaluation set

**Factors Suggesting Realistic Conditions:**

1. ✅ **Real Retrieval System:** Using actual Qdrant + Neo4j (not mocked)
2. ✅ **Real LLM:** GPT-OSS:20b (not GPT-4 or other SOTA closed models)
3. ✅ **Real Embeddings:** BGE-M3 (same as ingestion, not specialized)
4. ✅ **Real Datasets:** No synthetic/curated data, actual Amnesty reports + HotpotQA

**Verdict:** **Test conditions are REALISTIC but LIMITED IN SCOPE.**

---

## 3. Actionable Next Steps for Sprint 80+

### Sprint 80 (Immediate - 2 weeks)

**P0 - Critical Fixes:**

1. **Fix Faithfulness via Prompt Engineering (2 days):**
   - Add "cite sources" prompt to answer generator
   - Test on Amnesty dataset
   - **Success Metric:** F ≥ 0.750 (from 0.550)

2. **Fix Graph Mode HotpotQA Failures (3 days):**
   - Add fallback to Vector when Graph returns empty contexts
   - Run entity extraction audit on HotpotQA
   - **Success Metric:** 0/5 empty context failures (from 3/5)

3. **Hybrid Fusion Cross-Encoder Reranking (5 days):**
   - Implement deduplication + cross-encoder reranking
   - Test on Amnesty dataset
   - **Success Metric:** Amnesty Hybrid F ≥ 0.600 (from 0.301)

**P1 - High Priority:**

4. **Increase top_k Retrieval (1 day):**
   - Vector top_k=5 → 10, Graph top_k=3 → 7
   - Re-run RAGAS evaluation
   - **Success Metric:** CR ≥ 0.700 (from 0.587)

5. **Expand Evaluation Datasets (3 days):**
   - Amnesty: 10 → 50 questions
   - HotpotQA: 5 → 20 questions
   - **Success Metric:** More statistically robust metrics

**Deliverables:**
- Updated RAGAS evaluation results with fixes
- RAGAS_JOURNEY.md Experiment #3 entry
- ADR for Hybrid Fusion Reranking (if major architectural change)

---

### Sprint 81-82 (Medium-term - 4 weeks)

**P1 - Query-Adaptive Routing:**

1. **Implement Query Classifier (1 week):**
   - LLM-based classification: "entity" | "factoid" | "complex"
   - Route to Graph | Hybrid | Hybrid with extended context
   - **Success Metric:** +20-30% overall metrics

2. **Parent Chunk Retrieval (1 week):**
   - Retrieve sentence-level chunks, return parent sections
   - **Success Metric:** CR +50%, F +30%

3. **Entity Extraction Improvements (2 weeks):**
   - Add domain-agnostic entity types
   - Improve extraction prompts for .txt files
   - **Success Metric:** HotpotQA entity coverage ≥70%

**Deliverables:**
- Query-adaptive routing API integration
- Parent chunk retrieval implementation
- Entity extraction evaluation report

---

### Sprint 83+ (Long-term - 6+ weeks)

**P2 - DSPy Optimization:**

1. **DSPy for Faithfulness (3 weeks):**
   - Optimize prompts using RAGAS Faithfulness as reward
   - **Success Metric:** F ≥ 0.900 (SOTA parity)

2. **GraphRAG Community Detection (3 weeks):**
   - Implement Leiden algorithm for hierarchical summaries
   - **Success Metric:** Graph CP +30%, CR +50%

3. **Multi-Hop Graph Traversal (2 weeks):**
   - Increase graph expansion from 1-3 hops to 2-5 hops
   - **Success Metric:** Graph CR +100%

**Deliverables:**
- DSPy optimization module
- GraphRAG community detection integration
- SOTA performance parity report

---

## 4. Per-Sample Failure Case Analysis

### 4.1 Amnesty Dataset - Complete Failures

**Q1: "What are the global implications of the USA Supreme Court ruling on abortion?"**

**Vector Mode:**
- **CP=0.0, CR=0.0, F=0.5, AR=0.0** (complete retrieval failure)
- **Retrieved:** 5 irrelevant chunks about human rights violations, child rights, education
- **Root Cause:** Semantic similarity ≠ topical relevance (query about "abortion ruling" retrieved "rights violations" due to overlapping "rights" keyword)
- **Fix:** Query expansion with specific terms ("Supreme Court", "abortion", "Roe v Wade")

**Hybrid Mode:**
- **CP=0.0, CR=0.0, F=0.0, AR=0.749** (hallucination despite decent relevancy)
- **Retrieved:** Same 5 irrelevant Vector chunks + 3 Graph chunks (Graph's good chunks buried)
- **Root Cause:** Fusion mechanism didn't prioritize Graph's relevant chunks
- **Fix:** Cross-encoder reranking to surface Graph chunks

**Graph Mode (Best):**
- **CP=1.0, CR=0.429, F=0.444, AR=0.885** (only partial success)
- **Retrieved:** 3 highly relevant chunks about abortion ruling
- **Root Cause (F=0.444):** Answer over-elaborates beyond 3 chunks
- **Fix:** "Cite sources only" prompt

---

**Q3: "Which private companies in the Americas are the largest GHG emitters?"**

**All Modes:**
- **CP=0.0, CR=0.0, F=0.0-0.25, AR=1.0** (all fail equally)
- **Retrieved:** All modes retrieved irrelevant chunks (Russian invasion, human rights)
- **Root Cause:** Query too specific ("private companies in Americas") + sparse dataset (only 10 questions, may not have relevant chunks)
- **Fix:** Increase dataset size, add more climate-related documents

---

### 4.2 HotpotQA Dataset - Graph Mode Empty Context Failures

**Q1: "Which magazine was started first Arthur's Magazine or First for Women?"**

**Graph Mode:**
- **num_contexts_retrieved=0** (complete failure)
- **Answer:** "I don't have enough information in the knowledge base to answer this question."
- **Root Cause:** Entity "Arthur's Magazine" not extracted from .txt file
- **Fix:** Improve entity extraction to recognize publication names

**Vector/Hybrid Mode (Partial Success):**
- **Retrieved:** 5 chunks (all irrelevant - Allie Goertz, Peggy Seeger, Oberoi family)
- **Root Cause:** No chunk about magazines in namespace (ingestion issue?)
- **Fix:** Verify all HotpotQA documents ingested correctly

---

**Q4: "What nationality was James Henry Miller's wife?"**

**Graph Mode:**
- **num_contexts_retrieved=0** (complete failure)
- **Answer:** "I don't have enough information..."
- **Root Cause:** Entity "James Henry Miller" not extracted (stage name "Ewan MacColl" used instead)
- **Fix:** Improve entity extraction to capture aliases/alternate names

**Vector Mode (Success):**
- **CP=1.0, CR=1.0, F=1.0, AR=0.473** (perfect retrieval, but low relevancy)
- **Retrieved:** 2 chunks about Peggy Seeger (American) married to Ewan MacColl (James Henry Miller)
- **Answer:** Over-elaborate (includes full biographical details instead of just "American")
- **Fix:** Shorten answer to factoid response

---

**Q5: "Cadmium Chloride is slightly soluble in this chemical, it is also called what?"**

**Graph Mode:**
- **num_contexts_retrieved=0** (complete failure)
- **Root Cause:** Entity "Cadmium Chloride" not extracted (chemical entity type missing)
- **Fix:** Add "Chemical" to entity types

**All Modes:**
- **CP=0.0, CR=0.0, F=0.0, AR=0.343** (no relevant context in any mode)
- **Retrieved:** Allie Goertz, Peggy Seeger, Oberoi family (irrelevant)
- **Root Cause:** Chemistry document not ingested? Or wrong namespace?
- **Fix:** Verify data/uploads contains hotpot_000004.txt (ethanol document)

---

### 4.3 HotpotQA Dataset - Partial Failures

**Q3: "Musician and satirist Allie Goertz wrote a song about the 'The Simpsons' character Milhouse, who Matt Groening named after who?"**

**Vector/Hybrid Mode:**
- **CP≈0.75, CR=1.0, F=0.5, AR=0.709-0.789** (partial success)
- **Answer:** "...named after President Richard Nixon's middle name, Mussolini" (INCORRECT - should be "President Richard Nixon")
- **Retrieved Context:** "...created by Matt Groening who named the character after " (TRUNCATED at 500 chars)
- **Root Cause:** Graph chunk truncation → LLM infers "Mussolini" from character's middle name "Mussolini van Houten"
- **Fix:** Increase Graph chunk retrieval to 1000 chars

**Graph Mode:**
- **F=0.25** (worse than Vector/Hybrid F=0.5)
- **Same truncation issue** but Graph's longer, more elaborate answer has more unsupported claims
- **Fix:** Same as above + "cite sources" prompt

---

## 5. Summary of Concrete Recommendations

### Quick Wins (1-3 days each, total 1 week)

| Recommendation | Priority | Effort | Expected Impact | File(s) to Change |
|----------------|----------|--------|-----------------|-------------------|
| Prompt: "Cite sources only" | P0 | 1 day | F +50-80% | `src/agents/answer_generator.py` |
| Graph fallback to Vector | P0 | 1 day | HotpotQA failures 3/5 → 0/5 | `src/agents/graph_agent.py` |
| Increase top_k (5→10, 3→7) | P1 | 1 hour | CR +20-30% | `src/components/vector_search/`, `src/agents/graph.py` |
| Fix Graph chunk truncation | P0 | 1 day | HotpotQA F +20-30% | `src/components/graph_rag/chunk_retrieval.py` |

**Total Quick Wins:** ~4 days, expected to improve F from 0.550 → 0.750-0.850

---

### Medium Wins (1-2 weeks each, total 1 month)

| Recommendation | Priority | Effort | Expected Impact | Implementation |
|----------------|----------|--------|-----------------|----------------|
| Cross-encoder reranking | P0 | 1 week | Hybrid F +100-150% | New module `src/components/hybrid_fusion.py` |
| Citation-aware generation | P1 | 1 week | F +80-100% | `src/agents/answer_generator.py` |
| Entity extraction audit | P0 | 3 days | Document coverage gaps | New script `scripts/entity_extraction_audit.py` |
| Improve entity extraction | P1 | 1 week | HotpotQA empty contexts 3/5 → 1/5 | `src/components/graph_rag/entity_extraction.py` |
| Expand evaluation datasets | P1 | 3 days | More robust metrics | `data/evaluation/ragas_*.jsonl` |

**Total Medium Wins:** ~1 month, expected to achieve F ≥ 0.850, close Faithfulness gap to <10%

---

### Long-term Wins (2-6 weeks each, total 3 months)

| Recommendation | Priority | Effort | Expected Impact | Implementation |
|----------------|----------|--------|-----------------|----------------|
| Query-adaptive routing | P1 | 2 weeks | All metrics +20-30% | `src/agents/coordinator/router.py` |
| Parent chunk retrieval | P1 | 1 week | CR +50%, F +30% | `src/components/vector_search/chunk_retrieval.py` |
| DSPy optimization | P2 | 3 weeks | F +100-150% (SOTA parity) | New module `src/optimization/dspy_optimizer.py` |
| GraphRAG communities | P2 | 3 weeks | Graph CP +30%, CR +50% | `src/components/graph_rag/community_detection.py` |
| Multi-hop traversal | P2 | 2 weeks | Graph CR +100% | `src/components/graph_rag/traversal.py` |

**Total Long-term Wins:** ~3 months, expected to achieve SOTA parity (F ≥ 0.900, all metrics ≥ SOTA targets)

---

## 6. Conclusion

The RAGAS evaluation provides **valid, actionable insights** despite limited sample sizes. Key takeaways:

1. **Faithfulness is the critical bottleneck** - addressable via prompt engineering (quick wins) and DSPy optimization (long-term)
2. **Domain-dependent performance** - Graph excels on Amnesty (entity-centric), Hybrid excels on HotpotQA (factoid multi-hop)
3. **Graph Mode entity extraction gaps** - 60% failure rate on HotpotQA due to missing entity types
4. **Hybrid Mode fusion issues** - naive concatenation causes hallucination on complex queries (Amnesty)

**Recommended Sprint 80 Focus:**
1. **Quick wins:** Prompt engineering, Graph fallback, chunk truncation fix (4 days total)
2. **High-impact fix:** Cross-encoder reranking for Hybrid fusion (1 week)
3. **Expand evaluation:** 10 → 50 Amnesty, 5 → 20 HotpotQA (3 days)

**Expected Sprint 80 Results:**
- Amnesty Graph F: 0.550 → 0.750-0.850 (+36-55%)
- HotpotQA Graph failures: 3/5 → 0/5 (100% success)
- Amnesty Hybrid F: 0.301 → 0.600-0.750 (+99-149%)

**Path to SOTA Parity (Sprint 85, Q2 2026):**
- Sprint 80-82: Quick + Medium wins → F ≥ 0.850
- Sprint 83-85: DSPy + GraphRAG communities → F ≥ 0.900, all metrics SOTA

---

**Next Action:** Update RAGAS_JOURNEY.md with Experiment #3 (Sprint 80 fixes) and track progress towards SOTA targets.
