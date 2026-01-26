import { test, expect } from '@playwright/test';

test('Bash execution UI is accessible', async ({ page }) => {
  await page.goto('http://192.168.178.10/admin/tools');
  await page.waitForLoadState('networkidle');
  
  // Click on Bash tab
  const bashTab = page.locator('[data-testid="tab-bash"]');
  await expect(bashTab).toBeVisible({ timeout: 5000 });
  await bashTab.click();
  
  // Check for bash execution panel elements
  await expect(page.locator('[data-testid="bash-input"]')).toBeVisible({ timeout: 5000 });
  await expect(page.locator('[data-testid="bash-execute-button"]')).toBeVisible();
  
  // Type a command
  await page.locator('[data-testid="bash-input"]').fill('echo "test"');
  
  // Click execute button (will show approval dialog)
  await page.locator('[data-testid="bash-execute-button"]').click();
  
  // Check for approval dialog
  await expect(page.locator('[data-testid="bash-approval-dialog"]')).toBeVisible({ timeout: 3000 });
  
  console.log('✓ All bash execution UI elements found!');
});
