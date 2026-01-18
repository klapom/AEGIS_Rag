# Sprint 111 Plan - E2E Fixes + Long Context + Token Chart

**Status:** ✅ COMPLETE
**Target:** Complete E2E fixes + Long Context UI + Token Usage Chart
**Sprint Points:** 26 SP (26 SP complete)
**Completed:** 2026-01-18

**Results:**
- Feature 111.0: E2E Fixes ✅ 41/41 tests (100%)
- Feature 111.1: Long Context UI ✅ 10 SP, 10 tests
- Feature 111.2: Token Usage Chart ✅ 8 SP, 8 tests

**Note:** Sprint 111 now includes E2E test fixes from Sprint 110 deferred work.

---

## Sprint Goals

1. ✅ **Feature 111.0:** E2E Test Fixes for Groups 13-16 (8 SP) - **COMPLETE**
2. 📝 **Feature 111.1:** Implement Group 09 Long Context UI + E2E tests (10 SP)
3. 📝 **Feature 111.2:** Add Token Usage Over Time Chart to Cost Dashboard (8 SP)
4. Achieve 100% pass rate on Groups 01-03, 09, 13-16
5. Total: 26 SP, ~60 tests

---

## Feature 111.0: E2E Test Fixes (Groups 13-16) ✅ COMPLETE

**Status:** ✅ Complete
**Story Points:** 8 SP
**Test Results:** 41/41 (100%)

### Completed Fixes

| Group | Tests | Pass Rate | Key Fixes |
|-------|-------|-----------|-----------|
| **13** Agent Hierarchy | 8/8 | 100% | Zoom controls aria-labels, skills badges D3 format |
| **14** GDPR/Audit | 14/14 | 100% | Pagination controls, rights description, audit events |
| **15** Explainability | 13/13 | 100% | Model info section, audit trail link, decision paths |
| **16** MCP Marketplace | 6/6 | 100% | data-testid fix |

### Files Modified

- `AgentHierarchyD3.tsx`: Lowercase aria-labels for zoom controls
- `MCPServerBrowser.tsx`: Changed data-testid to `mcp-server-browser`
- `ConsentRegistry.tsx`: Added pagination controls (10 items/page)
- `DataSubjectRights.tsx`: Added rights description text
- `ExplainabilityPage.tsx`: Added model info section + audit trail link
- `group13-agent-hierarchy.spec.ts`: Fixed skills test mock format
- `group14-gdpr-audit.spec.ts`: Fixed audit events mock + pagination tests
- `group15-explainability.spec.ts`: Fixed API endpoint mocks

---

## Feature Breakdown

### Feature 111.1: Group 09 - Long Context (10 SP)

**Status:** ✅ Complete
**Priority:** ⭐ **HIGH** (User specifically requested)
**Story Points:** 10 SP
**Effort:** 1-2 days dedicated work

#### User Request Context

**Original Question:** "was ist mit den anderen SPRINT 109 features wie z.B. Long Context?"
**Decision:** Moved from Sprint 109 → Sprint 110 → Sprint 111 for dedicated focus

#### Scope

- **Large Document Handling:** >100K tokens, multi-megabyte files
- **Context Window Management UI:** Visual indicators for context usage
- **Document Chunking Visualization:** Interactive chunk explorer
- **Context Relevance Scoring:** Display relevance scores per chunk
- **Context Compression:** Strategies for fitting large contexts
- **Multi-Document Context:** Merging contexts from multiple sources

#### Test Coverage (10 tests)

1. **Large Document Upload** - Upload and process >100K token document
2. **Context Window Indicators** - Display current/max context usage
3. **Chunk Preview Functionality** - Navigate and preview document chunks
4. **Relevance Score Visualization** - Display chunk relevance scores
5. **Long Context Search** - Search within large context windows
6. **Context Compression Strategies** - Summarization, filtering UI
7. **Multi-Document Context Merging** - Combine contexts from multiple docs
8. **Context Overflow Handling** - Graceful degradation when context full
9. **Context Quality Metrics** - Display context quality indicators
10. **Context Export Functionality** - Export context data as JSON/Markdown

#### Component Requirements

**New Components Needed:**
```typescript
// Main container for long context features
LongContextViewer.tsx

// Visual gauge for context usage (0-100%)
ContextWindowIndicator.tsx

// Interactive chunk navigation
ChunkExplorer.tsx

// Score visualization component
RelevanceScoreDisplay.tsx

// Compression strategy selector
ContextCompressionPanel.tsx
```

**API Endpoints:**
- `GET /api/v1/context/documents/{doc_id}` - Get document with context metadata
- `GET /api/v1/context/chunks/{doc_id}` - Get all chunks for document
- `POST /api/v1/context/compress` - Trigger context compression
- `GET /api/v1/context/metrics` - Get context quality metrics

#### Success Criteria

