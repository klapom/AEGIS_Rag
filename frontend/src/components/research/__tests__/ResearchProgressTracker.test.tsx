/**
 * ResearchProgressTracker Component Tests
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResearchProgressTracker } from '../ResearchProgressTracker';
import type { ResearchProgress, ResearchPhase } from '../../../types/research';

// Helper to create mock progress events
function createProgress(
  phase: ResearchPhase,
  iteration: number = 1,
  metadata: Record<string, unknown> = {}
): ResearchProgress {
  return {
    phase,
    message: `Processing ${phase}`,
    iteration,
    metadata,
  };
}

describe('ResearchProgressTracker', () => {
  describe('rendering', () => {
    it('renders with data-testid', () => {
      render(
        <ResearchProgressTracker
          progress={[]}
          currentPhase={null}
          isResearching={false}
          error={null}
        />
      );

      expect(screen.getByTestId('research-progress-tracker')).toBeInTheDocument();
    });

    it('renders progress header', () => {
      render(
        <ResearchProgressTracker
          progress={[]}
          currentPhase={null}
          isResearching={false}
          error={null}
        />
      );

      expect(screen.getByText('Recherche-Fortschritt')).toBeInTheDocument();
    });

    it('renders progress bar', () => {
      render(
        <ResearchProgressTracker
          progress={[]}
          currentPhase={null}
          isResearching={false}
          error={null}
        />
      );

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('displays all main phases', () => {
      render(
        <ResearchProgressTracker
          progress={[]}
          currentPhase={null}
          isResearching={false}
          error={null}
        />
      );

      expect(screen.getByTestId('phase-item-plan')).toBeInTheDocument();
      expect(screen.getByTestId('phase-item-search')).toBeInTheDocument();
      expect(screen.getByTestId('phase-item-evaluate')).toBeInTheDocument();
      expect(screen.getByTestId('phase-item-synthesize')).toBeInTheDocument();
    });
  });

  describe('progress states', () => {
    it('shows current phase as in progress', () => {
      render(
        <ResearchProgressTracker
          progress={[createProgress('plan')]}
          currentPhase="plan"
          isResearching={true}
          error={null}
        />
      );

      const planPhase = screen.getByTestId('phase-item-plan');
      expect(planPhase.className).toContain('bg-blue-100');
    });

    it('shows completed phases with green styling', () => {
      render(
        <ResearchProgressTracker
          progress={[
            createProgress('plan'),
            createProgress('search'),
          ]}
          currentPhase="search"
          isResearching={true}
          error={null}
        />
      );

      const planPhase = screen.getByTestId('phase-item-plan');
      expect(planPhase.className).toContain('bg-green-100');
    });

    it('shows pending phases with gray styling', () => {
      render(
        <ResearchProgressTracker
          progress={[createProgress('plan')]}
          currentPhase="plan"
          isResearching={true}
          error={null}
        />
      );

      const synthesizePhase = screen.getByTestId('phase-item-synthesize');
      expect(synthesizePhase.className).toContain('bg-gray-100');
    });

    it('shows error state when error is provided', () => {
      render(
        <ResearchProgressTracker
          progress={[createProgress('search')]}
          currentPhase="search"
          isResearching={false}
          error="Test error message"
        />
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Test error message')).toBeInTheDocument();
    });
  });

  describe('progress bar', () => {
    it('shows 0% when no progress', () => {
      render(
        <ResearchProgressTracker
          progress={[]}
          currentPhase={null}
          isResearching={false}
          error={null}
        />
      );

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '0');
    });

    it('updates progress percentage as phases complete', () => {
      render(
        <ResearchProgressTracker
          progress={[
            createProgress('plan'),
            createProgress('search'),
          ]}
          currentPhase="evaluate"
          isResearching={true}
          error={null}
        />
      );

      const progressBar = screen.getByRole('progressbar');
      // With plan and search complete, and evaluate in progress, progress should be ~62%
      const progress = parseInt(progressBar.getAttribute('aria-valuenow') || '0');
      expect(progress).toBeGreaterThan(0);
      expect(progress).toBeLessThan(100);
    });

    it('shows high percentage when all phases completed', () => {
      render(
        <ResearchProgressTracker
          progress={[
            createProgress('plan'),
            createProgress('search'),
            createProgress('evaluate'),
            createProgress('synthesize'),
          ]}
          currentPhase="complete"
          isResearching={false}
          error={null}
        />
      );

      const progressBar = screen.getByRole('progressbar');
      // All 4 phases completed = 100% (4 phases / 4 phases = 100%)
      // Note: 'start' and 'complete' are implicit and not counted
      const progress = parseInt(progressBar.getAttribute('aria-valuenow') || '0');
      expect(progress).toBeGreaterThanOrEqual(80);
    });
  });

  describe('expandable details', () => {
    it('shows expandable details when phase has metadata', () => {
      render(
        <ResearchProgressTracker
          progress={[
            createProgress('plan', 1, { num_queries: 3 }),
          ]}
          currentPhase="plan"
          isResearching={true}
          error={null}
        />
      );

      const planPhase = screen.getByTestId('phase-item-plan');
      const expandButton = planPhase.querySelector('button');
      expect(expandButton).toBeInTheDocument();
    });

    it('expands phase details when clicked', () => {
      render(
        <ResearchProgressTracker
          progress={[
            createProgress('plan', 1, { num_queries: 3 }),
          ]}
          currentPhase="plan"
          isResearching={true}
          error={null}
        />
      );

      const planPhase = screen.getByTestId('phase-item-plan');
      const expandButton = planPhase.querySelector('button');

      fireEvent.click(expandButton!);

      expect(screen.getByText('Abfragen:')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('calls onPhaseClick callback when phase is clicked', () => {
      const onPhaseClick = vi.fn();

      render(
        <ResearchProgressTracker
          progress={[
            createProgress('plan', 1, { num_queries: 3 }),
          ]}
          currentPhase="plan"
          isResearching={true}
          error={null}
          onPhaseClick={onPhaseClick}
        />
      );

      const planPhase = screen.getByTestId('phase-item-plan');
      const expandButton = planPhase.querySelector('button');

      fireEvent.click(expandButton!);

      expect(onPhaseClick).toHaveBeenCalledWith('plan');
    });
  });

  describe('iteration tracking', () => {
    it('displays current iteration', () => {
      render(
        <ResearchProgressTracker
          progress={[
            createProgress('search', 2),
          ]}
          currentPhase="search"
          isResearching={true}
          error={null}
        />
      );

      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('shows iteration badge on phases with iteration > 0', () => {
      render(
        <ResearchProgressTracker
          progress={[
            createProgress('search', 3),
          ]}
          currentPhase="search"
          isResearching={true}
          error={null}
        />
      );

      expect(screen.getByText('Iteration 3')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has proper aria labels on phase buttons', () => {
      render(
        <ResearchProgressTracker
          progress={[
            createProgress('plan', 1, { num_queries: 3 }),
          ]}
          currentPhase="plan"
          isResearching={true}
          error={null}
        />
      );

      const planPhase = screen.getByTestId('phase-item-plan');
      const button = planPhase.querySelector('button');

      expect(button).toHaveAttribute('aria-expanded');
      expect(button).toHaveAttribute('aria-label');
    });

    it('progressbar has correct aria attributes', () => {
      render(
        <ResearchProgressTracker
          progress={[]}
          currentPhase={null}
          isResearching={false}
          error={null}
        />
      );

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      expect(progressBar).toHaveAttribute('aria-label', 'Research progress');
    });
  });
});
