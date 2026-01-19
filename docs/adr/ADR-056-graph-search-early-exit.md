# ADR-056: Graph Search Early-Exit Optimization

**Status:** Accepted
**Date:** 2026-01-19
**Sprint:** 113
**Authors:** Claude Opus 4.5

## Context

E2E tests were failing due to extremely slow response times. Analysis revealed:

| Component | Time | % of Total |
|-----------|------|------------|
| Direct Ollama | 1.22s | 9% |
| Hybrid Search Total | 13.77s | 100% |
| **Graph Search** | **13.38s** | **97.2%** |
| Vector Search | 14ms | 0.1% |

The bottleneck was identified in `SmartEntityExpander.expand_entities()` which performs:
1. **Stage 1:** LLM Entity Extraction (~5-6s)
2. **Stage 2:** Neo4j Graph Query (~1s)
3. **Stage 3:** LLM Synonym Generation (~5-6s, conditional)

These LLM calls executed **even when the namespace had zero entities**, wasting 10-12s per request.

## Decision

Implement an **early-exit check** in `SmartEntityExpander.expand_entities()` that:

1. Queries Neo4j for entity count in the target namespace(s)
2. If count = 0, immediately returns empty list without LLM calls
3. Only proceeds with 3-stage expansion if entities exist

### Implementation

**File:** `src/components/graph_rag/entity_expansion.py`

```python
async def _namespace_has_entities(self, namespaces: list[str]) -> bool:
    """Early-exit check: Does namespace have any entities?"""
    cypher = """
    MATCH (e:base)
    WHERE e.namespace_id IN $namespaces
    RETURN count(e) > 0 AS has_entities
    LIMIT 1
    """
    results = await self.neo4j_client.execute_read(cypher, {"namespaces": namespaces})
    return results[0].get("has_entities", False) if results else False

async def expand_entities(self, query: str, namespaces: list[str], top_k: int = 10):
    # Early-exit if namespace has no entities
    if not await self._namespace_has_entities(namespaces):
        logger.info("entity_expansion_early_exit", reason="namespace_has_no_entities")
        return [], 0

    # Continue with 3-stage expansion...
```

## Consequences

### Positive

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Hybrid Search** | 13.77s | 1.81s | **-87%** |
| **Graph Search** | 13,376ms | 99ms | **-99.3%** |

- Empty namespaces now respond in ~100ms instead of ~13s
- E2E tests no longer timeout on graph search
- No breaking changes to API

### Negative

- Additional Neo4j query (1 COUNT query) for every graph search
- Minimal overhead (~10-20ms) when entities exist

### Neutral

- Fulltext index on `entity_name` + `description` was created as bonus optimization
- 7 files identified for future fulltext query migration (not urgent now)

## Alternatives Considered

### 1. Fulltext Index Migration
Convert all `toLower(e.entity_name) CONTAINS term` queries to `db.index.fulltext.queryNodes()`.

**Pros:** Faster text search (index vs full scan)
**Cons:** Requires changes to 7 files, complex migration
**Decision:** Deferred - early-exit solves immediate problem

### 2. LLM Call Caching
Cache LLM entity extraction results.

**Pros:** Would help with repeated queries
**Cons:** Doesn't help empty namespaces, cache invalidation complex
**Decision:** Not implemented

### 3. Smaller LLM for Entity Extraction
Use faster model (qwen3:8b) for Stage 1 & 3.

**Pros:** Faster LLM calls
**Cons:** Still wastes time on empty namespaces
**Decision:** Not needed after early-exit

## Related

- **Sprint 78:** SmartEntityExpander introduced (3-stage expansion)
- **Sprint 92:** Graph Search performance optimization (17-19s → <2s)
- **Sprint 113:** E2E test timeout investigation (this ADR)
- **ADR-052:** Recursive LLM Adaptive Scoring

## Files Changed

- `src/components/graph_rag/entity_expansion.py` - Added `_namespace_has_entities()` method

## Verification

```bash
# Test hybrid search with empty namespace
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello", "intent": "hybrid"}'

# Check logs for early-exit
docker logs aegis-api 2>&1 | grep "entity_expansion_early_exit"
# Output: entity_expansion_early_exit | reason=namespace_has_no_entities
```
