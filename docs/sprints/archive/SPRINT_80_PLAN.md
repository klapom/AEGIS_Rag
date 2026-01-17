# Sprint 80: RAGAS P0 Critical Fixes - Faithfulness & Hybrid Fusion

**Status:** 📝 Planned
**Sprint Dauer:** 2026-01-13 bis 2026-01-24 (2 weeks)
**Story Points:** 21 SP
**Assignee:** Claude + Team
**Dependencies:** Sprint 79 Complete (RAGAS 0.4.2 POC, RAGAS_ANALYSIS_2026_01_08.md)

---

## Sprint Ziele

**Primär:** Address the two critical bottlenecks identified in RAGAS evaluation:
1. **Faithfulness** - max 0.550 vs SOTA 0.90 (39-44% gap)
2. **Hybrid Hallucination** - Amnesty Hybrid F=0.301 (worst across all modes)

**Sekundär:** Enable reliable fallback for Graph Mode empty context scenarios (3/5 HotpotQA failures).

**Tertiär:** Expand evaluation datasets for statistically robust metrics.

---

## Problem Statement

**RAGAS Evaluation Results (2026-01-08):**

| Dataset | Mode | CP | CR | F | AR | Critical Issue |
|---------|------|-----|-----|-----|-----|----------------|
| Amnesty | Graph | 0.581 | 0.587 | **0.550** | 0.735 | Over-elaboration |
| Amnesty | Hybrid | 0.400 | 0.556 | **0.301** | 0.781 | Hallucination (2/10 F=0.0) |
| HotpotQA | Graph | 0.200 | 0.200 | 0.250 | 0.345 | **3/5 empty contexts** |
| HotpotQA | Hybrid | 0.483 | 0.600 | 0.500 | 0.501 | Best but still F<0.6 |

**Root Causes:**
1. **Faithfulness Gap:** LLM extrapolates beyond retrieved contexts, no citation enforcement
2. **Hybrid Hallucination:** Conflicting Vector + Graph contexts confuse LLM, no cross-encoder reranking
3. **Graph Empty Contexts:** Entity extraction gaps in HotpotQA .txt files, no fallback mechanism

**Target Metrics (Sprint 80):**
| Metric | Baseline | Target | Method |
|--------|----------|--------|--------|
| Amnesty Graph F | 0.550 | **≥0.750** | Cite-sources prompt |
| Amnesty Hybrid F | 0.301 | **≥0.600** | Cross-encoder reranking |
| HotpotQA Graph Empty | 3/5 | **0/5** | Vector fallback |
| Overall CR | 0.587 | **≥0.700** | top_k increase |

---

## Features

### Feature 80.1: Cite-Sources Prompt Engineering (3 SP) 🎯 **P0 - CRITICAL**

**Beschreibung:**
Add citation enforcement to answer generation to dramatically improve Faithfulness. The LLM must cite sources for every claim, preventing hallucination.

**Problem:**
- Current Faithfulness max 0.550 (Graph Mode) vs SOTA 0.90
- LLM over-elaborates and extrapolates beyond retrieved contexts
- Example: Milhouse question - answer states "Mussolini" when context is truncated

**Technical Solution:**

```python
# src/agents/coordinator/prompts.py

CITE_SOURCES_SYSTEM_PROMPT = """
CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE EXACTLY:

1. ONLY include information EXPLICITLY stated in the provided sources.
2. For EVERY claim, cite the source number in [brackets] at the end of the sentence.
3. If information is NOT in the sources, explicitly state: "This information is not available in the provided sources."
4. DO NOT infer, extrapolate, or synthesize beyond what is written.
5. DO NOT add background knowledge or general facts not in the sources.

Example:
- WRONG: "Einstein developed relativity, which revolutionized physics."
- CORRECT: "Einstein developed the theory of relativity [1]. This work changed our understanding of space and time [1]."

RESPONSE FORMAT:
- Each claim must have at least one citation [X]
- Multiple sources for the same claim: [1, 2]
- Unknown information: "Not available in sources"
"""

# Integration in answer_generation_node()
def build_answer_prompt(query: str, contexts: list[str]) -> str:
    numbered_sources = "\n".join(
        f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)
    )
    return f"""
{CITE_SOURCES_SYSTEM_PROMPT}

SOURCES:
{numbered_sources}

QUESTION: {query}

ANSWER (with citations):
"""
```

