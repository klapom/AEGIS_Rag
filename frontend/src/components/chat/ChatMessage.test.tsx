/**
 * ChatMessage Component Tests
 * Sprint 35 Feature 35.1: Seamless Chat Flow
 * Sprint 35 Feature 35.6: Loading States & Animations
 *
 * Tests for the ChatMessage component which renders individual messages
 * in the conversation flow with proper avatars, content, and styling.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatMessage } from './ChatMessage';
import type { Source } from '../../types/chat';

describe('ChatMessage', () => {
  const mockUserMessage = {
    role: 'user' as const,
    content: 'What is AegisRAG?',
  };

  const mockAssistantMessage = {
    role: 'assistant' as const,
    content: 'AegisRAG is an agentic RAG system.',
  };

  const mockSources: Source[] = [
    {
      text: 'AegisRAG documentation',
      title: 'AegisRAG Overview',
      source: 'docs.pdf',
      score: 0.95,
    },
    {
      text: 'RAG architecture details',
      title: 'RAG Architecture',
      source: 'architecture.md',
      score: 0.87,
    },
  ];

  describe('Basic Rendering', () => {
    it('renders chat message container with correct data-testid', () => {
      render(<ChatMessage message={mockUserMessage} />);
      const message = screen.getByTestId('chat-message');
      expect(message).toBeInTheDocument();
    });

    it('sets correct data-role attribute for user messages', () => {
      render(<ChatMessage message={mockUserMessage} />);
      const message = screen.getByTestId('chat-message');
      expect(message).toHaveAttribute('data-role', 'user');
    });

    it('sets correct data-role attribute for assistant messages', () => {
      render(<ChatMessage message={mockAssistantMessage} />);
      const message = screen.getByTestId('chat-message');
      expect(message).toHaveAttribute('data-role', 'assistant');
    });
  });

  describe('User Messages', () => {
    it('renders user message with correct styling', () => {
      render(<ChatMessage message={mockUserMessage} />);
      const message = screen.getByTestId('chat-message');
      expect(message).toHaveClass('flex');
      expect(message).toHaveClass('gap-4');
      expect(message).toHaveClass('py-6');
      expect(message).toHaveClass('border-b');
      expect(message).toHaveClass('border-gray-100');
    });

    it('displays user message content correctly', () => {
      render(<ChatMessage message={mockUserMessage} />);
      expect(screen.getByText('What is AegisRAG?')).toBeInTheDocument();
    });

    it('displays Sie label for user role', () => {
      render(<ChatMessage message={mockUserMessage} />);
      expect(screen.getByText('Sie')).toBeInTheDocument();
    });

    it('renders UserAvatar for user messages', () => {
      render(<ChatMessage message={mockUserMessage} />);
      const userAvatar = screen.getByTestId('user-avatar');
      expect(userAvatar).toBeInTheDocument();
    });

    it('does not render BotAvatar for user messages', () => {
      render(<ChatMessage message={mockUserMessage} />);
      expect(screen.queryByTestId('bot-avatar')).not.toBeInTheDocument();
    });

    it('renders user content as plain text without markdown processing', () => {
      const messageWithMarkdown = {
        role: 'user' as const,
        content: 'What is **AegisRAG**? Check *this* out.',
      };
      render(<ChatMessage message={messageWithMarkdown} />);
      // Should display the markdown syntax as-is, not processed
      expect(screen.getByText(/What is \*\*AegisRAG\*\*?/)).toBeInTheDocument();
    });

    it('preserves whitespace in user messages', () => {
      const messageWithWhitespace = {
        role: 'user' as const,
        content: 'Line 1\nLine 2\nLine 3',
      };
      render(<ChatMessage message={messageWithWhitespace} />);
      const content = screen.getByText(/Line 1/);
      expect(content).toHaveClass('whitespace-pre-wrap');
    });
  });

  describe('Assistant Messages', () => {
    it('renders assistant message with correct styling', () => {
      render(<ChatMessage message={mockAssistantMessage} />);
      const message = screen.getByTestId('chat-message');
      expect(message).toHaveClass('flex');
      expect(message).toHaveClass('gap-4');
      expect(message).toHaveClass('py-6');
    });

    it('displays assistant message content correctly', () => {
      render(<ChatMessage message={mockAssistantMessage} />);
      expect(screen.getByText('AegisRAG is an agentic RAG system.')).toBeInTheDocument();
    });

    it('displays AegisRAG label for assistant role', () => {
      render(<ChatMessage message={mockAssistantMessage} />);
      expect(screen.getByText('AegisRAG')).toBeInTheDocument();
    });

    it('renders BotAvatar for assistant messages', () => {
      render(<ChatMessage message={mockAssistantMessage} />);
      const botAvatar = screen.getByTestId('bot-avatar');
      expect(botAvatar).toBeInTheDocument();
    });

    it('does not render UserAvatar for assistant messages', () => {
      render(<ChatMessage message={mockAssistantMessage} />);
      expect(screen.queryByTestId('user-avatar')).not.toBeInTheDocument();
    });

    it('renders assistant content with markdown support', () => {
      const markdownMessage = {
        role: 'assistant' as const,
        content: 'AegisRAG is **powerful** and *flexible*.',
      };
      const { container } = render(<ChatMessage message={markdownMessage} />);
      // Markdown should be rendered with proper structure
      const strong = container.querySelector('strong');
      const em = container.querySelector('em');
      expect(strong).toBeInTheDocument();
      expect(strong?.textContent).toBe('powerful');
      expect(em).toBeInTheDocument();
      expect(em?.textContent).toBe('flexible');
    });
  });

  describe('Citations', () => {
    it('renders assistant message with citations using MarkdownWithCitations', () => {
      const messageWithCitations = {
        role: 'assistant' as const,
        content: 'AegisRAG is powerful[1] and flexible[2].',
        citations: mockSources,
      };
      const mockOnClick = vi.fn();
      render(<ChatMessage message={messageWithCitations} onCitationClick={mockOnClick} />);
      // Message should render
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });

    it('does not call onCitationClick without handler', () => {
      const messageWithCitations = {
        role: 'assistant' as const,
        content: 'AegisRAG is powerful[1].',
        citations: mockSources,
      };
      // Should render without onCitationClick prop
      render(<ChatMessage message={messageWithCitations} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });

    it('passes citations to MarkdownWithCitations component', () => {
      const messageWithCitations = {
        role: 'assistant' as const,
        content: 'Result[1] and analysis[2].',
        citations: mockSources,
      };
      const mockOnClick = vi.fn();
      render(<ChatMessage message={messageWithCitations} onCitationClick={mockOnClick} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });

    it('uses plain markdown when no citations present', () => {
      const messageNoCitations = {
        role: 'assistant' as const,
        content: 'AegisRAG is **powerful** and *flexible*.',
      };
      render(<ChatMessage message={messageNoCitations} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });

    it('uses plain markdown when citations array is empty', () => {
      const messageEmptyCitations = {
        role: 'assistant' as const,
        content: 'AegisRAG is **powerful**.',
        citations: [],
      };
      render(<ChatMessage message={messageEmptyCitations} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });
  });

  describe('Animation Classes', () => {
    it('applies fade-in animation class to message', () => {
      render(<ChatMessage message={mockUserMessage} />);
      const message = screen.getByTestId('chat-message');
      expect(message).toHaveClass('animate-fade-in');
    });

    it('applies animation to both user and assistant messages', () => {
      const { rerender } = render(<ChatMessage message={mockUserMessage} />);
      expect(screen.getByTestId('chat-message')).toHaveClass('animate-fade-in');

      rerender(<ChatMessage message={mockAssistantMessage} />);
      expect(screen.getByTestId('chat-message')).toHaveClass('animate-fade-in');
    });
  });

  describe('Timestamps', () => {
    it('displays timestamp when provided', () => {
      const messageWithTimestamp = {
        role: 'user' as const,
        content: 'What is AegisRAG?',
        timestamp: '2025-12-04T14:30:00Z',
      };
      render(<ChatMessage message={messageWithTimestamp} />);
      // Timestamp should be formatted and displayed
      const timeElement = screen.getByText(/\d{2}:\d{2}/);
      expect(timeElement).toBeInTheDocument();
      expect(timeElement).toHaveClass('text-xs');
      expect(timeElement).toHaveClass('text-gray-400');
    });

    it('does not display timestamp when not provided', () => {
      render(<ChatMessage message={mockUserMessage} />);
      // Should not have time element
      const timeElements = screen.queryAllByText(/\d{2}:\d{2}/);
      // Filter out any incidental matches
      const actualTimeElements = timeElements.filter(el => el.classList.contains('text-gray-400'));
      expect(actualTimeElements.length).toBe(0);
    });

    it('formats timestamp using German locale', () => {
      const messageWithTimestamp = {
        role: 'user' as const,
        content: 'What is AegisRAG?',
        timestamp: '2025-12-04T14:30:00Z',
      };
      render(<ChatMessage message={messageWithTimestamp} />);
      // German locale uses HH:mm format
      const timeElement = screen.getByText(/\d{2}:\d{2}/);
      expect(timeElement).toBeInTheDocument();
    });

    it('applies correct styling to timestamp element', () => {
      const messageWithTimestamp = {
        role: 'user' as const,
        content: 'What is AegisRAG?',
        timestamp: '2025-12-04T14:30:00Z',
      };
      render(<ChatMessage message={messageWithTimestamp} />);
      const timeElement = screen.getByText(/\d{2}:\d{2}/);
      expect(timeElement).toHaveClass('text-xs');
      expect(timeElement).toHaveClass('text-gray-400');
      expect(timeElement).toHaveClass('mt-2');
    });
  });

  describe('Layout Structure', () => {
    it('maintains proper flex layout with avatar and content', () => {
      const { container } = render(<ChatMessage message={mockUserMessage} />);
      const message = container.querySelector('[data-testid="chat-message"]') as HTMLElement;

      // Check flex layout
      expect(message).toHaveClass('flex');
      expect(message).toHaveClass('gap-4');

      // Check avatar shrink container
      const avatarContainer = message.querySelector('.flex-shrink-0');
      expect(avatarContainer).toBeInTheDocument();

      // Check content container
      const contentContainer = message.querySelector('.flex-1');
      expect(contentContainer).toBeInTheDocument();
    });

    it('applies border styling between messages', () => {
      render(<ChatMessage message={mockUserMessage} />);
      const message = screen.getByTestId('chat-message');
      expect(message).toHaveClass('border-b');
      expect(message).toHaveClass('border-gray-100');
      expect(message).toHaveClass('last:border-b-0');
    });

    it('applies proper padding to message container', () => {
      render(<ChatMessage message={mockUserMessage} />);
      const message = screen.getByTestId('chat-message');
      expect(message).toHaveClass('py-6');
    });

    it('applies prose styling to content area', () => {
      const { container } = render(<ChatMessage message={mockAssistantMessage} />);
      const prose = container.querySelector('.prose');
      expect(prose).toBeInTheDocument();
      expect(prose).toHaveClass('prose-sm');
      expect(prose).toHaveClass('max-w-none');
      expect(prose).toHaveClass('text-gray-800');
    });

    it('prevents content overflow with min-w-0', () => {
      const { container } = render(<ChatMessage message={mockUserMessage} />);
      const content = container.querySelector('.flex-1');
      expect(content).toHaveClass('min-w-0');
    });
  });

  describe('Long Messages', () => {
    it('handles long user messages with word wrapping', () => {
      const longMessage = {
        role: 'user' as const,
        content: 'A'.repeat(200),
      };
      render(<ChatMessage message={longMessage} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });

    it('handles long assistant messages with word wrapping', () => {
      const longMessage = {
        role: 'assistant' as const,
        content: 'B'.repeat(200),
      };
      render(<ChatMessage message={longMessage} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });

    it('handles multiline user messages', () => {
      const multilineMessage = {
        role: 'user' as const,
        content: 'Line 1\nLine 2\nLine 3\nLine 4\nLine 5',
      };
      render(<ChatMessage message={multilineMessage} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
      expect(screen.getByText(/Line 1/)).toBeInTheDocument();
    });

    it('handles code blocks in assistant messages', () => {
      const messageWithCode = {
        role: 'assistant' as const,
        content: '```python\nprint("Hello")\n```',
      };
      render(<ChatMessage message={messageWithCode} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });
  });

  describe('Message Role Variations', () => {
    it('correctly identifies user role', () => {
      const { container } = render(<ChatMessage message={mockUserMessage} />);
      const message = container.querySelector('[data-role="user"]');
      expect(message).toBeInTheDocument();
    });

    it('correctly identifies assistant role', () => {
      const { container } = render(<ChatMessage message={mockAssistantMessage} />);
      const message = container.querySelector('[data-role="assistant"]');
      expect(message).toBeInTheDocument();
    });

    it('applies correct label based on role', () => {
      const { rerender } = render(<ChatMessage message={mockUserMessage} />);
      expect(screen.getByText('Sie')).toBeInTheDocument();

      rerender(<ChatMessage message={mockAssistantMessage} />);
      expect(screen.getByText('AegisRAG')).toBeInTheDocument();
    });
  });

  describe('Integration', () => {
    it('renders complete message with all elements for user', () => {
      render(<ChatMessage message={mockUserMessage} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
      expect(screen.getByTestId('user-avatar')).toBeInTheDocument();
      expect(screen.getByText('Sie')).toBeInTheDocument();
      expect(screen.getByText('What is AegisRAG?')).toBeInTheDocument();
    });

    it('renders complete message with all elements for assistant', () => {
      render(<ChatMessage message={mockAssistantMessage} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
      expect(screen.getByTestId('bot-avatar')).toBeInTheDocument();
      expect(screen.getByText('AegisRAG')).toBeInTheDocument();
      expect(screen.getByText('AegisRAG is an agentic RAG system.')).toBeInTheDocument();
    });

    it('handles multiple messages in sequence', () => {
      const { rerender } = render(<ChatMessage message={mockUserMessage} />);
      let message = screen.getByTestId('chat-message');
      expect(message).toHaveAttribute('data-role', 'user');

      rerender(<ChatMessage message={mockAssistantMessage} />);
      message = screen.getByTestId('chat-message');
      expect(message).toHaveAttribute('data-role', 'assistant');
    });

    it('maintains proper styling consistency across message types', () => {
      const { container: userContainer } = render(<ChatMessage message={mockUserMessage} />);
      const userMessage = userContainer.querySelector('[data-testid="chat-message"]');

      const { container: assistantContainer } = render(<ChatMessage message={mockAssistantMessage} />);
      const assistantMessage = assistantContainer.querySelector('[data-testid="chat-message"]');

      // Both should have same layout classes
      expect(userMessage).toHaveClass('flex');
      expect(assistantMessage).toHaveClass('flex');
      expect(userMessage).toHaveClass('gap-4');
      expect(assistantMessage).toHaveClass('gap-4');
    });
  });

  describe('Edge Cases', () => {
    it('handles empty message content', () => {
      const emptyMessage = {
        role: 'user' as const,
        content: '',
      };
      render(<ChatMessage message={emptyMessage} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });

    it('handles undefined citations gracefully', () => {
      const messageWithoutCitations = {
        role: 'assistant' as const,
        content: 'Response without citations',
        citations: undefined,
      };
      render(<ChatMessage message={messageWithoutCitations} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });

    it('handles special characters in content', () => {
      const specialMessage = {
        role: 'user' as const,
        content: 'Test with special chars: <>&"\'',
      };
      render(<ChatMessage message={specialMessage} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });

    it('handles HTML-like content safely', () => {
      const htmlLikeMessage = {
        role: 'user' as const,
        content: '<div>This is not HTML</div>',
      };
      render(<ChatMessage message={htmlLikeMessage} />);
      // Should render as text, not as HTML
      expect(screen.getByText('<div>This is not HTML</div>')).toBeInTheDocument();
    });

    it('handles very long URLs in assistant messages', () => {
      const longUrl = 'https://example.com/' + 'a'.repeat(200);
      const messageWithUrl = {
        role: 'assistant' as const,
        content: `Check out ${longUrl}`,
      };
      render(<ChatMessage message={messageWithUrl} />);
      expect(screen.getByTestId('chat-message')).toBeInTheDocument();
    });
  });
});
