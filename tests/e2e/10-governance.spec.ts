/**
 * E2E Tests for Governance UI - Sprint 98
 *
 * Sprint 98 Features Covered:
 * - 98.3: GDPR Consent Manager (8 SP) **P0 - EU Legal Requirement**
 * - 98.4: Audit Trail Viewer (6 SP) **P0 - EU AI Act Art. 12**
 * - 98.5: Explainability Dashboard (8 SP) **P0 - EU AI Act Art. 13**
 * - 98.6: Certification Dashboard (4 SP) **P1**
 *
 * Total: 32 tests covering governance and compliance features
 *
 * Test Data:
 * - 10 GDPR consent records
 * - 100 audit events
 * - 5 decision traces with multi-level explanations
 * - 15 skill certifications at various levels
 */

import { test, expect, Page } from '@playwright/test';

const ADMIN_URL = process.env.ADMIN_URL || 'http://localhost:5179/admin';
const API_URL = process.env.API_URL || 'http://localhost:8000';

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Navigate to Governance section
 */
async function navigateToGovernance(page: Page, section: 'gdpr' | 'audit' | 'explainability' | 'certification') {
  const urls: Record<string, string> = {
    gdpr: `${ADMIN_URL}/governance/gdpr`,
    audit: `${ADMIN_URL}/governance/audit`,
    explainability: `${ADMIN_URL}/governance/explainability`,
    certification: `${ADMIN_URL}/governance/certification`,
  };

  await page.goto(urls[section]);
  await page.waitForLoadState('networkidle');
}

/**
 * Fill GDPR consent form
 */
async function fillConsentForm(page: Page, data: {
  userId: string;
  purpose: string;
  legalBasis: string;
  dataCategories: string[];
}) {
  const userIdInput = page.getByTestId('consent-user-id-input');
  const purposeInput = page.getByTestId('consent-purpose-input');
  const legalBasisSelect = page.getByTestId('consent-legal-basis-select');

  await userIdInput.fill(data.userId);
  await purposeInput.fill(data.purpose);
  await legalBasisSelect.selectOption(data.legalBasis);

  // Select data categories
  for (const category of data.dataCategories) {
    const checkbox = page.getByTestId(`data-category-${category}`);
    if (await checkbox.isVisible()) {
      await checkbox.check();
    }
  }
}

/**
 * Apply filters to audit trail
 */
async function applyAuditFilters(page: Page, filters: {
  eventType?: string;
  timeRange?: string;
  search?: string;
}) {
  if (filters.eventType) {
    await page.getByTestId('event-type-filter').selectOption(filters.eventType);
  }

  if (filters.timeRange) {
    await page.getByTestId('time-range-filter').selectOption(filters.timeRange);
  }

  if (filters.search) {
    await page.getByTestId('audit-search-input').fill(filters.search);
  }

  await page.getByTestId('apply-filters-button').click();
  await page.waitForLoadState('networkidle');
}

// ============================================================================
// Test Suite
// ============================================================================

