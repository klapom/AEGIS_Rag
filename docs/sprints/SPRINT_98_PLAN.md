# Sprint 98 Plan: Governance & Monitoring UI

**Epic:** AegisRAG UI Completion - Sprints 90-96 Feature Coverage
**Phase:** Governance & Monitoring
**Prerequisite:** Sprint 97 (Skill Management UI)
**Duration:** 14-18 days
**Total Story Points:** 40 SP
**Status:** 📝 Planned

---

## Sprint Goal

Complete **Governance & Monitoring UI** for Sprints 90-96 backend features:
1. **Agent Communication Dashboard** - Monitor MessageBus, Blackboard, Orchestrator (Sprint 94)
2. **Agent Hierarchy Visualizer** - Visualize Executive→Manager→Worker delegation (Sprint 95)
3. **GDPR Consent Manager UI** - **EU Legal Requirement** - Manage consents, data subject rights (Sprint 96)
4. **Audit Trail Viewer** - **EU AI Act Art. 12** - View audit logs, compliance reports (Sprint 96)
5. **Explainability Dashboard** - **EU AI Act Art. 13** - Show decision traces, source attribution (Sprint 96)
6. **Certification Status Dashboard** - Show skill certifications, validation reports (Sprint 96)

**Target Outcome:** Full UI coverage for Sprints 90-96, EU compliance readiness, enterprise deployability

---

## Context: Sprint 97 vs Sprint 98

### Sprint 97: Skill Management UI (38 SP) ✅ Covers Sprint 90-93
- ✅ 97.1: Skill Registry Browser (10 SP) - Sprint 90 (Skill Registry)
- ✅ 97.2: Skill Configuration Editor (10 SP) - Sprint 91 (Skill Router)
- ✅ 97.3: Tool Authorization Manager (8 SP) - Sprint 93 (Tool Composition)
- ✅ 97.4: Skill Lifecycle Dashboard (6 SP) - Sprint 92 (Skill Lifecycle)
- ✅ 97.5: SKILL.md Visual Editor (4 SP) - Sprint 90 (SKILL.md structure)

### Sprint 98: Governance & Monitoring UI (40 SP) ⏳ Covers Sprint 94-96
- ⏳ 98.1: Agent Communication Dashboard (8 SP) - Sprint 94 (MessageBus, Orchestrator)
- ⏳ 98.2: Agent Hierarchy Visualizer (6 SP) - Sprint 95 (Hierarchical Agents)
- ⏳ 98.3: GDPR Consent Manager UI (8 SP) - Sprint 96 (GDPR Compliance) **P0 Legal**
- ⏳ 98.4: Audit Trail Viewer (6 SP) - Sprint 96 (Audit Trail) **P0 Legal**
- ⏳ 98.5: Explainability Dashboard (8 SP) - Sprint 96 (Explainability) **P0 Legal**
- ⏳ 98.6: Certification Status Dashboard (4 SP) - Sprint 96 (Certification) **P1**

---

## Features

| # | Feature | SP | Priority | Backend Coverage |
|---|---------|-----|----------|------------------|
| 98.1 | Agent Communication Dashboard | 8 | P0 | Sprint 94 (MessageBus, Blackboard, Orchestrator) |
| 98.2 | Agent Hierarchy Visualizer | 6 | P0 | Sprint 95 (Hierarchical Agents, Skill Libraries) |
| 98.3 | GDPR Consent Manager UI | 8 | P0 | Sprint 96 (GDPR Compliance Layer) |
| 98.4 | Audit Trail Viewer | 6 | P0 | Sprint 96 (Audit Trail System) |
| 98.5 | Explainability Dashboard | 8 | P0 | Sprint 96 (Explainability Engine) |
| 98.6 | Certification Status Dashboard | 4 | P1 | Sprint 96 (Certification Framework) |

**Total:** 40 SP

---

## Feature 98.1: Agent Communication Dashboard (8 SP)

### Description

Monitor inter-agent communication for debugging and performance optimization. Provides real-time visibility into MessageBus messages, Shared Memory (Blackboard) state, and Skill Orchestrator workflows.

### Backend Coverage

**Sprint 94 Features:**
- Feature 94.1: Agent Messaging Bus (8 SP)
- Feature 94.2: Shared Memory Protocol (Blackboard) (8 SP)
- Feature 94.3: Skill Orchestrator (10 SP)

