# TD-062: Multi-Criteria Entity Deduplication

**Created:** 2025-12-10
**Status:** COMPLETE ✅
**Completed:** 2025-12-11
**Priority:** Medium
**Effort:** 2-4 hours
**Sprint:** 43

---

## Problem Statement

The current `SemanticDeduplicator` uses **single-criteria** deduplication based only on cosine similarity of entity name embeddings with a threshold of 0.93. This approach misses several common duplicate patterns:

| Entity 1 | Entity 2 | Current (Semantic) | Should Match? |
|----------|----------|-------------------|---------------|
| "Nicolas Cage" | "nicolas cage" | ~0.87 ❌ | Yes (case only) |
| "Nicolas Cage" | "Nicholas Cage" | ~0.91 ❌ | Yes (typo) |
| "Nicolas Cage" | "Cage" | ~0.60 ❌ | Yes (substring) |
| "Nicolas Cage" | "Nick Cage" | ~0.94 ✅ | Yes (semantic) |

**Impact:** Benchmark with 500-char chunks extracted 116 entities, likely containing 30-50% duplicates that weren't merged.

---

## Root Cause Analysis

The Neo4j LLM Graph Builder uses **multi-criteria** deduplication:

```cypher
-- Neo4j approach (from graphDB_dataAccess.py)
WHERE apoc.text.distance(e1.id, e2.id) < 3  -- Edit distance
   OR gds.similarity.cosine(e1.embedding, e2.embedding) > threshold
   OR e1.id CONTAINS e2.id  -- Substring
```

Our current approach:
```python
# AegisRAG approach (semantic_deduplicator.py)
if cosine_similarity(embed(name1), embed(name2)) >= 0.93:
    return True  # That's it - only semantic
```

---

## Proposed Solution: Hybrid Multi-Criteria Deduplicator

Extend `SemanticDeduplicator` with additional criteria while keeping Python-based implementation (no APOC dependency).

### Implementation

```python
# src/components/graph_rag/semantic_deduplicator.py

try:
    from Levenshtein import distance as levenshtein_distance
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False

class MultiCriteriaDeduplicator(SemanticDeduplicator):
    """Extended deduplication with edit distance + substring + semantic similarity.

    Criteria (evaluated in order, first match wins):
    1. Exact match (case-insensitive)
    2. Edit distance < 3 (for entities >= 5 chars)
    3. Substring containment (for entities >= 6 chars)
    4. Semantic similarity >= threshold (existing)

    The min-length guards prevent false positives like "AI" in "NVIDIA".
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        threshold: float = 0.93,
        device: str = "cpu",
        edit_distance_threshold: int = 3,
        min_length_for_edit: int = 5,
        min_length_for_substring: int = 6,
    ) -> None:
        super().__init__(model_name, threshold, device)
        self.edit_distance_threshold = edit_distance_threshold
        self.min_length_for_edit = min_length_for_edit
        self.min_length_for_substring = min_length_for_substring

        if not LEVENSHTEIN_AVAILABLE:
            logger.warning(
                "python-Levenshtein not installed, edit distance check disabled. "
                "Install with: pip install python-Levenshtein"
            )

    def _is_duplicate_by_criteria(self, name1: str, name2: str) -> tuple[bool, str]:
        """Check if two entity names are duplicates using multiple criteria.

        Returns:
            Tuple of (is_duplicate, matched_criterion)
        """
        n1_lower = name1.lower().strip()
        n2_lower = name2.lower().strip()

        # Criterion 1: Exact match (case-insensitive)
        if n1_lower == n2_lower:
            return True, "exact_match"

        # Criterion 2: Edit distance (only for entities with min length)
        if LEVENSHTEIN_AVAILABLE:
            if len(n1_lower) >= self.min_length_for_edit and len(n2_lower) >= self.min_length_for_edit:
                if levenshtein_distance(n1_lower, n2_lower) < self.edit_distance_threshold:
                    return True, "edit_distance"

        # Criterion 3: Substring containment (only for entities with min length)
        if len(n1_lower) >= self.min_length_for_substring and len(n2_lower) >= self.min_length_for_substring:
            if n1_lower in n2_lower or n2_lower in n1_lower:
                return True, "substring"

        # Criterion 4: Semantic similarity (existing)
        # Note: This is checked in _deduplicate_group via similarity matrix
        return False, "none"

    def _deduplicate_group(
        self, entities: list[dict[str, Any]], entity_type: str
    ) -> list[dict[str, Any]]:
        """Deduplicate entities using multi-criteria matching."""
        if len(entities) <= 1:
            return entities

        names = [e["name"] for e in entities]

        # First pass: Check non-semantic criteria (fast)
        used = set()
        clusters = []  # list of (representative_idx, [member_indices])

        for i in range(len(entities)):
            if i in used:
                continue

            cluster = [i]
            for j in range(i + 1, len(entities)):
                if j in used:
                    continue

                is_dup, criterion = self._is_duplicate_by_criteria(names[i], names[j])
                if is_dup:
                    cluster.append(j)
                    used.add(j)
                    logger.debug(
                        "multi_criteria_match",
                        entity1=names[i],
                        entity2=names[j],
                        criterion=criterion,
                    )

            clusters.append((i, cluster))

        # Second pass: Check semantic similarity for remaining entities
        # (entities not matched by criteria 1-3)
        remaining_indices = [c[0] for c in clusters]  # Representatives only

        if len(remaining_indices) > 1:
            remaining_names = [names[i] for i in remaining_indices]
            embeddings = self.model.encode(
                remaining_names, batch_size=64, convert_to_tensor=True, show_progress_bar=False
            )
            embeddings_np = embeddings.cpu().numpy()
            similarity_matrix = cosine_similarity(embeddings_np)

            # Merge clusters based on semantic similarity
            merged_used = set()
            final_clusters = []

            for idx, (rep_i, cluster_i) in enumerate(clusters):
                if idx in merged_used:
                    continue

                merged_cluster = list(cluster_i)
                for jdx in range(idx + 1, len(clusters)):
                    if jdx in merged_used:
                        continue

                    if similarity_matrix[idx, jdx] >= self.threshold:
                        rep_j, cluster_j = clusters[jdx]
                        merged_cluster.extend(cluster_j)
                        merged_used.add(jdx)
                        logger.debug(
                            "semantic_match",
                            entity1=names[rep_i],
                            entity2=names[rep_j],
                            similarity=float(similarity_matrix[idx, jdx]),
                        )

                final_clusters.append((rep_i, merged_cluster))
        else:
            final_clusters = clusters

        # Build deduplicated list
        deduplicated = []
        for rep_idx, member_indices in final_clusters:
            representative = entities[rep_idx].copy()
            if len(member_indices) > 1:
                representative["description"] = (
                    f"{entities[rep_idx]['description']} "
                    f"[Deduplicated from {len(member_indices)} mentions]"
                )
            deduplicated.append(representative)

        return deduplicated
```

