# Sprint 77 Plan - Data Quality & Optimization

**Sprint Goal**: Fix data inconsistencies and optimize ingestion pipeline

**Duration**: 2 sessions (~13 hours total)

**Previous Sprint**: Sprint 76 - .txt File Support + Pydantic Chunk Fix

---

## 📊 Sprint 76 Summary

### ✅ **Completed**
1. .txt file support via Docling (100% success rate, 15 files)
2. Pydantic Chunk fix (no more repr() bugs)
3. HotpotQA dataset ingestion (146 entities, 217 MENTIONED_IN)
4. RAGAS dataset creation (15 questions)
5. Comprehensive statistics analysis

### ⚠️ **Issues Identified**
1. **TD-090**: BM25 namespace metadata missing (all marked "unknown")
2. **TD-091**: Chunk count mismatch (Qdrant 17, Neo4j 14)
3. **TD-093**: Qdrant index not updated post-ingestion
4. **TD-094**: Community summaries not generated (92 communities)
5. **TD-095**: Low entity connectivity (0.45 relations/entity)

---

## 🎯 Sprint 77 Objectives

### **Session 1: Critical Bug Fixes** (5 hours)

#### Feature 77.1: Fix BM25 Namespace Metadata (TD-090)
**Priority**: HIGH | **Effort**: 1 SP | **Time**: 1 hour

**Problem**: All 17 BM25 documents have `namespace="unknown"` instead of correct values

**Root Cause**: `hybrid_search.py:661-686` doesn't copy namespace field from Qdrant payload

**Solution**:
```python
# File: src/components/vector_search/hybrid_search.py
# Line: ~680

doc = {
    "id": str(point.id),
    "text": text,
    "source": ...,
    "document_id": ...,
    "section_id": ...,
    "section_headings": ...,
    # ADD THIS LINE:
    "namespace": str(point.payload.get("namespace", "unknown")) if point.payload else "unknown",
}
```

**Testing**:
1. Rebuild BM25 index: `POST /api/v1/admin/bm25/rebuild`
2. Verify namespace distribution in pickle file
3. Test namespace filtering in hybrid search

**Success Criteria**:
- ✅ BM25 documents have correct namespace values
- ✅ Namespace filtering works in hybrid search
- ✅ Integration test passes

---

#### Feature 77.2: Investigate Chunk Count Mismatch (TD-091)
**Priority**: HIGH | **Effort**: 2 SP | **Time**: 2 hours

**Problem**: Qdrant has 17 chunks, Neo4j has 14 chunks (3 missing)

**Investigation Steps**:
1. Query Qdrant for all chunk IDs in hotpotqa namespaces
2. Query Neo4j for all chunk IDs in hotpotqa namespaces
3. Compare lists to identify missing chunk IDs
4. Check LightRAG logs for insertion errors
5. Verify `insert_prechunked_documents()` transaction handling

**Potential Root Causes**:
- Transaction rollback in Neo4j (partial commit)
- Exception during `store_chunks_and_provenance()`
- Namespace filter mismatch
- Duplicate chunk IDs (MERGE collision)

**Solution** (TBD based on investigation):
- Option A: Re-ingest missing chunks
- Option B: Fix transaction handling in `store_chunks_and_provenance()`
- Option C: Add post-ingestion consistency check

**Testing**:
1. Create integration test with 10 chunks
2. Verify Qdrant and Neo4j have same count
3. Add automated consistency check to ingestion pipeline

**Success Criteria**:
- ✅ Root cause identified and documented
- ✅ Missing chunks restored or re-ingested
- ✅ Consistency check added to prevent recurrence

---

#### Feature 77.3: Add Qdrant Index Rebuild Post-Ingestion (TD-093)
**Priority**: MEDIUM | **Effort**: 2 SP | **Time**: 2 hours

**Problem**: `indexed_vectors=0` after ingestion (uses slow linear scan)

**Context**:
- HNSW indexing threshold: 20,000 vectors (default)
- Current collection: 17 vectors → not indexed
- **User Request**: "Nach jedem Ingestion sollten QDRANT Indexed Vectors upgedatet werden"

**Solution**:
1. Add post-ingestion index optimization step
2. Call Qdrant `optimize_collection()` API
3. Make configurable (enable/disable, async/sync)

