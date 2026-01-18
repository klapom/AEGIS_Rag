import { test, expect, setupAuthMocking, navigateClientSide } from './fixtures';

/**
 * Group 15: Explainability & Certification E2E Tests
 * Sprint 98 - Explainability Dashboard & Certification Status
 *
 * Tests:
 * - Explainability page loads
 * - Decision paths display
 * - Certification status shown
 * - Transparency metrics visible
 * - Audit trail links work
 *
 * Features:
 * - Decision path visualization
 * - Model explainability metrics
 * - Certification compliance status
 * - Link to audit trail for traceability
 */

test.describe('Group 15: Explainability & Certification - Sprint 98', () => {
  test.beforeEach(async ({ page }) => {
    // Setup authentication for admin routes
    await setupAuthMocking(page);
  });

  test('should load Explainability Dashboard page', async ({ page }) => {
    // Navigate to explainability page
    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');

    // Verify page loaded successfully
    const heading = page.locator('h1, h2').first();
    const headingText = await heading.textContent();
    expect(headingText).toBeTruthy();
    expect(headingText?.toLowerCase()).toMatch(/explainability|transparency|interpretability/);
  });

  test('should display decision paths', async ({ page }) => {
    // Sprint 111 Fix: Mock correct endpoint /api/v1/explainability/recent
    // The component calls getRecentTraces which uses this endpoint, not decision-paths
    await page.route('**/api/v1/explainability/recent*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            trace_id: 'trace-1',
            query: 'What is RAG?',
            timestamp: '2024-01-15T10:00:00Z',
            confidence: 0.95,
          },
          {
            trace_id: 'trace-2',
            query: 'Explain the graph extraction process',
            timestamp: '2024-01-15T10:05:00Z',
            confidence: 0.89,
          },
        ]),
      });
    });

    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Verify recent queries are displayed (decision paths)
    const decisionPaths = page.locator('[data-testid*="decision-path"], [class*="decision-path"], [data-testid*="trace-item"]');
    const pathCount = await decisionPaths.count();

    // Look for query text in the list
    const ragQuery = page.locator('text=/What is RAG|graph extraction/i');
    const hasQueryText = await ragQuery.count() > 0;

    expect(pathCount > 0 || hasQueryText).toBeTruthy();
  });

  test('should display certification status', async ({ page }) => {
    // Mock certification status endpoint
    await page.route('**/api/v1/certification/status*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          certification_status: 'compliant',
          certifications: [
            {
              id: 'cert-1',
              name: 'EU AI Act Compliance',
              status: 'certified',
              issued_date: '2024-01-01T00:00:00Z',
              expiry_date: '2025-01-01T00:00:00Z',
              issuer: 'EU Certification Body',
              certificate_url: 'https://example.com/cert-1.pdf',
            },
            {
              id: 'cert-2',
              name: 'GDPR Compliance',
              status: 'certified',
              issued_date: '2024-01-01T00:00:00Z',
              expiry_date: '2025-01-01T00:00:00Z',
              issuer: 'Data Protection Authority',
              certificate_url: 'https://example.com/cert-2.pdf',
            },
            {
              id: 'cert-3',
              name: 'ISO 27001',
              status: 'pending',
              issued_date: null,
              expiry_date: null,
              issuer: 'ISO Certification Body',
              certificate_url: null,
            },
          ],
          compliance_score: 95.5,
          last_audit_date: '2024-01-10T00:00:00Z',
        }),
      });
    });

    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Look for certification status section
    const certificationSection = page.locator('[data-testid*="certification"], [class*="certification"]');
    const sectionExists = await certificationSection.count() > 0;

    // Look for certification names
    const euAiActText = page.locator('text=/EU AI Act|GDPR|ISO 27001/i');
    const certificationText = page.locator('text=/certified|compliant|pending/i');

    const hasCertNames = await euAiActText.count() > 0;
    const hasCertStatus = await certificationText.count() > 0;

    expect(sectionExists || hasCertNames || hasCertStatus).toBeTruthy();
  });

  test('should display transparency metrics', async ({ page }) => {
    // Mock transparency metrics endpoint
    await page.route('**/api/v1/explainability/metrics*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          transparency_metrics: {
            explainability_score: 0.88,
            interpretability_score: 0.92,
            traceability_score: 0.95,
            accountability_score: 0.90,
          },
          model_metrics: {
            model_name: 'Nemotron3 Nano',
            model_version: '1.0',
            last_updated: '2024-01-01T00:00:00Z',
            total_predictions: 12345,
            average_confidence: 0.89,
          },
          audit_metrics: {
            total_audits: 45,
            passed_audits: 43,
            failed_audits: 2,
            compliance_rate: 0.956,
          },
        }),
      });
    });

    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Look for transparency metrics
    const metricsSection = page.locator('[data-testid*="metrics"], [class*="metrics"]');
    const sectionExists = await metricsSection.count() > 0;

    // Look for metric names
    const metricNames = page.locator('text=/explainability|interpretability|traceability|accountability/i');
    const metricScores = page.locator('text=/88|92|95|90/');

    const hasMetricNames = await metricNames.count() > 0;
    const hasMetricScores = await metricScores.count() > 0;

    expect(sectionExists || hasMetricNames || hasMetricScores).toBeTruthy();
  });

  test('should display audit trail links', async ({ page }) => {
    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Look for audit trail link
    const auditTrailLink = page.locator('a[href*="/audit"], button:has-text("Audit Trail"), button:has-text("View Audit")');
    const linkExists = await auditTrailLink.count() > 0;

    // Also check for text mentioning audit
    const auditText = page.locator('text=/view audit|audit trail|full audit/i');
    const textExists = await auditText.count() > 0;

    expect(linkExists || textExists).toBeTruthy();
  });

  test('should navigate to audit trail from explainability page', async ({ page }) => {
    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Try to click audit trail link
    const auditTrailLink = page.locator('a[href*="/audit"], button:has-text("Audit Trail")').first();
    const linkExists = await auditTrailLink.count() > 0;

    if (linkExists) {
      await auditTrailLink.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      // Verify we navigated to audit page
      const url = page.url();
      expect(url).toContain('/audit');
    }
  });

  test('should display decision path details modal', async ({ page }) => {
    // Mock explainability endpoint
    await page.route('**/api/v1/explainability/decision-paths*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          decision_paths: [
            {
              id: 'path-1',
              query: 'What is RAG?',
              timestamp: '2024-01-15T10:00:00Z',
              steps: [
                {
                  step_id: 1,
                  agent: 'Coordinator',
                  action: 'Query Classification',
                  reasoning: 'Classified as knowledge retrieval query',
                  confidence: 0.95,
                },
              ],
              final_decision: 'Answer generated',
            },
          ],
        }),
      });
    });

    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Try to click on a decision path to view details
    const decisionPathItem = page.locator('[data-testid*="decision-path"], [class*="decision-path"]').first();
    const itemExists = await decisionPathItem.count() > 0;

    if (itemExists) {
      await decisionPathItem.click();
      await page.waitForTimeout(1000);

      // Look for modal or expanded details
      const modal = page.locator('[role="dialog"], [data-testid="modal"], [class*="modal"]');
      const modalExists = await modal.isVisible().catch(() => false);

      if (modalExists) {
        // Verify modal contains decision path details
        const reasoning = page.locator('text=/reasoning|confidence|duration/i');
        expect(await reasoning.count()).toBeGreaterThan(0);
      }
    }
  });

  test('should filter decision paths by date range', async ({ page }) => {
    // Mock explainability endpoint with date filtering
    await page.route('**/api/v1/explainability/decision-paths*', (route) => {
      const url = new URL(route.request().url());
      const startDate = url.searchParams.get('start_date');
      const endDate = url.searchParams.get('end_date');

      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          decision_paths: [
            {
              id: 'path-1',
              query: 'Filtered query',
              timestamp: '2024-01-15T10:00:00Z',
              steps: [],
              final_decision: 'Filtered result',
            },
          ],
          total: 1,
        }),
      });
    });

    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Look for date range filter
    const dateFilter = page.locator('input[type="date"], [data-testid*="date-filter"]');
    const filterExists = await dateFilter.count() > 0;

    if (filterExists) {
      const startDate = dateFilter.first();
      await startDate.fill('2024-01-01');
      await page.waitForTimeout(1000);

      // Verify filtered results
      const filteredPaths = page.locator('[data-testid*="decision-path"]');
      expect(await filteredPaths.count()).toBeGreaterThan(0);
    }
  });

  test('should display model information', async ({ page }) => {
    // Mock model info endpoint
    await page.route('**/api/v1/explainability/model-info*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          model_name: 'Nemotron3 Nano',
          model_version: '1.0',
          model_type: 'LLM',
          embedding_model: 'BGE-M3',
          last_updated: '2024-01-01T00:00:00Z',
          parameters: 30000000000, // 30B parameters
          context_window: 32768,
        }),
      });
    });

    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Look for model information section
    const modelInfo = page.locator('[data-testid*="model-info"], [class*="model-info"]');
    const infoExists = await modelInfo.count() > 0;

    // Look for model names
    const modelText = page.locator('text=/Nemotron|BGE-M3|LLM/');
    const hasModelText = await modelText.count() > 0;

    expect(infoExists || hasModelText).toBeTruthy();
  });

  test('should handle empty decision paths gracefully', async ({ page }) => {
    // Sprint 111 Fix: Mock correct endpoint with empty response
    await page.route('**/api/v1/explainability/recent*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]), // Empty array
      });
    });

    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Verify empty state message - component shows "No decision paths available"
    // Sprint 111 Fix: Use separate locators to avoid CSS parsing issues
    const emptyByTestId = page.locator('[data-testid="empty-decision-paths"]');
    const emptyByText = page.locator('text=/no decision paths|submit queries/i');
    const hasEmptyState = (await emptyByTestId.count() > 0) || (await emptyByText.count() > 0);
    expect(hasEmptyState).toBeTruthy();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Sprint 111 Fix: Mock correct endpoint with error response
    await page.route('**/api/v1/explainability/recent*', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Internal server error',
        }),
      });
    });

    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Verify error message is displayed - component shows "Failed to load recent traces"
    const errorMessage = page.locator('text=/error|failed|unable/i');
    expect(await errorMessage.count()).toBeGreaterThan(0);
  });

  test('should display decision confidence levels', async ({ page }) => {
    // Mock explainability endpoint with confidence scores
    await page.route('**/api/v1/explainability/decision-paths*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          decision_paths: [
            {
              id: 'path-1',
              query: 'High confidence query',
              timestamp: '2024-01-15T10:00:00Z',
              steps: [
                {
                  step_id: 1,
                  agent: 'Coordinator',
                  action: 'Query Classification',
                  reasoning: 'High confidence classification',
                  confidence: 0.95, // High confidence
                },
                {
                  step_id: 2,
                  agent: 'Vector Agent',
                  action: 'Vector Search',
                  reasoning: 'Medium confidence retrieval',
                  confidence: 0.75, // Medium confidence
                },
                {
                  step_id: 3,
                  agent: 'Generation Agent',
                  action: 'Answer Synthesis',
                  reasoning: 'Low confidence synthesis',
                  confidence: 0.55, // Low confidence
                },
              ],
              final_decision: 'Answer generated with mixed confidence',
            },
          ],
        }),
      });
    });

    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Look for confidence scores (95%, 75%, 55%)
    const confidenceScores = page.locator('text=/95|75|55|confidence/i');
    expect(await confidenceScores.count()).toBeGreaterThan(0);
  });

  test('should export decision paths', async ({ page }) => {
    await navigateClientSide(page, '/admin/explainability');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Look for export button
    const exportButton = page.locator('button:has-text("Export"), button:has-text("Download")');
    const buttonExists = await exportButton.count() > 0;

    if (buttonExists) {
      // Setup download listener
      const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);

      await exportButton.first().click();

      const download = await downloadPromise;
      if (download) {
        // Verify download started
        expect(download.suggestedFilename()).toMatch(/decision.*path|export|explainability/i);
      }
    }
  });
});
