# Sprint 50: Comprehensive E2E Test Coverage with Playwright

**Status:** PLANNED
**Branch:** `sprint-50-e2e-tests`
**Start Date:** 2025-12-17
**Estimated Duration:** 8-10 Tage (2 Wochen)
**Total Story Points:** 72 SP

---

## Sprint Overview

Sprint 50 fokussiert auf **vollständige End-to-End Test-Abdeckung** für alle kritischen User Journeys. Nach erfolgreicher Implementierung von Sprint 49 (Provenance Tracking & BGE-M3 Consolidation) haben wir bereits 3 E2E-Tests:

- ✅ `test_e2e_document_ingestion_workflow.py` (Document Upload → Query)
- ✅ `test_e2e_hybrid_search_quality.py` (Search Quality Validation)
- ✅ `test_e2e_sprint49_features.py` (Sprint 49 Features)

**Ziel:** Implementierung der 9 fehlenden E2E-Tests für vollständige Abdeckung aller User Journeys.

**Strategie:** Parallele Subagenten für schnelle Umsetzung (3 Teams à 3 Tests).

---

## Current State Analysis

### Bestehende E2E-Tests (3)
- `test_e2e_document_ingestion_workflow.py` (495 lines) - Upload, Indexing, Query, Citations
- `test_e2e_hybrid_search_quality.py` (457 lines) - BM25, Vector, Hybrid Search
- `test_e2e_sprint49_features.py` (409 lines) - Index Consistency, Deduplication, Provenance

### Test-Infrastruktur
- ✅ Playwright (^1.57.0) installiert
- ✅ `tests/e2e/conftest.py` mit Browser-Fixtures
- ✅ `tests/e2e/README.md` mit Dokumentation
- ✅ Chromium Browser installiert
- ✅ Function-scoped fixtures für pytest-asyncio

### Fehlende E2E-Tests (9)
Siehe [USER_JOURNEYS_AND_TEST_PLAN.md](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md) für detaillierte Beschreibungen.

---

## Features

| # | Feature | SP | Priority | Dependencies | Team |
|---|---------|-----|----------|--------------|------|
| 50.1 | Domain Creation Workflow | 8 | P0 | - | Team A |
| 50.2 | Upload Page Domain Classification | 5 | P0 | - | Team A |
| 50.3 | Graph Exploration Workflow | 13 | P0 | - | Team A |
| 50.4 | Chat Streaming & Citations | 8 | P0 | - | Team B |
| 50.5 | Session Management | 8 | P1 | - | Team B |
| 50.6 | Community Detection Workflow | 8 | P1 | - | Team B |
| 50.7 | Cost Monitoring Workflow | 5 | P2 | - | Team C |
| 50.8 | Health Monitoring | 3 | P2 | - | Team C |
| 50.9 | Indexing Pipeline Monitoring | 8 | P2 | - | Team C |
| 50.10 | Test Infrastructure Improvements | 6 | P1 | All | Team C |

**Total: 72 SP**

---

## Feature Details