**Implementation**:
```python
# File: src/components/ingestion/nodes/vector_embedding.py
# After Qdrant upsert:

if state.get("optimize_index", True):
    logger.info("triggering_qdrant_index_optimization")

    # Option 1: Synchronous (blocking)
    qdrant_client.update_collection(
        collection_name=self.collection_name,
        optimizer_config=models.OptimizersConfigDiff(
            indexing_threshold=0  # Force indexing immediately
        )
    )

    # Option 2: Asynchronous (non-blocking)
    qdrant_client.update_collection(
        collection_name=self.collection_name,
        hnsw_config=models.HnswConfigDiff(
            payload_m=16,  # Trigger rebuild
        )
    )
```

**Configuration**:
```python
# src/core/config.py
class Settings(BaseSettings):
    # Qdrant Index Optimization
    qdrant_optimize_after_ingestion: bool = True
    qdrant_indexing_threshold: int = 0  # 0 = immediate, 20000 = default
```

**Testing**:
1. Ingest 10 documents
2. Verify `indexed_vectors > 0` after ingestion
3. Measure indexing time (should be <5s for small collections)

**Success Criteria**:
- ✅ Index rebuilt automatically after ingestion
- ✅ Configurable via settings
- ✅ Performance acceptable (<5s for <1000 vectors)

---

### **Session 2: Feature Enhancements** (8 hours)

#### Feature 77.4: Community Summarization Batch Job (TD-094)
**Priority**: MEDIUM | **Effort**: 3 SP | **Time**: 3 hours

**Problem**: 92 communities detected, 0 summaries generated (Graph-Global incomplete)

**Context**:
- Community summaries exist in `community_summarizer.py`
- Not integrated into ingestion pipeline (LLM-intensive)
- Should be separate batch job or on-demand

**Solution Options**:

**Option A: Batch Job Script** (Recommended)
```python
# scripts/generate_community_summaries.py

async def generate_summaries(namespace_id: str, batch_size: int = 10):
    """Generate community summaries for a namespace."""

    # 1. Get all communities without summaries
    communities = await get_communities_needing_summaries(namespace_id)

    # 2. Process in batches (avoid OOM)
    for batch in chunk_list(communities, batch_size):
        for community_id in batch:
            # Get community entities and relations
            community_data = await get_community_data(community_id)

            # Generate summary with LLM
            summary = await summarize_community(community_data)

            # Store in Neo4j
            await store_community_summary(community_id, summary)

    logger.info("community_summaries_complete", total=len(communities))
```

**Option B: Admin API Endpoint**
```python
# src/api/v1/admin_graph.py

@router.post("/communities/summarize")
async def generate_community_summaries(
    namespace_id: str,
    community_ids: list[str] | None = None,
    background: bool = True,
):
    """Generate summaries for communities in a namespace."""

    if background:
        # Launch background task
        task_id = await launch_summarization_task(namespace_id, community_ids)
        return {"status": "started", "task_id": task_id}
    else:
        # Synchronous (blocks request)
        result = await generate_summaries_sync(namespace_id, community_ids)
        return {"status": "complete", "summaries": len(result)}
```

**Implementation**:
1. Create batch script (Option A)
2. Add Admin API endpoint (Option B)
3. Add progress tracking (Prometheus metrics)
4. Add configuration (LLM model, batch size, concurrency)

**Testing**:
1. Test with 5 communities (small namespace)
2. Verify summaries stored in Neo4j (:CommunitySummary nodes)
3. Test Graph-Global retrieval with summaries

**Success Criteria**:
- ✅ Batch script generates summaries for all communities
- ✅ Admin API endpoint works (background + sync)
- ✅ Progress tracking visible in logs/metrics
- ✅ Graph-Global retrieval uses summaries

---

#### Feature 77.5: Entity Connectivity as Domain Training Metric (TD-095)
**Priority**: MEDIUM | **Effort**: 3 SP | **Time**: 3 hours

**Problem**: 0.45 relations/entity (low) - sparse graph reduces reasoning power

**Context**:
- **Sprint 76 TD-084/TD-085**: DSPy Domain Training for ER-Extraction prompts implemented
- Entity Connectivity is **domain-specific** (factual vs narrative vs technical)
- Current: 146 entities, 65 RELATES_TO relations (hotpotqa domain)
- Expected: Domain-dependent (see benchmarks below)

**Root Cause**: ER-Extraction prompts come from Domain Training - manual tuning bypasses DSPy optimization!

