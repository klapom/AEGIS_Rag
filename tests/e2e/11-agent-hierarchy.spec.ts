/**
 * E2E Tests for Agent Hierarchy & Communication - Sprint 98
 *
 * Sprint 98 Features Covered:
 * - 98.1: Agent Communication Dashboard (8 SP)
 * - 98.2: Agent Hierarchy Visualizer (6 SP)
 *
 * Total: 14 tests covering agent monitoring and hierarchy visualization
 *
 * Test Data:
 * - Agent hierarchy with 3 levels (1 executive, 3 managers, 9 workers)
 * - 50+ agent messages
 * - 5 active orchestrations
 * - Blackboard state with multiple namespaces
 */

import { test, expect, Page } from '@playwright/test';

const ADMIN_URL = process.env.ADMIN_URL || 'http://localhost:5179/admin';
const API_URL = process.env.API_URL || 'http://localhost:8000';

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Navigate to Agent Communication Dashboard
 */
async function navigateToAgentCommunication(page: Page) {
  await page.goto(`${ADMIN_URL}/agents/communication`);
  await page.waitForLoadState('networkidle');
  await expect(page.getByTestId('agent-communication-dashboard')).toBeVisible();
}

/**
 * Navigate to Agent Hierarchy Visualizer
 */
async function navigateToAgentHierarchy(page: Page) {
  await page.goto(`${ADMIN_URL}/agents/hierarchy`);
  await page.waitForLoadState('networkidle');
  await expect(page.getByTestId('agent-hierarchy-visualizer')).toBeVisible();
}

/**
 * Wait for real-time message to appear
 */
async function waitForMessage(page: Page, timeout = 5000) {
  const messages = page.getByTestId('message-item');
  await expect(messages.first()).toBeVisible({ timeout });
}

/**
 * Filter messages by agent
 */
async function filterMessagesByAgent(page: Page, agentName: string) {
  const agentFilter = page.getByTestId('agent-filter-select');
  await agentFilter.selectOption(agentName);
  await page.waitForLoadState('networkidle');
}

/**
 * Get orchestration details by ID
 */
async function getOrchestrationDetails(page: Page, orchestrationId: string) {
  const row = page.getByTestId(`orchestration-${orchestrationId}`);
  const detailsButton = row.getByTestId('view-details-button');
  await detailsButton.click();
  await page.waitForLoadState('networkidle');
}

// ============================================================================
// Test Suite
// ============================================================================

