# Technical Debt Archive Index

**Last Updated:** 2026-01-27 (Sprint 121 TD Cleanup — 15 additional items archived)
**Total Archived Items:** 59 (TD-043 through TD-104 + strategy docs)

---

## Purpose

This archive contains resolved, completed, or obsolete Technical Debt items that are no longer active but preserved for historical reference. Items are archived when:
- Resolved and implemented
- Superseded by later features or ADRs
- Deferred indefinitely as lower priority
- No longer applicable due to architecture changes

---

## Archived Items Summary

### Legend
- **RESOLVED:** TD was implemented and working feature delivered
- **COMPLETE:** Task finished with evidence of completion
- **IMPLEMENTED:** Feature deployed to production
- **OBSOLETE:** No longer applicable due to architecture changes
- **DEFERRED:** Postponed indefinitely due to low priority or competing demands
- **STRATEGY DOC:** One-time reference material (work completed, documentation preserved)

| TD# | Title | Status | Resolution Sprint | Archived Date |
|-----|-------|--------|-------------------|---------------|
| [TD-043_FIX_SUMMARY](TD-043_FIX_SUMMARY.md) | Follow-up Questions Redis Fix Summary | COMPLETE | Sprint 35 | 2025-12-04 |
| [TD-043_FOLLOWUP_QUESTIONS_REDIS](TD-043_FOLLOWUP_QUESTIONS_REDIS.md) | Follow-up Questions Redis Storage | COMPLETE | Sprint 35 | 2025-12-04 |
| [TD-044](TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md) | DoclingParsedDocument Interface Fix | OBSOLETE | Sprint 83 | 2026-01-10 |
| [TD-045](TD-045_ENTITY_ID_PROPERTY_MIGRATION.md) | entity_id Property Migration (LightRAG Alignment) | RESOLVED | Sprint 34 | 2025-12-18 |
| [TD-046](TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md) | RELATES_TO Relationship Extraction | RESOLVED | Sprint 42 | 2025-12-10 |
| [TD-047](TD-047_CRITICAL_PATH_E2E_TESTS.md) | Critical Path E2E Tests | RESOLVED | Sprint 71 | 2025-12-04 |
| [TD-048](TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md) | Graph Extraction with Unified Chunks | RESOLVED | Sprint 49 | 2025-12-16 |
| [TD-049](TD-049_IMPLICIT_USER_PROFILING.md) | Implicit User Profiling (Orphaned Feature 17.4) | DEFERRED | Sprint 121 | 2026-01-27 |
| [TD-050](TD-050_DUPLICATE_ANSWER_STREAMING.md) | Duplicate Answer Streaming Fix | RESOLVED | Sprint 47 | 2025-12-16 |
| [TD-051](TD-051_MEMORY_CONSOLIDATION_PIPELINE.md) | Memory Consolidation Pipeline (Orphaned Feature 9) | DEFERRED | Sprint 121 | 2026-01-27 |
| [TD-052](TD-052_USER_DOCUMENT_UPLOAD.md) | User Document Upload | RESOLVED | Sprint 83 | 2026-01-10 |
| [TD-053](TD-053_ADMIN_DASHBOARD_FULL.md) | Admin Dashboard Full Implementation (Orphaned Feature 11) | DEFERRED | Sprint 121 | 2026-01-27 |
| [TD-057](TD-057_4WAY_HYBRID_RRF_RETRIEVAL.md) | 4-Way Hybrid RRF Retrieval | IMPLEMENTED | Sprint 42 | 2025-12-09 |
| [TD-058](TD-058_COMMUNITY_SUMMARY_GENERATION.md) | Community Summary Generation | RESOLVED | Sprint 77 | 2025-12-04 |
| [TD-059](TD-059_RERANKING_DISABLED_CONTAINER.md) | Reranking via Ollama (bge-reranker-v2-m3) | RESOLVED | Sprint 48 | 2025-12-18 |
| [TD-060](TD-060_UNIFIED_CHUNK_IDS.md) | Unified Chunk/Document IDs | RESOLVED | Sprint 42 | 2025-12-10 |
| [TD-061](TD-061_OLLAMA_GPU_DOCKER_CONFIG.md) | Ollama Container GPU Config | RESOLVED | Sprint 42 | 2025-12-10 |
| [TD-062](TD-062_MULTI_CRITERIA_ENTITY_DEDUPLICATION.md) | Multi-Criteria Entity Deduplication | COMPLETE | Sprint 43 | 2025-12-11 |
| [TD-063](TD-063_RELATION_DEDUPLICATION.md) | Relation Deduplication (Semantic + NLP) | RESOLVED | Sprint 49 | 2025-12-16 |
| [TD-067](TD-067_DATASET_ANNOTATION_TOOL.md) | Dataset Annotation Tool for Domain Training (BACKLOG) | DEFERRED | Sprint 121 | 2026-01-27 |
| [TD-068](TD-068_CLOUD_LLM_SUPPORT.md) | Cloud LLM Support (Partial - via ADR-033) | DEFERRED | Sprint 121 | 2026-01-27 |
| [TD-069](TD-069_MULTIHOP_ENDPOINT_REVIEW.md) | Multi-Hop Endpoint Review | RESOLVED | Sprint 72 | 2025-12-04 |
| [TD-070](TD-070_INGESTION_PERFORMANCE_TUNING.md) | Ingestion Performance Tuning (77% faster) | RESOLVED | Sprint 121 | 2026-01-27 |
| [TD-071](TD-071_VLLM_VS_OLLAMA_INVESTIGATION.md) | vLLM vs Ollama Investigation | RESOLVED | Sprint 72 | 2025-12-04 |
| [TD-072](TD-072_SENTENCE_TRANSFORMERS_RERANKING.md) | Sentence Transformers Reranking | RESOLVED | Sprint 72 | 2025-12-04 |
| [TD-073](TD-073_SENTENCE_TRANSFORMERS_EMBEDDINGS.md) | Sentence Transformers Embeddings | RESOLVED | Sprint 72 | 2025-12-04 |
| [TD-074](TD-074_BM25_CACHE_DISCREPANCY.md) | BM25 Cache Discrepancy | RESOLVED | Sprint 87 (BGE-M3 replacement) | 2026-01-27 |
| [TD-075](TD-075_VLM_CHUNKING_INTEGRATION.md) | VLM Chunking Integration | RESOLVED | Sprint 77 | 2025-12-04 |
| [TD-076](TD-076_DOMAIN_CREATION_VALIDATION.md) | Domain Creation UX & Validation Issues (DSPy Training Mock) | DEFERRED | Sprint 121 | 2026-01-27 |
| [TD-077](TD-077_VLM_ADMIN_UI_INTEGRATION.md) | VLM Admin UI Integration | RESOLVED | Sprint 77 | 2025-12-04 |
| [TD-078-Phase2-Implementation](TD-078-Phase2-Implementation.md) | Section Extraction Performance Phase 2 Implementation | RESOLVED | Sprint 121 | 2026-01-27 |
| [TD-078_SECTION_EXTRACTION_PERFORMANCE](TD-078_SECTION_EXTRACTION_PERFORMANCE.md) | Section Extraction Performance | RESOLVED | Sprint 121 | 2026-01-27 |
| [TD-079](TD-079_LLM_INTENT_CLASSIFIER_CLARA.md) | LLM Intent Classifier (C-LARA SetFit 95.22%) | RESOLVED | Sprint 81 | 2026-01-08 |
| [TD-080](TD-080_CONTEXT_RELEVANCE_GUARD.md) | Context Relevance Guard | RESOLVED | Sprint 92 | 2026-01-27 |
| [TD-081-MEM0-INTEGRATION-GAP](TD-081-MEM0-INTEGRATION-GAP.md) | mem0 Integration Gap (Deferred 3x) | DEFERRED | Sprint 121 | 2026-01-27 |
| [TD-082-FRONTEND-CODE-SPLITTING](TD-082-FRONTEND-CODE-SPLITTING.md) | Frontend Code-Splitting & Bundle Size Optimization | DEFERRED | Sprint 121 | 2026-01-27 |
| [TD-083_IMPLEMENTATION](TD-083_IMPLEMENTATION.md) | Intent Classifier Implementation Detail | RESOLVED | Sprint 81 | 2025-12-04 |
| [TD-083_SETFIT_INTENT_CLASSIFIER_TRAINING](TD-083_SETFIT_INTENT_CLASSIFIER_TRAINING.md) | SetFit Intent Classifier Training | RESOLVED | Sprint 81 | 2025-12-04 |
| [TD-084_NAMESPACE_ISOLATION_IN_INGESTION_ORIGINAL](TD-084_NAMESPACE_ISOLATION_IN_INGESTION_ORIGINAL.md) | Namespace Isolation (Original) | RESOLVED | Sprint 76 | 2025-12-04 |
| [TD-084_NAMESPACE_ISOLATION_RESOLVED_SPRINT76](TD-084_NAMESPACE_ISOLATION_RESOLVED_SPRINT76.md) | Namespace Isolation (Resolved Sprint 76) | RESOLVED | Sprint 76 | 2025-12-04 |
| [TD-085_DSPY_DOMAIN_PROMPTS_NOT_USED_IN_EXTRACTION_ORIGINAL](TD-085_DSPY_DOMAIN_PROMPTS_NOT_USED_IN_EXTRACTION_ORIGINAL.md) | DSPy Domain Prompts (Original) | RESOLVED | Sprint 76 | 2025-12-04 |
| [TD-085_DSPY_DOMAIN_PROMPTS_RESOLVED_SPRINT76](TD-085_DSPY_DOMAIN_PROMPTS_RESOLVED_SPRINT76.md) | DSPy Domain Prompts (Resolved Sprint 76) | RESOLVED | Sprint 76 | 2025-12-04 |
| [TD-086](TD-086_COMMUNITY_DETECTION_UI_CONFIGURATION.md) | Community Detection Parameter Configuration (Partially Superseded by Sprint 92 GDS Fix) | DEFERRED | Sprint 121 | 2026-01-27 |
| [TD-091](TD-091_CHUNK_COUNT_MISMATCH.md) | Chunk Count Mismatch (Qdrant vs Neo4j) | RESOLVED | Sprint 77 | 2026-01-07 |
| [TD-094](TD-094_COMMUNITY_SUMMARIZATION_BATCH_JOB.md) | Community Summarization Batch Job | RESOLVED | Sprint 77 | 2026-01-07 |
| [TD-095](TD-095_ENTITY_CONNECTIVITY_DOMAIN_METRIC.md) | Entity Connectivity as Domain Training Metric | RESOLVED | Sprint 77 | 2026-01-07 |
| [TD-096](TD-096_CHUNKING_PARAMS_UI_INTEGRATION.md) | Chunking Params UI Integration | RESOLVED | Sprint 80 | 2025-12-04 |
| [TD-097](TD-097_SPRINT80_SETTINGS_UI_INTEGRATION.md) | Sprint 80 Settings UI Integration | RESOLVED | Sprint 80 | 2025-12-04 |
| [TD-099](TD-099_NAMESPACE_INGESTION_BUG.md) | Namespace Not Set During RAGAS Ingestion | RESOLVED | Sprint 81 | 2026-01-08 |
| [TD-100](TD-100_GLEANING_MULTI_PASS_EXTRACTION.md) | Gleaning Multi-Pass Extraction | RESOLVED | Sprint 83 | 2025-12-04 |
| [TD-101_COMMUNITY_SUMMARIZATION_BOTTLENECK](TD-101_COMMUNITY_SUMMARIZATION_BOTTLENECK.md) | Community Summarization Performance Bottleneck (TD Number Collision) | DEFERRED | Sprint 121 | 2026-01-27 |
| [TD-103](TD-103_BM25_INDEX_DESYNC.md) | BM25 Index Desync | RESOLVED | Sprint 87 (BGE-M3 replacement) | 2026-01-27 |
| [TD-104](TD-104_LIGHTRAG_CRUD_FEATURE_GAP.md) | LightRAG CRUD Feature Gap (GDPR Article 17 Compliance) | RESOLVED | Sprint 121 | 2026-01-27 |
| [TD_DEAD_CODE_STRATEGY](TD_DEAD_CODE_STRATEGY.md) | Dead Code Elimination Strategy (One-time sprint plan) | STRATEGY DOC | Sprint 71 | 2026-01-27 |
| [TD_TECH_DEBT](TD_TECH_DEBT.md) | Legacy Technical Debt Register (Superseded by TD_INDEX.md) | STRATEGY DOC | N/A | 2026-01-27 |

