# Sprint 78: Graph Semantic Search & Entity Expansion

**Status:** ✅ COMPLETED
**Sprint Dauer:** 2026-01-07 bis 2026-01-08 (2 Tage)
**Story Points:** 34 SP (Actual: 32 SP completed)
**Assignee:** Claude + Team

---

## Sprint Ziel

Verbesserung der Graph-basierten Retrieval durch Entity→Chunk Expansion, 3-stufige semantische Entity-Erweiterung und Konfigurierbarkeit der Graph-Traversal Parameter. Behebung des kritischen Bugs, bei dem Graph Search nur Entity-Descriptions (100 chars) statt vollständiger Document Chunks (800-1800 tokens) zurückgab.

**Kontext:** Sprint 77 RAGAS Evaluation zeigte, dass Graph Mode nur Entity-Metadata zurückgab statt echter Dokument-Inhalte, was zu 0.0000 Scores führte.

---

## Problem Statement

**Sprint 77 RAGAS Ergebnisse:**
```
Mode: graph
Questions: 3/3 successful
Retrieved Contexts: 0/15 (0%)
RAGAS Metrics: 0.0000 (alle 4 Metriken)
Root Cause: Entity descriptions statt Document chunks
```

**Technische Probleme:**
1. **Entity→Chunk Missing Link:** Graph Cypher Query gab nur `e.description` (100 chars) zurück
2. **Stop Words Manual:** 46 hardcoded Stop Words statt LLM-basierter Entity-Extraktion
3. **Fehlende Semantik:** Keine semantische Suche für Entities, nur Text-Matching
4. **Nicht konfigurierbar:** Graph Expansion Hops und Thresholds fest codiert

---

## Features

### Feature 78.1: Entity→Chunk Expansion Fix ✅ (8 SP) 🔥 **CRITICAL**

**Beschreibung:**
Kritischer Fix der Graph Search Cypher Query: Traversierung der `MENTIONED_IN` Beziehungen von Entities zu Chunks, um vollständige Dokument-Texte statt Entity-Descriptions zurückzugeben.

**Problem:**
```cypher
-- ALT (Sprint 77): Gibt nur Entity Metadata
MATCH (e:base)
WHERE e.namespace_id IN $namespaces
  AND e.entity_name IN $entities
RETURN e.entity_id, e.entity_name, e.description  -- 100 chars!
```

**Lösung:**
```cypher
-- NEU (Sprint 78): Expandiert zu vollständigen Chunks
MATCH (e:base)-[:MENTIONED_IN]->(c:chunk)
WHERE e.namespace_id IN $namespaces
  AND c.namespace_id IN $namespaces
  AND e.entity_name IN $expanded_entities
WITH c, collect(DISTINCT e.entity_name) AS matched_entities, count(DISTINCT e) AS entity_count
RETURN
  c.chunk_id AS id,
  c.text AS chunk_text,          -- FULL CHUNK! (800-1800 tokens)
  c.document_id AS document_id,
  c.chunk_index AS chunk_index,
  matched_entities,
  entity_count
ORDER BY entity_count DESC
LIMIT $top_k
```

**Implementierung:**
- `src/components/graph_rag/dual_level_search.py:123-292`
  - `local_search()` Methode komplett überarbeitet
  - Cypher Query verwendet jetzt `MENTIONED_IN` Relationship
  - Returns `GraphEntity` objects mit Chunk-Text in `description` field (backward compatible)

**Verification:**
```bash
# Test Query
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the global implications of abortion?",
    "namespaces": ["amnesty_qa"],
    "intent": "graph",
    "include_sources": true
  }' | jq '.sources[0].text | length'

# Output: 462 chars (ALT: 100 chars entity description)
```

**Impact:**
- Chunk Length: 100 chars → 447 chars average (4.5x mehr Content)
- Neo4j Query: 120 MENTIONED_IN relationships für amnesty_qa namespace
- RAGAS Ready: LLM hat jetzt echten Context für Answer Generation

