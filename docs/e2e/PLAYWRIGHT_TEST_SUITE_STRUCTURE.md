# Playwright E2E Test Suite Structure - Final Release Validation

**Date:** 2026-01-15
**Purpose:** Comprehensive E2E test coverage for Sprints 72-96 features
**Test Framework:** Playwright + TypeScript
**Target:** 100% UI coverage for final system release

---

## Test Suite Overview

**Total Test Suites:** 12 functional groups
**Estimated Total Tests:** 200+ tests (including edge cases)
**Coverage Target:** All user-facing features from Sprints 72-96

---

## Test Suite 1: Domain Training & Management

**File:** `tests/e2e/01-domain-training.spec.ts`
**Coverage:** Sprint 64 (Domain Training), Sprint 73 (Admin UI)
**Story Points Covered:** 15 SP (Feature 64.1, 73.1)

### Test Scenarios

```typescript
describe('Domain Training & Management', () => {

  describe('Domain Creation', () => {
    test('should create new domain with valid name and description', async ({ page }) => {
      // Navigate to Domain Management
      // Fill domain form (name, description, domain_type)
      // Submit and verify success message
      // Verify domain appears in list
    });

    test('should prevent duplicate domain names', async ({ page }) => {
      // Edge case: Try creating domain with existing name
      // Verify error message
    });

    test('should validate domain name format (no special chars)', async ({ page }) => {
      // Edge case: Test special characters validation
    });
  });

  describe('Training Examples Management', () => {
    test('should add training example with query and expected answer', async ({ page }) => {
      // Select domain
      // Click "Add Training Example"
      // Fill query + expected answer
      // Submit and verify
    });

    test('should edit existing training example', async ({ page }) => {
      // Navigate to training examples
      // Click edit on example
      // Modify fields
      // Save and verify changes
    });

    test('should delete training example with confirmation', async ({ page }) => {
      // Navigate to training examples
      // Click delete
      // Confirm modal
      // Verify deletion
    });

    test('should bulk import training examples from CSV', async ({ page }) => {
      // Edge case: Upload CSV with 100 examples
      // Verify batch processing
    });

    test('should handle invalid CSV format gracefully', async ({ page }) => {
      // Edge case: Upload malformed CSV
      // Verify error handling
    });
  });

  describe('RAG Settings Configuration', () => {
    test('should update retrieval method (vector/graph/hybrid)', async ({ page }) => {
      // Navigate to RAG settings
      // Change retrieval method dropdown
      // Save and verify
    });

    test('should configure top_k value (1-50)', async ({ page }) => {
      // Adjust top_k slider
      // Verify value updates
    });

    test('should configure reranking settings', async ({ page }) => {
      // Enable/disable reranking
      // Adjust reranking threshold
      // Save and verify
    });

    test('should prevent invalid top_k values (>50)', async ({ page }) => {
      // Edge case: Try setting top_k to 999
      // Verify validation error
    });
  });

  describe('Domain Activation', () => {
    test('should activate domain and verify active status', async ({ page }) => {
      // Toggle domain activation
      // Verify status indicator changes
    });

    test('should allow only one active domain at a time', async ({ page }) => {
      // Edge case: Try activating second domain
      // Verify first deactivates automatically
    });
  });

});
```

**Test Data Requirements:**
- 3 test domains: `test_machine_learning`, `test_quantum_computing`, `test_finance`
- 10 training examples per domain
- CSV files: `valid_100_examples.csv`, `malformed_examples.csv`

**Edge Cases:**
1. Domain name with 100+ characters
2. Training example with 10,000+ char answer
3. Concurrent domain creation by 2 users
4. RAG settings with conflicting values (e.g., top_k=0)

---

## Test Suite 2: MCP Tool Configuration

**File:** `tests/e2e/02-mcp-configuration.spec.ts`
**Coverage:** Sprint 72.1 (MCP Tools), Sprint 97.3 (Tool Authorization)
**Story Points Covered:** 12 SP (Feature 72.1, 97.3)

### Test Scenarios

```typescript
describe('MCP Tool Configuration', () => {

  describe('MCP Server Management', () => {
    test('should list available MCP servers', async ({ page }) => {
      // Navigate to MCP Tools
      // Verify server cards display (name, description, status)
    });

    test('should connect to MCP server successfully', async ({ page }) => {
      // Click "Connect" on server card
      // Wait for connection success
      // Verify status changes to "Connected"
    });

    test('should disconnect from MCP server', async ({ page }) => {
      // Click "Disconnect"
      // Verify status changes to "Disconnected"
    });

    test('should handle MCP server connection failure', async ({ page }) => {
      // Edge case: Connect to unavailable server
      // Verify error message
    });

    test('should show connection timeout after 10s', async ({ page }) => {
      // Edge case: Slow MCP server
      // Verify timeout handling
    });
  });

  describe('Tool Selection & Execution', () => {
    test('should select tool from dropdown and execute', async ({ page }) => {
      // Connect to MCP server
      // Select tool from dropdown
      // Fill tool parameters
      // Execute and verify result
    });

    test('should display tool parameters with correct types', async ({ page }) => {
      // Select tool
      // Verify parameter inputs (string, number, boolean)
    });

    test('should validate required tool parameters', async ({ page }) => {
      // Edge case: Try executing with missing required params
      // Verify validation error
    });

    test('should handle tool execution errors gracefully', async ({ page }) => {
      // Edge case: Tool fails with error
      // Verify error message displayed
    });
  });

  describe('Tool Authorization (Sprint 97.3)', () => {
    test('should view tool authorization for skill', async ({ page }) => {
      // Navigate to Tool Authorization Manager
      // Select skill
      // Verify authorized tools list
    });

    test('should add tool authorization to skill', async ({ page }) => {
      // Select skill
      // Click "Add Tool"
      // Select tool from dropdown
      // Configure access level (standard/elevated/admin)
      // Save and verify
    });

    test('should remove tool authorization from skill', async ({ page }) => {
      // Select skill
      // Click "Remove" on tool
      // Confirm removal
      // Verify tool removed
    });

    test('should configure tool access level (standard/elevated/admin)', async ({ page }) => {
      // Edit tool authorization
      // Change access level
      // Save and verify
    });

    test('should prevent unauthorized tool execution', async ({ page }) => {
      // Edge case: Try executing tool not authorized for skill
      // Verify permission error
    });

    test('should enforce rate limiting for tools', async ({ page }) => {
      // Edge case: Execute tool 100 times rapidly
      // Verify rate limit error after threshold
    });
  });

  describe('Tool History & Logs', () => {
    test('should display recent tool executions', async ({ page }) => {
      // Navigate to tool history
      // Verify recent executions listed
    });

    test('should filter tool history by tool name', async ({ page }) => {
      // Apply filter
      // Verify filtered results
    });

    test('should view tool execution details (input/output)', async ({ page }) => {
      // Click on execution
      // Verify details modal shows input/output
    });
  });

});
```