---

## Archive by Category

### Bug Fixes & Architecture Migrations
- TD-043: Follow-up Questions Redis storage issue
- TD-044: DoclingParsedDocument Interface (obsolete - section extraction working)
- TD-045: entity_id Property Migration (LightRAG alignment)
- TD-050: Duplicate Answer Streaming (React infinite loop fix)
- TD-061: Ollama GPU access in Docker
- TD-074: BM25 Cache Discrepancy (RESOLVED Sprint 87 via BGE-M3 native sparse vectors)
- TD-099: Namespace Not Set During RAGAS Ingestion
- TD-103: BM25 Index Desync (RESOLVED Sprint 87 via BGE-M3)
- TD-084: Namespace Isolation in Ingestion
- TD-085: DSPy Domain Prompts Not Used in Extraction

### Feature Implementations (Delivered)
- TD-046: RELATES_TO Relationship Extraction (semantic relationships)
- TD-048: Graph Extraction with Unified Chunks (provenance tracking)
- TD-052: User Document Upload (fast upload + background refinement)
- TD-057: 4-Way Hybrid RRF with Intent-Weighted Retrieval
- TD-058: Community Summary Generation (batch job)
- TD-059: Reranking via Ollama (BGE-Reranker integration)
- TD-060: Unified Chunk IDs between Qdrant and Neo4j
- TD-062: Multi-Criteria Entity Deduplication
- TD-063: Relation Deduplication (Semantic + NLP)
- TD-069: Multi-Hop Endpoint Review
- TD-070: Ingestion Performance Tuning (77% faster, 170s→38.5s)
- TD-071: vLLM vs Ollama Investigation
- TD-072: Sentence Transformers Reranking
- TD-073: Sentence Transformers Embeddings
- TD-075: VLM Chunking Integration
- TD-077: VLM Admin UI Integration
- TD-078: Section Extraction Performance Phase 2 (tokenizer cache + parallel)
- TD-079: LLM Intent Classifier (C-LARA SetFit 95.22% accuracy)
- TD-080: Context Relevance Guard (Sprint 92)
- TD-083: SetFit Intent Classifier Training & Implementation
- TD-091: Chunk Count Mismatch (Qdrant vs Neo4j)
- TD-094: Community Summarization Batch Job
- TD-095: Entity Connectivity as Domain Training Metric
- TD-096: Chunking Params UI Integration
- TD-097: Sprint 80 Settings UI Integration
- TD-100: Gleaning Multi-Pass Extraction
- TD-104: LightRAG CRUD Feature Gap (5 REST endpoints, GDPR Article 17 compliance)

