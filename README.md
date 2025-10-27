# AEGIS RAG - AI-Enhanced Guardrail Integration System

Enterprise-grade Retrieval-Augmented Generation System mit integrierten Guardrails.

## 📁 Projektstruktur

```
AEGIS_RAG/
├── docs/                           # Dokumentation
│   ├── core/                       # Kern-Dokumentation
│   │   ├── PROJECT_SUMMARY.md      # ⭐ Gesamtübersicht - Start hier!
│   │   ├── QUICK_START.md          # Tag-1-Setup
│   │   ├── CLAUDE.md               # Hauptkontext für Claude Code
│   │   ├── SPRINT_PLAN.md          # 12-Sprint Roadmap
│   │   ├── NAMING_CONVENTIONS.md   # Code Standards
│   │   ├── TECH_STACK.md           # Complete Technology Stack
│   │   ├── SUBAGENTS.md            # 5 Subagenten-Definitionen
│   │   ├── PROMPT_TEMPLATES.md     # 8 Claude Code Templates
│   │   └── ENFORCEMENT_GUIDE.md    # Quality Gates Übersicht
│   └── adr/                        # Architecture Decision Records
│       └── ADR_INDEX.md            # 8 Architecture Decisions
│
├── .github/                        # GitHub Konfiguration
│   ├── workflows/
│   │   └── ci.yml                  # 10-Job CI/CD Pipeline
│   ├── pull_request_template.md    # PR Checklist
│   └── CODEOWNERS                  # Auto-Review Zuweisungen
│
├── scripts/                        # Automation Scripts
│   ├── check_adr.py                # ADR Detection
│   └── check_naming.py             # Naming Convention Checker
│
├── .pre-commit-config.yaml         # 14 Pre-Commit Hooks
└── README.md                       # Diese Datei
```

## 🚀 Quick Start

1. **Dokumentation lesen**: Beginne mit [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md)
2. **Setup durchführen**: Folge [docs/core/QUICK_START.md](docs/core/QUICK_START.md)
3. **Claude Code nutzen**: Siehe [docs/core/PROMPT_TEMPLATES.md](docs/core/PROMPT_TEMPLATES.md) für Templates

## 📚 Wichtige Dokumente

### Core Dokumentation
- [PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md) - Gesamtübersicht
- [SPRINT_PLAN.md](docs/core/SPRINT_PLAN.md) - 12-Sprint Roadmap
- [QUICK_START.md](docs/core/QUICK_START.md) - Day-1 Setup Guide
- [PROMPT_TEMPLATES.md](docs/core/PROMPT_TEMPLATES.md) - Claude Code Templates
- [ADR_INDEX.md](docs/adr/ADR_INDEX.md) - 18+ Architecture Decisions

### Examples & Tutorials
- [Sprint 3 Usage Examples](docs/examples/sprint3_examples.md) - Reranking, Query Decomposition, Filters

### Setup & Enforcement
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - 14 Hooks
- [ci.yml](.github/workflows/ci.yml) - 10-Job Pipeline
- [pull_request_template.md](.github/pull_request_template.md) - PR Checklist
- [check_adr.py](scripts/check_adr.py) - ADR Detection
- [check_naming.py](scripts/check_naming.py) - Naming Checker
- [CODEOWNERS](.github/CODEOWNERS) - Auto-Review

## 🛠️ Technologie-Stack

- **Backend**: Python 3.11+, FastAPI
- **Orchestration**: LangGraph
- **RAG**: LlamaIndex, LightRAG
- **Vector DB**: Qdrant
- **Graph DB**: Neo4j
- **Memory**: Graphiti (Temporal Memory)
- **LLM**: Ollama (llama3.2:3b/8b, qwen2.5:7b, qwen3:0.6b, smollm2:1.7b)
- **Embeddings**: nomic-embed-text (lokal, 768-dim)
- **Reranking**: sentence-transformers (cross-encoder/ms-marco-MiniLM)
- **Evaluation**: RAGAS (Context Precision, Recall, Faithfulness)
- **Security**: Custom Guardrails, Content Filtering, SHA-256 hashing
- **DevOps**: Docker, GitHub Actions

