# TD-080: Context Relevance Guard for Anti-Hallucination

**Created:** 2026-01-02 (Sprint 71)
**Priority:** HIGH
**Story Points:** 5 SP
**Status:** OPEN
**Target Sprint:** 71+

---

## Problem Statement

The RAG system suffers from **hallucinations** when the LLM generates answers using its **parametric knowledge** (training data) instead of exclusively relying on retrieved contexts.

### Observed Behavior

**Example 1: "Was ist ein Knowledge Graph?"**
- ❌ **Hallucinated Answer:** Generic definition from LLM training data
- ✅ **Expected Behavior:** "Diese Information ist nicht in der Wissensdatenbank verfügbar."
- **Root Cause:** Retrieved contexts (OMNITRACKER docs) are irrelevant (38% similarity), but LLM generates answer anyway

**Example 2: "Erkläre mir das Konzept von RAG"**
- ✅ **Correct Behavior:** "I don't have enough information..."
- **Why it worked:** "RAG" is specific enough that LLM doesn't hallucinate

### Why This Happens

1. **Weak Prompt:** Current prompt says "basierend auf den Dokumenten" but doesn't enforce **exclusivity**
2. **No Relevance Check:** System doesn't verify if contexts can actually answer the query
3. **LLM Behavior:** LLMs default to parametric knowledge when contexts are vague/irrelevant

---

## Current Mitigation (Sprint 71)

**Quick Fix: Prompt Hardening (1-2 SP) - ✅ IMPLEMENTED**

Added explicit anti-hallucination rules to all prompts:

```python
ANSWER_GENERATION_PROMPT = """Du bist ein hilfreicher KI-Assistent für eine Wissensdatenbank.

**WICHTIGE REGELN:**
- Antworte NUR basierend auf den bereitgestellten Dokumenten
- Nutze KEIN externes Wissen aus deinem Training
- Wenn die Dokumente die Frage nicht beantworten können, antworte:
  "Diese Information ist nicht in der Wissensdatenbank verfügbar."
- Erfinde KEINE Informationen

**Dokumente:**
{context}
"""
```

**Effectiveness:** ~60-70% reduction in hallucinations (estimated)
**Limitations:** Not 100% reliable - LLMs can still ignore instructions

---

## Proposed Solutions (Needs Evaluation)

### Option 2: Embedding-Based Relevance Score (3 SP)

**Concept:** Compute semantic similarity between query and top-K contexts.

```python
async def generate_answer(self, query: str, contexts: list[dict], ...):
    if not contexts:
        return self._no_context_answer(query)

    # NEW: Check if contexts are relevant to query
    relevance_score = await self._calculate_relevance(query, contexts)

    if relevance_score < 0.4:  # Configurable threshold
        logger.info("contexts_not_relevant_to_query", score=relevance_score)
        return self._no_context_answer(query)

    # Proceed with generation...

async def _calculate_relevance(self, query: str, contexts: list[dict]) -> float:
    """Calculate semantic relevance using BGE-M3 embeddings."""
    from src.components.shared.embedding_service import get_embedding_service
    from src.components.retrieval.intent_classifier import cosine_similarity

    embedding_service = get_embedding_service()

    # Embed query
    query_embedding = await embedding_service.embed_single(query)

    # Embed top-3 contexts and compute average similarity
    context_texts = [ctx.get("text", "")[:500] for ctx in contexts[:3]]
    context_embeddings = await embedding_service.embed_batch(context_texts)

    similarities = [
        cosine_similarity(query_embedding, ctx_emb)
        for ctx_emb in context_embeddings
    ]

    return sum(similarities) / len(similarities) if similarities else 0.0
```

**Reusable Components:**
- ✅ `get_embedding_service()` from `src/components/shared/embedding_service.py`
- ✅ `cosine_similarity()` from `src/components/retrieval/intent_classifier.py`

**Pros:**
- Objective, quantitative score
- Configurable threshold (e.g., 0.3-0.5)
- Reuses existing infrastructure

**Cons:**
- Adds +50-100ms latency (embedding computation)
- Fixed threshold may not fit all query types

**Estimated Effectiveness:** ~80-85% reduction

---

### Option 3: LLM-Based Relevance Guard (5 SP)

**Concept:** Use LLM with Structured Output for intelligent pre-check.

