# Sprint 51: Unutilized Features E2E Test Coverage

**Status:** PLANNED
**Branch:** `sprint-51-unutilized-features`
**Start Date:** TBD (After Sprint 50)
**Estimated Duration:** 5-7 Tage (1.5 Wochen)
**Total Story Points:** 47 SP

---

## Sprint Overview

Sprint 51 fokussiert auf **E2E-Test-Abdeckung für implementierte aber ungenutzbare Features**. Nach Analyse aller ADRs und Sprint-Pläne 48-30 wurden mehrere vollständig implementierte Features identifiziert, die keine E2E-Tests haben und daher in User Journeys fehlen.

**Identifizierte Features:**
- ✅ **ADR-042:** Bi-Temporal Queries (6 API Endpoints, keine E2E Tests)
- ✅ **ADR-043:** Secure Shell Sandbox (440 Lines Code, keine E2E Tests)
- ✅ **Sprint 49.1:** Dynamic LLM Model Discovery (implementiert, nicht getestet)
- ✅ **Sprint 49.2:** Graph Relationship Type Filtering (implementiert, nicht getestet)
- ✅ **Sprint 49.3:** Historical Phase Events Display (implementiert, nicht getestet)
- ⚠️ **ADR-025:** Mem0 User Preference Learning (designed, NICHT implementiert)

**Ziel:** E2E-Tests für Features 1-5, optional Mem0-Implementation falls Zeit vorhanden.

**Strategie:** Fokussierte Implementierung der 5 kritischen E2E-Tests + Mem0 als Stretch Goal.

---

## Current State Analysis

### Implementierte Features ohne E2E Tests (5)

#### 1. Bi-Temporal Queries (ADR-042)
**Status:** Vollständig implementiert in Sprint 39
**Code:** `src/components/graph_rag/temporal_query_builder.py` (440 lines)
**API Endpoints:** 6 temporal query endpoints
**Problem:** Feature Flag `temporal_queries_enabled=False` - keine E2E-Validierung

#### 2. Secure Shell Sandbox (ADR-043)
**Status:** Vollständig implementiert in Sprint 40
**Code:** `src/components/sandbox/bubblewrap_backend.py` (440+ lines)
**Integration:** MCP Tools, deepagents Backend Protocol
**Problem:** Sandbox-Funktionalität nie in User Journey getestet

#### 3. Dynamic LLM Discovery (Sprint 49.1)
**Status:** Vollständig implementiert in Sprint 49
**API:** `/api/v1/admin/ollama/models`
**Frontend:** `AdminLLMConfigPage.tsx` mit Dynamic Dropdown
**Problem:** Model-Discovery funktioniert, aber nie E2E-getestet

#### 4. Graph Relationship Filtering (Sprint 49.2)
**Status:** Vollständig implementiert in Sprint 49
**Frontend:** `GraphAnalyticsPage.tsx` mit Multiselect
**Problem:** Filter-Funktionalität nicht in E2E-Tests validiert

#### 5. Historical Phase Events (Sprint 49.3)
**Status:** Vollständig implementiert in Sprint 49
**Component:** `PhaseEventHistory` in ConversationView
**API:** SSE-basiertes Phase Tracking
**Problem:** UI zeigt Events, aber keine E2E-Validierung

### Designtes Feature ohne Implementation (1)

#### 6. Mem0 User Preference Learning (ADR-025)
**Status:** Designed in Sprint 21, NICHT implementiert
**ADR:** Complete architecture, database schema, API design
**Reason Not Implemented:** Sprint 21 fokussierte auf andere Priorities
**Decision:** Optional Stretch Goal für Sprint 51 (falls Zeit)

---

## Features

| # | Feature | SP | Priority | Implementation Status | Team |
|---|---------|-----|----------|-----------------------|------|
| 51.1 | Bi-Temporal Queries / Graph Time Travel | 13 | P0 | ✅ Implemented | Team A |
| 51.2 | Secure Shell Sandbox Execution | 8 | P0 | ✅ Implemented | Team A |
| 51.3 | Dynamic LLM Model Configuration | 5 | P1 | ✅ Implemented | Team B |
| 51.4 | Graph Relationship Type Filtering | 5 | P1 | ✅ Implemented | Team B |
| 51.5 | Historical Phase Events Display | 3 | P1 | ✅ Implemented | Team B |
| 51.6 | Index Consistency Validation UI | 5 | P2 | ✅ Implemented | Team C |
| 51.7 | Mem0 User Preference Learning (OPTIONAL) | 13 | P3 | ⚠️ NOT Implemented | Team C |

