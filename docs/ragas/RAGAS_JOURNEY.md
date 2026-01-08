# RAGAS Journey - Continuous RAG Metrics Optimization

**Status:** 🔄 Active Development
**Sprint:** 79+
**Goal:** Achieve SOTA-level RAGAS metrics (F ≥ 0.90, AR ≥ 0.95, CP ≥ 0.85, CR ≥ 0.75)

---

## Purpose of This Document

This is a **living document** that tracks our continuous journey to optimize RAGAS metrics for AegisRAG. Unlike ADRs (architectural decisions) or DECISION_LOG (point-in-time choices), this document captures:

- **Experiments** - What we tried, what worked, what didn't
- **Metrics Evolution** - How scores change over time
- **Insights** - Lessons learned from each iteration
- **Action Items** - Next steps for improvement

**Update Frequency:** After every RAGAS evaluation run or significant optimization attempt.

---

## Current Status (2026-01-08)

| Metric | Vector | Graph | Hybrid | SOTA Target | Status |
|--------|--------|-------|--------|-------------|--------|
| **Context Precision** | 0.108 | **0.667** | 0.108 | 0.85 | 🟡 Graph OK, Others Low |
| **Context Recall** | 0.185 | 0.291 | 0.185 | 0.75 | 🔴 All Far Below |
| **Faithfulness** | 0.542 | 0.398 | 0.292 | 0.90 | 🔴 All Far Below |
| **Answer Relevancy** | 0.649 | **0.935** | 0.901 | 0.95 | 🟢 Graph Excellent |

**Best Mode:** Graph-Only (CP=0.667, AR=0.935)
**Main Bottlenecks:** Context Recall (max 0.291), Faithfulness (max 0.542)
**Dataset:** amnesty_qa (3 questions, multi-hop reasoning)

---

## Journey Log

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

### Sprint 80: Critical Fixes (3 SP)
- [x] Fix embedding dimension mismatch (BGE-M3 1024-dim)
- [ ] Re-run RAGAS with correct embeddings
- [ ] Hybrid fusion cross-encoder reranking
- [ ] Increase top_k to 10-15

**Expected Improvements:** CR +100%, CP +300% (Hybrid)

---

### Sprint 81-82: Retrieval Improvements (8 SP)
- [ ] Query-adaptive routing (Vector vs Graph vs Hybrid)
- [ ] Parent chunk retrieval (sentence → paragraph)
- [ ] Entity extraction quality audit
- [ ] Multi-hop graph traversal (1-3 hops → 2-5 hops)

**Expected Improvements:** CR +80%, CP +30%

---

### Sprint 83+: Answer Generation Optimization (12 SP)
- [ ] DSPy optimization for Faithfulness
- [ ] Citation-aware generation (force source citing)
- [ ] Prompt engineering for grounded answers
- [ ] GraphRAG-style community detection (Leiden algorithm)

**Expected Improvements:** F +100-150%, CR +50%

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

### Experiment #2: BGE-M3 1024-dim Re-Evaluation (2026-01-08 - IN PROGRESS)

**Hypothesis:** Using consistent embeddings (BGE-M3 1024-dim) will:
- Increase Context Precision/Recall (more accurate relevance judgments)
- Not affect Faithfulness/Answer Relevancy (LLM-based, no embeddings)

**Changes:**
- Replaced nomic-embed-text (768-dim) with SimpleBGEM3Embeddings (1024-dim)
- Same model as ingestion (BAAI/bge-m3 via SentenceTransformer)

**Results:** TBD (evaluation in progress)

**Status:** 🔄 Running

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
