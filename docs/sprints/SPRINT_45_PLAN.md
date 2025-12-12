# Sprint 45: Domain-Specific Prompt Optimization mit DSPy

**Status:** PLANNED
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
| 45.12: E2E Tests | 3 SP | P2 | Testing |
| **Total** | **55 SP** | | |

### Priority Overview
- **P0 (Must Have):** Features 45.1-45.3 - Backend Core (16 SP)
- **P1 (Should Have):** Features 45.4-45.7, 45.9-45.11 - UI + Auto-Discovery + Augmentation (34 SP)
- **P2 (Nice to Have):** Features 45.8, 45.12 - Fallback + E2E Tests (5 SP)

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

## Feature 45.12: E2E Tests (3 SP) - P2

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
