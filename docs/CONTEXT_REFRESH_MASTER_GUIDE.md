# CONTEXT REFRESH MASTER GUIDE
**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Purpose:** Complete guide for achieving FULL context refresh in any session
**Version:** 2.0 (Consolidated from all context refresh documentation)
**Last Updated:** 2025-10-22

---

## 📋 TABLE OF CONTENTS

1. [Quick Start](#quick-start) - Get context back in 1-5 minutes
2. [When to Refresh](#when-to-refresh) - Recognize the signs
3. [Three Refresh Strategies](#three-refresh-strategies) - Quick, Standard, Deep
4. [Current Project State](#current-project-state) - Where we are NOW
5. [Core Documentation Map](#core-documentation-map) - What to read
6. [Verification Checklist](#verification-checklist) - Confirm understanding
7. [Troubleshooting](#troubleshooting) - When refresh doesn't work
8. [Best Practices](#best-practices) - Optimize your workflow

---

## 🚀 QUICK START

### Copy-Paste This Prompt (Recommended for Most Cases)

```
🔄 CONTEXT REFRESH - AEGIS RAG

Bitte mach dich mit dem Projekt vertraut. Lies folgende Dateien:

📖 CORE CONTEXT:
1. CLAUDE.md - Projekt-Übersicht & Architektur
2. SUBAGENTS.md - Delegation Strategy & File Ownership
3. NAMING_CONVENTIONS.md - Code Standards

📊 CURRENT STATE:
4. SPRINT_12_COMPLETION_REPORT.md - Aktueller Stand (Sprint 12 abgeschlossen)
5. SPRINT_13_PLAN.md - Nächster Sprint (Test Infrastructure, 16 SP)
6. SPRINT_14_PLAN.md - Folgender Sprint (React Migration, 15 SP)

📚 DECISIONS & STANDARDS:
7. TECHNICAL_DEBT_SUMMARY.md - Bekannte Issues
8. README.md - Projekt-Überblick

Gib mir einen Executive Summary mit 5 Bulletpoints:
- Projekt-Ziel & Architektur
- Aktueller Sprint-Status
- Tech Stack & GPU Setup
- Nächste Prioritäten
- Wichtigste ADRs/Decisions
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
Context Refresh: Lies CLAUDE.md, SPRINT_13_PLAN.md, SUBAGENTS.md,
NAMING_CONVENTIONS.md. Bestätige kurz (3 Sätze).
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
1. CLAUDE.md - Projekt & Architektur
2. SPRINT_12_COMPLETION_REPORT.md - Sprint 12 Achievements
3. SPRINT_13_PLAN.md - Aktueller Sprint (Test Infrastructure, 16 SP)
4. SUBAGENTS.md - 5 Subagenten & File Ownership
5. NAMING_CONVENTIONS.md - Code Standards

📚 DECISIONS:
6. TECHNICAL_DEBT_SUMMARY.md - 22 Items (0 Critical, 9 Medium, 13 Low)
7. README.md - Sprint 12 Highlights

Bestätige mit Zusammenfassung (5 Bulletpoints):
- Projekt-Ziel
- Sprint-Status (12 Complete, 13 Planned)
- Tech Stack (FastAPI, LangGraph, Ollama, Qdrant, Neo4j, Redis)
- GPU Status (RTX 3060: 105 tokens/s)
- Top 3 Priorities
```

**What Gets Refreshed:**
- ✅ Vollständiger Projekt-Context
- ✅ Aktueller Sprint-Plan & Status
- ✅ Alle ADRs & Decisions
- ✅ Technical Debt Awareness
- ✅ Tech Stack & Versionen

**When to Use:**
- Nach größerer Kompaktierung
- Vor kritischen Tasks
- ADRs/Tech Stack unklar
- Session nach >1 Tag Pause

---

### Strategy 3: Deep Refresh (5 Minuten)

**Copy-Paste Prompt:**
```
🔄 DEEP CONTEXT REFRESH - VOLLSTÄNDIG

Neue Session / Major Context Loss. Vollständiger Sprint-Context benötigt:

📋 PROJECT FOUNDATION:
Lies in dieser Reihenfolge:
1. README.md - Projekt-Überblick & Sprint 12 Highlights
2. CLAUDE.md - Vollständiger Projekt-Context
3. docs/ARCHITECTURE_EVOLUTION.md - Sprint 1-12 Journey & Learnings
4. SPRINT_12_COMPLETION_REPORT.md - Sprint 12 Achievements (31/32 SP)
5. SPRINT_13_PLAN.md - Test Infrastructure & Performance (16 SP, 1-2 Wochen)
6. SPRINT_14_PLAN.md - React Migration Phase 1 (15 SP, 2 Wochen)

👥 WORKFLOW & STANDARDS:
7. SUBAGENTS.md - Delegation Strategy (5 Subagenten)
8. NAMING_CONVENTIONS.md - Complete Code Standards
9. docs/TESTING_STRATEGY.md - Test Pyramid, Fixtures, Sprint 13 Fixes
10. TECHNICAL_DEBT_SUMMARY.md - 22 Items (Post-Sprint 12)

🔧 TECHNICAL REFERENCE:
11. docs/COMPONENT_INTERACTION_MAP.md - Data Flows & API Contracts
12. docs/DECISION_LOG.md - Chronological Decision History
13. docs/DEPENDENCY_RATIONALE.md - Library Choice Justifications
14. docs/PRODUCTION_DEPLOYMENT_GUIDE.md - GPU Setup, Docker, K8s, Monitoring
15. docs/ADR_INDEX.md - 15 Architecture Decision Records

📊 SPRINT STATUS:
Sprint 12: ✅ COMPLETE (9/11 features, 31/32 SP)
- Feature 12.10: Production Deployment Guide ✅
- E2E Test Pass Rate: 17.9% → ~50% (2.8x improvement)
- 40 neue Tests (10 E2E + 30 Gradio UI)
- TD-23, TD-24, TD-25 resolved

Sprint 13: 🔵 PLANNED (Test Infrastructure & Performance, 16 SP)
- Features 13.1-13.3: Critical test fixes (7 SP)
- Features 13.4-13.5: CI/CD enhancements (4 SP)
- Features 13.6-13.8: Performance optimization (5 SP)
- Goal: 70%+ E2E test pass rate

Sprint 14: 🔵 PLANNED (React Migration Phase 1, 15 SP)
- Next.js 14 + TypeScript setup
- Chat UI + SSE streaming
- NextAuth.js authentication
- Tailwind CSS + dark mode

🎯 TECHNICAL STATE:
- Main Branch: sprint-10-dev archived, all features in main
- GPU: RTX 3060 verified (105 tokens/s, 52.7% VRAM)
- Backend: FastAPI + LangGraph + Ollama (100% local)
- RAG: Hybrid (Vector + Graph + BM25 with RRF)
- Memory: 3-Layer (Redis → Qdrant → Graphiti)

🎯 NÄCHSTE PRIORITÄTEN:
1. Sprint 13.1: Fix Memory Agent Event Loop Errors (TD-26)
2. Sprint 13.2: Fix Graphiti API Compatibility (TD-27)
3. Sprint 13.3: Fix LightRAG Fixture Connection (TD-28)

Gib mir einen Executive Summary (5-7 Bulletpoints):
- Projekt-Ziel & Architektur (4 Core-Komponenten)
- Sprint 12 Achievements
- Sprint 13 Focus & Story Points
- Sprint 14 Preview
- Tech Stack (Python 3.11+, FastAPI, LangGraph, Ollama, etc.)
- GPU Performance (RTX 3060)
- Top 3 Immediate Priorities
```

**What Gets Refreshed:**
- ✅ COMPLETE Project Context (all 4 core components)
- ✅ Full Sprint History (10-12 complete, 13-14 planned)
- ✅ All Architecture Decisions
- ✅ Complete Tech Stack & Dependencies
- ✅ Technical Debt Status
- ✅ GPU & Performance Metrics
- ✅ Production Deployment Knowledge

**When to Use:**
- Montag-Morgen / Wochenstart
- Nach langer Pause (>3 Tage)
- Major Context Loss (kompletter Reset)
- Team-Übergabe
- Sprint-Start

---

## 📊 CURRENT PROJECT STATE (As of 2025-10-22)

### Project Overview
**Name:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Purpose:** Hybrid Retrieval-Augmented Generation system for Bundeswehr
**Status:** Production-ready (Sprint 12 complete)

### Architecture (4 Core Components)
1. **Vector Search** - Qdrant + Ollama embeddings (nomic-embed-text)
2. **Graph RAG** - LightRAG + Graphiti (bi-temporal memory)
3. **Temporal Memory** - 3-Layer (Redis → Qdrant → Graphiti)
4. **Tool Integration** - MCP protocol for external services

### Tech Stack
```yaml
Backend:
  - Python: 3.11+
  - Framework: FastAPI 0.115.6
  - Orchestration: LangGraph 0.2.53
  - LLM: Ollama (llama3.2:3b/8b, qwen2.5:7b)
  - Embeddings: nomic-embed-text (768d)

Databases:
  - Vector: Qdrant 1.12.1
  - Graph: Neo4j 5.24-community
  - Memory: Redis 7.4-alpine

RAG Frameworks:
  - LightRAG: EMNLP 2025 graph RAG
  - Graphiti: Bi-temporal episodic memory
  - BM25: Keyword search with RRF fusion

Infrastructure:
  - Docker: docker-compose.yml
  - CI/CD: GitHub Actions (10 parallel jobs)
  - GPU: NVIDIA RTX 3060 (105 tokens/s)
```

### Sprint Status

**Sprint 12: ✅ COMPLETE (2025-10-22)**
- **Delivered:** 9/11 features, 31/32 SP (97% complete)
- **Highlights:**
  - Production Deployment Guide (800+ lines)
  - E2E test pass rate: 17.9% → ~50% (2.8x improvement)
  - 40 neue Tests (10 E2E + 30 Gradio UI)
  - 3 Technical Debt items resolved (TD-23, TD-24, TD-25)
  - GPU benchmarking (RTX 3060: 105 tokens/s verified)
  - Graph visualization API (4 endpoints)
- **New Technical Debt:** TD-26 (Memory Agent), TD-27 (Graphiti API), TD-28 (LightRAG), TD-29 (pytest-timeout)

**Sprint 13: 🔵 PLANNED (Test Infrastructure & Performance Optimization)**
- **Duration:** 1-2 weeks
- **Story Points:** 16 SP
- **Theme:** Backend Excellence - Testing & Performance
- **Features:**
  - 13.1: Fix Memory Agent Event Loop Errors (2 SP) - TD-26
  - 13.2: Fix Graphiti API Compatibility (3 SP) - TD-27
  - 13.3: Fix LightRAG Fixture Connection (2 SP) - TD-28
  - 13.4: Add pytest-timeout Plugin (1 SP) - TD-29
  - 13.5: CI/CD Pipeline Enhancements (3 SP)
  - 13.6: Community Detection Caching (2 SP)
  - 13.7: LLM Labeling Batching (2 SP)
  - 13.8: Cache Invalidation Patterns (1 SP)
- **Goal:** 70%+ E2E test pass rate

**Sprint 14: 🔵 PLANNED (React Frontend Migration Phase 1)**
- **Duration:** 2 weeks
- **Story Points:** 15 SP
- **Theme:** Frontend Excellence - Modern React Architecture
- **Features:**
  - 14.1: React Project Setup (Next.js 14) - 2 SP
  - 14.2: Basic Chat UI Component - 3 SP
  - 14.3: Server-Sent Events Streaming - 3 SP
  - 14.4: NextAuth.js Authentication - 3 SP
  - 14.5: Tailwind CSS Styling System - 2 SP
  - 14.6: Document Upload UI - 2 SP
- **Goal:** Production-ready React frontend replacing Gradio

### Technical Debt Summary (Post-Sprint 12)
**Total Items:** 22 (0 Critical, 0 High, 9 Medium, 13 Low)

**New in Sprint 12:**
- **TD-26** (Medium): Memory Agent Event Loop Errors (4 tests)
- **TD-27** (Critical → to be reclassified): Graphiti API Compatibility (18 tests)
- **TD-28** (Critical → to be reclassified): LightRAG Fixture Connection (5 tests)
- **TD-29** (Low): pytest-timeout not installed

**Resolved in Sprint 12:**
- ✅ TD-23: LightRAG E2E tests (5 tests fixed)
- ✅ TD-24: Graphiti method renamed (14 tests unblocked)
- ✅ TD-25: Redis async cleanup (0 warnings)

### GPU Performance (Verified)
```
Device: NVIDIA RTX 3060
VRAM: 12GB (52.7% utilized @ peak)
Speed: 105 tokens/s (llama3.2:3b)
Speedup: 15-20x vs CPU
Status: ✅ Production-ready
```

### Recent Commits (Last 4)
```bash
63283f3 docs: Reorganize documentation and add Sprint 11/12 completion reports
6f7fb9e docs(sprints): Split Sprint 13 into two focused sprints
fd5a6d4 docs(sprint12): Add Sprint 12 Completion Report and Sprint 13 Plan
b31d1e9 feat(sprint12): Complete Feature 12.10 and finalize Sprint 12 (31/32 SP)
```

### Branch Status
- **Current Branch:** main
- **Archived Branches:** sprint-10-dev (tag: archive/sprint-10-dev)
- **Status:** Clean (all sprint-10-dev features already in main)

---

## 📚 CORE DOCUMENTATION MAP

### Essential Reading (Always Read These)

| Document | What It Contains | Read When |
|----------|------------------|-----------|
| **CLAUDE.md** | Complete project context, architecture, workflows | Every refresh |
| **SUBAGENTS.md** | 5 subagents, file ownership, delegation rules | Every refresh |
| **NAMING_CONVENTIONS.md** | snake_case, PascalCase, SCREAMING_SNAKE rules | Every refresh |

### Sprint Planning & Status

| Document | What It Contains | Read When |
|----------|------------------|-----------|
| **SPRINT_12_COMPLETION_REPORT.md** | Sprint 12 achievements, metrics, lessons learned | Standard/Deep refresh |
| **SPRINT_13_PLAN.md** | Test Infrastructure plan (16 SP, 1-2 weeks) | Standard/Deep refresh |
| **SPRINT_14_PLAN.md** | React Migration plan (15 SP, 2 weeks) | Deep refresh |
| **SPRINT_10_PLAN.md** | Historical reference (Sprint 10) | Reference only |
| **SPRINT_11_COMPLETION_REPORT.md** | Historical reference (Sprint 11) | Reference only |

### Technical Reference

| Document | What It Contains | Read When |
|----------|------------------|-----------|
| **README.md** | Projekt-Überblick, Sprint 12 highlights, setup | Standard/Deep refresh |
| **TECHNICAL_DEBT_SUMMARY.md** | 22 items, severity, resolution plans | Standard/Deep refresh |
| **docs/PRODUCTION_DEPLOYMENT_GUIDE.md** | GPU setup, Docker, K8s, monitoring, security | Before deployment work |
| **docs/ADR_INDEX.md** | Architecture Decision Records (15 ADRs) | Before architectural changes |
| **docs/TECH_STACK.md** | Versions, dependencies, configs | When tech questions arise |

### Architecture & Deep Understanding (NEW - Sprint 12)

| Document | What It Contains | Read When |
|----------|------------------|-----------|
| **docs/ARCHITECTURE_EVOLUTION.md** | Sprint 1-12 journey, architecture milestones, learnings | Deep refresh, new developers |
| **docs/COMPONENT_INTERACTION_MAP.md** | Data flows, API contracts, request scenarios | Understanding system behavior |
| **docs/TESTING_STRATEGY.md** | Test pyramid, fixtures, async patterns, Sprint 13 fixes | Before writing tests, Sprint 13 work |
| **docs/DECISION_LOG.md** | Chronological decision history (Sprint 1-12) | Understanding "why" decisions |
| **docs/DEPENDENCY_RATIONALE.md** | Library choice justifications (60+ dependencies) | Before changing dependencies |

### Helper Documentation

| Document | What It Contains | Read When |
|----------|------------------|-----------|
| **docs/CONTEXT_REFRESH.md** | Detailed refresh strategies | Troubleshooting refresh |
| **docs/CONTEXT_REFRESH_CHEATSHEET.txt** | Quick reference ASCII art | Quick lookup |
| **docs/CONTEXT_REFRESH_SPRINT2_COMPLETE.md** | Historical Sprint 2 example | Reference only |
| **docs/GIT_COMMIT_COMMANDS.md** | Git workflow commands | Before commits |
| **docs/CHANGELOG_OLLAMA_MIGRATION.md** | Ollama migration history | Historical reference |

### File Reading Order (Deep Refresh)

```
Priority 1 (MUST READ):
1. README.md
2. CLAUDE.md
3. SPRINT_12_COMPLETION_REPORT.md
4. SPRINT_13_PLAN.md

Priority 2 (SHOULD READ):
5. SUBAGENTS.md
6. NAMING_CONVENTIONS.md
7. TECHNICAL_DEBT_SUMMARY.md
8. SPRINT_14_PLAN.md

Priority 3 (OPTIONAL):
9. docs/PRODUCTION_DEPLOYMENT_GUIDE.md
10. ADR documents (if task-specific)
```

---

## ✅ VERIFICATION CHECKLIST

After ANY refresh, Claude Code should be able to confirm:

### ✅ PROJECT CONTEXT
```
- [ ] Projekt-Name: AEGIS RAG (Agentic Enterprise Graph Intelligence System)
- [ ] Purpose: Hybrid RAG for Bundeswehr
- [ ] 4 Core-Komponenten: Vector Search, Graph RAG, Temporal Memory, MCP Tools
- [ ] Status: Production-ready (Sprint 12 complete)
```

### ✅ ARCHITECTURE
```
- [ ] Hybrid Retrieval: Vector (Qdrant) + Graph (LightRAG/Graphiti) + BM25
- [ ] 3-Layer Memory: Redis (short-term) → Qdrant (semantic) → Graphiti (episodic)
- [ ] Orchestration: LangGraph with multi-agent state management
- [ ] LLM Strategy: 100% local (Ollama), zero API costs
- [ ] Fusion: Reciprocal Rank Fusion (RRF) for result merging
```

### ✅ TECH STACK
```
- [ ] Backend: Python 3.11+, FastAPI 0.115.6
- [ ] Orchestration: LangGraph 0.2.53
- [ ] LLMs: Ollama (llama3.2:3b/8b, qwen2.5:7b)
- [ ] Embeddings: nomic-embed-text (768d)
- [ ] Vector DB: Qdrant 1.12.1
- [ ] Graph DB: Neo4j 5.24-community
- [ ] Memory: Redis 7.4-alpine
- [ ] GPU: NVIDIA RTX 3060 (105 tokens/s verified)
```

### ✅ SPRINT STATUS
```
- [ ] Sprint 12: ✅ COMPLETE (9/11 features, 31/32 SP, 97%)
- [ ] Sprint 13: 🔵 PLANNED (Test Infrastructure, 16 SP, 1-2 weeks)
- [ ] Sprint 14: 🔵 PLANNED (React Migration, 15 SP, 2 weeks)
- [ ] Current Branch: main
- [ ] sprint-10-dev: archived (all features already in main)
```

### ✅ WORKFLOW & STANDARDS
```
- [ ] 5 Subagenten: test-engineer, langgraph-specialist, graphiti-specialist,
                   lightrag-specialist, general-backend-dev
- [ ] File Ownership: Subagenten mapped to file patterns
- [ ] Naming Conventions:
      - Functions/variables: snake_case
      - Classes: PascalCase
      - Constants: SCREAMING_SNAKE_CASE
      - Test files: test_*.py
      - Fixtures: conftest.py
- [ ] 1 Feature = 1 Commit workflow
```

### ✅ TECHNICAL DEBT
```
- [ ] Total Items: 22 (0 Critical, 0 High, 9 Medium, 13 Low)
- [ ] Sprint 13 Targets: TD-26, TD-27, TD-28, TD-29
- [ ] Sprint 12 Resolved: TD-23, TD-24, TD-25
```

### ✅ PRIORITIES (Next Steps)
```
- [ ] Immediate: Sprint 13 Feature 13.1 (Memory Agent Event Loop)
- [ ] Next: Sprint 13 Feature 13.2 (Graphiti API Compatibility)
- [ ] Then: Sprint 13 Feature 13.3 (LightRAG Fixture Connection)
```

---

## 🆘 TROUBLESHOOTING

### Problem: Refresh doesn't help

**Symptoms:** Claude still doesn't understand project after refresh

**Solutions:**
1. Check if all docs are up-to-date: `git pull origin main`
2. Verify you're reading correct sprint plan (Sprint 13, not older)
3. Use Deep Refresh (Strategy 3) instead of Quick/Standard
4. Check if CLAUDE.md was recently updated
5. Ask user to verify which files are most critical

---

### Problem: Sprint-Nummer unclear

**Symptoms:** "Sprint {N}" not replaced correctly

**Solutions:**
1. Replace `{N}` manually with **13** in all prompts
2. Be explicit: "Sprint 13" not "Sprint {N}"
3. Read SPRINT_13_PLAN.md (current), not SPRINT_12_PLAN.md (historical)
4. Verify sprint status in SPRINT_12_COMPLETION_REPORT.md

---

### Problem: Too many refreshes needed

**Symptoms:** >5 refreshes per Sprint, context loss <15 messages

**Solutions:**
1. **Short-term:** Increase refresh frequency (every 15 messages)
2. **Medium-term:** Update CLAUDE.md with frequently forgotten info
3. **Long-term:** Keep sessions shorter (<100 messages)
4. **Best Practice:** Proactive Quick Checks every 20-30 messages

---

### Problem: Specific detail always forgotten

**Symptoms:** Same info (e.g., GPU specs, tech versions) forgotten repeatedly

**Solutions:**
1. Add to CLAUDE.md at the very top
2. Create dedicated section in CLAUDE.md for this info
3. Include in Quick Refresh prompt explicitly
4. Add to Verification Checklist

---

### Problem: Doesn't know which docs exist

**Symptoms:** "I don't see file X" but file exists

**Solutions:**
1. Use this guide's [Core Documentation Map](#core-documentation-map)
2. Run `ls -la` to see all files in root
3. Run `ls -la docs/` to see all docs
4. Check git status: `git status`
5. Read README.md first (has file overview)

---

## 🎯 BEST PRACTICES

### DO ✅

```
✅ Context Refresh bei JEDEM Zeichen von Context Loss
✅ Quick Check alle 20-30 Nachrichten in langen Sessions
✅ Standard Refresh am Session-Start (nach >1 Tag Pause)
✅ Deep Refresh am Montag / Sprint-Start
✅ Dokumentiere was vergessen wurde → Update CLAUDE.md
✅ Nutze die Copy-Paste Prompts aus diesem Guide
✅ Bestätige Verständnis mit Verification Checklist
✅ Lies Docs in der empfohlenen Reihenfolge (Priority 1 → 2 → 3)
```

### DON'T ❌

```
❌ Weitermachen wenn Naming Conventions ignoriert werden
❌ Hoffen dass Context "von selbst zurückkommt"
❌ Zu viele Details in Refresh (ineffizient, Overload)
❌ Quick Refresh bei Major Context Loss (nutze Deep Refresh!)
❌ Alte Sprint Plans lesen (z.B. Sprint 10 statt Sprint 13)
❌ Vergessen Sprint-Nummer zu ersetzen ({N} → 13)
❌ CLAUDE.md skippen (immer lesen!)
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

### Quality Metrics (Good Session)

```
✅ <3 Context Refreshes pro Sprint
✅ Keine Naming Violations nach Refresh
✅ Subagenten konsequent genutzt
✅ ADRs werden referenziert
✅ Tech Stack korrekt (Python 3.11+, FastAPI, etc.)
✅ Sprint-Ziele klar
```

### Quality Metrics (Needs Improvement)

```
⚠️ >5 Refreshes pro Sprint
⚠️ Violations trotz Refresh
⚠️ Context Loss innerhalb 15 Messages
⚠️ Sprint-Nummer falsch
⚠️ GPU specs vergessen (RTX 3060: 105 tokens/s)
```

---

## 🔄 QUICK DECISION TREE

```
┌─────────────────────────────────────────────┐
│ Habe ich Context Loss?                      │
└─────────────────────────────────────────────┘
           │
           ├─ JA → Was fehlt?
           │        │
           │        ├─ Naming/Subagenten              → Quick Refresh (1 Min)
           │        ├─ ADRs/Tech Stack                → Standard Refresh (2 Min)
           │        ├─ Sprint-Ziel/Kompletter Context → Deep Refresh (5 Min)
           │        └─ Unsicher                       → Standard Refresh
           │
           └─ NEIN → Weiter arbeiten
                     │
                     └─ Alle 20-30 Messages: Quick Check
                        "Sprint 13 klar? Subagenten OK? Naming OK?"
```

---

## 🔔 PROACTIVE CHECKS (Checklist)

Copy-paste these into chat at appropriate times:

### Every 20-30 Messages (Long Sessions)
```
Quick Check: Sprint 13 noch klar? Subagenten-Delegation OK?
Naming Conventions (snake_case) befolgt? Falls unsicher → Quick Refresh.
```

### Before Critical Tasks
```
Context Check: Lies nochmal CLAUDE.md Section "Architecture"
und SPRINT_13_PLAN.md Feature 13.X für diese Task.
```

### After Kompaktierung (Always)
```
Minimum: Quick Refresh (Strategy 1)
Falls Major Kompaktierung: Standard Refresh (Strategy 2)
```

### Monday / Sprint-Start
```
Deep Refresh (Strategy 3) durchführen.
Verify: Sprint 12 complete, Sprint 13 planned.
```

### Team-Übergabe
```
Developer B nutzt Deep Refresh (Strategy 3).
Liest zusätzlich: Letzter PR, aktuelle Branch, Sprint Status.
Developer A gibt Verbal Briefing.
```

---

## 📊 CONTEXT QUALITY TRACKING

### Metrics to Self-Monitor

```yaml
Session Quality Indicators:
  context_refreshes_per_session: <count>      # Target: <3
  naming_violations_after_refresh: <count>     # Target: 0
  subagent_delegation_accuracy: <percentage>   # Target: >90%
  time_to_first_context_loss: <minutes>       # Target: >30

Good Session:
  - 0-2 refreshes
  - 0 violations post-refresh
  - Consistent subagent use
  - ADRs referenced

Needs Improvement:
  - >5 refreshes
  - Violations persist
  - Context loss <15 messages
```

---

## 🎓 LESSONS LEARNED (From Past Sprints)

### What Works Well
1. **Feature-Based Development:** 1 Feature = 1 Commit (excellent tracking)
2. **Proactive Refreshes:** Every 20-30 messages prevents major loss
3. **Deep Refresh on Mondays:** Starts week with full context
4. **Copy-Paste Prompts:** Saves time, ensures consistency
5. **Verification Checklist:** Confirms understanding objectively

### Common Pitfalls
1. **Skipping CLAUDE.md:** Always leads to confusion later
2. **Reading Old Sprint Plans:** Sprint 10 vs Sprint 13 confusion
3. **Not Replacing {N}:** Template placeholders cause errors
4. **Too Brief Refresh:** Quick Refresh insufficient for Major Loss
5. **Ignoring Early Signals:** Naming violations = immediate refresh needed

### Key Insights
1. **Context Refresh is Normal:** Not a bug, it's how the system works
2. **2 Minutes >> 30 Minutes:** Refreshing faster than debugging wrong context
3. **Proactive > Reactive:** Quick Checks prevent major loss
4. **Documentation Quality Matters:** Good CLAUDE.md = fewer refreshes needed
5. **Sprint Plans Change:** Always read LATEST sprint plan, not historical

---

## 📞 HELP & RESOURCES

### If This Guide Doesn't Help

1. **Check Git Status:** `git status` - Are you on main branch?
2. **Pull Latest:** `git pull origin main` - Docs up-to-date?
3. **List Files:** `ls -la` - Which files actually exist?
4. **Ask User:** "Which specific context am I missing?"
5. **Read This Guide Again:** Section-by-section, verify each checklist

### Related Documentation

- **Full Refresh Details:** [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md)
- **Quick Reference:** [docs/CONTEXT_REFRESH_CHEATSHEET.txt](docs/CONTEXT_REFRESH_CHEATSHEET.txt)
- **Sprint 2 Example:** [docs/CONTEXT_REFRESH_SPRINT2_COMPLETE.md](docs/CONTEXT_REFRESH_SPRINT2_COMPLETE.md)
- **Project Overview:** [README.md](README.md)
- **Main Context:** [CLAUDE.md](CLAUDE.md)

---

## 🎯 FINAL CHECKLIST (Post-Refresh)

Before continuing work, verify:

```
✅ I know: AEGIS RAG = Hybrid RAG for Bundeswehr
✅ I know: 4 Core Components (Vector, Graph, Memory, MCP)
✅ I know: Sprint 12 COMPLETE (9/11, 31/32 SP)
✅ I know: Sprint 13 PLANNED (Test Infrastructure, 16 SP)
✅ I know: Sprint 14 PLANNED (React Migration, 15 SP)
✅ I know: Tech Stack (FastAPI, LangGraph, Ollama, Qdrant, Neo4j, Redis)
✅ I know: GPU Verified (RTX 3060: 105 tokens/s)
✅ I know: 5 Subagenten & their file ownership
✅ I know: Naming conventions (snake_case, PascalCase, SCREAMING_SNAKE)
✅ I know: Technical Debt (22 items, 4 in Sprint 13)
✅ I know: Next Priority (Sprint 13.1: Memory Agent Event Loop)
✅ I know: Main branch clean, sprint-10-dev archived
```

**If ANY checkbox unchecked → Perform Standard or Deep Refresh!**

---

## 💡 REMEMBER

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║  Context Refresh ist NORMAL und WICHTIG!                       ║
║                                                                ║
║  Besser 2-5 Minuten für vollständigen Context investieren      ║
║  als 30-60 Minuten mit suboptimalem/falschem Context arbeiten. ║
║                                                                ║
║                    Happy Coding! 🚀                            ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

**Document Version:** 2.0 (Master Consolidation)
**Created:** 2025-10-22
**Project:** AEGIS RAG
**Current Sprint:** Sprint 13 (Planned)
**Last Updated:** Post-Sprint 12 Completion

**Quick Access Commands:**
- Full Project Context: Read CLAUDE.md
- Current Sprint: Read SPRINT_13_PLAN.md
- Sprint Status: Read SPRINT_12_COMPLETION_REPORT.md
- Technical Debt: Read TECHNICAL_DEBT_SUMMARY.md
- Quick Refresh: Use Strategy 1 prompt above
- Deep Refresh: Use Strategy 3 prompt above
