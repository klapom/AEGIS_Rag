# Sprint 104 Plan: COMPLETE Production Readiness (95%+ Pass Rate)

**Sprint Duration:** 2026-01-16 → 2026-01-17
**Total Story Points:** 28 SP
**Status:** 📝 Planned
**Priority:** P0 (ABSOLUTE Production Readiness)

---

## Sprint Goal

**Fix ALL 81 E2E Test Failures** and achieve **95%+ Pass Rate** (185+/194 tests).

**Current State (Sprint 103):**
- ✅ 107/194 tests passing (56%)
- ❌ 81/194 tests failing (43%)
- ⏭️ 6/194 tests skipped (3%)

**Target State (Sprint 104):**
- ✅ **185+/194 tests passing (95%+)**
- ❌ **<10/194 tests failing (<5%)**
- 🎯 **Full Production-Ready System**

---

## 🔍 Root Cause Analysis (Why Tests Fail)

### Discovery: UIs Already Exist! (Sprints 95-98)

**CRITICAL FINDING:** Nach Code-Review existieren fast ALLE UIs bereits:
- ✅ **SkillRegistry.tsx** (Sprint 97) - Group 5 Skills Management
- ✅ **AgentCommunicationPage.tsx** (Sprint 98) - Group 6 Skills+Tools
- ✅ **AgentHierarchyPage.tsx** (Sprint 98) - Group 13 Agent Hierarchy
- ✅ **MCPToolsPage.tsx** (Sprint 72) - Group 1 MCP Tools
- ✅ **GDPRConsent.tsx** (Sprint 96) - Group 14 GDPR
- ✅ **AuditTrail.tsx** (Sprint 96) - Group 14 Audit
- ✅ **ExplainabilityPage.tsx** (Sprint 96) - Group 15 Explainability
- ❌ **BrowserToolsPage** FEHLT (Group 4) - Einzige wirklich fehlende UI!

### Actual Problems (Not Missing UIs!)

| Problem | Affected Groups | Failure Count | Root Cause |
|---------|-----------------|---------------|------------|
| **Missing data-testid** | 1, 5, 6, 7, 13, 14, 15 | 58 failures | Components exist but lack test IDs |
| **Missing Browser UI** | 4 | 6 failures | BrowserToolsPage doesn't exist |
| **Mock Data Mismatch** | 10 | 8 failures | Test mocks don't match API format |
| **Backend Integration** | 6, 14, 15 | 20 failures | UI shows static data, not API data |
| **DOM Structure** | 7 | 12 failures | Async rendering, CSS issues |
| **Easy Wins** | 2, 9, 11, 12 | 6 failures | Simple timeout/assertion fixes |
| **Sprint 100 API Fixes** | 14 | 4 failures | Fixes #3, #4 not implemented |

**Total: 81 failures = 58 (data-testid) + 6 (Browser UI) + 8 (Mocks) + 20 (Backend) + 12 (DOM) + 6 (Easy Wins) - overlaps**

---

## 📦 Sprint Features (6 Phases)

### Phase 1: data-testid Blitz (10 SP) - **KRITISCH**

**Problem:** 58 von 81 failures (72%) sind nur fehlende data-testid Attribute!

#### Feature 104.1: SkillRegistry data-testid (2 SP)
**Group 5: 0/8 tests → 8/8 tests (+100%)**

**File:** `frontend/src/pages/admin/SkillRegistry.tsx`

**Test IDs to Add:**
```typescript
// Line 89: Main container
<div data-testid="skills-page" className="min-h-screen">

// Line 115: Search input
<input
  data-testid="skill-search-input"
  type="text"
  placeholder="Search skills..."
/>

// Line 130: Filter dropdown
<select data-testid="skill-filter-status">
  <option value="all">All Skills</option>
  <option value="active">Active</option>
  <option value="inactive">Inactive</option>
</select>

// Line 180: Skill cards (in map function)
<div
  key={skill.name}
  data-testid={`skill-card-${skill.name}`}
  className="bg-white rounded-lg shadow"
>
  {/* Inside card */}
  <button
    data-testid={`skill-toggle-${skill.name}`}
    onClick={() => handleToggleActivation(skill.name, skill.is_active)}
  >
    {skill.is_active ? 'Deactivate' : 'Activate'}
  </button>

  <div data-testid={`skill-status-${skill.name}`}>
    {skill.is_active ? 'Active' : 'Inactive'}
  </div>

  <Link
    to={`/admin/skills/${skill.name}/config`}
    data-testid={`skill-config-link-${skill.name}`}
  >
    Configure
  </Link>
</div>

// Line 220: Pagination
<button data-testid="skills-prev-page" disabled={!hasPrevPage}>Previous</button>
<button data-testid="skills-next-page" disabled={!hasNextPage}>Next</button>
```

**Test Coverage:** 8 E2E tests fixed

---

#### Feature 104.2: AgentCommunicationPage data-testid (2 SP)
**Group 6: 0/9 tests → 9/9 tests (+100%)**

**File:** `frontend/src/pages/admin/AgentCommunicationPage.tsx`

**Test IDs to Add:**
```typescript
// Line 67: Main container
<div data-testid="agent-communication-page" className="min-h-screen">

// Line 98: Tab buttons
<button
  data-testid="tab-all"
  onClick={() => setActiveTab('all')}
>
  All Activity
</button>

<button
  data-testid="tab-messages"
  onClick={() => setActiveTab('messages')}
>
  Messages
</button>

<button
  data-testid="tab-blackboard"
  onClick={() => setActiveTab('blackboard')}
>
  Blackboard
</button>

<button
  data-testid="tab-orchestrations"
  onClick={() => setActiveTab('orchestrations')}
>
  Orchestrations
</button>

// Line 150+: Component wrappers
<div data-testid="message-bus-monitor">
  <MessageBusMonitor />
</div>

<div data-testid="blackboard-viewer">
  <BlackboardViewer />
</div>

<div data-testid="orchestration-timeline">
  <OrchestrationTimeline />
</div>

<div data-testid="communication-metrics">
  <CommunicationMetrics />
</div>
```

