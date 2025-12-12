# Sprint 45: Domain-Specific Prompt Optimization mit DSPy

**Status:** CLOSED (2025-12-12)
**Duration:** 5 Arbeitstage
**Story Points:** 47 SP
**Dependencies:** Sprint 44 (Pipeline Monitoring)
**ADR:** TBD - ADR-045: Domain-Specific Extraction Strategy

---

## Sprint Objectives

### Primary Goals
1. **Domain Training Admin UI** - Neue Adminseite zum Trainieren domain-spezifischer Extraction-Prompts
2. **DSPy Integration** - Automatische Prompt-Optimierung basierend auf Trainings-Datasets
3. **Domain Registry** - Persistierung optimierter Prompts in Neo4j
4. **Automatic Domain Classification** - Upload-Zeit Domain-Erkennung
5. **Fallback Prompt** - Generischer Extraction-Prompt ohne Domain-Spezifik
6. **Domain Auto-Discovery** - LLM-basierte Titel/Description-Generierung aus Sample-Dokumenten

### Why DSPy?
- **Automatische Prompt-Optimierung** statt manuellem Prompt-Engineering
- **Domain-Agnostisch** - funktioniert für Tech-Docs, Legal, Medical, etc.
- **Kompilierte Prompts** können extrahiert und ohne DSPy verwendet werden
- **Few-Shot Selection** automatisch aus Trainings-Dataset

### Key Design Decisions
- **Neo4j als Domain Registry** - Nutzt bestehende Infrastruktur, keine neue DB
- **DSPy nur für Training** - Kein DSPy in Production Runtime
- **LLM-Gruppierung bei Ingestion** - Dokumente nach LLM gruppieren für optimales Model Loading
- **Single-Domain per Document** - Ein Dokument gehört zu genau einer Domain

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ADMIN: Domain Training                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Domain    │    │  Training   │    │    DSPy     │    │   Prompt    │  │
│  │   Config    │───▶│   Dataset   │───▶│  Optimizer  │───▶│  Registry   │  │
│  │             │    │   Upload    │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│        │                  │                  │                  │          │
│        ▼                  ▼                  ▼                  ▼          │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        Domain Registry (Neo4j)                        │ │
│  │  - (:Domain {id, name, description, description_embedding})           │ │
│  │  - optimized_entity_prompt, optimized_relation_prompt                 │ │
│  │  - entity_examples, relation_examples (JSON)                          │ │
│  │  - training_metrics, llm_model, created_at, status                    │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ADMIN: Document Upload                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Document   │    │   Domain    │    │   Prompt    │    │  Extraction │  │
│  │   Upload    │───▶│  Classifier │───▶│  Selection  │───▶│   Pipeline  │  │
│  │             │    │             │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                            │                                               │
│                            ▼                                               │
│                    Domain Match Score                                       │
│                    + Manual Override                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature Overview

| Feature | Story Points | Priority | Type |
|---------|--------------|----------|------|
| 45.1: Domain Registry in Neo4j | 3 SP | P0 | Backend |
| 45.2: DSPy Integration Service | 8 SP | P0 | Backend |
| 45.3: Domain Training API | 5 SP | P0 | Backend |
| 45.4: Domain Training Admin UI | 8 SP | P1 | Frontend |
| 45.5: Training Progress & Logging | 3 SP | P1 | Backend |
| 45.6: Domain Classifier | 5 SP | P1 | Backend |
| 45.7: Upload Page Domain Suggestion | 5 SP | P1 | Frontend |
| 45.8: Fallback Generic Prompt | 2 SP | P2 | Backend |
| 45.9: Domain Auto-Discovery | 5 SP | P1 | Backend + Frontend |
| 45.10: LLM-Grouped Ingestion | 3 SP | P1 | Backend |
| 45.11: Training Data Augmentation | 5 SP | P1 | Backend |
| 45.12: Metric Configuration UI | 3 SP | P1 | Backend + Frontend |
| 45.13: E2E Tests | 3 SP | P2 | Testing |
| 45.14: SSE Real-Time Training Stream | 5 SP | P1 | Backend + Frontend |
| 45.15: JSONL Training Log Export | 3 SP | P1 | Backend + Frontend |
| 45.16: DSPy/AnyLLM Integration | 3 SP | P2 | Backend |
| **Total** | **69 SP** | | |

### Priority Overview
- **P0 (Must Have):** Features 45.1-45.3 - Backend Core (16 SP)
- **P1 (Should Have):** Features 45.4-45.7, 45.9-45.12 - UI + Auto-Discovery + Augmentation + Metrics (37 SP)
- **P2 (Nice to Have):** Features 45.8, 45.13 - Fallback + E2E Tests (5 SP)

---

## Feature 45.1: Domain Registry in Neo4j (3 SP) - P0

### Neo4j Schema

```cypher
// Domain Node - stores domain configuration and optimized prompts
CREATE CONSTRAINT domain_name_unique IF NOT EXISTS
FOR (d:Domain) REQUIRE d.name IS UNIQUE;

// Domain Node Schema
(:Domain {
    // Identity
    id: "uuid",
    name: "tech_docs",                    // Unique identifier (lowercase, underscores)
    description: "Technical documentation...",  // For classification matching
    description_embedding: [float...],    // BGE-M3 embedding of description (1024-dim)

    // Optimized Prompts (extracted from DSPy)
    entity_prompt: "Extract entities...",
    relation_prompt: "Extract relations...",

    // Few-Shot Examples (JSON strings)
    entity_examples: '[{text: ..., entities: [...]}]',
    relation_examples: '[{text: ..., relations: [...]}]',

    // Training Configuration
    llm_model: "qwen3:32b",
    training_samples: 25,
    training_duration_seconds: 342.5,
    training_metrics: '{"entity_f1": 0.85, "relation_f1": 0.72}',

    // Status
    status: "ready",  // pending, training, ready, failed

    // Timestamps
    created_at: datetime(),
    updated_at: datetime(),
    trained_at: datetime()
})

// Training Log Node - linked to Domain
(:TrainingLog {
    id: "uuid",
    started_at: datetime(),
    completed_at: datetime(),
    status: "completed",  // running, completed, failed
    current_step: "Optimizing relations...",
    progress_percent: 85.0,
    log_messages: '[{timestamp, level, message}]',
    metrics: '{"entity_f1": 0.85}',
    error_message: null
})

// Relationship
(d:Domain)-[:HAS_TRAINING_LOG]->(t:TrainingLog)
```

### Domain Repository

```python
# src/components/domain_training/domain_repository.py

from typing import Optional
import json
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class DomainRepository:
    """Repository for Domain configurations in Neo4j."""

    def __init__(self, neo4j_client):
        self.neo4j = neo4j_client

    async def create_domain(
        self,
        name: str,
        description: str,
        llm_model: str,
        description_embedding: list[float]
    ) -> dict:
        """Create a new domain configuration."""
        query = """
        CREATE (d:Domain {
            id: randomUUID(),
            name: $name,
            description: $description,
            description_embedding: $embedding,
            llm_model: $llm_model,
            status: 'pending',
            created_at: datetime(),
            updated_at: datetime(),
            training_samples: 0,
            entity_prompt: null,
            relation_prompt: null,
            entity_examples: '[]',
            relation_examples: '[]'
        })
        RETURN d
        """
        result = await self.neo4j.execute(query, {
            "name": name,
            "description": description,
            "embedding": description_embedding,
            "llm_model": llm_model
        })
        return result[0]["d"]

    async def get_domain(self, name: str) -> Optional[dict]:
        """Get domain by name."""
        query = "MATCH (d:Domain {name: $name}) RETURN d"
        result = await self.neo4j.execute(query, {"name": name})
        return result[0]["d"] if result else None

    async def list_domains(self) -> list[dict]:
        """List all domains ordered by name."""
        query = "MATCH (d:Domain) RETURN d ORDER BY d.name"
        result = await self.neo4j.execute(query)
        return [r["d"] for r in result]

    async def update_domain_prompts(
        self,
        name: str,
        entity_prompt: str,
        relation_prompt: str,
        entity_examples: list[dict],
        relation_examples: list[dict],
        metrics: dict
    ) -> dict:
        """Update domain with optimized prompts after DSPy training."""
        query = """
        MATCH (d:Domain {name: $name})
        SET d.entity_prompt = $entity_prompt,
            d.relation_prompt = $relation_prompt,
            d.entity_examples = $entity_examples,
            d.relation_examples = $relation_examples,
            d.training_metrics = $metrics,
            d.status = 'ready',
            d.trained_at = datetime(),
            d.updated_at = datetime()
        RETURN d
        """
        result = await self.neo4j.execute(query, {
            "name": name,
            "entity_prompt": entity_prompt,
            "relation_prompt": relation_prompt,
            "entity_examples": json.dumps(entity_examples),
            "relation_examples": json.dumps(relation_examples),
            "metrics": json.dumps(metrics)
        })
        return result[0]["d"]

    async def find_best_matching_domain(
        self,
        document_embedding: list[float],
        threshold: float = 0.5
    ) -> Optional[dict]:
        """Find domain with highest cosine similarity to document embedding."""
        query = """
        MATCH (d:Domain)
        WHERE d.status = 'ready' AND d.description_embedding IS NOT NULL
        WITH d, gds.similarity.cosine(d.description_embedding, $embedding) AS score
        WHERE score >= $threshold
        RETURN d, score
        ORDER BY score DESC
        LIMIT 1
        """
        result = await self.neo4j.execute(query, {
            "embedding": document_embedding,
            "threshold": threshold
        })
        if result:
            return {"domain": result[0]["d"], "score": result[0]["score"]}
        return None

    async def delete_domain(self, name: str) -> bool:
        """Delete domain and its training logs."""
        query = """
        MATCH (d:Domain {name: $name})
        OPTIONAL MATCH (d)-[:HAS_TRAINING_LOG]->(t:TrainingLog)
        DETACH DELETE d, t
        RETURN count(d) as deleted
        """
        result = await self.neo4j.execute(query, {"name": name})
        return result[0]["deleted"] > 0
```

### Deliverables
- [ ] Neo4j schema for Domain and TrainingLog nodes
- [ ] DomainRepository with CRUD operations
- [ ] Embedding-based domain matching query
- [ ] Default "general" domain initialization
- [ ] Migration script for existing databases

---

## Feature 45.2: DSPy Integration Service (8 SP) - P0

### DSPy Optimizer Service

