# Sprint 85 Plan: Relation Extraction Improvement (TD-102)

**Epic:** Knowledge Graph Quality Enhancement
**Technical Debt:** TD-102 (Relation Extraction Improvement)
**Duration:** 7-10 days
**Total Story Points:** 18 SP
**Status:** 📝 Planned

---

## Sprint Goal

Improve Relation Extraction Ratio from **0.27-0.61** to **≥1.0** through iterative improvements:
- **SpaCy-first Cascade** for robust entity baseline (UI-configurable)
- **Domain Training Integration** using existing domain prompts from Neo4j
- **Enhanced Gleaning** (already implemented - optimize configuration)

---

## Context

### Current State (Sprint 84/85 Multi-Format Test)

| Format | Entities | Relations | Ratio | Rating |
|--------|----------|-----------|-------|--------|
| CSV | 5 | 2 | 0.40 | Poor |
| XLSX | 5 | 2 | 0.40 | Poor |
| PDF | 22 | 6 | **0.27** | Very Poor |
| DOCX | 22 | 10 | 0.45 | Moderate |
| PPTX | 23 | 14 | 0.61 | Moderate |

### Existing Infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| **Gleaning (Multi-Pass)** | `extraction_service.py:1057` | ✅ Sprint 83 |
| **Domain Training Prompts** | `domain_repository.py` (Neo4j) | ✅ Sprint 45 |
| **SpaCy Multi-Language** | `hybrid_extraction_service.py` (DE/EN/FR/ES) | ✅ Sprint 83 |
| **DSPy MIPROv2** | `dspy_optimizer.py` | ✅ Sprint 64 |
| **3-Rank Cascade** | `extraction_cascade.py` | ✅ Sprint 83 |

### Target State (After Sprint 85)

| Metric | Baseline | Target |
|--------|----------|--------|
| **Relation Ratio** | 0.27-0.61 | ≥1.0 |
| **Typed Coverage** | ~5% | ≥60% |
| **Duplication Rate** | ~15% | ≤5% |

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 85.1 | Admin UI Cascade Configuration | 3 | P0 | 📝 Planned |
| 85.2 | Domain Training Prompt Integration | 3 | P0 | 📝 Planned |
| 85.3 | Enhanced Gleaning Configuration | 2 | P0 | 📝 Planned |
| 85.4 | Entity Canonicalization (Best Practice) | 3 | P1 | 📝 Planned |
| 85.5 | KG Hygiene & Deduplication (Best Practice) | 2 | P1 | 📝 Planned |
| 85.6 | Extraction Metrics (Log + LangGraph State) | 2 | P1 | 📝 Planned |
| 85.7 | DSPy Training Data Collection | 3 | P2 | 📝 Planned |

---

## Feature 85.1: Admin UI Cascade Configuration (3 SP)

### Description
Make the extraction cascade fully configurable through the Admin UI.

### Current State
The cascade is defined in `src/config/extraction_cascade.py` but not UI-configurable.

### Schema Extension (Admin UI)

```typescript
// frontend/src/types/extraction.ts

interface CascadeRankConfig {
  rank: number;               // 1, 2, 3
  model: string;              // "nemotron-3-nano:latest", "gpt-oss:20b", "spacy_multi"
  method: ExtractionMethod;   // "llm_only", "ner_only", "llm_relation_only", "hybrid"
  entity_timeout_s: number;   // Default: 60
  relation_timeout_s: number; // Default: 300
  enabled: boolean;           // Allow disabling ranks
}

type ExtractionMethod =
  | "llm_only"          // LLM extracts entities + relations
  | "ner_only"          // SpaCy NER only (entities)
  | "llm_relation_only" // LLM for relations with entity contract
  | "hybrid";           // SpaCy NER + LLM relations
```

### API Endpoints

