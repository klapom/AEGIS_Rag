# Scripts Directory

This directory contains production-ready and utility scripts for AEGIS RAG.

**Last Updated**: Sprint 19 (2025-10-30)

---

## Production Scripts

### Document Indexing

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `index_documents.py` | Main production indexing script | Sprint 2 | Index all documents in `data/sample_documents/` |
| `index_one_doc_test.py` | Single document indexing (testing) | Sprint 19 | Test indexing with one PDF (includes path-traversal & start_token fixes) |
| `index_three_specific_docs.py` | Index specific documents | Sprint 19 | Index DE-D-OTAutBasic and DE-D-OTAutAdvanced |
| `init_bm25_index.py` | Initialize BM25 keyword index | Sprint 2 | Setup BM25 search index |

### Query & Testing

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `ask_question.py` | Query the RAG system | Sprint 7 | Interactive Q&A with indexed documents |
| `run_ragas_benchmark.py` | RAGAS evaluation metrics | Sprint 8 | Benchmark retrieval quality (precision, recall, faithfulness) |

### Monitoring & Diagnostics

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `check_indexed_docs.py` | Verify indexed documents | Sprint 16 | Check Qdrant collection status |
| `check_adr.py` | Validate ADR format | Sprint 7 | Lint Architecture Decision Records |
| `check_naming.py` | Enforce naming conventions | Sprint 18 | Validate file/function naming standards |
| `check_imports.py` | Validate Python imports | Sprint 17 | Detect import errors before deployment |

### Benchmarking & Performance

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `benchmark_embeddings.py` | Compare embedding models | Sprint 16 | Test BGE-M3 vs nomic-embed-text |
| `benchmark_gpu.py` | GPU performance profiling | Sprint 14 | Measure Ollama GPU utilization |
| `test_hybrid_10docs.py` | Quick hybrid RAG test | Sprint 16 | Validate Qdrant + Neo4j indexing (10 docs) |
| `test_provenance_quick.py` | Test graph-based provenance | Sprint 14 | Validate LightRAG chunk-entity tracking |

### Setup & Demo

| Script | Purpose | Sprint | Usage |
|--------|---------|--------|-------|
| `setup_demo_data.py` | Create demo conversations | Sprint 12 | Populate UI with sample chat history |

---

## PowerShell Scripts

**Sprint 19 Update**: All PowerShell scripts updated to use current production models.
See `POWERSHELL_VALIDATION_REPORT.md` for detailed validation.

### Ollama Management (Sprint 19 - Updated)

| Script | Purpose | Models | Status |
|--------|---------|--------|--------|
| `setup_ollama_models.ps1` | Download all required models | llama3.2:3b, gemma-3-4b-it-Q8_0, bge-m3 | ✅ Updated |
| `check_ollama_health.ps1` | Verify Ollama + models | Checks connectivity, models, inference | ✅ Updated |
| `download_all_models.ps1` | Simple batch download | Same as setup script | ✅ Updated |

**Key Changes**:
- Upgraded from `nomic-embed-text` (768D) → `bge-m3` (1024D)
- Changed from `llama3.1:8b` → `gemma-3-4b-it-Q8_0` (LightRAG extraction)
- Kept `llama3.2:3b` (chat/generation)

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

- **`archive/deprecated/`**: Obsolete scripts (12 scripts)
  - Old reindex scripts, deprecated test helpers

- **`archive/bash-duplicates/`**: Bash versions of PowerShell scripts (2 scripts)
  - `check_ollama_health.sh`, `setup_ollama_models.sh`
  - Reason: Development on Windows, PowerShell scripts actively maintained

- **`archive/old-memory-config/`**: Old memory configuration (1 script)
  - `set_wsl_memory_9gb.ps1` (replaced by 12GB version)

---

## How to Use

### 1. Index Documents

```bash
# Full indexing (all documents)
poetry run python scripts/index_documents.py

# Test with one document (Sprint 19)
poetry run python scripts/index_one_doc_test.py

# Index specific documents
poetry run python scripts/index_three_specific_docs.py
```

### 2. Query System

```bash
poetry run python scripts/ask_question.py
```

### 3. Run Benchmarks

```bash
# RAGAS evaluation
poetry run python scripts/run_ragas_benchmark.py

# Embedding comparison
poetry run python scripts/benchmark_embeddings.py

# GPU profiling
poetry run python scripts/benchmark_gpu.py
```

### 4. Validate Code Quality

```bash
# Check imports (catch import errors)
poetry run python scripts/check_imports.py

# Check naming conventions
poetry run python scripts/check_naming.py

# Validate ADR format
poetry run python scripts/check_adr.py
```

### 5. Setup Demo Data

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
   # Sprint 19: Added path-traversal fix for temp directories
   ```

4. **Update README**: Add entry to this file when creating production scripts

5. **Archive Old Scripts**: Move deprecated scripts to `archive/` with context

---

## Maintenance Notes

### Sprint 19 Cleanup (2025-10-30)

- Reduced from 57 to 15 production scripts
- Archived 42 old test scripts from Sprints 13-18
- Created organized archive structure
- Updated all active scripts with latest fixes:
  - Path-traversal fix (commit 79abe52)
  - start_token KeyError fix (commit d8e52c0)

### Key Changes

- `index_one_doc_test.py`: New single-document test script with all Sprint 10/16 fixes
- `index_three_specific_docs.py`: Updated with path-traversal fix
- Archive created with 5 subdirectories for better organization

---

**For archived scripts**, see respective `archive/*/README.md` files for context and usage.
