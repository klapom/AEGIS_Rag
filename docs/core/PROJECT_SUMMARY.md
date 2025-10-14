# AegisRAG - Strategische Projektdokumentation
## Zusammenfassung & Dokumenten-Übersicht

Diese Dokumentation bildet die strategische Basis für die Entwicklung des AegisRAG-Systems mit Claude Code.

---

## 📦 Lieferumfang

Die folgenden strategischen Dokumente wurden erstellt:

| # | Dokument | Zweck | Zielgruppe |
|---|----------|-------|------------|
| 1 | **SPRINT_PLAN.md** | 10-Sprint Roadmap mit Deliverables | Alle |
| 2 | **CLAUDE.md** | Projekt-Context für Claude Code | Claude Code |
| 3 | **NAMING_CONVENTIONS.md** | Code Standards & Best Practices | Entwickler |
| 4 | **ADR_INDEX.md** | Architecture Decision Records | Tech Lead |
| 5 | **SUBAGENTS.md** | Claude Code Subagenten-Definitionen | Claude Code |
| 6 | **TECH_STACK.md** | Technology Stack Matrix | Alle |
| 7 | **QUICK_START.md** | Setup-Anleitung | Entwickler |

---

## 1️⃣ SPRINT_PLAN.md - Die 10-Sprint Roadmap

**Inhalt:**
- Detaillierte Planung für 10 Wochen (Sprints 1-10)
- Deliverables, Technical Tasks, Success Criteria pro Sprint
- Sprint-Velocity Assumptions
- Definition of Done (DoD)
- Risk Management Matrix
- Post-Sprint 10 Backlog

**Sprint-Überblick:**
```
Sprint 1: Foundation & Infrastructure Setup
Sprint 2: Component 1 - Vector Search Foundation
Sprint 3: Component 1 - Advanced Retrieval
Sprint 4: LangGraph Orchestration Layer
Sprint 5: Component 2 - LightRAG Integration
Sprint 6: Component 2 - Hybrid Vector-Graph Retrieval
Sprint 7: Component 3 - Graphiti Memory + Azure OpenAI (Optional)
Sprint 8: 3-Layer Memory Architecture + LLM A/B Testing
Sprint 9: Component 4 - MCP Server Integration
Sprint 10: Integration, Testing & Production Readiness
```

**Wann verwenden:**
- Zu Beginn jedes Sprints: Ziele und Tasks reviewen
- Weekly Stand-up: Progress gegen Plan tracken
- Sprint-Planning: Nächsten Sprint vorbereiten

---

## 2️⃣ CLAUDE.md - Der Projekt-Context

**Inhalt:**
- Projekt-Overview (4 Core-Komponenten)
- Architecture Principles & Design Patterns
- Technology Stack (Versions)
- Repository Structure (komplette Verzeichnishierarchie)
- Development Workflow (Branch Strategy, Commits)
- Code Quality Gates (Linting, Testing)
- Subagent Responsibilities
- Critical Implementation Details (Code Examples)
- Environment Variables
- Performance Requirements
- Testing Strategy
- Monitoring & Observability
- Common Issues & Solutions
- Security Considerations
- Deployment Instructions
- Troubleshooting Commands

**Wann verwenden:**
- **IMMER als Kontext für Claude Code bereitstellen**
- Bei jedem neuen Feature: Architektur-Patterns checken
- Bei Problemen: Troubleshooting Section konsultieren
- Onboarding: Kompletter Project Context

**Wichtig:** Dies ist das Hauptdokument für Claude Code!

---

## 3️⃣ NAMING_CONVENTIONS.md - Code Standards

**Inhalt:**
- Python Naming (Files, Classes, Functions, Variables)
- Directory & File Naming Patterns
- Component Structure Examples
- Test File Naming
- Imports Organization
- Type Hints Best Practices
- Docstrings Standards
- Error Handling Patterns
- Logging Best Practices
- Configuration Management
- API Conventions (RESTful Patterns)
- Database Conventions (Qdrant, Neo4j, Redis)
- Testing Conventions (Fixtures, Factories)
- Git Commit Standards (Conventional Commits)
- Code Review Checklist
- Performance Guidelines & Anti-Patterns
- Security Best Practices
- Documentation Standards

