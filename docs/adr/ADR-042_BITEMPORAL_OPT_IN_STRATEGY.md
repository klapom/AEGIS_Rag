# ADR-042: Bi-Temporal Queries - Opt-In Strategy

**Status:** ACCEPTED
**Date:** 2025-12-08
**Deciders:** Klaus Pommer, Claude Code
**Sprint:** 39 (planned)

---

## Context

AegisRAG hat bereits implementierte (aber nicht aktivierte) Bi-Temporal Query Komponenten:
- `temporal_query_builder.py` - Cypher Query Builder mit temporal Filters
- `evolution_tracker.py` - Entity Change Tracking
- `version_manager.py` - Entity Version Management

Diese Features ermöglichen:
- Point-in-Time Queries ("Was wussten wir am 1. November?")
- Entity Change Tracking mit Audit Trail (`changed_by` User)
- Version Comparison und Rollback

**Problem:** Bi-Temporal Queries haben signifikanten Performance-Overhead:
- +200-300% Query-Zeit durch zusätzliche WHERE-Conditions
- 4 zusätzliche datetime-Felder pro Entity (56 bytes)
- Komplexere Cypher-Queries

**Frage:** Wie aktivieren wir Bi-Temporal Features ohne Performance-Regression für normale Queries?

---

## Decision

Wir implementieren **Opt-In Temporal** mit Feature Flag:

```python
# src/core/config.py
class Settings(BaseSettings):
    temporal_queries_enabled: bool = False  # Default: OFF
    temporal_version_retention: int = 10    # Max Versions pro Entity
```

**Kernprinzipien:**
1. **Default OFF:** Normale Queries bleiben schnell (kein Overhead)
2. **Explizite Aktivierung:** Temporal nur bei Bedarf via UI Toggle oder API Parameter
3. **Isolierte UI:** Temporal Features in separatem Tab (nicht im Haupt-Graph-View)
4. **Pflicht-Indexes:** Composite Indexes für akzeptable Performance bei aktivem Temporal Mode

---

## Alternatives Considered

### Alternative 1: "Always Temporal" (Alle Queries mit temporal Filter)

```python
# Alle Queries haben automatisch temporal Filter
async def query_graph(query: str):
    builder = TemporalQueryBuilder()
    builder.current()  # Immer "valid_to IS NULL" Filter
```

**Pro:**
- Konsistentes Verhalten
- Kein Mode-Switching nötig

**Contra:**
- +200-300% Overhead auf ALLE Queries
- Komplexität für alle User (auch wenn nicht benötigt)
- Performance-Regression ohne Nutzen für 90% der Use Cases

### Alternative 2: "Temporal as Separate System"

Separates Temporal-Graph neben normalem Graph.

**Pro:**
- Vollständige Isolation
- Keine Performance-Auswirkung auf Haupt-Graph

**Contra:**
- Doppelte Infrastruktur (2x Neo4j oder Namespaces)
- Sync-Komplexität zwischen Systemen
- Höhere Kosten

### Alternative 3: "Migration Required"

Alle bestehenden Entities zu Temporal-Schema migrieren.

**Pro:**
- Einheitliches Schema
- Keine Altlasten

**Contra:**
- Wir sind noch nicht produktiv - keine Migration nötig
- Unnötiger Aufwand

---

## Rationale

**Opt-In Temporal** ist optimal weil:

1. **Keine Performance-Regression:**
   - Normale Queries: `MATCH (e:base) RETURN e` - 2ms
   - Mit Temporal: +300% nur wenn aktiviert

2. **Schrittweise Adoption:**
   - Start ohne Temporal (Sprint 38: Auth)
   - Temporal aktivieren wenn Auth fertig (Sprint 39)
   - User können Feature bei Bedarf nutzen

3. **Minimale Code-Änderungen:**
   ```python
   async def query_graph(query: str, temporal_mode: bool = False):
       if temporal_mode and settings.temporal_queries_enabled:
           builder = TemporalQueryBuilder()
           builder.as_of(datetime.now())
       else:
           builder = CypherQueryBuilder()  # Kein Overhead
   ```