**Also Update Child Components:**
- `MessageBusMonitor.tsx`: Add `message-{messageId}`, `message-sender`, `message-receiver`
- `BlackboardViewer.tsx`: Add `blackboard-item-{key}`, `blackboard-value`
- `OrchestrationTimeline.tsx`: Add `orchestration-{id}`, `orchestration-phase`

**Test Coverage:** 9 E2E tests fixed

---

#### Feature 104.3: MCPToolsPage data-testid (1 SP)
**Group 1: 13/19 tests → 18/19 tests (+5 tests)**

**File:** `frontend/src/pages/admin/MCPToolsPage.tsx`

**Existing IDs (already present):**
- ✅ `mcp-tools-page` (line 53)
- ✅ `tab-servers` (line 79)
- ✅ `tab-tools` (line 91)

**Missing IDs to Add:**
```typescript
// Inside MCPServerList component
<div data-testid="mcp-server-list">
  {servers.map(server => (
    <div
      key={server.name}
      data-testid={`server-card-${server.name}`}
    >
      <div data-testid={`server-status-${server.name}`}>
        {server.status}
      </div>
      <div data-testid={`server-latency-${server.name}`}>
        {server.latency_ms}ms
      </div>
      <button
        data-testid={`server-connect-${server.name}`}
        onClick={() => handleConnect(server.name)}
      >
        Connect
      </button>
    </div>
  ))}
</div>

// Inside MCPToolExecutionPanel
<div data-testid="tool-execution-panel">
  <select data-testid="tool-selector">
    {tools.map(tool => (
      <option key={tool.name} value={tool.name}>{tool.name}</option>
    ))}
  </select>

  <button data-testid="execute-tool-button">Execute</button>

  <div data-testid="tool-result">
    {result}
  </div>

  <div data-testid="execution-time">
    {executionTime}ms
  </div>
</div>
```

**Test Coverage:** 5 E2E tests fixed (1 edge case remains)

---

#### Feature 104.4: MemoryManagementPage data-testid (2 SP)
**Group 7: 3/15 tests → 14/15 tests (+11 tests)**

**File:** `frontend/src/pages/admin/MemoryManagementPage.tsx`

**Problem:** Existing test IDs present but tests still fail → DOM Structure Issue

**Root Cause Analysis:**
```typescript
// Current (Sprint 103):
<button data-testid={`tab-${tab.id}`}>  // Creates tab-stats, tab-search, etc.
```

**Issue:** Tabs might be:
1. Rendered asynchronously (not available on initial page load)
2. Hidden by CSS (display:none)
3. Inside conditional rendering
4. Not clickable (z-index, pointer-events)

**Fixes:**
```typescript
// 1. Ensure tabs render immediately (not async)
const [tabs] = useState([...]) // NOT lazy loaded

// 2. Add loading state check
{!loading && (
  <div data-testid="memory-tabs-container">
    {tabs.map(tab => (
      <button
        key={tab.id}
        data-testid={`tab-${tab.id}`}
        className="..." // Ensure visible classes
      >
        {tab.label}
      </button>
    ))}
  </div>
)}

// 3. Add additional IDs for content areas
<div data-testid="tab-content-stats" style={{ display: activeTab === 'stats' ? 'block' : 'none' }}>
  <div data-testid="memory-stats-table">
    {/* Stats content */}
  </div>
</div>

<div data-testid="tab-content-search">
  <input data-testid="memory-search-input" />
  <div data-testid="memory-search-results">
    {/* Results */}
  </div>
</div>

<div data-testid="tab-content-consolidation">
  <button data-testid="consolidation-trigger-btn">
    Trigger Consolidation
  </button>
  <div data-testid="consolidation-status">
    {/* Status */}
  </div>
</div>
```

**Test Coverage:** 11 E2E tests fixed (1 edge case remains)

---

#### Feature 104.5: AgentHierarchyPage data-testid (2 SP)
**Group 13: 2/8 tests → 8/8 tests (+6 tests, 100%)**

**File:** `frontend/src/pages/admin/AgentHierarchyPage.tsx`

**Existing IDs:**
- ✅ `unauthorized-message` (line 103)
- ✅ `refresh-hierarchy-button` (line 160)

**Missing IDs to Add:**
```typescript
// Line 115: Main container
<div data-testid="agent-hierarchy-page" className="min-h-screen">

// Line 140: Hierarchy tree container
<div data-testid="agent-hierarchy-tree">
  <AgentHierarchyD3
    data={hierarchyData}
    onNodeClick={handleNodeClick}
    highlightedAgents={highlightedAgents}
  />
</div>

// Line 170: Agent details panel
<div data-testid="agent-details-panel">
  <AgentDetailsPanel
    agentId={selectedAgentId}
    hierarchyData={hierarchyData}
  />
</div>

// Line 190: Delegation tracer
<div data-testid="delegation-chain-tracer">
  <DelegationChainTracer
    hierarchyData={hierarchyData}
    onHighlight={handleHighlightAgents}
  />
</div>

// Line 210: Statistics panel
<div data-testid="hierarchy-stats">
  <div data-testid="stat-total-agents">{stats.total}</div>
  <div data-testid="stat-executive-count">{stats.executive}</div>
  <div data-testid="stat-manager-count">{stats.manager}</div>
  <div data-testid="stat-worker-count">{stats.worker}</div>
</div>
```

**Also Update Child Components:**

`AgentHierarchyD3.tsx`:
```typescript
// Inside D3 rendering (use d.data.id for unique IDs)
svg.selectAll('.node')
  .data(nodes)
  .enter()
  .append('g')
  .attr('data-testid', d => `agent-node-${d.data.id}`)
  .attr('class', 'node')
```

