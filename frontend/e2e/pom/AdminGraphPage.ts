import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * Page Object for Admin Graph Visualization
 * Handles knowledge graph visualization and admin controls
 */
export class AdminGraphPage extends BasePage {
  readonly graphCanvas: Locator;
  readonly queryInput: Locator;
  readonly queryButton: Locator;
  readonly graphNodes: Locator;
  readonly graphEdges: Locator;
  readonly filterInput: Locator;
  readonly zoomInButton: Locator;
  readonly zoomOutButton: Locator;
  readonly resetViewButton: Locator;
  readonly nodeDetailsPanel: Locator;
  readonly nodeLabel: Locator;
  readonly exportGraphButton: Locator;
  readonly layoutToggle: Locator;

  constructor(page: Page) {
    super(page);
    this.graphCanvas = page.locator('[data-testid="graph-canvas"]');
    this.queryInput = page.locator('[data-testid="graph-query-input"]');
    this.queryButton = page.locator('[data-testid="graph-query-button"]');
    this.graphNodes = page.locator('[data-testid="graph-node"]');
    this.graphEdges = page.locator('[data-testid="graph-edge"]');
    this.filterInput = page.locator('[data-testid="graph-filter"]');
    this.zoomInButton = page.locator('[data-testid="zoom-in"]');
    this.zoomOutButton = page.locator('[data-testid="zoom-out"]');
    this.resetViewButton = page.locator('[data-testid="reset-view"]');
    this.nodeDetailsPanel = page.locator('[data-testid="node-details"]');
    this.nodeLabel = page.locator('[data-testid="node-label"]');
    this.exportGraphButton = page.locator('[data-testid="export-graph"]');
    this.layoutToggle = page.locator('[data-testid="layout-toggle"]');
  }

  /**
   * Navigate to admin graph page
   */
  async goto() {
    await super.goto('/admin/graph');
    await this.waitForNetworkIdle();
  }

  /**
   * Wait for graph to load
   */
  async waitForGraphLoad(timeout = 15000) {
    try {
      await this.graphCanvas.waitFor({ state: 'visible', timeout });
    } catch {
      throw new Error('Graph canvas failed to load');
    }
  }

  /**
   * Query the graph
   */
  async queryGraph(query: string) {
    await this.queryInput.fill(query);
    await this.queryButton.click();
    await this.page.waitForTimeout(1000);
  }

  /**
   * Get number of nodes in graph
   */
  async getNodeCount(): Promise<number> {
    return await this.graphNodes.count();
  }

  /**
   * Get number of edges in graph
   */
  async getEdgeCount(): Promise<number> {
    return await this.graphEdges.count();
  }