### UI Components

```typescript
// src/frontend/src/pages/Admin/AgentCommunication.tsx

export const AgentCommunicationDashboard: React.FC = () => {
  return (
    <div className="agent-communication-dashboard">
      {/* Real-time MessageBus Monitor */}
      <MessageBusMonitor />

      {/* Blackboard State Viewer */}
      <BlackboardViewer />

      {/* Active Orchestrations Timeline */}
      <OrchestrationTimeline />

      {/* Performance Metrics */}
      <CommunicationMetrics />
    </div>
  );
};
```

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│ Agent Communication Dashboard                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Real-time MessageBus] [Blackboard] [Orchestrations]       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ MessageBus (Live)                    [Pause] [Clear]  │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │ 14:23:45 VectorAgent → GraphAgent: SKILL_REQUEST      │  │
│  │   skill: retrieval, context_budget: 2000              │  │
│  │   [View Details]                                      │  │
│  │                                                       │  │
│  │ 14:23:46 GraphAgent → VectorAgent: SKILL_RESPONSE     │  │
│  │   result: {...}, duration: 120ms                      │  │
│  │   [View Details]                                      │  │
│  │                                                       │  │
│  │ 14:23:47 Orchestrator → ALL: BROADCAST                │  │
│  │   message: "Phase 2 complete, starting Phase 3"      │  │
│  │   [View Details]                                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Blackboard State                                      │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │ Namespace: retrieval                                  │  │
│  │   results: [...], confidence: 0.92                    │  │
│  │   [View Full State]                                   │  │
│  │                                                       │  │
│  │ Namespace: synthesis                                  │  │
│  │   summary: "...", confidence: 0.87                    │  │
│  │   [View Full State]                                   │  │
│  │                                                       │  │
│  │ Namespace: reflection                                 │  │
│  │   issues: [], confidence: 0.95                        │  │
│  │   [View Full State]                                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Active Orchestrations (2)                             │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │ research_workflow_7a2b                                │  │
│  │   Phase 2/3 (Aggregation) - 67% complete             │  │
│  │   Skills: [retrieval✅, web_search✅, synthesis⏸️]   │  │
│  │   [View Timeline]                                     │  │
│  │                                                       │  │
│  │ analysis_task_9f4c                                    │  │
│  │   Phase 1/2 (Parallel) - 40% complete                │  │
│  │   Skills: [analysis⏸️, validation⏳]                  │  │
│  │   [View Timeline]                                     │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Performance Metrics                                   │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │ Message Latency (P95): 25ms                           │  │
│  │ Orchestration Duration (Avg): 1,200ms                 │  │
│  │ Blackboard Writes: 342 (last hour)                    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### API Endpoints

```typescript
// Backend API endpoints needed

// MessageBus
GET /api/v1/agents/messages?timeRange=1h&agentId={id}
GET /api/v1/agents/messages/{messageId}

// Blackboard
GET /api/v1/agents/blackboard
GET /api/v1/agents/blackboard/{namespace}

// Orchestration
GET /api/v1/orchestration/active
GET /api/v1/orchestration/{id}/trace
GET /api/v1/orchestration/{id}/metrics
```

### Test Coverage

```typescript
// tests/e2e/agent-communication.spec.ts
describe('Agent Communication Dashboard', () => {
  test('should display real-time agent messages', async ({ page }) => {
    // Navigate to dashboard
    // Submit query to trigger messaging
    // Verify messages appear
  });

  test('should view blackboard state', async ({ page }) => {
    // Switch to Blackboard tab
    // Verify namespaces displayed
  });

  test('should monitor active orchestrations', async ({ page }) => {
    // Verify orchestrations listed
    // View orchestration timeline
  });
});
```

---

## Feature 98.2: Agent Hierarchy Visualizer (6 SP)

### Description

Visualize agent hierarchy for system understanding and debugging. Interactive tree showing Executive→Manager→Worker structure with delegation chains.

### Backend Coverage

**Sprint 95 Features:**
- Feature 95.1: Hierarchical Agent Pattern (10 SP)
- Feature 95.2: Skill Libraries & Bundles (8 SP)

### UI Components

