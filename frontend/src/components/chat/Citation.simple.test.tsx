/**
 * Simple test to verify 300ms delay works
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { Citation } from './Citation';
import type { Source } from '../../types/chat';

describe('Citation 300ms Delay', () => {
  const mockOnClickScrollTo = vi.fn();

  const testSource: Source = {
    text: 'Test content',
    title: 'Test Document',
    source: '/test.pdf',
    score: 0.9,
    document_id: 'test-doc',
    context: 'Test context',
  };

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not show tooltip immediately on hover', () => {
    render(
      <Citation
        sourceIndex={1}
        source={testSource}
        onClickScrollTo={mockOnClickScrollTo}
      />
    );

    const button = screen.getByTestId('citation');
    fireEvent.mouseEnter(button);

    // Tooltip should NOT be visible immediately
    expect(screen.queryByTestId('citation-tooltip')).not.toBeInTheDocument();
  });

  it('shows tooltip after 300ms', () => {
    render(
      <Citation
        sourceIndex={1}
        source={testSource}
        onClickScrollTo={mockOnClickScrollTo}
      />
    );

    const button = screen.getByTestId('citation');
    fireEvent.mouseEnter(button);

    // Advance timers by 300ms
    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Tooltip should now be visible
    expect(screen.getByTestId('citation-tooltip')).toBeInTheDocument();
  });

  it('does not show tooltip if mouse leaves before 300ms', () => {
    render(
      <Citation
        sourceIndex={1}
        source={testSource}
        onClickScrollTo={mockOnClickScrollTo}
      />
    );

    const button = screen.getByTestId('citation');
    fireEvent.mouseEnter(button);

    // Advance only 200ms
    act(() => {
      vi.advanceTimersByTime(200);
    });

    // Mouse leaves
    fireEvent.mouseLeave(button);

    // Advance remaining 100ms
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Tooltip should NOT be visible
    expect(screen.queryByTestId('citation-tooltip')).not.toBeInTheDocument();
  });
});
