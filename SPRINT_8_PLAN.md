# Sprint 8 Plan - Critical Path E2E Integration Testing

**Sprint Goal:** Validate critical integration paths from Sprint 1-6 with E2E tests (NO MOCKS)
**Duration:** 4 weeks (flexible, can be parallelized)
**Story Points:** 40 SP (40 critical E2E tests)
**Status:** Planning → Ready to Start
**Priority:** HIGH (blocks production confidence)

---

## Executive Summary

Sprint 8 is a **strategic quality investment** to validate the 26 critical integration paths identified in Sprint 1-6 that currently have zero or insufficient E2E test coverage. This sprint directly addresses the confidence gap revealed by Sprint 6's CI failures, where passing mocked tests failed to catch real Neo4j integration issues.

**Key Insight from Sprint 6:**
> "All unit tests passed with mocked Neo4j. Integration tests failed in CI with real Neo4j (timeout issues). Required multiple iterations to fix health checks and wait logic."
>
> **Root Cause:** Mocked Neo4j didn't simulate real startup time or connection behavior.

Sprint 8 prevents similar issues across **all** critical integration points.

---

## Problem Statement

### Current Test Coverage

```
Total Tests: ~470 test functions across 70 test files
├─ Mocked Unit Tests: 432 tests (92%) ← Fast but false confidence
└─ E2E Integration: 38 tests (8%) ← Only Sprint 7 memory system

Production Confidence: 75% ⚠️
```

### Critical Gaps Identified (26 paths, 12 with ZERO E2E coverage)

| Sprint | Critical Paths | E2E Coverage | Risk Level |
|--------|----------------|--------------|------------|
| Sprint 6 | Neo4j Graph Operations (13 paths) | **0%** | 🔴 CRITICAL |
| Sprint 5 | LightRAG Integration (15 paths) | **0%** | 🔴 CRITICAL |
| Sprint 3 | Advanced Retrieval (13 paths) | **7%** | 🟠 HIGH |
| Sprint 4 | LangGraph Orchestration (8 paths) | **25%** | 🟡 MEDIUM |
| Sprint 2 | Vector Search (10 paths) | **40%** | 🟢 GOOD |

**Historical Evidence:**
- **Sprint 6 (Oct 2025):** Neo4j integration tests failed in CI despite passing unit tests
- **Root Cause:** Mocked tests don't catch timing issues, connection failures, or configuration problems
- **Impact:** 2 days debugging CI, multiple iterations to fix

**Production Risk Without Sprint 8:**
- Community Detection could fail silently (Neo4j GDS untested)
- LightRAG entity extraction could produce corrupt graphs (Ollama→Neo4j untested)
- RAGAS evaluation unreliable (never validated with real LLM)
- Cross-encoder could crash on real models (never tested E2E)

---

## Sprint 8 Objectives

### Primary Goals

1. **Validate Critical Integration Points**
   - Test all 12 paths with zero E2E coverage
   - Increase E2E coverage from 8% → 16%
   - Achieve 95% production confidence (from 75%)

2. **Prevent Sprint 6-Style Failures**
   - Catch configuration issues before CI
   - Validate service startup timing
   - Test real error handling (not mocked exceptions)

3. **Enable Safe Production Deployment**
   - All critical paths validated with real services
   - Performance baselines established
   - Error scenarios tested

### Non-Goals (Deferred)

- ❌ Migrate ALL Sprint 1-6 tests to E2E (only critical paths)
- ❌ Unit test coverage improvements (Sprint 1-6 unit tests stay as-is)
- ❌ New feature development (100% focus on E2E testing)

---

## Test Categories & Breakdown

### 40 Critical Path E2E Tests (40 SP)

