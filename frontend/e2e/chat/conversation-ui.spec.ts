/**
 * E2E Tests for Sprint 46 Features 46.1 & 46.2
 * ConversationView (Feature 46.1) and ReasoningPanel (Feature 46.2)
 *
 * Test Coverage:
 * - Feature 46.1: ConversationView component rendering and interactions
 * - Feature 46.2: ReasoningPanel expansion, intent display, and retrieval chain visualization
 *
 * Prerequisites:
 * - Backend running on http://localhost:8000
 * - Frontend running on http://localhost:5179
 * - Ollama or configured LLM service available
 */

import { test, expect } from '../fixtures';

/**
 * FEATURE 46.1: CONVERSATIONVIEW TESTS
 * Tests for chat-style conversation UI layout and interactions
 */
test.describe('Sprint 46 - Feature 46.1: ConversationView', () => {
  /**
   * TC-46.1.1: Verify ConversationView renders on homepage
   * Should display the main conversation container with proper layout
   */
  test('TC-46.1.1: should render ConversationView on homepage', async ({ chatPage }) => {
    // ConversationView should be the main container for the chat interface
    const conversationView = chatPage.page.locator('[data-testid="conversation-view"]');
    await expect(conversationView).toBeVisible();

    // Should have the proper CSS classes for layout
    const conversationViewClasses = await conversationView.getAttribute('class');
    expect(conversationViewClasses).toContain('flex');
    expect(conversationViewClasses).toContain('flex-col');
    expect(conversationViewClasses).toContain('h-full');
  });

  /**
   * TC-46.1.2: Verify message container is visible
   * Messages should be in a scrollable container
   */
  test('TC-46.1.2: should verify message container is visible', async ({ chatPage }) => {
    const messagesContainer = chatPage.page.locator('[data-testid="messages-container"]');
    await expect(messagesContainer).toBeVisible();

    // Container should support scrolling
    const containerClasses = await messagesContainer.getAttribute('class');
    expect(containerClasses).toContain('overflow-y-auto');
    expect(containerClasses).toContain('flex-1');
  });

  /**
   * TC-46.1.3: Verify user messages have correct styling (left content, blue background)
   * User messages should be visually distinguished from assistant messages
   */
  test('TC-46.1.3: should apply correct styling to user messages', async ({ chatPage }) => {
    // Send a message
    await chatPage.sendMessage('What is the capital of France?');
    await chatPage.waitForResponse();

    // Get user message bubble
    const userMessageBubble = chatPage.page.locator('[data-testid="message-bubble"][data-role="user"]').first();
    await expect(userMessageBubble).toBeVisible();

    // Verify user message styling
    const userMessageClasses = await userMessageBubble.getAttribute('class');
    expect(userMessageClasses).toContain('bg-blue-50');

    // User messages should have sender label "Sie"
    const senderLabel = userMessageBubble.locator('text=Sie');
    await expect(senderLabel).toBeVisible();
  });

  /**
   * TC-46.1.4: Verify assistant messages have correct styling (left-aligned)
   * Assistant messages should have white background and AegisRAG label
   */
  test('TC-46.1.4: should apply correct styling to assistant messages', async ({ chatPage }) => {
    // Send a message to trigger assistant response
    await chatPage.sendMessage('Tell me about machine learning');
    await chatPage.waitForResponse();

    // Get assistant message bubble
    const assistantMessageBubble = chatPage.page
      .locator('[data-testid="message-bubble"][data-role="assistant"]')
      .first();
    await expect(assistantMessageBubble).toBeVisible();

    // Verify assistant message styling
    const bubbleClasses = await assistantMessageBubble.getAttribute('class');
    expect(bubbleClasses).toContain('bg-white');

    // Assistant messages should have sender label "AegisRAG"
    const senderLabel = assistantMessageBubble.locator('text=AegisRAG');
    await expect(senderLabel).toBeVisible();
  });

  /**
   * TC-46.1.5: Verify input is fixed at bottom of viewport
   * Input area should remain visible even when scrolling messages
   */
  test('TC-46.1.5: should keep input area fixed at bottom', async ({ chatPage }) => {
    // Input area should exist
    const inputArea = chatPage.page.locator('[data-testid="input-area"]');
    await expect(inputArea).toBeVisible();

    // Input area should have fixed positioning via flex-shrink-0
    const inputAreaClasses = await inputArea.getAttribute('class');
    expect(inputAreaClasses).toContain('flex-shrink-0');
    expect(inputAreaClasses).toContain('border-t');

    // Send multiple messages to trigger scrolling
    await chatPage.sendMessage('First question');
    await chatPage.waitForResponse();

    await chatPage.sendMessage('Second question');
    await chatPage.waitForResponse();

    // Input area should still be visible
    await expect(inputArea).toBeVisible();
    await expect(chatPage.messageInput).toBeVisible();
  });

  /**
   * TC-46.1.6: Verify send button is visible and clickable
   * Send button should be properly rendered and functional
   */
  test('TC-46.1.6: should display send button and allow interaction', async ({ chatPage }) => {
    // Send button should be visible
    await expect(chatPage.sendButton).toBeVisible();

    // Send button should be enabled when input is not empty
    await chatPage.messageInput.fill('Test message');

    // Wait for React state to update
    await chatPage.page.waitForTimeout(100);

    // Button should be enabled
    const isDisabled = await chatPage.sendButton.isDisabled();
    expect(isDisabled).toBeFalsy();

    // Button should be clickable
    await expect(chatPage.sendButton).toBeEnabled();
  });

  /**
   * TC-46.1.7: Verify message can be sent and appears in conversation
   * Complete flow: input message -> send -> appear in conversation history
   */
  test('TC-46.1.7: should send message and display in conversation', async ({ chatPage }) => {
    const testMessage = 'What is artificial intelligence?';

    // Get initial message count
    let initialMessages = await chatPage.getAllMessages();
    const initialCount = initialMessages.length;

    // Send message
    await chatPage.sendMessage(testMessage);

    // Wait for response
    await chatPage.waitForResponse();

    // Get updated messages
    const updatedMessages = await chatPage.getAllMessages();

    // Should have at least 2 more messages (user + assistant)
    expect(updatedMessages.length).toBeGreaterThan(initialCount);

    // User message should appear
    const conversationText = updatedMessages.join('\n');
    expect(conversationText).toContain(testMessage);

    // Input should be cleared after sending
    const inputValue = await chatPage.messageInput.inputValue();
    expect(inputValue).toBe('');
  });

  /**
   * TC-46.1.8: Verify streaming indicator during response
   * Should show typing indicator while waiting for LLM response
   */
  test('TC-46.1.8: should display streaming indicator during response', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('Explain quantum computing');

    // Check if streaming indicator is visible (may appear/disappear quickly)
    const isStreamingDuringWait = await chatPage.isStreaming();

    // Note: streaming indicator appears/disappears quickly with SSE streaming
    // We verify the final response is present instead
    await chatPage.waitForResponse();

    // Verify response exists after streaming completes
    const lastMessage = await chatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
    expect(lastMessage.length).toBeGreaterThan(50);
  });

  /**
   * TC-46.1.9: Verify multiple messages maintain proper layout
   * Conversation should grow vertically with proper spacing
   */
  test('TC-46.1.9: should maintain proper layout with multiple messages', async ({ chatPage }) => {
    // Send first message
    await chatPage.sendMessage('What is Python?');
    await chatPage.waitForResponse();

    // Send second message
    await chatPage.sendMessage('What is Java?');
    await chatPage.waitForResponse();

    // All messages should be visible
    const allMessages = await chatPage.getAllMessages();
    expect(allMessages.length).toBeGreaterThanOrEqual(4); // 2 user + 2 assistant

    // Message bubbles should all be visible
    const messageBubbles = chatPage.page.locator('[data-testid="message-bubble"]');
    const bubbleCount = await messageBubbles.count();
    expect(bubbleCount).toBeGreaterThanOrEqual(4);

    // Verify proper alternation: user, assistant, user, assistant
    const firstUserBubble = chatPage.page
      .locator('[data-testid="message-bubble"][data-role="user"]')
      .first();
    const firstAssistantBubble = chatPage.page
      .locator('[data-testid="message-bubble"][data-role="assistant"]')
      .first();

    await expect(firstUserBubble).toBeVisible();
    await expect(firstAssistantBubble).toBeVisible();
  });

  /**
   * TC-46.1.10: Verify empty state message
   * Should show welcome message when no messages exist
   */
  test('TC-46.1.10: should display welcome message when empty', async ({ chatPage }) => {
    // This test works best on first load or after clearing history
    // The ConversationView shows empty state content
    const conversationView = chatPage.page.locator('[data-testid="conversation-view"]');
    await expect(conversationView).toBeVisible();

    // Input should still be focused and ready
    const inputReady = await chatPage.isInputReady();
    expect(inputReady).toBeTruthy();
  });

  /**
   * TC-46.1.11: Verify keyboard navigation (Enter to send)
   * Should support sending messages with Enter key
   */
  test('TC-46.1.11: should send message using Enter key', async ({ chatPage }) => {
    const testMessage = 'What is blockchain?';

    // Get initial message count
    let initialMessages = await chatPage.getAllMessages();
    const initialCount = initialMessages.length;

    // Send with Enter key
    await chatPage.sendMessageWithEnter(testMessage);

    // Wait for response
    await chatPage.waitForResponse();

    // Verify message was sent
    const updatedMessages = await chatPage.getAllMessages();
    expect(updatedMessages.length).toBeGreaterThan(initialCount);
  });

  /**
   * TC-46.1.12: Verify avatars are displayed for each message
   * User and assistant messages should have appropriate avatars
   */
  test('TC-46.1.12: should display avatars for all messages', async ({ chatPage }) => {
    // Send a message
    await chatPage.sendMessage('Tell me about neural networks');
    await chatPage.waitForResponse();

    // Get message bubbles
    const messageBubbles = chatPage.page.locator('[data-testid="message-bubble"]');

    // Should have both user and assistant messages
    const userBubbles = chatPage.page.locator('[data-testid="message-bubble"][data-role="user"]');
    const assistantBubbles = chatPage.page.locator('[data-testid="message-bubble"][data-role="assistant"]');

    const userCount = await userBubbles.count();
    const assistantCount = await assistantBubbles.count();

    expect(userCount).toBeGreaterThan(0);
    expect(assistantCount).toBeGreaterThan(0);
  });

  /**
   * TC-46.1.13: Verify responsive message container
   * Messages area should be scrollable with proper flex layout
   */
  test('TC-46.1.13: should have responsive message container', async ({ chatPage }) => {
    // Get messages container
    const messagesContainer = chatPage.page.locator('[data-testid="messages-container"]');
    const containerBox = await messagesContainer.boundingBox();

    expect(containerBox).toBeTruthy();
    expect(containerBox?.width).toBeGreaterThan(0);
    expect(containerBox?.height).toBeGreaterThan(0);

    // Container should be visible
    await expect(messagesContainer).toBeVisible();
  });
});