```python
# src/components/domain_training/dspy_optimizer.py

import dspy
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class EntityExtractionSignature(dspy.Signature):
    """Extract key entities from the source text.
    Extracted entities are subjects or objects.
    This is for an extraction task, please be THOROUGH and accurate."""

    source_text: str = dspy.InputField()
    entities: list[str] = dspy.OutputField(desc="THOROUGH list of key entities")


class RelationExtractionSignature(dspy.Signature):
    """Extract subject-predicate-object triples from the source text.
    Subject and object must be from entities list.
    This is for an extraction task, please be thorough and accurate."""

    source_text: str = dspy.InputField()
    entities: list[str] = dspy.InputField()
    relations: list[dict] = dspy.OutputField(
        desc="List of {subject, predicate, object} tuples"
    )


class DSPyOptimizer:
    """Optimizes extraction prompts using DSPy."""

    def __init__(self, llm_model: str = "qwen3:32b"):
        self.llm_model = llm_model
        self._configure_dspy()

    def _configure_dspy(self):
        """Configure DSPy with Ollama backend."""
        self.lm = dspy.LM(
            model=f"ollama_chat/{self.llm_model}",
            api_base="http://localhost:11434",
            api_key="",  # Ollama doesn't need API key
        )
        dspy.configure(lm=self.lm)

    async def optimize_entity_extraction(
        self,
        training_data: list[dict],  # [{text: str, entities: list[str]}]
        progress_callback: callable = None,
    ) -> dict:
        """Optimize entity extraction prompt.

        Returns:
            {
                "instructions": str,  # Optimized prompt text
                "demos": list[dict],  # Selected few-shot examples
                "metrics": dict       # Training metrics
            }
        """
        # Convert training data to DSPy format
        trainset = [
            dspy.Example(
                source_text=item["text"],
                entities=item["entities"]
            ).with_inputs("source_text")
            for item in training_data
        ]

        # Create module
        entity_extractor = dspy.Predict(EntityExtractionSignature)

        # Define metric
        def entity_metric(example, prediction, trace=None):
            gold = set(e.lower() for e in example.entities)
            pred = set(e.lower() for e in prediction.entities)
            if not gold:
                return 1.0 if not pred else 0.0
            return len(gold & pred) / len(gold)  # Recall

        # Optimize
        optimizer = dspy.BootstrapFewShot(
            metric=entity_metric,
            max_bootstrapped_demos=4,
            max_labeled_demos=8,
        )

        if progress_callback:
            progress_callback("Optimizing entity extraction...", 10)

        optimized = optimizer.compile(entity_extractor, trainset=trainset)

        if progress_callback:
            progress_callback("Extracting optimized prompt...", 80)

        # Extract optimized prompt and examples
        predictor = optimized.predictors()[0]

        return {
            "instructions": predictor.signature.instructions,
            "demos": [
                {
                    "text": demo.source_text,
                    "entities": demo.entities
                }
                for demo in predictor.demos
            ],
            "metrics": {"entity_recall": self._evaluate(optimized, trainset, entity_metric)}
        }

    async def optimize_relation_extraction(
        self,
        training_data: list[dict],  # [{text, entities, relations}]
        progress_callback: callable = None,
    ) -> dict:
        """Optimize relation extraction prompt."""
        # Similar implementation...
        pass

    def extract_final_prompt(self, optimized_module) -> str:
        """Extract the final prompt text from an optimized module."""
        # Run a dummy call and inspect history
        dspy.inspect_history(n=1)
        # Parse and return the prompt
        pass

    def _evaluate(self, module, testset, metric) -> float:
        """Evaluate optimized module on test set."""
        scores = []
        for example in testset[:10]:  # Sample
            pred = module(source_text=example.source_text)
            scores.append(metric(example, pred))
        return sum(scores) / len(scores) if scores else 0.0
```

### Prompt Extractor

```python
# src/components/domain_training/prompt_extractor.py

def extract_prompt_from_dspy(optimized_module) -> dict:
    """Extract static prompt from DSPy optimized module.

    Returns prompt that can be used WITHOUT DSPy in production.
    """
    predictor = optimized_module.predictors()[0]

    # Get instructions
    instructions = predictor.signature.instructions

    # Get few-shot demos
    demos = []
    for demo in predictor.demos:
        demos.append({
            "input": demo.inputs(),
            "output": demo.labels()
        })

    # Format as static prompt
    prompt_template = f"""{instructions}

Few-shot examples:

"""
    for i, demo in enumerate(demos, 1):
        prompt_template += f"Example {i}:\n"
        prompt_template += f"Text: {demo['input']['source_text'][:500]}...\n"
        prompt_template += f"Output: {demo['output']}\n\n"

    prompt_template += """Now extract from this text:

Text:
{text}

Output (JSON array only):
"""

    return {
        "prompt_template": prompt_template,
        "instructions": instructions,
        "demos": demos
    }
```

### Deliverables
- [ ] DSPyOptimizer class with Ollama backend
- [ ] Entity extraction optimization
- [ ] Relation extraction optimization
- [ ] Prompt extractor for static usage
- [ ] Unit tests

---

## Feature 45.3: Domain Training API (5 SP) - P0

### API Endpoints

```python
# src/api/v1/domain_training.py

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin/domains", tags=["Domain Training"])


class DomainCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, pattern="^[a-z_]+$")
    description: str = Field(..., min_length=10, max_length=1000)
    llm_model: str = Field(default="qwen3:32b")


class TrainingDataset(BaseModel):
    samples: list[dict]  # [{text, entities, relations}]


class DomainResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    llm_model: str
    training_metrics: dict | None
    created_at: str
    trained_at: str | None


@router.post("/", response_model=DomainResponse)
async def create_domain(request: DomainCreateRequest):
    """Create a new domain configuration."""
    domain = await domain_service.create_domain(
        name=request.name,
        description=request.description,
        llm_model=request.llm_model
    )
    return DomainResponse.from_orm(domain)


@router.get("/", response_model=list[DomainResponse])
async def list_domains():
    """List all registered domains."""
    return await domain_service.list_domains()


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(domain_id: str):
    """Get domain details."""
    domain = await domain_service.get_domain(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@router.post("/{domain_id}/train")
async def start_training(
    domain_id: str,
    dataset: TrainingDataset,
    background_tasks: BackgroundTasks
):
    """Start DSPy optimization for a domain.

    The training runs in background. Use GET /domains/{id}/training-status
    to monitor progress.
    """
    domain = await domain_service.get_domain(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    if domain.status == "training":
        raise HTTPException(status_code=409, detail="Training already in progress")

    # Validate dataset
    if len(dataset.samples) < 5:
        raise HTTPException(
            status_code=400,
            detail="At least 5 training samples required"
        )

    # Start background training
    training_run = await domain_service.create_training_run(domain_id)
    background_tasks.add_task(
        run_dspy_optimization,
        domain_id=domain_id,
        training_run_id=training_run.id,
        dataset=dataset.samples
    )

    return {
        "message": "Training started",
        "training_run_id": training_run.id,
        "status_url": f"/admin/domains/{domain_id}/training-status"
    }


@router.get("/{domain_id}/training-status")
async def get_training_status(domain_id: str):
    """Get current training status and logs."""
    run = await domain_service.get_latest_training_run(domain_id)
    return {
        "status": run.status,
        "progress_percent": run.progress_percent,
        "current_step": run.current_step,
        "logs": run.log_messages[-50:],  # Last 50 log entries
        "metrics": run.metrics
    }


@router.get("/available-models")
async def get_available_models():
    """Get list of available LLM models from Ollama."""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:11434/api/tags")
        models = response.json().get("models", [])
        return {
            "models": [
                {
                    "name": m["name"],
                    "size": m.get("size", 0),
                    "modified_at": m.get("modified_at")
                }
                for m in models
            ]
        }


@router.delete("/{domain_id}")
async def delete_domain(domain_id: str):
    """Delete a domain configuration."""
    if domain_id == "general":
        raise HTTPException(status_code=400, detail="Cannot delete default domain")
    await domain_service.delete_domain(domain_id)
    return {"message": "Domain deleted"}
```

### Deliverables
- [ ] CRUD endpoints for domains
- [ ] Training trigger endpoint
- [ ] Training status endpoint
- [ ] Available models endpoint
- [ ] Input validation

---

## Feature 45.4: Domain Training Admin UI (8 SP) - P1

### GUI Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Admin > Domain Training                                           [+ New]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Registered Domains                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Name          │ Description              │ Model      │ Status │ Action ││
│  ├───────────────┼──────────────────────────┼────────────┼────────┼────────┤│
│  │ general       │ Fallback for unmatched   │ -          │ ✅ Ready│ [View] ││
│  │ tech_docs     │ Technical documentation  │ qwen3:32b  │ ✅ Ready│ [Edit] ││
│  │ legal         │ Legal contracts, laws    │ qwen2.5:7b │ 🔄 Training│ [View]││
│  │ scientific    │ Research papers          │ qwen3:32b  │ ⏳ Pending│[Train]││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  New Domain Training                                              [Cancel]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Step 1: Domain Configuration                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Name:  [tech_docs____________]  (lowercase, underscores only)           ││
│  │                                                                         ││
│  │ Description:                                                            ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐││
│  │ │ Technical documentation including API references, architecture      │││
│  │ │ documents, user manuals, and software specifications.               │││
│  │ └─────────────────────────────────────────────────────────────────────┘││
│  │                                                                         ││
│  │ LLM Model: [qwen3:32b ▼]                                               ││
│  │            └─ qwen3:32b (20GB) - Best quality, slowest                 ││
│  │               qwen2.5:7b (4GB) - Good balance                          ││
│  │               qwen2.5:3b (2GB) - Fastest, lower quality                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  Step 2: Training Dataset                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  [📁 Upload JSONL File]  or  [📝 Manual Entry]                         ││
│  │                                                                         ││
│  │  Expected format (JSONL):                                               ││
│  │  {"text": "...", "entities": ["Entity1", ...], "relations": [...]}     ││
│  │                                                                         ││
│  │  Loaded: 25 samples ✅                                                  ││
│  │  Preview:                                                               ││
│  │  ┌─────────────────────────────────────────────────────────────────┐   ││
│  │  │ Sample 1: "The REST API uses OAuth 2.0 for authentication..."   │   ││
│  │  │ Entities: REST API, OAuth 2.0, authentication                   │   ││
│  │  │ Relations: REST API --USES--> OAuth 2.0                         │   ││
│  │  └─────────────────────────────────────────────────────────────────┘   ││
│  │                                                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [Start Training]                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Training Progress: tech_docs                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Status: 🔄 Training (45%)                                                  │
│  ████████████████████░░░░░░░░░░░░░░░░░░░░  45%                             │
│                                                                             │
│  Current Step: Optimizing entity extraction prompts...                      │
│  Elapsed: 3m 42s                                                            │
│                                                                             │
│  Training Logs:                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 14:32:01 [INFO] Starting DSPy optimization for tech_docs               ││
│  │ 14:32:02 [INFO] Loaded 25 training samples                             ││
│  │ 14:32:05 [INFO] Configuring Ollama backend with qwen3:32b              ││
│  │ 14:32:10 [INFO] Running entity extraction optimization...               ││
│  │ 14:35:42 [INFO] Entity F1: 0.847 (iteration 3/5)                       ││
│  │ 14:35:43 [INFO] Optimizing relation extraction prompts...               ││
│  │ ...                                                                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [Cancel Training]                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Frontend Components

