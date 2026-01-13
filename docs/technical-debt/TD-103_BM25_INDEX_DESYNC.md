# TD-103: BM25 Index Desync (Critical)

**Priority:** P0 - Critical
**Story Points:** 21 SP
**Target Sprint:** Sprint 87
**Status:** ✅ RESOLVED (Sprint 87)

---

## Problem Statement

**Critical desync between Qdrant and BM25 indexes:**

| System | Documents | Percentage |
|--------|-----------|------------|
| Qdrant (dense vectors) | 502 chunks | 100% |
| BM25 (pickle file) | 23 docs | **4.5%** |

This means **95.5% of documents are NOT searchable via keyword (BM25)**, severely degrading hybrid search quality.

---

## Root Cause Analysis

### Architecture Issue

```
┌─────────────────────────────────────────────────────────────────┐
│                   INGESTION PIPELINE (LangGraph)                │
├─────────────────────────────────────────────────────────────────┤
│  chunking_node → embedding_node → graph_extraction_node         │
│                        │                                        │
│                        ▼                                        │
│              ┌─────────────────┐                                │
│              │ Qdrant Upload   │ ✅ Always updated              │
│              │ (dense vectors) │                                │
│              └─────────────────┘                                │
│                                                                 │
│  ╔═════════════════════════════════════════════════════════════╗│
│  ║ BM25 Index is NOT part of pipeline!                        ║│
│  ║ Must be manually updated via prepare_bm25_index()          ║│
│  ╚═════════════════════════════════════════════════════════════╝│
│                                                                 │
│              ┌─────────────────┐                                │
│              │ BM25 Pickle     │ ❌ Manual update only         │
│              │ (data/cache/)   │                                │
│              └─────────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

### Contributing Factors

1. **Custom ingestion scripts** (e.g., `ingest_ragas_simple.py`) create pipelines without BM25 node
2. **rank_bm25.BM25Okapi** doesn't support incremental updates - requires full corpus at `fit()`
3. **No automatic sync mechanism** between Qdrant and BM25
4. **Two sources of truth** - inherent architecture flaw

---

## Impact

### Hybrid Search Quality

| Scenario | Expected Behavior | Actual Behavior |
|----------|-------------------|-----------------|
| Query with rare keyword | BM25 finds exact match | ❌ BM25 returns nothing |
| Query "Nemotron3 timeout" | Should rank high | ❌ Not in BM25 index |
| 95.5% of documents | Hybrid search | Vector-only fallback |

### RAGAS Metrics Impact

- **Context Recall:** Likely underestimated (BM25 not contributing)
- **Hybrid Mode:** Not truly hybrid, mostly vector-only
- **Benchmark validity:** Questionable for hybrid evaluation

---

## Solution: BGE-M3 Native Hybrid

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   NEW INGESTION PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│  chunking_node → embedding_node → graph_extraction_node         │
│                        │                                        │
│                        ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ FlagEmbedding Service (BAAI/bge-m3)                      │   │
│  │                                                          │   │
│  │   Text → ┌─ Dense (1024D) ──┐                            │   │
│  │          └─ Sparse (lexical)┘  → Single Qdrant Point    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ╔═════════════════════════════════════════════════════════════╗│
│  ║ BOTH vectors stored in same Qdrant point!                  ║│
│  ║ Sync guaranteed by design - no separate BM25 index         ║│
│  ╚═════════════════════════════════════════════════════════════╝│
│                                                                 │
│                   RETRIEVAL PIPELINE                            │
│              ┌─────────────────────────────────────┐            │
│              │ Qdrant Query API                    │            │
│              │ - Prefetch dense + sparse           │            │
│              │ - Server-side RRF fusion            │            │
│              │ - Single round-trip                 │            │
│              └─────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Benefits

| Benefit | Description |
|---------|-------------|
| **Sync guaranteed** | Dense + sparse stored together |
| **No pickle file** | Everything in Qdrant |
| **Server-side RRF** | Lower latency |
| **Better sparse quality** | BGE-M3 lexical weights > BM25 Okapi |
| **Incremental updates** | Each upsert updates both |

---

## Implementation Plan

**Sprint 87: BGE-M3 Native Hybrid (21 SP)**

| Feature | SP | Description |
|---------|-----|-------------|
| 87.1 | 3 | FlagEmbedding Service |
| 87.2 | 2 | Sparse Vector Converter |
| 87.3 | 3 | Qdrant Multi-Vector Collection |
| 87.4 | 3 | Embedding Node Integration |
| 87.5 | 4 | Hybrid Retrieval with Query API |
| 87.6 | 3 | Migration Script (Zero-Downtime) |
| 87.7 | 3 | RAGAS Validation |

---

## Dependencies

### Prerequisites

- Qdrant 1.11+ (✅ Have v1.11.0)
- FlagEmbedding library
- Sprint 86 (Coreference Resolution) complete

### Files to Modify

```
src/components/shared/flag_embedding_service.py     # NEW
src/components/shared/sparse_vector_utils.py        # NEW
src/components/vector_search/multi_vector_collection.py  # NEW
src/components/vector_search/multi_vector_search.py      # NEW
src/components/ingestion/nodes/vector_embedding.py       # MODIFY
src/components/vector_search/hybrid_search.py            # MODIFY
scripts/migrate_to_multi_vector.py                       # NEW
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| FlagEmbedding incompatible | Low | High | Feature flag, fallback |
| Collection migration fails | Medium | High | Blue-green, backup |
| RAGAS regression | Low | High | Before/after validation |
| Latency increase | Low | Medium | Benchmark, optimize |

---

## References

- [BGE-M3 Paper](https://arxiv.org/abs/2402.03216)
- [Qdrant Sparse Vectors](https://qdrant.tech/documentation/concepts/vectors/#sparse-vectors)
- [Qdrant Query API](https://qdrant.tech/documentation/concepts/search/#query-api)
- [FlagEmbedding GitHub](https://github.com/FlagOpen/FlagEmbedding)

---

## Workaround (Immediate)

Until Sprint 87 is complete, run BM25 rebuild after any ingestion:

```bash
# After ingestion, rebuild BM25 index
curl -X POST http://localhost:8000/api/v1/admin/prepare-bm25-index

# Or programmatically:
# scripts/rebuild_bm25.py
```

**Note:** This is a temporary workaround. The fundamental architecture issue remains until Sprint 89.

---

**Created:** 2026-01-13
**Author:** Claude Opus 4.5
**Related:** TD-100 (hybrid search desync), TD-084 (namespace isolation)