```python
class ContextRelevance(BaseModel):
    """LLM assessment of context relevance."""
    can_answer: bool = Field(description="True if contexts can answer question")
    confidence: float = Field(description="Confidence 0-1")
    reasoning: str = Field(description="Brief explanation")

async def _check_context_relevance(self, query: str, contexts: list) -> bool:
    """Use LLM to check if contexts can answer query."""

    prompt = f"""Prüfe ob die folgenden Dokumente die Frage beantworten können.

    Frage: {query}

    Dokumente:
    {self._format_contexts(contexts[:3])}

    Können diese Dokumente die Frage beantworten?"""

    llm = get_llm_client().get_chat_model()
    structured_llm = llm.with_structured_output(ContextRelevance)

    decision = await structured_llm.ainvoke(prompt)

    if not decision.can_answer:
        logger.info("llm_rejected_contexts",
                   reasoning=decision.reasoning,
                   confidence=decision.confidence)
        return False

    return True

async def generate_answer(self, query: str, contexts: list[dict], ...):
    if not contexts:
        return self._no_context_answer(query)

    # NEW: LLM-based relevance check
    if not await self._check_context_relevance(query, contexts):
        return self._no_context_answer(query)

    # Proceed with generation...
```

**Pros:**
- Intelligent, context-aware decision
- Understands nuances and semantic relationships
- Provides reasoning for debugging

**Cons:**
- Additional LLM call (+100-300ms latency)
- Higher cost (~2x LLM calls per query)
- May reject valid contexts if overly conservative

**Estimated Effectiveness:** ~90-95% reduction

---

### Option 4: Hybrid Approach (5 SP)

**Concept:** Combine Option 1 (Prompt Hardening) + Option 2 (Embedding Score).

```python
async def generate_answer(self, query: str, contexts: list[dict], ...):
    if not contexts:
        return self._no_context_answer(query)

    # Phase 1: Fast embedding-based relevance check
    relevance_score = await self._calculate_relevance(query, contexts)

    if relevance_score < 0.3:  # Low threshold
        logger.info("contexts_rejected_by_relevance_score",
                   score=relevance_score)
        return self._no_context_answer(query)

    # Phase 2: Proceed with hardened prompt
    # (Prompt already has anti-hallucination rules)
    answer = await self._generate_with_llm(query, contexts)

    return answer
```

**Pros:**
- Fast (50ms overhead)
- Objective + explicit rules
- Balanced cost/latency

**Cons:**
- Still not 100% perfect
- Threshold tuning required

**Estimated Effectiveness:** ~85-90% reduction

---

## Recommended Approach

**Phase 1 (Sprint 71): ✅ COMPLETE**
- Prompt Hardening (1-2 SP) - **IMPLEMENTED**

**Phase 2 (Sprint 72): Evaluation Required**
- Evaluate effectiveness of prompt hardening with real queries
- Collect metrics: hallucination rate, false negatives (rejected valid contexts)

**Phase 3 (Sprint 73+): Select Best Solution**
- Based on evaluation results, implement:
  - **Option 2 (Hybrid)** if prompt hardening shows 70%+ effectiveness
  - **Option 3 (LLM Guard)** if hallucinations persist above 20%

---

## Evaluation Criteria

Before selecting Phase 3 solution, measure:

1. **Hallucination Rate:** % of queries where LLM uses parametric knowledge
2. **False Negative Rate:** % of valid contexts rejected
3. **Latency Impact:** P95 latency increase
4. **User Feedback:** Qualitative assessment of answer quality

**Target Metrics:**
- Hallucination Rate: <5%
- False Negative Rate: <10%
- Latency Impact: <100ms P95

---

## Implementation Files

**Modified (Sprint 71 - Prompt Hardening):**
- `src/prompts/answer_prompts.py` - Added anti-hallucination rules to all 3 prompts

**Future Implementation (Option 2/3/4):**
- `src/agents/answer_generator.py` - Add relevance check before generation
- `src/components/retrieval/relevance_checker.py` (NEW) - Reusable relevance scoring
- `tests/unit/agents/test_answer_generator.py` - Test relevance guard

---

## Academic References

- **RAGAS Framework** - Context Relevance Metric (https://docs.ragas.io/en/stable/concepts/metrics/context_relevance.html)
- **ARES** (Automated RAG Evaluation System) - Context Relevance Classifier
- **Self-RAG** (Asai et al., 2024) - Retrieval-augmented generation with self-reflection

---

## Related Technical Debt

- **TD-057:** 4-Way Hybrid RRF Retrieval (✅ COMPLETE) - Improves retrieval quality
- **TD-079:** LLM-Based Intent Classifier (✅ COMPLETE) - Better query understanding
- **TD-074:** BM25 Cache Discrepancy (OPEN) - Affects retrieval accuracy

---

## Notes

- **Reusable Components:** Intent Classifier already has `cosine_similarity()` and embedding-based classification logic that can be adapted for context relevance scoring
- **Cost Consideration:** Option 3 (LLM Guard) doubles LLM costs - only use if absolutely necessary
- **Sprint 71 Quick Fix:** Prompt hardening is a zero-latency, zero-cost mitigation that should be evaluated before implementing more complex solutions
