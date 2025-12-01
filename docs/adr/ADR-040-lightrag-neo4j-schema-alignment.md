# ADR-040: LightRAG Neo4j Schema Alignment

## Status
**ACCEPTED** (2025-12-01)

## Context

Nach der erfolgreichen Implementierung des VLM Image Enrichment Pipelines in Sprint 33 wurde eine Analyse der Neo4j Graph-Struktur durchgeführt. Dabei wurde festgestellt, dass unsere aktuelle Implementierung von der offiziellen LightRAG Neo4j Schema-Konvention abweicht.

### Aktuelle AEGIS RAG Struktur

```cypher
-- Entity Nodes
(:base:CONCEPT {id: "...", entity_type: "CONCEPT", entity_name: "..."})
(:base:TECHNOLOGY {id: "...", entity_type: "TECHNOLOGY", entity_name: "..."})

-- Relationships
(entity:base)-[:MENTIONED_IN]->(chunk:chunk)

-- Section Extensions (Sprint 32, ADR-039)
(:Document)-[:HAS_SECTION]->(:Section)
(:Section)-[:CONTAINS_CHUNK]->(:chunk)
(:Section)-[:DEFINES]->(entity:base)
```

### Offizielle LightRAG Struktur

Basierend auf der [Neo4j Developer Blog Analyse](https://neo4j.com/blog/developer/under-the-covers-with-lightrag-extraction/):

```cypher
-- Entity Nodes (beachte: entity_id statt id)
(:base {entity_id: "ent-...", entity_type: "...", entity_name: "...", description: "..."})

-- Document/Chunk Nodes
(:Document {id: "...", content: "...", file_path: "..."})
(:Chunk {content: "...", full_doc_id: "...", embedding: [...]})

-- Relationships
(entity:base)-[:RELATES_TO {weight: 0.8, description: "...", keywords: [...]}]->(entity:base)
(entity:base)-[:MENTIONED_IN]->(chunk:Chunk)
(document:Document)-[:CONTAINS]->(chunk:Chunk)
```

### Abweichungen identifiziert

| Aspekt | LightRAG Standard | AEGIS RAG Aktuell | Status |
|--------|-------------------|-------------------|--------|
| Entity Property | `entity_id` | `id` | Abweichend |
| Entity-Entity Relations | `RELATES_TO` mit properties | Nicht vorhanden | FEHLT |
| Node Label | `:base` | `:base` (korrekt) | OK |
| `MENTIONED_IN` | Vorhanden | Vorhanden | OK |
| Section Schema | Nicht in LightRAG | Eigene Erweiterung | OK (Zusatz) |

## Decision

Wir werden in **Sprint 34** die Neo4j Schema-Struktur an den LightRAG Standard angleichen:

1. **Property Migration**: `id` → `entity_id` auf allen `:base` Nodes
2. **Relationship Extraction**: Implementierung von `RELATES_TO` Entity-Entity Beziehungen
3. **Frontend Visualisierung**: Graph-UI für beide Relationship-Typen (`MENTIONED_IN` und `RELATES_TO`)
4. **Backward Compatibility**: Section-Schema (ADR-039) bleibt erhalten als Erweiterung

## Consequences

### Positive
- **LightRAG-Kompatibilität**: Native Cypher-Queries aus LightRAG Dokumentation funktionieren
- **Graph Reasoning verbessert**: `RELATES_TO` ermöglicht direkte Entity-Entity Traversierung
- **Reichere Visualisierung**: Frontend kann Entity-Beziehungen als separate Edge-Typen darstellen
- **Community Alignment**: Einfacherer Austausch mit LightRAG Community

### Negative
- **Migration erforderlich**: Bestehende Daten müssen migriert werden
- **Re-Indexing nötig**: Für `RELATES_TO` Extraction muss neu indexiert werden
- **Temporärer Overhead**: Zusätzliche LLM-Calls für Relationship-Extraction

### Neutral
- Section-Schema (ADR-039) bleibt unverändert (ist Erweiterung, kein Konflikt)
- Chunk-Label bleibt `chunk` (lowercase) - LightRAG verwendet `Chunk` (uppercase)

## Implementation Plan

### Phase 1: Property Migration (TD-045)
```cypher
-- Migration Query
MATCH (e:base)
WHERE e.id IS NOT NULL AND e.entity_id IS NULL
SET e.entity_id = e.id
REMOVE e.id
```

### Phase 2: RELATES_TO Extraction (TD-046)
- LLM-basierte Relationship-Extraction während Ingestion
- Edge-Properties: `weight`, `description`, `keywords`, `source_id`
- Integration in `langgraph_nodes.py` Entity Extraction Node

### Phase 3: Frontend Graph Visualization
- Unterschiedliche Edge-Farben: `MENTIONED_IN` (grau), `RELATES_TO` (blau)
- Edge-Labels und Tooltips mit Relationship-Properties
- Filter-Optionen für Relationship-Typen

## References

- [Under the Covers With LightRAG: Extraction - Neo4j Blog](https://neo4j.com/blog/developer/under-the-covers-with-lightrag-extraction/)
- [Under the Covers With LightRAG: Retrieval - Neo4j Blog](https://neo4j.com/blog/developer/under-the-covers-with-lightrag-retrieval/)
- [LightRAG GitHub Repository](https://github.com/HKUDS/LightRAG)
- ADR-039: Adaptive Section-Aware Chunking (bleibt erhalten)
- TD-045: entity_id Property Migration
- TD-046: RELATES_TO Relationship Extraction

## Decision Makers
- Klaus Pommer (Project Lead)
- Claude Code (Implementation)

## Date
2025-12-01