**Implementation Files:**
- `src/agents/coordinator/prompts.py` - Add CITE_SOURCES_SYSTEM_PROMPT
- `src/agents/coordinator/nodes.py` - Integrate in answer_generation_node()
- `tests/unit/agents/test_cite_sources_prompt.py` - 5 unit tests

**Acceptance Criteria:**
- [ ] CITE_SOURCES_SYSTEM_PROMPT added to prompts.py
- [ ] answer_generation_node() uses new prompt
- [ ] Generated answers contain [X] citations
- [ ] RAGAS Faithfulness: Amnesty Graph F=0.550 → **≥0.750** (+36%)
- [ ] Unit tests: 5/5 passing (citation format, missing info handling)
- [ ] Manual verification: 10 sample answers have correct citations

**Expected Impact:**
- Faithfulness: +50-80% (F=0.550 → 0.825-0.990)
- Answer Relevancy: +10-20% (more focused answers)

---

### Feature 80.2: Graph→Vector Fallback on Empty Contexts (2 SP) 🎯 **P0 - CRITICAL**

**Beschreibung:**
Implement automatic fallback to Vector retrieval when Graph retrieval returns empty contexts. This eliminates the 3/5 HotpotQA Graph Mode failures.

**Problem:**
- 3/5 HotpotQA questions return `num_contexts_retrieved=0` in Graph Mode
- Entities not extracted: "Arthur's Magazine", "James Henry Miller", "Cadmium Chloride"
- Error: "I don't have enough information in the knowledge base"

**Technical Solution:**

```python
# src/components/graph_rag/retrieval.py

async def graph_retrieval_with_fallback(
    query: str,
    namespace: str,
    top_k: int = 7,
    fallback_to_vector: bool = True,
) -> list[dict]:
    """
    Retrieve contexts from graph with automatic fallback to vector.

    If graph returns 0 contexts AND fallback_to_vector=True,
    automatically switch to vector retrieval.
    """
    # Try graph retrieval first
    graph_contexts = await graph_retrieval(query, namespace, top_k=top_k)

    if len(graph_contexts) > 0:
        logger.info(
            "graph_retrieval_success",
            namespace=namespace,
            num_contexts=len(graph_contexts),
        )
        return graph_contexts

    # Graph returned empty - fallback to vector
    if fallback_to_vector:
        logger.warning(
            "graph_retrieval_empty_fallback_to_vector",
            namespace=namespace,
            query=query[:100],
        )

        vector_contexts = await vector_retrieval(query, namespace, top_k=top_k)

        # Mark contexts as fallback for observability
        for ctx in vector_contexts:
            ctx["retrieval_mode"] = "vector_fallback"

        return vector_contexts

    # No fallback - return empty
    return []
```

**Implementation Files:**
- `src/components/graph_rag/retrieval.py` - Add fallback logic
- `src/agents/graph_agent/nodes.py` - Use new function
- `tests/unit/components/test_graph_fallback.py` - 4 unit tests

**Acceptance Criteria:**
- [ ] graph_retrieval_with_fallback() implemented
- [ ] graph_agent uses new function by default
- [ ] Fallback logged with structured logging
- [ ] Contexts marked with `retrieval_mode=vector_fallback`
- [ ] RAGAS HotpotQA Graph: 3/5 empty → **0/5 empty**
- [ ] Unit tests: 4/4 passing

**Expected Impact:**
- HotpotQA Graph failures: 60% → 0%
- Graph Mode usability: Now reliable for all query types