**Total (without Mem0): 39 SP**
**Total (with Mem0): 52 SP**

---

## Feature Details

### Feature 51.1: Bi-Temporal Queries / Graph Time Travel (13 SP)
**Priority:** P0
**Team:** Team A (Backend Agent)
**Reference:** ADR-042, Sprint 39
**Implementation Status:** ✅ Fully Implemented but Feature Flag OFF

**Ziel:** E2E-Test für vollständige Graph Time Travel Funktionalität mit Bi-Temporal Queries.

#### What Was Implemented (Sprint 39)

**Backend Components:**
```python
# All exist in codebase:
src/components/graph_rag/temporal_query_builder.py  # 440 lines
src/components/graph_rag/evolution_tracker.py       # Entity changes
src/components/graph_rag/version_manager.py         # Version management
```

**API Endpoints (6 total):**
```python
GET  /api/v1/graph/temporal/entities?as_of=2024-01-15
GET  /api/v1/graph/temporal/entity/{id}/history
POST /api/v1/graph/temporal/query  # With temporal filters
GET  /api/v1/graph/temporal/entity/{id}/versions
POST /api/v1/graph/temporal/entity/{id}/rollback
GET  /api/v1/graph/temporal/changes?from=...&to=...
```

**Neo4j Schema Extensions:**
```cypher
(:base {
  // Bi-Temporal Properties (already in schema)
  valid_from: datetime,
  valid_to: datetime | null,
  transaction_from: datetime,
  transaction_to: datetime | null,
  version_number: int,
  changed_by: string
})
```

**Feature Flag (Currently OFF):**
```python
# src/core/config.py
temporal_queries_enabled: bool = False  # DEFAULT: OFF
```

#### E2E Test Scenario

**Test Goal:** Validate complete time travel workflow from UI.

```python
class TestGraphTimeTravelWorkflow:
    """Test bi-temporal queries and graph time travel."""

    async def test_complete_graph_time_travel_workflow(
        self,
        page: Page,
        neo4j_driver,
        indexed_temporal_documents: list[Path]
    ):
        """
        Prerequisites:
        1. Enable temporal queries: temporal_queries_enabled=True
        2. Upload documents forming temporal graph
        3. Create multiple entity versions (updates)

        Steps:
        1. Navigate to /admin/graph
        2. Click "Time Travel" tab (new tab to add)
        3. Select historical date (e.g., 1 week ago)
        4. View graph as it existed on that date
        5. Click entity to see version history
        6. Compare two versions side-by-side
        7. View change audit trail (who changed what when)
        8. Test rollback functionality (restore old version)
        9. Verify current graph updated with rolled-back version
        """
```

**Frontend Changes Needed:**
```tsx
// frontend/src/pages/admin/GraphAnalyticsPage.tsx
// ADD: Time Travel Tab with Date Picker

<Tabs>
  <Tab label="Graph">
    <GraphView />
  </Tab>

  {/* NEW TAB */}
  <Tab label="Time Travel">
    <TimeTravelControls
      onDateChange={(date) => setAsOfDate(date)}
    />
    <GraphView
      temporalMode={true}
      asOf={asOfDate}
    />
    <VersionHistoryPanel entityId={selectedEntity} />
  </Tab>
</Tabs>
```

**Fixtures Needed:**
```python
@pytest_asyncio.fixture
async def indexed_temporal_documents(tmp_path_factory, neo4j_driver) -> list[Path]:
    """Create documents and update them over time to form temporal history."""

    # Document 1: Initial version
    doc1_v1 = """
    # Python 3.11 Release Notes
    Python 3.11 was released on October 24, 2022.
    """

    # Upload and wait for indexing
    # Update entity "Python 3.11" to create version 2
    # Update again to create version 3

    # Verify 3 versions exist in Neo4j
    async with neo4j_driver.session() as session:
        result = await session.run("""
            MATCH (e:base {name: 'Python 3.11'})
            RETURN e.version_number as version
            ORDER BY version DESC
            LIMIT 1
        """)
        record = await result.single()
        assert record["version"] == 3

    return [doc1_v1_path, doc1_v2_path, doc1_v3_path]
```

