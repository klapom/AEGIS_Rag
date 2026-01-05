# Sprint 75: RAGAS Evaluation & RAG Quality Optimization

**Sprint Start:** 2026-01-04
**Sprint End:** 2026-01-18 (2 weeks)
**Total Story Points:** 34 SP

---

## Sprint Goals

1. 🧪 **Execute RAGAS Evaluation** - Run comprehensive quality assessment
2. 📊 **Retrieval Method Comparison** - Empirical BM25 vs Vector vs Hybrid analysis
3. 🔍 **RAG Tuning Research** - Industry best practices and optimization techniques
4. 📈 **Quality Improvement Plan** - Data-driven recommendations based on results

---

## Sprint Context

Sprint 74 established the RAGAS evaluation framework and retrieval comparison infrastructure. Sprint 75 focuses on **execution and analysis**:

- Run RAGAS tests on 20-question AEGIS dataset
- Compare retrieval methods on 10-question comparison dataset
- Research state-of-the-art RAG optimization techniques
- Analyze results and create actionable improvement plan

**Expected Outcomes:**
- RAGAS baseline metrics established
- Clear understanding of retrieval method performance
- Documented optimization opportunities
- Prioritized improvement backlog for Sprint 76+

---

## Sprint Features

### Feature 75.1: RAGAS Baseline Evaluation (13 SP)

**Epic:** User Journey Step 7 - RAGAS Benchmark
**Priority:** P0 (Critical)

**Context:**
Execute comprehensive RAGAS evaluation to establish quality baselines for AEGIS RAG system. This provides objective metrics for:
- Context Precision: Are retrieved contexts relevant?
- Context Recall: Do we retrieve all needed information?
- Faithfulness: Are answers grounded in contexts (no hallucination)?
- Answer Relevancy: Do answers address the questions?

**Prerequisites:**
- ✅ Backend services running (Qdrant, Neo4j, Redis, Ollama)
- ✅ RAGAS dataset created (20 questions)
- ✅ RAGAS pytest tests implemented
- ⚠️ Evaluation dependencies installed: `poetry install --with evaluation`

**Tasks:**

#### Task 75.1.1: Run RAGAS Quick Smoke Test (2 SP)

**Command:**
```bash
pytest tests/ragas/test_ragas_integration.py::test_ragas_quick_smoke -m ragas_quick -v
```

**Purpose:**
- Validate RAGAS evaluation pipeline works end-to-end
- Test with 5 samples (1-2 minutes runtime)
- Verify all 4 metrics are computed
- Ensure no errors before full evaluation

**Acceptance Criteria:**
- Test passes (5/5 samples evaluated)
- All 4 RAGAS metrics > 0.5
- No errors or timeouts
- Results logged to console

**Expected Output:**
```python
ragas_quick_smoke_results:
  context_precision: 0.75
  context_recall: 0.68
  faithfulness: 0.92
  answer_relevancy: 0.81
  duration_seconds: 87.5
```

---

#### Task 75.1.2: Run Full RAGAS Evaluation (8 SP)

**Commands:**
```bash
# Context Precision (primary metric)
pytest tests/ragas/test_ragas_integration.py::test_ragas_context_precision -m ragas_slow -v

# Context Recall
pytest tests/ragas/test_ragas_integration.py::test_ragas_context_recall -m ragas_slow -v

# Faithfulness (hallucination detection)
pytest tests/ragas/test_ragas_integration.py::test_ragas_faithfulness -m ragas_slow -v

# Answer Relevancy
pytest tests/ragas/test_ragas_integration.py::test_ragas_answer_relevancy -m ragas_slow -v
```

**Purpose:**
- Evaluate all 20 questions in AEGIS dataset
- Generate comprehensive quality metrics
- Create per-intent breakdown (factual, exploratory, summary, multi-hop)
- Save results for regression tracking

**Acceptance Criteria:**
- All tests pass with 20/20 samples evaluated
- Overall metrics meet targets:
  - Context Precision > 0.75
  - Context Recall > 0.70
  - Faithfulness > 0.90
  - Answer Relevancy > 0.80
- Results saved to `reports/ragas_*.json`
- Per-intent metrics computed

**Expected Runtime:** 20-40 minutes (depends on Ollama speed)

**Expected Output Files:**
- `reports/ragas_context_precision.json`
- `reports/ragas_context_recall.json`
- `reports/ragas_faithfulness.json`
- `reports/ragas_answer_relevancy.json`

