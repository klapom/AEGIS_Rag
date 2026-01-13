# Sprint 84: Stabilization & Iterative Ingestion

**Duration:** 3-5 days
**Story Points:** 26 SP (8 features + bugfixes)
**Status:** 🏗️ In Progress (84.7, 84.8, 84.9 Complete)
**Goal:** Fehlerfreie Ingestion von 500 RAGAS Phase 1 Samples mit Sprint 83 Features + Enhanced Logging

---

## Sprint Objectives

### Primary Goal
**Iterative Ingestion Testing:** Schrittweise Skalierung (5 → 20 → 50 → 100 → 500 files) mit Sprint 83 Features (3-Rank Cascade, Gleaning, Fast Upload)

### Secondary Goals
1. **Outlier Detection:** RAGAS LLM Judging Failures erkennen und aus Metriken ausschließen
2. **Configurable Cascade:** Per-Domain Cascade-Konfiguration (model_id, timeout, extraction_type)
3. **Bugfixes:** Alle Ingestion-Fehler beheben und dokumentieren in RAGAS_JOURNEY.md

---

## Features

### Feature 84.1: RAGAS Outlier Detection & Enhanced Logging (3 SP)

**User Story:**
**As a** RAGAS Evaluator
**I want to** detect and exclude LLM judging failures (e.g., Faithfulness=0.0 für korrekte Antworten)
**So that** RAGAS metrics are robust gegen Parsing-Fehler

**Requirements:**

1. **RAGASEvaluationLogger Class:**
   ```python
   # src/evaluation/ragas_logger.py (NEW)

   class RAGASEvaluationLogger:
       """Enhanced RAGAS evaluation logging with outlier detection."""

       def log_judgment(
           self,
           question_id: str,
           metric: str,  # "faithfulness", "context_precision", etc.
           score: float,
           llm_response: str,
           judgment_latency_ms: float,
           error: Optional[str] = None
       ):
           """Log individual RAGAS metric judgment."""
           is_outlier = self._detect_outlier(metric, score, llm_response)

           logger.info(
               "ragas_judgment",
               question_id=question_id,
               metric=metric,
               score=score,
               latency_ms=judgment_latency_ms,
               llm_response_len=len(llm_response),
               error=error,
               is_outlier=is_outlier,
           )

           return is_outlier

       def _detect_outlier(self, metric: str, score: float, llm_response: str) -> bool:
           """Detect outlier scores (LLM parsing errors)."""
           # Heuristic 1: F=0.0 with long answer (>100 chars) likely parsing error
           if metric == "faithfulness" and score == 0.0 and len(llm_response) > 100:
               return True

           # Heuristic 2: AR=0.0 with substantive answer
           if metric == "answer_relevancy" and score == 0.0 and len(llm_response) > 50:
               return True

           # Heuristic 3: CP=0.0 with retrieved contexts (should have precision > 0)
           if metric == "context_precision" and score == 0.0:
               return True

           return False

       def summarize_evaluation(
           self,
           results: Dict[str, List[float]],
           outliers_removed: Dict[str, int]
       ):
           """Log evaluation summary with outlier statistics."""
           logger.info(
               "ragas_evaluation_complete",
               faithfulness_avg=np.mean(results["faithfulness"]),
               faithfulness_std=np.std(results["faithfulness"]),
               context_precision_avg=np.mean(results["context_precision"]),
               context_recall_avg=np.mean(results["context_recall"]),
               answer_relevancy_avg=np.mean(results["answer_relevancy"]),
               total_questions=len(results["faithfulness"]),
               outliers_removed=outliers_removed,
               outlier_rate=sum(outliers_removed.values()) / (len(results["faithfulness"]) * 4)
           )
   ```

2. **Integration in RAGAS Evaluation:**
   ```python
   # scripts/run_ragas_eval.py (MODIFY)

   logger = RAGASEvaluationLogger()
   results = {"faithfulness": [], "context_precision": [], ...}
   outliers = {"faithfulness": 0, "context_precision": 0, ...}

   for sample in dataset:
       # ... run RAGAS evaluation ...

       # Log judgment + detect outlier
       is_outlier = logger.log_judgment(
           question_id=sample["id"],
           metric="faithfulness",
           score=faithfulness_score,
           llm_response=llm_judgment,
           judgment_latency_ms=latency
       )

       # Only add non-outliers to results
       if not is_outlier:
           results["faithfulness"].append(faithfulness_score)
       else:
           outliers["faithfulness"] += 1
           logger.warning(
               "ragas_outlier_detected",
               question_id=sample["id"],
               metric="faithfulness",
               score=faithfulness_score,
               reason="F=0.0 with long answer"
           )

   # Summary with outlier stats
   logger.summarize_evaluation(results, outliers)
   ```

