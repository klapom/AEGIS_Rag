# Technical Debt Index

**Last Updated:** 2025-12-16
**Total Open Items:** 12
**Total Story Points:** ~179 SP

---

## Summary by Priority

| Priority | Count | Story Points |
|----------|-------|--------------|
| CRITICAL | 0     | 0 SP         |
| HIGH     | 3     | ~53 SP       |
| MEDIUM   | 6     | ~97 SP       |
| LOW      | 2     | ~20 SP       |

---

## Resolved in Sprint 47

| TD# | Title | Status | SP | Resolution |
|-----|-------|--------|-----|------------|
| TD-056 | React Infinite Loop in Chat Streaming | **RESOLVED** | 13 | Fixed unstable callback refs in useStreamChat.ts |
| TD-057 | Health Page Endpoint Mismatch | **RESOLVED** | 3 | Updated frontend to use /health instead of /health/detailed |
| TD-058 | Admin Domain List Sync Issue | **RESOLVED** | 5 | Fixed trailing slash + response structure in useDomainTraining.ts |
| TD-050 | Duplicate Answer Streaming | **RESOLVED** | 3 | Root cause same as TD-056, fixed by hasCalledOnComplete ref |

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

### Sprint 46 (Testing) → Resolved in Sprint 47
- ~~TD-056: React Infinite Loop in Chat Streaming (13 SP)~~ - **RESOLVED**
- ~~TD-057: Health Page Endpoint Mismatch (3 SP)~~ - **RESOLVED**
- ~~TD-058: Admin Domain List Sync Issue (5 SP)~~ - **RESOLVED**
- ~~TD-050: Duplicate Answer Streaming (3 SP)~~ - **RESOLVED** (same root cause)

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

### Bugs (All Sprint 47 bugs resolved)
- ~~TD-056: React Infinite Loop~~ - **RESOLVED Sprint 47**
- ~~TD-057: Health Page Endpoint~~ - **RESOLVED Sprint 47**
- ~~TD-058: Admin Domain List Sync~~ - **RESOLVED Sprint 47**
- ~~TD-050: Duplicate Streaming~~ - **RESOLVED Sprint 47** (same root cause as TD-056)

---

## Recommended Sprint Allocation

### Sprint 47 (COMPLETED - Bug Fixes)
- ~~TD-056: React Infinite Loop (13 SP)~~ - **RESOLVED**
- ~~TD-057: Health Page Endpoint (3 SP)~~ - **RESOLVED**
- ~~TD-058: Admin Domain Sync (5 SP)~~ - **RESOLVED**
- ~~TD-050: Duplicate Streaming (3 SP)~~ - **RESOLVED** (same root cause as TD-056)

### Sprint 48 (Current - Real-Time Thinking Phase Events)
**Focus:** Backend SSE Phase Events für transparente Verarbeitungsschritte
**Story Points:** 55 SP

| Feature | SP | Description |
|---------|-----|-------------|
| 48.1 | 5 | Phase Event Models & Types |
| 48.2 | 13 | CoordinatorAgent Streaming Method |
| 48.3 | 13 | Agent Node Instrumentation |
| 48.4 | 8 | Chat Stream API Enhancement |
| 48.5 | 5 | Phase Events Redis Persistence |
| 48.6 | 8 | Frontend Phase Event Handler |
| 48.7 | 3 | ReasoningData Builder |

**Related TDs:**
- TD-053: Admin Dashboard (Phase-Events für Monitoring)
- TD-059: Reranking Container (Phase zeigt Reranking Status)
- TD-043: Follow-up Questions (Redis Pattern)

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

1. **TD-056, TD-057, TD-058** added from Sprint 46 testing - prioritized for Sprint 47
2. **TD-056** is CRITICAL - React infinite loop blocks all chat functionality
3. **TD-050** being investigated to determine if related to TD-056
4. **TD-046** was completed in Sprint 34
5. **TD-044** is in progress with workarounds
6. **TD-047** is a large item (40 SP) requiring dedicated sprint

---

**Document maintained by:** Technical Debt Tracking System
**Review frequency:** Every sprint planning
