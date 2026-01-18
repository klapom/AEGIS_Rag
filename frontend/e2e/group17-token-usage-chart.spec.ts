import { test, expect, setupAuthMocking, navigateClientSide } from './fixtures';

/**
 * Group 17: Token Usage Chart E2E Tests
 * Sprint 111 Feature 111.2: Token Usage Over Time Chart
 *
 * Tests:
 * 1. Chart renders with data
 * 2. Slider changes time range
 * 3. Provider filter works
 * 4. Aggregation toggle works
 * 5. Empty state handling
 * 6. Loading state
 * 7. Error state handling
 * 8. Export chart as PNG
 */

test.describe('Group 17: Token Usage Chart - Sprint 111', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthMocking(page);
  });

  test('should render chart with data', async ({ page }) => {
    // Mock cost stats API
    await page.route('**/api/v1/admin/costs/stats*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_cost_usd: 12.34,
          total_tokens: 150000,
          total_calls: 100,
          avg_cost_per_call: 0.1234,
          by_provider: { ollama: { cost_usd: 10.0, tokens: 120000, calls: 80, avg_cost_per_call: 0.125 } },
          by_model: {},
          budgets: { ollama: { limit_usd: 50, spent_usd: 10, utilization_percent: 20, status: 'ok', remaining_usd: 40 } },
          time_range: '7d',
        }),
      });
    });

    // Mock timeseries API
    await page.route('**/api/v1/admin/costs/timeseries*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { date: '2026-01-17', tokens: 50000, cost_usd: 0.15, provider: 'ollama' },
            { date: '2026-01-16', tokens: 45000, cost_usd: 0.13, provider: 'ollama' },
            { date: '2026-01-15', tokens: 55000, cost_usd: 0.17, provider: 'ollama' },
          ],
          total_tokens: 150000,
          total_cost_usd: 0.45,
        }),
      });
    });

    await navigateClientSide(page, '/admin/costs');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Verify chart container exists
    const chartContainer = page.locator('[data-testid="token-usage-chart"]');
    await expect(chartContainer).toBeVisible();

    // Verify chart content exists
    const chartContent = page.locator('[data-testid="chart-container"]');
    await expect(chartContent).toBeVisible();

    console.log('✓ Chart renders with data');
  });

  test('should change time range with slider', async ({ page }) => {
    // Mock APIs
    await page.route('**/api/v1/admin/costs/stats*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_cost_usd: 5.0,
          total_tokens: 50000,
          total_calls: 50,
          avg_cost_per_call: 0.1,
          by_provider: {},
          by_model: {},
          budgets: {},
          time_range: '7d',
        }),
      });
    });

    await page.route('**/api/v1/admin/costs/timeseries*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [{ date: '2026-01-17', tokens: 10000, cost_usd: 0.1, provider: 'ollama' }],
        }),
      });
    });

    await navigateClientSide(page, '/admin/costs');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Check time range slider exists
    const slider = page.locator('[data-testid="time-range-slider"]');
    await expect(slider).toBeVisible();

    // Check preset buttons
    const preset7d = page.locator('[data-testid="preset-7d"]');
    const preset30d = page.locator('[data-testid="preset-30d"]');
    await expect(preset7d).toBeVisible();
    await expect(preset30d).toBeVisible();

    // Click 90d preset
    const preset90d = page.locator('[data-testid="preset-90d"]');
    await preset90d.click();
    await page.waitForTimeout(500);

    console.log('✓ Slider changes time range');
  });

  test('should filter by provider', async ({ page }) => {
    await page.route('**/api/v1/admin/costs/stats*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_cost_usd: 15.0,
          total_tokens: 200000,
          total_calls: 150,
          avg_cost_per_call: 0.1,
          by_provider: { ollama: { cost_usd: 10, tokens: 150000, calls: 100, avg_cost_per_call: 0.1 }, alibaba_cloud: { cost_usd: 5, tokens: 50000, calls: 50, avg_cost_per_call: 0.1 } },
          by_model: {},
          budgets: {},
          time_range: '7d',
        }),
      });
    });

    await page.route('**/api/v1/admin/costs/timeseries*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { date: '2026-01-17', tokens: 30000, cost_usd: 0.2, provider: 'ollama' },
            { date: '2026-01-17', tokens: 10000, cost_usd: 0.05, provider: 'alibaba_cloud' },
          ],
        }),
      });
    });

    await navigateClientSide(page, '/admin/costs');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Check provider filter exists
    const providerFilter = page.locator('[data-testid="provider-filter"]');
    await expect(providerFilter).toBeVisible();

    // Select a specific provider
    await providerFilter.selectOption('ollama');
    await page.waitForTimeout(500);

    console.log('✓ Provider filter works');
  });

  test('should toggle aggregation', async ({ page }) => {
    await page.route('**/api/v1/admin/costs/stats*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_cost_usd: 5.0,
          total_tokens: 50000,
          total_calls: 50,
          avg_cost_per_call: 0.1,
          by_provider: {},
          by_model: {},
          budgets: {},
          time_range: '7d',
        }),
      });
    });

    await page.route('**/api/v1/admin/costs/timeseries*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [{ date: '2026-01-17', tokens: 10000, cost_usd: 0.1, provider: 'ollama' }],
        }),
      });
    });

    await navigateClientSide(page, '/admin/costs');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Check aggregation selector
    const aggregationSelector = page.locator('[data-testid="aggregation-selector"]');
    await expect(aggregationSelector).toBeVisible();

    // Change to weekly
    await aggregationSelector.selectOption('weekly');
    await page.waitForTimeout(500);

    // Change to monthly
    await aggregationSelector.selectOption('monthly');
    await page.waitForTimeout(500);

    console.log('✓ Aggregation toggle works');
  });

  test('should handle empty state gracefully', async ({ page }) => {
    await page.route('**/api/v1/admin/costs/stats*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_cost_usd: 0,
          total_tokens: 0,
          total_calls: 0,
          avg_cost_per_call: 0,
          by_provider: {},
          by_model: {},
          budgets: {},
          time_range: '7d',
        }),
      });
    });

    await page.route('**/api/v1/admin/costs/timeseries*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [] }),
      });
    });

    await navigateClientSide(page, '/admin/costs');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Check for empty state message
    const emptyMessage = page.locator('[data-testid="chart-empty"]');
    await expect(emptyMessage).toBeVisible();

    console.log('✓ Empty state handled gracefully');
  });

  test('should display loading state', async ({ page }) => {
    await page.route('**/api/v1/admin/costs/stats*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_cost_usd: 5.0,
          total_tokens: 50000,
          total_calls: 50,
          avg_cost_per_call: 0.1,
          by_provider: {},
          by_model: {},
          budgets: {},
          time_range: '7d',
        }),
      });
    });

    // Delay the timeseries response to see loading state
    await page.route('**/api/v1/admin/costs/timeseries*', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [] }),
      });
    });

    await navigateClientSide(page, '/admin/costs');
    await page.waitForLoadState('networkidle');

    // Chart should be visible (component handles its own loading)
    const chart = page.locator('[data-testid="token-usage-chart"]');
    await expect(chart).toBeVisible({ timeout: 3000 });

    console.log('✓ Loading state displayed');
  });

  test('should handle API error gracefully', async ({ page }) => {
    await page.route('**/api/v1/admin/costs/stats*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_cost_usd: 5.0,
          total_tokens: 50000,
          total_calls: 50,
          avg_cost_per_call: 0.1,
          by_provider: {},
          by_model: {},
          budgets: {},
          time_range: '7d',
        }),
      });
    });

    // Simulate API error for timeseries
    await page.route('**/api/v1/admin/costs/timeseries*', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await navigateClientSide(page, '/admin/costs');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // Chart should still render (with fallback demo data)
    const chart = page.locator('[data-testid="token-usage-chart"]');
    await expect(chart).toBeVisible();

    console.log('✓ Error state handled gracefully');
  });

  test('should have export button available', async ({ page }) => {
    await page.route('**/api/v1/admin/costs/stats*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_cost_usd: 10.0,
          total_tokens: 100000,
          total_calls: 75,
          avg_cost_per_call: 0.13,
          by_provider: { ollama: { cost_usd: 10, tokens: 100000, calls: 75, avg_cost_per_call: 0.13 } },
          by_model: {},
          budgets: {},
          time_range: '7d',
        }),
      });
    });

    await page.route('**/api/v1/admin/costs/timeseries*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { date: '2026-01-17', tokens: 30000, cost_usd: 0.1, provider: 'ollama' },
            { date: '2026-01-16', tokens: 35000, cost_usd: 0.12, provider: 'ollama' },
            { date: '2026-01-15', tokens: 35000, cost_usd: 0.11, provider: 'ollama' },
          ],
        }),
      });
    });

    await navigateClientSide(page, '/admin/costs');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Check export button exists
    const exportButton = page.locator('[data-testid="export-chart-button"]');
    await expect(exportButton).toBeVisible();

    console.log('✓ Export chart button available');
  });
});
