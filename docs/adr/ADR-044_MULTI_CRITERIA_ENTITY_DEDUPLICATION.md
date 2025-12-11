# ADR-044: Hybrid Multi-Criteria Entity Deduplication

**Status:** ACCEPTED
**Date:** 2025-12-10
**Sprint:** 43
**Category:** Data Quality / Graph Performance
**Supersedes:** Extends ADR-017 (Semantic Entity Deduplication)
**Related TDs:** TD-062 (Implementation Details)
**Deciders:** Klaus Pommer, Claude Code

---

## Context

ADR-017 introduced semantic entity deduplication using sentence-transformers with cosine similarity (threshold 0.93). After 30 sprints of production usage and a comprehensive comparison with Neo4j LLM Graph Builder's deduplication approach, we identified significant gaps in our current implementation.

### Problem Statement

**Single-Criteria Limitation:**
The current `SemanticDeduplicator` only uses embedding cosine similarity, missing common duplicate patterns:

| Entity 1 | Entity 2 | Semantic Sim | Detected? | Real Duplicate? |
|----------|----------|--------------|-----------|-----------------|
| "Nicolas Cage" | "nicolas cage" | ~0.87 | No | Yes (case) |
| "Nicolas Cage" | "Nicholas Cage" | ~0.91 | No | Yes (typo) |
| "Nicolas Cage" | "Cage" | ~0.60 | No | Yes (substring) |
| "Nicolas Cage" | "Nick Cage" | ~0.94 | Yes | Yes (semantic) |

**Benchmark Evidence (Q1064 Extraction):**
- 500-char chunks: **116 raw entities** → estimated ~50 unique after proper dedup
- 3000-char chunks: **58 raw entities** → estimated ~45 unique after proper dedup
- Current dedup: ~14% reduction (should be 40-50%)

### Neo4j LLM Graph Builder Approach (Reference)

```cypher
-- Multi-criteria deduplication (graphDB_dataAccess.py)
WHERE apoc.text.distance(e1.id, e2.id) < 3  -- Edit distance
   OR gds.similarity.cosine(e1.embedding, e2.embedding) > threshold
   OR e1.id CONTAINS e2.id  -- Substring containment
```

---

## Decision

**We will extend the Python-based SemanticDeduplicator with multi-criteria matching instead of migrating to Neo4j APOC.**

### Multi-Criteria Deduplication Algorithm

```python
def is_duplicate(entity1: str, entity2: str) -> tuple[bool, str]:
    """Check duplicates using 4 criteria (in order):

    1. Exact match (case-insensitive)
    2. Edit distance < 3 (Levenshtein, for names >= 5 chars)
    3. Substring containment (for names >= 6 chars)
    4. Semantic similarity >= 0.93 (existing)

    Returns:
        (is_duplicate, matched_criterion)
    """
    n1, n2 = entity1.lower().strip(), entity2.lower().strip()

    # Criterion 1: Exact case-insensitive match
    if n1 == n2:
        return True, "exact_match"

    # Criterion 2: Edit distance (typos, minor variations)
    if len(n1) >= 5 and len(n2) >= 5:
        if levenshtein_distance(n1, n2) < 3:
            return True, "edit_distance"

    # Criterion 3: Substring (abbreviations, titles)
    if len(n1) >= 6 and len(n2) >= 6:
        if n1 in n2 or n2 in n1:
            return True, "substring"

    # Criterion 4: Semantic similarity (existing)
    if cosine_similarity(embed(n1), embed(n2)) >= 0.93:
        return True, "semantic"

    return False, "none"
```

### Min-Length Guards

**Why min-length for edit distance (5 chars)?**
- Prevents matching "AI" to "UI" (edit distance = 1)
- Short names have high collision probability

**Why min-length for substring (6 chars)?**
- Prevents matching "AI" contained in "NVIDIA"
- Short strings are too likely to be substrings

---

## Alternatives Considered

### Alternative 1: Full Neo4j APOC Migration

**Description:** Replace Python deduplicator with Cypher + APOC functions

**Pros:**
- Atomic database transactions
- Built-in relationship consolidation via `apoc.refactor.mergeNodes()`
- In-database processing (no data transfer)
- Native orphan node cleanup

**Cons:**
- **APOC plugin dependency** (not in Neo4j Community default)
- **Entity embeddings in Neo4j** (~1KB per entity storage overhead)
- **O(n²) in Cypher** (no batch optimization like Python)
- **No type-grouping** (compares ALL entity types = more false positives)
- **No singleton pattern** (no in-memory embedding cache)
- **Harder debugging** (Cypher vs Python breakpoints)
- **Transaction timeouts** on large merge operations
- **Effort: 1-2 days** vs 2-4 hours for Python extension

**Decision:** REJECTED - Too many drawbacks, higher effort

---

### Alternative 2: GDS (Graph Data Science) Library

**Description:** Use Neo4j GDS for similarity computations

**Pros:**
- Optimized graph algorithms
- KNN for batch similarity