Details siehe [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md) und [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)

## ✨ Latest Features

### Sprint 14 (IN PROGRESS - Backend Performance & Production Readiness)
- 🟡 **Feature 14.1**: LightRAG Integration with Three-Phase Pipeline (Option B - Wrapper approach)
- 🔵 **Feature 14.2**: Configuration & Toggle System (Planned)
- 🔵 **Feature 14.3**: Performance Benchmarking Suite (Planned)
- 🔵 **Feature 14.4**: GPU Memory Optimization (Planned)
- 🔵 **Feature 14.5**: Error Handling & Retry Logic (Planned)
- 🔵 **Feature 14.6**: Monitoring & Metrics (Planned)
- 🔵 **Feature 14.7**: CI/CD Pipeline Stability (Planned)

**Goal**: Integrate 3-Phase Pipeline into production, optimize performance, stabilize CI/CD
**Status**: Planning complete, implementation starting
**Documentation**: [SPRINT_14_PLAN.md](SPRINT_14_PLAN.md), [SPRINT_14_TODOS.md](SPRINT_14_TODOS.md)

### Sprint 13 (COMPLETE - Test Infrastructure & Three-Phase Extraction)
- ✅ **Feature 13.9**: Three-Phase Entity/Relation Extraction Pipeline (SpaCy + Semantic Dedup + Gemma 3 4B)
- ✅ **Performance**: Entity extraction improved from >300s timeout → <30s (10x faster)
- ✅ **Quality**: 28.6% deduplication rate, 144% entity accuracy, 123% relation accuracy
- ✅ **Technical Debt**: All TD-26 to TD-34 resolved (Memory Agent, Graphiti API, LightRAG fixtures)
- ✅ **CI/CD**: pytest-timeout plugin, --timeout=300s, artifact uploads configured

**Test Results**: 6/6 E2E tests passing in 128.68s total
**Documentation**: [SPRINT_13_TODOS.md](docs/archive/sprints/SPRINT_13_TODOS.md), [ADR-017](docs/adr/ADR-017-semantic-entity-deduplication.md), [ADR-018](docs/adr/ADR-018-model-selection-entity-relation-extraction.md)

### Sprint 12 (COMPLETE - 9/11 features, 28/32 SP)
- ✅ **Test Infrastructure Fixes**: LightRAG fixture (5 tests), Graphiti API (14 tests), Redis cleanup (0 warnings)
- ✅ **Production Deployment Guide**: GPU setup, Docker/K8s, monitoring, security, backup/DR
- ✅ **CI/CD Pipeline Enhanced**: Ollama service, 20min timeout, Docker cache, model pulling
- ✅ **Graph Visualization API**: 4 endpoints (export JSON/GraphML/Cytoscape, filter, highlight)
- ✅ **GPU Performance Benchmarking**: benchmark_gpu.py with nvidia-smi integration, JSON output
- ✅ **40 New Tests**: 10 E2E skeleton tests + 30 comprehensive Gradio UI integration tests
- ✅ **E2E Test Improvements**: Pass rate improved from 17.9% → ~50%

**Documentation**: [Production Deployment Guide](docs/PRODUCTION_DEPLOYMENT_GUIDE.md)
**Benchmarking**: `python scripts/benchmark_gpu.py --model llama3.2:3b`
**Status**: Production-ready with verified GPU acceleration (RTX 3060: 105 tokens/s)

### Sprint 11 (COMPLETE - 8/10 features)
- ✅ **LLM-Based Answer Generation**: Proper synthesis with Ollama instead of context concatenation
- ✅ **Unified Embedding Service**: Shared cache across vector/graph/memory systems
- ✅ **Unified Ingestion Pipeline**: Parallel indexing to Qdrant + BM25 + LightRAG
- ✅ **GPU Support**: NVIDIA GPU acceleration for Ollama (15-20x speedup: 105 vs 7 tokens/s)
- ✅ **LightRAG Model Switch**: llama3.2:3b for entity extraction (fixes qwen3 format issues)
- ✅ **Redis Checkpointer**: Production-grade LangGraph state persistence
- ✅ **Community Detection Optimization**: Parallel processing, progress tracking
- ✅ **Temporal Retention Policy**: Configurable cleanup for old graph versions