```typescript
// src/frontend/src/pages/Admin/AgentHierarchy.tsx

import * as d3 from 'd3';

export const AgentHierarchyVisualizer: React.FC = () => {
  const [hierarchyData, setHierarchyData] = useState<HierarchyNode | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentDetails | null>(null);

  return (
    <div className="agent-hierarchy-visualizer">
      {/* D3.js Tree Visualization */}
      <HierarchyTree data={hierarchyData} onNodeClick={setSelectedAgent} />

      {/* Agent Details Panel */}
      {selectedAgent && (
        <AgentDetailsPanel agent={selectedAgent} />
      )}

      {/* Task Delegation Tracer */}
      <DelegationChainTracer />
    </div>
  );
};
```

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│ Agent Hierarchy                                  [Reset Zoom]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────┐  ┌───────────────────┐│
│  │   Hierarchy Tree (D3.js)        │  │ Agent Details     ││
│  │                                 │  │ ───────────────── ││
│  │           ┌──────────────┐       │  │ Research Manager  ││
│  │           │  Executive   │       │  │                   ││
│  │           │  Director    │       │  │ Level: MANAGER    ││
│  │           │ [planner,    │       │  │ Skills:           ││
│  │           │  orchestrator]│      │  │ - research        ││
│  │           └──────┬───────┘       │  │ - web_search      ││
│  │                  │               │  │ - fact_check      ││
│  │      ┌───────────┼───────────┐   │  │                   ││
│  │      ▼           ▼           ▼   │  │ Active Tasks: 2   ││
│  │ ┌──────────┐┌──────────┐┌──────┐│  │ - Task #7a2b      ││
│  │ │Research  ││Analysis  ││Synth.││  │ - Task #9f4c      ││
│  │ │Manager   ││Manager   ││Mgr   ││  │                   ││
│  │ │[research]││[analysis]││[syn] ││  │ Performance:      ││
│  │ └────┬─────┘└────┬─────┘└──┬───┘│  │ Success: 87%      ││
│  │      │           │         │    │  │ Latency: 450ms    ││
│  │ ┌────┴──┐   ┌────┴──┐  ┌──┴──┐ │  │ Tasks Done: 142   ││
│  │ ▼  ▼  ▼    ▼  ▼  ▼   ▼  ▼  ▼  │  │                   ││
│  │W1 W2 W3   W4 W5 W6  W7 W8 W9   │  │ [View Logs]       ││
│  │                                 │  │ [View Tasks]      ││
│  └─────────────────────────────────┘  └───────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┤
│  │ Task Delegation Tracer                                  │
│  │ Select Task: [research_workflow_7a2b  ▼]                │
│  │                                                         │
│  │ Delegation Chain:                                       │
│  │ Executive Director → Research Manager → W1 (Retrieval)  │
│  │ [Highlight in Tree]                                     │
│  └─────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

### API Endpoints

```typescript
// Backend API endpoints needed

GET /api/v1/agents/hierarchy
GET /api/v1/agents/{id}/details
GET /api/v1/agents/{id}/current-tasks
GET /api/v1/agents/{id}/performance
GET /api/v1/agents/task/{taskId}/delegation-chain
```

### Test Coverage

```typescript
// tests/e2e/agent-hierarchy.spec.ts
describe('Agent Hierarchy Visualizer', () => {
  test('should display agent hierarchy tree', async ({ page }) => {
    // Navigate to hierarchy
    // Verify tree renders
  });

  test('should click agent node to view details', async ({ page }) => {
    // Click node
    // Verify details panel shows
  });

  test('should trace task delegation chain', async ({ page }) => {
    // Select task
    // Verify delegation path highlighted
  });
});
```

---

## Feature 98.3: GDPR Consent Manager UI (8 SP) **P0 - EU Legal Requirement**

### Description

**EU Legal Requirement** - Manage user consents and data subject rights. Implements GDPR Articles 6, 7, 13-17, 20, 30 UI workflows.

### Backend Coverage

**Sprint 96 Feature:**
- Feature 96.1: GDPR/DSGVO Compliance Layer (10 SP)
- Implements: Consent Management, Data Subject Rights, PII Detection, Processing Records

### UI Components

