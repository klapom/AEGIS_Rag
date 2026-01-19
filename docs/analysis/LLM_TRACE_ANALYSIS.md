# LLM Request Trace Analysis - Sprint 113

**Date:** 2026-01-19
**Author:** Claude (Sprint 113 Performance Investigation)
**Status:** Active Investigation

---

## Executive Summary

Diese Analyse dokumentiert die komplette Request-Trace eines Chat-Requests durch alle Komponenten des AegisRAG-Systems. Das Ziel ist, Performance-Bottlenecks zu identifizieren und zu quantifizieren.

### Key Finding: Entity Expansion Bottleneck

| Komponente | Zeit (ms) | Anteil |
|------------|-----------|--------|
| **Entity Expansion** | 8,515 | **99.97%** |
| Neo4j Chunk Query | 2.7 | 0.03% |
| Vector Search | 0.27 | 0.00% |
| Intent Classification | 84 | ~1% |

**Root Cause:** Die Entity Expansion in `dual_level_search.py` führt eine zeitintensive N-Hop-Traversal-Query in Neo4j aus.

---

## Detailed Trace (2026-01-19 12:55:48)

### Test Parameters
```
Query: "What is machine learning?"
Session ID: trace-1768827348
API Base: http://localhost:8000
Endpoint: POST /api/v1/chat/
```

### Timeline (Chronologisch)

```
[12:55:48.842] START: HTTP POST gesendet
[12:55:48.857] API Request empfangen (db1bae37-0037-46d4-82e7-6ad9cf708e31)
[12:55:48.XXX] base_graph_created (Router, Agents initialisiert)
[12:55:48.XXX] graph_query_node_invoked (intent=hybrid)
[12:55:48.XXX] graph_query_mode_selected (mode=local)
[12:55:48.XXX] entity_expansion_start
              ↓
              | 8,515ms BLOCKED: N-Hop Neo4j Traversal
              ↓
[12:55:57.XXX] local_search_completed (8,517ms, 0 chunks found)
[12:55:57.XXX] graph_empty_fallback_to_vector (triggered)
[12:55:57.XXX] graph_vector_fallback_complete (0 contexts)
[12:55:57.XXX] coordinator_query_complete (8,534ms)
[12:55:57.401] HTTP Response gesendet (200 OK)
```

### Phase-by-Phase Breakdown

#### Phase 1: HTTP Request Handling
```
Start:     12:55:48.842
End:       12:55:48.857
Duration:  ~15ms
Status:    ✅ Fast
```

#### Phase 2: Intent Classification (C-LARA SetFit)
```
Method:     embedding (SetFit)
Intent:     exploratory
Confidence: 72.77%
Duration:   84ms
Status:     ✅ Fast (Sprint 81 C-LARA: 95.22% accuracy)
```

#### Phase 3: Graph Query Agent
```
Mode:       local
Intent:     hybrid
Namespaces: ['default', 'general']
Duration:   8,518ms
Status:     ⚠️ SLOW - Primary Bottleneck
```

##### Graph Query Sub-Phases:
| Sub-Phase | Duration (ms) | Notes |
|-----------|---------------|-------|
| Agent Initialization | <1 | OK |
| Mode Selection | <1 | OK |
| **Entity Expansion** | **8,515** | **BOTTLENECK!** |
| Neo4j Chunk Query | 2.7 | OK |
| Intent Extraction | 0.09 | OK |

##### Entity Expansion Query (8,515ms):
```cypher
// This is the slow query in dual_level_search.py
MATCH (e1:base)
WHERE e1.namespace_id IN $namespaces
  AND ANY(init_entity IN $initial_entities WHERE
      toLower(e1.entity_name) CONTAINS toLower(init_entity)
      OR toLower(init_entity) CONTAINS toLower(e1.entity_name))

// N-Hop Traversal (graph_hops=2)
OPTIONAL MATCH path = (e1)-[r:RELATES_TO|PART_OF|SIMILAR_TO*1..2]-(e2:base)
WHERE e2.namespace_id IN $namespaces
  AND e2 <> e1

// Collect + Deduplicate
WITH collect(DISTINCT e1.entity_name) + collect(DISTINCT e2.entity_name) AS all_names
UNWIND all_names AS name
WITH DISTINCT name
WHERE name IS NOT NULL
RETURN name
LIMIT 50
```

**Neo4j Warnings während Query:**
- `PART_OF` Relationship-Typ nicht vorhanden
- `SIMILAR_TO` Relationship-Typ nicht vorhanden

#### Phase 4: Vector Search Fallback
```
Trigger:    graph_returned_empty_contexts
Duration:   ~1ms
Results:    0 contexts
Status:     ✅ Fast (but no data)
```

#### Phase 5: Answer Generation
```
Answer:     "I don't have enough information..."
Length:     141 chars
LLM Call:   ❌ Skipped (no contexts found)
Duration:   ~0ms
Status:     ✅ Fast (no LLM needed)
```

---

## Agent Path (Full Flow)