**Validation Points:**
- [ ] Feature flag can be toggled via Admin UI
- [ ] Time Travel tab visible when enabled
- [ ] Date picker functional
- [ ] Graph loads historical state correctly
- [ ] Entity version history displays
- [ ] Version comparison shows diff
- [ ] Audit trail shows user + timestamp
- [ ] Rollback functionality works
- [ ] Performance < 500ms (per ADR-042)

**Files to Create:**
- `tests/e2e/test_e2e_graph_time_travel_workflow.py`
- `tests/e2e/fixtures/temporal_graph_data.py`
- `frontend/src/components/graph/TimeTravelControls.tsx` (NEW)
- `frontend/src/components/graph/VersionHistoryPanel.tsx` (NEW)

**Acceptance Criteria:**
- [ ] Test passes with temporal_queries_enabled=True
- [ ] All 6 temporal API endpoints tested
- [ ] UI correctly displays historical graph state
- [ ] Version rollback verified in Neo4j
- [ ] Performance meets ADR-042 targets (<500ms)

---

### Feature 51.2: Secure Shell Sandbox Execution (8 SP)
**Priority:** P0
**Team:** Team A (Backend Agent)
**Reference:** ADR-043, Sprint 40
**Implementation Status:** ✅ Fully Implemented

**Ziel:** E2E-Test für Secure Shell Sandbox mit Bubblewrap-Integration.

#### What Was Implemented (Sprint 40)

**Backend Components:**
```python
# All exist in codebase:
src/components/sandbox/bubblewrap_backend.py  # 440+ lines
src/agents/code_analysis_agent.py             # deepagents integration
src/mcp_server/tools/shell.py                 # MCP Tool wrapper
```

**Sandbox Features:**
- Network isolation (--unshare-net)
- Filesystem isolation (read-only repo, writable workspace)
- Seccomp profile (~40 whitelisted syscalls)
- Timeout enforcement (30s default)
- Output sanitization (32KB limit)
- Audit logging

**MCP Tool:**
```python
# Exposed as MCP Tool:
secure_shell(command: str, workspace: str, timeout: int) -> dict
```

#### E2E Test Scenario

```python
class TestSecureShellSandboxExecution:
    """Test secure shell sandbox with Bubblewrap."""

    async def test_shell_sandbox_code_analysis_workflow(
        self,
        page: Page,
        sample_code_repository: Path
    ):
        """
        Prerequisites:
        1. Bubblewrap installed on system
        2. Sample code repository uploaded

        Steps:
        1. Navigate to /admin/code-analysis (NEW PAGE to create)
        2. Select repository to analyze
        3. Trigger code analysis agent
        4. Monitor sandbox execution logs (SSE)
        5. Verify commands run in isolated sandbox:
           - `find . -name "*.py" | wc -l`  (File counting)
           - `grep -r "import" . | head -20`  (Dependency analysis)
           - `git log --oneline | head -10`  (Git history)
        6. Verify results displayed correctly
        7. Check audit log for all executions
        8. Test sandbox security:
           - Try network access (should fail: --unshare-net)
           - Try writing outside workspace (should fail)
           - Try dangerous command (should be blocked)
        """

    async def test_sandbox_security_isolation(
        self,
        page: Page
    ):
        """Test sandbox security boundaries."""

        dangerous_commands = [
            "curl http://evil.com",  # Network access blocked
            "rm -rf /repo",          # Repo is read-only
            "cat /etc/passwd",       # Host filesystem isolated
            "ping 8.8.8.8",          # Network isolated
        ]

        for cmd in dangerous_commands:
            result = await execute_sandboxed_command(cmd)
            assert result["exit_code"] != 0
            assert "blocked" in result["stderr"].lower() or "denied" in result["stderr"].lower()
```