### Deferred/Backlog Items (Lower Priority)
- TD-049: Implicit User Profiling (Sprint 17 era, never prioritized, 21 SP)
- TD-051: Memory Consolidation Pipeline (Sprint 9 era, never prioritized, 21 SP)
- TD-053: Admin Dashboard Full Implementation (Sprint 11 era, partially superseded, 34 SP)
- TD-067: Dataset Annotation Tool (BACKLOG, no timeline, external tooling alternative)
- TD-068: Cloud LLM Support (partially done via ADR-033 AegisLLMProxy, remaining scope deferred)
- TD-076: Domain Creation UX & Validation (DSPy training mock, not functional, deferred)
- TD-081: mem0 Integration Gap (deferred 3x, low demand, optional feature)
- TD-082: Frontend Code-Splitting & Bundle Size (performance optimization, medium priority)
- TD-086: Community Detection UI Configuration (partially superseded by Sprint 92 GDS fix)
- TD-101: Community Summarization Performance Bottleneck (CRITICAL but deferred, TD number collision issue)

### Strategy & Reference Documents
- TD_TECH_DEBT.md: Legacy technical debt register (superseded by active TD_INDEX.md)
- TD_DEAD_CODE_STRATEGY.md: One-time sprint strategy document from Sprint 71 (work completed)

