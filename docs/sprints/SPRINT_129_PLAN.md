# Sprint 129 Plan: Extraction Resilience + RAGAS Full Ingestion + Domain Editor UI

**Status:** 📝 PLANNED
**Story Points:** ~42 SP (estimated)
**Duration:** 5-7 days
**Predecessor:** Sprint 128 ✅ (LightRAG Removal, Cascade Guard, vLLM Stability)

---

## Sprint Goals

1. **Extraction Resilience** — Window bisection fallback, max_relationships tuning, metadata artifact filtering
2. **RAGAS Full Ingestion** — Complete 498-doc Phase 1 benchmark (carried from Sprint 128.3)
3. **Domain Editor UI** — Admin UI for managing domain taxonomy (seed_domains.yaml)
4. **Table Ingestion** — Extract structured data from tables in PDFs/DOCX
5. **HyDE Refinements** — Query classification, adaptive weights, RAGAS evaluation

| # | Feature | SP | Priority | Origin |
|---|---------|-----|----------|--------|
| 129.1 | Cross-Sentence Window Bisection Fallback | 3 | HIGH | Sprint 128.3a Benchmark (0-relation windows) |
| 129.2 | max_relationships Cap Tuning | 2 | HIGH | Sprint 128.9 (cap at 100 loses valid relations) |
| 129.3 | Metadata Artifact Filtering | 2 | MEDIUM | Sprint 128.3a (`clean_text`/`Doc Type` as entities) |
| 129.4 | RAGAS Phase 1 Full Ingestion (498 docs) | 8 | HIGH | Sprint 128.3 (carried over) |
| 129.5 | RAGAS Re-Evaluation (post-LightRAG baseline) | 3 | HIGH | Sprint 128 Success Criteria |
| 129.6 | Domain Editor UI (Admin) | 5 | MEDIUM | DECISION_LOG Sprint 128 |
| 129.7 | Table Ingestion (Docling structured extraction) | 8 | MEDIUM | DECISION_LOG Sprint 128 |
| 129.8 | HyDE Query Classification (auto-enable for abstract queries) | 3 | LOW | HYDE_QUERY_EXPANSION.md |
| 129.9 | HyDE RAGAS A/B Evaluation | 3 | LOW | HYDE_QUERY_EXPANSION.md |
| 129.10 | TD-102: Relation Extraction Improvement (partial) | 5 | MEDIUM | TD_INDEX.md (18 SP total, partial) |

---

## Feature Details

### 129.1: Cross-Sentence Window Bisection Fallback (3 SP) — HIGH

**Problem:** Sprint 128.3a Cross-Sentence Benchmark shows some windows return **0 relations** from the LLM. Doc M (`w12_o3`) produced [0, 0, 0] across all 3 runs. The content is valid — the window is too large or complex for the model in a single call.

**Solution:** If a cross-sentence window returns 0 relations, **bisect the window** into two halves and retry extraction on each half.

**Algorithm:**
```
extract_relations(window) → results
if len(results) == 0 AND len(window.sentences) >= 4:
    mid = len(window.sentences) // 2
    left_window  = window.sentences[:mid + overlap]
    right_window = window.sentences[mid - overlap:]
    results = extract_relations(left_window) + extract_relations(right_window)
    deduplicate(results)
```

**Constraints:**
- Only bisect once (no recursive splitting) — avoids exponential LLM calls
- Minimum window size for bisection: 4 sentences (smaller windows are genuinely empty)
- Preserve sentence overlap between halves (1-2 sentences)
- Log bisection events: `window_bisected count=1 original_sentences=12 left=7 right=7`

**Files to Modify:**
- `src/components/graph_rag/extraction_service.py` — `_extract_relations_for_window()` or equivalent
- `src/components/graph_rag/cross_sentence_extractor.py` — Window splitting logic

**Acceptance Criteria:**
- [ ] 0-relation windows trigger automatic bisection retry
- [ ] Bisected halves include configurable sentence overlap
- [ ] No recursive bisection (max 1 split per window)
- [ ] Windows with <4 sentences are NOT bisected
- [ ] Bisection events logged with structured fields
- [ ] Unit tests for bisection logic
- [ ] Re-run Doc M benchmark: 0-relation configs produce >0 relations

---

### 129.2: max_relationships Cap Tuning (2 SP) — HIGH

**Problem:** `extraction_service.py` caps relations at 100 per window. Sprint 128.9 showed LLM extracts 100-176 relations per window — the cap silently drops valid relations.