**Frontend Changes Needed:**
```tsx
// NEW PAGE: frontend/src/pages/admin/CodeAnalysisPage.tsx

export function CodeAnalysisPage() {
  return (
    <div>
      <h1>Code Analysis Agent</h1>

      <RepositorySelector onSelect={setSelectedRepo} />

      <button onClick={startAnalysis}>
        Analyze Repository
      </button>

      <SandboxExecutionLog
        executions={sandboxLogs}
        showAuditTrail={true}
      />

      <AnalysisResults
        entities={extractedEntities}
        dependencies={foundDependencies}
      />
    </div>
  );
}
```

**Fixtures Needed:**
```python
@pytest_asyncio.fixture
async def sample_code_repository(tmp_path_factory) -> Path:
    """Create sample Python repository for analysis."""
    repo_dir = tmp_path_factory.mktemp("code_repo")

    # Create Python files
    (repo_dir / "main.py").write_text("""
import numpy as np
import pandas as pd

def analyze_data():
    pass
""")

    # Initialize git
    subprocess.run(["git", "init"], cwd=repo_dir)
    subprocess.run(["git", "add", "."], cwd=repo_dir)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir)

    return repo_dir
```

**Validation Points:**
- [ ] Sandbox commands execute successfully
- [ ] Network isolation enforced
- [ ] Filesystem isolation enforced
- [ ] Dangerous commands blocked
- [ ] Audit log records all executions
- [ ] Timeout enforcement works (30s)
- [ ] Output truncation works (32KB)
- [ ] Performance overhead < 200ms (per ADR-043)

**Files to Create:**
- `tests/e2e/test_e2e_secure_shell_sandbox.py`
- `frontend/src/pages/admin/CodeAnalysisPage.tsx` (NEW)
- `frontend/src/components/sandbox/SandboxExecutionLog.tsx` (NEW)

**Acceptance Criteria:**
- [ ] All sandbox security features validated
- [ ] Code analysis workflow functional
- [ ] Audit trail complete
- [ ] Performance meets ADR-043 targets

---

### Feature 51.3: Dynamic LLM Model Configuration (5 SP)
**Priority:** P1
**Team:** Team B (Frontend Agent)
**Reference:** Sprint 49.1
**Implementation Status:** ✅ Fully Implemented

**Ziel:** E2E-Test für Dynamic Model Discovery und Configuration.

#### What Was Implemented (Sprint 49.1)

**API Endpoint:**
```python
GET /api/v1/admin/ollama/models
Response: {
  "text_models": [...],
  "vision_models": [...],
  "total_count": 15
}
```

**Frontend Integration:**
```tsx
// frontend/src/pages/admin/AdminLLMConfigPage.tsx
// - Fetches models on page load
// - Populates dropdown dynamically
// - Filters out embedding models
// - Shows model size and capabilities
```

#### E2E Test Scenario

```python
class TestDynamicLLMConfiguration:
    """Test dynamic LLM model discovery and configuration."""

    async def test_dynamic_model_discovery_workflow(
        self,
        page: Page,
        ollama_client
    ):
        """
        Prerequisites:
        1. Ollama running with multiple models
        2. At least 1 text model and 1 vision model installed

        Steps:
        1. Navigate to /admin/llm-config
        2. Verify page loads model list from API (not hardcoded)
        3. Check dropdown contains all Ollama models
        4. Verify embedding models excluded (bge-m3, nomic-embed)
        5. Verify vision models tagged correctly
        6. Select a new model
        7. Save configuration
        8. Test connection with new model
        9. Verify chat uses new model
        10. Pull a new model via Ollama CLI
        11. Refresh page - verify new model appears automatically
        """

    async def test_model_filtering_logic(
        self,
        page: Page
    ):
        """Test that embedding models are correctly filtered."""

        # Navigate to LLM config
        await page.goto(f"{base_url}/admin/llm-config")

        # Get all model options
        options = await page.locator('select[name="model"] option').all_text_contents()

        # Verify embedding models NOT in list
        embedding_models = ["bge-m3", "nomic-embed", "mxbai-embed"]
        for emb_model in embedding_models:
            assert not any(emb_model in opt.lower() for opt in options)

        # Verify text models ARE in list
        text_models = ["llama3.2", "qwen", "mistral"]
        for text_model in text_models:
            assert any(text_model in opt.lower() for opt in options)
```

