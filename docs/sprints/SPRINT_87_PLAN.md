# Sprint 87 Plan: BGE-M3 Native Hybrid Search

**Epic:** Hybrid Search Architecture Overhaul
**Technical Debt:** TD-103 (BM25 Index Desync - Critical)
**Prerequisite:** Sprint 86 Complete
**Duration:** 5-7 days
**Total Story Points:** 21 SP
**Status:** ✅ COMPLETE (2026-01-13)

---

## Sprint Goal

Migrate from separate BM25 pickle index to BGE-M3 native sparse vectors stored in Qdrant, permanently solving the BM25 desync problem and enabling valid RAGAS evaluations.

---

## Context

### Problem Statement

**Critical BM25 Desync (TD-103):**

| System | Documents | Percentage |
|--------|-----------|------------|
| Qdrant (dense vectors) | 502 chunks | 100% |
| BM25 (pickle file) | 23 docs | **4.5%** |

**Impact:** 95.5% of documents are NOT searchable via BM25, making hybrid search effectively vector-only.

### Root Cause

Custom ingestion scripts create LangGraph pipelines with only:
```
chunking_node → embedding_node → graph_extraction_node
```

BM25 is **not part of the pipeline** - must be called manually via `prepare_bm25_index()`.

### Solution: BGE-M3 Native Hybrid

**Key Insight:** BGE-M3 can generate dense (semantic) AND sparse (lexical) vectors in one call!

```python
# FlagEmbedding library
from FlagEmbedding import BGEM3FlagModel
model = BGEM3FlagModel("BAAI/bge-m3")
output = model.encode(texts, return_dense=True, return_sparse=True)
# output["dense_vecs"]: 1024D semantic embeddings
# output["lexical_weights"]: Token-level weights (like BM25 but learned)
```

### Architecture Transformation

```
BEFORE (Current - BROKEN):
  Ingestion:
    Text → SentenceTransformers → Dense (1024D) → Qdrant
    [BM25 pickle is SEPARATE and DESYNCED!]

  Retrieval:
    Query → Qdrant (dense) ─┬─ Python RRF → Results
            BM25 (pickle) ──┘  (mostly empty!)

AFTER (Sprint 87):
  Ingestion:
    Text → FlagEmbedding → Dense + Sparse → Qdrant (named vectors)
    [BOTH vectors in same Qdrant point - sync guaranteed!]

  Retrieval:
    Query → Qdrant Query API → Server-Side RRF → Results
    [Single round-trip, always in sync]
```

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 87.1 | FlagEmbedding Service | 3 | P0 | 📝 Planned |
| 87.2 | Sparse Vector Converter | 2 | P0 | 📝 Planned |
| 87.3 | Qdrant Multi-Vector Collection | 3 | P0 | 📝 Planned |
| 87.4 | Embedding Node Integration | 3 | P0 | 📝 Planned |
| 87.5 | Hybrid Retrieval with Query API | 4 | P0 | 📝 Planned |
| 87.6 | Migration Script + Zero-Downtime | 3 | P1 | 📝 Planned |
| 87.7 | RAGAS Validation (Before/After) | 3 | P1 | 📝 Planned |

**Progress:** 0/21 SP (0%)

---

## Feature 87.1: FlagEmbedding Service (3 SP)

### Description

Create new embedding service using FlagEmbedding library to generate both dense and sparse vectors in a single call.

### Implementation

**File:** `src/components/shared/flag_embedding_service.py`

