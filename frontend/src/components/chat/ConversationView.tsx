/**
 * ConversationView Component
 * Sprint 46 Feature 46.1: Chat-Style Layout
 * Sprint 48 Feature 48.6: Phase event display integration
 * Sprint 48 Feature 48.10: Request timeout and cancel integration
 * Sprint 63 Feature 63.8: Research Mode integration
 * Sprint 118 Feature 118.7: Follow-up Questions integration
 *
 * Main container for the chat-style conversation UI.
 * Transforms the search interface into a ChatGPT/Claude-style conversation layout.
 *
 * Features:
 * - Conversation history scrolls upward (oldest at top, newest at bottom)
 * - Input area fixed at bottom of screen
 * - Auto-scroll to new messages with smooth animation
 * - Flex-col layout with flex-grow for messages area
 * - Typing indicator while streaming
 * - Keyboard navigation support
 * - Phase events display during thinking (Sprint 48)
 * - Timeout warning and cancel functionality (Sprint 48)
 * - Research Mode toggle in input area (Sprint 63)
 * - Follow-up questions after assistant response (Sprint 118)
 */

import { useRef, useEffect, useCallback, useState } from 'react';
import { MessageBubble, type MessageData } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { FollowUpQuestions } from './FollowUpQuestions';
import { SearchInput, type SearchMode } from '../search';
import type { PhaseEvent, PhaseType } from '../../types/reasoning';
import type { GraphExpansionConfig } from '../../types/settings';

/**
 * Props for the ConversationView component
 */
interface ConversationViewProps {
  /** Array of messages to display in the conversation */
  messages: MessageData[];
  /** Whether the assistant is currently streaming a response */
  isStreaming?: boolean;
  /** Callback when user submits a new message (Sprint 79: added graphExpansionConfig) */
  onSendMessage: (query: string, mode: SearchMode, namespaces: string[], graphExpansionConfig?: GraphExpansionConfig) => void;
  /** Callback when a citation is clicked */
  onCitationClick?: (sourceId: string) => void;
  /** Placeholder text for the input */
  placeholder?: string;
  /** Whether to show the typing indicator */
  showTypingIndicator?: boolean;
  /** Custom typing indicator text */
  typingText?: string;
  /** Empty state content when no messages */
  emptyStateContent?: React.ReactNode;
  /** Sprint 48: Current phase being processed */
  currentPhase?: PhaseType | null;
  /** Sprint 48: List of phase events for progress display */
  phaseEvents?: PhaseEvent[];
  /** Sprint 48: Whether to show timeout warning */
  showTimeoutWarning?: boolean;
  /** Sprint 48: Callback to cancel the current request */
  onCancel?: () => void;
  /** Sprint 63: Whether Research Mode is enabled */
  isResearchMode?: boolean;
  /** Sprint 63: Callback to toggle Research Mode */
  onResearchModeToggle?: () => void;
  /** Sprint 63: Whether to show Research Mode toggle */
  showResearchToggle?: boolean;
  /** Sprint 118: Session ID for follow-up questions */
  sessionId?: string;
  /** Sprint 118: Callback when a follow-up question is clicked */
  onFollowUpQuestion?: (question: string) => void;
}

/**
 * ConversationView provides the main chat interface layout.
 *
 * Layout structure:
 * - Full height container with flex-col
 * - Scrollable messages area (flex-grow)
 * - Fixed input area at bottom (flex-shrink-0)
 *
 * Auto-scroll behavior:
 * - Scrolls to bottom when new messages arrive
 * - Uses smooth scroll animation
 * - Only auto-scrolls if user is near bottom (prevents disrupting manual scroll)
 */