```
Week 1: Sprint 6 Neo4j Integration (13 tests, 13 SP) ← HIGHEST PRIORITY
├─ Community Detection E2E (Leiden + LLM labeling)
├─ Query Optimization E2E (CypherQueryBuilder + Cache)
├─ Temporal Features E2E (Bi-temporal queries)
├─ PageRank Analytics E2E (Real graph computation)
└─ Visualization Export E2E (D3.js data)

Week 2: Sprint 5 LightRAG Integration (15 tests, 16 SP) ← CRITICAL
├─ Entity Extraction E2E (Ollama → Neo4j)
├─ Graph Construction E2E (Full pipeline)
├─ Dual-Level Search E2E (Local + Global)
├─ Graph Query Agent E2E (LangGraph integration)
└─ Incremental Updates E2E (No full rebuild)

Week 3: Sprint 3 Advanced Retrieval (13 tests, 11 SP) ← HIGH PRIORITY
├─ Cross-Encoder Reranking E2E (sentence-transformers)
├─ RAGAS Evaluation E2E (Real Ollama LLM)
├─ Query Decomposition E2E (JSON parsing)
├─ Metadata Filtering E2E (Qdrant filters)
└─ Adaptive Chunking E2E (Document-type detection)

Week 4: Sprint 2 & 4 Enhancements (4 tests, 4 SP) ← MEDIUM
├─ Full Document Ingestion E2E
├─ Hybrid Search Latency E2E
├─ LangGraph State Persistence E2E
└─ Multi-turn Conversation E2E
```

---

## Detailed Test Specifications

### Week 1: Sprint 6 Neo4j Integration (13 tests, 13 SP)

#### Test 6.1: Community Detection with Real Neo4j E2E
**Priority:** P0 (CRITICAL - Zero current coverage)
**Story Points:** 2 SP
**Services:** Neo4j, Ollama (llama3.2:8b for labeling)

**Description:**
Tests community detection using Leiden algorithm with NetworkX (or Neo4j GDS if available), followed by LLM-based community labeling with real Ollama.

**Flow:**
```
1. Load test graph into Neo4j (100 nodes, 200 relationships)
2. Run CommunityDetector.detect_communities(algorithm="leiden")
3. Verify communities detected (expect 5-10 clusters)
4. Run CommunityLabeler.label_communities() with Ollama
5. Verify labels generated (2-4 words, descriptive)
6. Validate modularity score >0.3
7. Performance: <30s for 100 nodes
```

**What It Validates:**
- NetworkX Leiden algorithm works with real graph
- Neo4j graph projection for community detection
- Ollama LLM generates valid labels (not mock responses)
- Community detection → labeling pipeline E2E
- Performance targets met with real computation

**Why It's Critical:**
- **Zero current E2E coverage** (100% mocked)
- Community detection is core feature (Sprint 6 Feature 6.3)
- LLM labeling could produce unparseable responses
- Modularity calculations could fail with edge cases

**Potential Failures Without Test:**
- NetworkX vs Neo4j GDS variance causes different communities
- Ollama temperature variance produces inconsistent labels
- Graph projection fails with certain graph structures
- Performance degrades with larger graphs (not caught by mocks)

**Test Code Skeleton:**
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_community_detection_leiden_e2e(neo4j_driver, ollama_client_real):
    """E2E: Community detection with Leiden + LLM labeling."""
    # Setup: Create test graph in Neo4j
    community_detector = CommunityDetector(use_gds=False)  # NetworkX
    community_labeler = CommunityLabeler()

    # Execute: Detect communities
    communities = await community_detector.detect_communities(algorithm="leiden")

    # Verify: Communities detected
    assert len(communities) >= 5, "Expected 5+ communities"
    assert communities[0].modularity > 0.3

    # Execute: Label with Ollama
    labeled = await community_labeler.label_communities(communities)

    # Verify: Labels valid
    for community in labeled:
        assert community.label
        assert 2 <= len(community.label.split()) <= 4  # 2-4 words

    # Performance: <30s
    assert labeled[0].metadata["detection_time_ms"] < 30000