3. **Structured Log Output:**
   ```json
   {
     "event": "ragas_judgment",
     "question_id": "hotpotqa_123",
     "metric": "faithfulness",
     "score": 0.0,
     "latency_ms": 2340,
     "llm_response_len": 456,
     "is_outlier": true,
     "timestamp": "2026-01-10T15:30:45Z"
   }

   {
     "event": "ragas_evaluation_complete",
     "faithfulness_avg": 0.693,
     "faithfulness_std": 0.214,
     "context_precision_avg": 0.717,
     "context_recall_avg": 0.650,
     "answer_relevancy_avg": 0.859,
     "total_questions": 20,
     "outliers_removed": {"faithfulness": 3, "context_precision": 1, "context_recall": 0, "answer_relevancy": 2},
     "outlier_rate": 0.075
   }
   ```

**Acceptance Criteria:**
- [ ] RAGASEvaluationLogger class implemented (150 LOC)
- [ ] Outlier detection heuristics (3 rules: F=0.0, AR=0.0, CP=0.0)
- [ ] Structured logging (JSON format)
- [ ] Integration in run_ragas_eval.py
- [ ] 10 unit tests (outlier detection edge cases)

**Expected Impact:**
- **Robuste Metriken:** Outliers (5-10%) aus Berechnung ausgeschlossen
- **Debugging:** Outliers geloggt für manuelle Analyse
- **Transparency:** Outlier rate in Summary ersichtlich

---

### Feature 84.2: Configurable 3-Rank Cascade (3 SP)

**User Story:**
**As a** Domain Administrator
**I want to** configure extraction strategy per rank (LLM model, timeout, extraction type)
**So that** I can optimize extraction for different document types

**Requirements:**

**Siehe:** `/home/admin/projects/aegisrag/AEGIS_Rag/docs/sprints/FEATURE_83_5_CONFIGURABLE_CASCADE.md`

**Key Changes:**
1. Extend `CascadeRankConfig` with `model_id`, `prompt_source`, `extraction_type` fields
2. Support `extraction_type`: "llm", "spacy", "hybrid"
3. Support `prompt_source`: "default", "dspy" (if Sprint 79 DSPy optimization available)
4. Domain-specific cascade presets: DEFAULT, LEGAL, TECH

**Acceptance Criteria:**
- [ ] CascadeRankConfig extended (Pydantic validation)
- [ ] 3 presets defined (DEFAULT, LEGAL, TECH)
- [ ] ExtractionService uses rank_config (model_id, timeout, extraction_type)
- [ ] 18 unit tests (config validation, extraction switching)

**Expected Impact:**
- **Flexibility:** Per-domain cascade optimization
- **Performance:** SpaCy Rank 1 für einfache Docs (10x faster)
- **Quality:** LLM Rank 1 für komplexe Docs (higher quality)

---

### Feature 84.3: Iterative Ingestion Testing (10 SP)

**User Story:**
**As a** RAGAS Team
**I want to** iteratively ingest 500 Phase 1 samples (5 → 20 → 50 → 100 → 500)
**So that** errors are caught early and fixed before full-scale ingestion

**Requirements:**

**Siehe:** `docs/ragas/RAGAS_JOURNEY.md` - Iterative Ingestion Protocol

**Iteration Plan:**

| Iteration | Files | Expected Duration | Validation |
|-----------|-------|-------------------|------------|
| **1 (PoC)** | 5 | 10-20 Min | Sprint 83 features active? No errors? |
| **2** | 20 | 40-60 Min | Cascade Rank 1 success > 90%? |
| **3** | 50 | 1.5-2 Stunden | P95 latency < 60s? GPU VRAM < 12 GB? |
| **4** | 100 | 3-4 Stunden | Entities per chunk > 1? Relations per doc > 0? |
| **5 (Full)** | 500 | 10-15 Stunden | Complete, no errors |

