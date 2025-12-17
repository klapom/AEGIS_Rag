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
import { useMemo, useRef } from 'react';
import { UserAvatar } from './UserAvatar';
import { BotAvatar } from './BotAvatar';
import { MarkdownWithCitations } from './MarkdownWithCitations';
import { SourceCardsScroll, type SourceCardsScrollRef } from './SourceCardsScroll';
import { ReasoningPanel } from './ReasoningPanel';
import type { Source } from '../../types/chat';
import type { ReasoningData } from '../../types/reasoning';

/**
 * Extract citation numbers from answer text.
 * Matches patterns like [1], [2], [10], etc.
 *
 * Sprint 51 Fix: Used to filter sources to only show actually cited ones.
 */
function extractCitedNumbers(content: string): Set<number> {
  const matches = content.match(/\[(\d+)\]/g) || [];
  return new Set(matches.map((m) => parseInt(m.slice(1, -1), 10)));
}

/**
 * Cited source with its original citation number.
 * Sprint 51 Fix: Preserve original citation number for display.
 */
interface CitedSource {
  source: Source;
  citationNumber: number;
}

/**
 * Filter and reorder sources to only include cited ones.
 *
 * Sprint 51 Fix: Sources from search are ranked by search relevance (RRF),
 * but we should only show sources that were actually cited in the answer.
 * This prevents showing irrelevant sources with high "search relevance"
 * that weren't used by the LLM.
 *
 * @param sources - All sources from citation_map
 * @param content - Answer text with citations like [1], [2]
 * @returns Filtered sources with their original citation numbers
 */
function filterCitedSources(sources: Source[], content: string): CitedSource[] {
  const citedNumbers = extractCitedNumbers(content);

  // Sprint 51 Fix: If no citations found, return EMPTY array
  // This happens when the LLM determines the sources are irrelevant
  // and doesn't cite any of them in the answer
  if (citedNumbers.size === 0) {
    return [];
  }

  // Filter to only cited sources, preserving original citation numbers
  // Sources are 1-indexed in citation_map
  const citedSources: CitedSource[] = [];
  const sortedCitations = Array.from(citedNumbers).sort((a, b) => a - b);

  sortedCitations.forEach((num) => {
    const source = sources[num - 1]; // Convert 1-indexed to 0-indexed
    if (source) {
      citedSources.push({
        source,
        citationNumber: num,
      });
    }
  });

  return citedSources;
}

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
  const sourceCardsRef = useRef<SourceCardsScrollRef>(null);

  // Sprint 51 Fix: Filter sources to only show those actually cited in the answer
  // This prevents showing irrelevant sources with high "search relevance" but no actual usage
  const filteredSources = useMemo((): CitedSource[] => {
    if (!message.sources || message.sources.length === 0) {
      return [];
    }
    return filterCitedSources(message.sources, message.content);
  }, [message.sources, message.content]);

  const hasSources = filteredSources.length > 0;
  const hasOriginalSources = message.sources && message.sources.length > 0;

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
            // Sprint 51 Fix: Use original sources for citation lookup (correct [N] mapping)
            // but only show filtered (actually cited) sources in the cards below
            <>
              {hasOriginalSources ? (
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

        {/* Source cards for assistant messages - Sprint 51: Only show cited sources */}
        {!isUser && hasSources && !message.isStreaming && (
          <div className="mt-4">
            <SourceCardsScroll ref={sourceCardsRef} sources={filteredSources} />
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