`AgentDetailsPanel.tsx`:
```typescript
<div data-testid={`agent-details-${agentId}`}>
  <div data-testid="agent-name">{agent.name}</div>
  <div data-testid="agent-level">{agent.level}</div>
  <div data-testid="agent-status">{agent.status}</div>
  <div data-testid="agent-skills">
    {agent.skills.map(skill => (
      <span key={skill} data-testid={`agent-skill-${skill}`}>
        {skill}
      </span>
    ))}
  </div>
</div>
```

**Test Coverage:** 6 E2E tests fixed → **100% Group 13**

---

#### Feature 104.6: GDPR/Audit data-testid (1 SP)
**Group 14: 3/14 tests → 10/14 tests (+7 tests)**

**Files:**
- `frontend/src/pages/admin/GDPRConsent.tsx`
- `frontend/src/pages/admin/AuditTrail.tsx`

**GDPR Consent Test IDs:**
```typescript
// Already present from Sprint 103:
// ✅ tab-consents, tab-rights, tab-activities, tab-pii
// ✅ gdpr-consents-list
// ✅ consent-row-{consent_id}

// Missing IDs to add:
<div data-testid="gdpr-page">
  <div data-testid="consent-purpose-{consentId}">{consent.purpose}</div>
  <div data-testid="consent-status-{consentId}">{consent.status}</div>
  <button data-testid="consent-revoke-{consentId}">Revoke</button>

  <div data-testid="data-subject-rights-list">
    {rights.map(right => (
      <div key={right.id} data-testid={`right-request-${right.id}`}>
        <div data-testid={`right-type-${right.id}`}>{right.type}</div>
        <div data-testid={`right-status-${right.id}`}>{right.status}</div>
      </div>
    ))}
  </div>
</div>
```

**Audit Trail Test IDs:**
```typescript
<div data-testid="audit-trail-page">
  <input data-testid="audit-search-input" />
  <select data-testid="audit-filter-action">
    <option>All Actions</option>
    <option>CREATE</option>
    <option>UPDATE</option>
    <option>DELETE</option>
  </select>

  <div data-testid="audit-events-list">
    {events.map(event => (
      <div key={event.event_id} data-testid={`audit-event-${event.event_id}`}>
        <div data-testid={`event-action-${event.event_id}`}>{event.action}</div>
        <div data-testid={`event-timestamp-${event.event_id}`}>{event.timestamp}</div>
        <div data-testid={`event-user-${event.event_id}`}>{event.user_id}</div>
        <button data-testid={`event-details-${event.event_id}`}>
          View Details
        </button>
      </div>
    ))}
  </div>
</div>
```

**Test Coverage:** 7 E2E tests fixed (4 failures remain due to Sprint 100 API issues)

---

#### Feature 104.7: ExplainabilityPage data-testid (2 SP)
**Group 15: 4/13 tests → 11/13 tests (+7 tests)**

**File:** `frontend/src/pages/admin/ExplainabilityPage.tsx`

**Test IDs to Add:**
```typescript
<div data-testid="explainability-page" className="min-h-screen">

  {/* Tab navigation */}
  <button data-testid="tab-retrieval">Retrieval Explanations</button>
  <button data-testid="tab-decision">Decision Traces</button>
  <button data-testid="tab-compliance">Compliance Reports</button>

  {/* Retrieval explanations */}
  <div data-testid="retrieval-explanations-list">
    {retrievalExplanations.map(exp => (
      <div key={exp.query_id} data-testid={`explanation-retrieval-${exp.query_id}`}>
        <div data-testid={`explanation-query-${exp.query_id}`}>
          {exp.query}
        </div>

        {/* 3-level explanations */}
        <div data-testid={`explanation-level-technical-${exp.query_id}`}>
          {exp.technical}
        </div>
        <div data-testid={`explanation-level-business-${exp.query_id}`}>
          {exp.business}
        </div>
        <div data-testid={`explanation-level-regulatory-${exp.query_id}`}>
          {exp.regulatory}
        </div>
      </div>
    ))}
  </div>

  {/* Decision traces */}
  <div data-testid="decision-traces-list">
    {decisions.map(dec => (
      <div key={dec.decision_id} data-testid={`explanation-decision-${dec.decision_id}`}>
        <div data-testid={`decision-type-${dec.decision_id}`}>{dec.type}</div>
        <div data-testid={`decision-rationale-${dec.decision_id}`}>{dec.rationale}</div>
      </div>
    ))}
  </div>

  {/* Compliance reports */}
  <div data-testid="compliance-reports-list">
    {reports.map(report => (
      <div key={report.report_id} data-testid={`explanation-compliance-${report.report_id}`}>
        <div data-testid={`compliance-article-${report.report_id}`}>
          {report.gdpr_article}
        </div>
        <div data-testid={`compliance-status-${report.report_id}`}>
          {report.compliance_status}
        </div>
      </div>
    ))}
  </div>
</div>
```

**Test Coverage:** 7 E2E tests fixed (2 failures remain due to backend integration)

---

### Phase 2: Browser Tools Page (3 SP) - **NEW UI**

#### Feature 104.8: BrowserToolsPage Creation (3 SP)
**Group 4: 0/6 tests → 6/6 tests (+100%)**

**File:** `frontend/src/pages/admin/BrowserToolsPage.tsx` (NEW)

