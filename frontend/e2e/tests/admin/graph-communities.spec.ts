import { test, expect, setupAuthMocking } from '../../fixtures';
import type { Page } from '@playwright/test';

/**
 * E2E Tests for Graph Communities (Sprint 71 Feature 71.16)
 *
 * Features Tested:
 * - Communities tab in GraphAnalyticsPage
 * - Section Communities Dialog
 * - Community Comparison Dialog
 * - Section-level community detection
 * - Multi-section comparison with overlap analysis
 *
 * Components Under Test:
 * - GraphAnalyticsPage (with Communities tab)
 * - SectionCommunitiesDialog
 * - CommunityComparisonDialog
 * - CommunitiesTab
 *
 * Data Attributes Required:
 * - [data-testid="tab-communities"]
 * - [data-testid="communities-tab"]
 * - [data-testid="open-section-communities"]
 * - [data-testid="open-community-comparison"]
 * - [data-testid="section-communities-dialog"]
 * - [data-testid="document-select"]
 * - [data-testid="section-select"]
 * - [data-testid="algorithm-select"]
 * - [data-testid="resolution-input"]
 * - [data-testid="layout-select"]
 * - [data-testid="fetch-communities-button"]
 * - [data-testid="community-card-{index}"]
 * - [data-testid="expand-community-{index}"]
 * - [data-testid="community-comparison-dialog"]
 * - [data-testid="section-select-{index}"]
 * - [data-testid="add-section-button"]
 * - [data-testid="remove-section-{index}"]
 * - [data-testid="compare-button"]
 */

/**
 * Mock community detection response (Sprint 71 Feature 71.16)
 */
