# Technical Debt Archive Index

**Last Updated:** 2025-12-16
**Total Archived Items:** 6

---

## Purpose

This archive contains resolved, completed, or obsolete Technical Debt items that are no longer active but preserved for historical reference.

---

## Archived Items

| TD# | Title | Original Status | Resolution Sprint | Resolution Date |
|-----|-------|-----------------|-------------------|-----------------|
| [TD-043_FIX_SUMMARY](TD-043_FIX_SUMMARY.md) | Follow-up Questions Redis Fix Summary | COMPLETE | Sprint 35 | 2025-12-04 |
| [TD-050](TD-050_DUPLICATE_ANSWER_STREAMING.md) | Duplicate Answer Streaming Fix | RESOLVED | Sprint 47 | 2025-12-16 |
| [TD-057](TD-057_4WAY_HYBRID_RRF_RETRIEVAL.md) | 4-Way Hybrid RRF Retrieval | IMPLEMENTED | Sprint 42 | 2025-12-09 |
| [TD-060](TD-060_UNIFIED_CHUNK_IDS.md) | Unified Chunk/Document IDs | RESOLVED | Sprint 42 | 2025-12-10 |
| [TD-061](TD-061_OLLAMA_GPU_DOCKER_CONFIG.md) | Ollama Container GPU Config | RESOLVED | Sprint 42 | 2025-12-10 |
| [TD-062](TD-062_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md) | Multi-Criteria Entity Deduplication | COMPLETE | Sprint 43 | 2025-12-11 |

---

## Archive by Category

### Bug Fixes
- TD-043_FIX_SUMMARY: Follow-up Questions Redis storage issue
- TD-050: Duplicate Answer Streaming (same root cause as TD-056)
- TD-061: Ollama GPU access in Docker container

### Feature Implementations
- TD-057: 4-Way Hybrid RRF with Intent-Weighted Retrieval
- TD-060: Unified Chunk IDs between Qdrant and Neo4j
- TD-062: Multi-Criteria Entity Deduplication (edit distance, substring, semantic)

---

## Archive by Sprint

### Sprint 35
- TD-043_FIX_SUMMARY: Follow-up Questions Fix

### Sprint 42
- TD-057: 4-Way Hybrid RRF
- TD-060: Unified Chunk IDs
- TD-061: Ollama GPU Docker

### Sprint 43
- TD-062: Multi-Criteria Entity Deduplication

### Sprint 47
- TD-050: Duplicate Answer Streaming

---

## Notes

1. **TD-050** was resolved as part of Sprint 47 bug fixes. The root cause was the same as TD-056 (React infinite loop) - both were fixed by adding `hasCalledOnComplete` ref in `useStreamChat.ts`.

2. **TD-057** implemented the full 4-Way Hybrid Retrieval architecture with Intent Classification. This is now the production retrieval system.

3. **TD-060** and **TD-062** established the foundation for unified knowledge graph operations across Qdrant and Neo4j.

4. **TD-061** documented the critical fix for Ollama GPU access on DGX Spark - important for future deployments.

---

## Retrieval

Items in this archive may be referenced for:
- Historical context on past decisions
- Documentation of resolution approaches
- Learning from previous bug fixes
- Code archaeology when debugging related issues

---

**Document maintained by:** Technical Debt Tracking System
**Archive created:** 2025-12-16
