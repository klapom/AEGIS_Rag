# ADR-045: Namespace Isolation Architecture for Multi-Tenant Data

**Status:** Accepted
**Date:** 2025-12-17
**Sprint:** 51
**Author:** Claude Code

## Context

AEGIS RAG supports two types of document indexing:

1. **Admin Indexing**: Documents indexed via the Admin UI are globally available to all users
2. **User Project Indexing**: Documents indexed within user projects should be isolated to that project

Without proper namespace isolation:
- User A's project documents could leak into User B's search results
- Admin documents might not be properly distinguished from user documents
- Graph traversal could cross namespace boundaries, exposing private data

## Decision

Implement **namespace_id** as a mandatory property on all data elements across both Qdrant and Neo4j:

### 1. Qdrant (Vector Database)

**Chunks** receive `namespace: string` in their payload:
```python
# src/components/ingestion/langgraph_nodes.py
payload = {
    ...
    "namespace": "default",  # Admin-indexed docs
}
```

**Search Filtering** uses namespace array:
```python
# Default search namespaces
allowed_namespaces = ["default", "general"]

# Filter applied in hybrid search
FieldCondition(
    key="namespace",
    match=MatchAny(any=allowed_namespaces),
)
```

### 2. Neo4j (Graph Database)

**All node types** receive `namespace_id: string`:
- `:base` entities (e.g., PERSON, ORGANIZATION)
- `:chunk` nodes

**All relationship types** receive `namespace_id: string`:
- `:RELATES_TO` - semantic relationships between entities
- `:MENTIONED_IN` - provenance from entities to chunks

```cypher
-- Entity creation
MERGE (e:base:PERSON {entity_id: $entity_id})
SET e.namespace_id = $namespace_id,
    ...

-- Relationship creation
MERGE (e1)-[r:RELATES_TO]->(e2)
SET r.namespace_id = $namespace_id,
    ...
```

### 3. Namespace Values

| Context | Namespace Value | Description |
|---------|----------------|-------------|
| Admin Indexing | `"default"` | Globally searchable by all users |
| User Project | `"project_{project_id}"` | Isolated to project owner |
| System/Test | `"general"` | System-level documents |

### 4. Search Behavior

**Default Search** (no namespace specified):
- Includes: `["default", "general"]`
- Excludes: All user project namespaces

**Project-Scoped Search**:
- Includes: `["default", "general", "project_{user_project_id}"]`
- User sees global + their own project documents

## Implementation Details

### Files Modified

1. **`src/components/ingestion/langgraph_nodes.py`**
   - Qdrant payload includes `namespace: "default"`

2. **`src/components/graph_rag/lightrag_wrapper.py`**
   - `insert_prechunked_documents(namespace_id="default")`
   - `_store_chunks_and_provenance_in_neo4j(namespace_id="default")`
   - `_store_relations_to_neo4j(namespace_id="default")`
   - All Neo4j SET clauses include `namespace_id`

3. **`src/components/retrieval/filters.py`**
   - `MetadataFilters.namespace` for Qdrant filtering

4. **`src/core/neo4j_safety.py`** (pre-existing)
   - Query validator ensures namespace filtering on all Neo4j queries

### Migration for Existing Data

Existing data without namespace_id is migrated via:

```python
# Qdrant
client.set_payload(
    collection_name='documents_v1',
    payload={'namespace': 'default'},
    points=point_ids,
)

# Neo4j Entities/Chunks
MATCH (n) WHERE n.namespace_id IS NULL
SET n.namespace_id = "default"

# Neo4j Relationships
MATCH ()-[r]->() WHERE r.namespace_id IS NULL
SET r.namespace_id = "default"
```

## Consequences

### Positive

1. **Data Isolation**: User project documents are completely isolated
2. **Flexible Sharing**: Admin can make documents globally available
3. **Query Safety**: Neo4j safety layer enforces namespace filtering
4. **Audit Trail**: namespace_id provides clear data ownership

### Negative

1. **Storage Overhead**: Additional property on every element (~8-20 bytes each)
2. **Query Complexity**: Every query must include namespace filter
3. **Migration Required**: Existing data needs backfill

### Risks

1. **Forgotten Namespace**: New code paths might not set namespace_id
   - Mitigation: Neo4j safety layer rejects queries without namespace filter

2. **Cross-Namespace Leakage**: Graph traversal might cross boundaries
   - Mitigation: Relationships also have namespace_id for filtering

## Data Model Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                        QDRANT                                   │
├─────────────────────────────────────────────────────────────────┤
│  Collection: documents_v1                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Point                                                    │   │
│  │   vector: [1024 floats]                                  │   │
│  │   payload:                                               │   │
│  │     namespace: "default" | "project_{id}"                │   │
│  │     content: string                                      │   │
│  │     document_id: string                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        NEO4J                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  (:base:PERSON {                    (:chunk {                   │
│     entity_id: "...",                  chunk_id: "...",         │
│     entity_name: "...",                text: "...",             │
│     namespace_id: "default"  ─────────  namespace_id: "default" │
│  })                         MENTIONED  })                       │
│    │                           _IN                              │
│    │ RELATES_TO                                                 │
│    │ {namespace_id: "default"}                                  │
│    ▼                                                            │
│  (:base:ORGANIZATION {...})                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Future Work

1. **User Project Indexing API**: Add `namespace_id` parameter to project indexing endpoint
2. **Namespace Management UI**: Admin interface to manage namespaces
3. **Cross-Namespace Sharing**: Allow selective sharing between namespaces
4. **Namespace Cleanup**: Garbage collection when projects are deleted

## References

- Sprint 41 Feature 41.4: Namespace filtering in search
- Sprint 51: Multi-tenant namespace isolation
- `src/core/neo4j_safety.py`: Query validation layer
