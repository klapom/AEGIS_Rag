# Sprint 118 Plan: Testing Infrastructure & Quality Assurance

**Date:** 2026-01-20
**Status:** Planning
**Total Story Points:** 23 SP
**Predecessor:** Sprint 116 (UI Features), Sprint 117 (Domain Training)
**Successor:** Sprint 119+ (Versioning/TimeTravel - Technical Debt)

---

## Executive Summary

Sprint 118 focuses on **testing infrastructure** and **quality assurance** for comprehensive E2E test coverage. This sprint complements the feature implementation in Sprint 116 (UI features) and Sprint 117 (domain training) by ensuring:

1. **Visual Regression Framework** - Baseline infrastructure for preventing accidental UI regressions
2. **Performance Regression Tests** - Automated measurement of latency and throughput metrics
3. **Remaining infrastructure features** - Graph communities UI, remaining UI enhancements

These are foundational capabilities needed for reliable test-driven development across all subsequent sprints.

**Dependencies:** Requires Sprint 116 completion (UI features + error handling)

---

## Feature Breakdown

### Primary Objectives (18 SP)

| Feature | Category | SP | Dependencies | Priority |
|---------|----------|----|--------------:|----------|
| Visual Regression Framework | Infrastructure | 5 | Sprint 115+ | CRITICAL |
| Performance Regression Tests | Infrastructure | 13 | Sprint 115+ | CRITICAL |

### Secondary Objectives (5 SP)

| Feature | Category | SP | Dependencies | Priority |
|---------|----------|----|--------------:|----------|
| Graph Communities UI | Frontend | 5 | Sprint 116 | HIGH |

---

## Feature Specifications

### 1. Visual Regression Framework (5 SP)

**Purpose:** Automated visual regression detection using baseline snapshots

**Scope:**
- Playwright visual comparison infrastructure
- Baseline snapshot storage and versioning
- Diff generation and reporting
- Integration with E2E test suite

**Implementation Details:**

```typescript
// Baseline configuration (playwright.config.ts)
{
  webServer: {
    command: 'npm run dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
  },
  snapshotDir: 'frontend/e2e/snapshots',
  snapshotPathTemplate: '{snapshotDir}/{testFileDir}/{testFileName}-{platform}{ext}',
  updateSnapshots: process.env.UPDATE_SNAPSHOTS === 'true',
  expectMatch: {
    maxDiffPixels: 100,
    threshold: 0.2, // 20% variance allowed
  },
}
```

**Test Pattern:**

```typescript
// frontend/e2e/visual-regression.spec.ts
describe('Visual Regression - Chat Interface', () => {
  test('chat message display', async ({ page }) => {
    await page.goto('/chat');
    await page.fill('[data-testid="chat-input"]', 'Test message');
    await page.click('[data-testid="send-button"]');

    // Wait for response rendering
    await page.waitForSelector('[data-testid="chat-message"]');

    // Capture and compare snapshot
    await expect(page.locator('[data-testid="chat-container"]'))
      .toHaveScreenshot('chat-with-message.png');
  });

  test('search results layout', async ({ page }) => {
    await page.goto('/search?q=test');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[data-testid="search-results"]'))
      .toHaveScreenshot('search-results.png');
  });

  test('error state display', async ({ page }) => {
    await page.goto('/chat');
    await mockAPI('GET', '/api/v1/health', { status: 500 });

    await expect(page.locator('[data-testid="error-boundary"]'))
      .toHaveScreenshot('error-state.png');
  });
});
```

**Backend Requirements:**
- None (purely frontend infrastructure)

**Frontend Requirements:**
- Visual regression testing infrastructure
- Snapshot storage (`frontend/e2e/snapshots/`)
- Baseline comparison logic
- GitHub Actions workflow for snapshot updates

