# TD-063: Relation Deduplication

**Created:** 2025-12-11
**Status:** Planned
**Priority:** Medium
**Effort:** 4-6 hours
**Sprint:** 44 (planned)

---

## Problem Statement

After implementing **Multi-Criteria Entity Deduplication** (TD-062, Sprint 43), a significant gap remains: **Relations are NOT deduplicated** in any pipeline path. This leads to duplicate relationships in the knowledge graph, especially when using parallel extraction with multiple models.

### Current State

| Pipeline | Entity Dedup | Relation Dedup |
|----------|--------------|----------------|
| Normal (qwen3-32b) | MultiCriteriaDeduplicator | None |
| Parallel (gemma3:4b + qwen2.5:7b) | MultiCriteriaDeduplicator | Simple lowercase merge only |

### Symptoms

1. **Same relation extracted with different type names:**
   - Model A: `("Nicolas Cage", "STARRED_IN", "Leaving Las Vegas")`
   - Model B: `("Nicolas Cage", "ACTED_IN", "Leaving Las Vegas")`
   - Result: **2 duplicate edges** in Neo4j

2. **Entity name variants not remapped after dedup:**
   - Before dedup: `("nicolas cage", "STARRED_IN", "Leaving Las Vegas")`
   - After entity dedup: "nicolas cage" merged into "Nicolas Cage"
   - But relation still references: `"nicolas cage"` (orphaned)

3. **Bidirectional relations duplicated:**
   - `("Alice", "KNOWS", "Bob")` and `("Bob", "KNOWS", "Alice")`
   - For symmetric relations, these are duplicates

---

## Root Cause Analysis

### Code Analysis

**`src/components/graph_rag/parallel_extractor.py`** - Simple lowercase merge only:
```python
def _merge_relationships(self, all_relationships: list[dict]) -> list[dict]:
    """Merge relationships from multiple extraction results."""
    seen = {}
    for rel in all_relationships:
        key = f"{rel['source'].lower()}|{rel['target'].lower()}|{rel['relationship_type'].lower()}"
        if key not in seen:
            seen[key] = rel
    return list(seen.values())
```

**Problem:** Only catches exact lowercase matches. Misses:
- Type synonyms: `STARRED_IN` vs `ACTED_IN` vs `PLAYED_IN`
- Entity remapping: After "nicolas cage" → "Nicolas Cage", relations still use old name

**`src/components/graph_rag/lightrag_wrapper.py`** - No relation dedup at all:
```python
# Line 1545-1584: Entity deduplication
if settings.enable_multi_criteria_dedup and all_entities:
    deduplicator = create_deduplicator_from_config()
    deduplicated_entities = deduplicator.deduplicate(all_entities)

# Line 1590+: Relations converted but NOT deduplicated
relations = self._convert_relations_to_lightrag_format(all_relations)
```

**`src/components/graph_rag/extraction_service.py`** - No dedup:
```python
def extract_relationships(self, text: str, entities: list[dict]) -> list[dict]:
    # Returns raw LLM output - no deduplication
    return relationships
```

---

## Proposed Solution: RelationDeduplicator

A new `RelationDeduplicator` class with three-stage deduplication:

### Stage 1: Entity Name Normalization

After entity deduplication, create a mapping and remap all relation endpoints:

```python
class RelationDeduplicator:
    def normalize_entity_references(
        self,
        relations: list[dict],
        entity_mapping: dict[str, str]  # old_name -> canonical_name
    ) -> list[dict]:
        """Remap relation endpoints to canonical entity names."""
        normalized = []
        for rel in relations:
            source = entity_mapping.get(rel["source"].lower(), rel["source"])
            target = entity_mapping.get(rel["target"].lower(), rel["target"])
            normalized.append({
                **rel,
                "source": source,
                "target": target
            })
        return normalized
```

### Stage 2: Type Synonym Resolution

Define relation type clusters and normalize to canonical types:

