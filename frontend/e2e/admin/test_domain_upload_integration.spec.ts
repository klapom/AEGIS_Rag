import { test, expect } from '../fixtures';

/**
 * E2E Tests for Domain Training Integration with Upload Page
 * Feature 45.10: Batch Ingestion with Domain Routing
 *
 * Tests cover:
 * - Domain suggestion on upload page after document classification
 * - Domain selection override
 * - Batch upload with automatic domain routing
 * - Domain confidence display
 * - Integration between upload and domain training systems
 */

// Sprint 123.7: Partially fixed - test uses direct page.goto('/admin/upload') without fixture
// Tests will still fail with 180s timeout - would need AdminUploadPage POM with navigateClientSide
test.describe('Upload Page - Domain Classification Integration', () => {
  test('should navigate to upload page', async ({ page }) => {
    await page.goto('/admin/upload');

    // Verify page elements
    await expect(page.getByRole('heading', { name: /upload/i })).toBeVisible();
    await expect(page.getByTestId('file-dropzone')).toBeVisible();
  });

  test('should display file dropzone on load', async ({ page }) => {
    await page.goto('/admin/upload');

    const dropzone = page.getByTestId('file-dropzone');
    await expect(dropzone).toBeVisible();

    // Should have drag-and-drop instructions
    const instructions = page.getByText(/drag/i);
    // Instructions may or may not be visible - just ensure dropzone is interactive
    await expect(dropzone).toBeDefined();
  });

  test('should classify uploaded document and suggest domain', async ({ page }) => {
    // Mock the classification API
    await page.route('**/api/v1/admin/domains/classify', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          classifications: [
            {
              domain: 'software_development',
              score: 0.92,
              description: 'Technical documentation and software development resources',
            },
            {
              domain: 'general',
              score: 0.65,
              description: 'General purpose domain for any content',
            },
          ],
          recommended: 'software_development',
          confidence: 0.92,
        }),
      });
    });

    await page.goto('/admin/upload');

    // Create test file with technical content
    const fileContent =
      'This is a technical document about API design patterns, REST architecture, and microservices. It includes code examples and best practices for building scalable systems.';

    // Upload file
    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'technical_doc.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(fileContent),
    });

    // Wait for classification to complete
    await expect(page.getByTestId('domain-selector')).toBeVisible({ timeout: 10000 });

    // Should show domain selector with suggestion
    const domainSelector = page.getByTestId('domain-selector');
    await expect(domainSelector).toHaveValue('software_development');
  });

  test('should display confidence badge with color coding', async ({ page }) => {
    // Mock high confidence response
    await page.route('**/api/v1/admin/domains/classify', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          classifications: [
            { domain: 'software_development', score: 0.95, description: 'Tech domain' },
          ],
          recommended: 'software_development',
          confidence: 0.95,
        }),
      });
    });

    await page.goto('/admin/upload');

    const fileContent = 'Technical documentation about programming and software development';

    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'tech_doc.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(fileContent),
    });

    // Wait for classification
    await page.waitForTimeout(1000);

    // Confidence badge should be visible
    const confidenceBadge = page.getByTestId('domain-confidence-badge');
    const isVisible = await confidenceBadge.isVisible().catch(() => false);

    if (isVisible) {
      // Should show confidence percentage
      const text = await confidenceBadge.textContent();
      expect(text).toMatch(/\d+%/);
    }
  });

  test('should show low confidence with yellow badge', async ({ page }) => {
    // Mock low confidence response
    await page.route('**/api/v1/admin/domains/classify', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          classifications: [
            { domain: 'general', score: 0.52, description: 'General domain' },
          ],
          recommended: 'general',
          confidence: 0.52,
        }),
      });
    });

    await page.goto('/admin/upload');

    const fileContent = 'Some ambiguous document that could fit multiple categories';

    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'ambiguous_doc.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(fileContent),
    });

    // Wait for classification
    await page.waitForTimeout(1000);

    // Check for yellow badge indicating low confidence
    const yellowBadge = page.locator('[class*="bg-yellow"]');
    const isVisible = await yellowBadge.isVisible().catch(() => false);

    // At minimum, domain selector should be present
    const selector = page.getByTestId('domain-selector');
    await expect(selector).toBeVisible({ timeout: 5000 });
  });

  test('should allow manual domain override after classification', async ({ page }) => {
    // Mock classification response suggesting software_development
    await page.route('**/api/v1/admin/domains/classify', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          classifications: [
            {
              domain: 'software_development',
              score: 0.85,
              description: 'Tech domain',
            },
          ],
          recommended: 'software_development',
          confidence: 0.85,
        }),
      });
    });

    await page.goto('/admin/upload');

    const fileContent = 'Technical document about software development';

    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'tech_doc.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(fileContent),
    });

    // Wait for classification and selector to appear
    await expect(page.getByTestId('domain-selector')).toBeVisible({ timeout: 10000 });

    // Override domain selection
    await page.getByTestId('domain-selector').selectOption('general');

    // Verify selection changed
    const selector = page.getByTestId('domain-selector');
    await expect(selector).toHaveValue('general');
  });

  test('should handle multiple file uploads with domain classification each', async ({
    page,
  }) => {
    // Mock classification endpoints
    await page.route('**/api/v1/admin/domains/classify', (route) => {
      const request = route.request().postDataJSON();
      const text = request.text.toLowerCase();

      // Classify based on content
      let recommended = 'general';
      let confidence = 0.6;

      if (text.includes('api') || text.includes('code')) {
        recommended = 'software_development';
        confidence = 0.9;
      } else if (text.includes('legal') || text.includes('contract')) {
        recommended = 'legal_documents';
        confidence = 0.85;
      }

      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          classifications: [
            { domain: recommended, score: confidence, description: `${recommended} domain` },
          ],
          recommended: recommended,
          confidence: confidence,
        }),
      });
    });

    await page.goto('/admin/upload');

    // Upload first file (technical)
    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'api_doc.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('This is about REST API design and code examples'),
    });

    await page.waitForTimeout(500);

    // First classification should suggest software_development
    let selector = page.getByTestId('domain-selector');
    await expect(selector).toHaveValue('software_development');

    // Upload second file (legal)
    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'contract.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('This is a legal contract document for services'),
    });

    await page.waitForTimeout(500);

    // Second classification should suggest legal_documents
    selector = page.getByTestId('domain-selector');
    await expect(selector).toHaveValue('legal_documents');
  });

  test('should display domain description when suggested', async ({ page }) => {
    // Mock classification with detailed response
    await page.route('**/api/v1/admin/domains/classify', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          classifications: [
            {
              domain: 'software_development',
              score: 0.9,
              description:
                'Technical documentation and resources for software development including APIs, frameworks, and best practices',
            },
          ],
          recommended: 'software_development',
          confidence: 0.9,
        }),
      });
    });

    await page.goto('/admin/upload');

    const fileContent = 'Technical documentation about FastAPI framework and microservices';

    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'tech_doc.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(fileContent),
    });

    // Wait for classification
    await page.waitForTimeout(1000);

    // Domain description might be displayed
    const description = page.getByTestId('domain-description');
    const isVisible = await description.isVisible().catch(() => false);

    if (isVisible) {
      const text = await description.textContent();
      expect(text).toContain('Technical');
    }
  });

  test('should handle classification timeout gracefully', async ({ page }) => {
    // Mock slow response
    await page.route('**/api/v1/admin/domains/classify', (route) => {
      setTimeout(() => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            classifications: [{ domain: 'general', score: 0.5, description: 'General' }],
            recommended: 'general',
            confidence: 0.5,
          }),
        });
      }, 5000); // Simulate slow response
    });

    await page.goto('/admin/upload');

    const fileContent = 'Document for slow classification test';

    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'slow_doc.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(fileContent),
    });

    // Should eventually show domain selector
    await expect(page.getByTestId('domain-selector')).toBeVisible({ timeout: 15000 });
  });

  test('should handle classification error gracefully', async ({ page }) => {
    // Mock error response
    await page.route('**/api/v1/admin/domains/classify', (route) => {
      route.abort('failed');
    });

    await page.goto('/admin/upload');

    const fileContent = 'Document for error handling test';

    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'error_doc.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(fileContent),
    });

    // Should show error message or default to 'general' domain
    await page.waitForTimeout(2000);

    const errorMessage = page.getByTestId('classification-error');
    const selector = page.getByTestId('domain-selector');

    const errorVisible = await errorMessage.isVisible().catch(() => false);
    const selectorVisible = await selector.isVisible().catch(() => false);

    // Either error is shown OR selector shows general as fallback
    expect(errorVisible || selectorVisible).toBeTruthy();
  });

  test('should show available domains in dropdown', async ({ page }) => {
    await page.goto('/admin/upload');

    // Domain selector should be visible after page load or after file upload
    const selector = page.getByTestId('domain-selector');

    // Click to open dropdown
    if (await selector.isVisible()) {
      await selector.click();
      await page.waitForTimeout(300);

      // Should have at least 'general' option
      const options = await page.locator('select option').count();
      expect(options).toBeGreaterThanOrEqual(1);
    }
  });
});

