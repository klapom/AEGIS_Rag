# Sprint 34: Knowledge Graph Enhancement & LightRAG Alignment

**Status:** PLANNED
**Branch:** `sprint-34-knowledge-graph`
**Start Date:** TBD (nach Sprint 33 Abschluss)
**Estimated Duration:** 5-7 Tage
**Total Story Points:** 55 SP

## Sprint Overview

Sprint 34 steht ganz im Zeichen des **Knowledge Graphen**. Nach erfolgreicher Stabilisierung der Ingestion-Pipeline in Sprint 33 fokussieren wir uns auf:

1. **LightRAG Schema Alignment** - Neo4j Struktur an LightRAG Standard angleichen
2. **RELATES_TO Entity-Entity Relationships** - Beziehungen zwischen Entities speichern
3. **Frontend Graph Visualization** - Bestehenden GraphViewer erweitern (Sprint 29)
4. **Graph Analytics** - Verbesserte Traversierung und Reasoning

## Existing Infrastructure (Sprint 29)

Die Graph-Visualisierung wurde bereits in **Sprint 29** vorbereitet:

### Frontend (bereits implementiert)
- `frontend/src/components/graph/GraphViewer.tsx` - Force-directed Layout mit react-force-graph-2d
- `frontend/src/components/graph/GraphFilters.tsx` - Filter-Komponente
- `frontend/src/components/graph/GraphExportButton.tsx` - Export-Funktionalität
- `frontend/src/api/graphViz.ts` - API Client mit Endpoints
- `frontend/src/types/graph.ts` - TypeScript Types (GraphNode, GraphLink, etc.)

### API Endpoints (bereits implementiert)
- `POST /api/v1/graph/viz/export` - Graph Export
- `POST /api/v1/graph/viz/query-subgraph` - Subgraph fuer Query-Ergebnisse
- `GET /api/v1/graph/viz/statistics` - Graph-Statistiken
- `GET /api/v1/graph/viz/communities` - Community-Liste

### Was fehlt (Sprint 34 Fokus)
- **RELATES_TO Relationships** zwischen Entities (nur MENTIONED_IN existiert)
- **Edge-Type Unterscheidung** im Frontend (alle Edges gleich gefaerbt)
- **Relationship Properties** (weight, description) Anzeige

## Key Decisions

- **ADR-040**: LightRAG Neo4j Schema Alignment (ACCEPTED)
- **TD-045**: entity_id Property Migration - **ENTFAELLT** (kein Live-System)
- **TD-046**: RELATES_TO Relationship Extraction

## Features (revidiert)

| # | Feature | SP | Priority | Dependencies |
|---|---------|-----|----------|--------------|
| 34.1 | RELATES_TO Neo4j Storage | 8 | P0 | - |
| 34.2 | RELATES_TO in Ingestion Pipeline | 13 | P0 | 34.1 |
| 34.3 | Frontend Edge-Type Visualization | 8 | P0 | 34.2 |
| 34.4 | Relationship Tooltips & Details | 5 | P1 | 34.3 |
| 34.5 | Multi-Hop Query Support | 8 | P1 | 34.2 |
| 34.6 | Graph Edge Filter | 5 | P1 | 34.3 |
| 34.7 | Re-Indexing mit RELATES_TO | 3 | P0 | 34.2 |
| 34.8 | E2E Tests Graph Visualization | 5 | P2 | 34.3 |

**Total: 55 SP**

**Hinweis:** entity_id Migration (TD-045) entfaellt, da kein Live-System. Bei Neu-Indexierung wird direkt entity_id verwendet.

---

## Feature Details

### Feature 34.1: RELATES_TO Neo4j Storage (8 SP)
**Priority:** P0

**Bestehendes System:**
Die Relation-Extraktion existiert bereits in `src/components/graph_rag/relation_extractor.py`!
Der `RelationExtractor` liefert bereits:
```python
[{"source": "Alex", "target": "TechCorp", "description": "...", "strength": 8}]
```

**Problem:** Diese Relations werden NICHT in Neo4j gespeichert - nur Entities!

