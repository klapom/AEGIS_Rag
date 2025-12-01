# TD-045: entity_id Property Migration (LightRAG Alignment)

## Summary
Migrate Neo4j entity property from `id` to `entity_id` to align with LightRAG standard schema.

## Priority
**Medium** - Required for LightRAG compatibility, but existing functionality works.

## Current State

### Problem
AEGIS RAG verwendet `id` als Property-Name für Entities:
```cypher
MATCH (e:base {id: $entity_id}) RETURN e
```

LightRAG Standard verwendet `entity_id`:
```cypher
MATCH (e:base {entity_id: $entity_id}) RETURN e
```

### Impact
- LightRAG native Cypher-Queries funktionieren nicht ohne Anpassung
- Community-Beispiele aus LightRAG Docs müssen modifiziert werden
- Interoperabilität mit LightRAG Tools eingeschränkt

## Affected Files

### Source Files (12 files)
```
src/components/graph_rag/neo4j_client.py          # create_temporal_indexes()
src/components/graph_rag/analytics_engine.py      # _calculate_degree_centrality(), calculate_pagerank()
src/components/graph_rag/community_detector.py    # detect_communities(), get_entity_community()
src/components/graph_rag/community_labeler.py     # _get_entity_details()
src/components/graph_rag/community_search.py      # search_by_community()
src/components/graph_rag/dual_level_search.py     # _get_local_context()
```

### Test Files (affected by migration)
```
tests/unit/graph_rag/test_*.py                    # All graph_rag unit tests
tests/integration/test_graph_*.py                 # Graph integration tests
```

## Migration Plan

### Step 1: Data Migration Script
```python
# scripts/migrate_entity_id_property.py
async def migrate_entity_id():
    """Migrate id -> entity_id on all :base nodes."""
    query = """
    MATCH (e:base)
    WHERE e.id IS NOT NULL AND e.entity_id IS NULL
    SET e.entity_id = e.id
    RETURN count(e) AS migrated
    """
    result = await neo4j_client.execute_write(query)
    print(f"Migrated {result['migrated']} entities")

    # Verify migration
    verify_query = """
    MATCH (e:base)
    WHERE e.entity_id IS NULL
    RETURN count(e) AS remaining
    """
    remaining = await neo4j_client.execute_query(verify_query)
    assert remaining[0]['remaining'] == 0, "Migration incomplete"
```

### Step 2: Code Migration
1. Update all Cypher queries: `e.id` -> `e.entity_id`
2. Update Python code accessing `id` property
3. Update Pydantic models if applicable

### Step 3: Index Migration
```cypher
-- Drop old indexes
DROP INDEX entity_valid_from IF EXISTS

-- Create new indexes with entity_id
CREATE INDEX entity_entity_id IF NOT EXISTS FOR (e:base) ON (e.entity_id)
CREATE INDEX entity_valid_from IF NOT EXISTS FOR (e:base) ON (e.valid_from)
```

### Step 4: Optional Cleanup (after verification)
```cypher
-- Remove old id property (after verification)
MATCH (e:base)
WHERE e.id IS NOT NULL
REMOVE e.id
```

## Acceptance Criteria
- [ ] All `:base` nodes have `entity_id` property
- [ ] All Cypher queries use `entity_id` instead of `id`
- [ ] Neo4j indexes updated for `entity_id`
- [ ] All unit tests passing (109 graph_rag tests)
- [ ] Integration tests passing
- [ ] Migration script documented and tested

## Estimated Effort
**5 Story Points** (Sprint 34)

## References
- [ADR-040: LightRAG Neo4j Schema Alignment](../adr/ADR-040-lightrag-neo4j-schema-alignment.md)
- [Under the Covers With LightRAG: Extraction](https://neo4j.com/blog/developer/under-the-covers-with-lightrag-extraction/)
- [LightRAG GitHub Repository](https://github.com/HKUDS/LightRAG)

## Created
2025-12-01 (Sprint 33 Analysis)

## Target Sprint
Sprint 34 (Knowledge Graph Enhancement)