---

#### Task 75.1.3: Analyze RAGAS Results (3 SP)

**Analysis Questions:**
1. **Which metrics are below targets?**
   - If Context Precision < 0.75: Retrieval returning irrelevant contexts
   - If Context Recall < 0.70: Retrieval missing important information
   - If Faithfulness < 0.90: LLM hallucinating facts not in contexts
   - If Answer Relevancy < 0.80: LLM not addressing questions properly

2. **Which intent types perform worst?**
   - Factual: Should have high precision (specific facts)
   - Exploratory: May have lower recall (broad topics)
   - Summary: Should have high faithfulness (no creative additions)
   - Multi-hop: Most challenging (complex reasoning)

3. **What patterns emerge?**
   - German vs English questions
   - Short vs long questions
   - Domain-specific questions
   - Question complexity correlation with metrics

**Deliverables:**
- `docs/sprints/SPRINT_75_RAGAS_ANALYSIS.md`
- Screenshots of test output
- Metric breakdown tables
- Identified weak areas

**Acceptance Criteria:**
- Comprehensive analysis document created
- All 4 metrics analyzed with examples
- Per-intent breakdown interpreted
- Clear recommendations for improvement

---

### Feature 75.2: Retrieval Method Comparison (13 SP)

**Epic:** User Journey Step 7 - RAGAS Benchmark
**Priority:** P0 (Critical)

**Context:**
Empirically validate that Hybrid retrieval (Vector + BM25 RRF fusion) performs better than pure BM25 or pure Vector search. This informs:
- Default retrieval method recommendation
- User guidance in Settings UI
- Future optimization priorities

**Prerequisites:**
- ✅ Retrieval comparison dataset created (10 questions)
- ✅ Retrieval comparison tests implemented
- ✅ RetrievalMethodEvaluator class ready

**Tasks:**

#### Task 75.2.1: Run Retrieval Comparison Smoke Test (2 SP)

**Command:**
```bash
pytest tests/ragas/test_retrieval_comparison.py::test_retrieval_method_smoke_test -m ragas_quick -v
```

**Purpose:**
- Validate all 3 retrieval methods work
- Test with 3 samples (5-10 minutes)
- Ensure no errors before full comparison

**Acceptance Criteria:**
- All 3 evaluators (BM25, Vector, Hybrid) complete successfully
- 3/3 samples evaluated per method
- All metrics > 0 (not NaN)
- No errors or timeouts

---

#### Task 75.2.2: Run Full Retrieval Comparison (8 SP)

**Commands:**
```bash
# Full comparison across all 10 queries
pytest tests/ragas/test_retrieval_comparison.py::test_bm25_vs_vector_vs_hybrid_full_comparison -m ragas_slow -v

# BM25 excels on keyword queries (3 queries)
pytest tests/ragas/test_retrieval_comparison.py::test_bm25_excels_on_keyword_queries -m ragas_quick -v

# Vector excels on semantic queries (3 queries)
pytest tests/ragas/test_retrieval_comparison.py::test_vector_excels_on_semantic_queries -m ragas_quick -v

# Hybrid excels on complex queries (4 queries)
pytest tests/ragas/test_retrieval_comparison.py::test_hybrid_excels_on_complex_queries -m ragas_quick -v
```

**Purpose:**
- Compare BM25, Vector, and Hybrid on all 10 test queries
- Validate expected_best_method predictions
- Generate comparison metrics
- Save results for analysis

**Acceptance Criteria:**
- All comparisons complete (10 queries × 3 methods = 30 evaluations)
- Results saved to:
  - `reports/ragas_bm25_only.json`
  - `reports/ragas_vector_only.json`
  - `reports/ragas_hybrid.json`
- Hybrid performs competitively overall
- BM25 wins on keyword queries
- Vector wins on semantic queries

**Expected Runtime:** 30-60 minutes

---

#### Task 75.2.3: Analyze Retrieval Comparison Results (3 SP)

**Analysis Questions:**
1. **Does Hybrid outperform pure methods overall?**
   - Compare average Context Precision across all 10 queries
   - Compare average Context Recall across all 10 queries
   - Is the difference statistically significant?

2. **Are method specializations validated?**
   - BM25 best on queries 1-3 (keyword: "BGE-M3", "port 6333", "ADR-024")?
   - Vector best on queries 4-6 (semantic concepts)?
   - Hybrid best on queries 7-10 (complex multi-faceted)?

