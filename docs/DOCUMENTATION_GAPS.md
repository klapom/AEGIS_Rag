# DOCUMENTATION GAPS - AEGIS RAG

**Erstellungsdatum:** 2025-11-10
**Basierend auf:** DRIFT_ANALYSIS.md v1.0
**Status:** Initial Assessment
**Zweck:** Vollständige Liste aller fehlenden/veralteten Dokumentationen

---

## Executive Summary

Nach systematischer Analyse wurden **47 Dokumentations-Lücken** in 7 Kategorien identifiziert:

### Gap Distribution

| Kategorie | Gaps | Severity | Effort (h) |
|-----------|------|----------|------------|
| **Architecture Decision Records (ADRs)** | 13 fehlen | ⚠️ HOCH | 26h |
| **Core Documentation Updates** | 7 veraltet | ✅ KRITISCH | 15h |
| **Architecture Documentation** | 6 fehlen | ⚠️ HOCH | 18h |
| **API Documentation** | 5 inkomplett | ⚠️ MITTEL | 12h |
| **Code Documentation** | 8 Bereiche | ℹ️ NIEDRIG | 20h |
| **User Documentation** | 4 fehlen | ⚠️ MITTEL | 10h |
| **Developer Documentation** | 4 fehlen | ⚠️ MITTEL | 8h |

**Total:** 47 Gaps, 109 Stunden Aufwand (13.6 Tage)

---

## 1. Architecture Decision Records (ADRs) ❌ 13 GAPS

### 1.1 Fehlende ADRs (Kritische Entscheidungen)

#### ADR-027: Docling Container vs. LlamaIndex ✅ KRITISCH
**Status:** FEHLT
**Entscheidung:** Docling CUDA Container statt LlamaIndex für Document Parsing
**Sprint:** 21
**Impact:** HOCH - Deployment-kritisch, neue Docker/GPU Dependency
**Aufwand:** 3 Stunden
**Begründung:** Massivste Architektur-Änderung des Projekts ohne ADR
**Plan:** Siehe DOCUMENTATION_PLAN.md Task 1.1

#### ADR-028: LlamaIndex Deprecation Strategy ⚠️ WICHTIG
**Status:** FEHLT
**Entscheidung:** LlamaIndex wird zu Legacy Support degradiert
**Sprint:** 21
**Impact:** MITTEL - Migration Strategy fehlt
**Aufwand:** 2 Stunden
**Begründung:** Unklar welche LlamaIndex-Komponenten bleiben/gehen
**Inhalt:**
- Status: Accepted
- Context: Docling übernimmt Primary Ingestion
- Decision: LlamaIndex → Legacy Support Only
- Migration Plan: Welche Files migrieren, welche behalten
- Timeline: Vollständige Removal in Sprint 23?

#### ADR-029: React Frontend Migration Deferral ⚠️ WICHTIG
**Status:** FEHLT
**Entscheidung:** React Migration von Sprint 14 auf Sprint 22+ verschoben
**Sprint:** 14 → 21 (Deferral)
**Impact:** MITTEL - Roadmap-Anpassung, Stakeholder Communication
**Aufwand:** 1.5 Stunden
**Begründung:** Ursprünglicher Plan nicht umgesetzt, Gründe nicht dokumentiert
**Inhalt:**
- Status: Accepted
- Context: Sprint 14 Plan (React), nicht umgesetzt bis Sprint 21
- Decision: Gradio Retention bis Sprint 22+
- Rationale: Performance + Ingestion Priorität
- Consequences: Trade-off zwischen UI Polish und Core Features

#### ADR-030: Sprint Plan Extension (12 → 21+ Sprints) ⚠️ WICHTIG
**Status:** FEHLT
**Entscheidung:** Projekt-Scope von 12 auf 21+ Sprints erweitert
**Sprint:** 13 (Start der Extension)
**Impact:** MITTEL - Project Timeline + Budget Impact
**Aufwand:** 2 Stunden
**Begründung:** Original-Roadmap deutlich überschritten, keine Revision
**Inhalt:**
- Status: Accepted
- Context: Original Plan 12 Sprints, aktuell 21+
- Decision: Extension wegen zusätzlicher Features
- Rationale: Performance-Optimierungen, Advanced Features
- Consequences: +75% Timeline, aber bessere Produkt-Qualität

#### ADR-010, ADR-011, ADR-012, ADR-013 ℹ️ LÜCKEN
**Status:** FEHLT (Nummern-Lücken in ADR-Index)
**Sprint:** Unbekannt
**Impact:** NIEDRIG - Unklar ob vergessen oder nie geplant
**Aufwand:** 0.5 Stunden (Review + Klärung)
**Aktion:** Prüfen ob Lücken intentional (sprunghafte Nummerierung) oder fehlende ADRs

### 1.2 Fehlende ADRs (Technische Entscheidungen)

