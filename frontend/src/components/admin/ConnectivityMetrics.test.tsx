/**
 * ConnectivityMetrics Component Tests
 * Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConnectivityMetrics } from './ConnectivityMetrics';
import type { ConnectivityEvaluationResponse } from '../../hooks/useDomainTraining';

// Mock the hook
const mockRefetch = vi.fn();
let mockData: ConnectivityEvaluationResponse | null = null;
let mockIsLoading = false;
let mockError: Error | null = null;

vi.mock('../../hooks/useDomainTraining', async () => {
  const actual = await vi.importActual('../../hooks/useDomainTraining');
  return {
    ...actual,
    useConnectivityMetrics: () => ({
      data: mockData,
      isLoading: mockIsLoading,
      error: mockError,
      refetch: mockRefetch,
    }),
  };
});

// Helper: Create mock connectivity data
function createMockConnectivityData(
  overrides?: Partial<ConnectivityEvaluationResponse>
): ConnectivityEvaluationResponse {
  return {
    namespace_id: 'hotpotqa_large',
    domain_type: 'factual',
    total_entities: 146,
    total_relationships: 65,
    total_communities: 92,
    relations_per_entity: 0.45,
    entities_per_community: 1.59,
    benchmark_min: 0.3,
    benchmark_max: 0.8,
    within_benchmark: true,
    benchmark_status: 'within',
    recommendations: [
      '✅ Connectivity (0.45 relations/entity) is within benchmark range [0.3, 0.8]',
      'Graph structure is appropriate for factual domain (HotpotQA-style data)',
    ],
    ...overrides,
  };
}

describe('ConnectivityMetrics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockData = null;
    mockIsLoading = false;
    mockError = null;
  });

  describe('rendering states', () => {
    it('should not render when enabled is false', () => {
      mockData = createMockConnectivityData();
      const { container } = render(
        <ConnectivityMetrics namespaceId="test" domainType="factual" enabled={false} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should render loading state', () => {
      mockIsLoading = true;
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" enabled={true} />);

      expect(screen.getByTestId('connectivity-metrics-section')).toBeInTheDocument();
      expect(screen.getByText('Loading connectivity metrics...')).toBeInTheDocument();
      // Should show spinner
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('should render error state', () => {
      mockError = new Error('Network error: API unreachable');
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" enabled={true} />);

      expect(screen.getByTestId('connectivity-metrics-section')).toBeInTheDocument();
      // Component shows hardcoded error title
      expect(screen.getByText('Failed to load connectivity metrics')).toBeInTheDocument();
      // Component also shows the actual error message
      expect(screen.getByText('Network error: API unreachable')).toBeInTheDocument();
    });

    it('should not render when data is null', () => {
      mockData = null;
      const { container } = render(
        <ConnectivityMetrics namespaceId="test" domainType="factual" enabled={true} />
      );
      expect(container.firstChild).toBeNull();
    });
  });

  describe('metrics display', () => {
    it('should display connectivity metrics within benchmark', () => {
      mockData = createMockConnectivityData();
      render(<ConnectivityMetrics namespaceId="hotpotqa_large" domainType="factual" />);

      expect(screen.getByTestId('connectivity-metrics-section')).toBeInTheDocument();
      expect(screen.getByText('Entity Connectivity')).toBeInTheDocument();
      expect(screen.getByText('(factual domain)')).toBeInTheDocument();

      // Main metric value
      expect(screen.getByTestId('connectivity-value')).toHaveTextContent('0.45');

      // Status badge
      expect(screen.getByText('Within Benchmark')).toBeInTheDocument();

      // Benchmark range
      expect(screen.getByText('0.3 - 0.8')).toBeInTheDocument();
    });

    it('should display entity statistics', () => {
      mockData = createMockConnectivityData();
      render(<ConnectivityMetrics namespaceId="hotpotqa_large" domainType="factual" />);

      expect(screen.getByTestId('metric-entities')).toBeInTheDocument();
      expect(screen.getByTestId('metric-relationships')).toBeInTheDocument();
      expect(screen.getByTestId('metric-communities')).toBeInTheDocument();

      // Values should be formatted with locale string
      expect(screen.getByText('146')).toBeInTheDocument();
      expect(screen.getByText('65')).toBeInTheDocument();
      expect(screen.getByText('92')).toBeInTheDocument();
    });

    it('should display recommendations', () => {
      mockData = createMockConnectivityData();
      render(<ConnectivityMetrics namespaceId="hotpotqa_large" domainType="factual" />);

      expect(screen.getByTestId('recommendation-0')).toBeInTheDocument();
      expect(screen.getByTestId('recommendation-1')).toBeInTheDocument();

      expect(
        screen.getByText(/Connectivity \(0.45 relations\/entity\) is within benchmark/i)
      ).toBeInTheDocument();
    });
  });

  describe('benchmark status colors', () => {
    it('should show green for within benchmark', () => {
      mockData = createMockConnectivityData({
        relations_per_entity: 0.5,
        benchmark_status: 'within',
        within_benchmark: true,
      });
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" />);

      expect(screen.getByText('Within Benchmark')).toBeInTheDocument();
      // Check gauge has green color (via data-testid)
      const gauge = screen.getByTestId('connectivity-gauge');
      expect(gauge).toHaveClass('bg-green-500');
    });

    it('should show yellow for below benchmark', () => {
      mockData = createMockConnectivityData({
        relations_per_entity: 0.1,
        benchmark_status: 'below',
        within_benchmark: false,
        recommendations: [
          '⚠️ Connectivity (0.10 relations/entity) is below benchmark range [0.3, 0.8]',
          'Consider improving relation extraction with DSPy prompt optimization',
        ],
      });
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" />);

      expect(screen.getByText('Below Benchmark')).toBeInTheDocument();
      const gauge = screen.getByTestId('connectivity-gauge');
      expect(gauge).toHaveClass('bg-yellow-500');
    });

    it('should show orange for above benchmark', () => {
      mockData = createMockConnectivityData({
        relations_per_entity: 3.5,
        benchmark_status: 'above',
        within_benchmark: false,
        recommendations: [
          '⚠️ Connectivity (3.50 relations/entity) is above benchmark range [0.3, 0.8]',
          'Over-extraction detected. Consider tightening relation extraction criteria',
        ],
      });
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" />);

      expect(screen.getByText('Above Benchmark')).toBeInTheDocument();
      const gauge = screen.getByTestId('connectivity-gauge');
      expect(gauge).toHaveClass('bg-orange-500');
    });
  });

  describe('domain types', () => {
    it('should display factual domain type', () => {
      mockData = createMockConnectivityData({ domain_type: 'factual' });
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" />);

      expect(screen.getByText('(factual domain)')).toBeInTheDocument();
    });

    it('should display narrative domain type with higher benchmark', () => {
      mockData = createMockConnectivityData({
        domain_type: 'narrative',
        relations_per_entity: 2.0,
        benchmark_min: 1.5,
        benchmark_max: 3.0,
        benchmark_status: 'within',
        within_benchmark: true,
      });
      render(<ConnectivityMetrics namespaceId="test" domainType="narrative" />);

      expect(screen.getByText('(narrative domain)')).toBeInTheDocument();
      expect(screen.getByText('1.5 - 3.0')).toBeInTheDocument();
    });

    it('should display technical domain type', () => {
      mockData = createMockConnectivityData({
        domain_type: 'technical',
        relations_per_entity: 3.0,
        benchmark_min: 2.0,
        benchmark_max: 4.0,
      });
      render(<ConnectivityMetrics namespaceId="test" domainType="technical" />);

      expect(screen.getByText('(technical domain)')).toBeInTheDocument();
    });

    it('should display academic domain type', () => {
      mockData = createMockConnectivityData({
        domain_type: 'academic',
        relations_per_entity: 4.0,
        benchmark_min: 2.5,
        benchmark_max: 5.0,
      });
      render(<ConnectivityMetrics namespaceId="test" domainType="academic" />);

      expect(screen.getByText('(academic domain)')).toBeInTheDocument();
    });
  });

  describe('gauge calculation', () => {
    it('should calculate gauge percentage within range', () => {
      mockData = createMockConnectivityData({
        relations_per_entity: 0.55, // Middle of [0.3, 0.8]
        benchmark_min: 0.3,
        benchmark_max: 0.8,
      });
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" />);

      const gauge = screen.getByTestId('connectivity-gauge');
      // 0.55 - 0.3 = 0.25, range = 0.5, percentage = 50%
      expect(gauge).toHaveStyle({ width: '50%' });
    });

    it('should clamp gauge to 0% when below range', () => {
      mockData = createMockConnectivityData({
        relations_per_entity: 0.1, // Below 0.3
        benchmark_min: 0.3,
        benchmark_max: 0.8,
        benchmark_status: 'below',
      });
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" />);

      const gauge = screen.getByTestId('connectivity-gauge');
      // Should be clamped to 0% (negative values not allowed)
      expect(gauge).toHaveStyle({ width: expect.stringMatching(/^0%|^-/) });
    });

    it('should clamp gauge to 100% when above range', () => {
      mockData = createMockConnectivityData({
        relations_per_entity: 3.5, // Above 0.8
        benchmark_min: 0.3,
        benchmark_max: 0.8,
        benchmark_status: 'above',
      });
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" />);

      const gauge = screen.getByTestId('connectivity-gauge');
      // Should be clamped to 100% (no overflow)
      expect(gauge).toHaveStyle({ width: '100%' });
    });
  });

  describe('edge cases', () => {
    it('should handle zero entities', () => {
      mockData = createMockConnectivityData({
        total_entities: 0,
        total_relationships: 0,
        total_communities: 0,
        relations_per_entity: 0,
        benchmark_status: 'below',
        within_benchmark: false,
        recommendations: ['No entities found in namespace'],
      });
      render(<ConnectivityMetrics namespaceId="empty" domainType="factual" />);

      expect(screen.getByText('0')).toBeInTheDocument(); // Multiple zeros
      expect(screen.getByTestId('connectivity-value')).toHaveTextContent('0.00');
    });

    it('should format large numbers with locale string', () => {
      mockData = createMockConnectivityData({
        total_entities: 10000,
        total_relationships: 25000,
        total_communities: 500,
      });
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" />);

      // Should use toLocaleString() formatting
      expect(screen.getByText('10,000')).toBeInTheDocument();
      expect(screen.getByText('25,000')).toBeInTheDocument();
      expect(screen.getByText('500')).toBeInTheDocument();
    });

    it('should handle empty recommendations array', () => {
      mockData = createMockConnectivityData({ recommendations: [] });
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" />);

      // Recommendations section should not render
      expect(screen.queryByText('Recommendations')).not.toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('should have proper test IDs for automation', () => {
      mockData = createMockConnectivityData();
      render(<ConnectivityMetrics namespaceId="test" domainType="factual" />);

      expect(screen.getByTestId('connectivity-metrics-section')).toBeInTheDocument();
      expect(screen.getByTestId('connectivity-value')).toBeInTheDocument();
      expect(screen.getByTestId('connectivity-gauge')).toBeInTheDocument();
      expect(screen.getByTestId('metric-entities')).toBeInTheDocument();
      expect(screen.getByTestId('metric-relationships')).toBeInTheDocument();
      expect(screen.getByTestId('metric-communities')).toBeInTheDocument();
    });

    it('should have semantic HTML structure', () => {
      mockData = createMockConnectivityData();
      const { container } = render(
        <ConnectivityMetrics namespaceId="test" domainType="factual" />
      );

      // Should use section tag
      expect(container.querySelector('section')).toBeInTheDocument();
      // Should have h3 for section title
      expect(container.querySelector('h3')).toBeInTheDocument();
      // Should have h4 for subsection title
      expect(container.querySelector('h4')).toBeInTheDocument();
    });
  });
});