```python
# src/api/v1/admin_extraction.py

@router.get("/extraction/cascade")
async def get_cascade_config() -> list[CascadeRankConfig]:
    """Get current cascade configuration."""

@router.put("/extraction/cascade")
async def update_cascade_config(
    config: list[CascadeRankConfig]
) -> list[CascadeRankConfig]:
    """Update cascade configuration (persisted to Redis)."""

@router.get("/extraction/methods")
async def get_available_methods() -> list[str]:
    """Get list of available extraction methods."""
    return ["llm_only", "ner_only", "llm_relation_only", "hybrid"]

@router.get("/extraction/models")
async def get_available_models() -> list[str]:
    """Get list of available models (Ollama + SpaCy)."""
```

### Admin UI Component

```tsx
// frontend/src/components/admin/CascadeConfigEditor.tsx

function CascadeRankEditor({ rank, config, onChange }) {
  return (
    <Card>
      <CardHeader>Rank {rank.rank}</CardHeader>
      <CardContent>
        <Select
          label="Model"
          options={availableModels}
          value={rank.model}
          onChange={(v) => onChange({ ...rank, model: v })}
        />
        <Select
          label="Method"
          options={["llm_only", "ner_only", "llm_relation_only", "hybrid"]}
          value={rank.method}
          onChange={(v) => onChange({ ...rank, method: v })}
        />
        <NumberInput
          label="Entity Timeout (s)"
          value={rank.entity_timeout_s}
          min={10}
          max={600}
          onChange={(v) => onChange({ ...rank, entity_timeout_s: v })}
        />
        <NumberInput
          label="Relation Timeout (s)"
          value={rank.relation_timeout_s}
          min={30}
          max={900}
          onChange={(v) => onChange({ ...rank, relation_timeout_s: v })}
        />
        <Switch
          label="Enabled"
          checked={rank.enabled}
          onChange={(v) => onChange({ ...rank, enabled: v })}
        />
      </CardContent>
    </Card>
  );
}
```

### Default Configuration (SpaCy-first)

```python
# NEW: SpaCy-first cascade (configurable via UI)
DEFAULT_CASCADE = [
    CascadeRankConfig(
        rank=1,
        model="spacy_multi",  # de_core_news_lg, en_core_web_lg, fr_core_news_lg, es_core_news_lg
        method=ExtractionMethod.NER_ONLY,
        entity_timeout_s=60,
        enabled=True,
    ),
    CascadeRankConfig(
        rank=2,
        model="nemotron-3-nano:latest",
        method=ExtractionMethod.LLM_RELATION_ONLY,
        relation_timeout_s=300,
        enabled=True,
    ),
    CascadeRankConfig(
        rank=3,
        model="gpt-oss:20b",
        method=ExtractionMethod.LLM_ONLY,
        entity_timeout_s=300,
        relation_timeout_s=300,
        enabled=True,
    ),
]
```

### Acceptance Criteria

- [ ] Admin UI shows cascade configuration
- [ ] Each rank configurable (model, method, timeouts, enabled)
- [ ] Configuration persisted to Redis
- [ ] Changes applied without restart
- [ ] Unit tests for API endpoints

---

## Feature 85.2: Domain Training Prompt Integration (3 SP)

### Description
Use existing Domain Training prompts from Neo4j instead of hardcoded relation types.

### Current State (Domain Repository Schema)

```cypher
(:Domain {
    name: string,
    description: string,
    entity_prompt: string,        # ← Domain-specific entity extraction prompt
    relation_prompt: string,      # ← Domain-specific relation extraction prompt
    entity_examples: JSON,        # ← Few-shot examples for entities
    relation_examples: JSON,      # ← Few-shot examples for relations
    extraction_model_cascade: JSON,  # ← Custom cascade per domain
    extraction_settings: JSON,    # ← Fast vs refinement settings
})
```

### Integration Flow

