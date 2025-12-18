# Sprint 52 Plan

## Sprint Overview

| Field | Value |
|-------|-------|
| Sprint Number | 52 |
| Start Date | 2025-12-19 |
| Duration | 5 days |
| Total Story Points | 34 SP |
| Focus | Community Summary Generation, Admin Dashboard, Technical Debt Cleanup |

## Carry-Over from Sprint 51

- TD-053 (Admin Dashboard) - IN_PROGRESS, Navigation complete

## Features

### Feature 52.1: Community Summary Generation (TD-058) - 13 SP

**Priority:** HIGH - Required for Maximum Hybrid Search global mode optimization

Implement LLM-generated community summaries for semantic search over graph communities.

#### Phase 1: Delta-Tracking Infrastructure (5 SP)
- [ ] `CommunityDelta` dataclass für Change-Tracking
- [ ] `track_community_changes()` nach Community Detection
- [ ] Logging der betroffenen Communities
- [ ] Unit Tests für Delta-Tracking

**Files:**
- `src/components/graph_rag/community_delta_tracker.py` (NEW)
- `src/components/graph_rag/community_detector.py` (UPDATE)
- `tests/unit/components/graph_rag/test_community_delta_tracker.py` (NEW)

#### Phase 2: Summary Generation (5 SP)
- [ ] `generate_community_summary()` mit LLM via AegisLLMProxy
- [ ] `CommunitySummary` Node in Neo4j
- [ ] Summary-Prompt Template (entity names, relationships, keywords)
- [ ] Integration in Maximum Hybrid Search Graph Global

**Files:**
- `src/components/graph_rag/community_summarizer.py` (NEW)
- `src/components/retrieval/maximum_hybrid_search.py` (UPDATE)
- `tests/unit/components/graph_rag/test_community_summarizer.py` (NEW)

**Neo4j Schema Extension:**
```cypher
CREATE CONSTRAINT community_summary_unique
FOR (cs:CommunitySummary)
REQUIRE (cs.community_id, cs.valid_from) IS UNIQUE;

CREATE INDEX community_summary_temporal
FOR (cs:CommunitySummary)
ON (cs.community_id, cs.valid_from, cs.valid_to);
```

#### Phase 3: Temporal Summaries (3 SP)
- [ ] Bi-temporale Summary-Speicherung (valid_from/valid_to)
- [ ] `get_summary_at_timestamp()` mit Fallback-Regenerierung
- [ ] Caching-Strategie für häufige Zeiträume

**Files:**
- `src/components/graph_rag/temporal_summary_store.py` (NEW)
- `tests/unit/components/graph_rag/test_temporal_summary_store.py` (NEW)

**Cost Impact:**
- Without Delta-Tracking: ~50 LLM calls per ingestion
- With Delta-Tracking: ~3-5 LLM calls (90% savings)
- Cost per Summary: ~$0.01-0.05 (Ollama local = $0)

---

### Feature 52.2: Admin Dashboard Phase 1 (TD-053) - 13 SP

**Priority:** MEDIUM - Improves operability

Continue Admin Dashboard implementation from Sprint 51.

#### 52.2.1: Graph Analytics Page (5 SP)
- [ ] Entity/Relationship counts visualization
- [ ] Community statistics (size distribution, member counts)
- [ ] Graph health metrics (orphan nodes, disconnected components)
- [ ] Real-time updates via WebSocket

**Files:**
- `frontend/src/pages/admin/GraphAnalyticsPage.tsx` (UPDATE)
- `src/api/v1/admin.py` (UPDATE - add graph stats endpoint)
- `tests/e2e/test_e2e_graph_analytics.py` (NEW)

#### 52.2.2: Domain Management Enhancement (5 SP)
- [ ] Domain detail view (documents, chunks, entities per domain)
- [ ] Domain health status (indexing progress, errors)
- [ ] Bulk operations (re-index, validate, export)
- [ ] Domain comparison view

**Files:**
- `frontend/src/components/admin/DomainDetailDialog.tsx` (UPDATE)
- `frontend/src/pages/admin/DomainTrainingPage.tsx` (UPDATE)
- `src/api/v1/domain_training.py` (UPDATE)

#### 52.2.3: System Overview Dashboard (3 SP)
- [ ] Combined health view (all services)
- [ ] Recent activity feed
- [ ] Quick action buttons
- [ ] Alert summary

