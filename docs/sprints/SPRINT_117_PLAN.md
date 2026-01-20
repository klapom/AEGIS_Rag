# Sprint 117 Plan: Domain Training API & Features

**Date:** 2026-01-20
**Status:** Planned
**Epic:** Domain Training System Completion
**Total Story Points:** 61 SP

---

## Sprint Overview

Sprint 117 focuses on implementing the complete Domain Training API and supporting features identified from E2E test skipped tests (Sprint 116 analysis). This is **Phase 2 of Domain Management**, building on the foundation established in previous sprints.

**Objective:** Deliver production-ready domain management with classification, auto-discovery, data augmentation, and batch ingestion capabilities.

### Key Metrics
- **Test Coverage:** 50+ new E2E tests (currently skipped)
- **API Endpoints:** 9 new domain management endpoints
- **Frontend Features:** Domain training UI, classification widgets, discovery wizard
- **Integration Points:** LLM-based entity extraction, batch document processing
- **Performance Target:** Domain operations <500ms p95 (excluding LLM inference time)

---

## Feature Breakdown (61 SP Total)

### 1. Domain Training API - CRUD Operations (13 SP)

**Sprint Feature:** 117.1

**Objective:** Establish foundational domain management endpoints with full CRUD operations.

#### Backend Requirements

**Endpoints:**
```
GET  /api/v1/admin/domains/
POST /api/v1/admin/domains/
GET  /api/v1/admin/domains/{name}
PUT  /api/v1/admin/domains/{name}
DELETE /api/v1/admin/domains/{name}
```

**Data Model:**
```python
class DomainSchema(BaseModel):
    id: str                           # UUID primary key
    name: str                         # Domain name (unique, lowercase, max 50 chars)
    description: str                  # Domain description (max 500 chars)
    training_samples: int             # Count of labeled training samples
    entity_types: List[str]          # Custom entity types (e.g., ["Disease", "Symptom"])
    relation_types: List[str]        # Custom relation types (MENTIONED_IN always included)
    intent_classes: List[str]        # Intent classes for domain-specific classification
    model_family: str                # "general", "medical", "legal", "technical", "finance"
    confidence_threshold: float      # Min confidence for auto-extraction (0.0-1.0)
    created_at: datetime
    updated_at: datetime
    created_by: str                  # User ID
    status: Literal["active", "training", "inactive"]
    training_progress: Optional[int] # 0-100 during training
    metrics: Optional[Dict[str, float]]  # RAGAS metrics when available
```

**Standard Relation Types (immer enthalten):**
```python
REQUIRED_RELATION_TYPES = [
    "MENTIONED_IN",  # Entity → ChunkID (Provenienz, KRITISCH für Citations!)
]
```
> ⚠️ **MENTIONED_IN ist PFLICHT** - Ohne diese Relation fehlt der Verweis von Entities auf ihre Source-Chunks (ChunkIDs). Das bricht Citations, Explainability und RAGAS Context Recall.

**Validation Rules:**
- Domain name: alphanumeric + hyphens, unique, 3-50 characters
- Description: max 500 characters
- Entity types: 1-20 types, each 5-50 characters
- Relation types: 1-20 types, each 5-50 characters (MENTIONED_IN automatisch hinzugefügt)
- Confidence threshold: 0.0-1.0 (default 0.5)
- Model family: must be from predefined list

**Response Schemas:**

Domain List Response (GET /api/v1/admin/domains/):
```json
{
  "domains": [
    {
      "id": "domain_abc123",
      "name": "medical",
      "description": "Medical domain with disease and symptom extraction",
      "training_samples": 1247,
      "entity_types": ["Disease", "Symptom", "Treatment"],
      "relation_types": ["TREATS", "CAUSES", "SYMPTOM_OF"],
      "status": "active",
      "created_at": "2026-01-15T10:30:00Z",
      "model_family": "medical"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

Domain Details Response (GET /api/v1/admin/domains/{name}):
```json
{
  "id": "domain_abc123",
  "name": "medical",
  "description": "Medical domain with disease and symptom extraction",
  "training_samples": 1247,
  "entity_types": ["Disease", "Symptom", "Treatment"],
  "relation_types": ["TREATS", "CAUSES", "SYMPTOM_OF"],
  "intent_classes": ["inquiry", "symptom_report", "treatment_request"],
  "model_family": "medical",
  "confidence_threshold": 0.6,
  "status": "active",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-20T14:22:00Z",
  "created_by": "user_admin",
  "metrics": {
    "faithfulness": 0.87,
    "context_recall": 0.92,
    "context_precision": 0.89,
    "answer_relevancy": 0.91
  }
}
```

Create Domain Request (POST /api/v1/admin/domains/):
```json
{
  "name": "finance",
  "description": "Financial domain with accounting and stock data",
  "entity_types": ["Company", "StockTicker", "Currency", "Amount"],
  "relation_types": ["LISTED_ON", "FUNDED_BY", "TRADED_AT"],
  "intent_classes": ["price_query", "earnings_query", "investment_advice"],
  "model_family": "finance",
  "confidence_threshold": 0.7
}
```

**Error Handling:**
- 400: Validation error (duplicate name, invalid types, missing fields)
- 404: Domain not found
- 409: Domain already exists
- 422: Schema validation failed

#### Frontend Requirements

**Components:**
- `DomainList` - Display all domains with pagination
- `DomainCard` - Individual domain card with metadata
- `CreateDomainModal` - Wizard-style domain creation form
- `DomainDetailsView` - Full domain details with edit capability

**Features:**
- List domains with sorting (by name, creation date, samples)
- Filter by status (active/training/inactive)
- Pagination (20 domains per page)
- Quick search by domain name
- Create new domain with validation
- Edit domain details (description, thresholds)
- Delete domain with confirmation
- Display training progress when status="training"

**Test Coverage (E2E):**
- TC-117.1.1: List domains with pagination
- TC-117.1.2: Create domain with valid input
- TC-117.1.3: Reject invalid domain names
- TC-117.1.4: Edit domain details
- TC-117.1.5: Delete domain with confirmation
- TC-117.1.6: Display 404 for non-existent domain

#### Implementation Tasks
1. Create `DomainSchema` Pydantic models (src/core/models/domain.py)
2. Implement domain database layer (src/domains/knowledge_graph/domain_store.py)
3. Create FastAPI endpoints (src/api/v1/admin/domains.py)
4. Add comprehensive input validation
5. Implement error handling and logging
6. Create frontend components (React/TypeScript)
7. Add E2E tests to verify all operations
8. Database migrations for domain storage

**Acceptance Criteria:**
- [ ] All CRUD endpoints return correct HTTP status codes
- [ ] Domain validation rejects invalid inputs with helpful error messages
- [ ] Domains persist correctly in Neo4j/PostgreSQL
- [ ] Frontend can list, create, edit, and delete domains
- [ ] All E2E tests pass (TC-117.1.1 through TC-117.1.6)
- [ ] Comprehensive logging for debugging
- [ ] Documentation complete in API docs

---

### 2. Domain Classification - C-LARA Hybrid (8 SP)

**Sprint Feature:** 117.2

**Objective:** Implement hybrid document-to-domain classification using C-LARA SetFit fast classifier with optional LLM verification/enrichment.

**Architecture Decision:** Two-stage "C-LARA Candidate Generator + LLM Verifier" pattern:
- **Stage A (Fast):** C-LARA SetFit classifier (~40ms) provides top_k candidates with confidence
- **Stage B (Optional):** LLM enriches reasoning/entities only when needed

#### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Document Input                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Stage A: C-LARA SetFit Classifier              │
│                      (~40ms, local)                          │
│   Output: top_k candidates + confidence + evidence_chunks    │
└─────────────────────────┬───────────────────────────────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
     conf ≥ 0.85    0.60-0.85     conf < 0.60
              │           │           │
              ▼           ▼           ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│   Fast Return   │ │ LLM Verify Top-K│ │ LLM Fallback (All)  │
│  - ~40ms total  │ │  - ~500ms total │ │  - ~2-5s total      │
│  - No LLM cost  │ │  - $0.005       │ │  - $0.02            │
│  - 70-80% cases │ │  - 15-25% cases │ │  - 5-10% cases      │
└─────────────────┘ └─────────────────┘ └─────────────────────┘
```

