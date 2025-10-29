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
- **LLM**: Ollama (flexible)
- **Embeddings**: BGE-M3 (lokal, 1024-dim)
- **Reranking**: sentence-transformers (cross-encoder/ms-marco-MiniLM)
- **Evaluation**: RAGAS (Context Precision, Recall, Faithfulness)
- **Security**: Custom Guardrails, Content Filtering, SHA-256 hashing
- **DevOps**: Docker, GitHub Actions

Details siehe [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md) und [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)

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
- ✅ Sprint 12: Integration Testing & Production Readiness (COMPLETE)
- ✅ Sprint 13: Three-Phase Entity Extraction Pipeline (COMPLETE - 10x speedup, SpaCy + Semantic Dedup + Gemma 2 4B)
- ✅ Sprint 14: Backend Performance & Testing (COMPLETE - 132 tests, Prometheus metrics, retry logic)
- ✅ Sprint 15: Frontend Interface with Perplexity-Inspired UI (COMPLETE - React + Vite, SSE streaming)
- ✅ Sprint 16: Unified Ingestion Architecture & BGE-M3 Migration (COMPLETE - 69 SP, cross-layer similarity)
- ✅ Sprint 17: Admin UI & Advanced Features (COMPLETE - 55 SP, conversation history, user profiling)
- 📋 Sprint 18: Test Infrastructure & Security Hardening (PLANNED - 24 SP, JWT auth, rate limiting)

**Gesamt-Fortschritt:** 515/584 SP (88.2%)

Details siehe [docs/sprints/SPRINT_PLAN.md](docs/sprints/SPRINT_PLAN.md)

## 📞 Kontakt & Support

Bei Fragen zum Projekt:
1. Konsultiere [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md)
2. Prüfe die [ADRs](docs/adr/ADR_INDEX.md) für Architekturentscheidungen
3. Nutze die [Prompt Templates](docs/core/PROMPT_TEMPLATES.md) für Claude Code

---

## 🎯 Recent Highlights

### Sprint 16 (COMPLETE - Oktober 2024)
- **Unified Chunking Service**: 70% code reduction, SHA-256 deterministic IDs
- **BGE-M3 Migration**: System-wide 1024-dim embeddings, +23% German retrieval quality
- **Cross-Layer Similarity**: Enabled semantic search across all memory layers
- **Atomic Re-Indexing**: Admin endpoint with SSE progress tracking

### Sprint 17 (COMPLETE - Oktober 2024)
- **Admin UI**: Directory indexing with real-time progress display
- **Conversation Persistence**: Full history with follow-up question support
- **Auto-Generated Titles**: LLM-based, 3-5 word summaries (user-editable)
- **Implicit User Profiling**: Neo4j knowledge graph, semantic conversation search

### Sprint 18 (PLANNED)
- **Test Infrastructure**: Fix 44 failing E2E tests → 95% pass rate
- **JWT Authentication**: Secure admin endpoints with role-based access
- **API Rate Limiting**: Redis-backed, 10-100 req/min per endpoint
- **Production Readiness**: Security hardening for deployment

---

**Version**: 1.7.0 (Sprint 17 Complete)
**Erstellt**: Oktober 2024
**Letzte Aktualisierung**: 29. Oktober 2024
**Status**: Production-Ready (88.2% complete, Sprint 18 planned)