```

---

#### Test 6.2: Query Optimization with Real Neo4j E2E
**Priority:** P0 (CRITICAL)
**Story Points:** 1 SP
**Services:** Neo4j

**Description:**
Tests CypherQueryBuilder query construction and GraphQueryCache hit rate with real Neo4j execution.

**Flow:**
```
1. Build complex Cypher query with CypherQueryBuilder
2. Execute query against real Neo4j
3. Measure latency (expect <300ms)
4. Execute same query again (cache hit)
5. Verify cache hit rate >60%
6. Validate 40% latency reduction (target from Sprint 6)
```

**What It Validates:**
- CypherQueryBuilder generates valid Cypher (not mocked syntax)
- Real Neo4j query execution
- Cache hit/miss logic with real queries
- Performance targets met (300ms, 40% improvement)

**Why It's Critical:**
- Query optimization is key Sprint 6 feature
- Cypher syntax errors only caught by real Neo4j
- Cache invalidation logic untested

**Test Code Skeleton:**
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_query_optimization_e2e(neo4j_driver):
    """E2E: Query optimization with real Neo4j execution."""
    builder = CypherQueryBuilder()
    cache = GraphQueryCache(max_size=1000, ttl_seconds=300)

    # Build complex query
    query = builder.match("Entity").where({"type": "Person"}).return_all().build()

    # First execution (cache miss)
    start = time.time()
    result1 = await neo4j_driver.execute_read(query)
    latency1_ms = (time.time() - start) * 1000

    # Second execution (cache hit)
    start = time.time()
    result2 = await cache.get_or_execute(query, lambda: neo4j_driver.execute_read(query))
    latency2_ms = (time.time() - start) * 1000

    # Verify: Results identical
    assert result1 == result2

    # Verify: Cache hit
    assert cache.hit_rate > 0.6, "Expected 60%+ cache hit rate"

    # Verify: Performance improvement
    improvement = (latency1_ms - latency2_ms) / latency1_ms
    assert improvement > 0.4, f"Expected 40%+ improvement, got {improvement:.1%}"
```

---

#### Test 6.3-6.13: Additional Sprint 6 Tests (11 tests, 11 SP)

**Test 6.3:** Temporal Query with Bi-Temporal Model E2E (1 SP)
**Test 6.4:** PageRank Analytics on Real Graph E2E (1 SP)
**Test 6.5:** Betweenness Centrality E2E (1 SP)
**Test 6.6:** Knowledge Gap Detection E2E (1 SP)
**Test 6.7:** Recommendation Engine E2E (1 SP)
**Test 6.8:** D3.js Visualization Export E2E (1 SP)
**Test 6.9:** Cytoscape.js Visualization Export E2E (1 SP)
**Test 6.10:** Query Template Expansion E2E (1 SP)
**Test 6.11:** Batch Query Execution E2E (1 SP)
**Test 6.12:** Version Manager E2E (1 SP)
**Test 6.13:** Evolution Tracker E2E (1 SP)

*(Full specifications in appendix)*

---

### Week 2: Sprint 5 LightRAG Integration (15 tests, 16 SP)

#### Test 5.1: Entity Extraction with Ollama → Neo4j E2E
**Priority:** P0 (CRITICAL - Zero current coverage)
**Story Points:** 2 SP
**Services:** Ollama (llama3.2:8b), Neo4j

**Description:**
Tests full entity extraction pipeline from text → Ollama LLM → Neo4j storage, validating JSON parsing and graph construction.

**Flow:**
```
1. Input: Sample text (200 words about organizations)
2. ExtractionPipeline.extract_entities(text) with Ollama
3. Verify: Entities extracted (expect 5-10)
4. Verify: JSON parsing succeeds (LLM response valid)
5. Insert entities into Neo4j via LightRAG
6. Query Neo4j: Verify entities stored
7. Performance: <5s for 200-word text
```

**What It Validates:**
- Ollama llama3.2:8b produces valid JSON (not mocked response)
- JSON parsing handles real LLM variance (extra text, formatting)
- Neo4j storage succeeds with real entities
- Entity deduplication logic works
- Performance realistic (not instant mock)

