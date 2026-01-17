# Sprint 92 Recursive LLM Improvements

**Status:** 📝 Proposed Architecture Changes
**Created:** 2026-01-14
**Context:** User feedback on BGE-M3 scoring + parallel worker configuration

---

## Problem Statement

**Current Implementation Issues:**

1. **Level 1 Relevance Scoring (Lines 393-469):**
   - Uses LLM to score each segment individually (10-20 LLM calls)
   - Latency: ~100-200ms × 20 segments = **2-4 seconds**
   - Cost: 20 LLM API calls per document
   - Fragile regex parsing of LLM responses

2. **Level 2 Processing (Lines 270-278):**
   - Sequential `for` loop - **NO parallelization**
   - Contradicts Sprint 92 plan promise of "Parallel Processing"
   - DGX Spark: Limited to 1 worker (Ollama single-threaded)
   - Cloud models: Could support 5-10 parallel workers

---

## Proposed Solution

### Option A: BGE-M3 Sparse+Dense Relevance Scoring ✅ RECOMMENDED

**Architecture:**
```python
# Level 1: Use BGE-M3 for fast relevance scoring
from src.components.shared.embedding_factory import get_embedding_service

embedding_service = get_embedding_service()  # Returns FlagEmbedding with BGE-M3

# 1. Embed query once
query_embedding = embedding_service.embed_single(query)
# Returns: {"dense": [1024 floats], "sparse": {"token_id": weight, ...}}

# 2. Embed all segments in batch (10-20x faster than individual)
segment_embeddings = embedding_service.embed_batch([s.content[:2000] for s in segments])

# 3. Compute hybrid similarity scores
for i, segment in enumerate(segments):
    # Sparse score (BM25-like keyword matching)
    sparse_score = compute_sparse_similarity(
        query_embedding["sparse"],
        segment_embeddings[i]["sparse"]
    )

    # Dense score (semantic similarity)
    dense_score = cosine_similarity(
        query_embedding["dense"],
        segment_embeddings[i]["dense"]
    )

    # Hybrid fusion (same as Sprint 87 Qdrant RRF)
    segment.relevance_score = 0.4 * sparse_score + 0.6 * dense_score
```

**Performance Impact:**
- **Latency:** 2-4 seconds → **50-100ms** (20-40x speedup)
- **Cost:** 20 LLM calls → **0 LLM calls** (pure embedding compute)
- **Accuracy:** LLM "understands" query deeply, but BGE-M3 achieves **87.6% NDCG@10** on BEIR
- **Consistency:** No regex parsing, deterministic scores

**Integration:**
- ✅ BGE-M3 already integrated (Sprint 87)
- ✅ Used in `skill_rcr_router.py` (lines 70-72)
- ✅ Available via `get_embedding_service()`

**Trade-offs:**
| Aspect | LLM Scoring | BGE-M3 Scoring |
|--------|-------------|----------------|
| Latency | 2-4s (20 calls) | 50-100ms (batch) |
| Cost | $0.02-0.04 | $0 (local compute) |
| Accuracy | Deep reasoning | 87.6% NDCG@10 |
| Robustness | Regex parsing | Deterministic |
| Scalability | 10 docs/min | 100+ docs/min |

**Recommendation:** Use BGE-M3 for production (fast, cost-effective, proven accuracy).

---

### Option B: Hybrid LLM + BGE-M3 Scoring (If Deep Reasoning Required)

**Use Case:** Domain-specific scoring where LLM expertise adds value

```python
# 1. Fast filtering with BGE-M3 (reduces from 20 → 5 segments)
bge_scored = bge_m3_score(segments, query)
top_5 = [s for s in bge_scored if s.relevance_score > 0.6]

# 2. Deep LLM scoring only for top candidates
for segment in top_5:
    llm_score = await llm_score_segment(segment, query, skill_prompts)
    segment.relevance_score = 0.5 * bge_score + 0.5 * llm_score
```

**Performance:**
- Latency: 50ms (BGE-M3) + 500ms (5 LLM calls) = **~600ms**
- Cost: Reduced from 20 → 5 LLM calls

---

## Parallel Worker Configuration

### Current Issue
Lines 270-278 use sequential `for` loop:
```python
# Step 3: Recursive exploration
findings = []
for segment in scored_segments:  # ❌ Sequential
    if segment.relevance_score >= self.relevance_threshold:
        finding = await self._explore_segment(segment, query, depth=1, skill=recursive_skill)
        findings.append(finding)
```

### Proposed Solution: Configurable Parallelism

**Configuration (src/core/config.py):**
```python
class RecursiveLLMSettings(BaseSettings):
    """Recursive LLM processing configuration."""

    # Parallel worker configuration
    max_parallel_workers: int = Field(
        default=1,
        description="Max parallel segment processing workers (1 for DGX Spark, 5-10 for cloud)"
    )

    # Relevance scoring method
    scoring_method: Literal["llm", "bge-m3", "hybrid"] = Field(
        default="bge-m3",
        description="Relevance scoring method"
    )

    # Worker limits per backend
    worker_limits: dict[str, int] = {
        "ollama": 1,        # DGX Spark Ollama: single-threaded
        "openai": 10,       # OpenAI: high parallelism
        "alibaba": 5,       # Alibaba DashScope: moderate
    }
```