  /**
   * Click on a node to view details
   */
  async clickNode(index: number) {
    const node = this.graphNodes.nth(index);
    await node.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Get node details
   */
  async getNodeDetails(): Promise<{
    label: string | null;
    type: string | null;
    properties: Record<string, string>;
  }> {
    return {
      label: await this.nodeLabel.textContent(),
      type: await this.page
        .locator('[data-testid="node-type"]')
        .textContent(),
      properties: {},
    };
  }

  /**
   * Filter graph nodes
   */
  async filterGraph(filterText: string) {
    await this.filterInput.fill(filterText);
    await this.page.waitForTimeout(500);
  }

  /**
   * Zoom in
   */
  async zoomIn() {
    await this.zoomInButton.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Zoom out
   */
  async zoomOut() {
    await this.zoomOutButton.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Reset view to default
   */
  async resetView() {
    await this.resetViewButton.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Toggle layout algorithm (force-directed, hierarchical, etc.)
   */
  async toggleLayout() {
    await this.layoutToggle.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Export graph visualization
   */
  async exportGraph() {
    const downloadPromise = this.page.waitForEvent('download');
    await this.exportGraphButton.click();
    const download = await downloadPromise;
    return download.path();
  }

  /**
   * Check if graph is visible
   */
  async isGraphVisible(): Promise<boolean> {
    return await this.isVisible('[data-testid="graph-canvas"]');
  }

  /**
   * Get graph statistics
   */
  async getGraphStats(): Promise<{
    nodes: number;
    edges: number;
  }> {
    return {
      nodes: await this.getNodeCount(),
      edges: await this.getEdgeCount(),
    };
  }

  /**
   * Wait for graph update after query
   */
  async waitForGraphUpdate(timeout = 10000) {
    await this.page.waitForFunction(
      () => {
        const nodes = document.querySelectorAll('[data-testid="graph-node"]');
        return nodes.length > 0;
      },
      { timeout }
    );
  }

  /**
   * Sprint 34: Get edge type filters (RELATES_TO, MENTIONED_IN)
   */
  async getEdgeTypeFilters(): Promise<string[]> {
    const filterLabels = this.page.locator('[data-testid="edge-type-filter"] label');
    const count = await filterLabels.count();
    const filters: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await filterLabels.nth(i).textContent();
      if (text) {
        filters.push(text.trim());
      }
    }

    return filters;
  }

  /**
   * Sprint 34: Toggle specific edge type filter
   */
  async toggleEdgeTypeFilter(edgeType: string) {
    const checkbox = this.page.locator(
      `[data-testid="edge-type-filter"] label:has-text("${edgeType}") input[type="checkbox"]`
    );
    await checkbox.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Sprint 34: Set weight threshold (0-100)
   */
  async setWeightThreshold(percent: number) {
    const slider = this.page.locator('[data-testid="weight-threshold-slider"]');
    await slider.fill(percent.toString());
    await this.page.waitForTimeout(500);
  }

  /**
   * Sprint 34: Get current weight threshold value
   */
  async getWeightThreshold(): Promise<number> {
    const slider = this.page.locator('[data-testid="weight-threshold-slider"]');
    const value = await slider.inputValue();
    return value ? parseInt(value) : 0;
  }

  /**
   * Sprint 34: Check if relationship legend is visible
   */
  async isLegendVisible(): Promise<boolean> {
    const legend = this.page.locator('[data-testid="graph-legend"]');
    return await legend.isVisible({ timeout: 2000 }).catch(() => false);
  }

  /**
   * Sprint 34: Get relationship types from legend
   */
  async getRelationshipTypes(): Promise<string[]> {
    const legend = this.page.locator('[data-testid="graph-legend"]');
    const isVisible = await legend.isVisible({ timeout: 2000 }).catch(() => false);

    if (!isVisible) {
      return [];
    }

    const items = legend.locator('[data-testid*="legend-item"]');
    const count = await items.count();
    const types: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) {
        types.push(text.trim());
      }
    }

    return types;
  }

  /**
   * Sprint 34: Set hop depth for multi-hop queries
   */
  async setHopDepth(depth: number) {
    const depthSelector = this.page.locator('[data-testid="hop-depth-selector"]');
    await depthSelector.selectOption(depth.toString());
    await this.page.waitForTimeout(500);
  }

  /**
   * Sprint 34: Query multi-hop relationships
   */
  async queryMultiHop(entityId: string, maxHops: number = 2) {
    const queryInput = this.page.locator('[data-testid="graph-query-input"]');
    await queryInput.fill(entityId);

    const hopSelector = this.page.locator('[data-testid="hop-depth-selector"]');
    await hopSelector.selectOption(maxHops.toString());

    const queryButton = this.page.locator('[data-testid="graph-query-button"]');
    await queryButton.click();
    await this.page.waitForTimeout(1000);
  }

  /**
   * Sprint 34: Check if edge weight information is displayed
   */
  async hasEdgeWeightInfo(): Promise<boolean> {
    const weightLabel = this.page.locator('[data-testid="edge-weight"]');
    return await weightLabel.isVisible({ timeout: 2000 }).catch(() => false);
  }

  /**
   * Sprint 34: Get edge statistics (count by type)
   */
  async getEdgeStats(): Promise<Record<string, number>> {
    const stats: Record<string, number> = {};
    const statItems = this.page.locator('[data-testid="relationship-type-stats"] [data-testid*="stat-"]');
    const count = await statItems.count();

    for (let i = 0; i < count; i++) {
      const item = statItems.nth(i);
      const text = await item.textContent();
      if (text && text.includes(':')) {
        const [type, value] = text.split(':').map(s => s.trim());
        stats[type] = parseInt(value) || 0;
      }
    }

    return stats;
  }

  /**
   * Sprint 34: Reset all filters and view
   */
  async resetAllFilters() {
    const resetButton = this.page.locator('[data-testid="reset-filters"]');
    const hasButton = await resetButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasButton) {
      await resetButton.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Sprint 34: Check if graph has RELATES_TO relationships
   */
  async hasRelationships(type: string = 'RELATES_TO'): Promise<boolean> {
    const stats = await this.getEdgeStats();
    return (stats[type] || 0) > 0;
  }

  /**
   * Sprint 34: Get relationship edge count by type
   */
  async getEdgeCountByType(type: string): Promise<number> {
    const stats = await this.getEdgeStats();
    return stats[type] || 0;
  }
}