**Why It's Critical:**
- **Zero E2E coverage** for LightRAG (100% mocked in Sprint 5)
- LLM JSON parsing is fragile (temperature variance, formatting)
- Neo4j schema constraints could fail
- Core feature for Graph RAG functionality

**Potential Failures Without Test:**
- Ollama produces invalid JSON → extraction crashes
- Entity names with special characters break Neo4j
- Deduplication fails with similar entities
- Performance degrades with longer texts

**Test Code Skeleton:**
```python
@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow  # >5s execution
async def test_entity_extraction_ollama_neo4j_e2e(ollama_client_real, neo4j_driver):
    """E2E: Entity extraction from Ollama to Neo4j storage."""
    extraction_pipeline = ExtractionPipeline(
        llm_model="llama3.2:8b",
        ollama_base_url="http://localhost:11434"
    )

    text = """
    Microsoft was founded by Bill Gates and Paul Allen in 1975.
    The company is headquartered in Redmond, Washington.
    In 2023, Microsoft acquired OpenAI's exclusive rights.
    """

    # Execute: Extract entities
    entities = await extraction_pipeline.extract_entities(text, document_id="test_doc")

    # Verify: Entities extracted
    assert len(entities) >= 3, "Expected entities: Microsoft, Bill Gates, Paul Allen"
    entity_names = [e.name for e in entities]
    assert "Microsoft" in entity_names
    assert any("Bill Gates" in name or "Gates" in name for name in entity_names)

    # Verify: Entity types correct
    microsoft = next(e for e in entities if e.name == "Microsoft")
    assert microsoft.type in ["Organization", "Company"]

    # Execute: Store in Neo4j
    lightrag = LightRAGWrapper()
    await lightrag.add_entities(entities)

    # Verify: Entities in Neo4j
    with neo4j_driver.session() as session:
        result = session.run("MATCH (e:Entity {name: 'Microsoft'}) RETURN e")
        stored_entity = result.single()
        assert stored_entity is not None
        assert stored_entity["e"]["type"] == microsoft.type

    # Performance: <5s
    assert entities[0].metadata.get("extraction_time_ms", 0) < 5000
```

---

#### Test 5.2-5.15: Additional Sprint 5 Tests (14 tests, 14 SP)

**Test 5.2:** Relationship Extraction E2E (2 SP)
**Test 5.3:** Graph Construction Full Pipeline E2E (2 SP)
**Test 5.4:** Local Search (Entity-Level) E2E (1 SP)
**Test 5.5:** Global Search (Topic-Level) E2E (1 SP)
**Test 5.6:** Hybrid Search (Local + Global) E2E (1 SP)
**Test 5.7:** Graph Query Agent with LangGraph E2E (2 SP)
**Test 5.8:** Incremental Graph Updates E2E (2 SP)
**Test 5.9:** Entity Deduplication E2E (1 SP)
**Test 5.10:** Relationship Type Classification E2E (1 SP)
**Test 5.11:** Community Detection in Graph E2E (1 SP)
**Test 5.12:** Graph Visualization Data E2E (1 SP)
**Test 5.13:** Multi-Hop Graph Traversal E2E (1 SP)
**Test 5.14:** LightRAG Error Handling E2E (1 SP)
**Test 5.15:** Neo4j Schema Validation E2E (1 SP)

*(Full specifications in appendix)*

---

### Week 3: Sprint 3 Advanced Retrieval (13 tests, 11 SP)

#### Test 3.1: Cross-Encoder Reranking with Real Model E2E
**Priority:** P0 (CRITICAL - Zero current coverage)
**Story Points:** 2 SP
**Services:** HuggingFace sentence-transformers (CPU inference)

**Description:**
Tests cross-encoder reranking with real ms-marco-MiniLM-L-12-v2 model, validating model loading, inference, and score normalization.