```python
# src/components/graph_rag/extraction_service.py

async def extract_with_domain_prompts(
    self,
    text: str,
    document_id: str,
    domain: str | None = None,
) -> tuple[list[GraphEntity], list[GraphRelationship]]:
    """
    Extract using domain-specific prompts if available.

    Flow:
    1. Detect domain from document (or use provided)
    2. Load domain prompts from Neo4j (entity_prompt, relation_prompt)
    3. Use domain prompts instead of generic ENTITY_EXTRACTION_PROMPT
    4. Fall back to generic prompts if domain not found
    """
    # Get domain repository
    domain_repo = get_domain_repository()

    # Find matching domain
    if domain:
        domain_config = await domain_repo.get_domain_by_name(domain)
    else:
        # Auto-detect domain using document embedding
        doc_embedding = await self.embedding_service.embed(text[:2000])
        domain_config = await domain_repo.find_best_matching_domain(doc_embedding)

    # Use domain prompts or fall back to generic
    if domain_config and domain_config.entity_prompt:
        entity_prompt = domain_config.entity_prompt
        relation_prompt = domain_config.relation_prompt
        logger.info(
            "using_domain_prompts",
            domain=domain_config.name,
            has_entity_prompt=bool(domain_config.entity_prompt),
            has_relation_prompt=bool(domain_config.relation_prompt),
        )
    else:
        entity_prompt = ENTITY_EXTRACTION_PROMPT
        relation_prompt = RELATIONSHIP_EXTRACTION_PROMPT
        logger.info("using_generic_prompts", domain=domain)

    # Extract with selected prompts
    entities = await self._extract_entities_with_prompt(text, entity_prompt)
    relations = await self._extract_relations_with_prompt(text, entities, relation_prompt)

    return entities, relations
```

### Typed Relations from Domain Examples

```python
# Domain relation examples define available types
TECH_DOMAIN_RELATION_EXAMPLES = [
    {"source": "Python", "target": "TensorFlow", "type": "USES", "description": "..."},
    {"source": "TensorFlow", "target": "GPU", "type": "RUNS_ON", "description": "..."},
    {"source": "Module", "target": "Package", "type": "PART_OF", "description": "..."},
]

# Prompt includes domain-specific types from examples
DOMAIN_RELATION_PROMPT = """
Extract relationships between entities using these types from this domain:
{relation_types_from_examples}

Only use RELATES_TO if no specific type fits.
"""
```

### Acceptance Criteria

- [ ] Load entity_prompt from Domain if available
- [ ] Load relation_prompt from Domain if available
- [ ] Auto-detect domain using embedding similarity
- [ ] Fall back to generic prompts if domain not found
- [ ] Log which prompts are being used

---

## Feature 85.3: Enhanced Gleaning Configuration (2 SP)

### Description
Gleaning is already implemented (Sprint 83). This feature adds:
- Confidence thresholds
- Evidence span requirements
- Guardrail validation

### Current State

```python
# extraction_service.py:1057 - Already implemented!
async def extract_entities_with_gleaning(
    self,
    text: str,
    document_id: str | None = None,
    domain: str | None = None,
    gleaning_steps: int = 0,  # 0=disabled, 1-3=enabled
) -> list[GraphEntity]:
```

### Enhancement: GleaningConfig

```python
# src/config/gleaning_config.py

@dataclass
class GleaningConfig:
    """Enhanced gleaning configuration with guardrails."""

    # From existing implementation
    max_passes: int = 2

    # NEW: Quality guardrails
    min_confidence: float = 0.7
    evidence_required: bool = True
    max_evidence_words: int = 25
    allow_new_relations_only: bool = True
    dedupe_on_canonical: bool = True

    # NEW: Admin UI configurable
    enabled: bool = True

    @classmethod
    def from_domain(cls, domain_config: dict) -> "GleaningConfig":
        """Load gleaning config from domain settings."""
        settings = domain_config.get("extraction_settings", {})
        return cls(
            max_passes=settings.get("gleaning_steps", 2),
            min_confidence=settings.get("gleaning_min_confidence", 0.7),
            evidence_required=settings.get("gleaning_evidence_required", True),
        )
```