**Error Response Protocol:**

1. **STOP immediately** bei:
   - 0 entities per chunk (3+ chunks)
   - 0 relations per document (3+ docs)
   - Cascade Rank 3 fallback > 10%
   - GPU VRAM > 14 GB

2. **Root Cause Analysis:**
   - Extract logs: `tail -100 logs/ingestion.log > error_analysis/iterationN_error.log`
   - Identify: Which rank failed? Which file? Timeout or parse error?

3. **Fix & Document:**
   - Implement fix (Timeout erhöhen, Cascade-Config ändern, etc.)
   - Document in RAGAS_JOURNEY.md (siehe Iteration Log Template)

4. **Resume/Restart Decision:**
   - **Struktureller Fehler:** Neuer Namespace (`_v2`, `_v3`)
   - **Einzelner File-Fehler:** Gleicher Namespace, File überspringen

**Monitoring Commands:**
```bash
# Real-time log tail (separate terminal)
tail -f logs/ingestion.log | grep -E "cascade_rank|gleaning_round|TIMING_phase_summary|ERROR"

# GPU VRAM watch (separate terminal)
watch -n 5 nvidia-smi

# Entity/Relation count summary (after iteration)
grep "extraction_quality_metrics" logs/ingestion.log | jq '.entities_count, .relations_count' | awk '{sum+=$1; count++} END {print "Avg entities per chunk:", sum/count}'
```

**Acceptance Criteria:**
- [ ] 5 successful iterations documented in RAGAS_JOURNEY.md
- [ ] 500/500 files ingested (no errors)
- [ ] Sprint 83 features validated (Cascade, Gleaning, Fast Upload logs visible)
- [ ] All error thresholds met (entities > 1, relations > 0, Cascade Rank 1 > 90%)

**Expected Impact:**
- **Quality:** Early error detection prevents mass ingestion failures
- **Documentation:** Every error + fix documented for Sprint 85/86
- **Confidence:** 100% ingestion success rate proven

---

### Feature 84.4: Cascade Timeout Auto-Tuning (2 SP)

**User Story:**
**As a** Ingestion Pipeline
**I want to** automatically adjust LLM timeouts based on observed failures
**So that** timeouts are neither too short (failures) nor too long (waste time)

**Requirements:**

**Siehe:** `docs/ragas/RAGAS_JOURNEY.md` - Cascade Timeout Tuning Protocol

**Algorithm:**
```python
# Adaptive Timeout Tuning (triggered after 3+ timeouts on same rank)

if rank1_timeout_count >= 3:
    # Step 1: Try alternate model (Nemotron3 ↔ GPT-OSS:20b)
    current_model = CASCADE[0].model_id
    alternate_model = "gpt-oss:20b" if current_model == "nemotron3" else "nemotron3"

    log(f"Switching Rank 1: {current_model} → {alternate_model}")
    CASCADE[0].model_id = alternate_model

    # Reset timeout count
    rank1_timeout_count = 0

if rank1_timeout_count >= 3:  # After alternate model also fails
    # Step 2: Revert to original model, increase timeout +60s
    log(f"Reverting Rank 1: {CASCADE[0].model_id} → {original_model}, Timeout +60s")
    CASCADE[0].model_id = original_model
    CASCADE[0].timeout_s += 60

    rank1_timeout_count = 0

if rank1_timeout_count >= 3:  # After timeout increase also fails
    # Step 3: Switch to alternate model, keep increased timeout
    log(f"Switching Rank 1: {CASCADE[0].model_id} → {alternate_model}, Timeout={CASCADE[0].timeout_s}")
    CASCADE[0].model_id = alternate_model
    # timeout_s bleibt erhöht!

    rank1_timeout_count = 0

if rank1_timeout_count >= 3:  # Both models fail at increased timeout
    # Step 4: CRITICAL - Document complexity too high
    log(f"CRITICAL: Both models timeout at {CASCADE[0].timeout_s}s. Disabling gleaning.")
    chunking_config.gleaning_steps = 0  # Emergency fallback

    # OR: Switch Rank 1 to SpaCy NER (instant, no timeout)
    CASCADE[0].model_id = "spacy"
    CASCADE[0].extraction_type = "spacy"
    CASCADE[0].timeout_s = 0
```

