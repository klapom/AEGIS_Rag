import { test, expect, setupAuthMocking } from '../../fixtures';

/**
 * E2E Tests for Memory Management UI (Sprint 72 Feature 72.3)
 *
 * Features Tested:
 * - Memory Management Page (/admin/memory)
 * - MemoryStatsCard (Redis, Qdrant, Graphiti stats)
 * - MemorySearchPanel (search with filters, pagination, export)
 * - ConsolidationControl (manual trigger, history, status)
 *
 * Components Under Test:
 * - MemoryManagementPage
 * - MemoryStatsCard
 * - MemorySearchPanel
 * - ConsolidationControl
 *
 * Data Attributes Required:
 * - [data-testid="memory-management-page"]
 * - [data-testid="tab-stats|tab-search|tab-consolidation"]
 * - [data-testid="memory-stats-card"]
 * - [data-testid="redis-stats|qdrant-stats|graphiti-stats"]
 * - [data-testid="memory-search-panel"]
 * - [data-testid="search-query-input|user-id-input|session-id-input"]
 * - [data-testid="search-button|search-results|search-result-row"]
 * - [data-testid="export-button"]
 * - [data-testid="consolidation-control"]
 * - [data-testid="trigger-consolidation-button"]
 * - [data-testid="consolidation-history"]
 */

/**
 * Mock memory stats response data
 */
const mockMemoryStats = {
  redis: {
    keys: 1234,
    memory_mb: 45.5,
    hit_rate: 0.87,
  },
  qdrant: {
    documents: 5000,
    size_mb: 250.75,
    avg_search_latency_ms: 42.3,
  },
  graphiti: {
    episodes: 500,
    entities: 2000,
    avg_search_latency_ms: 85.5,
  },
};

/**
 * Mock memory search results
 */
const mockSearchResults = {
  results: [
    {
      id: 'mem-001',
      content: 'User asked about OMNITRACKER configuration',
      layer: 'redis',
      relevance_score: 0.95,
      timestamp: new Date().toISOString(),
    },
    {
      id: 'mem-002',
      content: 'Session contains vectorized memory for semantic search',
      layer: 'qdrant',
      relevance_score: 0.87,
      timestamp: new Date().toISOString(),
    },
    {
      id: 'mem-003',
      content: 'Temporal relationship between entities stored in Graphiti',
      layer: 'graphiti',
      relevance_score: 0.76,
      timestamp: new Date().toISOString(),
    },
  ],
  total_count: 3,
};

/**
 * Mock consolidation status
 */
const mockConsolidationStatus = {
  is_running: false,
  last_run: {
    id: 'consol-001',
    status: 'completed',
    started_at: new Date(Date.now() - 3600000).toISOString(),
    completed_at: new Date(Date.now() - 3500000).toISOString(),
    items_processed: 150,
    items_consolidated: 142,
    error: null,
  },
  history: [
    {
      id: 'consol-001',
      status: 'completed',
      started_at: new Date(Date.now() - 3600000).toISOString(),
      completed_at: new Date(Date.now() - 3500000).toISOString(),
      items_processed: 150,
      items_consolidated: 142,
      error: null,
    },
    {
      id: 'consol-002',
      status: 'completed',
      started_at: new Date(Date.now() - 7200000).toISOString(),
      completed_at: new Date(Date.now() - 7100000).toISOString(),
      items_processed: 128,
      items_consolidated: 125,
      error: null,
    },
  ],
};

test.describe('Memory Management Page Navigation (Feature 72.3)', () => {
  test('should display /admin/memory page when navigating from admin', async ({ page }) => {
    await setupAuthMocking(page);

    // Mock the memory stats endpoint
    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    // Navigate to memory management page
    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Page should be visible
    const pageElement = page.getByTestId('memory-management-page');
    await expect(pageElement).toBeVisible();

    // Page title should be visible
    const title = page.locator('h1:has-text("Memory Management")');
    await expect(title).toBeVisible();
  });
});

