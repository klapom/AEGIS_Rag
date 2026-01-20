# Sprint 116 Plan

**Date:** 2026-01-20 (Duration: 2 weeks)
**Status:** In Progress
**Total Story Points:** 64 SP

## Sprint Overview

Sprint 116 focuses on implementing critical missing features discovered through comprehensive E2E test analysis. The sprint addresses UI components, error handling, graph visualization, and deep research multi-step execution. These features bridge significant gaps between backend capabilities and frontend implementation, enabling full feature parity across the AegisRAG platform.

### Key Objectives
1. Implement admin dashboard statistics cards for system monitoring
2. Add robust API error handling with user-friendly feedback
3. Enhance citation functionality with tooltips and linking
4. Complete MCP tool management and bash execution UI
5. Implement graph visualization and filtering capabilities
6. Enable multi-step deep research execution with proper state management

### Sprint Goals
- **UI Completeness:** 90%+ of skipped E2E tests passing
- **Error Handling:** 100% error scenarios covered
- **Graph Features:** Full visualization + filtering working
- **Deep Research:** Multi-step execution with proper state progression
- **Test Coverage:** 250+ E2E tests passing (67%+)

---

## Sprint 116 Features (64 SP)

| Feature ID | Feature Name | SP | Priority | Status | Owner |
|-----------|-------------|----|---------|---------| ----- |
| 116.1 | Admin Dashboard Stats Cards | 5 | HIGH | Pending | Frontend |
| 116.2 | API Error Handling | 5 | HIGH | Pending | Frontend |
| 116.3 | Citation Tooltips | 5 | HIGH | Pending | Frontend |
| 116.4 | Citation Linking | 2 | MEDIUM | Pending | Frontend |
| 116.5 | MCP Tool Management UI | 8 | HIGH | Pending | Frontend |
| 116.6 | Bash Tool Execution UI | 8 | HIGH | Pending | Frontend |
| 116.7 | Graph Communities UI | 5 | MEDIUM | Pending | Frontend |
| 116.8 | Graph Edge Filters UI | 5 | MEDIUM | Pending | Frontend |
| 116.9 | Graph Visualization | 8 | HIGH | Pending | Frontend |
| 116.10 | Deep Research Multi-Step | 13 | CRITICAL | Pending | Backend + Frontend |

---

## Feature Details

### Feature 116.1: Admin Dashboard Stats Cards (5 SP)

**Requirement Source:** `admin-dashboard.spec.ts` - Admin Dashboard Stats Cards test

**Description:**
Implement statistics cards component for the admin dashboard displaying key system metrics and domain overview information.

**Backend Requirements:**
- `GET /api/v1/admin/dashboard/stats` endpoint
- Return metrics: total documents, total entities, active domains, system health
- Include domain-specific statistics (docs per domain, last update time)
- Response schema:
  ```json
  {
    "total_documents": 1234,
    "total_entities": 5678,
    "active_domains": 8,
    "system_health": "healthy",
    "domains": [
      {
        "name": "general",
        "document_count": 450,
        "entity_count": 2100,
        "last_updated": "2026-01-20T10:30:00Z"
      }
    ]
  }
  ```

**Frontend Requirements:**
- Create `StatCard` component displaying metric with icon + value
- Implement dashboard layout with 4-6 stat cards
- Add real-time refresh (30s interval)
- Loading states and error handling
- Responsive design for mobile/tablet

**Implementation Approach:**
1. Create backend endpoint in `src/api/v1/admin/routes.py`
2. Query Qdrant collection stats, Neo4j entity counts
3. Build `StatCard` component in `frontend/src/components/admin/StatCard.tsx`
4. Integrate into `AdminDashboard` page with grid layout
5. Add error boundary and loading spinner

**Success Criteria:**
- StatCards display correctly with real data
- 30s auto-refresh working
- Mobile responsive layout
- E2E test `admin-dashboard.spec.ts` passing
- Error states handled gracefully

---

### Feature 116.2: API Error Handling (5 SP)

**Requirement Source:** `api-errors.spec.ts` - API Error Handling test

**Description:**
Implement comprehensive error handling for API responses with user-friendly error messages and retry mechanisms.

**Requirements:**
- Handle 500 Internal Server Error with retry prompt
- Handle 413 Payload Too Large with file size warning
- Handle 504 Gateway Timeout with retry button
- Handle network timeouts with exponential backoff
- Parse error messages from response body
- Display error boundary component with recovery options