**Testing Strategy:**
1. Manual snapshot creation on main branch
2. CI/CD validation on all PRs (fail if visual regression detected)
3. Optional snapshot update with `UPDATE_SNAPSHOTS=true` flag
4. Review process for intentional visual changes

**Deliverables:**
- Visual regression test suite (10+ tests covering critical UI paths)
- Baseline snapshots for:
  - Chat interface (input, messages, error states)
  - Search results (vector, graph, hybrid modes)
  - Graph visualization (node layout, edges, communities)
  - Admin dashboard (stats cards, domain list)
  - Memory panel (memory visualization, stats)
- Documentation: `docs/e2e/VISUAL_REGRESSION.md`

---

### 2. Performance Regression Tests (13 SP)

**Purpose:** Automated measurement of API latency, throughput, and resource utilization

**Scope:**
- HAR (HTTP Archive) capture infrastructure
- Latency tracking (p50, p95, p99)
- Throughput measurement (queries/second)
- Resource utilization (GPU VRAM, CPU %)
- Baseline comparison and regression detection

**Implementation Details:**

```typescript
// frontend/e2e/performance-regression.spec.ts
describe('Performance Regression - Latency Baselines', () => {
  const perfMetrics = {
    vectorSearch: { p95: 200, p99: 350 }, // ms
    graphSearch: { p95: 500, p99: 1000 }, // ms
    hybridSearch: { p95: 300, p99: 600 }, // ms
    chatResponse: { p95: 2000, p99: 5000 }, // ms
  };

  test('vector search latency', async ({ page }, testInfo) => {
    const har = await page.context().recordHAR({ path: 'har/vector-search.har' });

    // Execute search
    const startTime = Date.now();
    await page.goto('/search?q=test&mode=vector');
    await page.waitForSelector('[data-testid="search-results"]');
    const latency = Date.now() - startTime;

    // Validate against baseline
    expect(latency).toBeLessThan(perfMetrics.vectorSearch.p95);

    // Extract network timings
    const harData = JSON.parse(await har.path());
    const apiCall = harData.log.entries.find(e =>
      e.request.url.includes('/api/v1/retrieval/search')
    );

    testInfo.attach('network-timings', {
      body: JSON.stringify({
        apiLatency: apiCall.time,
        totalLatency: latency,
        timestamp: new Date().toISOString(),
      }),
      contentType: 'application/json',
    });
  });

  test('graph search latency', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/search?q=test&mode=graph');
    await page.waitForSelector('[data-testid="graph-results"]');
    const latency = Date.now() - startTime;

    expect(latency).toBeLessThan(perfMetrics.graphSearch.p95);
  });

  test('hybrid search latency', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/search?q=test&mode=hybrid');
    await page.waitForSelector('[data-testid="hybrid-results"]');
    const latency = Date.now() - startTime;

    expect(latency).toBeLessThan(perfMetrics.hybridSearch.p95);
  });

  test('chat response latency', async ({ page }) => {
    await page.goto('/chat');
    await page.fill('[data-testid="chat-input"]', 'What is hybrid search?');

    const startTime = Date.now();
    await page.click('[data-testid="send-button"]');
    await page.waitForSelector('[data-testid="chat-response"]', { timeout: 10000 });
    const latency = Date.now() - startTime;

    expect(latency).toBeLessThan(perfMetrics.chatResponse.p95);
  });
});

describe('Performance Regression - Throughput', () => {
  test('sustained load: 10 sequential searches', async ({ page }) => {
    const latencies = [];

    for (let i = 0; i < 10; i++) {
      const startTime = Date.now();
      await page.goto(`/search?q=query${i}&mode=hybrid`);
      await page.waitForSelector('[data-testid="search-results"]', { timeout: 5000 });
      latencies.push(Date.now() - startTime);
    }

    const p95 = calculatePercentile(latencies, 0.95);
    const p99 = calculatePercentile(latencies, 0.99);

    expect(p95).toBeLessThan(400); // Allows for slight variance
    expect(p99).toBeLessThan(700);
  });

  test('parallel queries: 5 concurrent tabs', async ({ browser }) => {
    const contexts = await Promise.all([...Array(5)].map(() => browser.newContext()));
    const pages = await Promise.all(contexts.map(ctx => ctx.newPage()));

    const startTime = Date.now();
    await Promise.all(pages.map((p, i) =>
      p.goto(`/search?q=query${i}&mode=hybrid`)
    ));
    await Promise.all(pages.map(p =>
      p.waitForSelector('[data-testid="search-results"]')
    ));
    const totalTime = Date.now() - startTime;

    // Should not degrade significantly with parallelism
    expect(totalTime).toBeLessThan(800); // ~160ms/query average
  });
});

describe('Performance Regression - Resource Utilization', () => {
  test('GPU VRAM during search', async ({ page }) => {
    // Query backend metrics endpoint
    const metricsResponse = await page.request.get('/api/v1/admin/metrics/gpu');
    const { vram_used, vram_total } = await metricsResponse.json();

    const utilizationPercent = (vram_used / vram_total) * 100;

    // Should not exceed 85% utilization
    expect(utilizationPercent).toBeLessThan(85);
  });

  test('CPU during concurrent queries', async ({ page }) => {
    const metricsResponse = await page.request.get('/api/v1/admin/metrics/cpu');
    const { cpu_percent } = await metricsResponse.json();

    expect(cpu_percent).toBeLessThan(90);
  });
});
```

