import { test, expect } from '@playwright/test';
import { setupAuthMocking } from '../../fixtures';

/**
 * E2E Tests for Entity Changelog Panel - Sprint 39 Feature 39.6
 *
 * Tests:
 * 1. Changelog panel renders with changes list
 * 2. Change entries display all required information
 * 3. Change type badges display correctly
 * 4. User filter dropdown works
 * 5. View Version button is clickable
 * 6. Revert to Previous button is clickable
 * 7. Load More button loads additional changes
 * 8. Empty state displays when no changes
 * 9. Error handling displays error message
 *
 * Backend: GET /api/v1/entities/{entity_id}/changelog
 * Required: Backend running on http://localhost:8000
 *
 * Sprint 38: Uses setupAuthMocking for JWT authentication on protected routes
 */

test.describe('Entity Changelog Panel - Feature 39.6', () => {
  const mockChangelog = {
    changes: [
      {
        id: 'change1',
        timestamp: '2024-12-05T14:32:00Z',
        changedBy: 'admin',
        changeType: 'update',
        changedFields: ['description'],
        oldValues: { description: 'Old description' },
        newValues: { description: 'New description' },
        reason: 'Updated information',
        version: 3,
      },
      {
        id: 'change2',
        timestamp: '2024-11-28T09:15:00Z',
        changedBy: 'system',
        changeType: 'create',
        changedFields: ['name', 'type'],
        oldValues: {},
        newValues: { name: 'Kubernetes', type: 'TECHNOLOGY' },
        reason: 'Created from document',
        version: 1,
      },
      {
        id: 'change3',
        timestamp: '2024-12-01T10:00:00Z',
        changedBy: 'user1',
        changeType: 'relation_added',
        changedFields: ['relationships'],
        oldValues: {},
        newValues: { relationships: ['RELATES_TO -> Docker'] },
        reason: 'Added relationship',
        version: 2,
      },
    ],
    total: 3,
  };

  test.beforeEach(async ({ page }) => {
    // Setup authentication mocking for protected routes
    await setupAuthMocking(page);

    // Navigate to entity detail page with changelog tab
    await page.goto('/graph/entity/kubernetes/changelog');
    await page.waitForLoadState('networkidle');
  });

  test('should render changelog panel with changes list', async ({ page }) => {
    // Mock API response
    await page.route('**/api/v1/entities/*/changelog*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChangelog),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const changelog = page.locator('[data-testid="entity-changelog"]');
    await expect(changelog).toBeVisible();

    // Check header
    const header = page.locator('text=Change History (3 changes)');
    await expect(header).toBeVisible();

    // Check that changes are displayed
    const changeEntries = page.locator('[data-testid="changelog-entry"]');
    await expect(changeEntries).toHaveCount(3);
  });

  test('should display all change information correctly', async ({ page }) => {
    await page.route('**/api/v1/entities/*/changelog*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChangelog),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const firstEntry = page.locator('[data-testid="changelog-entry"]').first();

    // Check timestamp (German format)
    await expect(firstEntry).toContainText('5.12.2024');

    // Check user
    await expect(firstEntry).toContainText('admin');

    // Check change type badge
    const badge = firstEntry.locator('text=update');
    await expect(badge).toBeVisible();

    // Check changed fields
    await expect(firstEntry).toContainText('description');
  });

  test('should display correct change type badges with colors', async ({ page }) => {
    await page.route('**/api/v1/entities/*/changelog*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChangelog),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const entries = page.locator('[data-testid="changelog-entry"]');

    // Check update badge
    const updateBadge = entries.nth(0).locator('text=update');
    await expect(updateBadge).toBeVisible();

    // Check create badge
    const createBadge = entries.nth(1).locator('text=create');
    await expect(createBadge).toBeVisible();

    // Check relation_added badge
    const relationBadge = entries.nth(2).locator('text=relation added');
    await expect(relationBadge).toBeVisible();
  });

  test('should filter changes by user when filter is selected', async ({ page }) => {
    await page.route('**/api/v1/entities/*/changelog*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChangelog),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const userFilter = page.locator('[data-testid="user-filter"]');
    await userFilter.waitFor({ state: 'visible' });

    // Initially should show all changes
    let entries = page.locator('[data-testid="changelog-entry"]');
    await expect(entries).toHaveCount(3);

    // Select 'admin' filter
    await userFilter.selectOption('admin');
    await page.waitForTimeout(500);

    // Should now show only admin's changes
    entries = page.locator('[data-testid="changelog-entry"]');
    await expect(entries).toHaveCount(1);
    await expect(entries.first()).toContainText('admin');
  });

  test('should have clickable View Version button', async ({ page }) => {
    await page.route('**/api/v1/entities/*/changelog*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChangelog),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const viewButton = page
      .locator('[data-testid="changelog-entry"]')
      .first()
      .locator('[data-testid="view-version-button"]');

    await expect(viewButton).toBeVisible();
    await expect(viewButton).toContainText('View Version 3');
    await expect(viewButton).toBeEnabled();
  });

  test('should have clickable Revert to Previous button for non-create changes', async ({
    page,
  }) => {
    await page.route('**/api/v1/entities/*/changelog*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChangelog),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    // First entry (update) should have revert button
    const firstEntry = page.locator('[data-testid="changelog-entry"]').first();
    const revertButton = firstEntry.locator('[data-testid="revert-button"]');
    await expect(revertButton).toBeVisible();
    await expect(revertButton).toContainText('Revert to Previous');

    // Second entry (create) should NOT have revert button
    const secondEntry = page.locator('[data-testid="changelog-entry"]').nth(1);
    const noRevertButton = secondEntry.locator('[data-testid="revert-button"]');
    await expect(noRevertButton).not.toBeVisible();
  });

  test('should load more changes when Load More is clicked', async ({ page }) => {
    const initialChangelog = {
      changes: Array.from({ length: 50 }, (_, i) => ({
        id: `change${i}`,
        timestamp: '2024-12-01T10:00:00Z',
        changedBy: 'user',
        changeType: 'update',
        changedFields: ['field'],
        oldValues: {},
        newValues: {},
        reason: 'Update',
        version: i + 1,
      })),
      total: 100,
    };

    let requestCount = 0;

    await page.route('**/api/v1/entities/*/changelog*', async (route) => {
      requestCount++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(initialChangelog),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    // Check initial count
    let entries = page.locator('[data-testid="changelog-entry"]');
    await expect(entries).toHaveCount(50);

    // Click Load More
    const loadMoreButton = page.locator('[data-testid="load-more-button"]');
    await expect(loadMoreButton).toBeVisible();
    await loadMoreButton.click();

    // Wait for new request
    await page.waitForTimeout(1000);
    expect(requestCount).toBeGreaterThan(1);
  });

  test('should display empty state when no changes exist', async ({ page }) => {
    await page.route('**/api/v1/entities/*/changelog*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ changes: [], total: 0 }),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const emptyMessage = page.locator('text=No changes found for this entity');
    await expect(emptyMessage).toBeVisible();
  });

  test('should display error message on API failure', async ({ page }) => {
    await page.route('**/api/v1/entities/*/changelog*', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'text/plain',
        body: 'Internal Server Error',
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const errorMessage = page.locator('text=/Error loading changelog/i');
    await expect(errorMessage).toBeVisible();
  });
});