3. **What are the failure modes?**
   - When does BM25 fail completely?
   - When does Vector fail completely?
   - When does Hybrid underperform?

**Deliverables:**
- `docs/sprints/SPRINT_75_RETRIEVAL_COMPARISON.md`
- Comparison tables (Context Precision, Recall by method)
- Visualizations (if possible with matplotlib)
- Recommendations for default method

**Acceptance Criteria:**
- Comprehensive comparison analysis created
- All 3 methods analyzed with examples
- Query-type breakdown documented
- Clear recommendation for Settings UI default

---

### Feature 75.3: RAG Optimization Research & Recommendations (8 SP)

**Epic:** Quality Improvement
**Priority:** P1 (High)

**Context:**
Research state-of-the-art RAG optimization techniques to improve RAGAS metrics. Focus on practical, implementable improvements for AEGIS RAG.

**Tasks:**

#### Task 75.3.1: Online Research - RAG Tuning Best Practices (3 SP)

**Research Topics:**
1. **Chunking Optimization**
   - Optimal chunk sizes for different domains
   - Overlap strategies
   - Semantic vs fixed-size chunking
   - Section-aware chunking improvements

2. **Embedding Quality**
   - BGE-M3 fine-tuning for domain
   - Alternative embedding models (E5, Jina, Cohere)
   - Query vs document embedding optimization
   - Metadata-enhanced embeddings

3. **Retrieval Tuning**
   - BM25 parameter tuning (k1, b)
   - RRF weight optimization
   - Top-k selection strategies
   - Query rewriting techniques

4. **Reranking Improvements**
   - Cross-encoder model selection
   - Domain-specific reranker training
   - Multi-stage reranking
   - Diversity-aware reranking

5. **Context Optimization**
   - Context compression techniques
   - Deduplication strategies
   - Context ordering/prioritization
   - Window expansion for better recall

6. **LLM Prompt Engineering**
   - RAG-specific prompts
   - Citation enforcement
   - Hallucination reduction techniques
   - Answer structuring

**Sources to Check:**
- arXiv papers (2024-2025)
- Pinecone/Weaviate/Qdrant blogs
- LangChain/LlamaIndex documentation
- Reddit r/LocalLLaMA, r/MachineLearning
- Industry case studies (Anthropic, OpenAI, Google)

**Deliverables:**
- `docs/sprints/SPRINT_75_RAG_TUNING_RESEARCH.md`
- Categorized list of techniques
- Applicability to AEGIS RAG (Easy/Medium/Hard)
- Expected impact (Low/Medium/High)

**Acceptance Criteria:**
- 10+ optimization techniques documented
- Each technique has:
  - Description
  - Implementation difficulty
  - Expected impact
  - References/sources
- Prioritized by ROI (impact/effort)

---

#### Task 75.3.2: Improvement Recommendations (3 SP)

**Based on RAGAS results + research, create prioritized improvement plan:**

**Format:**
```markdown
## Improvement Recommendations (Sprint 76+)

### High Priority (Quick Wins)
1. **Issue:** Context Precision < 0.75 on exploratory questions
   **Root Cause:** Retrieval returns too many tangentially related contexts
   **Solution:** Increase similarity threshold, tune RRF weights
   **Effort:** 3 SP
   **Expected Gain:** +10% Context Precision

2. **Issue:** Faithfulness < 0.90 on summary questions
   **Root Cause:** LLM adds creative interpretations
   **Solution:** Stricter prompts, add "only use provided context" instruction
   **Effort:** 2 SP
   **Expected Gain:** +8% Faithfulness

### Medium Priority
...

### Low Priority (Long-term)
...
```

**Deliverables:**
- `docs/sprints/SPRINT_75_IMPROVEMENT_PLAN.md`
- Prioritized backlog items for Sprint 76+
- Effort estimates (SP)
- Expected metric improvements

**Acceptance Criteria:**
- 5+ concrete improvement recommendations
- Each recommendation has:
  - Issue identified
  - Root cause analysis
  - Proposed solution
  - Effort estimate
  - Expected metric gain
- Prioritized by ROI

---

#### Task 75.3.3: Update Sprint 76 Backlog (2 SP)

**Actions:**
1. Create placeholder `SPRINT_76_PLAN.md` with top 3 improvements
2. Update `docs/sprints/SPRINT_PLAN.md` with Sprint 75 completion
3. Document Sprint 75 retrospective