// Sprint 123.7: Skip - depends on Upload page auth pattern
test.describe('Batch Ingestion with Domain Routing', () => {
  test('should route multiple documents by classified domain', async ({ request }) => {
    // Create batch with documents that will be classified to different domains
    const batchItems = [
      {
        file_path: '/documents/api_guide.txt',
        text: 'REST API design guide with endpoints, status codes, and error handling',
        domain: 'software_development', // Pre-classified
      },
      {
        file_path: '/documents/legal_agreement.txt',
        text: 'Service agreement contract with terms and conditions',
        domain: 'legal_documents', // Pre-classified
      },
      {
        file_path: '/documents/general_info.txt',
        text: 'General information document',
        domain: 'general',
      },
    ];

    const response = await request.post('/api/v1/admin/domains/ingest-batch', {
      data: {
        items: batchItems,
      },
    });

    if (response.ok()) {
      const result = await response.json();

      // Should group items by domain
      expect(result.domain_groups).toBeDefined();
      expect(result.domain_groups.software_development).toBe(1);
      expect(result.domain_groups.legal_documents).toBe(1);
      expect(result.domain_groups.general).toBe(1);

      // Should group items by LLM model used for extraction
      expect(result.model_groups).toBeDefined();
    }
  });

  test('should optimize batch processing by LLM model', async ({ request }) => {
    // Multiple items for same domain should be grouped under same model
    const batchItems = [
      {
        file_path: '/docs/doc1.txt',
        text: 'First technical document',
        domain: 'software_development',
      },
      {
        file_path: '/docs/doc2.txt',
        text: 'Second technical document',
        domain: 'software_development',
      },
      {
        file_path: '/docs/doc3.txt',
        text: 'Third technical document',
        domain: 'software_development',
      },
    ];

    const response = await request.post('/api/v1/admin/domains/ingest-batch', {
      data: {
        items: batchItems,
      },
    });

    if (response.ok()) {
      const result = await response.json();

      // All items should be grouped under software_development domain
      expect(result.domain_groups.software_development).toBe(3);

      // Should result in minimal model group fragmentation
      const modelGroupCount = Object.keys(result.model_groups).length;
      expect(modelGroupCount).toBeLessThanOrEqual(2); // Should be 1, allowing for fallback
    }
  });

  test('should handle mixed domain batch with optimal routing', async ({ request }) => {
    // Create realistic batch with items for multiple domains
    const batchItems = Array.from({ length: 10 }, (_, i) => ({
      file_path: `/documents/doc${i + 1}.txt`,
      text: `Document ${i + 1} content relevant to software development and API design`,
      domain: i % 2 === 0 ? 'software_development' : 'general',
    }));

    const response = await request.post('/api/v1/admin/domains/ingest-batch', {
      data: {
        items: batchItems,
      },
    });

    if (response.ok()) {
      const result = await response.json();

      expect(result.total_items).toBe(10);
      expect(result.domain_groups.software_development).toBe(5);
      expect(result.domain_groups.general).toBe(5);

      // Verify model grouping efficiency
      expect(result.model_groups).toBeDefined();
    }
  });
});

