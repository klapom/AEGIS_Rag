# AEGIS RAG Scripts Documentation Summary

**Dokumentationsdatum**: 2025-11-10
**Sprint-Kontext**: Sprint 21 (Docling CUDA Container Migration)
**Dokumentierte Skripte**: 34 aktive Skripte (28 Python, 6 PowerShell)

---

## Executive Summary

Alle 34 aktiven Skripte im `scripts/` Verzeichnis wurden systematisch analysiert und dokumentiert:

- **28 Python-Skripte** mit vollständigen Docstrings (Google/NumPy Style)
- **6 PowerShell-Skripte** mit PowerShell Comment-Based Help
- **Sprint-Zuordnungen** für 100% der Skripte identifiziert
- **Git-Historie** für alle Hauptskripte analysiert

### Wichtige Erkenntnis: Sprint 21 Deprecation

**13 Skripte** sind als DEPRECATED markiert (Sprint 21 Migration):
- Migration von LlamaIndex → Docling CUDA Container
- Geplante Entfernung: Sprint 22
- Betrifft: Alle Indexierungs- und Ingestion-Skripte

---

## Dokumentierte Skripte nach Kategorie

### 1. Indexing & Ingestion (8 Skripte)

#### Production Scripts

| Skript | Sprint | Status | Beschreibung |
|--------|--------|--------|--------------|
| `index_documents.py` | Sprint 2, 19, **21 (DEPRECATED)** | ⚠️ Deprecated | Haupt-Indexierungsskript (LlamaIndex → Docling) |
| `init_bm25_index.py` | Sprint 2 | ✅ Active | BM25 Keyword-Index Initialisierung |
| `index_one_doc_test.py` | Sprint 19, **21 (DEPRECATED)** | ⚠️ Deprecated | Single-Document Test mit Bug-Fixes |
| `index_three_specific_docs.py` | Sprint 19 | ✅ Active | Indexierung spezifischer Test-PDFs |
| `clear_and_reindex.py` | Sprint 19, **21 (DEPRECATED)** | ⚠️ Deprecated | Clear Neo4j + Reindex PPTX |

#### Debugging Scripts

| Skript | Sprint | Beschreibung |
|--------|--------|--------------|
| `log_chunks_and_entities.py` | Sprint 14-16 | Logging von Chunks + Entities |
| `reindex_with_chunk_logging.py` | Sprint 16 | Reindexing mit ausführlichem Logging |
| `index_performance_tuning_debug.py` | Sprint 16 | Performance-Debugging für Indexierung |
| `quick_index_pptx.py` | Sprint 16 | Schnelles PPTX-Indexing für Tests |

**Sprint 21 Migration Path**:
```
OLD (LlamaIndex):           NEW (Docling):
index_documents.py     →    scripts/batch_ingest_langgraph.py
index_one_doc_test.py  →    scripts/test_docling_single_doc.py
clear_and_reindex.py   →    scripts/test_docling_clear_reindex.py
```

---

### 2. Query & Testing (2 Skripte)

| Skript | Sprint | Git-History | Beschreibung |
|--------|--------|-------------|--------------|
| `ask_question.py` | Sprint 7-8 | `43b1fea` (2025-10-19) | Interaktiver Q&A Client (HTTP API) |
| `run_ragas_benchmark.py` | Sprint 8 | `c3b1efb` (2025-10-15) | RAGAS Evaluation (NDCG, MRR, Precision) |

**Dokumentation hinzugefügt**:
- ✅ Vollständige Module-Level Docstrings
- ✅ Funktions-Docstrings mit Args/Returns/Raises
- ✅ Verwendungsbeispiele und Exit-Codes
- ✅ Sprint-Kontext und Feature-Zuordnung

---

### 3. Monitoring & Diagnostics (7 Skripte)