```python
RELATION_TYPE_SYNONYMS = {
    # Acting/Performing
    "ACTED_IN": ["STARRED_IN", "PLAYED_IN", "APPEARED_IN", "PERFORMED_IN"],
    "DIRECTED": ["DIRECTED_BY", "HELMED", "MADE"],
    "WRITTEN_BY": ["WROTE", "AUTHORED", "PENNED"],

    # Personal relationships
    "MARRIED_TO": ["SPOUSE_OF", "WED_TO", "HUSBAND_OF", "WIFE_OF"],
    "CHILD_OF": ["SON_OF", "DAUGHTER_OF", "OFFSPRING_OF"],
    "PARENT_OF": ["FATHER_OF", "MOTHER_OF"],

    # Professional
    "WORKS_FOR": ["EMPLOYED_BY", "WORKS_AT", "MEMBER_OF"],
    "FOUNDED": ["CREATED", "ESTABLISHED", "STARTED"],

    # Location
    "LOCATED_IN": ["BASED_IN", "SITUATED_IN", "FOUND_IN"],
    "BORN_IN": ["BIRTHPLACE", "NATIVE_OF"],
}

def _normalize_relation_type(self, rel_type: str) -> str:
    """Normalize relation type to canonical form."""
    rel_type_upper = rel_type.upper().replace(" ", "_")

    # Check if it's a canonical type
    if rel_type_upper in RELATION_TYPE_SYNONYMS:
        return rel_type_upper

    # Check if it's a synonym
    for canonical, synonyms in RELATION_TYPE_SYNONYMS.items():
        if rel_type_upper in synonyms:
            return canonical

    # Unknown type - return as-is
    return rel_type_upper
```

### Stage 3: Bidirectional/Symmetric Relation Handling

For symmetric relations, ensure only one direction is stored:

```python
SYMMETRIC_RELATIONS = {
    "KNOWS", "RELATED_TO", "MARRIED_TO", "COLLABORATED_WITH",
    "WORKS_WITH", "FRIENDS_WITH", "SIBLING_OF"
}

def _deduplicate_relations(self, relations: list[dict]) -> list[dict]:
    """Deduplicate relations including bidirectional handling."""
    seen = {}

    for rel in relations:
        source = rel["source"]
        target = rel["target"]
        rel_type = self._normalize_relation_type(rel["relationship_type"])

        # For symmetric relations, use sorted order to catch bidirectional dupes
        if rel_type in SYMMETRIC_RELATIONS:
            key_parts = sorted([source.lower(), target.lower()])
            key = f"{key_parts[0]}|{key_parts[1]}|{rel_type}"
        else:
            key = f"{source.lower()}|{target.lower()}|{rel_type}"

        if key not in seen:
            seen[key] = {
                **rel,
                "source": source,
                "target": target,
                "relationship_type": rel_type
            }

    return list(seen.values())
```

---

## Integration Points

### 1. Update `lightrag_wrapper.py`

```python
# After entity deduplication
if settings.enable_multi_criteria_dedup and all_entities:
    deduplicator = create_deduplicator_from_config()
    deduplicated_entities, entity_mapping = deduplicator.deduplicate_with_mapping(all_entities)

    # NEW: Deduplicate relations
    if settings.enable_relation_dedup and all_relations:
        relation_deduplicator = RelationDeduplicator()
        all_relations = relation_deduplicator.deduplicate(
            all_relations,
            entity_mapping=entity_mapping
        )
```

### 2. Update `parallel_extractor.py`

Replace simple `_merge_relationships()` with `RelationDeduplicator`:

```python
def _merge_relationships(self, all_relationships: list[dict]) -> list[dict]:
    """Merge relationships using RelationDeduplicator."""
    deduplicator = RelationDeduplicator()
    return deduplicator.deduplicate(all_relationships)
```

### 3. Modify Entity Deduplicator Interface

`MultiCriteriaDeduplicator.deduplicate()` should return mapping:

```python
def deduplicate_with_mapping(
    self, entities: list[dict]
) -> tuple[list[dict], dict[str, str]]:
    """Returns (deduplicated_entities, old_name -> canonical_name mapping)."""
```