**Files:**
- `frontend/src/pages/admin/AdminDashboard.tsx` (UPDATE)
- `frontend/src/components/admin/SystemOverview.tsx` (NEW)

---

### Feature 52.3: Follow-up Questions via Redis (TD-043) - 5 SP

**Priority:** LOW - Nice-to-have for UX

Implement session-aware follow-up question generation.

- [ ] Store conversation context in Redis (TTL: 30 min)
- [ ] Generate contextual follow-up questions
- [ ] Display in chat UI below answer
- [ ] Track which follow-ups were clicked

**Files:**
- `src/agents/followup_generator.py` (UPDATE)
- `src/components/memory/redis_context_store.py` (NEW)
- `frontend/src/components/chat/FollowUpQuestions.tsx` (UPDATE)
- `tests/unit/components/memory/test_redis_context_store.py` (NEW)

---

### Feature 52.4: CI/CD Pipeline Optimization - 3 SP

**Priority:** MEDIUM - Technical debt

Review and optimize GitHub Actions workflows.

- [ ] Re-enable integration tests with proper mocking
- [ ] Add Ollama mock for CI environment
- [ ] Optimize test parallelization
- [ ] Add test result caching

**Files:**
- `.github/workflows/ci.yml` (UPDATE)
- `tests/integration/conftest.py` (UPDATE - add CI auto-mocking)

---

## Acceptance Criteria

### Feature 52.1 (Community Summaries)
- [ ] Delta-tracking correctly identifies new/updated/merged communities
- [ ] Summaries are generated only for affected communities (not all)
- [ ] Summaries improve LightRAG global mode retrieval quality
- [ ] Temporal summaries enable time-travel queries
- [ ] Cost per ingestion reduced by >80%

### Feature 52.2 (Admin Dashboard)
- [ ] Graph analytics show entity/relationship/community counts
- [ ] Domain detail view shows all associated data
- [ ] System overview provides at-a-glance health status
- [ ] All new pages have E2E tests

### Feature 52.3 (Follow-up Questions)
- [ ] Follow-up questions are contextually relevant
- [ ] Session context persists for 30 minutes
- [ ] Clicking follow-up pre-fills chat input

### Feature 52.4 (CI/CD)
- [ ] Integration tests run in CI (mocked LLM)
- [ ] CI pipeline completes in <15 minutes

---

## Dependencies

| Feature | Depends On |
|---------|------------|
| 52.1 | CommunityDetector fixes (Sprint 51) |
| 52.2 | Admin Navigation (Sprint 51) |
| 52.3 | Redis Memory Layer (Sprint 7) |
| 52.4 | None |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| LLM costs for summary generation | Delta-tracking, Ollama local first |
| Community instability after ingestion | Threshold for re-summarization |
| CI complexity with mocked services | Gradual re-enablement |

---

## Parallel Execution Strategy

### Wave 1 (Day 1-2): Foundation
- **Agent 1:** Feature 52.1 Phase 1 (Delta-Tracking)
- **Agent 2:** Feature 52.2.1 (Graph Analytics)
- **Agent 3:** Feature 52.4 (CI/CD)

### Wave 2 (Day 2-3): Core Implementation
- **Agent 1:** Feature 52.1 Phase 2 (Summary Generation)
- **Agent 2:** Feature 52.2.2 (Domain Management)

### Wave 3 (Day 4-5): Integration & Polish
- **Agent 1:** Feature 52.1 Phase 3 (Temporal Summaries)
- **Agent 2:** Feature 52.2.3 (System Overview)
- **Agent 3:** Feature 52.3 (Follow-up Questions)

---

## Definition of Done

- [ ] All features implemented and tested
- [ ] Unit test coverage >80% for new code
- [ ] Integration tests pass locally
- [ ] E2E tests for new UI components
- [ ] Documentation updated (TECH_STACK.md, CLAUDE.md if needed)
- [ ] No regressions in existing functionality
- [ ] Sprint summary written

---

## References

- TD-058: Community Summary Generation
- TD-053: Admin Dashboard Full Implementation
- TD-043: Follow-up Questions Redis
- GraphRAG Paper (Edge et al., 2024): arXiv:2404.16130
- Sprint 51 Review Analysis
