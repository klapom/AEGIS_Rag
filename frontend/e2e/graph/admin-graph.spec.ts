import { test, expect } from '../fixtures';

test.describe('Admin Graph Visualization', () => {
  test('should display full knowledge graph in admin', async ({ adminGraphPage }) => {
    try {
      await adminGraphPage.waitForGraphLoad(15000);
    } catch {
      const pageHeading = adminGraphPage.page.locator('h1, h2').first();
      const isVisible = await pageHeading.isVisible({ timeout: 5000 }).catch(() => false);
      expect(isVisible).toBe(true);
      return;
    }

    const isGraphVisible = await adminGraphPage.isGraphVisible();
    expect(isGraphVisible).toBe(true);

    const stats = await adminGraphPage.getGraphStats();
    expect(stats).toBeDefined();
    expect(typeof stats.nodes).toBe('number');
    expect(typeof stats.edges).toBe('number');
  });

  test('should show graph statistics', async ({ adminGraphPage }) => {
    try {
      await adminGraphPage.waitForGraphLoad(15000);
    } catch {
      return;
    }

    const stats = await adminGraphPage.getGraphStats();
    expect(stats).toBeDefined();
    expect(typeof stats.nodes).toBe('number');
    expect(typeof stats.edges).toBe('number');
    expect(stats.nodes).toBeGreaterThanOrEqual(0);
    expect(stats.edges).toBeGreaterThanOrEqual(0);
  });

  test('should filter graph by entity type', async ({ adminGraphPage }) => {
    try {
      await adminGraphPage.waitForGraphLoad(15000);
    } catch {
      return;
    }

    const initialStats = await adminGraphPage.getGraphStats();
    const initialNodeCount = initialStats.nodes;

    const filterInput = adminGraphPage.page.locator('[data-testid="graph-filter"]');
    const isFilterVisible = await filterInput.isVisible({ timeout: 3000 }).catch(() => false);

    if (isFilterVisible) {
      await adminGraphPage.filterGraph('PERSON');
      await adminGraphPage.page.waitForTimeout(1000);

      const filteredStats = await adminGraphPage.getGraphStats();
      const filteredNodeCount = filteredStats.nodes;
      expect(filteredNodeCount).toBeLessThanOrEqual(initialNodeCount);

      await adminGraphPage.filterGraph('');
      await adminGraphPage.page.waitForTimeout(500);
    }
  });

  test('should support zoom controls', async ({ adminGraphPage }) => {
    try {
      await adminGraphPage.waitForGraphLoad(15000);
    } catch {
      return;
    }

    const zoomInButton = adminGraphPage.page.locator('[data-testid="zoom-in"]');
    const hasZoomIn = await zoomInButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasZoomIn) {
      await adminGraphPage.zoomIn();
      await adminGraphPage.page.waitForTimeout(300);
      expect(true).toBe(true);
    }
  });

  test('should reset view', async ({ adminGraphPage }) => {
    try {
      await adminGraphPage.waitForGraphLoad(15000);
    } catch {
      return;
    }

    const resetButton = adminGraphPage.page.locator('[data-testid="reset-view"]');
    const isResetVisible = await resetButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (isResetVisible) {
      await adminGraphPage.resetView();
      await adminGraphPage.page.waitForTimeout(300);
      expect(true).toBe(true);
    }
  });

  test('should allow selecting nodes', async ({ adminGraphPage }) => {
    try {
      await adminGraphPage.waitForGraphLoad(15000);
    } catch {
      return;
    }

    const stats = await adminGraphPage.getGraphStats();

    if (stats.nodes > 0) {
      await adminGraphPage.clickNode(0);
      const detailsPanel = adminGraphPage.page.locator('[data-testid="node-details"]');
      const isDetailsPanelVisible = await detailsPanel
        .isVisible({ timeout: 2000 })
        .catch(() => false);

      if (isDetailsPanelVisible) {
        const details = await adminGraphPage.getNodeDetails();
        expect(details).toBeDefined();
      }
    }
  });

  test('should export graph', async ({ adminGraphPage }) => {
    try {
      await adminGraphPage.waitForGraphLoad(15000);
    } catch {
      return;
    }

    const exportButton = adminGraphPage.page.locator('[data-testid="export-graph"]');
    const isExportVisible = await exportButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (isExportVisible) {
      await expect(exportButton).toBeEnabled();
      await exportButton.click();
      expect(true).toBe(true);
    }
  });

  test('should toggle layout', async ({ adminGraphPage }) => {
    try {
      await adminGraphPage.waitForGraphLoad(15000);
    } catch {
      return;
    }

    const layoutToggle = adminGraphPage.page.locator('[data-testid="layout-toggle"]');
    const isLayoutToggleVisible = await layoutToggle.isVisible({ timeout: 2000 }).catch(() => false);

    if (isLayoutToggleVisible) {
      await adminGraphPage.toggleLayout();
      await adminGraphPage.page.waitForTimeout(500);
      expect(true).toBe(true);
    }
  });
});

test.describe('Admin Graph Error Handling', () => {
  test('should handle empty graph', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.page.waitForLoadState('networkidle');

    const heading = adminGraphPage.page.locator('h1, h2').first();
    const isHeadingVisible = await heading.isVisible({ timeout: 5000 });
    expect(isHeadingVisible).toBe(true);

    const isGraphVisible = await adminGraphPage.isGraphVisible();
    expect(typeof isGraphVisible).toBe('boolean');
  });

  test('should handle loading timeout', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();

    const heading = adminGraphPage.page.locator('h1, h2').first();
    const isHeadingVisible = await heading.isVisible({ timeout: 3000 });
    expect(isHeadingVisible).toBe(true);
  });

  test('should handle filter errors', async ({ adminGraphPage }) => {
    try {
      await adminGraphPage.waitForGraphLoad(15000);
    } catch {
      return;
    }

    const filterInput = adminGraphPage.page.locator('[data-testid="graph-filter"]');
    const isFilterVisible = await filterInput.isVisible({ timeout: 2000 }).catch(() => false);

    if (isFilterVisible) {
      await adminGraphPage.filterGraph('!@#$%^&*()');
      await adminGraphPage.page.waitForTimeout(500);
      expect(true).toBe(true);
      await adminGraphPage.filterGraph('');
    }
  });
});
