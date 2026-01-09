# Sprint 81: Query-Adaptive Routing & Entity Extraction Improvements

**Status:** 🚧 In Progress (Feature 81.7 C-LARA Complete ✅)
**Sprint Dauer:** 2026-01-09 bis 2026-01-20 (2 weeks)
**Story Points:** 24 SP (13 SP Features + 11 TD) - 3 SP Done
**Assignee:** Claude + Team
**Dependencies:** Sprint 80 Complete (Faithfulness fixes, cross-encoder reranking)

> **Note:** Features 81.1 (5 SP) and 81.2 (6 SP) deprecated - C-LARA SetFit (81.7) now handles intent classification.

---

## Technical Debt (8 SP remaining, 3 SP done)

| TD# | Title | SP | Priority | Status |
|-----|-------|-----|----------|--------|
| [TD-099](../technical-debt/TD-099_NAMESPACE_INGESTION_BUG.md) | Namespace Not Set During RAGAS Ingestion | 3 | **HIGH** | ✅ DONE |
| [TD-096](../technical-debt/TD-096_CHUNKING_PARAMS_UI_INTEGRATION.md) | Chunking Parameters UI Integration | 5 | MEDIUM | 🎯 |
| [TD-097](../technical-debt/TD-097_SPRINT80_SETTINGS_UI_INTEGRATION.md) | Sprint 80 Settings UI/DB Integration | 3 | MEDIUM | 🎯 |

### TD-099: Namespace Ingestion Bug (3 SP) ✅ **RESOLVED (2026-01-09)**

**Problem:** Field name mismatch - ingestion wrote `namespace_id` but retrieval filtered by `namespace`.

**Fix Applied:**
- `filters.py:222` - Changed `key="namespace"` → `key="namespace_id"`
- `four_way_hybrid_search.py:448` - Same fix
- `src/api/v1/retrieval.py` - Added `namespace_id` to SearchResult model
- `hybrid_search.py` - Added `namespace_id` to result mapping

**Verified:** RAGAS A/B test successfully used `--namespace ragas_eval` filtering

### TD-096: Chunking Parameters UI Integration (5 SP)

Settings from Sprint 80 Feature 80.2 need UI integration:
- `adaptive_context_size` toggle
- `context_window_size` slider (5-20)

### TD-097: Sprint 80 Settings UI/DB Integration (3 SP)

Settings from Sprint 80 Features need UI:
- `strict_faithfulness_enabled` (80.1)
- `reranker_enabled` (80.3)
- Use case guidance in UI labels

---

## Sprint Ziele

**Primär (UPDATED):** C-LARA Intent Classification ✅ DONE + Faithfulness Optimization (RAG Tuning Agent P0: No-Hedging Prompt).

**Sekundär:** Implement parent chunk retrieval to improve Context Recall by returning full sections instead of isolated sentence-level chunks.

**Tertiär:** Performance dashboards and automated RAGAS evaluation pipeline.

> **Scope Change:** Features 81.1 (Query Routing) and 81.2 (Entity Extraction) deprecated. C-LARA (81.7) achieved **95.22% intent accuracy**, replacing LLM-based query routing. Focus shifts to Faithfulness optimization per RAG Tuning Agent recommendations.

---

## Problem Statement

**Post-Sprint 80 Assessment (Expected):**
- Faithfulness improved via cite-sources prompt (F ≥ 0.750)
- Hybrid hallucination fixed via cross-encoder reranking (F ≥ 0.600)
- Graph fallback eliminates empty contexts (0% failures)

**Remaining Gaps:**

1. **Manual Mode Selection Required:**
   - User must know when to use Graph vs Vector vs Hybrid
   - Amnesty-like queries → Graph Mode best
   - HotpotQA-like queries → Hybrid Mode best
   - No automatic routing → suboptimal results

2. **Entity Extraction Coverage (HotpotQA):**
   - Estimated <40% entity coverage on .txt files
   - Missing entity types: Publication, Chemical, Scientific Term
   - Entities like "Arthur's Magazine", "Cadmium Chloride" not extracted

3. **Truncated Context Chunks:**
   - Graph chunks truncated at 500 characters
   - Missing critical information (e.g., "President Richard Nixon" cutoff)
   - Parent chunk retrieval would return full sections

**Target Metrics (Sprint 81):**
| Metric | Baseline | Target | Method |
|--------|----------|--------|--------|
| Query routing accuracy | N/A (manual) | **≥85%** | LLM classifier |
| Entity extraction coverage | ~40% | **≥70%** | Domain-agnostic types |
| Context Recall | 0.700 (S80) | **≥0.800** | Parent chunk retrieval |
| Overall RAGAS avg | ~0.65 | **≥0.75** | Combined improvements |

