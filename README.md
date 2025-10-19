# AEGIS RAG - AI-Enhanced Guardrail Integration System

Retrieval-Augmented Generation System für die Bundeswehr mit integrierten Guardrails.

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
3. **Claude Code nutzen**: Siehe [docs/core/CLAUDE.md](docs/core/CLAUDE.md) für Kontext

## 📚 Wichtige Dokumente

### Core Dokumentation
- [PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md) - Gesamtübersicht
- [SPRINT_PLAN.md](docs/core/SPRINT_PLAN.md) - 12-Sprint Roadmap
- [SPRINT_3_SUMMARY.md](SPRINT_3_SUMMARY.md) - ✅ Sprint 3 Complete (335 tests, 99.1%)
- [CLAUDE.md](docs/core/CLAUDE.md) - Claude Code Hauptkontext
- [NAMING_CONVENTIONS.md](docs/core/NAMING_CONVENTIONS.md) - Code Standards
- [SUBAGENTS.md](docs/core/SUBAGENTS.md) - 5 Subagenten-Definitionen
- [TECH_STACK.md](docs/core/TECH_STACK.md) - Complete Technology Stack
- [ADR_INDEX.md](docs/adr/ADR_INDEX.md) - 9 Architecture Decisions

### Examples & Tutorials
- [Sprint 3 Usage Examples](docs/examples/sprint3_examples.md) - Reranking, Query Decomposition, Filters

### Setup & Enforcement (9 Dateien)
- [QUICK_START.md](docs/core/QUICK_START.md) - Tag-1-Setup
- [PROMPT_TEMPLATES.md](docs/core/PROMPT_TEMPLATES.md) - 8 Claude Code Templates
- [ENFORCEMENT_GUIDE.md](docs/core/ENFORCEMENT_GUIDE.md) - Quality Gates
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

Details siehe [docs/core/TECH_STACK.md](docs/core/TECH_STACK.md)

## ✨ Sprint 3 Features (COMPLETE)

- ✅ **Cross-Encoder Reranking**: +15-20% precision improvement with ms-marco-MiniLM
- ✅ **Query Decomposition**: LLM-based classification (SIMPLE/COMPOUND/MULTI_HOP) with Ollama
- ✅ **Metadata Filtering**: Date ranges, sources, document types, tags (42 tests, 100%)
- ✅ **RAGAS Evaluation**: Context Precision/Recall/Faithfulness metrics (Score: 0.88)
- ✅ **Adaptive Chunking**: Document-type aware strategies (paragraph/heading/function/sentence)
- ✅ **Security Fix**: MD5 → SHA-256 for document IDs (CVE-2010-4651)

**Test Coverage**: 335/338 passing (99.1%)
See [SPRINT_3_SUMMARY.md](SPRINT_3_SUMMARY.md) for details

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
- Hauptkontext in [docs/core/CLAUDE.md](docs/core/CLAUDE.md)
- 5 spezialisierte Subagenten definiert
- 8 Prompt-Templates vorbereitet
- Naming Conventions integriert

## 🔒 Sicherheit

- Bundeswehr-Compliance
- Multi-Layer Guardrails
- Content Filtering
- PII Detection
- Access Control

Details in [docs/core/TECH_STACK.md](docs/core/TECH_STACK.md) und [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)

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
- Sprint 9: 3-Layer Memory Architecture + MCP Server Integration (IN PLANNING)
- Sprint 10: End-User Interface (IN PLANNING)
- Sprint 11: Configuration & Admin Interface (IN PLANNING)
- Sprint 12: Integration, Testing & Production Readiness (IN PLANNING)

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