```typescript
// frontend/src/pages/admin/DomainTrainingPage.tsx

export function DomainTrainingPage() {
  const { data: domains, isLoading } = useDomains();
  const [showNewDomain, setShowNewDomain] = useState(false);

  return (
    <AdminLayout title="Domain Training">
      <div className="space-y-6">
        {/* Domain List */}
        <DomainList
          domains={domains}
          onNewDomain={() => setShowNewDomain(true)}
        />

        {/* New Domain Dialog */}
        {showNewDomain && (
          <NewDomainWizard onClose={() => setShowNewDomain(false)} />
        )}
      </div>
    </AdminLayout>
  );
}


// frontend/src/components/admin/NewDomainWizard.tsx

export function NewDomainWizard({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState<DomainConfig>({
    name: '',
    description: '',
    llm_model: 'qwen3:32b'
  });
  const [dataset, setDataset] = useState<TrainingSample[]>([]);
  const [trainingStatus, setTrainingStatus] = useState<TrainingStatus | null>(null);

  const { data: models } = useAvailableModels();
  const startTraining = useStartTraining();

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
      <div className="bg-white rounded-lg w-[800px] max-h-[90vh] overflow-auto">
        {step === 1 && (
          <DomainConfigStep
            config={config}
            models={models}
            onChange={setConfig}
            onNext={() => setStep(2)}
          />
        )}

        {step === 2 && (
          <DatasetUploadStep
            dataset={dataset}
            onUpload={setDataset}
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
          />
        )}

        {step === 3 && (
          <TrainingProgressStep
            domainId={config.name}
            status={trainingStatus}
            onComplete={onClose}
          />
        )}
      </div>
    </div>
  );
}
```

### Deliverables
- [ ] DomainTrainingPage with domain list
- [ ] NewDomainWizard (3-step wizard)
- [ ] DomainConfigStep (name, description, model)
- [ ] DatasetUploadStep (JSONL upload + preview)
- [ ] TrainingProgressStep (real-time logs)
- [ ] All data-testid attributes

---

## Feature 45.5: Training Progress & Logging (3 SP) - P1

### Background Task with Progress

```python
# src/components/domain_training/training_runner.py

async def run_dspy_optimization(
    domain_id: str,
    training_run_id: str,
    dataset: list[dict]
):
    """Run DSPy optimization in background with progress logging."""
    logger = TrainingLogger(training_run_id)

    try:
        await logger.log("Starting DSPy optimization", progress=5)

        # Get domain config
        domain = await domain_service.get_domain(domain_id)
        await logger.log(f"Using model: {domain.llm_model}", progress=10)

        # Initialize optimizer
        optimizer = DSPyOptimizer(llm_model=domain.llm_model)
        await logger.log(f"Loaded {len(dataset)} training samples", progress=15)

        # Optimize entity extraction
        await logger.log("Optimizing entity extraction prompts...", progress=20)
        entity_result = await optimizer.optimize_entity_extraction(
            training_data=dataset,
            progress_callback=lambda msg, pct: logger.log(msg, progress=20 + pct * 0.3)
        )
        await logger.log(
            f"Entity extraction optimized: F1={entity_result['metrics']['entity_recall']:.3f}",
            progress=50
        )

        # Optimize relation extraction
        await logger.log("Optimizing relation extraction prompts...", progress=55)
        relation_result = await optimizer.optimize_relation_extraction(
            training_data=dataset,
            progress_callback=lambda msg, pct: logger.log(msg, progress=55 + pct * 0.3)
        )
        await logger.log(
            f"Relation extraction optimized: F1={relation_result['metrics'].get('relation_f1', 0):.3f}",
            progress=85
        )

        # Save optimized prompts to domain
        await logger.log("Saving optimized prompts to domain registry...", progress=90)
        await domain_service.update_domain_prompts(
            domain_id=domain_id,
            entity_prompt=entity_result["instructions"],
            entity_examples=entity_result["demos"],
            relation_prompt=relation_result["instructions"],
            relation_examples=relation_result["demos"],
            metrics={
                "entity_recall": entity_result["metrics"]["entity_recall"],
                "relation_f1": relation_result["metrics"].get("relation_f1", 0),
                "training_samples": len(dataset),
            }
        )

        await logger.log("Training completed successfully!", progress=100, status="completed")

    except Exception as e:
        await logger.log(f"Training failed: {str(e)}", status="failed", error=str(e))
        raise


class TrainingLogger:
    """Logs training progress to database for real-time UI updates."""

    def __init__(self, training_run_id: str):
        self.run_id = training_run_id

    async def log(
        self,
        message: str,
        progress: float = None,
        status: str = None,
        error: str = None
    ):
        """Log a training message and update progress."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": "error" if error else "info"
        }

        await db.execute(
            """
            UPDATE training_logs
            SET log_messages = json_insert(log_messages, '$[#]', :entry),
                progress_percent = COALESCE(:progress, progress_percent),
                current_step = :message,
                status = COALESCE(:status, status),
                error_message = :error,
                completed_at = CASE WHEN :status IN ('completed', 'failed')
                               THEN :now ELSE completed_at END
            WHERE id = :run_id
            """,
            {
                "entry": json.dumps(log_entry),
                "progress": progress,
                "message": message,
                "status": status,
                "error": error,
                "now": datetime.now(),
                "run_id": self.run_id
            }
        )
```

### Deliverables
- [ ] TrainingLogger class
- [ ] Background task with progress updates
- [ ] SSE endpoint for real-time log streaming
- [ ] Error handling and recovery

---

## Feature 45.6: Domain Classifier (5 SP) - P1

### Document Domain Classification

```python
# src/components/domain_training/domain_classifier.py

from sentence_transformers import SentenceTransformer
import numpy as np

class DomainClassifier:
    """Classifies documents to registered domains based on content similarity."""

    def __init__(self):
        self.embedding_model = SentenceTransformer("BAAI/bge-m3")
        self._domain_embeddings: dict[str, np.ndarray] = {}

    async def load_domains(self):
        """Load domain descriptions and compute embeddings."""
        domains = await domain_service.list_domains()

        for domain in domains:
            if domain.description:
                embedding = self.embedding_model.encode(domain.description)
                self._domain_embeddings[domain.name] = embedding

    def classify_document(
        self,
        text: str,
        top_k: int = 3,
        sample_size: int = 2000
    ) -> list[dict]:
        """Classify document to best matching domain(s).

        Args:
            text: Document text (will sample beginning + middle + end)
            top_k: Number of top domains to return
            sample_size: Characters to sample for classification

        Returns:
            [{domain: str, score: float, description: str}]
        """
        # Sample text (beginning + middle + end for representative coverage)
        sampled_text = self._sample_text(text, sample_size)

        # Compute document embedding
        doc_embedding = self.embedding_model.encode(sampled_text)

        # Compute similarity to all domains
        scores = []
        for domain_name, domain_emb in self._domain_embeddings.items():
            similarity = np.dot(doc_embedding, domain_emb) / (
                np.linalg.norm(doc_embedding) * np.linalg.norm(domain_emb)
            )
            scores.append({
                "domain": domain_name,
                "score": float(similarity),
            })

        # Sort by score and return top_k
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def _sample_text(self, text: str, size: int) -> str:
        """Sample text from beginning, middle, and end."""
        if len(text) <= size:
            return text

        third = size // 3
        return (
            text[:third] +  # Beginning
            " ... " +
            text[len(text)//2 - third//2 : len(text)//2 + third//2] +  # Middle
            " ... " +
            text[-third:]  # End
        )


# API Endpoint
@router.post("/classify")
async def classify_document(request: ClassifyRequest):
    """Classify document text to best matching domain."""
    classifier = get_domain_classifier()

    results = classifier.classify_document(
        text=request.text,
        top_k=request.top_k or 3
    )

    return {
        "classifications": results,
        "recommended": results[0]["domain"] if results else "general",
        "confidence": results[0]["score"] if results else 0.0
    }
```

### Deliverables
- [ ] DomainClassifier with embedding-based matching
- [ ] Text sampling for efficient classification
- [ ] `/classify` API endpoint
- [ ] Confidence threshold for fallback to "general"

---

## Feature 45.7: Upload Page Domain Suggestion (5 SP) - P1

### Enhanced Upload Page

```typescript
// frontend/src/pages/admin/UploadPage.tsx (enhanced)

export function UploadPage() {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [domainSuggestions, setDomainSuggestions] = useState<Map<string, DomainSuggestion>>();

  const classifyDocument = useClassifyDocument();

  const handleFilesSelected = async (selectedFiles: File[]) => {
    const newFiles = selectedFiles.map(f => ({
      file: f,
      status: 'pending' as const,
      domainSuggestion: null as DomainSuggestion | null
    }));

    setFiles(prev => [...prev, ...newFiles]);

    // Classify each file
    for (const uploadFile of newFiles) {
      const text = await readFilePreview(uploadFile.file);
      const result = await classifyDocument.mutateAsync({ text });

      setDomainSuggestions(prev => new Map(prev).set(
        uploadFile.file.name,
        {
          recommended: result.recommended,
          confidence: result.confidence,
          alternatives: result.classifications
        }
      ));
    }
  };

  return (
    <AdminLayout title="Document Upload">
      <div className="space-y-6">
        {/* File Drop Zone */}
        <FileDropZone onFilesSelected={handleFilesSelected} />

        {/* File List with Domain Suggestions */}
        <div className="bg-white rounded-lg border">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left">File</th>
                <th className="px-4 py-3 text-left">Size</th>
                <th className="px-4 py-3 text-left">Suggested Domain</th>
                <th className="px-4 py-3 text-left">Confidence</th>
                <th className="px-4 py-3 text-left">Action</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file, idx) => {
                const suggestion = domainSuggestions?.get(file.file.name);
                return (
                  <tr key={idx} className="border-t">
                    <td className="px-4 py-3">{file.file.name}</td>
                    <td className="px-4 py-3">{formatBytes(file.file.size)}</td>
                    <td className="px-4 py-3">
                      <DomainSelector
                        suggested={suggestion?.recommended}
                        alternatives={suggestion?.alternatives}
                        onChange={(domain) => updateFileDomain(idx, domain)}
                      />
                    </td>
                    <td className="px-4 py-3">
                      {suggestion && (
                        <ConfidenceBadge score={suggestion.confidence} />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <button className="text-red-600 hover:underline">
                        Remove
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          className="px-6 py-3 bg-primary text-white rounded-lg"
        >
          Upload & Process ({files.length} files)
        </button>
      </div>
    </AdminLayout>
  );
}


function DomainSelector({
  suggested,
  alternatives,
  onChange
}: DomainSelectorProps) {
  const [selected, setSelected] = useState(suggested);

  return (
    <select
      value={selected}
      onChange={(e) => {
        setSelected(e.target.value);
        onChange(e.target.value);
      }}
      className="border rounded px-3 py-1"
      data-testid="domain-selector"
    >
      {alternatives?.map(alt => (
        <option key={alt.domain} value={alt.domain}>
          {alt.domain} ({(alt.score * 100).toFixed(0)}%)
        </option>
      ))}
    </select>
  );
}


function ConfidenceBadge({ score }: { score: number }) {
  const color = score > 0.8 ? 'green' : score > 0.5 ? 'yellow' : 'red';
  const label = score > 0.8 ? 'High' : score > 0.5 ? 'Medium' : 'Low';

  return (
    <span className={`px-2 py-1 rounded text-xs bg-${color}-100 text-${color}-800`}>
      {label} ({(score * 100).toFixed(0)}%)
    </span>
  );
}
```

### Deliverables
- [ ] Enhanced UploadPage with domain classification
- [ ] DomainSelector dropdown with alternatives
- [ ] ConfidenceBadge component
- [ ] Batch domain assignment for multiple files

---

## Feature 45.8: Fallback Generic Prompt (2 SP) - P2

### Default Generic Prompt

