/**
 * MetricResultsDisplay Component Tests
 * Sprint 45 Feature 45.12: Metric Configuration UI
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MetricResultsDisplay } from './MetricResultsDisplay';

describe('MetricResultsDisplay', () => {
  const fullResults = {
    entity_precision: 0.85,
    entity_recall: 0.78,
    entity_f1: 0.81,
    relation_precision: 0.72,
    relation_recall: 0.68,
    relation_f1: 0.70,
  };

  describe('rendering', () => {
    it('should render results container', () => {
      render(<MetricResultsDisplay results={fullResults} />);
      expect(screen.getByTestId('metric-results')).toBeInTheDocument();
    });

    it('should render title', () => {
      render(<MetricResultsDisplay results={fullResults} />);
      expect(screen.getByText('Training Results')).toBeInTheDocument();
    });

    it('should render entity and relation sections', () => {
      render(<MetricResultsDisplay results={fullResults} />);
      expect(screen.getByText('Entity Extraction')).toBeInTheDocument();
      expect(screen.getByText('Relation Extraction')).toBeInTheDocument();
    });

    it('should render all metric bars', () => {
      render(<MetricResultsDisplay results={fullResults} />);

      // Entity metrics (3 bars)
      expect(screen.getAllByText('Precision')).toHaveLength(2);
      expect(screen.getAllByText('Recall')).toHaveLength(2);
      expect(screen.getAllByText('F1 Score')).toHaveLength(2);
    });
  });

  describe('metric values', () => {
    it('should display entity precision correctly', () => {
      render(<MetricResultsDisplay results={fullResults} />);
      const bars = screen.getAllByTestId('metric-bar-precision');
      const entityBar = bars[0];
      expect(entityBar).toHaveTextContent('85%');
    });

    it('should display entity recall correctly', () => {
      render(<MetricResultsDisplay results={fullResults} />);
      const bars = screen.getAllByTestId('metric-bar-recall');
      const entityBar = bars[0];
      expect(entityBar).toHaveTextContent('78%');
    });

    it('should display entity f1 correctly', () => {
      render(<MetricResultsDisplay results={fullResults} />);
      const bars = screen.getAllByTestId('metric-bar-f1 score');
      const entityBar = bars[0];
      expect(entityBar).toHaveTextContent('81%');
    });

    it('should display relation precision correctly', () => {
      render(<MetricResultsDisplay results={fullResults} />);
      const bars = screen.getAllByTestId('metric-bar-precision');
      const relationBar = bars[1];
      expect(relationBar).toHaveTextContent('72%');
    });

    it('should display relation recall correctly', () => {
      render(<MetricResultsDisplay results={fullResults} />);
      const bars = screen.getAllByTestId('metric-bar-recall');
      const relationBar = bars[1];
      expect(relationBar).toHaveTextContent('68%');
    });

    it('should display relation f1 correctly', () => {
      render(<MetricResultsDisplay results={fullResults} />);
      const bars = screen.getAllByTestId('metric-bar-f1 score');
      const relationBar = bars[1];
      expect(relationBar).toHaveTextContent('70%');
    });

    it('should display "-" for undefined values', () => {
      const partialResults = {
        entity_precision: 0.85,
      };
      render(<MetricResultsDisplay results={partialResults} />);

      // Most values should be "-"
      const dashCount = screen.getAllByText('-').length;
      expect(dashCount).toBeGreaterThan(0);
    });
  });

  describe('visual feedback', () => {
    it('should use green color for high scores (>= 80%)', () => {
      render(<MetricResultsDisplay results={{ entity_precision: 0.85 }} />);
      const fills = screen.getAllByTestId('metric-bar-fill-precision');
      const entityFill = fills[0]; // First one is entity precision
      expect(entityFill).toHaveClass('bg-green-500');
    });

    it('should use yellow color for medium scores (60-79%)', () => {
      render(<MetricResultsDisplay results={{ entity_precision: 0.65 }} />);
      const fills = screen.getAllByTestId('metric-bar-fill-precision');
      const entityFill = fills[0];
      expect(entityFill).toHaveClass('bg-yellow-500');
    });

    it('should use red color for low scores (< 60%)', () => {
      render(<MetricResultsDisplay results={{ entity_precision: 0.45 }} />);
      const fills = screen.getAllByTestId('metric-bar-fill-precision');
      const entityFill = fills[0];
      expect(entityFill).toHaveClass('bg-red-500');
    });

    it('should set correct width for progress bars', () => {
      render(<MetricResultsDisplay results={{ entity_precision: 0.75 }} />);
      const fills = screen.getAllByTestId('metric-bar-fill-precision');
      const entityFill = fills[0];
      expect(entityFill).toHaveStyle({ width: '75%' });
    });

    it('should set 0% width for undefined values', () => {
      render(<MetricResultsDisplay results={{}} />);
      const fills = screen.getAllByTestId('metric-bar-fill-precision');
      const entityFill = fills[0];
      expect(entityFill).toHaveStyle({ width: '0%' });
    });
  });

  describe('edge cases', () => {
    it('should handle empty results object', () => {
      render(<MetricResultsDisplay results={{}} />);
      expect(screen.getByTestId('metric-results')).toBeInTheDocument();
      expect(screen.getAllByText('-')).toHaveLength(6); // All 6 metrics should show "-"
    });

    it('should handle partial results', () => {
      const partialResults = {
        entity_precision: 0.85,
        entity_f1: 0.80,
      };
      render(<MetricResultsDisplay results={partialResults} />);

      expect(screen.getByText('85%')).toBeInTheDocument();
      expect(screen.getByText('80%')).toBeInTheDocument();
      expect(screen.getAllByText('-').length).toBeGreaterThan(0);
    });

    it('should round values correctly', () => {
      const results = {
        entity_precision: 0.8567, // Should round to 86%
        relation_recall: 0.7234, // Should round to 72%
      };
      render(<MetricResultsDisplay results={results} />);

      expect(screen.getByText('86%')).toBeInTheDocument();
      expect(screen.getByText('72%')).toBeInTheDocument();
    });

    it('should handle zero values', () => {
      render(<MetricResultsDisplay results={{ entity_precision: 0 }} />);
      const fills = screen.getAllByTestId('metric-bar-fill-precision');
      const entityFill = fills[0];
      expect(entityFill).toHaveStyle({ width: '0%' });
      expect(entityFill).toHaveClass('bg-red-500'); // 0% is < 60, so red
    });

    it('should handle perfect scores', () => {
      render(<MetricResultsDisplay results={{ entity_precision: 1.0 }} />);
      const fills = screen.getAllByTestId('metric-bar-fill-precision');
      const entityFill = fills[0];
      expect(entityFill).toHaveStyle({ width: '100%' });
      expect(entityFill).toHaveClass('bg-green-500');
      expect(screen.getByText('100%')).toBeInTheDocument();
    });
  });
});
