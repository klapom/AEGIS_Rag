# Technical Debt Index

**Last Updated:** 2025-12-16
**Total Open Items:** 14
**Total Story Points:** ~230 SP
**Archived Items:** [6 items](archive/ARCHIVE_INDEX.md)

---

## Summary by Priority

| Priority | Count | Story Points |
|----------|-------|--------------|
| CRITICAL | 0     | 0 SP         |
| HIGH     | 3     | ~53 SP       |
| MEDIUM   | 8     | ~140 SP      |
| LOW      | 3     | ~37 SP       |

---

## Archived Items (Sprint 47)

Resolved items have been moved to [archive/](archive/ARCHIVE_INDEX.md):

| TD# | Title | Resolution Sprint |
|-----|-------|-------------------|
| TD-043_FIX_SUMMARY | Follow-up Questions Fix Summary | Sprint 35 |
| TD-050 | Duplicate Answer Streaming | Sprint 47 |
| TD-057 (Sprint 42) | 4-Way Hybrid RRF Retrieval | Sprint 42 |
| TD-060 | Unified Chunk IDs | Sprint 42 |
| TD-061 | Ollama GPU Docker Config | Sprint 42 |
| TD-062 | Multi-Criteria Entity Deduplication | Sprint 43 |

---

## Active Technical Debt Items

### HIGH Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-043](TD-043_FOLLOWUP_QUESTIONS_REDIS.md) | Follow-up Questions Redis Storage | OPEN | 5 | Sprint 49 |
| [TD-044](TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md) | DoclingParsedDocument Interface Fix | IN PROGRESS | 8 | Sprint 49 |
| [TD-045](TD-045_ENTITY_ID_PROPERTY_MIGRATION.md) | entity_id Property Migration (Neo4j) | OPEN | 5 | Sprint 49 |
| [TD-047](TD-047_CRITICAL_PATH_E2E_TESTS.md) | Critical Path E2E Tests | OPEN | 40 | Sprint 51 |

### MEDIUM Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-046](TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md) | RELATES_TO Relationship Extraction | PARTIAL | 13 | Done (Sprint 34) |
| [TD-048](TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md) | Graph Extraction with Unified Chunks | OPEN | 13 | Sprint 52 |
| [TD-049](TD-049_IMPLICIT_USER_PROFILING.md) | Implicit User Profiling | OPEN | 21 | Sprint 52+ |
| [TD-051](TD-051_MEMORY_CONSOLIDATION_PIPELINE.md) | Memory Consolidation Pipeline | OPEN | 21 | Sprint 52 |
| [TD-052](TD-052_USER_DOCUMENT_UPLOAD.md) | User Document Upload Interface | OPEN | 13 | Sprint 52+ |
| [TD-054](TD-054_UNIFIED_CHUNKING_SERVICE.md) | Unified Chunking Service | PARTIAL | 6 | Sprint 50 |
| [TD-058](TD-058_COMMUNITY_SUMMARY_GENERATION.md) | Community Summary Generation | PLANNED | 13 | Sprint 52+ |
| [TD-059](TD-059_RERANKING_DISABLED_CONTAINER.md) | Reranking via Ollama | OPEN | 8 | **Sprint 48** |
| [TD-063](TD-063_RELATION_DEDUPLICATION.md) | Relation Deduplication | PLANNED | 5 | Sprint 52+ |

### LOW Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-053](TD-053_ADMIN_DASHBOARD_FULL.md) | Admin Dashboard Full Implementation | OPEN | 34 | Sprint 52+ |
| [TD-055](TD-055_MCP_CLIENT_IMPLEMENTATION.md) | MCP Client Implementation | OPEN | 21 | Sprint 52+ |
| [TD-056](TD-056_PROJECT_COLLABORATION_SYSTEM.md) | Project Collaboration System | PLANNED | 34 | Sprint 52+ |
| [TD-067](TD-067_DATASET_ANNOTATION_TOOL.md) | Dataset Annotation Tool | BACKLOG | 21 | Future |

---

## Sprint 48 (Current - Real-Time Thinking Phase Events)

