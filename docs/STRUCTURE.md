# AEGIS RAG - Repository Structure

**Last Updated:** 2025-11-11 (Sprint 22 Feature 22.5 - 30-Format Support)
**Purpose:** Complete overview of repository organization

---

## 📁 Root Directory

```
AEGIS_RAG/
├── README.md                       # Project overview (Sprint 21)
├── STRUCTURE.md                    # This file - repository structure
├── pyproject.toml                  # Poetry dependencies
├── docker-compose.yml              # Local development stack
├── .pre-commit-config.yaml         # Pre-commit hooks
├── .gitignore                      # Git ignore rules
└── .claude/                        # Claude Code configuration
    ├── settings.json               # Claude settings
    └── agents/                     # 6 specialized subagents
        ├── api-agent.md
        ├── backend-agent.md
        ├── documentation-agent.md
        ├── infrastructure-agent.md
        ├── subagent-architect.md
        └── testing-agent.md
```

---

## 📚 Documentation Structure (docs/)

### Core Documentation (docs/ root) - 9 Essential Files

These files stay in the root for easy CONTEXT_REFRESH access:

```
docs/
├── CLAUDE.md                       # Project context for Claude Code (Sprint 21)
├── CONTEXT_REFRESH.md              # Context refresh strategies (v5.0, timeless)
├── TECH_STACK.md                   # Technology stack (Sprint 1-21)
├── ARCHITECTURE_EVOLUTION.md       # Sprint-by-sprint history (Sprint 1-21)
├── DEPENDENCY_RATIONALE.md         # Dependency justifications (Sprint 21)
├── SUBAGENTS.md                    # 6 specialized subagents
├── NAMING_CONVENTIONS.md           # Code standards
├── DECISION_LOG.md                 # Decision log
└── COMPONENT_INTERACTION_MAP.md    # Component interactions
```

### Organized Subdirectories - 12 Categories

#### 1. Architecture Decision Records (docs/adr/)
```
docs/adr/
├── ADR_INDEX.md                    # Index of all 30 ADRs
├── ADR-001-*.md through ADR-030-*.md
└── README.md                       # ADR guidelines
```

**Key ADRs (Sprint 21):**
- ADR-026: Pure LLM Extraction as Default Pipeline
- ADR-027: Docling CUDA Container vs. LlamaIndex
- ADR-028: LlamaIndex Deprecation Strategy
- ADR-029: React Migration Deferral
- ADR-030: Sprint Extension (12 → 21+ Sprints)

#### 2. API Documentation (docs/api/)
```
docs/api/
├── ENDPOINTS.md                    # API endpoint documentation
├── UPLOAD_ENDPOINT.md              # Upload API & 30-format support (Sprint 22)
├── ERROR_RESPONSES.md              # Standardized error responses (Sprint 22)
├── ERROR_CODES.md                  # Error code reference
└── SSE_STREAMING.md                # Server-Sent Events streaming
```

#### 3. Architecture Deep-Dives (docs/architecture/)
```
docs/architecture/
├── ARCHITECTURE_OVERVIEW.md        # System architecture (Sprint 21)
├── COMPONENT_INTERACTION_MAP.md    # Component data flows
├── HYBRID_RAG_SYNERGY.md          # Hybrid RAG explanation
├── LIGHTRAG_VS_GRAPHITI.md        # Layer 2 vs Layer 3 comparison
├── CHUNKING_STRATEGY_COMPARISON.md
└── 512_VS_600_TOKENS.md
```

#### 4. Core Project Documentation (docs/core/)
```
docs/core/
├── PROJECT_SUMMARY.md              # Project overview
├── QUICK_START.md                  # Day-1 setup guide
└── PROMPT_TEMPLATES.md             # Claude Code templates
```

#### 5. Setup & How-To Guides (docs/guides/)
```
docs/guides/
├── README.md                       # Guide index
├── DOCUMENT_UPLOAD_GUIDE.md        # Document upload (30 formats, Sprint 22)
├── PRODUCTION_DEPLOYMENT_GUIDE.md  # Production deployment
├── CI_CD_GUIDE.md                  # GitHub Actions CI/CD
├── GPU_REQUIREMENTS.md             # GPU setup (NVIDIA CUDA)
├── WSL2_CONFIGURATION.md           # Windows Subsystem for Linux
├── LM_STUDIO_INSTALLATION.md       # LM Studio setup
└── TESTING_STRATEGY.md             # Testing approach
```

#### 6. Technical References (docs/reference/)
```
docs/reference/
├── README.md                       # Reference index
├── API_CONVERSATION_ARCHIVING.md   # Conversation archiving API (Sprint 17)
├── ENFORCEMENT_GUIDE.md            # Quality gates
└── GRAPHITI_REFERENCE.md           # Graphiti memory system
```