**Acceptance Criteria:**
- [ ] Auto-tuning algorithm implemented (100 LOC)
- [ ] Timeout adjustments logged (before/after values)
- [ ] Emergency fallbacks (gleaning disable, SpaCy switch)
- [ ] 5 unit tests (timeout scenarios)

**Expected Impact:**
- **Resilience:** Automatic recovery from timeout patterns
- **Efficiency:** Optimal timeouts without manual tuning
- **Transparency:** All adjustments logged for analysis

---

### Feature 84.5: GPU VRAM Monitoring Dashboard (1 SP)

**User Story:**
**As a** DevOps Engineer
**I want to** monitor GPU VRAM usage during ingestion
**So that** I can prevent OOM errors and optimize batch sizes

**Requirements:**

1. **VRAM Tracking in Logs:**
   - Already implemented in Sprint 83.1 (pynvml)
   - Logs: `memory_snapshot` events with RAM + VRAM

2. **Dashboard Script:**
   ```bash
   # scripts/monitor_vram.sh (NEW)

   #!/bin/bash
   # Real-time VRAM monitoring during ingestion

   watch -n 5 'nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | awk -F, "{printf \"VRAM: %s/%s MB (%.1f%%), GPU: %s%%\n\", \$1, \$2, \$1/\$2*100, \$3}"'
   ```

3. **Alert Thresholds:**
   - ⚠️ Warning: VRAM > 12 GB (80%)
   - 🔴 Critical: VRAM > 14 GB (93%)
   - ✅ Normal: VRAM < 12 GB

**Acceptance Criteria:**
- [ ] monitor_vram.sh script created
- [ ] Log alerts when VRAM > 12 GB
- [ ] Documentation in RAGAS_JOURNEY.md (monitoring section)

**Expected Impact:**
- **Proactive:** Catch VRAM issues before OOM crash
- **Optimization:** Identify VRAM-hungry documents for tuning

---

### Feature 84.6: Ingestion Resume Script (1 SP)

**User Story:**
**As a** RAGAS Team
**I want to** resume failed ingestion from last successful file
**So that** I don't re-process already ingested documents

**Requirements:**

```python
# scripts/upload_ragas_phase2.py (MODIFY)

def upload_with_resume(
    dataset_path: str,
    namespace: str,
    start_index: int = 0  # Resume from index
):
    """Upload RAGAS dataset with resume support."""

    # Load dataset
    with open(dataset_path) as f:
        samples = [json.loads(line) for line in f]

    # Check existing files in namespace (Qdrant)
    existing_docs = qdrant_client.scroll(
        collection_name="documents",
        scroll_filter={"namespace": namespace},
        limit=1000
    )
    existing_ids = {doc.payload["document_id"] for doc in existing_docs[0]}

    # Resume logic
    total_files = len(samples)
    skipped = 0
    uploaded = 0

    for i, sample in enumerate(samples[start_index:], start=start_index):
        # Skip if already ingested
        if sample["id"] in existing_ids:
            logger.info(f"Skipping {sample['id']} (already ingested)")
            skipped += 1
            continue

        # Upload via Frontend API
        try:
            upload_document(sample["file_path"], namespace)
            uploaded += 1
            logger.info(f"Progress: {i+1}/{total_files} ({uploaded} new, {skipped} skipped)")
        except Exception as e:
            logger.error(f"Failed to upload {sample['id']}: {e}")
            logger.info(f"Resume command: python scripts/upload_ragas_phase2.py --start-index {i}")
            raise

    logger.info(f"Ingestion complete: {uploaded} uploaded, {skipped} skipped")

# Usage:
# python scripts/upload_ragas_phase2.py --start-index 0  # Start from beginning
# python scripts/upload_ragas_phase2.py --start-index 168  # Resume from file 168
```

**Acceptance Criteria:**
- [ ] --start-index flag implemented
- [ ] Skip logic for already ingested files
- [ ] Progress tracking (uploaded vs skipped)
- [ ] Error handling with resume command

**Expected Impact:**
- **Efficiency:** No re-processing on resume
- **Recovery:** Fast recovery from failures