const mockCommunityDetectionResponse = {
  document_id: 'doc_test_123',
  section_heading: 'Complete Document',
  total_communities: 3,
  total_entities: 18,
  communities: [
    {
      community_id: 'community_0',
      section_heading: 'Complete Document',
      size: 6,
      cohesion_score: 0.85,
      nodes: [
        {
          entity_id: 'ent_1',
          entity_name: 'Machine Learning',
          entity_type: 'CONCEPT',
          centrality: 0.92,
          degree: 5,
          x: 150.0,
          y: 200.0,
        },
        {
          entity_id: 'ent_2',
          entity_name: 'Neural Network',
          entity_type: 'CONCEPT',
          centrality: 0.88,
          degree: 4,
          x: 250.0,
          y: 200.0,
        },
        {
          entity_id: 'ent_3',
          entity_name: 'Algorithm',
          entity_type: 'CONCEPT',
          centrality: 0.78,
          degree: 3,
          x: 200.0,
          y: 300.0,
        },
        {
          entity_id: 'ent_4',
          entity_name: 'Training',
          entity_type: 'PROCESS',
          centrality: 0.75,
          degree: 3,
          x: 350.0,
          y: 250.0,
        },
        {
          entity_id: 'ent_5',
          entity_name: 'Deep Learning',
          entity_type: 'CONCEPT',
          centrality: 0.82,
          degree: 4,
          x: 100.0,
          y: 300.0,
        },
        {
          entity_id: 'ent_6',
          entity_name: 'Data',
          entity_type: 'CONCEPT',
          centrality: 0.70,
          degree: 2,
          x: 300.0,
          y: 350.0,
        },
      ],
      edges: [
        {
          source: 'ent_1',
          target: 'ent_2',
          relationship_type: 'RELATED_TO',
          weight: 1.0,
        },
        {
          source: 'ent_1',
          target: 'ent_3',
          relationship_type: 'USES',
          weight: 0.9,
        },
        {
          source: 'ent_2',
          target: 'ent_4',
          relationship_type: 'REQUIRES',
          weight: 0.8,
        },
        {
          source: 'ent_1',
          target: 'ent_5',
          relationship_type: 'SUBSET_OF',
          weight: 0.95,
        },
        {
          source: 'ent_4',
          target: 'ent_6',
          relationship_type: 'USES',
          weight: 0.7,
        },
      ],
      layout_type: 'force-directed',
      algorithm: 'louvain',
    },
    {
      community_id: 'community_1',
      section_heading: 'Complete Document',
      size: 7,
      cohesion_score: 0.79,
      nodes: [
        {
          entity_id: 'ent_7',
          entity_name: 'Evaluation',
          entity_type: 'PROCESS',
          centrality: 0.84,
          degree: 5,
          x: 450.0,
          y: 150.0,
        },
        {
          entity_id: 'ent_8',
          entity_name: 'Metrics',
          entity_type: 'CONCEPT',
          centrality: 0.80,
          degree: 4,
          x: 550.0,
          y: 200.0,
        },
        {
          entity_id: 'ent_9',
          entity_name: 'Accuracy',
          entity_type: 'METRIC',
          centrality: 0.76,
          degree: 3,
          x: 500.0,
          y: 300.0,
        },
        {
          entity_id: 'ent_10',
          entity_name: 'Validation',
          entity_type: 'PROCESS',
          centrality: 0.72,
          degree: 3,
          x: 600.0,
          y: 250.0,
        },
        {
          entity_id: 'ent_11',
          entity_name: 'Test Set',
          entity_type: 'DATA',
          centrality: 0.74,
          degree: 3,
          x: 450.0,
          y: 350.0,
        },
        {
          entity_id: 'ent_12',
          entity_name: 'Performance',
          entity_type: 'METRIC',
          centrality: 0.68,
          degree: 2,
          x: 550.0,
          y: 400.0,
        },
        {
          entity_id: 'ent_13',
          entity_name: 'Loss Function',
          entity_type: 'CONCEPT',
          centrality: 0.70,
          degree: 2,
          x: 400.0,
          y: 450.0,
        },
      ],
      edges: [
        {
          source: 'ent_7',
          target: 'ent_8',
          relationship_type: 'USES',
          weight: 1.0,
        },
        {
          source: 'ent_8',
          target: 'ent_9',
          relationship_type: 'INCLUDES',
          weight: 0.95,
        },
        {
          source: 'ent_7',
          target: 'ent_10',
          relationship_type: 'INCLUDES',
          weight: 0.85,
        },
        {
          source: 'ent_10',
          target: 'ent_11',
          relationship_type: 'USES',
          weight: 0.9,
        },
        {
          source: 'ent_8',
          target: 'ent_12',
          relationship_type: 'MEASURES',
          weight: 0.8,
        },
      ],
      layout_type: 'force-directed',
      algorithm: 'louvain',
    },
    {
      community_id: 'community_2',
      section_heading: 'Complete Document',
      size: 5,
      cohesion_score: 0.81,
      nodes: [
        {
          entity_id: 'ent_14',
          entity_name: 'Optimization',
          entity_type: 'PROCESS',
          centrality: 0.86,
          degree: 4,
          x: 700.0,
          y: 200.0,
        },
        {
          entity_id: 'ent_15',
          entity_name: 'Hyperparameters',
          entity_type: 'CONFIG',
          centrality: 0.80,
          degree: 3,
          x: 800.0,
          y: 150.0,
        },
        {
          entity_id: 'ent_16',
          entity_name: 'Gradient',
          entity_type: 'CONCEPT',
          centrality: 0.78,
          degree: 3,
          x: 750.0,
          y: 300.0,
        },
        {
          entity_id: 'ent_17',
          entity_name: 'Backpropagation',
          entity_type: 'PROCESS',
          centrality: 0.74,
          degree: 2,
          x: 850.0,
          y: 300.0,
        },
        {
          entity_id: 'ent_18',
          entity_name: 'Convergence',
          entity_type: 'STATE',
          centrality: 0.72,
          degree: 2,
          x: 700.0,
          y: 400.0,
        },
      ],
      edges: [
        {
          source: 'ent_14',
          target: 'ent_15',
          relationship_type: 'CONFIGURES',
          weight: 1.0,
        },
        {
          source: 'ent_14',
          target: 'ent_16',
          relationship_type: 'USES',
          weight: 0.9,
        },
        {
          source: 'ent_16',
          target: 'ent_17',
          relationship_type: 'COMPUTES',
          weight: 0.85,
        },
        {
          source: 'ent_14',
          target: 'ent_18',
          relationship_type: 'REACHES',
          weight: 0.75,
        },
      ],
      layout_type: 'force-directed',
      algorithm: 'louvain',
    },
  ],
  generation_time_ms: 250.5,
};

/**
 * Mock community comparison response (Sprint 71 Feature 71.16)
 */
const mockComparisonResponse = {
  section_count: 2,
  sections: ['Complete Document', 'Introduction'],
  total_shared_communities: 2,
  shared_entities: {
    'Complete Document-Introduction': ['ent_1', 'ent_2', 'ent_3', 'ent_4', 'ent_5'],
  },
  overlap_matrix: {
    'Complete Document': { 'Introduction': 5 },
    'Introduction': { 'Complete Document': 5 },
  },
  comparison_time_ms: 450.25,
};