**Test Data Requirements:**
- Mock MCP servers: `test_weather_mcp`, `test_calculator_mcp`, `test_browser_mcp`
- Tool definitions with various parameter types
- Authorization matrix: 3 skills × 5 tools

**Edge Cases:**
1. MCP server crashes during execution
2. Tool returns 1MB+ JSON response
3. Tool execution takes 60s (timeout)
4. Concurrent tool executions (10 simultaneous)
5. Tool with circular dependency

---

## Test Suite 3: Skill Management (Sprint 97)

**File:** `tests/e2e/03-skill-management.spec.ts`
**Coverage:** Sprint 97.1-97.5 (All Skill UI Features)
**Story Points Covered:** 38 SP (Sprint 97 complete)

### Test Scenarios

```typescript
describe('Skill Management', () => {

  describe('Skill Registry Browser (97.1)', () => {
    test('should display all available skills in grid view', async ({ page }) => {
      // Navigate to Skill Registry
      // Verify skill cards display (name, icon, version, status)
    });

    test('should filter skills by search query', async ({ page }) => {
      // Enter search term
      // Verify filtered results
    });

    test('should filter skills by status (active/inactive)', async ({ page }) => {
      // Select status filter
      // Verify filtered results
    });

    test('should toggle skill activation from registry', async ({ page }) => {
      // Click activation toggle
      // Verify status changes
      // Verify icon updates
    });

    test('should paginate skill list (12 per page)', async ({ page }) => {
      // Navigate to page 2
      // Verify different skills displayed
    });

    test('should handle registry with 100+ skills', async ({ page }) => {
      // Edge case: Large skill registry
      // Verify performance (<2s load)
    });
  });

  describe('Skill Configuration Editor (97.2)', () => {
    test('should open skill configuration editor', async ({ page }) => {
      // Click "Configure" on skill card
      // Verify editor opens
    });

    test('should edit YAML configuration and validate syntax', async ({ page }) => {
      // Edit YAML in Monaco editor
      // Verify syntax highlighting
      // Save and verify success
    });

    test('should show YAML validation errors', async ({ page }) => {
      // Edge case: Enter invalid YAML
      // Verify error message
    });

    test('should configure skill triggers (intent patterns)', async ({ page }) => {
      // Edit triggers array
      // Save and verify
    });

    test('should configure skill permissions', async ({ page }) => {
      // Edit permissions section
      // Add/remove permissions
      // Save and verify
    });

    test('should configure skill dependencies', async ({ page }) => {
      // Add dependency
      // Verify dependency validation
    });

    test('should prevent circular dependencies', async ({ page }) => {
      // Edge case: Create circular dependency
      // Verify error message
    });
  });

  describe('Skill Lifecycle Dashboard (97.4)', () => {
    test('should display skill lifecycle metrics', async ({ page }) => {
      // Navigate to Lifecycle Dashboard
      // Verify metrics: load count, execution count, success rate
    });

    test('should show real-time skill activations', async ({ page }) => {
      // Verify live update of active skills
    });

    test('should display skill execution history', async ({ page }) => {
      // Verify execution timeline
    });

    test('should show skill performance metrics (latency, errors)', async ({ page }) => {
      // Verify performance chart
    });

    test('should filter metrics by time range', async ({ page }) => {
      // Select time range (1h, 24h, 7d)
      // Verify metrics update
    });
  });

  describe('SKILL.md Visual Editor (97.5)', () => {
    test('should open SKILL.md visual editor', async ({ page }) => {
      // Click "Edit SKILL.md"
      // Verify editor opens
    });

    test('should edit frontmatter fields (name, version, etc.)', async ({ page }) => {
      // Edit form fields
      // Verify YAML updates in preview
    });

    test('should edit markdown content', async ({ page }) => {
      // Edit markdown in editor
      // Verify preview updates
    });

    test('should toggle between edit and preview modes', async ({ page }) => {
      // Switch modes
      // Verify content displays correctly
    });

    test('should validate required frontmatter fields', async ({ page }) => {
      // Edge case: Remove required field
      // Verify validation error
    });

    test('should save SKILL.md changes', async ({ page }) => {
      // Make changes
      // Save
      // Verify file updated
    });
  });

  describe('Skill Bundles (Sprint 95)', () => {
    test('should view available skill bundles', async ({ page }) => {
      // Navigate to Bundles
      // Verify bundles: research_assistant, data_analyst, code_reviewer
    });

    test('should activate skill bundle', async ({ page }) => {
      // Click "Activate" on bundle
      // Verify all bundle skills activate
    });

    test('should deactivate skill bundle', async ({ page }) => {
      // Click "Deactivate"
      // Verify all bundle skills deactivate
    });

    test('should view bundle configuration', async ({ page }) => {
      // Click bundle details
      // Verify skills list, context budget, triggers
    });

    test('should create custom bundle from selected skills', async ({ page }) => {
      // Click "Create Bundle"
      // Select skills
      // Configure bundle settings
      // Save and verify
    });
  });

});
```