#### 7. Evaluations & Comparisons (docs/evaluations/)
```
docs/evaluations/
├── README.md                       # Evaluation index
├── BGE_M3_EVALUATION.md            # BGE-M3 vs nomic-embed-text (Sprint 16, ADR-024)
├── LMSTUDIO_VS_OLLAMA_ANALYSIS.md  # LM Studio vs Ollama comparison
└── MODEL_COMPARISON_GEMMA_VS_LLAMA.md
```

#### 8. Planning Documents (docs/planning/)
```
docs/planning/
├── README.md                       # Planning index
├── DOCUMENTATION_GAPS.md           # Documentation gaps analysis
├── DOCUMENTATION_PLAN.md           # Documentation backfill plan
├── DRIFT_ANALYSIS.md               # Documentation drift (Sprint 1-21)
└── TEST_COVERAGE_PLAN.md           # Test coverage strategy
```

#### 9. Code Examples (docs/examples/)
```
docs/examples/
├── sprint3_examples.md
├── sprint5_examples.md
└── sprint6_examples.md
```

#### 10. Sprint Documentation (docs/sprints/)
```
docs/sprints/
├── SPRINT_PLAN.md                  # Master sprint tracking
├── SPRINT_01-03_FOUNDATION_SUMMARY.md
├── SPRINT_04-06_GRAPH_RAG_SUMMARY.md
├── SPRINT_07-09_MEMORY_MCP_SUMMARY.md
├── SPRINT_13_THREE_PHASE_EXTRACTION.md
├── SPRINT_14_PLAN.md through SPRINT_22_PLAN.md
├── SPRINT_14_COMPLETION_REPORT.md through SPRINT_21_*.md
└── Feature-specific docs (e.g., FEATURE_14_1_LIGHTRAG_PROVENANCE.md)
```

#### 11. Troubleshooting (docs/troubleshooting/)
```
docs/troubleshooting/
├── DEBUGGING_GUIDE.md
└── LightRAG_DEBUG_GUIDE.md
```

#### 12. Archive (docs/archive/)
```
docs/archive/
├── README.md                       # Archive explanation
├── Sprint 1-12 completion reports  # Historical sprint docs
├── TECHNICAL_DEBT_SUMMARY.md       # Sprint 12 tech debt (obsolete)
├── TESTING_GUIDE_SPRINT20.md       # Sprint 20 testing guide (obsolete)
├── ci-run-19030219862-analysis.md  # CI run analysis
├── technical-analysis-sprint-20-backend-issues.md
├── TD-41_RESOLUTION.md
├── TEST_STATUS_SPRINT_17.md
└── TECHNICAL_DEBT_SPRINT_18.md
```

---

## 🏗️ Source Code Structure (src/)

```
src/
├── api/                            # FastAPI REST API
│   ├── v1/                         # API v1 endpoints
│   │   ├── annotations.py          # VLM annotation endpoints (Sprint 21)
│   │   ├── chat.py
│   │   ├── query.py
│   │   ├── admin.py
│   │   └── memory.py
│   ├── health.py
│   └── main.py
│
├── agents/                         # LangGraph Agents
│   ├── coordinator.py              # Coordinator agent
│   ├── vector_search.py            # Vector search agent
│   ├── graph_query.py              # Graph query agent
│   ├── action.py                   # Action agent (MCP tools)
│   └── memory.py                   # Memory agent
│
├── components/                     # Core Components
│   ├── ingestion/                  # Document Ingestion (Sprint 21-22)
│   │   ├── docling_client.py       # Docling CUDA container client
│   │   ├── format_router.py        # Hybrid Docling/LlamaIndex routing (Sprint 22)
│   │   ├── langgraph_pipeline.py   # 6-node LangGraph pipeline
│   │   ├── langgraph_nodes.py      # Pipeline node implementations
│   │   ├── ingestion_state.py      # State definitions
│   │   ├── image_processor.py      # VLM image enrichment
│   │   ├── hybrid_chunker.py       # BBox-aware chunking
│   │   └── README.md
│   │
│   ├── vector_search/              # Vector Search (Qdrant + BM25)
│   │   ├── hybrid_search.py        # Hybrid search with RRF
│   │   ├── qdrant_client.py
│   │   ├── bm25_search.py
│   │   └── README.md
│   │
│   ├── graph_rag/                  # Graph RAG (LightRAG + Neo4j)
│   │   ├── extraction/
│   │   │   ├── llm_extraction.py   # Pure LLM extraction (ADR-026, default)
│   │   │   ├── three_phase_extraction.py  # DEPRECATED
│   │   │   └── entity_service.py
│   │   ├── lightrag_client.py
│   │   ├── neo4j_client.py
│   │   └── README.md
│   │
│   ├── memory/                     # Temporal Memory (Graphiti)
│   │   ├── graphiti_client.py
│   │   ├── consolidation.py
│   │   └── README.md
│   │
│   ├── retrieval/                  # Advanced Retrieval
│   │   ├── reranking.py            # Cross-encoder reranking
│   │   ├── query_decomposition.py
│   │   └── README.md
│   │
│   ├── mcp/                        # Model Context Protocol
│   │   ├── client.py
│   │   ├── server.py
│   │   └── README.md
│   │
│   ├── profiling/                  # User Profiling (Sprint 17)
│   │   ├── conversation_archiver.py
│   │   ├── user_profile.py
│   │   └── README.md
│   │
│   ├── shared/                     # Shared Utilities
│   │   ├── embedding_service.py    # BGE-M3 singleton
│   │   ├── chunking_service.py     # DEPRECATED (replaced by HybridChunker)
│   │   └── README.md
│   │
│   └── temporal_memory/            # Temporal Memory Utils
│       ├── retention_policy.py
│       └── README.md
│
├── core/                           # Core Infrastructure
│   ├── config.py                   # Pydantic settings
│   ├── logging.py                  # Structured logging
│   ├── models.py                   # Pydantic models
│   └── exceptions.py               # Custom exceptions
│
└── utils/                          # Helper Functions
    ├── text_processing.py
    └── validation.py
```