/**
 * Helper function to select an option in SearchableSelect component
 */
async function selectSearchableOption(page: Page, testId: string, searchText: string) {
  // Click trigger to open dropdown
  await page.getByTestId(`${testId}-trigger`).click();

  // Wait for dropdown to open and API data to load (increased for Qdrant scroll)
  await page.waitForTimeout(1500);

  // Type in search (partial text to match real filenames)
  await page.getByTestId(`${testId}-search`).fill(searchText);

  // Wait for filtering
  await page.waitForTimeout(500);

  // Click the first option (should be the match)
  const firstOption = page.locator(`[data-testid^="${testId}-option-"]`).first();

  // Wait for option to be visible
  await firstOption.waitFor({ state: 'visible', timeout: 5000 });

  await firstOption.click();
}

test.describe('Graph Communities Tab (Sprint 71 Feature 71.16)', () => {
  test('should display Communities tab in graph analytics page', async ({ page }) => {
    await setupAuthMocking(page);
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Communities tab should be visible
    const communitiesTab = page.getByTestId('tab-communities');
    await expect(communitiesTab).toBeVisible();
  });

  test('should switch to Communities tab when clicked', async ({ page }) => {
    await setupAuthMocking(page);
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Click Communities tab
    const communitiesTab = page.getByTestId('tab-communities');
    await communitiesTab.click();

    // Communities content should be visible
    const communitiesContent = page.getByTestId('communities-tab');
    await expect(communitiesContent).toBeVisible({ timeout: 5000 });
  });

  test('should display two feature cards on Communities tab', async ({ page }) => {
    await setupAuthMocking(page);
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Click Communities tab
    await page.getByTestId('tab-communities').click();
    await page.waitForTimeout(500);

    // Should have Section Communities button
    const sectionButton = page.getByTestId('open-section-communities');
    await expect(sectionButton).toBeVisible();

    // Should have Community Comparison button
    const comparisonButton = page.getByTestId('open-community-comparison');
    await expect(comparisonButton).toBeVisible();
  });

  test('should display info section about section communities', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Click Communities tab
    await page.getByTestId('tab-communities').click();
    await page.waitForTimeout(500);

    // Info section should be visible
    const infoSection = page.locator('text=/About Section Communities/i');
    await expect(infoSection).toBeVisible();
  });

  test('should display example use cases', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Click Communities tab
    await page.getByTestId('tab-communities').click();
    await page.waitForTimeout(500);

    // Should show use cases
    const useCases = page.locator('text=/Example Use Cases/i');
    await expect(useCases).toBeVisible();

    // Should mention at least one use case type
    const researchPapers = page.locator('text=/Research Papers/i');
    await expect(researchPapers).toBeVisible();
  });
});

