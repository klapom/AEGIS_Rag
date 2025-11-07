# CONTEXT REFRESH MASTER GUIDE
**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Purpose:** Complete guide for achieving FULL context refresh in any session
**Version:** 4.0 (Sprint 16 COMPLETE, Documentation Consolidated)
**Last Updated:** 2025-10-28

---

## 📋 TABLE OF CONTENTS

1. [Quick Start](#quick-start) - Get context back in 1-5 minutes
2. [When to Refresh](#when-to-refresh) - Recognize the signs
3. [Three Refresh Strategies](#three-refresh-strategies) - Quick, Standard, Deep
4. [Current Project State](#current-project-state) - Where we are NOW
5. [Core Documentation Map](#core-documentation-map) - What to read
6. [Verification Checklist](#verification-checklist) - Confirm understanding
7. [Best Practices](#best-practices) - Optimize your workflow

---

## 🚀 QUICK START

### Copy-Paste This Prompt (Recommended for Most Cases)

```
🔄 CONTEXT REFRESH - AEGIS RAG (Sprint 17 Ready)

Bitte mach dich mit dem Projekt vertraut. Lies folgende Dateien:

📖 CORE CONTEXT:
1. docs/CLAUDE.md - Projekt-Übersicht & Architektur
2. docs/SUBAGENTS.md - Delegation Strategy & File Ownership
3. docs/NAMING_CONVENTIONS.md - Code Standards
4. docs/core/PROJECT_SUMMARY.md - Projekt-Status (515/584 SP, 88.2%)

📊 CURRENT STATE:
5. docs/sprints/SPRINT_PLAN.md - Sprint-Übersicht (1-17)
6. docs/sprints/SPRINT_16_COMPLETION_REPORT.md - Sprint 16: 100% COMPLETE
7. docs/sprints/SPRINT_17_PLAN.md - Sprint 17: Admin UI (39 SP, BEREIT)

📚 UPDATED DOCUMENTATION:
8. docs/TECH_STACK.md - Tech Stack inkl. Sprint 16 Updates
9. docs/ARCHITECTURE_EVOLUTION.md - Sprint 1-16 Journey
10. docs/COMPONENT_INTERACTION_MAP.md - Unified Re-Indexing Flow

Gib mir einen Executive Summary mit 5 Bulletpoints:
- Projekt-Ziel & 3-Layer Architektur
- Sprint 16 COMPLETE (69/69 SP): Unified Chunking, BGE-M3, Re-Indexing
- Sprint 17 READY: Admin UI für Directory Indexing (13 SP Priorität)
- Tech Stack (React 18.2, FastAPI, LangGraph, BGE-M3 1024-dim)
- Wichtigste ADRs (ADR-022: Chunking, ADR-023: Re-Indexing, ADR-024: BGE-M3)
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
Context Refresh: Lies docs/CLAUDE.md, docs/core/SPRINT_PLAN.md (Sprint 16),
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
🔄 STANDARD CONTEXT REFRESH (Sprint 16)

Bitte reaktiviere vollständigen Projekt-Context:

📖 CORE:
1. docs/CLAUDE.md - Projekt & Architektur
2. docs/core/SPRINT_PLAN.md - 
3. docs/SUBAGENTS.md - 5 Subagenten & File Ownership
4. docs/NAMING_CONVENTIONS.md - Code Standards

📚 TECH & DECISIONS:
5. docs/TECH_STACK.md - React 18.2, FastAPI, LangGraph
6. docs/TECHNICAL_DEBT_SUMMARY.md - Current status
7. README.md - Project overview

Bestätige mit Zusammenfassung (5 Bulletpoints):
- Projekt-Ziel & 3-Layer Architecture
- Tech Stack Updates
- Next Priority 
- Key ADRs 
```

**What Gets Refreshed:**
- ✅ Vollständiger Projekt-Context
- ✅ Aktueller Sprint-Plan & Status
- ✅ Tech Stack & Recent Updates
- ✅ Subagent Workflow

**When to Use:**
- Nach größerer Kompaktierung
- Vor kritischen Tasks
- Session nach >1 Tag Pause

---

### Strategy 3: Deep Refresh (5-7 Minuten)

**Copy-Paste Prompt:**
```
🔄 DEEP CONTEXT REFRESH - Sprint 16 (VOLLSTÄNDIG)

Neue Session / Major Context Loss. Vollständiger Architektur-Context benötigt:

📋 PROJECT FOUNDATION:
1. README.md - Projekt-Überblick & Sprint Status
2. docs/CLAUDE.md - Vollständiger Projekt-Context
3. docs/ARCHITECTURE_EVOLUTION.md - Sprint 1-N Journey & Learnings
4. docs/core/SPRINT_PLAN.md - Sprint Plan

🏗️ ARCHITECTURE & TECH STACK:
5. docs/TECH_STACK.md - Complete stack with Sprint additions
6. docs/architecture/COMPONENT_INTERACTION_MAP.md - Data flows & API contracts
7. docs/DEPENDENCY_RATIONALE.md - Library choice justifications
8. docs/architecture/LIGHTRAG_VS_GRAPHITI.md - Layer 2 vs Layer 3 comparison

👥 WORKFLOW & STANDARDS:
9.  docs/SUBAGENTS.md - Delegation Strategy
10. docs/NAMING_CONVENTIONS.md - Code Standards
11. docs/TECHNICAL_DEBT_SUMMARY.md - Current TD status

🎯 ADRs (Architecture Decisions):
12. docs/adr/ADR*.md 

📊 SPRINT STATUS:
13. Check for ***LATEST*** SPRINT files SPRINT_*PLAN.md or  SPRINT_*SUMMARY.md or SPRINT_*TEST*.md  

🎯 TECHNICAL STATE (Post-Sprint 15):
- GPU: RTX 3060 verified 
- Backend: FastAPI + LangGraph + Ollama (100% local)
- Frontend: React 18.2 + Vite 7.1 + Tailwind CSS v4.1
- RAG: Hybrid (Vector + Graph + BM25 with RRF)
- Memory: 3-Layer (Redis → Qdrant → Graphiti)
- Extraction: Three-Phase Pipeline (SpaCy + Semantic Dedup + Gemma 2 4B)

🎯 NÄCHSTE PRIORITÄTEN:
14. Check for ***LATEST*** SPRINT files SPRINT_*PLAN.md or  SPRINT_*SUMMARY.md or SPRINT_*TEST*.md  

Gib mir einen Executive Summary (7 Bulletpoints):
- Projekt-Ziel & Architektur (3-Layer Memory)
- LATEST Sprint  Achievements 
- Sprint N Focus 
- Key Architectural Issues 
- Tech Stack (Full-stack)
- Top 3 Immediate Priorities
```

**What Gets Refreshed:**
- ✅ COMPLETE Project Context
- ✅ Full Sprint History (Last 6 Sprints)
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

## 📊 CURRENT PROJECT STATE (As of 2025-10-28)

### Project Overview
**Name:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Purpose:** Enterprise-grade Hybrid Retrieval-Augmented Generation system
**Status:** Production-ready frontend + backend (Sprint 15 complete)

### Architecture (3-Layer Memory)
1. **Layer 1 (Redis):** Short-term memory (conversation context)
2. **Layer 2 (Qdrant + BM25 + LightRAG):** Semantic search + keyword search + graph retrieval
3. **Layer 3 (Graphiti):** Episodic memory (temporal queries, communities)

### Tech Stack (Post-Sprint 15)
```yaml
Frontend (Sprint 15):
  - React: 18.2.0
  - TypeScript: 5.9.0
  - Vite: 7.1.0
  - Tailwind CSS: 4.1.0 (v4 syntax: @import)
  - React Router: 7.9.2
  - Zustand: 5.0.3 (state management)
  - SSE: Native EventSource API

Backend:
  - Python: 3.12+
  - Framework: FastAPI 0.115.6
  - Orchestration: LangGraph 0.2.53
  - LLM: Ollama (llama3.2:3b/8b, qwen2.5:7b, gemma2:4b)
  - Embeddings: nomic-embed-text (768d) + BGE-M3 (1024d for Graphiti)

Databases:
  - Vector: Qdrant 1.12.1
  - Graph: Neo4j 5.24-community
  - Memory: Redis 7.4-alpine

Extraction (Sprint 13):
  - SpaCy: en_core_web_lg (NER)
  - Sentence-Transformers: all-MiniLM-L6-v2 (dedup)
  - Gemma 2 4B: Quantized (Q4_K_M) relation extraction
  - FAISS: IndexFlatL2 (384-dim)

Infrastructure:
  - Docker: docker-compose.yml
  - CI/CD: GitHub Actions
  - GPU: NVIDIA RTX 3060 (105 tokens/s)
```


## 📚 CORE DOCUMENTATION MAP

### Essential Reading (Always Read These)

| Document | What It Contains | Read When |
|----------|------------------|-----------|
| **docs/CLAUDE.md** | Complete project context, architecture, workflows | Every refresh |
| **docs/SUBAGENTS.md** | 5 subagents, file ownership, delegation rules | Every refresh |
| **docs/NAMING_CONVENTIONS.md** | snake_case, PascalCase, SCREAMING_SNAKE rules | Every refresh |

### Sprint Planning & Status

| Document | What It Contains | Read When |
|----------|------------------|-----------|
| **docs/core/SPRINT_PLAN.md** | Master sprint plan (Sprints 1-16), current Sprint 16 | Standard/Deep refresh |

### Architecture & Deep Understanding (MUST READ for Deep Refresh)

| Document | What It Contains | Read When |
|----------|------------------|-----------|
| **docs/ARCHITECTURE_EVOLUTION.md** | Sprint 1-15 journey, learnings, architectural decisions | Deep refresh |
| **docs/TECH_STACK.md** | Complete tech stack with Sprint 12-15 additions | Standard/Deep refresh |
| **docs/architecture/COMPONENT_INTERACTION_MAP.md** | Data flows, API contracts, request scenarios | Deep refresh |
| **docs/DEPENDENCY_RATIONALE.md** | Library choice justifications (70+ dependencies) | Deep refresh |
| **docs/architecture/LIGHTRAG_VS_GRAPHITI.md** | Layer 2 vs Layer 3 comparison (NEW - Sprint 16) | Deep refresh |

### Technical Reference

| Document | What It Contains | Read When |
|----------|------------------|-----------|
| **docs/TECHNICAL_DEBT_SUMMARY.md** | Current TD status | Standard/Deep refresh |
| **docs/adr/** | Architecture Decision Records (23 ADRs) | Task-specific |
| **docs/ADR_INDEX.md** | ADR index and quick reference | Before architectural changes |

### File Reading Order (Deep Refresh)

```
Priority 1 (MUST READ):
1. README.md
2. docs/CLAUDE.md
3. docs/core/SPRINT_PLAN.md (Sprint 16)
4. docs/TECH_STACK.md

Priority 2 (SHOULD READ - Architecture):
5. docs/ARCHITECTURE_EVOLUTION.md
6. docs/architecture/COMPONENT_INTERACTION_MAP.md
7. docs/DEPENDENCY_RATIONALE.md
8. docs/architecture/LIGHTRAG_VS_GRAPHITI.md

Priority 3 (SHOULD READ - Workflow):
9. docs/SUBAGENTS.md
10. docs/NAMING_CONVENTIONS.md
11. docs/TECHNICAL_DEBT_SUMMARY.md

Priority 4 (OPTIONAL - Task-Specific):
12. docs/adr/ADR-022-unified-chunking-service.md
13. docs/adr/ADR-023-unified-reindexing-pipeline.md
14. Specific ADRs based on task
```

---

## ✅ VERIFICATION CHECKLIST

After ANY refresh, Claude Code should be able to confirm:

### ✅ PROJECT CONTEXT
```
- [ ] Projekt-Name: AEGIS RAG (Agentic Enterprise Graph Intelligence System)
- [ ] Purpose: Enterprise-grade Hybrid RAG
- [ ] 3-Layer Memory: Redis → Qdrant/BM25/LightRAG → Graphiti
- [ ] Status: Sprint N complete, Sprint N+1 planned or in progress
```

### ✅ ARCHITECTURE
```
- [ ] Layer 1: Redis (short-term memory)
- [ ] Layer 2: Qdrant (vector) + BM25 (keyword) + LightRAG (graph) - CHUNK-BASED
- [ ] Layer 3: Graphiti (episodic memory) - EPISODE-BASED (different data model!)
- [ ] Orchestration: LangGraph with multi-agent state management
- [ ] LLM Strategy: 100% local (Ollama), zero API costs
```

### ✅ TECH STACK
```
- [ ] Frontend: React 18.2, TypeScript 5.9, Vite 7.1, Tailwind CSS v4.1
- [ ] Backend: Python 3.12+, FastAPI 0.115.6
- [ ] Orchestration: LangGraph 0.2.53
- [ ] LLMs: Ollama (llama3.2:3b/8b, qwen2.5:7b, gemma2:4b)
- [ ] Embeddings: nomic-embed-text (768d) + BGE-M3 (1024d for Graphiti)
- [ ] Vector: Qdrant 1.12.1
- [ ] Graph: Neo4j 5.24-community
- [ ] Memory: Redis 7.4-alpine
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
✅ Lies ARCHITECTURE_EVOLUTION.md für vollständigen Context
✅ Lies TECH_STACK.md für Sprint 12-15 Updates
✅ Nutze die Copy-Paste Prompts aus diesem Guide
✅ Bestätige Verständnis mit Verification Checklist
```

### DON'T ❌

```
❌ Weitermachen wenn Naming Conventions ignoriert werden
❌ Hoffen dass Context "von selbst zurückkommt"
❌ Quick Refresh bei Major Context Loss (nutze Deep Refresh!)
❌ CLAUDE.md skippen (immer lesen!)
❌ ARCHITECTURE_EVOLUTION.md ignorieren (kritisch für Deep Refresh!)
❌ Alte Dateien lesen (CONTEXT_REFRESH.md, CONTEXT_REFRESH_CHEATSHEET.txt - VERALTET)
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
Quick Check: Sprint N noch klar? Feature N.M next?
Subagenten-Delegation OK? Naming Conventions (snake_case) befolgt?
Falls unsicher → Quick Refresh.
```

### Before Critical Tasks
```
Context Check: Lies docs/CLAUDE.md + docs/core/SPRINT_PLAN.md Feature 16.X
für diese Task. Architektur klar? (Layer 2 vs Layer 3?)
```

### After Kompaktierung (Always)
```
Minimum: Quick Refresh (Strategy 1)
Falls Major Kompaktierung: Standard Refresh (Strategy 2)
```

### Monday / Sprint-Start
```
Deep Refresh (Strategy 3) durchführen.
Verify: Sprint N complete, Sprint N+1 planned.
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
║  Deep Refresh = ARCHITECTURE_EVOLUTION.md + TECH_STACK.md!     ║
║                                                                ║
║                    Happy Coding! 🚀                            ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

**Document Version:** 3.0 (Sprint 16 Architecture-Focused Update)
**Created:** 2025-10-22
**Project:** AEGIS RAG
**Current Sprint:** Sprint 18 
**Last Updated:** 2025-10-28

**Quick Access Commands:**
- Full Project Context: Read docs/CLAUDE.md
- Architecture History: Read docs/ARCHITECTURE_EVOLUTION.md (Sprint 1-15 journey)
- Tech Stack Updates: Read docs/TECH_STACK.md (Sprint 12-15 additions)
- Layer Comparison: Read docs/architecture/LIGHTRAG_VS_GRAPHITI.md
- Quick Refresh: Use Strategy 1 prompt above
- Deep Refresh: Use Strategy 3 prompt above
