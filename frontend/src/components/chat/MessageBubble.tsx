/**
 * MessageBubble Component
 * Sprint 46 Feature 46.1: Chat-Style Layout
 *
 * Individual message display component for the chat-style conversation UI.
 * Displays user and assistant messages with appropriate styling and avatars.
 *
 * Features:
 * - User messages: Blue background, right-aligned feel with left avatar
 * - Assistant messages: White background, gradient avatar
 * - Markdown rendering for assistant messages
 * - Citation support for assistant messages
 * - Smooth fade-in animation on mount
 * - Source cards for assistant messages with sources
 */

import ReactMarkdown from 'react-markdown';
import { UserAvatar } from './UserAvatar';
import { BotAvatar } from './BotAvatar';
import { MarkdownWithCitations } from './MarkdownWithCitations';
import { SourceCardsScroll, type SourceCardsScrollRef } from './SourceCardsScroll';
import { ReasoningPanel } from './ReasoningPanel';
import type { Source } from '../../types/chat';
import type { ReasoningData } from '../../types/reasoning';
import { useRef } from 'react';

/**
 * Message data structure for MessageBubble
 */
export interface MessageData {
  /** Unique identifier for the message */
  id: string;
  /** Role of the message sender */
  role: 'user' | 'assistant';
  /** Message content (plain text for user, may contain markdown for assistant) */
  content: string;
  /** Optional sources for assistant messages */
  sources?: Source[];
  /** Optional timestamp */
  timestamp?: string;
  /** Whether the message is currently streaming (assistant only) */
  isStreaming?: boolean;
  /** Optional reasoning data for transparent reasoning panel (Feature 46.2) */
  reasoningData?: ReasoningData | null;
}

interface MessageBubbleProps {
  /** Message data to display */
  message: MessageData;
  /** Callback when a citation is clicked (assistant messages) */
  onCitationClick?: (sourceId: string) => void;
}

/**
 * MessageBubble renders a single message in the conversation.
 *
 * Layout follows ChatGPT/Claude style:
 * - Avatar on the left
 * - Content fills remaining width
 * - User messages have blue background tint
 * - Assistant messages have white background
 */
export function MessageBubble({ message, onCitationClick }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const hasSources = message.sources && message.sources.length > 0;
  const sourceCardsRef = useRef<SourceCardsScrollRef>(null);

  /**
   * Handle citation click by scrolling to the source card
   */
  const handleCitationClick = (sourceId: string) => {
    if (sourceCardsRef.current) {
      sourceCardsRef.current.scrollToSource(sourceId);
    }
    onCitationClick?.(sourceId);
  };

  return (
    <div
      className={`
        flex gap-4 py-6 px-6
        transition-colors duration-200
        animate-fade-in
        ${isUser ? 'bg-blue-50/50' : 'bg-white'}
      `}
      data-testid="message-bubble"
      data-role={message.role}
      data-message-id={message.id}
      data-streaming={message.isStreaming ? 'true' : 'false'}
    >
      {/* Avatar */}
      <div className="flex-shrink-0 pt-1">
        {isUser ? <UserAvatar /> : <BotAvatar />}
      </div>

      {/* Content container */}
      <div className="flex-1 min-w-0 space-y-4">
        {/* Sender label */}
        <div className="text-sm font-semibold text-gray-700">
          {isUser ? 'Sie' : 'AegisRAG'}
        </div>

        {/* Message content */}
        <div className="prose prose-sm max-w-none text-gray-800">
          {isUser ? (
            // User messages: plain text, preserve whitespace
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          ) : (
            // Assistant messages: Markdown with optional citations
            <>
              {hasSources ? (
                <MarkdownWithCitations
                  content={message.content}
                  sources={message.sources || []}
                  onCitationClick={handleCitationClick}
                />
              ) : (
                <ReactMarkdown>{message.content}</ReactMarkdown>
              )}
              {/* Streaming cursor */}
              {message.isStreaming && (
                <span className="animate-pulse text-primary ml-1">|</span>
              )}
            </>
          )}
        </div>

        {/* Source cards for assistant messages */}
        {!isUser && hasSources && !message.isStreaming && (
          <div className="mt-4">
            <SourceCardsScroll ref={sourceCardsRef} sources={message.sources || []} />
          </div>
        )}

        {/* Reasoning Panel for assistant messages (Feature 46.2) */}
        {!isUser && message.reasoningData && !message.isStreaming && (
          <ReasoningPanel data={message.reasoningData} />
        )}

        {/* Timestamp */}
        {message.timestamp && (
          <div className="text-xs text-gray-400">
            {new Date(message.timestamp).toLocaleTimeString('de-DE', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        )}
      </div>
    </div>
  );
}
