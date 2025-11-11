# CONTEXT REFRESH MASTER GUIDE
**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Purpose:** Timeless guide for achieving FULL context refresh in any session
**Version:** 5.0 (Sprint-Independent, Reference-Based)
**Last Updated:** 2025-11-10

---

## 📋 TABLE OF CONTENTS

1. [Quick Start](#quick-start) - Get context back in 1-5 minutes
2. [When to Refresh](#when-to-refresh) - Recognize the signs
3. [Three Refresh Strategies](#three-refresh-strategies) - Quick, Standard, Deep
4. [Core Documentation Map](#core-documentation-map) - What to read
5. [Verification Checklist](#verification-checklist) - Confirm understanding
6. [Best Practices](#best-practices) - Optimize your workflow

---

## 🚀 QUICK START

### Copy-Paste This Prompt (Recommended for Most Cases)

```
🔄 CONTEXT REFRESH - AEGIS RAG

Bitte mach dich mit dem Projekt vertraut. Lies folgende Dateien:

📖 CORE CONTEXT (IMMER):
1. docs/CLAUDE.md - Projekt-Übersicht & Architektur
2. docs/SUBAGENTS.md - Delegation Strategy & File Ownership
3. docs/NAMING_CONVENTIONS.md - Code Standards
4. README.md - Projekt-Status & Quick Start

📊 CURRENT STATE (DYNAMISCH):
5. docs/sprints/SPRINT_PLAN.md - Sprint-Übersicht & aktueller Sprint
6. Neueste SPRINT_*_PLAN.md oder SPRINT_*_SUMMARY.md - Aktueller Sprint-Status
7. docs/adr/ADR_INDEX.md - Alle Architecture Decisions (mit Querverweisen)

📚 ARCHITECTURE (BEI BEDARF):
8. docs/TECH_STACK.md - Tech Stack (dynamisch aktualisiert)
9. docs/ARCHITECTURE_EVOLUTION.md - Sprint Journey & Learnings
10. docs/architecture/COMPONENT_INTERACTION_MAP.md - Data Flows

Gib mir einen Executive Summary mit 5 Bulletpoints:
- Projekt-Ziel & Architektur (3-Layer Memory)
- Aktueller Sprint & Status (aus SPRINT_PLAN.md)
- Nächste Priorität
- Tech Stack Highlights
- Wichtigste ADRs (3-5)
```

**Expected Reading Time:** 3-5 minutes
**Use When:** Session resumed, context uncertain, before starting work

---

## 🚨 WHEN TO REFRESH

### ⚠️ Trigger Signals (PERFORM REFRESH IMMEDIATELY)

| Symptom | What It Means | Refresh Type |
|---------|---------------|--------------|
| "I don't have access to..." | File context lost | Quick Refresh |
| PascalCase statt snake_case | Standards forgotten | Quick Refresh |
| Keine Subagenten-Delegation | Workflow context lost | Standard Refresh |
| Fragen nach Tech Stack | Technical context lost | Standard Refresh |
| Keine ADR-Referenzen | Architecture context lost | Deep Refresh |
| Sprint-Ziel unklar | Planning context lost | Deep Refresh |
| "Was ist AEGIS RAG?" | COMPLETE context loss | Deep Refresh |

### ✅ Proactive Refresh Schedule

```
Session Start (Neue Session):        → Standard Refresh
Nach langer Pause (>1 Tag):          → Standard Refresh
Montag / Sprint-Start:                → Deep Refresh
Alle 20-30 Messages (lange Session): → Quick Check
Vor kritischen Tasks:                 → Quick Check + relevante Docs
Nach Kompaktierung:                   → Minimum Quick Refresh
Team-Übergabe:                        → Deep Refresh
```

---

## 🔄 THREE REFRESH STRATEGIES

### Strategy 1: Quick Refresh (1 Minute)

**Copy-Paste Prompt:**
```
Context Refresh: Lies docs/CLAUDE.md, docs/sprints/SPRINT_PLAN.md (aktueller Sprint),
docs/SUBAGENTS.md, docs/NAMING_CONVENTIONS.md. Bestätige kurz (3 Sätze).
```

**What Gets Refreshed:**
- ✅ Projekt-Name & Architektur
- ✅ Aktueller Sprint & Ziele
- ✅ Subagenten-Responsibilities
- ✅ Naming Conventions

**When to Use:**
- Nach kompakter Kompaktierung
- Task-Continuity wichtig
- Nur leichter Context Loss (Naming, Subagenten)

---

### Strategy 2: Standard Refresh (2-3 Minuten)

**Copy-Paste Prompt:**
```
🔄 STANDARD CONTEXT REFRESH

Bitte reaktiviere vollständigen Projekt-Context:

📖 CORE:
1. docs/CLAUDE.md - Projekt & Architektur
2. docs/sprints/SPRINT_PLAN.md - Sprint-Übersicht
3. Neueste SPRINT_*_PLAN.md - Aktueller Sprint
4. docs/SUBAGENTS.md - 5 Subagenten & File Ownership
5. docs/NAMING_CONVENTIONS.md - Code Standards

📚 TECH & DECISIONS:
6. docs/TECH_STACK.md - Tech Stack Updates
7. docs/adr/ADR_INDEX.md - Architecture Decisions
8. README.md - Project overview

Bestätige mit Zusammenfassung (5 Bulletpoints):
- Projekt-Ziel & 3-Layer Architecture
- Aktueller Sprint & Status
- Tech Stack Highlights
- Next Priority
- Key ADRs (3-5)
```

**What Gets Refreshed:**
- ✅ Vollständiger Projekt-Context
- ✅ Aktueller Sprint-Plan & Status
- ✅ Tech Stack & Recent Updates
- ✅ Subagent Workflow
- ✅ Important ADRs

**When to Use:**
- Nach größerer Kompaktierung
- Vor kritischen Tasks
- Session nach >1 Tag Pause

---

### Strategy 3: Deep Refresh (5-7 Minuten)

**Copy-Paste Prompt:**
```
🔄 DEEP CONTEXT REFRESH (VOLLSTÄNDIG)

Neue Session / Major Context Loss. Vollständiger Architektur-Context benötigt:

📋 PROJECT FOUNDATION:
1. README.md - Projekt-Überblick & Quick Start
2. docs/CLAUDE.md - Vollständiger Projekt-Context
3. docs/ARCHITECTURE_EVOLUTION.md - Sprint Journey & Learnings
4. docs/sprints/SPRINT_PLAN.md - Master Sprint Plan

🏗️ ARCHITECTURE & TECH STACK:
5. docs/TECH_STACK.md - Complete stack
6. docs/architecture/ARCHITECTURE_OVERVIEW.md - System design
7. docs/architecture/COMPONENT_INTERACTION_MAP.md - Data flows & API contracts
8. docs/DEPENDENCY_RATIONALE.md - Library choice justifications

👥 WORKFLOW & STANDARDS:
9.  docs/SUBAGENTS.md - Delegation Strategy
10. docs/NAMING_CONVENTIONS.md - Code Standards
11. docs/TECHNICAL_DEBT_SUMMARY.md - Current TD status (falls vorhanden)

🎯 ADRs (Architecture Decisions):
12. docs/adr/ADR_INDEX.md - Alle ADRs mit Querverweisen
13. Relevante ADRs basierend auf aktuellem Sprint

📊 CURRENT SPRINT STATUS:
14. Neueste SPRINT_*_PLAN.md - Aktueller Sprint
15. Neueste SPRINT_*_SUMMARY.md - Sprint-Abschluss (falls completed)

Gib mir einen Executive Summary (7 Bulletpoints):
- Projekt-Ziel & Architektur (3-Layer Memory)
- Aktueller Sprint & Achievements
- Nächster Sprint Focus
- Key Architectural Patterns
- Tech Stack (Full-stack)
- Top 5 Important ADRs
- Top 3 Immediate Priorities
```

**What Gets Refreshed:**
- ✅ COMPLETE Project Context
- ✅ Full Sprint History & Status
- ✅ All Architecture Decisions (ADRs)
- ✅ Complete Tech Stack & Dependencies
- ✅ Architecture Evolution & Learnings
- ✅ Component Interactions & Data Flows
- ✅ Technical Debt Status

**When to Use:**
- Montag-Morgen / Wochenstart
- Nach langer Pause (>3 Tage)
- Major Context Loss (kompletter Reset)
- Team-Übergabe
- Sprint-Start

---

## 📚 CORE DOCUMENTATION MAP

### Essential Reading (Always Read These)

| Document | What It Contains | Read When | Status |
|----------|------------------|-----------|--------|
| **docs/CLAUDE.md** | Complete project context, architecture, workflows | Every refresh | ✅ Auto-updated |
| **docs/SUBAGENTS.md** | 5 subagents, file ownership, delegation rules | Every refresh | ✅ Stable |
| **docs/NAMING_CONVENTIONS.md** | snake_case, PascalCase, SCREAMING_SNAKE rules | Every refresh | ✅ Stable |
| **README.md** | Project overview, quick start, current status | Every refresh | ✅ Auto-updated |

### Sprint Planning & Status (DYNAMIC - Check Latest Files)

| Document | What It Contains | Read When | Status |
|----------|------------------|-----------|--------|
| **docs/sprints/SPRINT_PLAN.md** | Master sprint plan (all sprints), **ALWAYS CHECK CURRENT SPRINT** | Standard/Deep refresh | ✅ Auto-updated |
| **Latest SPRINT_N_PLAN.md** | Current sprint plan (N = aktueller Sprint) | Standard/Deep refresh | 🔄 Dynamic |
| **Latest SPRINT_N_SUMMARY.md** | Completed sprint summary | After sprint completion | 🔄 Dynamic |

### Architecture & Deep Understanding (Read for Deep Refresh)

| Document | What It Contains | Read When | Status |
|----------|------------------|-----------|--------|
| **docs/ARCHITECTURE_EVOLUTION.md** | Sprint journey, learnings, architectural decisions | Deep refresh | ✅ Backfilled |
| **docs/TECH_STACK.md** | Complete tech stack (dynamisch aktualisiert) | Standard/Deep refresh | ✅ Auto-updated |
| **docs/architecture/ARCHITECTURE_OVERVIEW.md** | System design, components | Deep refresh | ✅ Stable |
| **docs/architecture/COMPONENT_INTERACTION_MAP.md** | Data flows, API contracts, request scenarios | Deep refresh | ✅ Updated |
| **docs/DEPENDENCY_RATIONALE.md** | Library choice justifications (70+ dependencies) | Deep refresh | ✅ Stable |

### Architecture Decisions (ADRs) - Read Task-Specific

| Document | What It Contains | Read When | Status |
|----------|------------------|-----------|--------|
| **docs/adr/ADR_INDEX.md** | ADR index and quick reference with cross-references | Standard/Deep refresh | ✅ Auto-updated |
| **docs/adr/ADR-*.md** | Individual Architecture Decision Records | Task-specific | 🔄 Growing |

### Component-Specific Documentation

| Document | What It Contains | Read When | Status |
|----------|------------------|-----------|--------|
| **src/components/*/README.md** | Component architecture, usage, APIs | Task-specific | ✅ Complete |
| **docs/api/**.md | API documentation (endpoints, SSE, errors) | API development | ✅ Complete |

### File Reading Order (Deep Refresh)

```
Priority 1 (MUST READ - ALWAYS CURRENT):
1. README.md - Project status
2. docs/CLAUDE.md - Full context
3. docs/sprints/SPRINT_PLAN.md - Sprint overview (check CURRENT sprint)
4. Latest SPRINT_*_PLAN.md - Current sprint details

Priority 2 (SHOULD READ - Architecture):
5. docs/TECH_STACK.md - Tech stack
6. docs/ARCHITECTURE_EVOLUTION.md - Sprint journey
7. docs/architecture/ARCHITECTURE_OVERVIEW.md - System design
8. docs/architecture/COMPONENT_INTERACTION_MAP.md - Data flows

Priority 3 (SHOULD READ - Workflow):
9. docs/SUBAGENTS.md - Delegation
10. docs/NAMING_CONVENTIONS.md - Code standards
11. docs/adr/ADR_INDEX.md - Architecture decisions

Priority 4 (OPTIONAL - Task-Specific):
12. Specific ADRs based on task (from ADR_INDEX.md)
13. Component READMEs (src/components/*/README.md)
14. API Documentation (docs/api/*.md)
```

---

## ✅ VERIFICATION CHECKLIST

After ANY refresh, Claude Code should be able to confirm:

### ✅ PROJECT CONTEXT
```
- [ ] Projekt-Name: AEGIS RAG (Agentic Enterprise Graph Intelligence System)
- [ ] Purpose: Enterprise-grade Hybrid RAG
- [ ] 3-Layer Memory: Redis → Qdrant/BM25/LightRAG → Graphiti
- [ ] Status: Aktueller Sprint klar (aus SPRINT_PLAN.md)
```

### ✅ ARCHITECTURE
```
- [ ] Layer 1: Redis (short-term memory)
- [ ] Layer 2: Qdrant (vector) + BM25 (keyword) + LightRAG (graph)
- [ ] Layer 3: Graphiti (episodic memory)
- [ ] Orchestration: LangGraph with multi-agent state management
- [ ] LLM Strategy: 100% local (Ollama), zero API costs
```

### ✅ TECH STACK (Check docs/TECH_STACK.md for current versions)
```
- [ ] Frontend: React + TypeScript + Vite + Tailwind CSS
- [ ] Backend: Python 3.12+, FastAPI
- [ ] Orchestration: LangGraph
- [ ] LLMs: Ollama (llama3.2, gemma, qwen)
- [ ] Embeddings: BGE-M3 (1024-dim, multilingual)
- [ ] Vector: Qdrant
- [ ] Graph: Neo4j
- [ ] Memory: Redis
```

### ✅ CURRENT STATE (Check SPRINT_PLAN.md for latest)
```
- [ ] Aktueller Sprint bekannt (Sprint N)
- [ ] Sprint-Ziel klar
- [ ] Nächste Priorität identifiziert
- [ ] Wichtigste ADRs für aktuellen Sprint bekannt (3-5)
```

### ✅ WORKFLOW & STANDARDS
```
- [ ] 5 Subagenten: test-engineer, langgraph-specialist, graphiti-specialist,
                   lightrag-specialist, general-backend-dev
- [ ] Naming Conventions:
      - Functions/variables: snake_case
      - Classes: PascalCase
      - Constants: SCREAMING_SNAKE_CASE
- [ ] 1 Feature = 1 Commit workflow
```

---

## 🎯 BEST PRACTICES

### DO ✅

```
✅ Context Refresh bei JEDEM Zeichen von Context Loss
✅ Deep Refresh am Montag / Sprint-Start
✅ Standard Refresh am Session-Start (nach >1 Tag)
✅ Quick Check alle 20-30 Nachrichten
✅ Lies SPRINT_PLAN.md für aktuellen Sprint-Status
✅ Lies ARCHITECTURE_EVOLUTION.md für vollständigen Context
✅ Lies TECH_STACK.md für aktuelle Versionen
✅ Nutze die Copy-Paste Prompts aus diesem Guide
✅ Bestätige Verständnis mit Verification Checklist
```

### DON'T ❌

```
❌ Weitermachen wenn Naming Conventions ignoriert werden
❌ Hoffen dass Context "von selbst zurückkommt"
❌ Quick Refresh bei Major Context Loss (nutze Deep Refresh!)
❌ CLAUDE.md skippen (immer lesen!)
❌ SPRINT_PLAN.md ignorieren (prüfe aktuellen Sprint!)
❌ Alte Sprint-spezifische Details im Gedächtnis behalten
❌ Hardcoded Sprint-Nummern annehmen (immer nachschlagen!)
```

### Timing Guidelines

```
Session Duration    | Recommended Refreshes
--------------------|------------------------
<30 messages        | 0-1 (nur bei Context Loss)
30-60 messages      | 1-2 (Quick Check @ 30, Refresh @ 60)
60-100 messages     | 2-3 (Quick Check @ 30, 60, Refresh @ 90)
>100 messages       | Consider new session + Deep Refresh
```

---

## 🔔 PROACTIVE CHECKS (Checklist)

### Every 20-30 Messages (Long Sessions)
```
Quick Check: Aktueller Sprint noch klar? Feature N.M next?
Subagenten-Delegation OK? Naming Conventions (snake_case) befolgt?
Falls unsicher → Quick Refresh.
```

### Before Critical Tasks
```
Context Check: Lies docs/CLAUDE.md + docs/sprints/SPRINT_PLAN.md
für diese Task. Architektur klar? ADRs bekannt?
```

### After Kompaktierung (Always)
```
Minimum: Quick Refresh (Strategy 1)
Falls Major Kompaktierung: Standard Refresh (Strategy 2)
```

### Monday / Sprint-Start
```
Deep Refresh (Strategy 3) durchführen.
Verify: Aktueller Sprint-Status aus SPRINT_PLAN.md.
Lies ARCHITECTURE_EVOLUTION.md für vollständigen Context.
```

---

## 💡 REMEMBER

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║  Context Refresh ist NORMAL und WICHTIG!                       ║
║                                                                ║
║  Besser 2-7 Minuten für vollständigen Context investieren      ║
║  als 30-60 Minuten mit suboptimalem/falschem Context arbeiten. ║
║                                                                ║
║  SPRINT_PLAN.md = ALWAYS CHECK CURRENT SPRINT!                 ║
║  CLAUDE.md = ALWAYS UPDATED PROJECT CONTEXT!                   ║
║                                                                ║
║  Deep Refresh = ARCHITECTURE_EVOLUTION.md + TECH_STACK.md!     ║
║                                                                ║
║                    Happy Coding! 🚀                            ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🔄 Document Maintenance

**This Document:**
- **Version:** 5.0 (Sprint-Independent, Reference-Based)
- **Created:** 2025-10-22
- **Last Updated:** 2025-11-10
- **Maintenance:** This document is TIMELESS - no sprint references

**Referenced Documents (Auto-Updated):**
- **docs/CLAUDE.md** - Auto-updated with current sprint status
- **docs/sprints/SPRINT_PLAN.md** - Master plan, always current
- **docs/TECH_STACK.md** - Tech stack, dynamically updated
- **docs/adr/ADR_INDEX.md** - ADR index, growing list

**How to Find Current Sprint:**
1. Read `docs/sprints/SPRINT_PLAN.md` (look for "Current Sprint" section)
2. Find latest `SPRINT_N_PLAN.md` (highest N)
3. Check `docs/CLAUDE.md` (Current Project State section)

---

**Quick Access Commands:**
- Full Project Context: Read `docs/CLAUDE.md`
- Current Sprint Status: Read `docs/sprints/SPRINT_PLAN.md`
- Architecture History: Read `docs/ARCHITECTURE_EVOLUTION.md`
- Tech Stack: Read `docs/TECH_STACK.md`
- All ADRs: Read `docs/adr/ADR_INDEX.md`
- Quick Refresh: Use Strategy 1 prompt above
- Deep Refresh: Use Strategy 3 prompt above