**Wann verwenden:**
- Vor Code-Review: Checklist durchgehen
- Beim Onboarding neuer Entwickler
- Bei Unsicherheiten zur Namensgebung
- Code Quality Gates Setup

**Enforcement:** Via Pre-commit Hooks + CI Pipeline

---

## 4️⃣ ADR_INDEX.md - Architecture Decisions

**Inhalt:**
- ADR Index (Übersichtstabelle)
- 8 detaillierte Architecture Decision Records:
  1. LangGraph als Orchestrierungs-Framework
  2. Hybrid Vector-Graph Retrieval Architecture
  3. Qdrant als primäre Vector Database
  4. LightRAG statt Microsoft GraphRAG
  5. 3-Layer Memory Architecture
  6. Model Context Protocol Integration
  7. Python + FastAPI für Backend
  8. Reciprocal Rank Fusion für Hybrid Search
- ADR Template für zukünftige Decisions
- Decision Review Process

**ADR Format:**
- Status (Proposed/Accepted/Deprecated/Superseded)
- Context (Problem Statement)
- Decision (Was wurde entschieden)
- Alternatives Considered (Pro/Contra)
- Rationale (Begründung)
- Consequences (Positive/Negative + Mitigations)

**Wann verwenden:**
- Bei neuen Architektur-Entscheidungen: Neues ADR erstellen
- Bei Fragen zu Technology Choices: ADRs nachlesen
- Quarterly Review: ADRs auf Aktualität prüfen
- Onboarding: Verständnis für Architektur-Rationale

---

## 5️⃣ SUBAGENTS.md - Claude Code Orchestration

**Inhalt:**
- Subagent Architecture Overview
- 5 spezialisierte Subagenten:
  1. **Backend Agent** (Core Business Logic)
  2. **Infrastructure Agent** (DevOps & Deployment)
  3. **API Agent** (REST Interface)
  4. **Testing Agent** (Quality Assurance)
  5. **Documentation Agent** (Docs & Examples)
- Pro Subagent:
  - Role & Responsibilities
  - Technical Expertise
  - File Ownership
  - Communication Protocol
  - Success Criteria
- Delegation Patterns (Sequential/Parallel/Collaborative)
- Context Sharing Between Agents
- Agent Handoff Protocol
- Agent Selection Decision Tree
- Example: Sprint 2 Task Delegation
- Communication Best Practices
- Subagent Performance Metrics

**Wann verwenden:**
- **Zu Beginn jeder Claude Code Session:** Überlegen welche Agents benötigt
- Bei komplexen Tasks: Delegation Strategy planen
- Bei Bottlenecks: Performance Metrics checken
- Onboarding: Delegation Patterns lernen

---

## 6️⃣ TECH_STACK.md - Technology Matrix

**Inhalt:**
- Core Stack Overview (Tabelle mit Alternativen)
- Detaillierte Analyse für 8 Haupt-Komponenten:
  1. FastAPI (Backend Framework)
  2. LangGraph (Orchestration)
  3. LlamaIndex (Data Ingestion)
  4. Qdrant (Vector DB)
  5. Neo4j (Graph DB)
  6. LightRAG (GraphRAG)
  7. Graphiti (Memory)
  8. LLM Selection Matrix
- Development Tools (Ruff, Black, MyPy, Pre-commit)
- Testing Stack (pytest, Locust)
- Monitoring & Observability (Prometheus, Grafana)
- Infrastructure Stack (Docker, Kubernetes)
- CI/CD Pipeline Details
- Dependency Management (Poetry/UV)
- Complete pyproject.toml Template
- Cost Estimation (MVP vs. Managed)
- Version Compatibility Matrix
- Technology Decision Checklist

**Wann verwenden:**
- Bei Setup: Versionen aus TECH_STACK kopieren
- Bei Dependency Updates: Compatibility prüfen
- Bei Budget Planning: Cost Estimation checken
- Bei Technology Evaluations: Decision Checklist nutzen

---

## 7️⃣ QUICK_START.md - Setup-Anleitung

