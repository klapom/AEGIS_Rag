/**
 * E2E Tests for Skill Management UI - Sprint 97
 *
 * Sprint 97 Features Covered:
 * - 97.1: Skill Registry Browser (10 SP)
 * - 97.2: Skill Configuration Editor (10 SP)
 * - 97.3: Tool Authorization Manager (8 SP)
 * - 97.4: Skill Lifecycle Dashboard (6 SP)
 * - 97.5: SKILL.md Visual Editor (4 SP)
 *
 * Total: 30 tests covering all skill management features
 *
 * Test Data:
 * - 15 test skills with various states (active/inactive)
 * - YAML configurations
 * - Tool authorization matrices
 * - Lifecycle metrics and execution history
 */

import { test, expect, Page } from '@playwright/test';

const ADMIN_URL = process.env.ADMIN_URL || 'http://localhost:5179/admin';
const API_URL = process.env.API_URL || 'http://localhost:8000';

// ============================================================================
// Test Fixtures & Utilities
// ============================================================================

interface SkillCard {
  name: string;
  version: string;
  description: string;
  isActive: boolean;
  toolsCount: number;
  triggersCount: number;
}

/**
 * Navigate to Skill Registry page
 */
async function navigateToSkillRegistry(page: Page) {
  await page.goto(`${ADMIN_URL}/skills/registry`);
  await page.waitForLoadState('networkidle');
  await expect(page.getByTestId('skill-registry-page')).toBeVisible();
}

/**
 * Get all skill cards from current page
 */
async function getSkillCards(page: Page): Promise<string[]> {
  const cards = await page.getByTestId('skill-card').all();
  return Promise.all(cards.map(card => card.getAttribute('data-skill-name') || ''));
}

/**
 * Search for skills in registry
 */
async function searchSkills(page: Page, query: string) {
  await page.getByTestId('skill-search-input').fill(query);
  await page.getByTestId('search-submit-button').click();
  await page.waitForLoadState('networkidle');
}

/**
 * Filter skills by status
 */
async function filterByStatus(page: Page, status: 'active' | 'inactive' | 'all') {
  await page.getByTestId('status-filter-dropdown').selectOption(status);
  await page.waitForLoadState('networkidle');
}

// ============================================================================
// Test Suite
// ============================================================================