#### ADR-031: GPU Memory Management Strategy ⚠️ MITTEL
**Status:** FEHLT
**Entscheidung:** Container Start/Stop für Memory-Optimierung
**Sprint:** 21
**Impact:** MITTEL - Core Architecture Pattern
**Aufwand:** 2 Stunden
**Inhalt:**
- Context: 4.4GB RAM constraint, RTX 3060 6GB VRAM
- Decision: Sequential Pipeline mit Container Lifecycle Management
- Alternatives: Parallel Execution (rejected - OOM), Smaller Models
- Consequences: +Latency (container start 30-45s), +Complexity

#### ADR-032: Docker Compose Profiles Strategy ℹ️ NIEDRIG
**Status:** FEHLT
**Entscheidung:** Ingestion-Profile für on-demand Docling
**Sprint:** 21
**Impact:** NIEDRIG - Deployment Pattern
**Aufwand:** 1 Stunde
**Inhalt:**
- Context: Docling sollte nicht always-on sein (GPU waste)
- Decision: `--profile ingestion` für manuellen Start
- Alternatives: Always-on (rejected - resource waste), Kubernetes Jobs
- Implementation: docker-compose.yml Profile + Dokumentation

#### ADR-033: Ollama Model Selection Matrix ℹ️ NIEDRIG
**Status:** FEHLT
**Entscheidung:** Welches Modell für welchen Use Case
**Sprint:** 20 (Mirostat v2 Optimization)
**Impact:** NIEDRIG - Operational Guidance
**Aufwand:** 1.5 Stunden
**Inhalt:**
- Context: 4+ Ollama Models verfügbar (llama3.2:3b/8b, gemma-3-4b, qwen2.5)
- Decision Matrix:
  - Query Understanding: llama3.2:3b (fast, 2GB)
  - Generation: llama3.2:8b (quality, 4.7GB)
  - Entity Extraction: gemma-3-4b-it (structured output)
  - Complex Reasoning: qwen2.5:7b (optional)
- Performance Characteristics per Model

#### ADR-034: Chunk Size Evolution Strategy ℹ️ NIEDRIG
**Status:** FEHLT
**Entscheidung:** 600 → 1200 → 1800 tokens Evolution
**Sprint:** 16 → 21
**Impact:** NIEDRIG - aber wichtig für Nachvollziehbarkeit
**Aufwand:** 1.5 Stunden
**Inhalt:**
- Sprint 16: 600 tokens (baseline)
- Sprint 20 Analysis: 65% overhead bei 600 tokens
- Sprint 21: 1800 tokens (3x größer, enables Pure LLM)
- Rationale: Balance zwischen Context und Processing Overhead

#### ADR-035: SpaCy vs. Pure LLM Evolution ℹ️ NIEDRIG
**Status:** FEHLT (teilweise in ADR-026, aber nicht vollständig)
**Entscheidung:** Three-Phase (SpaCy) vs. Pure LLM Extraction
**Sprint:** 13 → 20 → 21
**Impact:** NIEDRIG - Evolutions-Geschichte
**Aufwand:** 2 Stunden
**Inhalt:**
- Sprint 13: Three-Phase Pipeline (SpaCy + Dedup + Gemma)
- Sprint 20: Three-Phase als Default (Performance)
- Sprint 21: Pure LLM als Default (Quality, ADR-026)
- Consolidated Rationale

---

## 2. Core Documentation Updates ✅ 7 GAPS (KRITISCH)

### 2.1 CLAUDE.md (Hauptkontext für Claude Code)

**File:** `docs/core/CLAUDE.md`
**Last Updated:** 2025-10-28 (Sprint 15)
**Current Sprint:** 21 (6 Sprints behind!)
**Impact:** KRITISCH - Claude Code generiert veralteten Code
**Aufwand:** 2 Stunden
**Gaps:**

1. **Project State Section (Line 15):**
   - ❌ Current: "Sprint 15"
   - ✅ Target: "Sprint 21"
   - ❌ Missing: Sprint 17-21 Achievements

2. **Tech Stack Section (Line 55):**
   - ❌ Current: "Data Ingestion: LlamaIndex 0.11+"
   - ✅ Target: "Docling CUDA Container + LlamaIndex (legacy)"

3. **Embeddings (Line 66):**
   - ❌ Current: "nomic-embed-text (768-dim)"
   - ✅ Target: "BGE-M3 (1024-dim)"

4. **Repository Structure (Line 80):**
   - ❌ Missing: `src/components/ingestion/` (Sprint 21)
   - ❌ Missing: `src/core/chunking_service.py` (Sprint 16)

5. **Critical Implementation Details (Line 108):**
   - ❌ Missing: Docling Container example code
   - ❌ Missing: Ingestion State Machine example

6. **Environment Variables (Line 234):**
   - ❌ Missing: `DOCLING_BASE_URL`, `DOCLING_ENABLED`
   - ❌ Missing: `EXTRACTION_PIPELINE=llm_extraction`
   - ❌ Missing: Mirostat v2 parameters (Sprint 20)

7. **Troubleshooting Section (Line 322):**
   - ❌ Missing: Docling Container issues
   - ❌ Missing: GPU memory leak workaround

**Plan:** Siehe DOCUMENTATION_PLAN.md Task 1.2

