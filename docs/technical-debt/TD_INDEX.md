# Technical Debt Index

**Last Updated:** 2026-02-12 (Sprint 129 — TD-124 added for VLM LoRA fine-tuning)
**Total Active Items:** 10 (4 Active + 6 Deferred)
**Total Active Story Points:** ~147 SP
**Archived Items:** [49 items](archive/ARCHIVE_INDEX.md)
**Review Frequency:** Every sprint planning

---

## Summary by Priority

| Priority | Count | Story Points | Status |
|----------|-------|--------------|--------|
| CRITICAL | 1     | 6 SP         | TD-101: DEFERRED (Sprint 130+) |
| HIGH     | 1     | ~18 SP       | TD-102: Sprint 122 |
| MEDIUM   | 1     | ~8 SP        | TD-098: DEFERRED |
| LOW      | 7     | ~115 SP      | TD-056, TD-064, TD-120, TD-121, TD-122, TD-123, TD-124: DEFERRED/OPEN |

**Note:** TD-120 (31 SP), TD-121 (21 SP) deferred indefinitely unless customer trigger.
**Note:** TD-122 (5 SP), TD-123 (3 SP) — Sprint 121 discoveries, low priority.

---

## Active Technical Debt Items

### 🔴 CRITICAL Priority

| TD# | Title | Status | SP | Target Sprint | Notes |
|-----|-------|--------|-----|---------------|-------|
| [TD-101](TD-101-rise-reasoning-control.md) | **RISE Reasoning Control** | 🟡 **DEFERRED** | 6 | **Sprint 130+** | Research risk, prompt engineering covers 70-80% |

**TD-101 Discovery (Sprint 94):** Feature 94.4 (RISE Reasoning Control) deferred to technical debt. Integrating RISE sparse autoencoders for per-skill reasoning behavior control requires additional research and architecture planning. See ADR-055 (LangGraph 1.0 patterns) for implementation foundation.

### HIGH Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-102](TD-102_RELATION_EXTRACTION_IMPROVEMENT.md) | **Relation Extraction Improvement** | 🔴 OPEN | 18 | **Sprint 122** |

**TD-102 Discovery (Sprint 85):** Multi-format ingestion testing revealed Relation Ratio of only 0.27-0.61 (target: ≥1.0). Root causes: SpaCy only as fallback, generic RELATES_TO prompts, no Gleaning. 5 iterations planned: SpaCy-first → Typed Relations → Gleaning → DSPy → KG Hygiene.

### MEDIUM Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-098](TD-098_CROSS_ENCODER_FINE_TUNING.md) | Cross-Encoder Fine-tuning | 🟡 **DEFERRED** | 8 | **Post-RAGAS Phase 2** |

**TD-098 Update (Sprint 121):** Deferred until RAGAS Phase 2 baseline establishes whether reranking is the bottleneck. Cross-encoder fine-tuning is for reranking quality improvement (+10-18% Context Precision), not domain classification.

### LOW Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-056](TD-056_PROJECT_COLLABORATION_SYSTEM.md) | Project Collaboration System | PLANNED | 34 | Sprint 130+ |
| [TD-064](TD-064_TEMPORAL_COMMUNITY_SUMMARIES.md) | Temporal Community Summaries | 🟡 **DEFERRED** | 13 | **Indefinite** |
| [TD-120](TD-120_GRAPHITI_TIMETRAVEL_VERSIONING.md) | **Graphiti Time-Travel & Entity Versioning** | 🔴 **DEFERRED INDEFINITE** | 31 (Full) / 10 (Minimal) | **Customer Trigger** |
| [TD-121](TD-121_GRAPH_VERSIONING_UI.md) | **Neo4j Graph Versioning UI (39.5-39.7)** | 🔴 **DEFERRED** | 21 | **Sprint 122+** |
| [TD-122](TD-122_TOOL_PROGRESS_STREAMING.md) | **Tool Progress Streaming (Backend)** | 🔴 OPEN | 5 | **Sprint 123+** |
| [TD-123](TD-123_TOOL_DISPLAY_COMPONENT_MERGE.md) | **Tool Display Component Merge** | 🔴 OPEN | 3 | **Sprint 123+** |
| [TD-124](TD-124_VLM_LORA_TABLE_FINETUNING.md) | **VLM LoRA Fine-Tuning for Table OCR** | 🟡 **DEFERRED** | 8 | **Post-Sprint 130** |