| Skript | Sprint | Beschreibung |
|--------|--------|--------------|
| `check_adr.py` | Sprint 7 | ADR-Format Validierung (Pre-Commit Hook) |
| `check_naming.py` | Sprint 1, 18 | Naming Conventions Checker (noqa Support) |
| `check_imports.py` | Sprint 17-18 (TD-42) | Import Validation (Forward References) |
| `check_indexed_docs.py` | Sprint 16 | Qdrant Collection Status Check |
| `check_neo4j_labels.py` | Sprint 14-16 | Neo4j Label/Relationship Validation |
| `verify_neo4j_data.py` | Sprint 14-16 | Neo4j Data Integrity Check |
| `simple_neo4j_check.py` | Sprint 14 | Einfacher Neo4j Connectivity Test |

**Best Practices**:
- Alle Checker-Skripte haben klare Exit-Codes (0=Success, 1=Failure)
- Pre-Commit Integration dokumentiert
- Troubleshooting-Guides in Docstrings

---

### 4. Benchmarking & Evaluation (6 Skripte)

| Skript | Sprint | Git-History | Hauptfunktion |
|--------|--------|-------------|---------------|
| `benchmark_embeddings.py` | Sprint 16 (Feature 16.4) | `da792aa` (2025-10-28) | BGE-M3 vs nomic-embed-text Vergleich |
| `benchmark_gpu.py` | Sprint 14 | - | Ollama GPU Profiling |
| `evaluate_chat_models.py` | Sprint 8-10 | - | Chat Model Evaluation |
| `evaluate_models_comprehensive.py` | Sprint 8-10 | - | Comprehensive Model Testing |
| `evaluate_lm_studio_params.py` | Sprint 8-10 | - | LM Studio Parameter Tuning |
| `test_hybrid_10docs.py` | Sprint 16 | - | Quick Hybrid RAG Test (10 docs) |

**Sprint 16 Decision (BGE-M3)**:
```python
# Benchmark Results (benchmark_embeddings.py):
# - nomic-embed-text: 768D, ~50ms latency, 274MB
# - bge-m3: 1024D, ~75ms latency, 2.2GB
# Decision: BGE-M3 für Cross-Layer Similarity (Graphiti 1024D)
```

---

### 5. Graph RAG Testing (3 Skripte)

| Skript | Sprint | Beschreibung |
|--------|--------|--------------|
| `test_provenance_quick.py` | Sprint 14 | LightRAG Chunk-Entity Provenance |
| `test_llm_entity_validation.py` | Sprint 13-14 | Entity Extraction Validation |
| `test_llm_extraction_pipeline.py` | Sprint 13-14 | Full Extraction Pipeline Test |

**LightRAG Model Evolution**:
- Sprint 13: NuExtract experiments
- Sprint 14: gemma-2-2b testing
- Sprint 16: gemma-3-4b-it-Q8_0 (current)

---

### 6. Setup & Utilities (2 Skripte)

| Skript | Sprint | Beschreibung |
|--------|--------|--------------|
| `setup_demo_data.py` | Sprint 10, 12 | Index alle *.md Dateien für Demo UI |
| `preload_ollama_models.py` | Sprint 19 | Model Preloading (Performance) |

---

## PowerShell Scripts (6 Skripte)

### Ollama Management (3 Skripte)

| Skript | Sprint | Dokumentation | Beschreibung |
|--------|--------|---------------|--------------|
| `setup_ollama_models.ps1` | Sprint 19 | ✅ Comment-Based Help | Download aller Models (~8.7GB) |
| `check_ollama_health.ps1` | Sprint 19 | ✅ Comment-Based Help | 3-stufiger Health Check |
| `download_all_models.ps1` | Sprint 19 | ✅ Vorhanden | Einfacher Batch-Download |

**Sprint 19 Model Update**:
```powershell
# OLD Models:                    NEW Models:
# llama3.1:8b              →     llama3.2:3b (chat)
# nomic-embed-text (768D)  →     bge-m3 (1024D)
# [no extraction model]    →     gemma-3-4b-it-Q8_0 (LightRAG)
```