---

## Features

### Feature 81.1: Query-Adaptive Routing Classifier (5 SP) ❌ **DEPRECATED**

> **Deprecated:** Replaced by C-LARA SetFit Intent Classifier (Feature 81.7).
> C-LARA provides 5-class intent classification (factual, procedural, comparison, recommendation, navigation) with 95.22% accuracy and ~40ms latency.

**Beschreibung:**
Implement LLM-based query classification to automatically route queries to the optimal retrieval mode (Graph/Vector/Hybrid).

**Query Types & Routing:**

| Query Type | Example | Best Mode | Reasoning |
|------------|---------|-----------|-----------|
| **Entity-centric** | "What did Amnesty International say about abortion?" | Graph | Named entities, relationships |
| **Factoid** | "What city is the head office in?" | Hybrid | Simple fact, semantic similarity |
| **Multi-hop reasoning** | "Which magazine started first?" | Hybrid | Requires multiple sources |
| **Conceptual** | "Explain human rights violations" | Vector | Broad semantic match |

**Technical Solution:**

```python
# src/agents/coordinator/query_router.py

from enum import Enum
from pydantic import BaseModel
from typing import Literal

class QueryType(str, Enum):
    ENTITY_CENTRIC = "entity"      # → Graph Mode
    FACTOID = "factoid"            # → Hybrid Mode
    MULTI_HOP = "multi_hop"        # → Hybrid Mode (extended context)
    CONCEPTUAL = "conceptual"      # → Vector Mode

class QueryClassification(BaseModel):
    query_type: QueryType
    confidence: float
    reasoning: str
    recommended_mode: Literal["vector", "graph", "hybrid"]
    recommended_top_k: int

QUERY_CLASSIFIER_PROMPT = """
Classify the following query into one of these types:

1. ENTITY_CENTRIC: Query about specific named entities, organizations, people, or their relationships
   - Example: "What is Amnesty International's position on X?"
   - Example: "Who founded the Oberoi Group?"
   - Route to: GRAPH MODE

2. FACTOID: Simple factual question seeking a specific piece of information
   - Example: "What year was X founded?"
   - Example: "What city is the headquarters in?"
   - Route to: HYBRID MODE

3. MULTI_HOP: Complex question requiring information from multiple sources
   - Example: "Which magazine was started first, X or Y?"
   - Example: "What nationality was X's wife?"
   - Route to: HYBRID MODE with extended context

4. CONCEPTUAL: Broad question about concepts, explanations, or summaries
   - Example: "Explain human rights violations in X"
   - Example: "What are the implications of X?"
   - Route to: VECTOR MODE

Query: {query}

Respond in JSON format:
{{
    "query_type": "entity" | "factoid" | "multi_hop" | "conceptual",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation",
    "recommended_mode": "vector" | "graph" | "hybrid",
    "recommended_top_k": 5-15
}}
"""

class QueryRouter:
    """
    Intelligent query router using LLM classification.
    """

    def __init__(self, llm):
        self.llm = llm
        self.mode_mapping = {
            QueryType.ENTITY_CENTRIC: "graph",
            QueryType.FACTOID: "hybrid",
            QueryType.MULTI_HOP: "hybrid",
            QueryType.CONCEPTUAL: "vector",
        }
        self.top_k_mapping = {
            QueryType.ENTITY_CENTRIC: 7,
            QueryType.FACTOID: 10,
            QueryType.MULTI_HOP: 15,  # Extended context for multi-hop
            QueryType.CONCEPTUAL: 10,
        }

    async def classify(self, query: str) -> QueryClassification:
        """
        Classify query and return routing recommendation.
        """
        prompt = QUERY_CLASSIFIER_PROMPT.format(query=query)
        response = await self.llm.ainvoke(prompt)

        # Parse JSON response
        classification = QueryClassification.model_validate_json(response.content)

        # Override with mapping if confidence low
        if classification.confidence < 0.7:
            classification.recommended_mode = self.mode_mapping[classification.query_type]
            classification.recommended_top_k = self.top_k_mapping[classification.query_type]

        return classification

    async def route(
        self,
        query: str,
        namespace: str,
        force_mode: str | None = None,
    ) -> dict:
        """
        Route query to appropriate retrieval mode.

        Args:
            query: User query
            namespace: Collection namespace
            force_mode: Override automatic routing (for testing)

        Returns:
            Dict with contexts, mode used, and classification details
        """
        if force_mode:
            mode = force_mode
            classification = None
        else:
            classification = await self.classify(query)
            mode = classification.recommended_mode

        # Execute retrieval with recommended settings
        contexts = await self._retrieve(
            query=query,
            namespace=namespace,
            mode=mode,
            top_k=classification.recommended_top_k if classification else 10,
        )

        return {
            "contexts": contexts,
            "mode_used": mode,
            "classification": classification.model_dump() if classification else None,
        }
```