```
1. coordinator: started
2. router (user mode)
3. VectorSearchAgent: started
4. VectorSearchAgent: completed (0 results, 0ms)
5. graph_query_agent: processing graph query
6. graph_query_agent: graph query complete (local mode)  ← 8,518ms spent here
7. VectorSearchAgent: started (fallback)
8. VectorSearchAgent: completed (0 results, 0ms)
9. coordinator: completed (8535ms)
```

---

## Metadata Summary

### Search Metadata
```json
{
  "search_mode": "4way_hybrid",
  "latency_ms": 0.27,
  "result_count": 0,
  "dense_results_count": 0,
  "sparse_results_count": 0,
  "vector_results_count": 0,
  "bm25_results_count": 0,
  "reranking_applied": true,
  "intent": "exploratory",
  "intent_confidence": 0.7277,
  "intent_method": "embedding",
  "intent_latency_ms": 84
}
```

### Graph Search Metadata
```json
{
  "mode": "local",
  "latency_ms": 8518,
  "entities_found": 0,
  "relationships_found": 0,
  "topics_found": 0
}
```

### Coordinator Metadata
```json
{
  "total_latency_ms": 8534,
  "session_id": "trace-1768827348",
  "use_persistence": true
}
```

---

## Root Cause Analysis

### Why is Entity Expansion so slow?

1. **Full Table Scan:** Die Query führt einen `toLower()` Vergleich auf allen Entities durch
2. **N-Hop Traversal:** Variable-length path matching `*1..2` ist teuer
3. **Missing Indexes:** `namespace_id` und `entity_name` scheinen nicht optimal indiziert
4. **Missing Relationship Types:** Neo4j warnings zeigen fehlende `PART_OF` und `SIMILAR_TO` Typen

### Optimization Recommendations

#### Immediate (Sprint 113)

1. **Add Neo4j Indexes:**
```cypher
CREATE INDEX entity_name_idx FOR (n:base) ON (n.entity_name);
CREATE INDEX namespace_idx FOR (n:base) ON (n.namespace_id);
CREATE FULLTEXT INDEX entity_fulltext FOR (n:base) ON EACH [n.entity_name];
```

2. **Reduce Graph Hops:**
- Default von 2 auf 1 reduzieren für einfache Queries
- 2-hop nur für explizite "multi_hop" intents verwenden

3. **Add Timeout:**
- Graph query timeout von 5s einführen
- Bei Timeout: direkt zu Vector fallback

#### Future (Sprint 114+)

1. **Query Caching:**
- Entity expansion results für häufige Queries cachen
- TTL: 5 Minuten

2. **Parallel Execution:**
- Graph + Vector gleichzeitig statt sequentiell
- Schnellstes Ergebnis verwenden

3. **Lazy Entity Expansion:**
- Nur bei tatsächlichem "graph" intent expandieren
- Für "vector" oder "hybrid" überspringen

---

## E2E Test Impact

### Warum dauern Tests 78+ Sekunden?

Der aktuelle Test hatte **keine LLM-Generierung** (keine Ergebnisse gefunden).

Bei Tests **mit Ergebnissen**:
```
Graph Search:     8,500ms  (Entity Expansion)
LLM Generation:  60,000ms  (Ollama Nemotron3 Nano)
HTTP Overhead:    1,000ms
─────────────────────────
Total:          ~70,000ms  (~70 Sekunden)
```

Mit dem neuen **120s Timeout** sollten diese Tests bestehen, ABER die Performance ist noch suboptimal.

### Optimiertes Ziel-Szenario

| Phase | Aktuell | Ziel (Sprint 114) |
|-------|---------|-------------------|
| Entity Expansion | 8,500ms | <500ms |
| Graph Query | 3ms | <3ms |
| Vector Search | 0.3ms | <0.3ms |
| LLM Generation | 60,000ms | <10,000ms |
| **Total** | **~70,000ms** | **<15,000ms** |

---

## Files Referenced

| File | Purpose |
|------|---------|
| `src/agents/graph_query_agent.py` | Graph query orchestration |
| `src/components/graph_rag/dual_level_search.py` | Entity expansion (bottleneck) |
| `src/components/graph_rag/neo4j_client.py` | Neo4j connection |
| `src/agents/coordinator.py` | Request coordination |
| `src/domains/llm_integration/proxy/aegis_llm_proxy.py` | LLM routing |

---

## Appendix: Raw Logs

### Entity Expansion Log Entry
```
12:55:57 local_search_completed
  execution_time_ms: 8517.805337905884
  phase_timings: {
    'entity_expansion_ms': 8515.047073364258,
    'graph_hops_used': 2,
    'neo4j_chunk_query_ms': 2.732992172241211
  }
  query: "What is machine learning?"
  chunks_found: 0
```

### Neo4j Warnings
```
Neo.ClientNotification.Statement.UnknownRelationshipTypeWarning
- Missing: PART_OF (position: line 10, column 50)
- Missing: SIMILAR_TO (position: line 10, column 58)
```

---

**Next Steps:**
1. [ ] Neo4j Indexes erstellen
2. [ ] Graph hop default auf 1 reduzieren
3. [ ] Entity expansion timeout einführen
4. [ ] E2E Tests mit 120s Timeout validieren