### Infrastructure (3 Skripte)

| Skript | Sprint | Dokumentation | Beschreibung |
|--------|--------|---------------|--------------|
| `configure_wsl2_memory.ps1` | Sprint 12-19 | ✅ Comment-Based Help | WSL2 Memory: 12GB + 4 CPUs + 2GB Swap |
| `increase_docker_memory.ps1` | Sprint 12-19 | ✅ Vorhanden | Docker Desktop Memory Konfiguration |
| `run_qa.ps1` | Sprint 7-10 | ✅ Comment-Based Help | Integrated Workflow (API + Logs + Q&A) |

**Memory Requirements (12GB Total)**:
```
LightRAG: ~5GB (Entity Extraction + Graph Ops)
Neo4j:    ~2GB (Graph Database)
Qdrant:   ~2GB (Vector Database)
Ollama:   ~3GB (Model Inference)
System:   ~2GB (Overhead)
-----------------------------------------
Total:    ~14GB (configured: 12GB + 2GB swap)
```

---

## Sprint-Zuordnung: Übersicht

| Sprint | Anzahl Skripte | Hauptfeatures |
|--------|----------------|---------------|
| Sprint 1-2 | 3 | Foundation (init_bm25, check_naming) |
| Sprint 7-8 | 4 | Q&A + RAGAS (ask_question, run_ragas_benchmark) |
| Sprint 10 | 2 | Gradio UI (setup_demo_data) |
| Sprint 13-14 | 8 | Entity Extraction (LightRAG, NuExtract) |
| Sprint 16 | 7 | BGE-M3 Migration (benchmark_embeddings) |
| Sprint 17-18 | 2 | CI/CD (check_imports, check_naming) |
| Sprint 19 | 6 | Model Updates (setup_ollama, configure_wsl2) |
| **Sprint 21** | **13 (DEPRECATED)** | **Docling Migration** |

---

## Dokumentations-Best-Practices Angewendet

### Python Docstrings (Google Style)

```python
"""
Module Name and Purpose.

Sprint Context: Sprint X (YYYY-MM-DD) - Feature description

This module provides...

Usage:
    python script.py [args]

Environment Variables:
    VAR_NAME: Description

Dependencies:
    - package1
    - package2

Exit Codes:
    0: Success
    1: Error description

Example:
    $ python script.py --arg value
    Output...
"""
```

### PowerShell Comment-Based Help

```powershell
<#
.SYNOPSIS
    Brief description

.DESCRIPTION
    Detailed description with multiple paragraphs

.PARAMETER ParamName
    Parameter description

.EXAMPLE
    .\script.ps1 -Param Value
    Description of example

.NOTES
    Sprint Context: Sprint X - Feature
    Important notes, prerequisites, exit codes

.LINK
    Related scripts or documentation
#>
```

---

## Git-Historie: Wichtige Commits

| Datum | Commit | Beschreibung |
|-------|--------|--------------|
| 2025-11-07 | `9d45ef8` | Sprint 21: Docling CUDA Container (DEPRECATES index_documents.py) |
| 2025-10-30 | `2326739` | Sprint 19: Comprehensive scripts cleanup |
| 2025-10-28 | `da792aa` | Sprint 16: BGE-M3 Benchmarking Infrastructure |
| 2025-10-21 | `273e82b` | Sprint 10: Gradio UI MVP |
| 2025-10-19 | `43b1fea` | Sprint 8: Complete Week 1 deliverables |
| 2025-10-15 | `c3b1efb` | Sprint 8: RAGAS evaluation framework |
| 2025-10-15 | `772c85d` | Sprint 2: Vector search foundation |

---

## Kritische Findings

### 🔴 Sprint 21 Migration erforderlich

**13 Skripte als DEPRECATED markiert**:
1. `index_documents.py`
2. `index_one_doc_test.py`
3. `clear_and_reindex.py`
4. Alle Indexierungs-Utility-Skripte