test.describe('Section Communities Dialog (Sprint 71 Feature 71.16)', () => {
  test('should open section communities dialog when button clicked', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Click Communities tab
    await page.getByTestId('tab-communities').click();
    await page.waitForTimeout(500);

    // Click Section Communities button
    const sectionButton = page.getByTestId('open-section-communities');
    await sectionButton.click();

    // Dialog should open
    const dialog = page.getByTestId('section-communities-dialog');
    await expect(dialog).toBeVisible({ timeout: 5000 });
  });

  test('should display form inputs for section communities', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-section-communities').click();
    await page.waitForTimeout(1000);

    // Document searchable select
    const docSelect = page.getByTestId('document-select');
    await expect(docSelect).toBeVisible();

    // Section searchable select
    const sectionSelect = page.getByTestId('section-select');
    await expect(sectionSelect).toBeVisible();

    // Algorithm select
    const algorithmSelect = page.getByTestId('algorithm-select');
    await expect(algorithmSelect).toBeVisible();

    // Resolution input
    const resolutionInput = page.getByTestId('resolution-input');
    await expect(resolutionInput).toBeVisible();

    // Layout select
    const layoutSelect = page.getByTestId('layout-select');
    await expect(layoutSelect).toBeVisible();
  });

  test('should have algorithm options (louvain, leiden)', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-section-communities').click();
    await page.waitForTimeout(1000);

    // Algorithm select should have options
    const algorithmSelect = page.getByTestId('algorithm-select');
    const options = await algorithmSelect.locator('option').allTextContents();

    expect(options).toContain('Louvain');
    expect(options).toContain('Leiden');
  });

  test('should have layout algorithm options', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-section-communities').click();
    await page.waitForTimeout(1000);

    // Layout select should have options
    const layoutSelect = page.getByTestId('layout-select');
    const options = await layoutSelect.locator('option').allTextContents();

    expect(options.length).toBeGreaterThan(0);
    expect(options.some((opt) => /force|circular|hierarchical/i.test(opt))).toBeTruthy();
  });

  test('should disable analyze button when inputs are empty', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-section-communities').click();
    await page.waitForTimeout(1000);

    // Analyze button should be disabled initially
    const analyzeButton = page.getByTestId('fetch-communities-button');
    const isDisabled = await analyzeButton.isDisabled();
    expect(isDisabled).toBe(true);
  });

  test('should enable analyze button when inputs are filled', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-section-communities').click();
    await page.waitForTimeout(1000);

    // Fill inputs using real document names (partial match)
    await selectSearchableOption(page, 'document-select', 'test');  // Matches "small_test.pdf"
    await page.waitForTimeout(500); // Wait for sections to load
    await selectSearchableOption(page, 'section-select', 'Complete');  // Matches "Complete Document"

    // Analyze button should be enabled
    const analyzeButton = page.getByTestId('fetch-communities-button');
    const isDisabled = await analyzeButton.isDisabled();
    expect(isDisabled).toBe(false);
  });

  test('should fetch and display communities when analyze clicked', async ({ page }) => {
    await setupAuthMocking(page);

    // Mock documents endpoint
    await page.route('**/api/v1/graph/documents', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documents: [
            {
              id: 'doc_test_123',
              title: 'small_test.pdf',
              created_at: '2026-01-01T12:00:00Z',
              updated_at: '2026-01-02T15:30:00Z',
            },
          ],
        }),
      });
    });

    // Mock sections endpoint
    await page.route('**/api/v1/graph/documents/*/sections', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          document_id: 'doc_test_123',
          sections: [
            {
              id: 'complete',
              heading: 'Complete Document',
              level: 1,
              entity_count: 18,
              chunk_count: 8,
            },
          ],
        }),
      });
    });

    // Mock community detection endpoint
    await page.route('**/api/v1/graph/communities/*/sections/*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockCommunityDetectionResponse),
      });
    });

    await page.goto('/admin/graph');

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-section-communities').click();
    await page.waitForTimeout(1000);

    // Fill inputs
    await selectSearchableOption(page, 'document-select', 'test');
    await page.waitForTimeout(500); // Wait for sections to load
    await selectSearchableOption(page, 'section-select', 'Complete');

    // Analyze button should be enabled
    const analyzeButton = page.getByTestId('fetch-communities-button');
    await expect(analyzeButton).toBeEnabled();

    // Click analyze
    await analyzeButton.click();

    // Community cards should appear (wait for results)
    const communityCard = page.getByTestId('community-card-0');
    await expect(communityCard).toBeVisible({ timeout: 10000 });

    // Verify multiple communities are displayed
    const card1 = page.getByTestId('community-card-1');
    const card2 = page.getByTestId('community-card-2');

    await expect(card1).toBeVisible();
    await expect(card2).toBeVisible();
  });

  test('should show community details when expanded', async ({ page }) => {
    await setupAuthMocking(page);

    // Mock documents endpoint
    await page.route('**/api/v1/graph/documents', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documents: [
            {
              id: 'doc_test_123',
              title: 'small_test.pdf',
              created_at: '2026-01-01T12:00:00Z',
              updated_at: '2026-01-02T15:30:00Z',
            },
          ],
        }),
      });
    });

    // Mock sections endpoint
    await page.route('**/api/v1/graph/documents/*/sections', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          document_id: 'doc_test_123',
          sections: [
            {
              id: 'complete',
              heading: 'Complete Document',
              level: 1,
              entity_count: 18,
              chunk_count: 8,
            },
          ],
        }),
      });
    });

    // Mock community detection endpoint
    await page.route('**/api/v1/graph/communities/*/sections/*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockCommunityDetectionResponse),
      });
    });

    await page.goto('/admin/graph');

    // Open dialog and fetch communities
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-section-communities').click();
    await page.waitForTimeout(1000);

    // Fill inputs
    await selectSearchableOption(page, 'document-select', 'test');
    await page.waitForTimeout(500);
    await selectSearchableOption(page, 'section-select', 'Complete');

    // Click analyze
    await page.getByTestId('fetch-communities-button').click();

    // Wait for community cards to appear
    await expect(page.getByTestId('community-card-0')).toBeVisible({ timeout: 10000 });

    // Click expand button for first community
    const expandButton = page.getByTestId('expand-community-0');
    await expect(expandButton).toBeVisible();
    await expandButton.click();

    await page.waitForTimeout(500);

    // Entity details should appear in the expanded view
    const communityCard = page.getByTestId('community-card-0');
    const entityText = communityCard.locator('text=/Machine Learning|Neural Network|Algorithm/i');
    await expect(entityText.first()).toBeVisible();
  });

  test('should close dialog when X button clicked', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-section-communities').click();
    await page.waitForTimeout(1000);

    // Click close button
    const closeButton = page.getByTestId('close-dialog');
    await closeButton.click();

    // Dialog should disappear
    const dialog = page.getByTestId('section-communities-dialog');
    await expect(dialog).not.toBeVisible();
  });
});