**Expected Performance:**
| Path | Confidence | Latency | LLM Cost | Frequency |
|------|------------|---------|----------|-----------|
| Fast | ≥ 0.85 | ~40ms | $0 | ~70-80% |
| Verified | 0.60-0.85 | ~500ms | ~$0.005 | ~15-25% |
| Fallback | < 0.60 | ~2-5s | ~$0.02 | ~5-10% |

**Average:** ~150ms latency, ~$0.002/classification (vs ~3s, ~$0.02 pure LLM)

#### Backend Requirements

**Endpoint:**
```
POST /api/v1/admin/domains/classify
```

**Request Schema:**
```json
{
  "document_text": "The patient presents with elevated blood pressure and chest pain. Treatment options include ACE inhibitors...",
  "document_id": "doc_abc123",
  "chunk_ids": ["chunk_1", "chunk_2"],
  "top_k": 3,
  "threshold": 0.5,
  "force_llm": false
}
```

**Response Schema:**
```json
{
  "document_id": "doc_abc123",
  "domain_id": "medical",
  "domain_name": "medical",
  "confidence": 0.94,
  "reasoning": "Document contains medical terminology (blood pressure, ACE inhibitors) and clinical assessment format.",
  "matched_entity_types": ["Disease", "Treatment"],
  "matched_intent": "symptom_report",
  "classification_path": "fast",
  "latency_ms": 42,
  "candidates": [
    {"domain": "medical", "confidence": 0.94},
    {"domain": "general", "confidence": 0.15},
    {"domain": "legal", "confidence": 0.08}
  ],
  "model_used": "C-LARA-SetFit-v2"
}
```

**LangGraph State:**
```python
class DomainClassificationState(TypedDict):
    # Input
    document_text: str
    document_id: str
    chunk_ids: List[str]

    # Stage A: C-LARA Output
    candidates: List[DomainCandidate]
    max_confidence: float
    classifier_latency_ms: int

    # Stage B: LLM Enrichment (optional)
    needs_llm_verification: bool
    reasoning: Optional[str]
    matched_entity_types: List[str]
    matched_intent: Optional[str]

    # Final Output
    final_domain: Optional[str]
    final_confidence: float
    classification_path: Literal["fast", "verified", "fallback"]
    total_latency_ms: int
```

**LangGraph Nodes:**
1. `classify_clara` - C-LARA SetFit classification (~40ms)
2. `fast_return` - Direct return for high confidence (≥0.85)
3. `llm_verify_top_k` - LLM enriches top-3 candidates (0.60-0.85)
4. `llm_fallback_all_domains` - Full LLM comparison (<0.60)

**Conditional Routing:**
```python
def route_by_confidence(state: DomainClassificationState) -> str:
    conf = state["max_confidence"]
    if conf >= 0.85:
        return "fast_return"      # No LLM needed
    elif conf >= 0.60:
        return "llm_verify"       # LLM verifies top-k only
    else:
        return "llm_fallback"     # Full LLM comparison
```

#### C-LARA Training Pipeline

**Training New Domains:**
```python
class DomainClassifierTrainer:
    min_samples_per_domain = 20      # Minimum positive examples
    negative_ratio = 0.3             # 30% hard negatives

    async def train_new_domain(
        self,
        domain_id: str,
        positive_examples: List[str],
        hard_negatives: Optional[List[str]] = None,
    ) -> TrainingResult:
        # 1. Validate minimum samples (20-100 recommended)
        # 2. Load existing training data (retrain all classes)
        # 3. Balance classes (handle class imbalance)
        # 4. Train SetFit model (contrastive learning)
        # 5. Calibrate confidence (isotonic regression)
        # 6. Save model
```

**Training Guardrails:**
- **Minimum samples:** 20-100 positive examples per domain
- **Hard negatives:** Include semantically similar but incorrect examples
- **Catastrophic forgetting mitigation:** Retrain all classes together
- **Class imbalance:** Balanced sampling with oversampling minorities
- **Confidence calibration:** Temperature scaling / isotonic regression

#### Frontend Requirements

**Components:**
- `DocumentClassifier` - Text input area for document classification
- `ClassificationResults` - Display classification results with confidence bars
- `ClassificationPathBadge` - Shows "Fast ⚡" / "Verified ✓" / "Full 🔍"
- `CandidatesList` - Show all candidate domains with confidences

**Features:**
- Text input area with character counter (max 10,000 chars)
- Real-time validation
- Submit for classification
- Display results with confidence scores (as progress bars)
- Show classification path badge (Fast/Verified/Fallback)
- Show reasoning for top classification
- Show entity type matches
- Batch classification UI (upload CSV with documents)
- Copy results to clipboard
- `force_llm` toggle for A/B testing

**Test Coverage (E2E):**
- TC-117.2.1: Classify medical document to "medical" domain (fast path)
- TC-117.2.2: Classify finance document to "finance" domain (fast path)
- TC-117.2.3: Handle ambiguous document (verified path with LLM enrichment)
- TC-117.2.4: Reject empty input with validation error
- TC-117.2.5: Display confidence scores and classification path correctly
- TC-117.2.6: Batch classification processes multiple documents
- TC-117.2.7: force_llm=true bypasses C-LARA (for comparison testing)
- TC-117.2.8: Low confidence triggers fallback path

#### Implementation Tasks
1. Create C-LARA domain classifier model (`src/domains/llm_integration/clara/domain_classifier.py`)
2. Create LangGraph classification graph (`src/agents/domain_classifier/graph.py`)
3. Implement classification state (`src/agents/domain_classifier/state.py`)
4. Add confidence-based routing logic
5. Implement LLM verification node (top-k only)
6. Implement fallback node (original O(n) behavior)
7. Create training pipeline (`src/domains/llm_integration/clara/domain_trainer.py`)
8. Implement API endpoint with `force_llm` query param
9. Create React components with path badges
10. Add E2E tests for all three paths
11. Performance benchmarking (fast vs verified vs fallback)

**Acceptance Criteria:**
- [ ] Classification endpoint returns correct domain with confidence
- [ ] Fast path (≥0.85 confidence) completes in <50ms
- [ ] Verified path (0.60-0.85) completes in <600ms
- [ ] Fallback path (<0.60) completes in <5s
- [ ] Reasoning explains classification decision (verified/fallback paths)
- [ ] `force_llm=true` bypasses C-LARA for A/B testing
- [ ] Frontend displays classification path badge correctly
- [ ] Batch classification processes 100 documents efficiently
- [ ] New domain training requires 20+ samples
- [ ] All E2E tests pass (TC-117.2.1 through TC-117.2.8)
- [ ] Logging includes classification path, latency, and confidence

---

### 3. Domain Auto-Discovery (8 SP)

**Sprint Feature:** 117.3

**Objective:** Automatically discover and suggest domain configurations from sample documents.

#### Backend Requirements

**Endpoint:**
```
POST /api/v1/admin/domains/discover
```

**Request Schema:**
```json
{
  "sample_documents": [
    "Patient with Type 2 diabetes presenting with elevated fasting glucose...",
    "The stock price of AAPL increased 3% on strong earnings report...",
    "COVID-19 treatment protocols updated by WHO..."
  ],
  "min_samples": 3,
  "max_samples": 10,
  "suggested_count": 5
}
```