**Complete Component:**
```typescript
/**
 * BrowserToolsPage Component
 * Sprint 104 Feature 104.8: Browser Automation Tools UI
 *
 * Admin page for browser tool management and execution.
 * Integrates with Sprint 103 MCP Browser Backend.
 *
 * Route: /admin/browser-tools
 */

import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Globe, Camera, Code, MousePointer } from 'lucide-react';
import { executeBrowserTool } from '../../api/browserTools';

interface BrowserSession {
  status: 'idle' | 'active' | 'error';
  currentUrl?: string;
  screenshot?: string; // base64 PNG
  lastAction?: string;
  executionTime?: number;
}

export function BrowserToolsPage() {
  const [session, setSession] = useState<BrowserSession>({ status: 'idle' });
  const [url, setUrl] = useState('https://example.com');
  const [jsCode, setJsCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Navigate tool
  const handleNavigate = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await executeBrowserTool('browser_navigate', { url, timeout: 30000 });
      setSession({
        status: 'active',
        currentUrl: result.url,
        lastAction: `Navigated to ${result.url}`,
        executionTime: result.execution_time_ms,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Navigation failed');
      setSession(prev => ({ ...prev, status: 'error' }));
    } finally {
      setLoading(false);
    }
  };

  // Screenshot tool
  const handleScreenshot = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await executeBrowserTool('browser_screenshot', { full_page: true });
      setSession(prev => ({
        ...prev,
        screenshot: result.screenshot,
        lastAction: 'Screenshot taken',
        executionTime: result.execution_time_ms,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Screenshot failed');
    } finally {
      setLoading(false);
    }
  };

  // Evaluate JS tool
  const handleEvaluate = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await executeBrowserTool('browser_evaluate', { javascript: jsCode });
      setSession(prev => ({
        ...prev,
        lastAction: `Executed JS: ${result.result}`,
        executionTime: result.execution_time_ms,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'JS execution failed');
    } finally {
      setLoading(false);
    }
  };

  // Start browser session
  const handleStart = () => {
    setSession({ status: 'active', currentUrl: 'about:blank' });
  };

  // Stop browser session
  const handleStop = () => {
    setSession({ status: 'idle' });
  };

  return (
    <div data-testid="browser-tools-page" className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto py-8 px-6 space-y-6">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/admin"
              className="flex items-center gap-2 text-blue-600 hover:text-blue-700"
              data-testid="back-to-admin-button"
            >
              <ArrowLeft className="w-5 h-5" />
              Back to Admin
            </Link>
          </div>

          <div className="flex items-center gap-4">
            <div data-testid="browser-session-status" className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${
                session.status === 'active' ? 'bg-green-500' :
                session.status === 'error' ? 'bg-red-500' :
                'bg-gray-400'
              }`} />
              <span className="text-sm font-medium capitalize">{session.status}</span>
            </div>

            {session.status === 'idle' ? (
              <button
                data-testid="browser-start-btn"
                onClick={handleStart}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Start Browser
              </button>
            ) : (
              <button
                data-testid="browser-stop-btn"
                onClick={handleStop}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Stop Browser
              </button>
            )}
          </div>
        </header>

        {/* Page Title */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Browser Automation Tools
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Execute browser automation tasks using Playwright
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div data-testid="browser-error" className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Tools Grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Navigate Tool */}
          <div data-testid="browser-tool-navigate" className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
            <div className="flex items-center gap-3 mb-4">
              <Globe className="w-6 h-6 text-blue-600" />
              <h2 className="text-xl font-semibold">Navigate to URL</h2>
            </div>

            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              data-testid="navigate-url-input"
              className="w-full px-4 py-2 border rounded-lg mb-4"
              disabled={session.status !== 'active'}
            />

            <button
              onClick={handleNavigate}
              disabled={session.status !== 'active' || loading}
              data-testid="navigate-execute-btn"
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading ? 'Navigating...' : 'Navigate'}
            </button>
          </div>

          {/* Screenshot Tool */}
          <div data-testid="browser-tool-screenshot" className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
            <div className="flex items-center gap-3 mb-4">
              <Camera className="w-6 h-6 text-green-600" />
              <h2 className="text-xl font-semibold">Take Screenshot</h2>
            </div>

            <p className="text-sm text-gray-600 mb-4">
              Capture full-page screenshot as PNG
            </p>

            <button
              onClick={handleScreenshot}
              disabled={session.status !== 'active' || loading}
              data-testid="screenshot-execute-btn"
              className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400"
            >
              {loading ? 'Capturing...' : 'Take Screenshot'}
            </button>
          </div>

          {/* Evaluate JS Tool */}
          <div data-testid="browser-tool-evaluate" className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <Code className="w-6 h-6 text-purple-600" />
              <h2 className="text-xl font-semibold">Execute JavaScript</h2>
            </div>

            <textarea
              value={jsCode}
              onChange={(e) => setJsCode(e.target.value)}
              placeholder="document.title"
              rows={4}
              data-testid="evaluate-js-input"
              className="w-full px-4 py-2 border rounded-lg mb-4 font-mono text-sm"
              disabled={session.status !== 'active'}
            />

            <button
              onClick={handleEvaluate}
              disabled={session.status !== 'active' || loading || !jsCode}
              data-testid="evaluate-execute-btn"
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400"
            >
              {loading ? 'Executing...' : 'Execute JavaScript'}
            </button>
          </div>
        </div>

        {/* Session Info */}
        {session.status === 'active' && (
          <div data-testid="browser-session-info" className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
            <h3 className="text-lg font-semibold mb-4">Session Information</h3>

            <div className="space-y-2 text-sm">
              {session.currentUrl && (
                <div>
                  <span className="font-medium">Current URL:</span>{' '}
                  <span data-testid="session-current-url">{session.currentUrl}</span>
                </div>
              )}

              {session.lastAction && (
                <div>
                  <span className="font-medium">Last Action:</span>{' '}
                  <span data-testid="session-last-action">{session.lastAction}</span>
                </div>
              )}

              {session.executionTime && (
                <div>
                  <span className="font-medium">Execution Time:</span>{' '}
                  <span data-testid="session-execution-time">{session.executionTime}ms</span>
                </div>
              )}
            </div>

            {/* Screenshot Display */}
            {session.screenshot && (
              <div className="mt-6">
                <h4 className="font-medium mb-2">Screenshot:</h4>
                <img
                  src={`data:image/png;base64,${session.screenshot}`}
                  alt="Browser screenshot"
                  data-testid="browser-screenshot-image"
                  className="w-full border rounded-lg"
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

**API Integration:** `frontend/src/api/browserTools.ts` (NEW)
```typescript
const BACKEND_URL = 'http://localhost:8000';

interface BrowserToolResult {
  result: any;
  execution_time_ms: number;
  status: 'success' | 'error';
  error_message?: string;
}

export async function executeBrowserTool(
  toolName: string,
  parameters: Record<string, any>
): Promise<BrowserToolResult> {
  const response = await fetch(`${BACKEND_URL}/api/v1/mcp/tools/${toolName}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parameters, timeout: 30 }),
  });

  if (!response.ok) {
    throw new Error(`Browser tool execution failed: ${response.statusText}`);
  }

  return response.json();
}
```

**Route Registration:** Update `frontend/src/App.tsx`:
```typescript
import { BrowserToolsPage } from './pages/admin/BrowserToolsPage';

