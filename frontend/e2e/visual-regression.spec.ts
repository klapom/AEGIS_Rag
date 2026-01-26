/**
 * Visual Regression Testing Suite - Sprint 120 Feature 120.5
 *
 * Comprehensive visual regression tests for AEGIS RAG frontend
 * using Playwright's built-in toHaveScreenshot() API
 *
 * Features:
 * - Baseline screenshots of key pages (welcome, chat, admin)
 * - Component-level visual testing (buttons, inputs, panels)
 * - Responsive layout testing (mobile, tablet, desktop)
 * - Dynamic state testing (hover, focus, disabled states)
 * - Dark mode visual comparison
 *
 * Updating baselines after intentional UI changes:
 *   npx playwright test visual-regression.spec.ts --update-snapshots
 *
 * Running only visual tests:
 *   npx playwright test visual-regression.spec.ts
 *
 * Running with verbose output:
 *   npx playwright test visual-regression.spec.ts --reporter=verbose
 */

import { test, expect } from './fixtures';
import { Page, Locator } from '@playwright/test';

/**
 * Visual regression test configuration
 */
const VISUAL_CONFIG = {
  // Pixel difference threshold for full page comparisons
  fullPageThreshold: 0.02, // 2% - allows minor rendering differences
  // Pixel difference threshold for component comparisons
  componentThreshold: 0.01, // 1% - stricter for components
  // Wait time for animations to complete
  animationWaitMs: 500,
  // Mask dynamic content by default
  defaultMasks: [
    '[data-testid*="timestamp"]',
    '[data-testid*="timing"]',
    '.animate-spin',
    '.animate-pulse',
  ],
};

/**
 * Helper function to capture and compare screenshots
 */
async function capturePageScreenshot(
  page: Page,
  name: string,
  options: {
    fullPage?: boolean;
    mask?: string[];
    waitMs?: number;
  } = {}
): Promise<void> {
  const {
    fullPage = false,
    mask = [],
    waitMs = VISUAL_CONFIG.animationWaitMs,
  } = options;

  // Wait for animations to settle
  await page.waitForTimeout(waitMs);

  // Combine default masks with custom ones
  const allMasks = [...VISUAL_CONFIG.defaultMasks, ...mask];

  // Take screenshot with comparison
  await expect(page).toHaveScreenshot(`${name}.png`, {
    fullPage,
    mask: allMasks.map(selector => page.locator(selector)),
    threshold: VISUAL_CONFIG.fullPageThreshold,
    animations: 'disabled',
  });
}

/**
 * Helper function to capture component screenshots
 */
async function captureComponentScreenshot(
  locator: Locator,
  name: string,
  options: {
    mask?: string[];
    waitMs?: number;
  } = {}
): Promise<void> {
  const { mask = [], waitMs = VISUAL_CONFIG.animationWaitMs } = options;

  // Wait for animations
  await locator.page().waitForTimeout(waitMs);

  // Combine masks
  const allMasks = [...VISUAL_CONFIG.defaultMasks, ...mask];

  // Take screenshot
  await expect(locator).toHaveScreenshot(`${name}.png`, {
    mask: allMasks.map(selector => locator.page().locator(selector)),
    threshold: VISUAL_CONFIG.componentThreshold,
    animations: 'disabled',
  });
}

/**
 * Landing/Welcome Page Visual Regression Tests
 * Tests the initial landing page with no conversation context
 */
test.describe('Visual Regression - Landing Page', { tag: '@visual' }, () => {
  /**
   * TC-VR-001: Landing page default state
   * Captures baseline of landing page layout
   */
  test('TC-VR-001: landing page renders consistently', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for initial page render
    await page.waitForTimeout(1000);

    // Capture full page screenshot
    await capturePageScreenshot(page, 'landing-page-default', {
      fullPage: true,
    });
  });

  /**
   * TC-VR-002: Logo and header area
   * Tests header/logo rendering consistency
   */
  test('TC-VR-002: landing page header layout', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Capture viewport-height screenshot (typical above-fold)
    await capturePageScreenshot(page, 'landing-page-header', {
      fullPage: false,
    });
  });

  /**
   * TC-VR-003: Message input area
   * Tests chat input field styling and layout
   */
  test('TC-VR-003: message input component consistency', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Find message input
    const messageInput = page.locator('[data-testid="message-input"]');
    if (await messageInput.isVisible().catch(() => false)) {
      await captureComponentScreenshot(messageInput, 'message-input-default');
    } else {
      // Fallback: capture textarea or input
      const textarea = page.locator('textarea').first();
      if (await textarea.isVisible().catch(() => false)) {
        await captureComponentScreenshot(textarea, 'message-input-default');
      }
    }
  });

  /**
   * TC-VR-004: Send button styling
   * Tests send button appearance and styling
   */
  test('TC-VR-004: send button styling consistency', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const sendButton = page.locator('[data-testid="send-button"]');
    if (await sendButton.isVisible().catch(() => false)) {
      await captureComponentScreenshot(sendButton, 'send-button-default');
    }
  });

  /**
   * TC-VR-005: Welcome message/empty state
   * Tests empty conversation state UI
   */
  test('TC-VR-005: empty conversation state layout', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Capture the messages container in empty state
    const messagesContainer = page.locator('[data-testid="messages-container"]');
    if (await messagesContainer.isVisible().catch(() => false)) {
      await captureComponentScreenshot(
        messagesContainer,
        'empty-conversation-state'
      );
    }
  });
});