**Implementation (recursive_llm.py):**
```python
import asyncio
from itertools import islice

async def process(self, document: str, query: str, ...):
    # ... (segmentation + scoring) ...

    # Step 3: Parallel exploration with configurable workers
    findings = []

    # Determine worker count based on LLM backend
    llm_backend = self._detect_llm_backend()
    max_workers = min(
        self.settings.max_parallel_workers,
        self.settings.worker_limits.get(llm_backend, 1)
    )

    logger.info(
        "parallel_exploration_starting",
        max_workers=max_workers,
        segment_count=len(scored_segments),
        backend=llm_backend
    )

    # Process in batches of max_workers
    relevant_segments = [
        s for s in scored_segments
        if s.relevance_score >= self.relevance_threshold
    ]

    for batch in self._batched(relevant_segments, max_workers):
        # Process batch in parallel
        batch_findings = await asyncio.gather(*[
            self._explore_segment(segment, query, depth=1, skill=recursive_skill)
            for segment in batch
        ])
        findings.extend(batch_findings)

        logger.debug(
            "batch_processed",
            batch_size=len(batch),
            findings_count=len(batch_findings)
        )

    logger.info("exploration_complete", findings_count=len(findings))

    # ... (rest of aggregation) ...

def _batched(self, iterable, n):
    """Batch iterable into chunks of size n."""
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch

def _detect_llm_backend(self) -> str:
    """Detect current LLM backend from config."""
    if hasattr(self.llm, "model") and "gpt" in self.llm.model.lower():
        return "openai"
    elif "dashscope" in str(self.llm.__class__).lower():
        return "alibaba"
    else:
        return "ollama"
```

**Environment Configuration (.env):**
```bash
# DGX Spark (Ollama local)
RECURSIVE_LLM_MAX_PARALLEL_WORKERS=1
RECURSIVE_LLM_SCORING_METHOD=bge-m3

# Cloud deployment (OpenAI/Alibaba)
RECURSIVE_LLM_MAX_PARALLEL_WORKERS=10
RECURSIVE_LLM_SCORING_METHOD=bge-m3

# Hybrid mode (fast filter + deep LLM)
RECURSIVE_LLM_SCORING_METHOD=hybrid
```

---

## Performance Projections

### Scenario 1: DGX Spark (Ollama, 1 Worker)

**Before:**
- Level 1 Scoring: 2-4s (20 LLM calls)
- Level 2 Processing: 10s × 5 segments = 50s (sequential)
- **Total: 52-54s**

**After (BGE-M3 + 1 Worker):**
- Level 1 Scoring: 50-100ms (BGE-M3 batch)
- Level 2 Processing: 10s × 5 segments = 50s (still sequential, DGX limit)
- **Total: 50-51s** (~5% improvement, but 40x faster scoring)

### Scenario 2: Cloud (OpenAI, 10 Workers)

**Before:**
- Level 1 Scoring: 2-4s (20 LLM calls)
- Level 2 Processing: 10s × 5 segments = 50s (sequential)
- **Total: 52-54s**

**After (BGE-M3 + 10 Workers):**
- Level 1 Scoring: 50-100ms (BGE-M3 batch)
- Level 2 Processing: 10s (5 segments in parallel, batch_size=5)
- **Total: 10-11s** (**5x speedup**)

---

## Implementation Priority

### Phase 1: BGE-M3 Scoring (High Impact, Low Risk) ✅ PRIORITY 1
- **Benefit:** 20-40x faster scoring, $0 cost
- **Risk:** Low (BGE-M3 already integrated and tested)
- **Files:** `src/agents/context/recursive_llm.py` (method `_score_relevance`)
- **Story Points:** 3 SP

### Phase 2: Parallel Workers (High Impact, Medium Risk) ✅ PRIORITY 2
- **Benefit:** 5x speedup on cloud models
- **Risk:** Medium (async orchestration, backend detection)
- **Files:**
  - `src/agents/context/recursive_llm.py` (method `process`)
  - `src/core/config.py` (RecursiveLLMSettings)
- **Story Points:** 5 SP

### Phase 3: Hybrid Scoring (Optional, Low Priority)
- **Benefit:** Best of both worlds (speed + depth)
- **Risk:** Medium (complexity, testing)
- **Story Points:** 3 SP

---

## References

- [Sprint 87: BGE-M3 Integration](./SPRINT_87_FEATURE_87.1_SUMMARY.md)
- [Sprint 92 Plan](./SPRINT_92_PLAN.md)
- [ADR-051: Recursive LLM Context](../adr/ADR-051-recursive-llm-context.md)
- [BGE-M3 Paper: BAAI/bge-m3](https://arxiv.org/abs/2402.03216) - 87.6% NDCG@10 on BEIR

---

**Status:** ✅ Ready for Implementation
**Created:** 2026-01-14
**Proposed By:** User Feedback + Architecture Review