// Add route (line 94):
<Route path="/admin/browser-tools" element={<BrowserToolsPage />} />
```

**Test Coverage:** 6 E2E tests fixed → **100% Group 4**

---

### Phase 3: Backend Integration (6 SP)

#### Feature 104.9: GDPR/Audit API Contract Completion (2 SP)
**Group 14: 10/14 tests → 12/14 tests (+2 tests)**

**Sprint 100 Fixes MISSING:**
- ❌ Fix #3: Audit Events returns `items` field (not `events`)
- ❌ Fix #4: ISO 8601 timestamp format

**Backend Fix #3:** `src/api/v1/gdpr_audit.py`
```python
@router.get("/audit/events", response_model=AuditEventsResponse)
async def get_audit_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    action_filter: Optional[str] = None,
    user_filter: Optional[str] = None,
):
    """Get audit events with pagination."""
    # ... query logic ...

    # Sprint 100 Fix #3: Use 'items' field
    return {
        "items": events,  # NOT "events"
        "total": total_count,
        "page": page,
        "limit": limit,
    }
```

**Backend Fix #4:** ISO 8601 Timestamps
```python
from datetime import datetime

# All timestamp returns:
"timestamp": datetime.utcnow().isoformat() + "Z"  # "2026-01-16T14:30:00Z"

# NOT:
"timestamp": str(datetime.utcnow())  # "2026-01-16 14:30:00"
```

**Frontend Update:** `AuditTrail.tsx`
```typescript
// Change line 45:
const auditData = await response.json();
const items = auditData.items;  // NOT auditData.events

// Parse ISO 8601 timestamps:
const formattedTimestamp = new Date(event.timestamp).toLocaleString();
```

**Test Coverage:** 2 E2E tests fixed (2 complex failures remain)

---

#### Feature 104.10: Explainability Backend Integration (2 SP)
**Group 15: 11/13 tests → 13/13 tests (+2 tests, 100%)**

**Problem:** ExplainabilityPage shows static mock data instead of real API data

**API Endpoints to Implement:**

`src/api/v1/explainability.py` (NEW):
```python
from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/explainability", tags=["explainability"])

class RetrievalExplanation(BaseModel):
    query_id: str
    query: str
    technical: str  # Technical explanation
    business: str   # Business explanation
    regulatory: str # GDPR/Regulatory explanation
    created_at: str

class DecisionTrace(BaseModel):
    decision_id: str
    type: str
    rationale: str
    alternatives: List[str]
    created_at: str

class ComplianceReport(BaseModel):
    report_id: str
    gdpr_article: str
    compliance_status: str
    evidence: List[str]
    created_at: str

@router.get("/retrieval/{query_id}", response_model=RetrievalExplanation)
async def get_retrieval_explanation(query_id: str):
    """Get 3-level explanation for retrieval query."""
    # Fetch from DB or generate
    return {
        "query_id": query_id,
        "query": "Sample query",
        "technical": "Vector search with BGE-M3 embeddings, top-k=10",
        "business": "Found relevant documents about topic X",
        "regulatory": "GDPR Article 22: Automated decision-making transparency",
        "created_at": "2026-01-16T14:30:00Z",
    }

@router.get("/decision/{decision_id}", response_model=DecisionTrace)
async def get_decision_trace(decision_id: str):
    """Get decision trace with alternatives."""
    return {
        "decision_id": decision_id,
        "type": "retrieval_mode_selection",
        "rationale": "Hybrid mode selected due to entity extraction confidence >0.8",
        "alternatives": ["vector_only", "graph_only"],
        "created_at": "2026-01-16T14:30:00Z",
    }

@router.get("/compliance/{report_id}", response_model=ComplianceReport)
async def get_compliance_report(report_id: str):
    """Get GDPR compliance report."""
    return {
        "report_id": report_id,
        "gdpr_article": "Article 15: Right of Access",
        "compliance_status": "compliant",
        "evidence": [
            "User data exported on request",
            "Response time <30 days",
            "Complete audit trail maintained",
        ],
        "created_at": "2026-01-16T14:30:00Z",
    }

@router.get("/retrieval", response_model=List[RetrievalExplanation])
async def list_retrieval_explanations(limit: int = 20):
    """List recent retrieval explanations."""
    # Return last N from DB
    return []

@router.get("/decisions", response_model=List[DecisionTrace])
async def list_decision_traces(limit: int = 20):
    """List recent decision traces."""
    return []

@router.get("/compliance", response_model=List[ComplianceReport])
async def list_compliance_reports(limit: int = 20):
    """List recent compliance reports."""
    return []
```

**Frontend API Integration:** `frontend/src/api/explainability.ts` (NEW)
```typescript
const BACKEND_URL = 'http://localhost:8000';

export async function fetchRetrievalExplanations(): Promise<any[]> {
  const response = await fetch(`${BACKEND_URL}/api/v1/explainability/retrieval`);
  if (!response.ok) throw new Error('Failed to fetch retrieval explanations');
  return response.json();
}