---

### 2.2 PROJECT_SUMMARY.md

**File:** `docs/core/PROJECT_SUMMARY.md`
**Last Updated:** 2025-10-28 (Sprint 16)
**Current Sprint:** 21 (5 Sprints behind)
**Impact:** HOCH - Stakeholder Communication
**Aufwand:** 1.5 Stunden
**Gaps:**

1. **Sprint Progress Table:**
   - ❌ Missing: Sprint 17-21 entries
   - ❌ Outdated: "515/584 SP (88.2%)" - Sprint 21 SP fehlen

2. **Sprint Achievements:**
   - ❌ Missing: Sprint 17 (Admin UI, Conversation Persistence)
   - ❌ Missing: Sprint 20 (Mirostat v2, Entity Fix)
   - ❌ Missing: Sprint 21 (Docling Container)

3. **Technology Stack:**
   - ❌ Outdated: LlamaIndex als Primary
   - ❌ Missing: Docling

---

### 2.3 TECH_STACK.md

**File:** `docs/core/TECH_STACK.md`
**Last Updated:** 2025-10-28 (Sprint 16)
**Current Sprint:** 21
**Impact:** HOCH - Setup/Deployment
**Aufwand:** 2 Stunden
**Gaps:**

1. **Core Stack Table:**
   - ❌ Missing: Docling CUDA Container row
   - ❌ Outdated: "LlamaIndex 0.11+" (nicht mehr Primary)
   - ❌ Outdated: "nomic-embed-text" → "BGE-M3"

2. **Detailed Analysis Sections:**
   - ❌ Missing: Docling section (Features, Why chosen, Alternatives)
   - ❌ Missing: Docker Container Strategy section
   - ❌ Missing: NVIDIA Container Toolkit requirements

3. **Cost Estimation:**
   - ❌ Outdated: Docker GPU nodes nicht eingerechnet

---

### 2.4 QUICK_START.md

**File:** `docs/core/QUICK_START.md`
**Last Updated:** Unbekannt (vermutlich Sprint 10 oder früher)
**Current Sprint:** 21
**Impact:** KRITISCH - Onboarding blockiert
**Aufwand:** 2 Stunden
**Gaps:**

1. **Prerequisites Section:**
   - ❌ Missing: NVIDIA Container Toolkit installation
   - ❌ Missing: Docker Desktop GPU support
   - ❌ Missing: GPU verification steps (`nvidia-smi`)

2. **Docker Compose Section:**
   - ❌ Missing: `--profile ingestion` usage
   - ❌ Missing: Docling health check

3. **Troubleshooting:**
   - ❌ Missing: "Docling won't start" scenarios
   - ❌ Missing: GPU access failures

**Plan:** Siehe DOCUMENTATION_PLAN.md Task 1.3

---

### 2.5 DECISION_LOG.md

**File:** `docs/DECISION_LOG.md`
**Last Updated:** 2025-10-22 (Sprint 16)
**Current Sprint:** 21
**Impact:** MITTEL - Nachvollziehbarkeit
**Aufwand:** 3 Stunden
**Gaps:**

1. **Missing Sprint Entries:**
   - ❌ Sprint 17: Admin UI, Conversation Persistence, User Profiling
   - ❌ Sprint 18: Status unklar (durchgeführt oder nicht?)
   - ❌ Sprint 19: Komplett fehlt (kein Dokument)
   - ❌ Sprint 20: Mirostat v2 (86% speedup), Entity Bug Fix
   - ❌ Sprint 21: Docling Container, Pure LLM Default

2. **Pivot Points:**
   - ❌ Missing: React Deferral (Sprint 14 → 22+)
   - ❌ Missing: Sprint Extension Rationale (12 → 21+)

---

### 2.6 README.md (Root)

**File:** `README.md`
**Last Updated:** 2025-10-29 (aktuell)
**Current Sprint:** 21
**Impact:** MITTEL - Erste Anlaufstelle
**Aufwand:** 1 Stunde
**Gaps:**

1. **Tech Stack Section (Line 61-76):**
   - ❌ Outdated: "Data Ingestion: LlamaIndex 0.11+"
   - ❌ Missing: Docling

2. **Sprint Plan (Line 110-132):**
   - ❌ Inkonsistent: Original Plan (12 Sprints) vs. Realität (21 Sprints)
   - ❌ Sprint 18 Status unklar
   - ❌ Sprint 19 fehlt

3. **Recent Highlights (Line 144-163):**
   - ❌ Missing: Sprint 21 (Docling)
   - ❌ Outdated: Sprint 18 als "PLANNED" gelistet

---

### 2.7 NAMING_CONVENTIONS.md

**File:** `docs/core/NAMING_CONVENTIONS.md`
**Last Updated:** 2025-10-27
**Current Sprint:** 21
**Impact:** NIEDRIG - Keine kritischen Gaps
**Aufwand:** 0.5 Stunden
**Gaps:**

1. **Component-Specific Conventions:**
   - ⚠️ Missing: Docling-spezifische Naming Patterns
   - ⚠️ Missing: LangGraph Node Naming (langgraph_nodes.py)