**Deliverables:**
- `docs/sprints/SPRINT_76_PLAN.md` (draft)
- `docs/sprints/SPRINT_PLAN.md` (updated)
- `docs/sprints/SPRINT_75_RETROSPECTIVE.md`

**Acceptance Criteria:**
- Sprint 76 has clear focus based on Sprint 75 results
- Sprint Plan updated with Sprint 75 as completed
- Retrospective documents learnings

---

## Success Metrics

**Sprint Completion Criteria:**
- ✅ All RAGAS tests executed (20 questions)
- ✅ All retrieval comparison tests executed (10 queries × 3 methods)
- ✅ Baseline RAGAS metrics established
- ✅ Retrieval method performance comparison documented
- ✅ 10+ RAG optimization techniques researched
- ✅ 5+ concrete improvement recommendations created
- ✅ Sprint 76 backlog prepared

**Quality Targets:**
- RAGAS Context Precision: >0.75 (goal)
- RAGAS Context Recall: >0.70 (goal)
- RAGAS Faithfulness: >0.90 (goal)
- RAGAS Answer Relevancy: >0.80 (goal)
- Hybrid retrieval competitive with or better than pure methods

**Documentation:**
- RAGAS analysis report created
- Retrieval comparison analysis created
- RAG tuning research documented
- Improvement plan with 5+ recommendations
- Sprint 76 backlog prepared

---

## Risk Mitigation

**Risk 1: RAGAS tests fail completely**
- **Mitigation:** Start with smoke test (5 samples)
- **Fallback:** Debug with single sample, check Ollama connectivity

**Risk 2: Metrics below targets**
- **Mitigation:** This is expected! Focus on establishing baseline
- **Action:** Use low metrics to guide improvement plan

**Risk 3: Long evaluation time (>2 hours)**
- **Mitigation:** Run tests in background with `pytest -v`
- **Action:** Parallelize tests if possible

**Risk 4: Ollama instability**
- **Mitigation:** Monitor Ollama logs, restart if needed
- **Fallback:** Use smaller sample size (10 instead of 20)

**Risk 5: Insufficient online research results**
- **Mitigation:** Use academic papers (arXiv) as primary source
- **Fallback:** Leverage LangChain/LlamaIndex documentation

---

## Daily Breakdown

**Day 1 (2026-01-04):**
- ✅ Create SPRINT_75_PLAN.md
- ✅ Update SPRINT_PLAN.md
- 🎯 Task 75.1.1: Run RAGAS smoke test (2 SP)

**Day 2 (2026-01-05):**
- 🎯 Task 75.1.2: Run full RAGAS evaluation (8 SP)
  - Morning: Context Precision + Recall
  - Afternoon: Faithfulness + Answer Relevancy

**Day 3 (2026-01-06):**
- 🎯 Task 75.1.3: Analyze RAGAS results (3 SP)
- 🎯 Task 75.2.1: Run retrieval comparison smoke test (2 SP)

**Day 4-5 (2026-01-07/08):**
- 🎯 Task 75.2.2: Run full retrieval comparison (8 SP)
  - Day 4: BM25 vs Vector comparisons
  - Day 5: Hybrid comparisons

**Day 6 (2026-01-09):**
- 🎯 Task 75.2.3: Analyze retrieval comparison (3 SP)

**Day 7-8 (2026-01-10/11):**
- 🎯 Task 75.3.1: Online RAG tuning research (3 SP)

**Day 9 (2026-01-12):**
- 🎯 Task 75.3.2: Create improvement recommendations (3 SP)

**Day 10 (2026-01-13):**
- 🎯 Task 75.3.3: Update Sprint 76 backlog (2 SP)
- 📝 Sprint retrospective and documentation review

---

## Notes

**Important Reminders:**
- Run tests on DGX Spark (backend services must be running)
- Save all JSON reports to `reports/` directory
- Take screenshots of test output for documentation
- Document any unexpected behavior or errors
- German LLM responses are expected (language-agnostic tests)

**Performance Expectations:**
- RAGAS smoke test: ~2 minutes (5 samples)
- RAGAS full test: ~30-40 minutes (20 samples)
- Retrieval comparison: ~60 minutes (30 evaluations)
- Total test runtime: ~2-3 hours

**After Sprint 75:**
- We'll have objective quality baseline
- Clear understanding of retrieval method tradeoffs
- Data-driven improvement roadmap for Sprint 76+
- Foundation for continuous quality monitoring