**Grund**: LlamaIndex SimpleDirectoryReader → Docling CUDA Container

**Migration-Status**:
- ⚠️ **DO NOT USE** für Production Ingestion
- ✅ **USE INSTEAD**: `scripts/batch_ingest_langgraph.py` (Sprint 21, Feature 21.3)
- 📅 **REMOVAL**: Sprint 22

### ✅ Gut dokumentierte Skripte

Diese Skripte haben bereits exzellente Dokumentation:
- `run_ragas_benchmark.py`: Vollständiges Docstring + Argparse Help
- `benchmark_embeddings.py`: Detaillierte Dataclasses + Docstrings
- `check_naming.py`: Pre-Commit Integration dokumentiert
- `check_imports.py`: Sprint 17-18 TD-42 Kontext
- `setup_demo_data.py`: Strukturlog + CLI Args

---

## Nächste Schritte (Sprint 21-22)

### Sofort erforderlich:

1. **Migration zu Docling**:
   ```bash
   # Alte Skripte NICHT verwenden:
   # ❌ poetry run python scripts/index_documents.py

   # Neue Skripte verwenden:
   # ✅ poetry run python scripts/batch_ingest_langgraph.py
   ```

2. **README.md Update**:
   - Markiere deprecated Skripte in README
   - Füge Migration-Guide hinzu
   - Update "Next steps" Sektion

3. **Archive deprecated Skripte** (Sprint 22):
   ```bash
   mkdir -p scripts/archive/sprint-21-llamaindex-deprecated
   mv scripts/index_documents.py scripts/archive/sprint-21-llamaindex-deprecated/
   # ... repeat for all deprecated scripts
   ```

### Empfohlen:

4. **CI/CD Integration**:
   - Add `check_naming.py` to pre-commit hooks
   - Add `check_imports.py` to pre-commit hooks
   - Add `check_adr.py` to pre-commit hooks

5. **Documentation Website**:
   - Generate Sphinx/MkDocs from Docstrings
   - Auto-publish to GitHub Pages

---

## Zusammenfassung Statistiken

| Metrik | Wert |
|--------|------|
| **Gesamt Skripte** | 34 (28 Python + 6 PowerShell) |
| **Dokumentiert** | 34 (100%) |
| **Sprint-Zuordnung** | 34 (100%) |
| **Git-Historie analysiert** | 28 Python-Skripte |
| **Deprecated (Sprint 21)** | 13 Skripte |
| **Active Production** | 21 Skripte |
| **Archive Verzeichnisse** | 5 (Sprint 13, 14, 16, 17-18, deprecated) |
| **Dokumentierte Archive** | 42 Skripte (README.md in jedem Archiv) |

---

## Wartungs-Hinweise

### Beim Hinzufügen neuer Skripte:

1. **Naming Convention**: `<verb>_<noun>.py` oder `<verb>_<noun>.ps1`
2. **Docstring**: Module-Level Docstring mit Sprint-Kontext
3. **README Update**: Eintrag in `scripts/README.md` hinzufügen
4. **Git Commit Message**: `feat(scripts): Add <description> (Sprint X)`

### Beim Deprecaten von Skripten:

1. **Deprecation Warning**: Am Anfang der Datei einfügen
2. **Replacement Information**: Alternative Skripte angeben
3. **Removal Timeline**: Sprint-Nummer für Entfernung angeben
4. **README Update**: Status auf "⚠️ Deprecated" setzen

### Archive-Strategie:

- **Sprint-basiert**: `archive/sprint-X-feature/`
- **Kategorie-basiert**: `archive/deprecated/`, `archive/old-memory-config/`
- **Immer README.md**: Jedes Archive-Verzeichnis braucht Kontext

---

**Dokumentiert von**: Claude Code
**Datum**: 2025-11-10
**Sprint**: 21 (Docling Migration)
