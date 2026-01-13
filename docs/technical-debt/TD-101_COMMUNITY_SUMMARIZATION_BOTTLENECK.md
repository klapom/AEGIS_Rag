# TD-101: Community Summarization Performance Bottleneck

**Created:** 2026-01-11
**Priority:** CRITICAL
**Story Points:** 21
**Sprint Target:** Sprint 86 (URGENT)

---

## Problem Statement

During multi-format ingestion testing (Sprint 85), **TWO CRITICAL performance bottlenecks** were identified in the community summarization phase:

### CRITICAL Finding 1: Full Graph Re-Summarization

**Every document upload triggers community summarization for the ENTIRE Neo4j graph, not just new entities!**

| Metric | Value | Impact |
|--------|-------|--------|
| Neo4j Total Entities | 3,058 | Full graph size |
| Neo4j Total Relations | 6,007 | Full graph size |
| Communities Processed | ~2,000+ | Per upload! |
| Time per Upload | 40-60 min | Scales with graph size |

**This is O(N) instead of O(delta)** - ingestion time grows linearly with total graph size, not document size.

### CRITICAL Finding 2: Single-Entity Community LLM Calls

For a simple **1153-byte CSV file**, the system generates **2000+ individual community summaries**, with ~95% containing only **1 entity and 0 relationships**.

| Metric | Value | Impact |
|--------|-------|--------|
| Single-Entity Communities | ~95% | Unnecessary LLM calls |
| Time per Summary | ~1.4s | Accumulates to ~40+ min |
| Prompt Cache Hit Rate | ~85% | Helps but doesn't solve root cause |

### Root Cause Analysis

1. **CRITICAL: Full Graph Processing:** Community summarization runs on ALL communities, not just new/affected ones
2. **Isolated Entity Problem:** Each entity without relationships gets assigned to its own community
3. **Unnecessary LLM Calls:** Single-entity communities don't need LLM summarization
4. **No Incremental Updates:** No mechanism to detect which communities changed
5. **Neo4j GDS creates many isolated communities** for unconnected entities

---

## Current Behavior

```python
# src/components/graph_rag/community_summarizer.py
async def summarize_community(self, community_id: int) -> str:
    """Generate summary for any community, regardless of size."""
    # LLM call made even for single-entity communities
    response = await self.llm.generate(prompt)  # ~1.4s per call
```

**Log Example:**
```
generating_community_summary community_id=1754 entities_count=1 relationships_count=0
```

---

## Proposed Solution

### Option A: Skip Single-Entity Summarization (Recommended)

```python
async def summarize_community(self, community_id: int) -> str:
    """Generate summary only for meaningful communities."""
    entities = await self._get_community_entities(community_id)
    relationships = await self._get_community_relationships(community_id)

    # Skip LLM for isolated entities
    if len(entities) == 1 and len(relationships) == 0:
        entity = entities[0]
        return f"{entity['name']}: {entity.get('description', entity.get('type', 'Unknown entity'))}"

    # Full LLM summarization for connected communities
    return await self._llm_summarize(entities, relationships)
```

**Expected Impact:**
- ~95% reduction in LLM calls for community summarization
- Ingestion time: ~40 min → ~2-5 min for typical documents
- Preserves quality for meaningful connected communities

### Option B: Minimum Community Size Threshold

```python
MIN_COMMUNITY_SIZE = 2  # Skip communities with fewer entities

if len(entities) < MIN_COMMUNITY_SIZE:
    return self._create_simple_summary(entities)
```

### Option C: Batch Summarization for Small Communities

Group small communities and summarize in batches to reduce LLM call overhead.

---

## Implementation Plan

### Phase 1: Quick Win (3 SP)
1. Add community size check before LLM call
2. Return entity description for single-entity communities
3. Add metrics for "communities_skipped" vs "communities_summarized"

### Phase 2: Optimization (5 SP)
1. Implement batch summarization for medium-sized communities
2. Add parallel processing for independent communities
3. Improve prompt caching key generation

### Phase 3: Long-term (5 SP)
1. Review community detection algorithm (GDS parameters)
2. Consider alternative community detection that produces fewer isolated entities
3. Implement incremental community summarization

---

## Acceptance Criteria

- [ ] Single-entity communities (0 relationships) are NOT LLM-summarized
- [ ] Ingestion time for 1KB CSV < 5 minutes (currently ~40+ min)
- [ ] Ingestion time for typical PDF (5-10 pages) < 15 minutes
- [ ] Community summary quality preserved for connected communities
- [ ] Metrics track skipped vs summarized communities
- [ ] No regression in RAGAS retrieval scores

---

## Related Items

- TD-078: Section Extraction Performance (similar scaling issue)
- TD-070: Ingestion Performance Tuning (general performance)
- Feature 83.2: LLM Fallback Cascade (related LLM optimization)
- Sprint 85: Multi-Format Ingestion Testing (discovery context)

---

## Discovery Context

**Test Run Details:**
- File: test_document.csv (1153 bytes)
- Content: 3 sections on ML/NLP/Knowledge Graphs
- Expected entities: ~12 (TensorFlow, PyTorch, BERT, Neo4j, etc.)
- Actual communities: ~1755 (isolated from previous ingestions?)
- Timeout: 900s (test still running after full community summarization)

**Logs:**
```
generating_community_summary community_id=1275 entities_count=1 relationships_count=0
...
generating_community_summary community_id=1755 entities_count=4 relationships_count=6  # Rare!
```