**Validation Points:**
- [ ] API endpoint returns all models
- [ ] Embedding models filtered out
- [ ] Vision models tagged correctly
- [ ] Model dropdown populated dynamically
- [ ] Model selection persists
- [ ] Connection test functional
- [ ] New models appear after Ollama update

**Files to Create:**
- `tests/e2e/test_e2e_dynamic_llm_configuration.py`

**Acceptance Criteria:**
- [ ] Dynamic discovery works
- [ ] Filtering logic correct
- [ ] Model selection functional
- [ ] No hardcoded model lists

---

### Feature 51.4: Graph Relationship Type Filtering (5 SP)
**Priority:** P1
**Team:** Team B (Frontend Agent)
**Reference:** Sprint 49.2
**Implementation Status:** ✅ Fully Implemented

**Ziel:** E2E-Test für Graph Relationship Type Multiselect Filter.

#### What Was Implemented (Sprint 49.2)

**Frontend Component:**
```tsx
// frontend/src/pages/admin/GraphAnalyticsPage.tsx
// - Multiselect for relationship types
// - Filter applied to graph query
// - Updates graph visualization
```

#### E2E Test Scenario

```python
class TestGraphRelationshipFiltering:
    """Test relationship type multiselect filtering."""

    async def test_relationship_filtering_workflow(
        self,
        page: Page,
        neo4j_driver,
        indexed_graph_documents: list[Path]
    ):
        """
        Prerequisites:
        1. Documents uploaded forming graph with diverse relationships
        2. At least 3 different relationship types (e.g., WORKED_AT, FOUNDED, KNOWS)

        Steps:
        1. Navigate to /admin/graph
        2. View initial graph (all relationships visible)
        3. Open relationship filter multiselect
        4. Select only "WORKED_AT" relationships
        5. Verify graph updates to show only WORKED_AT edges
        6. Add "FOUNDED" to filter
        7. Verify graph now shows WORKED_AT + FOUNDED
        8. Deselect all → verify graph shows all relationships again
        9. Test with entity search (filter should persist)
        """

    async def test_relationship_filter_persistence(
        self,
        page: Page
    ):
        """Test filter persists across page refresh."""

        # Set filter
        await page.goto(f"{base_url}/admin/graph")
        await page.locator('select[name="relationshipTypes"]').select_option(["WORKED_AT"])

        # Refresh page
        await page.reload()

        # Verify filter still applied
        selected = await page.locator('select[name="relationshipTypes"]').input_value()
        assert "WORKED_AT" in selected
```

**Validation Points:**
- [ ] Multiselect functional
- [ ] Graph updates on filter change
- [ ] Filter persists across interactions
- [ ] Filter works with entity search
- [ ] Performance acceptable (<3s render)

**Files to Create:**
- `tests/e2e/test_e2e_graph_relationship_filtering.py`

**Acceptance Criteria:**
- [ ] Filtering functional
- [ ] UI responsive
- [ ] Filter persistence works

---

### Feature 51.5: Historical Phase Events Display (3 SP)
**Priority:** P1
**Team:** Team B (Frontend Agent)
**Reference:** Sprint 49.3
**Implementation Status:** ✅ Fully Implemented

**Ziel:** E2E-Test für Historical Phase Events in Chat Interface.

#### What Was Implemented (Sprint 49.3)

**Frontend Component:**
```tsx
// frontend/src/components/chat/PhaseEventHistory.tsx
// - Displays past phase events for message
// - Expandable accordion UI
// - Shows timing and status
```

**Integration:**
```tsx
// frontend/src/pages/HomePage.tsx
// ConversationView includes PhaseEventHistory
```

#### E2E Test Scenario