```python
# src/prompts/extraction_prompts.py

# Generic fallback prompt - no domain-specific entity/relation types
GENERIC_ENTITY_EXTRACTION_PROMPT = """Extract all significant entities from the following text.

An entity is any named thing: person, organization, place, concept, technology, product, event, etc.
Do NOT limit yourself to predefined types - extract whatever is meaningful in the context.

Text:
{text}

Return a JSON array of entities. Each entity should have:
- name: The exact name as it appears in text
- type: Your best categorization (use natural language, e.g., "Software Framework", "Medical Procedure")
- description: Brief description based on context (1 sentence)

Output (JSON array only):
"""

GENERIC_RELATION_EXTRACTION_PROMPT = """Extract relationships between the given entities from the text.

Entities:
{entities}

Text:
{text}

Return subject-predicate-object triples where:
- subject and object MUST be from the entity list above
- predicate is a natural language description of the relationship (e.g., "is used by", "developed", "located in")
- Do NOT limit to predefined relation types - describe the actual relationship

Output format (JSON array):
[
  {{"subject": "Entity1", "predicate": "relationship description", "object": "Entity2", "description": "context"}}
]

Output (JSON array only):
"""
```

### Integration with Domain Selection

```python
# src/components/graph_rag/extraction_service.py

class ExtractionService:
    async def extract_entities(self, text: str, domain: str = "general"):
        """Extract entities using domain-specific or fallback prompt."""

        # Get domain-specific prompt if available
        domain_config = await domain_service.get_domain(domain)

        if domain_config and domain_config.entity_prompt:
            prompt = self._build_domain_prompt(
                domain_config.entity_prompt,
                domain_config.entity_examples,
                text
            )
        else:
            # Fallback to generic prompt
            prompt = GENERIC_ENTITY_EXTRACTION_PROMPT.format(text=text)

        # ... rest of extraction logic
```

### Deliverables
- [ ] Generic entity extraction prompt
- [ ] Generic relation extraction prompt
- [ ] Fallback logic in ExtractionService
- [ ] "general" domain in registry

---

## Feature 45.9: Domain Auto-Discovery (5 SP) - P1

### Konzept

Beim Erstellen einer neuen Domain kann der Benutzer 5 Sample-Dokumente hochladen. Das LLM analysiert diese und generiert automatisch:
- **Domain Title** (z.B. "tech_docs", "legal_contracts")
- **Domain Description** für das Embedding-Matching

### API Endpoint

```python
# src/api/v1/domain_training.py

class DomainAutoDiscoveryRequest(BaseModel):
    sample_texts: list[str] = Field(..., min_items=3, max_items=10)
    # Expects 3-10 text samples (first 2000 chars each)


class DomainAutoDiscoveryResponse(BaseModel):
    suggested_name: str
    suggested_description: str
    detected_characteristics: list[str]
    confidence: float


@router.post("/auto-discover", response_model=DomainAutoDiscoveryResponse)
async def auto_discover_domain(request: DomainAutoDiscoveryRequest):
    """Analyze sample documents and suggest domain configuration.

    Uses LLM to:
    1. Identify common themes across samples
    2. Generate appropriate domain name (lowercase, underscores)
    3. Write description for embedding-based matching
    """
    # Sample first 2000 chars from each text
    samples = [text[:2000] for text in request.sample_texts]

    prompt = f"""Analyze these {len(samples)} document samples and determine their common domain/category.

Sample 1:
{samples[0]}

Sample 2:
{samples[1]}

Sample 3:
{samples[2]}
{"".join(f'''

Sample {i+1}:
{s}''' for i, s in enumerate(samples[3:], 3))}

Based on these samples, provide:
1. A short domain name (lowercase, underscores only, e.g., "tech_docs", "legal_contracts", "medical_records")
2. A detailed description (2-3 sentences) that captures what makes these documents unique. This will be used for automatic document classification.
3. 3-5 key characteristics/themes found in these documents.

Output in JSON format:
{{"name": "...", "description": "...", "characteristics": ["...", "..."], "confidence": 0.0-1.0}}
"""

    result = await llm_service.generate(prompt, model="qwen3:32b")
    parsed = json.loads(result)

    return DomainAutoDiscoveryResponse(
        suggested_name=parsed["name"],
        suggested_description=parsed["description"],
        detected_characteristics=parsed["characteristics"],
        confidence=parsed.get("confidence", 0.7)
    )
```

### Frontend Integration

```typescript
// frontend/src/components/admin/DomainAutoDiscovery.tsx

export function DomainAutoDiscovery({ onDiscovered }: Props) {
  const [sampleFiles, setSampleFiles] = useState<File[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const autoDiscover = useAutoDiscoverDomain();

  const handleAnalyze = async () => {
    if (sampleFiles.length < 3) {
      toast.error("Please upload at least 3 sample documents");
      return;
    }

    setIsAnalyzing(true);
    try {
      const texts = await Promise.all(
        sampleFiles.map(f => f.text().then(t => t.slice(0, 2000)))
      );

      const result = await autoDiscover.mutateAsync({ sample_texts: texts });
      onDiscovered(result);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="border-2 border-dashed rounded-lg p-6">
      <h3 className="font-semibold mb-4">Auto-Discover Domain</h3>
      <p className="text-gray-600 mb-4">
        Upload 3-10 sample documents and let AI suggest the domain configuration.
      </p>

      <FileDropZone
        accept=".txt,.md,.pdf"
        maxFiles={10}
        onFilesSelected={setSampleFiles}
        data-testid="sample-upload-dropzone"
      />

      {sampleFiles.length > 0 && (
        <div className="mt-4">
          <p className="text-sm text-gray-500">{sampleFiles.length} files selected</p>
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || sampleFiles.length < 3}
            className="mt-2 px-4 py-2 bg-primary text-white rounded"
            data-testid="analyze-samples-button"
          >
            {isAnalyzing ? "Analyzing..." : "Analyze Samples"}
          </button>
        </div>
      )}
    </div>
  );
}
```

### Deliverables
- [ ] `/admin/domains/auto-discover` API endpoint
- [ ] LLM prompt for domain discovery
- [ ] DomainAutoDiscovery frontend component
- [ ] Integration in NewDomainWizard (Step 0: Auto-Discovery OR Manual)
- [ ] Unit tests for discovery logic

---

## Feature 45.10: LLM-Grouped Ingestion (3 SP) - P1

### Konzept

Wenn mehrere Dokumente gleichzeitig verarbeitet werden, gruppiere sie nach dem Ziel-LLM (aus der Domain-Konfiguration), um Model Load/Unload zu minimieren.

### Implementierung

```python
# src/components/ingestion/grouped_processor.py

from collections import defaultdict
from typing import AsyncIterator
import structlog

logger = structlog.get_logger(__name__)


class GroupedIngestionProcessor:
    """Processes documents grouped by LLM model for optimal model loading."""

    def __init__(self, domain_service, extraction_service):
        self.domain_service = domain_service
        self.extraction_service = extraction_service
        self._current_model: str | None = None

    async def process_batch(
        self,
        documents: list[dict],  # [{text, domain, metadata}]
    ) -> AsyncIterator[dict]:
        """Process documents grouped by their domain's LLM model.

        Yields:
            Processing results for each document
        """
        # Step 1: Group documents by LLM model
        model_groups = defaultdict(list)

        for doc in documents:
            domain = await self.domain_service.get_domain(doc["domain"])
            llm_model = domain.llm_model if domain else "qwen3:32b"  # default
            model_groups[llm_model].append({
                **doc,
                "_llm_model": llm_model,
                "_domain_config": domain
            })

        logger.info(
            "documents_grouped_by_model",
            total=len(documents),
            groups={model: len(docs) for model, docs in model_groups.items()}
        )

        # Step 2: Process each model group sequentially
        for llm_model, group_docs in model_groups.items():
            logger.info("processing_model_group", model=llm_model, count=len(group_docs))

            # Load model once for the group
            if self._current_model != llm_model:
                await self._switch_model(llm_model)

            # Process all documents in this group
            for doc in group_docs:
                try:
                    result = await self._process_single_document(doc)
                    yield {"status": "success", "document": doc["metadata"], "result": result}
                except Exception as e:
                    logger.error("document_processing_failed", error=str(e))
                    yield {"status": "error", "document": doc["metadata"], "error": str(e)}

    async def _switch_model(self, model: str):
        """Switch to a different LLM model."""
        logger.info("switching_model", from_model=self._current_model, to_model=model)

        # Configure extraction service with new model
        self.extraction_service.set_model(model)
        self._current_model = model

    async def _process_single_document(self, doc: dict) -> dict:
        """Process a single document with the currently loaded model."""
        domain_config = doc["_domain_config"]

        # Use domain-specific prompts if available
        entities = await self.extraction_service.extract_entities(
            doc["text"],
            prompt=domain_config.entity_prompt if domain_config else None,
            examples=domain_config.entity_examples if domain_config else None
        )

        relations = await self.extraction_service.extract_relationships(
            doc["text"],
            entities,
            prompt=domain_config.relation_prompt if domain_config else None,
            examples=domain_config.relation_examples if domain_config else None
        )

        return {
            "entities": len(entities),
            "relations": len(relations),
            "model_used": self._current_model
        }


# Integration in Upload API
@router.post("/batch-upload")
async def batch_upload(
    files: list[UploadFile],
    domain_assignments: dict[str, str],  # filename -> domain
    background_tasks: BackgroundTasks
):
    """Upload multiple documents with domain assignments.

    Documents are automatically grouped by LLM model for efficient processing.
    """
    documents = []
    for file in files:
        text = await extract_text(file)
        domain = domain_assignments.get(file.filename, "general")
        documents.append({
            "text": text,
            "domain": domain,
            "metadata": {"filename": file.filename, "size": file.size}
        })

    # Start grouped processing in background
    job_id = str(uuid.uuid4())
    background_tasks.add_task(
        process_documents_grouped,
        job_id=job_id,
        documents=documents
    )

    return {
        "job_id": job_id,
        "documents_queued": len(documents),
        "status_url": f"/admin/jobs/{job_id}/status"
    }
```

### Monitoring

```python
# Model switching is logged for performance analysis
# Expected log output:
# {"event": "documents_grouped_by_model", "total": 10, "groups": {"qwen3:32b": 6, "qwen2.5:7b": 4}}
# {"event": "switching_model", "from_model": null, "to_model": "qwen3:32b"}
# {"event": "processing_model_group", "model": "qwen3:32b", "count": 6}
# {"event": "switching_model", "from_model": "qwen3:32b", "to_model": "qwen2.5:7b"}
# {"event": "processing_model_group", "model": "qwen2.5:7b", "count": 4}
```

### Deliverables
- [ ] GroupedIngestionProcessor class
- [ ] Model switching logic with logging
- [ ] Batch upload API endpoint
- [ ] Integration with existing ingestion pipeline
- [ ] Unit tests for grouping logic

---

## Feature 45.11: Training Data Augmentation (5 SP) - P1

### Konzept

Wenn der Benutzer weniger als 25 annotierte Samples hat, kann das LLM zusätzliche Trainingsdaten generieren:
- **Input:** 5-10 manuell annotierte Samples
- **Output:** 20-50 synthetisch generierte Samples
- **Methode:** LLM paraphrasiert Texte und passt Annotationen entsprechend an

### Implementierung

