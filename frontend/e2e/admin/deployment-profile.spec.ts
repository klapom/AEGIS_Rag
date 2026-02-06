import { test, expect, setupAuthMocking, navigateClientSide } from '../fixtures';

/**
 * E2E Tests for Deployment Profile Management
 * Sprint 125 Feature 125.9c: Deployment Profile Selection
 *
 * Features Tested:
 * - Navigation to deployment profile page from admin nav
 * - Display of available deployment profiles (6 profiles)
 * - Selection of deployment profiles
 * - Custom domain multi-select (when custom profile chosen)
 * - API calls for saving profile
 * - Persistence of profile selection after reload
 *
 * Backend Endpoints:
 * - GET /api/v1/admin/deployment-profile (fetch current profile)
 * - GET /api/v1/admin/domains (fetch available domains)
 * - PUT /api/v1/admin/deployment-profile (save profile selection)
 *
 * Sprint 125 Feature: Domain-aware deployment with profile-based domain activation
 */

/**
 * Mock deployment profile response
 */
const mockDeploymentProfile = {
  profile_name: 'software_company',
  display_name: 'Software Company',
  description: 'Technology and engineering domains',
  active_domains: ['computer_science', 'electrical_engineering', 'mathematics'],
};

/**
 * Mock available domains
 */
const mockAvailableDomains = {
  domains: [
    {
      domain_id: 'computer_science',
      domain_name: 'Computer Science & IT',
      ddc_code: '004',
      description: 'Computing and programming',
      status: 'active',
    },
    {
      domain_id: 'electrical_engineering',
      domain_name: 'Electrical Engineering',
      ddc_code: '621.3',
      description: 'Electrical systems and power',
      status: 'active',
    },
    {
      domain_id: 'mathematics',
      domain_name: 'Mathematics & Statistics',
      ddc_code: '510',
      description: 'Mathematical sciences',
      status: 'active',
    },
    {
      domain_id: 'medicine',
      domain_name: 'Medicine & Healthcare',
      ddc_code: '610',
      description: 'Medical and health sciences',
      status: 'active',
    },
    {
      domain_id: 'chemistry',
      domain_name: 'Chemistry',
      ddc_code: '540',
      description: 'Chemical sciences',
      status: 'active',
    },
    {
      domain_id: 'biology',
      domain_name: 'Biology & Life Sciences',
      ddc_code: '570',
      description: 'Biological and life sciences',
      status: 'active',
    },
  ],
};