**Tasks:**
- [ ] Erweitere `lightrag_wrapper.py` um `_store_relations_to_neo4j()` Methode
- [ ] Erstelle RELATES_TO Relationships mit Properties (weight, description, source_chunk_id)
- [ ] Update Graph Statistics Query fuer RELATES_TO Count
- [ ] Unit Tests fuer neue Storage-Methode

**Neo4j Schema:**
```cypher
CREATE (e1:base)-[:RELATES_TO {
    weight: 0.8,              -- strength / 10 (normalized)
    description: "...",
    source_chunk_id: "...",
    created_at: datetime()
}]->(e2:base)
```

**Acceptance Criteria:**
- [ ] RELATES_TO relationships werden bei Ingestion erstellt
- [ ] Properties korrekt gespeichert
- [ ] Graph Statistics zeigen RELATES_TO Count

---

### Feature 34.2: RELATES_TO in Ingestion Pipeline (13 SP)
**Priority:** P0
**Technical Debt:** TD-046
**Dependencies:** Feature 34.1

**Bestehendes System:**
Die LLM Prompts existieren bereits!

1. `src/prompts/extraction_prompts.py`:
```python
RELATIONSHIP_EXTRACTION_PROMPT = """Extract relationships between entities...
Return: [{source, target, type, description}]
"""
```

2. `src/components/graph_rag/relation_extractor.py` (LightRAG-Style):
```python
SYSTEM_PROMPT_RELATION = """---Role---
You are an intelligent assistant that identifies relationships...
---Output---
{"relations": [{source, target, description, strength}]}
"""
```

**Was fehlt:** Integration in den LangGraph Ingestion Pipeline

**Tasks:**
- [ ] Erweitere `langgraph_nodes.py` Entity-Extraction Node um Relations
- [ ] Rufe `RelationExtractor.extract()` nach Entity-Extraction auf
- [ ] Uebergebe Relations an `_store_relations_to_neo4j()` (Feature 34.1)
- [ ] Logging fuer Relation-Count
- [ ] Performance-Monitoring (Zeitmessung)

**Pipeline-Integration:**
```python
# In langgraph_nodes.py entity_extraction_node
async def entity_extraction_node(state: IngestionState) -> IngestionState:
    # 1. Entity Extraction (bestehend)
    entities = await entity_extractor.extract(text)

    # 2. NEU: Relation Extraction
    relations = await relation_extractor.extract(text, entities)

    # 3. Store to Neo4j
    await lightrag_wrapper._store_entities_to_neo4j(entities, chunk_id)
    await lightrag_wrapper._store_relations_to_neo4j(relations, chunk_id)  # NEU

    return state.copy(update={"entities": entities, "relations": relations})
```

**Acceptance Criteria:**
- [ ] Relations werden waehrend Ingestion extrahiert
- [ ] Relations werden in Neo4j als RELATES_TO gespeichert
- [ ] Logging zeigt Entity + Relation Count
- [ ] Performance: <5s zusaetzlich pro Chunk

---

### Feature 34.3: Frontend Edge-Type Visualization (8 SP)
**Priority:** P0
**Dependencies:** Feature 34.2

**Bestehende Frontend-Komponenten (Sprint 29):**
- `GraphViewer.tsx` - Force-directed Graph mit react-force-graph-2d
- `GraphFilters.tsx` - Filter-UI (Entity Types)
- `graphViz.ts` - API Client

**Bestehender Code zu erweitern:**
```typescript
// frontend/src/components/graph/GraphViewer.tsx (Zeile 120-133)
const getLinkColor = useCallback(
  (link: any) => {
    // AKTUELL: Nur selected/default
    if (selectedNode && ...) return '#f59e0b';
    return '#d1d5db';  // Gray
  }
);
```

**Tasks:**
- [ ] Erweitere `getLinkColor()` um Edge-Type Check
- [ ] Erweitere `GraphLink` Type um `type: string` (bereits vorhanden als `label`)
- [ ] Add Edge-Thickness basierend auf `weight` Property
- [ ] Update Legend-Overlay fuer Edge-Types

