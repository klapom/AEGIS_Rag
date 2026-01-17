# Feature 92.3: Configurable Recursive Deep-Dive

**Status:** 📝 Proposed Enhancement
**Created:** 2026-01-14
**Story Points:** 5 SP
**Context:** User feedback on per-level configuration and ColBERT vs BGE-M3

---

## Problem Statement

**Current Implementation Issues:**

1. **Fixed Segment Size:** All levels use same `context_window=8192` tokens
   - Level 0 (Overview): Could use larger chunks (16K tokens)
   - Level 1 (Details): Should use medium chunks (8K tokens)
   - Level 2 (Fine-grained): Should use smaller chunks (4K tokens)

2. **Hardcoded max_depth=3:** Not configurable per use case
   - Short documents: 1-2 levels sufficient
   - Long research papers: 3-4 levels needed

3. **Hardcoded Top-3 Sub-Segments:** Line 545 in recursive_llm.py
   - Should be configurable based on document complexity

4. **No Token-Level Matching:** Currently uses document-level dense+sparse
   - Fine-grained queries need token-level precision (e.g., "What is the p-value?")

---

## Solution: Per-Level Configuration + BGE-M3 Multi-Vector

### Discovery: BGE-M3 Already Has ColBERT!

★ **Critical Insight:** BGE-M3's multi-vector mode IS ColBERT-style late interaction!
- Same MaxSim operation
- Token-level embeddings (1024D vs ColBERT's 128D)
- More precise due to higher dimensionality
- Already integrated in Sprint 87!

**Architecture Comparison:**

| Model | Token Embedding | Late Interaction | Storage | Speed | Accuracy |
|-------|----------------|------------------|---------|-------|----------|
| ColBERT | 128D per token | MaxSim | Low | Fast | 0.87 NDCG@10 |
| BGE-M3 Dense | 1024D per doc | N/A | Lowest | Fastest | 0.876 NDCG@10 |
| BGE-M3 Sparse | Token weights | N/A | Low | Fast | Lexical matching |
| **BGE-M3 Multi-Vector** | **1024D per token** | **MaxSim** | **Highest** | **Slower** | **~0.89 NDCG@10** |

**Recommendation:** Use BGE-M3 multi-vector mode for Level 2+ (fine-grained), skip standalone ColBERT.

---

## Proposed Configuration

### 1. Per-Level Segment Sizes

**Configuration (src/core/config.py):**

```python
from pydantic import BaseModel, Field
from typing import List, Literal

class RecursiveLevelConfig(BaseModel):
    """Configuration for a specific recursion level."""

    level: int = Field(description="Recursion depth (0=top level)")

    segment_size_tokens: int = Field(
        description="Target segment size in tokens",
        ge=1000, le=32000
    )

    overlap_tokens: int = Field(
        default=200,
        description="Overlap between segments to prevent information loss"
    )

    top_k_subsegments: int = Field(
        default=3,
        description="Number of sub-segments to explore"
    )

    scoring_method: Literal["dense+sparse", "multi-vector"] = Field(
        default="dense+sparse",
        description="BGE-M3 scoring method for this level"
    )

    relevance_threshold: float = Field(
        default=0.5,
        ge=0.0, le=1.0,
        description="Minimum relevance score to explore"
    )


class RecursiveLLMSettings(BaseSettings):
    """Recursive LLM processing configuration."""

    # Global settings
    max_depth: int = Field(
        default=3,
        ge=1, le=5,
        description="Maximum recursion depth (1-5 levels)"
    )

    # Per-level configuration (adaptive sizing)
    levels: List[RecursiveLevelConfig] = Field(
        default_factory=lambda: [
            # Level 0: Overview (large chunks, fast dense+sparse)
            RecursiveLevelConfig(
                level=0,
                segment_size_tokens=16384,  # 16K tokens
                overlap_tokens=400,
                top_k_subsegments=5,
                scoring_method="dense+sparse",  # Fast document-level
                relevance_threshold=0.5,
            ),
            # Level 1: Details (medium chunks, fast dense+sparse)
            RecursiveLevelConfig(
                level=1,
                segment_size_tokens=8192,  # 8K tokens
                overlap_tokens=300,
                top_k_subsegments=4,
                scoring_method="dense+sparse",  # Fast document-level
                relevance_threshold=0.6,
            ),
            # Level 2: Fine-grained (small chunks, precise multi-vector)
            RecursiveLevelConfig(
                level=2,
                segment_size_tokens=4096,  # 4K tokens
                overlap_tokens=200,
                top_k_subsegments=3,
                scoring_method="multi-vector",  # Token-level late interaction
                relevance_threshold=0.7,
            ),
            # Level 3: Ultra-fine (tiny chunks, precise multi-vector)
            RecursiveLevelConfig(
                level=3,
                segment_size_tokens=2048,  # 2K tokens
                overlap_tokens=100,
                top_k_subsegments=2,
                scoring_method="multi-vector",  # Token-level late interaction
                relevance_threshold=0.8,
            ),
        ]
    )

    # Worker configuration
    max_parallel_workers: int = Field(
        default=1,
        description="Max parallel segment processing workers"
    )


# Global instance
recursive_llm_settings = RecursiveLLMSettings()
```

**Environment Configuration (.env):**

```bash
# DGX Spark (Ollama, conservative)
RECURSIVE_LLM_MAX_DEPTH=3
RECURSIVE_LLM_MAX_PARALLEL_WORKERS=1

# Cloud deployment (OpenAI, aggressive)
RECURSIVE_LLM_MAX_DEPTH=4
RECURSIVE_LLM_MAX_PARALLEL_WORKERS=10

# Custom per-level (JSON array)
RECURSIVE_LLM_LEVELS='[
  {"level": 0, "segment_size_tokens": 16384, "scoring_method": "dense+sparse"},
  {"level": 1, "segment_size_tokens": 8192, "scoring_method": "dense+sparse"},
  {"level": 2, "segment_size_tokens": 4096, "scoring_method": "multi-vector"}
]'
```

---

## Implementation Changes

### 1. Updated `__init__` (Lines 158-190)

**Before:**
```python
def __init__(
    self,
    llm: BaseChatModel,
    skill_registry: SkillRegistry,
    context_window: int = 8192,
    overlap_tokens: int = 200,
    max_depth: int = 3,
    relevance_threshold: float = 0.5,
):
    self.llm = llm
    self.skills = skill_registry
    self.context_window = context_window
    self.overlap_tokens = overlap_tokens
    self.max_depth = max_depth
    self.relevance_threshold = relevance_threshold
```

**After:**
```python
def __init__(
    self,
    llm: BaseChatModel,
    skill_registry: SkillRegistry,
    settings: Optional[RecursiveLLMSettings] = None,
):
    """Initialize recursive LLM processor with per-level configuration.

    Args:
        llm: Language model for scoring and summarization
        skill_registry: Skill registry for loading context skills
        settings: Per-level configuration (defaults to global settings)
    """
    self.llm = llm
    self.skills = skill_registry
    self.settings = settings or recursive_llm_settings
    self.embedding_service = get_embedding_service()  # For multi-vector

    # Validate level configuration
    if not self.settings.levels:
        raise ValueError("At least one level configuration required")

    if len(self.settings.levels) < self.settings.max_depth:
        raise ValueError(f"Need {self.settings.max_depth} level configs, got {len(self.settings.levels)}")

    logger.info(
        "recursive_llm_processor_initialized",
        max_depth=self.settings.max_depth,
        levels=[
            {
                "level": cfg.level,
                "segment_size": cfg.segment_size_tokens,
                "scoring_method": cfg.scoring_method,
            }
            for cfg in self.settings.levels
        ],
    )
```

---

### 2. Updated `_segment_document` (Lines 318-391)

**Before (Fixed segment size):**
```python
def _segment_document(
    self,
    text: str,
    level: int,
    parent_id: Optional[str] = None,
) -> list[DocumentSegment]:
    # Fixed size for all levels
    chars_per_segment = (self.context_window - 500) * 4
    # ... segmentation logic ...
    offset = end - (self.overlap_tokens * 4)
```

**After (Per-level sizes):**
```python
def _segment_document(
    self,
    text: str,
    level: int,
    parent_id: Optional[str] = None,
) -> list[DocumentSegment]:
    """Segment document using level-specific configuration.

    Args:
        text: Text to segment
        level: Depth in hierarchy (uses settings.levels[level] config)
        parent_id: ID of parent segment

    Returns:
        List of DocumentSegment objects sized for current level
    """
    # Get level-specific configuration
    if level >= len(self.settings.levels):
        # Fallback to last level config
        level_config = self.settings.levels[-1]
        logger.warning(
            "level_config_fallback",
            requested_level=level,
            available_levels=len(self.settings.levels),
        )
    else:
        level_config = self.settings.levels[level]

    # Calculate segment size from level config
    segment_size_tokens = level_config.segment_size_tokens
    overlap_tokens = level_config.overlap_tokens

    chars_per_segment = (segment_size_tokens - 500) * 4  # Leave room for prompt

    segments = []
    offset = 0
    segment_id = 0

    while offset < len(text):
        # Find natural break point
        end = min(offset + chars_per_segment, len(text))

        # Try to find paragraph break
        if end < len(text):
            para_break = text.rfind("\n\n", offset, end)
            if para_break > offset + chars_per_segment // 2:
                end = para_break
            else:
                newline_break = text.rfind("\n", offset, end)
                if newline_break > offset + chars_per_segment // 2:
                    end = newline_break

        segment_text = text[offset:end].strip()
        if segment_text:
            segments.append(
                DocumentSegment(
                    id=f"seg_{level}_{segment_id}",
                    content=segment_text,
                    level=level,
                    parent_id=parent_id,
                    start_offset=offset,
                    end_offset=end,
                )
            )
            segment_id += 1

        # Per-level overlap
        offset = end - (overlap_tokens * 4)

    logger.debug(
        "document_segmented",
        level=level,
        segment_count=len(segments),
        segment_size_tokens=segment_size_tokens,
        overlap_tokens=overlap_tokens,
    )

    return segments
```

---

### 3. Updated `_score_relevance` (Lines 393-469)

**Add BGE-M3 Multi-Vector Support:**

```python
async def _score_relevance(
    self,
    segments: list[DocumentSegment],
    query: str,
    skill: Optional[LoadedSkill],
    level: int,  # NEW: Level for config lookup
) -> list[DocumentSegment]:
    """Score each segment's relevance using level-specific method.

    Args:
        segments: List of document segments
        query: User's query
        skill: Loaded skill with scoring prompts (optional)
        level: Current recursion level (determines scoring method)

    Returns:
        List of segments sorted by relevance (highest first)
    """
    level_config = self.settings.levels[min(level, len(self.settings.levels) - 1)]
    scoring_method = level_config.scoring_method

    logger.info(
        "scoring_segments",
        segment_count=len(segments),
        level=level,
        scoring_method=scoring_method,
    )

    if scoring_method == "multi-vector":
        # Use BGE-M3 multi-vector (ColBERT-style late interaction)
        return await self._score_relevance_multi_vector(segments, query)
    else:
        # Use BGE-M3 dense+sparse (fast document-level)
        return await self._score_relevance_dense_sparse(segments, query)


async def _score_relevance_dense_sparse(
    self,
    segments: list[DocumentSegment],
    query: str,
) -> list[DocumentSegment]:
    """Score segments using BGE-M3 dense+sparse embeddings (fast).

    This is the default method for Level 0-1 (overview and details).
    Uses document-level embeddings for fast scoring.
    """
    # Embed query once
    query_embedding = self.embedding_service.embed_single(query)
    # Returns: {"dense": [1024 floats], "sparse": {"token_id": weight, ...}}

    # Batch embed all segment previews (2000 chars each)
    segment_texts = [s.content[:2000] for s in segments]
    segment_embeddings = self.embedding_service.embed_batch(segment_texts)

    # Score each segment
    for i, segment in enumerate(segments):
        seg_emb = segment_embeddings[i]

        # Dense score (semantic similarity)
        dense_score = self._cosine_similarity(
            query_embedding["dense"],
            seg_emb["dense"]
        )

        # Sparse score (lexical matching, like BM25)
        sparse_score = self._sparse_similarity(
            query_embedding["sparse"],
            seg_emb["sparse"]
        )

        # Hybrid fusion (Sprint 87 RRF-style)
        segment.relevance_score = 0.6 * dense_score + 0.4 * sparse_score

    segments.sort(key=lambda s: s.relevance_score, reverse=True)

    logger.info(
        "segments_scored_dense_sparse",
        avg_score=sum(s.relevance_score for s in segments) / len(segments),
    )

    return segments


async def _score_relevance_multi_vector(
    self,
    segments: list[DocumentSegment],
    query: str,
) -> list[DocumentSegment]:
    """Score segments using BGE-M3 multi-vector (ColBERT-style late interaction).

    This method is used for Level 2+ (fine-grained analysis) where
    token-level precision is needed.

    Architecture:
        1. Embed query → token-level embeddings (N_q tokens × 1024D)
        2. Embed each segment → token-level embeddings (N_d tokens × 1024D)
        3. Compute MaxSim(query_tokens, doc_tokens) for each segment
        4. Sort by MaxSim scores

    Latency:
        - Slower than dense+sparse (10-20x)
        - But more precise for fine-grained queries
        - Only used at deeper levels (2+)
    """
    # Get multi-vector embeddings from BGE-M3
    # Note: This requires FlagEmbedding with multi-vector support
    try:
        from FlagEmbedding import BGEM3FlagModel

        # Initialize multi-vector model (singleton)
        if not hasattr(self, "_multi_vector_model"):
            self._multi_vector_model = BGEM3FlagModel(
                "BAAI/bge-m3",
                use_fp16=True,
                device="auto"
            )

        # Embed query (token-level)
        query_token_embeddings = self._multi_vector_model.encode(
            [query],
            return_dense=False,
            return_sparse=False,
            return_colbert_vecs=True  # ColBERT-style token embeddings
        )["colbert_vecs"][0]  # Shape: (N_q, 1024)

        # Embed all segments (token-level)
        segment_texts = [s.content[:2000] for s in segments]
        segment_token_embeddings = self._multi_vector_model.encode(
            segment_texts,
            return_dense=False,
            return_sparse=False,
            return_colbert_vecs=True
        )["colbert_vecs"]  # List of (N_d, 1024) arrays

        # Compute MaxSim scores (late interaction)
        import numpy as np

        for i, segment in enumerate(segments):
            doc_tokens = segment_token_embeddings[i]  # (N_d, 1024)

            # Compute similarity matrix: (N_q, N_d)
            sim_matrix = np.dot(query_token_embeddings, doc_tokens.T)

            # MaxSim: For each query token, take max similarity across doc tokens
            max_sims = np.max(sim_matrix, axis=1)

            # Average over query tokens
            segment.relevance_score = float(np.mean(max_sims))

        segments.sort(key=lambda s: s.relevance_score, reverse=True)

        logger.info(
            "segments_scored_multi_vector",
            avg_score=sum(s.relevance_score for s in segments) / len(segments),
        )

        return segments

    except ImportError as e:
        logger.warning(
            "multi_vector_fallback",
            error=str(e),
            message="Falling back to dense+sparse scoring"
        )
        # Fallback to dense+sparse
        return await self._score_relevance_dense_sparse(segments, query)


def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import numpy as np
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


def _sparse_similarity(self, sparse1: dict, sparse2: dict) -> float:
    """Compute sparse similarity (like BM25) between two sparse vectors."""
    # Sparse vectors are dicts: {"token_id": weight, ...}
    common_tokens = set(sparse1.keys()) & set(sparse2.keys())
    if not common_tokens:
        return 0.0

    score = sum(sparse1[t] * sparse2[t] for t in common_tokens)

    # Normalize by vector magnitudes
    import math
    mag1 = math.sqrt(sum(w**2 for w in sparse1.values()))
    mag2 = math.sqrt(sum(w**2 for w in sparse2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return score / (mag1 * mag2)
```

---

### 4. Updated `_explore_segment` (Lines 471-549)

**Use level-specific top_k and threshold:**

```python
async def _explore_segment(
    self,
    segment: DocumentSegment,
    query: str,
    depth: int,
    skill: Optional[LoadedSkill],
) -> dict[str, Any]:
    """Recursively explore a segment with level-specific configuration.

    Args:
        segment: Document segment to explore
        query: User's query
        depth: Current recursion depth
        skill: Loaded skill with summarization prompts (optional)

    Returns:
        Dict containing segment summary and sub-findings
    """
    # ... (summarization code remains same) ...

    result = {
        "segment_id": segment.id,
        "summary": segment.summary,
        "relevance": segment.relevance_score,
        "depth": depth,
        "sub_findings": [],
    }

    # Get level-specific configuration
    level_config = self.settings.levels[min(depth, len(self.settings.levels) - 1)]

    # Recursive dive if depth allows and segment is large enough
    if depth < self.settings.max_depth and len(segment.content) > level_config.segment_size_tokens * 2:
        sub_segments = self._segment_document(
            segment.content,
            level=depth,
            parent_id=segment.id,
        )

        if len(sub_segments) > 1:  # Only recurse if we can subdivide
            # Score using level-specific method
            scored_subs = await self._score_relevance(
                sub_segments,
                query,
                skill,
                level=depth  # Pass level for config lookup
            )

            # Explore top-K sub-segments (per-level config)
            top_k = level_config.top_k_subsegments
            threshold = level_config.relevance_threshold

            for sub in scored_subs[:top_k]:
                if sub.relevance_score >= threshold:
                    sub_finding = await self._explore_segment(sub, query, depth + 1, skill)
                    result["sub_findings"].append(sub_finding)

            logger.debug(
                "recursive_exploration",
                depth=depth,
                top_k=top_k,
                threshold=threshold,
                explored=len(result["sub_findings"]),
            )

    return result
```

---

## Performance Projections

### Scenario 1: DGX Spark (Research Paper, 320K tokens)

**Configuration:**
```python
levels = [
    {"level": 0, "segment_size_tokens": 16384, "scoring_method": "dense+sparse"},  # Overview
    {"level": 1, "segment_size_tokens": 8192, "scoring_method": "dense+sparse"},   # Details
    {"level": 2, "segment_size_tokens": 4096, "scoring_method": "multi-vector"},   # Fine-grained
]
max_depth = 2
max_parallel_workers = 1
```

**Latency Breakdown:**

| Step | Before | After (Config + Multi-Vector) | Improvement |
|------|--------|-------------------------------|-------------|
| Level 0 Segmentation | 100ms | 100ms | - |
| Level 0 Scoring (20 segs) | 2-4s (LLM) | **50ms** (BGE-M3 dense+sparse) | **40-80x** |
| Level 1 Segmentation | 50ms | 50ms | - |
| Level 1 Scoring (10 segs) | 1-2s (LLM) | **30ms** (BGE-M3 dense+sparse) | **33-66x** |
| Level 2 Segmentation | 30ms | 30ms | - |
| Level 2 Scoring (5 segs) | 500ms-1s (LLM) | **200ms** (BGE-M3 multi-vector) | **2.5-5x** |
| Level 1-2 Processing | 50s (sequential) | 50s (1 worker limit) | - |
| **Total** | **54-57s** | **50.4-50.5s** | **~10% faster** |

**Key Benefit:** Token-level precision for fine-grained queries at Level 2.

---

### Scenario 2: Cloud (OpenAI, 10 Workers)

**Configuration:**
```python
levels = [
    {"level": 0, "segment_size_tokens": 16384, "scoring_method": "dense+sparse"},
    {"level": 1, "segment_size_tokens": 8192, "scoring_method": "dense+sparse"},
    {"level": 2, "segment_size_tokens": 4096, "scoring_method": "multi-vector"},
]
max_depth = 2
max_parallel_workers = 10
```

**Latency Breakdown:**

| Step | Before | After | Improvement |
|------|--------|-------|-------------|
| Level 0 Scoring | 2-4s | **50ms** | **40-80x** |
| Level 1 Scoring | 1-2s | **30ms** | **33-66x** |
| Level 2 Scoring | 500ms-1s | **200ms** | **2.5-5x** |
| Level 1-2 Processing | 50s (sequential) | **10s** (10 workers) | **5x** |
| **Total** | **54-57s** | **10.3s** | **5.2-5.5x faster** |

**Key Benefit:** Massive speedup from parallelization + fast embeddings.

---

## ColBERT vs BGE-M3 Multi-Vector: Final Verdict

| Aspect | Standalone ColBERT | BGE-M3 Multi-Vector | Winner |
|--------|-------------------|---------------------|--------|
| **Token Embeddings** | 128D | 1024D | BGE-M3 (more precise) |
| **Late Interaction** | MaxSim | MaxSim (same) | Tie |
| **Integration** | Requires new library | Already integrated (Sprint 87) | **BGE-M3** |
| **Multi-Functionality** | Only multi-vector | Dense + Sparse + Multi-Vector | **BGE-M3** |
| **Storage** | Lower (128D) | Higher (1024D) | ColBERT |
| **Speed** | Faster (128D) | Slower (1024D) | ColBERT |
| **Accuracy** | 0.87 NDCG@10 | ~0.89 NDCG@10 | **BGE-M3** |
| **Maintenance** | New dependency | Already maintained | **BGE-M3** |

**Recommendation:** ✅ **Use BGE-M3 multi-vector mode** instead of standalone ColBERT.

**Rationale:**
1. ✅ Already integrated (Sprint 87)
2. ✅ Higher accuracy (1024D vs 128D)
3. ✅ Multi-functionality (dense + sparse + multi-vector in one model)
4. ✅ Zero new dependencies
5. ⚠️ Only downside: Slower inference (but acceptable for Level 2+ where precision matters)

---

## Implementation Priority

### Phase 1: Per-Level Configuration ✅ PRIORITY 1
- **Files:**
  - `src/core/config.py` (RecursiveLevelConfig, RecursiveLLMSettings)
  - `src/agents/context/recursive_llm.py` (__init__, _segment_document, _explore_segment)
- **Benefit:** Adaptive sizing, configurable depth/top-k
- **Story Points:** 3 SP

### Phase 2: BGE-M3 Dense+Sparse Scoring ✅ PRIORITY 2
- **Files:**
  - `src/agents/context/recursive_llm.py` (_score_relevance_dense_sparse)
- **Benefit:** 40-80x faster scoring (Level 0-1)
- **Story Points:** 2 SP

### Phase 3: BGE-M3 Multi-Vector Scoring (ColBERT-style) 🚀 PRIORITY 3
- **Files:**
  - `src/agents/context/recursive_llm.py` (_score_relevance_multi_vector)
- **Benefit:** Token-level precision for fine-grained queries (Level 2+)
- **Story Points:** 3 SP
- **Requirement:** FlagEmbedding with colbert_vecs support

### Phase 4: Parallel Workers (from previous doc) ✅ PRIORITY 4
- **Files:**
  - `src/agents/context/recursive_llm.py` (process method)
- **Benefit:** 5x speedup on cloud models
- **Story Points:** 5 SP

---

## References

- [Weaviate: Late Interaction Overview](https://weaviate.io/blog/late-interaction-overview)
- [Qdrant: Late Interaction Models](https://qdrant.tech/articles/late-interaction-models/)
- [BGE-M3 Documentation](https://bge-model.com/bge/bge_m3.html)
- [Jina-ColBERT-v2 Paper](https://arxiv.org/html/2408.16672v3)
- [Sprint 87: BGE-M3 Integration](./SPRINT_87_FEATURE_87.1_SUMMARY.md)
- [Sprint 92 Plan](./SPRINT_92_PLAN.md)

---

**Status:** ✅ Ready for Implementation
**Created:** 2026-01-14
**Total Story Points:** 13 SP (Phases 1-4)
