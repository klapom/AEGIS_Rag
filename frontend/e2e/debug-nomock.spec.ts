import { test, expect, navigateClientSide } from './fixtures';

test('navigate without mocks', async ({ page }) => {
  // No beforeEach mocking - just navigate directly
  await navigateClientSide(page, '/admin/tools');
  
  console.log('URL after navigation:', page.url());
  await page.screenshot({ path: '/tmp/nomock.png' });
  
  // Check for the title
  const title = page.locator('h1');
  const titleText = await title.textContent();
  console.log('Page title:', titleText);
});
