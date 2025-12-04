# Technical Debt Index

**Last Updated:** 2025-12-04
**Total Open Items:** 13
**Total Story Points:** ~180 SP

---

## Summary by Priority

| Priority | Count | Story Points |
|----------|-------|--------------|
| HIGH     | 4     | ~60 SP       |
| MEDIUM   | 7     | ~100 SP      |
| LOW      | 2     | ~20 SP       |

---

## Active Technical Debt Items

### HIGH Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-043](TD-043_FOLLOWUP_QUESTIONS_REDIS.md) | Follow-up Questions Redis Storage | OPEN | 5 | Sprint 35 |
| [TD-044](TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md) | DoclingParsedDocument Interface Fix | IN PROGRESS | 8 | Sprint 35/36 |
| [TD-045](TD-045_ENTITY_ID_PROPERTY_MIGRATION.md) | entity_id Property Migration (Neo4j) | OPEN | 5 | Sprint 36 |
| [TD-047](TD-047_CRITICAL_PATH_E2E_TESTS.md) | Critical Path E2E Tests (Sprint 8) | OPEN | 40 | Sprint 37 |

### MEDIUM Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-046](TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md) | RELATES_TO Relationship Extraction | PARTIAL | 13 | Sprint 34 (done) |
| [TD-048](TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md) | Graph Extraction with Unified Chunks | OPEN | 13 | Sprint 38 |
| [TD-049](TD-049_IMPLICIT_USER_PROFILING.md) | Implicit User Profiling | OPEN | 21 | Sprint 39 |
| [TD-050](TD-050_DUPLICATE_ANSWER_STREAMING.md) | Duplicate Answer Streaming Fix | NEEDS VERIFICATION | 3 | Sprint 35/36 |
| [TD-051](TD-051_MEMORY_CONSOLIDATION_PIPELINE.md) | Memory Consolidation Pipeline | OPEN | 21 | Sprint 38 |
| [TD-052](TD-052_USER_DOCUMENT_UPLOAD.md) | User Document Upload Interface | OPEN | 13 | Sprint 39/40 |
| [TD-054](TD-054_UNIFIED_CHUNKING_SERVICE.md) | Unified Chunking Service | PARTIAL | 6 | Sprint 36 |

### LOW Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-053](TD-053_ADMIN_DASHBOARD_FULL.md) | Admin Dashboard Full Implementation | OPEN | 34 | Sprint 40+ |
| [TD-055](TD-055_MCP_CLIENT_IMPLEMENTATION.md) | MCP Client Implementation | OPEN | 21 | Sprint 41+ |

---

## Items by Original Sprint

### Sprint 8
- [TD-047](TD-047_CRITICAL_PATH_E2E_TESTS.md): Critical Path E2E Tests (40 SP)

### Sprint 9
- [TD-051](TD-051_MEMORY_CONSOLIDATION_PIPELINE.md): Memory Consolidation Pipeline (21 SP)
- [TD-055](TD-055_MCP_CLIENT_IMPLEMENTATION.md): MCP Client Implementation (21 SP)

### Sprint 10
- [TD-052](TD-052_USER_DOCUMENT_UPLOAD.md): User Document Upload Interface (13 SP)

### Sprint 11
- [TD-053](TD-053_ADMIN_DASHBOARD_FULL.md): Admin Dashboard Full (34 SP)

### Sprint 16
- [TD-048](TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md): Graph Extraction with Unified Chunks (13 SP)
- [TD-054](TD-054_UNIFIED_CHUNKING_SERVICE.md): Unified Chunking Service (6 SP)

### Sprint 17
- [TD-049](TD-049_IMPLICIT_USER_PROFILING.md): Implicit User Profiling (21 SP)
- [TD-050](TD-050_DUPLICATE_ANSWER_STREAMING.md): Duplicate Answer Streaming Fix (3 SP)

### Sprint 32/33
- [TD-043](TD-043_FOLLOWUP_QUESTIONS_REDIS.md): Follow-up Questions Redis Storage (5 SP)
- [TD-044](TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md): DoclingParsedDocument Interface (8 SP)
- [TD-045](TD-045_ENTITY_ID_PROPERTY_MIGRATION.md): entity_id Property Migration (5 SP)
- [TD-046](TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md): RELATES_TO Extraction (13 SP)

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

### Features
- [TD-043](TD-043_FOLLOWUP_QUESTIONS_REDIS.md): Follow-up Questions
- [TD-049](TD-049_IMPLICIT_USER_PROFILING.md): User Profiling
- [TD-052](TD-052_USER_DOCUMENT_UPLOAD.md): User Document Upload
- [TD-053](TD-053_ADMIN_DASHBOARD_FULL.md): Admin Dashboard
- [TD-055](TD-055_MCP_CLIENT_IMPLEMENTATION.md): MCP Client

### Bugs
- [TD-050](TD-050_DUPLICATE_ANSWER_STREAMING.md): Duplicate Streaming

---

## Recommended Sprint Allocation

### Sprint 35 (Current)
- TD-043: Follow-up Questions Redis (5 SP) - **PLANNED**
- TD-050: Duplicate Streaming Fix (3 SP) - **Verify first**

### Sprint 36
- TD-044: DoclingParsedDocument Interface (8 SP)
- TD-045: entity_id Migration (5 SP)
- TD-054: Unified Chunking Service (6 SP)

### Sprint 37
- TD-047: Critical Path E2E Tests (40 SP) - **Dedicated sprint**

### Sprint 38
- TD-048: Graph Extraction Unified (13 SP)
- TD-051: Memory Consolidation (21 SP)

### Sprint 39
- TD-049: User Profiling (21 SP)
- TD-052: User Document Upload (13 SP)

### Sprint 40+
- TD-053: Admin Dashboard Full (34 SP)
- TD-055: MCP Client (21 SP)

---

## Dependency Graph

```
TD-044 (Docling Interface)
    └─→ TD-054 (Unified Chunking) ─→ TD-048 (Graph Extraction)

TD-043 (Follow-up Questions)
    └─→ TD-049 (User Profiling)

TD-045 (entity_id Migration)
    └─→ TD-046 (RELATES_TO) ✓ DONE
```

---

## Metrics

### Velocity Required (to clear backlog)
- Total remaining: ~180 SP
- At 15 SP/sprint: 12 sprints
- At 30 SP/sprint (parallel): 6 sprints

### Aging
- Oldest item: TD-047 (Sprint 8) - 26+ sprints old
- Average age: ~15 sprints

---

## Notes

1. **TD-043** is already planned for Sprint 35
2. **TD-046** was completed in Sprint 34
3. **TD-044** is in progress with workarounds
4. **TD-050** needs verification before implementation
5. **TD-047** is a large item (40 SP) requiring dedicated sprint

---

**Document maintained by:** Technical Debt Tracking System
**Review frequency:** Every sprint planning