**Status:** Überwiegend aktuell, nur Minor Updates

---

## 3. Architecture Documentation ⚠️ 6 GAPS (HOCH)

### 3.1 Architecture Overview Diagram

**File:** `docs/architecture/CURRENT_ARCHITECTURE.md`
**Status:** FEHLT KOMPLETT
**Impact:** KRITISCH - Keine visuelle Übersicht
**Aufwand:** 4 Stunden
**Benötigt:**

1. **High-Level Mermaid Diagram:**
   - Client Layer (Gradio UI, FastAPI)
   - LangGraph Orchestration (Router, Agents)
   - Docker Containers (Ollama, Qdrant, Neo4j, Redis, Docling)
   - Monitoring (Prometheus, Grafana)

2. **Data Flow Diagrams:**
   - Ingestion Flow (Sprint 21): User → API → LangGraph → Docling → Chunking → Embedding → Graph
   - Retrieval Flow (Hybrid): User → Router → Vector+Graph → Generator → Response

3. **Deployment Topology:**
   - Development (Docker Compose)
   - Production (Kubernetes)

4. **Component Interaction Map:**
   - Welche Services kommunizieren wie?
   - Ports, Protocols, Dependencies

**Plan:** Siehe DOCUMENTATION_PLAN.md Task 1.4

---

### 3.2 Component Documentation

**Directory:** `docs/architecture/components/`
**Status:** FEHLT KOMPLETT
**Impact:** HOCH - Deep-Dive Dokumentation fehlt
**Aufwand:** 8 Stunden (total für alle Components)
**Benötigt:**

#### 3.2.1 INGESTION_PIPELINE.md
**Aufwand:** 2 Stunden
**Inhalt:**
- Docling Container Client API
- LangGraph State Machine Details
- Node Implementations (memory_check, docling, chunking, embedding, graph_extraction)
- Error Handling & Retry Logic
- Progress Tracking (SSE)

#### 3.2.2 VECTOR_SEARCH.md
**Aufwand:** 1.5 Stunden
**Inhalt:**
- Qdrant Collections Schema
- BGE-M3 Embedding Process
- BM25 Keyword Search
- Reciprocal Rank Fusion (RRF)
- Cross-Encoder Reranking

#### 3.2.3 GRAPH_RAG.md
**Aufwand:** 1.5 Stunden
**Inhalt:**
- LightRAG Integration
- Entity/Relation Extraction Pipelines (3 types)
- Neo4j Schema
- Community Detection (Leiden)
- Graph Query Patterns

#### 3.2.4 MEMORY_ARCHITECTURE.md
**Aufwand:** 1.5 Stunden
**Inhalt:**
- 3-Layer Architecture Details
- Redis (Layer 1): Short-term memory
- Qdrant (Layer 2): Semantic long-term
- Graphiti (Layer 3): Episodic temporal
- Memory Consolidation Pipeline

#### 3.2.5 ORCHESTRATION.md
**Aufwand:** 1.5 Stunden
**Inhalt:**
- LangGraph Architecture
- Agent Definitions (Router, Vector, Graph, Memory, Generator)
- State Management (AgentState, IngestionState)
- Conditional Routing Logic
- Parallel Execution (Send API)

---

### 3.3 Data Flow Documentation

**File:** `docs/architecture/DATA_FLOW.md`
**Status:** FEHLT
**Impact:** MITTEL - Understanding von End-to-End Flows
**Aufwand:** 2 Stunden
**Benötigt:**

1. **User Query Flow (Retrieval):**
   - User → API → Router → [Vector/Graph/Memory] → Generator → SSE Stream → User
   - Latency breakdown per stage
   - Error paths

2. **Document Ingestion Flow:**
   - User Upload → API → LangGraph → Docling → ... → Neo4j/Qdrant
   - Batch processing
   - Failure scenarios

3. **Memory Consolidation Flow:**
   - Background job (APScheduler)
   - Redis → Qdrant/Graphiti migration
   - Eviction policies

---

### 3.4 Deployment Architecture

**File:** `docs/architecture/DEPLOYMENT.md`
**Status:** TEILWEISE (PRODUCTION_DEPLOYMENT_GUIDE.md existiert, aber veraltet)
**Impact:** HOCH - Deployment-kritisch
**Aufwand:** 3 Stunden (Update)
**Gaps:**

1. **Docling Container Deployment:**
   - ❌ Missing: Docker Compose Profile Strategy
   - ❌ Missing: Kubernetes DaemonSet für GPU nodes
   - ❌ Missing: Health checks für Docling

2. **GPU Node Requirements:**
   - ❌ Missing: NVIDIA Driver versions
   - ❌ Missing: CUDA Toolkit versions
   - ❌ Missing: Memory allocation strategy

3. **Container Orchestration:**
   - ❌ Missing: Start/Stop automation
   - ❌ Missing: Batch job scheduling (K8s CronJobs)

**Action:** Update existing `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`

---

### 3.5 Integration Points