---

### Feature 80.3: Hybrid Fusion Cross-Encoder Reranking (5 SP) 🎯 **P0 - CRITICAL**

**Beschreibung:**
Implement cross-encoder reranking after Vector+Graph fusion to resolve context conflicts and surface the most relevant chunks. This addresses the Amnesty Hybrid hallucination issue.

**Problem:**
- Amnesty Hybrid F=0.301 (worst Faithfulness across all modes)
- 2/10 questions have F=0.0 (complete hallucination)
- Root cause: Irrelevant Vector chunks listed first → LLM focuses on noise
- Example Q1: Graph has 3 relevant chunks (F=0.444), but Hybrid buries them with 5 irrelevant Vector chunks (F=0.0)

**Technical Solution:**

```python
# src/components/hybrid_fusion/reranking.py

from sentence_transformers import CrossEncoder
import numpy as np

class HybridFusionReranker:
    """
    Cross-encoder reranking for hybrid Vector+Graph fusion.

    Architecture:
    1. Concatenate Vector + Graph contexts (deduplication)
    2. Score each context with cross-encoder (query, context) pairs
    3. Return top-k by cross-encoder score

    Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (42MB, <50ms)
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        similarity_threshold: float = 0.95,
    ):
        self.cross_encoder = CrossEncoder(model_name)
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, contexts: list[dict]) -> list[dict]:
        """Remove near-duplicate contexts by text similarity."""
        seen_texts = set()
        unique = []

        for ctx in contexts:
            text = ctx.get("text", ctx.get("content", ""))
            # Simple dedup: check if text already seen
            text_hash = hash(text[:500])  # First 500 chars
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique.append(ctx)

        return unique

    def rerank(
        self,
        query: str,
        vector_contexts: list[dict],
        graph_contexts: list[dict],
        top_k: int = 10,
    ) -> list[dict]:
        """
        Rerank hybrid fusion results with cross-encoder.

        Returns top-k contexts sorted by cross-encoder relevance score.
        """
        # Step 1: Concatenate and deduplicate
        all_contexts = vector_contexts + graph_contexts
        unique_contexts = self.deduplicate(all_contexts)

        if len(unique_contexts) == 0:
            return []

        # Step 2: Score with cross-encoder
        texts = [ctx.get("text", ctx.get("content", "")) for ctx in unique_contexts]
        pairs = [(query, text) for text in texts]
        scores = self.cross_encoder.predict(pairs)

        # Step 3: Sort by score and return top-k
        scored = list(zip(unique_contexts, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        # Add score to context metadata
        result = []
        for ctx, score in scored[:top_k]:
            ctx["cross_encoder_score"] = float(score)
            result.append(ctx)

        return result
```

**Implementation Files:**
- `src/components/hybrid_fusion/__init__.py` - New module
- `src/components/hybrid_fusion/reranking.py` - HybridFusionReranker
- `src/agents/coordinator/nodes.py` - Integrate reranker in hybrid mode
- `tests/unit/components/test_hybrid_fusion_reranking.py` - 6 unit tests
- `tests/integration/test_hybrid_fusion_e2e.py` - 2 integration tests

**Dependencies:**
```bash
poetry add sentence-transformers
# Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (auto-downloaded)
```

**Acceptance Criteria:**
- [ ] HybridFusionReranker class implemented
- [ ] Deduplication removes near-duplicate contexts
- [ ] Cross-encoder scoring integrated
- [ ] Hybrid mode uses reranker by default
- [ ] cross_encoder_score added to context metadata
- [ ] RAGAS Amnesty Hybrid F: 0.301 → **≥0.600** (+100%)
- [ ] Latency impact: <100ms per query (acceptable)
- [ ] Unit tests: 6/6 passing
- [ ] Integration tests: 2/2 passing