```python
# src/components/domain_training/data_augmenter.py

import structlog
from typing import AsyncIterator

logger = structlog.get_logger(__name__)


class TrainingDataAugmenter:
    """Generates additional training samples from seed data using LLM."""

    def __init__(self, llm_model: str = "qwen3:32b"):
        self.llm_model = llm_model

    async def augment_dataset(
        self,
        seed_samples: list[dict],  # [{text, entities, relations}]
        target_count: int = 30,
        diversity_factor: float = 0.7,
    ) -> AsyncIterator[dict]:
        """Generate augmented training samples.

        Args:
            seed_samples: Original annotated samples (minimum 5)
            target_count: Desired total sample count
            diversity_factor: 0.0-1.0, higher = more variation

        Yields:
            Augmented samples with same structure as input
        """
        if len(seed_samples) < 5:
            raise ValueError("At least 5 seed samples required for augmentation")

        samples_to_generate = target_count - len(seed_samples)
        if samples_to_generate <= 0:
            logger.info("no_augmentation_needed", seed_count=len(seed_samples))
            return

        logger.info(
            "starting_augmentation",
            seed_samples=len(seed_samples),
            to_generate=samples_to_generate
        )

        # Yield original samples first
        for sample in seed_samples:
            yield sample

        # Generate augmented samples
        generated = 0
        for seed in self._cycle_seeds(seed_samples, samples_to_generate):
            try:
                augmented = await self._augment_single(seed, diversity_factor)
                if augmented and self._validate_augmented(augmented, seed):
                    yield augmented
                    generated += 1
                    logger.debug("sample_augmented", count=generated)
            except Exception as e:
                logger.warning("augmentation_failed", error=str(e))
                continue

        logger.info("augmentation_complete", generated=generated)

    def _cycle_seeds(self, seeds: list[dict], count: int):
        """Cycle through seed samples to generate requested count."""
        idx = 0
        for _ in range(count):
            yield seeds[idx % len(seeds)]
            idx += 1

    async def _augment_single(
        self,
        seed: dict,
        diversity: float
    ) -> dict | None:
        """Augment a single sample using LLM paraphrasing."""
        prompt = f"""You are a training data augmentation assistant.

Given this annotated text sample, create a PARAPHRASED version that:
1. Preserves the same entities and their relationships
2. Uses different wording, sentence structure, and phrasing
3. Maintains factual accuracy
4. Diversity level: {diversity:.0%} (higher = more creative rewording)

ORIGINAL TEXT:
{seed['text']}

ENTITIES TO PRESERVE:
{seed['entities']}

RELATIONS TO PRESERVE:
{seed.get('relations', [])}

Generate a paraphrased version. Output JSON with:
- "text": the paraphrased text
- "entities": list of entity names (same as original, but as they appear in new text)
- "relations": list of relations (same structure as original)

Important: Entity names in the output must match how they appear in the paraphrased text.
If an entity name changes slightly (e.g., "Dr. Smith" → "Doctor Smith"), update accordingly.

Output (JSON only):
"""

        from src.components.llm_proxy import AegisLLMProxy
        llm = AegisLLMProxy()

        response = await llm.generate(
            prompt=prompt,
            model=self.llm_model,
            temperature=0.3 + (diversity * 0.4),  # 0.3-0.7 based on diversity
            max_tokens=2000
        )

        try:
            import json
            result = json.loads(response.strip())
            return {
                "text": result["text"],
                "entities": result["entities"],
                "relations": result.get("relations", []),
                "_augmented": True,
                "_seed_id": seed.get("id", "unknown")
            }
        except json.JSONDecodeError:
            logger.warning("invalid_json_response", response=response[:200])
            return None

    def _validate_augmented(self, augmented: dict, seed: dict) -> bool:
        """Validate augmented sample quality."""
        # Check text is different
        if augmented["text"] == seed["text"]:
            return False

        # Check entities are preserved (with some tolerance for name variations)
        seed_entities = set(e.lower() for e in seed["entities"])
        aug_entities = set(e.lower() for e in augmented["entities"])

        # At least 70% entity overlap required
        if seed_entities:
            overlap = len(seed_entities & aug_entities) / len(seed_entities)
            if overlap < 0.7:
                logger.debug("entity_overlap_too_low", overlap=overlap)
                return False

        # Check minimum text length
        if len(augmented["text"]) < len(seed["text"]) * 0.5:
            return False

        return True


# API Integration
@router.post("/{domain_id}/augment-dataset")
async def augment_training_dataset(
    domain_id: str,
    request: AugmentRequest
):
    """Augment a small training dataset with LLM-generated samples.

    Use this when you have fewer than 25 annotated samples.
    The LLM will paraphrase existing samples while preserving annotations.
    """
    if len(request.samples) < 5:
        raise HTTPException(
            status_code=400,
            detail="At least 5 seed samples required for augmentation"
        )

    if len(request.samples) >= request.target_count:
        return {
            "message": "No augmentation needed",
            "original_count": len(request.samples),
            "augmented_count": 0
        }

    domain = await domain_service.get_domain(domain_id)
    augmenter = TrainingDataAugmenter(llm_model=domain.llm_model)

    augmented_samples = []
    async for sample in augmenter.augment_dataset(
        seed_samples=request.samples,
        target_count=request.target_count,
        diversity_factor=request.diversity or 0.7
    ):
        augmented_samples.append(sample)

    return {
        "original_count": len(request.samples),
        "augmented_count": len(augmented_samples) - len(request.samples),
        "total_count": len(augmented_samples),
        "samples": augmented_samples
    }
```

### Frontend Integration

```typescript
// In DatasetUploadStep.tsx

function DatasetUploadStep({ dataset, onDatasetChange }: Props) {
  const [isAugmenting, setIsAugmenting] = useState(false);
  const augmentDataset = useAugmentDataset();

  const handleAugment = async () => {
    if (dataset.length >= 25) {
      toast.info("Dataset already has enough samples");
      return;
    }

    setIsAugmenting(true);
    try {
      const result = await augmentDataset.mutateAsync({
        samples: dataset,
        target_count: 30,
        diversity: 0.7
      });

      onDatasetChange(result.samples);
      toast.success(`Generated ${result.augmented_count} additional samples`);
    } finally {
      setIsAugmenting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Dataset preview */}
      <DatasetPreview samples={dataset} />

      {/* Augmentation suggestion */}
      {dataset.length > 0 && dataset.length < 25 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">
            You have {dataset.length} samples. DSPy works best with 25+ samples.
          </p>
          <button
            onClick={handleAugment}
            disabled={isAugmenting}
            className="mt-2 px-4 py-2 bg-yellow-600 text-white rounded"
            data-testid="augment-dataset-button"
          >
            {isAugmenting
              ? "Generating..."
              : `Generate ${30 - dataset.length} more samples with AI`}
          </button>
        </div>
      )}
    </div>
  );
}
```

### Deliverables
- [ ] TrainingDataAugmenter class
- [ ] LLM prompt for paraphrasing with entity preservation
- [ ] Validation logic for augmented samples
- [ ] `/admin/domains/{id}/augment-dataset` API endpoint
- [ ] Frontend integration in DatasetUploadStep
- [ ] Unit tests for augmentation logic

---

## Feature 45.12: Metric Configuration UI (3 SP) - P1

### Konzept

Der Benutzer kann die Evaluationsmetrik für DSPy-Training konfigurieren:
- **Preset-Auswahl:** F1, Recall-focused, Precision-focused
- **Gewichtung:** Entity vs. Relation Importance
- **Threshold:** Minimum Score für Few-Shot Demo Selection

### API Models

```python
# src/api/v1/domain_training.py

class MetricPreset(str, Enum):
    F1_BALANCED = "f1"              # 50/50 Precision/Recall
    RECALL_FOCUSED = "recall"        # Alle Entities finden, Extras ok
    PRECISION_FOCUSED = "precision"  # Weniger aber korrekt


class MetricConfiguration(BaseModel):
    """Configuration for DSPy training metrics."""
    preset: MetricPreset = MetricPreset.F1_BALANCED

    # Advanced: Custom weights (0.0 - 1.0)
    precision_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    recall_weight: float = Field(default=0.5, ge=0.0, le=1.0)

    # Entity vs Relation importance
    entity_weight: float = Field(default=0.8, ge=0.0, le=1.0)
    relation_weight: float = Field(default=0.2, ge=0.0, le=1.0)

    # Minimum score for a sample to be used as few-shot demo
    demo_threshold: float = Field(default=0.6, ge=0.0, le=1.0)

    @validator('recall_weight', always=True)
    def weights_sum_to_one(cls, v, values):
        if 'precision_weight' in values:
            # Auto-adjust recall_weight based on precision_weight
            return 1.0 - values['precision_weight']
        return v

    @validator('relation_weight', always=True)
    def entity_relation_sum(cls, v, values):
        if 'entity_weight' in values:
            return 1.0 - values['entity_weight']
        return v


# Update DomainCreateRequest
class DomainCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, pattern="^[a-z_]+$")
    description: str = Field(..., min_length=10, max_length=1000)
    llm_model: str = Field(default="qwen3:32b")
    metric_config: MetricConfiguration = Field(default_factory=MetricConfiguration)
```

### Backend Metric Factory

```python
# src/components/domain_training/metrics.py

from enum import Enum
from typing import Callable
import structlog

logger = structlog.get_logger(__name__)


class MetricFactory:
    """Creates metric functions based on configuration."""

    @staticmethod
    def create_entity_metric(config: MetricConfiguration) -> Callable:
        """Create entity extraction metric based on config."""

        def metric(example, prediction, trace=None):
            gold = set(e.lower() for e in example.entities)
            pred = set(e.lower() for e in prediction.entities)

            if not gold and not pred:
                return 1.0
            if not gold:
                return 0.0 if pred else 1.0
            if not pred:
                return 0.0

            intersection = len(gold & pred)
            precision = intersection / len(pred)
            recall = intersection / len(gold)

            # Weighted combination based on config
            p_weight = config.precision_weight
            r_weight = config.recall_weight

            if config.preset == MetricPreset.F1_BALANCED:
                # Standard F1
                if precision + recall == 0:
                    return 0.0
                return 2 * precision * recall / (precision + recall)

            elif config.preset == MetricPreset.RECALL_FOCUSED:
                # Weighted towards recall (find all entities)
                return 0.3 * precision + 0.7 * recall

            elif config.preset == MetricPreset.PRECISION_FOCUSED:
                # Weighted towards precision (avoid false positives)
                return 0.7 * precision + 0.3 * recall

            else:
                # Custom weights
                return p_weight * precision + r_weight * recall

        return metric

    @staticmethod
    def create_relation_metric(config: MetricConfiguration) -> Callable:
        """Create relation extraction metric based on config."""

        def metric(example, prediction, trace=None):
            def normalize(r):
                return (
                    r.get("subject", "").lower(),
                    r.get("predicate", "").lower(),
                    r.get("object", "").lower()
                )

            gold = set(normalize(r) for r in example.relations)
            pred = set(normalize(r) for r in prediction.relations)

            if not gold and not pred:
                return 1.0
            if not gold or not pred:
                return 0.0

            intersection = len(gold & pred)
            precision = intersection / len(pred)
            recall = intersection / len(gold)

            # Apply same weighting as entity metric
            p_weight = config.precision_weight
            r_weight = config.recall_weight

            return p_weight * precision + r_weight * recall

        return metric

    @staticmethod
    def create_combined_metric(config: MetricConfiguration) -> Callable:
        """Create combined metric weighing entities and relations."""
        entity_metric = MetricFactory.create_entity_metric(config)
        relation_metric = MetricFactory.create_relation_metric(config)

        def metric(example, prediction, trace=None):
            entity_score = entity_metric(example, prediction, trace)
            relation_score = relation_metric(example, prediction, trace)

            # Weighted combination
            combined = (
                config.entity_weight * entity_score +
                config.relation_weight * relation_score
            )

            return combined

        return metric
```

