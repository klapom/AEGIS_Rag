# AEGIS RAG - Verzeichnisstruktur

## Übersicht aller 16 strategischen Dokumente

### 📁 Hauptverzeichnis
```
AEGIS_RAG/
├── README.md                       # Projekt-Hauptübersicht
├── STRUCTURE.md                    # Diese Datei
└── .pre-commit-config.yaml         # 14 Pre-Commit Hooks
```

### 📚 Core Dokumentation (3 Dateien)
```
docs/core/
├── PROJECT_SUMMARY.md              # ⭐ Gesamtübersicht - START HIER!
├── QUICK_START.md                  # Tag-1-Setup
└── PROMPT_TEMPLATES.md             # 8 Claude Code Templates
```

### 📅 Sprint Planning
```
docs/sprints/
└── SPRINT_PLAN.md                  # 18-Sprint Roadmap
```

### 🏗️ Architecture Decision Records
```
docs/adr/
└── ADR_INDEX.md                    # 8 Architecture Decisions
```

### ⚙️ Setup & Enforcement (9 Dateien)

#### GitHub Workflows
```
.github/
├── workflows/
│   └── ci.yml                      # 10-Job CI/CD Pipeline
├── pull_request_template.md        # PR Checklist
└── CODEOWNERS                      # Auto-Review Zuweisungen
```

#### Scripts
```
scripts/
├── check_adr.py                    # ADR Detection Script
└── check_naming.py                 # Naming Convention Checker
```

## 📊 Dokumenten-Kategorien

### 1. Einstiegsdokumente (für neue Teammitglieder)
- ✅ [README.md](README.md)
- ✅ [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md)
- ✅ [docs/core/QUICK_START.md](docs/core/QUICK_START.md)

### 2. Entwicklungs-Guidelines
- See [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md) for architecture decisions

### 3. Projektplanung
- ✅ [docs/sprints/SPRINT_PLAN.md](docs/sprints/SPRINT_PLAN.md)
- ✅ [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)

### 4. Claude Code Integration
- ✅ [docs/core/PROMPT_TEMPLATES.md](docs/core/PROMPT_TEMPLATES.md)

### 5. Automation & Quality
- ✅ [.pre-commit-config.yaml](.pre-commit-config.yaml)
- ✅ [.github/workflows/ci.yml](.github/workflows/ci.yml)
- ✅ [.github/pull_request_template.md](.github/pull_request_template.md)
- ✅ [.github/CODEOWNERS](.github/CODEOWNERS)
- ✅ [scripts/check_adr.py](scripts/check_adr.py)
- ✅ [scripts/check_naming.py](scripts/check_naming.py)

## 🎯 Schnellzugriff nach Anwendungsfall

### "Ich bin neu im Projekt"
1. [README.md](README.md) - Projekt verstehen
2. [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md) - Details lesen
3. [docs/core/QUICK_START.md](docs/core/QUICK_START.md) - Setup durchführen

### "Ich will Code schreiben"
1. [docs/core/PROMPT_TEMPLATES.md](docs/core/PROMPT_TEMPLATES.md) - Templates
2. [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md) - Architecture Decisions

### "Ich will verstehen warum X so ist"
1. [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md) - Architekturentscheidungen
2. [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md) - Technology Overview

### "Ich will Quality sicherstellen"
1. [.pre-commit-config.yaml](.pre-commit-config.yaml) - Pre-Commit Hooks
2. [.github/workflows/ci.yml](.github/workflows/ci.yml) - CI/CD Pipeline

### "Ich plane Features"
1. [docs/sprints/SPRINT_PLAN.md](docs/sprints/SPRINT_PLAN.md) - Roadmap
2. [docs/core/PROJECT_SUMMARY.md](docs/core/PROJECT_SUMMARY.md) - Vision
3. [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md) - Constraints

## 📏 Dokumenten-Metriken

| Kategorie | Anzahl | Dateien |
|-----------|--------|---------|
| Core Docs | 4 | PROJECT_SUMMARY, SPRINT_PLAN, QUICK_START, PROMPT_TEMPLATES |
| ADRs | 1 | ADR_INDEX (mit 18+ ADRs) |
| GitHub | 3 | ci.yml, pull_request_template.md, CODEOWNERS |
| Scripts | 2 | check_adr.py, check_naming.py |
| Config | 1 | .pre-commit-config.yaml |
| **TOTAL** | **11** | Alle strategischen Dokumente |

## 🔄 Nächste Schritte

Nach dem Sortieren der Dateien:

1. ✅ **Struktur erstellt** - Alle Dateien organisiert
2. ✅ **Git initialisiert** - Repository aufgesetzt
3. ✅ **Pre-Commit Hooks installiert** - `pre-commit install`
4. ✅ **Commits erstellt** - Sprint 1-14 completed
5. ✅ **Claude Code konfiguriert** - Aktiv in Verwendung

## 📋 Checkliste für Vollständigkeit

### Dokumentation
- [x] PROJECT_SUMMARY.md
- [x] SPRINT_PLAN.md
- [x] ADR_INDEX.md
- [x] QUICK_START.md
- [x] PROMPT_TEMPLATES.md

### Setup & Enforcement
- [x] .pre-commit-config.yaml
- [x] .github/workflows/ci.yml
- [x] .github/pull_request_template.md
- [x] scripts/check_adr.py
- [x] scripts/check_naming.py
- [x] .github/CODEOWNERS

### Root-Level
- [x] README.md
- [x] STRUCTURE.md

**Status**: ✅ Alle 11 strategischen Dokumente erfolgreich sortiert und organisiert!

---

**Version**: 1.0.0
**Erstellt**: Oktober 2024
**Maintainer**: AEGIS RAG Team