**File:** `docs/architecture/INTEGRATION_POINTS.md`
**Status:** FEHLT
**Impact:** MITTEL - Für Erweiterungen wichtig
**Aufwand:** 1.5 Stunden
**Benötigt:**

1. **REST API Endpoints:**
   - Alle FastAPI Routes
   - Request/Response Schemas
   - Authentication Requirements

2. **Docker Service APIs:**
   - Docling HTTP API (POST /parse)
   - Ollama API (POST /api/generate, /api/embeddings)
   - Qdrant API (REST + gRPC)
   - Neo4j Bolt Protocol

3. **Internal Component APIs:**
   - ChunkingService interface
   - EmbeddingService interface
   - ExtractionPipeline interface

---

### 3.6 Performance Characteristics

**File:** `docs/architecture/PERFORMANCE.md`
**Status:** TEILWEISE (verstreut in Sprint Docs)
**Impact:** MITTEL - Für Capacity Planning
**Aufwand:** 2 Stunden (Konsolidierung)
**Benötigt:**

1. **Latency Targets:**
   - p50, p95, p99 per Operation
   - Actual vs. Target comparison

2. **Throughput Metrics:**
   - QPS sustained/peak
   - Concurrent users
   - Ingestion docs/hour

3. **Resource Utilization:**
   - CPU, RAM, VRAM per Service
   - Disk I/O patterns

4. **Scaling Characteristics:**
   - Horizontal scaling limits
   - Vertical scaling recommendations

**Action:** Konsolidiere aus Sprint Docs → Zentrale Performance-Doku

---

## 4. API Documentation ⚠️ 5 GAPS (MITTEL)

### 4.1 API Reference (OpenAPI)

**File:** `docs/api/ENDPOINTS.md`
**Status:** FEHLT (nur auto-generated OpenAPI unter /docs)
**Impact:** MITTEL - Developer Experience
**Aufwand:** 4 Stunden
**Benötigt:**

1. **Endpoint Listing:**
   - Alle 30+ FastAPI Endpoints
   - Gruppierung nach Funktionalität

2. **Request/Response Schemas:**
   - Pydantic Model Documentation
   - Field descriptions
   - Validation rules

3. **Code Examples:**
   - curl commands
   - Python (requests/httpx)
   - TypeScript (fetch)

4. **Authentication:**
   - JWT Token Acquisition
   - Header format
   - Rate limits

**Current:** OpenAPI Spec unter http://localhost:8000/docs (gut, aber nicht in Markdown docs/)

---

### 4.2 SSE Streaming API

**File:** `docs/api/SSE_STREAMING.md`
**Status:** FEHLT
**Impact:** MITTEL - Für UI Entwicklung wichtig
**Aufwand:** 1.5 Stunden
**Benötigt:**

1. **SSE Format:**
   - Event types (message, progress, error, done)
   - Data structure per event

2. **Client Implementation:**
   - JavaScript EventSource example
   - Python SSE client example
   - Error handling

3. **Endpoints using SSE:**
   - `/api/v1/chat/stream`
   - `/api/v1/admin/reindex` (progress tracking)

---

### 4.3 Admin API

**File:** `docs/api/ADMIN_ENDPOINTS.md`
**Status:** FEHLT
**Impact:** NIEDRIG - Operational Docs
**Aufwand:** 1.5 Stunden
**Benötigt:**

1. **Reindexing API:**
   - POST /api/v1/admin/reindex
   - Query parameters (confirm, dry_run)
   - SSE progress events

2. **Health Checks:**
   - GET /health
   - GET /health/detailed
   - Response format

3. **Metrics Export:**
   - GET /metrics (Prometheus)

---

### 4.4 Pydantic Models

**File:** `docs/api/MODELS.md`
**Status:** FEHLT
**Impact:** NIEDRIG - Auto-generated via OpenAPI ausreichend
**Aufwand:** 2 Stunden (optional)
**Benötigt:**

1. **Core Models:**
   - AgentState (TypedDict)
   - IngestionState (TypedDict)
   - DocumentChunk (Pydantic)
   - QueryRequest/Response (Pydantic)

2. **Field Descriptions:**
   - Purpose of each field
   - Validation rules
   - Example values

**Optional:** Auto-generate via pydantic-to-markdown tool

---

### 4.5 Error Responses

**File:** `docs/api/ERROR_CODES.md`
**Status:** FEHLT
**Impact:** NIEDRIG - aber hilfreich für Frontend
**Aufwand:** 1 Stunde
**Benötigt:**

1. **HTTP Status Codes:**
   - 400: Bad Request (validation errors)
   - 401: Unauthorized (JWT missing/invalid)
   - 429: Rate Limit Exceeded
   - 500: Internal Server Error
   - 503: Service Unavailable (e.g., Ollama down)

2. **Error Response Format:**
   - JSON structure
   - Error codes (DOCLING_UNAVAILABLE, QDRANT_CONNECTION_FAILED, etc.)
   - User-friendly messages

---

## 5. Code Documentation ℹ️ 8 GAPS (NIEDRIG)