**Flow:**
```
1. Load cross-encoder model (ms-marco-MiniLM-L-12-v2)
2. Generate 10 candidate results (varying relevance)
3. Rerank with CrossEncoderReranker
4. Verify: Scores between 0-1
5. Verify: Results reordered (top result changed)
6. Performance: <500ms for 10 candidates
7. Verify: 15%+ precision improvement @3
```

**What It Validates:**
- sentence-transformers model loads correctly
- Real inference (not mocked scores)
- Score normalization to [0,1] range
- Reranking improves top-k precision
- Performance with real CPU inference

**Why It's Critical:**
- **Zero E2E coverage** (100% mocked)
- Model loading could fail (missing dependencies, CUDA issues)
- Real inference slower than mocks
- Score distribution different from mocks

**Potential Failures Without Test:**
- Model file download fails in CI
- CUDA/CPU inference issues
- Score normalization produces NaN
- Performance target missed (>500ms)

**Test Code Skeleton:**
```python
@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow  # Model loading ~5s first time
async def test_cross_encoder_reranking_e2e():
    """E2E: Cross-encoder reranking with real sentence-transformers model."""
    reranker = CrossEncoderReranker(
        model_name="cross-encoder/ms-marco-MiniLM-L-12-v2"
    )

    # Generate test candidates
    query = "What is machine learning?"
    candidates = [
        "Machine learning is a subset of AI...",  # Relevant
        "Python is a programming language...",     # Less relevant
        "The weather today is sunny...",           # Irrelevant
        # ... 7 more candidates
    ]

    # Execute: Rerank
    start = time.time()
    reranked = await reranker.rerank(query, candidates, top_k=5)
    latency_ms = (time.time() - start) * 1000

    # Verify: Scores valid
    for result in reranked:
        assert 0 <= result.score <= 1, f"Invalid score: {result.score}"

    # Verify: Reordering happened
    assert reranked[0].text == candidates[0], "Most relevant should be top"

    # Verify: Performance
    assert latency_ms < 500, f"Expected <500ms, got {latency_ms}ms"

    # Verify: Precision improvement (compare with baseline)
    baseline_top3 = candidates[:3]
    reranked_top3 = [r.text for r in reranked[:3]]
    relevance_gain = calculate_precision_at_k(reranked_top3, baseline_top3)
    assert relevance_gain > 0.15, f"Expected 15%+ improvement, got {relevance_gain:.1%}"
```

---

#### Test 3.2: RAGAS Evaluation with Real Ollama LLM E2E
**Priority:** P0 (CRITICAL)
**Story Points:** 2 SP
**Services:** Ollama (llama3.2:8b), Qdrant

**Description:**
Tests RAGAS evaluation framework with real Ollama LLM for answer generation, validating context precision/recall/faithfulness metrics.

**Flow:**
```
1. Load test dataset (10 Q&A pairs)
2. Retrieve contexts from Qdrant
3. Generate answers with Ollama llama3.2:8b
4. Compute RAGAS metrics (Precision, Recall, Faithfulness)
5. Verify: Overall RAGAS score >0.85
6. Verify: LLM answer quality (not mocked)
7. Performance: <30s for 10 evaluations
```

**What It Validates:**
- RAGAS works with Ollama (not just OpenAI)
- Real LLM answer generation quality
- Metric calculations with real data
- Performance at scale

**Why It's Critical:**
- **Zero E2E coverage** (RAGAS tests use mocked LLM)
- RAGAS designed for OpenAI, Ollama compatibility unproven
- Real LLM could produce unparseable answers
- Metric variance with temperature

**Test Code Skeleton:**
```python
@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow  # LLM inference ~2s per question
async def test_ragas_evaluation_ollama_e2e(ollama_client_real, qdrant_client_real):
    """E2E: RAGAS evaluation with real Ollama LLM."""
    evaluator = RAGASEvaluator(llm_model="llama3.2:8b")

    # Test dataset
    test_data = [
        {"question": "What is RAG?", "ground_truth": "Retrieval-Augmented Generation..."},
        # ... 9 more Q&A pairs
    ]

    # Execute: Evaluate
    results = await evaluator.evaluate(
        test_data=test_data,
        retriever=qdrant_client_real,
        generator=ollama_client_real
    )

    # Verify: Metrics computed
    assert results["context_precision"] > 0.8
    assert results["context_recall"] > 0.8
    assert results["answer_faithfulness"] > 0.8
    assert results["ragas_score"] > 0.85

    # Verify: All questions answered
    assert len(results["details"]) == len(test_data)
```