**Backend Requirements:**

1. **Metrics Endpoints:**
```python
# POST /api/v1/admin/metrics/collect
{
  "metrics": {
    "api_latencies": [145.2, 156.3, 201.5],  # ms per request
    "gpu_vram_mb": 8192,
    "gpu_util_percent": 78.5,
    "cpu_percent": 45.2,
    "memory_mb": 4096,
    "timestamp": "2026-01-20T15:30:00Z"
  }
}

# GET /api/v1/admin/metrics/gpu
{
  "vram_used": 8192,
  "vram_total": 24576,
  "utilization_percent": 78.5,
  "model": "NVIDIA GB10"
}

# GET /api/v1/admin/metrics/cpu
{
  "cpu_percent": 45.2,
  "memory_mb": 4096
}
```

2. **Instrumentation in API responses:**
   - Add `X-Response-Time` header to all API endpoints
   - Track embeddings latency (Dense + Sparse)
   - Track reranker latency
   - Track LLM inference latency

3. **Baseline metrics collection:**
   - Export baseline metrics to JSON file
   - Store in `docs/performance/baselines/`
   - Update after each major optimization

**Frontend Requirements:**
- HAR recording infrastructure (Playwright built-in)
- Performance metrics collection from browser DevTools
- Network timing extraction from HAR files
- Baseline comparison logic

**Testing Strategy:**

1. **Establish Baselines (Week 1):**
   - Run performance tests 5 times on main branch
   - Calculate p50, p95, p99 percentiles
   - Store baselines in `docs/performance/baselines/current.json`

2. **Regression Detection (Ongoing):**
   - CI/CD runs performance tests on all PRs
   - Fail if p95 exceeds baseline by >10%
   - Allow opt-in variance for known optimizations

3. **Performance Reports (Weekly):**
   - Generate HTML report with graphs
   - Track performance trends over time
   - Identify regression points

**Deliverables:**
- Performance regression test suite (8+ tests covering all search modes + chat)
- HAR recording infrastructure
- Metrics collection endpoints
- Baseline metrics file
- Performance report generator
- Documentation: `docs/performance/PERFORMANCE_TESTING.md`

---

### 3. Graph Communities UI (5 SP)

**Purpose:** Frontend component for displaying graph community detection results

**Scope:**
- Communities list view with cards
- Community details modal
- Community member visualization
- Integration with existing graph search

**Implementation Details:**