**Expected Impact:**
- Amnesty Hybrid Faithfulness: +100-150% (F=0.301 → 0.600-0.750)
- Amnesty Hybrid Context Precision: +63-100% (CP=0.400 → 0.650-0.800)

---

### Feature 80.4: Increase Retrieval top_k (1 SP) 🎯 **P1**

**Beschreibung:**
Increase the number of retrieved contexts to improve Context Recall without sacrificing precision (thanks to cross-encoder reranking from Feature 80.3).

**Current Configuration:**
- Vector top_k=5
- Graph top_k=3
- Hybrid concatenates = 8 contexts max

**New Configuration:**
- Vector top_k=10
- Graph top_k=7
- Hybrid after reranking = 10 contexts max

**Implementation:**

```python
# src/core/config.py

class Settings(BaseSettings):
    # Retrieval Configuration
    vector_top_k: int = Field(default=10, description="Vector retrieval top-k")  # Was 5
    graph_top_k: int = Field(default=7, description="Graph retrieval top-k")      # Was 3
    hybrid_final_top_k: int = Field(default=10, description="Final contexts after reranking")
```

**Acceptance Criteria:**
- [ ] Config defaults updated (vector: 5→10, graph: 3→7)
- [ ] Hybrid reranker returns top-10 after fusion
- [ ] RAGAS CR: 0.587 → **≥0.700** (+19%)
- [ ] RAGAS CP: No significant degradation (reranker compensates)

---

### Feature 80.5: Expand RAGAS Evaluation Datasets (4 SP) 🎯 **P1**

**Beschreibung:**
Expand evaluation datasets for statistically robust metrics. Current sample sizes (10 Amnesty, 5 HotpotQA) are too small for reliable conclusions.

**Target Dataset Sizes:**
- Amnesty: 10 → **50 questions** (5x)
- HotpotQA: 5 → **20 questions** (4x)

**Data Sources:**

1. **Amnesty Expansion (40 new questions):**
   - **Source:** HuggingFace `explodinggradients/amnesty_qa` (official RAGAS dataset)
   - `scripts/setup_amnesty_qa_ragas.py` already downloads full dataset (20+ questions in eval split)
   - Additional questions via RAGAS TestsetGenerator from ingested Amnesty contexts
   - Ground truth: Curated by RAGAS team, verified quality

2. **HotpotQA Expansion (15 new questions):**
   - **Source:** HuggingFace `hotpot_qa` dataset (113K questions in distractor split)
   - Filter for questions with entities matching our ingested documents
   - Include ground truth from dataset

**⚠️ CRITICAL: Ingestion Method**

All new documents MUST be ingested via Frontend API to ensure namespace isolation:

```bash
# For Amnesty contexts
scripts/upload_amnesty_contexts.sh
# - Uses: POST /api/v1/retrieval/upload
# - Namespace: amnesty_qa
# - Auth: JWT token from /api/v1/auth/login

# For HotpotQA contexts
scripts/upload_ragas_frontend.sh
# - Uses: POST /api/v1/retrieval/upload
# - Namespace: ragas_eval_txt
# - Auth: JWT token from /api/v1/auth/login
```

**❌ DO NOT use `scripts/ingest_ragas_simple.py`** - bypasses namespace settings!

**Implementation:**

