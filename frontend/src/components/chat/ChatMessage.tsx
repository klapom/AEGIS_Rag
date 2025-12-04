/**
 * ChatMessage Component
 * Sprint 35 Feature 35.1: Seamless Chat Flow (Claude/ChatGPT Style)
 * Sprint 35 Feature 35.6: Loading States & Animations
 *
 * Renders a single chat message with avatar and content in a continuous flow layout.
 * Supports both user and assistant messages with Markdown rendering.
 * Features smooth fade-in animation on mount.
 */

import ReactMarkdown from 'react-markdown';
import { UserAvatar } from './UserAvatar';
import { BotAvatar } from './BotAvatar';
import type { Source } from '../../types/chat';
import { MarkdownWithCitations } from './MarkdownWithCitations';

interface ChatMessageProps {
  message: {
    role: 'user' | 'assistant';
    content: string;
    citations?: Source[];
    timestamp?: string;
  };
  onCitationClick?: (sourceId: string) => void;
}

/**
 * ChatMessage renders a single message in the conversation flow.
 * - User messages: Blue avatar on left, plain text content
 * - Assistant messages: Gradient avatar on left, Markdown content with optional citations
 */
export function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const hasCitations = message.citations && message.citations.length > 0;

  return (
    <div
      className="flex gap-4 py-6 border-b border-gray-100 last:border-b-0 animate-fade-in"
      data-testid="chat-message"
      data-role={message.role}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isUser ? <UserAvatar /> : <BotAvatar />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Optional name label */}
        <div className="text-sm font-semibold text-gray-700 mb-2">
          {isUser ? 'Sie' : 'AegisRAG'}
        </div>

        {/* Message content */}
        <div className="prose prose-sm max-w-none text-gray-800">
          {isUser ? (
            // User messages: plain text (no markdown needed)
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            // Assistant messages: Markdown with citations
            hasCitations && onCitationClick ? (
              <MarkdownWithCitations
                content={message.content}
                sources={message.citations || []}
                onCitationClick={onCitationClick}
              />
            ) : (
              <ReactMarkdown>{message.content}</ReactMarkdown>
            )
          )}
        </div>

        {/* Optional timestamp */}
        {message.timestamp && (
          <div className="text-xs text-gray-400 mt-2">
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
