# Technical Debt Index

**Last Updated:** 2025-12-18 (Sprint 52 Complete)
**Total Open Items:** 12
**Total Story Points:** ~207 SP
**Archived Items:** [10 items](archive/ARCHIVE_INDEX.md)
**Sprint 51 Review:** [Analysis & Archival Decisions](SPRINT_51_REVIEW_ANALYSIS.md)
**Sprint 52:** Community Summaries, Async Follow-ups, Admin Dashboard, CI/CD

---

## Summary by Priority

| Priority | Count | Story Points |
|----------|-------|--------------|
| CRITICAL | 0     | 0 SP         |
| HIGH     | 3     | ~53 SP       |
| MEDIUM   | 6     | ~122 SP      |
| LOW      | 3     | ~37 SP       |

---

## Archived Items

Resolved items have been moved to [archive/](archive/ARCHIVE_INDEX.md):

| TD# | Title | Resolution Sprint |
|-----|-------|-------------------|
| TD-043 | Async Follow-up Questions | Sprint 52 |
| TD-043_FIX_SUMMARY | Follow-up Questions Fix Summary | Sprint 35 |
| TD-045 | entity_id Property Migration | Sprint 34 |
| TD-048 | Graph Extraction with Unified Chunks | Sprint 49 |
| TD-050 | Duplicate Answer Streaming | Sprint 47 |
| TD-057 (Sprint 42) | 4-Way Hybrid RRF Retrieval | Sprint 42 |
| TD-058 | Community Summary Generation | Sprint 52 |
| TD-059 | Reranking via Ollama | Sprint 48 |
| TD-060 | Unified Chunk IDs | Sprint 42 |
| TD-061 | Ollama GPU Docker Config | Sprint 42 |
| TD-062 | Multi-Criteria Entity Deduplication | Sprint 43 |
| TD-063 | Relation Deduplication | Sprint 49 |

---

## Active Technical Debt Items

### HIGH Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-043](TD-043_FOLLOWUP_QUESTIONS_REDIS.md) | Follow-up Questions Redis Storage | **RESOLVED** ✅ | 5 | Sprint 52 ✓ |
| [TD-044](TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md) | DoclingParsedDocument Interface Fix | IN PROGRESS | 8 | Sprint 53 |
| [TD-045](TD-045_ENTITY_ID_PROPERTY_MIGRATION.md) | entity_id Property Migration (Neo4j) | **RESOLVED** ✅ | 5 | Sprint 34 ✓ |
| [TD-047](TD-047_CRITICAL_PATH_E2E_TESTS.md) | Critical Path E2E Tests | **RESOLVED** ✅ | 40 | Sprint 51 ✓ |

### MEDIUM Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-046](TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md) | RELATES_TO Relationship Extraction | **PARTIAL** (Core Done) | 13 | Sprint 34 ✓ |
| [TD-049](TD-049_IMPLICIT_USER_PROFILING.md) | Implicit User Profiling | OPEN | 21 | Sprint 52+ |
| [TD-051](TD-051_MEMORY_CONSOLIDATION_PIPELINE.md) | Memory Consolidation Pipeline | OPEN | 21 | Sprint 52+ |
| [TD-052](TD-052_USER_DOCUMENT_UPLOAD.md) | User Document Upload Interface | OPEN | 13 | Sprint 52+ |
| [TD-053](TD-053_ADMIN_DASHBOARD_FULL.md) | Admin Dashboard Full Implementation | **IN PROGRESS** | 34 | Sprint 52+ |
| [TD-054](TD-054_UNIFIED_CHUNKING_SERVICE.md) | Unified Chunking Service | PARTIAL | 6 | Sprint 50+ |
| [TD-058](TD-058_COMMUNITY_SUMMARY_GENERATION.md) | Community Summary Generation | **RESOLVED** ✅ | 13 | Sprint 52 ✓ |
| [TD-059](TD-059_RERANKING_DISABLED_CONTAINER.md) | Reranking via Ollama | **RESOLVED** ✅ | 8 | Sprint 48 ✓ |
| [TD-064](TD-064_TEMPORAL_COMMUNITY_SUMMARIES.md) | Temporal Community Summaries | PLANNED | 13 | Sprint 53+ |

### LOW Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-053](TD-053_ADMIN_DASHBOARD_FULL.md) | Admin Dashboard Full Implementation | OPEN | 34 | Sprint 52+ |
| [TD-055](TD-055_MCP_CLIENT_IMPLEMENTATION.md) | MCP Client Implementation | OPEN | 21 | Sprint 52+ |
| [TD-056](TD-056_PROJECT_COLLABORATION_SYSTEM.md) | Project Collaboration System | PLANNED | 34 | Sprint 52+ |
| [TD-067](TD-067_DATASET_ANNOTATION_TOOL.md) | Dataset Annotation Tool | BACKLOG | 21 | Future |

---

## Sprint 51 (Completed - E2E Test Coverage & TD Review)

**Focus:** E2E test coverage for unutilized features + Technical Debt Review
**Story Points:** 39 SP (without Mem0 optional feature)
**Status:** ✅ COMPLETE

**Achievements:**
- 111 E2E tests implemented and passing (vs. 40 planned)
- 4 TDs reviewed and updated (TD-045, TD-046, TD-047, TD-059)
- Root documentation reorganized (13 files moved/archived)
- Production confidence improved to >90%