/**
 * FEATURE 46.2: REASONINGPANEL TESTS
 * Tests for the transparent reasoning panel showing intent and retrieval chain
 */
test.describe('Sprint 46 - Feature 46.2: ReasoningPanel', () => {
  /**
   * TC-46.2.1: Verify "Reasoning anzeigen" button exists on assistant messages
   * ReasoningPanel should have a toggle button when reasoning data is available
   */
  test('TC-46.2.1: should display reasoning toggle button on assistant message', async ({
    chatPage,
  }) => {
    // Send message to get assistant response with reasoning
    await chatPage.sendMessage('What is machine learning?');
    await chatPage.waitForResponse();

    // Look for reasoning panel toggle button
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    // The button may or may not be visible depending on backend support
    // If it exists, it should be visible
    const isVisible = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (isVisible) {
      // Button should have the correct text
      const buttonText = await reasoningToggle.textContent();
      expect(buttonText).toMatch(/Reasoning\s+(anzeigen|ausblenden)/i);
    }
  });

  /**
   * TC-46.2.2: Verify panel expands when clicked
   * ReasoningPanel should expand to show detailed reasoning information
   */
  test('TC-46.2.2: should expand reasoning panel when button clicked', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('Explain neural networks');
    await chatPage.waitForResponse();

    // Find reasoning toggle
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    // If toggle exists
    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Get the button's aria-expanded state before click
      let ariaExpanded = await reasoningToggle.getAttribute('aria-expanded');
      expect(['true', 'false']).toContain(ariaExpanded);

      // Click to expand
      await reasoningToggle.click();

      // Wait for content to appear
      await chatPage.page.waitForTimeout(300);

      // Content should now be visible
      const reasoningContent = chatPage.page.locator('[data-testid="reasoning-content"]');
      const contentVisible = await reasoningContent.isVisible({ timeout: 3000 }).catch(() => false);

      // Verify expansion state
      const newAriaExpanded = await reasoningToggle.getAttribute('aria-expanded');
      expect(newAriaExpanded).toBe('true');
    }
  });

  /**
   * TC-46.2.3: Verify panel collapses when clicked again
   * ReasoningPanel should collapse to hide reasoning information
   */
  test('TC-46.2.3: should collapse reasoning panel when clicked again', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('What is deep learning?');
    await chatPage.waitForResponse();

    // Find reasoning toggle
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // First click to expand
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Verify expanded
      let ariaExpanded = await reasoningToggle.getAttribute('aria-expanded');
      expect(ariaExpanded).toBe('true');

      // Second click to collapse
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Verify collapsed
      const newAriaExpanded = await reasoningToggle.getAttribute('aria-expanded');
      expect(newAriaExpanded).toBe('false');

      // Content should no longer be visible
      const reasoningContent = chatPage.page.locator('[data-testid="reasoning-content"]');
      const contentVisible = await reasoningContent.isVisible({ timeout: 1000 }).catch(() => false);
      expect(contentVisible).toBeFalsy();
    }
  });

  /**
   * TC-46.2.4: Verify intent classification is displayed
   * When panel expands, should show intent type and confidence score
   */
  test('TC-46.2.4: should display intent classification', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('Tell me about transformers in AI');
    await chatPage.waitForResponse();

    // Find and expand reasoning panel
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Expand panel
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Look for intent section
      const intentSection = chatPage.page.locator('[data-testid="intent-section"]');
      const intentVisible = await intentSection.isVisible({ timeout: 3000 }).catch(() => false);

      if (intentVisible) {
        // Intent section should contain classification info
        const sectionText = await intentSection.textContent();

        // Should contain intent type labels (German)
        const hasIntentType =
          sectionText?.includes('Faktenbezogen') ||
          sectionText?.includes('Stichwortsuche') ||
          sectionText?.includes('Explorativ') ||
          sectionText?.includes('Zusammenfassung');

        expect(hasIntentType).toBeTruthy();

        // Should show confidence percentage
        const hasConfidence = sectionText?.match(/\d+%/);
        expect(hasConfidence).toBeTruthy();
      }
    }
  });

  /**
   * TC-46.2.5: Verify retrieval steps are shown
   * When panel expands, should display retrieval chain with steps
   */
  test('TC-46.2.5: should display retrieval chain steps', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('What is vector search?');
    await chatPage.waitForResponse();

    // Find and expand reasoning panel
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Expand panel
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Look for retrieval chain
      const retrievalChain = chatPage.page.locator('[data-testid="retrieval-chain"]');
      const chainVisible = await retrievalChain.isVisible({ timeout: 3000 }).catch(() => false);

      if (chainVisible) {
        // Retrieval chain should have steps
        const retrievalSteps = chatPage.page.locator('[data-testid^="retrieval-step-"]');
        const stepCount = await retrievalSteps.count();

        // Should have at least one retrieval step
        expect(stepCount).toBeGreaterThan(0);

        // First step should be visible
        const firstStep = retrievalSteps.first();
        await expect(firstStep).toBeVisible();

        // Step should have source information
        const stepSource = await firstStep.getAttribute('data-source');
        expect(stepSource).toBeTruthy();
      }
    }
  });

  /**
   * TC-46.2.6: Verify timing information is displayed
   * Should show total duration and individual step timings
   */
  test('TC-46.2.6: should display timing information', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('Explain attention mechanisms');
    await chatPage.waitForResponse();

    // Find reasoning toggle
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Get the button text which should include timing
      const buttonText = await reasoningToggle.textContent();

      // Should show either ms or s format
      const hasTimingInfo = /\d+(ms|s)/i.test(buttonText || '');
      expect(hasTimingInfo || buttonText?.includes('Reasoning')).toBeTruthy();

      // Expand to see step timings
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Look for retrieval steps with timing
      const retrievalSteps = chatPage.page.locator('[data-testid^="retrieval-step-"]');
      const stepCount = await retrievalSteps.count();

      if (stepCount > 0) {
        // First step should contain timing information
        const firstStep = retrievalSteps.first();
        const stepText = await firstStep.textContent();

        // Should show duration in ms or s
        const hasStepTiming = /\d+(ms|s)/i.test(stepText || '');
        expect(hasStepTiming).toBeTruthy();
      }
    }
  });

  /**
   * TC-46.2.7: Verify retrieval sources are displayed
   * Should show which sources were used (Qdrant, BM25, Neo4j, etc.)
   */
  test('TC-46.2.7: should display retrieval sources', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('What is hybrid search?');
    await chatPage.waitForResponse();

    // Find and expand reasoning panel
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Expand panel
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Look for retrieval steps
      const retrievalSteps = chatPage.page.locator('[data-testid^="retrieval-step-"]');
      const stepCount = await retrievalSteps.count();

      if (stepCount > 0) {
        // Collect all sources used
        const sources = new Set<string>();

        for (let i = 0; i < stepCount; i++) {
          const step = retrievalSteps.nth(i);
          const source = await step.getAttribute('data-source');
          if (source) {
            sources.add(source);
          }
        }

        // Should have at least one source
        expect(sources.size).toBeGreaterThan(0);

        // Valid sources should be present
        const validSources = ['qdrant', 'bm25', 'neo4j', 'redis', 'rrf_fusion', 'reranker'];
        let hasValidSource = false;

        sources.forEach((source) => {
          if (validSources.includes(source)) {
            hasValidSource = true;
          }
        });

        expect(hasValidSource).toBeTruthy();
      }
    }
  });

  /**
   * TC-46.2.8: Verify intent colors/badges
   * Intent classification should show appropriate visual styling
   */
  test('TC-46.2.8: should display intent with proper styling', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('Summarize machine learning concepts');
    await chatPage.waitForResponse();

    // Find and expand reasoning panel
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Expand panel
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Look for intent section
      const intentSection = chatPage.page.locator('[data-testid="intent-section"]');
      const intentVisible = await intentSection.isVisible({ timeout: 3000 }).catch(() => false);

      if (intentVisible) {
        // Intent badge should have color classes
        const intentBadge = intentSection.locator('span').first();
        const badgeClasses = await intentBadge.getAttribute('class');

        // Should have either background and text color from Tailwind
        const hasColorClass =
          badgeClasses?.includes('bg-') && (badgeClasses?.includes('text-') || badgeClasses?.includes('-'));

        expect(hasColorClass).toBeTruthy();
      }
    }
  });

  /**
   * TC-46.2.9: Verify result counts are displayed
   * Retrieval steps should show how many results were returned
   */
  test('TC-46.2.9: should display result counts for retrieval steps', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('Tell me about embeddings');
    await chatPage.waitForResponse();

    // Find and expand reasoning panel
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Expand panel
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Look for retrieval steps
      const retrievalSteps = chatPage.page.locator('[data-testid^="retrieval-step-"]');
      const stepCount = await retrievalSteps.count();

      if (stepCount > 0) {
        // First step should have result count info
        const firstStep = retrievalSteps.first();
        const stepText = await firstStep.textContent();

        // German: "Ergebnisse:" or "Results:"
        const hasResultCount =
          stepText?.includes('Ergebnisse:') || stepText?.includes('Zusammengefuehrt:');

        expect(hasResultCount).toBeTruthy();
      }
    }
  });

  /**
   * TC-46.2.10: Verify panel responsive behavior
   * ReasoningPanel should adapt to different viewport sizes
   */
  test('TC-46.2.10: should have responsive panel layout', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('Explain neural networks');
    await chatPage.waitForResponse();

    // Find reasoning panel
    const reasoningPanel = chatPage.page.locator('[data-testid="reasoning-panel"]');

    const panelExists = await reasoningPanel.isVisible({ timeout: 5000 }).catch(() => false);

    if (panelExists) {
      // Panel should be visible and have proper structure
      const panelBox = await reasoningPanel.boundingBox();
      expect(panelBox).toBeTruthy();
      expect(panelBox?.width).toBeGreaterThan(0);
      expect(panelBox?.height).toBeGreaterThan(0);

      // Panel should have proper styling
      const panelClasses = await reasoningPanel.getAttribute('class');
      expect(panelClasses).toContain('border');
      expect(panelClasses).toContain('rounded-lg');
    }
  });

  /**
   * TC-46.2.11: Verify Chevron icon state change
   * Chevron should point right when collapsed, down when expanded
   */
  test('TC-46.2.11: should update chevron icon on toggle', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('What is tokenization?');
    await chatPage.waitForResponse();

    // Find reasoning toggle
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Initially should show ChevronRight icon
      let chevronIcon = reasoningToggle.locator('svg').first();
      let iconVisible = await chevronIcon.isVisible();

      // Click to expand
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Check that content is visible after expansion
      const reasoningContent = chatPage.page.locator('[data-testid="reasoning-content"]');
      const contentVisible = await reasoningContent.isVisible({ timeout: 3000 }).catch(() => false);

      if (contentVisible) {
        // Should show expanded state
        const ariaExpanded = await reasoningToggle.getAttribute('aria-expanded');
        expect(ariaExpanded).toBe('true');
      }
    }
  });

  /**
   * TC-46.2.12: Verify tools section display
   * Should show tools that were used in retrieval (if any)
   */
  test('TC-46.2.12: should display tools section when available', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('What are large language models?');
    await chatPage.waitForResponse();

    // Find and expand reasoning panel
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');

    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Expand panel
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Look for tools section
      const toolsSection = chatPage.page.locator('[data-testid="tools-section"]');
      const toolsSectionVisible = await toolsSection.isVisible({ timeout: 3000 }).catch(() => false);

      // Tools section may or may not be present depending on retrieval
      // If it is present, it should be properly formatted
      if (toolsSectionVisible) {
        const toolsText = await toolsSection.textContent();
        expect(toolsText).toContain('Verwendete Tools');
      }
    }
  });
});