/**
 * Chat Interface Visual Regression Tests
 * Tests chat UI with messages and interactions
 */
test.describe('Visual Regression - Chat Interface', { tag: '@visual' }, () => {
  /**
   * TC-VR-010: Chat interface with single message
   * Verifies layout remains consistent with messages
   */
  test('TC-VR-010: chat interface with message', async ({ chatPage }) => {
    const { page } = chatPage;

    // Verify page loaded
    await page.waitForLoadState('networkidle');

    // Check if messages container exists and is visible
    const messagesContainer = page.locator('[data-testid="messages-container"]');
    if (await messagesContainer.isVisible().catch(() => false)) {
      // Capture the chat interface
      await capturePageScreenshot(page, 'chat-interface-default', {
        fullPage: true,
      });
    }
  });

  /**
   * TC-VR-011: Sidebar navigation layout
   * Tests sidebar rendering consistency
   */
  test('TC-VR-011: sidebar navigation consistency', async ({ chatPage }) => {
    const { page } = chatPage;

    // Look for sidebar
    const sidebar = page.locator('[data-testid*="sidebar"]').first();
    const navElement = page.locator('nav').first();
    const target = (await sidebar.isVisible().catch(() => false))
      ? sidebar
      : navElement;

    if (await target.isVisible().catch(() => false)) {
      await captureComponentScreenshot(target, 'sidebar-navigation');
    }
  });

  /**
   * TC-VR-012: Conversation history list
   * Tests history/conversation list rendering
   */
  test('TC-VR-012: conversation history rendering', async ({ chatPage }) => {
    const { page } = chatPage;

    // Look for conversation list
    const conversationList = page.locator('[data-testid="conversation-list"]');
    if (await conversationList.isVisible().catch(() => false)) {
      await captureComponentScreenshot(
        conversationList,
        'conversation-history-list'
      );
    }
  });

  /**
   * TC-VR-013: Reasoning panel when visible
   * Tests reasoning/metadata panel layout
   */
  test('TC-VR-013: reasoning panel layout', async ({ chatPage }) => {
    const { page } = chatPage;

    // Look for reasoning panel
    const reasoningPanel = page.locator('[data-testid="reasoning-panel"]');
    if (await reasoningPanel.isVisible().catch(() => false)) {
      await captureComponentScreenshot(reasoningPanel, 'reasoning-panel');
    } else {
      // Look for alternative panel names
      const alternativePanel = page.locator(
        '[data-testid*="panel"], [data-testid*="metadata"]'
      ).first();
      if (await alternativePanel.isVisible().catch(() => false)) {
        await captureComponentScreenshot(alternativePanel, 'metadata-panel');
      }
    }
  });

  /**
   * TC-VR-014: Message container scrolling area
   * Tests scrollable messages area styling
   */
  test('TC-VR-014: messages container styling', async ({ chatPage }) => {
    const { page } = chatPage;

    const messagesContainer = page.locator('[data-testid="messages-container"]');
    if (await messagesContainer.isVisible().catch(() => false)) {
      await captureComponentScreenshot(
        messagesContainer,
        'messages-container-styled'
      );
    }
  });
});

/**
 * Settings Page Visual Regression Tests
 * Tests admin/settings interface consistency
 */
test.describe('Visual Regression - Settings Page', { tag: '@visual' }, () => {
  /**
   * TC-VR-020: Settings page default layout
   * Captures settings page baseline
   */
  test('TC-VR-020: settings page layout consistency', async ({
    settingsPage,
  }) => {
    const { page } = settingsPage;

    // Wait for settings to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    // Capture full page
    await capturePageScreenshot(page, 'settings-page-default', {
      fullPage: true,
    });
  });

  /**
   * TC-VR-021: Settings form fields
   * Tests form input rendering
   */
  test('TC-VR-021: settings form fields layout', async ({ settingsPage }) => {
    const { page } = settingsPage;

    // Find form
    const form = page.locator('form').first();
    if (await form.isVisible().catch(() => false)) {
      await captureComponentScreenshot(form, 'settings-form');
    }
  });

  /**
   * TC-VR-022: Settings buttons/actions
   * Tests action button styling
   */
  test('TC-VR-022: settings action buttons', async ({ settingsPage }) => {
    const { page } = settingsPage;

    // Find buttons container
    const buttonContainer = page.locator('[data-testid*="button"]').first();
    const actionArea = page.locator('footer, [role="contentinfo"]').first();

    const target = (await buttonContainer.isVisible().catch(() => false))
      ? buttonContainer
      : actionArea;

    if (await target.isVisible().catch(() => false)) {
      await captureComponentScreenshot(target, 'settings-actions');
    }
  });
});