```python
from FlagEmbedding import BGEM3FlagModel

class FlagEmbeddingService:
    """Multi-vector embedding service using FlagEmbedding (BGE-M3).

    Generates both dense and sparse vectors in a single forward pass:
    - Dense: 1024D semantic embeddings (identical to SentenceTransformers)
    - Sparse: Token-level lexical weights (replaces BM25)
    """

    def __init__(self, model_name: str = "BAAI/bge-m3", use_fp16: bool = True):
        self.model = BGEM3FlagModel(model_name, use_fp16=use_fp16)

    def embed_single(self, text: str) -> dict[str, Any]:
        """Embed single text, returning dense + sparse vectors.

        Returns:
            {
                "dense": list[float],       # 1024D vector
                "sparse": dict[int, float]  # {token_id: weight}
            }
        """
        output = self.model.encode([text], return_dense=True, return_sparse=True)
        return {
            "dense": output["dense_vecs"][0].tolist(),
            "sparse": self._convert_sparse(output["lexical_weights"][0]),
        }

    def embed_batch(self, texts: list[str]) -> list[dict[str, Any]]:
        """Embed batch with caching."""
        # ... (with LRU cache like SentenceTransformers)

    def _convert_sparse(self, lexical_weights: dict[str, float]) -> dict[int, float]:
        """Convert token strings to integer IDs for Qdrant."""
        return {hash(k) % (2**31): v for k, v in lexical_weights.items()}

    # Backward compatibility
    def embed_single_dense(self, text: str) -> list[float]:
        return self.embed_single(text)["dense"]
```

### Acceptance Criteria

- [ ] FlagEmbeddingService class implemented
- [ ] Dense + sparse vectors in single call
- [ ] LRU cache for deduplication (10,000 entries)
- [ ] Backward compatibility methods
- [ ] Unit tests (test_flag_embedding.py)
- [ ] Benchmark vs SentenceTransformers (<10% overhead)

### Dependencies

```bash
pip install FlagEmbedding  # ~400MB
```

---

## Feature 87.2: Sparse Vector Converter (2 SP)

### Description

Utility to convert FlagEmbedding lexical weights to Qdrant SparseVector format.

### Implementation

**File:** `src/components/shared/sparse_vector_utils.py`

```python
from qdrant_client.models import SparseVector

def lexical_to_sparse_vector(
    lexical_weights: dict[str, float],
    min_weight: float = 0.0,
    top_k: int | None = None,
) -> SparseVector:
    """Convert FlagEmbedding lexical weights to Qdrant SparseVector.

    Args:
        lexical_weights: {token_string: weight} from FlagEmbedding
        min_weight: Filter tokens below this weight
        top_k: Keep only top-k tokens by weight

    Returns:
        Qdrant SparseVector(indices=[...], values=[...])
    """
    # Filter and sort
    filtered = {k: v for k, v in lexical_weights.items() if v > min_weight}
    sorted_items = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    if top_k:
        sorted_items = sorted_items[:top_k]

    # Convert to integer indices
    indices = [hash(k) % (2**31) for k, _ in sorted_items]
    values = [v for _, v in sorted_items]

    return SparseVector(indices=indices, values=values)
```

### Acceptance Criteria

- [ ] lexical_to_sparse_vector function
- [ ] min_weight filtering
- [ ] top_k truncation
- [ ] Unit tests

---

## Feature 87.3: Qdrant Multi-Vector Collection (3 SP)

### Description

Create Qdrant collection with named vectors (dense + sparse) using the new schema.

### Implementation

**File:** `src/components/vector_search/multi_vector_collection.py`

```python
from qdrant_client.models import (
    Distance, SparseIndexParams, SparseVectorParams, VectorParams
)

class MultiVectorCollectionManager:
    """Manager for Qdrant collections with named vectors."""

    async def create_multi_vector_collection(
        self,
        collection_name: str,
        dense_dim: int = 1024,
    ) -> None:
        """Create collection with dense + sparse vector support."""
        await self.client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(size=dense_dim, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(index=SparseIndexParams()),
            },
        )
```

### Schema

```yaml
# New Collection Schema (aegis_chunks_v2)
vectors:
  dense:
    size: 1024
    distance: Cosine
sparse_vectors:
  sparse:
    index:
      on_disk: true
```

### Acceptance Criteria

- [ ] MultiVectorCollectionManager class
- [ ] create_multi_vector_collection method
- [ ] collection_has_sparse check
- [ ] Unit tests

---