### 5.1 Module Docstrings

**Scope:** Alle Python Files in `src/`
**Current Coverage:** Unbekannt (Schätzung: ~70%)
**Target Coverage:** >90%
**Impact:** NIEDRIG - aber Best Practice
**Aufwand:** 6 Stunden (Audit + Fix)
**Aktion:**

1. **Audit Script:**
   - Scan alle `src/**/*.py`
   - Check: Module docstring vorhanden?
   - Generate report: `docs/CODE_DOCUMENTATION_GAPS.md`

2. **Add Missing Docstrings:**
   - Template:
     ```python
     """Module name.

     Brief description of module purpose.

     This module provides:
     - Feature 1
     - Feature 2

     Example:
         >>> from src.module import MyClass
         >>> obj = MyClass()
     """
     ```

---

### 5.2 Function Docstrings

**Scope:** Alle Public Functions (ohne leading `_`)
**Current Coverage:** Schätzung: ~60%
**Target Coverage:** >80%
**Impact:** NIEDRIG
**Aufwand:** 8 Stunden (Major effort)
**Aktion:**

1. **Priority Functions:**
   - `DoclingContainerClient` methods (HIGH)
   - `ChunkingService` methods (HIGH)
   - `LangGraph` node functions (HIGH)
   - Utility functions (MEDIUM)

2. **Template:**
   ```python
   def my_function(arg1: str, arg2: int) -> bool:
       """Brief description.

       Detailed explanation of what function does.

       Args:
           arg1: Description of arg1
           arg2: Description of arg2

       Returns:
           Description of return value

       Raises:
           ValueError: When arg1 is invalid
           IngestionError: When parsing fails

       Example:
           >>> result = my_function("test", 42)
           >>> result
           True
       """
   ```

---

### 5.3 Complex Algorithms

**Scope:** Performance-kritische oder komplexe Funktionen
**Current:** Einige haben Kommentare, aber inkonsistent
**Impact:** NIEDRIG - aber wichtig für Maintenance
**Aufwand:** 4 Stunden
**Kandidaten:**

1. **Reciprocal Rank Fusion (hybrid_search.py):**
   - ✅ Aktuell: Gute inline comments
   - Action: Formalize in docstring

2. **Three-Phase Entity Extraction (three_phase_extractor.py):**
   - ⚠️ Aktuell: Minimal comments
   - Action: Add algorithm explanation

3. **Memory Consolidation (memory_consolidation.py):**
   - ⚠️ Aktuell: Logik unklar
   - Action: Flowchart + docstring

4. **Semantic Deduplication (semantic_dedup.py):**
   - ✅ Aktuell: OK
   - Action: Minor cleanup

---

### 5.4 Type Hints

**Scope:** Alle Functions
**Current Coverage:** Schätzung: ~85% (MyPy enforced)
**Target Coverage:** 100%
**Impact:** NIEDRIG - MyPy enforcement hilft
**Aufwand:** 2 Stunden (Fix remaining)
**Aktion:**

1. **MyPy Strict Mode Check:**
   ```bash
   mypy src/ --strict
   ```

2. **Fix Missing Hints:**
   - Priorität: Public Functions
   - Optional: Private Functions

---

### 5.5 Inline Comments

**Scope:** Complex code blocks
**Current:** Inconsistent
**Impact:** NIEDRIG
**Aufwand:** 3 Stunden (Review + Add)
**Guidelines:**

1. **When to Comment:**
   - Non-obvious logic
   - Workarounds (with "# TODO: Fix properly")
   - Magic numbers/constants
   - Performance optimizations

2. **When NOT to Comment:**
   - Obvious code (self-explanatory)
   - Redundant to docstring

---

### 5.6 Configuration Examples

**Scope:** Alle Config Files
**Files:** `config.py`, `.env.example`, `docker-compose.yml`
**Current:** Partial comments
**Impact:** NIEDRIG
**Aufwand:** 1.5 Stunden
**Aktion:**

1. **config.py:**
   - ✅ Aktuell: Pydantic Field descriptions (gut)
   - Action: Add more examples in docstrings

2. **.env.example:**
   - ⚠️ Aktuell: Minimal comments
   - Action: Add inline comments per setting

3. **docker-compose.yml:**
   - ✅ Aktuell: Good section comments (Sprint 21)
   - Action: Minor cleanup

---

### 5.7 Test Documentation

**Scope:** Test docstrings + README in tests/
**Current:** Minimal
**Impact:** NIEDRIG
**Aufwand:** 2 Stunden
**Aktion:**

1. **tests/README.md:**
   - Create: Test structure explanation
   - Test naming conventions
   - How to run tests (pytest commands)

2. **Test Docstrings:**
   - Template:
     ```python
     def test_docling_client_parse_document():
         """Test Docling client parses PDF correctly.

         Given: Valid PDF file (sample.pdf)
         When: DoclingClient.parse_document() called
         Then: Returns DoclingParsedDocument with text + metadata
         """
     ```

---

### 5.8 Code Examples

