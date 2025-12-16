# TD-057: 4-Way Hybrid Retrieval with Intent-Weighted RRF

## Status
**IMPLEMENTED** (Sprint 42 - 2025-12-09)

## Context

Die aktuelle Retrieval-Architektur nutzt nur 2-Kanal RRF (Qdrant Vector + BM25).
LightRAG's Dual-Level Retrieval (Local/Global) wird nicht genutzt, obwohl die
Infrastruktur vorhanden ist.

## Decision

Implementierung einer **4-Way Hybrid Retrieval** Architektur mit **Intent-gewichtetem RRF**.

## Architecture

### 4-Kanal RRF Formula

```
score(chunk) = w_vec(intent)    * 1/(k+r_vec)
             + w_bm25(intent)   * 1/(k+r_bm25)
             + w_local(intent)  * 1/(k+r_local)
             + w_global(intent) * 1/(k+r_global)
```

### Retriever-Rollen

| Retriever | Funktion | Datenquelle |
|-----------|----------|-------------|
| **Vector (Qdrant)** | Semantische Ähnlichkeit | Chunk-Embeddings |
| **BM25** | Keyword-Matching | Chunk-Text |
| **Graph Local** | Entity-Fakten | Entities → MENTIONED_IN → Chunks |
| **Graph Global** | Themen/Kontext ("Siehe auch") | Communities → Entities → Chunks |

### Intent-Profile (Gewichtungen)

| Intent | Vec | BM25 | Local | Global |
|--------|-----|------|-------|--------|
| `factual` | 0.3 | 0.3 | 0.4 | 0.0 |
| `keyword` | 0.1 | 0.6 | 0.3 | 0.0 |
| `exploratory` | 0.2 | 0.1 | 0.2 | 0.5 |
| `summary` | 0.1 | 0.0 | 0.1 | 0.8 |

## Prerequisites

1. **RELATES_TO Pipeline Fix** - Chunk-ID Alignment zwischen Qdrant und Neo4j
2. **Community Detection** - Leiden/Louvain auf RELATES_TO Graph
3. **Intent Classifier** - Query → Intent Mapping

## Implementation Plan

### Phase 1: Foundation (Sprint 42) ✅ COMPLETE
- [x] Fix Chunk-ID alignment (Qdrant ↔ Neo4j)
- [x] Ensure RELATES_TO relationships are created during ingestion
- [x] Verify MENTIONED_IN relationships work correctly (425 relationships in graph)

### Phase 2: Community Detection (Sprint 42) ✅ COMPLETE
- [x] Run Community Detection after ingestion (automatic via langgraph_nodes.py)
- [x] Store community_id on entity nodes (via CommunityDetector)
- [ ] Generate community summaries (LLM) - FUTURE ENHANCEMENT

### Phase 3: Intent Classification (Sprint 42) ✅ COMPLETE
- [x] Implement Intent Classifier (LLM + rule-based fallback)
  - File: `src/components/retrieval/intent_classifier.py`
  - Uses qwen3:8b via Ollama `/api/generate`
  - 100% accuracy on test queries, ~140-200ms latency
- [x] Define intent → weight mappings (INTENT_WEIGHT_PROFILES)
- [x] Add intent to query pipeline

### Phase 4: 4-Way RRF Integration (Sprint 42) ✅ COMPLETE
- [x] Implement Graph Local → Chunks expansion (MENTIONED_IN)
- [x] Implement Graph Global → Chunks expansion (community_id)
- [x] Integrate into FourWayHybridSearch class
  - File: `src/components/retrieval/four_way_hybrid_search.py`
- [x] Add intent-weighted scoring via weighted_reciprocal_rank_fusion

## Implementation Files

| File | Purpose |
|------|---------|
| `src/components/retrieval/intent_classifier.py` | Intent classification (LLM + rule-based) |
| `src/components/retrieval/four_way_hybrid_search.py` | 4-Way RRF fusion engine |
| `src/components/ingestion/langgraph_nodes.py` | Automatic Community Detection |
| `tests/unit/test_intent_classifier.py` | 67 unit tests |
| `tests/unit/test_four_way_hybrid_search.py` | 28 unit tests |

## Test Results

- **95 unit tests** - All passing (0.95s execution time)
- **Live Intent Classification**: 100% accuracy on 4 test queries
- **Graceful Degradation**: System continues with available channels when some fail

## Graph Expansion Queries

### Local → Chunks
```cypher
MATCH (e:base)-[:MENTIONED_IN]->(c:chunk)
WHERE e.entity_name IN $matched_entities
RETURN c.chunk_id, c.text, count(e) AS relevance
ORDER BY relevance DESC
```

### Global → Chunks
```cypher
MATCH (e:base)-[:MENTIONED_IN]->(c:chunk)
WHERE e.community_id = $community_id
RETURN c.chunk_id, c.text, count(e) AS relevance
ORDER BY relevance DESC
```

## References

### Internal ADRs
- ADR-003: Hybrid Vector-Graph Retrieval Architecture
- ADR-005: LightRAG statt Microsoft GraphRAG
- ADR-009: Reciprocal Rank Fusion für Hybrid Search
- ADR-040: LightRAG Neo4j Schema Alignment

### Academic References
- **GraphRAG** (Edge et al., 2024) - arXiv:2404.16130 - Local/Global, Leiden Communities
- **LightRAG** (Guo et al., EMNLP 2025) - arXiv:2410.05779 - Dual-level Retrieval
- **HybridRAG** (2024) - arXiv:2408.04948 - Vector + Graph Fusion
- **Adaptive-RAG** (Jeong et al., NAACL 2024) - arXiv:2403.14403 - Intent-Classification
- **Fusion Functions** (Bruch et al., ACM TOIS 2023) - arXiv:2210.11934 - Learned Weights vs RRF

## Decision Makers
- Klaus Pommer (Project Lead)
- Claude Code (Implementation)

## Date
2025-12-09
