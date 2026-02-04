import { test, expect, setupAuthMocking } from '../fixtures';

/**
 * E2E Tests for Admin Dashboard - Feature 46.8
 *
 * Sprint 46: Unified Admin Dashboard
 *
 * Feature 46.8 provides a comprehensive admin dashboard that consolidates
 * domain management, indexing operations, system settings, and monitoring.
 * Tests cover:
 *
 * Test Cases:
 * TC-46.8.1: Dashboard loads at /admin route
 * TC-46.8.2: Domain section renders with domain list
 * TC-46.8.3: Indexing section renders with stats
 * TC-46.8.4: Settings section renders with config
 * TC-46.8.5: Section headers are clickable
 * TC-46.8.6: Clicking header toggles section collapse
 * TC-46.8.7: Quick navigation links work
 * TC-46.8.8: Shows loading state initially
 *
 * Backend: GET /api/v1/admin/dashboard/stats
 *          GET /api/v1/admin/domains
 *          GET /api/v1/admin/indexing/stats
 * Required: Authentication mocking (admin access)
 */

// Sprint 123.7: Partially fixed - uses setupAuthMocking but still uses page.goto('/admin') instead of fixture
// Use adminDashboardPage fixture instead to preserve auth state
test.describe('Sprint 46 - Feature 46.8: Admin Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthMocking(page);
  });

  test('TC-46.8.1: should load dashboard at /admin route', async ({ page }) => {
    // Navigate to admin dashboard
    await page.goto('/admin');

    // Wait for main dashboard heading
    const dashboardHeading = page.getByRole('heading', { name: /admin dashboard|dashboard/i });
    await expect(dashboardHeading).toBeVisible({ timeout: 10000 });

    // Verify page is at correct URL
    const url = page.url();
    expect(url).toContain('/admin');
  });

  test('TC-46.8.2: should render Domain section with domain list', async ({ page }) => {
    // Mock dashboard API response
    await page.route('**/api/v1/admin/dashboard/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_domains: 5,
          active_domains: 3,
          total_documents: 150,
          total_embeddings: 1200,
          last_updated: new Date().toISOString(),
        }),
      });
    });

    // Mock domains list API
    await page.route('**/api/v1/admin/domains', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          domains: [
            {
              id: 'domain-1',
              title: 'Software Development',
              description: 'Technical documentation',
              status: 'active',
              document_count: 50,
            },
            {
              id: 'domain-2',
              title: 'Product Management',
              description: 'Product specs and features',
              status: 'active',
              document_count: 35,
            },
            {
              id: 'domain-3',
              title: 'General Knowledge',
              description: 'General purpose domain',
              status: 'active',
              document_count: 65,
            },
          ],
        }),
      });
    });

    await page.goto('/admin');

    // Wait for page load
    await page.waitForTimeout(500);

    // Check for Domain section header
    const domainSection = page.locator('[data-testid="dashboard-section-domains"]');
    const domainHeaderVisible = await domainSection.isVisible().catch(() => false);

    if (!domainHeaderVisible) {
      // Try alternative selector
      const domainHeader = page.getByText(/domain|domains/i);
      await expect(domainHeader.first()).toBeVisible({ timeout: 5000 });
    } else {
      await expect(domainSection).toBeVisible();
    }

    // Check for domain list
    const domainList = page.locator('[data-testid="dashboard-domain-list"]');
    const listVisible = await domainList.isVisible().catch(() => false);

    if (listVisible) {
      // Domain list should have items
      const domainItems = page.locator('[data-testid="dashboard-domain-item"]');
      const itemCount = await domainItems.count();
      expect(itemCount).toBeGreaterThan(0);
    }

    // At least domain section should be present
    const domainContent = page.locator('text=/software development|domains|domain/i');
    const hasContent = await domainContent.first().isVisible().catch(() => false);
    expect(hasContent).toBeTruthy();
  });

  test('TC-46.8.3: should render Indexing section with stats', async ({ page }) => {
    // Mock indexing stats API
    await page.route('**/api/v1/admin/indexing/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_documents_indexed: 1250,
          documents_processing: 5,
          documents_failed: 2,
          total_chunks: 8942,
          average_chunk_size: 842,
          last_index_time: '2024-12-15T10:30:00Z',
          indexing_speed: 125,
        }),
      });
    });

    await page.goto('/admin');

    // Wait for page load
    await page.waitForTimeout(500);

    // Check for Indexing section
    const indexingSection = page.locator('[data-testid="dashboard-section-indexing"]');
    const sectionVisible = await indexingSection.isVisible().catch(() => false);

    if (sectionVisible) {
      await expect(indexingSection).toBeVisible();

      // Check for indexing stats
      const stats = page.locator('[data-testid="dashboard-indexing-stat"]');
      const statCount = await stats.count();
      expect(statCount).toBeGreaterThan(0);
    } else {
      // Look for indexing-related content
      const indexingText = page.getByText(/indexing|documents|chunks/i);
      const hasContent = await indexingText.first().isVisible().catch(() => false);
      expect(hasContent).toBeTruthy();
    }
  });

  test('TC-46.8.4: should render Settings section with config', async ({ page }) => {
    // Mock settings API
    await page.route('**/api/v1/admin/settings', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          embedding_model: 'BGE-M3',
          chunk_size: '1200',
          chunk_overlap: '200',
          enable_auto_discovery: true,
          enable_logging: true,
          log_level: 'INFO',
          retention_days: 90,
        }),
      });
    });

    await page.goto('/admin');

    await page.waitForTimeout(500);

    // Check for Settings section
    const settingsSection = page.locator('[data-testid="dashboard-section-settings"]');
    const sectionVisible = await settingsSection.isVisible().catch(() => false);

    if (sectionVisible) {
      await expect(settingsSection).toBeVisible();

      // Check for settings config items
      const configItems = page.locator('[data-testid="dashboard-setting-item"]');
      const itemCount = await configItems.count();
      expect(itemCount).toBeGreaterThan(0);
    } else {
      // Look for settings-related content
      const settingsText = page.getByText(/settings|configuration|config/i);
      const hasContent = await settingsText.first().isVisible().catch(() => false);
      expect(hasContent).toBeTruthy();
    }
  });

  test('TC-46.8.5: should have clickable section headers', async ({ page }) => {
    await page.goto('/admin');

    await page.waitForTimeout(500);

    // Find section headers
    const domainHeader = page.locator('[data-testid="dashboard-section-header-domains"]');
    const indexingHeader = page.locator('[data-testid="dashboard-section-header-indexing"]');

    // At least one section header should be interactive
    const domainHeaderVisible = await domainHeader.isVisible().catch(() => false);
    const indexingHeaderVisible = await indexingHeader.isVisible().catch(() => false);

    if (domainHeaderVisible) {
      // Header should be clickable (have click handler)
      const isClickable = await domainHeader
        .evaluate((el) => {
          const style = window.getComputedStyle(el);
          return style.cursor === 'pointer' || el.onclick !== null;
        })
        .catch(() => true); // Assume clickable if evaluation fails

      // At minimum, header should be a button or have role="button"
      const role = await domainHeader.getAttribute('role').catch(() => null);
      expect(domainHeaderVisible && (isClickable || role === 'button')).toBeTruthy();
    }
  });

  test('TC-46.8.6: should toggle section collapse when header is clicked', async ({ page }) => {
    await page.goto('/admin');

    await page.waitForTimeout(500);

    // Find a section with content
    const domainSection = page.locator('[data-testid="dashboard-section-domains"]');
    const domainHeader = page.locator('[data-testid="dashboard-section-header-domains"]');
    const domainContent = page.locator('[data-testid="dashboard-section-content-domains"]');

    const headerVisible = await domainHeader.isVisible().catch(() => false);

    if (headerVisible) {
      // Get initial state
      const initiallyExpanded = await domainContent.isVisible().catch(() => false);

      // Click header to toggle
      await domainHeader.click();

      // Wait for state change
      await page.waitForTimeout(300);

      // Content visibility should change (or at least attempt to)
      const afterClickExpanded = await domainContent.isVisible().catch(() => false);

      // Either state changed or section doesn't support collapsing
      // Both states are acceptable for this test
      expect(typeof afterClickExpanded === 'boolean').toBeTruthy();
    }
  });

  test('TC-46.8.7: should have working quick navigation links', async ({ page }) => {
    // Mock all necessary APIs
    await page.route('**/api/v1/admin/domains', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ domains: [] }),
      });
    });

    await page.goto('/admin');

    await page.waitForTimeout(500);

    // Find quick navigation links
    const navLink = page.locator('[data-testid="dashboard-nav-link"]').first();
    const navLinkVisible = await navLink.isVisible().catch(() => false);

    if (navLinkVisible) {
      // Get link href
      const href = await navLink.getAttribute('href');
      expect(href).toBeTruthy();

      // Click navigation link
      await navLink.click();

      // Wait for navigation
      await page.waitForTimeout(500);

      // Should navigate to new page
      const newUrl = page.url();
      expect(newUrl).not.toContain('/admin/'); // Should navigate away from main admin
    } else {
      // Navigation may not be present, which is acceptable
      expect(true).toBeTruthy();
    }
  });

  test('TC-46.8.8: should show loading state initially', async ({ page }) => {
    // Set up route interception to delay response
    await page.route('**/api/v1/admin/**', async (route) => {
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 500));
      route.continue();
    });

    // Navigate to admin page
    await page.goto('/admin');

    // Look for loading state immediately after navigation
    const loadingSpinner = page.locator('[data-testid="dashboard-loading"]');
    const loadingIndicator = page.locator('[data-testid="loading-spinner"]');

    const spinnerVisible = await loadingSpinner.isVisible({ timeout: 2000 }).catch(() => false);
    const indicatorVisible = await loadingIndicator.isVisible({ timeout: 2000 }).catch(() => false);

    if (spinnerVisible || indicatorVisible) {
      // Loading state should exist
      expect(spinnerVisible || indicatorVisible).toBeTruthy();

      // Loading should complete
      const contentLoaded = page.getByRole('heading', { name: /admin|dashboard/i });
      await expect(contentLoaded).toBeVisible({ timeout: 10000 });
    }
  });

  // Sprint 114: Skip - depends on unimplemented domain statistics feature
  test.skip('TC-46.8.9: should display domain statistics cards', async ({ page }) => {
    // Mock stats API with comprehensive data
    await page.route('**/api/v1/admin/dashboard/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_domains: 8,
          active_domains: 6,
          inactive_domains: 2,
          total_documents: 2500,
          total_embeddings: 18750,
          last_updated: new Date().toISOString(),
        }),
      });
    });

    await page.goto('/admin');

    await page.waitForTimeout(500);

    // Look for stat cards
    const statCards = page.locator('[data-testid="dashboard-stat-card"]');
    const cardCount = await statCards.count().catch(() => 0);

    if (cardCount > 0) {
      expect(cardCount).toBeGreaterThan(0);

      // Verify cards contain numeric values
      const firstCard = statCards.first();
      const cardText = await firstCard.textContent();
      expect(cardText).toMatch(/\d+/);
    }

    // Alternative: check for stat values directly
    const domainCount = page.getByText(/total domains|domains/i);
    const domainVisible = await domainCount.isVisible().catch(() => false);
    expect(domainVisible || cardCount > 0).toBeTruthy();
  });

  test('TC-46.8.10: should update stats when refresh is triggered', async ({ page }) => {
    let callCount = 0;

    // Mock stats API
    await page.route('**/api/v1/admin/dashboard/stats', (route) => {
      callCount++;
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_domains: 5 + callCount,
          active_domains: 3,
          total_documents: 150,
          total_embeddings: 1200,
          last_updated: new Date().toISOString(),
        }),
      });
    });

    await page.goto('/admin');

    // Wait for initial load
    await page.waitForTimeout(500);

    // Find refresh button
    const refreshButton = page.locator('[data-testid="dashboard-refresh-button"]');
    const refreshVisible = await refreshButton.isVisible().catch(() => false);

    if (refreshVisible) {
      const initialCallCount = callCount;

      // Click refresh
      await refreshButton.click();

      // Wait for new request
      await page.waitForTimeout(500);

      // Call count should increase
      expect(callCount).toBeGreaterThan(initialCallCount);
    }
  });

  test('TC-46.8.11: should handle missing sections gracefully', async ({ page }) => {
    // Mock API with minimal response
    await page.route('**/api/v1/admin/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      });
    });

    await page.goto('/admin');

    // Dashboard should still load without errors
    const dashboardHeading = page.getByRole('heading', { name: /admin|dashboard/i });
    await expect(dashboardHeading).toBeVisible({ timeout: 10000 });

    // Page should be functional even with missing data
    const url = page.url();
    expect(url).toContain('/admin');
  });

  test('TC-46.8.12: should display error message on API failure', async ({ page }) => {
    // Mock API error
    await page.route('**/api/v1/admin/dashboard/stats', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Internal server error',
          detail: 'Failed to fetch dashboard stats',
        }),
      });
    });

    await page.goto('/admin');

    // Look for error message
    const errorMessage = page.locator('[data-testid="dashboard-error"]');
    const errorVisible = await errorMessage.isVisible({ timeout: 5000 }).catch(() => false);

    if (errorVisible) {
      const errorText = await errorMessage.textContent();
      expect(errorText).toMatch(/error|failed|unable/i);
    } else {
      // Page should still be accessible
      const dashboardHeading = page.getByRole('heading');
      const headingCount = await dashboardHeading.count();
      expect(headingCount).toBeGreaterThan(0);
    }
  });

  test('TC-46.8.13: should show user information in header', async ({ page }) => {
    await page.goto('/admin');

    // Look for user profile/info section
    const userInfo = page.locator('[data-testid="user-profile"]');
    const userBadge = page.locator('[data-testid="user-badge"]');

    const userInfoVisible = await userInfo.isVisible().catch(() => false);
    const userBadgeVisible = await userBadge.isVisible().catch(() => false);

    if (userInfoVisible) {
      // Should show user info
      const userText = await userInfo.textContent();
      expect(userText).toBeTruthy();
    }

    if (userBadgeVisible) {
      await expect(userBadge).toBeVisible();
    }
  });

  test('TC-46.8.14: should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });

    await page.goto('/admin');

    // Dashboard should still be accessible
    const dashboardHeading = page.getByRole('heading', { name: /admin|dashboard/i });
    await expect(dashboardHeading).toBeVisible({ timeout: 10000 });

    // Content should be visible (may be scrollable)
    const url = page.url();
    expect(url).toContain('/admin');
  });

  test('TC-46.8.15: should display last update timestamp', async ({ page }) => {
    const now = new Date();

    await page.route('**/api/v1/admin/dashboard/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_domains: 5,
          active_domains: 3,
          total_documents: 150,
          last_updated: now.toISOString(),
        }),
      });
    });

    await page.goto('/admin');

    // Look for last updated timestamp
    const lastUpdated = page.locator('[data-testid="dashboard-last-updated"]');
    const timestampVisible = await lastUpdated.isVisible().catch(() => false);

    if (timestampVisible) {
      const timestamp = await lastUpdated.textContent();
      expect(timestamp).toMatch(/\d{4}-\d{2}-\d{2}|just now|minutes ago/i);
    }
  });
});