---

#### Test 3.3-3.13: Additional Sprint 3 Tests (11 tests, 9 SP)

**Test 3.3:** Query Decomposition JSON Parsing E2E (1 SP)
**Test 3.4:** Metadata Date Range Filtering E2E (1 SP)
**Test 3.5:** Metadata Source Filtering E2E (1 SP)
**Test 3.6:** Metadata Tag Filtering E2E (1 SP)
**Test 3.7:** Combined Metadata Filters E2E (1 SP)
**Test 3.8:** Adaptive Chunking by Document Type E2E (1 SP)
**Test 3.9:** Query Classification (SIMPLE/COMPOUND/MULTI_HOP) E2E (1 SP)
**Test 3.10:** Reranking Performance at Scale E2E (1 SP)
**Test 3.11:** RAGAS Context Precision E2E (1 SP)
**Test 3.12:** RAGAS Context Recall E2E (1 SP)
**Test 3.13:** Query Decomposition with Complex Queries E2E (1 SP)

*(Full specifications in appendix)*

---

### Week 4: Sprint 2 & 4 Enhancements (4 tests, 4 SP)

#### Test 2.1: Full Document Ingestion Pipeline E2E
**Priority:** P1 (MEDIUM)
**Story Points:** 1 SP
**Services:** Ollama (nomic-embed-text), Qdrant

**Description:**
Tests complete document ingestion from file → chunking → embedding → Qdrant storage.

**Flow:**
```
1. Load PDF document (10 pages)
2. Chunk with SentenceSplitter
3. Generate embeddings with Ollama
4. Store in Qdrant collection
5. Verify: All chunks stored
6. Verify: Embeddings valid (768-dim)
7. Performance: <30s for 10-page PDF
```

**What It Validates:**
- Full ingestion pipeline E2E
- Real Ollama embedding generation
- Qdrant batch upsert
- Performance at scale

**Why It's Medium Priority:**
- Sprint 2 already has good hybrid search E2E coverage
- This adds full pipeline validation

**Test Code Skeleton:**
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_document_ingestion_pipeline_e2e(ollama_client_real, qdrant_client_real):
    """E2E: Full document ingestion pipeline."""
    pipeline = DocumentIngestionPipeline()

    # Execute: Ingest document
    result = await pipeline.ingest_file("tests/fixtures/test_document.pdf")

    # Verify: Chunks created
    assert result["chunks_created"] > 20  # 10 pages ~20+ chunks

    # Verify: Stored in Qdrant
    collection_info = qdrant_client_real.get_collection("documents")
    assert collection_info.points_count >= result["chunks_created"]

    # Performance: <30s
    assert result["processing_time_ms"] < 30000