### Frontend Component

```typescript
// frontend/src/components/admin/MetricConfigStep.tsx

interface MetricConfig {
  preset: 'f1' | 'recall' | 'precision';
  precisionWeight: number;
  entityWeight: number;
  demoThreshold: number;
}

export function MetricConfigStep({
  config,
  onChange
}: {
  config: MetricConfig;
  onChange: (config: MetricConfig) => void;
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const presets = [
    {
      value: 'f1',
      label: 'F1 Score (Balanced)',
      description: 'Equal weight on finding all entities and avoiding false positives',
      recommended: true
    },
    {
      value: 'recall',
      label: 'Recall-focused',
      description: 'Prioritize finding all entities, tolerate some extras'
    },
    {
      value: 'precision',
      label: 'Precision-focused',
      description: 'Prioritize accuracy, may miss some entities'
    },
  ];

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">Evaluation Metric</h3>
      <p className="text-gray-600">
        Choose how DSPy should evaluate extraction quality during optimization.
      </p>

      {/* Preset Selection */}
      <div className="space-y-2">
        {presets.map((preset) => (
          <label
            key={preset.value}
            className={`
              flex items-start p-4 border rounded-lg cursor-pointer
              ${config.preset === preset.value ? 'border-primary bg-primary/5' : 'border-gray-200'}
            `}
            data-testid={`metric-preset-${preset.value}`}
          >
            <input
              type="radio"
              name="metric-preset"
              value={preset.value}
              checked={config.preset === preset.value}
              onChange={() => onChange({ ...config, preset: preset.value as MetricConfig['preset'] })}
              className="mt-1"
            />
            <div className="ml-3">
              <span className="font-medium">{preset.label}</span>
              {preset.recommended && (
                <span className="ml-2 text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                  Recommended
                </span>
              )}
              <p className="text-sm text-gray-500">{preset.description}</p>
            </div>
          </label>
        ))}
      </div>

      {/* Advanced Toggle */}
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-sm text-primary hover:underline"
        data-testid="toggle-advanced-metrics"
      >
        {showAdvanced ? '▼ Hide advanced options' : '▶ Show advanced options'}
      </button>

      {/* Advanced Options */}
      {showAdvanced && (
        <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
          {/* Entity vs Relation Weight */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Entity vs Relation Weight
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={config.entityWeight * 100}
              onChange={(e) => onChange({
                ...config,
                entityWeight: parseInt(e.target.value) / 100
              })}
              className="w-full"
              data-testid="entity-weight-slider"
            />
            <div className="flex justify-between text-sm text-gray-500">
              <span>Entities: {Math.round(config.entityWeight * 100)}%</span>
              <span>Relations: {Math.round((1 - config.entityWeight) * 100)}%</span>
            </div>
          </div>

          {/* Demo Threshold */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Minimum Score for Few-Shot Examples
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={config.demoThreshold * 100}
              onChange={(e) => onChange({
                ...config,
                demoThreshold: parseInt(e.target.value) / 100
              })}
              className="w-full"
              data-testid="demo-threshold-slider"
            />
            <div className="flex justify-between text-sm text-gray-500">
              <span>Threshold: {Math.round(config.demoThreshold * 100)}%</span>
              <span className="text-gray-400">
                (Lower = more demos, Higher = stricter selection)
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

### Integration in DSPy Optimizer

```python
# src/components/domain_training/dspy_optimizer.py (updated)

class DSPyOptimizer:
    def __init__(self, llm_model: str, metric_config: MetricConfiguration):
        self.llm_model = llm_model
        self.metric_config = metric_config
        self._configure_dspy()

    async def optimize_entity_extraction(self, training_data: list[dict], ...):
        # Use configured metric instead of hardcoded one
        metric = MetricFactory.create_entity_metric(self.metric_config)

        optimizer = dspy.BootstrapFewShot(
            metric=metric,
            max_bootstrapped_demos=4,
            max_labeled_demos=8,
            # Use configured threshold
            metric_threshold=self.metric_config.demo_threshold,
        )
        # ...
```

### Neo4j Schema Update

```cypher
// Add metric_config to Domain node
(:Domain {
    // ... existing fields ...
    metric_config: '{"preset": "f1", "entity_weight": 0.8, ...}',  // JSON
})
```

### Deliverables
- [ ] MetricConfiguration Pydantic model
- [ ] MetricFactory with preset + custom metrics
- [ ] MetricConfigStep frontend component
- [ ] Integration in Domain creation wizard (Step 1.5)
- [ ] Neo4j schema update for metric_config
- [ ] Unit tests for metric calculations

---

## Feature 45.13: E2E Tests (3 SP) - P2

### Playwright Tests

```typescript
// tests/e2e/domain-training.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Domain Training', () => {
  test('should create new domain and start training', async ({ page }) => {
    await page.goto('/admin/domains');

    // Click new domain button
    await page.click('[data-testid="new-domain-button"]');

    // Step 1: Configuration
    await page.fill('[data-testid="domain-name-input"]', 'test_domain');
    await page.fill('[data-testid="domain-description-input"]',
      'Test domain for technical documentation and API references');
    await page.selectOption('[data-testid="llm-model-select"]', 'qwen2.5:3b');
    await page.click('[data-testid="next-step-button"]');

    // Step 2: Dataset upload
    await page.setInputFiles('[data-testid="dataset-upload"]',
      'tests/fixtures/training_dataset.jsonl');
    await expect(page.locator('[data-testid="sample-count"]')).toContainText('10 samples');
    await page.click('[data-testid="start-training-button"]');

    // Step 3: Training progress
    await expect(page.locator('[data-testid="training-status"]')).toContainText('Training');

    // Wait for completion (with timeout)
    await expect(page.locator('[data-testid="training-status"]'))
      .toContainText('Ready', { timeout: 300000 });
  });

  test('should classify uploaded document to correct domain', async ({ page }) => {
    await page.goto('/admin/upload');

    // Upload a tech doc
    await page.setInputFiles('[data-testid="file-upload"]',
      'tests/fixtures/sample_api_doc.txt');

    // Wait for classification
    await expect(page.locator('[data-testid="domain-selector"]'))
      .toHaveValue('tech_docs');

    // Check confidence badge
    await expect(page.locator('[data-testid="confidence-badge"]'))
      .toContainText('High');
  });
});
```

### Deliverables
- [ ] Domain creation E2E test
- [ ] Training flow E2E test
- [ ] Document classification E2E test
- [ ] Test fixtures (JSONL dataset, sample docs)

---

## Feature 45.14: SSE Real-Time Training Stream (5 SP) - P1

### Konzept

Echtzeit-Streaming von Training-Events via Server-Sent Events (SSE) statt Polling. Das Frontend erhält sofort alle LLM-Interaktionen, Evaluationsergebnisse und Fortschrittsupdates ohne Verzögerung.

### Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   DSPy Train    │────────▶│ TrainingStream  │────────▶│   SSE Client    │
│   Background    │  emit   │   (Singleton)   │  yield  │   (Frontend)    │
│     Task        │         │                 │         │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
        │                          │
        │                          ▼
        │                   ┌─────────────────┐
        └──────────────────▶│  JSONL Logger   │
                            │  (Optional)     │
                            └─────────────────┘
```

### Event Types

```python
class EventType(str, Enum):
    # Progress events
    STARTED = "started"
    PHASE_CHANGED = "phase_changed"
    PROGRESS_UPDATE = "progress_update"
    COMPLETED = "completed"
    FAILED = "failed"

    # LLM interaction events (FULL content, not truncated)
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"

    # Sample processing events
    SAMPLE_PROCESSING = "sample_processing"
    SAMPLE_RESULT = "sample_result"

    # Evaluation events
    EVALUATION_START = "evaluation_start"
    EVALUATION_RESULT = "evaluation_result"

    # Optimization events
    BOOTSTRAP_ITERATION = "bootstrap_iteration"
    DEMO_SELECTED = "demo_selected"
```

### Backend SSE Endpoint

```python
# src/api/v1/domain_training.py

from fastapi.responses import StreamingResponse
from src.components.domain_training.training_stream import (
    get_training_stream,
    TrainingEvent
)

@router.get("/{domain_name}/training-stream")
async def stream_training_progress(
    domain_name: str,
    training_run_id: str,
):
    """Stream training progress via Server-Sent Events.

    Connect to this endpoint to receive real-time updates during training.
    Events include LLM prompts/responses, evaluation results, and progress.

    Example:
        const eventSource = new EventSource(
            `/admin/domains/tech_docs/training-stream?training_run_id=abc123`
        );
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data.event_type, data.message);
        };
    """
    stream = get_training_stream()

    if not stream.is_active(training_run_id):
        raise HTTPException(
            status_code=404,
            detail="Training stream not found or already completed"
        )

    async def event_generator():
        async for event in stream.subscribe(training_run_id):
            yield event.to_sse()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

### Training Event Emission

```python
# src/components/domain_training/training_runner.py (updated)

from src.components.domain_training.training_stream import (
    get_training_stream,
    EventType
)

async def run_dspy_optimization(...):
    stream = get_training_stream()

    # Start stream with optional JSONL logging
    stream.start_stream(
        training_run_id=training_run_id,
        domain=domain_name,
        log_path=log_path  # From API request
    )

    try:
        # Emit start event
        stream.emit(
            training_run_id=training_run_id,
            event_type=EventType.STARTED,
            domain=domain_name,
            progress_percent=0,
            phase="initializing",
            message="Starting DSPy optimization",
            data={"samples_count": len(dataset)}
        )

        # During entity extraction, emit LLM interactions
        def on_llm_call(prompt, response, score):
            stream.emit(
                training_run_id=training_run_id,
                event_type=EventType.LLM_RESPONSE,
                domain=domain_name,
                progress_percent=current_progress,
                phase="entity_extraction",
                message="LLM completed extraction",
                data={
                    "prompt": prompt,  # FULL prompt, not truncated
                    "response": response,  # FULL response
                    "score": score,
                    "sample_index": idx
                }
            )

        # ... optimization with callbacks ...

    finally:
        stream.close_stream(training_run_id)
```

### Frontend SSE Hook

```typescript
// frontend/src/hooks/useTrainingStream.ts

import { useEffect, useState, useCallback } from 'react';

interface TrainingEvent {
  event_type: string;
  timestamp: string;
  training_run_id: string;
  domain: string;
  progress_percent: number;
  phase: string;
  message: string;
  data: Record<string, unknown>;
}

