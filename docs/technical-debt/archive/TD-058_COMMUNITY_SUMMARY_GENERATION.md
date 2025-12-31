# TD-058: Community Summary Generation mit Delta-Tracking

## Status
**RESOLVED** ✅ (2025-12-18) - Phases 1-2 implemented in Sprint 52

Phase 3 (Temporal Summaries) moved to TD-064.

## Context

TD-057 implementiert 4-Way Hybrid RRF mit Graph Global Retrieval. Der Global-Channel
nutzt aktuell nur Entity-Name-Matching innerhalb von Communities. GraphRAG (Microsoft, 2024)
empfiehlt zusätzlich **LLM-generierte Community Summaries** für semantische Suche.

## Problem

### 1. Naive Implementierung = Hohe Kosten
```
Jede Ingestion → Alle Communities neu summarisieren → N * LLM-Calls
```

### 2. Community-Grenzen sind instabil
Neue Entities/Relationships können Communities **verschmelzen** oder **splitten**:
```
Vorher: Community 5 (10 Entities) + Community 8 (8 Entities)
Nachher: Community 5 (18 Entities) ← Merged durch neue RELATES_TO Edge
```

### 3. Bi-Temporale Historisierung (Sprint 39)
Mit `valid_from`/`valid_to` auf Relationships existieren **zeitabhängige Community-Strukturen**:
```cypher
-- Community-Struktur am 2025-01-01 war anders als heute!
MATCH (e1)-[r:RELATES_TO]->(e2)
WHERE r.valid_from <= $timestamp AND (r.valid_to IS NULL OR r.valid_to > $timestamp)
```

## Decision

Implementierung von **Delta-Tracking** für inkrementelle Community Summary Updates.

## Architecture

### Phase 1: Delta-Tracking nach Ingestion

```python
@dataclass
class CommunityDelta:
    """Tracks community changes after ingestion."""
    new_communities: set[int]           # Neu erstellte Communities
    updated_communities: set[int]       # Entities hinzugefügt/entfernt
    merged_communities: dict[int, int]  # old_id → new_id (Merge)
    split_communities: dict[int, set[int]]  # old_id → {new_ids} (Split)

async def track_community_changes(
    entities_before: dict[str, int | None],  # entity_id → community_id
    entities_after: dict[str, int],
) -> CommunityDelta:
    delta = CommunityDelta(set(), set(), {}, {})

    for entity_id, new_comm in entities_after.items():
        old_comm = entities_before.get(entity_id)

        if old_comm is None:
            # Neue Entity → neue oder aktualisierte Community
            delta.new_communities.add(new_comm)
        elif old_comm != new_comm:
            # Entity hat Community gewechselt
            delta.updated_communities.add(old_comm)
            delta.updated_communities.add(new_comm)

    # Detect merges/splits durch Community-Size-Analyse
    # ... (siehe Implementation Details)

    return delta
```

### Phase 2: Inkrementelle Summary-Generierung

```python
async def update_community_summaries(delta: CommunityDelta) -> None:
    affected = (
        delta.new_communities |
        delta.updated_communities |
        set(delta.merged_communities.values())
    )

    for community_id in affected:
        entities = await get_community_entities(community_id)
        summary = await generate_summary(entities)
        await store_community_summary(community_id, summary)

    # Alte Summaries für gemergte/gesplittete Communities löschen
    for old_id in delta.merged_communities.keys():
        await delete_community_summary(old_id)
```

### Phase 3: Temporale Community Summaries (Bi-Temporal)

Für Time-Travel Queries (Sprint 39) benötigen wir **versionierte Summaries**:

```python
@dataclass
class TemporalCommunitySummary:
    community_id: int
    summary: str
    valid_from: datetime
    valid_to: datetime | None  # None = aktuell gültig

async def get_community_summary_at(
    community_id: int,
    timestamp: datetime
) -> str | None:
    """Hole Community Summary gültig zum Zeitpunkt."""
    query = """
    MATCH (cs:CommunitySummary {community_id: $community_id})
    WHERE cs.valid_from <= $timestamp
      AND (cs.valid_to IS NULL OR cs.valid_to > $timestamp)
    RETURN cs.summary
    """
    return await neo4j.execute_read(query, community_id=community_id, timestamp=timestamp)
```

#### Historisierungs-Strategie für Summaries