```python
# scripts/expand_evaluation_datasets.py

from datasets import load_dataset
from ragas.testset.generator import TestsetGenerator
from ragas.testset.transforms import default_transforms

async def expand_amnesty_dataset(
    documents: list,
    current_questions: list,
    target_count: int = 50,
):
    """
    Generate additional Amnesty questions using RAGAS TestsetGenerator.
    """
    generator = TestsetGenerator(
        llm=llm,
        embedding_model=embeddings,
        transforms=default_transforms(),
    )

    # Generate new questions (excluding current ones)
    new_count = target_count - len(current_questions)
    testset = await generator.generate_with_langchain_docs(
        documents,
        test_size=new_count,
        distributions={
            "simple": 0.3,
            "reasoning": 0.4,
            "multi_context": 0.3,
        },
    )

    return current_questions + testset.to_list()


def expand_hotpotqa_dataset(
    namespace: str,
    current_questions: list,
    target_count: int = 20,
):
    """
    Sample additional HotpotQA questions from HuggingFace.
    Filter for questions with entities in our namespace.
    """
    dataset = load_dataset("hotpot_qa", "distractor", split="validation")

    # Filter for questions with entities in our graph
    available_entities = get_entities_in_namespace(namespace)

    new_questions = []
    for sample in dataset:
        if len(new_questions) >= target_count - len(current_questions):
            break

        # Check if question entities are in our graph
        question_entities = extract_entities(sample["question"])
        if any(e in available_entities for e in question_entities):
            new_questions.append({
                "question": sample["question"],
                "ground_truth": sample["answer"],
                "contexts": sample["context"]["sentences"],
            })

    return current_questions + new_questions
```

**Deliverables:**
- `data/evaluation/ragas_amnesty_50.jsonl` (50 questions)
- `data/evaluation/ragas_hotpotqa_20.jsonl` (20 questions)
- `scripts/expand_evaluation_datasets.py`

**Acceptance Criteria:**
- [ ] Amnesty dataset expanded to 50 questions
- [ ] HotpotQA dataset expanded to 20 questions
- [ ] Human review completed for quality assurance
- [ ] New datasets validated (no duplicates, valid ground truths)
- [ ] RAGAS evaluation re-run on expanded datasets
- [ ] Statistical confidence improved (p<0.05 for metric comparisons)

---

### Feature 80.6: RAGAS Evaluation Re-Run & Analysis (3 SP) 🎯 **VALIDATION**

**Beschreibung:**
Re-run RAGAS evaluation after all Sprint 80 fixes to validate improvements and document results in RAGAS_JOURNEY.md.

**Execution Plan:**

1. **Baseline Documentation:**
   - Save pre-fix metrics (from 2026-01-08 evaluation)

2. **Fix Integration:**
   - Deploy Features 80.1-80.5
   - Verify all fixes active in evaluation

3. **Full RAGAS Evaluation:**
   ```bash
   # Amnesty (50 questions, 3 modes)
   poetry run python scripts/run_ragas_evaluation.py \
     --dataset data/evaluation/ragas_amnesty_50.jsonl \
     --namespace amnesty_qa \
     --modes vector,graph,hybrid \
     --output-dir data/evaluation/results/sprint80/

   # HotpotQA (20 questions, 3 modes)
   poetry run python scripts/run_ragas_evaluation.py \
     --dataset data/evaluation/ragas_hotpotqa_20.jsonl \
     --namespace ragas_eval_txt \
     --modes vector,graph,hybrid \
     --output-dir data/evaluation/results/sprint80/
   ```

4. **Results Analysis:**
   - Compare pre/post metrics
   - Document improvements in RAGAS_JOURNEY.md
   - Identify remaining gaps for Sprint 81

**Expected Results:**

| Metric | Pre-Fix | Post-Fix | Improvement |
|--------|---------|----------|-------------|
| Amnesty Graph F | 0.550 | ≥0.750 | +36% |
| Amnesty Hybrid F | 0.301 | ≥0.600 | +100% |
| HotpotQA Graph Empty | 60% | 0% | -60pp |
| Overall CR | 0.587 | ≥0.700 | +19% |

**Acceptance Criteria:**
- [ ] Pre/post comparison documented
- [ ] All target metrics achieved
- [ ] RAGAS_JOURNEY.md Experiment #3 entry added
- [ ] Remaining gaps identified for Sprint 81

---

### Feature 80.7: Update RAGAS_JOURNEY.md Documentation (1 SP)

**Beschreibung:**
Document Sprint 80 experiment results in the living RAGAS_JOURNEY.md document.

**Content to Add:**

