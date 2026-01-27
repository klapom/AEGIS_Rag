# Technical Debt Archive Index

**Last Updated:** 2026-01-10 (Sprint 83)
**Total Archived Items:** 20 (TD-044, TD-046, TD-052, TD-079, TD-099 added)

---

## Purpose

This archive contains resolved, completed, or obsolete Technical Debt items that are no longer active but preserved for historical reference.

---

## Archived Items

| TD# | Title | Original Status | Resolution Sprint | Resolution Date |
|-----|-------|-----------------|-------------------|-----------------|
| [TD-043_FIX_SUMMARY](TD-043_FIX_SUMMARY.md) | Follow-up Questions Redis Fix Summary | COMPLETE | Sprint 35 | 2025-12-04 |
| [TD-044](TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md) | DoclingParsedDocument Interface Fix | OBSOLETE | Sprint 83 | 2026-01-10 |
| [TD-045](TD-045_ENTITY_ID_PROPERTY_MIGRATION.md) | entity_id Property Migration (LightRAG Alignment) | RESOLVED | Sprint 34 | 2025-12-18 |
| [TD-046](TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md) | RELATES_TO Relationship Extraction | RESOLVED | Sprint 42 | 2025-12-10 |
| [TD-048](TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md) | Graph Extraction with Unified Chunks | RESOLVED | Sprint 49 | 2025-12-16 |
| [TD-050](TD-050_DUPLICATE_ANSWER_STREAMING.md) | Duplicate Answer Streaming Fix | RESOLVED | Sprint 47 | 2025-12-16 |
| [TD-052](TD-052_USER_DOCUMENT_UPLOAD.md) | User Document Upload | RESOLVED | Sprint 83 | 2026-01-10 |
| [TD-057](TD-057_4WAY_HYBRID_RRF_RETRIEVAL.md) | 4-Way Hybrid RRF Retrieval | IMPLEMENTED | Sprint 42 | 2025-12-09 |
| [TD-059](TD-059_RERANKING_DISABLED_CONTAINER.md) | Reranking via Ollama (bge-reranker-v2-m3) | RESOLVED | Sprint 48 | 2025-12-18 |
| [TD-060](TD-060_UNIFIED_CHUNK_IDS.md) | Unified Chunk/Document IDs | RESOLVED | Sprint 42 | 2025-12-10 |
| [TD-061](TD-061_OLLAMA_GPU_DOCKER_CONFIG.md) | Ollama Container GPU Config | RESOLVED | Sprint 42 | 2025-12-10 |
| [TD-062](TD-062_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md) | Multi-Criteria Entity Deduplication | COMPLETE | Sprint 43 | 2025-12-11 |
| [TD-063](TD-063_RELATION_DEDUPLICATION.md) | Relation Deduplication (Semantic + NLP) | RESOLVED | Sprint 49 | 2025-12-16 |
| [TD-079](TD-079_LLM_INTENT_CLASSIFIER_CLARA.md) | LLM Intent Classifier (C-LARA SetFit) | RESOLVED | Sprint 81 | 2026-01-08 |
| [TD-091](TD-091_CHUNK_COUNT_MISMATCH.md) | Chunk Count Mismatch (Qdrant vs Neo4j) | RESOLVED | Sprint 77 | 2026-01-07 |
| [TD-094](TD-094_COMMUNITY_SUMMARIZATION_BATCH_JOB.md) | Community Summarization Batch Job | RESOLVED | Sprint 77 | 2026-01-07 |
| [TD-095](TD-095_ENTITY_CONNECTIVITY_DOMAIN_METRIC.md) | Entity Connectivity as Domain Training Metric | RESOLVED | Sprint 77 | 2026-01-07 |
| [TD-099](TD-099_NAMESPACE_INGESTION_BUG.md) | Namespace Not Set During RAGAS Ingestion | RESOLVED | Sprint 81 | 2026-01-08 |

---

## Archive by Category

### Bug Fixes & Architecture Migrations
- TD-043_FIX_SUMMARY: Follow-up Questions Redis storage issue
- TD-044: DoclingParsedDocument Interface Fix (obsolete - section extraction now working)
- TD-045: entity_id Property Migration (LightRAG schema alignment)
- TD-050: Duplicate Answer Streaming (React infinite loop fix)
- TD-061: Ollama GPU access in Docker container
- TD-099: Namespace Not Set During RAGAS Ingestion (namespace field bug)

### Feature Implementations
- TD-046: RELATES_TO Relationship Extraction (semantic relationships)
- TD-048: Graph Extraction with Unified Chunks (provenance tracking)
- TD-052: User Document Upload (fast upload + background refinement)
- TD-057: 4-Way Hybrid RRF with Intent-Weighted Retrieval
- TD-059: Reranking via Ollama (BGE-Reranker integration)
- TD-060: Unified Chunk IDs between Qdrant and Neo4j
- TD-062: Multi-Criteria Entity Deduplication (edit distance, substring, semantic)
- TD-063: Relation Deduplication (Semantic similarity + NLP)
- TD-079: LLM Intent Classifier (C-LARA SetFit 95.22% accuracy)

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

### Sprint 77
- TD-091: Chunk Count Mismatch (Qdrant vs Neo4j)
- TD-094: Community Summarization Batch Job
- TD-095: Entity Connectivity as Domain Training Metric

### Sprint 81
- TD-079: LLM Intent Classifier (C-LARA SetFit)
- TD-099: Namespace Not Set During RAGAS Ingestion

### Sprint 83
- TD-044: DoclingParsedDocument Interface Fix (obsolete)
- TD-052: User Document Upload

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

9. **Sprint 77 Archival:** TD-091 (chunk count mismatch), TD-094 (community summarization), TD-095 (entity connectivity) resolved during Sprint 77 graph optimization (January 7, 2026).

10. **Sprint 81 Archival:** TD-079 (C-LARA SetFit classifier 95.22% accuracy) and TD-099 (namespace ingestion bug) resolved during Sprint 81 (January 8, 2026).

11. **Sprint 83 Archival:** TD-044 (DoclingParsedDocument interface - obsolete, section extraction now working), TD-046 (RELATES_TO extraction - ADR-040), TD-052 (user upload - Feature 83.4) archived during Sprint 83 technical debt cleanup (January 10, 2026).

12. **Sprint 121 Archival (2026-01-27):** 5 TDs resolved (44 SP total):
    - **TD-054** (6 SP): Unified Chunking Service — `ChunkingService` (775 lines) deleted, production uses `adaptive_chunking.py`. -1,727 lines removed.
    - **TD-055** (10 SP): MCP Client Implementation — Tool detection default changed from `hybrid` to `llm`. Enhanced bilingual prompts, 9 skill triggers configured.
    - **TD-070** (3 SP): Ingestion Performance Tuning — Verified: 170s→38.5s (77% faster). Graph extraction 162s→31.2s (81% faster). Ollama GPU fix confirmed.
    - **TD-078** (11 SP): Section Extraction Performance Phase 2 — Tokenizer singleton cache (thread-safe double-check locking) + ThreadPoolExecutor batch tokenization (4 workers).
    - **TD-104** (14 SP): LightRAG CRUD Feature Gap — 5 REST endpoints, 9 Pydantic models, GDPR Article 17 compliance. EntityManagementPage frontend.

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
**Last updated:** 2026-01-27 (Sprint 121 Technical Debt Consolidation — 5 TDs, 44 SP)