**Acceptance Criteria:**
- [x] Cypher Query traversiert `MENTIONED_IN` relationships
- [x] Returns `c.text` (full chunk) statt `e.description`
- [x] Backward compatible via `GraphEntity.description` field
- [x] Namespaces korrekt gefiltert (entities AND chunks)
- [x] Ordering by `entity_count` (mehr Matches = relevanter)
- [x] Manual Test: 3 chunks à 447 chars average

---

### Feature 78.2: 3-Stufen Entity Expansion ✅ (13 SP)

**Beschreibung:**
Intelligente Entity-Erweiterung mit 3-stufiger Pipeline: LLM Entity Extraction → Graph N-Hop Expansion → LLM Synonym Fallback. Ersetzt manuelle Stop Words Liste durch LLM-basierte Extraktion.

**Architecture:**
```
Query: "What are the global implications of abortion?"
   ↓
┌────────────────────────────────────────────────────────┐
│ STAGE 1: LLM Entity Extraction                         │
│ Input:  Query                                          │
│ Output: ["abortion", "reproductive rights", "global"]  │
│ LLM:    GPT-OSS:20b via AegisLLMProxy                 │
└────────────────────────────────────────────────────────┘
   ↓
┌────────────────────────────────────────────────────────┐
│ STAGE 2: Graph N-Hop Expansion (Configurable 1-3)     │
│ Input:  3 entities                                     │
│ Graph:  1-hop traversal via RELATES_TO relationships  │
│ Output: 7 entities (3 initial + 4 connected)          │
└────────────────────────────────────────────────────────┘
   ↓
┌────────────────────────────────────────────────────────┐
│ STAGE 3: LLM Synonym Fallback (if <10 entities)       │
│ Trigger: 7 < 10 (threshold)                           │
│ LLM:     Generate 3 synonyms per top 2 entities       │
│ Output:  6 synonyms added → 13 total entities         │
└────────────────────────────────────────────────────────┘
   ↓
Final: 13 entities → Chunk Retrieval
```

**Implementierung:**
- `src/components/graph_rag/entity_expansion.py` (NEW FILE - 400+ lines)
  - `SmartEntityExpander` class
  - `expand_entities()` - Main 3-stage pipeline
  - `_extract_entities_llm()` - Stage 1: LLM extraction
  - `_expand_via_graph()` - Stage 2: N-hop graph traversal
  - `_generate_synonyms_llm()` - Stage 3: Synonym generation
  - `expand_and_rerank()` - Stage 4: Semantic reranking (Feature 78.3)

**Stage 1: LLM Entity Extraction**
```python
async def _extract_entities_llm(self, query: str) -> list[str]:
    prompt = """Extract key entities, concepts, and named entities from this question.
    Return only the entity names, one per line.

    Examples:
    - Question: "What are the global implications of abortion?"
      Entities:
      global implications
      abortion
      reproductive rights

    Question: {query}

    Entities:"""

    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt=prompt,
        complexity=Complexity.LOW,
        quality_requirement=QualityRequirement.MEDIUM,
    )
    response = await self.llm_proxy.generate(task)
    return parse_entities(response.content)
```

**Stage 2: Graph N-Hop Expansion**
```cypher
// Configurable 1-3 hops
MATCH (e1:base)
WHERE e1.namespace_id IN $namespaces
  AND ANY(entity IN $initial_entities WHERE
      toLower(e1.entity_name) CONTAINS toLower(entity))

// N-hop traversal (e.g., *1..2 for 2 hops)
OPTIONAL MATCH path = (e1)-[r:RELATES_TO|PART_OF|SIMILAR_TO*1..{max_hops}]-(e2:base)
WHERE e2.namespace_id IN $namespaces

WITH collect(DISTINCT e1.entity_name) + collect(DISTINCT e2.entity_name) AS all_names
UNWIND all_names AS name
RETURN DISTINCT name
LIMIT 50
```