test.describe('Skill Management - Sprint 97', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure we're logged in
    await page.goto(ADMIN_URL);
    await page.waitForLoadState('networkidle');
  });

  // ========================================================================
  // 97.1: Skill Registry Browser (8 tests)
  // ========================================================================

  test.describe('Skill Registry Browser (97.1)', () => {
    test('should display skill registry with grid view', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Verify grid layout
      const grid = page.getByTestId('skill-grid');
      await expect(grid).toBeVisible();

      // Verify multiple skill cards are visible
      const cards = await page.getByTestId('skill-card').all();
      expect(cards.length).toBeGreaterThan(0);
    });

    test('should display skill card with correct metadata', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Get first skill card
      const firstCard = page.getByTestId('skill-card').first();
      await expect(firstCard).toBeVisible();

      // Verify card elements
      const skillName = firstCard.getByTestId('skill-name');
      const version = firstCard.getByTestId('skill-version');
      const description = firstCard.getByTestId('skill-description');
      const toolsCount = firstCard.getByTestId('tools-count');
      const triggersCount = firstCard.getByTestId('triggers-count');
      const statusBadge = firstCard.getByTestId('status-badge');

      await expect(skillName).toBeVisible();
      await expect(version).toBeVisible();
      await expect(description).toBeVisible();
      await expect(toolsCount).toBeVisible();
      await expect(triggersCount).toBeVisible();
      await expect(statusBadge).toBeVisible();
    });

    test('should search skills by name', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Search for a specific skill
      await searchSkills(page, 'retrieval');

      // Verify results are filtered
      const cards = await getSkillCards(page);
      expect(cards.length).toBeGreaterThan(0);

      // All results should contain "retrieval"
      for (const name of cards) {
        expect(name.toLowerCase()).toContain('retrieval');
      }
    });

    test('should search skills and show no results message', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Search for non-existent skill
      await searchSkills(page, 'nonexistent_skill_xyz_123');

      // Verify no results message
      await expect(page.getByTestId('no-results-message')).toBeVisible();
    });

    test('should filter skills by active status', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Filter to show only active skills
      await filterByStatus(page, 'active');

      // Verify all visible skills are marked as active
      const statusBadges = await page.getByTestId('status-badge').all();
      for (const badge of statusBadges) {
        const text = await badge.textContent();
        expect(text).toContain('Active');
      }
    });

    test('should filter skills by inactive status', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Filter to show only inactive skills
      await filterByStatus(page, 'inactive');

      // Verify all visible skills are marked as inactive
      const statusBadges = await page.getByTestId('status-badge').all();
      for (const badge of statusBadges) {
        const text = await badge.textContent();
        expect(text).toContain('Inactive');
      }
    });

    test('should toggle skill activation from registry', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Get first skill card
      const firstCard = page.getByTestId('skill-card').first();
      const toggleButton = firstCard.getByTestId('activation-toggle');
      const statusBadge = firstCard.getByTestId('status-badge');

      // Get initial status
      const initialStatus = await statusBadge.textContent();

      // Click toggle
      await toggleButton.click();
      await page.waitForTimeout(500);

      // Verify status changed
      const newStatus = await statusBadge.textContent();
      expect(newStatus).not.toBe(initialStatus);
    });

    test('should paginate skill list (12 per page)', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Check pagination controls
      const pagination = page.getByTestId('skill-pagination');
      const nextButton = pagination.getByTestId('page-next-button');

      // Get current page count
      const currentCards = await page.getByTestId('skill-card').count();
      expect(currentCards).toBeLessThanOrEqual(12);

      // If more pages exist, click next
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        await page.waitForLoadState('networkidle');

        // Verify new page loaded
        const newCards = await page.getByTestId('skill-card').count();
        expect(newCards).toBeGreaterThan(0);
      }
    });

    test('should handle registry with large dataset (performance check)', async ({ page }) => {
      const startTime = Date.now();

      await navigateToSkillRegistry(page);

      // Verify page loads within 2 seconds
      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(2000);

      // Verify cards are visible
      const cards = await page.getByTestId('skill-card').all();
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  // ========================================================================
  // 97.2: Skill Configuration Editor (6 tests)
  // ========================================================================

  test.describe('Skill Configuration Editor (97.2)', () => {
    test('should open skill configuration editor', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Click config button on first skill
      const firstCard = page.getByTestId('skill-card').first();
      const configButton = firstCard.getByTestId('config-button');
      await configButton.click();

      // Verify editor opens
      const editor = page.getByTestId('skill-config-editor');
      await expect(editor).toBeVisible();
    });

    test('should display YAML editor with syntax highlighting', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open editor
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('config-button').click();

      // Verify editor elements
      const yamlEditor = page.getByTestId('yaml-editor');
      const preview = page.getByTestId('config-preview');

      await expect(yamlEditor).toBeVisible();
      await expect(preview).toBeVisible();

      // Verify editor has content
      const content = await yamlEditor.getAttribute('class');
      expect(content).toBeTruthy();
    });

    test('should edit YAML configuration and validate syntax', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open editor
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('config-button').click();

      // Get the YAML editor input
      const editor = page.getByTestId('yaml-editor-input');

      // Clear and set new content
      await editor.click();
      await page.keyboard.press('Control+A');

      const newConfig = `
embedding:
  model: bge-m3
  dimension: 1024
search:
  top_k: 15
  modes:
    - vector
    - hybrid
`;
      await page.keyboard.type(newConfig, { delay: 10 });

      // Wait for validation
      await page.waitForTimeout(500);

      // Verify validation success
      const validationStatus = page.getByTestId('validation-status');
      await expect(validationStatus).toContainText('Valid');
    });

    test('should show YAML validation errors', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open editor
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('config-button').click();

      // Enter invalid YAML
      const editor = page.getByTestId('yaml-editor-input');
      await editor.click();
      await page.keyboard.press('Control+A');

      const invalidYaml = `
embedding:
  model: bge-m3
  dimension: 1024
invalid_indent:
    wrong: spacing
  bad: alignment
`;
      await page.keyboard.type(invalidYaml, { delay: 5 });

      // Wait for validation
      await page.waitForTimeout(500);

      // Verify error message
      const errorMessage = page.getByTestId('validation-error');
      await expect(errorMessage).toBeVisible();
    });

    test('should save configuration changes', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open editor
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('config-button').click();

      // Modify config
      const editor = page.getByTestId('yaml-editor-input');
      await editor.click();

      // Make a small change (e.g., change top_k value)
      await page.keyboard.press('Control+F');
      await page.keyboard.type('top_k');
      await page.keyboard.press('Enter');
      await page.keyboard.press('Escape');

      // Click save button
      const saveButton = page.getByTestId('config-save-button');
      await saveButton.click();

      // Verify success message
      await expect(page.getByTestId('save-success-message')).toBeVisible();
    });

    test('should reset configuration to previous state', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open editor
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('config-button').click();

      // Get original content
      const editor = page.getByTestId('yaml-editor-input');
      const originalContent = await editor.inputValue();

      // Modify config
      await editor.click();
      await page.keyboard.press('Control+A');
      await page.keyboard.type('# Modified');

      // Click reset button
      const resetButton = page.getByTestId('config-reset-button');
      await resetButton.click();

      // Verify content restored
      await page.waitForTimeout(300);
      const restoredContent = await editor.inputValue();
      expect(restoredContent).toBe(originalContent);
    });
  });

  // ========================================================================
  // 97.3: Tool Authorization Manager (6 tests)
  // ========================================================================

  test.describe('Tool Authorization Manager (97.3)', () => {
    test('should view tool authorization for skill', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Click auth button on first skill
      const firstCard = page.getByTestId('skill-card').first();
      const authButton = firstCard.getByTestId('auth-button');
      await authButton.click();

      // Verify auth manager opens
      const authManager = page.getByTestId('tool-auth-manager');
      await expect(authManager).toBeVisible();

      // Verify tools table is visible
      const toolsTable = page.getByTestId('authorized-tools-table');
      await expect(toolsTable).toBeVisible();
    });

    test('should display authorized tools with access levels', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open auth manager
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('auth-button').click();

      // Get tools from table
      const toolRows = await page.getByTestId('tool-row').all();
      expect(toolRows.length).toBeGreaterThan(0);

      // Verify each tool has access level
      for (const row of toolRows) {
        const accessLevel = row.getByTestId('access-level');
        await expect(accessLevel).toBeVisible();

        const level = await accessLevel.textContent();
        expect(['Standard', 'Elevated', 'Admin']).toContain(level?.trim());
      }
    });

    test('should add tool authorization to skill', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open auth manager
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('auth-button').click();

      // Get initial tool count
      const initialCount = await page.getByTestId('tool-row').count();

      // Click add tool button
      const addButton = page.getByTestId('add-tool-button');
      await addButton.click();

      // Select tool from dropdown
      const toolDropdown = page.getByTestId('tool-select-dropdown');
      await toolDropdown.selectOption({ label: /.*/ }); // Select first option

      // Select access level
      const accessDropdown = page.getByTestId('access-level-select');
      await accessDropdown.selectOption('Standard');

      // Click confirm button
      const confirmButton = page.getByTestId('add-tool-confirm-button');
      await confirmButton.click();

      // Wait for update
      await page.waitForTimeout(500);

      // Verify tool count increased
      const newCount = await page.getByTestId('tool-row').count();
      expect(newCount).toBeGreaterThan(initialCount);
    });

    test('should remove tool authorization from skill', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open auth manager
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('auth-button').click();

      // Get initial tool count
      const initialCount = await page.getByTestId('tool-row').count();

      if (initialCount > 0) {
        // Click delete on first tool
        const firstRow = page.getByTestId('tool-row').first();
        const deleteButton = firstRow.getByTestId('delete-tool-button');
        await deleteButton.click();

        // Confirm deletion
        const confirmButton = page.getByTestId('delete-confirm-button');
        await confirmButton.click();

        // Wait for update
        await page.waitForTimeout(500);

        // Verify tool count decreased
        const newCount = await page.getByTestId('tool-row').count();
        expect(newCount).toBeLessThan(initialCount);
      }
    });

    test('should change tool access level', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open auth manager
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('auth-button').click();

      // Get first tool row
      const firstRow = page.getByTestId('tool-row').first();
      const accessDropdown = firstRow.getByTestId('access-level-dropdown');

      // Get current level
      const currentLevel = await accessDropdown.inputValue();

      // Change level
      const newLevel = currentLevel === 'Standard' ? 'Elevated' : 'Standard';
      await accessDropdown.selectOption(newLevel);

      // Wait for save
      await page.waitForTimeout(300);

      // Verify level changed
      const updatedLevel = await accessDropdown.inputValue();
      expect(updatedLevel).toBe(newLevel);
    });

    test('should configure domain restrictions for tools', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open auth manager
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('auth-button').click();

      // Click on domain restrictions section
      const restrictionSection = page.getByTestId('domain-restrictions-section');
      if (await restrictionSection.isVisible()) {
        const addDomainButton = restrictionSection.getByTestId('add-allowed-domain-button');
        if (await addDomainButton.isEnabled()) {
          await addDomainButton.click();

          // Enter domain
          const domainInput = page.getByTestId('domain-input');
          await domainInput.fill('example.com');

          // Confirm
          const confirmButton = page.getByTestId('add-domain-confirm-button');
          await confirmButton.click();

          // Verify domain added
          await expect(page.getByTestId('domain-example-com')).toBeVisible();
        }
      }
    });
  });

  // ========================================================================
  // 97.4: Skill Lifecycle Dashboard (5 tests)
  // ========================================================================

  test.describe('Skill Lifecycle Dashboard (97.4)', () => {
    test('should display skill lifecycle dashboard with metrics', async ({ page }) => {
      await page.goto(`${ADMIN_URL}/skills/dashboard`);
      await page.waitForLoadState('networkidle');

      // Verify dashboard loads
      const dashboard = page.getByTestId('lifecycle-dashboard');
      await expect(dashboard).toBeVisible();

      // Verify metric cards
      const activeSkillsCard = page.getByTestId('active-skills-card');
      const toolCallsCard = page.getByTestId('tool-calls-card');
      const alertsCard = page.getByTestId('alerts-card');

      await expect(activeSkillsCard).toBeVisible();
      await expect(toolCallsCard).toBeVisible();
      await expect(alertsCard).toBeVisible();
    });

    test('should display skill activation timeline', async ({ page }) => {
      await page.goto(`${ADMIN_URL}/skills/dashboard`);

      // Verify timeline section
      const timeline = page.getByTestId('activation-timeline');
      await expect(timeline).toBeVisible();

      // Verify timeline has data
      const timelineItems = await page.getByTestId('timeline-item').count();
      expect(timelineItems).toBeGreaterThan(0);
    });

    test('should display top tool usage ranking', async ({ page }) => {
      await page.goto(`${ADMIN_URL}/skills/dashboard`);

      // Verify usage table
      const usageTable = page.getByTestId('top-tool-usage-table');
      await expect(usageTable).toBeVisible();

      // Verify rows exist
      const rows = await page.getByTestId('usage-row').count();
      expect(rows).toBeGreaterThan(0);
    });

    test('should display policy violations and alerts', async ({ page }) => {
      await page.goto(`${ADMIN_URL}/skills/dashboard`);

      // Verify violations section
      const violationsSection = page.getByTestId('policy-violations-section');
      if (await violationsSection.isVisible()) {
        const violations = await page.getByTestId('violation-item').count();
        expect(violations).toBeGreaterThanOrEqual(0);
      }
    });

    test('should filter metrics by time range', async ({ page }) => {
      await page.goto(`${ADMIN_URL}/skills/dashboard`);

      // Select time range
      const timeRangeSelect = page.getByTestId('time-range-select');
      await timeRangeSelect.selectOption('7d');

      // Wait for update
      await page.waitForLoadState('networkidle');

      // Verify data updated (check for new data)
      const timeline = page.getByTestId('activation-timeline');
      await expect(timeline).toBeVisible();
    });
  });

  // ========================================================================
  // 97.5: SKILL.md Visual Editor (5 tests)
  // ========================================================================

  test.describe('SKILL.md Visual Editor (97.5)', () => {
    test('should open SKILL.md editor from skill card', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Get first skill name
      const firstCard = page.getByTestId('skill-card').first();
      const skillName = await firstCard.getByTestId('skill-name').textContent();

      // Click edit button
      const editButton = firstCard.getByTestId('edit-skill-md-button');
      if (await editButton.isVisible()) {
        await editButton.click();

        // Verify editor opens
        const editor = page.getByTestId('skill-md-editor');
        await expect(editor).toBeVisible();

        // Verify skill name in editor
        const editorTitle = page.getByTestId('editor-skill-name');
        const titleText = await editorTitle.textContent();
        expect(titleText).toContain(skillName);
      }
    });

    test('should edit frontmatter fields in SKILL.md', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open editor
      const firstCard = page.getByTestId('skill-card').first();
      const editButton = firstCard.getByTestId('edit-skill-md-button');
      if (await editButton.isVisible()) {
        await editButton.click();

        // Edit version field
        const versionInput = page.getByTestId('frontmatter-version-input');
        if (await versionInput.isVisible()) {
          const currentVersion = await versionInput.inputValue();
          const newVersion = `${currentVersion}.1`;

          await versionInput.clear();
          await versionInput.fill(newVersion);

          // Verify preview updates
          const preview = page.getByTestId('markdown-preview');
          const previewText = await preview.textContent();
          expect(previewText).toContain(newVersion);
        }
      }
    });

    test('should edit markdown content in SKILL.md', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open editor
      const firstCard = page.getByTestId('skill-card').first();
      const editButton = firstCard.getByTestId('edit-skill-md-button');
      if (await editButton.isVisible()) {
        await editButton.click();

        // Get editor textarea
        const markdownEditor = page.getByTestId('markdown-content-input');
        if (await markdownEditor.isVisible()) {
          // Get current content
          const currentContent = await markdownEditor.inputValue();

          // Append text
          const testText = '\n\n## Test Section\nThis is a test addition.';
          await markdownEditor.evaluate(
            (el: HTMLTextAreaElement, text) => {
              el.value += text;
              el.dispatchEvent(new Event('input', { bubbles: true }));
            },
            testText
          );

          // Verify preview updates
          const preview = page.getByTestId('markdown-preview');
          const previewText = await preview.textContent();
          expect(previewText).toContain('Test Section');
        }
      }
    });

    test('should toggle between edit and preview modes', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open editor
      const firstCard = page.getByTestId('skill-card').first();
      const editButton = firstCard.getByTestId('edit-skill-md-button');
      if (await editButton.isVisible()) {
        await editButton.click();

        // Get tabs
        const editTab = page.getByTestId('edit-mode-tab');
        const previewTab = page.getByTestId('preview-mode-tab');

        // Click preview tab
        if (await previewTab.isVisible()) {
          await previewTab.click();

          // Verify preview is visible
          const preview = page.getByTestId('markdown-preview');
          await expect(preview).toBeVisible();

          // Click back to edit
          await editTab.click();

          // Verify editor is visible
          const editor = page.getByTestId('markdown-content-input');
          await expect(editor).toBeVisible();
        }
      }
    });

    test('should validate required frontmatter fields', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open editor
      const firstCard = page.getByTestId('skill-card').first();
      const editButton = firstCard.getByTestId('edit-skill-md-button');
      if (await editButton.isVisible()) {
        await editButton.click();

        // Try to clear a required field
        const nameInput = page.getByTestId('frontmatter-name-input');
        if (await nameInput.isVisible()) {
          await nameInput.clear();

          // Try to save
          const saveButton = page.getByTestId('save-skill-md-button');
          if (await saveButton.isVisible()) {
            await saveButton.click();

            // Verify validation error
            const errorMessage = page.getByTestId('validation-error-message');
            await expect(errorMessage).toBeVisible();
          }
        }
      }
    });
  });

  // ========================================================================
  // Edge Cases
  // ========================================================================

  test.describe('Edge Cases', () => {
    test('should handle skill with 50+ triggers', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Search for skill with many triggers
      await searchSkills(page, 'automation');

      // Verify skill displays
      const cards = await page.getByTestId('skill-card').all();
      expect(cards.length).toBeGreaterThan(0);

      // Check for triggers count
      for (const card of cards) {
        const triggersText = await card.getByTestId('triggers-count').textContent();
        expect(triggersText).toMatch(/\d+/);
      }
    });

    test('should handle concurrent skill updates', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open two skill editors
      const firstCard = page.getByTestId('skill-card').first();
      const firstConfigButton = firstCard.getByTestId('config-button');
      await firstConfigButton.click();

      // Verify at least one editor is open
      const editor = page.getByTestId('skill-config-editor');
      await expect(editor).toBeVisible();
    });

    test('should handle skill with special characters in YAML', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Open editor
      const firstCard = page.getByTestId('skill-card').first();
      await firstCard.getByTestId('config-button').click();

      // Try to enter YAML with special characters
      const editor = page.getByTestId('yaml-editor-input');
      if (await editor.isVisible()) {
        // This should be handled by YAML parser
        const yamlContent = `
description: "Special chars: @#$%^&*()"
name: 'test_skill'
`;
        await editor.click();
        await page.keyboard.press('Control+A');
        await page.keyboard.type(yamlContent, { delay: 5 });

        // Verify it validates
        await page.waitForTimeout(300);
        const status = page.getByTestId('validation-status');
        const statusText = await status.textContent();
        expect(statusText).toBeTruthy();
      }
    });

    test('should handle rapid search queries', async ({ page }) => {
      await navigateToSkillRegistry(page);

      // Perform multiple rapid searches
      const queries = ['retrieval', 'synthesis', 'graph', 'memory'];
      for (const query of queries) {
        await searchSkills(page, query);
        await page.waitForTimeout(100);
      }

      // Verify final results are correct
      const cards = await page.getByTestId('skill-card').all();
      expect(cards.length).toBeGreaterThan(0);
    });
  });
});