---

## Configuration

```python
# src/core/config.py
enable_relation_dedup: bool = Field(
    default=True,
    description="Enable relation deduplication (type synonyms + bidirectional)"
)
relation_type_synonyms_file: str | None = Field(
    default=None,
    description="Optional JSON file with custom relation type synonyms"
)
```

---

## Expected Impact

### Before (Current State)

Parallel extraction with 2 models on same document:
- Model A extracts: 45 relations
- Model B extracts: 52 relations
- Simple merge: ~85 relations (some exact dupes removed)
- **Actually unique:** ~50-60 relations

### After (With RelationDeduplicator)

- After Stage 1 (entity normalization): ~75 relations
- After Stage 2 (type synonyms): ~60 relations
- After Stage 3 (bidirectional): ~50-55 relations
- **Reduction:** 35-40%

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `src/components/graph_rag/relation_deduplicator.py` | **NEW** - RelationDeduplicator class |
| `src/components/graph_rag/semantic_deduplicator.py` | Add `deduplicate_with_mapping()` method |
| `src/components/graph_rag/lightrag_wrapper.py` | Integrate relation deduplication |
| `src/components/graph_rag/parallel_extractor.py` | Use RelationDeduplicator |
| `src/core/config.py` | Add relation dedup settings |
| `tests/unit/components/graph_rag/test_relation_deduplicator.py` | **NEW** - Unit tests |

---

## Test Cases

```python
def test_relation_type_synonyms():
    dedup = RelationDeduplicator()
    relations = [
        {"source": "Nicolas Cage", "target": "Leaving Las Vegas", "relationship_type": "STARRED_IN"},
        {"source": "Nicolas Cage", "target": "Leaving Las Vegas", "relationship_type": "ACTED_IN"},
    ]
    result = dedup.deduplicate(relations)
    assert len(result) == 1
    assert result[0]["relationship_type"] == "ACTED_IN"  # canonical


def test_entity_name_normalization():
    dedup = RelationDeduplicator()
    relations = [
        {"source": "nicolas cage", "target": "Leaving Las Vegas", "relationship_type": "ACTED_IN"},
    ]
    entity_mapping = {"nicolas cage": "Nicolas Cage"}
    result = dedup.deduplicate(relations, entity_mapping=entity_mapping)
    assert result[0]["source"] == "Nicolas Cage"


def test_bidirectional_symmetric():
    dedup = RelationDeduplicator()
    relations = [
        {"source": "Alice", "target": "Bob", "relationship_type": "KNOWS"},
        {"source": "Bob", "target": "Alice", "relationship_type": "KNOWS"},
    ]
    result = dedup.deduplicate(relations)
    assert len(result) == 1
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Over-aggressive type merging | Configurable synonym mappings, start conservative |
| Performance with large relation sets | O(n) after normalization, very fast |
| Breaking existing graph structure | Feature flag `enable_relation_dedup` |
| Loss of information | Keep original type in metadata if needed |

---

## Related Documents

- [TD-062: Multi-Criteria Entity Deduplication](TD-062_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md) - Prerequisite
- [ADR-044: Multi-Criteria Entity Deduplication](../adr/ADR-044_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md)
- [ADR-040: RELATES_TO Semantic Relationships](../adr/ADR-040_RELATES_TO_SEMANTIC_RELATIONSHIP.md)

---

## Implementation Checklist

- [ ] Create `src/components/graph_rag/relation_deduplicator.py`
- [ ] Define initial `RELATION_TYPE_SYNONYMS` mapping
- [ ] Define `SYMMETRIC_RELATIONS` set
- [ ] Add `deduplicate_with_mapping()` to entity deduplicator
- [ ] Integrate into `lightrag_wrapper.py`
- [ ] Update `parallel_extractor.py` to use new deduplicator
- [ ] Add config options to `src/core/config.py`
- [ ] Write unit tests
- [ ] Run benchmark to measure reduction rate
- [ ] Update documentation

---

**Author:** Claude Code
**Last Updated:** 2025-12-11