**Implementation Files:**
- `src/agents/coordinator/query_router.py` - QueryRouter class
- `src/agents/coordinator/nodes.py` - Integrate in retrieval node
- `tests/unit/agents/test_query_router.py` - 8 unit tests
- `tests/integration/test_query_routing_e2e.py` - 4 integration tests

**Acceptance Criteria:**
- [ ] QueryRouter class implemented with LLM classifier
- [ ] 4 query types correctly identified
- [ ] Mode routing accuracy ≥85% on test set
- [ ] Integration with coordinator nodes
- [ ] force_mode parameter for testing/override
- [ ] Classification logged for observability
- [ ] Unit tests: 8/8 passing
- [ ] Integration tests: 4/4 passing

**Test Dataset (20 queries):**
```json
[
    {"query": "What is Amnesty International's position on X?", "expected_type": "entity"},
    {"query": "What year was X founded?", "expected_type": "factoid"},
    {"query": "Which magazine started first?", "expected_type": "multi_hop"},
    {"query": "Explain human rights violations", "expected_type": "conceptual"},
    // ... 16 more queries
]
```

**Expected Impact:**
- Overall RAGAS metrics: +20-30% (automatic mode selection)
- User experience: No manual mode selection required

---

### Feature 81.2: Domain-Agnostic Entity Extraction (6 SP) ❌ **DEPRECATED**

> **Deprecated:** Deferred in favor of Faithfulness optimization (RAG Tuning Agent recommendations).
> C-LARA handles query routing; entity extraction improvements deferred to Sprint 82+ if needed.

**Beschreibung:**
Improve entity extraction to handle diverse document types beyond legal/policy documents. Add entity types for publications, chemicals, scientific terms, and generic proper nouns.

**Problem:**
- HotpotQA entity coverage ~40% (hypothesis)
- Missing entities: "Arthur's Magazine", "Cadmium Chloride", "James Henry Miller"
- Current prompts optimized for Amnesty-style legal documents

**Current Entity Types (Amnesty-optimized):**
```python
ENTITY_TYPES = [
    "Person", "Organization", "Location", "Date",
    "Event", "Legal_Case", "Document", "Policy",
]
```

**New Entity Types (Domain-agnostic):**
```python
ENTITY_TYPES = [
    # Core (existing)
    "Person", "Organization", "Location", "Date", "Event",

    # Legal/Policy (existing)
    "Legal_Case", "Document", "Policy", "Law", "Treaty",

    # Publications (NEW)
    "Magazine", "Newspaper", "Book", "Journal", "Publication",

    # Science (NEW)
    "Chemical", "Element", "Scientific_Term", "Medical_Term",

    # Entertainment (NEW)
    "TV_Show", "Movie", "Song", "Character", "Creator",

    # Generic (NEW - catch-all)
    "Proper_Noun", "Named_Entity", "Product", "Brand",
]
```

**Technical Solution:**