## Feature 87.4: Embedding Node Integration (3 SP)

### Description

Update embedding_node to generate and store both dense and sparse vectors.

### Implementation

**File:** `src/components/ingestion/nodes/vector_embedding.py` (modified)

```python
async def embedding_node(state: IngestionState) -> IngestionState:
    """Generate embeddings + upload with dense + sparse vectors."""

    # Sprint 87: Use FlagEmbedding for dense + sparse
    try:
        from src.components.shared.flag_embedding_service import get_flag_embedding_service
        embedding_service = get_flag_embedding_service()
        use_sparse = True
    except ImportError:
        # Fallback to dense-only
        from src.components.shared.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        use_sparse = False

    # Generate embeddings
    embeddings = await embedding_service.embed_batch(texts)
    # embeddings[i] = {"dense": [...], "sparse": {...}}

    # Create points with named vectors
    points = []
    for chunk, embedding in zip(chunks, embeddings):
        point = PointStruct(
            id=chunk_id,
            vector={"dense": embedding["dense"]},
            payload=payload,
        )
        points.append(point)

    # Upsert with sparse vectors (separate API call)
    await upsert_with_sparse(collection, points, [e["sparse"] for e in embeddings])
```

### Acceptance Criteria

- [ ] embedding_node uses FlagEmbeddingService
- [ ] Fallback to dense-only if unavailable
- [ ] Points contain both dense and sparse vectors
- [ ] Logging shows sparse vector stats
- [ ] Integration tests

---

## Feature 87.5: Hybrid Retrieval with Query API (4 SP)

### Description

Replace Python-side RRF with Qdrant Query API for server-side fusion.

### Implementation

**File:** `src/components/vector_search/multi_vector_search.py`

```python
from qdrant_client.models import Fusion, FusionQuery, Prefetch

class MultiVectorHybridSearch:
    """Hybrid search using Qdrant Query API with server-side RRF."""

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        prefetch_limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search with server-side RRF fusion."""

        # 1. Embed query (dense + sparse)
        query_embedding = self.embedding_service.embed_single(query)

        # 2. Execute Query API with prefetch + fusion
        results = await self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                # Dense (semantic) search
                Prefetch(
                    query=query_embedding["dense"],
                    using="dense",
                    limit=prefetch_limit,
                ),
                # Sparse (lexical) search
                Prefetch(
                    query=dict_to_sparse_vector(query_embedding["sparse"]),
                    using="sparse",
                    limit=prefetch_limit,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),  # Server-side RRF!
            limit=top_k,
        )

        return self._format_results(results)
```

### Query API Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    QDRANT QUERY API                             │
├────────────────────────────────────────────────────────────────┤
│  1. Prefetch Dense     2. Prefetch Sparse                      │
│     (HNSW Index)          (Sparse Index)                       │
│     Top-50 by cos         Top-50 by IDF                        │
│           │                     │                              │
│           └─────────┬───────────┘                              │
│                     ▼                                          │
│            3. Server-Side RRF                                  │
│               (k=60, no network)                               │
│                     ▼                                          │
│            4. Return Top-K                                     │
│               (Single Round-Trip)                              │
└────────────────────────────────────────────────────────────────┘
```

### Acceptance Criteria

- [ ] MultiVectorHybridSearch class
- [ ] Server-side RRF via Query API
- [ ] Namespace filtering support
- [ ] Fallback to dense-only
- [ ] Integration with existing HybridSearch API
- [ ] Latency benchmark (<100ms for hybrid)

---

## Feature 87.6: Migration Script + Zero-Downtime (3 SP)

### Description

Script to migrate existing collection to multi-vector format with zero downtime.

### Strategy: Blue-Green Deployment

```
1. Create aegis_chunks_v2 (new schema)
2. Re-embed all documents with FlagEmbedding
3. Validate counts + random sample search
4. Atomic alias switch: aegis_chunks → v2
5. Keep v1 as backup (7 days)
```

### Implementation

**File:** `scripts/migrate_to_multi_vector.py`

```bash
# Dry run (validation only)
python scripts/migrate_to_multi_vector.py --dry-run