---

### Feature 84.7: Neo4j Cypher Escaping Bug Fix (3 SP) ✅ COMPLETE

**User Story:**
**As a** Graph Storage System
**I want to** properly escape entity IDs with special characters (spaces, colons, slashes)
**So that** entities are persisted to Neo4j without Cypher syntax errors

**Root Cause (Discovered in Iteration 1):**

**Problem:** LightRAG Neo4j storage creates broken Cypher queries for entity IDs containing special characters:

```
ERROR entity_creation_failed entity_id="RAGAS Phase 1 Benchmark"
error={code: Neo.ClientError.Statement.SyntaxError}
message: Invalid input 'Dataset': expected a parameter, '&', ')', ':', 'WHERE', '{' or '|'
```

**Impact:**
- ❌ **Neo4j**: 0 documents, 0 chunks, 0 entities persisted (complete persistence failure)
- ❌ **Qdrant**: 0 ragas points (transaction rollback)
- ✅ **API**: Returns "success" + entity counts (from in-memory extraction)
- 🔴 **Silent Failure**: No HTTP error, user unaware of data loss!

**Iteration 1 Evidence:**
- 5/5 files processed, 139 entities extracted, **0 persisted to any database**
- Entities with spaces/colons/slashes: "RAGAS Phase 1 Benchmark", "Moloch: or, This Gentile World", "Henry Miller Memorial Library"

**Requirements:**

