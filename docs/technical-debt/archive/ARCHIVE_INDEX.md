# Technical Debt Archive Index

**Last Updated:** 2025-12-18
**Total Archived Items:** 12

---

## Purpose

This archive contains resolved, completed, or obsolete Technical Debt items that are no longer active but preserved for historical reference.

---

## Archived Items

| TD# | Title | Original Status | Resolution Sprint | Resolution Date |
|-----|-------|-----------------|-------------------|-----------------|
| [TD-043_FIX_SUMMARY](TD-043_FIX_SUMMARY.md) | Follow-up Questions Redis Fix Summary | COMPLETE | Sprint 35 | 2025-12-04 |
| [TD-045](TD-045_ENTITY_ID_PROPERTY_MIGRATION.md) | entity_id Property Migration (LightRAG Alignment) | RESOLVED | Sprint 34 | 2025-12-18 |
| [TD-048](TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md) | Graph Extraction with Unified Chunks | RESOLVED | Sprint 49 | 2025-12-16 |
| [TD-050](TD-050_DUPLICATE_ANSWER_STREAMING.md) | Duplicate Answer Streaming Fix | RESOLVED | Sprint 47 | 2025-12-16 |
| [TD-057](TD-057_4WAY_HYBRID_RRF_RETRIEVAL.md) | 4-Way Hybrid RRF Retrieval | IMPLEMENTED | Sprint 42 | 2025-12-09 |
| [TD-059](TD-059_RERANKING_DISABLED_CONTAINER.md) | Reranking via Ollama (bge-reranker-v2-m3) | RESOLVED | Sprint 48 | 2025-12-18 |
| [TD-060](TD-060_UNIFIED_CHUNK_IDS.md) | Unified Chunk/Document IDs | RESOLVED | Sprint 42 | 2025-12-10 |
| [TD-061](TD-061_OLLAMA_GPU_DOCKER_CONFIG.md) | Ollama Container GPU Config | RESOLVED | Sprint 42 | 2025-12-10 |
| [TD-062](TD-062_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md) | Multi-Criteria Entity Deduplication | COMPLETE | Sprint 43 | 2025-12-11 |
| [TD-063](TD-063_RELATION_DEDUPLICATION.md) | Relation Deduplication (Semantic + NLP) | RESOLVED | Sprint 49 | 2025-12-16 |

---

## Archive by Category

### Bug Fixes & Architecture Migrations
- TD-043_FIX_SUMMARY: Follow-up Questions Redis storage issue
- TD-045: entity_id Property Migration (LightRAG schema alignment)
- TD-050: Duplicate Answer Streaming (React infinite loop fix)
- TD-061: Ollama GPU access in Docker container

### Feature Implementations
- TD-048: Graph Extraction with Unified Chunks (provenance tracking)
- TD-057: 4-Way Hybrid RRF with Intent-Weighted Retrieval
- TD-059: Reranking via Ollama (BGE-Reranker integration)
- TD-060: Unified Chunk IDs between Qdrant and Neo4j
- TD-062: Multi-Criteria Entity Deduplication (edit distance, substring, semantic)
- TD-063: Relation Deduplication (Semantic similarity + NLP)

---

## Archive by Sprint

### Sprint 34
- TD-045: entity_id Property Migration

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

### Sprint 48
- TD-059: Reranking via Ollama

### Sprint 49
- TD-048: Graph Extraction with Unified Chunks
- TD-063: Relation Deduplication

---

## Notes

1. **TD-045** was actually resolved in Sprint 34 but discovered during Sprint 51 review. LightRAG compatibility achieved.

2. **TD-048** and **TD-063** were completed in Sprint 49, establishing semantic deduplication across entities and relations.

3. **TD-050** was resolved as part of Sprint 47 bug fixes. The root cause was the same as TD-056 (React infinite loop) - both were fixed by adding `hasCalledOnComplete` ref in `useStreamChat.ts`.

4. **TD-057** implemented the full 4-Way Hybrid Retrieval architecture with Intent Classification. This is now the production retrieval system.

5. **TD-059** Reranking via Ollama was completed in Sprint 48, enabling cross-encoder reranking through the Ollama container.

6. **TD-060** and **TD-062** established the foundation for unified knowledge graph operations across Qdrant and Neo4j.

7. **TD-061** documented the critical fix for Ollama GPU access on DGX Spark - important for future deployments.

8. **Sprint 51 Archival:** TD-045 and TD-059 added to archive during Sprint 51 technical debt review (December 18, 2025).

---

## Retrieval

Items in this archive may be referenced for:
- Historical context on past decisions
- Documentation of resolution approaches
- Learning from previous bug fixes
- Code archaeology when debugging related issues

---

**Document maintained by:** Documentation Agent
**Archive created:** 2025-12-16
**Last updated:** 2025-12-18 (Sprint 51 Review & Archival)
