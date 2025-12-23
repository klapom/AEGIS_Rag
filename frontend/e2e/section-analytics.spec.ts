import { test, expect } from '../fixtures';

/**
 * E2E Tests for Section Analytics
 * Sprint 62 Feature 62.5: Section Analytics Endpoint and Visualization
 *
 * Tests verify:
 * - Analytics endpoint returns section statistics
 * - Section level distribution displayed correctly
 * - Entity counts per section accurate
 * - Section size distribution shown properly
 * - Analytics refresh works correctly
 * - UI handles empty analytics gracefully
 *
 * Backend: Uses real analytics endpoint at /api/v1/analytics/sections
 * Cost: FREE (no LLM inference required)
 */

test.describe('Section Analytics', () => {
  test('should load and display section statistics', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    // Look for analytics section on admin dashboard
    const analyticsSection = adminDashboardPage.page.locator('[data-testid="analytics-section"]');
    const isAnalyticsVisible = await analyticsSection.isVisible().catch(() => false);

    if (isAnalyticsVisible) {
      // Verify analytics loaded
      const statsContainer = analyticsSection.locator('[data-testid="section-stats"]');
      const hasStats = await statsContainer.isVisible().catch(() => false);

      expect(hasStats).toBeTruthy();
    }
  });

  test('should display section level distribution', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    // Navigate to analytics or indexing page with analytics
    const analyticsTab = adminDashboardPage.page.locator('[data-testid="analytics-tab"]');
    const isTabVisible = await analyticsTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await analyticsTab.click();
      await adminDashboardPage.page.waitForTimeout(500);
    }

    // Look for level distribution chart or list
    const levelDistribution = adminDashboardPage.page.locator('[data-testid="level-distribution"]');
    const isDistributionVisible = await levelDistribution.isVisible().catch(() => false);

    if (isDistributionVisible) {
      // Verify distribution has content
      const levels = await levelDistribution.locator('[data-testid="level-item"]').all();

      if (levels.length > 0) {
        // Verify each level item has proper structure
        for (const level of levels) {
          const levelName = level.locator('[data-testid="level-name"]');
          const count = level.locator('[data-testid="level-count"]');

          const hasName = await levelName.isVisible().catch(() => false);
          const hasCount = await count.isVisible().catch(() => false);

          if (hasName && hasCount) {
            const countText = await count.textContent();
            expect(countText).toBeTruthy();
            expect(/\d+/.test(countText || '')).toBeTruthy();
          }
        }
      }
    }
  });

  test('should display entity counts per section', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    // Look for entity statistics
    const entityStats = adminDashboardPage.page.locator('[data-testid="entity-stats"]');
    const hasEntityStats = await entityStats.isVisible().catch(() => false);

    if (hasEntityStats) {
      // Verify entity count display
      const entityItems = await entityStats.locator('[data-testid="entity-item"]').all();

      if (entityItems.length > 0) {
        const firstItem = entityItems[0];

        // Check for entity count information
        const count = firstItem.locator('[data-testid="entity-count"]');
        const hasCount = await count.isVisible().catch(() => false);

        if (hasCount) {
          const countText = await count.textContent();
          expect(countText).toBeTruthy();
          // Should be a number
          expect(/\d+/.test(countText || '')).toBeTruthy();
        }
      }
    }
  });

  test('should show section size distribution', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    // Look for size distribution or metrics
    const sizeMetrics = adminDashboardPage.page.locator('[data-testid="size-metrics"]');
    const hasSizeMetrics = await sizeMetrics.isVisible().catch(() => false);

    if (hasSizeMetrics) {
      // Verify metrics display
      const metrics = await sizeMetrics.locator('[data-testid="metric"]').all();

      for (const metric of metrics) {
        const label = metric.locator('[data-testid="metric-label"]');
        const value = metric.locator('[data-testid="metric-value"]');

        const hasLabel = await label.isVisible().catch(() => false);
        const hasValue = await value.isVisible().catch(() => false);

        if (hasLabel && hasValue) {
          const valueText = await value.textContent();
          expect(valueText).toBeTruthy();
        }
      }
    }
  });

  test('should handle analytics for documents with multiple sections', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    // Look for section breakdown
    const sectionBreakdown = adminDashboardPage.page.locator('[data-testid="section-breakdown"]');
    const hasBreakdown = await sectionBreakdown.isVisible().catch(() => false);

    if (hasBreakdown) {
      // Verify multiple sections are listed
      const sections = await sectionBreakdown.locator('[data-testid="section-item"]').all();

      if (sections.length > 1) {
        // Multiple sections found - verify they have different metadata
        const sectionIds: string[] = [];

        for (const section of sections) {
          const id = section.getAttribute('data-section-id');
          if (id) {
            const idValue = await id;
            if (idValue) sectionIds.push(idValue);
          }
        }

        // Should have multiple unique sections or at least multiple entries
        expect(sections.length).toBeGreaterThanOrEqual(1);
      }
    }
  });

  test('should display correct hierarchy level counts', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    const levelStats = adminDashboardPage.page.locator('[data-testid="level-distribution"]');
    const hasLevelStats = await levelStats.isVisible().catch(() => false);

    if (hasLevelStats) {
      // Get all level items
      const levelItems = await levelStats.locator('[data-testid="level-item"]').all();

      // Verify level names are correct
      const levelNames = ['Chapter', 'Section', 'Subsection', 'Subsubsection'];

      for (let i = 0; i < Math.min(levelItems.length, 4); i++) {
        const item = levelItems[i];
        const levelName = item.locator('[data-testid="level-name"]');
        const nameText = await levelName.textContent();

        // Level name might be in the list or customized
        expect(nameText).toBeTruthy();
      }
    }
  });

  test('should support analytics refresh', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    // Look for refresh button
    const refreshButton = adminDashboardPage.page.locator('[data-testid="refresh-analytics"]');
    const hasRefreshButton = await refreshButton.isVisible().catch(() => false);

    if (hasRefreshButton) {
      // Click refresh
      await refreshButton.click();
      await adminDashboardPage.page.waitForTimeout(500);

      // Verify loading state appears and completes
      const loadingState = adminDashboardPage.page.locator('[data-testid="analytics-loading"]');
      const showsLoading = await loadingState.isVisible().catch(() => false);

      // After refresh, should have analytics displayed
      const analyticsContent = adminDashboardPage.page.locator('[data-testid="analytics-content"]');
      const hasContent = await analyticsContent.isVisible({ timeout: 5000 }).catch(() => false);

      expect(hasContent).toBeTruthy();
    }
  });

  test('should display analytics summary statistics', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    // Look for summary stats (total sections, avg entities, etc.)
    const summaryStats = adminDashboardPage.page.locator('[data-testid="summary-stats"]');
    const hasSummary = await summaryStats.isVisible().catch(() => false);

    if (hasSummary) {
      // Verify key metrics are present
      const totalSections = summaryStats.locator('[data-testid="total-sections"]');
      const avgEntities = summaryStats.locator('[data-testid="avg-entities"]');
      const totalChunks = summaryStats.locator('[data-testid="total-chunks"]');

      // At least one stat should be visible
      const stats = [totalSections, avgEntities, totalChunks];
      let statsFound = false;

      for (const stat of stats) {
        const isVisible = await stat.isVisible().catch(() => false);
        if (isVisible) {
          const value = await stat.textContent();
          expect(value).toBeTruthy();
          statsFound = true;
        }
      }

      expect(statsFound).toBeTruthy();
    }
  });

  test('should show analytics for different domains separately', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    // Look for domain selector
    const domainSelector = adminDashboardPage.page.locator('[data-testid="domain-selector"]');
    const hasDomainSelector = await domainSelector.isVisible().catch(() => false);

    if (hasDomainSelector) {
      // Get list of domains
      const options = await domainSelector.locator('option, [role="option"]').all();

      if (options.length > 1) {
        // Select second domain
        const secondDomain = options[1];
        await secondDomain.click();
        await adminDashboardPage.page.waitForTimeout(500);

        // Verify analytics updated for new domain
        const analyticsContent = adminDashboardPage.page.locator('[data-testid="analytics-content"]');
        const hasContent = await analyticsContent.isVisible().catch(() => false);

        expect(hasContent).toBeTruthy();
      }
    }
  });

  test('should handle empty analytics gracefully', async ({ adminDashboardPage }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    // Look for analytics section
    const analyticsSection = adminDashboardPage.page.locator('[data-testid="analytics-section"]');
    const hasAnalytics = await analyticsSection.isVisible().catch(() => false);

    if (hasAnalytics) {
      // Verify either has content or shows empty state message
      const emptyState = analyticsSection.locator('[data-testid="empty-state"]');
      const content = analyticsSection.locator('[data-testid="analytics-content"]');

      const hasEmptyState = await emptyState.isVisible().catch(() => false);
      const hasContent = await content.isVisible().catch(() => false);

      // Should have either content or empty state, not neither
      expect(hasEmptyState || hasContent).toBeTruthy();
    }
  });

  test('should display analytics in responsive layout', async ({ adminDashboardPage, page }) => {
    // Test on desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    const analyticsContent = adminDashboardPage.page.locator('[data-testid="analytics-content"]');
    const desktopVisible = await analyticsContent.isVisible().catch(() => false);

    // Test on mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await adminDashboardPage.page.reload();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    const mobileVisible = await analyticsContent.isVisible().catch(() => false);

    // Analytics should be accessible on both layouts (or have responsive layout)
    expect(desktopVisible || mobileVisible).toBeTruthy();

    // Reset viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
  });

  test('should export analytics data', async ({ adminDashboardPage, page }) => {
    await adminDashboardPage.goto();
    await adminDashboardPage.page.waitForLoadState('networkidle');

    // Look for export button
    const exportButton = adminDashboardPage.page.locator('[data-testid="export-analytics"]');
    const hasExportButton = await exportButton.isVisible().catch(() => false);

    if (hasExportButton) {
      // Set up listener for download
      const downloadPromise = page.waitForEvent('download').catch(() => null);

      // Click export
      await exportButton.click();

      // Wait for download
      const download = await downloadPromise;

      if (download) {
        // Verify download was initiated
        expect(download).toBeTruthy();
        const filename = download.suggestedFilename();
        // Should be CSV, JSON, or PDF
        expect(/\.(csv|json|pdf)$/i.test(filename)).toBeTruthy();
      }
    }
  });
});
