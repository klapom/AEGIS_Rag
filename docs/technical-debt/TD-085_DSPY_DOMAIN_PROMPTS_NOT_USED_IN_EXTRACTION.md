# TD-085: DSPy Domain-Optimized Prompts Not Used in Entity/Relation Extraction

**Status:** Open
**Priority:** 🔴 **CRITICAL** - Core Feature Broken
**Effort:** 21 SP
**Sprint:** 76-77 (Multi-sprint feature)
**Created:** 2025-01-05
**Root Cause:** Sprint 45 built Domain Training but never integrated with extraction pipeline

---

## Problem

**CRITICAL MISSING INTEGRATION:** DSPy domain training optimizes prompts per domain, but these optimized prompts are **NEVER USED** during document ingestion!

### What Was Supposed to Happen (Sprint 45 Intent)

1. User creates domain "medical_reports" with description
2. User uploads training samples (entities/relations examples)
3. DSPy optimizes extraction prompts for medical terminology
4. **Documents ingested into "medical_reports" domain use optimized prompts**
5. Better entity/relation extraction quality for medical docs

### What Actually Happens (BROKEN)

1. User creates domain "medical_reports" ✓
2. User uploads training samples ✓
3. DSPy optimizes prompts ✓
4. **Optimized prompts stored in Redis** ✓
5. **Documents ingested → USE DEFAULT PROMPTS** ❌ **BROKEN!**
6. **Optimized prompts NEVER USED!** ❌ **ALL TRAINING WASTED!**

---

## Evidence

### 1. Domain Training Works (Sprint 45)

```python
# src/api/v1/domain_training.py - Training endpoint exists
@router.post("/{domain}/train")
async def start_training(
    domain: str,
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
):
    # DSPy optimizes prompts for this domain
    optimizer = BootstrapFewShot()
    optimized_module = optimizer.compile(
        student=extraction_signature,
        trainset=training_data,
    )
    # Saves to Redis: f"dspy_domain:{domain}:optimized_prompt"
```

**Result:** Optimized prompts stored in Redis ✓

### 2. Ingestion Pipeline Ignores Domains

```python
# src/components/ingestion/ingestion_state.py
class IngestionState(TypedDict, total=False):
    document_path: str
    document_id: str
    # ❌ NO domain_id field!
    # ❌ NO way to specify which domain's prompts to use!
```

```python
# src/components/ingestion/nodes/graph_extraction.py
async def graph_extraction_node(state: IngestionState):
    # Uses ThreePhaseExtractor with DEFAULT prompts
    extractor = ThreePhaseExtractor()  # ❌ No domain parameter!
    entities = await extractor.extract(chunk_text)  # ❌ Uses generic prompts!
```

**Result:** Optimized prompts in Redis are NEVER retrieved! ❌

### 3. No Connection Between Domain & Ingestion

**Upload API has NO domain parameter:**
```python
# src/api/v1/admin_indexing.py
@router.post("/indexing/add")
async def add_documents(file_paths: list[str]):
    # ❌ No domain_id parameter!
    # ❌ Cannot specify which domain's prompts to use!
```

**Frontend has NO domain selector:**
```tsx
// frontend/src/pages/admin/AdminIndexingPage.tsx
// ❌ No domain selection UI!
// ❌ User cannot choose domain for upload!
```

---

## Impact Analysis

### Wasted Effort

| Sprint | Feature | SP Invested | Current Value |
|--------|---------|-------------|---------------|
| 45 | Domain Training API | 8 SP | **0% (unused)** |
| 45 | DSPy Optimizer Integration | 13 SP | **0% (unused)** |
| 45 | Training Dataset Upload | 5 SP | **0% (unused)** |
| 45 | Domain Training UI | 8 SP | **0% (unused)** |
| **Total** | **Domain Training System** | **34 SP** | **COMPLETELY WASTED** |

### Missing Benefits

**What We're Missing:**

1. **Domain-Specific Extraction Quality**
   - Medical docs: Extract "diagnosis", "treatment", "medication" properly
   - Legal docs: Extract "parties", "clauses", "obligations" accurately
   - Technical docs: Extract "components", "dependencies", "configurations"

2. **LLM Model Selection Per Domain**
   - Complex domains (medical): Use larger model (qwen3:32b)
   - Simple domains (FAQs): Use smaller model (llama3.2:8b)
   - Currently: All docs use same generic extractor

3. **Prompt Optimization ROI**
   - DSPy training takes 10-30 minutes per domain
   - Optimized prompts give +20-40% extraction accuracy
   - **But we're not using them!**

---

## Root Cause

**Architectural Disconnect:**