/**
 * Admin Dashboard Visual Regression Tests
 * Tests admin interface consistency
 */
test.describe('Visual Regression - Admin Dashboard', { tag: '@visual' }, () => {
  /**
   * TC-VR-030: Admin dashboard layout
   * Captures admin page baseline
   */
  test('TC-VR-030: admin dashboard renders consistently', async ({
    adminDashboardPage,
  }) => {
    const { page } = adminDashboardPage;

    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    // Capture full page
    await capturePageScreenshot(page, 'admin-dashboard-default', {
      fullPage: true,
    });
  });

  /**
   * TC-VR-031: Admin tabs/navigation
   * Tests admin tab navigation rendering
   */
  test('TC-VR-031: admin tabs navigation layout', async ({
    adminDashboardPage,
  }) => {
    const { page } = adminDashboardPage;

    // Find tabs or nav
    const tabs = page.locator('[role="tablist"]').first();
    if (await tabs.isVisible().catch(() => false)) {
      await captureComponentScreenshot(tabs, 'admin-tabs-navigation');
    }
  });
});

/**
 * Responsive Design Visual Regression Tests
 * Tests layout consistency across different viewport sizes
 */
test.describe('Visual Regression - Responsive Design', { tag: '@visual' }, () => {
  const viewports = [
    { name: 'mobile', width: 375, height: 667 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'desktop', width: 1920, height: 1080 },
  ];

  /**
   * TC-VR-040: Landing page responsive layout
   * Tests landing page at multiple viewport sizes
   */
  test('TC-VR-040: landing page responsive layout', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    for (const viewport of viewports) {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await page.waitForTimeout(500); // Allow layout to settle

      await capturePageScreenshot(
        page,
        `landing-page-responsive-${viewport.name}`,
        { fullPage: false }
      );
    }
  });

  /**
   * TC-VR-041: Chat interface responsive layout
   * Tests chat UI responsiveness
   */
  test('TC-VR-041: chat interface responsive layout', async ({ chatPage }) => {
    const { page } = chatPage;

    for (const viewport of viewports) {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await page.waitForTimeout(500);

      await capturePageScreenshot(
        page,
        `chat-interface-responsive-${viewport.name}`,
        { fullPage: false }
      );
    }
  });

  /**
   * TC-VR-042: Message input responsive sizing
   * Tests input field responsiveness
   */
  test('TC-VR-042: message input responsive sizing', async ({ chatPage }) => {
    const { page } = chatPage;

    const messageInput = page.locator('[data-testid="message-input"]');
    if (!(await messageInput.isVisible().catch(() => false))) {
      test.skip();
    }

    for (const viewport of viewports) {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await page.waitForTimeout(300);

      await captureComponentScreenshot(
        messageInput,
        `message-input-responsive-${viewport.name}`
      );
    }
  });
});

/**
 * Component State Visual Regression Tests
 * Tests UI components in different states (hover, focus, disabled)
 */
test.describe('Visual Regression - Component States', { tag: '@visual' }, () => {
  /**
   * TC-VR-050: Send button state variations
   * Tests button in default, hover, and focus states
   */
  test('TC-VR-050: send button state variations', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const sendButton = page.locator('[data-testid="send-button"]');
    if (!(await sendButton.isVisible().catch(() => false))) {
      test.skip();
    }

    // Default state
    await captureComponentScreenshot(sendButton, 'button-default-state');

    // Hover state
    await sendButton.hover();
    await page.waitForTimeout(300);
    await captureComponentScreenshot(sendButton, 'button-hover-state');

    // Focus state
    await sendButton.focus();
    await page.waitForTimeout(300);
    await captureComponentScreenshot(sendButton, 'button-focus-state');
  });

  /**
   * TC-VR-051: Message input focus state
   * Tests input field appearance when focused
   */
  test('TC-VR-051: message input focus state', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const messageInput = page.locator('[data-testid="message-input"]');
    if (!(await messageInput.isVisible().catch(() => false))) {
      test.skip();
    }

    // Default state
    await captureComponentScreenshot(
      messageInput,
      'input-default-state'
    );

    // Focused state
    await messageInput.focus();
    await page.waitForTimeout(300);
    await captureComponentScreenshot(
      messageInput,
      'input-focused-state'
    );

    // With placeholder text visible
    await messageInput.fill('Test query');
    await page.waitForTimeout(300);
    await captureComponentScreenshot(
      messageInput,
      'input-with-text-state'
    );
  });

  /**
   * TC-VR-052: Navigation link active states
   * Tests navigation styling consistency
   */
  test('TC-VR-052: navigation link states', async ({ chatPage }) => {
    const { page } = chatPage;

    // Find navigation links
    const navLinks = page.locator('a[data-testid*="nav"], nav a').first();
    if (!(await navLinks.isVisible().catch(() => false))) {
      test.skip();
    }

    // Default state
    await captureComponentScreenshot(navLinks, 'nav-link-default');

    // Hover state
    await navLinks.hover();
    await page.waitForTimeout(300);
    await captureComponentScreenshot(navLinks, 'nav-link-hover');
  });
});

