import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';
import { navigateClientSide } from '../fixtures';

/**
 * Page Object for Cost Dashboard (Feature 31.10)
 * Handles cost tracking visualization, budget management, and analytics
 */
export class CostDashboardPage extends BasePage {
  readonly totalCostDisplay: Locator;
  readonly monthlyBudget: Locator;
  readonly costChart: Locator;
  readonly costBreakdown: Locator;
  readonly providerStats: Locator;
  readonly budgetProgress: Locator;
  readonly refreshButton: Locator;
  readonly dateRangeSelector: Locator;
  readonly exportButton: Locator;
  readonly alertBanner: Locator;
  readonly costDetails: Locator;
  readonly totalCostCard: Locator;
  readonly totalTokensCard: Locator;
  readonly totalCallsCard: Locator;
  readonly avgCostCard: Locator;
  readonly timeRangeSelector: Locator;

  constructor(page: Page) {
    super(page);
    this.totalCostDisplay = page.locator('[data-testid="total-cost"]');
    this.monthlyBudget = page.locator('[data-testid="monthly-budget"]');
    this.costChart = page.locator('[data-testid="cost-chart"]');
    this.costBreakdown = page.locator('[data-testid="cost-breakdown"]');
    this.providerStats = page.locator('[data-testid="provider-stats"]');
    this.budgetProgress = page.locator('[data-testid="budget-progress"]');
    this.refreshButton = page.locator('[data-testid="refresh-costs"]');
    this.dateRangeSelector = page.locator('[data-testid="date-range"]');
    this.exportButton = page.locator('[data-testid="export-costs"]');
    this.alertBanner = page.locator('[data-testid="budget-alert"]');
    this.costDetails = page.locator('[data-testid="cost-details-row"]');
    // Summary cards
    this.totalCostCard = page.locator('[data-testid="card-total-cost"]');
    this.totalTokensCard = page.locator('[data-testid="card-total-tokens"]');
    this.totalCallsCard = page.locator('[data-testid="card-total-calls"]');
    this.avgCostCard = page.locator('[data-testid="card-avg-cost"]');
    this.timeRangeSelector = page.locator('[data-testid="time-range-selector"]');
  }

  /**
   * Navigate to cost dashboard
   * Sprint 123.7: Use navigateClientSide to preserve auth state
   */
  async goto(path: string = '/admin/costs') {
    await navigateClientSide(this.page, path);
    await this.waitForNetworkIdle();
  }

  /**
   * Get total cost displayed
   */
  async getTotalCost(): Promise<number> {
    const text = await this.totalCostCard.locator(".text-3xl").textContent();
    const match = text?.match(/\$?([\d.]+)/);
    return match ? parseFloat(match[1]) : 0;
  }

  /**
   * Get monthly budget
   */
  async getMonthlyBudget(): Promise<number> {
    const text = await this.monthlyBudget.textContent();
    const match = text?.match(/\$?([\d.]+)/);
    return match ? parseFloat(match[1]) : 0;
  }

  /**
   * Get budget usage percentage
   */
  async getBudgetUsagePercentage(): Promise<number> {
    const text = await this.budgetProgress.textContent();
    const match = text?.match(/(\d+)%/);
    return match ? parseInt(match[1]) : 0;
  }

  /**
   * Refresh cost data
   */
  async refreshCosts() {
    await this.refreshButton.click();
    await this.waitForNetworkIdle();
  }

  /**
   * Change date range
   */
  async setDateRange(startDate: string, endDate: string) {
    await this.dateRangeSelector.click();
    // Assuming date picker exists
    const startInput = this.page.locator('[data-testid="date-start"]');
    const endInput = this.page.locator('[data-testid="date-end"]');
    await startInput.fill(startDate);
    await endInput.fill(endDate);
    await this.page.waitForTimeout(500);
  }