**Response Schema:**
```json
{
  "discovered_domains": [
    {
      "name": "medical",
      "suggested_description": "Medical domain covering diseases, treatments, and clinical terminology",
      "confidence": 0.92,
      "entity_types": ["Disease", "Symptom", "Treatment", "Medication", "Test"],
      "relation_types": ["TREATS", "CAUSES", "DIAGNOSED_WITH", "PRESCRIBED"],
      "intent_classes": ["symptom_inquiry", "treatment_request", "diagnosis_query"],
      "sample_entities": {
        "Disease": ["diabetes", "COVID-19"],
        "Treatment": ["insulin therapy", "treatment protocols"]
      },
      "reasoning": "Samples contain clinical language, medical terminology, and healthcare entities"
    },
    {
      "name": "finance",
      "suggested_description": "Financial domain for stock prices, earnings, and market data",
      "confidence": 0.87,
      "entity_types": ["Company", "StockTicker", "Currency", "Amount"],
      "relation_types": ["LISTED_ON", "TRADED_AT", "EARNINGS_FROM"],
      "intent_classes": ["price_inquiry", "earnings_query"],
      "sample_entities": {
        "StockTicker": ["AAPL"],
        "Amount": ["3%"]
      },
      "reasoning": "Samples reference stock tickers, earnings reports, and financial metrics"
    }
  ],
  "general_info": {
    "total_samples_analyzed": 3,
    "unique_entities_found": 45,
    "languages_detected": ["English"],
    "processing_time_ms": 1247
  }
}
```

**Implementation Details:**
- Analyze 3-10 sample documents
- Extract entities using C-LARA or pure LLM pipeline
- Cluster entities by semantic similarity
- Suggest domain names based on entity clusters
- Generate descriptions and suggested configurations
- Return confidence scores for each discovered domain
- Provide entity samples as evidence

**Multi-Step Process:**
1. Extract entities from all samples (Entity Extraction Agent)
2. Cluster entities semantically (Graph Analysis)
3. Suggest domain names based on clusters (LLM)
4. Generate entity/relation types for each domain (LLM)
5. Format and return suggestions

#### Frontend Requirements

**Components:**
- `DomainDiscoveryWizard` - Multi-step discovery flow
- `DocumentUploadArea` - Drag-drop file upload (TXT, MD, DOCX, PDF)
- `DiscoveryResults` - Display suggested domains with details
- `DomainPreview` - Preview discovered domain configuration

**Features:**
- Upload 3-10 sample documents
- Real-time analysis status with progress
- Display discovered domains ranked by confidence
- Show entity type suggestions with samples
- Show relation type suggestions
- One-click domain creation from suggestion
- Edit suggested configuration before creating
- Download domain config as JSON

**Test Coverage (E2E):**
- TC-117.3.1: Upload 3 sample documents
- TC-117.3.2: Discover domains from samples
- TC-117.3.3: Display suggested entity/relation types
- TC-117.3.4: Reject <3 or >10 samples
- TC-117.3.5: Create domain from suggestion
- TC-117.3.6: Edit suggestion before creation

#### Implementation Tasks
1. Create Discovery Agent (src/agents/domain_discovery_agent.py)
2. Implement entity clustering logic (src/components/knowledge_graph/entity_clustering.py)
3. Create discovery endpoint (src/api/v1/admin/domains/discover.py)
4. Add LLM prompts for domain name/type suggestions
5. Create React components for wizard flow
6. Add file upload handling (PDF, DOCX support)
7. Add E2E tests
8. Performance optimization for large documents

**Acceptance Criteria:**
- [ ] Auto-discovery from 3-10 samples completes <2s (excluding LLM)
- [ ] Suggested entity types match document content
- [ ] Confidence scores reflect discovery quality
- [ ] Frontend wizard guides users through discovery
- [ ] One-click domain creation works from suggestions
- [ ] All E2E tests pass
- [ ] Error handling for unsupported file types
- [ ] Comprehensive logging of discovery process

---

### 4. Domain Data Augmentation (8 SP)

**Sprint Feature:** 117.4

**Objective:** Generate synthetic training data from seed samples to augment domain datasets.

#### Backend Requirements

**Endpoint:**
```
POST /api/v1/admin/domains/augment
```

**Request Schema:**
```json
{
  "domain_name": "medical",
  "seed_samples": [
    {
      "text": "Patient with Type 2 diabetes and hypertension",
      "entities": [
        {"text": "Type 2 diabetes", "type": "Disease", "start": 17, "end": 33},
        {"text": "hypertension", "type": "Disease", "start": 38, "end": 50}
      ],
      "relations": [
        {"source": "Type 2 diabetes", "target": "hypertension", "type": "CO_OCCURS_WITH"}
      ]
    }
  ],
  "target_count": 100,
  "augmentation_strategy": "paraphrase_and_vary",
  "temperature": 0.7
}
```

**Response Schema:**
```json
{
  "augmentation_job_id": "aug_job_xyz789",
  "domain_name": "medical",
  "seed_count": 5,
  "target_count": 100,
  "generated_count": 98,
  "status": "completed",
  "generation_summary": {
    "paraphrases": 45,
    "entity_substitutions": 30,
    "back_translations": 18,
    "synthetic_documents": 5
  },
  "quality_metrics": {
    "diversity_score": 0.87,
    "entity_coverage": 0.94,
    "relation_coverage": 0.89,
    "duplicate_rate": 0.02
  },
  "sample_outputs": [
    {
      "text": "A patient suffering from type II diabetes mellitus combined with high blood pressure",
      "entities": [
        {"text": "type II diabetes mellitus", "type": "Disease"},
        {"text": "high blood pressure", "type": "Disease"}
      ],
      "source_seed": "seed_001",
      "generation_method": "paraphrase"
    }
  ],
  "created_at": "2026-01-20T15:30:00Z",
  "completed_at": "2026-01-20T15:35:42Z",
  "processing_time_ms": 342000
}
```

**Augmentation Strategies:**
1. **Paraphrase & Vary** (default): Rephrase sentences while preserving entities/relations
2. **Entity Substitution**: Replace entities with synonyms/similar types
3. **Back Translation**: Translate to another language and back
4. **Synthetic Generation**: Generate new documents from entity/relation patterns
5. **Hybrid**: Combination of above strategies

**Implementation Details:**
- Use LLM for paraphrasing and generation
- Preserve entity and relation annotations during augmentation
- Validate generated samples match domain schema
- Support async job processing for large augmentations
- Track diversity to avoid near-duplicates
- Store augmented samples in domain dataset

**Multi-Step Process:**
1. Validate seed samples (entity types, relations)
2. Select augmentation strategies based on target count
3. Generate paraphrases/variations
4. Validate generated samples against domain schema
5. Filter near-duplicates (similarity >0.95)
6. Return augmented dataset with quality metrics

#### Frontend Requirements

**Components:**
- `AugmentationWizard` - Multi-step augmentation flow
- `SeedSampleInput` - Input area for seed samples
- `AugmentationConfig` - Strategy and parameter selection
- `AugmentationResults` - Display generated samples and metrics

**Features:**
- Input seed samples with entity annotation
- Select augmentation strategy
- Set target augmentation count
- Real-time progress indicator
- Display generation results with quality scores
- Preview sample augmentations
- Download augmented dataset as JSON/CSV
- Validate before adding to domain

**Test Coverage (E2E):**
- TC-117.4.1: Start augmentation with seed samples
- TC-117.4.2: Display generation progress
- TC-117.4.3: Show augmentation results with metrics
- TC-117.4.4: Generate 100 samples from 5 seeds
- TC-117.4.5: Reject invalid domain name
- TC-117.4.6: Download augmented dataset