/**
 * Dark Mode Visual Regression Tests
 * Tests UI appearance in dark mode if supported
 */
test.describe('Visual Regression - Dark Mode', { tag: '@visual' }, () => {
  /**
   * TC-VR-060: Dark mode landing page
   * Captures landing page in dark theme
   */
  test('TC-VR-060: landing page dark mode', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check if theme toggle exists
    const themeToggle = page.locator('[data-testid*="theme"], [data-testid*="dark"]');
    if (!(await themeToggle.first().isVisible().catch(() => false))) {
      test.skip();
    }

    // Click theme toggle if visible
    const toggle = themeToggle.first();
    if (await toggle.isVisible().catch(() => false)) {
      await toggle.click();
      await page.waitForTimeout(500); // Allow theme transition

      await capturePageScreenshot(page, 'landing-page-dark-mode', {
        fullPage: true,
      });
    } else {
      test.skip();
    }
  });

  /**
   * TC-VR-061: Chat interface dark mode
   * Tests chat UI in dark mode
   */
  test('TC-VR-061: chat interface dark mode', async ({ chatPage }) => {
    const { page } = chatPage;

    const themeToggle = page.locator('[data-testid*="theme"], [data-testid*="dark"]').first();
    if (!(await themeToggle.isVisible().catch(() => false))) {
      test.skip();
    }

    await themeToggle.click();
    await page.waitForTimeout(500);

    await capturePageScreenshot(page, 'chat-interface-dark-mode', {
      fullPage: true,
    });
  });
});

/**
 * Layout Consistency Tests
 * Tests that critical layout elements remain properly positioned
 */
test.describe('Visual Regression - Layout Consistency', { tag: '@visual' }, () => {
  /**
   * TC-VR-070: Three-column layout alignment
   * Tests main/sidebar/panel alignment
   */
  test('TC-VR-070: three-column layout consistency', async ({ chatPage }) => {
    const { page } = chatPage;

    // Set standard desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    // Capture full layout
    await capturePageScreenshot(page, 'layout-three-column', {
      fullPage: false,
    });
  });

  /**
   * TC-VR-071: Footer positioning
   * Tests footer remains properly positioned
   */
  test('TC-VR-071: footer positioning consistency', async ({ page }) => {
    await page.goto('/');
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForLoadState('networkidle');

    const footer = page.locator('footer, [data-testid*="footer"]').first();
    if (await footer.isVisible().catch(() => false)) {
      await captureComponentScreenshot(footer, 'footer-positioning');
    }
  });

  /**
   * TC-VR-072: Header positioning
   * Tests header remains properly positioned
   */
  test('TC-VR-072: header positioning consistency', async ({ page }) => {
    await page.goto('/');
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForLoadState('networkidle');

    const header = page.locator('header, [data-testid*="header"]').first();
    if (await header.isVisible().catch(() => false)) {
      await captureComponentScreenshot(header, 'header-positioning');
    }
  });
});

/**
 * Typography and Text Rendering Tests
 * Tests font rendering consistency across platforms
 */
test.describe('Visual Regression - Typography', { tag: '@visual' }, () => {
  /**
   * TC-VR-080: Heading typography
   * Tests heading font rendering consistency
   */
  test('TC-VR-080: heading typography consistency', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h1, h2').first();
    if (await heading.isVisible().catch(() => false)) {
      await captureComponentScreenshot(heading, 'heading-typography');
    }
  });

  /**
   * TC-VR-081: Body text rendering
   * Tests paragraph/body text rendering
   */
  test('TC-VR-081: body text rendering', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const paragraph = page.locator('p').first();
    if (await paragraph.isVisible().catch(() => false)) {
      await captureComponentScreenshot(paragraph, 'body-text-rendering');
    }
  });

  /**
   * TC-VR-082: Button text rendering
   * Tests button text appearance
   */
  test('TC-VR-082: button text rendering', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const button = page.locator('button').first();
    if (await button.isVisible().catch(() => false)) {
      await captureComponentScreenshot(button, 'button-text-rendering');
    }
  });
});