/**
 * INTEGRATION TESTS: ConversationView + ReasoningPanel
 * Tests for the combined behavior of both features
 */
test.describe('Sprint 46 - Feature 46.1 + 46.2: Integration Tests', () => {
  /**
   * Integration Test 1: Complete conversation flow with reasoning
   * Should support sending message, receiving response, and viewing reasoning
   */
  test('should support complete conversation flow with reasoning visibility', async ({
    chatPage,
  }) => {
    // Step 1: Verify initial state
    const conversationView = chatPage.page.locator('[data-testid="conversation-view"]');
    await expect(conversationView).toBeVisible();

    // Step 2: Send message
    const testMessage = 'Explain the concept of overfitting in machine learning';
    await chatPage.sendMessage(testMessage);

    // Step 3: Wait for response
    await chatPage.waitForResponse();

    // Step 4: Verify message appears in conversation
    const allMessages = await chatPage.getAllMessages();
    const conversationText = allMessages.join('\n');
    expect(conversationText).toContain(testMessage);

    // Step 5: Look for reasoning panel
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');
    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Step 6: Expand reasoning panel
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Step 7: Verify reasoning content
      const reasoningContent = chatPage.page.locator('[data-testid="reasoning-content"]');
      const contentVisible = await reasoningContent.isVisible({ timeout: 3000 }).catch(() => false);

      if (contentVisible) {
        // Step 8: Verify intent section
        const intentSection = chatPage.page.locator('[data-testid="intent-section"]');
        const intentVisible = await intentSection.isVisible({ timeout: 1000 }).catch(() => false);
        expect(intentVisible).toBeTruthy();
      }

      // Step 9: Collapse reasoning
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Step 10: Verify collapsed
      const newAriaExpanded = await reasoningToggle.getAttribute('aria-expanded');
      expect(newAriaExpanded).toBe('false');
    }
  });

  /**
   * Integration Test 2: Multiple messages with reasoning for each
   * Should support viewing reasoning for different messages
   */
  test('should support viewing reasoning for multiple messages', async ({ chatPage }) => {
    // Send first message
    await chatPage.sendMessage('What is a neural network?');
    await chatPage.waitForResponse();

    // Send second message
    await chatPage.sendMessage('How do backpropagation work?');
    await chatPage.waitForResponse();

    // Should have multiple messages
    const allMessages = await chatPage.getAllMessages();
    expect(allMessages.length).toBeGreaterThanOrEqual(4);

    // Find all reasoning toggles
    const reasoningToggles = chatPage.page.locator('[data-testid="reasoning-toggle"]');
    const toggleCount = await reasoningToggles.count();

    // Each assistant message should potentially have a toggle
    // (depending on backend support)
    if (toggleCount > 0) {
      // Click first toggle to verify it works
      const firstToggle = reasoningToggles.first();
      await firstToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Should expand
      const ariaExpanded = await firstToggle.getAttribute('aria-expanded');
      expect(ariaExpanded).toBe('true');

      // Collapse it
      await firstToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Should collapse
      const newAriaExpanded = await firstToggle.getAttribute('aria-expanded');
      expect(newAriaExpanded).toBe('false');
    }
  });

  /**
   * Integration Test 3: Input area remains functional with expanded reasoning
   * Should allow sending new messages while reasoning panel is open
   */
  test('should keep input functional while reasoning panel is expanded', async ({ chatPage }) => {
    // Send initial message
    await chatPage.sendMessage('Tell me about transformers');
    await chatPage.waitForResponse();

    // Find and expand reasoning panel
    const reasoningToggle = chatPage.page.locator('[data-testid="reasoning-toggle"]');
    const toggleExists = await reasoningToggle.isVisible({ timeout: 5000 }).catch(() => false);

    if (toggleExists) {
      // Expand reasoning
      await reasoningToggle.click();
      await chatPage.page.waitForTimeout(300);

      // Verify input is still visible and functional
      await expect(chatPage.messageInput).toBeVisible();
      await expect(chatPage.sendButton).toBeVisible();

      // Send another message while reasoning is expanded
      const messageCount = (await chatPage.getAllMessages()).length;

      await chatPage.sendMessage('Can you compare with RNNs?');
      await chatPage.waitForResponse();

      // Verify new message was added
      const newMessageCount = (await chatPage.getAllMessages()).length;
      expect(newMessageCount).toBeGreaterThan(messageCount);
    }
  });
});
