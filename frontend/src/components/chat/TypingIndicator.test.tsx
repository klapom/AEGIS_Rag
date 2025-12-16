/**
 * TypingIndicator Component Tests
 * Sprint 35 Feature 35.6: Loading States & Animations
 * Sprint 47: Enhanced with elapsed time and phase display tests
 * Sprint 48 Feature 48.6: Phase events integration tests
 * Sprint 48 Feature 48.10: Timeout warning and cancel button tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { TypingIndicator } from './TypingIndicator';
import type { PhaseEvent, PhaseType } from '../../types/reasoning';

describe('TypingIndicator', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders with default text', () => {
    render(<TypingIndicator />);
    const indicator = screen.getByTestId('typing-indicator-message');
    expect(indicator).toBeInTheDocument();
    expect(screen.getByText('AegisRAG denkt nach...')).toBeInTheDocument();
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

  it('shows text when showAvatar={false}', () => {
    render(<TypingIndicator text="Suche läuft..." showAvatar={false} />);
    expect(screen.getByText('Suche läuft...')).toBeInTheDocument();
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

  describe('Sprint 47: Elapsed time display', () => {
    it('does not show elapsed time when startTime is not provided', () => {
      render(<TypingIndicator />);
      expect(screen.queryByTestId('elapsed-time')).not.toBeInTheDocument();
    });

    it('shows elapsed time when startTime is provided', () => {
      const startTime = Date.now();
      render(<TypingIndicator startTime={startTime} />);
      expect(screen.getByTestId('elapsed-time')).toBeInTheDocument();
    });

    it('displays elapsed time in seconds format', () => {
      vi.setSystemTime(new Date('2025-01-01T00:00:00.000Z'));
      const startTime = Date.now();

      render(<TypingIndicator startTime={startTime} />);

      // Initial time should be 0.0s
      expect(screen.getByTestId('elapsed-time')).toHaveTextContent('0.0s');

      // Advance time by 2.5 seconds
      act(() => {
        vi.advanceTimersByTime(2500);
      });

      expect(screen.getByTestId('elapsed-time')).toHaveTextContent('2.5s');
    });

    it('displays elapsed time in minutes format when over 60 seconds', () => {
      vi.setSystemTime(new Date('2025-01-01T00:00:00.000Z'));
      const startTime = Date.now();

      render(<TypingIndicator startTime={startTime} />);

      // Advance time by 90 seconds
      act(() => {
        vi.advanceTimersByTime(90000);
      });

      expect(screen.getByTestId('elapsed-time')).toHaveTextContent('1:30');
    });
  });

  describe('Sprint 47: Phase display', () => {
    it('does not show phase when not provided', () => {
      render(<TypingIndicator />);
      expect(screen.queryByTestId('current-phase')).not.toBeInTheDocument();
    });

    it('shows phase when provided', () => {
      render(<TypingIndicator phase="Retrieval" />);
      expect(screen.getByTestId('current-phase')).toHaveTextContent('Retrieval');
    });

    it('shows progress bar when progress is provided', () => {
      const { container } = render(<TypingIndicator progress={50} />);
      const progressBar = container.querySelector('.bg-blue-500');
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveStyle({ width: '50%' });
    });

    it('shows details when provided', () => {
      render(<TypingIndicator details="Querying 3 vector stores..." />);
      expect(screen.getByTestId('thinking-details')).toHaveTextContent(
        'Querying 3 vector stores...'
      );
    });

    it('shows phase and progress together', () => {
      const { container } = render(<TypingIndicator phase="Graph Query" progress={75} />);
      expect(screen.getByTestId('current-phase')).toHaveTextContent('Graph Query');
      const progressBar = container.querySelector('.bg-blue-500');
      expect(progressBar).toHaveStyle({ width: '75%' });
    });
  });

  describe('Sprint 48: Phase events integration', () => {
    const mockPhaseEvents: PhaseEvent[] = [
      {
        phase_type: 'intent_classification',
        status: 'completed',
        start_time: '2025-01-01T00:00:00.000Z',
        end_time: '2025-01-01T00:00:00.100Z',
        duration_ms: 100,
      },
      {
        phase_type: 'vector_search',
        status: 'in_progress',
        start_time: '2025-01-01T00:00:00.100Z',
      },
    ];

    it('does not show phase indicator when no phase events are provided', () => {
      render(<TypingIndicator />);
      expect(screen.queryByTestId('phase-indicator-container')).not.toBeInTheDocument();
    });

    it('shows phase indicator when phase events are provided', () => {
      render(<TypingIndicator phaseEvents={mockPhaseEvents} />);
      expect(screen.getByTestId('phase-indicator-container')).toBeInTheDocument();
    });

    it('shows phase indicator when currentPhase is provided', () => {
      render(<TypingIndicator currentPhase="vector_search" />);
      expect(screen.getByTestId('phase-indicator-container')).toBeInTheDocument();
    });

    it('passes currentPhase to PhaseIndicator', () => {
      render(
        <TypingIndicator
          currentPhase="vector_search"
          phaseEvents={mockPhaseEvents}
        />
      );
      // PhaseIndicator should show the current phase display
      expect(screen.getByTestId('current-phase-display')).toBeInTheDocument();
    });

    it('displays phase events in PhaseIndicator', () => {
      render(<TypingIndicator phaseEvents={mockPhaseEvents} />);
      expect(screen.getByTestId('phase-list')).toBeInTheDocument();
      expect(screen.getByTestId('phase-item-intent_classification')).toBeInTheDocument();
      expect(screen.getByTestId('phase-item-vector_search')).toBeInTheDocument();
    });
  });

  describe('Sprint 48: Timeout warning and cancel button', () => {
    it('does not show timeout warning by default', () => {
      render(<TypingIndicator />);
      expect(screen.queryByTestId('timeout-warning')).not.toBeInTheDocument();
    });

    it('shows timeout warning when showTimeoutWarning is true', () => {
      render(<TypingIndicator showTimeoutWarning={true} />);
      expect(screen.getByTestId('timeout-warning')).toBeInTheDocument();
      expect(screen.getByText(/Diese Anfrage dauert ungewoehnlich lange/)).toBeInTheDocument();
    });

    it('timeout warning has correct accessibility attributes', () => {
      render(<TypingIndicator showTimeoutWarning={true} />);
      const warning = screen.getByTestId('timeout-warning');
      expect(warning).toHaveAttribute('role', 'alert');
      expect(warning).toHaveAttribute('aria-live', 'assertive');
    });

    it('does not show cancel button when onCancel is not provided', () => {
      render(<TypingIndicator />);
      expect(screen.queryByTestId('cancel-button')).not.toBeInTheDocument();
    });

    it('shows cancel button when onCancel is provided', () => {
      const handleCancel = vi.fn();
      render(<TypingIndicator onCancel={handleCancel} />);
      expect(screen.getByTestId('cancel-button')).toBeInTheDocument();
    });

    it('cancel button has correct accessibility attributes', () => {
      const handleCancel = vi.fn();
      render(<TypingIndicator onCancel={handleCancel} />);
      const button = screen.getByTestId('cancel-button');
      expect(button).toHaveAttribute('aria-label', 'Anfrage abbrechen');
      expect(button).toHaveAttribute('title', 'Anfrage abbrechen');
    });

    it('calls onCancel when cancel button is clicked', () => {
      const handleCancel = vi.fn();
      render(<TypingIndicator onCancel={handleCancel} />);

      fireEvent.click(screen.getByTestId('cancel-button'));

      expect(handleCancel).toHaveBeenCalledTimes(1);
    });

    it('shows both timeout warning and cancel button together', () => {
      const handleCancel = vi.fn();
      render(<TypingIndicator showTimeoutWarning={true} onCancel={handleCancel} />);

      expect(screen.getByTestId('timeout-warning')).toBeInTheDocument();
      expect(screen.getByTestId('cancel-button')).toBeInTheDocument();
    });

    it('cancel button works in inline mode (showAvatar=false)', () => {
      const handleCancel = vi.fn();
      render(<TypingIndicator showAvatar={false} onCancel={handleCancel} />);

      const button = screen.getByTestId('cancel-button');
      expect(button).toBeInTheDocument();

      fireEvent.click(button);
      expect(handleCancel).toHaveBeenCalledTimes(1);
    });
  });
});