| Feature | SP | Status |
|---------|-----|--------|
| 51.1 | 13 | ✅ Bi-Temporal Queries E2E Tests |
| 51.2 | 8 | ✅ Secure Shell Sandbox E2E Tests |
| 51.3 | 5 | ✅ Dynamic LLM Model Configuration E2E |
| 51.4 | 5 | ✅ Graph Relationship Type Filtering E2E |
| 51.5 | 3 | ✅ Historical Phase Events Display E2E |
| 51.6 | 5 | ✅ Index Consistency Validation UI + E2E |
| TD Review | N/A | ✅ 4 TDs reviewed and status updated |
| Doc Org | N/A | ✅ Root docs reorganized |

---

## Recommended Sprint Allocation

### Sprint 52 (ACTIVE)
- **TD-058: Community Summary Generation (13 SP)**
  - Phase 1: Delta-Tracking Infrastructure (5 SP)
  - Phase 2: Summary Generation + Admin LLM Config (8 SP)
- **TD-053: Admin Dashboard Phase 1 (10 SP)**
  - Graph Analytics Page (5 SP)
  - Domain Management Enhancement (5 SP)
- **TD-043: Async Follow-up Questions (5 SP)**
- CI/CD Pipeline Optimization (3 SP)

### Sprint 53
- **TD-064: Temporal Community Summaries (8 SP)** - deferred from Sprint 52
- **TD-053 Phase 2:** Admin Dashboard Monitoring (16 SP)
- TD-044: DoclingParsedDocument Interface (8 SP)

### Sprint 54+
- TD-051: Memory Consolidation (21 SP)
- TD-049: User Profiling (21 SP)
- TD-052: User Document Upload (13 SP)
- TD-055: MCP Client (21 SP)
- TD-056: Project Collaboration (34 SP)
- TD-067: Dataset Annotation Tool (21 SP)

---

## Items by Category

### Architecture
- [TD-054](TD-054_UNIFIED_CHUNKING_SERVICE.md): Unified Chunking Service
- [TD-051](TD-051_MEMORY_CONSOLIDATION_PIPELINE.md): Memory Consolidation Pipeline

### Testing
- [TD-047](TD-047_CRITICAL_PATH_E2E_TESTS.md): Critical Path E2E Tests

### Data Model
- [TD-044](TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md): DoclingParsedDocument Interface
- [TD-045](TD-045_ENTITY_ID_PROPERTY_MIGRATION.md): entity_id Property Migration
- [TD-046](TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md): RELATES_TO Extraction
- [TD-058](TD-058_COMMUNITY_SUMMARY_GENERATION.md): Community Summary Generation

### Features
- [TD-043](TD-043_FOLLOWUP_QUESTIONS_REDIS.md): Follow-up Questions
- [TD-049](TD-049_IMPLICIT_USER_PROFILING.md): User Profiling
- [TD-052](TD-052_USER_DOCUMENT_UPLOAD.md): User Document Upload
- [TD-053](TD-053_ADMIN_DASHBOARD_FULL.md): Admin Dashboard
- [TD-055](TD-055_MCP_CLIENT_IMPLEMENTATION.md): MCP Client
- [TD-056](TD-056_PROJECT_COLLABORATION_SYSTEM.md): Project Collaboration
- [TD-059](TD-059_RERANKING_DISABLED_CONTAINER.md): Reranking via Ollama
- [TD-067](TD-067_DATASET_ANNOTATION_TOOL.md): Dataset Annotation Tool

---

## Dependency Graph

```
TD-044 (Docling Interface)
    └─→ TD-054 (Unified Chunking) ─→ TD-048 ✓ DONE (Sprint 49)

TD-043 (Follow-up Questions)
    └─→ TD-049 (User Profiling)

TD-045 (entity_id Migration)
    └─→ TD-046 (RELATES_TO) ✓ DONE (Sprint 34)

TD-048 (Graph Extraction) ✓ DONE (Sprint 49)
TD-059 (Reranking) ✓ DONE (Sprint 48)
TD-063 (Relation Dedup) ✓ DONE (Sprint 49)
```

---

## Metrics

### Velocity Required (to clear backlog)
- Total remaining: ~212 SP
- At 15 SP/sprint: 14 sprints
- At 30 SP/sprint (parallel): 7 sprints

### Aging
- Oldest item: TD-047 (Sprint 8) - 40+ sprints old
- Average age: ~20 sprints

---

## Notes

1. **Sprint 49 TDs resolved** - TD-048 (Provenance Tracking) and TD-063 (Relation Dedup) completed
2. **10 items archived** - Resolved TDs moved to archive folder (TD-045, TD-059 added Sprint 51)
3. **TD-046** was completed in Sprint 34 (core), visualization pending
4. **TD-047** exceeded baseline - 111 E2E tests vs. 40 planned (Sprint 51)
5. **TD-053** navigation framework complete, configuration features deferred
6. **Sprint 51 achievements**: 111 E2E tests, 4 TDs reviewed, documentation reorganized
7. **Embedding consolidation**: All embedding tasks now use BGE-M3 (sentence-transformers removed)
8. **Next priority**: Sprint 52 should focus on TD-043/044 + TD-053 Phases 1-2

---

**Document maintained by:** Technical Debt Tracking System
**Review frequency:** Every sprint planning