---

## 🔄 Hybrid Ingestion Architecture (Sprint 22)

### FormatRouter Component

The **FormatRouter** intelligently routes documents to optimal parsers based on format capabilities and availability:

```
Document Upload → FormatRouter → Parser Selection
                                    ├─ Docling (GPU): 14 exclusive + 7 shared = 21 formats
                                    └─ LlamaIndex (CPU): 9 exclusive + 7 shared = 16 formats
                                                         Total: 30 formats
```

**Key Features:**
- **30 Format Support:** Comprehensive coverage across office, markup, images, e-books
- **Intelligent Routing:** Format-based decision tree with health checks
- **Graceful Degradation:** Automatic fallback for shared formats (7 formats)
- **Performance Optimization:** GPU-accelerated Docling preferred (3.5x faster)

**Format Categories:**

| Category | Count | Parser | Key Features |
|----------|-------|--------|--------------|
| **Docling-Exclusive** | 14 | Docling CUDA | GPU OCR (95%), Table extraction (92%), Layout preservation |
| **LlamaIndex-Exclusive** | 9 | LlamaIndex | Text-only, 300+ connectors, E-book/LaTeX support |
| **Shared Formats** | 7 | Docling (preferred) | Both support, automatic fallback |

**Routing Decision Tree:**

```
format_router.route(file_path)
│
├─ Format Supported?
│  ├─ Yes → Continue
│  └─ No → InvalidFileFormatError (lists 30 formats)
│
├─ Docling-Exclusive? (.pdf, .docx, .png, etc.)
│  ├─ Docling Available? → Use Docling (GPU, high confidence)
│  └─ Docling Unavailable? → Error (no fallback)
│
├─ LlamaIndex-Exclusive? (.md, .epub, .rst, etc.)
│  └─ Always use LlamaIndex (high confidence)
│
└─ Shared Format? (.txt, .doc, .htm, etc.)
   ├─ Docling Available? → Use Docling (prefer performance, high confidence)
   └─ Docling Unavailable? → Use LlamaIndex (fallback, medium confidence)
```

**Implementation:**
- **Location:** `src/components/ingestion/format_router.py`
- **Lines of Code:** 498 (well-documented with examples)
- **Decision Records:** ADR-027 (Docling Integration), ADR-028 (LlamaIndex Strategy)
- **API Integration:** `/upload` endpoint (30 formats), `/formats` endpoint (support matrix)

**Performance Impact:**
- **Docling (GPU):** 120s/doc average (95% OCR accuracy)
- **LlamaIndex (CPU):** 420s/doc average (text-only)
- **Speedup:** 3.5x faster for GPU-accelerated formats

**Example Usage:**
```python
from src.components.ingestion.format_router import FormatRouter

# Initialize router with health check
router = await initialize_format_router()

# Route document
decision = router.route(Path("document.pdf"))
print(f"Parser: {decision.parser}, Confidence: {decision.confidence}")
# Output: Parser: docling, Confidence: high

# Get supported formats
all_formats = router.get_supported_formats()  # Returns 30 formats
docling_formats = router.get_supported_formats(ParserType.DOCLING)  # Returns 21
llamaindex_formats = router.get_supported_formats(ParserType.LLAMAINDEX)  # Returns 16
```

**Documentation:**
- **API Docs:** `docs/api/UPLOAD_ENDPOINT.md` (complete endpoint reference)
- **User Guide:** `docs/guides/DOCUMENT_UPLOAD_GUIDE.md` (format-specific tips)
- **Format Matrix:** `FORMAT_SUPPORT_MATRIX.md` (30 formats with capabilities)

