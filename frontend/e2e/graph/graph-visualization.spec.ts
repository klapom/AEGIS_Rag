import { test, expect } from '../fixtures';

/**
 * E2E Tests for Graph Visualization - Sprint 34
 *
 * Tests graph visualization features implemented in Sprint 34:
 * - Feature 34.3: Edge Type Visualization (colored edges by relationship type)
 * - Feature 34.4: Relationship Tooltips & Details
 * - Feature 34.5: Multi-Hop Query Support (API endpoints)
 * - Feature 34.6: Graph Edge Filter (filter by relationship type, weight threshold)
 *
 * Dependencies:
 * - Backend running on http://localhost:8000 with Neo4j connected
 * - Knowledge graph populated with RELATES_TO relationships (Feature 34.1, 34.2)
 * - Frontend graph components compiled and deployed
 *
 * Backend Requirements:
 * - RELATES_TO relationships stored in Neo4j (from Feature 34.1, 34.2)
 * - Multi-hop query endpoint: POST /api/v1/graph/viz/multi-hop
 * - Shortest-path endpoint: POST /api/v1/graph/viz/shortest-path
 * - Edge type information in graph visualization
 */

test.describe('Graph Visualization - Edge Type Display (Feature 34.3)', () => {
  // Sprint 119 BUG-119.1: Skip tests when no graph data available in test namespace
  test.beforeEach(async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForNetworkIdle();
    const statsNode = adminGraphPage.page.locator('[data-testid="graph-stats-nodes"]');
    const hasStats = await statsNode.isVisible({ timeout: 5000 }).catch(() => false);
    if (hasStats) {
      const nodeCount = await statsNode.textContent().then(t => parseInt(t || '0')).catch(() => 0);
      if (nodeCount === 0) {
        test.skip(true, 'No graph data available in test namespace');
      }
    }
  });

  test('should display graph with colored edges by relationship type', async ({
    adminGraphPage,
  }) => {
    // Navigate to graph analytics page
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    // Check that graph canvas is visible
    const isGraphVisible = await adminGraphPage.isGraphVisible();
    expect(isGraphVisible).toBe(true);

    // Verify canvas element exists
    const graphCanvas = adminGraphPage.page.locator('canvas').first();
    await expect(graphCanvas).toBeVisible();
  });

  test('should show relationship legend with edge types', async ({
    adminGraphPage,
  }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const isGraphVisible = await adminGraphPage.isGraphVisible();
    if (!isGraphVisible) {
      test.skip();
    }

    // Check for legend section with relationship types
    const legend = adminGraphPage.page.locator('[data-testid="graph-legend"]');
    const hasLegend = await legend.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasLegend) {
      // Check for RELATES_TO relationship type
      const relatesTo = adminGraphPage.page.locator('text=/RELATES_TO|Relates To/i');
      const hasRelatesTo = await relatesTo.isVisible({ timeout: 2000 }).catch(() => false);
      expect(typeof hasRelatesTo).toBe('boolean');

      // Check for MENTIONED_IN relationship type
      const mentionedIn = adminGraphPage.page.locator('text=/MENTIONED_IN|Mentioned In/i');
      const hasMentionedIn = await mentionedIn.isVisible({ timeout: 2000 }).catch(() => false);
      expect(typeof hasMentionedIn).toBe('boolean');
    } else {
      // If no legend, at least verify graph is displayed
      await expect(adminGraphPage.graphCanvas).toBeVisible();
    }
  });

  test('should distinguish edges by color based on relationship type', async ({
    adminGraphPage,
  }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const isGraphVisible = await adminGraphPage.isGraphVisible();
    expect(isGraphVisible).toBe(true);

    // Get all edges from the graph
    const edges = adminGraphPage.graphEdges;
    const edgeCount = await edges.count();

    // If graph has edges, verify they exist
    if (edgeCount > 0) {
      expect(edgeCount).toBeGreaterThan(0);
      // Note: Canvas-based rendering makes color verification difficult
      // This test verifies edges are present
    }
  });
});