**Code-Aenderung:**
```typescript
const getLinkColor = useCallback((link: any) => {
  const linkType = link.label || link.type;

  // Edge-Type Farben
  switch (linkType) {
    case 'RELATES_TO':
      return '#3B82F6';  // Blue
    case 'MENTIONED_IN':
      return '#9CA3AF';  // Gray
    case 'HAS_SECTION':
      return '#10B981';  // Green
    default:
      return '#d1d5db';
  }
}, []);

const getLinkWidth = useCallback((link: any) => {
  if (link.label === 'RELATES_TO' && link.weight) {
    return 1 + (link.weight * 2);  // 1-3px
  }
  return 1;
}, []);
```

**Acceptance Criteria:**
- [ ] RELATES_TO Edges blau gefaerbt
- [ ] MENTIONED_IN Edges grau gefaerbt
- [ ] Edge-Thickness spiegelt weight wider
- [ ] Legend zeigt Edge-Types

---

### Feature 34.4: Graph Filter & Edge Styling (8 SP)
**Priority:** P1
**Dependencies:** Feature 34.3

**Tasks:**
- [ ] Add filter dropdown for relationship types
- [ ] Add checkbox "Show MENTIONED_IN" / "Show RELATES_TO"
- [ ] Add search filter for entity names
- [ ] Add confidence threshold slider (min weight)
- [ ] Persist filter settings in localStorage
- [ ] Update URL query params for shareable views

**UI Components:**
```typescript
interface GraphFilters {
  showMentionedIn: boolean;
  showRelatesTo: boolean;
  showHasSection: boolean;
  minWeight: number;          // 0.0 - 1.0
  entitySearch: string;
  selectedEntityTypes: string[];  // ["CONCEPT", "TECHNOLOGY", ...]
}
```

**Acceptance Criteria:**
- [ ] Filter controls visible in graph view
- [ ] Filters update graph in real-time
- [ ] Settings persist across sessions
- [ ] URL updates for shareable links

---

### Feature 34.5: Multi-Hop Query Support (8 SP)
**Priority:** P1
**Dependencies:** Feature 34.2

**Tasks:**
- [ ] Implement n-hop traversal queries
- [ ] Add path finding between entities
- [ ] Create API endpoint `GET /api/v1/graph/paths`
- [ ] Visualize paths in frontend
- [ ] Add hop limit configuration (1-5 hops)
- [ ] Performance optimization for deep traversal

**Cypher Examples:**
```cypher
-- 2-hop traversal
MATCH path = (start:base {entity_id: $entity_id})-[:RELATES_TO*1..2]-(connected)
RETURN path

-- Shortest path
MATCH path = shortestPath(
  (start:base {entity_id: $start_id})-[:RELATES_TO*]-(end:base {entity_id: $end_id})
)
RETURN path
```

**Acceptance Criteria:**
- [ ] Multi-hop queries return connected entities
- [ ] Path visualization in frontend
- [ ] Performance <500ms for 3-hop queries
- [ ] API documented in OpenAPI

---

### Feature 34.6: Graph Export (Cytoscape/D3) (5 SP)
**Priority:** P2
**Dependencies:** Feature 34.3

**Tasks:**
- [ ] Add export button to graph view
- [ ] Implement Cytoscape.js JSON export
- [ ] Implement D3.js JSON export
- [ ] Implement vis.js JSON export
- [ ] Add PNG/SVG image export
- [ ] Download file naming with timestamp

**Export Formats:**
```typescript
// Cytoscape format
{
  elements: {
    nodes: [{ data: { id: "ent-1", label: "Web Gateway" } }],
    edges: [{ data: { source: "ent-1", target: "ent-2", type: "RELATES_TO" } }]
  }
}

// D3 format
{
  nodes: [{ id: "ent-1", name: "Web Gateway" }],
  links: [{ source: "ent-1", target: "ent-2", type: "RELATES_TO" }]
}
```

**Acceptance Criteria:**
- [ ] Export buttons visible in graph view
- [ ] All 3 JSON formats downloadable
- [ ] PNG/SVG export works
- [ ] Files properly named

---