**Options:**
1. Increase cap to 200 (simple, more VRAM for downstream dedup)
2. Make cap configurable via env var `AEGIS_MAX_RELATIONSHIPS_PER_WINDOW`
3. Remove cap entirely, rely on dedup + quality scoring

**Recommended:** Option 2 — configurable, default 150, env-overridable.

**Files to Modify:**
- `src/components/graph_rag/extraction_service.py` — `MAX_RELATIONSHIPS` constant
- `src/core/config.py` — New setting `AEGIS_MAX_RELATIONSHIPS_PER_WINDOW`

**Acceptance Criteria:**
- [ ] Cap configurable via environment variable
- [ ] Default increased from 100 to 150
- [ ] Logging when cap is hit: `max_relationships_exceeded extracted=176 cap=150 dropped=26`
- [ ] No regression in extraction latency

---

### 129.3: Metadata Artifact Filtering (2 SP) — MEDIUM

**Problem:** Sprint 128.3a Benchmark shows LLM extracts metadata artifacts as entities: `clean_text`, `Doc Type`, `DOCUMENT`, `RAGAS Phase 1 Benchmark`. These are document structure tokens, not domain entities.

**Solution:** Post-extraction filter that removes known metadata artifacts before storing to Neo4j.

**Approach:**
- Blocklist of metadata entity names: `clean_text`, `Doc Type`, `document`, `chunk`, `text`, `content`, `file`
- Also filter relations where both subject and object are metadata artifacts
- Case-insensitive matching
- Configurable blocklist (can extend over time)

**Files to Modify:**
- `src/components/graph_rag/extraction_service.py` — Post-extraction filter step
- `src/core/config.py` — `AEGIS_ENTITY_BLOCKLIST` setting

**Acceptance Criteria:**
- [ ] Metadata artifacts filtered before Neo4j storage
- [ ] Blocklist configurable via config
- [ ] Logging: `metadata_artifacts_filtered count=3 names=['clean_text', 'Doc Type', 'DOCUMENT']`
- [ ] Unit tests for filter logic

---

### 129.4: RAGAS Phase 1 Full Ingestion — 498 docs (8 SP) — HIGH

**Carried from Sprint 128.3.** With LightRAG removed (128.1), cascade guard (128.2), and stable eugr vLLM (128.7), full ingestion is now feasible.

**Estimated Duration:** ~42 hours (498 docs × 306s avg @ 2 workers)
- With bisection fallback (129.1): fewer 0-relation failures → fewer wasted cycles
- Batch script with JWT re-auth every 25 min
- Checkpoint every 50 docs (resume from last checkpoint on failure)
- Namespace: `ragas_phase1_sprint129`

**Prerequisites:** 129.1 (bisection), 129.2 (cap tuning)

**Files to Create/Modify:**
- `scripts/batch_upload_ragas_full.sh` — Full 498-doc upload with checkpointing
- Monitor via: `docker exec aegis-api python -c "...count docs in namespace..."`

**Acceptance Criteria:**
- [ ] 498/498 docs ingested (or ≥95% with documented failures)
- [ ] Namespace `ragas_phase1_sprint129` in Qdrant + Neo4j
- [ ] Entity count ≥2,000 (based on 15-doc extrapolation: ~14/doc × 498)
- [ ] Relation specificity ≥80% (matching 128.9 baseline of 84.5%)
- [ ] 0 CUDA crashes during full batch

---

### 129.5: RAGAS Re-Evaluation — Post-LightRAG Baseline (3 SP) — HIGH

**Goal:** Run RAGAS evaluation on the full 498-doc corpus and compare against Sprint 127 baseline.

**Sprint 127 Baseline:**

| Metric | Sprint 127 | Target Sprint 129 |
|--------|-----------|-------------------|
| Context Precision | 0.739 | ≥0.75 |
| Context Recall | 0.760 | ≥0.80 |
| Faithfulness | 0.699 | ≥0.75 |
| Answer Relevancy | 0.828 | ≥0.85 |

**Approach:**
- Use existing `scripts/run_ragas_evaluation.py` (Sprint 127)
- 50-100 sample questions from RAGAS Phase 1 dataset
- Compare vector-only, graph-only, hybrid modes
- Document results in `docs/ragas/RAGAS_JOURNEY.md`

**Prerequisites:** 129.4 (full ingestion complete)

**Acceptance Criteria:**
- [ ] RAGAS evaluation completed on ≥50 samples
- [ ] All 4 metrics documented
- [ ] Comparison table vs Sprint 127 in RAGAS_JOURNEY.md
- [ ] At least 2 of 4 metrics improved over Sprint 127