```
Option A: Summary-Snapshots bei jeder Änderung
├── Pro: Exakte historische Rekonstruktion
├── Con: Hoher Speicherbedarf
└── Use Case: Compliance, Audit

Option B: On-Demand Regenerierung
├── Pro: Kein zusätzlicher Speicher
├── Con: Langsam bei Time-Travel Queries (LLM-Call pro Query)
└── Use Case: Seltene historische Abfragen

Option C: Hybrid (Empfohlen)
├── Speichere Summaries für "wichtige" Zeitpunkte (Monatsende, Major Updates)
├── Regeneriere on-demand für Zwischenzeitpunkte
└── Cache regenerierte Summaries für häufige Zeiträume
```

#### Implementation für Hybrid-Ansatz

```python
# Beim Erstellen/Update einer Summary
async def store_temporal_summary(
    community_id: int,
    summary: str,
    valid_from: datetime,
) -> None:
    # Schließe vorherige Summary ab
    await neo4j.execute_write("""
        MATCH (cs:CommunitySummary {community_id: $community_id})
        WHERE cs.valid_to IS NULL
        SET cs.valid_to = $valid_from
    """, community_id=community_id, valid_from=valid_from)

    # Erstelle neue Summary
    await neo4j.execute_write("""
        CREATE (cs:CommunitySummary {
            community_id: $community_id,
            summary: $summary,
            valid_from: $valid_from,
            valid_to: null,
            created_at: datetime()
        })
    """, community_id=community_id, summary=summary, valid_from=valid_from)

# Time-Travel Query mit Fallback
async def get_summary_at_timestamp(
    community_id: int,
    timestamp: datetime
) -> str:
    # Versuche gespeicherte Summary zu finden
    stored = await get_community_summary_at(community_id, timestamp)
    if stored:
        return stored

    # Fallback: Regeneriere aus historischem Graph-State
    entities = await get_community_entities_at(community_id, timestamp)
    if not entities:
        return "Community did not exist at this time."

    summary = await generate_summary(entities)

    # Optional: Cache für häufig abgefragte Zeitpunkte
    if is_frequently_queried_period(timestamp):
        await cache_temporal_summary(community_id, summary, timestamp)

    return summary
```

## Neo4j Schema Extension

```cypher
-- Community Summary Node (temporal)
CREATE CONSTRAINT community_summary_unique
FOR (cs:CommunitySummary)
REQUIRE (cs.community_id, cs.valid_from) IS UNIQUE;

-- Index für Time-Travel Queries
CREATE INDEX community_summary_temporal
FOR (cs:CommunitySummary)
ON (cs.community_id, cs.valid_from, cs.valid_to);
```

## Cost Analysis

| Szenario | Ohne Delta-Tracking | Mit Delta-Tracking | Ersparnis |
|----------|--------------------|--------------------|-----------|
| Kleine Ingestion (10 Entities) | 50 LLM Calls | 3-5 LLM Calls | ~90% |
| Große Ingestion (100 Entities) | 50 LLM Calls | 10-20 LLM Calls | ~60-80% |
| Re-Index (alle Dokumente) | 50 LLM Calls | 50 LLM Calls | 0% |

Geschätzte Kosten pro Summary: ~0.01-0.05€ (je nach LLM und Entity-Anzahl)

## Implementation Plan

### Phase 1: Delta-Tracking Infrastructure ✅ Sprint 52
- [x] `CommunityDelta` Dataclass (`src/components/graph_rag/community_delta_tracker.py`)
- [x] `track_community_changes()` nach Community Detection
- [x] Logging der betroffenen Communities
- [x] 19 Unit Tests

### Phase 2: Summary Generation ✅ Sprint 52
- [x] `generate_community_summary()` mit LLM (`src/components/graph_rag/community_summarizer.py`)
- [x] `CommunitySummary` Node in Neo4j
- [x] Admin LLM Config für Model-Auswahl
- [x] 24 Unit Tests

### Phase 3: Temporal Summaries → TD-064
- [ ] Bi-temporale Summary-Speicherung
- [ ] `get_summary_at_timestamp()` mit Fallback
- [ ] Caching-Strategie für häufige Zeiträume

## Dependencies

- TD-057: 4-Way Hybrid RRF (IMPLEMENTED)
- Sprint 39: Bi-Temporal Knowledge Graph (IMPLEMENTED)
- CommunityDetector (existing)

## References

- **GraphRAG** (Edge et al., 2024) - arXiv:2404.16130 - Community Summaries
- **LightRAG** (Guo et al., 2025) - arXiv:2410.05779 - Dual-level Retrieval
- Sprint 39 Implementation: Bi-Temporal Entity Versioning

## Decision Makers
- Klaus Pommer (Project Lead)
- Claude Code (Implementation)

## Date
2025-12-09