#### Implementation Tasks
1. Create Augmentation Agent (src/agents/data_augmentation_agent.py)
2. Implement augmentation strategies (src/components/data_augmentation/*.py)
3. Create augmentation endpoint (src/api/v1/admin/domains/augment.py)
4. Add background job processing (Celery or similar)
5. Create React components for augmentation wizard
6. Add sample validation and filtering
7. Add E2E tests
8. Quality metrics calculation and reporting

**Acceptance Criteria:**
- [ ] Generate 100 augmented samples from 5 seeds in <1 minute
- [ ] Preserve entity annotations in augmented samples
- [ ] Diversity score >0.85 (low duplication)
- [ ] Entity coverage >0.90 (most entity types included)
- [ ] Frontend displays progress and results clearly
- [ ] Download augmented dataset works
- [ ] All E2E tests pass
- [ ] Job tracking and error handling for failed augmentations

---

### 5. Domain Batch Ingestion (8 SP)

**Sprint Feature:** 117.5

**Objective:** Ingest and route multiple documents to appropriate domains in batch.

#### Backend Requirements

**Endpoint:**
```
POST /api/v1/admin/domains/ingest-batch
```

**Request Schema:**
```json
{
  "documents": [
    {
      "file_id": "file_001",
      "content": "Patient with Type 2 diabetes...",
      "filename": "patient_report.txt",
      "suggested_domain": "medical",
      "metadata": {
        "source": "hospital_system",
        "date_created": "2026-01-20"
      }
    },
    {
      "file_id": "file_002",
      "content": "Stock AAPL rose 3% on earnings...",
      "filename": "market_news.txt",
      "suggested_domain": null,
      "metadata": {
        "source": "news_feed",
        "date_created": "2026-01-20"
      }
    }
  ],
  "batch_name": "daily_ingestion_2026_01_20",
  "auto_classify_missing": true,
  "namespace": "medical_training_v1"
}
```

**Response Schema:**
```json
{
  "batch_id": "batch_xyz789",
  "batch_name": "daily_ingestion_2026_01_20",
  "status": "processing_background",
  "total_documents": 2,
  "processing_results": {
    "ingested": 2,
    "failed": 0,
    "skipped": 0
  },
  "documents": [
    {
      "file_id": "file_001",
      "filename": "patient_report.txt",
      "document_id": "doc_abc123",
      "assigned_domain": "medical",
      "status": "ingested",
      "chunks_created": 3,
      "entities_extracted": 8,
      "processing_time_ms": 245
    },
    {
      "file_id": "file_002",
      "filename": "market_news.txt",
      "document_id": "doc_def456",
      "assigned_domain": "finance",
      "classification_confidence": 0.91,
      "status": "ingested",
      "chunks_created": 2,
      "entities_extracted": 5,
      "processing_time_ms": 312
    }
  ],
  "batch_stats": {
    "total_chunks": 5,
    "total_entities": 13,
    "total_relations": 7,
    "processing_time_ms": 2847,
    "estimated_completion": "2026-01-20T16:15:00Z"
  },
  "message": "Batch ingestion started. Processing in background..."
}
```

**Implementation Details:**
- Accept up to 100 documents per batch
- Auto-classify documents to domain if not provided
- Route documents to appropriate domain pipelines
- Extract entities using domain-specific configuration
- Create chunks with domain context
- Support async processing for large batches
- Return job ID for progress tracking
- Provide batch statistics and per-document status

**Multi-Step Process:**
1. Validate batch request and documents
2. For each document without domain, auto-classify
3. Route documents to domain-specific ingestion pipelines
4. Extract entities using domain entity types
5. Create chunks with domain context
6. Store in Qdrant (with domain_name metadata)
7. Update Neo4j with domain-specific graph
8. Return batch results

#### Frontend Requirements

**Components:**
- `BatchIngestionWizard` - Multi-step ingestion flow
- `DocumentUploadArea` - Drag-drop file upload for multiple files
- `BatchPreview` - Preview documents and assigned domains
- `BatchProgress` - Real-time ingestion progress
- `BatchResults` - Summary of ingestion results

**Features:**
- Upload multiple documents (CSV, JSON, or file upload)
- Preview documents and assigned domains
- Manual domain assignment if auto-classification uncertain
- Real-time progress with status per document
- Download batch report (JSON/CSV)
- Retry failed documents
- View entity extraction results per document
- Bulk operations (re-ingest, update metadata)

**Test Coverage (E2E):**
- TC-117.5.1: Upload batch of 10 documents
- TC-117.5.2: Auto-classify documents to domains
- TC-117.5.3: Ingest batch successfully
- TC-117.5.4: Display batch progress in real-time
- TC-117.5.5: Show per-document status and errors
- TC-117.5.6: Download batch results
- TC-117.5.7: Retry failed document ingestion

#### Implementation Tasks
1. Create Batch Ingestion Agent (src/agents/batch_ingestion_agent.py)
2. Implement batch endpoint (src/api/v1/admin/domains/ingest_batch.py)
3. Create domain routing logic
4. Add background job processing
5. Create React components for batch ingestion UI
6. Add progress tracking and job status API
7. Add E2E tests
8. Error handling and retry logic

**Acceptance Criteria:**
- [ ] Ingest batch of 100 documents in <5 minutes
- [ ] Documents routed to correct domains with >0.90 accuracy
- [ ] Entity extraction respects domain entity types
- [ ] Real-time progress updates via WebSocket/polling
- [ ] Failed documents can be retried
- [ ] Batch results can be downloaded
- [ ] All E2E tests pass
- [ ] Comprehensive logging for troubleshooting

---

### 6. Domain Details & Training Status (5 SP)

**Sprint Feature:** 117.6

**Objective:** Provide detailed domain information and real-time training progress tracking.

#### Backend Requirements

**Endpoints:**
```
GET /api/v1/admin/domains/{name}
GET /api/v1/admin/domains/{name}/training-status
POST /api/v1/admin/domains/{name}/train
```

**Training Status Response:**
```json
{
  "domain_name": "medical",
  "current_status": "training",
  "training_progress": 65,
  "training_started_at": "2026-01-20T14:00:00Z",
  "estimated_completion": "2026-01-20T16:30:00Z",
  "training_metrics": {
    "current": {
      "accuracy": 0.87,
      "precision": 0.89,
      "recall": 0.85,
      "f1_score": 0.87,
      "entity_recall": 0.91,
      "relation_recall": 0.78
    },
    "baseline": {
      "accuracy": 0.82,
      "precision": 0.84,
      "recall": 0.80,
      "f1_score": 0.82
    },
    "improvement": {
      "accuracy": 0.05,
      "precision": 0.05,
      "recall": 0.05,
      "f1_score": 0.05
    }
  },
  "dataset_stats": {
    "training_samples": 1247,
    "original_samples": 500,
    "augmented_samples": 747,
    "validation_samples": 156,
    "test_samples": 156
  },
  "entity_types_count": 12,
  "relation_types_count": 8,
  "latest_logs": [
    {"timestamp": "2026-01-20T15:45:30Z", "level": "INFO", "message": "Training checkpoint 65 saved"},
    {"timestamp": "2026-01-20T15:43:15Z", "level": "INFO", "message": "Batch 130 processed - Loss: 0.234"}
  ]
}
```

**Train Domain Request:**
```json
{
  "strategy": "fine_tune",
  "model_base": "Nemotron3",
  "epochs": 5,
  "batch_size": 32,
  "learning_rate": 0.0001,
  "validation_split": 0.2,
  "early_stopping": true,
  "patience": 3
}
```

#### Frontend Requirements

**Components:**
- `DomainDetailsPanel` - Full domain information display
- `TrainingProgressBar` - Visual training progress with ETA
- `MetricsComparison` - Baseline vs current metrics comparison
- `TrainingLogs` - Real-time training log display

**Features:**
- Display domain metadata (entities, relations, samples)
- Show training progress with time estimate
- Display metrics improvements vs baseline
- Real-time log streaming during training
- Start/stop training
- Download training results and models
- View dataset statistics
- Compare with previous training runs

**Test Coverage (E2E):**
- TC-117.6.1: Get domain details for existing domain
- TC-117.6.2: Display training status while training
- TC-117.6.3: Show metrics improvements
- TC-117.6.4: Update progress in real-time
- TC-117.6.5: Return 404 for non-existent domain
- TC-117.6.6: Display latest training logs

#### Implementation Tasks
1. Extend domain endpoint to include training status
2. Implement training progress tracking
3. Create metrics comparison logic
4. Add real-time log streaming (WebSocket or SSE)
5. Create React components for status display
6. Add progress polling mechanism
7. Add E2E tests
8. Implement checkpoint saving and restoration

**Acceptance Criteria:**
- [ ] Domain details include complete metadata
- [ ] Training status updates in real-time
- [ ] Metrics comparison displays correctly
- [ ] Progress bar accurate within 5%
- [ ] ETA within 10% of actual completion time
- [ ] Training logs update every 5-10 seconds
- [ ] All E2E tests pass
- [ ] Handles training timeouts gracefully

---

### 7. Domain Validation (5 SP)

**Sprint Feature:** 117.7

**Objective:** Comprehensive validation of domain configuration and training samples.

#### Backend Requirements

**Endpoint:**
```
POST /api/v1/admin/domains/{id}/validate
```

**Validation Request:**
```json
{
  "validation_type": "full",
  "check_samples": true,
  "check_entity_types": true,
  "check_relations": true,
  "sample_size": 100
}
```

**Validation Response:**
```json
{
  "domain_id": "domain_abc123",
  "domain_name": "medical",
  "validation_status": "passed_with_warnings",
  "overall_health_score": 0.82,
  "checks": {
    "structure": {
      "status": "passed",
      "message": "Domain structure is valid",
      "details": {
        "entity_types_count": 12,
        "relation_types_count": 8,
        "entity_types_valid": true,
        "relation_types_valid": true
      }
    },
    "samples": {
      "status": "passed_with_warnings",
      "message": "Training samples mostly valid with some issues",
      "details": {
        "total_samples": 1247,
        "valid_samples": 1198,
        "invalid_samples": 49,
        "coverage_score": 0.87,
        "diversity_score": 0.78,
        "issues": [
          {"sample_id": "sample_001", "issue": "Entity type 'Medication' not in domain definition"},
          {"sample_id": "sample_002", "issue": "Relation 'DISCOVERED_BY' not defined"}
        ]
      }
    },
    "entities": {
      "status": "passed",
      "message": "Entity types are well-defined",
      "details": {
        "entity_types": 12,
        "avg_sample_coverage": 0.91,
        "unused_types": [],
        "type_distribution": {"Disease": 0.35, "Treatment": 0.28, "Symptom": 0.22}
      }
    },
    "relations": {
      "status": "passed",
      "message": "Relation types are well-defined",
      "details": {
        "relation_types": 8,
        "avg_relation_count": 2.3,
        "unused_types": [],
        "coverage": 0.89
      }
    },
    "balance": {
      "status": "warning",
      "message": "Dataset may be imbalanced",
      "details": {
        "train_test_split": "0.80/0.20",
        "class_balance": {
          "Disease": 0.35,
          "Treatment": 0.28,
          "Symptom": 0.22
        },
        "recommendations": ["Consider augmenting underrepresented entity types"]
      }
    }
  },
  "recommendations": [
    "Fix entity type mismatches in 49 samples",
    "Augment underrepresented entity types (Symptom)",
    "Review unused entity types"
  ],
  "validation_timestamp": "2026-01-20T16:00:00Z"
}
```

**Validation Checks:**
1. **Structure Validation**: Domain schema completeness
2. **Sample Validation**: Training samples follow schema
3. **Entity Validation**: Entity type coverage and distribution
4. **Relation Validation**: Relation type definitions
5. **Balance Validation**: Dataset class balance
6. **Coverage Validation**: Entity/relation type coverage in samples

#### Frontend Requirements

**Components:**
- `ValidationReport` - Display validation results with status indicators
- `HealthScoreGauge` - Visual health score display
- `IssuesList` - List of found issues with suggestions
- `ValidationRecommendations` - Actionable recommendations

**Features:**
- Run validation checks
- Display health score with visual indicator
- Show per-check status (passed/warning/failed)
- List specific issues with sample IDs
- Provide actionable recommendations
- Export validation report as PDF/JSON
- Schedule periodic validation runs
- Compare validation results over time

**Test Coverage (E2E):**
- TC-117.7.1: Run validation on valid domain
- TC-117.7.2: Display validation results
- TC-117.7.3: Show health score
- TC-117.7.4: List found issues
- TC-117.7.5: Provide recommendations
- TC-117.7.6: Export validation report

#### Implementation Tasks
1. Create validation engine (src/components/domain_validation/validator.py)
2. Implement validation endpoint
3. Add validation check implementations
4. Create issue detection logic
5. Generate recommendations
6. Create React components for report display
7. Add E2E tests
8. Export functionality (PDF, JSON)

**Acceptance Criteria:**
- [ ] Validation completes in <10 seconds for 1000+ samples
- [ ] All check types execute and report status
- [ ] Issues identified with specific locations
- [ ] Recommendations are actionable
- [ ] Health score reflects overall domain quality
- [ ] Report can be exported
- [ ] All E2E tests pass

---

### 8. Domain Response Format Standardization (3 SP)

**Sprint Feature:** 117.8

**Objective:** Standardize response schemas across all domain endpoints for consistency.

#### Requirements

**Standard Envelope:**
```json
{
  "success": true,
  "data": {
    // Endpoint-specific data
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2026-01-20T16:00:00Z",
    "processing_time_ms": 342,
    "api_version": "v1"
  },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "has_more": true
  }
}
```

**Error Envelope:**
```json
{
  "success": false,
  "error": {
    "code": "DOMAIN_NOT_FOUND",
    "message": "Domain 'medical' not found",
    "details": {
      "domain_name": "medical",
      "suggestion": "Available domains: general, finance, legal"
    }
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2026-01-20T16:00:00Z",
    "api_version": "v1"
  }
}
```

**Error Codes:**
```
DOMAIN_NOT_FOUND: 404
DOMAIN_ALREADY_EXISTS: 409
VALIDATION_ERROR: 400
UNAUTHORIZED: 401
INSUFFICIENT_PERMISSIONS: 403
RATE_LIMITED: 429
INTERNAL_ERROR: 500
```

#### Implementation Tasks
1. Create response envelope models (src/core/models/response.py)
2. Create response wrapper utilities
3. Update all domain endpoints to use standard envelope
4. Add error code mappings
5. Update API documentation
6. Add response validation tests

**Acceptance Criteria:**
- [ ] All domain endpoints use standard envelope
- [ ] Error responses include helpful details
- [ ] Pagination info always included for list endpoints
- [ ] Request tracking IDs in all responses
- [ ] Processing time metrics logged
- [ ] API documentation updated
- [ ] All responses validated against schema

---

### 9. Domain Default Seeding (3 SP)

**Sprint Feature:** 117.9

**Objective:** Seed system with "general" default domain on initialization.

#### Requirements

**Default Domain:**
```json
{
  "name": "general",
  "description": "General purpose domain for non-specialized content",
  "entity_types": ["Entity", "Person", "Organization", "Location", "Concept"],
  "relation_types": ["RELATES_TO", "MENTIONED_IN", "AUTHORED_BY", "LOCATED_IN"],
  "intent_classes": ["general_inquiry", "information_request", "clarification"],
  "model_family": "general",
  "confidence_threshold": 0.5,
  "status": "active"
}
```

**Implementation Tasks:**
1. Create database migration for default domain
2. Add seeding function to database initialization
3. Add idempotency check (don't re-create if exists)
4. Add verification test
5. Document seed process

**Acceptance Criteria:**
- [ ] "general" domain created on system initialization
- [ ] Idempotent (safe to run multiple times)
- [ ] Verify in tests that general domain always exists
- [ ] Documented in system setup guide

---

## Backend API Summary

### Complete Domain Management API

| Endpoint | Method | Purpose | Feature |
|----------|--------|---------|---------|
| `/api/v1/admin/domains/` | GET | List all domains | 117.1 |
| `/api/v1/admin/domains/` | POST | Create domain | 117.1 |
| `/api/v1/admin/domains/{name}` | GET | Get domain details | 117.1 |
| `/api/v1/admin/domains/{name}` | PUT | Update domain | 117.1 |
| `/api/v1/admin/domains/{name}` | DELETE | Delete domain | 117.1 |
| `/api/v1/admin/domains/classify` | POST | Classify document to domain | 117.2 |
| `/api/v1/admin/domains/discover` | POST | Auto-discover domains | 117.3 |
| `/api/v1/admin/domains/augment` | POST | Augment training data | 117.4 |
| `/api/v1/admin/domains/ingest-batch` | POST | Batch document ingestion | 117.5 |
| `/api/v1/admin/domains/{name}/training-status` | GET | Get training progress | 117.6 |
| `/api/v1/admin/domains/{name}/train` | POST | Start domain training | 117.6 |
| `/api/v1/admin/domains/{id}/validate` | POST | Validate domain | 117.7 |

---

## Frontend Components Summary

### Domain Management UI

| Component | Purpose | Feature |
|-----------|---------|---------|
| `DomainList` | Display all domains | 117.1 |
| `DomainCard` | Individual domain card | 117.1 |
| `CreateDomainModal` | Create new domain | 117.1 |
| `DomainDetailsView` | Full domain details | 117.1 |
| `DocumentClassifier` | Classify document | 117.2 |
| `ClassificationResults` | Show classification results | 117.2 |
| `DomainDiscoveryWizard` | Auto-discovery flow | 117.3 |
| `DocumentUploadArea` | Drag-drop upload | 117.3 |
| `AugmentationWizard` | Data augmentation flow | 117.4 |
| `AugmentationResults` | Show augmentation results | 117.4 |
| `BatchIngestionWizard` | Batch ingestion flow | 117.5 |
| `BatchProgress` | Real-time ingestion progress | 117.5 |
| `BatchResults` | Batch results summary | 117.5 |
| `DomainDetailsPanel` | Domain information display | 117.6 |
| `TrainingProgressBar` | Training progress visual | 117.6 |
| `TrainingLogs` | Real-time training logs | 117.6 |
| `ValidationReport` | Validation results display | 117.7 |
| `HealthScoreGauge` | Domain health score | 117.7 |

---

## Testing Strategy

### Unit Tests (Backend)
- **Coverage Target:** 80%+
- **Test Files:** `tests/unit/admin/domains/`
- **Scope:**
  - Domain CRUD operations
  - Input validation
  - Classification logic
  - Augmentation strategies
  - Response schemas

### Integration Tests
- **Coverage Target:** 70%+
- **Test Files:** `tests/integration/domains/`
- **Scope:**
  - Database persistence
  - LLM integration
  - Batch processing
  - End-to-end workflows

### E2E Tests (Playwright)
- **Coverage Target:** All 9 features
- **Test Files:** `frontend/e2e/admin/test_domain_training_api.spec.ts` (updated)
- **Test Count:** 30+ E2E tests
- **Scope:**
  - UI workflows
  - Form validation
  - Error handling
  - Real-time progress updates
  - Download/export functionality

### Performance Tests
- **Targets:**
  - CRUD operations: <100ms
  - Classification: <500ms (excluding LLM)
  - Discovery: <2s (excluding LLM)
  - Augmentation: <60 seconds for 100 samples
  - Batch ingestion: <5 minutes for 100 documents
  - Validation: <10 seconds for 1000+ samples

---

## Success Criteria

### Backend
- [ ] All 12 API endpoints implemented and documented
- [ ] Input validation on all endpoints with 400 errors for invalid input
- [ ] Error handling with appropriate HTTP status codes
- [ ] Request/response logging for debugging
- [ ] Unit test coverage >80%
- [ ] Integration test coverage >70%
- [ ] Response format standardization across all endpoints

### Frontend
- [ ] All 18 React components implemented
- [ ] Form validation with user-friendly error messages
- [ ] Real-time progress indicators
- [ ] Responsive design (mobile, tablet, desktop)
- [ ] Accessibility compliance (WCAG 2.1 AA)
- [ ] 30+ E2E tests passing
- [ ] Loading states and error boundaries

### Integration
- [ ] End-to-end workflows tested
- [ ] LLM integration working smoothly
- [ ] Batch processing reliable
- [ ] Database persistence verified
- [ ] API documentation complete
- [ ] User guide drafted

### Quality
- [ ] No hardcoded values
- [ ] Comprehensive error messages
- [ ] Logging at appropriate levels
- [ ] Code style consistent with project
- [ ] No blocking issues from linters
- [ ] Performance targets met

---

## Dependencies & Blockers

### Internal Dependencies
- **On Sprint 116:** Domain CRUD must complete before other features
- **On Backend Agent:** LLM routing and model selection
- **On Testing Agent:** E2E test infrastructure and fixtures

### External Dependencies
- **Ollama/Nemotron3:** LLM inference for classification, discovery, augmentation
- **LangGraph:** Orchestration for multi-step agents
- **Qdrant:** Vector storage for domain embeddings
- **Neo4j:** Graph storage for entity/relation tracking

### Known Blockers
- None identified at sprint start

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| LLM Classification Accuracy | Medium | High | Implement confidence thresholds, validation layer |
| Performance of Batch Ingestion | Low | Medium | Async processing, load testing, optimization |
| E2E Test Flakiness | Medium | Medium | Proper timeouts, retry logic, test stabilization |
| Entity Extraction Issues | Low | Medium | Validation layer, manual review option |

---

## Definition of Done

- [ ] All acceptance criteria met for each feature
- [ ] Code reviewed and approved
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass
- [ ] E2E tests pass (all 30+ tests)
- [ ] API documentation complete
- [ ] No console errors/warnings
- [ ] Performance targets met
- [ ] Linting passes (ruff, mypy)
- [ ] Documentation updated (API docs, README)
- [ ] Commits follow convention (feat/fix scopes)
- [ ] Sprint review presentation prepared

---

### 10. Upload Dialog Domain Classification Display (3 SP)

**Sprint Feature:** 117.10

**Objective:** Nach jedem Dokument-Upload im Dialog anzeigen, für welche Domain mit welcher Konfidenz und mit welchem Classification Path das Dokument klassifiziert wurde.

#### Backend Requirements

**Extended Upload Response:**
```json
{
  "document_id": "doc_abc123",
  "filename": "medical_report.pdf",
  "status": "completed",
  "domain_classification": {
    "domain_id": "medical",
    "domain_name": "Medical Documents",
    "confidence": 0.94,
    "classification_path": "fast",
    "latency_ms": 42,
    "model_used": "C-LARA-SetFit-v2",
    "matched_entity_types": ["Disease", "Treatment", "Medication"],
    "matched_intent": "diagnosis_report"
  },
  "extraction_summary": {
    "entities_count": 47,
    "relations_count": 23,
    "chunks_count": 12,
    "mentioned_in_count": 47
  },
  "processing_time_ms": 3420
}
```

**Modify Existing Endpoint:**
```
POST /api/v1/retrieval/upload
GET /api/v1/admin/upload-status/{document_id}
```

#### Frontend Requirements

**Components:**
- `UploadResultCard` - Extended to show domain classification
- `DomainClassificationBadge` - Shows domain + confidence + path icon
- `ClassificationPathIcon` - ⚡ Fast | ✓ Verified | 🔍 Full

**UI Design:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ✅ Upload Successful                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📄 medical_report.pdf                                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Domain Classification                                    │   │
│  │  ┌──────────────────┐                                    │   │
│  │  │ 🏥 Medical       │  94% confidence  ⚡ Fast Path      │   │
│  │  └──────────────────┘                                    │   │
│  │  Matched: Disease, Treatment, Medication                 │   │
│  │  Intent: diagnosis_report                                │   │
│  │  Latency: 42ms                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Extraction Summary:                                            │
│  • 47 Entities extracted                                        │
│  • 23 Relations identified                                      │
│  • 12 Chunks indexed                                            │
│  • 47 MENTIONED_IN links created                                │
│                                                                 │
│  Processing Time: 3.4s                                          │
│                                                                 │
│  [View Document]  [View in Graph]  [Upload Another]            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Test Coverage (E2E):**
- TC-117.10.1: Upload shows domain classification badge
- TC-117.10.2: Classification path icon displays correctly (fast/verified/full)
- TC-117.10.3: Confidence percentage renders with color coding
- TC-117.10.4: Extraction summary shows all counts
- TC-117.10.5: MENTIONED_IN count displayed

**Acceptance Criteria:**
- [ ] Upload response includes domain_classification object
- [ ] Frontend displays domain badge with confidence
- [ ] Classification path shown with appropriate icon
- [ ] Matched entity types and intent displayed
- [ ] Extraction summary shows MENTIONED_IN count
- [ ] Low confidence warning displayed when `requires_review: true`
- [ ] Alternative domains shown when confidence < 0.60
- [ ] All E2E tests pass

---

### 11. Manual Domain Override (2 SP)

**Sprint Feature:** 117.11

**Objective:** Benutzer muss die automatisch erkannte Domain manuell überschreiben können, wenn die Klassifikation falsch ist.

#### Backend Requirements

**New Endpoint:**
```
PATCH /api/v1/documents/{document_id}/domain
```

**Request Schema:**
```json
{
  "domain_id": "medical",
  "reason": "Document contains medical terminology not recognized by classifier",
  "reprocess_extraction": true
}
```

**Response Schema:**
```json
{
  "document_id": "doc_abc123",
  "previous_domain": {
    "domain_id": "general",
    "confidence": 0.42,
    "classification_path": "fallback"
  },
  "new_domain": {
    "domain_id": "medical",
    "source": "manual_override",
    "override_reason": "Document contains medical terminology...",
    "overridden_by": "user_admin",
    "overridden_at": "2026-01-20T16:30:00Z"
  },
  "reprocessing": {
    "status": "started",
    "job_id": "reprocess_xyz789"
  }
}
```

**Behavior:**
1. **Update document metadata** with new domain
2. **Log override** for audit trail (who, when, why)
3. **Optional: Re-run extraction** with domain-specific prompts
4. **Update graph** with new entity types if reprocessed
5. **Feed back to C-LARA** as training signal (optional)

**Reprocessing Logic:**
```python
if reprocess_extraction:
    # 1. Load domain-specific DSPy prompts
    domain_prompts = load_domain_prompts(new_domain_id)

    # 2. Re-extract entities/relations with new prompts
    new_entities, new_relations = await extract_with_domain(
        document_text, domain_prompts
    )

    # 3. Update Neo4j graph
    await update_graph(document_id, new_entities, new_relations)

    # 4. Update MENTIONED_IN relations
    await update_mentioned_in(document_id, new_entities)
```

#### Frontend Requirements

**UI Enhancement in Upload Result Card:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ Low Confidence Classification                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📄 research_paper.pdf                                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Domain Classification  [✏️ Override]  ← NEW BUTTON      │   │
│  │  ┌──────────────────┐                                    │   │
│  │  │ 📁 General       │  42% confidence  🔍 Fallback       │   │
│  │  └──────────────────┘                                    │   │
│  │                                                          │   │
│  │  ⚠️ Low confidence - please review                       │   │
│  │                                                          │   │
│  │  Alternative suggestions:                                │   │
│  │  • Medical (32%)  [Use this]                            │   │
│  │  • Legal (28%)    [Use this]                            │   │
│  │  • Finance (15%)  [Use this]                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Override Modal:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Change Domain Classification                              [X]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Current Domain: General (42%)                                  │
│                                                                 │
│  Select New Domain:                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ▼ Medical                                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Reason for Override (optional):                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Document contains medical terminology not recognized... │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ☑️ Re-extract entities with new domain prompts                 │
│     (Recommended for better extraction quality)                 │
│                                                                 │
│                              [Cancel]  [Apply Override]         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Test Coverage (E2E):**
- TC-117.11.1: Override button appears for low confidence
- TC-117.11.2: Override modal shows all available domains
- TC-117.11.3: Successful override updates display
- TC-117.11.4: Reprocessing triggered when checkbox enabled
- TC-117.11.5: Override reason saved to audit log

**Acceptance Criteria:**
- [ ] Override button visible when confidence < 0.60
- [ ] Modal allows domain selection from all active domains
- [ ] Reason field optional but encouraged
- [ ] Reprocessing checkbox works correctly
- [ ] Audit log records all overrides
- [ ] UI updates after successful override
- [ ] All E2E tests pass

---

### 12. LLM Model Selection per Domain (3 SP)

**Sprint Feature:** 117.12

**Objective:** LLM-Modell soll pro Domain konfigurierbar sein, für DSPy Training und Production Extraction.

#### Architecture Decision

**Drei Optionen für Modell-Auswahl:**

| Option | Beschreibung | Empfehlung |
|--------|--------------|------------|
| **A: Manual per Domain** | Admin wählt Modell bei Domain-Erstellung | ✅ Empfohlen |
| **B: DSPy Hyperparameter** | DSPy optimiert auch Modell-Wahl | ⚠️ Komplex, teuer |
| **C: Global Default** | Ein Modell für alle Domains | ❌ Nicht flexibel |

**Empfehlung: Option A - Manual per Domain**

Gründe:
1. **Kontrollierbar:** Admin entscheidet basierend auf Domain-Komplexität
2. **Kosteneffizient:** Kleine Domains → kleineres Modell, komplexe → größeres
3. **DSPy-kompatibel:** DSPy optimiert Prompts, nicht Modelle
4. **Einfach zu implementieren:** Dropdown bei Domain-Erstellung

#### Extended Domain Schema

```python
class DomainSchema(BaseModel):
    # ... existing fields ...

    # NEW: LLM Configuration
    llm_config: DomainLLMConfig = Field(default_factory=DomainLLMConfig)

class DomainLLMConfig(BaseModel):
    """LLM configuration per domain."""

    # DSPy Training Model (for prompt optimization)
    training_model: str = "qwen3:32b"
    training_temperature: float = 0.7
    training_max_tokens: int = 4096

    # Production Extraction Model (for entity/relation extraction)
    extraction_model: str = "nemotron3"
    extraction_temperature: float = 0.3
    extraction_max_tokens: int = 2048

    # Classification Model (for C-LARA fallback LLM verification)
    classification_model: str = "nemotron3"

    # Model Provider
    provider: Literal["ollama", "alibaba", "openai"] = "ollama"
```

**Available Models (Ollama on DGX Spark):**

| Model | Size | Use Case | Latency |
|-------|------|----------|---------|
| `nemotron3` | 8B | Fast extraction, classification | ~2s |
| `qwen3:32b` | 32B | DSPy training, complex domains | ~5-10s |
| `qwen3:8b` | 8B | Balanced speed/quality | ~2-3s |
| `llama3.1:70b` | 70B | Maximum quality (if available) | ~15-20s |

#### Frontend Requirements

**Domain Creation Form Extension:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Create New Domain                                         [X]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Domain Name: [medical___________]                              │
│  Description: [Medical documents__]                             │
│                                                                 │
│  Entity Types: [Disease, Symptom, Treatment, Medication]        │
│  Relation Types: [TREATS, CAUSES, SYMPTOM_OF]                   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🤖 LLM Configuration                           [Advanced]│   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  Training Model (DSPy Optimization):                     │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ ▼ qwen3:32b (Recommended for complex domains)   │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ℹ️ Larger models produce better DSPy prompts            │   │
│  │                                                          │   │
│  │  Extraction Model (Production):                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ ▼ nemotron3 (Fast, good for most cases)         │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ℹ️ Used for entity/relation extraction after training   │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                                    [Cancel]  [Create Domain]    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Model Selection Endpoint:**
```
GET /api/v1/admin/domains/available-models
```

**Response:**
```json
{
  "models": [
    {
      "id": "nemotron3",
      "name": "Nemotron3 8B",
      "provider": "ollama",
      "size_gb": 4.7,
      "recommended_for": ["extraction", "classification"],
      "speed": "fast",
      "quality": "good"
    },
    {
      "id": "qwen3:32b",
      "name": "Qwen3 32B",
      "provider": "ollama",
      "size_gb": 18.5,
      "recommended_for": ["training"],
      "speed": "slow",
      "quality": "excellent"
    }
  ],
  "recommendations": {
    "training": "qwen3:32b",
    "extraction": "nemotron3",
    "classification": "nemotron3"
  }
}
```

**Test Coverage (E2E):**
- TC-117.12.1: Model dropdown shows available Ollama models
- TC-117.12.2: Selected model saved with domain
- TC-117.12.3: DSPy training uses configured training model
- TC-117.12.4: Production extraction uses configured extraction model
- TC-117.12.5: Model change triggers re-training option

**Acceptance Criteria:**
- [ ] Model selection dropdown in domain creation form
- [ ] Separate models for training vs extraction
- [ ] Available models fetched from Ollama API
- [ ] Model recommendations displayed
- [ ] Domain uses correct model for DSPy training
- [ ] Domain uses correct model for production extraction
- [ ] All E2E tests pass

---

## Cross-Cutting Requirement: LangSmith Tracing

**KRITISCH für Debugging und Qualitätssicherung!**

### LangSmith Trace Points

Alle folgenden Operationen MÜSSEN LangSmith Traces haben:

| Operation | Trace Name | Key Metrics |
|-----------|------------|-------------|
| Domain Classification | `domain_classification` | confidence, path, latency |
| DSPy Entity Extraction Training | `dspy_entity_training` | prompts, scores, iterations |
| DSPy Relation Extraction Training | `dspy_relation_training` | prompts, scores, iterations |
| Entity Extraction (Production) | `entity_extraction` | entity_count, latency, domain |
| Relation Extraction (Production) | `relation_extraction` | relation_count, latency, domain |
| C-LARA Classifier Training | `clara_training` | accuracy, calibration_score |
| Data Augmentation | `data_augmentation` | generated_count, diversity_score |
| Domain Discovery | `domain_discovery` | discovered_domains, confidence |

### Implementation Requirements

```python
# Beispiel: LangSmith Tracing für Domain Classification
from langsmith import traceable

@traceable(name="domain_classification", run_type="chain")
async def classify_document(document_text: str, document_id: str) -> DomainClassificationResult:
    """Classify document with full LangSmith tracing."""
    # Stage A: C-LARA
    with trace("clara_classifier") as t:
        candidates = await clara_classify(document_text)
        t.metadata["confidence"] = candidates[0].confidence
        t.metadata["path"] = determine_path(candidates[0].confidence)

    # Stage B: Optional LLM
    if needs_llm_verification(candidates):
        with trace("llm_verification") as t:
            enriched = await llm_verify(candidates[:3])
            t.metadata["reasoning_length"] = len(enriched.reasoning)

    return result
```

### Monitoring Dashboard

LangSmith Project: `aegisrag-domain-training`

**Key Metrics to Track:**
- Classification accuracy by domain
- Path distribution (fast/verified/fallback)
- Average latency per path
- DSPy training convergence
- Entity/Relation extraction quality scores
- C-LARA confidence calibration

### Testing Integration

Nach Sprint 117 Implementation:
1. **Un-skip** alle Domain Training E2E Tests
2. **Run** Tests mit LangSmith Tracing aktiviert
3. **Analyze** Traces für Schwachstellen
4. **Iterate** basierend auf Trace-Erkenntnissen

**Test Files to Un-skip:**
- `frontend/e2e/admin/test_domain_training_api.spec.ts`
- `frontend/e2e/admin/domain-auto-discovery.spec.ts`
- `frontend/e2e/admin/test_domain_upload_integration.spec.ts`
- `frontend/e2e/admin/test_domain_training_flow.spec.ts`

---

## Updated Sprint Summary

| Feature | SP | Description |
|---------|-----|-------------|
| 117.1 | 13 | Domain CRUD API |
| 117.2 | 8 | Domain Classification (C-LARA Hybrid) |
| 117.3 | 8 | Domain Auto-Discovery |
| 117.4 | 8 | Domain Data Augmentation |
| 117.5 | 8 | Batch Document Ingestion |
| 117.6 | 5 | Domain Training Status/Progress |
| 117.7 | 5 | Domain Validation |
| 117.8 | 3 | Response Format Standardization |
| 117.9 | 3 | Domain Default Seeding |
| 117.10 | 3 | Upload Dialog Classification Display |
| **117.11** | **2** | **Manual Domain Override** |
| **117.12** | **3** | **LLM Model Selection per Domain** |
| **Total** | **69** | **(+8 SP from original 61)** |

---

## References

### Related Documentation
- Sprint 116 Analysis: `docs/sprints/SPRINT_116_SKIPPED_TESTS_ANALYSIS.md`
- E2E Testing Guide: `docs/e2e/PLAYWRIGHT_E2E.md`
- Architecture: `docs/ARCHITECTURE.md`
- Technology Stack: `docs/TECH_STACK.md`

### Test Files
- E2E Tests: `/frontend/e2e/admin/test_domain_training_api.spec.ts`
- Domain Auto-Discovery: `/frontend/e2e/admin/domain-auto-discovery.spec.ts`
- Domain Upload: `/frontend/e2e/admin/test_domain_upload_integration.spec.ts`
- Domain Training Flow: `/frontend/e2e/admin/test_domain_training_flow.spec.ts`

### Related ADRs
- ADR-026: Pure LLM extraction pipeline
- ADR-039: Adaptive section-aware chunking
- ADR-041: Graph expansion and semantic search

---

## Sprint Retrospective Template (Post-Sprint)

### What Went Well
- [ ] Team communication and coordination
- [ ] Feature development pace
- [ ] E2E test coverage improvements
- [ ] Code quality and reviews

### Challenges
- [ ] Specific blockers encountered
- [ ] Time estimate accuracy
- [ ] Testing complexity

### Improvements for Next Sprint
- [ ] Process improvements
- [ ] Tool/infrastructure improvements
- [ ] Team learnings

### Metrics
- **Story Points Delivered:** 61 SP
- **Velocity:** [To be filled]
- **E2E Pass Rate:** [To be filled]
- **Code Coverage:** [To be filled]
- **Deployment Status:** [To be filled]

---

**Document History**
- 2026-01-20: Initial Sprint 117 Plan created based on SPRINT_116_SKIPPED_TESTS_ANALYSIS.md
