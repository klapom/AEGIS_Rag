# Sprint 76: Namespace & Domain Architecture Completion + RAGAS Evaluation

**Sprint Start:** 2026-01-06
**Sprint End:** 2026-01-24 (3 weeks)
**Total Story Points:** 68 SP (CRITICAL architecture fixes + deferred RAGAS features)

---

## Sprint Goals

1. 🔴 **Fix Critical Architecture Gaps** - TD-084 & TD-085 (34 SP)
2. 🧪 **Execute RAGAS Evaluation** - Deferred from Sprint 75 (34 SP)
3. 📊 **Establish Quality Baseline** - With proper namespace isolation

**Sprint Theme:** Complete the architecture foundation to enable accurate quality measurement

---

## Sprint Context

**Sprint 75 Discovery:** Two CRITICAL architecture gaps found that invalidate RAGAS evaluation:
- **TD-084:** Namespace isolation missing in ingestion → All docs mixed in "default"
- **TD-085:** DSPy domain training not integrated → 34 SP investment from Sprint 45 wasted

**Sprint 76 Strategy:** Fix architecture FIRST, then run RAGAS with proper isolation

---

## Phase 1: Architecture Fixes (Week 1-2)

### Feature 76.1: TD-084 - Namespace Isolation in Ingestion (13 SP)

**Priority:** 🔴 **CRITICAL** - Multi-tenant isolation broken
**Epic:** Platform Integrity
**Prerequisites:** None (blocking all multi-tenant features)

#### Problem Statement
All ingested documents are stored with `namespace_id="default"` hardcoded, breaking multi-tenant separation:
- RAGAS evaluation domain contaminated by production docs
- Project-specific docs pollute other projects
- No way to isolate test data from production

#### Solution Design

**Backend Changes (8 SP):**

1. **IngestionState - Add Namespace Field (1 SP)**
   ```python
   # src/components/ingestion/ingestion_state.py
   class IngestionState(TypedDict, total=False):
       namespace_id: str  # Multi-tenant isolation (default: "default")
       domain_id: str | None  # Optional DSPy domain (TD-085)
   ```

2. **Embedding Node - Use Namespace (2 SP)**
   ```python
   # src/components/ingestion/nodes/embedding_node.py
   namespace_id = state.get("namespace_id", "default")
   payload = {
       "namespace_id": namespace_id,  # Add to Qdrant metadata
       # ...
   }
   ```

3. **Graph Extraction - Use Namespace (2 SP)**
   ```python
   # src/components/ingestion/nodes/graph_extraction.py
   namespace_id = state.get("namespace_id", "default")
   await lightrag.insert_prechunked_documents(
       namespace_id=namespace_id,  # Pass to LightRAG
   )
   ```

4. **Backend API - Accept Namespace (3 SP)**
   ```python
   # src/api/v1/admin_indexing.py
   class AddDocumentsRequest(BaseModel):
       namespace_id: str = Field(default="default")
   ```

**Frontend Changes (5 SP):**

5. **AdminIndexingPage - Namespace Selector (3 SP)**
   ```tsx
   // Reuse existing NamespaceSelector component
   <NamespaceSelector
     selectedNamespaces={[selectedNamespace]}
     onSelectionChange={(ns) => setSelectedNamespace(ns[0])}
   />
   ```

6. **API Client - Pass Namespace (2 SP)**
   ```typescript
   export async function uploadFiles(
     files: File[],
     namespace_id: string = 'default'
   )
   ```

#### Testing (3 SP)
- Unit tests: IngestionState with namespace
- Integration tests: Upload to custom namespace → verify isolation
- E2E tests: RAGAS workflow with namespace

#### Acceptance Criteria
- [ ] `namespace_id` field in IngestionState
- [ ] All ingestion nodes use `state["namespace_id"]`
- [ ] Backend APIs accept `namespace_id` parameter
- [ ] Frontend has namespace selector
- [ ] Qdrant points have `namespace_id` in metadata
- [ ] Neo4j entities tagged with namespace
- [ ] Tests verify complete isolation
- [ ] RAGAS workflow works with custom namespace

---

### Feature 76.2: TD-085 - DSPy Domain Integration (21 SP)

**Priority:** 🔴 **CRITICAL** - 34 SP investment wasted (Sprint 45)
**Epic:** Domain Training Completion
**Prerequisites:** None (independent of TD-084)

#### Problem Statement
DSPy domain training (Sprint 45) optimizes prompts per domain, but these optimized prompts are **NEVER USED** during extraction:
- 34 SP invested → 0% value delivered
- Domain-specific extraction quality improvements unrealized
- LLM model selection per domain not working