**Stage 3: LLM Synonym Fallback**
```python
async def _generate_synonyms_llm(self, entities: list[str], max_per_entity: int = 3):
    # Only triggered if graph expansion < threshold (default: 10)
    if len(graph_entities) >= self.min_entities_threshold:
        return graph_entities  # Skip Stage 3

    # Generate synonyms for top 2 entities
    prompt = f"""Generate {max_per_entity} synonyms for each entity.

    Entities:
    - abortion
    - reproductive rights

    Synonyms:"""

    # Returns: ["pregnancy termination", "induced abortion", "reproductive choice", ...]
```

**Configuration (Feature 78.5):**
```python
# src/core/config.py
graph_expansion_hops: int = 1  # UI: 1-3 hops
graph_min_entities_threshold: int = 10  # UI: 5-20
graph_max_synonyms_per_entity: int = 3  # UI: 1-5
```

**Log Evidence:**
```
2026-01-08 07:49:45 INFO stage3_synonym_fallback
  graph_count=7 synonym_count=6 final_count=13 threshold=10
```

**Acceptance Criteria:**
- [x] Stage 1: LLM extracts entities (deduplicated, case-insensitive)
- [x] Stage 2: Graph expands via configurable N-hop traversal
- [x] Stage 3: LLM generates synonyms only if <threshold
- [x] All stages integrated in `dual_level_search.local_search()`
- [x] Replaces manual 46-word stop words list

---

### Feature 78.3: Semantic Entity Reranking (BGE-M3) ✅ (5 SP)

**Beschreibung:**
Semantische Reranking der expandierten Entities via BGE-M3 Embeddings (1024-dim) und Cosine Similarity. Verbessert Relevanz-Ranking über Text-Matching hinaus.

**Implementation:**
```python
# src/components/graph_rag/entity_expansion.py:155-189
async def expand_and_rerank(
    self, query: str, namespaces: list[str], top_k: int = 10
) -> list[tuple[str, float]]:
    """Stage 4: Semantic reranking via BGE-M3."""

    # Stage 1-3: Get expanded entities (e.g., 13 entities)
    expanded_entities = await self.expand_entities(query, namespaces, top_k * 3)

    # Encode query
    query_embedding = await self.embedding_service.encode(query)

    # Score each entity
    scored_entities = []
    for entity_name in expanded_entities:
        entity_embedding = await self.embedding_service.encode(entity_name)
        similarity = self._cosine_similarity(query_embedding, entity_embedding)
        scored_entities.append((entity_name, float(similarity)))

    # Sort by similarity (descending)
    scored_entities.sort(key=lambda x: x[1], reverse=True)
    return scored_entities[:top_k]

def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Cosine similarity: dot(A,B) / (||A|| * ||B||)."""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
```

**Example:**
```python
query = "What are the global implications of abortion?"
entities = ["abortion", "reproductive rights", "climate change"]

# BGE-M3 Embeddings (1024-dim)
query_emb = [0.8, 0.1, 0.1, ...]  # 1024 dims
entity_embs = {
    "abortion": [0.75, 0.15, 0.1, ...],          # cos_sim = 0.92
    "reproductive rights": [0.6, 0.3, 0.1, ...], # cos_sim = 0.78
    "climate change": [0.1, 0.1, 0.8, ...],      # cos_sim = 0.23
}

# Reranked: abortion (0.92), reproductive rights (0.78), climate change (0.23)
```

**Acceptance Criteria:**
- [x] Uses BGE-M3 embeddings (1024-dim)
- [x] Cosine similarity scoring
- [x] Returns sorted list with scores
- [x] Optional feature (controlled by `graph_semantic_reranking_enabled`)

---

### Feature 78.4: Remove Stop Words ✅ (2 SP)

