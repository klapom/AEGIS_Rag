/**
 * ConversationView Component
 * Sprint 46 Feature 46.1: Chat-Style Layout
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
 */

import { useRef, useEffect, useCallback } from 'react';
import { MessageBubble, type MessageData } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { SearchInput, type SearchMode } from '../search';

/**
 * Props for the ConversationView component
 */
interface ConversationViewProps {
  /** Array of messages to display in the conversation */
  messages: MessageData[];
  /** Whether the assistant is currently streaming a response */
  isStreaming?: boolean;
  /** Callback when user submits a new message */
  onSendMessage: (query: string, mode: SearchMode, namespaces: string[]) => void;
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
}: ConversationViewProps) {
  // Ref for the messages container to handle scrolling
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  // Ref for the end-of-messages marker (scroll target)
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // Track if user has manually scrolled up
  const userHasScrolledUp = useRef(false);
  // Track previous message count to detect new messages
  const prevMessageCount = useRef(messages.length);

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
   * Auto-scroll when new messages arrive or while streaming
   * Only scrolls if user hasn't manually scrolled up
   */
  useEffect(() => {
    const hasNewMessages = messages.length > prevMessageCount.current;
    prevMessageCount.current = messages.length;

    // Auto-scroll conditions:
    // 1. New message arrived and user is near bottom
    // 2. Streaming content updated and user is near bottom
    if ((hasNewMessages || isStreaming) && !userHasScrolledUp.current) {
      scrollToBottom();
    }

    // Reset scroll tracking when user sends a new message (detected by odd message count)
    if (hasNewMessages && messages.length > 0 && messages[messages.length - 1].role === 'user') {
      userHasScrolledUp.current = false;
      scrollToBottom();
    }
  }, [messages, isStreaming, scrollToBottom]);

  /**
   * Initial scroll to bottom when component mounts with existing messages
   */
  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom('instant');
    }
  }, []); // Only on mount

  /**
   * Determine if typing indicator should be shown
   */
  const shouldShowTypingIndicator = showTypingIndicator ?? (isStreaming && messages.length > 0);

  /**
   * Get the last message for streaming state detection
   */
  const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;
  const isLastMessageStreaming = lastMessage?.isStreaming ?? false;

  return (
    <div
      className="flex flex-col h-full bg-gray-50"
      data-testid="conversation-view"
    >
      {/* Messages Area - Scrollable, flex-grow to fill available space */}
      <div
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto scroll-smooth"
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
                <TypingIndicator text={typingText} showAvatar={true} />
              </div>
            )}

            {/* Scroll anchor - invisible element at the bottom for scrollIntoView */}
            <div ref={messagesEndRef} className="h-0" aria-hidden="true" />
          </div>
        )}
      </div>

      {/* Input Area - Fixed at bottom, flex-shrink-0 */}
      <div
        className="flex-shrink-0 bg-white border-t border-gray-200 shadow-lg"
        data-testid="input-area"
      >
        <div className="max-w-4xl mx-auto py-4 px-6">
          <SearchInput
            onSubmit={onSendMessage}
            placeholder={placeholder}
            autoFocus={messages.length === 0}
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Export type for MessageData to be used by parent components
 */
export type { MessageData } from './MessageBubble';