```python
# src/components/graph_rag/entity_extraction.py

ENTITY_EXTRACTION_PROMPT_V2 = """
Extract ALL named entities from the following text. Be comprehensive and include:

1. **People:** Names, aliases, stage names (e.g., "James Henry Miller" aka "Ewan MacColl")
2. **Organizations:** Companies, NGOs, government bodies, institutions
3. **Publications:** Magazines, newspapers, books, journals (e.g., "Arthur's Magazine")
4. **Locations:** Cities, countries, regions, addresses
5. **Scientific Terms:** Chemicals, elements, medical terms (e.g., "Cadmium Chloride", "ethanol")
6. **Entertainment:** TV shows, movies, songs, fictional characters
7. **Products/Brands:** Named products, brands, models
8. **Events:** Conferences, historical events, incidents
9. **Legal/Policy:** Laws, treaties, court cases, policies
10. **Dates/Times:** Specific dates, time periods, eras

For each entity, provide:
- name: The entity text as it appears
- type: One of the types above (use most specific type)
- aliases: Alternative names if mentioned (e.g., stage names, abbreviations)
- context: Brief context snippet (10-20 words)

Text:
{text}

Respond in JSON format:
{{
    "entities": [
        {{
            "name": "Arthur's Magazine",
            "type": "Magazine",
            "aliases": [],
            "context": "Arthur's Magazine was an American literary magazine..."
        }},
        ...
    ]
}}
"""

class EntityExtractorV2:
    """
    Improved entity extraction with domain-agnostic types.
    """

    ENTITY_TYPES = [
        "Person", "Organization", "Location", "Date", "Event",
        "Legal_Case", "Document", "Policy", "Law", "Treaty",
        "Magazine", "Newspaper", "Book", "Journal", "Publication",
        "Chemical", "Element", "Scientific_Term", "Medical_Term",
        "TV_Show", "Movie", "Song", "Character", "Creator",
        "Proper_Noun", "Named_Entity", "Product", "Brand",
    ]

    def __init__(self, llm, neo4j_driver):
        self.llm = llm
        self.neo4j = neo4j_driver

    async def extract_entities(self, text: str) -> list[dict]:
        """
        Extract entities using improved prompt.
        """
        prompt = ENTITY_EXTRACTION_PROMPT_V2.format(text=text)
        response = await self.llm.ainvoke(prompt)

        entities = self._parse_response(response.content)

        # Validate entity types
        for entity in entities:
            if entity["type"] not in self.ENTITY_TYPES:
                entity["type"] = "Named_Entity"  # Fallback

        return entities

    async def extract_with_aliases(self, text: str) -> list[dict]:
        """
        Extract entities and expand aliases as separate nodes.

        Creates relationships: (Entity)-[:ALIAS_OF]->(Alias)
        """
        entities = await self.extract_entities(text)

        expanded = []
        for entity in entities:
            expanded.append(entity)

            # Add aliases as separate entries with ALIAS_OF relationship
            for alias in entity.get("aliases", []):
                expanded.append({
                    "name": alias,
                    "type": entity["type"],
                    "alias_of": entity["name"],
                    "context": entity["context"],
                })

        return expanded
```

**Implementation Files:**
- `src/components/graph_rag/entity_extraction.py` - EntityExtractorV2
- `src/components/graph_rag/prompts.py` - ENTITY_EXTRACTION_PROMPT_V2
- `scripts/entity_extraction_audit.py` - Audit tool for coverage analysis
- `tests/unit/components/test_entity_extraction_v2.py` - 10 unit tests

**Entity Coverage Audit:**

```bash
# Run entity extraction audit on HotpotQA dataset
poetry run python scripts/entity_extraction_audit.py \
  --dataset data/evaluation/ragas_hotpotqa_20.jsonl \
  --namespace ragas_eval_txt \
  --output data/evaluation/entity_coverage_hotpotqa.json

# Expected output:
# {
#   "total_ground_truth_entities": 45,
#   "extracted_entities": 32,
#   "coverage": 0.71,
#   "missing_entities": ["Arthur's Magazine", "First for Women", ...],
#   "missing_by_type": {
#     "Magazine": 2,
#     "Chemical": 1,
#     "Person_Alias": 1
#   }
# }
```

**Acceptance Criteria:**
- [ ] EntityExtractorV2 class implemented
- [ ] 12 new entity types added
- [ ] Alias extraction implemented (ALIAS_OF relationships)
- [ ] Entity coverage audit script created
- [ ] HotpotQA entity coverage: 40% → **≥70%** (+30pp)
- [ ] Amnesty entity coverage: No regression
- [ ] Unit tests: 10/10 passing
- [ ] Re-ingest HotpotQA documents with new extractor

**Expected Impact:**
- HotpotQA Graph Mode: 60% empty contexts → <10%
- Entity recall: +75% (more entities captured)
- Graph query success rate: +30-40%

---

### Feature 81.3: Parent Chunk Retrieval (5 SP) 🎯 **P1 - HIGH**

**Beschreibung:**
Implement parent chunk retrieval to return full sections when sentence-level chunks are matched. This improves Context Recall by providing complete context instead of truncated snippets.

**Problem:**
- Current: Retrieve chunk, return same chunk (often truncated at 500-800 chars)
- Example: "...created by Matt Groening who named the character after " (cutoff)
- Missing information leads to LLM hallucination

**Solution Architecture:**

```
Document Structure:
├── Section 1 (parent chunk, 2000 tokens)
│   ├── Paragraph 1.1 (child chunk, 200 tokens)
│   ├── Paragraph 1.2 (child chunk, 250 tokens) ← Matched by query
│   └── Paragraph 1.3 (child chunk, 180 tokens)
├── Section 2 (parent chunk, 1800 tokens)
│   └── ...

Current behavior: Return Paragraph 1.2 only (250 tokens)
New behavior: Return Section 1 (2000 tokens) with Paragraph 1.2 highlighted
```

**Technical Solution:**