```typescript
// src/frontend/src/pages/Admin/GDPRConsent.tsx

export const GDPRConsentManager: React.FC = () => {
  return (
    <div className="gdpr-consent-manager">
      {/* Consent Registry */}
      <ConsentRegistry />

      {/* Data Subject Rights Handler */}
      <DataSubjectRights />

      {/* Processing Activity Log (Art. 30) */}
      <ProcessingActivityLog />

      {/* PII Redaction Settings */}
      <PIIRedactionSettings />
    </div>
  );
};
```

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│ GDPR Consent Management                         [Add Consent]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Consents] [Data Subject Rights] [Processing Activities]   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Active Consents (3)                                   │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │                                                       │  │
│  │ ✅ user_123 - Customer Support                        │  │
│  │    Legal Basis: Contract (Art. 6(1)(b))              │  │
│  │    Data Categories: [identifier, contact]            │  │
│  │    Granted: 2025-12-01 | Expires: 2026-12-01         │  │
│  │    Skill Restrictions: [customer_support]            │  │
│  │    [Revoke] [Edit] [View Details]                    │  │
│  │                                                       │  │
│  │ ✅ user_456 - Marketing Communications               │  │
│  │    Legal Basis: Consent (Art. 6(1)(a))               │  │
│  │    Data Categories: [contact, behavioral]            │  │
│  │    Granted: 2026-01-10 | Expires: Never              │  │
│  │    Skill Restrictions: None                          │  │
│  │    [Revoke] [Edit] [View Details]                    │  │
│  │                                                       │  │
│  │ ⚠️ user_789 - Research Participation                 │  │
│  │    Legal Basis: Consent (Art. 6(1)(a))               │  │
│  │    Data Categories: [identifier, health]             │  │
│  │    Granted: 2025-06-15 | Expires: 2026-06-15 (soon!) │  │
│  │    Skill Restrictions: [research, analysis]          │  │
│  │    [Renew] [Revoke] [View Details]                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Data Subject Rights Requests (1 pending)              │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │ Request #789: Right to Erasure (user_123)            │  │
│  │ Article: GDPR Art. 17                                │  │
│  │ Submitted: 2026-01-14 14:30                          │  │
│  │ Status: ⏳ Pending Review                             │  │
│  │ Scope:                                               │  │
│  │ - Revoke all consents                                │  │
│  │ - Delete processing records                          │  │
│  │ - Purge cached data from all skills                  │  │
│  │                                                       │  │
│  │ [Approve & Execute] [Reject] [Request Info]          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### API Endpoints

```typescript
// Backend API endpoints (from Sprint 96)

// Consents (Art. 6, 7)
GET /api/v1/gdpr/consents?userId={id}&status=active|withdrawn
POST /api/v1/gdpr/consent
PUT /api/v1/gdpr/consent/{id}
DELETE /api/v1/gdpr/consent/{id}

// Data Subject Rights (Art. 15-22)
POST /api/v1/gdpr/erasure-request
POST /api/v1/gdpr/rectification-request
GET /api/v1/gdpr/data-export?userId={id}
GET /api/v1/gdpr/access-request?userId={id}

// Processing Activities (Art. 30)
GET /api/v1/gdpr/processing-activities?timeRange=30d
GET /api/v1/gdpr/processing-activities?userId={id}

// PII Detection
POST /api/v1/gdpr/detect-pii
POST /api/v1/gdpr/redact-pii
```

### Test Coverage

```typescript
// tests/e2e/gdpr-consent.spec.ts
describe('GDPR Consent Manager', () => {
  test('should create new consent record', async ({ page }) => {
    // Fill consent form
    // Save and verify
  });

  test('should revoke consent', async ({ page }) => {
    // Click revoke
    // Confirm
    // Verify status updated
  });

  test('should handle right to erasure request', async ({ page }) => {
    // Submit erasure request
    // Approve
    // Verify data purged
  });

  test('should export user data (Art. 20 portability)', async ({ page }) => {
    // Request export
    // Verify JSON download
  });
});
```

---

## Feature 98.4: Audit Trail Viewer (6 SP) **P0 - EU AI Act Art. 12**

### Description

**EU AI Act Art. 12** - View audit logs and generate compliance reports. Displays immutable audit trail with cryptographic integrity verification.

### Backend Coverage

**Sprint 96 Feature:**
- Feature 96.2: Audit Trail System (8 SP)
- Implements: Immutable audit log, cryptographic chain, compliance reporting

### UI Components

