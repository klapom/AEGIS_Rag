# TD-048: Graph Extraction with Unified Chunks (Sprint 16)

**Status:** OPEN
**Priority:** MEDIUM
**Severity:** Architectural Inconsistency
**Original Sprint:** Sprint 16 (Feature 16.5)
**Story Points:** 13 SP
**Created:** 2025-12-04

---

## Problem Statement

Graph extraction in LightRAG is not fully aligned with the unified chunking strategy. Entity-to-chunk provenance tracking is incomplete, making it difficult to trace which chunks contributed to specific entity extractions.

**Current State:**
- LightRAG extracts entities but chunk provenance is inconsistent
- Neo4j `MENTIONED_IN` relationships lack `source_chunk_id` property
- Cross-layer consistency between Qdrant chunks and Neo4j entities unclear
- BM25 corpus, Qdrant points, and LightRAG chunk counts may diverge

---

## Impact

### Functional Impact
- Cannot reliably trace entity origins to source chunks
- Debugging entity extraction issues is difficult
- No validation that all indexes are synchronized

### Architecture Impact
- Violates "single source of truth" principle for chunks
- Makes re-indexing validation unreliable
- Cross-layer similarity comparisons not possible

---

## Current Implementation

### LightRAG Entity Extraction
```python
# Current: Entities created without explicit chunk provenance
(entity:base)-[:MENTIONED_IN]->(chunk:chunk)
# Missing: source_chunk_id property on relationship
```

### Expected Implementation
```python
# Target: Full provenance tracking
(entity:base)-[:MENTIONED_IN {
    source_chunk_id: "chunk_abc123",  # Link to Qdrant chunk
    confidence: 0.95,
    extraction_timestamp: datetime()
}]->(chunk:chunk)
```

---

## Solution

### Phase 1: Add Provenance to MENTIONED_IN Relationships

```python
# src/components/graph_rag/lightrag_wrapper.py

async def store_entity_with_provenance(
    self,
    entity: Entity,
    chunk_id: str,
    confidence: float
) -> None:
    """Store entity with full chunk provenance."""
    query = """
    MERGE (e:base {entity_id: $entity_id})
    SET e.entity_name = $name, e.entity_type = $type
    MERGE (c:chunk {chunk_id: $chunk_id})
    MERGE (e)-[r:MENTIONED_IN]->(c)
    SET r.source_chunk_id = $chunk_id,
        r.confidence = $confidence,
        r.extraction_timestamp = datetime()
    """
```

### Phase 2: Refactor LightRAGWrapper.insert_documents()

```python
async def insert_documents(
    self,
    chunks: List[Chunk]  # Accept unified chunks, not raw text
) -> dict:
    """Insert documents using unified chunks from ChunkingService."""
    for chunk in chunks:
        entities = await self.extract_entities(chunk.text)
        for entity in entities:
            await self.store_entity_with_provenance(
                entity=entity,
                chunk_id=chunk.chunk_id,  # From unified chunking
                confidence=entity.confidence
            )
```

### Phase 3: Validate Index Consistency

```python
async def validate_index_consistency() -> dict:
    """Validate all indexes have same chunk count."""
    qdrant_count = await qdrant_client.count_points()
    bm25_count = bm25_engine.corpus_size()
    neo4j_chunks = await neo4j_client.count_chunks()

    return {
        "qdrant_points": qdrant_count,
        "bm25_corpus": bm25_count,
        "neo4j_chunks": neo4j_chunks,
        "consistent": qdrant_count == bm25_count == neo4j_chunks
    }
```

---

## Acceptance Criteria

- [ ] `MENTIONED_IN` relationships include `source_chunk_id` property
- [ ] LightRAGWrapper accepts unified Chunk objects (not raw text)
- [ ] Entity extraction tracks chunk provenance
- [ ] Validation endpoint confirms index consistency
- [ ] BM25 corpus size == Qdrant points count == Neo4j chunk count
- [ ] Unit tests for provenance tracking (10+ tests)
- [ ] Integration tests for cross-index consistency

---

## Affected Files

```
src/components/graph_rag/lightrag_wrapper.py    # Main refactoring
src/components/graph_rag/neo4j_client.py        # Add provenance queries
src/components/ingestion/langgraph_nodes.py     # Pass unified chunks
src/api/v1/admin.py                             # Add validation endpoint
tests/unit/graph_rag/test_provenance.py         # New tests
tests/integration/test_index_consistency.py     # New tests
```

---

## Dependencies

- **TD-054:** Unified Chunking Service (provides chunk objects)
- **ADR-022:** Unified Chunking Service decision

---

## Estimated Effort

**Story Points:** 13 SP

**Breakdown:**
- Phase 1 (Provenance properties): 5 SP
- Phase 2 (Refactor insert_documents): 5 SP
- Phase 3 (Validation): 3 SP

---

## References

- [SPRINT_PLAN.md - Sprint 16 Feature 16.5](../sprints/SPRINT_PLAN.md#sprint-16)
- [TD-054: Unified Chunking Service](TD-054_UNIFIED_CHUNKING_SERVICE.md)
- [ADR-022: Unified Chunking Service](../adr/ADR-022-unified-chunking-service.md)

---

## Target Sprint

**Recommended:** Sprint 38 (after TD-054 Unified Chunking)

---

**Last Updated:** 2025-12-04