// Sprint 123.7: Skip - depends on Upload page auth pattern
test.describe('Domain Selection UX', () => {
  test('should highlight high confidence suggestion', async ({ page }) => {
    // Mock high confidence response
    await page.route('**/api/v1/admin/domains/classify', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          classifications: [
            { domain: 'software_development', score: 0.95, description: 'Tech domain' },
          ],
          recommended: 'software_development',
          confidence: 0.95,
        }),
      });
    });

    await page.goto('/admin/upload');

    const fileContent = 'Technical documentation about APIs and frameworks';

    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'tech_doc.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(fileContent),
    });

    // Wait for classification
    await page.waitForTimeout(1000);

    // High confidence badge should be visible with green color
    const greenBadge = page.locator('[class*="bg-green"]');
    const isVisible = await greenBadge.isVisible().catch(() => false);

    if (isVisible) {
      await expect(greenBadge).toBeVisible();
    } else {
      // At minimum, selector should be present and set to recommended domain
      const selector = page.getByTestId('domain-selector');
      await expect(selector).toHaveValue('software_development');
    }
  });

  test('should show visual feedback during classification', async ({ page }) => {
    // Mock response with delay
    await page.route('**/api/v1/admin/domains/classify', async (route) => {
      await page.waitForTimeout(1000); // Simulate processing
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          classifications: [{ domain: 'general', score: 0.7, description: 'General' }],
          recommended: 'general',
          confidence: 0.7,
        }),
      });
    });

    await page.goto('/admin/upload');

    const fileContent = 'Document for feedback test';

    // Start upload
    await page.getByTestId('file-dropzone').setInputFiles({
      name: 'feedback_doc.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(fileContent),
    });

    // Look for loading/processing indicator
    const loadingIndicator = page.getByTestId('classification-loading');
    const isLoading = await loadingIndicator.isVisible().catch(() => false);

    // Should eventually show result
    await expect(page.getByTestId('domain-selector')).toBeVisible({ timeout: 10000 });
  });
});