```typescript
// src/frontend/src/pages/Admin/AuditTrail.tsx

export const AuditTrailViewer: React.FC = () => {
  return (
    <div className="audit-trail-viewer">
      {/* Audit Log Browser */}
      <AuditLogBrowser />

      {/* Compliance Reports */}
      <ComplianceReports />

      {/* Integrity Verification */}
      <IntegrityVerification />

      {/* Export Functions */}
      <AuditExport />
    </div>
  );
};
```

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│ Audit Trail Viewer                       [Verify Integrity] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Filters:                                                   │
│  Event Type: [All ▼] Actor: [All ▼] Time: [Last 24h ▼]     │
│  Search: [____________________] [Apply]                     │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Audit Events (Latest 50)                              │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │                                                       │  │
│  │ 🟢 2026-01-15 14:25:32 | SKILL_EXECUTED                │  │
│  │    Actor: user_123 → retrieval skill                  │  │
│  │    Resource: query_7a3f9b                             │  │
│  │    Outcome: ✅ success, 120ms                          │  │
│  │    Hash: 7a3f9b... (chain verified ✓)                │  │
│  │    [View Details]                                     │  │
│  │                                                       │  │
│  │ 🟡 2026-01-15 14:25:30 | DATA_READ                     │  │
│  │    Actor: retrieval skill → document_7f3a             │  │
│  │    Resource: document_7f3a                            │  │
│  │    Outcome: ✅ success                                 │  │
│  │    Hash: 5d2c8a... (chain verified ✓)                │  │
│  │    Metadata: data_categories: [identifier, contact]  │  │
│  │    [View Details]                                     │  │
│  │                                                       │  │
│  │ 🟢 2026-01-15 14:25:20 | AUTH_SUCCESS                  │  │
│  │    Actor: user_123                                    │  │
│  │    Resource: /api/v1/chat                             │  │
│  │    Outcome: ✅ success                                 │  │
│  │    Hash: 9e1b4f... (chain verified ✓)                │  │
│  │    [View Details]                                     │  │
│  │                                                       │  │
│  │ 🔴 2026-01-15 14:24:10 | POLICY_VIOLATION              │  │
│  │    Actor: user_456 → shell tool                       │  │
│  │    Resource: shell_exec                               │  │
│  │    Outcome: ❌ blocked (insufficient permissions)      │  │
│  │    Hash: 3c7d2a... (chain verified ✓)                │  │
│  │    [View Details]                                     │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Quick Actions                                         │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │ [Generate GDPR Report (Art. 30)]                      │  │
│  │ [Generate Security Report]                            │  │
│  │ [Export to CSV] [Export to JSON]                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### API Endpoints

```typescript
// Backend API endpoints (from Sprint 96)

// Query Events
GET /api/v1/audit/events?startTime={}&endTime={}&eventType={}&actorId={}
GET /api/v1/audit/events/{eventId}

// Compliance Reports
GET /api/v1/audit/reports/gdpr
GET /api/v1/audit/reports/security
GET /api/v1/audit/reports/skill-usage

// Integrity Verification
GET /api/v1/audit/integrity?startTime={}&endTime={}

// Export
GET /api/v1/audit/export?format=json|csv&startTime={}&endTime={}
```

### Test Coverage

```typescript
// tests/e2e/audit-trail.spec.ts
describe('Audit Trail Viewer', () => {
  test('should view audit events with filters', async ({ page }) => {
    // Navigate to audit trail
    // Apply filters
    // Verify filtered results
  });

  test('should verify audit chain integrity', async ({ page }) => {
    // Click "Verify Integrity"
    // Verify result displayed
  });

  test('should generate GDPR compliance report', async ({ page }) => {
    // Click "Generate GDPR Report"
    // Verify report displayed
  });

  test('should export audit log to CSV', async ({ page }) => {
    // Click "Export to CSV"
    // Verify download
  });
});
```

---

## Feature 98.5: Explainability Dashboard (8 SP) **P0 - EU AI Act Art. 13**

### Description

**EU AI Act Art. 13** - Show decision transparency and reasoning traces. Provides multi-level explanations (User/Expert/Audit) with source attribution.

### Backend Coverage

**Sprint 96 Feature:**
- Feature 96.3: Explainability Engine (8 SP)
- Implements: Decision traces, source attribution, multi-level explanations

### UI Components