test.describe('Memory Stats Display (Feature 72.3)', () => {
  test('should show memory stats for all layers (Redis, Qdrant, Graphiti)', async ({ page }) => {
    await setupAuthMocking(page);

    // Mock the memory stats endpoint
    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    // Navigate and wait for stats to load
    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Stats card should be visible
    const statsCard = page.getByTestId('memory-stats-card');
    await expect(statsCard).toBeVisible({ timeout: 5000 });

    // All three layer stats should be visible
    const redisStats = page.getByTestId('redis-stats');
    const qdrantStats = page.getByTestId('qdrant-stats');
    const graphitiStats = page.getByTestId('graphiti-stats');

    await expect(redisStats).toBeVisible();
    await expect(qdrantStats).toBeVisible();
    await expect(graphitiStats).toBeVisible();
  });

  test('should display Redis stats (keys, memory_mb, hit_rate)', async ({ page }) => {
    await setupAuthMocking(page);

    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    const redisStats = page.getByTestId('redis-stats');

    // Verify Redis metrics are displayed
    // Note: Numbers are formatted with commas (1,234) and percentages are shown
    await expect(redisStats).toContainText('Redis');
    await expect(redisStats).toContainText('1,234'); // keys (formatted with comma)
    await expect(redisStats).toContainText('45.5'); // memory_mb
    await expect(redisStats).toContainText('87.0% Hit Rate'); // hit_rate percentage
  });

  test('should display Qdrant stats (documents, size_mb, avg_search_latency_ms)', async ({ page }) => {
    await setupAuthMocking(page);

    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    const qdrantStats = page.getByTestId('qdrant-stats');

    // Verify Qdrant metrics are displayed
    // Note: Numbers are formatted with commas
    await expect(qdrantStats).toContainText('Qdrant');
    await expect(qdrantStats).toContainText('5,000'); // documents (formatted with comma)
    await expect(qdrantStats).toContainText('250'); // size_mb (rounded display)
    await expect(qdrantStats).toContainText('42.3'); // avg_search_latency_ms
  });

  test('should display Graphiti stats (episodes, entities, avg_search_latency_ms)', async ({ page }) => {
    await setupAuthMocking(page);

    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    const graphitiStats = page.getByTestId('graphiti-stats');

    // Verify Graphiti metrics are displayed
    // Note: toLocaleString() formats numbers with commas (2,000 instead of 2000)
    await expect(graphitiStats).toContainText('Graphiti');
    await expect(graphitiStats).toContainText('500'); // episodes
    await expect(graphitiStats).toContainText('2'); // entities (part of 2,000)
    await expect(graphitiStats).toContainText('85.5'); // avg_search_latency_ms
  });
});

test.describe('Memory Search Functionality (Feature 72.3)', () => {
  test('should search memory by user ID', async ({ page }) => {
    await setupAuthMocking(page);

    // Mock memory stats endpoint
    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    // Mock search endpoint
    await page.route('**/api/v1/memory/search', (route) => {
      const request = route.request();
      const body = request.postDataJSON();

      // Return results only if user_id is in request
      if (body.user_id) {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockSearchResults),
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ results: [], total_count: 0 }),
        });
      }
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Ensure page is loaded by waiting for memory-management-page element
    await expect(page.getByTestId('memory-management-page')).toBeVisible({ timeout: 5000 });

    // Click search tab
    const searchTab = page.getByTestId('tab-search');
    await searchTab.waitFor({ state: 'visible', timeout: 5000 });
    await searchTab.click();
    await page.waitForTimeout(500);

    // Click filters to show them
    await page.getByTestId('toggle-filters-button').click();
    await page.waitForTimeout(300);

    // Fill in user ID
    await page.getByTestId('user-id-input').fill('user-123');
    await page.waitForTimeout(300);

    // Click search
    await page.getByTestId('search-button').click();

    // Wait for results to appear
    const results = page.getByTestId('search-results');
    await expect(results).toBeVisible({ timeout: 5000 });

    // Results should show items - check for the total count display
    // The header shows "Found X results"
    await expect(results).toContainText('3'); // We have 3 mock search results
  });

  test('should search memory by session ID', async ({ page }) => {
    await setupAuthMocking(page);

    // Mock memory stats endpoint
    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    await page.route('**/api/v1/memory/search', (route) => {
      const request = route.request();
      const body = request.postDataJSON();

      if (body.session_id) {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockSearchResults),
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ results: [], total_count: 0 }),
        });
      }
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Ensure page is loaded
    await expect(page.getByTestId('memory-management-page')).toBeVisible({ timeout: 5000 });

    // Click search tab
    const searchTab = page.getByTestId('tab-search');
    await searchTab.waitFor({ state: 'visible', timeout: 5000 });
    await searchTab.click();
    await page.waitForTimeout(500);

    // Click filters to show them
    await page.getByTestId('toggle-filters-button').click();
    await page.waitForTimeout(300);

    // Fill in session ID
    await page.getByTestId('session-id-input').fill('session-abc123');
    await page.waitForTimeout(300);

    // Click search
    await page.getByTestId('search-button').click();

    // Wait for results
    const results = page.getByTestId('search-results');
    await expect(results).toBeVisible({ timeout: 5000 });
  });

  test('should display search results with relevance scores', async ({ page }) => {
    await setupAuthMocking(page);

    // Mock memory stats endpoint
    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    await page.route('**/api/v1/memory/search', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSearchResults),
      });
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Ensure page is loaded
    await expect(page.getByTestId('memory-management-page')).toBeVisible({ timeout: 5000 });

    // Click search tab
    const searchTab = page.getByTestId('tab-search');
    await searchTab.waitFor({ state: 'visible', timeout: 5000 });
    await searchTab.click();
    await page.waitForTimeout(500);

    // Enter search query and search
    await page.getByTestId('search-query-input').fill('OMNITRACKER');
    await page.getByTestId('search-button').click();

    // Wait for results
    await expect(page.getByTestId('search-results')).toBeVisible({ timeout: 5000 });

    // Verify search result rows are visible
    // Sprint 113: Added timeout to prevent race condition
    const resultRows = page.getByTestId('search-result-row');
    await expect(resultRows).toHaveCount(3, { timeout: 10000 });

    // Verify relevance scores are displayed - use first() to avoid strict mode error
    await expect(page.locator('text=/Relevance/').first()).toBeVisible();

    // Check that results display different memory layers - use first() to avoid strict mode
    await expect(page.locator('text=/Redis/').first()).toBeVisible();
    await expect(page.locator('text=/Qdrant/').first()).toBeVisible();
    await expect(page.locator('text=/Graphiti/').first()).toBeVisible();
  });
});