**Scope:** Usage examples in key modules
**Current:** Some modules have examples in docstrings, but inconsistent
**Impact:** NIEDRIG
**Aufwand:** 2 Stunden
**Aktion:**

1. **Priority Modules:**
   - `DoclingContainerClient` (HIGH)
   - `ChunkingService` (HIGH)
   - `LangGraph` state machines (MEDIUM)

2. **Example Location:**
   - In module docstring (simple usage)
   - In `docs/examples/` (complex scenarios)

---

## 6. User Documentation ⚠️ 4 GAPS (MITTEL)

### 6.1 User Guide

**File:** `docs/user/USER_GUIDE.md`
**Status:** FEHLT
**Impact:** MITTEL - Für End-User wichtig
**Aufwand:** 3 Stunden
**Benötigt:**

1. **Getting Started:**
   - What is AEGIS RAG?
   - Use cases
   - System requirements

2. **Using the Chat Interface:**
   - Gradio UI walkthrough
   - Search modes explained (Hybrid, Vector, Graph, Memory)
   - File upload for document ingestion

3. **Tips & Tricks:**
   - Best query formulation
   - When to use which mode
   - Understanding responses

---

### 6.2 FAQ

**File:** `docs/user/FAQ.md`
**Status:** FEHLT
**Impact:** NIEDRIG - aber reduziert Support-Last
**Aufwand:** 2 Stunden
**Benötigt:**

1. **Common Questions:**
   - Q: Why is my query slow?
   - Q: How do I upload documents?
   - Q: What file formats are supported?
   - Q: Can I delete indexed documents?
   - Q: How do I export search results?

2. **Troubleshooting:**
   - Query returns no results → Try different mode
   - Ingestion fails → Check file format
   - Response is irrelevant → Refine query

---

### 6.3 Tutorial

**File:** `docs/user/TUTORIAL.md`
**Status:** FEHLT
**Impact:** NIEDRIG
**Aufwand:** 3 Stunden
**Benötigt:**

1. **Tutorial 1: First Query:**
   - Start Gradio UI
   - Enter simple query
   - Understand response

2. **Tutorial 2: Document Upload:**
   - Upload PDF
   - Wait for ingestion
   - Query uploaded document

3. **Tutorial 3: Advanced Search:**
   - Use Graph mode for relationship queries
   - Use Memory mode for conversational context
   - Combine modes

---

### 6.4 Release Notes

**File:** `docs/RELEASE_NOTES.md` oder `CHANGELOG.md`
**Status:** FEHLT
**Impact:** NIEDRIG - aber Best Practice
**Aufwand:** 2 Stunden (+ ongoing maintenance)
**Format:**

```markdown
# Release Notes

## v1.2.0 - Sprint 21 (2025-11-07)

### Added
- Docling CUDA Container for GPU-accelerated document parsing
- LangGraph State Machine for ingestion pipeline
- Pure LLM extraction as default (ADR-026)

### Changed
- BGE-M3 embeddings (1024-dim) now default
- Chunk size increased to 1800 tokens

### Fixed
- Entity extraction bug (entities not created in Neo4j)

### Deprecated
- LlamaIndex as primary ingestion (now legacy support)

## v1.1.0 - Sprint 16 (2025-10-28)
...
```

---

## 7. Developer Documentation ⚠️ 4 GAPS (MITTEL)

### 7.1 Development Setup

**File:** `docs/development/SETUP.md`
**Status:** TEILWEISE (QUICK_START.md covers some)
**Impact:** MITTEL
**Aufwand:** 2 Stunden
**Benötigt:**

1. **Prerequisites:**
   - Python, Poetry, Docker (detailed versions)
   - GPU setup (NVIDIA drivers, CUDA toolkit)

2. **IDE Setup:**
   - VS Code recommended settings
   - PyCharm configuration
   - Extensions (Python, Docker, MyPy)

3. **Development Workflow:**
   - Create feature branch
   - Run tests locally
   - Pre-commit hooks

---

### 7.2 Testing Guide

**File:** `docs/development/TESTING.md`
**Status:** FEHLT
**Impact:** MITTEL - Für Contributors wichtig
**Aufwand:** 2 Stunden
**Benötigt:**

1. **Test Types:**
   - Unit tests (pytest)
   - Integration tests (real services)
   - E2E tests (critical paths)

2. **Running Tests:**
   - `pytest tests/unit/` - Fast unit tests
   - `pytest tests/integration/` - Slower, requires Docker
   - `pytest -m sprint21` - Sprint-specific tests

3. **Writing Tests:**
   - Naming conventions
   - Fixtures (pytest fixtures explained)
   - Mocking (when to mock, when not)

4. **Coverage Requirements:**
   - Target: >80%
   - How to generate report: `pytest --cov=src`

---

### 7.3 Contributing Guide

**File:** `docs/development/CONTRIBUTING.md`
**Status:** FEHLT
**Impact:** NIEDRIG - Für Open Source wichtig
**Aufwand:** 2 Stunden
**Benötigt:**