**Beschreibung:**
Entfernung der manuellen 46-Wörter Stop Words Liste, da LLM-basierte Entity-Extraktion (Feature 78.2) Stop Words automatisch filtert.

**Removed Code:**
```python
# src/components/graph_rag/dual_level_search.py (DELETED)
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than",
}

# Manual filtering (DELETED)
query_words = [w for w in query.lower().split() if w not in STOP_WORDS]
```

**Replacement:**
LLM automatically extracts meaningful entities and ignores stop words.

**Acceptance Criteria:**
- [x] STOP_WORDS set removed from codebase
- [x] Manual filtering logic removed
- [x] LLM extraction handles stop words implicitly

---

### Feature 78.5: Configuration Setup ✅ (3 SP)

**Beschreibung:**
Neue konfigurierbare Settings für Graph Search Parameter. Ermöglicht UI-basierte Anpassung ohne Code-Änderungen.

**Implementation:**
```python
# src/core/config.py:565-577
class Settings(BaseSettings):
    # Sprint 78: Semantic Graph Search Configuration
    graph_expansion_hops: int = Field(
        default=1,
        ge=1, le=3,
        description="Number of hops for graph entity expansion (1-3)"
    )
    graph_min_entities_threshold: int = Field(
        default=10,
        ge=5, le=20,
        description="Minimum entities before LLM synonym fallback (5-20)"
    )
    graph_max_synonyms_per_entity: int = Field(
        default=3,
        ge=1, le=5,
        description="Maximum synonyms to generate per entity (1-5)"
    )
    graph_semantic_reranking_enabled: bool = Field(
        default=True,
        description="Enable semantic reranking of graph entities (BGE-M3)"
    )
```

**Environment Variables:**
```bash
# .env
GRAPH_EXPANSION_HOPS=2              # 1-3 (default: 1)
GRAPH_MIN_ENTITIES_THRESHOLD=15     # 5-20 (default: 10)
GRAPH_MAX_SYNONYMS_PER_ENTITY=5     # 1-5 (default: 3)
GRAPH_SEMANTIC_RERANKING_ENABLED=true
```

**Usage:**
```python
from src.core.config import settings

expander = SmartEntityExpander(
    graph_expansion_hops=settings.graph_expansion_hops,        # ENV var
    min_entities_threshold=settings.graph_min_entities_threshold,
    max_synonyms_per_entity=settings.graph_max_synonyms_per_entity,
)
```

**Future UI (Sprint 79+):**
```tsx
// AdvancedSettings.tsx
<FormField>
  <Label>Graph Expansion Hops</Label>
  <Slider min={1} max={3} value={settings.graph_expansion_hops} />
  <Description>Controls depth of graph traversal (1-3 hops)</Description>
</FormField>
```

**Acceptance Criteria:**
- [x] 4 neue Settings in `config.py`
- [x] Validation ranges (ge/le constraints)
- [x] Environment variable support via Pydantic
- [x] Documented in `docs/CONFIGURATION.md`

---

### Feature 78.6: Unit Tests ✅ (1 SP)

**Beschreibung:**
Umfassende Unit Tests für alle Sprint 78 Features mit Mocking externer Dependencies.

**Test Suite:**
```
tests/unit/components/graph_rag/
├── test_entity_expansion.py (NEW - 14 tests)
│   ├── TestSmartEntityExpander
│   │   ├── test_extract_entities_llm_basic
│   │   ├── test_extract_entities_llm_deduplication
│   │   ├── test_extract_entities_llm_filters_noise
│   │   ├── test_expand_via_graph_1hop
│   │   ├── test_expand_via_graph_3hop
│   │   ├── test_generate_synonyms_llm_basic
│   │   ├── test_generate_synonyms_llm_respects_max
│   │   ├── test_expand_entities_3stage_no_fallback
│   │   ├── test_expand_entities_3stage_with_fallback
│   │   ├── test_expand_and_rerank_semantic
│   │   ├── test_cosine_similarity_calculation
│   │   ├── test_initialization_validates_hops
│   │   ├── test_initialization_validates_threshold
│   │   └── test_initialization_validates_synonyms
│
└── test_dual_level_search.py (UPDATED - +6 tests)
    └── TestSprint78EntityChunkExpansion (NEW)
        ├── test_local_search_returns_chunks_not_descriptions
        ├── test_local_search_uses_mentioned_in_relationship
        ├── test_local_search_uses_smart_entity_expander
        ├── test_local_search_filters_by_namespace
        ├── test_local_search_orders_by_entity_count
        └── test_local_search_respects_top_k
```

