/**
 * PhaseIndicator Component Tests
 * Sprint 48 Feature 48.6: Phase Event Display Tests
 * Sprint 51 Feature 51.1: Updated for dynamic phase count (removed TOTAL_PHASES)
 *
 * Tests for the PhaseIndicator component that displays real-time
 * progress through RAG processing phases.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PhaseIndicator } from './PhaseIndicator';
import type { PhaseEvent, PhaseType } from '../../types/reasoning';
import { PHASE_NAMES } from '../../types/reasoning';

describe('PhaseIndicator', () => {
  const createPhaseEvent = (
    phaseType: PhaseType,
    status: PhaseEvent['status'],
    durationMs?: number
  ): PhaseEvent => ({
    phase_type: phaseType,
    status,
    start_time: '2025-01-01T00:00:00.000Z',
    ...(status === 'completed' && {
      end_time: '2025-01-01T00:00:00.100Z',
      duration_ms: durationMs ?? 100,
    }),
  });

  describe('Progress calculation', () => {
    it('shows 0% progress when no phases are completed', () => {
      // Sprint 51 Feature 51.1: With no events and no totalPhases, shows 0 of 0
      render(<PhaseIndicator currentPhase={null} phaseEvents={[]} />);
      expect(screen.getByTestId('phase-progress-summary')).toHaveTextContent(
        '0 von 0 Phasen abgeschlossen'
      );
    });

    it('shows 0% progress with totalPhases prop when no phases completed', () => {
      // Sprint 51 Feature 51.1: With totalPhases prop, shows correct total
      render(<PhaseIndicator currentPhase={null} phaseEvents={[]} totalPhases={5} />);
      expect(screen.getByTestId('phase-progress-summary')).toHaveTextContent(
        '0 von 5 Phasen abgeschlossen'
      );
    });

    it('calculates progress based on completed phases (dynamic count)', () => {
      const events: PhaseEvent[] = [
        createPhaseEvent('intent_classification', 'completed'),
        createPhaseEvent('vector_search', 'completed'),
        createPhaseEvent('bm25_search', 'in_progress'),
      ];

      // Sprint 51 Feature 51.1: Without totalPhases, uses events count as total
      render(<PhaseIndicator currentPhase="bm25_search" phaseEvents={events} />);
      expect(screen.getByTestId('phase-progress-summary')).toHaveTextContent(
        '2 von 3 Phasen abgeschlossen'
      );
    });

    it('calculates progress with explicit totalPhases prop', () => {
      const events: PhaseEvent[] = [
        createPhaseEvent('intent_classification', 'completed'),
        createPhaseEvent('vector_search', 'completed'),
        createPhaseEvent('bm25_search', 'in_progress'),
      ];

      // Sprint 51 Feature 51.1: With totalPhases prop, uses that as denominator
      render(<PhaseIndicator currentPhase="bm25_search" phaseEvents={events} totalPhases={7} />);
      expect(screen.getByTestId('phase-progress-summary')).toHaveTextContent(
        '2 von 7 Phasen abgeschlossen'
      );
    });

    it('includes skipped phases in progress calculation', () => {
      const events: PhaseEvent[] = [
        createPhaseEvent('intent_classification', 'completed'),
        createPhaseEvent('vector_search', 'skipped'),
      ];

      // Sprint 51 Feature 51.1: Without totalPhases, uses events count as total
      render(<PhaseIndicator currentPhase={null} phaseEvents={events} />);
      expect(screen.getByTestId('phase-progress-summary')).toHaveTextContent(
        '2 von 2 Phasen abgeschlossen'
      );
    });
  });

  describe('Current phase display', () => {
    it('does not show current phase when null', () => {
      render(<PhaseIndicator currentPhase={null} phaseEvents={[]} />);
      expect(screen.queryByTestId('current-phase-display')).not.toBeInTheDocument();
    });

    it('shows current phase when provided', () => {
      render(<PhaseIndicator currentPhase="vector_search" phaseEvents={[]} />);
      const display = screen.getByTestId('current-phase-display');
      expect(display).toBeInTheDocument();
      expect(display).toHaveTextContent(PHASE_NAMES['vector_search']);
    });

    it('displays translated phase name', () => {
      render(<PhaseIndicator currentPhase="intent_classification" phaseEvents={[]} />);
      expect(screen.getByTestId('current-phase-display')).toHaveTextContent(
        'Intent analysieren'
      );
    });
  });

  describe('Progress bar', () => {
    it('has progressbar role with correct attributes', () => {
      render(<PhaseIndicator currentPhase={null} phaseEvents={[]} />);
      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuenow', '0');
      expect(progressbar).toHaveAttribute('aria-valuemin', '0');
      expect(progressbar).toHaveAttribute('aria-valuemax', '100');
    });

    it('updates progress bar width based on completion (dynamic)', () => {
      const events: PhaseEvent[] = Array.from({ length: 5 }, (_, i) =>
        createPhaseEvent(
          ['intent_classification', 'vector_search', 'bm25_search', 'rrf_fusion', 'reranking'][i] as PhaseType,
          'completed'
        )
      );

      // Sprint 51 Feature 51.1: Without totalPhases, 5 completed out of 5 events = 100%
      const { container } = render(
        <PhaseIndicator currentPhase={null} phaseEvents={events} />
      );

      const expectedProgress = 100; // All 5 events are completed
      const progressFill = container.querySelector('.bg-gradient-to-r');
      expect(progressFill).toHaveStyle({ width: `${expectedProgress}%` });
    });

    it('updates progress bar width with explicit totalPhases', () => {
      const events: PhaseEvent[] = Array.from({ length: 5 }, (_, i) =>
        createPhaseEvent(
          ['intent_classification', 'vector_search', 'bm25_search', 'rrf_fusion', 'reranking'][i] as PhaseType,
          'completed'
        )
      );

      // Sprint 51 Feature 51.1: With totalPhases=9, 5 completed out of 9 = ~56%
      const { container } = render(
        <PhaseIndicator currentPhase={null} phaseEvents={events} totalPhases={9} />
      );

      const expectedProgress = Math.round((5 / 9) * 100);
      const progressFill = container.querySelector('.bg-gradient-to-r');
      expect(progressFill).toHaveStyle({ width: `${expectedProgress}%` });
    });
  });

  describe('Phase list', () => {
    it('does not show phase list when showDetails is false', () => {
      const events: PhaseEvent[] = [createPhaseEvent('intent_classification', 'completed')];
      render(
        <PhaseIndicator currentPhase={null} phaseEvents={events} showDetails={false} />
      );
      expect(screen.queryByTestId('phase-list')).not.toBeInTheDocument();
    });

    it('does not show phase list when no events', () => {
      render(<PhaseIndicator currentPhase={null} phaseEvents={[]} showDetails={true} />);
      expect(screen.queryByTestId('phase-list')).not.toBeInTheDocument();
    });

    it('shows phase list when events are provided', () => {
      const events: PhaseEvent[] = [createPhaseEvent('intent_classification', 'completed')];
      render(<PhaseIndicator currentPhase={null} phaseEvents={events} />);
      expect(screen.getByTestId('phase-list')).toBeInTheDocument();
    });

    it('renders all phase events', () => {
      const events: PhaseEvent[] = [
        createPhaseEvent('intent_classification', 'completed'),
        createPhaseEvent('vector_search', 'in_progress'),
        createPhaseEvent('bm25_search', 'pending'),
      ];

      render(<PhaseIndicator currentPhase="vector_search" phaseEvents={events} />);

      expect(screen.getByTestId('phase-item-intent_classification')).toBeInTheDocument();
      expect(screen.getByTestId('phase-item-vector_search')).toBeInTheDocument();
      expect(screen.getByTestId('phase-item-bm25_search')).toBeInTheDocument();
    });

    it('shows duration for completed phases', () => {
      const events: PhaseEvent[] = [
        createPhaseEvent('intent_classification', 'completed', 150),
      ];

      render(<PhaseIndicator currentPhase={null} phaseEvents={events} />);
      expect(screen.getByTestId('phase-duration-intent_classification')).toHaveTextContent(
        '150ms'
      );
    });

    it('formats duration in seconds for long phases', () => {
      const events: PhaseEvent[] = [
        createPhaseEvent('llm_generation', 'completed', 2500),
      ];

      render(<PhaseIndicator currentPhase={null} phaseEvents={events} />);
      expect(screen.getByTestId('phase-duration-llm_generation')).toHaveTextContent(
        '2.5s'
      );
    });

    it('does not show duration for non-completed phases', () => {
      const events: PhaseEvent[] = [createPhaseEvent('vector_search', 'in_progress')];

      render(<PhaseIndicator currentPhase="vector_search" phaseEvents={events} />);
      expect(
        screen.queryByTestId('phase-duration-vector_search')
      ).not.toBeInTheDocument();
    });
  });

  describe('Phase status display', () => {
    it('displays completed status with checkmark', () => {
      const events: PhaseEvent[] = [createPhaseEvent('intent_classification', 'completed')];
      render(<PhaseIndicator currentPhase={null} phaseEvents={events} />);

      const item = screen.getByTestId('phase-item-intent_classification');
      expect(item).toHaveClass('text-green-600');
    });

    it('displays in_progress status with animation', () => {
      const events: PhaseEvent[] = [createPhaseEvent('vector_search', 'in_progress')];
      render(<PhaseIndicator currentPhase="vector_search" phaseEvents={events} />);

      const item = screen.getByTestId('phase-item-vector_search');
      expect(item).toHaveClass('text-blue-600');
      expect(item).toHaveClass('animate-pulse');
    });

    it('displays failed status with error message', () => {
      const events: PhaseEvent[] = [
        {
          phase_type: 'graph_query',
          status: 'failed',
          start_time: '2025-01-01T00:00:00.000Z',
          error: 'Connection timeout',
        },
      ];

      render(<PhaseIndicator currentPhase={null} phaseEvents={events} />);

      const item = screen.getByTestId('phase-item-graph_query');
      expect(item).toHaveClass('text-red-600');
      expect(screen.getByTestId('phase-error-graph_query')).toHaveTextContent(
        'Connection timeout'
      );
    });

    it('displays skipped status', () => {
      const events: PhaseEvent[] = [createPhaseEvent('memory_retrieval', 'skipped')];
      render(<PhaseIndicator currentPhase={null} phaseEvents={events} />);

      const item = screen.getByTestId('phase-item-memory_retrieval');
      expect(item).toHaveClass('text-gray-400');
    });
  });

  describe('Accessibility', () => {
    it('has status role for screen readers', () => {
      render(<PhaseIndicator currentPhase={null} phaseEvents={[]} />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has aria-label for the component', () => {
      render(<PhaseIndicator currentPhase={null} phaseEvents={[]} />);
      const component = screen.getByRole('status');
      expect(component).toHaveAttribute('aria-label', 'Verarbeitungsfortschritt');
    });

    it('has aria-live for dynamic updates', () => {
      render(<PhaseIndicator currentPhase={null} phaseEvents={[]} />);
      const component = screen.getByRole('status');
      expect(component).toHaveAttribute('aria-live', 'polite');
    });

    it('phase list has list role', () => {
      const events: PhaseEvent[] = [createPhaseEvent('intent_classification', 'completed')];
      render(<PhaseIndicator currentPhase={null} phaseEvents={events} />);
      expect(screen.getByRole('list')).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('accepts custom className', () => {
      const { container } = render(
        <PhaseIndicator
          currentPhase={null}
          phaseEvents={[]}
          className="custom-class"
        />
      );
      expect(container.firstChild).toHaveClass('custom-class');
    });
  });
});
