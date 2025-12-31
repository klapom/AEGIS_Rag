# Sprint 41: RAG Evaluation with RAGAS + Namespace Isolation

**Status:** IN PROGRESS
**Started:** 2025-12-09
**Completed:** -
**Priority:** High (Quality Assurance + Infrastructure)
**Prerequisites:** Sprint 42 complete (4-Way Hybrid RRF)

---

## Objective

1. Implement namespace isolation layer for multi-tenant document management
2. Evaluate AEGIS RAG using standard benchmarks (RAGAS) for comparability
3. Enable enterprise use case: "general" + project-specific document isolation

---

## Architecture Decision

### Namespace Model (Enterprise-Ready)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Enterprise Namespace Hierarchy                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     "general"                                    │   │
│  │         Company-wide documentation (policies, manuals)          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│              ┌───────────────┼───────────────┐                         │
│              ▼               ▼               ▼                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐              │
│  │ user_proj_a   │  │ user_proj_b   │  │ eval_hotpotqa │              │
│  │ (isolated)    │  │ (isolated)    │  │ (benchmark)   │              │
│  └───────────────┘  └───────────────┘  └───────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Query Scenarios

| Scenario | Namespaces | Use Case |
|----------|------------|----------|
| General question | `["general"]` | Company-wide search |
| Project question | `["general", "user_proj_x"]` | Project + company context |
| Benchmark eval | `["eval_hotpotqa"]` | Isolated evaluation |

---

## Technical Implementation

### Storage Strategy (Single Collection + Payload Filter)

| Component | Strategy | Rationale |
|-----------|----------|-----------|
| **Qdrant** | Single collection + `namespace_id` payload index | Qdrant recommends this over multiple collections |
| **Neo4j** | `namespace_id` property + Query Validator | Community Edition: no multi-database |
| **BM25** | In-memory with namespace filter | Post-filter on search |
| **Redis** | Key prefix `{namespace}:` | Native support |

### Neo4j Query Validator (Security)

Every Neo4j query MUST contain namespace filtering. A validator rejects queries without it:

```python
# REJECTED - no namespace filter
MATCH (e:Entity) RETURN e

# ACCEPTED - has namespace filter
MATCH (e:Entity) WHERE e.namespace_id IN $allowed_namespaces RETURN e
```

---

## Features

### Feature 41.1: Namespace Isolation Layer - Core (5 SP) ✅

**Status:** COMPLETED
**Deliverables:**
- [x] `src/core/namespace.py` - NamespaceManager class
- [x] `src/core/neo4j_safety.py` - Query Validator + SecureClient
- [x] Unit tests (77 passed)
- [x] Integration tests (8/11 passed)
- [x] Playwright E2E tests (11 passed)

**Files:**
- `src/core/namespace.py`
- `src/core/neo4j_safety.py`
- `tests/unit/core/test_namespace.py`
- `tests/unit/core/test_neo4j_safety.py`

---

### Feature 41.2: Integrate Namespace into FourWayHybridSearch (3 SP) ✅

**Status:** COMPLETED
**Deliverables:**
- [x] Add `allowed_namespaces` parameter to `search()` method
- [x] Qdrant vector search with namespace filter
- [x] BM25 search with namespace result filtering
- [x] Namespace info in search metadata (`namespaces_searched`)

**Files:**
- `src/components/retrieval/four_way_hybrid_search.py`

---

### Feature 41.3: Namespace Filter in Graph Searches (3 SP) ✅

**Status:** COMPLETED
**Deliverables:**
- [x] `_graph_local_search()` with namespace filter in Cypher
- [x] `_graph_global_search()` with namespace filter in Cypher
- [x] All node matches filtered by `namespace_id IN $allowed_namespaces`

**Files:**
- `src/components/retrieval/four_way_hybrid_search.py`

---

### Feature 41.4: Chat API Namespace Parameter (2 SP) ✅

**Status:** COMPLETED
**Deliverables:**
- [x] `namespaces` field in ChatRequest model
- [x] Pass namespaces through to retrieval pipeline (AgentState, CoordinatorAgent, VectorSearchAgent)
- [x] Default: `["default", "general"]`

**Files:**
- `src/api/v1/chat.py`
- `src/agents/coordinator.py`
- `src/agents/state.py`
- `src/agents/vector_search_agent.py`
- `src/components/retrieval/filters.py`

---

### Feature 41.5: Namespace Integration Tests (2 SP) ✅

**Status:** COMPLETED
**Deliverables:**
- [x] E2E test verifying namespace isolation in actual search
- [x] Test that documents in namespace A are NOT returned for namespace B query
- [x] Test cross-namespace search (general + project)

**Files:**
- `tests/integration/test_namespaced_search.py`
- `frontend/e2e/search/namespace-isolation.spec.ts` (update)

---

### Feature 41.6: Benchmark Corpus Ingestion (5 SP) ✅

**Status:** COMPLETED
**Deliverables:**
- [x] HuggingFace dataset loader (`BenchmarkDatasetLoader`)
- [x] Corpus extraction and ingestion pipeline (`BenchmarkCorpusIngestionPipeline`)
- [x] Benchmark namespaces: `eval_nq`, `eval_hotpotqa`, `eval_msmarco`, `eval_fever`, `eval_ragbench`
- [x] Batch processing with BGE-M3 embeddings

**Benchmarks (Track A - Standard):**
| Benchmark | Sample Size | Purpose |
|-----------|-------------|---------|
| Natural Questions | 1000 | Google standard |
| HotpotQA | 1000 | Multi-hop reasoning |
| MS MARCO | 1000 | Microsoft standard |