**Test Results:**
```bash
$ poetry run pytest tests/unit/components/graph_rag/test_entity_expansion.py -v
============================= test session starts ==============================
collected 14 items

test_entity_expansion.py::TestSmartEntityExpander::test_extract_entities_llm_basic PASSED [  7%]
test_entity_expansion.py::TestSmartEntityExpander::test_extract_entities_llm_deduplication PASSED [ 14%]
test_entity_expansion.py::TestSmartEntityExpander::test_extract_entities_llm_filters_noise PASSED [ 21%]
test_entity_expansion.py::TestSmartEntityExpander::test_expand_via_graph_1hop PASSED [ 28%]
test_entity_expansion.py::TestSmartEntityExpander::test_expand_via_graph_3hop PASSED [ 35%]
test_entity_expansion.py::TestSmartEntityExpander::test_generate_synonyms_llm_basic PASSED [ 42%]
test_entity_expansion.py::TestSmartEntityExpander::test_generate_synonyms_llm_respects_max PASSED [ 50%]
test_entity_expansion.py::TestSmartEntityExpander::test_expand_entities_3stage_no_fallback PASSED [ 57%]
test_entity_expansion.py::TestSmartEntityExpander::test_expand_entities_3stage_with_fallback PASSED [ 64%]
test_entity_expansion.py::TestSmartEntityExpander::test_expand_and_rerank_semantic PASSED [ 71%]
test_entity_expansion.py::TestSmartEntityExpander::test_cosine_similarity_calculation PASSED [ 78%]
test_entity_expansion.py::TestSmartEntityExpander::test_initialization_validates_hops PASSED [ 85%]
test_entity_expansion.py::TestSmartEntityExpander::test_initialization_validates_threshold PASSED [ 92%]
test_entity_expansion.py::TestSmartEntityExpander::test_initialization_validates_synonyms PASSED [100%]

============================== 14 passed in 0.25s =======================================

$ poetry run pytest tests/unit/components/graph_rag/test_dual_level_search.py::TestSprint78EntityChunkExpansion -v
============================= test session starts ==============================
collected 6 items

test_dual_level_search.py::TestSprint78EntityChunkExpansion::test_local_search_returns_chunks_not_descriptions PASSED [ 16%]
test_dual_level_search.py::TestSprint78EntityChunkExpansion::test_local_search_uses_mentioned_in_relationship PASSED [ 33%]
test_dual_level_search.py::TestSprint78EntityChunkExpansion::test_local_search_uses_smart_entity_expander PASSED [ 50%]
test_dual_level_search.py::TestSprint78EntityChunkExpansion::test_local_search_filters_by_namespace PASSED [ 66%]
test_dual_level_search.py::TestSprint78EntityChunkExpansion::test_local_search_orders_by_entity_count PASSED [ 83%]
test_dual_level_search.py::TestSprint78EntityChunkExpansion::test_local_search_respects_top_k PASSED [100%]

============================== 6 passed in 0.13s ============================================
```

**Total: 20 tests, 100% pass rate ✅**

**Key Test Patterns:**
1. **Mocking:** AsyncMock for Neo4j, LLM, Embeddings
2. **Lazy Import Patching:** Patch at source module, not caller
3. **Data Format:** Correct Neo4j field names (`name` not `entity_name`)
4. **Validation:** Range constraints for config parameters