```
┌─────────────────────┐         ┌─────────────────────┐
│  Domain Training    │         │   Ingestion         │
│  (Sprint 45)        │         │   Pipeline          │
├─────────────────────┤         ├─────────────────────┤
│ - Create domain     │         │ - Parse documents   │
│ - Upload samples    │         │ - Extract entities  │
│ - Optimize prompts  │         │ - Store in Neo4j    │
│ - Store in Redis    │         │                     │
└─────────────────────┘         └─────────────────────┘
         ↓                                ↑
    Optimized Prompts            Uses DEFAULT Prompts
    stored in Redis              (ignores Redis!)
         ↓                                ↑
         └────────── NO CONNECTION ───────┘
                    ❌ BROKEN ❌
```

**Nobody built the bridge between these two systems!**

---

## Solution Design

### Architecture Integration

```
User Upload Flow:
─────────────────

1. User selects domain: "medical_reports"
2. Upload API receives domain_id
3. Ingestion pipeline loads optimized prompts from Redis
4. ThreePhaseExtractor uses domain-specific prompts
5. Better entity extraction for medical terminology
```

### Required Changes

#### 1. **IngestionState - Add Domain Field (1 SP)**

```python
# src/components/ingestion/ingestion_state.py
class IngestionState(TypedDict, total=False):
    document_path: str
    document_id: str
    namespace_id: str  # Multi-tenant isolation (TD-084)
    domain_id: str | None  # ✅ NEW: Domain for prompt selection
    # ...
```

#### 2. **ThreePhaseExtractor - Domain-Aware (5 SP)**

```python
# src/components/graph_rag/extractors/three_phase_extractor.py
class ThreePhaseExtractor:
    def __init__(
        self,
        domain_id: str | None = None,  # ✅ NEW parameter
        llm_model: str | None = None,
    ):
        self.domain_id = domain_id

        # Load domain-optimized prompts from Redis if available
        if domain_id:
            optimized_prompts = await self._load_domain_prompts(domain_id)
            if optimized_prompts:
                logger.info(
                    "using_domain_optimized_prompts",
                    domain_id=domain_id,
                    prompt_version=optimized_prompts["version"],
                )
                self.entity_prompt = optimized_prompts["entity_extraction"]
                self.relation_prompt = optimized_prompts["relation_extraction"]
            else:
                logger.warning(
                    "domain_prompts_not_found_using_defaults",
                    domain_id=domain_id,
                )
                self.entity_prompt = DEFAULT_ENTITY_PROMPT
                self.relation_prompt = DEFAULT_RELATION_PROMPT
        else:
            # No domain specified, use defaults
            self.entity_prompt = DEFAULT_ENTITY_PROMPT
            self.relation_prompt = DEFAULT_RELATION_PROMPT

    async def _load_domain_prompts(
        self, domain_id: str
    ) -> dict[str, Any] | None:
        """Load optimized prompts for domain from Redis.

        Redis key: f"dspy_domain:{domain_id}:optimized_prompt"
        """
        from src.components.memory import get_redis_memory

        redis = await get_redis_memory()
        redis_client = await redis.client

        prompt_key = f"dspy_domain:{domain_id}:optimized_prompt"
        cached = await redis_client.get(prompt_key)

        if cached:
            import json
            return json.loads(cached)

        return None
```

#### 3. **Graph Extraction Node - Use Domain (3 SP)**

```python
# src/components/ingestion/nodes/graph_extraction.py
async def graph_extraction_node(state: IngestionState) -> IngestionState:
    domain_id = state.get("domain_id")  # ✅ Get domain from state

    # Create domain-aware extractor
    extractor = ThreePhaseExtractor(
        domain_id=domain_id,  # ✅ Pass domain!
        llm_model=state.get("llm_model", "llama3.2:8b"),
    )

    # Extract with optimized prompts
    entities = await extractor.extract(chunk_text)
    # Now uses domain-specific prompts! ✓
```

#### 4. **Backend API - Accept Domain (3 SP)**

```python
# src/api/v1/admin_indexing.py

class AddDocumentsRequest(BaseModel):
    file_paths: list[str]
    namespace_id: str = Field(default="default")
    domain_id: str | None = Field(  # ✅ NEW!
        default=None,
        description="Domain for optimized extraction prompts"
    )

@router.post("/indexing/add")
async def add_documents_endpoint(request: AddDocumentsRequest):
    state = IngestionState(
        document_path=file_path,
        document_id=doc_id,
        namespace_id=request.namespace_id,
        domain_id=request.domain_id,  # ✅ Pass to pipeline!
        # ...
    )
```