```python
# src/components/vector_search/parent_chunk_retrieval.py

class ParentChunkRetriever:
    """
    Retrieves parent sections when child chunks are matched.

    Database Schema:
    - chunks table: id, text, document_id, section_id, chunk_type (section|paragraph|sentence)
    - sections table: id, text, document_id, parent_section_id

    Chunk types:
    - section: Full document section (800-2000 tokens)
    - paragraph: Individual paragraph (100-400 tokens)
    - sentence: Single sentence (10-50 tokens)
    """

    def __init__(self, qdrant_client, chunk_store):
        self.qdrant = qdrant_client
        self.chunk_store = chunk_store

    async def retrieve_with_parent(
        self,
        query: str,
        namespace: str,
        top_k: int = 10,
        return_parent: bool = True,
        max_parent_tokens: int = 2000,
    ) -> list[dict]:
        """
        Retrieve chunks and expand to parent sections.

        Args:
            query: Search query
            namespace: Collection namespace
            top_k: Number of chunks to retrieve
            return_parent: If True, return parent section instead of matched chunk
            max_parent_tokens: Maximum tokens for parent section

        Returns:
            List of contexts with parent sections
        """
        # Step 1: Retrieve matched chunks (sentence or paragraph level)
        matched_chunks = await self.qdrant.search(
            collection_name=namespace,
            query_text=query,
            limit=top_k * 2,  # Retrieve more, deduplicate after parent expansion
        )

        if not return_parent:
            return matched_chunks[:top_k]

        # Step 2: Expand to parent sections
        parent_sections = []
        seen_parents = set()

        for chunk in matched_chunks:
            parent_id = chunk.get("section_id") or chunk.get("parent_id")

            if parent_id and parent_id not in seen_parents:
                seen_parents.add(parent_id)

                # Retrieve parent section
                parent = await self.chunk_store.get_section(parent_id)

                if parent and len(parent["text"]) <= max_parent_tokens * 4:  # ~4 chars/token
                    parent_sections.append({
                        "text": parent["text"],
                        "chunk_id": parent_id,
                        "matched_chunk_id": chunk["id"],
                        "matched_text": chunk["text"],
                        "score": chunk["score"],
                        "document_id": chunk["document_id"],
                        "retrieval_type": "parent_expansion",
                    })

            # Fallback: No parent, use original chunk
            elif parent_id not in seen_parents:
                parent_sections.append({
                    **chunk,
                    "retrieval_type": "direct",
                })

        # Step 3: Deduplicate and return top-k
        return parent_sections[:top_k]
```

**Implementation Files:**
- `src/components/vector_search/parent_chunk_retrieval.py` - ParentChunkRetriever
- `src/domains/document_processing/chunking.py` - Add section_id to chunks
- `tests/unit/components/test_parent_chunk_retrieval.py` - 6 unit tests

**Database Schema Update:**

```python
# Add section_id to chunk metadata during ingestion
chunk_metadata = {
    "id": chunk_id,
    "text": chunk_text,
    "document_id": document_id,
    "section_id": section_id,  # NEW: Parent section reference
    "chunk_type": "paragraph",  # NEW: section | paragraph | sentence
    "section_title": section_title,  # NEW: For display
}
```

**Acceptance Criteria:**
- [ ] ParentChunkRetriever class implemented
- [ ] section_id added to chunk metadata
- [ ] Parent expansion logic working
- [ ] Deduplication prevents duplicate sections
- [ ] Max token limit enforced
- [ ] RAGAS Context Recall: 0.700 → **≥0.800** (+14%)
- [ ] Unit tests: 6/6 passing

**Expected Impact:**
- Context Recall: +14% (more complete context)
- Faithfulness: +10-20% (less truncation-induced hallucination)

---

### Feature 81.4: Retrieval Mode Performance Dashboard (3 SP) 🎯 **P2**

**Beschreibung:**
Create a monitoring dashboard to track retrieval mode performance and query routing decisions. Enables data-driven optimization.

**Dashboard Metrics:**

```yaml
Query Routing:
  - Queries by type (entity/factoid/multi_hop/conceptual)
  - Mode distribution (vector/graph/hybrid)
  - Routing override rate (force_mode usage)
  - Classification confidence distribution

Retrieval Performance:
  - Contexts retrieved by mode
  - Empty context rate by mode
  - Average retrieval latency by mode
  - Cross-encoder reranking latency

Quality Metrics (from RAGAS):
  - Faithfulness by mode
  - Context Precision by mode
  - Context Recall by mode
  - Answer Relevancy by mode
```

**Technical Solution:**

