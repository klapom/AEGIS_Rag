# TD-046: RELATES_TO Relationship Extraction (LightRAG Alignment)

## Summary
Implement Entity-to-Entity `RELATES_TO` relationship extraction to align with LightRAG standard schema and enable direct graph traversal between entities.

## Priority
**High** - Critical for LightRAG graph reasoning capabilities.

## Current State

### Problem
AEGIS RAG erstellt nur `MENTIONED_IN` Beziehungen (Entity -> Chunk):
```cypher
(entity:base)-[:MENTIONED_IN]->(chunk:chunk)
```

LightRAG erstellt zusätzlich `RELATES_TO` Beziehungen (Entity <-> Entity):
```cypher
(entity1:base)-[:RELATES_TO {weight: 0.85, description: "...", keywords: [...]}]->(entity2:base)
```

### Impact
- **Kein direktes Graph-Reasoning**: Entity-Entity Beziehungen fehlen
- **Eingeschränkte Graph-Traversierung**: Multi-Hop Queries müssen über Chunks gehen
- **Keine Relationship-Properties**: Keine Beschreibungen oder Gewichtungen für Beziehungen
- **Visualisierung limitiert**: Frontend kann nur Entity-Chunk Verbindungen zeigen

## Target Schema

### RELATES_TO Relationship
```cypher
CREATE (e1:base)-[:RELATES_TO {
    weight: 0.85,              -- Relationship strength (0.0-1.0)
    description: "...",        -- Human-readable description
    keywords: ["...", "..."],  -- Extracted keywords
    source_id: "chunk_123",    -- Source chunk where relationship was extracted
    created_at: datetime()
}]->(e2:base)
```

### Example
```cypher
(:base {entity_id: "ent-web-gateway", entity_name: "Web Gateway"})-[:RELATES_TO {
    weight: 0.92,
    description: "Web Gateway ermöglicht Load Balancing",
    keywords: ["configuration", "load-balancing"]
}]->(:base {entity_id: "ent-load-balancing", entity_name: "Load Balancing"})
```

## Implementation Plan

### Step 1: LLM Extraction Prompt
Erweitere den Entity-Extraction Prompt um Relationship-Extraction:

```python
RELATIONSHIP_EXTRACTION_PROMPT = """
Analyze the following text and extract relationships between entities.

For each relationship, provide:
1. source_entity: The entity where the relationship starts
2. target_entity: The entity where the relationship ends
3. relationship_type: Type of relationship (e.g., "enables", "uses", "contains")
4. description: A short description of the relationship
5. confidence: Confidence score (0.0-1.0)

Text:
{text}

Entities found: {entities}

Output as JSON:
[
  {
    "source_entity": "Web Gateway",
    "target_entity": "Load Balancing",
    "relationship_type": "enables",
    "description": "Web Gateway enables Load Balancing through configuration",
    "confidence": 0.92
  }
]
"""
```

### Step 2: Extraction Pipeline Integration
```python
# src/components/ingestion/langgraph_nodes.py

async def extract_relationships(
    entities: List[Entity],
    chunk_text: str,
    chunk_id: str
) -> List[Relationship]:
    """Extract entity-entity relationships using LLM."""

    # Skip if less than 2 entities
    if len(entities) < 2:
        return []

    prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
        text=chunk_text,
        entities=[e.name for e in entities]
    )

    response = await aegis_llm_proxy.generate(
        prompt=prompt,
        task_type="extraction",
        complexity="HIGH"
    )

    relationships = parse_relationship_json(response)

    # Add source tracking
    for rel in relationships:
        rel.source_id = chunk_id

    return relationships
```

### Step 3: Neo4j Storage
```python
# src/components/graph_rag/neo4j_client.py

async def create_relates_to_relationships(
    self,
    relationships: List[Relationship]
) -> dict[str, int]:
    """Batch create RELATES_TO relationships."""

    query = """
    UNWIND $relationships AS rel
    MATCH (e1:base {entity_id: rel.source_entity_id})
    MATCH (e2:base {entity_id: rel.target_entity_id})
    MERGE (e1)-[r:RELATES_TO]->(e2)
    SET r.weight = rel.confidence,
        r.description = rel.description,
        r.keywords = rel.keywords,
        r.source_id = rel.source_id,
        r.created_at = datetime()
    RETURN count(r) AS created
    """

    result = await self.execute_write(query, {"relationships": relationships})
    return {"relationships_created": result["created"]}
```

### Step 4: Frontend Visualization
```typescript
// frontend/src/components/graph/GraphVisualization.tsx

const edgeColors = {
  MENTIONED_IN: '#9CA3AF',  // Gray
  RELATES_TO: '#3B82F6',    // Blue
  HAS_SECTION: '#10B981',   // Green
  CONTAINS_CHUNK: '#6B7280' // Dark Gray
};

// Edge rendering with different styles
const getEdgeStyle = (edge: GraphEdge) => ({
  color: edgeColors[edge.type] || '#9CA3AF',
  width: edge.type === 'RELATES_TO' ? edge.weight * 3 : 1,
  label: edge.type === 'RELATES_TO' ? edge.description : undefined
});
```

## Affected Files

### Backend
```
src/components/ingestion/langgraph_nodes.py     # Add relationship extraction
src/components/graph_rag/neo4j_client.py        # Add create_relates_to_relationships()
src/components/graph_rag/lightrag_wrapper.py    # Integrate with LightRAG
src/api/v1/graph.py                             # Expose relationship endpoints
```

### Frontend
```
frontend/src/components/graph/GraphVisualization.tsx  # Render RELATES_TO edges
frontend/src/components/graph/GraphControls.tsx       # Filter by relationship type
frontend/src/types/graph.ts                           # Add Relationship type
```

### Tests
```
tests/unit/graph_rag/test_relationship_extraction.py  # New test file
tests/integration/test_relates_to_pipeline.py         # Integration tests
tests/e2e/test_graph_visualization.spec.ts            # E2E graph tests
```

## Acceptance Criteria
- [ ] RELATES_TO relationships extracted during ingestion
- [ ] Relationship properties stored (weight, description, keywords, source_id)
- [ ] Neo4j Cypher queries support RELATES_TO traversal
- [ ] Frontend displays RELATES_TO edges with distinct styling
- [ ] Filter option for relationship types in graph visualization
- [ ] Unit tests for relationship extraction (>80% coverage)
- [ ] Integration tests for full pipeline

## Performance Considerations
- Additional LLM calls for relationship extraction (cost impact)
- Consider batching relationship extraction per document
- Cache entity pairs to avoid duplicate relationship creation
- Index on `entity_id` for fast MATCH queries

## Estimated Effort
**13 Story Points** (Sprint 34)

## References
- [ADR-040: LightRAG Neo4j Schema Alignment](../adr/ADR-040-lightrag-neo4j-schema-alignment.md)
- [Under the Covers With LightRAG: Extraction](https://neo4j.com/blog/developer/under-the-covers-with-lightrag-extraction/)
- [Under the Covers With LightRAG: Retrieval](https://neo4j.com/blog/developer/under-the-covers-with-lightrag-retrieval/)
- [LightRAG GitHub Repository](https://github.com/HKUDS/LightRAG)
- TD-045: entity_id Property Migration (prerequisite)

## Created
2025-12-01 (Sprint 33 Analysis)

## Target Sprint
Sprint 34 (Knowledge Graph Enhancement)
