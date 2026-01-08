/**
 * GraphStatisticsCard Component Tests
 * Sprint 79 Feature 79.7: Admin Graph Operations UI
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GraphStatisticsCard } from './GraphStatisticsCard';
import type { GraphOperationsStats } from '../../api/graphOperations';

// Helper: Create mock GraphOperationsStats
function createMockStats(overrides?: Partial<GraphOperationsStats>): GraphOperationsStats {
  return {
    total_entities: 1500,
    total_relationships: 3200,
    entity_types: { PERSON: 500, ORGANIZATION: 400, LOCATION: 300, EVENT: 200, PRODUCT: 100 },
    relationship_types: { RELATES_TO: 2000, MENTIONED_IN: 1000, CO_OCCURS: 200 },
    community_count: 92,
    community_sizes: [45, 30, 20, 15, 10, 8, 5, 5, 4, 3],
    orphan_nodes: 50,
    avg_degree: 4.27,
    summary_status: {
      generated: 80,
      pending: 12,
    },
    graph_health: 'healthy',
    timestamp: '2026-01-08T10:30:00Z',
    ...overrides,
  };
}

describe('GraphStatisticsCard', () => {
  const mockOnRefresh = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('loading state', () => {
    it('should show loading skeleton when loading with no data', () => {
      render(
        <GraphStatisticsCard
          stats={null}
          loading={true}
          error={null}
          lastRefresh={null}
          onRefresh={mockOnRefresh}
        />
      );

      expect(screen.getByTestId('graph-statistics-loading')).toBeInTheDocument();
    });

    it('should show spinner on refresh button when loading with existing data', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats()}
          loading={true}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      const refreshButton = screen.getByTestId('graph-statistics-refresh');
      expect(refreshButton).toBeInTheDocument();
      // Check that SVG has animate-spin class (refresh button icon)
      const svg = refreshButton.querySelector('svg');
      expect(svg).toHaveClass('animate-spin');
    });
  });

  describe('error state', () => {
    it('should show error message when error is present', () => {
      render(
        <GraphStatisticsCard
          stats={null}
          loading={false}
          error={new Error('Failed to fetch statistics')}
          lastRefresh={null}
          onRefresh={mockOnRefresh}
        />
      );

      expect(screen.getByTestId('graph-statistics-error')).toBeInTheDocument();
      expect(screen.getByText('Failed to Load Statistics')).toBeInTheDocument();
      expect(screen.getByText('Failed to fetch statistics')).toBeInTheDocument();
    });

    it('should call onRefresh when retry button is clicked', () => {
      render(
        <GraphStatisticsCard
          stats={null}
          loading={false}
          error={new Error('Connection failed')}
          lastRefresh={null}
          onRefresh={mockOnRefresh}
        />
      );

      fireEvent.click(screen.getByTestId('graph-statistics-retry'));
      expect(mockOnRefresh).toHaveBeenCalledTimes(1);
    });
  });

  describe('empty state', () => {
    it('should show empty state when no stats and not loading', () => {
      render(
        <GraphStatisticsCard
          stats={null}
          loading={false}
          error={null}
          lastRefresh={null}
          onRefresh={mockOnRefresh}
        />
      );

      expect(screen.getByTestId('graph-statistics-empty')).toBeInTheDocument();
      expect(screen.getByText('No statistics available')).toBeInTheDocument();
    });
  });

  describe('stats display', () => {
    it('should display all statistics correctly', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats()}
          loading={false}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      expect(screen.getByTestId('graph-statistics-card')).toBeInTheDocument();
      // Use regex to handle locale differences (1,500 or 1.500)
      expect(screen.getByTestId('stat-entities')).toHaveTextContent(/1[,.]?500/);
      expect(screen.getByTestId('stat-relationships')).toHaveTextContent(/3[,.]?200/);
      expect(screen.getByTestId('stat-communities')).toHaveTextContent('92');
      expect(screen.getByTestId('stat-summaries')).toHaveTextContent('80/92');
    });

    it('should display health badge correctly for healthy state', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats({ graph_health: 'healthy' })}
          loading={false}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      const badge = screen.getByTestId('graph-health-badge');
      expect(badge).toHaveTextContent('healthy');
      expect(badge).toHaveClass('bg-green-100');
    });

    it('should display health badge correctly for warning state', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats({ graph_health: 'warning' })}
          loading={false}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      const badge = screen.getByTestId('graph-health-badge');
      expect(badge).toHaveTextContent('warning');
      expect(badge).toHaveClass('bg-yellow-100');
    });

    it('should display health badge correctly for critical state', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats({ graph_health: 'critical' })}
          loading={false}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      const badge = screen.getByTestId('graph-health-badge');
      expect(badge).toHaveTextContent('critical');
      expect(badge).toHaveClass('bg-red-100');
    });

    it('should display summary progress bar', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats({ summary_status: { generated: 80, pending: 12 } })}
          loading={false}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      const progressBar = screen.getByTestId('summary-progress-bar');
      expect(progressBar).toBeInTheDocument();
      // Progress is 80/92 = ~86.96%, check that aria-valuenow is a number around 87
      const ariaValue = parseFloat(progressBar.getAttribute('aria-valuenow') || '0');
      expect(ariaValue).toBeGreaterThan(86);
      expect(ariaValue).toBeLessThan(88);
    });

    it('should display 0% progress when no summaries exist', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats({ summary_status: { generated: 0, pending: 0 } })}
          loading={false}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      const progressBar = screen.getByTestId('summary-progress-bar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '0');
    });

    it('should display last refresh timestamp', () => {
      const lastRefresh = new Date('2026-01-08T10:30:00');
      render(
        <GraphStatisticsCard
          stats={createMockStats()}
          loading={false}
          error={null}
          lastRefresh={lastRefresh}
          onRefresh={mockOnRefresh}
        />
      );

      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });
  });

  describe('refresh button', () => {
    it('should call onRefresh when refresh button is clicked', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats()}
          loading={false}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      fireEvent.click(screen.getByTestId('graph-statistics-refresh'));
      expect(mockOnRefresh).toHaveBeenCalledTimes(1);
    });

    it('should disable refresh button when loading', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats()}
          loading={true}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      expect(screen.getByTestId('graph-statistics-refresh')).toBeDisabled();
    });
  });

  describe('accessibility', () => {
    it('should have proper ARIA attributes on progress bar', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats({ summary_status: { generated: 50, pending: 50 } })}
          loading={false}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      const progressBar = screen.getByTestId('summary-progress-bar');
      expect(progressBar).toHaveAttribute('role', 'progressbar');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      expect(progressBar).toHaveAttribute('aria-valuenow', '50');
    });

    it('should have accessible label on refresh button', () => {
      render(
        <GraphStatisticsCard
          stats={createMockStats()}
          loading={false}
          error={null}
          lastRefresh={new Date()}
          onRefresh={mockOnRefresh}
        />
      );

      expect(screen.getByTestId('graph-statistics-refresh')).toHaveAttribute(
        'aria-label',
        'Refresh statistics'
      );
    });
  });
});