**Benchmarks (Track B - Specialized):**
| Benchmark | Sample Size | Purpose |
|-----------|-------------|---------|
| FEVER | 100 | Fact verification |
| RAGBench | 100 | Industry manuals |

**Files:**
- `src/evaluation/benchmark_loader.py`
- `src/evaluation/corpus_ingestion.py`

---

### Feature 41.7: RAGAS Evaluation Pipeline (5 SP) ✅

**Status:** COMPLETED
**Deliverables:**
- [x] RAGAS integration with namespace-scoped search
- [x] Per-intent metric breakdown (factual, keyword, exploratory, summary)
- [x] Batch evaluation support with configurable batch size
- [x] LangChain wrappers for AegisLLMProxy and UnifiedEmbeddingService

**RAGAS Metrics:**
| Metric | Description |
|--------|-------------|
| Context Precision | Relevance of retrieved contexts |
| Context Recall | Coverage of ground truth |
| Faithfulness | Answer grounded in context |
| Answer Relevancy | Answer addresses the question |

**Files:**
- `src/evaluation/ragas_evaluator.py`
- `scripts/run_evaluation.py`

---

### Feature 41.8: Evaluation Reports (3 SP) ✅

**Status:** COMPLETED
**Deliverables:**
- [x] CLI report generation (with `rich` library support)
- [x] Markdown summary export
- [x] JSON export format
- [x] Regression detection vs baseline (>5% threshold)
- [x] Per-benchmark and per-intent breakdown

**Files:**
- `src/evaluation/report_generator.py`
- `data/evaluation/reports/`
- `data/evaluation/baselines/`

---

### Feature 41.9: JSON Apostrophe Fix + Parallel Embeddings (2 SP) ✅

**Status:** COMPLETED
**Deliverables:**
- [x] Smart JSON repair for French apostrophes (`L'Histoire` no longer breaks parsing)
- [x] Parallel embedding generation with `asyncio.gather()` + Semaphore
- [x] Configurable `embedding_max_concurrent` setting (default: 20)
- [x] GPU utilization improved from ~5% to ~50-80% during embedding phase

**Problem Solved:**
1. **JSON Parsing Bug:** LLM responses with French text like `"L'Histoire du soldat"` were corrupted when single quotes were blindly replaced with double quotes, creating invalid JSON like `"L"Histoire du soldat"`.
2. **Low GPU Utilization:** Sequential embedding generation only used 5% GPU on DGX Spark. Now parallelized with configurable concurrency.

**Technical Details:**
- `_repair_json_string()` now detects single-quote-delimited JSON vs apostrophes in text
- `embed_batch()` uses `asyncio.gather()` with Semaphore for bounded parallelism
- Order-preserving parallel execution (results sorted by original index)

**Files:**
- `src/components/graph_rag/extraction_service.py`
- `src/components/shared/embedding_service.py`
- `src/core/config.py`

---

## Test Strategy

### Unit Tests
- `tests/unit/core/test_namespace.py`
- `tests/unit/core/test_neo4j_safety.py`
- `tests/unit/evaluation/test_benchmark_loader.py`

### Integration Tests
- `tests/integration/test_namespace_isolation.py`
- `tests/integration/test_namespaced_search.py`

### E2E Tests (Playwright)
- `frontend/e2e/namespace/search-with-namespace.spec.ts`
- `frontend/e2e/evaluation/benchmark-results.spec.ts`

---

## Success Criteria

### Namespace Isolation
- [ ] Neo4j queries without namespace filter are REJECTED
- [ ] Qdrant search only returns documents from allowed namespaces
- [ ] BM25 search respects namespace filter
- [ ] No cross-namespace data leakage (verified by tests)

### Evaluation
| Metric | Target | Baseline (Sprint 3) |
|--------|--------|---------------------|
| Context Precision | ≥0.90 | 0.91 |
| Context Recall | ≥0.90 | 0.87 |
| Faithfulness | ≥0.88 | 0.88 |
| Answer Relevancy | ≥0.85 | N/A |

---

## Story Points

| Feature | SP | Status |
|---------|-----|--------|
| 41.1 Namespace Isolation Layer - Core | 5 | COMPLETED |
| 41.2 Integrate Namespace into FourWayHybridSearch | 3 | COMPLETED |
| 41.3 Namespace Filter in Graph Searches | 3 | COMPLETED |
| 41.4 Chat API Namespace Parameter | 2 | COMPLETED |
| 41.5 Namespace Integration Tests | 2 | COMPLETED |
| 41.6 Benchmark Corpus Ingestion | 5 | COMPLETED |
| 41.7 RAGAS Evaluation Pipeline | 5 | COMPLETED |
| 41.8 Evaluation Reports | 3 | COMPLETED |
| 41.9 JSON Apostrophe Fix + Parallel Embeddings | 2 | COMPLETED |
| **Total** | **30** | **PENDING RAGAS RESULTS** |

---

## Dependencies

### Existing (pyproject.toml)
```toml
ragas = "^0.3.7"
datasets = "^4.0.0"
```

### Runtime
- Ollama (qwen3:8b for evaluation)
- Qdrant with payload index
- Neo4j 5.24 Community
- Redis

---

## References

- [TD-056: Project Collaboration System](../technical-debt/TD-056_PROJECT_COLLABORATION_SYSTEM.md)
- [Qdrant Filtering Guide](https://qdrant.tech/articles/vector-search-filtering/)
- [Neo4j Multi-Tenancy](https://neo4j.com/developer/multi-tenancy-worked-example/)

---

## Date
2025-12-09