#### Solution Design

**Backend Changes (13 SP):**

1. **IngestionState - Add Domain Field (1 SP)**
   ```python
   # src/components/ingestion/ingestion_state.py
   domain_id: str | None  # Domain for optimized prompts
   ```

2. **ThreePhaseExtractor - Domain-Aware (5 SP)**
   ```python
   # src/components/graph_rag/extractors/three_phase_extractor.py
   class ThreePhaseExtractor:
       def __init__(self, domain_id: str | None = None):
           if domain_id:
               # Load optimized prompts from Redis
               prompts = await self._load_domain_prompts(domain_id)
               self.entity_prompt = prompts["entity_extraction"]
               self.relation_prompt = prompts["relation_extraction"]
   ```

3. **Graph Extraction - Use Domain (3 SP)**
   ```python
   # src/components/ingestion/nodes/graph_extraction.py
   domain_id = state.get("domain_id")
   extractor = ThreePhaseExtractor(domain_id=domain_id)
   ```

4. **Backend API - Accept Domain (3 SP)**
   ```python
   # src/api/v1/admin_indexing.py
   class AddDocumentsRequest(BaseModel):
       domain_id: str | None = Field(default=None)
   ```

5. **Domain LLM Model Selection (1 SP)**
   ```python
   # Load domain config, use preferred LLM model
   domain_config = await load_domain_config(domain_id)
   llm_model = domain_config.get("llm_model", "llama3.2:8b")
   ```

**Frontend Changes (5 SP):**

6. **AdminIndexingPage - Domain Selector (3 SP)**
   ```tsx
   const { data: domains } = useDomains();
   <select value={selectedDomain || ''}>
     <option value="">No Domain (Generic Prompts)</option>
     {domains?.map(d => <option value={d.name}>{d.name}</option>)}
   </select>
   ```

7. **API Client - Pass Domain (2 SP)**
   ```typescript
   export async function streamAddDocuments(
     filePaths: string[],
     namespace_id: string,
     domain_id?: string
   )
   ```

#### Testing (3 SP)
- Unit tests: ThreePhaseExtractor loads Redis prompts
- Integration tests: Domain prompts used (verify logs)
- E2E tests: Full workflow with domain

#### Acceptance Criteria
- [ ] `domain_id` field in IngestionState
- [ ] ThreePhaseExtractor loads prompts from Redis
- [ ] Backend API accepts `domain_id`
- [ ] Frontend has domain selector
- [ ] Logs show "using_domain_optimized_prompts"
- [ ] Domain LLM model selection works
- [ ] Tests verify prompts actually used
- [ ] Quality improvement: +20% entity F1 vs generic

---

## Phase 2: RAGAS Evaluation (Week 3) - Deferred from Sprint 75

### Feature 76.3: RAGAS Baseline Evaluation (13 SP)

**Priority:** P0 (Unblocked by TD-084)
**Epic:** Quality Measurement
**Prerequisites:** ✅ TD-084 complete (namespace isolation)

#### Tasks

**Task 76.3.1: Setup RAGAS Namespace (2 SP)**
- Create namespace "ragas_eval_domain" via UI
- Ingest AEGIS RAG docs (493 .md files) with namespace isolation
- Verify namespace isolation (query should only return AEGIS docs)

**Task 76.3.2: Run RAGAS Smoke Test (2 SP)**
```bash
pytest tests/ragas/test_ragas_integration.py::test_ragas_quick_smoke -m ragas_quick -v
```
- 5 samples, 1-2 min runtime
- All 4 metrics > 0.5
- No errors

**Task 76.3.3: Run Full RAGAS Evaluation (8 SP)**
```bash
pytest tests/ragas/test_ragas_integration.py -m ragas_slow -v
```
- All 20 questions
- 30-40 min runtime
- Results saved to `reports/ragas_*.json`

**Task 76.3.4: Analyze RAGAS Results (1 SP)**
- Identify metrics below targets
- Per-intent breakdown
- Create analysis document

#### Acceptance Criteria
- [ ] RAGAS namespace isolated (no contamination)
- [ ] All 4 metrics computed successfully
- [ ] Results meet targets:
  - Context Precision > 0.75
  - Context Recall > 0.70
  - Faithfulness > 0.90
  - Answer Relevancy > 0.80
- [ ] Analysis document created

---

### Feature 76.4: Retrieval Method Comparison (13 SP)

**Priority:** P0 (Unblocked by TD-084)
**Epic:** Quality Measurement
**Prerequisites:** ✅ TD-084 complete, Feature 76.3 complete

#### Tasks