---

## Archive by Sprint

### Sprint 34-35
- TD-045: entity_id Property Migration (Sprint 34)
- TD-043: Follow-up Questions Redis Fix (Sprint 35)

### Sprint 42-43
- TD-057: 4-Way Hybrid RRF (Sprint 42)
- TD-046: RELATES_TO Relationship Extraction (Sprint 42)
- TD-060: Unified Chunk IDs (Sprint 42)
- TD-061: Ollama GPU Docker (Sprint 42)
- TD-062: Multi-Criteria Entity Deduplication (Sprint 43)

### Sprint 47-49
- TD-050: Duplicate Answer Streaming (Sprint 47)
- TD-059: Reranking via Ollama (Sprint 48)
- TD-048: Graph Extraction with Unified Chunks (Sprint 49)
- TD-063: Relation Deduplication (Sprint 49)

### Sprint 71-72
- TD-047: Critical Path E2E Tests (Sprint 71)
- TD-069: Multi-Hop Endpoint Review (Sprint 72)
- TD-071: vLLM vs Ollama (Sprint 72)
- TD-072: Sentence Transformers Reranking (Sprint 72)
- TD-073: Sentence Transformers Embeddings (Sprint 72)

### Sprint 76-77
- TD-084: Namespace Isolation (Sprint 76)
- TD-085: DSPy Domain Prompts (Sprint 76)
- TD-075: VLM Chunking Integration (Sprint 77)
- TD-077: VLM Admin UI Integration (Sprint 77)
- TD-058: Community Summary Generation (Sprint 77)
- TD-091: Chunk Count Mismatch (Sprint 77)
- TD-094: Community Summarization Batch Job (Sprint 77)
- TD-095: Entity Connectivity Metric (Sprint 77)