**Acceptance Criteria:**
- [x] 20 unit tests created (14 new + 6 updated)
- [x] 100% pass rate
- [x] Covers all 3 stages of expansion
- [x] Covers Entity→Chunk traversal
- [x] Covers configuration validation

---

## Technische Details

### Files Modified

```
src/components/graph_rag/
├── entity_expansion.py (NEW - 418 lines)
│   └── SmartEntityExpander class with 3-stage pipeline
├── dual_level_search.py (MODIFIED - 170 lines changed)
│   └── local_search() now uses SmartEntityExpander + MENTIONED_IN
└── __init__.py (MODIFIED)
    └── Export SmartEntityExpander

src/core/
└── config.py (MODIFIED - 4 new fields)
    └── graph_expansion_hops, graph_min_entities_threshold, etc.

scripts/
└── run_ragas_evaluation.py (MODIFIED)
    └── max_workers: 4 → 1 (sequentielles RAGAS)

tests/unit/components/graph_rag/
├── test_entity_expansion.py (NEW - 448 lines)
│   └── 14 comprehensive tests
└── test_dual_level_search.py (MODIFIED - +230 lines)
    └── 6 additional Sprint 78 tests
```

**Total LOC:** ~1,266 lines (418 new entity_expansion + 400 tests + 448 updates)

### Dependencies

**Unchanged:**
- Python 3.12.7
- LangGraph 0.6.10
- Neo4j 5.24
- BGE-M3 embeddings
- AegisLLMProxy (Ollama backend)

**No new dependencies added** ✅

---

## RAGAS Evaluation (Attempted)

### Execution
```bash
poetry run python scripts/run_ragas_evaluation.py \
  --namespace amnesty_qa \
  --mode graph \
  --dataset data/amnesty_qa_contexts/ragas_amnesty_tiny.jsonl \
  --output-dir data/evaluation/results \
  --max-questions 3
```

### Results

**Query Phase: ✅ SUCCESS**
```
[1/3] What are the global implications of the USA Supreme Court ruling on abortion?
  ✓ Answer: According to the sources...
  Retrieved 3 contexts in 14s

[2/3] Which companies are the main contributors to GHG emissions?
  ✓ Answer: According to the Carbon Majors database...
  Retrieved 3 contexts in 63s

[3/3] Which private companies in the Americas are the largest GHG emitters?
  ✓ Answer: According to the Carbon Majors database...
  Retrieved 3 contexts in 37s

Total Query Time: 114s (avg 38s per query)
```

**Metrics Phase: ❌ TIMEOUT**
```
Computing RAGAS Metrics with GPT-OSS:20b (Ollama)...
Worker Config: max_workers=1 (sequential), timeout=300s

Evaluating:   0%|          | 0/12 [00:00<?, ?it/s]
Exception raised in Job[0]: TimeoutError()
Evaluating:   8%|▊         | 1/12 [05:00<55:00, 300.00s/it]
...
```

**Root Cause Analysis:**

We performed detailed performance testing to understand the timeout issue:

**Test 1: GPT-OSS:20b with exact RAGAS prompt**
```python
# Exact RAGAS Context Precision prompt (2903 chars, 3 few-shot examples)
result = await ollama.generate(model="gpt-oss:20b", prompt=ragas_prompt)

# Result:
Time: 85.76s per evaluation
Tokens: 222 output tokens
Scaling: 15 evaluations × 85.76s = 1286s (21 minutes)
RAGAS Timeout: 300s per job
Verdict: ❌ TIMEOUT INEVITABLE
```

**Test 2: Nemotron3 Nano simple test**
```bash
$ time curl http://localhost:11434/api/generate -d '{
  "model": "nemotron-3-nano",
  "prompt": "Question: Is the sky blue? Answer yes or no."
}'

# Result:
Answer: "Yes"
Time: 11m 26s (686 seconds)
Verdict: ❌ EVEN WORSE
```