### Feature 34.7: Graph Analytics Dashboard (8 SP)
**Priority:** P2
**Dependencies:** Feature 34.2

**Tasks:**
- [ ] Add analytics summary panel
- [ ] Show entity count by type (pie chart)
- [ ] Show relationship count by type (bar chart)
- [ ] Show top 10 connected entities (PageRank)
- [ ] Show graph density metrics
- [ ] Add refresh button for real-time stats

**Metrics:**
```typescript
interface GraphAnalytics {
  totalEntities: number;
  totalRelationships: number;
  entitiesByType: Record<string, number>;
  relationshipsByType: Record<string, number>;
  averageDegree: number;
  graphDensity: number;
  topEntities: Array<{ name: string; degree: number; pagerank: number }>;
}
```

**Acceptance Criteria:**
- [ ] Analytics panel visible in Admin UI
- [ ] Charts render correctly
- [ ] Data updates on refresh
- [ ] Performance <1s load time

---

### Feature 34.8: Re-Indexing with New Schema (3 SP)
**Priority:** P0
**Dependencies:** Feature 34.1, 34.2

**Tasks:**
- [ ] Create full re-index script
- [ ] Clear existing entities and relationships
- [ ] Re-ingest all documents with new extraction
- [ ] Verify schema compliance
- [ ] Document re-indexing process

**Script:**
```bash
# Clear and re-index
poetry run python scripts/reindex_knowledge_graph.py \
  --clear-entities \
  --clear-relationships \
  --source-dir data/sample_documents \
  --batch-size 5
```

**Acceptance Criteria:**
- [ ] Re-indexing completes without errors
- [ ] All entities have `entity_id` property
- [ ] RELATES_TO relationships created
- [ ] Graph structure verified

---

## Architecture References

- **ADR-040**: [LightRAG Neo4j Schema Alignment](../adr/ADR-040-lightrag-neo4j-schema-alignment.md)
- **TD-045**: [entity_id Property Migration](../technical-debt/TD-045_ENTITY_ID_PROPERTY_MIGRATION.md)
- **TD-046**: [RELATES_TO Relationship Extraction](../technical-debt/TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md)

## External References

- [Under the Covers With LightRAG: Extraction - Neo4j Blog](https://neo4j.com/blog/developer/under-the-covers-with-lightrag-extraction/)
- [Under the Covers With LightRAG: Retrieval - Neo4j Blog](https://neo4j.com/blog/developer/under-the-covers-with-lightrag-retrieval/)
- [LightRAG GitHub Repository](https://github.com/HKUDS/LightRAG)

---

## Timeline (Parallel Execution)

```
Day 1-2: Feature 34.1 (entity_id migration) + Feature 34.8 prep
Day 2-4: Feature 34.2 (RELATES_TO extraction)
Day 3-5: Feature 34.3 (Frontend visualization)
Day 4-6: Feature 34.4 (Filters) + Feature 34.5 (Multi-hop)
Day 5-7: Feature 34.6 (Export) + Feature 34.7 (Analytics) + Feature 34.8 (Re-index)
```

**Estimated Total:** 5-7 Tage mit paralleler Entwicklung

---

## Success Criteria

- [ ] Neo4j Schema aligned with LightRAG standard
- [ ] All entities use `entity_id` property
- [ ] RELATES_TO relationships extracted and stored
- [ ] Frontend displays both relationship types visually
- [ ] Graph filters and controls functional
- [ ] Multi-hop queries supported
- [ ] Export functionality working
- [ ] Analytics dashboard populated
- [ ] All tests passing (>80% coverage for new code)
- [ ] Documentation complete

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM relationship extraction quality | Medium | High | Iterative prompt tuning, manual validation |
| Performance regression from additional extraction | Medium | Medium | Batch processing, async execution |
| Frontend graph performance with many edges | Low | Medium | Edge aggregation, lazy loading |
| Migration breaks existing queries | Low | High | Comprehensive test suite, rollback script |

---

## Post-Sprint Review Items

- Evaluate relationship extraction quality (precision/recall)
- Measure ingestion time increase
- Gather user feedback on graph visualization
- Identify optimization opportunities for Sprint 35
