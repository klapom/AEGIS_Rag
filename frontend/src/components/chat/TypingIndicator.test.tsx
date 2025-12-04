/**
 * TypingIndicator Component Tests
 * Sprint 35 Feature 35.6: Loading States & Animations
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TypingIndicator } from './TypingIndicator';

describe('TypingIndicator', () => {
  it('renders with default text', () => {
    render(<TypingIndicator />);
    const indicator = screen.getByTestId('typing-indicator-message');
    expect(indicator).toBeInTheDocument();
    expect(screen.getByText('AegisRAG is thinking...')).toBeInTheDocument();
  });

  it('renders with custom text', () => {
    render(<TypingIndicator text="Processing..." />);
    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });

  it('renders inline without avatar', () => {
    render(<TypingIndicator showAvatar={false} />);
    const indicator = screen.getByTestId('typing-indicator');
    expect(indicator).toBeInTheDocument();

    // Should not have full message layout
    expect(screen.queryByTestId('typing-indicator-message')).not.toBeInTheDocument();
  });

  it('has three bouncing dots', () => {
    const { container } = render(<TypingIndicator showAvatar={false} />);
    const dots = container.querySelectorAll('.animate-bounce');
    expect(dots.length).toBe(3);
  });

  it('dots have staggered animation delays', () => {
    const { container } = render(<TypingIndicator showAvatar={false} />);
    const dots = container.querySelectorAll('.animate-bounce');

    expect(dots[0]).toHaveStyle({ animationDelay: '0ms' });
    expect(dots[1]).toHaveStyle({ animationDelay: '150ms' });
    expect(dots[2]).toHaveStyle({ animationDelay: '300ms' });
  });

  it('matches ChatMessage layout when showAvatar is true', () => {
    const { container } = render(<TypingIndicator />);

    // Should have same flex gap structure as ChatMessage
    const message = container.querySelector('.flex.gap-4.py-6');
    expect(message).toBeInTheDocument();

    // Should have avatar
    const avatar = container.querySelector('.flex-shrink-0');
    expect(avatar).toBeInTheDocument();

    // Should have content area
    const content = container.querySelector('.flex-1');
    expect(content).toBeInTheDocument();
  });
});
