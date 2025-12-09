# CONTEXT REFRESH MASTER GUIDE
**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Purpose:** Timeless guide for achieving FULL context refresh in any session
**Version:** 5.2 (Sprint-Independent, Reference-Based)
**Last Updated:** 2025-11-29 

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
1. CLAUDE.md - Projekt-Übersicht & Architektur (inkl. Subagent Responsibilities)
2. docs/NAMING_CONVENTIONS.md - Code Standards
3. README.md - Projekt-Status & Quick Start

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

## 🔄 REFRESH STRATEGY

### Deep Refresh (5-7 Minuten)

**Copy-Paste Prompt:**
```
🔄 DEEP CONTEXT REFRESH (VOLLSTÄNDIG)

Neue Session / Major Context Loss. Vollständiger Architektur-Context benötigt:

📋 PROJECT FOUNDATION:
1. README.md - Projekt-Überblick & Quick Start
2. CLAUDE.md - Vollständiger Projekt-Context (inkl. Subagent Responsibilities)
3. docs/ARCHITECTURE_EVOLUTION.md - Sprint Journey & Learnings
4. docs/sprints/SPRINT_PLAN.md - Master Sprint Plan

🏗️ ARCHITECTURE & TECH STACK:
5. docs/TECH_STACK.md - Complete stack

👥 WORKFLOW & STANDARDS:
6. docs/NAMING_CONVENTIONS.md - Code Standards

🎯 ADRs (Architecture Decisions):
7. docs/adr/ADR_INDEX.md - Alle ADRs mit Querverweisen
8. Relevante ADRs basierend auf aktuellem Sprint

📊 CURRENT SPRINT STATUS:
9. Neueste SPRINT_*_PLAN.md - Aktueller Sprint
10. Neueste SPRINT_*_SUMMARY.md - Sprint-Abschluss (falls completed)

Gib mir einen Executive Summary (7 Bulletpoints):
- Projekt-Ziel & Architektur (3-Layer Memory)
- Aktueller Sprint & Achievements
- Nächster Sprint Focus
- Key Architectural Patterns
- Tech Stack (Full-stack)
- Top 3 Immediate Priorities
```
---

## 📚 CORE DOCUMENTATION MAP

### Essential Reading (Always Read These)

| Document | What It Contains | Read When | Status |
|----------|------------------|-----------|--------|
| **CLAUDE.md** | Complete project context, architecture, workflows, subagent responsibilities | Every refresh | ✅ Auto-updated |
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

### Operations & Deployment

| Document | What It Contains | Read When | Status |
|----------|------------------|-----------|--------|
| **docs/operations/DGX_SPARK_DEPLOYMENT.md** | DGX Spark setup, containers (API vs Test), GPU config, testing | Deployment/Testing | ✅ Complete |

### File Reading Order (Deep Refresh)

```
Priority 1 (MUST READ - ALWAYS CURRENT):
1. README.md - Project status
2. CLAUDE.md - Full context
3. docs/sprints/SPRINT_PLAN.md - Sprint overview (check CURRENT sprint)
4. Latest SPRINT_*_PLAN.md - Current sprint details

Priority 2 (SHOULD READ - Architecture):
5. docs/TECH_STACK.md - Tech stack
6. docs/ARCHITECTURE_EVOLUTION.md - Sprint journey
7. docs/architecture/COMPONENT_INTERACTION_MAP.md - Data flows

Priority 3 (SHOULD READ - Workflow):
8. docs/NAMING_CONVENTIONS.md - Code standards
9. docs/adr/ADR_INDEX.md - Architecture decisions

```


**Referenced Documents (Auto-Updated):**
- **docs/CLAUDE.md** - Auto-updated with current sprint status
- **docs/sprints/SPRINT_PLAN.md** - Master plan, always current
- **docs/TECH_STACK.md** - Tech stack, dynamically updated
- **docs/adr/ADR_INDEX.md** - ADR index, growing list

**How to Find Current Sprint:**
1. Read `docs/sprints/SPRINT_PLAN.md` (look for "Current Sprint" section)
2. Find latest `SPRINT_N_PLAN.md` (highest N)

---

**Quick Access Commands:**
- Full Project Context: Read `CLAUDE.md` (inkl. Subagent Responsibilities)
- Current Sprint Status: Read `docs/sprints/SPRINT_PLAN.md`
- Architecture History: Read `docs/ARCHITECTURE_EVOLUTION.md`
- Tech Stack: Read `docs/TECH_STACK.md`
- All ADRs: Read `docs/adr/ADR_INDEX.md`
- Naming Standards: Read `docs/NAMING_CONVENTIONS.md`