### Validation Function

```python
def validate_gleaning_relation(
    relation: dict,
    config: GleaningConfig,
    existing_relations: list[dict]
) -> tuple[bool, str]:
    """Validate gleaning relation against guardrails."""

    # Confidence check
    if relation.get("confidence", 0) < config.min_confidence:
        return False, f"confidence {relation.get('confidence')} < {config.min_confidence}"

    # Evidence check
    if config.evidence_required:
        evidence = relation.get("evidence_span", "")
        if not evidence:
            return False, "no evidence_span"
        if len(evidence.split()) > config.max_evidence_words:
            return False, f"evidence too long ({len(evidence.split())} words)"

    # Duplicate check (on canonical form)
    if config.allow_new_relations_only:
        rel_key = _canonical_relation_key(relation)
        existing_keys = {_canonical_relation_key(r) for r in existing_relations}
        if rel_key in existing_keys:
            return False, "duplicate relation"

    return True, "valid"
```

### Acceptance Criteria

- [ ] GleaningConfig dataclass with guardrails
- [ ] Validation function for gleaned relations
- [ ] Integration with existing gleaning code
- [ ] Admin UI toggle for gleaning

---

## Feature 85.4: Entity Canonicalization (Best Practice) (3 SP)

### Description
Implement entity canonicalization following LightRAG and Neo4j ERKG best practices.

### Best Practice: LightRAG Approach