export async function fetchDecisionTraces(): Promise<any[]> {
  const response = await fetch(`${BACKEND_URL}/api/v1/explainability/decisions`);
  if (!response.ok) throw new Error('Failed to fetch decision traces');
  return response.json();
}

export async function fetchComplianceReports(): Promise<any[]> {
  const response = await fetch(`${BACKEND_URL}/api/v1/explainability/compliance`);
  if (!response.ok) throw new Error('Failed to fetch compliance reports');
  return response.json();
}
```

**Frontend Update:** `ExplainabilityPage.tsx`
```typescript
import { fetchRetrievalExplanations, fetchDecisionTraces, fetchComplianceReports } from '../../api/explainability';

// Replace static mock data with API calls:
useEffect(() => {
  const loadData = async () => {
    setLoading(true);
    try {
      const [retrievalData, decisionData, complianceData] = await Promise.all([
        fetchRetrievalExplanations(),
        fetchDecisionTraces(),
        fetchComplianceReports(),
      ]);

      setRetrievalExplanations(retrievalData);
      setDecisionTraces(decisionData);
      setComplianceReports(complianceData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  void loadData();
}, []);
```

**Test Coverage:** 2 E2E tests fixed → **100% Group 15**

---

#### Feature 104.11: Skills Backend Integration (2 SP)
**Group 5: 8/8 tests remain passing**

**Verify API Integration:**
- Skills API already exists: `GET /api/v1/skills/registry`
- Frontend API calls already implemented in `frontend/src/api/skills.ts`
- Just ensure data flows correctly

**Potential Issues to Fix:**
```typescript
// frontend/src/api/skills.ts - Verify response format
export async function listSkills(params): Promise<{ items: SkillSummary[], total: number }> {
  const response = await fetch(`${BACKEND_URL}/api/v1/skills/registry?${queryString}`);
  const data = await response.json();

  // Sprint 100 Fix #1: Use 'items' field
  return {
    items: data.items,  // NOT data.skills
    total: data.total,
  };
}
```

**No new implementation needed - just verification**

---

### Phase 4: Mock Data Fixes (4 SP)

#### Feature 104.12: Hybrid Search Mock Data (2 SP)
**Group 10: 5/13 tests → 11/13 tests (+6 tests)**

**Problem:** E2E test mocks don't match actual API response format

**Step 1: Document Actual API Response**
```bash
# Run actual API request:
curl http://localhost:8000/api/v1/retrieval/hybrid-search \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 10}'
```

**Expected Format:**
```json
{
  "items": [...],
  "mode": "hybrid",
  "execution_time_ms": 245,
  "metadata": {
    "vector_count": 5,
    "graph_count": 5,
    "fusion_algorithm": "rrf"
  }
}
```

**Step 2: Update E2E Mocks**

`frontend/e2e/group10-hybrid-search.spec.ts`:
```typescript
// BEFORE (WRONG):
await page.route('**/api/v1/retrieval/hybrid-search', route => {
  route.fulfill({
    status: 200,
    body: JSON.stringify({
      results: [...]  // ❌ Wrong field
    })
  });
});

// AFTER (CORRECT):
await page.route('**/api/v1/retrieval/hybrid-search', route => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      items: [  // ✅ Correct field
        {
          document_id: "doc_1",
          content: "Sample content",
          score: 0.95,
          source: "vector",
        },
        {
          document_id: "doc_2",
          content: "Graph content",
          score: 0.87,
          source: "graph",
        },
      ],
      mode: "hybrid",
      execution_time_ms: 245,
      metadata: {
        vector_count: 5,
        graph_count: 5,
        fusion_algorithm: "rrf",
      },
    })
  });
});
```

**Step 3: Update Test Assertions**
```typescript
// Change all assertions:
expect(response.results).toBeDefined();  // ❌ WRONG
expect(response.items).toBeDefined();    // ✅ CORRECT