**TD-064 Update (Sprint 121):** Marked DEFERRED per user decision. No immediate business need.

**TD-120 Discovery (Sprint 114):** Graphiti temporal infrastructure supports time-travel queries, entity versioning, and change history. Deferred indefinitely - low user demand, high complexity (31 SP), uncertain ROI.

**TD-121 Discovery (Sprint 119):** E2E test analysis found 28 skipped tests for Neo4j Graph Versioning. Deferred to Sprint 122+.

**TD-122 Discovery (Sprint 121):** `tool_progress` SSE event is a "sleeping feature" — frontend handler exists in `useStreamChat.ts` but backend never emits this event. Low priority, needed for long-running tool UX (>5s bash/python).

**TD-123 Discovery (Sprint 121):** Two overlapping tool display components: `ToolExecutionDisplay.tsx` (Sprint 63, post-execution) and `ToolExecutionPanel.tsx` (Sprint 119+121, streaming). ~600 lines with significant overlap. Merge into shared component family.

**TD-124 Discovery (Sprint 129):** VLM Cross-Validation Benchmark showed Nemotron VL FP4 has 22 OCR errors on German automotive tables. LoRA fine-tuning on 100-500 corrected samples expected to reduce errors 50-70%. Benchmark data archived in `data/evaluation/table_benchmark/TD-124_VLM_LORA_TABLE_FINETUNING.zip`. Prerequisite: Table ingestion pipeline (Sprint 129.6) must be production-ready first.

---

## Archived Items

Resolved items have been moved to [archive/](archive/ARCHIVE_INDEX.md). See ARCHIVE_INDEX.md for the complete list (49 items).

### Recent Archival History

| Sprint | Items Archived | SP Cleared |
|--------|---------------|------------|
| **Sprint 121** | TD-054, TD-055, TD-070, TD-078, TD-104 (resolved) + 10 orphans/obsolete | **44 SP** (resolved) |
| **Sprint 92** | TD-080 (Context Relevance Guard) | **5 SP** |
| **Sprint 87** | TD-074, TD-103 (BGE-M3 eliminates BM25) | **26 SP** |
| **Sprint 84** | TD-059, TD-075, TD-077, TD-083, TD-100 (code analysis) | **31 SP** |
| **Sprint 83** | TD-044, TD-046, TD-052, TD-079, TD-099 | **27 SP** |
| **Sprint 81** | TD-096, TD-097 (Settings UI) | **8 SP** |
| **Sprint 76** | TD-084, TD-085 (Architecture Gaps) | **34 SP** |

### Sprint 121 TD Cleanup Details

**Resolved (5 TDs, 44 SP):**
- **TD-054** (6 SP): Unified Chunking Service — `ChunkingService` deleted, -1,727 lines
- **TD-055** (10 SP): MCP Client Implementation — LLM tool detection default, bilingual skills
- **TD-070** (3 SP): Ingestion Performance Tuning — 170s→38.5s (77% faster)
- **TD-078** (11 SP): Section Extraction Performance — Tokenizer singleton + parallel batch
- **TD-104** (14 SP): LightRAG CRUD Feature Gap — Entity Delete API, GDPR Art. 17

**Orphaned/Obsolete (15 files archived):**
- TD-045 (duplicate in active), TD-049, TD-051, TD-053, TD-067, TD-068
- TD-074, TD-076, TD-081, TD-082, TD-086, TD-101 (community bottleneck, TD# collision)
- TD-103, TD_TECH_DEBT.md (legacy register), TD_DEAD_CODE_STRATEGY.md

---

## Notes

1. **Sprint 121 major cleanup** — Active folder reduced from 23 → 8 files (7 TDs + index)
2. **Total archived items:** 49 (see [ARCHIVE_INDEX.md](archive/ARCHIVE_INDEX.md))
3. **Next target:** TD-102 (Relation Extraction, 18 SP) scheduled for Sprint 122
4. **All deferred items** require external trigger (customer need, RAGAS results, research breakthrough)

---

**Document maintained by:** Technical Debt Tracking System
**Review frequency:** Every sprint planning
