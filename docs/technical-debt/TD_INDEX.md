# Technical Debt Index

**Last Updated:** 2025-12-21 (Sprint 60 Complete)
**Total Open Items:** 14
**Total Story Points:** ~233 SP
**Archived Items:** [11 items](archive/ARCHIVE_INDEX.md)
**Sprint 51 Review:** [Analysis & Archival Decisions](SPRINT_51_REVIEW_ANALYSIS.md)
**Sprint 52:** Community Summaries, Async Follow-ups, Admin Dashboard, CI/CD
**Sprint 53-58:** Refactoring Initiative (ADR-046)
**Sprint 59:** Agentic Features, Tool Use
**Sprint 60:** ✅ Documentation Consolidation, Technical Investigations (COMPLETE)

---

## Summary by Priority

| Priority | Count | Story Points |
|----------|-------|--------------|
| CRITICAL | 0     | 0 SP         |
| HIGH     | 3     | ~53 SP       |
| MEDIUM   | 8     | ~148 SP      |
| LOW      | 4     | ~58 SP       |
| Investigation | 2 | ~26 SP      |

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
| TD-069 | Multihop Endpoint Review | Sprint 60 |

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

### Investigation / Review

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-068](TD-068_CLOUD_LLM_SUPPORT.md) | Cloud LLM Support (AnyLLM/Dashscope) | OPEN | 13 | Sprint 61+ |
| [TD-069](TD-069_MULTIHOP_ENDPOINT_REVIEW.md) | Multihop Endpoint Status Review | **RESOLVED** ✅ | 3 | Sprint 60 ✓ |
| [TD-070](TD-070_INGESTION_PERFORMANCE_TUNING.md) | Ingestion Performance Tuning | OPEN | 13 | Sprint 61+ |
| [TD-071](TD-071_VLLM_VS_OLLAMA_INVESTIGATION.md) | vLLM vs Ollama Investigation | **RESOLVED** ✅ | 5 | Sprint 60 ✓ |
| [TD-072](TD-072_SENTENCE_TRANSFORMERS_RERANKING.md) | Sentence-Transformers Reranking | **INVESTIGATION COMPLETE** → Sprint 61 | 5 | Sprint 60 ✓ |
| [TD-073](TD-073_SENTENCE_TRANSFORMERS_EMBEDDINGS.md) | Sentence-Transformers Embeddings | **INVESTIGATION COMPLETE** → Sprint 61 | 5 | Sprint 60 ✓ |

---

## Sprint 60 (Completed - Documentation Consolidation & Technical Investigations)

**Focus:** Documentation consolidation post-refactoring (Sprint 53-59) + Technical investigations
**Story Points:** 45 SP
**Status:** ✅ COMPLETE

**Achievements:**
- 7 consolidated documentation files created (ARCHITECTURE.md, TECH_STACK.md, CONVENTIONS.md, 4 analysis docs)
- 17 files archived (6 from Wave 1, 11 from Wave 3)
- 4 technical investigations completed (TD-069, TD-071, TD-072, TD-073)
- Clear recommendations for Sprint 61+ (2 migrations recommended, 1 removal recommended, 1 keep Ollama)

| Feature | SP | Status |
|---------|-----|--------|
| 60.1 | 13 | ✅ Core Documentation Consolidation |
| 60.2 | 8 | ✅ GRAPHITI Temporal Queries Analysis |
| 60.3 | 3 | ✅ Section Nodes Implementation Review |
| 60.4 | 3 | ✅ TD-069 Multihop Endpoint Review |
| 60.5 | 5 | ✅ TD-071 vLLM vs Ollama Investigation |
| 60.6 | 5 | ✅ TD-072 Sentence-Transformers Reranking Investigation |
| 60.7 | 5 | ✅ TD-073 Sentence-Transformers Embeddings Investigation |
| 60.8 | 3 | ✅ Subdirectory Cleanup |

**Investigation Results:**
- **TD-069:** ✅ RESOLVED - Remove multihop endpoints (unused, deprecated)
- **TD-071:** ✅ RESOLVED - Keep Ollama (vLLM not justified at current scale)
- **TD-072:** 🔄 MIGRATE - Cross-Encoder reranking recommended (50x faster)
- **TD-073:** 🔄 MIGRATE - Native Sentence-Transformers recommended (3-5x faster)

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

### Sprint 61 (NEXT)
**Based on Sprint 60 investigations, high ROI performance optimizations:**
- **NEW TD: Native Sentence-Transformers Embeddings (8 SP)** - from TD-073
  - 3-5x faster embeddings, 60% less VRAM, identical quality
- **NEW TD: Cross-Encoder Reranking (9 SP)** - from TD-072
  - 50x faster reranking, comparable quality
- **Remove Multihop Endpoints (2 SP)** - from TD-069
  - Clean up 5 deprecated graph_viz endpoints
- **Total:** 19 SP

### Sprint 62
- **TD-064: Temporal Community Summaries (8 SP)** - deferred from Sprint 52
- **TD-053 Phase 2:** Admin Dashboard Monitoring (16 SP)
- TD-044: DoclingParsedDocument Interface (8 SP)

### Sprint 63+
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
2. **11 items archived** - Resolved TDs moved to archive folder (TD-069 added Sprint 60)
3. **TD-046** was completed in Sprint 34 (core), visualization pending
4. **TD-047** exceeded baseline - 111 E2E tests vs. 40 planned (Sprint 51)
5. **TD-053** navigation framework complete, configuration features deferred
6. **Sprint 51 achievements**: 111 E2E tests, 4 TDs reviewed, documentation reorganized
7. **Sprint 60 achievements**: 7 docs consolidated, 17 files archived, 4 technical investigations complete
8. **Embedding consolidation**: All embedding tasks now use BGE-M3 (sentence-transformers removed)
9. **Performance optimizations ready**: Sprint 61 should implement TD-072/073 migrations (high ROI)
10. **vLLM investigation**: Keep Ollama - vLLM not justified at current scale (<50 QPS)

---

**Document maintained by:** Technical Debt Tracking System
**Review frequency:** Every sprint planning
