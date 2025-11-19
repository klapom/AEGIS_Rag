# Scripts Directory

This directory contains production-ready and utility scripts for AEGIS RAG.

**Last Updated**: Sprint 30 (2025-11-19)

---

## Production Scripts

### Document Indexing

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `index_documents.py` | Main production indexing script | Sprint 2/21 | Index all documents in `data/sample_documents/` |
| `index_one_doc_test.py` | Single document indexing (testing) | Sprint 19 | Test indexing with one PDF (includes path-traversal & start_token fixes) |
| `index_three_specific_docs.py` | Index specific documents | Sprint 19 | Index DE-D-OTAutBasic and DE-D-OTAutAdvanced |
| `init_bm25_index.py` | Initialize BM25 keyword index | Sprint 2 | Setup BM25 search index |

**Sprint 30 Note:** Indexing now uses Docling CUDA Container (Sprint 21, ADR-027) with GPU-accelerated OCR for superior quality.

---

### VLM-Enhanced Indexing (Sprint 30 NEW)

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `test_vlm_indexing.py` | VLM-enhanced directory indexing | Sprint 30 | Index documents with Qwen3-VL image descriptions |
| `test_single_pdf.py` | VLM-enhanced single PDF test | Sprint 30 | Test VLM indexing for one PDF file |

**Features:**
- Docling CUDA Container parsing (95% OCR accuracy)
- Qwen3-VL image descriptions (Alibaba Cloud)
- BGE-M3 embeddings (1024D) → Qdrant
- Neo4j graph extraction
- Progress tracking with detailed statistics

**Usage:**
```bash
# Test single PDF
poetry run python scripts/test_single_pdf.py "path/to/document.pdf"

# Index entire directory
poetry run python scripts/test_vlm_indexing.py
```

---

### Query & Testing

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `ask_question.py` | Query the RAG system | Sprint 7 | Interactive Q&A with indexed documents |
| `run_ragas_benchmark.py` | RAGAS evaluation metrics | Sprint 8 | Benchmark retrieval quality (precision, recall, faithfulness) |

---

### Multi-Cloud LLM Testing (Sprint 23)

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `test_alibaba_cloud.py` | Test Alibaba Cloud DashScope API | Sprint 23 | Validate Qwen models connectivity and routing |
| `test_dashscope_vlm.py` | Test DashScope VLM with fallback | Sprint 23 | Test qwen3-vl models with cost tracking |
| `test_vlm_routing.py` | Test VLM routing logic | Sprint 23 | Validate VLM task routing decisions |
| `query_cost_tracking.py` | SQLite cost database query | Sprint 23 | Analyze LLM costs by provider/model/task |

**Context:** Sprint 23 introduced AegisLLMProxy (ADR-033) with multi-cloud routing:
- **Tier 1 (70%):** Local Ollama (FREE)
- **Tier 2 (20%):** Alibaba Cloud Qwen (~$0.001/1k tokens)
- **Tier 3 (10%):** OpenAI (optional, ~$0.015/1k tokens)

**Usage:**
```bash
# Test Alibaba Cloud connectivity
poetry run python scripts/test_alibaba_cloud.py

# Test DashScope VLM with cost tracking
poetry run python scripts/test_dashscope_vlm.py

# Query cost database
poetry run python scripts/query_cost_tracking.py
```

---

### Monitoring & Diagnostics

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `check_indexed_docs.py` | Verify indexed documents | Sprint 16 | Check Qdrant collection status |
| `check_adr.py` | Validate ADR format | Sprint 7 | Lint Architecture Decision Records |
| `check_naming.py` | Enforce naming conventions | Sprint 18 | Validate file/function naming standards |
| `check_imports.py` | Validate Python imports | Sprint 17 | Detect import errors before deployment |
| `test_metrics_endpoint.py` | Test Prometheus metrics | Sprint 25 | Validate /metrics endpoint and Prometheus export |

---

### Benchmarking & Performance

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `benchmark_embeddings.py` | Compare embedding models | Sprint 16 | Test BGE-M3 vs nomic-embed-text |
| `benchmark_gpu.py` | GPU performance profiling | Sprint 14 | Measure Ollama GPU utilization |
| `test_hybrid_10docs.py` | Quick hybrid RAG test | Sprint 16 | Validate Qdrant + Neo4j indexing (10 docs) |
| `test_provenance_quick.py` | Test graph-based provenance | Sprint 14 | Validate LightRAG chunk-entity tracking |

---