**Cons:**
- Already using GDS for community detection (analytics_engine.py)
- Would require projecting embeddings to GDS graph
- Extra complexity for marginal benefit

**Decision:** REJECTED - Unnecessary for deduplication scope

---

### Alternative 3: Keep Single-Criteria Semantic Only

**Description:** Continue with current ADR-017 implementation

**Pros:**
- No changes required
- Already working

**Cons:**
- Misses 30-50% of duplicates
- Graph quality degrading over time
- Benchmark showed entity explosion with smaller chunks

**Decision:** REJECTED - Data quality insufficient

---

## Implementation Comparison

| Aspect | Neo4j APOC | Hybrid Python (Chosen) |
|--------|------------|------------------------|
| **Effort** | 1-2 days | 2-4 hours |
| **Dependencies** | APOC plugin (separate install) | python-Levenshtein (optional) |
| **Performance** | O(n²) in Cypher | O(n²) in Python + batch embeddings |
| **Type Grouping** | No (compares all types) | Yes (same types only) |
| **Embedding Cache** | No | Yes (singleton model) |
| **Debugging** | Cypher logs | Python debugger |
| **Atomicity** | Transactional | Python objects |
| **Code Changes** | Multiple files | 1 file extension |

---

## Consequences

### Positive

1. **Higher Duplicate Detection Rate:**
   - From ~14% to ~50% duplicate reduction
   - Catches case variations, typos, abbreviations, semantic matches

2. **Minimal Effort:**
   - 2-4 hours vs 1-2 days for Neo4j migration
   - Single class extension (`MultiCriteriaDeduplicator`)

3. **No New Infrastructure:**
   - No APOC plugin installation required
   - `python-Levenshtein` is optional (graceful fallback)

4. **Preserves Existing Optimizations:**
   - Type-grouping (only compare entities of same type)
   - Singleton embedding model (cached in memory)
   - Batch encoding (all embeddings at once)

5. **Better Debugging:**
   - Python breakpoints and logging
   - Clear criterion tracking per duplicate

### Negative / Risks

1. **Non-Atomic Deduplication:**
   - Python-side dedup doesn't benefit from Neo4j transactions
   - Mitigated: Dedup runs before graph insertion

2. **Optional Dependency:**
   - `python-Levenshtein` may not be installed
   - Mitigated: Graceful fallback with warning log

3. **No Automatic Relationship Consolidation:**
   - When entities merge, relationships aren't auto-merged
   - Mitigated: Dedup happens pre-insertion (no relationships yet)

4. **Maintenance of Two Libraries:**
   - GDS already used for analytics, now Levenshtein for dedup
   - Mitigated: Clear separation of concerns

---

## Configuration

```python
# src/core/config.py
class DeduplicationSettings(BaseSettings):
    enable_multi_criteria_dedup: bool = True
    semantic_threshold: float = 0.93
    edit_distance_threshold: int = 3
    min_length_for_edit: int = 5
    min_length_for_substring: int = 6
```

### Feature Flag

```bash
# Disable multi-criteria (fallback to semantic-only)
ENABLE_MULTI_CRITERIA_DEDUP=false
```

---

## Success Metrics

| Metric | Before | Target | Alert Threshold |
|--------|--------|--------|-----------------|
| Duplicate Reduction | ~14% | 40-50% | <20% |
| Unique Entities per Doc | Varies | Stable | >50% variance |
| Dedup Time | 1.5s | <2s | >3s |
| False Positive Rate | N/A | <2% | >5% |

---

## Migration Path

### Phase 1: Implementation (Sprint 43)
- Implement `MultiCriteriaDeduplicator` class
- Add `python-Levenshtein` to optional dependencies
- Unit tests for all criteria
- Feature flag (default: enabled)

### Phase 2: Validation (Sprint 44)
- Run benchmark with multi-criteria enabled
- Compare entity counts vs single-criteria
- Monitor false positive reports

### Phase 3: Future Considerations
- If false positives emerge: Add context-aware exceptions
- If performance degrades: Implement parallel batch processing
- If Neo4j benefits needed: Consider selective APOC integration for post-processing

---

## Related Documents

- [ADR-017: Semantic Entity Deduplication](ADR-017-semantic-entity-deduplication.md) (original)
- [TD-062: Multi-Criteria Entity Deduplication](../technical-debt/TD-062_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md) (implementation)
- [NEO4J_LLM_GRAPH_BUILDER_COMPARISON.md](../NEO4J_LLM_GRAPH_BUILDER_COMPARISON.md) (research)
- [RAGAS_EVALUATION_ANALYSIS.md](../RAGAS_EVALUATION_ANALYSIS.md) Section 3.6 (benchmark data)

---

## Approval

**Decision:** Hybrid Python Multi-Criteria Deduplication
**Approved By:** Klaus Pommer
**Date:** 2025-12-10
**Review Date:** End of Sprint 44

---

**Document Version:** 1.0
**Created:** 2025-12-10
**Last Updated:** 2025-12-10
**Status:** ACCEPTED

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