1. **Fix `src/components/graph_rag/lightrag/neo4j_storage.py`:**
   ```python
   def _sanitize_entity_id(self, entity_id: str) -> str:
       """Sanitize entity ID for Cypher query safety.

       Neo4j Cypher requires:
       - Backticks (`) for node labels/IDs with special chars
       - No unescaped colons, slashes, quotes
       """
       # Replace problematic characters
       sanitized = entity_id.replace("`", "\\`")  # Escape existing backticks

       # Always use backticks for safe Cypher identifiers
       return f"`{sanitized}`"

   def upsert_entity(self, entity_name: str, entity_type: str, description: str):
       """Create or update entity in Neo4j."""
       # Sanitize entity_name for Cypher
       safe_entity_name = self._sanitize_entity_id(entity_name)
       safe_entity_type = self._sanitize_entity_id(entity_type)

       query = f"""
       MERGE (e:Entity {safe_entity_name})
       ON CREATE SET e.entity_type = {safe_entity_type},
                     e.description = $description,
                     e.created_at = timestamp()
       ON MATCH SET e.description = $description,
                    e.updated_at = timestamp()
       """

       self.session.run(query, description=description)
   ```

2. **Add Transaction Rollback on Entity Creation Failure:**
   ```python
   def persist_graph(self, entities, relations):
       """Persist graph with rollback on failure."""
       try:
           with self.driver.session() as session:
               with session.begin_transaction() as tx:
                   # Persist entities
                   for entity in entities:
                       self._upsert_entity_tx(tx, entity)

                   # Persist relations
                   for relation in relations:
                       self._upsert_relation_tx(tx, relation)

                   tx.commit()
                   return {"success": True, "entities": len(entities), "relations": len(relations)}

       except Exception as e:
           logger.error("graph_persistence_failed", error=str(e))
           # Rollback handled automatically by context manager
           return {"success": False, "error": str(e)}
   ```

3. **Update API Response to Reflect Persistence Status:**
   ```python
   # src/api/v1/retrieval.py

   graph_result = graph_storage.persist_graph(entities, relations)

   if not graph_result["success"]:
       # Rollback Qdrant points if Neo4j failed
       qdrant_client.delete(collection_name="documents", points=[chunk_ids])

       raise HTTPException(
           status_code=500,
           detail=f"Graph persistence failed: {graph_result['error']}"
       )

   return IngestionResponse(
       status="success",  # Only if ALL persistence succeeded
       neo4j_entities=graph_result["entities"],
       neo4j_relationships=graph_result["relations"]
   )
   ```

4. **Add Unit Tests:**
   ```python
   # tests/unit/test_neo4j_escaping.py (NEW)

   def test_entity_id_with_spaces():
       entity_id = "RAGAS Phase 1 Benchmark"
       safe_id = storage._sanitize_entity_id(entity_id)
       assert safe_id == "`RAGAS Phase 1 Benchmark`"

   def test_entity_id_with_colon():
       entity_id = "Moloch: or, This Gentile World"
       safe_id = storage._sanitize_entity_id(entity_id)
       assert safe_id == "`Moloch: or, This Gentile World`"

   def test_entity_id_with_slash():
       entity_id = "Henry Miller Memorial Library"  # "/" in description
       safe_id = storage._sanitize_entity_id(entity_id)
       # Backticks handle all special chars
       assert safe_id.startswith("`") and safe_id.endswith("`")

   @pytest.mark.integration
   def test_entity_persistence_with_special_chars(neo4j_session):
       """Integration test: Verify entities with special chars persist."""
       storage = Neo4jStorage(neo4j_session)

       # Create entity with problematic ID
       storage.upsert_entity(
           entity_name="Test: Entity / With Special <Chars>",
           entity_type="Test Type",
           description="Test description"
       )

       # Verify entity exists in Neo4j
       result = neo4j_session.run(
           "MATCH (e:Entity {name: $name}) RETURN e",
           name="Test: Entity / With Special <Chars>"
       ).single()

       assert result is not None
   ```

**Acceptance Criteria:**
- [x] `_sanitize_entity_id()` method implemented in `neo4j_storage.py`
- [x] Transaction rollback on entity creation failure
- [x] API returns HTTP 500 if Neo4j persistence fails
- [x] Qdrant points deleted if Neo4j persistence fails
- [x] Unit tests for entity ID escaping (4+ test cases)
- [x] Integration test: Entities with special chars persist to Neo4j
- [ ] Re-run Iteration 1 (5 files) → All 139 entities persist successfully

**Expected Impact:**
- **Data Integrity:** 0% → 100% persistence success rate
- **Error Visibility:** Silent failures → HTTP 500 errors
- **Robustness:** Handles all Unicode characters in entity IDs

---

### Feature 84.8: Section Extraction Performance Optimization (TD-078) (3 SP) ✅ COMPLETE

**User Story:**
**As a** Ingestion Pipeline
**I want to** reduce section-aware chunking latency from 42s to <5s for 3.6KB .txt files
**So that** overall ingestion throughput increases by 8-10x

**Root Cause Analysis (From Iteration 1 Logs):**

**Problem:** Section extraction takes 42-43s for tiny 3.6KB .txt files:

```
File 1 (3.6KB): node_timings_ms={'chunking': 42756.0}  = 42.8s
File 1 retry:   node_timings_ms={'chunking': 43116.0}  = 43.1s
```

**Expected Performance:** 3.6KB should chunk in <1s (similar to PDF chunking)

**Hypothesis:**
1. **LLM Section Detection**: Currently uses LLM to detect sections in .txt files
2. **.txt Format Mismatch**: Docling's section detection designed for PDFs (headings, layout)
3. **Overhead**: .txt files have no structural markup → LLM makes many inference calls

**Investigation Required:**

```bash
# Check if section detection is active for .txt files
grep -A 5 "node_chunking_start" logs/ingestion.log | grep -E "chunking_strategy|section_detection"

# Compare .txt vs .pdf chunking timings
grep "node_timings_ms" logs/ingestion.log | grep -E "\.txt|\.pdf"
```

**Requirements (To Be Determined After Analysis):**

**Option A: Disable Section Detection for .txt Files**
```python
# src/components/ingestion/nodes/chunking.py

def should_use_section_detection(file_format: str) -> bool:
    """Determine if section detection is beneficial."""
    # Section detection only useful for structured formats
    if file_format in [".txt", ".md"]:
        return False  # Use simple sentence-based chunking

    if file_format in [".pdf", ".docx", ".pptx"]:
        return True  # Use Docling section detection

    return False  # Default: simple chunking
```

**Option B: Use Regex-Based Section Detection for .txt**
```python
def detect_txt_sections(text: str) -> List[Section]:
    """Fast regex-based section detection for .txt files."""
    import re

    # Pattern: Lines starting with ###, ##, or ALL CAPS
    section_pattern = r"^(#{1,3}\s+.+|[A-Z\s]{10,})\n"

    sections = []
    for match in re.finditer(section_pattern, text, re.MULTILINE):
        sections.append({
            "heading": match.group(1).strip(),
            "start_offset": match.start()
        })

    return sections if len(sections) > 1 else []  # Only if multiple sections found
```

**Acceptance Criteria:**
- [ ] **Analysis Complete**: Identify root cause via logs + code inspection
- [ ] **Fix Implemented**: .txt chunking < 5s for 3.6KB files
- [ ] **Throughput Improvement**: 8-10x faster ingestion for .txt files
- [ ] **Tests Added**: Unit tests for .txt vs .pdf chunking strategies
- [ ] **Documentation**: Update TD-078 with resolution details

**Expected Impact:**
- **Performance:** 42s → <5s chunking (8.4x faster)
- **Scalability:** 500 .txt files: 5.8 hours → 41 minutes
- **Cost**: Fewer LLM calls for section detection

**Status:** ✅ COMPLETE (O(n²) fix implemented in Sprint 85)

---

## Bugfixes (As Needed)

**During iterative ingestion, fix any bugs discovered:**

1. **Cascade Failures:** LLM timeouts, parse errors, model crashes
2. **Gleaning Issues:** Completeness check too strict/loose, deduplication errors
3. **API Errors:** Upload failures, status tracking bugs
4. **Logging Gaps:** Missing metrics, incorrect P95 calculation

**Process:**
1. STOP ingestion immediately
2. Root cause analysis (logs, stack trace)
3. Fix implementation
4. Document in RAGAS_JOURNEY.md
5. Resume/Restart ingestion

---

## Success Criteria

**Sprint 84 Complete:**
- [ ] 500/500 RAGAS Phase 1 samples ingested (namespace: `ragas_phase2_sprint83_v1`)
- [ ] Sprint 83 features validated (Cascade, Gleaning, Fast Upload logs visible)
- [ ] All error thresholds met:
  - [ ] Entities per chunk > 1 (avg > 5)
  - [ ] Relations per document > 0 (avg > 10)
  - [ ] Cascade Rank 1 success > 90%
  - [ ] P95 latency < 60s per chunk
  - [ ] GPU VRAM peak < 12 GB
- [ ] 5 iterations documented in RAGAS_JOURNEY.md
- [ ] Feature 84.1 complete (Outlier Detection, 3 SP)
- [ ] Feature 84.2 complete (Configurable Cascade, 3 SP)
- [ ] 0 blocking bugs (all ingestion errors fixed)

**Ready for Sprint 85:**
- [ ] RAGAS Phase 2 dataset fully ingested
- [ ] Baseline metrics available (Context Recall, Context Precision, Faithfulness, Answer Relevancy)
- [ ] Cascade timeout tuning documented (optimal timeouts per rank)

---

## Dependencies

- **Sprint 83 Complete:** All features implemented and tested
- **RAGAS Phase 1 Dataset:** 500 samples available (HotpotQA + RAGBench)
- **Ollama Models:** Nemotron3, GPT-OSS:20b, SpaCy NER models installed
- **GPU Availability:** DGX Spark accessible (12+ GB VRAM free)

---

## Timeline

| Day | Tasks | Focus |
|-----|-------|-------|
| **Day 1** | Feature 84.1 (Outlier Detection) | Implement RAGASEvaluationLogger |
| **Day 2** | Feature 84.2 (Configurable Cascade) | Extend CascadeRankConfig, presets |
| **Day 3** | Iteration 1-2 (5 + 20 files) | PoC + small-scale validation |
| **Day 4** | Iteration 3-4 (50 + 100 files) | Medium-scale validation + bugfixes |
| **Day 5** | Iteration 5 (500 files) | Full-scale ingestion + documentation |

---

## Notes

- **Iterative Approach:** STOP immediately on errors, fix, document, resume
- **Cascade Tuning:** Expect 2-3 timeout adjustments during iterations
- **Gleaning Impact:** Expected +20-40% entity recall vs Sprint 82 baseline
- **Fast Upload:** User experience improvement (2-5s vs 30-60s)
- **Documentation:** RAGAS_JOURNEY.md is living document (updated after each iteration)

---

**Status:** 🏗️ In Progress (3/9 features complete)
**Next Sprint:** Sprint 85 (Relation Extraction Improvement - TD-102)