**Error Response Schema:**
```json
{
  "error": "Validation Error",
  "detail": "File size exceeds 100MB limit",
  "status_code": 413,
  "timestamp": "2026-01-20T10:30:00Z",
  "request_id": "req_abc123"
}
```

**Implementation Approach:**
1. Create `ErrorBoundary` component in `frontend/src/components/error/`
2. Implement error interceptor in Axios/Fetch layer
3. Add retry logic with exponential backoff (100ms, 500ms, 2s, 10s)
4. Create error display component with action buttons
5. Add error logging to monitoring system

**Success Criteria:**
- All 3 error types handled correctly
- Retry mechanism working with exponential backoff
- User-friendly error messages displayed
- Request ID provided for debugging
- E2E test `api-errors.spec.ts` passing

---

### Feature 116.3: Citation Tooltips (5 SP)

**Requirement Source:** `citations.spec.ts` - Citation Features test

**Description:**
Implement hover tooltips for citations showing source preview and metadata.

**Requirements:**
- Hover over citation number shows tooltip
- Tooltip displays:
  - Source document name
  - Excerpt text (50-100 chars)
  - Page/section number
  - Citation score/confidence
- Tooltip positioned near cursor, no layout shift
- Dismiss on click or mouseleave
- Mobile support (tap to show/hide)

**Implementation Approach:**
1. Create `CitationTooltip` component in `frontend/src/components/chat/`
2. Implement hover detection with slight delay (300ms)
3. Query citation metadata from response
4. Use Floating UI or Popper.js for positioning
5. Add keyboard support (Enter to show, Esc to hide)

**Success Criteria:**
- Tooltips appear on hover with 300ms delay
- Correct metadata displayed
- No page layout shift
- Mobile tap support working
- E2E test `citations.spec.ts` passing

---

### Feature 116.4: Citation Linking (2 SP)

**Requirement Source:** `citations.spec.ts` - Citation Features test

**Description:**
Implement linking from citations to their source documents/sections.