### Feature 50.1: Domain Creation Workflow (8 SP)
**Priority:** P0
**Team:** Team A (Backend Agent)
**Reference:** [USER_JOURNEYS_AND_TEST_PLAN.md - Journey 1](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md#journey-1-admin-setup--domain-creation)

**Ziel:** E2E-Test für vollständigen Domain Creation Workflow mit DSPy Training.

**Test-Szenario:**
```python
class TestDomainCreationWorkflow:
    """Test complete domain creation workflow with DSPy training."""

    async def test_complete_domain_creation_workflow(
        self,
        page: Page,
        sample_training_dataset: Path
    ):
        """
        Steps:
        1. Navigate to /admin/domain-training
        2. Click "New Domain" button
        3. Fill domain config (name, description, LLM model)
        4. Upload training dataset (JSON with query-answer pairs)
        5. Start training and monitor SSE logs
        6. Verify domain appears in list with "ready" status
        7. Validate training metrics displayed
        """
```

**Fixtures Needed:**
- `sample_training_dataset` - JSON file with 10-20 training examples

**Validation Points:**
- [ ] Domain creation form works
- [ ] Training dataset upload successful
- [ ] SSE training logs display in real-time
- [ ] Training completes without errors
- [ ] Domain appears in list with "ready" status
- [ ] Training metrics visible (loss, validation score)

**Files to Create:**
- `tests/e2e/test_e2e_domain_creation_workflow.py`
- `tests/e2e/fixtures/training_datasets.py` (fixtures)

**Acceptance Criteria:**
- [ ] Test passes with valid training dataset
- [ ] Test fails correctly with invalid dataset
- [ ] SSE streaming validated
- [ ] Domain persistence verified

---

### Feature 50.2: Upload Page Domain Classification (5 SP)
**Priority:** P0
**Team:** Team A (Backend Agent)
**Reference:** [USER_JOURNEYS_AND_TEST_PLAN.md - Journey 2](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md#journey-2-document-upload--ingestion)

**Ziel:** E2E-Test für Document Upload mit AI-powered Domain Classification.

**Test-Szenario:**
```python
class TestUploadPageDomainClassification:
    """Test document upload with automatic domain classification."""

    async def test_document_upload_with_domain_classification(
        self,
        page: Page,
        sample_documents_various_domains: list[Path]
    ):
        """
        Steps:
        1. Navigate to /admin/upload
        2. Upload documents (legal, medical, technical)
        3. Wait for AI classification (DSPy)
        4. Verify domain suggestions with confidence scores
        5. Override one domain manually
        6. Submit upload
        7. Validate documents indexed with correct domains
        """
```

**Fixtures Needed:**
- `sample_documents_various_domains` - Legal, medical, technical documents

**Validation Points:**
- [ ] File upload works
- [ ] Domain suggestions appear
- [ ] Confidence badges displayed (High/Medium/Low)
- [ ] Manual domain override works
- [ ] Documents indexed with correct domains

**Files to Create:**
- `tests/e2e/test_e2e_upload_page_domain_classification.py`
- `tests/e2e/fixtures/sample_documents.py`

---

### Feature 50.3: Graph Exploration Workflow (13 SP)
**Priority:** P0
**Team:** Team A (Backend Agent)
**Reference:** [USER_JOURNEYS_AND_TEST_PLAN.md - Journey 4](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md#journey-4-knowledge-graph-exploration)

**Ziel:** E2E-Test für vollständige Knowledge Graph Exploration.

**Test-Szenario:**
```python
class TestGraphExplorationWorkflow:
    """Test complete graph exploration workflow."""

    async def test_complete_graph_exploration_workflow(
        self,
        page: Page,
        indexed_graph_documents: list[Path],
        neo4j_driver
    ):
        """
        Steps:
        1. Upload documents to create graph
        2. Navigate to /admin/graph
        3. View graph statistics (nodes, edges, communities)
        4. Apply filters (entity types, min degree)
        5. Search for entity (e.g., "Andrew Ng")
        6. View node details panel
        7. Explore communities
        8. Export graph (GraphML/JSON)
        """
```

**Fixtures Needed:**
- `indexed_graph_documents` - Documents forming interesting graph (Stanford AI Lab, Google Brain, Deep Learning pioneers)
- `neo4j_driver` - Neo4j connection for validation

**Validation Points:**
- [ ] Graph renders without errors
- [ ] Statistics show correct counts
- [ ] Filters apply successfully
- [ ] Entity search works
- [ ] Node details panel displays
- [ ] Communities highlightable
- [ ] Export functionality works

**Files to Create:**
- `tests/e2e/test_e2e_graph_exploration_workflow.py`
- `tests/e2e/fixtures/graph_data.py`

**Acceptance Criteria:**
- [ ] Graph visualization loads
- [ ] All filters functional
- [ ] Export generates valid files
- [ ] Performance < 5s render time

---

### Feature 50.4: Chat Streaming & Citations (8 SP)
**Priority:** P0
**Team:** Team B (Frontend Agent)
**Reference:** [USER_JOURNEYS_AND_TEST_PLAN.md - Journey 3](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md#journey-3-hybrid-search--query)

**Ziel:** E2E-Test für Chat Interface mit Streaming Responses und Citations.

**Test-Szenario:**
```python
class TestChatStreamingAndCitations:
    """Test chat interface with streaming responses and citations."""

    async def test_chat_with_streaming_and_citations(
        self,
        page: Page,
        indexed_documents: list[Path]
    ):
        """
        Steps:
        1. Navigate to chat page (/)
        2. Enter query
        3. Watch streaming response (phase indicators)
        4. Verify citations appear
        5. Click citation to view source
        6. Check follow-up questions
        7. Test session persistence after refresh
        """
```

**Validation Points:**
- [ ] Query submission works
- [ ] Streaming response displays
- [ ] Phase indicators show (Sprint 48)
- [ ] Citations appear
- [ ] Citation panel opens with source text
- [ ] Follow-up questions suggested
- [ ] Session persists after refresh

**Files to Create:**
- `tests/e2e/test_e2e_chat_streaming_and_citations.py`

---

### Feature 50.5: Session Management (8 SP)
**Priority:** P1
**Team:** Team B (Frontend Agent)
**Reference:** [USER_JOURNEYS_AND_TEST_PLAN.md - Journey 7](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md#journey-7-session-management--history)

**Ziel:** E2E-Test für Session Management Features.

**Test-Szenario:**
```python
class TestSessionManagement:
    """Test session management and history features."""

    async def test_session_management_workflow(
        self,
        page: Page
    ):
        """
        Steps:
        1. Create new chat session
        2. View session in sidebar
        3. Rename session
        4. Create second session
        5. Switch between sessions
        6. Archive session
        7. Share session (generate link)
        8. Delete session
        """
```

**Validation Points:**
- [ ] Session creation works
- [ ] Sessions appear in sidebar
- [ ] Session rename functional
- [ ] Session switching loads correct conversation
- [ ] Archive moves to archived list
- [ ] Share generates valid link
- [ ] Delete removes session

**Files to Create:**
- `tests/e2e/test_e2e_session_management.py`

---

### Feature 50.6: Community Detection Workflow (8 SP)
**Priority:** P1
**Team:** Team B (Frontend Agent)
**Reference:** [USER_JOURNEYS_AND_TEST_PLAN.md - Journey 5](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md#journey-5-community-detection--analysis)

**Ziel:** E2E-Test für Community Detection und Analysis.

**Test-Szenario:**
```python
class TestCommunityDetectionWorkflow:
    """Test community detection and analysis workflow."""

    async def test_community_detection_and_analysis(
        self,
        page: Page,
        neo4j_driver
    ):
        """
        Steps:
        1. Navigate to graph analytics
        2. View community list
        3. Select community
        4. Analyze community composition
        5. View community documents
        6. Validate semantic coherence
        """
```

**Validation Points:**
- [ ] Communities detected in Neo4j
- [ ] Community list displays
- [ ] Community selection highlights graph
- [ ] Community stats shown
- [ ] Documents linked to community
- [ ] Semantic coherence validated

**Files to Create:**
- `tests/e2e/test_e2e_community_detection_workflow.py`

---

### Feature 50.7: Cost Monitoring Workflow (5 SP)
**Priority:** P2
**Team:** Team C (API Agent)
**Reference:** [USER_JOURNEYS_AND_TEST_PLAN.md - Journey 8](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md#journey-8-cost-monitoring--llm-configuration)

**Ziel:** E2E-Test für Cost Dashboard und LLM Configuration.

**Test-Szenario:**
```python
class TestCostMonitoringWorkflow:
    """Test cost monitoring and LLM configuration."""

    async def test_cost_dashboard_display(
        self,
        page: Page
    ):
        """
        Steps:
        1. Navigate to /admin/costs
        2. View total costs
        3. Check cost by provider (Ollama, Alibaba, OpenAI)
        4. Verify budget alerts
        5. Navigate to /admin/llm-config
        6. Test LLM connection
        """
```

**Validation Points:**
- [ ] Cost dashboard loads
- [ ] Total costs displayed
- [ ] Provider breakdown shown
- [ ] Budget alerts functional
- [ ] LLM config page loads
- [ ] Connection test works

**Files to Create:**
- `tests/e2e/test_e2e_cost_monitoring_workflow.py`

---

### Feature 50.8: Health Monitoring (3 SP)
**Priority:** P2
**Team:** Team C (API Agent)
**Reference:** [USER_JOURNEYS_AND_TEST_PLAN.md - Journey 9](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md#journey-9-system-health--monitoring)

**Ziel:** E2E-Test für System Health Monitoring.

**Test-Szenario:**
```python
class TestHealthMonitoring:
    """Test system health monitoring."""

    async def test_health_dashboard(
        self,
        page: Page
    ):
        """
        Steps:
        1. Navigate to /health
        2. View service status (Qdrant, Neo4j, Redis, Ollama)
        3. Check status indicators (green/red/yellow)
        4. Test service connections
        5. View error logs
        """
```

**Validation Points:**
- [ ] Health dashboard loads
- [ ] All services shown
- [ ] Status indicators correct
- [ ] Connection tests work
- [ ] Error logs displayed

**Files to Create:**
- `tests/e2e/test_e2e_health_monitoring.py`

---

### Feature 50.9: Indexing Pipeline Monitoring (8 SP)
**Priority:** P2
**Team:** Team C (API Agent)
**Reference:** [USER_JOURNEYS_AND_TEST_PLAN.md - Journey 10](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md#journey-10-indexing-management)

**Ziel:** E2E-Test für Indexing Pipeline Monitoring.

**Test-Szenario:**
```python
class TestIndexingPipelineMonitoring:
    """Test indexing pipeline monitoring."""

    async def test_indexing_pipeline_workflow(
        self,
        page: Page,
        sample_pdf: Path
    ):
        """
        Steps:
        1. Navigate to /admin/indexing
        2. View pipeline stages
        3. Trigger indexing
        4. Monitor SSE progress
        5. Check worker pool status
        6. Verify completion
        """
```

**Validation Points:**
- [ ] Indexing page loads
- [ ] Pipeline stages shown
- [ ] Indexing can be triggered
- [ ] Live logs display
- [ ] Worker pool status shown
- [ ] Completion detected

**Files to Create:**
- `tests/e2e/test_e2e_indexing_pipeline_monitoring.py`

---

### Feature 50.10: Test Infrastructure Improvements (6 SP)
**Priority:** P1
**Team:** Team C (Testing Agent)

**Ziel:** Verbesserungen der E2E Test-Infrastruktur für Stabilität und Performance.

**Improvements:**

1. **Test Data Management**
   - Shared test data fixtures
   - Cleanup utilities
   - Data generators

2. **Parallel Execution**
   - pytest-xdist integration
   - Test isolation improvements
   - Shared browser context optimization

3. **CI/CD Integration**
   - GitHub Actions workflow
   - Docker service configuration
   - Screenshot capture on failure
   - Video recording for debugging

4. **Debugging Tools**
   - Better error messages
   - Trace viewer integration
   - Network request logging
   - Performance profiling

**Tasks:**
- [ ] `tests/e2e/fixtures/` organization
- [ ] Shared data cleanup utilities
- [ ] CI/CD workflow in `.github/workflows/e2e.yml`
- [ ] Parallel execution configuration
- [ ] Trace viewer setup
- [ ] Performance baseline measurements

**Acceptance Criteria:**
- [ ] Tests run reliably in CI
- [ ] Parallel execution works
- [ ] Screenshots/videos on failure
- [ ] Performance baselines documented

---

## Architecture References

- **Sprint 49**: [Provenance Tracking & BGE-M3 Consolidation](SPRINT_49_PLAN.md)
- **Sprint 35**: [Frontend UX Enhancement](SPRINT_35_PLAN.md) (Chat Interface)
- **Sprint 45**: [Domain Training with DSPy](SPRINT_45_PLAN.md)
- **Sprint 46**: [Conversation UI & Domain Auto-Discovery](SPRINT_46_PLAN.md)
- **ADR-024**: [BGE-M3 Embeddings](../adr/ADR-024_BGE-M3-EMBEDDINGS.md)
- **USER_JOURNEYS_AND_TEST_PLAN.md**: [Complete User Journeys Documentation](../e2e/USER_JOURNEYS_AND_TEST_PLAN.md)

---

## Timeline (Parallel Execution with 3 Teams)

### Week 1 (Days 1-5)

**Team A (Backend Agent) - Graph & Domain Features:**
```
Day 1-2: Feature 50.1 (Domain Creation Workflow)
Day 2-3: Feature 50.2 (Upload Page Classification)
Day 3-5: Feature 50.3 (Graph Exploration Workflow)
```

**Team B (Frontend Agent) - Chat & Sessions:**
```
Day 1-2: Feature 50.4 (Chat Streaming & Citations)
Day 3-4: Feature 50.5 (Session Management)
Day 4-5: Feature 50.6 (Community Detection)
```

**Team C (API Agent) - Monitoring:**
```
Day 1: Feature 50.8 (Health Monitoring)
Day 2: Feature 50.7 (Cost Monitoring)
Day 3-4: Feature 50.9 (Indexing Pipeline Monitoring)
Day 5: Feature 50.10 (Test Infrastructure)
```

### Week 2 (Days 6-8)

**All Teams:**
```
Day 6: Integration Testing, Bug Fixes
Day 7: Performance Optimization, Flaky Test Fixes
Day 8: Documentation, Code Review, Final Validation
```

**Estimated Total:** 8 Tage mit paralleler Entwicklung (3 Teams)

---

## Parallel Agent Strategy

### Team A: Backend Agent
**Focus:** Backend-heavy features (Domain Creation, Graph Exploration)
**Tools:** Python, FastAPI, Neo4j, Qdrant, Playwright
**Output:** 3 E2E tests (26 SP)

### Team B: Frontend Agent
**Focus:** Frontend-heavy features (Chat, Sessions, Communities)
**Tools:** React, TypeScript, Playwright, DOM interaction
**Output:** 3 E2E tests (24 SP)

### Team C: API Agent
**Focus:** Admin features, Monitoring, Infrastructure
**Tools:** FastAPI, Redis, Health checks, CI/CD
**Output:** 3 E2E tests + Infrastructure (22 SP)

**Synchronization Points:**
- Daily standup (async via commits)
- Day 3: Mid-sprint sync
- Day 6: Integration testing
- Day 8: Final review

---

## Success Criteria

- [ ] All 9 new E2E tests implemented and passing
- [ ] Total: 12 E2E tests (3 existing + 9 new)
- [ ] 100% coverage of critical user journeys
- [ ] All tests run reliably in local environment
- [ ] CI/CD pipeline configured and passing
- [ ] Tests run in < 15 minutes total
- [ ] Code coverage >80% for new test code
- [ ] Documentation complete (README, inline comments)
- [ ] No flaky tests (3 consecutive runs pass)
- [ ] Performance baselines documented

---

## Deliverables

### Test Files (9 new)
1. `tests/e2e/test_e2e_domain_creation_workflow.py`
2. `tests/e2e/test_e2e_upload_page_domain_classification.py`
3. `tests/e2e/test_e2e_graph_exploration_workflow.py`
4. `tests/e2e/test_e2e_chat_streaming_and_citations.py`
5. `tests/e2e/test_e2e_session_management.py`
6. `tests/e2e/test_e2e_community_detection_workflow.py`
7. `tests/e2e/test_e2e_cost_monitoring_workflow.py`
8. `tests/e2e/test_e2e_health_monitoring.py`
9. `tests/e2e/test_e2e_indexing_pipeline_monitoring.py`

### Support Files
- `tests/e2e/fixtures/training_datasets.py` - Training data fixtures
- `tests/e2e/fixtures/sample_documents.py` - Test documents
- `tests/e2e/fixtures/graph_data.py` - Graph test data
- `tests/e2e/fixtures/sessions.py` - Session fixtures
- `.github/workflows/e2e.yml` - CI/CD configuration

### Documentation
- `tests/e2e/README.md` - Updated with new tests
- `docs/e2e/USER_JOURNEYS_AND_TEST_PLAN.md` - Implementation status updates
- `docs/sprints/SPRINT_50_SUMMARY.md` - Sprint summary (after completion)

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Flaky Tests (async timing) | High | High | Proper waits, retry logic, deterministic test data |
| Service Dependencies (Neo4j, Qdrant) | Medium | High | Health checks before tests, fallback strategies |
| Playwright Browser Issues | Low | Medium | Pin browser version, install verification |
| Test Data Conflicts | Medium | Medium | Isolated test databases, cleanup fixtures |
| CI/CD Resource Limits | Low | Medium | Optimize parallel execution, caching |
| Team Coordination | Medium | Low | Clear interfaces, daily sync, shared fixtures |
| Performance Regression | Low | Medium | Baseline measurements, performance tests |

---

## Performance Targets

### Individual Test Performance
- Page Load: < 3 seconds
- Graph Render: < 5 seconds
- Search Response: < 2 seconds (streaming start)
- Upload Processing: < 30 seconds per document
- Test Execution: < 2 minutes per test (average)

### Suite Performance
- Full Suite: < 15 minutes (local)
- Full Suite: < 20 minutes (CI/CD)
- Parallel Execution: 3 workers
- Flakiness Rate: < 1% (max 1 failure in 100 runs)

---

## Quality Metrics

### Test Coverage Goals
- **Critical User Journeys:** 100% (all 11 journeys)
- **Admin Features:** 90%
- **Error Scenarios:** 80%
- **Edge Cases:** 70%

### Code Quality
- **Test Code Coverage:** >80%
- **Linting:** Ruff clean
- **Type Checking:** MyPy strict
- **Documentation:** All tests documented

### Reliability
- **Pass Rate:** >99% (3 consecutive runs)
- **Flakiness:** < 1%
- **False Positives:** 0
- **False Negatives:** 0

---

## Post-Sprint Review Items

- User feedback on test coverage
- Identify untested edge cases
- Performance optimization opportunities
- CI/CD pipeline improvements
- Test maintenance strategy
- Next sprint planning (Sprint 51)

---

## Definition of Done (DoD)

### Per Feature
- [ ] E2E test implemented and passing locally
- [ ] Test documented with clear comments
- [ ] Fixtures created and reusable
- [ ] Validation points all checked
- [ ] Test runs reliably (3x consecutive pass)
- [ ] Code review completed
- [ ] Team demo performed

### Sprint Complete
- [ ] All 9 E2E tests passing
- [ ] CI/CD pipeline green
- [ ] Documentation updated
- [ ] Performance targets met
- [ ] Code coverage >80%
- [ ] Zero flaky tests
- [ ] Sprint summary created
- [ ] Retrospective completed

---

**END OF SPRINT 50 PLAN**