**Task 76.4.1: Run Comparison Smoke Test (2 SP)**
- 3 samples × 3 methods (BM25, Vector, Hybrid)
- Verify all work end-to-end

**Task 76.4.2: Run Full Comparison (8 SP)**
- 10 queries × 3 methods = 30 evaluations
- 30-60 min runtime
- Results saved to `reports/ragas_{bm25|vector|hybrid}.json`

**Task 76.4.3: Analyze Comparison (3 SP)**
- Hybrid vs pure methods
- Query-type specializations
- Failure mode analysis

#### Acceptance Criteria
- [ ] All 3 methods evaluated
- [ ] Hybrid competitive overall
- [ ] BM25 wins on keyword queries
- [ ] Vector wins on semantic queries
- [ ] Analysis document created

---

### Feature 76.5: RAG Optimization Research (8 SP)

**Priority:** P1 (Nice-to-have)
**Epic:** Continuous Improvement
**Prerequisites:** Features 76.3-76.4 complete

#### Tasks

**Task 76.5.1: Online Research (3 SP)**
- Chunking optimization techniques
- Embedding quality improvements
- Retrieval tuning best practices
- Reranking improvements
- Context optimization
- Prompt engineering

**Task 76.5.2: Create Improvement Plan (3 SP)**
- Prioritize by ROI (impact/effort)
- 5+ concrete recommendations
- Effort estimates (SP)
- Expected metric gains

**Task 76.5.3: Update Sprint 77 Backlog (2 SP)**
- Create SPRINT_77_PLAN.md with top improvements
- Update SPRINT_PLAN.md

#### Acceptance Criteria
- [ ] 10+ techniques documented
- [ ] 5+ actionable recommendations
- [ ] Sprint 77 backlog prepared

---

## Success Metrics

**Sprint Completion Criteria:**
- ✅ TD-084 implemented (namespace isolation working)
- ✅ TD-085 implemented (domain prompts used)
- ✅ RAGAS baseline established (with proper isolation)
- ✅ Retrieval comparison complete
- ✅ Improvement plan created

**Quality Targets:**
- RAGAS Context Precision: >0.75
- RAGAS Context Recall: >0.70
- RAGAS Faithfulness: >0.90
- RAGAS Answer Relevancy: >0.80
- Domain extraction: +20% F1 vs generic

**Documentation:**
- TD-084 implementation report
- TD-085 implementation report
- RAGAS analysis document
- Retrieval comparison analysis
- RAG tuning research
- Sprint 77 plan

---

## Risk Mitigation

**Risk 1: TD fixes break existing functionality**
- **Mitigation:** Comprehensive test suite (unit + integration + E2E)
- **Fallback:** Default namespace="default" preserves current behavior

**Risk 2: RAGAS still fails after TD-084**
- **Mitigation:** Thorough namespace isolation verification before RAGAS
- **Fallback:** Debug with single sample, check namespace filtering

**Risk 3: Domain prompts don't improve quality**
- **Mitigation:** A/B test: domain prompts vs generic prompts
- **Action:** Document findings, iterate on prompt optimization

**Risk 4: Sprint scope too large (68 SP)**
- **Mitigation:** Phase 1 (TDs) is CRITICAL, Phase 2 (RAGAS) can slip to Sprint 77
- **Contingency:** If behind schedule, defer Features 76.4-76.5 to Sprint 77

---

## Daily Breakdown (3 weeks)

### Week 1: TD-084 (Namespace Isolation)
**Day 1-2:** Backend changes (IngestionState, Embedding, Graph, API)
**Day 3-4:** Frontend changes (Namespace selector, API client)
**Day 5:** Testing & integration

### Week 2: TD-085 (Domain Integration)
**Day 6-7:** ThreePhaseExtractor domain-aware
**Day 8-9:** Frontend domain selector, API integration
**Day 10:** Testing & verification

### Week 3: RAGAS Evaluation
**Day 11:** Setup RAGAS namespace, ingest docs
**Day 12-13:** Run RAGAS + Retrieval comparison
**Day 14-15:** Analysis, research, Sprint 77 planning

---

## Notes

**Architecture Investment:**
- TD-084 + TD-085 = 34 SP (1 week effort each)
- Unlocks: Multi-tenant support, domain-specific extraction, valid RAGAS
- ROI: Prevents months of invalid evaluation data

**Sprint 45 Redemption:**
- 34 SP invested in Domain Training (Sprint 45)
- TD-085 finally connects training to extraction
- Expected payoff: +20-40% extraction quality on domain docs

**After Sprint 76:**
- Namespace isolation production-ready
- Domain training fully functional
- RAGAS baseline established
- Clear quality improvement roadmap for Sprint 77+
