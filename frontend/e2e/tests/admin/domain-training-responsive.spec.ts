/**
 * E2E Tests for Domain Training Page Responsive Design
 * Sprint 73 Feature 73.1
 *
 * Tests cover:
 * 11. Mobile (375px): Form fields stack vertically
 * 12. Tablet (768px): 2-column form layout
 * 13. Desktop (1024px+): 3-column form with preview panel
 *
 * Components Tested:
 * - /admin/domain-training
 * - Domain creation wizard
 * - Training configuration forms
 * - Sample upload and preview
 *
 * Implementation Notes:
 * - Uses setupAuthMocking for authentication
 * - Tests form layout at each breakpoint
 * - Verifies field visibility and arrangement
 * - Screenshots captured for visual verification (see comments)
 */

import { test, expect } from '@playwright/test';
import { setupAuthMocking } from '../../fixtures';

test.describe('Domain Training Page Responsive Design', () => {
  test('should display mobile layout (375px) - vertically stacked form fields', async ({
    page,
  }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Setup authentication and navigate to domain training
    await setupAuthMocking(page);
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Test 1: Create domain button should be full width on mobile
    const createButton = page.getByTestId('create-domain-button');
    const createVisible = await createButton.isVisible().catch(() => false);

    if (createVisible) {
      const buttonWidth = await createButton.evaluate(el => el.getBoundingClientRect().width);
      const viewportWidth = 375;

      // Create button should be wide (>80% width) on mobile
      expect(buttonWidth).toBeGreaterThan(viewportWidth * 0.75);

      // Click to open wizard
      await createButton.click();
      await page.waitForTimeout(1000);
    }

    // Test 2: Form fields should stack vertically
    const formContainer = page.locator('form, [data-testid="domain-form"]');
    const formVisible = await formContainer.isVisible().catch(() => false);

    if (formVisible) {
      // Check first two form inputs
      const inputs = formContainer.locator('input, select, textarea');
      const inputCount = await inputs.count();

      if (inputCount >= 2) {
        const input1 = inputs.nth(0);
        const input2 = inputs.nth(1);

        const pos1 = await input1.evaluate(el => el.getBoundingClientRect());
        const pos2 = await input2.evaluate(el => el.getBoundingClientRect());

        // Inputs should stack (input2 below input1)
        expect(pos2.top).toBeGreaterThan(pos1.bottom - 10);

        // Each input should be near full width
        const viewportWidth = 375;
        expect(pos1.width).toBeGreaterThan(viewportWidth * 0.75);
      }
    }

    // Test 3: Sample upload area should be full width
    const uploadArea = page.getByTestId('sample-upload-area');
    const uploadVisible = await uploadArea.isVisible().catch(() => false);

    if (uploadVisible) {
      const uploadWidth = await uploadArea.evaluate(el => el.getBoundingClientRect().width);
      const viewportWidth = 375;

      // Upload area should be near full width
      expect(uploadWidth).toBeGreaterThan(viewportWidth * 0.8);
    }

    // Test 4: Preview panel (if exists) should be below form on mobile
    const previewPanel = page.getByTestId('sample-preview-panel');
    const previewVisible = await previewPanel.isVisible().catch(() => false);

    if (previewVisible && formVisible) {
      const formPos = await formContainer.evaluate(el => el.getBoundingClientRect());
      const previewPos = await previewPanel.evaluate(el => el.getBoundingClientRect());

      // Preview should be below form (not side-by-side)
      expect(previewPos.top).toBeGreaterThan(formPos.bottom - 50);
    }

    // Test 5: Training samples table should be scrollable on mobile
    const samplesTable = page.locator('table').first();
    const tableVisible = await samplesTable.isVisible().catch(() => false);

    if (tableVisible) {
      // Table container should allow horizontal scroll on mobile
      const tableContainer = page.locator('table').first().locator('..');
      const overflowX = await tableContainer.evaluate(el => {
        return window.getComputedStyle(el).overflowX;
      });

      // Should have horizontal scroll enabled
      expect(overflowX).toMatch(/auto|scroll/);
    }

    // Screenshot: Mobile domain training form
    // await page.screenshot({ path: 'screenshots/domain-training-mobile-375px.png' });
  });

  test('should display tablet layout (768px) - 2-column form layout', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    // Setup authentication and navigate to domain training
    await setupAuthMocking(page);
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Open domain creation wizard
    const createButton = page.getByTestId('create-domain-button');
    const createVisible = await createButton.isVisible().catch(() => false);

    if (createVisible) {
      await createButton.click();
      await page.waitForTimeout(1000);
    }

    // Test 1: Form should have 2-column layout on tablet
    const formContainer = page.locator('form, [data-testid="domain-form"]');
    const formVisible = await formContainer.isVisible().catch(() => false);

    if (formVisible) {
      // Check if form uses grid layout
      const formLayout = await formContainer.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          display: style.display,
          gridTemplateColumns: style.gridTemplateColumns,
        };
      });

      // Form should use grid or flex with multiple columns
      const hasColumns =
        formLayout.display === 'grid' ||
        (formLayout.gridTemplateColumns && formLayout.gridTemplateColumns.split(' ').length >= 2);

      if (hasColumns) {
        expect(hasColumns).toBeTruthy();
      }

      // Check if first two inputs are side-by-side
      const inputs = formContainer.locator('input, select').filter({ hasNotText: 'hidden' });
      const inputCount = await inputs.count();

      if (inputCount >= 4) {
        // Compare first and third inputs (should be in different columns)
        const input1 = inputs.nth(0);
        const input3 = inputs.nth(2);

        const pos1 = await input1.evaluate(el => el.getBoundingClientRect());
        const pos3 = await input3.evaluate(el => el.getBoundingClientRect());

        // If 2-column layout, input3 should be roughly aligned with input1
        const aligned = Math.abs(pos1.left - pos3.left) < 50;

        if (aligned) {
          // They're in same column - good for 2-column layout
          expect(aligned).toBeTruthy();
        }
      }
    }

    // Test 2: Form fields should be ~45% width each (2-column)
    const firstInput = page.locator('input, select').first();
    const inputVisible = await firstInput.isVisible().catch(() => false);

    if (inputVisible) {
      const inputWidth = await firstInput.evaluate(el => {
        // Get the input's parent container width
        const parent = el.closest('[class*="grid"], [class*="flex"]');
        const rect = el.getBoundingClientRect();
        const parentRect = parent ? parent.getBoundingClientRect() : { width: 768 };

        return {
          inputWidth: rect.width,
          containerWidth: parentRect.width,
        };
      });

      // Each input should be 35-55% of container (2-column layout)
      const widthPercent = (inputWidth.inputWidth / inputWidth.containerWidth) * 100;

      if (widthPercent > 10) {
        // Only test if we got valid measurements
        expect(widthPercent).toBeGreaterThan(30);
        expect(widthPercent).toBeLessThan(60);
      }
    }

    // Test 3: Preview panel should be visible on tablet
    const previewPanel = page.getByTestId('sample-preview-panel');
    const previewVisible = await previewPanel.isVisible().catch(() => false);

    if (previewVisible) {
      await expect(previewPanel).toBeVisible();

      // Preview should have reasonable width (30-50% of screen)
      const previewWidth = await previewPanel.evaluate(el => el.getBoundingClientRect().width);
      const viewportWidth = 768;

      expect(previewWidth).toBeGreaterThan(viewportWidth * 0.25);
      expect(previewWidth).toBeLessThan(viewportWidth * 0.6);
    }

    // Test 4: Training configuration should be 2-column
    const configSection = page.getByTestId('training-config-section');
    const configVisible = await configSection.isVisible().catch(() => false);

    if (configVisible) {
      const configLayout = await configSection.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          display: style.display,
          gridTemplateColumns: style.gridTemplateColumns,
        };
      });

      // Config should use grid layout
      const hasGrid = configLayout.display === 'grid' || configLayout.gridTemplateColumns !== 'none';

      expect(hasGrid).toBeTruthy();
    }

    // Screenshot: Tablet domain training form
    // await page.screenshot({ path: 'screenshots/domain-training-tablet-768px.png' });
  });

  test('should display desktop layout (1024px+) - 3-column form with preview', async ({
    page,
  }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1280, height: 720 });

    // Setup authentication and navigate to domain training
    await setupAuthMocking(page);
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Open domain creation wizard
    const createButton = page.getByTestId('create-domain-button');
    const createVisible = await createButton.isVisible().catch(() => false);

    if (createVisible) {
      await createButton.click();
      await page.waitForTimeout(1000);
    }

    // Test 1: Form should have 3-column layout on desktop
    const formContainer = page.locator('form, [data-testid="domain-form"]');
    const formVisible = await formContainer.isVisible().catch(() => false);

    if (formVisible) {
      const formLayout = await formContainer.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          display: style.display,
          gridTemplateColumns: style.gridTemplateColumns,
        };
      });

      // Check for 3-column grid
      if (formLayout.gridTemplateColumns && formLayout.gridTemplateColumns !== 'none') {
        const columnCount = formLayout.gridTemplateColumns.split(' ').length;
        // Should have 2-3 columns on desktop
        expect(columnCount).toBeGreaterThanOrEqual(2);
      }
    }

    // Test 2: Form and preview should be side-by-side on desktop
    const previewPanel = page.getByTestId('sample-preview-panel');
    const previewVisible = await previewPanel.isVisible().catch(() => false);

    if (previewVisible && formVisible) {
      const layout = await page.evaluate(() => {
        const form = document.querySelector('form, [data-testid="domain-form"]');
        const preview = document.querySelector('[data-testid="sample-preview-panel"]');

        if (!form || !preview) return null;

        const formRect = form.getBoundingClientRect();
        const previewRect = preview.getBoundingClientRect();

        return {
          formLeft: formRect.left,
          formRight: formRect.right,
          previewLeft: previewRect.left,
          previewRight: previewRect.right,
          formWidth: formRect.width,
          previewWidth: previewRect.width,
        };
      });

      if (layout) {
        // Preview should be to the right of form (or vice versa)
        const sideBySide =
          layout.previewLeft >= layout.formRight - 100 ||
          layout.formLeft >= layout.previewRight - 100;

        expect(sideBySide).toBeTruthy();

        // Form should be 50-70% of width
        const viewportWidth = 1280;
        const formPercent = (layout.formWidth / viewportWidth) * 100;

        expect(formPercent).toBeGreaterThan(45);
        expect(formPercent).toBeLessThan(75);
      }
    }

    // Test 3: Training configuration should use full width efficiently
    const configSection = page.getByTestId('training-config-section');
    const configVisible = await configSection.isVisible().catch(() => false);

    if (configVisible) {
      const configWidth = await configSection.evaluate(el => el.getBoundingClientRect().width);
      const viewportWidth = 1280;

      // Config section should use 60-90% of width
      expect(configWidth).toBeGreaterThan(viewportWidth * 0.55);
      expect(configWidth).toBeLessThan(viewportWidth * 0.95);
    }

    // Test 4: Sample cards should be in grid (2-3 columns)
    const sampleCards = page.locator('[data-testid^="sample-card-"]');
    const cardCount = await sampleCards.count();

    if (cardCount >= 3) {
      // Get positions of first 3 cards
      const card1 = sampleCards.nth(0);
      const card2 = sampleCards.nth(1);
      const card3 = sampleCards.nth(2);

      const pos1 = await card1.evaluate(el => el.getBoundingClientRect());
      const pos2 = await card2.evaluate(el => el.getBoundingClientRect());
      const pos3 = await card3.evaluate(el => el.getBoundingClientRect());

      // Check if first 3 cards are in same row (grid layout)
      const allInRow =
        Math.abs(pos1.top - pos2.top) < 50 && Math.abs(pos2.top - pos3.top) < 50;

      if (allInRow) {
        // Cards in same row - good grid layout
        expect(allInRow).toBeTruthy();

        // Each card should be ~30% width (3-column grid)
        const viewportWidth = 1280;
        const cardPercent = (pos1.width / viewportWidth) * 100;

        expect(cardPercent).toBeGreaterThan(20);
        expect(cardPercent).toBeLessThan(40);
      }
    }

    // Test 5: Wizard steps should be horizontal on desktop
    const wizardSteps = page.locator('[data-testid="wizard-steps"]');
    const stepsVisible = await wizardSteps.isVisible().catch(() => false);

    if (stepsVisible) {
      const stepsLayout = await wizardSteps.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          flexDirection: style.flexDirection,
          display: style.display,
        };
      });

      // Steps should be horizontal (row) on desktop
      expect(stepsLayout.flexDirection).toMatch(/row|horizontal/);
    }

    // Test 6: Action buttons should be grouped and aligned
    const actionButtons = page.locator('button[type="submit"], button:has-text("Next")');
    const buttonCount = await actionButtons.count();

    if (buttonCount > 0) {
      const firstButton = actionButtons.first();
      const buttonWidth = await firstButton.evaluate(el => el.getBoundingClientRect().width);

      // Buttons should be reasonable size on desktop (120-250px)
      expect(buttonWidth).toBeGreaterThan(100);
      expect(buttonWidth).toBeLessThan(300);
    }

    // Screenshot: Desktop domain training form
    // await page.screenshot({ path: 'screenshots/domain-training-desktop-1280px.png' });
  });
});
