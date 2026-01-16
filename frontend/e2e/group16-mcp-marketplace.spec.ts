/**
 * E2E Tests for MCP Marketplace
 * Sprint 107 Feature 107.3: Test server browsing, search, and installation
 *
 * Test Group 16: MCP Server Marketplace (6 tests)
 */

import { test, expect, Page, setupAuthMocking } from './fixtures';

// Test data
const mockServers = {
  registry: 'https://mock-registry.com/servers.json',
  count: 5,
  servers: [
    {
      id: '@modelcontextprotocol/server-filesystem',
      name: 'Filesystem Server',
      description: 'Read and write files and directories',
      transport: 'stdio',
      command: 'npx',
      args: ['@modelcontextprotocol/server-filesystem'],
      version: '1.0.2',
      stars: 1250,
      downloads: 15000,
      tags: ['filesystem', 'files', 'io'],
      repository: 'https://github.com/modelcontextprotocol/servers',
    },
    {
      id: '@modelcontextprotocol/server-github',
      name: 'GitHub Server',
      description: 'Interact with GitHub repositories',
      transport: 'stdio',
      command: 'npx',
      args: ['@modelcontextprotocol/server-github'],
      dependencies: {
        npm: ['@modelcontextprotocol/server-github@^1.0.0'],
        env: ['GITHUB_TOKEN'],
      },
      version: '1.0.1',
      stars: 980,
      downloads: 8500,
      tags: ['github', 'git', 'vcs'],
      repository: 'https://github.com/modelcontextprotocol/servers',
    },
  ],
};

// Helper function to setup API mocks
async function setupApiMocks(page: Page) {
  // Mock registry servers endpoint
  await page.route('**/api/v1/mcp/registry/servers*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockServers),
    });
  });

  // Mock install endpoint
  await page.route('**/api/v1/mcp/registry/install', async (route) => {
    const request = route.request();
    const postData = request.postDataJSON();

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'installed',
        message: `Server ${postData.server_id} installed successfully`,
        server: mockServers.servers.find((s) => s.id === postData.server_id),
        auto_connect: postData.auto_connect || false,
      }),
    });
  });

  // Mock reload config endpoint
  await page.route('**/api/v1/mcp/reload-config*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        servers_before: 3,
        servers_after: 4,
        connected: 2,
        connection_results: {},
      }),
    });
  });
}