```typescript
// src/frontend/src/pages/Admin/Explainability.tsx

export const ExplainabilityDashboard: React.FC = () => {
  return (
    <div className="explainability-dashboard">
      {/* Decision Trace Viewer */}
      <DecisionTraceViewer />

      {/* Multi-level Explanations (User/Expert/Audit) */}
      <ExplanationLevels />

      {/* Source Attribution Panel */}
      <SourceAttributionPanel />

      {/* Confidence Metrics */}
      <ConfidenceMetrics />
    </div>
  );
};
```

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│ Explainability Dashboard                [Recent Traces ▼]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Query: "What are the latest quantum computing trends?"     │
│  Trace ID: trace_1737052332_decision.routed                │
│  Timestamp: 2026-01-15 14:25:32                            │
│                                                             │
│  Explanation Level:  ◉ User View  ○ Expert View  ○ Audit   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ How this answer was generated:                        │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │                                                       │  │
│  │ This response was created with **high confidence**   │  │
│  │ (87%) using information from:                        │  │
│  │                                                       │  │
│  │ • quantum_computing_2025.pdf (relevance: 94%)        │  │
│  │ • arxiv_2501_trends.pdf (relevance: 89%)             │  │
│  │ • nature_qc_review.pdf (relevance: 82%)              │  │
│  │                                                       │  │
│  │ The system used **3 specialized capabilities**        │  │
│  │ (retrieval, web_search, synthesis) to find and       │  │
│  │ combine the relevant information.                     │  │
│  │                                                       │  │
│  │ **Hallucination Risk:** Low (8%)                      │  │
│  │                                                       │  │
│  │ [Switch to Expert View for technical details]        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Decision Flow                                         │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │                                                       │  │
│  │ 1. Intent Classification                             │  │
│  │    ✓ RESEARCH (confidence: 92%)                      │  │
│  │                                                       │  │
│  │ 2. Skill Selection                                   │  │
│  │    ✓ research skill (trigger: "latest trends")       │  │
│  │    ✓ web_search skill (intent-based)                │  │
│  │    ✓ synthesis skill (auto-activated)               │  │
│  │                                                       │  │
│  │ 3. Retrieval                                         │  │
│  │    Mode: Hybrid (vector + graph)                     │  │
│  │    Retrieved: 15 chunks, Used: 8 chunks              │  │
│  │                                                       │  │
│  │ 4. Response Generation                               │  │
│  │    Duration: 1,200ms                                 │  │
│  │    Tokens: 487                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Source Attribution                                    │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │ [quantum_computing_2025.pdf] Page 12-14              │  │
│  │   "Recent advances in topological qubits..."         │  │
│  │   Relevance: 94% | Confidence: High                  │  │
│  │                                                       │  │
│  │ [arxiv_2501_trends.pdf] Page 3-5                     │  │
│  │   "Industry adoption of quantum annealing..."        │  │
│  │   Relevance: 89% | Confidence: High                  │  │
│  │                                                       │  │
│  │ [nature_qc_review.pdf] Page 8                        │  │
│  │   "Comparison of gate-based vs annealing..."         │  │
│  │   Relevance: 82% | Confidence: Medium                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### API Endpoints

```typescript
// Backend API endpoints (from Sprint 96)

// Decision Traces
GET /api/v1/explainability/trace/{traceId}
GET /api/v1/explainability/recent?userId={}&limit=10

// Multi-level Explanations
GET /api/v1/explainability/explain/{traceId}?level=user|expert|audit

// Source Attribution
GET /api/v1/explainability/attribution/{traceId}?claim={}
GET /api/v1/explainability/sources/{traceId}
```

### Test Coverage

```typescript
// tests/e2e/explainability.spec.ts
describe('Explainability Dashboard', () => {
  test('should view decision trace for query', async ({ page }) => {
    // Submit query
    // Navigate to explainability
    // View trace
  });

  test('should switch between explanation levels', async ({ page }) => {
    // View trace
    // Switch to Expert View
    // Verify technical details shown
  });

  test('should view source attribution', async ({ page }) => {
    // View trace
    // Verify sources listed with relevance scores
  });

  test('should find source for specific claim', async ({ page }) => {
    // Enter claim
    // Click "Find Sources"
    // Verify sources highlighted
  });
});
```

---

## Feature 98.6: Certification Status Dashboard (4 SP) **P1**

### Description

Show skill certification levels and validation status. Displays compliance checks, validation reports, and expiring certifications.

### Backend Coverage