```typescript
// Frontend component structure
components/
├── GraphCommunities/
│   ├── CommunitiesList.tsx          # List view with pagination
│   ├── CommunityCard.tsx             # Individual community card
│   ├── CommunityDetailsModal.tsx     # Modal with details/members
│   └── CommunityVisualization.tsx    # Graph visualization of community
```

**Test Coverage:**
- Communities list loads from API
- Cards display community metadata (size, density, summary)
- Modal opens/closes on click
- Member list pagination works
- Graph visualization renders

**Backend Dependencies:**
- Existing graph community detection API (already implemented in Sprint 92)
- No new backend endpoints required

**Testing Strategy:**
- Playwright E2E tests for UI interactions
- Component snapshot tests
- Integration tests with graph search API

**Deliverables:**
- CommunitiesList component
- CommunityCard component
- CommunityDetailsModal component
- CommunityVisualization component
- 5+ Playwright E2E tests
- Storybook stories for each component

---

## Implementation Approach

### Phase 1: Visual Regression Framework (Week 1, 5 SP)

**Tasks:**
1. Configure Playwright visual regression settings
2. Create visual-regression.spec.ts with baseline tests
3. Generate initial snapshots
4. Add baseline snapshots to Git
5. Document visual regression workflow
6. Create GitHub Actions workflow for snapshot validation

**Acceptance Criteria:**
- All critical UI paths have baseline snapshots
- CI/CD detects visual regressions on PRs
- Snapshot update process documented

### Phase 2: Performance Regression Tests (Week 1-2, 13 SP)

**Tasks:**
1. Design metrics collection architecture
2. Implement backend metrics endpoints (3 SP)
3. Add API instrumentation (response headers, timing data) (3 SP)
4. Create performance test suite (4 SP)
5. Implement baseline collection script (2 SP)
6. Add performance report generator (1 SP)

**Acceptance Criteria:**
- All performance tests pass with <5% variance
- Baselines established and documented
- CI/CD runs performance tests on all PRs
- Performance regression detection working

### Phase 3: Graph Communities UI (Week 2, 5 SP)

**Tasks:**
1. Implement CommunitiesList component (2 SP)
2. Implement CommunityDetailsModal (2 SP)
3. Add 5+ Playwright tests (1 SP)

**Acceptance Criteria:**
- All E2E tests passing
- Visual snapshots captured
- Component integrated with graph search

---

## Dependencies

### Upstream (Must Complete Before Sprint 118)

**Sprint 115/116 Requirements:**
- Chat interface stable
- Search results UI complete
- Graph visualization working
- Error boundary components

**Sprint 117 Requirements:**
- Domain training UI (if needed for performance tests)

### Downstream (Sprint 119+)

**Sprint 119 Implications:**
- Performance tests will baseline all subsequent features
- Visual regressions will block feature merges
- Provides metrics for optimization work

---

## Testing Strategy

### Test Coverage Goals

| Category | Target | Notes |
|----------|--------|-------|
| Visual Regression Tests | 15+ | Critical UI paths |
| Performance Tests | 8+ | Latency + throughput |
| Graph Communities Tests | 5+ | UI interactions |
| **Total Tests** | **28+** | Combined coverage |

### Performance Acceptance Criteria

| Metric | Target | Upper Bound |
|--------|--------|------------|
| Vector Search P95 | <200ms | 250ms |
| Graph Search P95 | <500ms | 550ms |
| Hybrid Search P95 | <300ms | 350ms |
| Chat Response P95 | <2000ms | 2500ms |
| Sustained Load (10x) | <400ms p95 | 500ms |
| GPU Utilization | <85% | 90% |

### Failure Handling

1. **Visual Regression Detected:**
   - CI/CD fails with link to visual diff
   - Developer reviews and accepts/rejects changes
   - Can opt-out with `SKIP_VISUAL_REGRESSION=true`