expect(response.mode).toBe('hybrid');    // ✅ NEW
expect(response.execution_time_ms).toBeGreaterThan(0);  // ✅ NEW
```

**Test Coverage:** 6 E2E tests fixed (2 complex failures remain)

---

#### Feature 104.13: Easy Wins - Perfect Groups (2 SP)
**Groups 2, 9, 11, 12: +6 tests → 4 Perfect Groups**

**Group 2 (Bash): 15/16 → 16/16 (+1 test)**

Analyze failing test:
```bash
# Run specific test:
npx playwright test group02-bash-execution.spec.ts --grep "failing test name"
```

Likely issues:
- Timeout too short (5s → 10s)
- Command output format mismatch
- Shell error handling

**Group 9 (Long Context): 11/13 → 13/13 (+2 tests)**

Likely issues:
- Response assertion format (streaming vs complete)
- Token count calculation mismatch
- Memory limit exceeded

**Group 11 (Upload): 13/15 → 15/15 (+2 tests)**

Likely issues:
- File size limit validation
- Upload progress tracking format
- Status endpoint polling interval

**Group 12 (Communities): 14/15 → 15/15 (+1 test)**

Likely issues:
- Community ID format (UUID vs integer)
- Pagination offset calculation
- Section-level community endpoint

**Approach:** Analyze each failure, apply quick fix (<30 min each)

**Test Coverage:** 6 E2E tests fixed → **4 Perfect Groups**

---

### Phase 5: E2E Testing & Documentation (3 SP)

#### Feature 104.14: Full E2E Test Execution (2 SP)

**Deliverables:**
1. Run all 194 E2E tests after Phase 1-4 fixes
2. Identify remaining failures (<10 expected)
3. Quick fixes for any low-hanging fruit
4. Document final results

**Execution:**
```bash
cd frontend
npm run test:e2e -- --workers=4
```

**Expected Results:**
- ✅ 185+/194 tests passing (95%+)
- ❌ <10 tests failing (complex edge cases)
- ⏭️ 0 tests skipped

**Acceptance Criteria:**
- ✅ 185+/194 E2E tests passing (95%+)
- ✅ All groups >85% pass rate
- ✅ 10+ Perfect Groups (100% pass rate)
- ✅ No P0 blockers remaining

---

#### Feature 104.15: Sprint 104 Documentation (1 SP)

**Deliverables:**
1. `docs/sprints/SPRINT_104_COMPLETE.md` - Final results with detailed test breakdown
2. `docs/sprints/SPRINT_104_SUMMARY.md` - Sprint overview and achievements
3. Update `docs/sprints/SPRINT_PLAN.md` - Mark Sprint 104 ✅ Complete
4. Update `CLAUDE.md` - Add Sprint 104 summary line
5. Update `README.md` - Update Current Sprint Status section

**Acceptance Criteria:**
- ✅ Complete documentation of all 15 features
- ✅ Test results documented by group with before/after comparison
- ✅ Sprint 105 recommendations provided
- ✅ Technical debt items updated (resolved TDs archived)

---

## 📊 Success Metrics

### Primary Metrics

| Metric | Sprint 103 | Sprint 104 Target | Improvement |
|--------|------------|-------------------|-------------|
| **E2E Pass Rate** | 56% (107/194) | **95%+ (185+/194)** | **+39pp** 🎯 |
| **Tests Fixed** | +97 from Sprint 102 | **+78 from Sprint 103** | +175 total |
| **Blocked Groups (0%)** | 3 groups | **0 groups** | -3 groups |
| **Perfect Groups (100%)** | 2 groups | **10+ groups** | +8 groups |
| **Production Readiness** | 56% | **95%+** | **+39pp** |

### Group-Specific Targets (COMPLETE)

| Group | Current | Target | Delta | Feature | Impact |
|-------|---------|--------|-------|---------|--------|
| Group 1 (MCP Tools) | 68% (13/19) | **95%** (18/19) | +27pp | 104.3 | data-testid |
| Group 2 (Bash) | 94% (15/16) | **100%** (16/16) | +6pp | 104.13 | Easy Win |
| Group 3 (Python) | **100%** (16/16) | **100%** (16/16) | 0 | - | Already perfect |
| Group 4 (Browser) | 0% (0/6) | **100%** (6/6) | **+100pp** | 104.8 | New UI |
| Group 5 (Skills) | 0% (0/8) | **100%** (8/8) | **+100pp** | 104.1 | data-testid |
| Group 6 (Skills+Tools) | 0% (0/9) | **100%** (9/9) | **+100pp** | 104.2 | data-testid |
| Group 7 (Memory) | 20% (3/15) | **93%** (14/15) | +73pp | 104.4 | DOM fix |
| Group 8 (Deep Research) | **100%** (11/11) | **100%** (11/11) | 0 | - | Already perfect |
| Group 9 (Long Context) | 85% (11/13) | **100%** (13/13) | +15pp | 104.13 | Easy Win |
| Group 10 (Hybrid Search) | 38% (5/13) | **85%** (11/13) | +47pp | 104.12 | Mocks |
| Group 11 (Upload) | 87% (13/15) | **100%** (15/15) | +13pp | 104.13 | Easy Win |
| Group 12 (Communities) | 93% (14/15) | **100%** (15/15) | +7pp | 104.13 | Easy Win |
| Group 13 (Agent Hier) | 25% (2/8) | **100%** (8/8) | **+75pp** | 104.5 | data-testid |
| Group 14 (GDPR/Audit) | 21% (3/14) | **86%** (12/14) | +65pp | 104.6, 104.9 | API fixes |
| Group 15 (Explainability) | 31% (4/13) | **100%** (13/13) | **+69pp** | 104.7, 104.10 | data-testid + Backend |

### Perfect Groups (100% Pass Rate)

**Target: 10+ Perfect Groups**

1. ✅ Group 2 (Bash Execution) - 16/16
2. ✅ Group 3 (Python Execution) - 16/16
3. ✅ Group 4 (Browser Tools) - 6/6 (NEW)
4. ✅ Group 5 (Skills Management) - 8/8
5. ✅ Group 6 (Skills Using Tools) - 9/9
6. ✅ Group 8 (Deep Research) - 11/11
7. ✅ Group 9 (Long Context) - 13/13
8. ✅ Group 11 (Document Upload) - 15/15
9. ✅ Group 12 (Graph Communities) - 15/15
10. ✅ Group 13 (Agent Hierarchy) - 8/8
11. ✅ Group 15 (Explainability) - 13/13

**Total: 11 Perfect Groups** (vs 2 currently)

### Remaining Failures After Sprint 104

**Expected: 8-10 failures total (<5%)**

- Group 1: 1 failure (complex MCP integration edge case)
- Group 7: 1 failure (memory consolidation timing issue)
- Group 10: 2 failures (complex hybrid search scenarios)
- Group 14: 2 failures (complex GDPR multi-consent scenarios)
- **Total: 6 failures** (3.1% failure rate)

---

## 💼 Story Points Breakdown

| Feature | Component | SP | Priority | Tests Fixed |
|---------|-----------|----|----|-------------|
| **Phase 1: data-testid Blitz** | | **10** | **P0** | **58 tests** |
| 104.1 SkillRegistry data-testid | Frontend | 2 | P0 | +8 tests |
| 104.2 AgentCommunication data-testid | Frontend | 2 | P0 | +9 tests |
| 104.3 MCPToolsPage data-testid | Frontend | 1 | P0 | +5 tests |
| 104.4 MemoryManagement data-testid | Frontend | 2 | P0 | +11 tests |
| 104.5 AgentHierarchy data-testid | Frontend | 2 | P0 | +6 tests |
| 104.6 GDPR/Audit data-testid | Frontend | 1 | P0 | +7 tests |
| 104.7 Explainability data-testid | Frontend | 2 | P0 | +7 tests |
| **Phase 2: Browser Tools** | | **3** | **P0** | **6 tests** |
| 104.8 BrowserToolsPage Creation | Frontend | 3 | P0 | +6 tests |
| **Phase 3: Backend Integration** | | **6** | **P1** | **11 tests** |
| 104.9 GDPR/Audit API Fixes | Backend + Frontend | 2 | P1 | +2 tests |
| 104.10 Explainability Backend | Backend + Frontend | 2 | P1 | +2 tests |
| 104.11 Skills Backend Verify | Backend | 2 | P2 | 0 tests (verification) |
| **Phase 4: Mock Data Fixes** | | **4** | **P2** | **12 tests** |
| 104.12 Hybrid Search Mocks | Tests | 2 | P2 | +6 tests |
| 104.13 Easy Wins (Groups 2,9,11,12) | Tests | 2 | P2 | +6 tests |
| **Phase 5: Testing & Docs** | | **3** | **P0** | **Validation** |
| 104.14 Full E2E Test Execution | Tests | 2 | P0 | Validation |
| 104.15 Documentation | Docs | 1 | P0 | Documentation |
| **TOTAL** | | **28 SP** | | **+78 tests** |

---

## 🚀 Implementation Strategy

### Parallel Execution Plan

**Phase 1 (10 SP):** 7 Frontend-Agents parallel → 3-4 hours
- Agent 1: SkillRegistry data-testid (104.1)
- Agent 2: AgentCommunication data-testid (104.2)
- Agent 3: MCPToolsPage data-testid (104.3)
- Agent 4: MemoryManagement data-testid (104.4)
- Agent 5: AgentHierarchy data-testid (104.5)
- Agent 6: GDPR/Audit data-testid (104.6)
- Agent 7: Explainability data-testid (104.7)

**Phase 2 (3 SP):** 1 Frontend-Agent → 2-3 hours
- Agent 1: BrowserToolsPage Creation (104.8)

**Phase 3 (6 SP):** 3 Agents parallel → 2-3 hours
- Agent 1: GDPR/Audit API Fixes (104.9) - Backend
- Agent 2: Explainability Backend (104.10) - Backend
- Agent 3: Skills Backend Verify (104.11) - Backend

**Phase 4 (4 SP):** 2 Agents parallel → 2-3 hours
- Agent 1: Hybrid Search Mocks (104.12)
- Agent 2: Easy Wins (104.13)

**Phase 5 (3 SP):** Sequential → 2 hours
- E2E Test Execution (104.14)
- Documentation (104.15)

**Total Estimated Time:** 10-14 hours (1.5 working days with parallel execution)

---

## 🔗 Dependencies

### External Dependencies
- None (all tools and infrastructure ready)

### Internal Dependencies
- ✅ Sprint 103 MCP Backend (complete)
- ✅ Sprint 95-98 Frontend UIs (complete)
- ✅ Sprint 100 API Contract Spec (partial - completing in 104.9)
- ✅ Playwright E2E Test Framework (complete)

---

## ⚠️ Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| data-testid additions miss edge cases | Medium | Medium | Analyze ALL test files before implementation |
| Browser Tools Page complexity exceeds 3 SP | Low | Medium | Use existing MCPToolsPage as template |
| Backend API changes break existing tests | Low | High | Run E2E tests after each backend change |
| Easy Wins take longer than expected | Medium | Low | Budget 2 SP = 4-6 hours for 6 tests |
| Parallel execution coordination overhead | Low | Medium | Clear agent assignments, no overlapping files |

---

## ✅ Definition of Done

Sprint 104 is **COMPLETE** when:

1. ✅ **185+/194 E2E tests** passing (95%+ pass rate)
2. ✅ **All 15 features** implemented and tested
3. ✅ **10+ Perfect Groups** (100% pass rate)
4. ✅ **0 Blocker Groups** (<50% pass rate)
5. ✅ **<10 failures** remaining (all documented as complex edge cases)
6. ✅ **Unit test coverage** >80% on all new components
7. ✅ **Complete documentation** created (SPRINT_104_COMPLETE.md, SUMMARY.md)
8. ✅ **Sprint 105 plan** drafted with recommendations

---

## 📋 Sprint 105 Preview (Future Work)

**Remaining Work After Sprint 104:**

1. **Final 5% Polish** (6-10 remaining failures)
   - Complex MCP integration edge cases
   - Memory consolidation timing issues
   - Multi-consent GDPR scenarios
   - **Estimated:** 4-6 SP

2. **Performance Optimization**
   - Response times <200ms P95
   - E2E test runtime <5 minutes
   - **Estimated:** 6-8 SP

3. **RAGAS Phase 2 Evaluation** (deferred from Sprint 88)
   - Tables + Code QA evaluation
   - Comprehensive metrics schema
   - **Estimated:** 10-12 SP

4. **Domain Training Optimization** (deferred from Sprint 103)
   - DSPy prompt optimization
   - Multi-domain training
   - **Estimated:** 8-10 SP

**Estimated Sprint 105:** 28-36 SP
**Goal:** 98%+ E2E Pass Rate + Performance + RAGAS Phase 2

---

## 🎯 Sprint 104 Summary

**What Makes This Sprint Different:**

1. **UIs Already Exist!** Only 1 new page needed (Browser Tools), rest is data-testid additions
2. **72% of failures** are just missing test IDs → Quick wins with parallel frontend-agents
3. **Backend mostly complete** from Sprint 103 → Only API contract fixes needed
4. **Aggressive but achievable** → 95%+ pass rate with 28 SP in 1.5 days

**Key Success Factors:**
- ✅ Parallel execution (7 agents in Phase 1)
- ✅ Clear component ownership (no file conflicts)
- ✅ Existing UIs as templates (copy-paste data-testid patterns)
- ✅ Backend APIs ready (just format fixes)

**Expected Outcome:**
- **185+/194 tests passing** (95%+)
- **11 Perfect Groups** (vs 2 currently)
- **Full Production Readiness** 🎉
