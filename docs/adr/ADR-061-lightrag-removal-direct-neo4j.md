# ADR-061: LightRAG Removal — Direct Neo4j Architecture

## Status
**Proposed** (2026-02-06) — Planned for Sprint 127

## Context

A comprehensive audit of LightRAG usage in AegisRAG (Sprint 125 planning) revealed that the `lightrag-hku` package (v1.4.9) provides **minimal value** relative to the complexity it adds. AegisRAG has incrementally replaced nearly all LightRAG functionality with custom implementations over Sprints 14-121.

### Current LightRAG Usage (3 Functions)

| # | Function | Location | Purpose |
|---|----------|----------|---------|
| 1 | `rag.chunk_entity_relation_graph._driver` | `neo4j_storage.py:96` | Neo4j AsyncDriver instance |
| 2 | `rag.ainsert_custom_kg()` | `ingestion.py:720` | Store entities/relations in LightRAG's internal format |
| 3 | `rag.aquery(query, param)` | `client.py:235` | Graph query with local/global/hybrid modes |

### AegisRAG Custom Implementations (NOT Using LightRAG)

| Capability | AegisRAG Implementation | Files |
|-----------|------------------------|-------|
| Entity Extraction | 3-Rank LLM Cascade (Nemotron3→GPT-OSS→Hybrid SpaCy) | `extraction_service.py`, `extraction_factory.py` |
| Relation Extraction | RelationExtractor + Gleaning | `relation_extractor.py`, `cross_sentence_extractor.py` |
| Chunking | Docling CUDA section-aware (800-1800 tokens) | `adaptive_chunking.py` |
| Neo4j Schema | Custom Cypher (`:base`, `:chunk`, `MENTIONED_IN`, `RELATES_TO`) | `neo4j_storage.py`, `neo4j_client.py` |
| Entity Dedup | 3-strategy (exact + Levenshtein + BGE-M3 embedding) | `entity_canonicalization.py`, `semantic_deduplicator.py` |
| Relation Dedup | Exact + semantic + hybrid | `relation_deduplicator.py`, `hybrid_relation_deduplicator.py` |
| KG Hygiene | Self-loop detection, evidence validation | `kg_hygiene.py` |
| Community Detection | Neo4j GDS Louvain + summarization | `community_detector.py`, `community_summarizer.py` |
| Graph Query (primary) | DualLevelSearch with entity-expansion | `dual_level_search.py` |
| Embeddings | BGE-M3 1024-dim (Dense + Sparse) | `bge_m3_service.py` |
| Monitoring | Prometheus counters per entity/relation type | `extraction_metrics.py`, `monitoring/metrics.py` |
| DSPy Training | Auto-collection of training samples | `domain_training/training_data_collector.py` |

**45+ files** in `src/components/graph_rag/` are 100% custom code with zero LightRAG imports.

### Problems with Current Architecture

1. **Double Data Storage**: `ainsert_custom_kg()` stores entities in LightRAG's internal format, then `store_chunks_and_provenance()` stores them again in AegisRAG's custom Neo4j schema. Every entity is written twice.

2. **Two Neo4j Drivers**: LightRAG initializes its own Neo4j driver (`rag.chunk_entity_relation_graph._driver`), while AegisRAG has a separate `neo4j_client.py` with its own `AsyncGraphDatabase.driver()`. Two connection pools for one database.

3. **Format Conversion Overhead**: `converters.py` converts AegisRAG's native dicts to LightRAG's format (`convert_entities_to_lightrag_format`, `convert_relations_to_lightrag_format`) — only to pass them to `ainsert_custom_kg()`. This is pure overhead.

4. **S-P-O Triple Constraint**: LightRAG's internal schema stores relations as `RELATES_TO` with a `relation_type` property. ADR-060's 21 universal relation types work within this constraint, but native Neo4j relationship types (e.g., `(e1)-[:DEVELOPED]->(e2)`) would enable more efficient Cypher queries.

5. **Query Path Redundancy**: The primary query path uses `DualLevelSearch` (Sprint 115, ADR-057). LightRAG's `aquery()` is only used as one of 4 signals in `maximum_hybrid_search.py`'s RRF fusion.

6. **Dependency Lock-in**: `lightrag-hku ^1.4.9` pulls in transitive dependencies that may conflict with other packages. The package is maintained by HKU (Hong Kong University) — smaller community than core Neo4j driver.

## Decision

### Remove `lightrag-hku` dependency and replace with direct Neo4j operations.

### Migration Plan

#### Phase 1: Eliminate Double Storage (ingestion.py)

```python
# BEFORE: Two writes
lightrag_entities = convert_entities_to_lightrag_format(all_entities)
await rag.ainsert_custom_kg({...})           # Write 1: LightRAG internal
await store_chunks_and_provenance(rag, ...)  # Write 2: AegisRAG custom

# AFTER: Single write
await store_chunks_and_provenance(neo4j_client, ...)  # Single write
```

#### Phase 2: Replace Neo4j Driver Source (neo4j_storage.py)

```python
# BEFORE: Access LightRAG's internal driver
graph = rag.chunk_entity_relation_graph
async with graph._driver.session() as session:
    await session.run(cypher_query)

# AFTER: Use AegisRAG's own Neo4j client
from src.components.graph_rag.neo4j_client import get_neo4j_client
neo4j_client = get_neo4j_client()
async with neo4j_client.driver.session() as session:
    await session.run(cypher_query)
```