### Sprint 3 Features (COMPLETE)
- ✅ **Cross-Encoder Reranking**: +15-20% precision improvement with ms-marco-MiniLM
- ✅ **Query Decomposition**: LLM-based classification (SIMPLE/COMPOUND/MULTI_HOP) with Ollama
- ✅ **Metadata Filtering**: Date ranges, sources, document types, tags (42 tests, 100%)
- ✅ **RAGAS Evaluation**: Context Precision/Recall/Faithfulness metrics (Score: 0.88)
- ✅ **Adaptive Chunking**: Document-type aware strategies (paragraph/heading/function/sentence)
- ✅ **Security Fix**: MD5 → SHA-256 for document IDs (CVE-2010-4651)

**Test Coverage**: 335/338 passing (99.1%)
See [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md) for project details

### LLM-Strategie (ADR-002)
- **Development & Production**: 100% Ollama (kostenfrei, offline-fähig)
- **Compliance**: Vollständig air-gapped Deployment
- **Privacy**: Keine Daten verlassen lokales Netzwerk

## 📋 Entwicklungsprozess

1. **Pre-Commit Hooks**: Automatische Checks bei jedem Commit
2. **CI/CD Pipeline**: 10 Jobs in GitHub Actions
3. **Architecture Decisions**: Dokumentiert in ADRs
4. **Code Review**: Automatische Zuweisung via CODEOWNERS
5. **Quality Gates**: Definiert in ENFORCEMENT_GUIDE.md

## 🤖 Claude Code Integration

Das Projekt ist vollständig auf Claude Code optimiert:
- Hauptkontext in [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md)
- Prompt-Templates in [docs/core/PROMPT_TEMPLATES.md](docs/core/PROMPT_TEMPLATES.md)
- Naming Conventions integriert

## 🔒 Sicherheit

- Enterprise-Compliance (Air-Gapped, DSGVO)
- Multi-Layer Guardrails
- Content Filtering
- PII Detection
- Access Control

Details in [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md) und [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)

## 📅 Sprint Plan

12 Sprints geplant über 12 Wochen:
- ✅ Sprint 1: Foundation & Infrastructure Setup (COMPLETE)
- ✅ Sprint 2: Vector Search Foundation (COMPLETE - 212 tests passing)
- ✅ Sprint 3: Advanced Retrieval (COMPLETE - 335 tests passing, 99.1%)
- ✅ Sprint 4: LangGraph Orchestration Layer (COMPLETE)
- ✅ Sprint 5: LightRAG Integration (COMPLETE)
- ✅ Sprint 6: Hybrid Vector-Graph Retrieval (COMPLETE)
- ✅ Sprint 7: Graphiti Memory Integration (COMPLETE)
- ✅ Sprint 8: Critical Path E2E Testing (COMPLETE - 80% baseline)
- ✅ Sprint 9: 3-Layer Memory Architecture + MCP Server Integration (COMPLETE)
- ✅ Sprint 10: End-User Interface (COMPLETE - Gradio UI)
- ✅ Sprint 11: Technical Debt Resolution & Unified Pipeline (COMPLETE - 8/10 features, GPU support)
- 🔄 Sprint 12: Integration Testing & Production Readiness (IN PLANNING)

Details siehe [docs/core/SPRINT_PLAN.md](docs/core/SPRINT_PLAN.md)

## 📞 Kontakt & Support

Bei Fragen zum Projekt:
1. Konsultiere [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md)
2. Prüfe die [ADRs](docs/adr/ADR_INDEX.md) für Architekturentscheidungen
3. Nutze die [Prompt Templates](docs/core/PROMPT_TEMPLATES.md) für Claude Code

---

**Version**: 1.0.0
**Erstellt**: Oktober 2024
**Status**: In Entwicklung