4. **Isolierte UI-Komplexität:**
   - Haupt-Graph-View bleibt einfach
   - Temporal-Tab für Power-User mit Time Travel Slider

---

## Implementation Details

### Schema-Erweiterung (Opt-In)

```cypher
// Neue Properties nur bei aktivem Temporal Mode
(:base {
  name: "Kubernetes",
  type: "TECHNOLOGY",
  // ... existing

  // BI-TEMPORAL (nur wenn temporal_queries_enabled=true)
  valid_from: datetime,      // Wann Fakt real gültig wurde
  valid_to: datetime | null, // null = aktuell gültig
  transaction_from: datetime, // Wann in DB gespeichert
  transaction_to: datetime | null, // null = aktuelle Version
  version_number: int,
  changed_by: string         // Erfordert Auth!
})
```

### Pflicht-Indexes

```cypher
// Composite Index für Temporal Queries - MUSS erstellt werden
CREATE INDEX temporal_validity_idx FOR (e:base)
ON (e.valid_from, e.valid_to);

CREATE INDEX temporal_transaction_idx FOR (e:base)
ON (e.transaction_from, e.transaction_to);

// Partial Index für "current only" Queries
CREATE INDEX current_version_idx FOR (e:base)
ON (e.valid_to) WHERE e.valid_to IS NULL;
```

**Performance ohne Indexes:** 10-50x langsamer (Full Node Scan)
**Performance mit Indexes:** +200-300% (akzeptabel)

### API Design

```python
# Expliziter Temporal-Parameter
@router.post("/graph/query")
async def query_graph(
    request: GraphQueryRequest,
    temporal_mode: bool = Query(default=False),
    as_of: datetime | None = Query(default=None)
) -> GraphQueryResponse:
    """Query graph with optional temporal filters."""
```

### Frontend Integration

```typescript
// Isolierter Temporal-Tab im Graph View
<Tabs>
  <Tab label="Graph">
    <GraphView />  {/* Normaler View ohne Temporal */}
  </Tab>
  <Tab label="Time Travel">
    <TimeTravel onDateChange={...} />  {/* Temporal UI */}
    <GraphView temporalMode={true} asOf={selectedDate} />
  </Tab>
</Tabs>
```

---

## Consequences

### Positive

- Keine Performance-Regression für normale Queries
- Schrittweise Feature-Aktivierung möglich
- Isolierte Komplexität (nur Power-User sehen Temporal UI)
- Einfaches Rollback (Feature Flag = false)
- Keine Migration nötig (noch nicht produktiv)

### Negative

- Zwei Code-Pfade (temporal vs. non-temporal)
- Feature Flag Management
- Indexes müssen manuell erstellt werden

### Mitigations

- **Zwei Code-Pfade:** Builder-Pattern abstrahiert Unterschied
- **Feature Flag:** Settings-basiert, zur Laufzeit änderbar
- **Indexes:** Automatische Erstellung beim Feature-Aktivieren via Admin UI

---

## Performance Expectations

| Query-Typ | Ohne Temporal | Mit Temporal | Overhead |
|-----------|---------------|--------------|----------|
| Entity Lookup | 2ms | 8ms | +300% |
| Subgraph (50 nodes) | 50ms | 150ms | +200% |
| Multi-Hop (3 hops) | 200ms | 500ms | +150% |

**Akzeptanz-Kriterium:** Temporal Queries < 500ms für typische Requests

---

## Related Documents

- `src/components/graph_rag/temporal_query_builder.py`
- `src/components/graph_rag/evolution_tracker.py`
- `src/components/graph_rag/version_manager.py`
- Sprint 38: JWT Authentication (prerequisite for `changed_by`)
- Sprint 39: Bi-Temporal Features (implementation)

---

## Decision Outcome

**Chosen Option:** Opt-In Temporal mit Feature Flag

**Begründung:**
- Performance-kritisch: Keine Regression für 90% der Use Cases
- Pragmatisch: Keine Migration nötig (noch nicht produktiv)
- Isoliert: Temporal-UI in separatem Tab
- Sicher: Pflicht-Indexes für akzeptable Performance