---

### 129.6: Domain Editor UI (5 SP) — MEDIUM

**Goal:** Admin UI page for viewing and editing domain taxonomy (currently hardcoded in `data/seed_domains.yaml`).

**Features:**
- List all 35 domains with DDC/FORD codes, keywords, entity/relation sub-types
- Edit domain metadata (keywords, descriptions)
- Activate/deactivate domains per deployment profile
- View domain-specific extraction prompts (read-only preview)
- Re-seed domains to Neo4j after editing

**Files to Create/Modify:**
- `frontend/src/pages/admin/AdminDomainEditorPage.tsx` — NEW
- `src/api/v1/admin_domains.py` — CRUD API endpoints
- `frontend/src/App.tsx` — Add route

**Acceptance Criteria:**
- [ ] Domain list page with search/filter
- [ ] Edit domain metadata (keywords, description)
- [ ] Toggle domain active/inactive
- [ ] Preview extraction prompts per domain
- [ ] Re-seed button (calls existing `seed_domains()`)
- [ ] E2E tests for CRUD operations

---

### 129.7: Table Ingestion — Docling Structured Extraction (8 SP) — MEDIUM

**Goal:** Extract structured data from tables in PDF/DOCX documents and store as typed relations in Neo4j.

**Current State:** Docling CUDA parser extracts table bounding boxes but converts them to flat text. Structured row/column data is lost.

**Approach:**
1. Use Docling's `TableStructure` output to preserve row/column headers
2. Convert table cells to entity-relation triples: `(row_header, column_header, cell_value)`
3. Store with relation type `HAS_VALUE` and entity type `TABLE_CELL` / `TABLE_HEADER`
4. Add `source_type: "table"` metadata to distinguish from text-extracted relations

**Files to Modify:**
- `src/components/document_processing/document_parsers.py` — Table extraction path
- `src/components/graph_rag/extraction_service.py` — Table-aware extraction mode
- `src/core/models.py` — `source_type` field on relations

**Acceptance Criteria:**
- [ ] Tables in PDFs produce structured triples (not flat text)
- [ ] Table headers become entity names
- [ ] Cell values stored with row+column context
- [ ] `source_type: "table"` metadata present
- [ ] Unit tests with sample table PDF

---

### 129.8: HyDE Query Classification (3 SP) — LOW

**Goal:** Auto-enable HyDE only for abstract/conceptual queries where hypothetical document generation adds value. Disable for factual lookups where HyDE can hurt precision.

**Classification:**
- **HyDE beneficial:** "What are the impacts of climate change on agriculture?" (abstract)
- **HyDE harmful:** "What is the population of Berlin?" (factual lookup)
- **Method:** Intent classification using existing C-LARA classifier (Sprint 81, 95% accuracy)

**Files to Modify:**
- `src/components/retrieval/hyde.py` — Add query classification gate
- `src/components/retrieval/maximum_hybrid_search.py` — Conditional HyDE activation

**Acceptance Criteria:**
- [ ] HyDE skipped for factual queries (intent: `factual_lookup`)
- [ ] HyDE enabled for abstract/conceptual queries
- [ ] Logging: `hyde_skipped reason=factual_query`
- [ ] Unit tests for classification gate

---

### 129.9: HyDE RAGAS A/B Evaluation (3 SP) — LOW

**Goal:** Measure HyDE impact on RAGAS metrics via controlled A/B test.

**Approach:**
- Run RAGAS evaluation WITH HyDE enabled (Sprint 128.4 implementation)
- Run RAGAS evaluation WITHOUT HyDE (baseline)
- Compare all 4 metrics
- Document in RAGAS_JOURNEY.md

**Prerequisites:** 129.4 (full ingestion), 129.5 (baseline evaluation)

**Acceptance Criteria:**
- [ ] A/B results for all 4 RAGAS metrics
- [ ] Statistical significance assessment (≥50 samples per condition)
- [ ] Recommendation: keep HyDE enabled/disabled/conditional
- [ ] Results documented in RAGAS_JOURNEY.md

---

### 129.10: TD-102 Relation Extraction Improvement — Partial (5 SP) — MEDIUM

**From TD-102 (18 SP total).** Address the most impactful items from the technical debt item.

**Scope for Sprint 129:**
- Typed relation prompts (already partially done in Sprint 128 prompt rewrite)
- Relation type validation against ADR-060 taxonomy (21 universal types)
- Reject/remap relations not in taxonomy → reduces RELATED_TO fallback rate

