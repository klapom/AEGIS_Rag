import { test, expect } from '@playwright/test';

test('debug login and navigate to admin tools', async ({ page }) => {
  // Navigate to login page
  await page.goto('/');
  await page.waitForLoadState('networkidle');

  console.log('1. Current URL:', page.url());

  // Wait for login form
  const usernameInput = page.getByPlaceholder('Enter your username');
  await usernameInput.waitFor({ state: 'visible', timeout: 5000 });

  // Fill login form
  await usernameInput.fill('admin');
  const passwordInput = page.getByPlaceholder('Enter your password');
  await passwordInput.fill('admin123');

  // Click Sign In
  const signInButton = page.getByRole('button', { name: 'Sign In' });
  await signInButton.click();

  // Wait for navigation away from login
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });
  await page.waitForLoadState('networkidle');
  console.log('2. After login URL:', page.url());

  // Check localStorage for auth token
  const token = await page.evaluate(() => localStorage.getItem('aegis_auth_token'));
  console.log('2b. Token in localStorage:', token ? token.substring(0, 100) + '...' : 'NULL');

  // Parse and check token structure
  if (token) {
    const parsed = JSON.parse(token);
    console.log('2c. Token keys:', Object.keys(parsed));
    console.log('2d. ExpiresAt:', parsed.expiresAt, 'Now:', Date.now(), 'Valid:', parsed.expiresAt > Date.now());
  }

  // Test 1: page.goto() - full page reload
  await page.goto('/admin');
  await page.waitForLoadState('networkidle');
  console.log('Test 1 (page.goto /admin):', page.url().includes('/login') ? 'REDIRECT' : 'SUCCESS');

  // Go back to home first
  await page.goto('/');
  await page.waitForLoadState('networkidle');

  // Re-login if needed
  if (page.url().includes('/login')) {
    await page.getByPlaceholder('Enter your username').fill('admin');
    await page.getByPlaceholder('Enter your password').fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });
    console.log('Re-logged in');
  }

  // Test 2: Use evaluate to do client-side navigation
  await page.evaluate(() => {
    window.history.pushState({}, '', '/admin');
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
  await page.waitForTimeout(2000);
  console.log('Test 2 (pushState /admin):', page.url());

  // Test 3: Click a link in the sidebar/menu
  // First check if there's an Admin link on the home page
  const adminLink = page.locator('a[href*="/admin"], button:has-text("Admin"), [data-testid*="admin"]').first();
  const hasAdminLink = await adminLink.count() > 0;
  console.log('Test 3: Admin link exists:', hasAdminLink);

  if (hasAdminLink) {
    await adminLink.click();
    await page.waitForTimeout(2000);
    console.log('Test 3 (click link):', page.url());
  }

  await page.screenshot({ path: '/tmp/navigation-test.png' });
});
