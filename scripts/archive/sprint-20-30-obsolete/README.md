# Archive: Sprint 20-30 Obsolete Scripts

**Archived:** 2025-11-19 (Sprint 30 Cleanup)
**Reason:** Scripts superseded by newer implementations or no longer relevant to current architecture

---

## Archived Scripts

### Model Evaluation (Superseded by AegisLLMProxy)

| Script | Sprint | Reason for Archival |
|--------|--------|---------------------|
| `evaluate_chat_models.py` | 20 | Superseded by AegisLLMProxy multi-cloud routing (Sprint 23) |
| `evaluate_models_comprehensive.py` | 20 | Old model benchmarking, replaced by routing logic |
| `evaluate_lm_studio_params.py` | N/A | LM Studio not used in production |

**Context:** Sprint 20 focused on comparing Llama vs Gemma models manually. Sprint 23 introduced AegisLLMProxy with automatic routing based on quality/complexity, making manual evaluation scripts obsolete.

---

### Indexing Scripts (Superseded by Docling + LangGraph)

| Script | Sprint | Reason for Archival |
|--------|--------|---------------------|
| `clear_and_reindex.py` | Pre-21 | Uses deprecated LlamaIndex SimpleDirectoryReader |
| `quick_index_pptx.py` | Pre-21 | Replaced by Docling CUDA Container (Sprint 21) |
| `reindex_with_chunk_logging.py` | Pre-21 | Replaced by LangGraph pipeline (Sprint 21) |
| `index_performance_tuning_debug.py` | Pre-21 | Old debugging, superseded by Feature 21 monitoring |

**Context:** Sprint 21 migrated from LlamaIndex to Docling CUDA Container with GPU-accelerated OCR (ADR-027). All old indexing scripts using LlamaIndex SimpleDirectoryReader are now deprecated.

---

### Neo4j Debugging Scripts (Obsolete)

| Script | Sprint | Reason for Archival |
|--------|--------|---------------------|
| `verify_neo4j_data.py` | Pre-20 | Old Neo4j verification, replaced by LightRAG integration tests |
| `check_neo4j_labels.py` | Pre-20 | Duplicate functionality of LightRAG monitoring |
| `log_chunks_and_entities.py` | Pre-20 | Old logging, replaced by structured logging (Sprint 21+) |
| `simple_neo4j_check.py` | Pre-20 | Basic check, superseded by comprehensive tests |

**Context:** Early Neo4j debugging scripts created before LightRAG wrapper stabilized. Now covered by integration tests and LightRAG monitoring.

---

### Ollama Cloud Scripts (Not Used)

| Script | Sprint | Reason for Archival |
|--------|--------|---------------------|
| `test_ollama_cloud.py` | 23 | Ollama Cloud not used (using Alibaba Cloud instead) |
| `list_ollama_cloud_models.py` | 23 | Ollama Cloud not used |
| `test_local_ollama.py` | 23 | Basic test, covered by test_alibaba_cloud.py |
| `preload_ollama_models.py` | Pre-23 | Old model preloading, not needed with auto-pull |

**Context:** Initially explored Ollama Cloud as cloud provider, but chose Alibaba Cloud DashScope for better cost/performance (Sprint 23, ADR-033).

---

### Entity Extraction & LLM Pipeline (Obsolete)

| Script | Sprint | Reason for Archival |
|--------|--------|---------------------|
| `test_llm_entity_validation.py` | Pre-20 | Old entity validation, replaced by three-phase extraction (Sprint 13) |
| `test_llm_extraction_pipeline.py` | Pre-20 | Old extraction pipeline, replaced by ExtractionService (Sprint 21+) |

**Context:** Early entity extraction experiments before three-phase extraction (SpaCy + Gemma + LLM validation) was finalized in Sprint 13.

---

### Docling Debugging (Sprint 21)

| Script | Sprint | Reason for Archival |
|--------|--------|---------------------|
| `debug_docling_images.py` | 21 | Sprint 21 debugging script for Docling image extraction |
| `generate_document_ingestion_report.py` | 21 | Sprint 21 reporting, replaced by VLM indexing reports (Sprint 30) |

**Context:** Created during Sprint 21 Docling integration for debugging image extraction. Issues resolved, script no longer needed.

---

### MyPy Fix Scripts (One-Time Use)

| Script | Sprint | Reason for Archival |
|--------|--------|---------------------|
| `fix_mypy_redis_manager.py` | 25 | One-time MyPy fix for redis_manager.py |
| `fix_all_mypy_errors.py` | 25 | One-time bulk MyPy fix script |
| `fix_escaped_quotes.py` | 25 | One-time quote escaping fix |
| `fix_missing_typing_imports.py` | 25 | One-time import fix |
| `fix_langgraph_pipeline_import.py` | 25 | One-time LangGraph import fix |
| `fix_malformed_imports.py` | 25 | One-time import formatting fix |
| `remove_unused_ignores.py` | 25 | One-time cleanup of type: ignore comments |
| `fix_vector_search_errors.py` | 25 | One-time vector search type fix |

**Context:** Sprint 25 Feature 25.5 enabled MyPy strict mode. These scripts were created to bulk-fix type errors and are not reusable.

---

### CI Testing (One-Time)

| Script | Sprint | Reason for Archival |
|--------|--------|---------------------|
| `test_ci_fixes.py` | 24-25 | One-time CI fix validation script |

**Context:** Created to verify CI fixes were working. Tests now covered by CI pipeline and run_ci_checks_local.py.

---

## Migration Notes

### For Model Evaluation
Use AegisLLMProxy routing logic instead:
```python
from src.components.llm_proxy import get_aegis_llm_proxy, LLMTask

proxy = get_aegis_llm_proxy()
task = LLMTask(task_type=TaskType.GENERATION, quality_requirement=QualityRequirement.HIGH, complexity=Complexity.HIGH)
result = await proxy.generate(task)  # Automatic routing to best provider
```

### For Indexing
Use Sprint 30 VLM indexing scripts instead:
```bash
# Single PDF
poetry run python scripts/test_single_pdf.py <pdf_path>

# Directory
poetry run python scripts/test_vlm_indexing.py
```

### For Neo4j Debugging
Use LangGraph integration tests:
```bash
poetry run pytest tests/integration/test_graph_rag.py -v
```

### For Cloud Provider Testing
Use current test scripts:
```bash
# Alibaba Cloud
poetry run python scripts/test_alibaba_cloud.py

# DashScope VLM
poetry run python scripts/test_dashscope_vlm.py
```

---

## Restoration

If any of these scripts need to be restored (unlikely):
```bash
# From scripts/archive/sprint-20-30-obsolete/
cp <script_name>.py ../../
```

---

**Total Scripts Archived:** 21
**Archive Date:** 2025-11-19
**Sprint:** 30