export function ConversationView({
  messages,
  isStreaming = false,
  onSendMessage,
  onCitationClick,
  placeholder = 'Stellen Sie eine Frage...',
  showTypingIndicator,
  typingText = 'AegisRAG denkt nach...',
  emptyStateContent,
  currentPhase,
  phaseEvents = [],
  showTimeoutWarning = false,
  onCancel,
  isResearchMode = false,
  onResearchModeToggle,
  showResearchToggle = true,
  sessionId,
  onFollowUpQuestion,
}: ConversationViewProps) {
  // Ref for the messages container to handle scrolling
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  // Ref for the end-of-messages marker (scroll target)
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // Track if user has manually scrolled up
  const userHasScrolledUp = useRef(false);
  // Track previous message count to detect new messages
  const prevMessageCount = useRef(messages.length);

  // Sprint 47: Track thinking start time for elapsed time display
  const [thinkingStartTime, setThinkingStartTime] = useState<number | null>(null);

  // Sprint 52: Get last message early for scroll tracking
  const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;
  const isLastMessageStreaming = lastMessage?.isStreaming ?? false;

  /**
   * Check if the user is scrolled near the bottom of the messages container
   */
  const isNearBottom = useCallback((): boolean => {
    const container = messagesContainerRef.current;
    if (!container) return true;

    const threshold = 150; // pixels from bottom to consider "near bottom"
    const scrollBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    return scrollBottom < threshold;
  }, []);

  /**
   * Smoothly scroll to the bottom of the messages
   */
  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior, block: 'end' });
  }, []);

  /**
   * Handle scroll events to track if user has scrolled up manually
   */
  const handleScroll = useCallback(() => {
    userHasScrolledUp.current = !isNearBottom();
  }, [isNearBottom]);

  /**
   * Auto-scroll when new messages arrive
   * Only scrolls if user hasn't manually scrolled up
   */
  useEffect(() => {
    const hasNewMessages = messages.length > prevMessageCount.current;
    prevMessageCount.current = messages.length;

    // Auto-scroll when new message arrives and user is near bottom
    if (hasNewMessages && !userHasScrolledUp.current) {
      scrollToBottom();
    }

    // Reset scroll tracking when user sends a new message (detected by odd message count)
    if (hasNewMessages && messages.length > 0 && messages[messages.length - 1].role === 'user') {
      userHasScrolledUp.current = false;
      scrollToBottom();
    }
  }, [messages.length, scrollToBottom]);

  /**
   * Sprint 52: Auto-scroll during streaming when content updates
   * This ensures the latest streamed content stays visible above the floating input
   */
  const lastMessageContent = lastMessage?.content ?? '';
  useEffect(() => {
    // Only scroll during active streaming if user hasn't scrolled up
    if (isStreaming && lastMessage?.isStreaming && !userHasScrolledUp.current) {
      scrollToBottom('smooth');
    }
  }, [lastMessageContent, isStreaming, lastMessage?.isStreaming, scrollToBottom]);

  /**
   * Initial scroll to bottom when component mounts with existing messages
   */
  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom('instant');
    }
  }, []); // Only on mount

  /**
   * Sprint 47: Track thinking start time
   * Starts timer when streaming begins, resets when streaming ends
   */
  useEffect(() => {
    const shouldShowIndicator = showTypingIndicator ?? (isStreaming && messages.length > 0);
    const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;
    const isLastMessageStreaming = lastMessage?.isStreaming ?? false;

    if (shouldShowIndicator && !isLastMessageStreaming && !thinkingStartTime) {
      // Start thinking timer
      setThinkingStartTime(Date.now());
    } else if (!shouldShowIndicator || isLastMessageStreaming) {
      // Reset thinking timer when indicator hides or streaming starts
      if (thinkingStartTime) {
        setThinkingStartTime(null);
      }
    }
  }, [isStreaming, showTypingIndicator, messages, thinkingStartTime]);

  /**
   * Determine if typing indicator should be shown
   */
  const shouldShowTypingIndicator = showTypingIndicator ?? (isStreaming && messages.length > 0);

  return (
    <div
      className="relative flex flex-col h-full bg-gray-50"
      data-testid="conversation-view"
    >
      {/* Messages Area - Scrollable, with bottom padding for floating input */}
      <div
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto scroll-smooth pb-32"
        data-testid="messages-container"
        role="log"
        aria-label="Konversationsverlauf"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          // Empty state
          <div className="flex items-center justify-center h-full">
            {emptyStateContent || (
              <div className="text-center text-gray-500 p-8">
                <p className="text-lg font-medium mb-2">Starten Sie eine Konversation</p>
                <p className="text-sm">
                  Stellen Sie eine Frage, um zu beginnen.
                </p>
              </div>
            )}
          </div>
        ) : (
          // Messages list
          <div className="min-h-full flex flex-col justify-end">
            <div className="divide-y divide-gray-100" data-testid="message-container">
              {messages.map((message) => (
                <div key={message.id} data-testid="message">
                  <MessageBubble
                    message={message}
                    onCitationClick={onCitationClick}
                  />
                </div>
              ))}
            </div>

            {/* Typing indicator - shown while waiting for response */}
            {shouldShowTypingIndicator && !isLastMessageStreaming && (
              <div className="px-6 py-4 bg-white border-t border-gray-100">
                <TypingIndicator
                  text={typingText}
                  showAvatar={true}
                  startTime={thinkingStartTime ?? undefined}
                  currentPhase={currentPhase}
                  phaseEvents={phaseEvents}
                  showTimeoutWarning={showTimeoutWarning}
                  onCancel={onCancel}
                />
              </div>
            )}

            {/* Sprint 118: Follow-up Questions - shown after response completes */}
            {sessionId && !isStreaming && messages.length > 0 && onFollowUpQuestion && (
              <div className="px-6 py-4">
                <FollowUpQuestions
                  sessionId={sessionId}
                  answerComplete={!isStreaming && messages.length > 0}
                  onQuestionClick={onFollowUpQuestion}
                />
              </div>
            )}

            {/* Scroll anchor - invisible element at the bottom for scrollIntoView */}
            <div ref={messagesEndRef} className="h-0" aria-hidden="true" />
          </div>
        )}
      </div>

      {/* Input Area - Floating at bottom with gradient fade */}
      {/* Sprint 52: overflow-visible allows dropdown to extend above input area */}
      <div
        className="absolute bottom-0 left-0 right-0 pointer-events-none overflow-visible"
        data-testid="input-area"
      >
        {/* Gradient fade effect */}
        <div className="h-8 bg-gradient-to-t from-gray-50 to-transparent" />

        {/* Input container - overflow-visible for dropdown */}
        <div className="bg-gray-50 pb-4 pt-2 pointer-events-auto overflow-visible">
          <div className="max-w-3xl mx-auto px-4 overflow-visible">
            <SearchInput
              onSubmit={onSendMessage}
              placeholder={placeholder}
              autoFocus={messages.length === 0}
              isResearchMode={isResearchMode}
              onResearchModeToggle={onResearchModeToggle}
              showResearchToggle={showResearchToggle}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Export type for MessageData to be used by parent components
 */
export type { MessageData } from './MessageBubble';