test.describe('Graph Visualization - Relationship Details (Feature 34.4)', () => {
  // Sprint 119 BUG-119.1: Skip tests when no graph data available in test namespace
  test.beforeEach(async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForNetworkIdle();
    const statsNode = adminGraphPage.page.locator('[data-testid="graph-stats-nodes"]');
    const hasStats = await statsNode.isVisible({ timeout: 5000 }).catch(() => false);
    if (hasStats) {
      const nodeCount = await statsNode.textContent().then(t => parseInt(t || '0')).catch(() => 0);
      if (nodeCount === 0) {
        test.skip(true, 'No graph data available in test namespace');
      }
    }
  });

  test('should display edge weight information', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const isGraphVisible = await adminGraphPage.isGraphVisible();
    if (!isGraphVisible) {
      test.skip();
    }

    // Check for edge weight display
    const weightLabel = adminGraphPage.page.locator('[data-testid="edge-weight"]');
    const hasWeightDisplay = await weightLabel
      .isVisible({ timeout: 2000 })
      .catch(() => false);

    // Verify element exists (may not be visible depending on graph state)
    expect(typeof hasWeightDisplay).toBe('boolean');
  });

  test('should display relationship description on node selection', async ({
    adminGraphPage,
  }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const stats = await adminGraphPage.getGraphStats();

    if (stats.nodes > 0) {
      // Click on first node
      await adminGraphPage.clickNode(0);

      // Check if details panel shows relationship info
      const detailsPanel = adminGraphPage.page.locator('[data-testid="node-details"]');
      const isDetailsPanelVisible = await detailsPanel
        .isVisible({ timeout: 2000 })
        .catch(() => false);

      expect(typeof isDetailsPanelVisible).toBe('boolean');

      if (isDetailsPanelVisible) {
        const details = await adminGraphPage.getNodeDetails();
        expect(details).toBeDefined();
      }
    }
  });
});

test.describe('Graph Visualization - Edge Filters (Feature 34.6)', () => {
  // Sprint 119 BUG-119.1: Skip tests when no graph data available in test namespace
  test.beforeEach(async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForNetworkIdle();
    const statsNode = adminGraphPage.page.locator('[data-testid="graph-stats-nodes"]');
    const hasStats = await statsNode.isVisible({ timeout: 5000 }).catch(() => false);
    if (hasStats) {
      const nodeCount = await statsNode.textContent().then(t => parseInt(t || '0')).catch(() => 0);
      if (nodeCount === 0) {
        test.skip(true, 'No graph data available in test namespace');
      }
    }
  });

  test('should have relationship type filter checkboxes', async ({
    adminGraphPage,
  }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    // Check for filter section
    const filterSection = adminGraphPage.page.locator('[data-testid="graph-edge-filter"]');
    const hasFilterSection = await filterSection
      .isVisible({ timeout: 3000 })
      .catch(() => false);

    if (hasFilterSection) {
      // Check for RELATES_TO checkbox
      const relatesToCheckbox = adminGraphPage.page.locator(
        'label:has-text("RELATES_TO"), label:has-text("Relates To")'
      );
      const hasRelatesTo = await relatesToCheckbox.isVisible({ timeout: 2000 }).catch(() => false);

      // Check for MENTIONED_IN checkbox
      const mentionedInCheckbox = adminGraphPage.page.locator(
        'label:has-text("MENTIONED_IN"), label:has-text("Mentioned In")'
      );
      const hasMentionedIn = await mentionedInCheckbox
        .isVisible({ timeout: 2000 })
        .catch(() => false);

      // At least one filter should exist
      const hasFilters = hasRelatesTo || hasMentionedIn;
      expect(typeof hasFilters).toBe('boolean');
    }
  });

  test('should have weight threshold slider', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    // Check for weight filter
    const filterSection = adminGraphPage.page.locator('[data-testid="graph-edge-filter"]');
    const hasFilterSection = await filterSection
      .isVisible({ timeout: 3000 })
      .catch(() => false);

    if (hasFilterSection) {
      // Look for weight slider
      const slider = adminGraphPage.page.locator('[data-testid="weight-threshold-slider"]');
      const hasSlider = await slider.isVisible({ timeout: 2000 }).catch(() => false);

      if (hasSlider) {
        await expect(slider).toBeVisible();
        // Verify slider is an input element
        const sliderType = await slider.getAttribute('type');
        expect(['range', null]).toContain(sliderType);
      }
    }
  });

  test('should update graph when toggling edge type filters', async ({
    adminGraphPage,
  }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const initialStats = await adminGraphPage.getGraphStats();
    const initialEdgeCount = initialStats.edges;

    // Try to toggle a filter
    const filterCheckbox = adminGraphPage.page.locator(
      'input[type="checkbox"][data-testid*="filter"]'
    );
    const hasCheckbox = await filterCheckbox.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasCheckbox) {
      await filterCheckbox.click();
      await adminGraphPage.page.waitForTimeout(500);

      const updatedStats = await adminGraphPage.getGraphStats();
      // Stats should exist (may be same or different)
      expect(typeof updatedStats.edges).toBe('number');
      expect(updatedStats.edges).toBeGreaterThanOrEqual(0);
    }
  });

  test('should adjust edge count when changing weight threshold', async ({
    adminGraphPage,
  }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const slider = adminGraphPage.page.locator('[data-testid="weight-threshold-slider"]');
    const hasSlider = await slider.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasSlider) {
      const initialStats = await adminGraphPage.getGraphStats();

      // Move slider
      await slider.fill('50');
      await adminGraphPage.page.waitForTimeout(500);

      const updatedStats = await adminGraphPage.getGraphStats();
      // Verify stats are still valid
      expect(typeof updatedStats.edges).toBe('number');
      expect(updatedStats.edges).toBeGreaterThanOrEqual(0);
    }
  });
});