test.describe('Group 16: MCP Marketplace', () => {
  test.beforeEach(async ({ page }) => {
    // Setup API mocks FIRST (before navigation)
    await setupApiMocks(page);
  });

  test('16.1: should display marketplace page with server browser', async ({ page }) => {
    // Navigate and perform real login
    await setupAuthMocking(page);

    await page.goto('/admin/mcp-marketplace');
    await page.waitForLoadState('networkidle');

    // Check page title and subtitle
    await expect(page.getByTestId('page-title')).toHaveText('MCP Server Marketplace');
    await expect(page.getByTestId('page-subtitle')).toContainText(
      'Browse and install MCP servers'
    );

    // Check server browser is visible
    await expect(page.getByTestId('mcp-server-browser')).toBeVisible();

    // Check search input
    await expect(page.getByTestId('search-input')).toBeVisible();
    await expect(page.getByTestId('search-input')).toHaveAttribute(
      'placeholder',
      /Search servers/i
    );

    // Check server count
    await expect(page.getByTestId('server-count')).toContainText('5 servers found');

    // Check reload config button
    await expect(page.getByTestId('reload-config-button')).toBeVisible();
    await expect(page.getByTestId('reload-config-button')).toContainText('Connect Servers');
  });

  test('16.2: should display server cards with correct information', async ({ page }) => {
    await page.goto('/admin/mcp-marketplace');

    // Wait for servers to load
    await expect(page.getByTestId('server-count')).toContainText('5 servers found');

    // Check first server card
    const firstCard = page.getByTestId(
      'server-card-@modelcontextprotocol/server-filesystem'
    );
    await expect(firstCard).toBeVisible();

    // Check server name
    const serverName = firstCard.getByTestId('server-name');
    await expect(serverName).toHaveText('Filesystem Server');

    // Check server ID
    const serverId = firstCard.getByTestId('server-id');
    await expect(serverId).toHaveText('@modelcontextprotocol/server-filesystem');

    // Check transport badge
    const transport = firstCard.getByTestId('server-transport');
    await expect(transport).toHaveText('stdio');

    // Check description
    const description = firstCard.getByTestId('server-description');
    await expect(description).toContainText('Read and write files');

    // Check stats
    const stars = firstCard.getByTestId('server-stars');
    await expect(stars).toContainText('1,250');

    const downloads = firstCard.getByTestId('server-downloads');
    await expect(downloads).toContainText('15,000');

    const version = firstCard.getByTestId('server-version');
    await expect(version).toContainText('v1.0.2');

    // Check tags
    const tags = firstCard.getByTestId('server-tags');
    await expect(tags).toContainText('filesystem');
    await expect(tags).toContainText('files');

    // Check install button
    await expect(firstCard.getByTestId('install-button')).toBeVisible();
    await expect(firstCard.getByTestId('install-button')).toHaveText('Install');

    // Check repository link
    await expect(firstCard.getByTestId('repository-link')).toBeVisible();
  });

  test('16.3: should search servers by name and tags', async ({ page }) => {
    await page.goto('/admin/mcp-marketplace');

    // Wait for initial load
    await expect(page.getByTestId('server-count')).toContainText('5 servers found');

    // Search by name
    const searchInput = page.getByTestId('search-input');
    await searchInput.fill('filesystem');

    // Should show only filesystem server
    await expect(page.getByTestId('server-count')).toContainText('1 server found');
    await expect(
      page.getByTestId('server-card-@modelcontextprotocol/server-filesystem')
    ).toBeVisible();

    // Clear search
    await searchInput.clear();
    await expect(page.getByTestId('server-count')).toContainText('5 servers found');

    // Search by tag
    await searchInput.fill('github');
    await expect(page.getByTestId('server-count')).toContainText('1 server found');
    await expect(
      page.getByTestId('server-card-@modelcontextprotocol/server-github')
    ).toBeVisible();

    // Search with no results
    await searchInput.fill('nonexistent');
    await expect(page.getByTestId('server-count')).toContainText('0 servers found');
    await expect(page.getByTestId('empty-state')).toBeVisible();
    await expect(page.getByTestId('empty-state')).toContainText('No servers found');
  });

  test('16.4: should open installer dialog when clicking server card', async ({ page }) => {
    await page.goto('/admin/mcp-marketplace');

    // Click on first server card
    const firstCard = page.getByTestId(
      'server-card-@modelcontextprotocol/server-filesystem'
    );
    await firstCard.click();

    // Check installer dialog is open
    await expect(page.getByTestId('installer-dialog')).toBeVisible();
    await expect(page.getByTestId('dialog-title')).toHaveText('Install MCP Server');

    // Check server info in dialog
    await expect(page.getByTestId('server-name')).toHaveText('Filesystem Server');
    await expect(page.getByTestId('server-id')).toHaveText(
      '@modelcontextprotocol/server-filesystem'
    );
    await expect(page.getByTestId('server-description')).toContainText(
      'Read and write files'
    );

    // Check auto-connect checkbox
    await expect(page.getByTestId('auto-connect-option')).toBeVisible();
    const autoConnectCheckbox = page.locator('#auto-connect');
    await expect(autoConnectCheckbox).toBeChecked(); // Should be checked by default

    // Check install button
    await expect(page.getByTestId('install-button')).toBeVisible();
    await expect(page.getByTestId('install-button')).toHaveText('Install');

    // Check cancel button
    await expect(page.getByTestId('cancel-button')).toBeVisible();
    await expect(page.getByTestId('cancel-button')).toHaveText('Cancel');

    // Close dialog
    await page.getByTestId('close-button').click();
    await expect(page.getByTestId('installer-dialog')).not.toBeVisible();
  });

  test('16.5: should show dependencies in installer dialog', async ({ page }) => {
    await page.goto('/admin/mcp-marketplace');

    // Click on GitHub server (has dependencies)
    const githubCard = page.getByTestId('server-card-@modelcontextprotocol/server-github');
    await githubCard.click();

    // Check installer dialog
    await expect(page.getByTestId('installer-dialog')).toBeVisible();

    // Check dependencies section
    await expect(page.getByTestId('dependencies-section')).toBeVisible();

    // Check npm dependencies
    await expect(page.getByTestId('npm-dependencies')).toBeVisible();
    await expect(page.getByTestId('npm-dependencies')).toContainText(
      '@modelcontextprotocol/server-github@^1.0.0'
    );

    // Check environment variables
    await expect(page.getByTestId('env-dependencies')).toBeVisible();
    await expect(page.getByTestId('env-dependencies')).toContainText('GITHUB_TOKEN');
  });

  test('16.6: should install server and show success message', async ({ page }) => {
    await page.goto('/admin/mcp-marketplace');

    // Click on first server card
    const firstCard = page.getByTestId(
      'server-card-@modelcontextprotocol/server-filesystem'
    );
    await firstCard.click();

    // Check auto-connect is checked
    const autoConnectCheckbox = page.locator('#auto-connect');
    await expect(autoConnectCheckbox).toBeChecked();

    // Click install
    await page.getByTestId('install-button').click();

    // Check installing status
    await expect(page.getByTestId('installing-status')).toBeVisible();
    await expect(page.getByTestId('installing-status')).toContainText('Installing server');

    // Wait for success
    await expect(page.getByTestId('success-status')).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('success-status')).toContainText('Installation successful');
    await expect(page.getByTestId('success-status')).toContainText(
      'Tools will be available after connection'
    );

    // Dialog should close automatically after 2 seconds
    await expect(page.getByTestId('installer-dialog')).not.toBeVisible({ timeout: 3000 });
  });
});
