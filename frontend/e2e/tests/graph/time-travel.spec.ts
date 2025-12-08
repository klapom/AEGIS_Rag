import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Time Travel Tab - Sprint 39 Feature 39.5
 *
 * Tests:
 * 1. Time Travel tab renders with all controls
 * 2. Date slider updates selected date
 * 3. Date picker input works correctly
 * 4. Quick jump buttons set correct dates
 * 5. Apply button triggers temporal query
 * 6. Entity statistics display correctly
 * 7. Export snapshot downloads JSON file
 * 8. Loading state displays during query
 * 9. Error handling displays error message
 *
 * Backend: POST /api/v1/temporal/point-in-time
 * Required: Backend running on http://localhost:8000
 */

test.describe('Time Travel Tab - Feature 39.5', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to graph page (adjust URL as needed)
    await page.goto('http://localhost:5173/graph');
    await page.waitForLoadState('networkidle');
  });

  test('should render time travel tab with all controls', async ({ page }) => {
    // Click on Time Travel tab
    const timeTravelTab = page.locator('[data-testid="time-travel-tab"]');
    await timeTravelTab.waitFor({ state: 'visible', timeout: 5000 });

    // Check Active badge
    const activeBadge = timeTravelTab.locator('text=Active');
    await expect(activeBadge).toBeVisible();

    // Check time slider
    const timeSlider = page.locator('[data-testid="time-slider"]');
    await expect(timeSlider).toBeVisible();

    // Check date picker
    const datePicker = page.locator('[data-testid="date-picker"]');
    await expect(datePicker).toBeVisible();

    // Check apply button
    const applyButton = page.locator('[data-testid="apply-date-button"]');
    await expect(applyButton).toBeVisible();
    await expect(applyButton).toHaveText('Apply');
  });

  test('should update selected date when slider is moved', async ({ page }) => {
    const timeSlider = page.locator('[data-testid="time-slider"]');
    await timeSlider.waitFor({ state: 'visible' });

    const datePicker = page.locator('[data-testid="date-picker"]');
    const initialDate = await datePicker.inputValue();

    // Move slider (this is tricky with range inputs, so we'll use keyboard)
    await timeSlider.focus();
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('ArrowLeft');

    const newDate = await datePicker.inputValue();
    expect(newDate).not.toBe(initialDate);
  });

  test('should allow manual date selection via date picker', async ({ page }) => {
    const datePicker = page.locator('[data-testid="date-picker"]');
    await datePicker.waitFor({ state: 'visible' });

    // Set a specific date (30 days ago)
    const targetDate = new Date();
    targetDate.setDate(targetDate.getDate() - 30);
    const dateString = targetDate.toISOString().split('T')[0];

    await datePicker.fill(dateString);
    await expect(datePicker).toHaveValue(dateString);
  });

  test('should set correct date when clicking 1 Week Ago button', async ({ page }) => {
    const quickJumpButton = page.locator('[data-testid="quick-jump-1-week"]');
    await quickJumpButton.waitFor({ state: 'visible' });

    await quickJumpButton.click();

    const datePicker = page.locator('[data-testid="date-picker"]');
    const selectedDate = await datePicker.inputValue();

    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    const expectedDate = oneWeekAgo.toISOString().split('T')[0];

    expect(selectedDate).toBe(expectedDate);
  });

  test('should set correct date when clicking 1 Month Ago button', async ({ page }) => {
    const quickJumpButton = page.locator('[data-testid="quick-jump-1-month"]');
    await quickJumpButton.waitFor({ state: 'visible' });

    await quickJumpButton.click();

    const datePicker = page.locator('[data-testid="date-picker"]');
    const selectedDate = await datePicker.inputValue();

    // Verify the date is approximately 30 days ago
    const selectedDateTime = new Date(selectedDate).getTime();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const thirtyDaysAgoTime = thirtyDaysAgo.getTime();

    // Allow 1 day tolerance
    const oneDayMs = 24 * 60 * 60 * 1000;
    expect(Math.abs(selectedDateTime - thirtyDaysAgoTime)).toBeLessThan(oneDayMs);
  });

  test('should trigger temporal query when Apply is clicked', async ({ page }) => {
    // Mock the API response
    await page.route('**/api/v1/temporal/point-in-time', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          entities: [
            {
              id: 'entity1',
              name: 'Test Entity',
              type: 'TECHNOLOGY',
              properties: {},
              valid_from: '2024-01-01T00:00:00Z',
              valid_to: null,
              version_number: 1,
            },
          ],
          as_of: '2024-11-01T00:00:00Z',
          total_count: 1,
          changed_count: 0,
          new_count: 0,
          graphData: {
            nodes: [
              {
                id: 'entity1',
                label: 'Test Entity',
                type: 'TECHNOLOGY',
              },
            ],
            links: [],
          },
        }),
      });
    });

    const applyButton = page.locator('[data-testid="apply-date-button"]');
    await applyButton.click();

    // Wait for loading to finish
    await page.waitForTimeout(1000);

    // Check that statistics are displayed
    const totalCount = page.locator('text=Entities shown:');
    await expect(totalCount).toBeVisible();
  });

  test('should display loading state during query', async ({ page }) => {
    // Mock a slow API response
    await page.route('**/api/v1/temporal/point-in-time', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          entities: [],
          as_of: '2024-11-01T00:00:00Z',
          total_count: 0,
        }),
      });
    });

    const applyButton = page.locator('[data-testid="apply-date-button"]');
    await applyButton.click();

    // Check loading text
    await expect(applyButton).toHaveText('Loading...');
    await expect(applyButton).toBeDisabled();
  });

  test('should display error message on API failure', async ({ page }) => {
    // Mock API error
    await page.route('**/api/v1/temporal/point-in-time', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'text/plain',
        body: 'Internal Server Error',
      });
    });

    const applyButton = page.locator('[data-testid="apply-date-button"]');
    await applyButton.click();

    await page.waitForTimeout(1000);

    // Check for error message
    const errorMessage = page.locator('text=/Error loading temporal data/i');
    await expect(errorMessage).toBeVisible();
  });

  test('should trigger export snapshot download', async ({ page }) => {
    // Mock API response
    await page.route('**/api/v1/temporal/point-in-time', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          entities: [],
          as_of: '2024-11-01T00:00:00Z',
          total_count: 0,
        }),
      });
    });

    const applyButton = page.locator('[data-testid="apply-date-button"]');
    await applyButton.click();
    await page.waitForTimeout(1000);

    // Set up download listener
    const downloadPromise = page.waitForEvent('download');

    const exportButton = page.locator('[data-testid="export-snapshot"]');
    await exportButton.click();

    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/graph-snapshot-.*\.json/);
  });
});