  /**
   * Get cost breakdown by provider
   */
  async getCostBreakdown(): Promise<Record<string, number>> {
    const breakdown: Record<string, number> = {};
    const count = await this.costBreakdown.count();

    for (let i = 0; i < count; i++) {
      const item = this.costBreakdown.nth(i);
      const provider = await item
        .locator('[data-testid="provider-name"]')
        .textContent();
      const cost = await item
        .locator('[data-testid="provider-cost"]')
        .textContent();

      if (provider && cost) {
        const costValue = parseFloat(cost.match(/[\d.]+/)?.[0] || '0');
        breakdown[provider.trim()] = costValue;
      }
    }

    return breakdown;
  }

  /**
   * Get provider statistics
   */
  async getProviderStats(): Promise<
    Array<{
      provider: string;
      requests: number;
      totalCost: number;
      avgCost: number;
    }>
  > {
    const stats: Array<{
      provider: string;
      requests: number;
      totalCost: number;
      avgCost: number;
    }> = [];

    const count = await this.providerStats.count();
    for (let i = 0; i < count; i++) {
      const row = this.providerStats.nth(i);
      const provider = await row
        .locator('[data-testid="stat-provider"]')
        .textContent();
      const requests = await row
        .locator('[data-testid="stat-requests"]')
        .textContent();
      const totalCost = await row
        .locator('[data-testid="stat-total"]')
        .textContent();
      const avgCost = await row
        .locator('[data-testid="stat-average"]')
        .textContent();

      if (provider) {
        stats.push({
          provider: provider.trim(),
          requests: parseInt(requests?.match(/\d+/)?.[0] || '0') || 0,
          totalCost: parseFloat(totalCost?.match(/[\d.]+/)?.[0] || '0') || 0,
          avgCost: parseFloat(avgCost?.match(/[\d.]+/)?.[0] || '0') || 0,
        });
      }
    }

    return stats;
  }

  /**
   * Check if budget alert is shown
   */
  async hasBudgetAlert(): Promise<boolean> {
    try {
      await this.alertBanner.waitFor({ state: 'visible', timeout: 1000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get alert message
   */
  async getAlertMessage(): Promise<string | null> {
    if (await this.hasBudgetAlert()) {
      return await this.alertBanner.textContent();
    }
    return null;
  }

  /**
   * Export costs as CSV
   */
  async exportCosts() {
    const downloadPromise = this.page.waitForEvent('download');
    await this.exportButton.click();
    const download = await downloadPromise;
    return download.path();
  }

  /**
   * Get cost details for a specific row
   */
  async getCostDetailRow(index: number): Promise<{
    date: string | null;
    provider: string | null;
    model: string | null;
    cost: number;
  }> {
    const row = this.costDetails.nth(index);
    const dateText = await row.locator('[data-testid="detail-date"]').textContent();
    const providerText = await row
      .locator('[data-testid="detail-provider"]')
      .textContent();
    const modelText = await row.locator('[data-testid="detail-model"]').textContent();
    const costText = await row.locator('[data-testid="detail-cost"]').textContent();

    return {
      date: dateText?.trim() || null,
      provider: providerText?.trim() || null,
      model: modelText?.trim() || null,
      cost: parseFloat(costText?.match(/[\d.]+/)?.[0] || '0') || 0,
    };
  }

  /**
   * Check if dashboard is visible
   */
  async isDashboardVisible(): Promise<boolean> {
    return await this.isVisible('[data-testid="cost-dashboard"]');
  }

  /**
   * Wait for cost data to load
   */
  async waitForCostDataLoad(timeout = 10000) {
    try {
      await this.totalCostCard.waitFor({ state: 'visible', timeout });
    } catch {
      throw new Error('Cost data failed to load');
    }
  }

  /**
   * Get current month cost summary
   */
  async getMonthSummary(): Promise<{
    totalCost: number;
    budget: number;
    usagePercentage: number;
    remainingBudget: number;
  }> {
    const totalCost = await this.getTotalCost();
    const budget = await this.getMonthlyBudget();
    const usagePercentage = await this.getBudgetUsagePercentage();
    const remainingBudget = budget - totalCost;

    return {
      totalCost,
      budget,
      usagePercentage,
      remainingBudget,
    };
  }
}