```python
class TestHistoricalPhaseEventsDisplay:
    """Test phase event history display in chat."""

    async def test_phase_events_display_workflow(
        self,
        page: Page,
        indexed_documents: list[Path]
    ):
        """
        Prerequisites:
        1. Documents indexed
        2. Chat interface ready

        Steps:
        1. Navigate to chat (/)
        2. Submit query that triggers RAG pipeline
        3. Wait for response completion
        4. Verify phase events displayed during streaming:
           - "Query Analysis" phase
           - "Retrieval" phase
           - "Response Generation" phase
        5. After completion, verify phase history expandable
        6. Click to expand phase history
        7. Verify all past events shown with timestamps
        8. Verify phase durations displayed
        9. Check multiple messages - each has own phase history
        """

    async def test_phase_event_timing_accuracy(
        self,
        page: Page
    ):
        """Verify phase event timestamps are accurate."""

        start_time = datetime.now()

        # Submit query
        await page.fill('textarea[name="query"]', "Test query")
        await page.click('button[type="submit"]')

        # Wait for completion
        await page.wait_for_selector('[data-testid="phase-complete"]')

        end_time = datetime.now()

        # Extract phase durations from UI
        phase_durations = await page.locator('[data-testid="phase-duration"]').all_text_contents()
        total_duration = sum(parse_duration(d) for d in phase_durations)

        # Verify total matches wall-clock time (within 10% margin)
        actual_duration = (end_time - start_time).total_seconds()
        assert abs(total_duration - actual_duration) / actual_duration < 0.1
```

**Validation Points:**
- [ ] Phase events display during streaming
- [ ] Phase history expandable after completion
- [ ] Timestamps accurate
- [ ] Multiple messages tracked separately
- [ ] UI performance acceptable

**Files to Create:**
- `tests/e2e/test_e2e_historical_phase_events.py`

**Acceptance Criteria:**
- [ ] Phase events visible
- [ ] History expandable
- [ ] Timing accurate

---

### Feature 51.6: Index Consistency Validation UI (5 SP)
**Priority:** P2
**Team:** Team C (API Agent)
**Reference:** Sprint 49.6
**Implementation Status:** ✅ Fully Implemented (Backend only)

**Ziel:** E2E-Test für Index Consistency Validation mit Admin UI.

#### What Was Implemented (Sprint 49.6)

**Backend:**
```python
# API endpoint exists:
GET /api/v1/admin/index/consistency
POST /api/v1/admin/index/consistency/check
```

**Missing:** Frontend UI to trigger and display validation results.

#### E2E Test Scenario

```python
class TestIndexConsistencyValidation:
    """Test index consistency validation UI."""

    async def test_consistency_check_workflow(
        self,
        page: Page,
        neo4j_driver,
        qdrant_client
    ):
        """
        Prerequisites:
        1. Documents indexed in Qdrant, Neo4j, BM25
        2. Introduce inconsistency (delete entity from Neo4j)

        Steps:
        1. Navigate to /admin/indexing (or new /admin/consistency page)
        2. Click "Check Consistency" button
        3. Watch validation progress (SSE)
        4. Verify results display:
           - Qdrant chunk count
           - Neo4j entity/relation count
           - BM25 document count
           - Inconsistencies highlighted
        5. View detailed inconsistency report
        6. Trigger re-indexing for inconsistent documents
        7. Re-run check → verify consistency restored
        """
```

**Frontend Changes Needed:**
```tsx
// ADD to: frontend/src/pages/admin/AdminIndexingPage.tsx
// OR create: frontend/src/pages/admin/ConsistencyCheckPage.tsx

<div>
  <h2>Index Consistency Validation</h2>

  <button onClick={runConsistencyCheck}>
    Check Consistency
  </button>

  <ConsistencyReport
    results={consistencyResults}
    onReindex={handleReindex}
  />
</div>
```

**Validation Points:**
- [ ] Consistency check triggers
- [ ] Results display correctly
- [ ] Inconsistencies highlighted
- [ ] Re-indexing resolves issues

**Files to Create:**
- `tests/e2e/test_e2e_index_consistency_validation.py`
- `frontend/src/components/admin/ConsistencyReport.tsx` (NEW)

**Acceptance Criteria:**
- [ ] UI functional
- [ ] Validation accurate
- [ ] Re-indexing works

---