#### 5. **Frontend UI - Domain Selector (5 SP)**

```tsx
// frontend/src/pages/admin/AdminIndexingPage.tsx
import { useDomains } from '../../hooks/useDomainTraining';

export function AdminIndexingPage() {
  const { data: domains } = useDomains();
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);

  return (
    <>
      {/* Domain Selector */}
      <div className="mb-4">
        <label className="text-sm font-medium text-gray-700 mb-2 block">
          Extraction Domain (Optional)
        </label>
        <select
          value={selectedDomain || ''}
          onChange={(e) => setSelectedDomain(e.target.value || null)}
          className="w-full px-3 py-2 border rounded-lg"
        >
          <option value="">No Domain (Generic Prompts)</option>
          {domains?.map((domain) => (
            <option key={domain.name} value={domain.name}>
              {domain.name} - {domain.description}
            </option>
          ))}
        </select>
        <p className="text-xs text-gray-500 mt-1">
          Select a trained domain to use optimized extraction prompts
        </p>
      </div>

      {/* Existing upload UI */}
      {/* ... */}
    </>
  );
}
```

#### 6. **LLM Model Selection Per Domain (4 SP)**

```python
# src/api/v1/domain_training.py - Store model with domain
class DomainCreateRequest(BaseModel):
    name: str
    description: str
    llm_model: str = Field(default="llama3.2:8b")  # Model for this domain

# During ingestion, use domain's preferred model
async def graph_extraction_node(state: IngestionState):
    if domain_id := state.get("domain_id"):
        # Load domain config from Neo4j/Redis
        domain_config = await load_domain_config(domain_id)
        llm_model = domain_config.get("llm_model", "llama3.2:8b")
    else:
        llm_model = "llama3.2:8b"

    extractor = ThreePhaseExtractor(
        domain_id=domain_id,
        llm_model=llm_model,  # ✅ Use domain's preferred model!
    )
```

---

## Testing Strategy

### Unit Tests (3 SP)
- ThreePhaseExtractor loads domain prompts from Redis
- Fallback to default prompts if domain not found
- Domain prompt caching works correctly

### Integration Tests (5 SP)
- Create domain → Train → Upload docs with domain
- Verify optimized prompts are used (check logs)
- Compare extraction quality: domain vs generic

### E2E Tests (3 SP)
- Full workflow: Train domain → Upload → Verify entities
- Multi-domain test: Medical vs Legal vs Technical
- Quality metrics: Entity precision/recall per domain

---

## Acceptance Criteria

1. ✅ IngestionState has `domain_id` field
2. ✅ ThreePhaseExtractor loads prompts from Redis
3. ✅ Backend API accepts `domain_id` parameter
4. ✅ Frontend has domain selector in upload UI
5. ✅ Logs show "using_domain_optimized_prompts"
6. ✅ Tests verify prompts are actually used
7. ✅ Domain-specific LLM model selection works
8. ✅ Quality improvement: +20% entity F1 score vs generic

---

## Migration & Rollback

### Backward Compatibility

**If no domain specified:**
- ✅ Uses default prompts (current behavior)
- ✅ No breaking changes
- ✅ Existing uploads work unchanged

### Gradual Rollout

1. **Phase 1:** Backend support (domain_id optional)
2. **Phase 2:** Frontend UI (hidden behind feature flag)
3. **Phase 3:** Train first domain, test thoroughly
4. **Phase 4:** Enable for all users

---

## ROI Analysis

### Investment

- **Already Spent:** 34 SP (Sprint 45 - Domain Training)
- **Additional Needed:** 21 SP (This TD)
- **Total:** 55 SP

### Returns

1. **Quality Improvement:** +20-40% entity extraction accuracy
2. **Model Efficiency:** Use small model for simple domains → Cost savings
3. **User Satisfaction:** Domain-specific extraction "just works"
4. **Feature Completion:** 34 SP investment finally pays off

**Break-Even:** After ~50 documents per domain (quality gains offset cost)

---

## Related Issues

- **TD-084:** Namespace isolation in ingestion (required prerequisite)
- **Sprint 45:** Domain Training System (original implementation)
- **Sprint 75:** RAGAS evaluation (would benefit from domain isolation)

---

## References

- `src/api/v1/domain_training.py` - Domain training endpoints
- `src/components/graph_rag/extractors/three_phase_extractor.py` - Entity extractor
- `src/components/ingestion/nodes/graph_extraction.py` - Graph extraction node
- `docs/adr/ADR-045_DSPY_DOMAIN_TRAINING.md` - Original design (if exists)
- Redis Keys: `dspy_domain:{domain_id}:optimized_prompt`