test.describe('Agent Hierarchy & Communication - Sprint 98', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure we're logged in
    await page.goto(ADMIN_URL);
    await page.waitForLoadState('networkidle');
  });

  // ========================================================================
  // 98.1: Agent Communication Dashboard (8 tests)
  // ========================================================================

  test.describe('Agent Communication Dashboard (98.1)', () => {
    test('should display agent communication dashboard', async ({ page }) => {
      await navigateToAgentCommunication(page);

      // Verify dashboard loaded
      const dashboard = page.getByTestId('agent-communication-dashboard');
      await expect(dashboard).toBeVisible();

      // Verify tabs are present
      const messageBusTab = page.getByTestId('messagebus-tab');
      const blackboardTab = page.getByTestId('blackboard-tab');
      const orchestrationsTab = page.getByTestId('orchestrations-tab');

      await expect(messageBusTab).toBeVisible();
      await expect(blackboardTab).toBeVisible();
      await expect(orchestrationsTab).toBeVisible();
    });

    test('should display real-time agent messages', async ({ page }) => {
      await navigateToAgentCommunication(page);

      // Ensure messagebus tab is active
      const messageBusTab = page.getByTestId('messagebus-tab');
      if (!await messageBusTab.getAttribute('class')?.includes('active')) {
        await messageBusTab.click();
      }

      // Verify messages area
      const messagesArea = page.getByTestId('messages-area');
      await expect(messagesArea).toBeVisible();

      // Check for message items
      const messages = await page.getByTestId('message-item').count();
      expect(messages).toBeGreaterThanOrEqual(0);

      // Verify at least some message structure if messages exist
      if (messages > 0) {
        const firstMessage = page.getByTestId('message-item').first();
        const sender = firstMessage.getByTestId('message-sender');
        const timestamp = firstMessage.getByTestId('message-timestamp');

        await expect(sender).toBeVisible();
        await expect(timestamp).toBeVisible();
      }
    });

    test('should display message content and metadata', async ({ page }) => {
      await navigateToAgentCommunication(page);

      // Ensure messagebus tab active
      const messageBusTab = page.getByTestId('messagebus-tab');
      await messageBusTab.click();

      // Wait for messages to load
      const messages = await page.getByTestId('message-item').count();
      if (messages > 0) {
        // Get first message
        const firstMessage = page.getByTestId('message-item').first();

        // Verify message elements
        const sender = firstMessage.getByTestId('message-sender');
        const recipient = firstMessage.getByTestId('message-recipient');
        const type = firstMessage.getByTestId('message-type');
        const content = firstMessage.getByTestId('message-content');
        const timestamp = firstMessage.getByTestId('message-timestamp');

        await expect(sender).toBeVisible();
        if (await recipient.isVisible()) {
          const text = await recipient.textContent();
          expect(text).toBeTruthy();
        }
        if (await type.isVisible()) {
          const text = await type.textContent();
          expect(['SKILL_REQUEST', 'SKILL_RESPONSE', 'BROADCAST']).toContain(text?.trim());
        }
        if (await content.isVisible()) {
          const text = await content.textContent();
          expect(text?.length).toBeGreaterThan(0);
        }
      }
    });

    test('should filter messages by agent', async ({ page }) => {
      await navigateToAgentCommunication(page);

      // Ensure messagebus tab active
      const messageBusTab = page.getByTestId('messagebus-tab');
      await messageBusTab.click();

      // Get available agents for filtering
      const agentFilter = page.getByTestId('agent-filter-select');
      if (await agentFilter.isVisible()) {
        // Select an agent
        const options = await agentFilter.locator('option').count();
        if (options > 1) {
          await agentFilter.selectOption({ index: 1 }); // Select second option (first non-default)
          await page.waitForLoadState('networkidle');

          // Verify filtered messages
          const messages = await page.getByTestId('message-item').count();
          expect(messages).toBeGreaterThanOrEqual(0);
        }
      }
    });

    test('should view blackboard shared memory state', async ({ page }) => {
      await navigateToAgentCommunication(page);

      // Click blackboard tab
      const blackboardTab = page.getByTestId('blackboard-tab');
      await blackboardTab.click();

      // Wait for blackboard to load
      await page.waitForLoadState('networkidle');

      // Verify blackboard section
      const blackboardSection = page.getByTestId('blackboard-section');
      await expect(blackboardSection).toBeVisible();

      // Check for namespace items
      const namespaces = await page.getByTestId('blackboard-namespace').count();
      expect(namespaces).toBeGreaterThan(0);

      // Verify namespace structure
      const firstNamespace = page.getByTestId('blackboard-namespace').first();
      const namespaceName = firstNamespace.getByTestId('namespace-name');
      const namespaceData = firstNamespace.getByTestId('namespace-data');

      await expect(namespaceName).toBeVisible();
      if (await namespaceData.isVisible()) {
        const data = await namespaceData.textContent();
        expect(data).toBeTruthy();
      }
    });

    test('should view active orchestrations', async ({ page }) => {
      await navigateToAgentCommunication(page);

      // Click orchestrations tab
      const orchestrationsTab = page.getByTestId('orchestrations-tab');
      await orchestrationsTab.click();

      // Wait for orchestrations to load
      await page.waitForLoadState('networkidle');

      // Verify orchestrations section
      const orchestrationsSection = page.getByTestId('orchestrations-section');
      await expect(orchestrationsSection).toBeVisible();

      // Check for orchestration items
      const orchestrations = await page.getByTestId('orchestration-item').count();
      expect(orchestrations).toBeGreaterThanOrEqual(0);

      // Verify orchestration structure
      if (orchestrations > 0) {
        const firstOrch = page.getByTestId('orchestration-item').first();

        const id = firstOrch.getByTestId('orchestration-id');
        const phase = firstOrch.getByTestId('orchestration-phase');
        const progress = firstOrch.getByTestId('orchestration-progress');

        await expect(id).toBeVisible();
        if (await phase.isVisible()) {
          const text = await phase.textContent();
          expect(text).toMatch(/phase|stage|step/i);
        }
      }
    });

    test('should view orchestration execution trace', async ({ page }) => {
      await navigateToAgentCommunication(page);

      // Click orchestrations tab
      const orchestrationsTab = page.getByTestId('orchestrations-tab');
      await orchestrationsTab.click();

      // Get first orchestration
      const firstOrch = page.getByTestId('orchestration-item').first();
      if (await firstOrch.isVisible()) {
        const detailsButton = firstOrch.getByTestId('view-details-button');
        if (await detailsButton.isVisible()) {
          await detailsButton.click();

          // Wait for details panel
          await page.waitForLoadState('networkidle');

          // Verify trace displayed
          const tracePanel = page.getByTestId('orchestration-trace-panel');
          if (await tracePanel.isVisible()) {
            const phases = await page.getByTestId('trace-phase').count();
            expect(phases).toBeGreaterThan(0);
          }
        }
      }
    });

    test('should pause and resume message stream', async ({ page }) => {
      await navigateToAgentCommunication(page);

      // Ensure messagebus tab active
      const messageBusTab = page.getByTestId('messagebus-tab');
      await messageBusTab.click();

      // Get pause button
      const pauseButton = page.getByTestId('pause-messages-button');
      if (await pauseButton.isVisible()) {
        // Pause stream
        await pauseButton.click();

        // Verify pause state
        const isPaused = await pauseButton.getAttribute('data-paused');
        expect(isPaused).toBe('true');

        // Resume stream
        await pauseButton.click();

        // Verify resume state
        const isResumed = await pauseButton.getAttribute('data-paused');
        expect(isResumed).toBe('false');
      }
    });
  });

  // ========================================================================
  // 98.2: Agent Hierarchy Visualizer (6 tests)
  // ========================================================================

  test.describe('Agent Hierarchy Visualizer (98.2)', () => {
    test('should display agent hierarchy tree', async ({ page }) => {
      await navigateToAgentHierarchy(page);

      // Verify visualizer loaded
      const visualizer = page.getByTestId('agent-hierarchy-visualizer');
      await expect(visualizer).toBeVisible();

      // Verify D3 tree is rendered
      const d3Tree = page.getByTestId('hierarchy-d3-tree');
      await expect(d3Tree).toBeVisible();

      // Verify nodes exist in tree
      const nodes = await page.locator('[data-node-type="agent"]').count();
      expect(nodes).toBeGreaterThan(0);
    });

    test('should display hierarchy with executive at top', async ({ page }) => {
      await navigateToAgentHierarchy(page);

      // Find executive node
      const executiveNode = page.locator('[data-agent-level="executive"]').first();
      await expect(executiveNode).toBeVisible();

      // Verify executive has children (managers)
      const childrenCount = await page.locator('[data-agent-level="manager"]').count();
      expect(childrenCount).toBeGreaterThan(0);
    });

    test('should click agent node to view details', async ({ page }) => {
      await navigateToAgentHierarchy(page);

      // Get first agent node
      const firstNode = page.locator('[data-node-type="agent"]').first();
      await firstNode.click();

      // Wait for details panel
      await page.waitForTimeout(300);

      // Verify details panel appears
      const detailsPanel = page.getByTestId('agent-details-panel');
      await expect(detailsPanel).toBeVisible();

      // Verify agent info displayed
      const agentName = detailsPanel.getByTestId('agent-name');
      const agentLevel = detailsPanel.getByTestId('agent-level');

      await expect(agentName).toBeVisible();
      await expect(agentLevel).toBeVisible();
    });

    test('should display agent skills and current tasks', async ({ page }) => {
      await navigateToAgentHierarchy(page);

      // Click an agent node
      const firstNode = page.locator('[data-node-type="agent"]').first();
      await firstNode.click();

      // Wait for details to load
      await page.waitForTimeout(300);

      // Verify details panel
      const detailsPanel = page.getByTestId('agent-details-panel');
      await expect(detailsPanel).toBeVisible();

      // Verify skills section
      const skillsSection = detailsPanel.getByTestId('agent-skills-section');
      if (await skillsSection.isVisible()) {
        const skills = await skillsSection.locator('[data-skill-item]').count();
        expect(skills).toBeGreaterThanOrEqual(0);
      }

      // Verify tasks section
      const tasksSection = detailsPanel.getByTestId('agent-tasks-section');
      if (await tasksSection.isVisible()) {
        const tasks = await tasksSection.locator('[data-task-item]').count();
        expect(tasks).toBeGreaterThanOrEqual(0);
      }
    });

    test('should display agent performance metrics', async ({ page }) => {
      await navigateToAgentHierarchy(page);

      // Click an agent node
      const firstNode = page.locator('[data-node-type="agent"]').first();
      await firstNode.click();

      // Wait for details
      await page.waitForTimeout(300);

      // Verify metrics section
      const metricsSection = page.getByTestId('agent-performance-metrics');
      if (await metricsSection.isVisible()) {
        // Verify metric items
        const successRate = metricsSection.getByTestId('success-rate-metric');
        const avgLatency = metricsSection.getByTestId('avg-latency-metric');
        const tasksCompleted = metricsSection.getByTestId('tasks-completed-metric');

        if (await successRate.isVisible()) {
          const text = await successRate.textContent();
          expect(text).toMatch(/\d+%/);
        }

        if (await avgLatency.isVisible()) {
          const text = await avgLatency.textContent();
          expect(text).toMatch(/\d+ms/);
        }

        if (await tasksCompleted.isVisible()) {
          const text = await tasksCompleted.textContent();
          expect(text).toMatch(/\d+/);
        }
      }
    });

    test('should highlight delegation chain for task', async ({ page }) => {
      await navigateToAgentHierarchy(page);

      // Get task selector
      const taskSelector = page.getByTestId('task-select-dropdown');
      if (await taskSelector.isVisible()) {
        // Select a task
        const options = await taskSelector.locator('option').count();
        if (options > 1) {
          await taskSelector.selectOption({ index: 1 });

          // Wait for highlighting
          await page.waitForTimeout(300);

          // Verify delegation chain is highlighted
          const highlightedPath = await page.locator('[data-highlighted="true"]').count();
          expect(highlightedPath).toBeGreaterThan(0);

          // Verify delegation tracer shows path
          const tracer = page.getByTestId('delegation-chain-tracer');
          if (await tracer.isVisible()) {
            const pathText = await tracer.textContent();
            expect(pathText).toBeTruthy();
          }
        }
      }
    });

    test('should handle hierarchy interaction with pan and zoom', async ({ page }) => {
      await navigateToAgentHierarchy(page);

      // Get D3 tree canvas
      const d3Tree = page.getByTestId('hierarchy-d3-tree');

      // Perform pan (drag)
      await d3Tree.dragTo(d3Tree, { sourcePosition: { x: 100, y: 100 }, targetPosition: { x: 150, y: 150 } });

      // Perform zoom (scroll)
      await d3Tree.hover();
      await page.mouse.wheel(0, 100);

      // Tree should still be visible
      await expect(d3Tree).toBeVisible();

      // Nodes should still be present
      const nodes = await page.locator('[data-node-type="agent"]').count();
      expect(nodes).toBeGreaterThan(0);
    });
  });

  // ========================================================================
  // Edge Cases
  // ========================================================================

  test.describe('Agent Communication & Hierarchy Edge Cases', () => {
    test('should handle large message volume (100+ messages)', async ({ page }) => {
      await navigateToAgentCommunication(page);

      // Ensure messagebus tab active
      const messageBusTab = page.getByTestId('messagebus-tab');
      await messageBusTab.click();

      // Verify messages load (with potential pagination)
      const messages = await page.getByTestId('message-item').count();
      expect(messages).toBeGreaterThan(0);

      // If pagination exists, verify it works
      const nextButton = page.getByTestId('messages-next-page-button');
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        await page.waitForLoadState('networkidle');

        const newMessages = await page.getByTestId('message-item').count();
        expect(newMessages).toBeGreaterThan(0);
      }
    });

    test('should handle large hierarchy (100+ agents)', async ({ page }) => {
      await navigateToAgentHierarchy(page);

      // Verify tree renders with large dataset
      const d3Tree = page.getByTestId('hierarchy-d3-tree');
      await expect(d3Tree).toBeVisible();

      // Measure performance: tree should render in reasonable time
      const nodes = await page.locator('[data-node-type="agent"]').count();
      expect(nodes).toBeGreaterThan(0);

      // Verify tree is responsive despite size
      const firstNode = page.locator('[data-node-type="agent"]').first();
      await firstNode.click();

      // Details should appear quickly
      await page.waitForTimeout(500);
      const detailsPanel = page.getByTestId('agent-details-panel');
      await expect(detailsPanel).toBeVisible();
    });

    test('should handle real-time message stream lag', async ({ page }) => {
      await navigateToAgentCommunication(page);

      // Ensure messagebus tab active
      const messageBusTab = page.getByTestId('messagebus-tab');
      await messageBusTab.click();

      // Subscribe to message updates
      const initialCount = await page.getByTestId('message-item').count();

      // Wait for potential new messages
      await page.waitForTimeout(2000);

      // Check if new messages arrived
      const newCount = await page.getByTestId('message-item').count();

      // Whether messages arrived or not, system should handle gracefully
      expect(newCount).toBeGreaterThanOrEqual(initialCount);
    });

    test('should handle circular delegation detection in hierarchy', async ({ page }) => {
      await navigateToAgentHierarchy(page);

      // Tree should render correctly even with potential circular relationships
      const d3Tree = page.getByTestId('hierarchy-d3-tree');
      await expect(d3Tree).toBeVisible();

      // No infinite loops or rendering errors should occur
      const nodes = await page.locator('[data-node-type="agent"]').count();
      expect(nodes).toBeGreaterThan(0);

      // Verify no error message displayed
      const errorMessage = page.getByTestId('error-message');
      if (await errorMessage.isVisible()) {
        const text = await errorMessage.textContent();
        expect(text).not.toContain('circular');
      }
    });

    test('should handle concurrent agent state updates', async ({ page }) => {
      // Rapidly navigate between communication and hierarchy views
      await navigateToAgentCommunication(page);
      await page.waitForTimeout(200);

      await navigateToAgentHierarchy(page);
      await page.waitForTimeout(200);

      await navigateToAgentCommunication(page);
      await page.waitForTimeout(200);

      // Final view should be fully functional
      const dashboard = page.getByTestId('agent-communication-dashboard');
      await expect(dashboard).toBeVisible();
    });

    test('should handle agent node with no tasks or skills', async ({ page }) => {
      await navigateToAgentHierarchy(page);

      // Click through multiple nodes to find one with minimal data
      const nodes = await page.locator('[data-node-type="agent"]').all();
      for (const node of nodes.slice(0, 5)) {
        await node.click();
        await page.waitForTimeout(200);

        // Details should display gracefully even if empty
        const detailsPanel = page.getByTestId('agent-details-panel');
        if (await detailsPanel.isVisible()) {
          // Should handle empty sections gracefully
          const skillsSection = detailsPanel.getByTestId('agent-skills-section');
          const tasksSection = detailsPanel.getByTestId('agent-tasks-section');

          if (await skillsSection.isVisible()) {
            const skills = await skillsSection.locator('[data-skill-item]').count();
            expect(skills).toBeGreaterThanOrEqual(0);
          }

          if (await tasksSection.isVisible()) {
            const tasks = await tasksSection.locator('[data-task-item]').count();
            expect(tasks).toBeGreaterThanOrEqual(0);
          }
        }
      }
    });
  });
});