### Feature 51.7: Mem0 User Preference Learning (OPTIONAL - 13 SP)
**Priority:** P3 (Stretch Goal)
**Team:** Team C (Backend + Frontend Agent)
**Reference:** ADR-025, Sprint 21 (planned but not implemented)
**Implementation Status:** ⚠️ NOT IMPLEMENTED

**Ziel:** Vollständige Implementation von Mem0 User Preference Learning (if time permits).

#### What Was Designed (ADR-025)

**Complete Architecture:**
- Layer 0 in 4-layer memory system
- Qdrant collection: `mem0_user_preferences`
- Ollama LLM for fact extraction
- BGE-M3 embeddings
- PostgreSQL schema extensions
- API endpoints for preference management
- Frontend user profile page

**Why Not Implemented:**
Sprint 21 fokussierte auf andere Features, Mem0 wurde zurückgestellt.

#### Implementation Tasks (IF Time Permits)

1. **Backend Implementation (8 SP):**
   - Install mem0ai package
   - Implement `Mem0Wrapper` class (ADR-025 spec)
   - Create Qdrant collection
   - Integrate into chat API
   - Background fact extraction

2. **Frontend Implementation (3 SP):**
   - User preferences page
   - View learned facts
   - Delete individual preferences
   - Toggle mem0 enabled/disabled

3. **Testing (2 SP):**
   - Unit tests
   - Integration tests
   - E2E test for preference learning

**Decision:** Only implement if Sprint 51 finishes ahead of schedule (5+ SP buffer).

**Files to Create (if implemented):**
- `src/components/memory/mem0_wrapper.py`
- `tests/e2e/test_e2e_mem0_user_preferences.py`
- `frontend/src/pages/ProfilePage.tsx`

---

## Architecture References

- **Sprint 49**: [Dynamic UX & Knowledge Graph Deduplication](SPRINT_49_PLAN.md)
- **Sprint 39**: [Bi-Temporal Queries Implementation]
- **Sprint 40**: [MCP + Secure Shell Sandbox Integration]
- **ADR-025**: [mem0 User Preference Layer](../adr/ADR-025-mem0-user-preference-layer.md)
- **ADR-042**: [Bi-Temporal Queries Opt-In Strategy](../adr/ADR-042_BITEMPORAL_OPT_IN_STRATEGY.md)
- **ADR-043**: [Secure Shell Sandbox](../adr/ADR-043_SECURE_SHELL_SANDBOX.md)

---

## Timeline (Sequential Execution)

### Week 1 (Days 1-5)

**Team A (Backend-heavy Features):**
```
Day 1-2: Feature 51.1 (Graph Time Travel) - 13 SP
Day 3-4: Feature 51.2 (Shell Sandbox) - 8 SP
```

**Team B (Frontend-heavy Features):**
```
Day 1: Feature 51.3 (LLM Configuration) - 5 SP
Day 2: Feature 51.4 (Graph Filtering) - 5 SP
Day 3: Feature 51.5 (Phase Events) - 3 SP
```

**Team C (Admin Features):**
```
Day 1-2: Feature 51.6 (Consistency Validation) - 5 SP
Day 3-5: Feature 51.7 (Mem0) - OPTIONAL if time permits
```

### Week 2 (Days 6-7)

**All Teams:**
```
Day 6: Integration Testing, Bug Fixes
Day 7: Documentation, Code Review, Sprint Review
```

**Estimated Total:** 5-7 Tage (depends on Mem0 decision)

---

## Parallel Agent Strategy

### Team A: Backend Agent
**Focus:** Complex backend features (Temporal Queries, Sandbox)
**Tools:** Python, Neo4j, Bubblewrap, deepagents
**Output:** 2 E2E tests (21 SP)

### Team B: Frontend Agent
**Focus:** UI-heavy features (LLM Config, Filters, Phase Events)
**Tools:** React, TypeScript, Playwright
**Output:** 3 E2E tests (13 SP)

### Team C: API Agent
**Focus:** Admin features (Consistency, Optional Mem0)
**Tools:** FastAPI, Qdrant, PostgreSQL
**Output:** 1-2 E2E tests (5-18 SP)

**Synchronization Points:**
- Daily async sync via commits
- Day 3: Mid-sprint check
- Day 6: Integration testing
- Day 7: Final review