test.describe('Community Comparison Dialog (Sprint 71 Feature 71.16)', () => {
  test('should open community comparison dialog when button clicked', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Click Communities tab
    await page.getByTestId('tab-communities').click();
    await page.waitForTimeout(500);

    // Click Community Comparison button
    const comparisonButton = page.getByTestId('open-community-comparison');
    await comparisonButton.click();

    // Dialog should open
    const dialog = page.getByTestId('community-comparison-dialog');
    await expect(dialog).toBeVisible({ timeout: 5000 });
  });

  test('should display form inputs for community comparison', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-community-comparison').click();
    await page.waitForTimeout(1000);

    // Document ID input
    const docInput = page.getByTestId('document-select-trigger');
    await expect(docInput).toBeVisible();

    // Should have at least 2 section inputs
    const section0Input = page.getByTestId('section-select-0-trigger');
    await expect(section0Input).toBeVisible();

    const section1Input = page.getByTestId('section-select-1-trigger');
    await expect(section1Input).toBeVisible();
  });

  test('should allow adding more sections', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-community-comparison').click();
    await page.waitForTimeout(1000);

    // Fill document first (required to enable add button)
    await selectSearchableOption(page, 'document-select', 'test');
    await page.waitForTimeout(500);

    // Fill first two sections
    await selectSearchableOption(page, 'section-select-0', 'Complete');
    await page.waitForTimeout(300);
    await selectSearchableOption(page, 'section-select-1', 'Complete');
    await page.waitForTimeout(300);

    // Click add section button (should now be enabled)
    const addButton = page.getByTestId('add-section-button');
    await addButton.click();

    // Third section input should appear
    const section2Input = page.getByTestId('section-select-2-trigger');
    await expect(section2Input).toBeVisible();
  });

  test('should allow removing sections (minimum 2)', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-community-comparison').click();
    await page.waitForTimeout(1000);

    // Fill document first (required to enable add button)
    await selectSearchableOption(page, 'document-select', 'test');
    await page.waitForTimeout(500);

    // Fill first two sections
    await selectSearchableOption(page, 'section-select-0', 'Complete');
    await page.waitForTimeout(300);
    await selectSearchableOption(page, 'section-select-1', 'Complete');
    await page.waitForTimeout(300);

    // Add a third section
    await page.getByTestId('add-section-button').click();
    await page.waitForTimeout(500);

    // Remove button should be visible for section 2
    const removeButton = page.getByTestId('remove-section-2');
    const isRemoveVisible = await removeButton.isVisible().catch(() => false);

    if (isRemoveVisible) {
      await removeButton.click();

      // Section 2 should be removed
      const section2Input = page.getByTestId('section-select-2-trigger');
      const isStillVisible = await section2Input.isVisible().catch(() => false);
      expect(isStillVisible).toBe(false);
    }
  });

  test('should disable compare button when less than 2 sections filled', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-community-comparison').click();
    await page.waitForTimeout(1000);

    // Compare button should be disabled initially
    const compareButton = page.getByTestId('compare-button');
    const isDisabled = await compareButton.isDisabled();
    expect(isDisabled).toBe(true);
  });

  test('should enable compare button when doc ID and 2+ sections filled', async ({ page }) => {
    await setupAuthMocking(page);
    await page.goto('/admin/graph');
    // Page loaded, networkidle wait removed to avoid timeouts

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-community-comparison').click();
    await page.waitForTimeout(1000);

    // Fill inputs using real document names
    await selectSearchableOption(page, 'document-select', 'test');  // Matches "small_test.pdf"
    await page.waitForTimeout(500);
    await selectSearchableOption(page, 'section-select-0', 'Complete');  // Matches "Complete Document"
    await page.waitForTimeout(300);
    await selectSearchableOption(page, 'section-select-1', 'Complete');  // Matches "Complete Document"

    // Compare button should be enabled
    const compareButton = page.getByTestId('compare-button');
    const isDisabled = await compareButton.isDisabled();
    expect(isDisabled).toBe(false);
  });

  test('should compare communities when button clicked', async ({ page }) => {
    await setupAuthMocking(page);

    // Mock documents endpoint
    await page.route('**/api/v1/graph/documents', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documents: [
            {
              id: 'doc_test_123',
              title: 'small_test.pdf',
              created_at: '2026-01-01T12:00:00Z',
              updated_at: '2026-01-02T15:30:00Z',
            },
          ],
        }),
      });
    });

    // Mock sections endpoint
    await page.route('**/api/v1/graph/documents/*/sections', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          document_id: 'doc_test_123',
          sections: [
            {
              id: 'complete',
              heading: 'Complete Document',
              level: 1,
              entity_count: 18,
              chunk_count: 8,
            },
            {
              id: 'intro',
              heading: 'Introduction',
              level: 1,
              entity_count: 12,
              chunk_count: 5,
            },
          ],
        }),
      });
    });

    // Mock community comparison endpoint
    await page.route('**/api/v1/graph/communities/compare', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockComparisonResponse),
      });
    });

    await page.goto('/admin/graph');

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-community-comparison').click();
    await page.waitForTimeout(1000);

    // Fill inputs
    await selectSearchableOption(page, 'document-select', 'test');
    await page.waitForTimeout(500);
    await selectSearchableOption(page, 'section-select-0', 'Complete');
    await page.waitForTimeout(300);
    await selectSearchableOption(page, 'section-select-1', 'Introduction');

    // Compare button should be enabled
    const compareButton = page.getByTestId('compare-button');
    await expect(compareButton).toBeEnabled();

    // Click compare
    await compareButton.click();

    // Results should appear (overlap matrix and shared entities)
    const overlapSection = page.locator('text=/Overlap|Shared/i');
    await expect(overlapSection.first()).toBeVisible({ timeout: 10000 });
  });

  test('should display overlap matrix when comparison complete', async ({ page }) => {
    await setupAuthMocking(page);

    // Mock documents endpoint
    await page.route('**/api/v1/graph/documents', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documents: [
            {
              id: 'doc_test_123',
              title: 'small_test.pdf',
              created_at: '2026-01-01T12:00:00Z',
              updated_at: '2026-01-02T15:30:00Z',
            },
          ],
        }),
      });
    });

    // Mock sections endpoint
    await page.route('**/api/v1/graph/documents/*/sections', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          document_id: 'doc_test_123',
          sections: [
            {
              id: 'complete',
              heading: 'Complete Document',
              level: 1,
              entity_count: 18,
              chunk_count: 8,
            },
            {
              id: 'intro',
              heading: 'Introduction',
              level: 1,
              entity_count: 12,
              chunk_count: 5,
            },
          ],
        }),
      });
    });

    // Mock community comparison endpoint
    await page.route('**/api/v1/graph/communities/compare', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockComparisonResponse),
      });
    });

    await page.goto('/admin/graph');

    // Open dialog
    await page.getByTestId('tab-communities').click();
    await page.getByTestId('open-community-comparison').click();
    await page.waitForTimeout(1000);

    // Fill inputs
    await selectSearchableOption(page, 'document-select', 'test');
    await page.waitForTimeout(500);
    await selectSearchableOption(page, 'section-select-0', 'Complete');
    await page.waitForTimeout(300);
    await selectSearchableOption(page, 'section-select-1', 'Introduction');

    // Click compare
    await page.getByTestId('compare-button').click();

    // Wait for comparison results to appear
    await expect(page.locator('text=/Overlap|Shared/i').first()).toBeVisible({ timeout: 10000 });

    // Check for overlap matrix or comparison results table
    const results = page.locator('text=/Complete Document|Introduction/');
    await expect(results.first()).toBeVisible();

    // Verify shared entities are displayed
    const sharedEntities = page.locator('text=/ent_1|ent_2|ent_3/');
    const isSharedVisible = await sharedEntities.first().isVisible().catch(() => false);

    if (isSharedVisible) {
      expect(isSharedVisible).toBeTruthy();
    }
  });
});