### CI/CD & Quality

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `run_ci_checks_local.py` | Simulate GitHub Actions CI pipeline | Sprint 24 | Run all CI checks locally before push |
| `validate_token_tracking.py` | Validate accurate token tracking | Sprint 25 | Verify input/output split accuracy (Feature 25.3) |
| `generate_sprint_end_report.py` | Generate sprint-end quality report | Sprint 22+ | Code quality metrics aggregation |

**CI Checks Included:**
1. Python import validation
2. MyPy type checking (strict mode)
3. Ruff linting
4. Black formatting
5. Unit tests
6. Integration tests
7. API contract validation

**Usage:**
```bash
# Run full CI suite
poetry run python scripts/run_ci_checks_local.py

# Quick mode (skip tests)
poetry run python scripts/run_ci_checks_local.py --quick

# Validate token tracking accuracy
poetry run python scripts/validate_token_tracking.py

# Generate sprint-end report
poetry run python scripts/generate_sprint_end_report.py --sprint 30 --output report.md
```

---

### Setup & Demo

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `setup_demo_data.py` | Create demo conversations | Sprint 12 | Populate UI with sample chat history |

---

## PowerShell Scripts

**Sprint 19 Update**: All PowerShell scripts updated to use current production models.
See `POWERSHELL_VALIDATION_REPORT.md` for detailed validation.

### System Startup (Sprint 30 NEW)

| Script | Purpose | Features | Status |
|--------|---------|----------|--------|
| `start_aegis_rag.ps1` | One-command system startup | Backend API + Frontend UI + Infrastructure | ✅ Sprint 30 |

