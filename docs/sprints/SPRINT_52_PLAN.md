# Sprint 52 Plan

## Sprint Overview

| Field | Value |
|-------|-------|
| Sprint Number | 52 |
| Start Date | 2025-12-19 |
| Duration | 5 days |
| Total Story Points | 31 SP |
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

#### Phase 2: Summary Generation + Admin Config (8 SP)
- [ ] `generate_community_summary()` mit LLM via AegisLLMProxy
- [ ] `CommunitySummary` Node in Neo4j
- [ ] Summary-Prompt Template (entity names, relationships, keywords)
- [ ] Integration in Maximum Hybrid Search Graph Global
- [ ] **Admin LLM Config:** Dropdown to select model for summary generation
- [ ] Store selected model in settings (localStorage + API)

**Files:**
- `src/components/graph_rag/community_summarizer.py` (NEW)
- `src/components/retrieval/maximum_hybrid_search.py` (UPDATE)
- `frontend/src/pages/admin/AdminLLMConfigPage.tsx` (UPDATE - add summary model selector)
- `src/api/v1/admin.py` (UPDATE - add summary model config endpoint)
- `tests/unit/components/graph_rag/test_community_summarizer.py` (NEW)

**Neo4j Schema Extension:**
```cypher
CREATE CONSTRAINT community_summary_unique
FOR (cs:CommunitySummary)
REQUIRE cs.community_id IS UNIQUE;
```

**Note:** Temporal Summaries (bi-temporal storage, time-travel queries) deferred to TD-064.

**Cost Impact:**
- Without Delta-Tracking: ~50 LLM calls per ingestion
- With Delta-Tracking: ~3-5 LLM calls (90% savings)
- Cost per Summary: ~$0.01-0.05 (Ollama local = $0)

---

### Feature 52.2: Admin Dashboard Phase 1 (TD-053) - 10 SP

**Priority:** MEDIUM - Improves operability

Continue Admin Dashboard implementation from Sprint 51.

#### 52.2.1: Graph Analytics Page (5 SP)
- [ ] Entity/Relationship counts visualization
- [ ] Community statistics (size distribution, member counts)
- [ ] Graph health metrics (orphan nodes, disconnected components)
- [ ] Community summary status (generated/pending)

**Files:**
- `frontend/src/pages/admin/GraphAnalyticsPage.tsx` (UPDATE)
- `src/api/v1/admin.py` (UPDATE - add graph stats endpoint)
- `tests/e2e/test_e2e_graph_analytics.py` (NEW)

#### 52.2.2: Domain Management Enhancement (5 SP)
- [ ] Domain detail view (documents, chunks, entities per domain)
- [ ] Domain health status (indexing progress, errors)
- [ ] Bulk operations (re-index, validate)

**Files:**
- `frontend/src/components/admin/DomainDetailDialog.tsx` (UPDATE)
- `frontend/src/pages/admin/DomainTrainingPage.tsx` (UPDATE)
- `src/api/v1/domain_training.py` (UPDATE)

---

### Feature 52.3: Async Follow-up Questions (TD-043) - 5 SP

**Priority:** LOW - Nice-to-have for UX

Implement session-aware follow-up question generation **asynchronously** after the answer appears.

**Key Requirement:** Follow-up generation must NOT block or delay the answer display.

#### Implementation:
- [ ] Store conversation context in Redis (TTL: 30 min)
- [ ] **Async generation:** Trigger follow-up generation AFTER answer is complete
- [ ] SSE event `followup_questions` sent separately from answer
- [ ] Display in chat UI below answer with loading skeleton
- [ ] Track which follow-ups were clicked

**Flow:**
```
User Query → Answer Streams → Answer Complete → [Async] Generate Follow-ups → SSE followup_questions → UI Update
```

**Files:**
- `src/agents/followup_generator.py` (UPDATE - async generation)
- `src/agents/coordinator.py` (UPDATE - emit followup_questions event after answer)
- `frontend/src/components/chat/FollowUpQuestions.tsx` (UPDATE - loading state)
- `frontend/src/hooks/useStreamChat.ts` (UPDATE - handle followup_questions event)
- `tests/unit/agents/test_followup_generator.py` (NEW)

---

### Feature 52.4: CI/CD Pipeline Optimization - 3 SP

**Priority:** MEDIUM - Technical debt

Review and optimize GitHub Actions workflows.

- [ ] Re-enable integration tests with proper mocking
- [ ] Add Ollama mock for CI environment
- [ ] Optimize test parallelization

**Files:**
- `.github/workflows/ci.yml` (UPDATE)
- `tests/integration/conftest.py` (UPDATE - add CI auto-mocking)

---

## Acceptance Criteria

### Feature 52.1 (Community Summaries)
- [ ] Delta-tracking correctly identifies new/updated/merged communities
- [ ] Summaries are generated only for affected communities (not all)
- [ ] Summaries improve LightRAG global mode retrieval quality
- [ ] **Admin can configure which LLM model to use for summaries**
- [ ] Cost per ingestion reduced by >80%

### Feature 52.2 (Admin Dashboard)
- [ ] Graph analytics show entity/relationship/community counts
- [ ] Domain detail view shows all associated data
- [ ] All new pages have E2E tests

### Feature 52.3 (Follow-up Questions)
- [ ] **Follow-up questions do NOT delay answer display**
- [ ] Follow-up questions appear after answer completes
- [ ] Loading skeleton shown while generating
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
| 52.3 | Redis Memory Layer (Sprint 7), SSE Streaming (Sprint 50) |
| 52.4 | None |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| LLM costs for summary generation | Delta-tracking, Ollama local first, admin config |
| Community instability after ingestion | Threshold for re-summarization |
| Follow-up latency perceived as slow | Loading skeleton, async pattern |
| CI complexity with mocked services | Gradual re-enablement |

---

## Parallel Execution Strategy

### Wave 1 (Day 1-2): Foundation
- **Agent 1:** Feature 52.1 Phase 1 (Delta-Tracking) + Phase 2 (Summary Generation)
- **Agent 2:** Feature 52.2.1 (Graph Analytics)
- **Agent 3:** Feature 52.4 (CI/CD)

### Wave 2 (Day 3-4): Core Implementation
- **Agent 1:** Feature 52.1 Admin LLM Config
- **Agent 2:** Feature 52.2.2 (Domain Management)
- **Agent 3:** Feature 52.3 (Async Follow-up Questions)

### Wave 3 (Day 5): Testing & Integration
- Full integration testing
- E2E tests for all new features
- Documentation updates

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
- TD-064: Temporal Community Summaries (NEW - deferred from this sprint)
- GraphRAG Paper (Edge et al., 2024): arXiv:2404.16130
- Sprint 51 Review Analysis