### Sprint 80-81
- TD-096: Chunking Params UI Integration (Sprint 80)
- TD-097: Sprint 80 Settings UI Integration (Sprint 80)
- TD-079: C-LARA SetFit Intent Classifier (Sprint 81)
- TD-083: Intent Classifier Implementation (Sprint 81)
- TD-099: Namespace Ingestion Bug (Sprint 81)

### Sprint 83
- TD-044: DoclingParsedDocument Interface (obsolete)
- TD-052: User Document Upload
- TD-100: Gleaning Multi-Pass Extraction

### Sprint 87
- TD-074: BM25 Cache Discrepancy (resolved via BGE-M3 native sparse vectors)
- TD-103: BM25 Index Desync (resolved via BGE-M3 native hybrid search)

### Sprint 92
- TD-080: Context Relevance Guard

### Sprint 121 Cleanup (2026-01-27)
**15 additional items archived this sprint:**

**Previously Resolved (5 items moved from active in Sprint 121):**
- TD-070: Ingestion Performance Tuning (3 SP, verified 77% faster)
- TD-078: Section Extraction Performance Phase 2 (11 SP, tokenizer cache + parallel)
- TD-104: LightRAG CRUD Feature Gap (14 SP, GDPR compliance)

**Deferred Backlog Items (10 items):**
- TD-049: Implicit User Profiling (21 SP, Feature 17.4)
- TD-051: Memory Consolidation Pipeline (21 SP, Feature 9)
- TD-053: Admin Dashboard Full (34 SP, Feature 11)
- TD-067: Dataset Annotation Tool (BACKLOG)
- TD-068: Cloud LLM Support (partial via ADR-033)
- TD-076: Domain Creation Validation (DSPy mock, 5 SP)
- TD-081: mem0 Integration Gap (deferred 3x, 13-21 SP)
- TD-082: Frontend Code-Splitting (4-5 hours)
- TD-086: Community Detection UI Configuration (8 SP)
- TD-101: Community Summarization Bottleneck (21 SP, number collision)

**Strategy Documents (2 items):**
- TD_TECH_DEBT.md: Legacy register
- TD_DEAD_CODE_STRATEGY.md: One-time sprint strategy

---

## Historical Notes

### Sprint 51 Archival
TD-045 and TD-059 were discovered resolved and added to archive during Sprint 51 technical debt review (December 18, 2025).

### Sprint 77 Archival
TD-091 (chunk count mismatch), TD-094 (community summarization), TD-095 (entity connectivity) resolved during Sprint 77 graph optimization (January 7, 2026).

### Sprint 81 Archival
TD-079 (C-LARA SetFit classifier 95.22% accuracy) and TD-099 (namespace ingestion bug) resolved during Sprint 81 (January 8, 2026).