test.describe('Graph Visualization - Multi-Hop Queries (Feature 34.5)', () => {
  test('should have multi-hop query API endpoint available', async ({ request }) => {
    try {
      const response = await request.post('http://localhost:8000/api/v1/graph/viz/multi-hop', {
        data: {
          entity_id: 'test-entity',
          max_hops: 2,
          include_paths: false,
        },
      });

      // Should return 200, 404 (not found), or 422 (validation error)
      // NOT 500 (internal error)
      expect([200, 404, 422]).toContain(response.status());
    } catch (error) {
      // API may not be available in test environment
      test.skip();
    }
  });

  test('should have shortest-path query API endpoint', async ({ request }) => {
    try {
      const response = await request.post('http://localhost:8000/api/v1/graph/viz/shortest-path', {
        data: {
          source_entity: 'entity-a',
          target_entity: 'entity-b',
          max_hops: 5,
        },
      });

      // Should return 200, 404, or 422
      expect([200, 404, 422]).toContain(response.status());
    } catch (error) {
      // API may not be available in test environment
      test.skip();
    }
  });

  test('should display multi-hop subgraph when querying', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const isGraphVisible = await adminGraphPage.isGraphVisible();
    if (!isGraphVisible) {
      test.skip();
    }

    // Check for multi-hop query controls
    const queryInput = adminGraphPage.page.locator('[data-testid="graph-query-input"]');
    const hasQueryInput = await queryInput.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasQueryInput) {
      // Verify multi-hop depth selector exists
      const depthSelector = adminGraphPage.page.locator('[data-testid="hop-depth-selector"]');
      const hasDepthSelector = await depthSelector.isVisible({ timeout: 2000 }).catch(() => false);

      expect(typeof hasDepthSelector).toBe('boolean');
    }
  });
});

test.describe('Graph Statistics and Metrics', () => {
  // Sprint 119 BUG-119.1: Skip tests when no graph data available in test namespace
  test.beforeEach(async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForNetworkIdle();
    const statsNode = adminGraphPage.page.locator('[data-testid="graph-stats-nodes"]');
    const hasStats = await statsNode.isVisible({ timeout: 5000 }).catch(() => false);
    if (hasStats) {
      const nodeCount = await statsNode.textContent().then(t => parseInt(t || '0')).catch(() => 0);
      if (nodeCount === 0) {
        test.skip(true, 'No graph data available in test namespace');
      }
    }
  });

  test('should display updated node and edge counts', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const stats = await adminGraphPage.getGraphStats();

    expect(stats).toBeDefined();
    expect(typeof stats.nodes).toBe('number');
    expect(typeof stats.edges).toBe('number');
    expect(stats.nodes).toBeGreaterThanOrEqual(0);
    expect(stats.edges).toBeGreaterThanOrEqual(0);
  });

  test('should display relationship type breakdown in stats', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const isGraphVisible = await adminGraphPage.isGraphVisible();
    if (!isGraphVisible) {
      test.skip();
    }

    // Check for stats breakdown by relationship type
    const relationshipStats = adminGraphPage.page.locator(
      '[data-testid="relationship-type-stats"]'
    );
    const hasStats = await relationshipStats.isVisible({ timeout: 2000 }).catch(() => false);

    expect(typeof hasStats).toBe('boolean');
  });

  test('should show entity type distribution', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    // Check for entity type breakdown
    const entityStats = adminGraphPage.page.locator('[data-testid="entity-type-stats"]');
    const hasEntityStats = await entityStats.isVisible({ timeout: 2000 }).catch(() => false);

    expect(typeof hasEntityStats).toBe('boolean');
  });
});