```

---

#### Test 2.2-2.4: Additional Sprint 2 & 4 Tests (3 tests, 3 SP)

**Test 2.2:** Hybrid Search Latency Validation E2E (1 SP)
**Test 4.1:** LangGraph State Persistence with Redis E2E (1 SP)
**Test 4.2:** Multi-turn Conversation State E2E (1 SP)

*(Full specifications in appendix)*

---

## Implementation Strategy

### Week-by-Week Plan

**Week 1: Sprint 6 Neo4j (13 tests)**
- Days 1-2: Community Detection + Query Optimization (4 tests)
- Days 3-4: Temporal + Analytics (5 tests)
- Day 5: Visualization + Buffer (4 tests)

**Week 2: Sprint 5 LightRAG (15 tests)**
- Days 1-2: Entity/Relationship Extraction (4 tests)
- Days 3-4: Graph Construction + Search (6 tests)
- Day 5: Incremental Updates + Agent (5 tests)

**Week 3: Sprint 3 Advanced Retrieval (13 tests)**
- Days 1-2: Cross-Encoder + RAGAS (4 tests)
- Days 3-4: Metadata Filters + Chunking (6 tests)
- Day 5: Query Decomposition + Buffer (3 tests)

**Week 4: Sprint 2 & 4 Enhancements (4 tests)**
- Days 1-2: Full Ingestion + Hybrid (2 tests)
- Days 3-4: LangGraph State + Conversations (2 tests)
- Day 5: Documentation + Sprint 8 Completion Report

### Parallel Execution Strategy

Tests can be parallelized by week (4 subagents):
- **Subagent 1:** Week 1 tests (Sprint 6)
- **Subagent 2:** Week 2 tests (Sprint 5)
- **Subagent 3:** Week 3 tests (Sprint 3)
- **Subagent 4:** Week 4 tests (Sprint 2 & 4)

**Result:** 4-week sequential plan → **1-week parallel execution**

---

## Success Criteria

### Functional Requirements

- [ ] All 40 E2E tests passing with real services
- [ ] Zero mocks in Sprint 8 tests (ADR-014 compliance)
- [ ] Test execution time <20 minutes total
- [ ] All critical paths validated (12 zero-coverage paths)

### Quality Metrics

| Metric | Before Sprint 8 | After Sprint 8 | Target |
|--------|----------------|----------------|--------|
| **E2E Coverage** | 8% (38 tests) | 16% (78 tests) | 16%+ |
| **Production Confidence** | 75% | 95% | 95% |
| **CI Failure Rate** | 3/sprint | 0/sprint | <1/sprint |
| **Integration Bugs** | 10/quarter | 2/quarter | <3/quarter |

### Performance Benchmarks

| Test Category | Target | Acceptance |
|---------------|--------|------------|
| Sprint 6 Neo4j | <30s/test | <60s/test |
| Sprint 5 LightRAG | <5s/test | <10s/test |
| Sprint 3 Retrieval | <3s/test | <6s/test |
| Sprint 2 & 4 | <2s/test | <5s/test |
| **Total Suite** | <15 min | <20 min |

---

## Risk Assessment

### High Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Test execution time >20 min | Medium | Medium | Parallel execution (pytest-xdist -n 4) |
| Service startup failures in CI | Low | High | Robust health checks (reuse Sprint 7 logic) |
| Real LLM variance breaks tests | Medium | Medium | Temperature=0.1, retry logic, flexible assertions |
| Neo4j GDS unavailable (Community) | High | Low | Use NetworkX fallback (already implemented) |

### Medium Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cross-encoder model download fails | Low | Medium | Cache model in CI, fallback URL |
| RAGAS incompatibility with Ollama | Low | High | Validate early (Week 3 Day 1) |
| Test flakiness (timing issues) | Medium | Low | Retry decorator, increased timeouts |

---

## Deliverables

### Test Files Created (4 new files)

1. **tests/integration/sprint6_critical_e2e.py** (13 tests, Week 1)
2. **tests/integration/sprint5_critical_e2e.py** (15 tests, Week 2)
3. **tests/integration/sprint3_critical_e2e.py** (13 tests, Week 3)
4. **tests/integration/sprint2_4_enhancements_e2e.py** (4 tests, Week 4)

### Documentation Created

5. **SPRINT_8_COMPLETION_REPORT.md** (End of Sprint 8)
   - Test results summary
   - Coverage improvements
   - Bugs found and fixed
   - Recommendations for future sprints

6. **docs/testing/CRITICAL_PATH_TESTING_GUIDE.md**
   - How to identify critical paths
   - When to write E2E vs unit tests
   - Best practices for E2E testing

### Updated Documentation

7. **docs/core/SPRINT_PLAN.md** (Insert Sprint 8)
8. **docs/adr/ADR_INDEX.md** (Add ADR-015)
9. **docs/adr/ADR-015-critical-path-testing.md** (New ADR)

---

## Definition of Done

For Sprint 8 completion:

- [ ] All 40 E2E tests implemented and passing
- [ ] Tests run in CI with Docker services
- [ ] Test execution time <20 minutes
- [ ] Zero mocks in new tests (ADR-014 compliance)
- [ ] All critical paths have E2E coverage
- [ ] Sprint 8 Completion Report published
- [ ] Documentation updated (SPRINT_PLAN.md, ADRs)
- [ ] Production confidence increased to 95%
- [ ] Team sign-off on test quality

---

## Post-Sprint 8: Impact

### Confidence Progression

```
Before Sprint 8:
├─ Unit Tests: 432 (92%)
├─ E2E Tests: 38 (8%)
└─ Confidence: 75% ⚠️