**Sprint 96 Feature:**
- Feature 96.4: Skill Certification Framework (4 SP)
- Implements: 3-tier certification (Basic/Standard/Enterprise), validation checks

### UI Components

```typescript
// src/frontend/src/pages/Admin/SkillCertification.tsx

export const CertificationDashboard: React.FC = () => {
  return (
    <div className="certification-dashboard">
      {/* Certification Overview */}
      <CertificationOverview />

      {/* Skill Certification Grid */}
      <SkillCertificationGrid />

      {/* Expiring Certifications Alert */}
      <ExpiringCertificationsAlert />

      {/* Validation Report Viewer */}
      <ValidationReportViewer />
    </div>
  );
};
```

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│ Skill Certification Dashboard            [Validate All]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Certification Overview                                     │
│  🟢 Enterprise: 8 skills | 🟡 Standard: 12 | ⚪ Basic: 5     │
│  ⚠️ Expiring Soon: 2 skills (within 30 days)                │
│                                                             │
│  Filter: [All Levels ▼] [Status ▼] [Search: _______]       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Skill Certifications                                  │  │
│  │ ───────────────────────────────────────────────────── │  │
│  │                                                       │  │
│  │ 🟢 retrieval                   ENTERPRISE             │  │
│  │    Version: 1.2.0                                     │  │
│  │    Valid until: 2027-01-15                            │  │
│  │    Last validated: 2026-01-15                         │  │
│  │    Checks: ✅ GDPR ✅ Security ✅ Audit ✅ Explainability│  │
│  │    [View Report] [Re-validate]                        │  │
│  │                                                       │  │
│  │ 🟢 synthesis                   ENTERPRISE             │  │
│  │    Version: 1.1.3                                     │  │
│  │    Valid until: 2027-01-10                            │  │
│  │    Last validated: 2026-01-10                         │  │
│  │    Checks: ✅ All passed                               │  │
│  │    [View Report] [Re-validate]                        │  │
│  │                                                       │  │
│  │ 🟡 web_search                  STANDARD               │  │
│  │    Version: 1.0.5                                     │  │
│  │    Valid until: 2026-12-20                            │  │
│  │    Last validated: 2025-12-20                         │  │
│  │    Issues: ⚠️ GDPR purpose declaration incomplete     │  │
│  │    [View Report] [Upgrade to Enterprise]              │  │
│  │                                                       │  │
│  │ 🔴 experimental_tool           BASIC                  │  │
│  │    Version: 0.9.0                                     │  │
│  │    Valid until: 2026-03-15 (expiring in 15 days!)    │  │
│  │    Last validated: 2025-03-15                         │  │
│  │    Issues: ❌ No audit integration                     │  │
│  │            ❌ Security patterns: blocked eval() found │  │
│  │    [View Report] [Fix Issues] [Upgrade]               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### API Endpoints

```typescript
// Backend API endpoints (from Sprint 96)

// Skill Certifications
GET /api/v1/certification/skills?level=&status=
GET /api/v1/certification/skill/{name}/report
POST /api/v1/certification/skill/{name}/validate
GET /api/v1/certification/expiring?days=30

// Certification Levels
GET /api/v1/certification/levels
GET /api/v1/certification/requirements/{level}
```

### Test Coverage

```typescript
// tests/e2e/skill-certification.spec.ts
describe('Certification Dashboard', () => {
  test('should view all skill certifications', async ({ page }) => {
    // Navigate to certification dashboard
    // Verify skills listed with levels
  });

  test('should view certification report', async ({ page }) => {
    // Click "View Report"
    // Verify checks displayed
  });

  test('should re-validate skill', async ({ page }) => {
    // Click "Validate"
    // Verify validation runs
    // Verify updated level
  });

  test('should show expiring certifications', async ({ page }) => {
    // Verify "Expiring Soon" section
    // Verify skills <30 days displayed
  });
});
```

---

## Deliverables