**Test Data Requirements:**
- 15 test skills (retrieval, synthesis, reflection, web_search, etc.)
- 3 skill bundles (research_assistant, data_analyst, code_reviewer)
- SKILL.md templates for each skill

**Edge Cases:**
1. Skill with 50+ triggers
2. SKILL.md with 10,000+ lines
3. Bundle with 20+ skills
4. Concurrent skill activations
5. Skill activation during execution

---

## Test Suite 4: End User Search - Simple Query Intent

**File:** `tests/e2e/04-search-simple-query.spec.ts`
**Coverage:** Sprint 81 (C-LARA Intent Classification), Sprint 87 (BGE-M3 Hybrid Search)
**Story Points Covered:** 18 SP (Feature 81.7, 87.1-87.3)

### Test Scenarios

```typescript
describe('End User Search - Simple Query Intent', () => {

  beforeEach(async ({ page }) => {
    // Navigate to Chat Interface
    // Ensure domain is activated
  });

  describe('Intent Classification (C-LARA)', () => {
    test('should classify simple factual query as QUERY intent', async ({ page }) => {
      // Type: "What is machine learning?"
      // Submit
      // Verify intent badge shows "QUERY"
    });

    test('should trigger vector search for QUERY intent', async ({ page }) => {
      // Submit simple query
      // Verify retrieval method indicator shows "Vector"
    });

    test('should display search results with source citations', async ({ page }) => {
      // Submit query
      // Wait for response
      // Verify citations display (document name, page number)
    });

    test('should show retrieval metrics (chunks, latency)', async ({ page }) => {
      // Submit query
      // Verify metrics panel shows:
      //   - Chunks retrieved
      //   - Sparse/Dense counts
      //   - Search latency
    });
  });

  describe('BGE-M3 Hybrid Search (Sprint 87)', () => {
    test('should use dense+sparse vectors for hybrid retrieval', async ({ page }) => {
      // Submit query
      // Verify search uses both dense and sparse
      // Check metrics: "Dense: 8, Sparse: 5"
    });

    test('should apply RRF fusion for hybrid results', async ({ page }) => {
      // Submit query
      // Verify RRF score in debug panel (if enabled)
    });

    test('should rerank results with cross-encoder', async ({ page }) => {
      // Submit query
      // Verify reranking applied (metrics show reranked count)
    });

    test('should handle query with no results', async ({ page }) => {
      // Edge case: Query for non-existent topic
      // Verify "No results found" message
    });

    test('should handle very long query (500+ words)', async ({ page }) => {
      // Edge case: Paste 500-word essay
      // Verify query processes without error
    });
  });

  describe('Response Generation', () => {
    test('should generate coherent answer from retrieved chunks', async ({ page }) => {
      // Submit query
      // Verify response is coherent (contains key terms from query)
    });

    test('should show confidence indicator (high/medium/low)', async ({ page }) => {
      // Submit query
      // Verify confidence badge displayed
    });

    test('should stream response tokens (not wait for full response)', async ({ page }) => {
      // Submit query
      // Verify tokens appear incrementally
    });

    test('should handle LLM timeout gracefully', async ({ page }) => {
      // Edge case: LLM takes 60s+ (timeout)
      // Verify timeout error message
    });
  });

  describe('Source Citations', () => {
    test('should display inline citations [1][2][3]', async ({ page }) => {
      // Submit query
      // Verify citations appear inline
    });

    test('should show citation details on hover', async ({ page }) => {
      // Hover over [1]
      // Verify tooltip shows document name, page, relevance
    });

    test('should link to source document (if available)', async ({ page }) => {
      // Click citation
      // Verify document viewer opens (or download)
    });

    test('should group citations by source document', async ({ page }) => {
      // Submit query
      // Verify citations panel groups by document
    });
  });

  describe('Follow-up Questions', () => {
    test('should suggest relevant follow-up questions', async ({ page }) => {
      // Submit query
      // Verify 3-5 follow-up suggestions displayed
    });

    test('should submit follow-up question on click', async ({ page }) => {
      // Click follow-up suggestion
      // Verify query submitted automatically
    });
  });

});
```

**Test Data Requirements:**
- Indexed domain: `test_machine_learning` (100 documents, 5,000 chunks)
- Sample queries: 20 simple factual questions
- Expected responses with ground truth