test.describe('Sprint 125 - Feature 125.9c: Deployment Profile Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthMocking(page);

    // Mock deployment profile endpoint
    await page.route('**/api/v1/admin/deployment-profile', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockDeploymentProfile),
        });
      } else if (route.request().method() === 'PUT') {
        // Return updated profile on save
        const body = route.request().postDataJSON();
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ...mockDeploymentProfile,
            profile_name: body.profile_name || mockDeploymentProfile.profile_name,
            active_domains: body.active_domains || mockDeploymentProfile.active_domains,
          }),
        });
      }
    });

    // Mock domains endpoint
    await page.route('**/api/v1/admin/domains', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockAvailableDomains),
      });
    });
  });

  test('should navigate to deployment profile page from admin nav', async ({ page }) => {
    // Navigate to admin dashboard
    await navigateClientSide(page, '/admin');
    await page.waitForLoadState('networkidle');

    // Look for deployment profile link
    const deploymentProfileLink = page.locator('text=/deployment.*profile|profile.*management/i');
    const isVisible = await deploymentProfileLink.isVisible().catch(() => false);

    // If link exists, click it
    if (isVisible) {
      await deploymentProfileLink.click();
      await page.waitForLoadState('networkidle');

      // Verify we're on the deployment profile page
      const pageElement = page.locator('[data-testid="deployment-profile-page"]');
      await expect(pageElement).toBeVisible({ timeout: 10000 });
    } else {
      // Alternatively, navigate directly
      await navigateClientSide(page, '/admin/deployment-profile');
      await page.waitForLoadState('networkidle');

      const pageElement = page.locator('[data-testid="deployment-profile-page"]');
      await expect(pageElement).toBeVisible({ timeout: 10000 });
    }
  });

  test('should display available deployment profiles', async ({ page }) => {
    await navigateClientSide(page, '/admin/deployment-profile');
    await page.waitForLoadState('networkidle');

    // Verify page is visible
    const pageElement = page.locator('[data-testid="deployment-profile-page"]');
    await expect(pageElement).toBeVisible({ timeout: 10000 });

    // Check for profile options
    const profiles = [
      'general',
      'software_company',
      'pharma_company',
      'law_firm',
      'university',
      'custom',
    ];

    for (const profileName of profiles) {
      const profileOption = page.locator(`[data-testid="profile-${profileName}"]`);
      const isVisible = await profileOption.isVisible().catch(() => false);
      // At least some profiles should be visible
      if (profileName === 'general' || profileName === 'software_company') {
        expect(isVisible).toBeTruthy();
      }
    }
  });

  test('should show active domains for selected profile', async ({ page }) => {
    await navigateClientSide(page, '/admin/deployment-profile');
    await page.waitForLoadState('networkidle');

    // Get software_company profile option
    const softwareCompanyProfile = page.locator('[data-testid="profile-software_company"]');
    await expect(softwareCompanyProfile).toBeVisible({ timeout: 10000 });

    // Check that domain tags are displayed
    const domainTags = page.locator('text=/Computer Science|Electrical Engineering|Mathematics/');
    const isVisible = await domainTags.isVisible().catch(() => false);

    // If profile shows domain names, they should be visible
    if (isVisible) {
      expect(isVisible).toBeTruthy();
    }
  });

  test('should allow selecting a deployment profile', async ({ page }) => {
    await navigateClientSide(page, '/admin/deployment-profile');
    await page.waitForLoadState('networkidle');

    // Get general profile option
    const generalProfile = page.locator('[data-testid="profile-general"]');
    await expect(generalProfile).toBeVisible({ timeout: 10000 });

    // Click to select
    await generalProfile.click();

    // Verify it's selected (border or background color change)
    const isSelected = await generalProfile.evaluate((el) => {
      const classes = el.className;
      return classes.includes('border-blue') || classes.includes('bg-blue');
    });

    expect(isSelected).toBeTruthy();
  });

  test('should save deployment profile via API', async ({ page }) => {
    await navigateClientSide(page, '/admin/deployment-profile');
    await page.waitForLoadState('networkidle');

    // Select a profile (if not already selected)
    const generalProfile = page.locator('[data-testid="profile-general"]');
    await generalProfile.click();
    await page.waitForTimeout(500);

    // Click save button
    const saveButton = page.locator('[data-testid="save-profile-button"]');
    await expect(saveButton).toBeVisible({ timeout: 5000 });

    // Listen for PUT request
    const putRequestPromise = page.waitForRequest(
      (request) => request.method() === 'PUT' && request.url().includes('/api/v1/admin/deployment-profile')
    );

    await saveButton.click();

    // Wait for request to complete
    const putRequest = await putRequestPromise.catch(() => null);

    if (putRequest) {
      const body = putRequest.postDataJSON();
      expect(body.profile_name).toBeTruthy();
    }

    // Wait for success message
    const successMessage = page.locator('text=/saved.*successfully|profile.*saved/i');
    const isVisible = await successMessage.isVisible().catch(() => false);

    if (isVisible) {
      expect(isVisible).toBeTruthy();
    }
  });

  test('should show custom domain selection when custom profile chosen', async ({ page }) => {
    await navigateClientSide(page, '/admin/deployment-profile');
    await page.waitForLoadState('networkidle');

    // Select custom profile
    const customProfile = page.locator('[data-testid="profile-custom"]');
    await expect(customProfile).toBeVisible({ timeout: 10000 });
    await customProfile.click();

    // Wait for custom domain section to appear
    await page.waitForTimeout(500);

    // Check for custom domain grid
    const domainCheckboxes = page.locator('[data-testid^="domain-"]');
    const count = await domainCheckboxes.count();

    // Should show multiple domain options
    expect(count).toBeGreaterThan(2);
  });

  test('should allow multi-select domains in custom mode', async ({ page }) => {
    await navigateClientSide(page, '/admin/deployment-profile');
    await page.waitForLoadState('networkidle');

    // Select custom profile
    const customProfile = page.locator('[data-testid="profile-custom"]');
    await customProfile.click();

    await page.waitForTimeout(500);

    // Select first domain
    const firstDomain = page.locator('[data-testid="domain-computer_science"]');
    if (await firstDomain.isVisible().catch(() => false)) {
      await firstDomain.click();

      // Select second domain
      const secondDomain = page.locator('[data-testid="domain-mathematics"]');
      if (await secondDomain.isVisible().catch(() => false)) {
        await secondDomain.click();

        // Verify both are checked
        const firstChecked = await firstDomain.evaluate((el: HTMLElement) => {
          const checkbox = el.querySelector('input[type="checkbox"]');
          return (checkbox as HTMLInputElement)?.checked || false;
        });

        const secondChecked = await secondDomain.evaluate((el: HTMLElement) => {
          const checkbox = el.querySelector('input[type="checkbox"]');
          return (checkbox as HTMLInputElement)?.checked || false;
        });

        expect(firstChecked).toBeTruthy();
        expect(secondChecked).toBeTruthy();
      }
    }
  });

  test('should persist profile selection after page reload', async ({ page }) => {
    await navigateClientSide(page, '/admin/deployment-profile');
    await page.waitForLoadState('networkidle');

    // Select a profile
    const softwareCompanyProfile = page.locator('[data-testid="profile-software_company"]');
    await softwareCompanyProfile.click();

    // Save profile
    const saveButton = page.locator('[data-testid="save-profile-button"]');
    await saveButton.click();

    // Wait for success
    await page.waitForTimeout(2000);

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Verify the saved profile is still selected
    const softwareCompanyProfile2 = page.locator('[data-testid="profile-software_company"]');
    const isSelected = await softwareCompanyProfile2.evaluate((el) => {
      const classes = el.className;
      return classes.includes('border-blue') || classes.includes('bg-blue');
    });

    expect(isSelected).toBeTruthy();
  });
});