- ✅ Upload and process documents >100K tokens
- ✅ Context window indicator shows accurate usage (0-100%)
- ✅ Chunk explorer allows navigation through 100+ chunks
- ✅ Relevance scores displayed consistently (0.00-1.00 format)
- ✅ Long context search returns results within 2s
- ✅ Context compression reduces size by >50%
- ✅ All 10 tests passing (100% pass rate)

---

### Feature 111.2: Cost Dashboard Token Usage Chart (8 SP)

**Status:** ✅ Complete
**Priority:** ⭐ **HIGH** (User requested)
**Story Points:** 8 SP
**Effort:** 1-2 days

#### User Request Context

**Original Request:** "Cost Dashboard - dort fehlt noch eine Grafik über die Tokennutzung über die Zeit.
Es sollen verschiedene Zeiträume eingegeben werden. Die Skala: per Schieberegler einstellbar (1 Tag - 3 Jahre)"

#### Scope

- **Token Usage Over Time Line Chart** - Using Recharts library
- **Time Range Slider** - Adjustable from 1 day to 3 years
- **Logarithmic/Linear Scale Toggle** - For different data ranges
- **Provider Filter** - Filter by provider (all/individual)
- **Aggregation Control** - Daily/Weekly/Monthly aggregation

#### Component Requirements

**New Components:**
```typescript
// Main chart component with Recharts
TokenUsageChart.tsx

// Time range slider with preset buttons (1d, 7d, 30d, 90d, 1y, 3y)
TimeRangeSlider.tsx

// Aggregation selector + Provider filter
ChartControls.tsx
```

**Backend Requirements:**

**New Endpoint:** `GET /api/v1/admin/costs/timeseries`

**Parameters:**
- `start` (ISO date) - Start date for range
- `end` (ISO date) - End date for range
- `aggregation` (string) - "daily" | "weekly" | "monthly"
- `provider` (string, optional) - Filter by provider

**Response Schema:**
```json
{
  "data": [
    {
      "date": "2026-01-17",
      "tokens": 150000,
      "cost_usd": 0.45,
      "provider": "ollama"
    },
    {
      "date": "2026-01-17",
      "tokens": 25000,
      "cost_usd": 0.03,
      "provider": "alibaba_cloud"
    }
  ],
  "total_tokens": 175000,
  "total_cost_usd": 0.48,
  "aggregation": "daily",
  "time_range": {
    "start": "2026-01-10",
    "end": "2026-01-17"
  }
}
```

#### UI Design

```
+----------------------------------------------------------+
| Token Usage Over Time                           [Export] |
|                                                          |
| Time Range: [1d] [7d] [30d] [90d] [1y] [3y] [Custom]    |
|                                                          |
| [=======================|--] Slider: 30 days            |
|                                                          |
| Provider: [All ▼]  Aggregation: [Daily ▼]  Scale: [○Lin ●Log] |
|                                                          |
|     ▲                                                   |
| 1M  │     ╭──╮                                          |
|     │    ╱    ╲    ╭──╮                                 |
| 500K│   ╱      ╲  ╱    ╲                                |
|     │  ╱        ╲╱      ╲___                            |
| 100K│ ╱                     ╲___                        |
|     │╱                          ╲___                    |
|   0 │─────────────────────────────────▶                 |
|     Jan 10   Jan 12   Jan 14   Jan 16   Jan 17          |
|                                                          |
| Total: 2.5M tokens | $12.34 | Last 30 days              |
+----------------------------------------------------------+
```

#### Test Coverage (8 tests)

1. **Chart Renders with Data** - Chart displays when data available
2. **Slider Changes Time Range** - Slider updates chart data correctly
3. **Provider Filter Works** - Single provider filtering
4. **Aggregation Toggle** - Daily/Weekly/Monthly updates chart
5. **Empty State Handling** - Graceful message when no data
6. **Loading State** - Spinner during data fetch
7. **Error State** - Error message on API failure
8. **Export Chart as PNG** - Download button works

#### Success Criteria

- ✅ Chart renders with real token data from backend
- ✅ Slider adjusts time range from 1 day to 3 years
- ✅ Provider filter correctly isolates data
- ✅ Aggregation changes granularity appropriately
- ✅ Logarithmic scale handles large value differences
- ✅ Export generates valid PNG file
- ✅ All 8 tests passing (100% pass rate)

---

## Sprint 111 Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **E2E Test Fixes** | 8 SP | 8 SP | ✅ Complete |
| **Feature 111.1 Long Context** | 10 SP | 10 SP | ✅ Complete |
| **Feature 111.2 Token Chart** | 8 SP | 8 SP | ✅ Complete |
| **Groups 01-03 Tests** | ~46 tests | 46/46 | ✅ 100% |
| **Group 09 Tests** | 23 tests | 23/23 | ✅ 100% |
| **Groups 13-16 Tests** | 41/41 | 41/41 | ✅ 100% |
| **Group 17 Tests** | 8/8 | 8/8 | ✅ 100% |
| **Total Story Points** | 26 SP | 26 SP | ✅ Complete |