#### Phase 3: Replace rag.aquery() (maximum_hybrid_search.py)

```python
# BEFORE: LightRAG query as RRF signal
result = await lightrag_client.query_graph(query, mode="local")

# AFTER: DualLevelSearch as RRF signal
from src.components.graph_rag.dual_level_search import get_dual_level_search
dls = get_dual_level_search()
result = await dls.search(query, mode="entity_expansion")
```

For global mode, replace with community-based search:
```python
# BEFORE
result = await lightrag_client.query_graph(query, mode="global")

# AFTER
from src.components.graph_rag.community_search import get_community_search
cs = get_community_search()
result = await cs.search_communities(query)
```

#### Phase 4: Cleanup

- Remove `lightrag-hku` from `pyproject.toml`
- Delete `src/components/graph_rag/lightrag/` module (7 files)
- Delete `converters.py` format conversion functions
- Update `LightRAGClient` → rename to `GraphRAGClient` (or remove facade entirely)
- Update all imports and backward-compatibility aliases

### Optional: Native Neo4j Relationship Types

With LightRAG removed, relations can use native Neo4j relationship types:

```cypher
-- BEFORE (constrained by LightRAG)
MERGE (e1)-[r:RELATES_TO]->(e2)
SET r.relation_type = "DEVELOPED"

-- AFTER (native types, more efficient queries)
MERGE (e1)-[r:DEVELOPED]->(e2)
SET r.description = "...",
    r.weight = 0.8
```

This enables direct Cypher pattern matching:
```cypher
-- Find all things NVIDIA developed (fast, index-backed)
MATCH (nvidia:ORGANIZATION {entity_name: "NVIDIA"})-[:DEVELOPED]->(product)
RETURN product

-- vs current approach (slower, property filter)
MATCH (nvidia:base)-[r:RELATES_TO]->(product)
WHERE r.relation_type = "DEVELOPED"
RETURN product
```

**Decision:** Defer native relationship types to a future sprint. Keep `RELATES_TO` with `relation_type` property for backward compatibility in Sprint 127. Evaluate native types after RAGAS benchmark comparison.

## Alternatives Considered

### A. Keep LightRAG (Status Quo)
**Rejected.** Double data storage, format conversion overhead, two Neo4j drivers, and unnecessary dependency complexity outweigh the minimal value of 3 functions.

### B. Fork LightRAG and Customize
**Rejected.** We use <1% of LightRAG's codebase. Maintaining a fork is more effort than removing the dependency entirely.

### C. Gradual Deprecation Over 3 Sprints
**Rejected.** The migration is small enough (~3-5 days) to complete in a single sprint. Gradual deprecation maintains dual codepaths longer than necessary.

### D. Replace with LangChain's GraphRAG
**Rejected.** Would introduce another heavy dependency. AegisRAG's custom implementations are already more capable (3-rank cascade, entity canonicalization, community detection, DSPy training).

## Consequences

### Positive
- **~50% fewer Neo4j writes** during ingestion (eliminate double storage)
- **Simpler architecture** — one Neo4j client, one data path
- **No format conversion** overhead (remove converters.py)
- **Full control** over Neo4j schema (native relationship types possible)
- **Fewer dependencies** — smaller Docker image, no version conflicts
- **Cleaner codebase** — remove ~7 files, ~1,500 lines of wrapper/conversion code

### Negative
- **3-5 days migration effort** (one Sprint 127 feature)
- **Risk of regression** in `maximum_hybrid_search.py` RRF quality — mitigated by RAGAS benchmark comparison (Sprint 126 baseline vs Sprint 127 post-removal)
- **ADR-005 superseded** (LightRAG statt Microsoft GraphRAG) — but the reasoning still holds: lightweight KG > heavy GraphRAG. We're just implementing it ourselves now.

### Estimated Impact on RAGAS Metrics

| Metric | Expected Change | Reasoning |
|--------|----------------|-----------|
| Context Recall | Neutral to +5% | DualLevelSearch already primary path |
| Context Precision | Neutral | Vector search unaffected |
| Faithfulness | Neutral | LLM generation unaffected |
| Answer Relevancy | Neutral to +3% | Elimination of LightRAG's potentially redundant context |

### VRAM Impact
None — LightRAG doesn't use GPU memory. Only Neo4j and application memory affected (one fewer connection pool).

## Related Decisions
- **ADR-005:** LightRAG statt Microsoft GraphRAG → **Superseded** by this ADR
- **ADR-026:** Pure LLM Extraction Pipeline → Unchanged (extraction is 100% custom)
- **ADR-033:** AegisLLMProxy Multi-Cloud Routing → Unchanged
- **ADR-057:** Graph Query Optimization (disable SmartEntityExpander) → Supports this decision
- **ADR-059:** vLLM Dual-Engine Architecture → Independent
- **ADR-060:** Domain Taxonomy Architecture → Independent

## Verification Plan

1. **Sprint 126:** RAGAS Phase 1 Benchmark **with** LightRAG (baseline)
2. **Sprint 127:** Remove LightRAG, re-run RAGAS benchmark
3. **Compare:** If RAGAS metrics within ±5% → migration validated
4. **Rollback:** If significant degradation → revert commit, re-evaluate