```markdown
## Experiment #3: Sprint 80 P0 Fixes (2026-01-XX)

### Changes Implemented
1. **Cite-Sources Prompt** (Feature 80.1): Enforce source citations
2. **Graph→Vector Fallback** (Feature 80.2): Eliminate empty contexts
3. **Hybrid Cross-Encoder Reranking** (Feature 80.3): Resolve context conflicts
4. **Increased top_k** (Feature 80.4): 5→10 Vector, 3→7 Graph
5. **Expanded Datasets** (Feature 80.5): 50 Amnesty, 20 HotpotQA

### Results

| Dataset | Mode | Metric | Before | After | Change |
|---------|------|--------|--------|-------|--------|
| Amnesty | Graph | F | 0.550 | X.XXX | +XX% |
| Amnesty | Hybrid | F | 0.301 | X.XXX | +XX% |
| HotpotQA | Graph | Empty | 60% | 0% | -60pp |
| Overall | All | CR | 0.587 | X.XXX | +XX% |

### Key Learnings
- [To be filled after evaluation]

### Next Steps (Sprint 81)
- Query-adaptive routing
- Parent chunk retrieval
- Entity extraction improvements
```

**Acceptance Criteria:**
- [ ] Experiment #3 section added
- [ ] All metrics documented
- [ ] Learnings captured
- [ ] Sprint 81 next steps defined

---

### Feature 80.8: ADR-044 Hybrid Fusion Cross-Encoder Reranking (2 SP)

**Beschreibung:**
Create Architecture Decision Record for the Hybrid Fusion Cross-Encoder Reranking approach.

**ADR Content:**

```markdown
# ADR-044: Hybrid Fusion Cross-Encoder Reranking

**Status:** Accepted
**Date:** 2026-01-XX
**Context:** Sprint 80 RAGAS P0 fixes

## Decision
Implement cross-encoder reranking after Vector+Graph fusion to resolve context conflicts and improve Faithfulness.

## Context
- Amnesty Hybrid F=0.301 (worst Faithfulness)
- Root cause: Conflicting contexts confuse LLM
- Vector retrieves tangentially related noise
- Graph's good contexts buried in fusion

## Rationale
1. Cross-encoder directly scores (query, context) pairs
2. More accurate than bi-encoder similarity alone
3. Deduplication prevents redundant contexts
4. ms-marco-MiniLM-L-6-v2 adds <50ms latency

## Consequences
- Improved Faithfulness (+100-150%)
- Additional dependency: sentence-transformers
- Model download on first use (42MB)
- Latency increase: <100ms per query
```

**Acceptance Criteria:**
- [ ] ADR-044 created in docs/adr/
- [ ] ADR_INDEX.md updated
- [ ] Technical decision documented
- [ ] Trade-offs explained

---

## Technical Requirements

### New Dependencies

```bash
poetry add sentence-transformers  # For cross-encoder reranking
```

### Model Downloads

```python
# Auto-downloaded on first use
# cross-encoder/ms-marco-MiniLM-L-6-v2 (42MB)
# Cached in ~/.cache/huggingface/
```

### Performance Requirements

| Operation | Target | Method |
|-----------|--------|--------|
| Cross-encoder reranking | <100ms | Batch scoring |
| Cite-sources prompt | +0ms | Prompt change only |
| Graph fallback | +50ms | Vector retrieval |

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/agents/test_cite_sources_prompt.py
class TestCiteSourcesPrompt:
    def test_citation_format(self):
        """Verify answers contain [X] citations."""

    def test_missing_info_handling(self):
        """Verify 'not available' for missing info."""

    def test_no_hallucination(self):
        """Verify no claims without citations."""

# tests/unit/components/test_hybrid_fusion_reranking.py
class TestHybridFusionReranker:
    def test_deduplication(self):
        """Verify near-duplicate removal."""

    def test_cross_encoder_scoring(self):
        """Verify scores assigned correctly."""

    def test_top_k_selection(self):
        """Verify top-k returned by score."""