**Inhalt:**
- Voraussetzungen (Python, Docker, API Keys)
- Schritt-für-Schritt Projekt-Setup mit Claude Code
- Erwartete Projekt-Struktur nach Sprint 1
- Lokale Entwicklung (Environment, Secrets, Docker)
- Entwicklungs-Workflow mit Claude Code
- Feature Development Beispiel (Sprint 2)
- Troubleshooting (Docker, Import Errors, Tests)
- Sprint 1 Checkliste & Definition of Done
- Nächste Schritte nach Sprint 1
- Wichtige Ressourcen (Links)
- Pro Tips für Claude Code (Effektive Delegation)
- Sprint 1 Completion Criteria

**Wann verwenden:**
- **Tag 1: Komplettes Initial Setup**
- Bei Onboarding neuer Team-Mitglieder
- Bei Problemen: Troubleshooting Section
- Referenz für Claude Code Best Practices

---

## 🎯 Wie diese Dokumentation nutzen

### Für Team Lead / Architekt

```
Start: ADR_INDEX.md lesen (Architektur-Entscheidungen verstehen)
  ↓
SPRINT_PLAN.md reviewen (Roadmap verstehen)
  ↓
TECH_STACK.md studieren (Technology Choices validieren)
  ↓
Wöchentlich: SPRINT_PLAN.md tracken
Monatlich: ADRs reviewen
```

### Für Entwickler

```
Start: QUICK_START.md (Setup durchführen)
  ↓
CLAUDE.md lesen (Projekt-Context verstehen)
  ↓
NAMING_CONVENTIONS.md studieren (Code Standards)
  ↓
Täglich: SUBAGENTS.md (effektive Delegation mit Claude Code)
Bei Unsicherheiten: TECH_STACK.md (Versionen, Configs)
```

### Für Claude Code

```
Immer: CLAUDE.md als Context laden
  ↓
Delegation: SUBAGENTS.md (welcher Agent für welche Task)
  ↓
Implementierung: NAMING_CONVENTIONS.md (Code Standards)
  ↓
Technische Details: TECH_STACK.md (Versionen, Configs)
  ↓
Sprint-Context: SPRINT_PLAN.md (aktuelle Ziele)
```

---

## 🔄 Dokumentations-Maintenance

### Wöchentlich
- [ ] SPRINT_PLAN.md: Progress aktualisieren
- [ ] Sprint-spezifische TODOs tracken

### Monatlich
- [ ] TECH_STACK.md: Dependency Updates prüfen
- [ ] CLAUDE.md: Common Issues erweitern (wenn neue gefunden)

### Quarterly
- [ ] ADR_INDEX.md: ADRs auf Aktualität reviewen
- [ ] Alle Docs: Broken Links prüfen
- [ ] TECH_STACK.md: Cost Estimation aktualisieren

### Bei Bedarf
- [ ] NAMING_CONVENTIONS.md: Bei neuen Patterns erweitern
- [ ] SUBAGENTS.md: Bei Performance-Issues anpassen
- [ ] QUICK_START.md: Bei Setup-Problemen Troubleshooting ergänzen

---

## 📊 Dokumenten-Abhängigkeiten

```
CLAUDE.md (Hauptdokument, referenziert alle anderen)
    ├── SPRINT_PLAN.md (Sprint-Ziele)
    ├── NAMING_CONVENTIONS.md (Code Standards)
    ├── ADR_INDEX.md (Architektur-Rationale)
    ├── SUBAGENTS.md (Delegation Strategy)
    └── TECH_STACK.md (Versionen & Configs)

QUICK_START.md (Setup-Entry Point)
    └── Referenziert alle anderen Docs
```

---

## ✅ Dokumentations-Checkliste

**Vor Sprint 1 Start:**
- [ ] Alle 7 Dokumente in Projekt übertragen
- [ ] CLAUDE.md als Context in Claude Code geladen
- [ ] Team hat alle Docs gelesen
- [ ] Fragen geklärt

**Während Entwicklung:**
- [ ] SPRINT_PLAN.md als Referenz für Tasks
- [ ] NAMING_CONVENTIONS.md bei Code Reviews nutzen
- [ ] SUBAGENTS.md für effektive Delegation
- [ ] TECH_STACK.md bei Setup-Problemen

**Bei Architektur-Änderungen:**
- [ ] Neues ADR in ADR_INDEX.md
- [ ] CLAUDE.md updaten
- [ ] TECH_STACK.md bei Tech-Wechsel updaten

---

## 🚀 Nächste Schritte