### Sprint 83 Archival
TD-044 (DoclingParsedDocument interface - obsolete), TD-046 (RELATES_TO extraction - ADR-040), TD-052 (user upload - Feature 83.4) archived during Sprint 83 technical debt cleanup (January 10, 2026).

### Sprint 121 Major Cleanup (2026-01-27)
**15 additional TDs archived:**

**Resolved TDs (5 items, 44 SP total):**
1. **TD-054** (6 SP): Unified Chunking Service — ChunkingService (775 lines) deleted, production uses adaptive_chunking.py. -1,727 lines removed.
2. **TD-055** (10 SP): MCP Client Implementation — Tool detection default changed from `hybrid` to `llm`. Enhanced bilingual prompts, 9 skill triggers configured.
3. **TD-070** (3 SP): Ingestion Performance Tuning — Verified: 170s→38.5s (77% faster). Graph extraction 162s→31.2s (81% faster). Ollama GPU fix confirmed.
4. **TD-078** (11 SP): Section Extraction Performance Phase 2 — Tokenizer singleton cache (thread-safe double-check locking) + ThreadPoolExecutor batch tokenization (4 workers).
5. **TD-104** (14 SP): LightRAG CRUD Feature Gap — 5 REST endpoints, 9 Pydantic models, GDPR Article 17 compliance. EntityManagementPage frontend.

**Deferred Backlog TDs (10 items):**
- **TD-049** (21 SP): Implicit User Profiling — Feature 17.4, orphaned since Sprint 17 era, no recent demand
- **TD-051** (21 SP): Memory Consolidation Pipeline — Feature 9, orphaned, 3-layer memory consolidation never prioritized
- **TD-053** (34 SP): Admin Dashboard Full — Feature 11, orphaned, partially superseded by smaller admin features
- **TD-067**: Dataset Annotation Tool — BACKLOG, external tooling alternatives exist (Label Studio, Argilla)
- **TD-068** (13 SP): Cloud LLM Support — Partially via ADR-033 (AegisLLMProxy multi-cloud routing), remaining scope low priority
- **TD-076** (5 SP): Domain Creation Validation — DSPy training implementation is mock/stub, not functional (6 critical bugs found)
- **TD-081** (13-21 SP): mem0 Integration Gap — Deferred 3x (Sprint 21, Sprint 59, Sprint 72), low user demand, optional feature
- **TD-082** (4-5 hours): Frontend Code-Splitting — Bundle optimization, medium priority, 66% size reduction possible
- **TD-086** (8 SP): Community Detection UI Configuration — Partially superseded by Sprint 92 GDS community detection fix (2,387 communities)
- **TD-101** (21 SP): Community Summarization Bottleneck — CRITICAL performance issue (95% singleton communities), deferred due to competing demands

**Strategy Documents (2 items):**
- **TD_TECH_DEBT.md**: Legacy technical debt register, superseded by active TD_INDEX.md
- **TD_DEAD_CODE_STRATEGY.md**: One-time sprint strategy doc from Sprint 71, work completed, archived for reference

---

## Retrieval & Reference

Items in this archive may be referenced for:
- Historical context on past decisions
- Documentation of resolution approaches
- Learning from previous bug fixes
- Code archaeology when debugging related issues
- Understanding deferred features and their rationale

---

## Deferral Rationale

### Why Items Were Deferred (Sprint 121 Analysis)

1. **Lower Priority:** TD-049, TD-051, TD-053 are feature-gap items from early sprints (9-17) that never gained momentum
2. **Backlog Items:** TD-067 has better alternatives (Label Studio, Argilla); AD-068 partially addressed via ADR-033
3. **Non-Functional Features:** TD-076 identified as mock implementation (6 critical bugs), requires redesign
4. **Deferred 3x:** TD-081 (mem0) deferred in Sprint 21, 59, 72 — indicates low organizational demand
5. **Performance Optimizations:** TD-082, TD-086 are enhancements, not blocking issues
6. **Competing Demands:** TD-101 (critical performance) deferred due to higher-priority work in Sprint 121

---

**Document maintained by:** Documentation Agent
**Archive created:** 2025-12-16
**Last updated:** 2026-01-27 (Sprint 121 — Full archive consolidation, 59 total items)