```python
# src/api/v1/admin_retrieval_metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Query routing metrics
query_classification_counter = Counter(
    "aegis_query_classification_total",
    "Total query classifications",
    ["query_type", "recommended_mode"],
)

routing_confidence_histogram = Histogram(
    "aegis_routing_confidence",
    "Query routing confidence distribution",
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# Retrieval metrics
retrieval_latency_histogram = Histogram(
    "aegis_retrieval_latency_seconds",
    "Retrieval latency by mode",
    ["mode"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)

empty_context_counter = Counter(
    "aegis_empty_context_total",
    "Empty context retrievals",
    ["mode", "namespace"],
)

# RAGAS metrics (updated after evaluation)
ragas_metric_gauge = Gauge(
    "aegis_ragas_metric",
    "RAGAS evaluation metrics",
    ["metric", "mode", "dataset"],
)
```

**Grafana Dashboard:**

```json
{
  "panels": [
    {
      "title": "Query Type Distribution",
      "type": "piechart",
      "query": "sum(aegis_query_classification_total) by (query_type)"
    },
    {
      "title": "Retrieval Mode Performance",
      "type": "timeseries",
      "query": "histogram_quantile(0.95, aegis_retrieval_latency_seconds)"
    },
    {
      "title": "RAGAS Faithfulness by Mode",
      "type": "stat",
      "query": "aegis_ragas_metric{metric='faithfulness'}"
    }
  ]
}
```

**Acceptance Criteria:**
- [ ] Prometheus metrics exported
- [ ] Grafana dashboard created
- [ ] Query routing metrics tracked
- [ ] Retrieval performance monitored
- [ ] RAGAS metrics integrated

---

### Feature 81.5: RAGAS Automated Evaluation Pipeline (3 SP) 🎯 **P2**

**Beschreibung:**
Create automated RAGAS evaluation pipeline that runs nightly or on-demand to track metrics over time.

**Pipeline Architecture:**

```yaml
# .github/workflows/ragas-evaluation.yml
name: RAGAS Evaluation

on:
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM
  workflow_dispatch:      # Manual trigger

jobs:
  evaluate:
    runs-on: self-hosted  # DGX Spark
    steps:
      - uses: actions/checkout@v4

      - name: Run RAGAS Evaluation
        run: |
          poetry run python scripts/run_ragas_evaluation.py \
            --dataset data/evaluation/ragas_amnesty_50.jsonl \
            --modes vector,graph,hybrid \
            --output-dir data/evaluation/results/$(date +%Y-%m-%d)/

      - name: Upload Metrics to Prometheus
        run: |
          poetry run python scripts/push_ragas_metrics.py \
            --results data/evaluation/results/$(date +%Y-%m-%d)/

      - name: Update RAGAS_JOURNEY.md
        run: |
          poetry run python scripts/update_ragas_journey.py \
            --results data/evaluation/results/$(date +%Y-%m-%d)/
```

**Implementation Files:**
- `.github/workflows/ragas-evaluation.yml` - CI/CD pipeline
- `scripts/push_ragas_metrics.py` - Prometheus metrics pusher
- `scripts/update_ragas_journey.py` - Auto-update RAGAS_JOURNEY.md

**Acceptance Criteria:**
- [ ] GitHub Actions workflow created
- [ ] Nightly evaluation running
- [ ] Metrics pushed to Prometheus
- [ ] RAGAS_JOURNEY.md auto-updated
- [ ] Slack/email notifications on regression

---

### Feature 81.7: C-LARA SetFit Intent Classifier Training (3 SP) ✅ **DONE**

**Beschreibung:**
Complete the C-LARA (Context-aware LLM-Assisted RAG) intent classifier training that was started in Sprint 67. Uses Multi-Teacher approach with edge cases for robust training.

**Sprint 81 Achievements (2026-01-09):**
- **Multi-Teacher:** 4 different LLMs (qwen2.5:7b, mistral:7b, phi4-mini, gemma3:4b) to reduce single-model bias
- **Edge Cases:** 42 manually crafted examples (typos, code, mixed language, short queries)
- **Achieved Accuracy:** **95.22%** (exceeded 91-96% target!)
- **Training Time:** 37 min (NGC GPU Container)
- **5-Class C-LARA Intents:** factual, procedural, comparison, recommendation, navigation

**Data Generation:**
```bash
# Multi-Teacher generation (1040 examples total)
poetry run python -m src.adaptation.intent_data_generator \
  --multi-teacher \
  --output data/intent_training_multi_teacher_v1.jsonl
```

**Model Training:**
```bash
# Train SetFit model on multi-teacher data
poetry run python -m src.adaptation.intent_trainer \
  --data data/intent_training_multi_teacher_v1.jsonl \
  --output models/intent_classifier
```

**Integration:**
- Model saved to `models/intent_classifier/` (tracked in git)
- Activated via `USE_SETFIT_CLASSIFIER=true` environment variable
- IntentClassifier automatically loads model and adjusts RRF weights