2. **Performance Regression Detected:**
   - CI/CD fails with performance report
   - Requires justification or performance fix
   - Can opt-out with `SKIP_PERF_REGRESSION=true` (rare)

3. **Test Timeout:**
   - Increase timeout to 30s and retry once
   - If still fails, investigate infrastructure

---

## Success Metrics

### Definition of Done

- [ ] All visual regression tests passing
- [ ] All performance tests passing with <5% variance
- [ ] Performance baselines established and documented
- [ ] Graph Communities UI functional and tested
- [ ] CI/CD integration working
- [ ] Documentation complete
- [ ] No regression in existing test pass rate

### Deliverables Checklist

**Visual Regression:**
- [ ] `frontend/e2e/visual-regression.spec.ts` (15+ tests)
- [ ] `frontend/e2e/snapshots/` directory with baseline images
- [ ] `playwright.config.ts` updated with snapshot config
- [ ] `.github/workflows/visual-regression.yml` workflow
- [ ] `docs/e2e/VISUAL_REGRESSION.md` documentation

**Performance Regression:**
- [ ] `frontend/e2e/performance-regression.spec.ts` (8+ tests)
- [ ] Backend metrics endpoints implemented
- [ ] API instrumentation added
- [ ] `docs/performance/baselines/current.json` baseline file
- [ ] `scripts/performance_report.py` report generator
- [ ] `.github/workflows/performance-regression.yml` workflow
- [ ] `docs/performance/PERFORMANCE_TESTING.md` documentation

**Graph Communities:**
- [ ] `src/components/GraphCommunities/*.tsx` (4 components)
- [ ] `frontend/e2e/group12-graph-communities.spec.ts` (5+ tests)
- [ ] Integration with graph search results
- [ ] Storybook stories

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Performance baseline unstable | MEDIUM | HIGH | Run 5 times, use p95 median |
| Visual regression too strict | MEDIUM | MEDIUM | Allow 20% threshold variance |
| GPU metrics API not available | LOW | MEDIUM | Mock API responses in tests |
| HAR files too large | LOW | MEDIUM | Compress and cleanup after tests |
| Communities UI unfinished | LOW | LOW | Deferrable to Sprint 119 |

---

## Rollback & Contingency

**If Visual Regression Fails:**
- Revert snapshot baseline changes
- Investigate UI regression
- Fix underlying issue before re-running

**If Performance Regression Fails:**
- Check if regression is expected (new feature)
- Profile with `py-spy` or `cProfile`
- Identify bottleneck and optimize
- Update baseline if necessary

**If Communities UI Incomplete:**
- Defer to Sprint 119 (lower priority)
- Focus on regression testing infrastructure

---

## Sprint Deliverables Summary

### Code Changes
- 3 new test files (visual, performance, communities)
- 4 new frontend components (communities UI)
- 3 new backend endpoints (metrics)
- 10+ API instrumentation points

### Documentation
- `docs/e2e/VISUAL_REGRESSION.md`
- `docs/performance/PERFORMANCE_TESTING.md`
- `docs/performance/baselines/current.json`
- Performance report examples
- Integration guide for Sprint 119+

### Test Infrastructure
- Playwright visual regression framework
- Performance metrics collection
- HAR recording and analysis
- GitHub Actions workflows
- Baseline comparison logic

---

## References

**Related Documentation:**
- [E2E Testing Guide](../e2e/PLAYWRIGHT_E2E.md)
- [Performance Tuning](../performance/PERFORMANCE_TESTING.md)
- [Sprint 116 Plan](SPRINT_116_PLAN.md)
- [Sprint 117 Plan](SPRINT_117_PLAN.md)

**External Resources:**
- [Playwright Visual Comparisons](https://playwright.dev/docs/test-snapshots)
- [HAR Format Specification](http://www.softwareishard.com/blog/har-12-spec/)
- [Web Performance APIs](https://developer.mozilla.org/en-US/docs/Web/API/Performance)
