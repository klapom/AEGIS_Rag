/**
 * SkeletonMessage Component Tests
 * Sprint 35 Feature 35.6: Loading States & Animations
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SkeletonMessage } from './SkeletonMessage';

describe('SkeletonMessage', () => {
  it('renders with default assistant role', () => {
    render(<SkeletonMessage />);
    const skeleton = screen.getByTestId('skeleton-message');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute('data-role', 'assistant');
  });

  it('renders with user role', () => {
    render(<SkeletonMessage role="user" />);
    const skeleton = screen.getByTestId('skeleton-message');
    expect(skeleton).toHaveAttribute('data-role', 'user');
  });

  it('has pulse animation class', () => {
    render(<SkeletonMessage />);
    const skeleton = screen.getByTestId('skeleton-message');
    expect(skeleton).toHaveClass('animate-pulse');
  });

  it('matches ChatMessage layout structure', () => {
    const { container } = render(<SkeletonMessage />);

    // Should have same flex gap structure as ChatMessage
    const skeleton = container.querySelector('.flex.gap-4.py-6');
    expect(skeleton).toBeInTheDocument();

    // Should have avatar placeholder
    const avatar = container.querySelector('.flex-shrink-0 > div');
    expect(avatar).toBeInTheDocument();

    // Should have content skeleton with multiple lines
    const contentLines = container.querySelectorAll('.flex-1 .space-y-2 > div');
    expect(contentLines.length).toBeGreaterThan(0);
  });
});