1. **Dokumentation in Projekt übertragen**
   ```bash
   cp /home/claude/*.md ~/aegis-rag/docs/
   cp /home/claude/CLAUDE.md ~/aegis-rag/
   cp /home/claude/QUICK_START.md ~/aegis-rag/
   ```

2. **QUICK_START.md folgen**
   - Initial Setup durchführen
   - Claude Code starten
   - Sprint 1 Ziele laden

3. **Mit Claude Code arbeiten**
   - CLAUDE.md als Context bereitstellen
   - SUBAGENTS.md für Delegation nutzen
   - SPRINT_PLAN.md für Tasks referenzieren

4. **Iterativ entwickeln**
   - Sprint 1 → Sprint 2 → ... → Sprint 10
   - Dokumentation bei Bedarf erweitern
   - ADRs bei Architektur-Änderungen

---

## 📈 Erfolgskriterien

**Diese Dokumentation ist erfolgreich wenn:**
- [ ] Team kann ohne externe Hilfe Setup durchführen (QUICK_START.md)
- [ ] Claude Code liefert konsistente, hochwertige Outputs (CLAUDE.md)
- [ ] Code Reviews sind schnell & standardisiert (NAMING_CONVENTIONS.md)
- [ ] Architektur-Entscheidungen sind nachvollziehbar (ADR_INDEX.md)
- [ ] Technology Stack ist klar dokumentiert (TECH_STACK.md)
- [ ] Sprints laufen nach Plan (SPRINT_PLAN.md)
- [ ] Delegation an Claude Code ist effizient (SUBAGENTS.md)

---

## 🎓 Lern-Ressourcen

**Für neue Team-Mitglieder:**
1. Tag: QUICK_START.md + CLAUDE.md (Setup & Overview)
2. Tag: NAMING_CONVENTIONS.md (Code Standards)
3. Tag: ADR_INDEX.md (Architektur-Rationale)
4. Tag: SUBAGENTS.md (Claude Code Delegation)
5. Tag: Hands-on mit Claude Code (echte Tasks)

**Für Claude Code Sessions:**
- Vor jeder Session: SPRINT_PLAN.md checken (aktuelle Ziele)
- Bei Session: CLAUDE.md + SUBAGENTS.md als Context
- Nach Session: Progress in SPRINT_PLAN.md updaten

---

## 💡 Pro Tips

### Dokumentation optimal nutzen

**Tipp 1: CLAUDE.md ist König**
- Immer als Context für Claude Code laden
- Bei Unsicherheiten: CLAUDE.md nachschlagen
- Regelmäßig aktualisieren mit neuen Learnings

**Tipp 2: ADRs sind Zeitersparnis**
- Statt lange zu diskutieren: ADR schreiben
- Bei Fragen: "Siehe ADR-003" statt zu erklären
- Dokumentiert Rationale für zukünftige Entscheidungen

**Tipp 3: SPRINT_PLAN.md lebt**
- Nicht starr befolgen, sondern adaptieren
- Learnings einfließen lassen
- Velocity anpassen basierend auf Realität

**Tipp 4: SUBAGENTS.md ist Delegation-Guide**
- Nicht alles selbst machen
- Claude Code Subagenten optimal nutzen
- Performance Metrics tracken

**Tipp 5: TECH_STACK.md ist Single Source of Truth**
- Bei Dependency Updates: Hier zuerst
- Bei Versionen-Konflikten: Hier nachschlagen
- Bei Budget-Fragen: Cost Estimation checken

---

## 📞 Support & Fragen

**Bei Fragen zur Dokumentation:**
1. Relevantes Dokument durchsuchen (Ctrl+F)
2. In CLAUDE.md "Common Issues" checken
3. In QUICK_START.md "Troubleshooting" schauen

**Bei technischen Problemen:**
1. QUICK_START.md → Troubleshooting Section
2. CLAUDE.md → Common Issues & Solutions
3. TECH_STACK.md → Compatibility Matrix

**Bei Architektur-Fragen:**
1. ADR_INDEX.md → Relevantes ADR lesen
2. CLAUDE.md → Architecture Principles
3. TECH_STACK.md → Alternatives Considered

---

**Viel Erfolg mit AegisRAG! 🚀**

Diese strategische Dokumentation bildet das Fundament für ein erfolgreiches Projekt mit Claude Code.