**Focus:** Backend SSE Phase Events + Reranking + Nemotron + Timeout
**Story Points:** 73 SP

| Feature | SP | Description |
|---------|-----|-------------|
| 48.1 | 5 | Phase Event Models & Types |
| 48.2 | 13 | CoordinatorAgent Streaming Method |
| 48.3 | 13 | Agent Node Instrumentation |
| 48.4 | 8 | Chat Stream API Enhancement |
| 48.5 | 5 | Phase Events Redis Persistence |
| 48.6 | 8 | Frontend Phase Event Handler |
| 48.7 | 3 | ReasoningData Builder |
| 48.8 | 8 | **TD-059 Reranking via Ollama (bge-reranker-v2-m3)** |
| 48.9 | 5 | **Default LLM zu Nemotron wechseln** |
| 48.10 | 5 | **Request Timeout & Cancel** |

---

## Recommended Sprint Allocation

### Sprint 49
- TD-043: Follow-up Questions Redis (5 SP)
- TD-044: DoclingParsedDocument Interface (8 SP)
- TD-045: entity_id Migration (5 SP)

### Sprint 50
- TD-054: Unified Chunking Service (6 SP)

### Sprint 51
- TD-047: Critical Path E2E Tests (40 SP) - **Dedicated sprint**

### Sprint 52+
- TD-048: Graph Extraction Unified (13 SP)
- TD-051: Memory Consolidation (21 SP)
- TD-049: User Profiling (21 SP)
- TD-052: User Document Upload (13 SP)
- TD-053: Admin Dashboard Full (34 SP)
- TD-055: MCP Client (21 SP)
- TD-056: Project Collaboration (34 SP)
- TD-058: Community Summaries (13 SP)
- TD-063: Relation Deduplication (5 SP)
- TD-067: Dataset Annotation Tool (21 SP)

---

## Items by Category

### Architecture
- [TD-054](TD-054_UNIFIED_CHUNKING_SERVICE.md): Unified Chunking Service
- [TD-048](TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md): Graph Extraction with Unified Chunks
- [TD-051](TD-051_MEMORY_CONSOLIDATION_PIPELINE.md): Memory Consolidation Pipeline

### Testing
- [TD-047](TD-047_CRITICAL_PATH_E2E_TESTS.md): Critical Path E2E Tests

### Data Model
- [TD-044](TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md): DoclingParsedDocument Interface
- [TD-045](TD-045_ENTITY_ID_PROPERTY_MIGRATION.md): entity_id Property Migration
- [TD-046](TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md): RELATES_TO Extraction
- [TD-058](TD-058_COMMUNITY_SUMMARY_GENERATION.md): Community Summary Generation
- [TD-063](TD-063_RELATION_DEDUPLICATION.md): Relation Deduplication

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
    └─→ TD-054 (Unified Chunking) ─→ TD-048 (Graph Extraction)

TD-043 (Follow-up Questions)
    └─→ TD-049 (User Profiling)

TD-045 (entity_id Migration)
    └─→ TD-046 (RELATES_TO) ✓ DONE

TD-059 (Reranking) → Sprint 48
```

---

## Metrics

### Velocity Required (to clear backlog)
- Total remaining: ~230 SP
- At 15 SP/sprint: 15 sprints
- At 30 SP/sprint (parallel): 8 sprints

### Aging
- Oldest item: TD-047 (Sprint 8) - 40+ sprints old
- Average age: ~20 sprints

---

## Notes

1. **Sprint 47 bugs resolved** - All testing bugs from Sprint 46 were fixed
2. **6 items archived** - Resolved TDs moved to archive folder
3. **TD-046** was completed in Sprint 34
4. **TD-044** is in progress with workarounds
5. **TD-047** is a large item (40 SP) requiring dedicated sprint
6. **TD-059** scheduled for Sprint 48 (Reranking via Ollama)
7. **New TDs added**: TD-056 (Collaboration), TD-058 (Community Summaries), TD-063 (Relation Dedup), TD-067 (Annotation Tool)

---

**Document maintained by:** Technical Debt Tracking System
**Review frequency:** Every sprint planning
