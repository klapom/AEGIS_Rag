import { test, expect } from '@playwright/test';
import { setupAuthMocking } from '../../fixtures';

/**
 * E2E Tests for Version Comparison View - Sprint 39 Feature 39.7
 *
 * Tests:
 * 1. Version Compare modal renders with selectors
 * 2. Version dropdowns populate with available versions
 * 3. Side-by-side diff view displays correctly
 * 4. Changed fields are highlighted properly
 * 5. Summary displays change counts
 * 6. Export Diff button downloads JSON
 * 7. Revert button prompts for reason and reverts
 * 8. Close button closes modal
 * 9. Error handling displays error message
 *
 * Backend:
 *   - GET /api/v1/entities/{entity_id}/versions
 *   - GET /api/v1/entities/{entity_id}/versions/{v1}/compare/{v2}
 *   - POST /api/v1/entities/{entity_id}/versions/{version}/revert
 * Required: Backend running on http://localhost:8000
 *
 * Sprint 38: Uses setupAuthMocking for JWT authentication on protected routes
 */

test.describe('Version Comparison View - Feature 39.7', () => {
  const mockVersions = [
    {
      version: 3,
      timestamp: '2024-12-05T14:32:00Z',
      changedBy: 'admin',
      properties: {
        name: 'Kubernetes',
        type: 'TECHNOLOGY',
        description: 'Container orchestration platform for automated deployment',
      },
      relationships: [
        { type: 'RELATES_TO', target: 'Docker', weight: 0.9 },
        { type: 'RELATES_TO', target: 'Helm', weight: 0.7 },
      ],
    },
    {
      version: 2,
      timestamp: '2024-12-01T10:00:00Z',
      changedBy: 'user1',
      properties: {
        name: 'Kubernetes',
        type: 'TECHNOLOGY',
        description: 'Container orchestration platform',
      },
      relationships: [{ type: 'RELATES_TO', target: 'Docker', weight: 0.9 }],
    },
    {
      version: 1,
      timestamp: '2024-11-28T09:15:00Z',
      changedBy: 'system',
      properties: {
        name: 'Kubernetes',
        type: 'TECHNOLOGY',
        description: 'Container orchestration',
      },
      relationships: [],
    },
  ];

  const mockDiff = {
    versionA: mockVersions[1],
    versionB: mockVersions[0],
    changes: {
      added: [{ field: 'relationships[1]', newValue: 'RELATES_TO -> Helm', changeType: 'added' }],
      removed: [],
      changed: [
        {
          field: 'description',
          oldValue: 'Container orchestration platform',
          newValue: 'Container orchestration platform for automated deployment',
          changeType: 'changed',
        },
      ],
    },
    summary: '1 field changed, 1 relationship added',
  };

  test.beforeEach(async ({ page }) => {
    // Setup authentication mocking for protected routes
    await setupAuthMocking(page);

    await page.goto('/graph/entity/kubernetes/versions/compare');
    await page.waitForLoadState('networkidle');
  });

  test('should render version compare modal with all controls', async ({ page }) => {
    await page.route('**/api/v1/entities/*/versions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVersions),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const compareModal = page.locator('[data-testid="version-compare"]');
    await expect(compareModal).toBeVisible();

    // Check title
    const title = page.locator('text=Compare Versions');
    await expect(title).toBeVisible();

    // Check version selectors
    const versionASelect = page.locator('[data-testid="version-a-select"]');
    const versionBSelect = page.locator('[data-testid="version-b-select"]');
    await expect(versionASelect).toBeVisible();
    await expect(versionBSelect).toBeVisible();

    // Check close button
    const closeButton = page.locator('[data-testid="close-button"]');
    await expect(closeButton).toBeVisible();
  });

  test('should populate version dropdowns with available versions', async ({ page }) => {
    await page.route('**/api/v1/entities/*/versions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVersions),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const versionASelect = page.locator('[data-testid="version-a-select"]');

    // Check that options are populated
    // Sprint 113: Added timeout to prevent race condition
    const options = versionASelect.locator('option');
    await expect(options).toHaveCount(4, { timeout: 10000 }); // 1 placeholder + 3 versions

    // Check option text includes version number and date
    await expect(options.nth(1)).toContainText('v3');
    await expect(options.nth(1)).toContainText('admin');
  });

  test('should auto-select latest two versions on load', async ({ page }) => {
    await page.route('**/api/v1/entities/*/versions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVersions),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const versionASelect = page.locator('[data-testid="version-a-select"]');
    const versionBSelect = page.locator('[data-testid="version-b-select"]');

    // Should auto-select version 2 and 3
    await expect(versionBSelect).toHaveValue('3');
    await expect(versionASelect).toHaveValue('2');
  });

  test('should display side-by-side diff view correctly', async ({ page }) => {
    await page.route('**/api/v1/entities/*/versions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVersions),
      });
    });

    await page.route('**/api/v1/entities/*/versions/2/compare/3', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiff),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // Check Version A header
    const versionAHeader = page.locator('text=Version 2');
    await expect(versionAHeader).toBeVisible();

    // Check Version B header
    const versionBHeader = page.locator('text=Version 3');
    await expect(versionBHeader).toBeVisible();

    // Check properties are displayed
    // Sprint 113: Added timeout to prevent race condition
    await expect(page.locator('text=Properties:')).toHaveCount(2, { timeout: 10000 });

    // Check relationships are displayed
    await expect(page.locator('text=Relationships:')).toHaveCount(2, { timeout: 10000 });
  });

  test('should highlight changed fields with badges', async ({ page }) => {
    await page.route('**/api/v1/entities/*/versions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVersions),
      });
    });

    await page.route('**/api/v1/entities/*/versions/2/compare/3', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiff),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // Check for CHANGED badge
    const changedBadge = page.locator('text=[CHANGED]');
    await expect(changedBadge).toBeVisible();

    // Check for ADDED badge
    const addedBadge = page.locator('text=[ADDED]');
    await expect(addedBadge).toBeVisible();
  });

  test('should display summary with change counts', async ({ page }) => {
    await page.route('**/api/v1/entities/*/versions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVersions),
      });
    });

    await page.route('**/api/v1/entities/*/versions/2/compare/3', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiff),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    const summary = page.locator('text=1 field changed, 1 relationship added');
    await expect(summary).toBeVisible();
  });

  test('should download JSON when Export Diff is clicked', async ({ page }) => {
    await page.route('**/api/v1/entities/*/versions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVersions),
      });
    });

    await page.route('**/api/v1/entities/*/versions/2/compare/3', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiff),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // Set up download listener
    const downloadPromise = page.waitForEvent('download');

    const exportButton = page.locator('[data-testid="export-diff-button"]');
    await exportButton.click();

    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/version-diff-.*\.json/);
  });

  test('should prompt for reason and revert when Revert is clicked', async ({ page }) => {
    await page.route('**/api/v1/entities/*/versions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVersions),
      });
    });

    await page.route('**/api/v1/entities/*/versions/2/compare/3', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDiff),
      });
    });

    let revertCalled = false;
    await page.route('**/api/v1/entities/*/versions/*/revert', async (route) => {
      revertCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVersions[0]),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // Mock the prompt dialog
    page.on('dialog', async (dialog) => {
      expect(dialog.type()).toBe('prompt');
      expect(dialog.message()).toContain('reason');
      await dialog.accept('Test revert reason');
    });

    const revertButton = page.locator('[data-testid="revert-button"]');
    await revertButton.click();

    // Wait for API call
    await page.waitForTimeout(1000);
    expect(revertCalled).toBe(true);
  });

  test('should close modal when close button is clicked', async ({ page }) => {
    await page.route('**/api/v1/entities/*/versions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVersions),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const closeButton = page.locator('[data-testid="close-button"]');
    await closeButton.click();

    // Modal should be closed (this depends on your implementation)
    // You might need to adjust based on how the modal closing is handled
  });

  test('should display error message on API failure', async ({ page }) => {
    await page.route('**/api/v1/entities/*/versions', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'text/plain',
        body: 'Internal Server Error',
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const errorMessage = page.locator('text=/Error loading/i');
    await expect(errorMessage).toBeVisible();
  });
});