1. **How to Contribute:**
   - Fork repo
   - Create feature branch
   - Write tests
   - Submit PR

2. **Code Standards:**
   - Reference to NAMING_CONVENTIONS.md
   - Linting (Ruff, Black, MyPy)
   - Type hints required

3. **PR Process:**
   - PR template
   - Code review checklist
   - CI checks must pass

4. **ADR Process:**
   - When to create ADR
   - ADR template
   - Review process

---

### 7.4 Code Review Guidelines

**File:** `docs/development/CODE_REVIEW.md`
**Status:** FEHLT
**Impact:** NIEDRIG
**Aufwand:** 1.5 Stunden
**Benötigt:**

1. **Reviewer Checklist:**
   - Code style (Ruff, Black)
   - Type hints present
   - Tests added/updated
   - Documentation updated
   - ADR created (if major change)

2. **Common Issues:**
   - Missing docstrings
   - Hardcoded values (use config)
   - No error handling
   - Security issues

3. **Review Etiquette:**
   - Be constructive
   - Ask questions
   - Suggest alternatives

---

## 8. Zusammenfassung - Priorisierung

### Kritisch (DIESE WOCHE)

| Gap | Effort | Impact | Owner |
|-----|--------|--------|-------|
| ADR-027 (Docling) | 3h | KRITISCH | Doc Agent |
| CLAUDE.md Update | 2h | KRITISCH | Doc Agent |
| QUICK_START.md | 2h | KRITISCH | Infra Agent |
| Architecture Diagram | 4h | KRITISCH | Backend + Doc Agent |
| **TOTAL** | **11h** | — | — |

### Wichtig (NÄCHSTE 2 WOCHEN)

| Gap | Effort | Impact | Owner |
|-----|--------|--------|-------|
| ADR-028, 029, 030 | 5.5h | HOCH | Doc Agent |
| PROJECT_SUMMARY.md | 1.5h | HOCH | Doc Agent |
| TECH_STACK.md | 2h | HOCH | Doc Agent |
| DECISION_LOG.md | 3h | MITTEL | Doc Agent |
| README.md | 1h | MITTEL | Doc Agent |
| Component Docs | 8h | HOCH | Backend Agent |
| **TOTAL** | **21h** | — | — |

### Wünschenswert (NÄCHSTER SPRINT)

| Gap Category | Effort | Impact |
|--------------|--------|--------|
| Remaining ADRs | 10h | NIEDRIG |
| API Documentation | 12h | MITTEL |
| Code Documentation | 20h | NIEDRIG |
| User Documentation | 10h | MITTEL |
| Developer Documentation | 8h | MITTEL |
| **TOTAL** | **60h** | — |

### Grand Total

**47 Gaps, 92 Stunden Aufwand (11.5 Tage)**

---

## 9. Automated Gap Detection (Future)

### Tooling Recommendations

1. **Docstring Coverage:**
   - Tool: `interrogate` (Python docstring coverage)
   - Command: `interrogate -v src/`
   - Target: >90%

2. **Documentation Linting:**
   - Tool: `markdownlint`
   - Check: Broken links, outdated dates
   - CI Integration: Fail PR if docs outdated

3. **ADR Numbering Check:**
   - Custom script: Check for gaps in ADR-NNN sequence
   - Alert if missing numbers

4. **Code → Doc Sync Check:**
   - Parse imports in code
   - Check if mentioned in TECH_STACK.md
   - Alert if new dependency without doc update

---

## 10. Maintenance Plan

### Weekly

- [ ] Check CLAUDE.md up-to-date (current sprint)
- [ ] Update Sprint Status in README.md

### Sprint Completion

- [ ] Create ADR (if major decision)
- [ ] Update DECISION_LOG.md
- [ ] Update Core Docs (if architecture changed)
- [ ] Create Sprint Summary Document

### Monthly

- [ ] Review all Core Docs for accuracy
- [ ] Check for broken links (markdownlint)
- [ ] Update Performance Metrics

### Quarterly

- [ ] Full documentation audit (this analysis)
- [ ] Archive outdated docs
- [ ] Refactor documentation structure (if needed)

---

## Anhang: Gap Scoring Methodology

**Gap Severity Score:**
```
KRITISCH (10): Blocks Onboarding/Deployment
HOCH (7-9): Significant impact on understanding/usage
MITTEL (4-6): Moderate impact, workarounds exist
NIEDRIG (1-3): Nice-to-have, minimal impact
```

**Effort Estimation:**
```
1h: Simple update (< 50 lines)
2h: Medium update (50-200 lines)
4h: Large update (200-500 lines)
8h: Major document creation (500-1000 lines)
```

**Priority Calculation:**
```
Priority Score = (Severity × 2) + (10 - Effort_Hours)

Example:
  Severity: 10 (KRITISCH)
  Effort: 3h
  Priority: (10 × 2) + (10 - 3) = 27 (HIGHEST)
```

---

**VERSION:** 1.0
**STATUS:** Complete Gap Analysis
**NEXT ACTION:** Execute DOCUMENTATION_PLAN.md (prioritized tasks)