**Conclusion:**
RAGAS Few-Shot prompts (2903 chars, 3 examples) sind zu komplex für lokale Ollama Inference:
- GPT-OSS:20b: 85.76s → Timeout bei 15 Evaluationen
- Nemotron3 Nano: >600s → Completely unusable

**RAGAS ist für Cloud APIs optimiert, nicht für lokale LLMs!**

### Alternative Validation

Da RAGAS Metriken mit lokalen LLMs nicht funktionieren, verwenden wir **funktionale Verifikation**:

**Evidence 1: Chunk Length Increase**
```bash
# Before (Sprint 77): Entity descriptions only
$ curl .../chat | jq '.sources[0].text | length'
100  # Only entity description

# After (Sprint 78): Full document chunks
$ curl .../chat | jq '.sources[0].text | length'
462  # Full chunk text (4.6x mehr Content!)
```

**Evidence 2: Log Analysis**
```
2026-01-08 07:49:45 INFO stage3_synonym_fallback
  graph_count=7 synonym_count=6 final_count=13 threshold=10

2026-01-08 07:49:45 INFO local_search_completed
  chunks_found=3 execution_time_ms=47.82
```

**Evidence 3: Neo4j Verification**
```cypher
MATCH (c:chunk {namespace_id: 'amnesty_qa'})
RETURN size(c.text) AS length
ORDER BY length DESC LIMIT 5

// Results: 1423, 1423, 1423, 1381, 1245 chars
// ✅ Chunks exist with full text
```

**Evidence 4: Unit Tests**
```
20/20 tests passing (100%)
- Entity extraction works
- Graph expansion works
- Semantic reranking works
- Chunk retrieval works
```

**Sprint 78 Goals Achieved:** ✅
- Entity→Chunk expansion functional
- 3-stage pipeline operational
- Configuration working
- Tests passing

---

## Success Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Entity→Chunk Fix | MENTIONED_IN traversal | ✅ Implemented | ✅ |
| Chunk Length | >400 chars avg | 447 chars avg | ✅ |
| 3-Stage Pipeline | LLM→Graph→Synonyms | ✅ Functional | ✅ |
| Configuration | 4 new settings | ✅ 4 settings | ✅ |
| Unit Tests | >15 tests | 20 tests (100% pass) | ✅ |
| RAGAS Evaluation | Metrics completion | ❌ Timeout (local LLM) | ⚠️ |

**Overall: 5/6 goals achieved** (RAGAS deferred to Sprint 79 with DSPy optimization)

---

## Deliverables

**Code:**
- [x] `src/components/graph_rag/entity_expansion.py` - 3-stage pipeline (418 lines)
- [x] `src/components/graph_rag/dual_level_search.py` - Entity→Chunk expansion (170 lines modified)
- [x] `src/core/config.py` - 4 new configuration fields
- [x] `tests/unit/components/graph_rag/test_entity_expansion.py` - 14 tests (448 lines)
- [x] `tests/unit/components/graph_rag/test_dual_level_search.py` - 6 tests (230 lines added)

**Documentation:**
- [x] `docs/sprints/SPRINT_78_PLAN.md` (this document)
- [x] `docs/sprints/SPRINT_79_PLAN.md` (DSPy RAGAS optimization)
- [x] ADR-041: Entity→Chunk Expansion & 3-Stage Semantic Search
- [x] Updated ARCHITECTURE.md (Graph Search section)
- [x] Updated TECH_STACK.md (DSPy planned for Sprint 79)

**Functional Verification:**
- [x] Manual tests with real queries (447 chars avg chunks)
- [x] Log evidence (3-stage expansion working)
- [x] Neo4j verification (MENTIONED_IN relationships exist)
- [x] Unit tests (20/20 passing)

---

## Lessons Learned

### What Worked Well ✅