**Files:**
- `src/adaptation/intent_data_generator.py` - Multi-Teacher data generation
- `src/adaptation/intent_trainer.py` - SetFit training script
- `src/components/retrieval/intent_classifier.py` - Production classifier
- `models/intent_classifier/` - Trained model (git tracked)

**Acceptance Criteria:**
- [x] 1000+ training examples generated from 4 models ✅ (1,043 examples)
- [x] SetFit model trained with validation accuracy ≥90% ✅ (**95.22%**)
- [x] Model saved to models/intent_classifier/ ✅ (418 MB)
- [x] Intent router functional with trained model ✅ (100% test accuracy, ~40ms latency)
- [x] TD-079 resolved and archived ✅ (moved to archive/)

**Achieved Impact:**
- Intent classification: 60% → **95.22%** accuracy (+35 pp)
- Per-class F1: All 5 classes >92% (factual 93%, procedural 94%, comparison 98%, recommendation 98%, navigation 94%)
- Inference latency: **~40ms** (vs 200-500ms LLM-based)
- Confidence: **99.7%+** on all test queries

---

### Feature 81.8: No-Hedging Prompt for Faithfulness (1 SP) 🎯 **P0 - CRITICAL**

**Beschreibung:**
Implement "No-Hedging Prompt" to eliminate LLM meta-commentary hallucination and improve Faithfulness score.

**Problem (from RAG Tuning Agent Analysis):**
- Current Faithfulness: 0.6267 (with C-LARA ON)
- LLM adds meta-commentary like "The provided documents do not contain information about..."
- This contradicts the context (which may contain relevant info) → Faithfulness penalty
- Root cause: LLM "hedging" behavior, not retrieval quality issue

**Solution:**

```python
# src/agents/multi_turn/prompts.py

NO_HEDGING_PROMPT = """
CRITICAL INSTRUCTION - FAITHFULNESS REQUIREMENTS:

1. ONLY use facts explicitly stated in the provided context
2. NEVER add meta-commentary about what the documents contain/don't contain
3. NEVER say "The documents don't mention..." or "No information available about..."
4. If information is not in context: Simply answer based on what IS available
5. If completely unanswerable: Say "I cannot answer this based on the provided information."

DO NOT hedge, qualify, or comment on document contents - just answer the question directly.
"""
```

**Expected Impact:**
- Faithfulness: 0.63 → **0.80** (+27%)
- Eliminates LLM-induced hallucination ("meta-commentary")
- Maintains high Answer Relevancy (0.72+)

**Acceptance Criteria:**
- [ ] NO_HEDGING_PROMPT added to generation prompts
- [ ] RAGAS evaluation shows Faithfulness ≥0.75
- [ ] No regression on other metrics (CP, CR, AR)
- [ ] Integration with C-LARA (conditional hedging based on confidence)

---

### Feature 81.6: Entity Extraction Benchmark Suite (2 SP)

**Beschreibung:**
Create benchmark suite to measure entity extraction quality across different document types.

**Benchmark Datasets:**
- Amnesty (legal/policy) - existing
- HotpotQA (general knowledge) - existing
- SciQ (scientific) - new
- Legal-BERT (legal cases) - new

**Metrics:**
- Entity Recall: % of ground truth entities extracted
- Entity Precision: % of extracted entities that are correct
- Type Accuracy: % of entities with correct type labels

**Implementation:**

```python
# scripts/benchmark_entity_extraction.py

class EntityExtractionBenchmark:
    def __init__(self, extractor, ground_truth):
        self.extractor = extractor
        self.ground_truth = ground_truth

    def run(self, dataset: str) -> dict:
        results = {
            "recall": 0.0,
            "precision": 0.0,
            "type_accuracy": 0.0,
            "by_type": {},
        }

        for sample in self.ground_truth[dataset]:
            extracted = self.extractor.extract(sample["text"])
            gt_entities = sample["entities"]

            # Calculate metrics
            matched = self._match_entities(extracted, gt_entities)
            results["recall"] += len(matched) / len(gt_entities)
            results["precision"] += len(matched) / len(extracted) if extracted else 0

        # Average
        n = len(self.ground_truth[dataset])
        results["recall"] /= n
        results["precision"] /= n

        return results
```

**Acceptance Criteria:**
- [ ] Benchmark script created
- [ ] 4 datasets configured
- [ ] Ground truth entities annotated
- [ ] Baseline metrics established
- [ ] Improvement tracking enabled

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/agents/test_query_router.py
class TestQueryRouter:
    def test_entity_query_classification(self):
        """Verify entity queries routed to graph."""

    def test_factoid_query_classification(self):
        """Verify factoid queries routed to hybrid."""

    def test_multi_hop_query_classification(self):
        """Verify multi-hop queries get extended context."""

    def test_low_confidence_fallback(self):
        """Verify low confidence uses default mapping."""