After Sprint 8:
├─ Unit Tests: 432 (92%) [unchanged]
├─ E2E Tests: 78 (16%) [+40 critical path tests]
└─ Confidence: 95% ✅
```

### Expected Benefits

**Short-term (Immediate):**
- ✅ All critical integration paths validated
- ✅ Sprint 6-style CI failures prevented
- ✅ Production deployment safe

**Medium-term (3 months):**
- ✅ Integration bug rate: 10/quarter → 2/quarter (80% reduction)
- ✅ CI debugging time: 5 hours/week → 1 hour/week (80% reduction)
- ✅ Developer confidence in deployments

**Long-term (6-12 months):**
- ✅ Faster feature development (less debugging)
- ✅ Easier onboarding (E2E tests as documentation)
- ✅ Lower maintenance costs

---

## Sprint 8 Checklist

**Before Starting:**
- [ ] All services running (Redis, Qdrant, Neo4j, Ollama)
- [ ] Sprint 7 E2E tests passing (baseline)
- [ ] Test fixtures from Sprint 7 available
- [ ] Team capacity confirmed (30-40 SP)

**Week 1 (Sprint 6 Tests):**
- [ ] Community Detection E2E (2 SP)
- [ ] Query Optimization E2E (1 SP)
- [ ] Temporal Features E2E (3 tests, 3 SP)
- [ ] Analytics E2E (4 tests, 4 SP)
- [ ] Visualization E2E (3 tests, 3 SP)

**Week 2 (Sprint 5 Tests):**
- [ ] Entity Extraction E2E (2 SP)
- [ ] Relationship Extraction E2E (2 SP)
- [ ] Graph Construction E2E (2 SP)
- [ ] Dual-Level Search E2E (3 tests, 3 SP)
- [ ] Graph Query Agent E2E (2 SP)
- [ ] Incremental Updates E2E (5 tests, 5 SP)

**Week 3 (Sprint 3 Tests):**
- [ ] Cross-Encoder Reranking E2E (2 SP)
- [ ] RAGAS Evaluation E2E (2 SP)
- [ ] Query Decomposition E2E (2 tests, 2 SP)
- [ ] Metadata Filtering E2E (4 tests, 4 SP)
- [ ] Adaptive Chunking E2E (3 tests, 3 SP)

**Week 4 (Sprint 2 & 4 Tests):**
- [ ] Full Document Ingestion E2E (1 SP)
- [ ] Hybrid Search Latency E2E (1 SP)
- [ ] LangGraph State Persistence E2E (1 SP)
- [ ] Multi-turn Conversation E2E (1 SP)

**Completion:**
- [ ] All 40 tests passing
- [ ] Sprint 8 Completion Report
- [ ] Documentation updates
- [ ] Production confidence: 95%

---

**Sprint 8 Status:** Planning → Ready to Start
**Estimated Start:** After Sprint 7 completion
**Estimated Duration:** 4 weeks (sequential) or 1 week (parallel with 4 subagents)
**Story Points:** 40 SP
**Priority:** HIGH (Critical for production readiness)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