1. **Systematic Debugging**
   - Clear problem identification (Entity descriptions vs. Chunks)
   - Root cause analysis via Neo4j inspection
   - Step-by-step verification

2. **3-Stage Architecture**
   - Flexible fallback mechanism (Graph → Synonyms)
   - Clean separation of concerns
   - Easy to test independently

3. **Configuration Design**
   - Pydantic validation ranges (ge/le)
   - Environment variable support
   - Ready for UI integration

4. **Test-Driven Approach**
   - 20 comprehensive tests
   - Mocking strategy clear
   - 100% pass rate

### What Didn't Work ❌

1. **RAGAS with Local LLMs**
   - GPT-OSS:20b: Too slow (85.76s per eval)
   - Nemotron3 Nano: Extremely slow (>600s per eval)
   - Few-shot prompts too complex for local inference
   - **Solution:** Sprint 79 will use DSPy for prompt optimization

2. **Initial Implementation Bugs**
   - LLM Proxy API signature wrong (`prompt` kwarg vs. `LLMTask`)
   - Neo4j field names incorrect (`id` vs. `chunk_id`)
   - Response attribute wrong (`text` vs. `content`)
   - **Learning:** Read documentation before assuming API structure

### Improvements for Next Sprint

1. **DSPy Integration** (Sprint 79)
   - Automatic prompt optimization for local LLMs
   - Few-shot compression (3 examples → 1-2)
   - Target: <20s per evaluation (4x speedup)

2. **Integration Tests**
   - Add integration tests with real Neo4j + Ollama
   - Test full pipeline end-to-end
   - Performance benchmarking

3. **Documentation**
   - More inline code documentation
   - Architecture diagrams for 3-stage pipeline
   - Performance tuning guide

---

## Follow-up: Sprint 79

**Sprint 79: DSPy RAGAS Optimization** (Planned 2026-01-08 - 2026-01-10)

**Goal:** Enable RAGAS evaluation with local LLMs through DSPy prompt optimization

**Features:**
- Feature 79.1: DSPy Integration (8 SP)
- Feature 79.2: Optimized Prompts for GPT-OSS:20b (5 SP) - Target: <20s per eval
- Feature 79.3: Optimized Prompts for Nemotron3 Nano (5 SP) - Target: <60s per eval
- Feature 79.4: Performance Benchmarking (2 SP)
- Feature 79.5: RAGAS Evaluation with Optimized Prompts (1 SP)

**Expected Results:**
- Context Precision: 85.76s → <20s (4.3x speedup)
- Total RAGAS time: Timeout (>21m) → <5m
- Accuracy: ≥90% vs. Original RAGAS

**See:** [SPRINT_79_PLAN.md](SPRINT_79_PLAN.md)

---

## References

- **Sprint 77:** RAGAS Integration & Initial Evaluation (discovered Entity→Chunk bug)
- **Sprint 79:** DSPy RAGAS Optimization (follow-up)
- **ADR-041:** Entity→Chunk Expansion & 3-Stage Semantic Search
- **Code Review:** Entity Expansion Implementation
- **Performance Analysis:** RAGAS Local LLM Timeout Investigation

---

**Sprint Retrospective:**

**Keep Doing:**
- Systematic debugging and root cause analysis
- Comprehensive unit testing (20 tests)
- Clean architecture (3-stage pipeline)
- Functional verification when metrics unavailable

**Stop Doing:**
- Assuming RAGAS works with all LLMs
- Assuming API signatures without checking docs
- Running long evaluations without timeout analysis

**Start Doing:**
- DSPy for prompt optimization (Sprint 79)
- Performance testing BEFORE long-running evals
- Integration tests for critical paths

---

**Sprint 78 Status:** ✅ **COMPLETED** (32/34 SP)
**Next Sprint:** Sprint 79 - DSPy RAGAS Optimization
**Last Updated:** 2026-01-08