**Deferred to Sprint 130+:**
- SpaCy-first extraction (remaining 13 SP)
- Full KG Hygiene pipeline

**Files to Modify:**
- `src/components/graph_rag/extraction_service.py` — Relation type validation
- `src/prompts/extraction_prompts.py` — Typed relation examples

**Acceptance Criteria:**
- [ ] Relations validated against ADR-060 taxonomy
- [ ] Unknown relation types mapped to closest universal type (not RELATED_TO)
- [ ] Relation specificity ≥85% on benchmark docs
- [ ] Unit tests for relation type validation

---

## Dependency Graph

```
129.1 (Bisection) ──┐
129.2 (Cap Tuning) ──┼──→ 129.4 (Full Ingestion) ──→ 129.5 (RAGAS Eval)
129.3 (Filtering) ──┘                                       │
                                                             ↓
                                               129.9 (HyDE A/B) ←── 129.8 (HyDE Classification)

129.6 (Domain Editor UI) ──→ independent
129.7 (Table Ingestion) ──→ independent
129.10 (TD-102 partial) ──→ feeds into 129.4 quality
```

**Critical Path:** 129.1 → 129.2 → 129.4 → 129.5 → 129.9

---

## VRAM Budget (Sprint 129)

```
DGX Spark: 128 GB Unified Memory

Ingestion Mode (same as Sprint 128):
  vLLM NVFP4 (0.45 util)         64.5 GB   (eugr SM121 image)
  Ollama Nemotron-3-Nano         ~30 GB    (Chat — start on demand)
  BGE-M3 Embeddings               2 GB
  OS + CUDA Overhead             ~10 GB
  ─────────────────────────────────────
  Total (all loaded):            ~107 GB
  Free:                          ~21 GB
```

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| 498-doc batch fails mid-ingestion | Lost time | Medium | Checkpoint every 50 docs, resume script |
| Bisection doubles LLM calls | Slower ingestion | Low | Only triggers on 0-result windows (~5-10%) |
| RAGAS metrics regress vs Sprint 127 | Missed targets | Low | LightRAG removal improved relation specificity 21%→85% |
| Table ingestion quality poor | Low ROI | Medium | Start with simple row/column triples, iterate |
| HyDE hurts factual queries | CP regression | Low | Query classification gate (129.8) |

---

## Success Criteria

Sprint 129 is complete when:

- [ ] 0-relation windows trigger bisection fallback (129.1)
- [ ] max_relationships configurable, default 150 (129.2)
- [ ] Metadata artifacts filtered from extraction (129.3)
- [ ] ≥95% of 498 RAGAS docs ingested (129.4)
- [ ] RAGAS evaluation completed with ≥2/4 metrics improved (129.5)
- [ ] Domain Editor UI functional (129.6)
- [ ] Table extraction produces structured triples (129.7)
- [ ] All tests pass (unit, integration)
- [ ] Docker containers rebuilt and verified
- [ ] Documentation updated (RAGAS_JOURNEY.md, SPRINT_PLAN.md, DECISION_LOG.md)

---

## Sprint 128.3a Benchmark Results (Input for 129.1-129.3)

*To be updated when benchmark completes.*

### Key Findings (preliminary):
- **Doc S (2KB, 1 window):** w14_o3 most stable (CV=13.4%)
- **Doc M (4KB, 3 windows):** ALL configs have 0-relation runs — needs bisection (129.1)
- **Doc L (5.6KB, 3 windows):** w12_o3 most stable (CV=7.6%)
- **Metadata artifacts:** `clean_text`, `Doc Type` extracted as entities — needs filtering (129.3)
- **max_relationships cap:** 300 = 100×3 windows, LLM extracts up to 176/window — needs increase (129.2)

---

## References

- [Sprint 128 Plan](SPRINT_128_PLAN.md) — Predecessor sprint
- [RAGAS Journey](../ragas/RAGAS_JOURNEY.md) — Metrics evolution
- [HyDE Query Expansion](../features/HYDE_QUERY_EXPANSION.md) — Future enhancements
- [TD-102](../technical-debt/TD-102_RELATION_EXTRACTION_IMPROVEMENT.md) — Relation extraction debt
- [ADR-060](../adr/ADR-060-universal-entity-relation-types.md) — Universal type taxonomy
- [ADR-061](../adr/ADR-061-lightrag-removal.md) — LightRAG removal