**Architecture Insight**:
```
Current Pipeline:
1. Domain Training (TD-085) → Domain-Optimized ER Prompts
2. Graph Extraction → Entities + Relations
3. [Missing] Domain Evaluation Metrics

Proposed:
1. Domain Training → Domain-Optimized ER Prompts
2. Graph Extraction → Entities + Relations
3. Domain Evaluation → Entity Connectivity Metrics ← NEW!
4. DSPy Optimization Loop → Improve Prompts based on Metrics
```

**Solution: Integrate Entity Connectivity into Domain Training**

**Step 1: Domain-Specific Connectivity Benchmarks**
```python
# src/domains/knowledge_graph/domain_metrics.py

DOMAIN_CONNECTIVITY_BENCHMARKS = {
    "factual": {
        # Atomic facts (HotpotQA, Wikipedia snippets)
        "relations_per_entity": (0.3, 0.8),  # (min, max)
        "entities_per_community": (1.5, 3.0),
        "description": "Sparse, fact-oriented graphs"
    },
    "narrative": {
        # Stories, articles, reports
        "relations_per_entity": (1.5, 3.0),
        "entities_per_community": (5.0, 10.0),
        "description": "Dense, narrative-driven graphs"
    },
    "technical": {
        # Documentation, manuals, specifications
        "relations_per_entity": (2.0, 4.0),
        "entities_per_community": (3.0, 8.0),
        "description": "Hierarchical, structured graphs"
    },
    "academic": {
        # Research papers, theses
        "relations_per_entity": (2.5, 5.0),
        "entities_per_community": (4.0, 12.0),
        "description": "Citation-heavy, interconnected graphs"
    }
}
```

**Step 2: Add Connectivity Metrics to Domain Training**
```python
# src/components/graph_rag/domain_training.py

async def evaluate_domain_extraction_quality(
    domain_id: str,
    namespace_id: str
) -> DomainExtractionMetrics:
    """Evaluate ER extraction quality for a domain.

    Sprint 77 Feature 77.5: Entity connectivity as quality metric.
    """
    # Get domain benchmark
    benchmark = DOMAIN_CONNECTIVITY_BENCHMARKS.get(
        domain_id,
        DOMAIN_CONNECTIVITY_BENCHMARKS["factual"]  # default
    )

    # Query Neo4j for connectivity stats
    stats = await get_connectivity_stats(namespace_id)

    # Compare to benchmark
    metrics = {
        "relations_per_entity": stats["relations"] / stats["entities"],
        "entities_per_community": stats["entities"] / stats["communities"],
        "benchmark_min": benchmark["relations_per_entity"][0],
        "benchmark_max": benchmark["relations_per_entity"][1],
        "within_benchmark": (
            benchmark["relations_per_entity"][0]
            <= (stats["relations"] / stats["entities"])
            <= benchmark["relations_per_entity"][1]
        )
    }

    return DomainExtractionMetrics(**metrics)
```

**Step 3: DSPy Optimization with Connectivity Metric**
```python
# Use connectivity as DSPy evaluation metric

class ConnectivityMetric(dspy.Metric):
    def __call__(self, example, prediction, trace=None):
        """Score extraction quality by entity connectivity."""
        relations_per_entity = len(prediction.relations) / len(prediction.entities)

        # Domain-specific target
        target = DOMAIN_CONNECTIVITY_BENCHMARKS[example.domain]["relations_per_entity"]

        # Normalized score (0-1)
        if target[0] <= relations_per_entity <= target[1]:
            return 1.0  # Perfect
        elif relations_per_entity < target[0]:
            return relations_per_entity / target[0]  # Penalize sparse
        else:
            return target[1] / relations_per_entity  # Penalize over-extraction
```

**Implementation**:
1. **Add domain-specific connectivity benchmarks** (30min)
   - Research typical connectivity per domain type
   - Add to `domain_metrics.py`

2. **Integrate connectivity into Domain Training UI** (1h)
   - Frontend: Display connectivity metrics in Domain Training panel
   - Backend: Add connectivity evaluation endpoint
   - Show benchmark comparison (green if within range)

3. **Add connectivity to DSPy optimization** (1h)
   - Use ConnectivityMetric in DSPy prompt optimization
   - Re-train hotpotqa domain with connectivity metric
   - Compare before/after results

4. **Create connectivity tracking dashboard** (30min)
   - Prometheus metrics: `graph_connectivity_relations_per_entity{domain="..."}`
   - Grafana panel: Connectivity by domain over time