> "In LightRAG, all occurrences of the same entities are combined and grouped across chunks. Relationships are consolidated across chunks to give a consistent, canonical key."
> — [Neo4j Blog: Under the Covers With LightRAG](https://neo4j.com/blog/developer/under-the-covers-with-lightrag-extraction/)

### Implementation

```python
# src/components/graph_rag/entity_canonicalization.py

@dataclass
class CanonicalEntity:
    """Canonical entity form for stable graph construction."""

    canonical_id: str      # Normalized: "nvidia_rtx_3060"
    surface_forms: set[str]  # Original: {"RTX 3060", "RTX3060", "GeForce RTX 3060"}
    entity_type: str       # "HARDWARE"
    merged_descriptions: list[str]  # Descriptions from all chunks
    source_chunks: list[str]  # Chunk IDs where entity appears

    @property
    def primary_name(self) -> str:
        """Most common surface form as display name."""
        # Return most frequent surface form
        return max(self.surface_forms, key=len)  # Simplification


class EntityCanonicalizer:
    """Canonicalize entities for stable graph construction."""

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        use_embeddings: bool = True
    ):
        self.similarity_threshold = similarity_threshold
        self.use_embeddings = use_embeddings
        self.embedding_service = get_embedding_service()

    def normalize(self, entity_name: str) -> str:
        """Normalize entity name to canonical form."""
        # Lowercase
        normalized = entity_name.lower()
        # Replace whitespace with underscores
        normalized = re.sub(r'\s+', '_', normalized)
        # Remove special characters (keep alphanumeric and underscore)
        normalized = re.sub(r'[^\w]', '', normalized)
        return normalized

    async def find_canonical_match(
        self,
        entity: GraphEntity,
        existing_entities: list[CanonicalEntity]
    ) -> CanonicalEntity | None:
        """Find matching canonical entity using embedding similarity."""

        if not existing_entities:
            return None

        # Quick check: exact normalized match
        normalized = self.normalize(entity.name)
        for canonical in existing_entities:
            if normalized == canonical.canonical_id:
                return canonical

        # Embedding-based similarity (if enabled)
        if self.use_embeddings:
            entity_embedding = await self.embedding_service.embed(entity.name)

            for canonical in existing_entities:
                # Check all surface forms
                for surface_form in canonical.surface_forms:
                    form_embedding = await self.embedding_service.embed(surface_form)
                    similarity = cosine_similarity(entity_embedding, form_embedding)

                    if similarity >= self.similarity_threshold:
                        return canonical

        return None

    def merge_entity(
        self,
        entity: GraphEntity,
        canonical: CanonicalEntity,
        chunk_id: str
    ) -> CanonicalEntity:
        """Merge entity into existing canonical entity."""
        canonical.surface_forms.add(entity.name)
        canonical.merged_descriptions.append(entity.description)
        canonical.source_chunks.append(chunk_id)
        return canonical
```

### Neo4j Storage

```cypher
# Canonical entity with surface forms
CREATE (e:Entity {
    canonical_id: "nvidia_rtx_3060",
    primary_name: "NVIDIA RTX 3060",
    surface_forms: ["RTX 3060", "RTX3060", "GeForce RTX 3060"],
    type: "HARDWARE",
    description: "High-performance graphics card"
})
```

### Acceptance Criteria

- [ ] CanonicalEntity dataclass
- [ ] Normalize function (lowercase, underscores)
- [ ] Embedding-based similarity matching
- [ ] Merge logic for duplicate entities
- [ ] Unit tests for canonicalization

---

## Feature 85.5: KG Hygiene & Deduplication (Best Practice) (2 SP)

### Description
Implement KG hygiene following LlamaIndex best practices.

### Best Practice: LlamaIndex Approach

> "Entity deduplication uses a combination of text embedding similarity and word distance to find potential duplicates. This involves defining a vector index on entities in the graph using Cypher queries with cosine similarity functions."
> — [LlamaIndex Blog: Customizing Property Graph Index](https://www.llamaindex.ai/blog/customizing-property-graph-index-in-llamaindex)

### Implementation

```python
# src/components/graph_rag/kg_hygiene.py

class KGHygieneService:
    """Knowledge Graph hygiene and deduplication."""

    def __init__(self):
        self.neo4j_client = get_neo4j_client()
        self.embedding_service = get_embedding_service()

    async def find_duplicate_entities(
        self,
        similarity_threshold: float = 0.90
    ) -> list[tuple[str, str, float]]:
        """Find potential duplicate entities using Neo4j vector index."""

        # Use Neo4j's vector similarity (requires vector index on entities)
        query = """
        MATCH (e1:Entity)
        WHERE e1.embedding IS NOT NULL
        CALL db.index.vector.queryNodes('entity_embedding_index', 10, e1.embedding)
        YIELD node AS e2, score
        WHERE e1 <> e2 AND score >= $threshold
        RETURN e1.canonical_id AS entity1,
               e2.canonical_id AS entity2,
               score AS similarity
        ORDER BY score DESC
        """

        results = await self.neo4j_client.execute_read(
            query, {"threshold": similarity_threshold}
        )
        return [(r["entity1"], r["entity2"], r["similarity"]) for r in results]

    async def validate_relations(self) -> dict[str, int]:
        """Validate all relations against hygiene rules."""

        violations = {
            "self_loops": 0,
            "missing_evidence": 0,
            "invalid_type": 0,
            "orphan_relations": 0,
        }

        # Self-loops
        self_loops = await self.neo4j_client.execute_read("""
            MATCH (e:Entity)-[r]->(e)
            RETURN count(r) AS count
        """)
        violations["self_loops"] = self_loops[0]["count"]

        # Missing evidence
        no_evidence = await self.neo4j_client.execute_read("""
            MATCH ()-[r:RELATES_TO]->()
            WHERE r.evidence_span IS NULL OR r.evidence_span = ""
            RETURN count(r) AS count
        """)
        violations["missing_evidence"] = no_evidence[0]["count"]

        return violations

    async def merge_duplicate_entities(
        self,
        entity1_id: str,
        entity2_id: str,
        keep: str = "entity1"
    ) -> None:
        """Merge two duplicate entities, preserving all relationships."""

        merge_query = """
        MATCH (keep:Entity {canonical_id: $keep_id})
        MATCH (remove:Entity {canonical_id: $remove_id})
        // Transfer all incoming relationships
        CALL apoc.refactor.mergeNodes([keep, remove], {
            properties: "combine",
            mergeRels: true
        })
        YIELD node
        RETURN node
        """

        keep_id = entity1_id if keep == "entity1" else entity2_id
        remove_id = entity2_id if keep == "entity1" else entity1_id

        await self.neo4j_client.execute_write(
            merge_query,
            {"keep_id": keep_id, "remove_id": remove_id}
        )
```

### Hygiene Rules

```python
KG_HYGIENE_RULES = [
    # No self-loops
    lambda r: r["source"] != r["target"],

    # Evidence present
    lambda r: r.get("evidence_span") is not None and len(r["evidence_span"]) > 0,

    # Valid relation type
    lambda r: r["type"] in VALID_RELATION_TYPES or r["type"] == "RELATES_TO",

    # Entities exist
    lambda r: r["source_exists"] and r["target_exists"],
]
```

### Acceptance Criteria

- [ ] Vector-based duplicate detection (Neo4j index)
- [ ] Hygiene validation rules
- [ ] Entity merge function (APOC)
- [ ] Hygiene report API endpoint

---

## Feature 85.6: Extraction Metrics (Log + LangGraph State) (2 SP)

### Description
Output extraction metrics to structured logs AND LangGraph state for observability.

### Metrics Schema

```python
# src/components/graph_rag/extraction_metrics.py

@dataclass
class ExtractionMetrics:
    """Extraction quality and performance metrics."""

    # Entity metrics
    entities_spacy: int = 0
    entities_llm: int = 0
    entities_total: int = 0

    # Relation metrics
    relations_initial: int = 0
    relations_gleaning: int = 0
    relations_total: int = 0

    # Quality metrics
    relation_ratio: float = 0.0      # relations / entities
    typed_coverage: float = 0.0      # typed / total relations
    duplication_rate: float = 0.0    # duplicates / total

    # Performance metrics (ms)
    spacy_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    gleaning_latency_ms: float = 0.0
    total_latency_ms: float = 0.0

    # SpaCy languages used
    languages_detected: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dict for logging/state."""
        return asdict(self)
```

### Structured Logging

```python
def log_extraction_metrics(metrics: ExtractionMetrics, document_id: str):
    """Log extraction metrics in structured format."""
    logger.info(
        "extraction_metrics",
        document_id=document_id,
        **metrics.to_dict()
    )
```

### LangGraph State Integration

```python
# src/components/ingestion/ingestion_state.py

class IngestionState(TypedDict):
    """LangGraph state for ingestion pipeline."""

    document_id: str
    chunks: list[dict]
    entities: list[dict]
    relations: list[dict]

    # NEW: Extraction metrics (merged from all chunks)
    extraction_metrics: ExtractionMetrics | None
```

### State Merge Function

```python
def merge_extraction_metrics(
    existing: ExtractionMetrics | None,
    new: ExtractionMetrics
) -> ExtractionMetrics:
    """Merge extraction metrics from multiple chunks."""
    if existing is None:
        return new

    return ExtractionMetrics(
        entities_spacy=existing.entities_spacy + new.entities_spacy,
        entities_llm=existing.entities_llm + new.entities_llm,
        entities_total=existing.entities_total + new.entities_total,
        relations_initial=existing.relations_initial + new.relations_initial,
        relations_gleaning=existing.relations_gleaning + new.relations_gleaning,
        relations_total=existing.relations_total + new.relations_total,
        relation_ratio=(existing.relations_total + new.relations_total) /
                       max(1, existing.entities_total + new.entities_total),
        spacy_latency_ms=existing.spacy_latency_ms + new.spacy_latency_ms,
        llm_latency_ms=existing.llm_latency_ms + new.llm_latency_ms,
        gleaning_latency_ms=existing.gleaning_latency_ms + new.gleaning_latency_ms,
        total_latency_ms=existing.total_latency_ms + new.total_latency_ms,
        languages_detected=list(set(existing.languages_detected + new.languages_detected)),
    )
```

### Acceptance Criteria

- [ ] ExtractionMetrics dataclass
- [ ] Structured logging with all metrics
- [ ] LangGraph state integration
- [ ] Merge function for chunk-level aggregation
- [ ] Languages detected included (DE/EN/FR/ES)

---

## Feature 85.7: DSPy Training Data Collection (3 SP)

### Description
Collect high-quality training data during extraction for future DSPy optimization.

### DSPy Training Data Requirements

Based on existing `dspy_optimizer.py`:

```python
# Entity extraction training data
entity_training_sample = {
    "text": str,                    # Source text
    "entities": list[str],          # Entity names (not full objects)
}

# Relation extraction training data
relation_training_sample = {
    "text": str,                    # Source text
    "entities": list[str],          # Entity names
    "relations": list[dict],        # [{"subject": str, "predicate": str, "object": str}]
}
```

### Enhanced Training Sample Schema

```python
# src/components/domain_training/training_data_collector.py

@dataclass
class DSPyTrainingSample:
    """Training sample for DSPy optimization."""

    # Core fields (required by dspy_optimizer.py)
    text: str
    entities: list[str]
    relations: list[dict]  # [{"subject": str, "predicate": str, "object": str}]

    # Metadata for stratification
    doc_type: str                   # pdf_text, docx, table, code_config, etc.
    language: str                   # de, en, fr, es
    extraction_source: str          # "validated_llm", "manual", "high_confidence"

    # Quality indicators
    entity_confidence: float        # Average confidence
    relation_confidence: float      # Average confidence
    evidence_coverage: float        # % of relations with evidence spans

    # Provenance
    document_id: str
    chunk_id: str
    domain: str | None
    timestamp: datetime
```

### Collection During Extraction

```python
class TrainingDataCollector:
    """Collect training data during extraction."""

    def __init__(
        self,
        min_entity_confidence: float = 0.8,
        min_relation_confidence: float = 0.7,
        min_evidence_coverage: float = 0.8
    ):
        self.min_entity_confidence = min_entity_confidence
        self.min_relation_confidence = min_relation_confidence
        self.min_evidence_coverage = min_evidence_coverage
        self.samples: list[DSPyTrainingSample] = []

    def collect(
        self,
        text: str,
        entities: list[GraphEntity],
        relations: list[GraphRelationship],
        metadata: dict
    ) -> DSPyTrainingSample | None:
        """Collect sample if quality thresholds met."""

        # Calculate quality metrics
        avg_entity_conf = sum(e.confidence for e in entities) / max(1, len(entities))
        avg_rel_conf = sum(r.confidence for r in relations) / max(1, len(relations))
        evidence_coverage = sum(1 for r in relations if r.evidence_span) / max(1, len(relations))

        # Check quality thresholds
        if avg_entity_conf < self.min_entity_confidence:
            return None
        if avg_rel_conf < self.min_relation_confidence:
            return None
        if evidence_coverage < self.min_evidence_coverage:
            return None

        # Convert to DSPy format
        sample = DSPyTrainingSample(
            text=text,
            entities=[e.name for e in entities],
            relations=[
                {"subject": r.source, "predicate": r.type, "object": r.target}
                for r in relations
            ],
            doc_type=metadata.get("doc_type", "unknown"),
            language=metadata.get("language", "en"),
            extraction_source="validated_llm",
            entity_confidence=avg_entity_conf,
            relation_confidence=avg_rel_conf,
            evidence_coverage=evidence_coverage,
            document_id=metadata.get("document_id"),
            chunk_id=metadata.get("chunk_id"),
            domain=metadata.get("domain"),
            timestamp=datetime.now(),
        )

        self.samples.append(sample)
        return sample

    def export_to_jsonl(self, path: Path) -> int:
        """Export samples to JSONL for DSPy training."""
        count = 0
        with open(path, "w") as f:
            for sample in self.samples:
                # DSPy format (entity extraction)
                entity_sample = {
                    "text": sample.text,
                    "entities": sample.entities,
                }
                f.write(json.dumps(entity_sample) + "\n")

                # DSPy format (relation extraction)
                relation_sample = {
                    "text": sample.text,
                    "entities": sample.entities,
                    "relations": sample.relations,
                }
                f.write(json.dumps(relation_sample) + "\n")
                count += 1

        return count
```

### Target Corpus (Stratified)

```yaml
training_corpus:
  total_samples: 500

  by_doc_type:
    pdf_text: 100 (20%)
    pdf_ocr: 75 (15%)
    docx: 75 (15%)
    table: 75 (15%)
    code_config: 75 (15%)
    slides: 50 (10%)
    tickets_logs: 50 (10%)

  by_language:
    de: 300 (60%)
    en: 150 (30%)
    fr: 25 (5%)
    es: 25 (5%)
```

### Acceptance Criteria

- [ ] DSPyTrainingSample matches dspy_optimizer.py requirements
- [ ] Collection with quality thresholds
- [ ] Export to JSONL format
- [ ] Stratification by doc_type and language
- [ ] Integration with ingestion pipeline

---

## SpaCy Languages

The `HybridExtractionService` already supports **4 languages**:

```python
# src/components/graph_rag/hybrid_extraction_service.py:41

SPACY_MODELS = {
    "de": "de_core_news_lg",  # German
    "en": "en_core_web_lg",   # English
    "fr": "fr_core_news_lg",  # French
    "es": "es_core_news_lg",  # Spanish
}
```

**All 4 languages are available and should be used.** The language is auto-detected or can be specified.

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| Admin API | `src/api/v1/admin_extraction.py` | Cascade configuration endpoints |
| Admin UI | `frontend/src/components/admin/CascadeConfig.tsx` | Cascade editor |
| Domain Integration | `src/components/graph_rag/extraction_service.py` | Domain prompt loading |
| Gleaning Config | `src/config/gleaning_config.py` | Enhanced gleaning guardrails |
| Canonicalization | `src/components/graph_rag/entity_canonicalization.py` | Entity normalization |
| KG Hygiene | `src/components/graph_rag/kg_hygiene.py` | Deduplication & validation |
| Metrics | `src/components/graph_rag/extraction_metrics.py` | Quality tracking |
| DSPy Collector | `src/components/domain_training/training_data_collector.py` | Training data |

---

## Success Criteria

- [ ] Relation Ratio ≥ 0.8 (vs 0.27-0.61 baseline)
- [ ] Typed Coverage ≥ 50%
- [ ] Duplication Rate ≤ 10%
- [ ] Admin UI cascade configuration working
- [ ] Domain prompts integrated
- [ ] All Multi-Format Tests pass
- [ ] 80+ unit tests passing

---

## References

- [Neo4j: Entity Resolved Knowledge Graphs](https://neo4j.com/blog/developer/entity-resolved-knowledge-graphs/)
- [Neo4j: Under the Covers With LightRAG](https://neo4j.com/blog/developer/under-the-covers-with-lightrag-extraction/)
- [LlamaIndex: Customizing Property Graph Index](https://www.llamaindex.ai/blog/customizing-property-graph-index-in-llamaindex)
- [Microsoft GraphRAG](https://microsoft.github.io/graphrag/)
- [TD-102: Relation Extraction Improvement](../technical-debt/TD-102_RELATION_EXTRACTION_IMPROVEMENT.md)

---

**Previous Sprint:** Sprint 84 (Stabilization & Iterative Ingestion)
**Next Sprint:** Sprint 86 (DSPy MIPROv2 Optimization)
