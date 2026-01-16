import { test, expect } from '@playwright/test';

test('direct navigation to admin tools', async ({ page }) => {
  // Go directly to admin/tools
  await page.goto('/admin/tools');
  await page.waitForLoadState('networkidle');
  
  console.log('1. URL after goto:', page.url());
  await page.screenshot({ path: '/tmp/step1.png' });
  
  // If on login, login
  if (page.url().includes('/login')) {
    console.log('2. On login page, logging in...');
    await page.getByPlaceholder('Enter your username').fill('admin');
    await page.getByPlaceholder('Enter your password').fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });
    console.log('3. After login URL:', page.url());
    await page.screenshot({ path: '/tmp/step2-after-login.png' });
  }
  
  // Now try to navigate to admin/tools via sidebar click
  console.log('4. Looking for admin/settings links...');
  
  // First find what links are available
  const links = await page.locator('a').evaluateAll(els => 
    els.map(el => ({ href: el.getAttribute('href'), text: el.textContent?.trim() }))
  );
  console.log('5. Available links:', JSON.stringify(links.filter(l => l.href?.includes('admin')), null, 2));
  
  await page.screenshot({ path: '/tmp/step3-home.png' });
});