**Edge Cases:**
1. Query with only stopwords ("the a an of")
2. Query in foreign language (German, French)
3. Query with special characters (@#$%)
4. Query during ingestion (concurrent access)
5. Query with 0 results (fallback behavior)

---

## Test Suite 5: End User Search - Research Intent

**File:** `tests/e2e/05-search-research-intent.spec.ts`
**Coverage:** Sprint 91 (Planner Skill), Sprint 92 (Recursive LLM), Sprint 94 (Orchestrator)
**Story Points Covered:** 25 SP (Features 91.3, 92.1-92.3, 94.3)

### Test Scenarios

```typescript
describe('End User Search - Research Intent', () => {

  describe('Intent Classification', () => {
    test('should classify complex research query as RESEARCH intent', async ({ page }) => {
      // Type: "Compare quantum annealing vs gate-based quantum computing"
      // Verify intent badge shows "RESEARCH"
    });

    test('should trigger multi-step research workflow', async ({ page }) => {
      // Submit research query
      // Verify workflow indicator shows phases: Plan → Search → Analyze → Synthesize
    });
  });

  describe('Task Decomposition (Planner Skill)', () => {
    test('should decompose research query into subtasks', async ({ page }) => {
      // Submit complex query
      // Verify subtasks displayed:
      //   1. Define quantum annealing
      //   2. Define gate-based quantum computing
      //   3. Compare approaches
      //   4. Synthesize findings
    });

    test('should show subtask progress indicators', async ({ page }) => {
      // Verify each subtask shows: ⏳ Pending → ⏸️ Running → ✅ Complete
    });

    test('should handle plan modification mid-execution', async ({ page }) => {
      // Edge case: User clicks "Stop Research"
      // Verify graceful cancellation
    });
  });

  describe('Recursive Document Processing (Sprint 92)', () => {
    test('should process large documents in segments', async ({ page }) => {
      // Submit query requiring 200KB document
      // Verify document segmented (Level 1)
      // Verify relevant segments processed (Level 2)
      // Verify recursive deep-dive if needed (Level 3)
    });

    test('should show document processing progress', async ({ page }) => {
      // Verify progress bar: "Processing document 1/3..."
    });

    test('should display hierarchical citations (segment-level)', async ({ page }) => {
      // Submit query
      // Verify citations show: Document > Section > Segment
    });
  });

  describe('Multi-Skill Orchestration (Sprint 94)', () => {
    test('should orchestrate multiple skills in parallel', async ({ page }) => {
      // Submit research query
      // Verify skills activated: retrieval + web_search + graph_query
      // Verify parallel execution in metrics
    });

    test('should orchestrate skills sequentially when dependent', async ({ page }) => {
      // Submit query requiring sequence: retrieval → analysis → synthesis
      // Verify sequential execution
    });

    test('should aggregate results from multiple skills', async ({ page }) => {
      // Submit query
      // Verify final response combines findings from all skills
    });

    test('should handle skill execution failure gracefully', async ({ page }) => {
      // Edge case: One skill fails
      // Verify workflow continues with available results
    });
  });

  describe('Research Report Generation', () => {
    test('should generate structured research report', async ({ page }) => {
      // Submit research query
      // Verify report sections:
      //   - Executive Summary
      //   - Key Findings (with citations)
      //   - Detailed Analysis
      //   - Recommendations
    });

    test('should allow export to PDF/Markdown', async ({ page }) => {
      // Click "Export Report"
      // Select format
      // Verify download
    });
  });

});
```

**Test Data Requirements:**
- Large test documents (200-500KB)
- Complex research queries (10 samples)
- Multi-document answers requiring synthesis

**Edge Cases:**
1. Research query requiring 10+ subtasks
2. Document requiring 20+ segments (max recursion)
3. All skills fail (system fallback)
4. User cancels mid-research (cleanup)
5. Concurrent research queries (resource limits)

---

## Test Suite 6: End User Search - Graph/Analysis Intent

**File:** `tests/e2e/06-search-graph-analysis.spec.ts`
**Coverage:** Sprint 78 (Graph Entity Expansion), Sprint 79 (Graph Communities)
**Story Points Covered:** 20 SP (Features 78.1-78.4, 79.1-79.2)

### Test Scenarios

```typescript
describe('End User Search - Graph/Analysis Intent', () => {

  describe('Intent Classification', () => {
    test('should classify entity-centric query as GRAPH intent', async ({ page }) => {
      // Type: "Show me all connections to quantum entanglement"
      // Verify intent badge shows "GRAPH"
    });

    test('should trigger graph search with entity expansion', async ({ page }) => {
      // Submit graph query
      // Verify retrieval method: "Graph"
    });
  });

  describe('Entity Expansion (Sprint 78)', () => {
    test('should extract entities from query using LLM', async ({ page }) => {
      // Submit query
      // Verify entities extracted (displayed in debug panel)
    });

    test('should expand entities using graph N-hop traversal', async ({ page }) => {
      // Submit query
      // Verify metrics show: "Graph Hops: 2, Entities Expanded: 12"
    });

    test('should fall back to synonym expansion if < threshold', async ({ page }) => {
      // Submit query with rare entity
      // Verify synonym expansion triggered
    });

    test('should apply semantic reranking to expanded results', async ({ page }) => {
      // Submit query
      // Verify reranking applied (metrics)
    });

    test('should configure graph expansion settings from UI', async ({ page }) => {
      // Navigate to Admin > Graph Settings
      // Adjust graph_expansion_hops (1-3)
      // Adjust graph_min_entities_threshold (5-20)
      // Save and test query
    });
  });

  describe('Graph Visualization', () => {
    test('should display entity relationship graph', async ({ page }) => {
      // Submit graph query
      // Click "Show Graph"
      // Verify D3.js graph renders (nodes + edges)
    });

    test('should allow graph interaction (pan, zoom, click nodes)', async ({ page }) => {
      // Interact with graph
      // Click node → Verify details panel shows entity info
    });

    test('should show relationship types on edges', async ({ page }) => {
      // Hover edge
      // Verify relationship label displayed
    });

    test('should filter graph by relationship type', async ({ page }) => {
      // Apply relationship filter
      // Verify graph updates
    });

    test('should export graph to image (PNG/SVG)', async ({ page }) => {
      // Click "Export Graph"
      // Verify download
    });
  });

  describe('Community Detection (Sprint 79)', () => {
    test('should display graph communities in sidebar', async ({ page }) => {
      // Navigate to Graph Communities
      // Verify communities listed (ID, size, key entities)
    });

    test('should view community details', async ({ page }) => {
      // Click community
      // Verify entities + relationships displayed
    });

    test('should search communities by entity', async ({ page }) => {
      // Enter entity name
      // Verify matching communities highlighted
    });

    test('should refresh communities on demand', async ({ page }) => {
      // Click "Refresh Communities"
      // Verify background job triggered
      // Verify completion notification
    });
  });

  describe('Graph Analytics', () => {
    test('should display graph statistics', async ({ page }) => {
      // Navigate to Graph Analytics
      // Verify stats: Total entities, Total relationships, Avg degree
    });

    test('should show entity connectivity rankings', async ({ page }) => {
      // Verify top 10 most connected entities
    });

    test('should show relationship type distribution', async ({ page }) => {
      // Verify pie chart of relationship types
    });
  });

});
```

**Test Data Requirements:**
- Graph with 500+ entities, 2,000+ relationships
- Community detection results (5-10 communities)
- Graph queries requiring multi-hop expansion

**Edge Cases:**
1. Query requiring 5-hop expansion (max)
2. Entity with 100+ connections (hub node)
3. Isolated entity (no connections)
4. Graph query during community detection
5. Very large graph (10,000+ entities)

---

## Test Suite 7: Continue Previous Search

**File:** `tests/e2e/07-continue-search.spec.ts`
**Coverage:** Sprint 72.3 (Memory Management), Sprint 95 (Procedural Memory)
**Story Points Covered:** 12 SP (Features 72.3, 95.4)

### Test Scenarios

```typescript
describe('Continue Previous Search', () => {

  describe('Search History', () => {
    test('should display recent search history', async ({ page }) => {
      // Navigate to Search History
      // Verify recent queries listed (timestamp, intent, results count)
    });

    test('should filter history by date range', async ({ page }) => {
      // Select date range
      // Verify filtered results
    });

    test('should filter history by intent type', async ({ page }) => {
      // Select intent filter
      // Verify filtered results
    });

    test('should search history by keyword', async ({ page }) => {
      // Enter search term
      // Verify matching queries
    });
  });

  describe('Resume Previous Search', () => {
    test('should click previous query to resume', async ({ page }) => {
      // Click query in history
      // Verify chat reopens with that query
    });

    test('should restore previous context (retrieved chunks)', async ({ page }) => {
      // Resume query
      // Verify same chunks displayed
    });

    test('should allow follow-up question on previous search', async ({ page }) => {
      // Resume query
      // Type follow-up: "Tell me more about X"
      // Verify context maintained
    });

    test('should maintain conversation thread across sessions', async ({ page }) => {
      // Submit query
      // Refresh page
      // Resume query
      // Verify conversation preserved
    });
  });

  describe('Memory Management', () => {
    test('should view Redis memory stats', async ({ page }) => {
      // Navigate to Memory Management
      // Verify Redis stats: Keys, Memory used, Hit rate
    });

    test('should view Qdrant memory stats', async ({ page }) => {
      // Verify Qdrant stats: Collections, Vectors, Storage
    });

    test('should view Graphiti memory stats', async ({ page }) => {
      // Verify Graphiti stats: Episodes, Facts, Entities
    });

    test('should clear conversation memory', async ({ page }) => {
      // Click "Clear Memory"
      // Confirm action
      // Verify memory cleared
    });

    test('should configure memory retention period', async ({ page }) => {
      // Navigate to settings
      // Set retention period (hours/days)
      // Save and verify
    });
  });

  describe('Procedural Memory Learning (Sprint 95)', () => {
    test('should display skill success rates over time', async ({ page }) => {
      // Navigate to Procedural Memory
      // Verify chart shows skill performance trends
    });

    test('should show skill recommendations based on query history', async ({ page }) => {
      // Submit new query
      // Verify suggested skills based on similar past queries
    });

    test('should track bundle effectiveness', async ({ page }) => {
      // View bundle analytics
      // Verify success rates per bundle
    });
  });

});
```

**Test Data Requirements:**
- 50+ historical queries with various intents
- Memory snapshots at different states
- Procedural memory learning data (100+ executions)

**Edge Cases:**
1. Resume query from 30 days ago (memory expiration)
2. Resume query with deleted documents (handle gracefully)
3. Clear memory during active query (race condition)
4. Concurrent memory access from 10 sessions
5. Memory full (Redis maxmemory)

---

## Test Suite 8: Deep Research Mode

**File:** `tests/e2e/08-deep-research.spec.ts`
**Coverage:** Sprint 63 (Multi-turn Research), Sprint 92 (Enhanced Deep Research)
**Story Points Covered:** 15 SP (Features 63.1-63.3, 92.4)

### Test Scenarios

```typescript
describe('Deep Research Mode', () => {

  describe('Research Mode Activation', () => {
    test('should activate deep research mode from toggle', async ({ page }) => {
      // Toggle research mode
      // Verify UI changes (plan panel appears)
    });

    test('should deactivate research mode', async ({ page }) => {
      // Toggle off
      // Verify normal chat mode restored
    });
  });

  describe('Research Planning', () => {
    test('should generate research plan with 3-5 phases', async ({ page }) => {
      // Submit research query
      // Verify plan displays phases:
      //   Phase 1: Define scope
      //   Phase 2: Search sources
      //   Phase 3: Analyze findings
      //   Phase 4: Synthesize
    });

    test('should edit research plan before execution', async ({ page }) => {
      // View plan
      // Click "Edit Plan"
      // Modify phases
      // Save and verify
    });

    test('should approve plan to start execution', async ({ page }) => {
      // View plan
      // Click "Approve & Execute"
      // Verify execution starts
    });

    test('should reject plan and regenerate', async ({ page }) => {
      // Edge case: User doesn't like plan
      // Click "Regenerate Plan"
      // Verify new plan generated
    });
  });

  describe('Research Execution', () => {
    test('should execute research phases sequentially', async ({ page }) => {
      // Start research
      // Verify phase 1 completes before phase 2 starts
    });

    test('should show phase progress indicators', async ({ page }) => {
      // Verify progress: Phase 1 (✅) → Phase 2 (⏸️ Running) → Phase 3 (⏳)
    });

    test('should display intermediate findings per phase', async ({ page }) => {
      // Verify each phase shows:
      //   - Phase name
      //   - Key findings
      //   - Sources used
    });

    test('should allow user to stop research mid-execution', async ({ page }) => {
      // Click "Stop Research"
      // Verify graceful cancellation
      // Verify partial results available
    });

    test('should handle phase failure gracefully', async ({ page }) => {
      // Edge case: Phase fails
      // Verify error message
      // Verify option to retry or skip
    });
  });

  describe('Research Report', () => {
    test('should generate comprehensive research report', async ({ page }) => {
      // Complete research
      // Verify report sections:
      //   - Executive Summary
      //   - Methodology
      //   - Findings (per phase)
      //   - Citations
      //   - Conclusions
    });

    test('should show confidence score per finding', async ({ page }) => {
      // Verify confidence indicators (high/medium/low)
    });

    test('should link findings to source documents', async ({ page }) => {
      // Click citation
      // Verify document reference
    });

    test('should export research report to PDF', async ({ page }) => {
      // Click "Export to PDF"
      // Verify download with formatting
    });

    test('should save research to history', async ({ page }) => {
      // Complete research
      // Navigate to history
      // Verify research saved
    });
  });

  describe('Tool Use in Research (Sprint 93)', () => {
    test('should use browser tool for web search phase', async ({ page }) => {
      // Submit query requiring web search
      // Verify browser tool invoked
      // Verify web results incorporated
    });

    test('should use calculator tool for analysis phase', async ({ page }) => {
      // Submit query requiring calculation
      // Verify calculator tool invoked
    });

    test('should show tool execution in research timeline', async ({ page }) => {
      // Verify timeline shows: Phase X → Tool Y executed
    });
  });

});
```

**Test Data Requirements:**
- Research queries requiring 3-5 phases
- Multi-step research plans
- Expected research reports (ground truth)

**Edge Cases:**
1. Research requiring 10+ phases (complex)
2. Research with all phases failing
3. User edits plan during execution
4. Concurrent research queries
5. Research timeout (>5 minutes)

---

## Test Suite 9: Document Upload & Ingestion

**File:** `tests/e2e/09-document-upload.spec.ts`
**Coverage:** Sprint 83 (Fast Upload), Sprint 66 (VLM Metadata)
**Story Points Covered:** 12 SP (Features 83.3, 66.1)

### Test Scenarios

```typescript
describe('Document Upload & Ingestion', () => {

  describe('Document Upload', () => {
    test('should upload PDF document successfully', async ({ page }) => {
      // Navigate to Upload
      // Select PDF file
      // Upload and verify success message
    });

    test('should upload .txt document successfully', async ({ page }) => {
      // Upload .txt file
      // Verify success
    });

    test('should upload .docx document successfully', async ({ page }) => {
      // Upload .docx file
      // Verify success
    });

    test('should reject unsupported file types', async ({ page }) => {
      // Edge case: Upload .exe file
      // Verify rejection error
    });

    test('should reject files >50MB', async ({ page }) => {
      // Edge case: Upload 100MB file
      // Verify size limit error
    });

    test('should handle upload failure gracefully', async ({ page }) => {
      // Edge case: Network error during upload
      // Verify error message + retry option
    });
  });

  describe('Fast Upload (Sprint 83)', () => {
    test('should return success within 2-5 seconds (background processing)', async ({ page }) => {
      // Upload document
      // Verify response <5s
      // Verify message: "Processing in background"
    });

    test('should check upload status', async ({ page }) => {
      // Upload document
      // Navigate to Upload Status
      // Verify status: "Processing" → "Complete"
    });

    test('should show processing progress', async ({ page }) => {
      // View upload status
      // Verify progress: Parsing → Chunking → Embedding → Indexing
    });

    test('should notify on completion', async ({ page }) => {
      // Upload document
      // Wait for notification
      // Verify: "Document XYZ ready for search"
    });
  });

  describe('VLM Metadata Extraction (Sprint 66)', () => {
    test('should extract image descriptions from PDF', async ({ page }) => {
      // Upload PDF with images
      // Navigate to document details
      // Verify image descriptions displayed
    });

    test('should show bounding box coordinates for images', async ({ page }) => {
      // View image metadata
      // Verify bbox: {x, y, width, height}
    });

    test('should link image descriptions to chunks', async ({ page }) => {
      // Search using image description
      // Verify relevant chunk retrieved
    });
  });

  describe('Document Management', () => {
    test('should list uploaded documents', async ({ page }) => {
      // Navigate to Documents
      // Verify documents listed (name, date, status)
    });

    test('should filter documents by namespace', async ({ page }) => {
      // Select namespace filter
      // Verify filtered results
    });

    test('should view document details', async ({ page }) => {
      // Click document
      // Verify details: Chunks, Entities, Upload date
    });

    test('should delete document', async ({ page }) => {
      // Click "Delete"
      // Confirm action
      // Verify document removed from all DBs
    });

    test('should bulk delete documents', async ({ page }) => {
      // Select multiple documents
      // Click "Delete Selected"
      // Verify batch deletion
    });

    test('should handle concurrent uploads (10 simultaneous)', async ({ page }) => {
      // Edge case: Upload 10 documents at once
      // Verify all process successfully
    });
  });

});
```

**Test Data Requirements:**
- Test documents: 5 PDFs (1-20 pages), 5 .txt files, 5 .docx files
- PDF with images (for VLM testing)
- Large file (49MB, near limit)
- Invalid file types (.exe, .zip)

**Edge Cases:**
1. Document with 0 text (images only)
2. Document with special characters in filename
3. Duplicate document upload (same hash)
4. Upload during system maintenance
5. Corrupt PDF file

---

## Test Suite 10: Governance UI (Sprint 98 - PROPOSED)

**File:** `tests/e2e/10-governance.spec.ts`
**Coverage:** Sprint 98.3-98.6 (GDPR, Audit, Explainability, Certification)
**Story Points Covered:** 26 SP (Proposed Sprint 98 features)

### Test Scenarios

```typescript
describe('Governance & Compliance UI', () => {

  describe('GDPR Consent Management (98.3)', () => {
    test('should view all user consents', async ({ page }) => {
      // Navigate to GDPR Consent Manager
      // Verify consents listed
    });

    test('should create new consent record', async ({ page }) => {
      // Click "Add Consent"
      // Fill form (userId, purpose, legal_basis, data_categories)
      // Save and verify
    });

    test('should revoke consent', async ({ page }) => {
      // Click "Revoke" on consent
      // Confirm action
      // Verify consent status updated
    });

    test('should handle right to erasure request', async ({ page }) => {
      // Navigate to Data Subject Rights
      // Submit erasure request for user_123
      // Verify confirmation + erasure report
    });

    test('should export user data (portability)', async ({ page }) => {
      // Submit data export request
      // Verify JSON download with all user data
    });

    test('should view processing activity log (GDPR Art. 30)', async ({ page }) => {
      // Navigate to Processing Activities
      // Verify activities listed by purpose
    });
  });

  describe('Audit Trail Viewer (98.4)', () => {
    test('should view audit events with filters', async ({ page }) => {
      // Navigate to Audit Trail
      // Apply filters: Event type, Actor, Time range
      // Verify filtered results
    });

    test('should verify audit chain integrity', async ({ page }) => {
      // Click "Verify Integrity"
      // Verify result: "✓ Chain verified (0 issues)"
    });

    test('should generate GDPR compliance report', async ({ page }) => {
      // Click "Generate Report" → GDPR
      // Verify report displayed with processing activities
    });

    test('should generate security audit report', async ({ page }) => {
      // Click "Generate Report" → Security
      // Verify report shows auth failures, policy violations
    });

    test('should export audit log to CSV', async ({ page }) => {
      // Click "Export"
      // Verify CSV download
    });
  });

  describe('Explainability Dashboard (98.5)', () => {
    test('should view decision trace for query', async ({ page }) => {
      // Submit query
      // Navigate to Explainability
      // Verify trace ID listed
    });

    test('should view user-level explanation', async ({ page }) => {
      // Click trace
      // Select "User View"
      // Verify simple explanation displayed
    });

    test('should view expert-level explanation', async ({ page }) => {
      // Select "Expert View"
      // Verify technical details: skills, tools, metrics
    });

    test('should view audit-level explanation (full trace)', async ({ page }) => {
      // Select "Audit View"
      // Verify full JSON trace
    });

    test('should find source attribution for claim', async ({ page }) => {
      // Enter claim text
      // Click "Find Sources"
      // Verify matching sources highlighted
    });
  });

  describe('Certification Dashboard (98.6)', () => {
    test('should view all skill certifications', async ({ page }) => {
      // Navigate to Certification Dashboard
      // Verify skills with levels: Enterprise, Standard, Basic
    });

    test('should view certification report for skill', async ({ page }) => {
      // Click "View Report" on skill
      // Verify checks displayed: GDPR, Security, Audit
    });

    test('should re-validate skill certification', async ({ page }) => {
      // Click "Validate" on skill
      // Verify validation runs
      // Verify updated certification level
    });

    test('should show expiring certifications', async ({ page }) => {
      // Verify "Expiring Soon" section
      // Verify skills <30 days to expiration
    });
  });

});
```

**Test Data Requirements:**
- 10 consent records
- 100 audit events
- 5 decision traces
- 15 skill certifications

**Edge Cases:**
1. GDPR request for non-existent user
2. Audit chain with tampered event (integrity failure)
3. Explainability for query with no retrieval
4. Certification for skill with invalid SKILL.md
5. Concurrent GDPR erasure requests

---

## Test Suite 11: Agent Hierarchy & Communication (Sprint 98 - PROPOSED)

**File:** `tests/e2e/11-agent-hierarchy.spec.ts`
**Coverage:** Sprint 98.1-98.2 (MessageBus, Blackboard, Hierarchy)
**Story Points Covered:** 14 SP (Proposed Sprint 98 features)

### Test Scenarios

```typescript
describe('Agent Hierarchy & Communication', () => {

  describe('Agent Communication Dashboard (98.1)', () => {
    test('should view real-time agent messages', async ({ page }) => {
      // Navigate to Agent Communication
      // Submit query to trigger messaging
      // Verify messages appear in real-time
    });

    test('should filter messages by agent', async ({ page }) => {
      // Apply agent filter
      // Verify filtered messages
    });

    test('should view blackboard state', async ({ page }) => {
      // Switch to "Blackboard" tab
      // Verify skill namespaces displayed
    });

    test('should view active orchestrations', async ({ page }) => {
      // Switch to "Orchestrations" tab
      // Verify running workflows listed
    });

    test('should view orchestration execution trace', async ({ page }) => {
      // Click orchestration
      // Verify phase timeline displayed
    });
  });

  describe('Agent Hierarchy Visualizer (98.2)', () => {
    test('should display agent hierarchy tree', async ({ page }) => {
      // Navigate to Agent Hierarchy
      // Verify tree: Executive → Manager → Worker
    });

    test('should interact with hierarchy (pan, zoom)', async ({ page }) => {
      // Pan graph
      // Zoom in/out
      // Verify smooth interaction
    });

    test('should click agent node to view details', async ({ page }) => {
      // Click "Research Manager" node
      // Verify details panel shows:
      //   - Skills
      //   - Current tasks
      //   - Performance metrics
    });

    test('should highlight delegation chain for task', async ({ page }) => {
      // Select task from dropdown
      // Verify delegation path highlighted
    });

    test('should show agent performance metrics', async ({ page }) => {
      // View agent details
      // Verify metrics: Success rate, Avg latency, Tasks completed
    });
  });

});
```

**Test Data Requirements:**
- Agent hierarchy with 3 levels
- 50+ agent messages
- 5 active orchestrations

**Edge Cases:**
1. Hierarchy with 100+ agents (visualization performance)
2. Circular delegation (should not occur, but test detection)
3. Agent failure during task execution
4. Concurrent orchestrations (10 simultaneous)
5. Blackboard memory overflow

---

## Test Suite 12: Performance & Stress Testing

**File:** `tests/e2e/12-performance-stress.spec.ts`
**Coverage:** System-wide performance validation
**Story Points Covered:** N/A (non-functional requirements)

### Test Scenarios

```typescript
describe('Performance & Stress Testing', () => {

  describe('Query Performance', () => {
    test('should complete simple query in <200ms (P95)', async ({ page }) => {
      // Submit 100 simple queries
      // Measure latencies
      // Verify P95 < 200ms
    });

    test('should complete hybrid query in <500ms (P95)', async ({ page }) => {
      // Submit 100 hybrid queries
      // Verify P95 < 500ms
    });

    test('should complete research query in <5000ms (P95)', async ({ page }) => {
      // Submit 50 research queries
      // Verify P95 < 5000ms
    });
  });

  describe('Concurrent Load', () => {
    test('should handle 10 concurrent users', async ({ page }) => {
      // Simulate 10 concurrent sessions
      // Submit queries from each
      // Verify all complete successfully
    });

    test('should handle 50 concurrent users', async ({ page }) => {
      // Simulate 50 concurrent sessions
      // Verify system remains responsive
    });

    test('should sustain 50 QPS for 5 minutes', async ({ page }) => {
      // Send 50 queries per second for 5 minutes
      // Verify error rate <1%
    });
  });

  describe('Data Limits', () => {
    test('should handle namespace with 10,000 documents', async ({ page }) => {
      // Query large namespace
      // Verify results returned
    });

    test('should handle query returning 1,000 chunks', async ({ page }) => {
      // Broad query
      // Verify system handles large result set
    });

    test('should handle graph with 10,000 entities', async ({ page }) => {
      // Query large graph
      // Verify visualization performs
    });
  });

  describe('Edge Case Combinations', () => {
    test('should handle all edge cases in sequence', async ({ page }) => {
      // Execute all edge cases from other suites
      // Verify system recovers from each
    });
  });

});
```

---

## Test Execution Plan

### Phase 1: Core Features (Suites 1-3)
**Duration:** Week 1
**Focus:** Domain Training, MCP Config, Skill Management
**Exit Criteria:** 100% pass rate on Suites 1-3

### Phase 2: Search & Research (Suites 4-8)
**Duration:** Week 2
**Focus:** All search intents, research mode, history
**Exit Criteria:** 100% pass rate on Suites 4-8

### Phase 3: Documents & Admin (Suite 9)
**Duration:** Week 2 (parallel with Phase 2)
**Focus:** Upload, ingestion, document management
**Exit Criteria:** 100% pass rate on Suite 9

### Phase 4: Governance (Suites 10-11)
**Duration:** Week 3 (after Sprint 98 completion)
**Focus:** GDPR, Audit, Explainability, Agent monitoring
**Exit Criteria:** 100% pass rate on Suites 10-11

### Phase 5: Performance Validation (Suite 12)
**Duration:** Week 4
**Focus:** Load testing, stress testing, edge cases
**Exit Criteria:** All performance targets met

---

## CI/CD Integration

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        suite: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
      - name: Install dependencies
        run: npm ci
      - name: Start services
        run: docker-compose up -d
      - name: Run E2E Suite ${{ matrix.suite }}
        run: npm run test:e2e:suite-${{ matrix.suite }}
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results-suite-${{ matrix.suite }}
          path: test-results/
```

---

## Test Reporting

### Metrics to Track:
1. **Pass Rate:** % tests passing
2. **Flakiness:** % tests with intermittent failures
3. **Coverage:** % UI features covered
4. **Performance:** P50, P95, P99 latencies
5. **Edge Case Coverage:** % edge cases tested

### Report Format:
```markdown
# E2E Test Report - Sprint 97

**Date:** 2026-01-20
**Branch:** main
**Commit:** abc123

## Summary
- **Total Tests:** 210
- **Passed:** 205 (97.6%)
- **Failed:** 5 (2.4%)
- **Flaky:** 3 (1.4%)
- **Duration:** 45 minutes

## Failed Tests
1. Suite 4, Test 12: "should handle query timeout" - LLM timeout (60s exceeded)
2. Suite 9, Test 8: "should handle concurrent uploads" - Race condition in DB

## Performance Results
- Simple Query P95: 185ms ✅
- Hybrid Query P95: 480ms ✅
- Research Query P95: 4800ms ✅

## Recommendations
- Fix flaky tests in Suite 4
- Increase LLM timeout to 90s
- Add DB locking for concurrent uploads
```

---

**Document:** PLAYWRIGHT_TEST_SUITE_STRUCTURE.md
**Status:** Complete
**Created:** 2026-01-15
**Next Action:** Implement test suites 1-9, extend for Sprint 98 (Suites 10-11)