**Testing**:
1. **Baseline**: 0.45 relations/entity (hotpotqa, factual domain)
2. **Benchmark**: 0.3-0.8 for factual domains → ✅ **Within Range!**
3. **Re-train**: Use DSPy with ConnectivityMetric
4. **Verify**: Connectivity improves while maintaining precision

**Success Criteria**:
- ✅ Domain-specific connectivity benchmarks defined (4 domains)
- ✅ Connectivity metrics integrated into Domain Training UI
- ✅ DSPy optimization uses connectivity metric
- ✅ Grafana dashboard tracks connectivity over time
- ✅ HotpotQA domain stays within factual benchmark (0.3-0.8)

---

## 📋 Task Breakdown

### **Session 1** (5 hours)
| Task | File(s) | Time | Dependencies |
|------|---------|------|--------------|
| 77.1: BM25 namespace fix | `hybrid_search.py` | 1h | None |
| 77.2: Chunk mismatch investigation | Neo4j queries, logs | 2h | None |
| 77.3: Qdrant index rebuild | `vector_embedding.py`, `config.py` | 2h | None |

### **Session 2** (8 hours)
| Task | File(s) | Time | Dependencies |
|------|---------|------|--------------|
| 77.4: Community summaries | `scripts/`, `admin_graph.py` | 3h | None |
| 77.5: Entity connectivity | `domain_metrics.py`, `domain_training.py`, Domain UI | 3h | TD-084/TD-085 |
| Documentation | Sprint results, TDs | 2h | All above |

---

## 📊 Success Metrics

| Metric | Sprint 76 | Sprint 77 Target |
|--------|-----------|------------------|
| BM25 Namespace Accuracy | 0% (all "unknown") | 100% |
| Chunk Consistency (Qdrant/Neo4j) | 82% (14/17) | 100% |
| Indexed Vectors | 0 | 17+ |
| Community Summaries | 0 (0%) | 92 (100%) |
| Relations/Entity (factual domain) | 0.45 | 0.3-0.8 (within benchmark ✅) |
| Domain Connectivity Benchmarks | 0 domains | 4 domains defined |

---

## 🧪 Testing Strategy

### **Unit Tests**
1. BM25 namespace extraction from Qdrant payload
2. Qdrant index optimization API calls
3. Community summarization batch processing

### **Integration Tests**
1. Full ingestion → BM25 namespace correctness
2. Full ingestion → Qdrant/Neo4j chunk count match
3. Community summary generation → Neo4j storage → Graph-Global retrieval

### **E2E Tests** (Playwright)
1. Upload document → verify BM25 namespace filter works
2. Admin panel → trigger community summarization → verify completion
3. Graph query → verify community summaries used

---

## 🚨 Risks & Mitigation

### **Risk 1: Chunk Mismatch Root Cause Unclear**
- **Likelihood**: MEDIUM
- **Impact**: HIGH (blocks data consistency)
- **Mitigation**: Allocate extra 1 hour for deep investigation
- **Fallback**: Re-ingest missing chunks manually

### **Risk 2: Community Summarization Too Slow**
- **Likelihood**: HIGH (92 communities × 30s = 45min)
- **Impact**: MEDIUM (UX issue, not blocker)
- **Mitigation**: Batch processing + background jobs
- **Fallback**: Generate on-demand (lazy loading)

### **Risk 3: Domain Training Integration Complex**
- **Likelihood**: MEDIUM
- **Impact**: LOW (enhances existing system, not critical)
- **Mitigation**:
  - Start with simple benchmarks (4 domains)
  - Test connectivity metric on HotpotQA first
  - UI integration is optional (can use API)
- **Fallback**:
  - Manual connectivity monitoring
  - Accept HotpotQA connectivity (0.45) as baseline for factual domain

---

## 📚 References

- [Sprint 76 Final Results](SPRINT_76_FINAL_RESULTS.md)
- [TD-090: BM25 Namespace Metadata](../technical-debt/TD-090.md)
- [TD-091: Chunk Count Mismatch](../technical-debt/TD-091.md)
- [TD-093: Qdrant Index Optimization](../technical-debt/TD-093.md)
- [TD-094: Community Summarization](../technical-debt/TD-094.md)
- [TD-095: Entity Connectivity](../technical-debt/TD-095.md)
- [Qdrant Optimization API](https://qdrant.tech/documentation/concepts/optimizer/)

---

**Sprint Start**: 2026-01-07 (Session 1)
**Sprint End**: TBD (2 sessions)
**Total Effort**: 11 Story Points
**Estimated Time**: 13 hours