| Artifact | Location | Description | Status |
|----------|----------|-------------|--------|
| Agent Communication Dashboard | `frontend/src/pages/Admin/AgentCommunication.tsx` | MessageBus, Blackboard, Orchestrator UI | ⏳ TODO |
| Agent Hierarchy Visualizer | `frontend/src/pages/Admin/AgentHierarchy.tsx` | D3.js hierarchy tree | ⏳ TODO |
| GDPR Consent Manager | `frontend/src/pages/Admin/GDPRConsent.tsx` | Consent management, Data Subject Rights | ⏳ TODO |
| Audit Trail Viewer | `frontend/src/pages/Admin/AuditTrail.tsx` | Audit log browser, Compliance reports | ⏳ TODO |
| Explainability Dashboard | `frontend/src/pages/Admin/Explainability.tsx` | Decision traces, Source attribution | ⏳ TODO |
| Certification Dashboard | `frontend/src/pages/Admin/SkillCertification.tsx` | Skill certifications, Validation reports | ⏳ TODO |
| E2E Tests | `tests/e2e/10-governance.spec.ts` | Governance UI tests | ⏳ TODO |
| E2E Tests | `tests/e2e/11-agent-hierarchy.spec.ts` | Agent monitoring tests | ⏳ TODO |
| Documentation | `docs/guides/GOVERNANCE_UI_GUIDE.md` | User guide for governance features | ⏳ TODO |

---

## Success Criteria

| Metric | Target | Status |
|--------|--------|--------|
| Agent Communication Dashboard | Functional with real-time updates | ⏳ TODO |
| Agent Hierarchy Visualizer | Interactive D3.js tree with 100+ agents | ⏳ TODO |
| GDPR Consent Manager | Full Art. 6, 7, 13-22 support | ⏳ TODO |
| Audit Trail Viewer | 7-year retention, integrity verification | ⏳ TODO |
| Explainability Dashboard | 3-level explanations (User/Expert/Audit) | ⏳ TODO |
| Certification Dashboard | 3-tier framework (Basic/Standard/Enterprise) | ⏳ TODO |
| Test Coverage | 100% for all 6 features | ⏳ TODO |
| Code Quality | All deliverables documented | ⏳ TODO |
| EU Compliance | Full GDPR + AI Act Art. 12-13 | ⏳ TODO |

---

## Dependencies

### Sprint 97 (Prerequisite)
- Must be complete before Sprint 98 starts
- Shares Admin UI navigation structure
- Shares API authentication/authorization patterns

### Sprint 96 Backend (Complete)
- All Sprint 96 backend features implemented (GDPR, Audit, Explainability, Certification)
- APIs available for UI integration

### Sprint 94-95 Backend (Complete)
- Sprint 94: MessageBus, Blackboard, Orchestrator
- Sprint 95: Hierarchical Agents, Skill Libraries

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| D3.js visualization performance with 100+ agents | Medium | Implement virtual rendering, lazy loading |
| Real-time MessageBus streaming overhead | Medium | Use WebSocket with throttling, pagination |
| GDPR UI complexity (many forms/workflows) | High | Break into phased rollout, wizard UIs |
| Audit log query performance (7-year retention) | Medium | Add database indexing, pagination, caching |
| Explainability LLM call latency | Medium | Cache explanations, background generation |

---

## Alternative: Reduced Scope (26 SP)

If time-constrained, implement **P0 features only** (Features 98.1, 98.3, 98.4, 98.5):

| # | Feature | SP | Priority |
|---|---------|-----|----------|
| 98.1 | Agent Communication Dashboard | 8 | P0 |
| 98.3 | GDPR Consent Manager UI | 8 | P0 |
| 98.4 | Audit Trail Viewer | 6 | P0 |
| 98.5 | Explainability Dashboard (Basic only) | 6 | P0 (reduced) |

**Total:** 28 SP (reduced from 40 SP)

Defer P1 features (98.2 Agent Hierarchy, 98.6 Certification) to Sprint 99.

---

## Sprint 97-98 Summary

| Sprint | Focus | Features | SP | Backend Coverage |
|--------|-------|----------|-----|------------------|
| **97** | Skill Management UI | 5 | 38 | Sprints 90-93 (Skills, Tools, Lifecycle) |
| **98** | Governance & Monitoring UI | 6 | 40 | Sprints 94-96 (Communication, Hierarchy, Governance) |

**Total UI Implementation:** 11 features, 78 SP, complete coverage for Sprints 90-96

**Outcome:** Full-stack enterprise system with EU compliance readiness

---

**Document:** SPRINT_98_PLAN.md
**Status:** 📝 Planned
**Created:** 2026-01-15
**Dependencies:** Sprint 97 (Skill Management UI), Sprints 90-96 (Backend complete)
**Next Action:** Review with stakeholders, approve for implementation