# tests/unit/components/test_entity_extraction_v2.py
class TestEntityExtractorV2:
    def test_publication_extraction(self):
        """Verify magazine/journal entities extracted."""

    def test_chemical_extraction(self):
        """Verify chemical entities extracted."""

    def test_alias_extraction(self):
        """Verify person aliases captured."""
```

### Integration Tests

```bash
# Query routing E2E test
pytest tests/integration/test_query_routing_e2e.py -v

# Entity extraction on HotpotQA
pytest tests/integration/test_entity_extraction_hotpotqa.py -v
```

---

## Success Metrics

| Metric | Baseline (Sprint 80) | Target (Sprint 81) | Status |
|--------|---------------------|-------------------|--------|
| Intent classification accuracy | 60% (LLM-based) | ≥90% | ✅ **95.22%** (C-LARA) |
| Faithfulness | 0.60 (S80) | ≥0.75 | 🎯 0.6267 (+4.5% C-LARA) |
| Context Recall | 1.0000 | ≥1.00 | ✅ **1.0000** |
| Context Precision | 1.0000 | ≥1.00 | ✅ **1.0000** |
| Answer Relevancy | 0.72 | ≥0.75 | 🎯 0.7249 |
| ~Query routing accuracy~ | ~N/A~ | ~≥85%~ | ❌ Deprecated (81.1) |
| ~Entity coverage (HotpotQA)~ | ~40%~ | ~≥70%~ | ❌ Deprecated (81.2) |

---

## Deliverables

1. **Code:**
   - [ ] `src/agents/coordinator/query_router.py` - QueryRouter
   - [ ] `src/components/graph_rag/entity_extraction.py` - EntityExtractorV2
   - [ ] `src/components/vector_search/parent_chunk_retrieval.py`
   - [ ] `scripts/entity_extraction_audit.py`
   - [ ] 24 unit tests, 8 integration tests

2. **Data:**
   - [ ] Entity extraction benchmarks
   - [ ] Query classification test set (20 queries)

3. **Documentation:**
   - [ ] ADR-045: Query-Adaptive Routing
   - [ ] ADR-046: Parent Chunk Retrieval
   - [ ] RAGAS_JOURNEY.md Experiment #4

4. **Infrastructure:**
   - [ ] Grafana dashboard for retrieval metrics
   - [ ] Automated RAGAS evaluation pipeline

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM classifier adds latency | Medium | Medium | Cache classifications, <100ms target |
| Entity extraction regression on Amnesty | Low | High | Test on both datasets before deploy |
| Parent chunk retrieval increases token usage | High | Medium | Enforce max_parent_tokens limit |
| Query routing accuracy <85% | Medium | High | Fallback to hybrid mode for uncertain queries |

---

## Timeline

**Week 1 (2026-01-27 to 2026-01-31):**
- Day 1-3: Feature 81.1 (Query-Adaptive Routing)
- Day 3-5: Feature 81.2 (Entity Extraction V2)

**Week 2 (2026-02-03 to 2026-02-07):**
- Day 1-2: Feature 81.3 (Parent Chunk Retrieval)
- Day 3: Feature 81.4 (Performance Dashboard)
- Day 4: Feature 81.5 (Automated Pipeline)
- Day 4-5: Feature 81.6 (Benchmarks), Documentation
- Day 5: Sprint Review

---

## Sprint Review Criteria

**P1 High Priority (MUST PASS):**
- [ ] Query routing accuracy ≥85%
- [ ] Entity coverage (HotpotQA) ≥70%
- [ ] Context Recall ≥0.800
- [ ] No regression on Sprint 80 metrics

**P2 Medium Priority (SHOULD PASS):**
- [ ] Grafana dashboard operational
- [ ] Automated evaluation pipeline running
- [ ] Benchmarks established

**Documentation:**
- [ ] ADR-045 and ADR-046 created
- [ ] RAGAS_JOURNEY.md Experiment #4 complete

---

## Follow-up for Sprint 82+

**DSPy Optimization (if Faithfulness <0.90):**
- DSPy for answer generation optimization
- RAGAS Faithfulness as reward signal
- Target: F ≥ 0.90 (SOTA parity)

**GraphRAG Enhancements:**
- Community detection (Leiden algorithm)
- Hierarchical summaries
- Multi-hop graph traversal (2-5 hops)

**Evaluation Expansion:**
- Add SciQ, Legal-BERT datasets
- Multi-language evaluation
- Production traffic sampling