---

## Success Criteria

- [ ] All 5 critical E2E tests implemented and passing (Features 51.1-51.5)
- [ ] Feature 51.6 (Consistency) completed
- [ ] Feature 51.7 (Mem0) evaluated for implementation
- [ ] All tests run reliably (3x consecutive pass)
- [ ] Frontend UI for Time Travel and Shell Sandbox
- [ ] Performance targets met (per ADRs)
- [ ] Documentation complete
- [ ] Code coverage >80%

---

## Deliverables

### Test Files (5-6)
1. `tests/e2e/test_e2e_graph_time_travel_workflow.py`
2. `tests/e2e/test_e2e_secure_shell_sandbox.py`
3. `tests/e2e/test_e2e_dynamic_llm_configuration.py`
4. `tests/e2e/test_e2e_graph_relationship_filtering.py`
5. `tests/e2e/test_e2e_historical_phase_events.py`
6. `tests/e2e/test_e2e_index_consistency_validation.py`
7. `tests/e2e/test_e2e_mem0_user_preferences.py` (OPTIONAL)

### Support Files
- `tests/e2e/fixtures/temporal_graph_data.py`
- `tests/e2e/fixtures/code_repositories.py`
- `frontend/src/components/graph/TimeTravelControls.tsx` (NEW)
- `frontend/src/components/graph/VersionHistoryPanel.tsx` (NEW)
- `frontend/src/pages/admin/CodeAnalysisPage.tsx` (NEW)
- `frontend/src/components/sandbox/SandboxExecutionLog.tsx` (NEW)
- `frontend/src/components/admin/ConsistencyReport.tsx` (NEW)

### Documentation
- `docs/e2e/USER_JOURNEYS_AND_TEST_PLAN.md` - Add new journeys
- `docs/sprints/SPRINT_51_SUMMARY.md` - Sprint summary (after completion)
- Updated `tests/e2e/README.md`

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Temporal Queries Complex | Medium | High | Clear ADR-042 spec, step-by-step implementation |
| Bubblewrap Not Installed | Low | High | Installation check in CI/CD, documentation |
| Frontend UI Development Time | Medium | Medium | Simple UI first, polish later |
| Mem0 Scope Creep | Low | Medium | Clear OPTIONAL designation, time-boxed |
| Test Flakiness (Temporal) | Medium | Medium | Deterministic timestamps, retry logic |

---

## Performance Targets

### Individual Test Performance
- Temporal Query Test: < 2 minutes
- Sandbox Test: < 1 minute (sandbox overhead <200ms per command)
- LLM Config Test: < 30 seconds
- Graph Filter Test: < 1 minute
- Phase Events Test: < 1 minute

### Suite Performance
- Full Suite: < 10 minutes (6 tests)
- Parallel Execution: 2-3 workers

---

## Quality Metrics

### Test Coverage Goals
- **Unutilized Features:** 100% (all 5-6 features)
- **API Endpoints:** 100% (temporal + sandbox)
- **Frontend Components:** 90%

### Code Quality
- **Test Code Coverage:** >80%
- **Linting:** Ruff clean
- **Type Checking:** MyPy strict
- **Documentation:** All tests documented

### Reliability
- **Pass Rate:** >99%
- **Flakiness:** < 1%

---

## Post-Sprint Review Items

- Evaluate Mem0 implementation decision
- User feedback on Time Travel UI/UX
- Sandbox security audit
- Performance optimization opportunities
- Next sprint planning (Sprint 52)

---

## Definition of Done (DoD)

### Per Feature
- [ ] E2E test implemented and passing locally
- [ ] Frontend UI (if needed) implemented
- [ ] Test documented with clear comments
- [ ] Validation points all checked
- [ ] Test runs reliably (3x consecutive pass)
- [ ] Code review completed

### Sprint Complete
- [ ] All 5-6 E2E tests passing
- [ ] CI/CD pipeline green
- [ ] Documentation updated
- [ ] Performance targets met
- [ ] Code coverage >80%
- [ ] Zero flaky tests
- [ ] Sprint summary created
- [ ] Retrospective completed

---

**END OF SPRINT 51 PLAN**