---

## 🧪 Test Structure (tests/)

```
tests/
├── unit/                           # Unit Tests (112+ tests)
│   ├── test_vector_search.py
│   ├── test_graph_rag.py
│   ├── test_memory.py
│   └── ...
│
├── integration/                    # Integration Tests (51+ tests)
│   ├── test_agents.py
│   ├── test_ingestion.py           # 31 Docling tests (Sprint 21)
│   ├── test_hybrid_search.py
│   └── ...
│
└── e2e/                            # E2E Tests (28+ tests)
    ├── test_query_flows.py
    ├── test_memory_flows.py
    └── ...
```

---

## 🛠️ Scripts & Tools (scripts/)

```
scripts/
├── feature_21_6/                   # Sprint 21 Feature 21.6 development files (gitignored)
│   ├── Sprint21_Feature21_6.docx
│   ├── generate_docling_report.py
│   ├── test_qwen3vl_cpu_offload.py
│   └── vision-model-benchmark/
│
├── check_adr.py                    # ADR detection
├── check_naming.py                 # Naming convention checker
├── benchmark_embeddings.py
└── migrate.py
```

---

## 🐳 Docker & Infrastructure

```
├── docker-compose.yml              # Local development stack
├── docker/                         # Dockerfiles
│   ├── Dockerfile.api
│   └── Dockerfile.worker
│
└── k8s/                            # Kubernetes manifests
    ├── helm-chart/
    └── values-prod.yaml
```

---

## ⚙️ Configuration Files

```
├── pyproject.toml                  # Poetry dependencies
├── pytest.ini                      # Pytest configuration
├── .pre-commit-config.yaml         # Pre-commit hooks
├── .gitignore                      # Git ignore rules
├── .env.template                   # Environment variable template
└── .github/                        # GitHub configuration
    ├── workflows/
    │   └── ci.yml                  # CI/CD pipeline
    ├── pull_request_template.md
    └── CODEOWNERS
```

---

## 📊 Documentation Metrics

| Category | Count | Notes |
|----------|-------|-------|
| **Core Docs** | 9 | Essential reference docs in docs/ root |
| **ADRs** | 30 | ADR-001 through ADR-030 |
| **Component READMEs** | 10+ | src/components/*/README.md |
| **Sprint Docs** | 33 | Plans, reports, progress tracking |
| **Subdirectories** | 12 | Organized doc categories |
| **Archived Docs** | 85+ | Historical sprint docs in docs/archive/ |
| **Total Markdown** | 100+ | Comprehensive documentation |

---

## 🎯 Quick Navigation by Role

### For New Developers
1. [README.md](README.md) - Project overview
2. [docs/CLAUDE.md](docs/CLAUDE.md) - Project context
3. [docs/core/QUICK_START.md](docs/core/QUICK_START.md) - Day-1 setup
4. [docs/NAMING_CONVENTIONS.md](docs/NAMING_CONVENTIONS.md) - Code standards

### For Architects
1. [docs/ARCHITECTURE_EVOLUTION.md](docs/ARCHITECTURE_EVOLUTION.md) - Sprint history
2. [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md) - All 30 ADRs
3. [docs/TECH_STACK.md](docs/TECH_STACK.md) - Complete stack
4. [docs/architecture/](docs/architecture/) - Deep-dive docs

### For DevOps Engineers
1. [docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md](docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md)
2. [docs/guides/CI_CD_GUIDE.md](docs/guides/CI_CD_GUIDE.md)
3. [docker-compose.yml](docker-compose.yml) - Local stack
4. [k8s/](k8s/) - Kubernetes manifests

### For Claude Code Users
1. [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md) - Context strategies
2. [docs/SUBAGENTS.md](docs/SUBAGENTS.md) - 6 specialized agents
3. [.claude/agents/](. claude/agents/) - Agent definitions
4. [docs/core/PROMPT_TEMPLATES.md](docs/core/PROMPT_TEMPLATES.md) - Templates

---

## 🔄 Maintenance

### Documentation Updates
- **Core Docs:** Update when architecture changes (ADRs required)
- **Sprint Docs:** Update at end of each sprint
- **Component READMEs:** Update when component logic changes
- **Archive:** Move obsolete sprint-specific docs to archive

### Structural Changes
- **Never move Core Docs (9 files):** They stay in docs/ root for CONTEXT_REFRESH
- **Use subdirectories:** For all thematic/sprint-specific docs
- **Archive obsolete:** Don't delete, move to docs/archive/ with README

---

**Last Updated:** 2025-11-11 (Sprint 22 Feature 22.5 - 30-Format Support)
**Maintainer:** AEGIS RAG Team
**Version:** 2.1.0 (Reflects Sprint 22 Hybrid Ingestion Architecture)