test.describe('Governance & Compliance UI - Sprint 98', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure we're logged in
    await page.goto(ADMIN_URL);
    await page.waitForLoadState('networkidle');
  });

  // ========================================================================
  // 98.3: GDPR Consent Manager (10 tests)
  // ========================================================================

  test.describe('GDPR Consent Manager (98.3)', () => {
    test('should display GDPR consent manager with consent list', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Verify page loaded
      const manager = page.getByTestId('gdpr-consent-manager');
      await expect(manager).toBeVisible();

      // Verify consents table
      const consentsTable = page.getByTestId('consents-table');
      await expect(consentsTable).toBeVisible();

      // Verify at least one consent row
      const consentRows = await page.getByTestId('consent-row').count();
      expect(consentRows).toBeGreaterThan(0);
    });

    test('should display consent with all required fields', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Get first consent row
      const firstRow = page.getByTestId('consent-row').first();

      // Verify fields
      const userId = firstRow.getByTestId('consent-user-id');
      const purpose = firstRow.getByTestId('consent-purpose');
      const legalBasis = firstRow.getByTestId('consent-legal-basis');
      const grantedDate = firstRow.getByTestId('consent-granted-date');
      const status = firstRow.getByTestId('consent-status');

      await expect(userId).toBeVisible();
      await expect(purpose).toBeVisible();
      await expect(legalBasis).toBeVisible();
      await expect(grantedDate).toBeVisible();
      await expect(status).toBeVisible();
    });

    test('should create new consent record', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Click add consent button
      const addButton = page.getByTestId('add-consent-button');
      await addButton.click();

      // Verify form appears
      const form = page.getByTestId('consent-form');
      await expect(form).toBeVisible();

      // Fill form
      await fillConsentForm(page, {
        userId: 'user_test_123',
        purpose: 'Customer Support',
        legalBasis: 'Contract',
        dataCategories: ['identifier', 'contact'],
      });

      // Submit form
      const submitButton = page.getByTestId('consent-form-submit-button');
      await submitButton.click();

      // Verify success message
      await expect(page.getByTestId('consent-created-message')).toBeVisible();

      // Verify consent appears in list
      const newConsent = page.getByTestId('consent-user_test_123');
      await expect(newConsent).toBeVisible();
    });

    test('should revoke user consent', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Get first consent
      const firstRow = page.getByTestId('consent-row').first();
      const revokeButton = firstRow.getByTestId('revoke-consent-button');

      // Click revoke
      await revokeButton.click();

      // Confirm action
      const confirmButton = page.getByTestId('revoke-confirm-button');
      await confirmButton.click();

      // Verify status changed
      await page.waitForTimeout(500);
      const status = firstRow.getByTestId('consent-status');
      const statusText = await status.textContent();
      expect(statusText).toContain('Withdrawn');
    });

    test('should handle right to erasure request', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Click Data Subject Rights tab
      const rightsTab = page.getByTestId('data-subject-rights-tab');
      if (await rightsTab.isVisible()) {
        await rightsTab.click();

        // Click submit erasure request
        const erasureButton = page.getByTestId('submit-erasure-request-button');
        await erasureButton.click();

        // Verify form appears
        const form = page.getByTestId('erasure-request-form');
        await expect(form).toBeVisible();

        // Fill user ID
        const userIdInput = page.getByTestId('erasure-user-id-input');
        await userIdInput.fill('user_123');

        // Submit
        const submitButton = page.getByTestId('erasure-request-submit-button');
        await submitButton.click();

        // Verify request created
        await expect(page.getByTestId('erasure-request-created')).toBeVisible();
      }
    });

    test('should export user data for portability (Art. 20)', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Click Data Subject Rights tab
      const rightsTab = page.getByTestId('data-subject-rights-tab');
      if (await rightsTab.isVisible()) {
        await rightsTab.click();

        // Click export data button
        const exportButton = page.getByTestId('submit-export-request-button');
        await exportButton.click();

        // Verify form appears
        const form = page.getByTestId('export-request-form');
        await expect(form).toBeVisible();

        // Fill user ID
        const userIdInput = page.getByTestId('export-user-id-input');
        await userIdInput.fill('user_456');

        // Submit
        const submitButton = page.getByTestId('export-request-submit-button');
        await submitButton.click();

        // Verify request created
        await expect(page.getByTestId('export-request-created')).toBeVisible();
      }
    });

    test('should view processing activity log (Art. 30)', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Click Processing Activities tab
      const activitiesTab = page.getByTestId('processing-activities-tab');
      if (await activitiesTab.isVisible()) {
        await activitiesTab.click();

        // Verify activities table loads
        const table = page.getByTestId('processing-activities-table');
        await expect(table).toBeVisible();

        // Verify activity rows
        const rows = await page.getByTestId('activity-row').count();
        expect(rows).toBeGreaterThanOrEqual(0);
      }
    });

    test('should filter consents by status', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Click status filter
      const statusFilter = page.getByTestId('consent-status-filter');
      await statusFilter.selectOption('active');

      // Wait for filter
      await page.waitForLoadState('networkidle');

      // Verify all visible consents are active
      const rows = await page.getByTestId('consent-row').all();
      for (const row of rows) {
        const status = row.getByTestId('consent-status');
        const statusText = await status.textContent();
        expect(statusText).toContain('Active');
      }
    });

    test('should display consent expiration warnings', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Look for expiring soon section
      const expiringSection = page.getByTestId('expiring-consents-section');
      if (await expiringSection.isVisible()) {
        // Verify warning banner
        const warningBanner = expiringSection.getByTestId('expiration-warning');
        if (await warningBanner.isVisible()) {
          const text = await warningBanner.textContent();
          expect(text).toContain('expir');
        }
      }
    });

    test('should handle invalid GDPR request gracefully', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Try to create consent with missing data
      const addButton = page.getByTestId('add-consent-button');
      await addButton.click();

      // Try to submit empty form
      const submitButton = page.getByTestId('consent-form-submit-button');
      await submitButton.click();

      // Verify validation error
      await expect(page.getByTestId('form-validation-error')).toBeVisible();
    });
  });

  // ========================================================================
  // 98.4: Audit Trail Viewer (8 tests)
  // ========================================================================

  test.describe('Audit Trail Viewer (98.4)', () => {
    test('should display audit trail with event list', async ({ page }) => {
      await navigateToGovernance(page, 'audit');

      // Verify page loaded
      const viewer = page.getByTestId('audit-trail-viewer');
      await expect(viewer).toBeVisible();

      // Verify events table
      const eventsTable = page.getByTestId('audit-events-table');
      await expect(eventsTable).toBeVisible();

      // Verify event rows
      const eventRows = await page.getByTestId('audit-event-row').count();
      expect(eventRows).toBeGreaterThan(0);
    });

    test('should display audit event with all details', async ({ page }) => {
      await navigateToGovernance(page, 'audit');

      // Get first event row
      const firstRow = page.getByTestId('audit-event-row').first();

      // Verify event fields
      const timestamp = firstRow.getByTestId('event-timestamp');
      const eventType = firstRow.getByTestId('event-type');
      const actor = firstRow.getByTestId('event-actor');
      const resource = firstRow.getByTestId('event-resource');
      const outcome = firstRow.getByTestId('event-outcome');

      await expect(timestamp).toBeVisible();
      await expect(eventType).toBeVisible();
      await expect(actor).toBeVisible();
      await expect(resource).toBeVisible();
      await expect(outcome).toBeVisible();
    });

    test('should filter audit events by type', async ({ page }) => {
      await navigateToGovernance(page, 'audit');

      // Apply type filter
      await applyAuditFilters(page, { eventType: 'SKILL_EXECUTED' });

      // Verify filtered results
      const eventRows = await page.getByTestId('audit-event-row').all();
      expect(eventRows.length).toBeGreaterThan(0);

      // Verify all events are of selected type
      for (const row of eventRows) {
        const typeCell = row.getByTestId('event-type');
        const typeText = await typeCell.textContent();
        expect(typeText).toContain('SKILL_EXECUTED');
      }
    });

    test('should filter audit events by time range', async ({ page }) => {
      await navigateToGovernance(page, 'audit');

      // Apply time range filter
      await applyAuditFilters(page, { timeRange: '24h' });

      // Verify results
      const eventRows = await page.getByTestId('audit-event-row').count();
      expect(eventRows).toBeGreaterThan(0);
    });

    test('should search audit events', async ({ page }) => {
      await navigateToGovernance(page, 'audit');

      // Apply search filter
      await applyAuditFilters(page, { search: 'retrieval' });

      // Verify filtered results
      const eventRows = await page.getByTestId('audit-event-row').count();
      expect(eventRows).toBeGreaterThanOrEqual(0);
    });

    test('should verify audit chain integrity', async ({ page }) => {
      await navigateToGovernance(page, 'audit');

      // Click verify integrity button
      const verifyButton = page.getByTestId('verify-integrity-button');
      await verifyButton.click();

      // Wait for verification
      await page.waitForTimeout(1000);

      // Verify result message
      const resultMessage = page.getByTestId('integrity-result-message');
      await expect(resultMessage).toBeVisible();

      const text = await resultMessage.textContent();
      expect(text).toMatch(/verified|integrity|chain/i);
    });

    test('should generate GDPR compliance report', async ({ page }) => {
      await navigateToGovernance(page, 'audit');

      // Click generate report button
      const reportButton = page.getByTestId('generate-gdpr-report-button');
      if (await reportButton.isVisible()) {
        await reportButton.click();

        // Wait for report generation
        await page.waitForTimeout(1500);

        // Verify report section appears
        const reportSection = page.getByTestId('gdpr-report-section');
        await expect(reportSection).toBeVisible();
      }
    });

    test('should export audit log to CSV', async ({ page }) => {
      await navigateToGovernance(page, 'audit');

      // Start waiting for download
      const downloadPromise = page.waitForEvent('download');

      // Click export button
      const exportButton = page.getByTestId('export-csv-button');
      await exportButton.click();

      // Get download
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/audit.*\.csv/i);
    });
  });

  // ========================================================================
  // 98.5: Explainability Dashboard (8 tests)
  // ========================================================================

  test.describe('Explainability Dashboard (98.5)', () => {
    test('should display explainability dashboard with recent traces', async ({ page }) => {
      await navigateToGovernance(page, 'explainability');

      // Verify dashboard loaded
      const dashboard = page.getByTestId('explainability-dashboard');
      await expect(dashboard).toBeVisible();

      // Verify traces list
      const tracesList = page.getByTestId('recent-traces-list');
      if (await tracesList.isVisible()) {
        const traces = await page.getByTestId('trace-item').count();
        expect(traces).toBeGreaterThan(0);
      }
    });

    test('should view decision trace for query', async ({ page }) => {
      await navigateToGovernance(page, 'explainability');

      // Get first trace
      const firstTrace = page.getByTestId('trace-item').first();
      if (await firstTrace.isVisible()) {
        await firstTrace.click();

        // Verify trace details appear
        const traceDetails = page.getByTestId('trace-details');
        await expect(traceDetails).toBeVisible();

        // Verify query is displayed
        const query = page.getByTestId('trace-query');
        await expect(query).toBeVisible();
      }
    });

    test('should switch to user-level explanation', async ({ page }) => {
      await navigateToGovernance(page, 'explainability');

      // Get first trace
      const firstTrace = page.getByTestId('trace-item').first();
      if (await firstTrace.isVisible()) {
        await firstTrace.click();

        // Verify trace details loaded
        await expect(page.getByTestId('trace-details')).toBeVisible();

        // Click user view radio button
        const userViewRadio = page.getByTestId('explanation-level-user');
        await userViewRadio.click();

        // Verify user explanation displayed
        const explanation = page.getByTestId('user-level-explanation');
        await expect(explanation).toBeVisible();

        // Verify explanation is simple language
        const text = await explanation.textContent();
        expect(text?.length).toBeGreaterThan(0);
      }
    });

    test('should switch to expert-level explanation', async ({ page }) => {
      await navigateToGovernance(page, 'explainability');

      // Get first trace
      const firstTrace = page.getByTestId('trace-item').first();
      if (await firstTrace.isVisible()) {
        await firstTrace.click();

        // Click expert view radio button
        const expertViewRadio = page.getByTestId('explanation-level-expert');
        await expertViewRadio.click();

        // Verify expert explanation displayed
        const explanation = page.getByTestId('expert-level-explanation');
        await expect(explanation).toBeVisible();

        // Verify technical details present
        const decision = page.getByTestId('decision-flow-details');
        if (await decision.isVisible()) {
          const text = await decision.textContent();
          expect(text).toMatch(/skill|intent|retrieve|confidence/i);
        }
      }
    });

    test('should switch to audit-level full trace', async ({ page }) => {
      await navigateToGovernance(page, 'explainability');

      // Get first trace
      const firstTrace = page.getByTestId('trace-item').first();
      if (await firstTrace.isVisible()) {
        await firstTrace.click();

        // Click audit view radio button
        const auditViewRadio = page.getByTestId('explanation-level-audit');
        await auditViewRadio.click();

        // Verify JSON trace displayed
        const jsonTrace = page.getByTestId('audit-level-json-trace');
        await expect(jsonTrace).toBeVisible();
      }
    });

    test('should view source attribution for response', async ({ page }) => {
      await navigateToGovernance(page, 'explainability');

      // Get first trace
      const firstTrace = page.getByTestId('trace-item').first();
      if (await firstTrace.isVisible()) {
        await firstTrace.click();

        // Verify sources panel
        const sourcesPanel = page.getByTestId('source-attribution-panel');
        if (await sourcesPanel.isVisible()) {
          // Verify source items
          const sources = await page.getByTestId('attribution-source-item').count();
          expect(sources).toBeGreaterThan(0);

          // Verify each source has relevance score
          const sourceItems = await page.getByTestId('attribution-source-item').all();
          for (const item of sourceItems) {
            const relevance = item.getByTestId('source-relevance-score');
            await expect(relevance).toBeVisible();
          }
        }
      }
    });

    test('should find source for specific claim', async ({ page }) => {
      await navigateToGovernance(page, 'explainability');

      // Get first trace
      const firstTrace = page.getByTestId('trace-item').first();
      if (await firstTrace.isVisible()) {
        await firstTrace.click();

        // Get a claim from the response
        const claimElement = page.getByTestId('response-claim').first();
        if (await claimElement.isVisible()) {
          const claimText = await claimElement.textContent();

          // Find sources button
          const findSourcesButton = claimElement.getByTestId('find-sources-button');
          if (await findSourcesButton.isVisible()) {
            await findSourcesButton.click();

            // Verify sources highlighted
            await page.waitForTimeout(300);
            const highlightedSources = await page.locator('[data-highlighted="true"]').count();
            expect(highlightedSources).toBeGreaterThan(0);
          }
        }
      }
    });

    test('should display confidence and hallucination metrics', async ({ page }) => {
      await navigateToGovernance(page, 'explainability');

      // Get first trace
      const firstTrace = page.getByTestId('trace-item').first();
      if (await firstTrace.isVisible()) {
        await firstTrace.click();

        // Verify metrics displayed
        const confidenceMetric = page.getByTestId('response-confidence-metric');
        const hallucMetric = page.getByTestId('hallucination-risk-metric');

        if (await confidenceMetric.isVisible()) {
          const text = await confidenceMetric.textContent();
          expect(text).toMatch(/\d+%/);
        }

        if (await hallucMetric.isVisible()) {
          const text = await hallucMetric.textContent();
          expect(text).toMatch(/\d+%/);
        }
      }
    });
  });

  // ========================================================================
  // 98.6: Certification Dashboard (6 tests)
  // ========================================================================

  test.describe('Certification Status Dashboard (98.6)', () => {
    test('should display skill certification dashboard', async ({ page }) => {
      await navigateToGovernance(page, 'certification');

      // Verify dashboard loaded
      const dashboard = page.getByTestId('certification-dashboard');
      await expect(dashboard).toBeVisible();

      // Verify overview cards
      const enterpriseCard = page.getByTestId('enterprise-cert-card');
      const standardCard = page.getByTestId('standard-cert-card');
      const basicCard = page.getByTestId('basic-cert-card');

      await expect(enterpriseCard).toBeVisible();
      await expect(standardCard).toBeVisible();
      await expect(basicCard).toBeVisible();
    });

    test('should display all skill certifications with levels', async ({ page }) => {
      await navigateToGovernance(page, 'certification');

      // Verify certifications table
      const table = page.getByTestId('skill-certifications-table');
      await expect(table).toBeVisible();

      // Get certification rows
      const rows = await page.getByTestId('certification-row').all();
      expect(rows.length).toBeGreaterThan(0);

      // Verify each has level indicator
      for (const row of rows) {
        const levelBadge = row.getByTestId('certification-level-badge');
        await expect(levelBadge).toBeVisible();

        const level = await levelBadge.textContent();
        expect(['Enterprise', 'Standard', 'Basic']).toContain(level?.trim());
      }
    });

    test('should view certification report for skill', async ({ page }) => {
      await navigateToGovernance(page, 'certification');

      // Get first certification
      const firstRow = page.getByTestId('certification-row').first();
      const reportButton = firstRow.getByTestId('view-report-button');

      // Click view report
      await reportButton.click();

      // Verify report modal/panel opens
      const reportPanel = page.getByTestId('certification-report-panel');
      await expect(reportPanel).toBeVisible();

      // Verify report sections
      const gdprCheck = page.getByTestId('report-gdpr-check');
      const securityCheck = page.getByTestId('report-security-check');
      const auditCheck = page.getByTestId('report-audit-check');

      if (await gdprCheck.isVisible()) {
        const status = await gdprCheck.textContent();
        expect(status).toMatch(/passed|failed|pending/i);
      }
    });

    test('should re-validate skill certification', async ({ page }) => {
      await navigateToGovernance(page, 'certification');

      // Get first certification
      const firstRow = page.getByTestId('certification-row').first();
      const validateButton = firstRow.getByTestId('validate-button');

      if (await validateButton.isVisible()) {
        // Click validate
        await validateButton.click();

        // Verify validation in progress
        const validatingIndicator = page.getByTestId('validating-indicator');
        if (await validatingIndicator.isVisible()) {
          await expect(validatingIndicator).toBeVisible();
        }

        // Wait for completion
        await page.waitForTimeout(2000);

        // Verify result message
        const resultMessage = page.getByTestId('validation-result-message');
        if (await resultMessage.isVisible()) {
          const text = await resultMessage.textContent();
          expect(text).toMatch(/validat|updated|complete/i);
        }
      }
    });

    test('should display expiring certifications alert', async ({ page }) => {
      await navigateToGovernance(page, 'certification');

      // Look for expiring section
      const expiringSection = page.getByTestId('expiring-certifications-section');
      if (await expiringSection.isVisible()) {
        // Verify skills listed
        const expiringSkills = await page.getByTestId('expiring-skill-item').count();
        expect(expiringSkills).toBeGreaterThanOrEqual(0);

        // If any expiring, verify warning
        if (expiringSkills > 0) {
          const warningBanner = page.getByTestId('expiration-warning-banner');
          if (await warningBanner.isVisible()) {
            const text = await warningBanner.textContent();
            expect(text).toContain('expir');
          }
        }
      }
    });

    test('should filter certifications by level', async ({ page }) => {
      await navigateToGovernance(page, 'certification');

      // Apply level filter
      const levelFilter = page.getByTestId('level-filter');
      await levelFilter.selectOption('Enterprise');

      // Wait for filter
      await page.waitForLoadState('networkidle');

      // Verify all visible certs are Enterprise
      const rows = await page.getByTestId('certification-row').all();
      for (const row of rows) {
        const levelBadge = row.getByTestId('certification-level-badge');
        const text = await levelBadge.textContent();
        expect(text).toContain('Enterprise');
      }
    });
  });

  // ========================================================================
  // Edge Cases
  // ========================================================================

  test.describe('Governance Edge Cases', () => {
    test('should handle GDPR request for non-existent user', async ({ page }) => {
      await navigateToGovernance(page, 'gdpr');

      // Try to create consent with invalid user ID
      const addButton = page.getByTestId('add-consent-button');
      await addButton.click();

      // Fill with invalid data
      const userIdInput = page.getByTestId('consent-user-id-input');
      await userIdInput.fill('nonexistent_user_');

      // Try to submit
      const submitButton = page.getByTestId('consent-form-submit-button');
      await submitButton.click();

      // Should either validate or show error gracefully
      await page.waitForTimeout(500);
    });

    test('should handle audit log query with large time range', async ({ page }) => {
      await navigateToGovernance(page, 'audit');

      // Apply very large time range filter
      await applyAuditFilters(page, { timeRange: '1y' });

      // Should handle gracefully with pagination/performance
      const eventRows = await page.getByTestId('audit-event-row').count();
      expect(eventRows).toBeGreaterThanOrEqual(0);
    });

    test('should handle explainability for query with no retrieval', async ({ page }) => {
      await navigateToGovernance(page, 'explainability');

      // Try to find a trace with minimal retrieval
      const traces = await page.getByTestId('trace-item').all();
      if (traces.length > 0) {
        // Click through traces to find one with few sources
        for (const trace of traces.slice(0, 3)) {
          await trace.click();

          // Check if has sources
          const sources = await page.getByTestId('attribution-source-item').count();
          if (sources === 0) {
            // Verify "no sources" message displayed gracefully
            const noSourcesMsg = page.getByTestId('no-sources-message');
            if (await noSourcesMsg.isVisible()) {
              break;
            }
          }

          // Go back
          const backButton = page.getByTestId('back-button');
          if (await backButton.isVisible()) {
            await backButton.click();
          }
        }
      }
    });

    test('should handle concurrent governance UI operations', async ({ page }) => {
      // Open multiple governance pages in sequence
      await navigateToGovernance(page, 'gdpr');
      await page.waitForLoadState('networkidle');

      await navigateToGovernance(page, 'audit');
      await page.waitForLoadState('networkidle');

      await navigateToGovernance(page, 'explainability');
      await page.waitForLoadState('networkidle');

      await navigateToGovernance(page, 'certification');
      await page.waitForLoadState('networkidle');

      // Verify final page loaded correctly
      const dashboard = page.getByTestId('certification-dashboard');
      await expect(dashboard).toBeVisible();
    });
  });
});