---

## Sprint 111 Execution Order

### Phase 1: Long Context (PRIORITY ⭐)
**Duration:** 1-2 days
**SP:** 10 SP

1. **Day 1-2: Group 09 Long Context** (10 tests, 10 SP)
   - Implement UI components (5 components)
   - Connect to backend APIs (4 endpoints)
   - Write E2E tests (10 tests)
   - **Deliverable:** Long Context UI fully functional

### Phase 2: Cost Dashboard Token Chart
**Duration:** 1-2 days
**SP:** 8 SP

2. **Day 3-4: Token Usage Chart** (8 tests, 8 SP)
   - Create `TokenUsageChart.tsx` with Recharts
   - Build `TimeRangeSlider.tsx` (1d-3y range)
   - Implement `ChartControls.tsx` (aggregation, filter)
   - Add backend endpoint `/api/v1/admin/costs/timeseries`
   - Write E2E tests (8 tests)
   - **Deliverable:** Token usage chart with slider functional

**Sprint 111 Total Duration:** 3-4 days

---

## Dependencies & Blockers

### Feature 111.1 Long Context Dependencies
- ✅ Backend context window calculation (should exist)
- ✅ Qdrant chunk metadata storage (exists)
- ❓ Context compression service (verify if implemented)
- ❓ Relevance scoring algorithm (verify if implemented)

### Feature 111.2 Token Chart Dependencies
- ✅ Cost tracking already exists in backend
- ❓ Token usage history storage (verify if persisted)
- 📝 New timeseries endpoint needed

---

## Technical Notes

### Recharts Integration (Feature 111.2)

**Package:** Already available in package.json (verify, else install)

```bash
# If not installed
npm install recharts
```

**Component Example:**
```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

<ResponsiveContainer width="100%" height={300}>
  <LineChart data={tokenData}>
    <XAxis dataKey="date" />
    <YAxis scale={isLogScale ? 'log' : 'linear'} domain={['auto', 'auto']} />
    <Tooltip />
    <Legend />
    <Line type="monotone" dataKey="tokens" stroke="#8884d8" />
  </LineChart>
</ResponsiveContainer>
```

### Time Range Slider Implementation

**Options:**
1. **rc-slider** - Lightweight, customizable
2. **@mui/material Slider** - If MUI already in project
3. **Custom implementation** - HTML5 range input + styling

**Preset Buttons:**
```typescript
const presets = [
  { label: '1d', days: 1 },
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
  { label: '1y', days: 365 },
  { label: '3y', days: 1095 },
];
```

---

## Success Criteria

### Minimum Viable (Must Have)
- ✅ Group 09: Long Context - 10/10 tests (100%)
- ✅ Token Usage Chart with slider - 8/8 tests (100%)
- ✅ Backend timeseries endpoint working

### Stretch Goals (Nice to Have)
- ✅ Chart export as PNG/SVG
- ✅ Multiple chart types (line, bar, area)
- ✅ Real-time update (WebSocket)

---

## Known Risks

1. **Token History Data Availability**
   - **Risk:** Historical token data may not be persisted
   - **Mitigation:** Add migration to backfill from logs, or start fresh

2. **Large Dataset Performance**
   - **Risk:** 3 years of daily data = 1,095 points
   - **Mitigation:** Use aggregation (weekly/monthly for longer ranges)

3. **Recharts Bundle Size**
   - **Risk:** Recharts adds ~50KB to bundle
   - **Mitigation:** Lazy load the component

---

## Deferred from Previous Sprints

### Group 06: Skills Using Tools (9 tests, 2 SP)
**Reason:** Requires chat interface integration
**Status:** ⏸️ Deferred to Sprint 112 or later
**Dependencies:** Chat UI refactoring

---

## Next Immediate Actions (Sprint 111 Kickoff)

**Pre-Sprint:**
1. 📝 Verify backend APIs exist for Long Context features
2. 📝 Check if token usage history is persisted
3. 📝 Verify Recharts is in package.json

**Sprint Start:**
1. 📝 Create `LongContextViewer.tsx` component
2. 📝 Implement `ContextWindowIndicator.tsx` (progress gauge)
3. 📝 Build `ChunkExplorer.tsx` (virtual scroll list)
4. 📝 Create `TokenUsageChart.tsx` with Recharts
5. 📝 Build `TimeRangeSlider.tsx` (1d-3y slider)
6. 📝 Add `GET /api/v1/admin/costs/timeseries` endpoint
7. 📝 Write E2E tests for both features

---

**Last Updated:** 2026-01-17 (Sprint 111 PLANNED)
**Previous Sprint:** Sprint 110 (In Progress)
**Next Review:** After Sprint 110 completion