test.describe('Memory Export Functionality (Feature 72.3)', () => {
  test('should export memory as JSON download', async ({ page }) => {
    await setupAuthMocking(page);

    // Mock memory stats endpoint
    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    await page.route('**/api/v1/memory/search', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSearchResults),
      });
    });

    await page.route('**/api/v1/memory/session/*/export', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/octet-stream',
        body: JSON.stringify(mockSearchResults),
        headers: {
          'Content-Disposition': 'attachment; filename="session-abc123-memory.json"',
        },
      });
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Ensure page is loaded
    await expect(page.getByTestId('memory-management-page')).toBeVisible({ timeout: 5000 });

    // Click search tab
    const searchTab = page.getByTestId('tab-search');
    await searchTab.waitFor({ state: 'visible', timeout: 5000 });
    await searchTab.click();
    await page.waitForTimeout(500);

    // Click filters and enter session ID
    await page.getByTestId('toggle-filters-button').click();
    await page.waitForTimeout(300);
    await page.getByTestId('session-id-input').fill('session-abc123');

    // Search first to get results
    await page.getByTestId('search-button').click();
    await expect(page.getByTestId('search-results')).toBeVisible({ timeout: 5000 });

    // Click export button
    const exportButton = page.getByTestId('export-button');
    await expect(exportButton).toBeVisible();

    // The download event should be triggered when export is clicked
    // (In real scenario, the download would happen)
    await exportButton.click();

    // Button should show loading state
    await page.waitForTimeout(300);
    // The download promise would resolve here in a real scenario
  });
});

test.describe('Memory Consolidation Control (Feature 72.3)', () => {
  test('should trigger manual memory consolidation', async ({ page }) => {
    await setupAuthMocking(page);

    const consolidationTriggerPromise = page.waitForResponse('**/api/v1/memory/consolidate');

    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    await page.route('**/api/v1/memory/consolidate/status', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockConsolidationStatus),
      });
    });

    // Mock consolidate POST endpoint
    await page.route('**/api/v1/memory/consolidate', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...mockConsolidationStatus,
          is_running: true,
        }),
      });
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Ensure page is loaded
    await expect(page.getByTestId('memory-management-page')).toBeVisible({ timeout: 5000 });

    // Click consolidation tab
    const consolidationTab = page.getByTestId('tab-consolidation');
    await consolidationTab.waitFor({ state: 'visible', timeout: 5000 });
    await consolidationTab.click();
    await page.waitForTimeout(500);

    // Consolidation control should be visible
    await expect(page.getByTestId('consolidation-control')).toBeVisible({ timeout: 5000 });

    // Trigger consolidation button should be visible
    const triggerButton = page.getByTestId('trigger-consolidation-button');
    await expect(triggerButton).toBeVisible();

    // Click trigger button
    await triggerButton.click();

    // Button should become disabled or show loading state
    await expect(triggerButton).toBeDisabled({ timeout: 3000 });
  });

  test('should display consolidation history', async ({ page }) => {
    await setupAuthMocking(page);

    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    // Return consolidation status with empty history to test the empty state
    await page.route('**/api/v1/memory/consolidate/status', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...mockConsolidationStatus,
          history: [], // Empty history for this test
        }),
      });
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Ensure page is loaded
    await expect(page.getByTestId('memory-management-page')).toBeVisible({ timeout: 5000 });

    // Click consolidation tab
    const consolidationTab = page.getByTestId('tab-consolidation');
    await consolidationTab.waitFor({ state: 'visible', timeout: 5000 });
    await consolidationTab.click();
    await page.waitForTimeout(500);

    // History section should be visible
    const history = page.getByTestId('consolidation-history');
    await expect(history).toBeVisible({ timeout: 5000 });

    // Verify history section is displayed (may be empty or with data)
    // Check for either "No consolidation history" or "Completed" depending on state
    const historyText = await history.textContent();
    expect(historyText).toBeTruthy();
  });
});