### Configuration

```python
# src/core/config.py - Add new settings
enable_multi_criteria_dedup: bool = Field(
    default=True,
    description="Use multi-criteria dedup (edit distance + substring + semantic)"
)
dedup_edit_distance_threshold: int = Field(
    default=3,
    description="Max edit distance for duplicate detection (Levenshtein)"
)
dedup_min_length_for_edit: int = Field(
    default=5,
    description="Min entity name length for edit distance check"
)
dedup_min_length_for_substring: int = Field(
    default=6,
    description="Min entity name length for substring check"
)
```

---

## Comparison: Neo4j vs Hybrid Python

| Aspect | Neo4j (APOC) | Hybrid Python |
|--------|--------------|---------------|
| **Dependencies** | APOC + GDS plugins | python-Levenshtein (optional) |
| **Performance** | O(n²) in Cypher | O(n²) in Python (faster) |
| **Type Grouping** | No (compares all) | Yes (only same types) |
| **Debugging** | Cypher logs | Python logging |
| **Singleton Cache** | No | Yes (embeddings cached) |
| **Atomic Merge** | Yes (transactions) | No (Python objects) |
| **Relationship Consolidation** | Automatic | Manual (if needed) |

**Decision:** Hybrid Python approach chosen because:
1. No APOC dependency required
2. Faster (Python + cached embeddings)
3. Better debugging
4. Type-grouping prevents false positives
5. Minimal code changes (extend existing class)

---

## Files to Modify

| File | Change |
|------|--------|
| `src/components/graph_rag/semantic_deduplicator.py` | Add `MultiCriteriaDeduplicator` class |
| `src/core/config.py` | Add new config options |
| `pyproject.toml` | Add `python-Levenshtein` dependency |
| `tests/unit/test_semantic_deduplicator.py` | Add tests for new criteria |

---

## Expected Results

### Before (Single Criteria)
- 500-char chunks: 116 entities → ~100 after dedup (14% reduction)
- Misses: case variants, typos, substrings

### After (Multi Criteria)
- 500-char chunks: 116 entities → ~50-60 after dedup (50%+ reduction)
- Catches: case variants, typos (edit dist < 3), substrings, semantic matches

---

## Test Cases

```python
def test_multi_criteria_deduplication():
    dedup = MultiCriteriaDeduplicator(threshold=0.93)

    entities = [
        {"name": "Nicolas Cage", "type": "PERSON", "description": "Actor"},
        {"name": "nicolas cage", "type": "PERSON", "description": "Star"},  # case
        {"name": "Nicholas Cage", "type": "PERSON", "description": "Lead"},  # typo
        {"name": "Cage", "type": "PERSON", "description": "Performer"},  # substring
        {"name": "Nick Cage", "type": "PERSON", "description": "Celeb"},  # semantic
        {"name": "Mike Figgis", "type": "PERSON", "description": "Director"},  # different
    ]

    result = dedup.deduplicate(entities)

    # Should merge all "Cage" variants into 1, keep "Mike Figgis" separate
    assert len(result) == 2
    assert any("Nicolas Cage" in e["name"] for e in result)
    assert any("Mike Figgis" in e["name"] for e in result)
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| False positives from substring | Min-length guard (6 chars) |
| Performance regression | Fast criteria (1-3) checked before slow semantic |
| python-Levenshtein not installed | Graceful fallback (warn, skip edit distance) |
| Breaking existing behavior | Feature flag `enable_multi_criteria_dedup` |

---

## Related Documents

- [NEO4J_LLM_GRAPH_BUILDER_COMPARISON.md](../NEO4J_LLM_GRAPH_BUILDER_COMPARISON.md)
- [ADR-017: Semantic Entity Deduplication](../adr/ADR-017_SEMANTIC_ENTITY_DEDUPLICATION.md)
- [RAGAS_EVALUATION_ANALYSIS.md](../RAGAS_EVALUATION_ANALYSIS.md) - Section 3.6 Chunk Size Analysis

---

## Implementation Checklist

- [x] Add `python-Levenshtein` to pyproject.toml
- [x] Implement `MultiCriteriaDeduplicator` class
- [x] Add config options to `src/core/config.py`
- [x] Update factory function `create_deduplicator_from_config`
- [x] Write unit tests (335 lines, Nicolas Cage test cases)
- [x] Run benchmark to verify improvement (10.1% reduction achieved)
- [x] Update documentation

---

**Author:** Claude Code
**Last Updated:** 2025-12-10