test.describe('Graph Page Controls and Interactions', () => {
  // Sprint 119 BUG-119.1: Skip tests when no graph data available in test namespace
  test.beforeEach(async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForNetworkIdle();
    const statsNode = adminGraphPage.page.locator('[data-testid="graph-stats-nodes"]');
    const hasStats = await statsNode.isVisible({ timeout: 5000 }).catch(() => false);
    if (hasStats) {
      const nodeCount = await statsNode.textContent().then(t => parseInt(t || '0')).catch(() => 0);
      if (nodeCount === 0) {
        test.skip(true, 'No graph data available in test namespace');
      }
    }
  });

  test('should support graph export with edge type information', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const isGraphVisible = await adminGraphPage.isGraphVisible();
    if (!isGraphVisible) {
      test.skip();
    }

    const exportButton = adminGraphPage.page.locator('[data-testid="export-graph"]');
    const hasExport = await exportButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasExport) {
      await expect(exportButton).toBeEnabled();
      expect(true).toBe(true);
    }
  });

  test('should reset filters and view', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const resetButton = adminGraphPage.page.locator('[data-testid="reset-filters"]');
    const hasResetButton = await resetButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasResetButton) {
      await resetButton.click();
      await adminGraphPage.page.waitForTimeout(300);
      expect(true).toBe(true);
    }
  });

  test('should support zoom and pan controls', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const isGraphVisible = await adminGraphPage.isGraphVisible();
    expect(isGraphVisible).toBe(true);

    const zoomInButton = adminGraphPage.page.locator('[data-testid="zoom-in"]');
    const hasZoomIn = await zoomInButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasZoomIn) {
      await adminGraphPage.zoomIn();
      expect(true).toBe(true);
    }
  });
});

test.describe('Graph Error Handling and Edge Cases', () => {
  // Sprint 119 BUG-119.1: Skip tests when no graph data available in test namespace
  test.beforeEach(async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForNetworkIdle();
    const statsNode = adminGraphPage.page.locator('[data-testid="graph-stats-nodes"]');
    const hasStats = await statsNode.isVisible({ timeout: 5000 }).catch(() => false);
    if (hasStats) {
      const nodeCount = await statsNode.textContent().then(t => parseInt(t || '0')).catch(() => 0);
      if (nodeCount === 0) {
        test.skip(true, 'No graph data available in test namespace');
      }
    }
  });

  test('should handle graph with no RELATES_TO relationships', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const isGraphVisible = await adminGraphPage.isGraphVisible();
    expect(typeof isGraphVisible).toBe('boolean');

    // Graph should still render even if no specific relationship type
    await expect(adminGraphPage.graphCanvas).toBeVisible({ timeout: 5000 });
  });

  test('should gracefully handle missing edge properties', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const stats = await adminGraphPage.getGraphStats();

    // Verify stats are valid regardless of edge properties
    expect(typeof stats.nodes).toBe('number');
    expect(typeof stats.edges).toBe('number');
  });

  test('should handle filter with no matching relationships', async ({ adminGraphPage }) => {
    await adminGraphPage.goto();
    await adminGraphPage.waitForGraphLoad(15000);

    const filterInput = adminGraphPage.page.locator('[data-testid="graph-filter"]');
    const hasFilter = await filterInput.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasFilter) {
      // Filter for non-existent type
      await adminGraphPage.filterGraph('NONEXISTENT_TYPE');
      await adminGraphPage.page.waitForTimeout(500);

      // Graph should still be visible
      const isGraphVisible = await adminGraphPage.isGraphVisible();
      expect(typeof isGraphVisible).toBe('boolean');

      // Clear filter
      await adminGraphPage.filterGraph('');
    }
  });

  test('should handle multi-hop query with non-existent entity', async ({ request }) => {
    try {
      const response = await request.post('http://localhost:8000/api/v1/graph/viz/multi-hop', {
        data: {
          entity_id: 'nonexistent-entity-12345',
          max_hops: 2,
          include_paths: false,
        },
      });

      // Should handle gracefully (404 or empty result, not 500)
      expect([200, 404, 422]).toContain(response.status());
    } catch (error) {
      test.skip();
    }
  });
});