```

### Integration Tests

```bash
# RAGAS evaluation with fixes
pytest tests/integration/test_ragas_evaluation.py -v
```

---

## Success Metrics

| Metric | Baseline (Sprint 79) | Target (Sprint 80) | Status |
|--------|---------------------|-------------------|--------|
| Amnesty Graph F | 0.550 | ≥0.750 | 🎯 |
| Amnesty Hybrid F | 0.301 | ≥0.600 | 🎯 |
| HotpotQA Graph Empty | 60% | 0% | 🎯 |
| Overall CR | 0.587 | ≥0.700 | 🎯 |
| Amnesty Hybrid CP | 0.400 | ≥0.650 | 🎯 |

---

## Deliverables

1. **Code:**
   - [ ] `src/agents/coordinator/prompts.py` - CITE_SOURCES_SYSTEM_PROMPT
   - [ ] `src/components/graph_rag/retrieval.py` - Fallback logic
   - [ ] `src/components/hybrid_fusion/reranking.py` - Cross-encoder reranker
   - [ ] `scripts/expand_evaluation_datasets.py`
   - [ ] 15 unit tests, 4 integration tests

2. **Data:**
   - [ ] `data/evaluation/ragas_amnesty_50.jsonl`
   - [ ] `data/evaluation/ragas_hotpotqa_20.jsonl`
   - [ ] `data/evaluation/results/sprint80/` - Evaluation results

3. **Documentation:**
   - [ ] ADR-044: Hybrid Fusion Cross-Encoder Reranking
   - [ ] RAGAS_JOURNEY.md Experiment #3
   - [ ] TECH_STACK.md (sentence-transformers)

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cross-encoder latency >100ms | Low | Medium | Use batch scoring, smaller model |
| Cite-sources reduces answer quality | Medium | High | Tune prompt, allow synthesis with citations |
| Dataset expansion yields poor quality | Medium | Medium | Human review, filter by confidence |
| HuggingFace HotpotQA entity mismatch | High | Low | Accept lower coverage, document gaps |

---

## Timeline

**Week 1 (2026-01-13 to 2026-01-17):**
- Day 1-2: Feature 80.1 (Cite-sources prompt)
- Day 2-3: Feature 80.2 (Graph fallback)
- Day 3-5: Feature 80.3 (Cross-encoder reranking)
- Day 5: Feature 80.4 (top_k increase)

**Week 2 (2026-01-20 to 2026-01-24):**
- Day 1-3: Feature 80.5 (Dataset expansion)
- Day 4: Feature 80.6 (RAGAS re-run)
- Day 4-5: Features 80.7, 80.8 (Documentation)
- Day 5: Sprint Review

---

## Sprint Review Criteria

**P0 Critical (MUST PASS):**
- [ ] Amnesty Graph F ≥ 0.750 (cite-sources working)
- [ ] Amnesty Hybrid F ≥ 0.600 (cross-encoder reranking working)
- [ ] HotpotQA Graph Empty = 0% (fallback working)

**P1 High Priority (SHOULD PASS):**
- [ ] Overall CR ≥ 0.700 (top_k increase effective)
- [ ] Expanded datasets available (50 Amnesty, 20 HotpotQA)
- [ ] Statistical confidence improved

**Documentation:**
- [ ] ADR-044 created and reviewed
- [ ] RAGAS_JOURNEY.md Experiment #3 complete
- [ ] All unit/integration tests passing

---

## Follow-up for Sprint 81

**Remaining P1 items from RAGAS_ANALYSIS_2026_01_08.md:**
1. Query-Adaptive Routing (entity | factoid | complex classification)
2. Parent Chunk Retrieval (sentence-level → parent section)
3. Entity Extraction Improvements (domain-agnostic types)

**New items identified:**
- DSPy optimization for Faithfulness (if F<0.90 after Sprint 80)
- Automatic RAGAS CI/CD integration (nightly evaluation)