**Requirements:**
- Click citation number navigates to source
- Highlights relevant section in source document
- Supports document sidebar scroll-to-section
- Maintains chat context (don't lose conversation)
- Back button returns to chat

**Implementation Approach:**
1. Add link handler to citation numbers
2. Store citation metadata with source references
3. Use React Router for document navigation
4. Implement section highlighting on document load
5. Manage navigation state in context

**Success Criteria:**
- Citation clicks navigate to source
- Section highlighted correctly
- Chat context preserved
- Back navigation working
- E2E test passing

---

### Feature 116.5: MCP Tool Management UI (8 SP)

**Requirement Source:** `group01-mcp-tools.spec.ts` - MCP Tool Management test

**Description:**
Implement user interface for managing MCP tools including listing, enabling/disabling, and configuration.

**Backend Requirements:**
- `GET /api/v1/mcp/tools` - List all available MCP tools
- `POST /api/v1/mcp/tools/{id}/enable` - Enable tool
- `POST /api/v1/mcp/tools/{id}/disable` - Disable tool
- `GET /api/v1/mcp/tools/{id}/config` - Get tool configuration
- `PATCH /api/v1/mcp/tools/{id}/config` - Update configuration
- Response schema includes: id, name, description, enabled, permissions, config

**Frontend Requirements:**
- Create `MCPToolsPage` component listing all tools
- Tool card showing: icon, name, description, enabled toggle
- Permissions badge (read/write/execute)
- Click to open configuration modal
- Batch enable/disable actions
- Search/filter by category

**Implementation Approach:**
1. Create backend endpoints in `src/api/v1/mcp/routes.py`
2. Query MCP registry for tool metadata
3. Build `MCPToolsPage` with tool grid layout
4. Implement `ToolCard` component with toggle
5. Create `ToolConfigModal` for settings
6. Add permission verification

**Success Criteria:**
- Tool list displays with metadata
- Enable/disable toggles working
- Configuration modal opens/saves
- Permissions verified
- Search filtering functional
- E2E test `group01-mcp-tools.spec.ts` passing

---

### Feature 116.6: Bash Tool Execution UI (8 SP)

**Requirement Source:** `group02-bash-execution.spec.ts` - Bash Tool Execution test

**Description:**
Implement UI for executing bash commands through MCP tools with command input, execution, and output display.

**Backend Requirements:**
- `POST /api/v1/mcp/tools/bash/execute` - Execute bash command
- Input validation: command length <1000 chars, timeout 30s
- Timeout handling: return partial output + timeout error
- Output streaming (WebSocket or Server-Sent Events)
- Security: command sanitization, resource limits

**Frontend Requirements:**
- Command input field (syntax highlighting optional)
- Tool selector dropdown (bash, python, node)
- Execute button with loading state
- Output display area (monospace, scrollable)
- Timestamp for each command execution
- Clear button to reset output
- Copy output to clipboard

**Implementation Approach:**
1. Create `/api/v1/mcp/tools/bash/execute` endpoint
2. Implement command sanitization and timeout logic
3. Build `BashExecutionUI` component
4. Add tool selector combobox
5. Implement WebSocket for streaming output
6. Add syntax highlighting (optional: Prism or highlight.js)

**Success Criteria:**
- Commands execute successfully
- Output displays correctly
- Timeout handled gracefully (partial output shown)
- Tool selector working
- Output copy functionality
- E2E test `group02-bash-execution.spec.ts` passing

---

### Feature 116.7: Graph Communities UI (5 SP)

**Requirement Source:** `group12-graph-communities.spec.ts` - Graph Communities test

**Description:**
Implement UI for displaying graph communities with statistics and visualization options.

**Backend Requirements:**
- `GET /api/v1/graph/communities` - List all communities
- `GET /api/v1/graph/communities/{id}` - Get community details
- Response includes: id, name, entity_count, relationship_count, summary, members
- Support filtering by min size

**Frontend Requirements:**
- Communities list page with card layout
- Community card: ID, name, entity count, relationship count
- Click card to view community details
- Community detail page: members list, graph visualization
- Search/filter by name or size
- Export community as JSON/CSV

**Implementation Approach:**
1. Create backend endpoints in `src/api/v1/graph/routes.py`
2. Query Neo4j for community data (uses GDS community detection from Sprint 92)
3. Build `CommunitiesPage` component
4. Implement `CommunityCard` component
5. Create `CommunityDetailView` page
6. Add search and filter logic

**Success Criteria:**
- Communities list displays correctly
- Community cards show accurate counts
- Click to detail view working
- Search/filter functional
- Mobile responsive
- E2E test `group12-graph-communities.spec.ts` passing

---

### Feature 116.8: Graph Edge Filters UI (5 SP)

**Requirement Source:** `edge-filters.spec.ts` - Graph Edge Filters test

**Description:**
Implement UI controls for filtering graph edges by type and weight.

**Requirements:**
- Edge type filter checkboxes: RELATES_TO, MENTIONED_IN, CONTAINS, etc.
- Weight threshold slider (0-100)
- Real-time graph update when filters change
- Checkbox for "show all types"
- Legend showing edge types with colors
- Apply/Reset buttons
- Save filter preferences to localStorage

**Implementation Approach:**
1. Create filter control component in `frontend/src/components/graph/`
2. Implement Slider component for weight threshold
3. Add Checkbox group for edge type selection
4. Update graph rendering based on selected filters
5. Add event handlers for filter changes
6. Persist filter state to localStorage

**Success Criteria:**
- All edge types selectable
- Weight slider working (0-100)
- Graph updates in real-time
- Filters persist across sessions
- Legend displays correctly
- E2E test `edge-filters.spec.ts` passing

---

### Feature 116.9: Graph Visualization (8 SP)

**Requirement Source:** `graph-visualization.spec.ts` - Graph Visualization test

**Description:**
Implement interactive graph visualization with edge colors, legend, and relationship tooltips.

**Requirements:**
- Render graph nodes and edges on canvas
- Edge colors by type: RELATES_TO (blue), MENTIONED_IN (green), CONTAINS (orange)
- Hover on edge shows relationship details tooltip
- Legend showing edge types + color mapping
- Node clustering/force-directed layout
- Pan and zoom controls
- Export graph as PNG/SVG
- Mobile touch support

**Implementation Approach:**
1. Choose graph library: Vis.js, Cytoscape.js, or Three.js
2. Build `GraphVisualization` component
3. Implement edge coloring by type
4. Create `EdgeTooltip` for relationship details
5. Add legend component
6. Implement export functionality
7. Add touch event handlers for mobile

**Success Criteria:**
- Graph renders correctly
- Edge colors match type (blue, green, orange)
- Tooltips appear on edge hover
- Legend visible and accurate
- Pan/zoom working
- Export to PNG working
- E2E test `graph-visualization.spec.ts` passing

---

### Feature 116.10: Deep Research Multi-Step (13 SP)

**Requirement Source:** `group08-deep-research.spec.ts` - Deep Research Multi-Step test

**Description:**
Implement multi-step deep research execution with LangGraph state progression and synthesis of results.

**Backend Requirements:**
- LangGraph agent with 30-60s timeout per step
- Multi-step research workflow:
  1. Initial query decomposition (break into sub-questions)
  2. Retrieve context for each sub-question
  3. Generate intermediate answers
  4. Synthesize final comprehensive answer
- Track state progression: pending → decomposing → retrieving → analyzing → synthesizing → complete
- WebSocket events for step progress updates
- Error handling with graceful degradation (partial results)
- Response includes: final_answer, intermediate_answers, sources, execution_steps

**Frontend Requirements:**
- Research progress visualization (step indicators)
- Real-time status updates (WebSocket)
- Display current step being executed
- Show intermediate results as they complete
- Final synthesis display
- Estimated time remaining
- Cancel research button (graceful stop)
- Export research as PDF/markdown

**Implementation Approach:**
1. Update LangGraph agent in `src/agents/deep_research/`
2. Implement step-by-step state machine
3. Add WebSocket event broadcasting for progress
4. Create `DeepResearchUI` component with progress tracking
5. Implement step indicator component
6. Add streaming output display
7. Create PDF/markdown export functionality

**LangGraph Agent Structure:**
```python
# Multi-step research graph
state: ResearchState
  - query: str
  - sub_questions: List[str]
  - contexts: Dict[str, List[Document]]
  - intermediate_answers: Dict[str, str]
  - final_answer: str
  - current_step: str
  - execution_steps: List[ExecutionStep]

# Nodes
1. decompose_query → generates sub_questions
2. retrieve_context → retrieves for each sub-question
3. analyze_context → generates intermediate answers
4. synthesize_answer → combines into final answer
```

**Success Criteria:**
- Multi-step execution working end-to-end
- State progression tracking accurately
- WebSocket progress updates real-time
- Intermediate results displayed
- Final synthesis correct and comprehensive
- Timeout handling graceful (30-60s per step)
- Cancel research working
- Export to PDF/markdown
- E2E test `group08-deep-research.spec.ts` passing

---

## Implementation Priorities

### Phase 1 (Week 1): Critical UI & Error Handling
1. **116.2** API Error Handling (5 SP) - Blocking feature
2. **116.1** Admin Dashboard Stats (5 SP) - High visibility
3. **116.3** Citation Tooltips (5 SP) - Quality enhancement
4. **116.4** Citation Linking (2 SP) - Complete citation feature

### Phase 2 (Week 1-2): Tool Management & Visualization
5. **116.5** MCP Tool Management (8 SP) - Backend + Frontend
6. **116.6** Bash Tool Execution (8 SP) - Backend + Frontend
7. **116.9** Graph Visualization (8 SP) - Core feature

### Phase 3 (Week 2): Graph Features & Deep Research
8. **116.7** Graph Communities UI (5 SP) - Display layer
9. **116.8** Graph Edge Filters (5 SP) - Filter layer
10. **116.10** Deep Research Multi-Step (13 SP) - Comprehensive feature

---

## Testing Strategy

### E2E Test Mapping
- Feature 116.1 → `admin-dashboard.spec.ts`
- Feature 116.2 → `api-errors.spec.ts`
- Feature 116.3 & 116.4 → `citations.spec.ts`
- Feature 116.5 → `group01-mcp-tools.spec.ts`
- Feature 116.6 → `group02-bash-execution.spec.ts`
- Feature 116.7 → `group12-graph-communities.spec.ts`
- Feature 116.8 → `edge-filters.spec.ts`
- Feature 116.9 → `graph-visualization.spec.ts`
- Feature 116.10 → `group08-deep-research.spec.ts`

### Test Execution
```bash
# Run all E2E tests (should pass 250+ out of 337)
cd frontend
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --reporter=list

# Run specific test groups
npx playwright test admin-dashboard.spec.ts
npx playwright test api-errors.spec.ts
npx playwright test citations.spec.ts
```

### Success Metrics
- **E2E Pass Rate:** 67%+ (250+/337 tests)
- **Feature Completeness:** 100% of 10 features implemented
- **Error Coverage:** 95%+ of error paths tested
- **Performance:** <500ms p95 for feature operations
- **Code Coverage:** 80%+ for new code

---

## Risk Mitigation

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| WebSocket timeout (Deep Research) | Medium | High | Implement heartbeat, graceful reconnect |
| Graph rendering performance | Medium | Medium | Lazy load nodes, implement clustering |
| Error handling complexity | Low | Medium | Comprehensive unit test coverage |
| MCP tool permission model | Medium | Medium | Clear permission documentation |

### Scope Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Deep Research complexity | High | High | Reduce scope to 3-step process initially |
| Graph visualization library selection | Medium | Low | Quick POC before full implementation |
| Citation linking navigation | Low | Low | Use React Router patterns proven elsewhere |

---

## Definition of Done

Each feature must satisfy:
- [ ] Backend endpoints implemented and tested
- [ ] Frontend components implemented and styled
- [ ] Unit tests written (>80% code coverage)
- [ ] E2E test passing
- [ ] Error handling for all failure paths
- [ ] Accessibility (WCAG 2.1 AA)
- [ ] Mobile responsive (tested on 375px, 768px, 1920px)
- [ ] Performance targets met (<500ms)
- [ ] Documentation updated (JSDoc + README)
- [ ] Code review approved

---

## Dependencies & Blockers

### No External Blockers
All features are built on existing infrastructure:
- Backend: FastAPI, LangGraph, Neo4j, Qdrant established
- Frontend: React 19, Playwright, Tailwind CSS established
- Deployment: Docker containers ready

### Internal Dependencies
- Feature 116.2 (Error Handling) must complete before other features
- Feature 116.5/116.6 (MCP Tools) depend on backend MCP integration (Sprint 93)
- Feature 116.10 (Deep Research) depends on LangGraph agent framework (Sprint 95)

---

## Sprint Completion Criteria

Sprint 116 is complete when:
1. All 10 features implemented and code-reviewed
2. E2E test pass rate ≥67% (250+/337)
3. Zero critical bugs in production
4. Documentation updated (ADRs, README, API docs)
5. Performance benchmarks met
6. Team sign-off on quality

---

## Reference: Skipped E2E Tests - Missing Features

Comprehensive analysis of 23 skipped E2E test suites discovered in `/frontend/e2e/`. All tests are documented in `SPRINT_116_SKIPPED_TESTS_ANALYSIS.md`.

### Skipped E2E Tests Summary

| Test File | Test Name | Missing Feature | Backend/Frontend | Est. SP |
|-----------|-----------|-----------------|------------------|---------|
| time-travel.spec.ts | Time Travel Tab - Feature 39.5 | Temporal point-in-time graph queries with date slider, quick jump buttons, snapshot export | Backend (POST /api/v1/temporal/point-in-time), Frontend (TimeTravelTab component, date controls) | 8 |
| version-compare.spec.ts | Version Comparison View - Feature 39.7 | Entity versioning with side-by-side diff, version comparison API, revert functionality | Backend (GET /api/v1/entities/{id}/versions, POST /api/v1/entities/{id}/versions/{v1}/compare/{v2}, POST /api/v1/entities/{id}/versions/{version}/revert), Frontend (VersionCompareView component) | 13 |
| entity-changelog.spec.ts | Entity Changelog Panel - Feature 39.6 | Entity change history tracking, changelog display, user filtering, change type badges | Backend (GET /api/v1/entities/{id}/changelog, filtering/pagination), Frontend (EntityChangelogPanel component, change badges) | 10 |
| admin-dashboard.spec.ts | Admin Dashboard Stats Cards - Feature 46.8.9 | Domain statistics cards with numeric values, domain overview metrics | Backend (GET /api/v1/admin/dashboard/stats with enhanced data), Frontend (StatCard components) | 5 |
| test_domain_training_api.spec.ts | Domain Training API - CRUD | Domain management endpoints with list/get/create domain APIs and validation | Backend (GET /api/v1/admin/domains/, POST /api/v1/admin/domains/) | 13 |
| test_domain_training_api.spec.ts | Domain Training API - Classification | Document-to-domain classifier with top_k parameter and confidence scoring | Backend (POST /api/v1/admin/domains/classify) | 8 |
| test_domain_training_api.spec.ts | Domain Training API - Auto-Discovery | Automatic domain discovery from sample texts (3-10 sample validation) | Backend (POST /api/v1/admin/domains/discover) | 8 |
| test_domain_training_api.spec.ts | Domain Training API - Data Augmentation | Training data augmentation from seed samples with target count generation | Backend (POST /api/v1/admin/domains/augment) | 8 |
| test_domain_training_api.spec.ts | Domain Training API - Batch Ingestion | Batch document ingestion with domain routing and model grouping | Backend (POST /api/v1/admin/domains/ingest-batch) | 8 |
| test_domain_training_api.spec.ts | Domain Training API - Domain Details | Get domain details, training status endpoints, 404 error handling | Backend (GET /api/v1/admin/domains/{name}, GET /api/v1/admin/domains/{name}/training-status) | 5 |
| test_domain_training_api.spec.ts | Domain Training API - Input Validation | Training sample structure validation, entity/relation field requirements | Backend (POST /api/v1/admin/domains/{id}/train) | 5 |
| test_domain_training_api.spec.ts | Domain Training API - Response Format | Consistent response structure for domain list, classification, and endpoints | Backend (Response schema validation) | 3 |
| group02-bash-execution.spec.ts | Bash Tool Execution | Bash command execution UI with tool selector, command input, output display | Frontend (MCP tool executor UI, tool selector combobox) | 8 |
| group12-graph-communities.spec.ts | Graph Communities | Communities list loading, UI rendering with data-testid selectors | Frontend (Graph communities page, community cards) | 5 |
| group01-mcp-tools.spec.ts | MCP Tool Management | Tool list display, permissions, enable/disable toggles, tool configuration modal | Frontend (MCPToolsPage, tool cards, toggles) | 8 |
| test_domain_training_flow.spec.ts | Domain Default Seeding | Default "general" domain seeding in backend, guaranteed presence | Backend (Domain initialization on system startup) | 3 |
| group08-deep-research.spec.ts | Deep Research Multi-Step | Multi-step research execution with LangGraph state progression and synthesis | Backend (LangGraph agent with 30-60s timeout), Frontend (Research UI) | 13 |
| visual-regression.example.spec.ts | Visual Regression Framework | Visual regression infrastructure with baseline snapshots and comparison logic | Frontend (Visual regression config, snapshot storage) | 5 |
| api-errors.spec.ts | API Error Handling | Graceful error handling for 500/413/504 errors with user-friendly messages | Frontend (Error boundary, retry mechanisms) | 5 |
| performance-regression.spec.ts | Performance Regression Tests | Performance baseline measurement with HAR capture, latency tracking, p95 metrics | Backend/Frontend (Performance instrumentation) | 13 |
| edge-filters.spec.ts | Graph Edge Filters | Edge type filtering UI (RELATES_TO, MENTIONED_IN), weight threshold slider | Frontend (Graph filter controls) | 5 |
| graph-visualization.spec.ts | Graph Visualization | Graph canvas rendering with edge colors by type, legend, relationship tooltips | Frontend (Graph visualization component) | 8 |
| citations.spec.ts | Citation Features | Citation hover tooltips with source preview, citation-to-source linking | Frontend (Citation tooltip, source linking) | 5 |

**Total Story Points:** 176 SP across 23 test suites

### Feature Categories & Priority

**Domain Management Features (53 SP) - HIGHEST PRIORITY**
- Domain Training API CRUD (13 SP) - Foundation
- Domain Classification (8 SP)
- Domain Auto-Discovery (8 SP)
- Domain Augmentation (8 SP)
- Domain Batch Ingestion (8 SP)
- Domain Details/Status (5 SP)
- Domain Validation (5 SP)
- Response Format (3 SP)

**Graph & Versioning Features (39 SP)**
- Version Comparison (13 SP) - Foundation
- Entity Changelog (10 SP)
- Time Travel Tab (8 SP)
- Graph Edge Filters (5 SP)
- Graph Visualization (3 SP)

**Research & Performance Features (26 SP)**
- Deep Research Multi-Step (13 SP)
- Performance Regression Tests (13 SP)

**MCP & Tool Features (21 SP)**
- Tool Management (8 SP)
- Bash Tool Execution (8 SP)
- Graph Communities UI (5 SP)

**Quality & Infrastructure (18 SP)**
- Visual Regression Framework (5 SP)
- API Error Handling (5 SP)
- Citation Tooltips (5 SP)
- Citation Linking (3 SP)

**Admin Dashboard (5 SP)**
- Statistics Cards (5 SP)

## Reference

See `SPRINT_116_SKIPPED_TESTS_ANALYSIS.md` for complete analysis including:
- Detailed backend API endpoint specifications
- Frontend component requirements
- Test file locations and patterns
- Dependency graph
- Implementation priority recommendations