# Execute migration
python scripts/migrate_to_multi_vector.py --execute

# Rollback if needed
python scripts/migrate_to_multi_vector.py --rollback
```

### Acceptance Criteria

- [ ] Migration script with dry-run mode
- [ ] Blue-green deployment with alias
- [ ] Validation (count match, sample search)
- [ ] Rollback capability
- [ ] Progress logging
- [ ] Error handling

---

## Feature 87.7: RAGAS Validation (Before/After) (3 SP)

### Description

Run RAGAS evaluation before and after migration to validate quality.

### Validation Script

**File:** `scripts/validate_migration_ragas.py`

```python
async def validate_migration():
    """Run before/after RAGAS comparison."""

    # 1. Retrieve with OLD system (dense + BM25 pickle)
    old_results = await old_hybrid_search.search(test_questions)

    # 2. Retrieve with NEW system (dense + sparse Qdrant)
    new_results = await new_multi_vector_search.search(test_questions)

    # 3. Evaluate both with RAGAS
    old_scores = evaluate(old_results, metrics=[context_precision, context_recall])
    new_scores = evaluate(new_results, metrics=[context_precision, context_recall])

    # 4. Compare
    return {
        "old": old_scores,
        "new": new_scores,
        "delta": {k: new_scores[k] - old_scores[k] for k in old_scores},
    }