**Features:**
- Checks prerequisites (Poetry, Docker, Node.js)
- Starts Docker Compose services (Qdrant, Neo4j, Redis, Ollama)
- Launches Backend API in new terminal (http://localhost:8000)
- Launches Frontend UI in new terminal (http://localhost:5173)
- Performs health checks
- Shows comprehensive service summary

**Usage:**
```powershell
# Start entire system
.\scripts\start_aegis_rag.ps1

# Services will open in separate terminal windows
# Access:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Qdrant: http://localhost:6333/dashboard
# - Neo4j: http://localhost:7474
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

---

### Ollama Management (Sprint 19 - Updated)

| Script | Purpose | Models | Status |
|--------|---------|--------|--------|
| `setup_ollama_models.ps1` | Download all required models | llama3.2:3b, gemma-3-4b-it-Q8_0, bge-m3 | ✅ Updated |
| `check_ollama_health.ps1` | Verify Ollama + models | Checks connectivity, models, inference | ✅ Updated |
| `download_all_models.ps1` | Simple batch download | Same as setup script | ✅ Updated |

**Key Changes:**
- Upgraded from `nomic-embed-text` (768D) → `bge-m3` (1024D)
- Changed from `llama3.1:8b` → `gemma-3-4b-it-Q8_0` (LightRAG extraction)
- Kept `llama3.2:3b` (chat/generation)

**Usage:**
```powershell
# Download all models
.\scripts\setup_ollama_models.ps1

# Check health
.\scripts\check_ollama_health.ps1
```

---

### Infrastructure (12GB Memory Required)

| Script | Purpose | Configuration | Status |
|--------|---------|---------------|--------|
| `configure_wsl2_memory.ps1` | Set WSL2 memory limits | 12GB RAM, 4 CPUs, 2GB swap | ✅ Valid |
| `increase_docker_memory.ps1` | Increase Docker Desktop RAM | 12GB RAM | ✅ Valid |
| `run_qa.ps1` | API + logging + Q&A workflow | Auto-starts API, opens logs, runs Q&A | ✅ Valid |

**Why 12GB?** Required for LightRAG (5GB) + Neo4j (2GB) + Qdrant (2GB) + system overhead

---

## Archive Directories

Old test scripts from previous sprints have been archived:

- **`archive/sprint-13-entity-extraction/`**: Entity/relation extraction experiments (18 scripts)
  - NuExtract models, SpaCy-only tests, LightRAG prompt variations

- **`archive/sprint-14-benchmarks/`**: Model benchmarking scripts (8 scripts)
  - Gemma quantization comparisons, production pipeline benchmarks

- **`archive/sprint-16-metadata/`**: Metadata cleanup experiments (4 scripts)
  - Metadata field analysis, single-file tests

- **`archive/sprint-17-18-admin/`**: Admin feature tests (3 scripts)
  - Admin stats endpoint debugging, conversation archiving tests

- **`archive/sprint-20-30-obsolete/`**: Obsolete scripts from Sprint 20-30 (21 scripts) **NEW**
  - Model evaluation (superseded by AegisLLMProxy)
  - Old indexing scripts (superseded by Docling)
  - Neo4j debugging scripts
  - Ollama Cloud scripts (not used)
  - MyPy fix scripts (one-time use)
  - See `archive/sprint-20-30-obsolete/README.md` for details

- **`archive/deprecated/`**: Obsolete scripts (12 scripts)
  - Old reindex scripts, deprecated test helpers

- **`archive/bash-duplicates/`**: Bash versions of PowerShell scripts (2 scripts)
  - `check_ollama_health.sh`, `setup_ollama_models.sh`
  - Reason: Development on Windows, PowerShell scripts actively maintained

- **`archive/old-memory-config/`**: Old memory configuration (1 script)
  - `set_wsl_memory_9gb.ps1` (replaced by 12GB version)

---

## Feature-Specific Scripts

### Sprint 21 Feature 21.6 (VLM Image Processing)

Located in `scripts/feature_21_6/`:

| Script | Purpose | Status |
|--------|---------|--------|
| `test_metadata_extraction_ad_hoc.py` | Ad-hoc VLM metadata testing | Sprint 21 |
| `generate_docling_report.py` | Docling JSON structure analysis | Sprint 21 |
| `generate_docling_report_enhanced.py` | Enhanced Docling report with images | Sprint 21 |
| `inspect_docling_json.py` | Inspect Docling JSON output | Sprint 21 |
| `inspect_image_structure.py` | Analyze Docling image structure | Sprint 21 |
| `test_qwen3vl_cpu_offload.py` | Test Qwen3-VL CPU offloading | Sprint 21 (experimental) |

**Vision Model Benchmark** (`feature_21_6/vision-model-benchmark/`):
- `generate_test_images.py`: Create synthetic test images
- `benchmark.py`: Benchmark vision models (llava vs qwen3-vl)
- `analyze.py`: Analyze benchmark results

**Context:** Sprint 21 Feature 21.6 implemented VLM-based image description using Qwen3-VL models via Alibaba Cloud DashScope.

---

## How to Use

### 1. Quick Start (Sprint 30)

```powershell
# Start entire system
.\scripts\start_aegis_rag.ps1

# System will auto-start:
# - Docker services (Qdrant, Neo4j, Redis, Ollama)
# - Backend API (http://localhost:8000)
# - Frontend UI (http://localhost:5173)
```

---

### 2. Index Documents (Sprint 30 VLM)

```bash
# Index entire directory with VLM
poetry run python scripts/test_vlm_indexing.py

# Test single PDF
poetry run python scripts/test_single_pdf.py "path/to/document.pdf"

# Full indexing (all documents)
poetry run python scripts/index_documents.py

# Test with one document (Sprint 19)
poetry run python scripts/index_one_doc_test.py

# Index specific documents
poetry run python scripts/index_three_specific_docs.py
```

---

### 3. Query System

```bash
poetry run python scripts/ask_question.py
```

---

### 4. Run Benchmarks

```bash
# RAGAS evaluation
poetry run python scripts/run_ragas_benchmark.py

# Embedding comparison
poetry run python scripts/benchmark_embeddings.py

# GPU profiling
poetry run python scripts/benchmark_gpu.py
```

---

### 5. Test Multi-Cloud LLM (Sprint 23)

```bash
# Test Alibaba Cloud connectivity
poetry run python scripts/test_alibaba_cloud.py

# Test DashScope VLM with cost tracking
poetry run python scripts/test_dashscope_vlm.py

# Query cost database
poetry run python scripts/query_cost_tracking.py
```

---

### 6. Validate Code Quality (Sprint 24+)

```bash
# Run all CI checks locally
poetry run python scripts/run_ci_checks_local.py

# Quick mode (skip tests)
poetry run python scripts/run_ci_checks_local.py --quick

# Check imports (catch import errors)
poetry run python scripts/check_imports.py

# Check naming conventions
poetry run python scripts/check_naming.py

# Validate ADR format
poetry run python scripts/check_adr.py

# Test Prometheus metrics
poetry run python scripts/test_metrics_endpoint.py

# Validate token tracking accuracy
poetry run python scripts/validate_token_tracking.py
```

---

### 7. Setup Demo Data

```bash
poetry run python scripts/setup_demo_data.py
```

---

## Script Development Guidelines

When adding new scripts:

1. **Naming Convention**: Use `<verb>_<noun>.py` format
   - Good: `index_documents.py`, `benchmark_embeddings.py`
   - Bad: `indexer.py`, `bench.py`

2. **Documentation**: Add docstring at top of file
   ```python
   """
   Brief description.

   Sprint X: Context and purpose.
   Usage: python scripts/your_script.py
   """
   ```

3. **Sprint Tracking**: Include sprint number in comments
   ```python
   # Sprint 30: Added VLM image description support
   ```

4. **Update README**: Add entry to this file when creating production scripts

5. **Archive Old Scripts**: Move deprecated scripts to `archive/` with context

---

## Maintenance Notes

### Sprint 30 Cleanup (2025-11-19)

- **Archived 21 scripts** to `archive/sprint-20-30-obsolete/`
- **Added 3 new scripts**: `test_vlm_indexing.py`, `test_single_pdf.py`, `start_aegis_rag.ps1`
- **Updated documentation** with Sprint 30 features:
  - VLM-enhanced indexing
  - Multi-cloud LLM testing
  - CI/CD local simulation
  - System startup automation

**Key Changes:**
- VLM indexing now production-ready (Sprint 30)
- Docling CUDA Container fully integrated (Sprint 21)
- AegisLLMProxy multi-cloud routing (Sprint 23)
- Prometheus metrics and Grafana dashboards (Sprint 25)
- MyPy strict mode enforced (Sprint 25)

---

### Sprint 19 Cleanup (2025-10-30)

- Reduced from 57 to 15 production scripts
- Archived 42 old test scripts from Sprints 13-18
- Created organized archive structure
- Updated all active scripts with latest fixes:
  - Path-traversal fix (commit 79abe52)
  - start_token KeyError fix (commit d8e52c0)

**Key Changes:**
- `index_one_doc_test.py`: New single-document test script with all Sprint 10/16 fixes
- `index_three_specific_docs.py`: Updated with path-traversal fix
- Archive created with 5 subdirectories for better organization

---

## Sprint 30 Highlights

### NEW Scripts
1. **`test_vlm_indexing.py`**: VLM-enhanced directory indexing
   - Docling CUDA parsing + Qwen3-VL descriptions
   - Comprehensive progress tracking
   - Cost tracking via SQLite

2. **`test_single_pdf.py`**: Quick VLM test for single PDF
   - Validates full VLM pipeline
   - Detailed statistics output
   - Error handling and reporting

3. **`start_aegis_rag.ps1`**: One-command system startup
   - Starts all services automatically
   - Opens Backend + Frontend in separate terminals
   - Comprehensive health checks

### UPDATED Scripts
- All PowerShell scripts (Sprint 19): Current model configuration
- All indexing scripts (Sprint 21): Docling CUDA Container support
- All LLM scripts (Sprint 23): AegisLLMProxy routing

### ARCHIVED Scripts (21 total)
- Model evaluation scripts (superseded by AegisLLMProxy)
- Old indexing scripts (superseded by Docling)
- Neo4j debugging scripts (superseded by integration tests)
- Ollama Cloud scripts (not used)
- MyPy fix scripts (one-time use)

---

## Architecture Context

### Document Ingestion (Sprint 21 ADR-027)
- **Primary**: Docling CUDA Container (GPU-accelerated OCR, 95% accuracy)
- **Fallback**: LlamaIndex 0.14.3 (connectors only)
- **VLM**: Qwen3-VL via Alibaba Cloud DashScope

### LLM Routing (Sprint 23 ADR-033)
- **Framework**: AegisLLMProxy (ANY-LLM wrapper)
- **Tier 1 (70%)**: Local Ollama (FREE)
- **Tier 2 (20%)**: Alibaba Cloud Qwen (~$0.001/1k tokens)
- **Tier 3 (10%)**: OpenAI (optional, ~$0.015/1k tokens)
- **Cost Tracking**: SQLite database (persistent tracking)

### Embeddings (Sprint 16 ADR-024)
- **Model**: BGE-M3 (1024-dimensional, multilingual)
- **Provider**: Local Ollama (cost-free)
- **Vector DB**: Qdrant 1.11.0

### Graph RAG (Sprint 13)
- **Framework**: LightRAG with Three-Phase Extraction
- **Graph DB**: Neo4j 5.24 Community Edition
- **Extraction Model**: gemma-3-4b-it-Q8_0 (local)

---

**For archived scripts**, see respective `archive/*/README.md` files for context and usage.

---

**Total Production Scripts**: 32 (up from 15 in Sprint 19)
**Total Archived**: 69 scripts across 6 archive directories
**Last Cleanup**: Sprint 30 (2025-11-19)