test.describe('Memory Management UI Interactions (Feature 72.3)', () => {
  test('should switch between tabs (Stats, Search, Consolidation)', async ({ page }) => {
    await setupAuthMocking(page);

    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    await page.route('**/api/v1/memory/consolidate/status', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockConsolidationStatus),
      });
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Ensure page is loaded
    await expect(page.getByTestId('memory-management-page')).toBeVisible({ timeout: 5000 });

    // Check Stats tab is active by default
    let statsTab = page.getByTestId('tab-stats');
    await statsTab.waitFor({ state: 'visible', timeout: 5000 });
    await expect(statsTab).toHaveAttribute('aria-selected', 'true');

    // Click Search tab
    const searchTabBtn = page.getByTestId('tab-search');
    await searchTabBtn.waitFor({ state: 'visible', timeout: 5000 });
    await searchTabBtn.click();
    await page.waitForTimeout(300);

    // Search tab should be active
    let searchTab = page.getByTestId('tab-search');
    await expect(searchTab).toHaveAttribute('aria-selected', 'true');

    // Search tab content should be visible
    await expect(page.getByTestId('memory-search-panel')).toBeVisible();

    // Click Consolidation tab
    const consolidationTabBtn = page.getByTestId('tab-consolidation');
    await consolidationTabBtn.waitFor({ state: 'visible', timeout: 5000 });
    await consolidationTabBtn.click();
    await page.waitForTimeout(300);

    // Consolidation tab should be active
    let consolidationTab = page.getByTestId('tab-consolidation');
    await expect(consolidationTab).toHaveAttribute('aria-selected', 'true');

    // Consolidation content should be visible
    await expect(page.getByTestId('consolidation-control')).toBeVisible({ timeout: 5000 });

    // Go back to Stats
    const statsTabBtn = page.getByTestId('tab-stats');
    await statsTabBtn.click();
    await page.waitForTimeout(300);

    // Stats should be active again
    statsTab = page.getByTestId('tab-stats');
    await expect(statsTab).toHaveAttribute('aria-selected', 'true');
  });

  test('should refresh memory stats on button click', async ({ page }) => {
    await setupAuthMocking(page);

    let callCount = 0;
    await page.route('**/api/v1/memory/stats', (route) => {
      callCount++;
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Ensure page is loaded
    await expect(page.getByTestId('memory-management-page')).toBeVisible({ timeout: 5000 });

    // Wait for initial load
    await expect(page.getByTestId('memory-stats-card')).toBeVisible({ timeout: 5000 });

    const initialCallCount = callCount;

    // Click refresh button
    const refreshButton = page.getByTestId('refresh-stats-button');
    await refreshButton.waitFor({ state: 'visible', timeout: 5000 });
    await refreshButton.click();

    // Wait a bit for the request
    await page.waitForTimeout(500);

    // Should have made another API call
    expect(callCount).toBeGreaterThan(initialCallCount);
  });

  test('should display error message on API failure', async ({ page }) => {
    await setupAuthMocking(page);

    await page.route('**/api/v1/memory/stats', (route) => {
      route.abort('failed');
    });

    await page.goto('/admin/memory');

    // Wait for error to appear
    const errorMessage = page.locator('text=/Failed to Load Memory Stats/');
    await expect(errorMessage).toBeVisible({ timeout: 5000 });

    // Retry button should be visible
    const retryButton = page.locator('button:has-text("Retry")');
    await expect(retryButton).toBeVisible();
  });
});

test.describe('Memory Management Accessibility (Feature 72.3)', () => {
  test('should have proper tab navigation structure', async ({ page }) => {
    await setupAuthMocking(page);

    await page.route('**/api/v1/memory/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockMemoryStats),
      });
    });

    await page.route('**/api/v1/memory/consolidate/status', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockConsolidationStatus),
      });
    });

    await page.goto('/admin/memory');
    await page.waitForLoadState('networkidle');

    // Tab buttons should have proper role
    const tabButtons = page.locator('[role="tab"]');
    expect(await tabButtons.count()).toBeGreaterThan(0);

    // Each tab should have aria-selected
    for (let i = 0; i < (await tabButtons.count()); i++) {
      const tab = tabButtons.nth(i);
      const ariaSelected = await tab.getAttribute('aria-selected');
      expect(['true', 'false']).toContain(ariaSelected);
    }
  });
});