```

### Success Criteria

| Metric | Minimum | Target |
|--------|---------|--------|
| Context Precision | No regression (≥0%) | +5% improvement |
| Context Recall | No regression (≥0%) | +10% improvement |
| Latency | No regression (≤110%) | -20% improvement |

### Acceptance Criteria

- [ ] Before/after RAGAS comparison script
- [ ] Automated pass/fail thresholds
- [ ] Detailed per-question breakdown
- [ ] Results logged to RAGAS_JOURNEY.md

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| FlagEmbedding Service | `src/components/shared/flag_embedding_service.py` | Dense + sparse embeddings |
| Sparse Vector Utils | `src/components/shared/sparse_vector_utils.py` | Conversion utilities |
| Multi-Vector Collection | `src/components/vector_search/multi_vector_collection.py` | Collection manager |
| Multi-Vector Search | `src/components/vector_search/multi_vector_search.py` | Query API hybrid search |
| Migration Script | `scripts/migrate_to_multi_vector.py` | Zero-downtime migration |
| RAGAS Validation | `scripts/validate_migration_ragas.py` | Before/after comparison |
| Unit Tests | `tests/unit/embedding/test_flag_embedding.py` | FlagEmbedding tests |
| Integration Tests | `tests/integration/search/test_multi_vector.py` | End-to-end tests |
| Technical Debt Doc | `docs/technical-debt/TD-103_BM25_INDEX_DESYNC.md` | Problem documentation |
| ADR-042 | `docs/adr/ADR-042-bge-m3-native-hybrid.md` | Architecture decision |

---

## Success Criteria

- [ ] FlagEmbedding generates dense + sparse vectors
- [ ] Qdrant collection has named vectors (dense + sparse)
- [ ] Query API hybrid search working
- [ ] Zero-downtime migration completed
- [ ] RAGAS scores: No regression, ideally +5-10%
- [ ] BM25 pickle file eliminated
- [ ] All ingestion pipelines use new embedding service
- [ ] TD-103 marked as RESOLVED

---

## Dependencies

### Prerequisites

- **Sprint 86 Complete:** Coreference resolution, cascade monitoring
- **Qdrant 1.11+:** Query API, sparse vectors (✅ Have v1.11.0)
- **FlagEmbedding:** `pip install FlagEmbedding` (~400MB)

### Follow-Up Sprints

- **Sprint 88:** RAGAS Phase 2 (valid hybrid search now!)
- **Sprint 89:** RAGAS Phase 3 (visual assets)

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| FlagEmbedding fails | Low | High | Feature flag, fallback to SentenceTransformers |
| Migration data loss | Medium | High | Blue-green deployment, backup collection |
| RAGAS regression | Low | High | Before/after validation, rollback if needed |
| Latency increase | Low | Medium | Benchmark, optimize prefetch limits |

---

## References

- [BGE-M3 Paper](https://arxiv.org/abs/2402.03216)
- [Qdrant Sparse Vectors](https://qdrant.tech/documentation/concepts/vectors/#sparse-vectors)
- [Qdrant Query API](https://qdrant.tech/documentation/concepts/search/#query-api)
- [FlagEmbedding GitHub](https://github.com/FlagOpen/FlagEmbedding)
- [TD-103: BM25 Index Desync](../technical-debt/TD-103_BM25_INDEX_DESYNC.md)

---

**Previous Sprint:** Sprint 86 (DSPy MIPROv2 Optimization)
**Next Sprint:** Sprint 88 (RAGAS Phase 2 - Structured Data)

---

## Sprint Completion Summary (2026-01-13)

### Features Completed

| Feature | Status | Lines of Code | Tests |
|---------|--------|---------------|-------|
| 87.1 FlagEmbedding Service | ✅ | 686 | 5 |
| 87.2 Sparse Vector Converter | ✅ | 317 | 4 |
| 87.3 Multi-Vector Collection | ✅ | 531 | 23 |
| 87.4 Embedding Node Integration | ✅ | ~150 | 6 |
| 87.5 Hybrid Retrieval Query API | ✅ | 576 | 23 |
| 87.6 Migration Script | ⏭️ SKIPPED | - | - |
| 87.7 RAGAS Validation | ✅ Ready | - | - |

**Total:** ~2,260 LOC, 61 tests

### Key Achievements

1. **BM25 Desync Eliminated**: TD-103 + TD-074 resolved
2. **Native Hybrid Search**: Dense + Sparse in same Qdrant point
3. **Server-Side RRF**: Query API fusion (single round-trip)
4. **Backward Compatible**: Existing collections continue to work
5. **Configuration-Driven**: `EMBEDDING_BACKEND=flag-embedding`

### Files Created/Modified

```
NEW:
  src/components/shared/flag_embedding_service.py      (686 LOC)
  src/components/shared/sparse_vector_utils.py        (317 LOC)
  src/components/vector_search/multi_vector_collection.py (531 LOC)
  src/components/vector_search/multi_vector_search.py (576 LOC)
  tests/unit/.../test_multi_vector_collection.py      (23 tests)
  tests/unit/.../test_multi_vector_search.py          (23 tests)
  tests/unit/.../test_vector_embedding_multi_vector.py (6 tests)

MODIFIED:
  src/components/ingestion/nodes/vector_embedding.py
  src/components/shared/embedding_factory.py
  src/core/config.py
  pyproject.toml (FlagEmbedding ^1.2.0)

DOCS:
  docs/technical-debt/TD-103_BM25_INDEX_DESYNC.md (NEW)
  docs/technical-debt/TD-074_BM25_CACHE_DISCREPANCY.md (RESOLVED)
  docs/technical-debt/TD_INDEX.md (updated)
```

### Docker Update

- **Image:** `aegis-rag-api-cuda:latest`
- **FlagEmbedding Version:** 1.3.5
- **Build Date:** 2026-01-13

### How to Enable Multi-Vector Mode

```bash
# In .env file:
EMBEDDING_BACKEND=flag-embedding

# Then restart API and re-ingest documents
docker compose -f docker-compose.dgx-spark.yml up -d api
```

### Technical Debt Status

- **TD-103 (BM25 Index Desync):** ✅ RESOLVED
- **TD-074 (BM25 Cache Discrepancy):** ✅ RESOLVED
- **Active TD Count:** 5 → 3 items (-2)

### Next Steps (Sprint 88)

With working hybrid search, RAGAS Phase 2 (Structured Data) can now proceed with valid baseline metrics.