export function useTrainingStream(
  domainName: string,
  trainingRunId: string | null,
  enabled: boolean = true
) {
  const [events, setEvents] = useState<TrainingEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [latestEvent, setLatestEvent] = useState<TrainingEvent | null>(null);

  useEffect(() => {
    if (!enabled || !trainingRunId) return;

    const eventSource = new EventSource(
      `/admin/domains/${domainName}/training-stream?training_run_id=${trainingRunId}`
    );

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    eventSource.onmessage = (event) => {
      const data: TrainingEvent = JSON.parse(event.data);
      setLatestEvent(data);
      setEvents((prev) => [...prev, data]);

      // Auto-close on completion
      if (data.event_type === 'completed' || data.event_type === 'failed') {
        eventSource.close();
        setIsConnected(false);
      }
    };

    eventSource.onerror = () => {
      setError(new Error('Connection lost'));
      setIsConnected(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [domainName, trainingRunId, enabled]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    events,
    latestEvent,
    isConnected,
    error,
    clearEvents,
    progress: latestEvent?.progress_percent ?? 0,
    phase: latestEvent?.phase ?? 'pending',
  };
}
```

### Live Log Display Component

```typescript
// frontend/src/components/admin/TrainingLiveLog.tsx

import { useRef, useEffect } from 'react';
import { useTrainingStream, TrainingEvent } from '../../hooks/useTrainingStream';

interface TrainingLiveLogProps {
  domainName: string;
  trainingRunId: string;
  onComplete?: () => void;
}

export function TrainingLiveLog({
  domainName,
  trainingRunId,
  onComplete
}: TrainingLiveLogProps) {
  const logRef = useRef<HTMLDivElement>(null);
  const { events, isConnected, progress, phase } = useTrainingStream(
    domainName,
    trainingRunId
  );

  // Auto-scroll to bottom
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [events]);

  // Handle completion
  useEffect(() => {
    const lastEvent = events[events.length - 1];
    if (lastEvent?.event_type === 'completed') {
      onComplete?.();
    }
  }, [events, onComplete]);

  return (
    <div className="space-y-4" data-testid="training-live-log">
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="font-medium">{phase}</span>
          <span>{progress.toFixed(1)}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-600 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Connection Status */}
      <div className="flex items-center gap-2 text-sm">
        <span
          className={`w-2 h-2 rounded-full ${
            isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
          }`}
        />
        <span className="text-gray-600">
          {isConnected ? 'Live connected' : 'Disconnected'}
        </span>
      </div>

      {/* Event Log */}
      <div
        ref={logRef}
        className="h-96 overflow-y-auto font-mono text-sm bg-gray-900 text-gray-100 rounded-lg p-4 space-y-2"
        data-testid="event-log"
      >
        {events.map((event, idx) => (
          <TrainingEventRow key={idx} event={event} />
        ))}
      </div>
    </div>
  );
}

function TrainingEventRow({ event }: { event: TrainingEvent }) {
  const timestamp = new Date(event.timestamp).toLocaleTimeString();

  // Color coding by event type
  const typeColors: Record<string, string> = {
    llm_request: 'text-yellow-400',
    llm_response: 'text-green-400',
    sample_processing: 'text-blue-400',
    sample_result: 'text-cyan-400',
    evaluation_result: 'text-purple-400',
    failed: 'text-red-400',
    completed: 'text-green-500',
  };

  const color = typeColors[event.event_type] || 'text-gray-400';

  return (
    <div className="border-b border-gray-800 pb-2">
      <div className="flex items-start gap-2">
        <span className="text-gray-500 text-xs">{timestamp}</span>
        <span className={`font-semibold ${color}`}>
          [{event.event_type}]
        </span>
        <span className="text-gray-300">{event.message}</span>
      </div>

      {/* Show full data for LLM events */}
      {(event.event_type === 'llm_request' || event.event_type === 'llm_response') && (
        <div className="mt-2 ml-4">
          {event.data.prompt && (
            <details className="text-xs">
              <summary className="cursor-pointer text-yellow-300">
                Prompt ({(event.data.prompt as string).length} chars)
              </summary>
              <pre className="mt-1 p-2 bg-gray-800 rounded whitespace-pre-wrap max-h-64 overflow-y-auto">
                {event.data.prompt as string}
              </pre>
            </details>
          )}
          {event.data.response && (
            <details className="text-xs mt-1">
              <summary className="cursor-pointer text-green-300">
                Response ({(event.data.response as string).length} chars)
              </summary>
              <pre className="mt-1 p-2 bg-gray-800 rounded whitespace-pre-wrap max-h-64 overflow-y-auto">
                {event.data.response as string}
              </pre>
            </details>
          )}
          {event.data.score !== undefined && (
            <span className="text-purple-300 text-xs">
              Score: {(event.data.score as number).toFixed(3)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
```

### Deliverables
- [ ] TrainingEventStream singleton class
- [ ] SSE endpoint `/admin/domains/{name}/training-stream`
- [ ] Event emission in training_runner.py
- [ ] useTrainingStream React hook
- [ ] TrainingLiveLog component with auto-scroll
- [ ] Full LLM prompt/response display (expandable)
- [ ] Unit tests for stream management

---

## Feature 45.15: JSONL Training Log Export (3 SP) - P1

### Konzept

Optionale Speicherung aller Training-Events als JSONL-Datei für spätere DSPy-Evaluation und Debugging. Der Benutzer gibt im UI einen Log-Pfad an, alle Events werden vollständig (nicht gekürzt) gespeichert.

### API Request Update

```python
# src/api/v1/domain_training.py

class TrainingDataset(BaseModel):
    samples: list[TrainingSample]
    log_path: str | None = Field(
        default=None,
        description="Optional path to save training log as JSONL. "
                    "All events (prompts, responses, scores) will be saved."
    )

@router.post("/{domain_name}/train")
async def start_training(
    domain_name: str,
    dataset: TrainingDataset,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    # ... validation ...

    # Pass log_path to training task
    background_tasks.add_task(
        run_dspy_optimization,
        domain_name=domain_name,
        training_run_id=training_log["id"],
        dataset=[s.model_dump() for s in dataset.samples],
        log_path=dataset.log_path,  # NEW
    )

    return {
        "message": "Training started",
        "training_run_id": training_log["id"],
        "log_path": dataset.log_path,
        # ...
    }
```

### JSONL Log Format

```jsonl
{"event_type": "started", "timestamp": "2025-12-12T18:30:00Z", "training_run_id": "abc123", "domain": "tech_docs", "progress_percent": 0, "phase": "initializing", "message": "Starting DSPy optimization", "data": {"samples_count": 12}}
{"event_type": "llm_request", "timestamp": "2025-12-12T18:30:05Z", "training_run_id": "abc123", "domain": "tech_docs", "progress_percent": 15, "phase": "entity_extraction", "message": "Sending prompt to LLM", "data": {"prompt": "Extract key entities from the following text...\n\nText: OMNITRACKER Task Management - Die Aufgaben...", "sample_index": 0}}
{"event_type": "llm_response", "timestamp": "2025-12-12T18:30:12Z", "training_run_id": "abc123", "domain": "tech_docs", "progress_percent": 18, "phase": "entity_extraction", "message": "LLM completed extraction", "data": {"prompt": "Extract key entities...", "response": "[\"OMNITRACKER\", \"Task Management\", \"Aufgabenmanagement\", ...]", "expected": ["OMNITRACKER", "Task Management", ...], "score": 0.85, "sample_index": 0}}
{"event_type": "evaluation_result", "timestamp": "2025-12-12T18:32:00Z", "training_run_id": "abc123", "domain": "tech_docs", "progress_percent": 50, "phase": "entity_extraction", "message": "Entity extraction evaluation complete", "data": {"precision": 0.82, "recall": 0.91, "f1": 0.86, "samples_evaluated": 12}}
{"event_type": "completed", "timestamp": "2025-12-12T18:45:00Z", "training_run_id": "abc123", "domain": "tech_docs", "progress_percent": 100, "phase": "completed", "message": "Training completed successfully", "data": {"entity_f1": 0.86, "relation_f1": 0.72, "total_duration_seconds": 900}}
```

### Frontend: Log Path Input

```typescript
// frontend/src/components/admin/DatasetUploadStep.tsx (updated)

interface DatasetUploadStepProps {
  dataset: TrainingSample[];
  logPath: string;
  onUpload: (samples: TrainingSample[]) => void;
  onLogPathChange: (path: string) => void;
  onBack: () => void;
  onNext: () => void;
}

export function DatasetUploadStep({
  dataset,
  logPath,
  onUpload,
  onLogPathChange,
  onBack,
  onNext
}: DatasetUploadStepProps) {
  return (
    <div className="space-y-6" data-testid="dataset-upload-step">
      {/* ... file upload section ... */}

      {/* Log Path Input */}
      <div className="space-y-2">
        <label
          htmlFor="log-path"
          className="block text-sm font-medium text-gray-700"
        >
          Training Log Path (Optional)
        </label>
        <div className="flex gap-2">
          <input
            id="log-path"
            type="text"
            value={logPath}
            onChange={(e) => onLogPathChange(e.target.value)}
            placeholder="/var/log/aegis/training/my_domain_2025-12-12.jsonl"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
            data-testid="log-path-input"
          />
          <button
            type="button"
            onClick={() => {
              const defaultPath = `/var/log/aegis/training/${Date.now()}.jsonl`;
              onLogPathChange(defaultPath);
            }}
            className="px-3 py-2 text-sm bg-gray-100 rounded-lg hover:bg-gray-200"
            data-testid="generate-log-path"
          >
            Auto
          </button>
        </div>
        <p className="text-sm text-gray-500">
          All training events (LLM prompts, responses, scores) will be saved to this file
          for later analysis and DSPy evaluation.
        </p>
      </div>

      {/* Actions */}
      <div className="flex justify-between pt-4 border-t">
        <button onClick={onBack}>Back</button>
        <button
          onClick={onNext}
          disabled={dataset.length === 0}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg"
          data-testid="start-training-button"
        >
          Start Training
        </button>
      </div>
    </div>
  );
}
```

### Log File Management

```python
# src/components/domain_training/training_stream.py

class TrainingEventStream:
    def start_stream(
        self,
        training_run_id: str,
        domain: str,
        log_path: str | None = None,
    ) -> None:
        """Start a new training event stream.

        Args:
            training_run_id: Unique training run identifier
            domain: Domain being trained
            log_path: Optional path for JSONL log file (FULL events, not truncated)
        """
        # Create log file if path provided
        file_handle = None
        path = None
        if log_path:
            path = Path(log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            file_handle = open(path, "w", encoding="utf-8")
            logger.info("jsonl_log_file_created", path=str(path))

        state = StreamState(
            training_run_id=training_run_id,
            domain=domain,
            log_path=path,
            queue=asyncio.Queue(),
            log_file=file_handle,
        )
        self._streams[training_run_id] = state

    def emit_event(self, training_run_id: str, event: TrainingEvent) -> None:
        """Emit an event to the stream."""
        state = self._streams.get(training_run_id)
        if not state:
            return

        # Write FULL event to JSONL log file (not truncated!)
        if state.log_file:
            state.log_file.write(event.to_json() + "\n")
            state.log_file.flush()  # Ensure immediate write

        # Put in queue for SSE consumers
        state.queue.put_nowait(event)

    def close_stream(self, training_run_id: str) -> None:
        """Close a training stream."""
        state = self._streams.get(training_run_id)
        if state and state.log_file:
            state.log_file.close()
            logger.info(
                "jsonl_log_file_closed",
                path=str(state.log_path),
                event_count=state.event_count,
            )
        # ... rest of cleanup ...
```

### Example: Using JSONL for DSPy Evaluation

```python
# scripts/evaluate_from_log.py
"""Evaluate DSPy training from JSONL log file."""

import json
from pathlib import Path


def load_training_log(log_path: str) -> list[dict]:
    """Load all events from JSONL log."""
    events = []
    with open(log_path, "r") as f:
        for line in f:
            events.append(json.loads(line))
    return events


def extract_llm_interactions(events: list[dict]) -> list[dict]:
    """Extract LLM request/response pairs for analysis."""
    interactions = []
    for event in events:
        if event["event_type"] == "llm_response":
            interactions.append({
                "prompt": event["data"]["prompt"],
                "response": event["data"]["response"],
                "expected": event["data"].get("expected"),
                "score": event["data"].get("score"),
                "phase": event["phase"],
            })
    return interactions


def compute_metrics(interactions: list[dict]) -> dict:
    """Compute aggregate metrics from logged interactions."""
    scores = [i["score"] for i in interactions if i["score"] is not None]
    return {
        "total_interactions": len(interactions),
        "avg_score": sum(scores) / len(scores) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "max_score": max(scores) if scores else 0,
    }


if __name__ == "__main__":
    import sys
    log_path = sys.argv[1] if len(sys.argv) > 1 else "training.jsonl"

    events = load_training_log(log_path)
    interactions = extract_llm_interactions(events)
    metrics = compute_metrics(interactions)

    print(f"Loaded {len(events)} events from {log_path}")
    print(f"LLM Interactions: {metrics['total_interactions']}")
    print(f"Average Score: {metrics['avg_score']:.3f}")
    print(f"Score Range: {metrics['min_score']:.3f} - {metrics['max_score']:.3f}")
```

### Deliverables
- [ ] `log_path` parameter in TrainingDataset model
- [ ] JSONL file writing in TrainingEventStream
- [ ] Log path input in DatasetUploadStep
- [ ] Auto-generate log path button
- [ ] Example evaluation script
- [ ] Documentation for log format

---

## Feature 45.16: DSPy/AnyLLM Integration (3 SP) - P2

### Konzept

Integration von DSPy Training mit dem AegisLLMProxy (AnyLLM) System für einheitliche LLM-Nutzung und Cost Tracking. Statt direkter Ollama-Konfiguration soll DSPy über den bestehenden AegisLLMProxy geroutet werden.

### Ziele

1. **Einheitliches LLM Routing** - DSPy nutzt AegisLLMProxy statt direkter Ollama-Verbindung
2. **Cost Measuring** - Alle DSPy LLM-Calls werden im bestehenden Cost Tracking erfasst
3. **Provider Flexibilität** - Ermöglicht Cloud-Provider als Fallback (DashScope, OpenAI)
4. **Transparenz** - Training-Kosten werden im Admin UI sichtbar

### Technische Änderungen

```python
# src/components/domain_training/dspy_optimizer.py

# AKTUELL (direkte Ollama-Konfiguration):
self.lm = self._dspy.LM(
    model=f"ollama_chat/{self.llm_model}",
    api_base="http://localhost:11434",
    api_key="",
)

# ZIEL (über AegisLLMProxy):
from src.components.llm_proxy import get_llm_proxy

proxy = get_llm_proxy()
# Option A: Custom DSPy LM wrapper für AegisLLMProxy
# Option B: DSPy litellm backend mit Proxy-Endpoint

# Cost Tracking automatisch durch Proxy
```

### UI-Erweiterungen

```typescript
// TrainingProgressStep.tsx - Cost Anzeige
interface TrainingMetrics {
  // ... existing metrics ...
  llm_cost?: {
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    estimated_cost_usd?: number;
    model: string;
    provider: string;
  };
}
```

### Implementierungs-Optionen

| Option | Beschreibung | Aufwand |
|--------|--------------|---------|
| A: Custom LM Wrapper | DSPy LM Klasse die AegisLLMProxy nutzt | Mittel |
| B: LiteLLM Proxy Mode | DSPy → LiteLLM → AegisLLMProxy | Gering |
| C: Pre-Processing | AegisLLMProxy als pre-processor vor Ollama | Gering |

### Tasks

- [ ] Analyse: DSPy LM Backend Architektur
- [ ] Entscheidung: Welche Integration-Option
- [ ] Custom DSPy LM Wrapper für AegisLLMProxy (wenn Option A)
- [ ] Cost Tracking in Training Events emittieren
- [ ] Training Metrics um Kosten erweitern
- [ ] Frontend: Kosten-Anzeige in TrainingProgressStep
- [ ] ADR: Integration Strategy (ADR-046)

### Akzeptanzkriterien

- [ ] DSPy Training nutzt AegisLLMProxy
- [ ] Alle LLM-Calls werden im Cost Tracking erfasst
- [ ] Training-Kosten im UI sichtbar
- [ ] Fallback zu Cloud-Provider funktioniert
- [ ] Keine Regression bei Training Performance

---

## Feature 45.17: Embedding-based Semantic Matching (1 SP) - P1 ✅

### Konzept

Replace exact string matching in DSPy evaluation metrics with BGE-M3 embedding-based cosine similarity. This improves F1 scores for semantically equivalent extractions that differ textually (e.g., "verfügt über" vs "hat", "Rechtesystem" vs "Rechte-System").

### Problem

DSPy BootstrapFewShot evaluates candidate prompts using a metric function. With exact string matching:
- `{"subject": "OMNITRACKER", "predicate": "verfügt über", "object": "Rechtesystem"}`
- `{"subject": "OMNITRACKER", "predicate": "hat", "object": "Rechte-System"}`

These semantically identical relations would have F1 = 0.0 due to string mismatch.

### Lösung

`SemanticMatcher` class in `src/components/domain_training/semantic_matcher.py`:

```python
class SemanticMatcher:
    def __init__(self, threshold: float = 0.75, predicate_weight: float = 0.4):
        """
        threshold: Minimum cosine similarity for match (0.0-1.0)
        predicate_weight: Weight for predicate in relation matching
        """

    def compute_entity_metrics(self, gold_entities, pred_entities) -> dict:
        """Compute P/R/F1 using semantic matching instead of exact set intersection."""

    def compute_relation_metrics(self, gold_relations, pred_relations) -> dict:
        """Compute P/R/F1 using weighted semantic similarity across s/p/o."""
```

### Key Features

- **BGE-M3 Embeddings**: Multilingual support (German documents)
- **Configurable Thresholds**: Entity matching >= 0.75, Relation matching >= 0.70
- **Weighted Relation Matching**: Predicate weight 0.4, Subject/Object 0.3 each
- **LRU Cache**: 1000 embeddings cached for efficiency
- **Graceful Fallback**: Token overlap (Jaccard) when embeddings unavailable

### Commits

- `d0b955f feat(sprint45): Add embedding-based semantic matching (Feature 45.17)`

---

## Success Criteria

### Feature 45.1-45.3: Backend
- [ ] Domain registry stores optimized prompts
- [ ] DSPy optimization produces valid prompts
- [ ] Training API handles background tasks correctly
- [ ] Prompts extractable without DSPy dependency

### Feature 45.4-45.5: Admin UI
- [ ] Domain creation wizard works end-to-end
- [ ] Real-time training progress visible
- [ ] Training logs streamed to UI
- [ ] Error states handled gracefully

### Feature 45.6-45.7: Classification
- [ ] Documents classified with >80% accuracy to correct domain
- [ ] Upload page shows domain suggestions
- [ ] Manual override possible
- [ ] Fallback to "general" when confidence < 50%

### Feature 45.8-45.9: Integration
- [ ] Generic prompt works for unknown domains
- [ ] All E2E tests pass
- [ ] No DSPy dependency in production code

---

## Technical Debt Created

- **TD-064:** DSPy version pinning for reproducible prompts
- **TD-065:** Domain embedding caching for faster classification
- **TD-066:** Training dataset validation and preprocessing

---

## References

- [DSPy Documentation](https://dspy.ai/)
- [DSPy Saving and Loading](https://dspy.ai/tutorials/saving/)
- [KGGen Repository](https://github.com/stair-lab/kg-gen) - Inspiration for DSPy signatures
- Sprint 44: Pipeline Monitoring (prerequisite)
- ADR-045: Domain-Specific Extraction Strategy (TBD)

---

## Sprint Closure Notes (2025-12-12)

### Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| 45.1 Domain Registry Neo4j | ✅ | Domain nodes with embeddings |
| 45.2 DSPy Integration Service | ✅ | BootstrapFewShot optimization |
| 45.3 Training Status API | ✅ | Real-time progress via SSE |
| 45.4 Domain Training Admin UI | ✅ | 3-step wizard |
| 45.5 Training Progress Display | ✅ | Live log with SSE streaming |
| 45.6 Domain Classifier | ✅ | Embedding-based classification |
| 45.7 Upload Integration | ✅ | Domain suggestion on upload |
| 45.12 Metric Configuration UI | ✅ | DSPy metric thresholds configurable |
| 45.13 SSE Training Stream | ✅ | Full content streaming (not truncated) |
| 45.17 Semantic Matching | ✅ | BGE-M3 embedding-based evaluation |

### Deferred Features (Future Sprints)

| Feature | Reason |
|---------|--------|
| 45.8 Generic Fallback Prompt | Not yet needed, current setup works |
| 45.14 Prompt Template Comparison | Nice-to-have, low priority |
| 45.15 JSONL Event Logging | Optional disk logging |
| 45.16 DSPy/AnyLLM Integration | Cost tracking via proxy |

### Open Items for Future Sprints

1. **Manual Testing of Domain Concept**
   - End-to-end testing with real domain data
   - Verify extraction quality improvements
   - Measure F1 improvement with semantic matching

2. **Admin UI Improvements**
   - Smaller fonts for better density
   - Fewer graphical elements (streamline UI)
   - Combine admin areas into sections on one page
   - Reduce visual clutter, focus on functionality

3. **Domain Auto-Discovery Enhancement**
   - Auto-create domain title and description from uploaded document
   - LLM-based analysis of sample document for metadata
   - Suggest appropriate domain name based on content

### Key Commits (Sprint 45)

```
d0b955f feat(sprint45): Add embedding-based semantic matching (Feature 45.17)
90ca182 feat(sprint45): SSE streaming, DSPy fixes, and progress tracking
54f5020 fix(dspy): Use proper DSPy Signature classes
07b0fa5 fix(dspy): Use async-safe context for DSPy configuration
20f753f fix(domain-training): Fix training workflow bugs
4da6d97 refactor(frontend): Standardize JSONL format to match API directly
ee52bc0 docs(sprint45): Add Metric Configuration UI (Feature 45.12)
ea4ce78 docs(sprint45): Complete Sprint 45 plan with DSPy domain training
945295c feat(evaluation): Add model quality comparison with Precision/Recall/F1
```

### Lessons Learned

1. **Thread-Local Context**: DSPy LM configuration is thread-local; must re-configure inside ThreadPoolExecutor workers
2. **SSE Timing**: Frontend needs ~500ms delay to establish connection before backend starts streaming
3. **Semantic Matching**: Exact string matching gives poor F1 for German text; embeddings solve this
4. **Progress Tracking**: Async callbacks require careful handling with `asyncio.iscoroutinefunction()`
