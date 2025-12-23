/**
 * ResearchResponseDisplay Component Tests
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResearchResponseDisplay } from '../ResearchResponseDisplay';
import type { ResearchSource, ResearchState } from '../../../types/research';

// Helper to create mock sources
function createSource(index: number): ResearchSource {
  return {
    text: `Source text ${index}`,
    score: 0.9 - index * 0.1,
    source_type: index % 2 === 0 ? 'vector' : 'graph',
    metadata: {},
    entities: [`Entity${index}A`, `Entity${index}B`],
    relationships: [],
  };
}

// Default quality metrics
const defaultMetrics: ResearchState['qualityMetrics'] = {
  iterations: 2,
  totalSources: 5,
  webSources: 0,
};

describe('ResearchResponseDisplay', () => {
  describe('rendering', () => {
    it('renders with data-testid when content is available', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test synthesis"
          sources={[createSource(0)]}
          researchPlan={['Step 1']}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.getByTestId('research-response-display')).toBeInTheDocument();
    });

    it('returns null when no synthesis and no sources', () => {
      const { container } = render(
        <ResearchResponseDisplay
          synthesis={null}
          sources={[]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it('shows loading state when isLoading and no synthesis', () => {
      render(
        <ResearchResponseDisplay
          synthesis={null}
          sources={[]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={true}
        />
      );

      expect(screen.getByTestId('research-response-loading')).toBeInTheDocument();
      expect(screen.getByText('Recherche wird durchgefuehrt...')).toBeInTheDocument();
    });
  });

  describe('synthesis display', () => {
    it('renders synthesis text', () => {
      render(
        <ResearchResponseDisplay
          synthesis="This is the research synthesis"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.getByTestId('research-synthesis')).toBeInTheDocument();
      expect(screen.getByText('This is the research synthesis')).toBeInTheDocument();
    });

    it('renders synthesis with data-testid', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test synthesis content"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.getByTestId('research-synthesis')).toBeInTheDocument();
    });
  });

  describe('quality metrics', () => {
    it('displays iteration count', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={{ ...defaultMetrics, iterations: 3 }}
          isLoading={false}
        />
      );

      expect(screen.getByText('Iterationen:')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('displays total sources count', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={{ ...defaultMetrics, totalSources: 10 }}
          isLoading={false}
        />
      );

      expect(screen.getByText('Quellen:')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
    });

    it('displays quality score when available', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={{ ...defaultMetrics, overall_score: 0.85 }}
          isLoading={false}
        />
      );

      expect(screen.getByText('Qualitaet:')).toBeInTheDocument();
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('displays web sources count when > 0', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={{ ...defaultMetrics, webSources: 3 }}
          isLoading={false}
        />
      );

      expect(screen.getByText('Web-Quellen:')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('hides web sources count when 0', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={{ ...defaultMetrics, webSources: 0 }}
          isLoading={false}
        />
      );

      expect(screen.queryByText('Web-Quellen:')).not.toBeInTheDocument();
    });
  });

  describe('research plan section', () => {
    it('renders collapsible research plan section', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={['Step 1', 'Step 2', 'Step 3']}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.getByTestId('research-plan-section')).toBeInTheDocument();
      expect(screen.getByText('Recherche-Plan (3 Schritte)')).toBeInTheDocument();
    });

    it('expands research plan when clicked', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={['Search for topic A', 'Analyze results']}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      const planSection = screen.getByTestId('research-plan-section');
      const button = planSection.querySelector('button');

      fireEvent.click(button!);

      expect(screen.getByText('Search for topic A')).toBeInTheDocument();
      expect(screen.getByText('Analyze results')).toBeInTheDocument();
    });

    it('hides research plan section when empty', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.queryByTestId('research-plan-section')).not.toBeInTheDocument();
    });
  });

  describe('sources section', () => {
    it('renders collapsible sources section', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[createSource(0), createSource(1)]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.getByTestId('research-sources-section')).toBeInTheDocument();
      expect(screen.getByText('Quellen (2)')).toBeInTheDocument();
    });

    it('displays source items with indices', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[createSource(0), createSource(1)]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      // Sources section is expanded by default
      expect(screen.getByTestId('source-item-0')).toBeInTheDocument();
      expect(screen.getByTestId('source-item-1')).toBeInTheDocument();
    });

    it('displays source text content', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[createSource(0)]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.getByText('Source text 0')).toBeInTheDocument();
    });

    it('displays source type badge', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[createSource(0)]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.getByText('vector')).toBeInTheDocument();
    });

    it('displays source score', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[createSource(0)]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.getByText('Score: 90.0%')).toBeInTheDocument();
    });

    it('displays entity tags', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[createSource(0)]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.getByText('Entity0A')).toBeInTheDocument();
      expect(screen.getByText('Entity0B')).toBeInTheDocument();
    });

    it('limits displayed sources to 10', () => {
      const manySources = Array.from({ length: 15 }, (_, i) => createSource(i));

      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={manySources}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      // Should show first 10 sources
      expect(screen.getByTestId('source-item-0')).toBeInTheDocument();
      expect(screen.getByTestId('source-item-9')).toBeInTheDocument();

      // Should show message about additional sources
      expect(screen.getByText('+5 weitere Quellen')).toBeInTheDocument();
    });

    it('hides sources section when empty', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={defaultMetrics}
          isLoading={false}
        />
      );

      expect(screen.queryByTestId('research-sources-section')).not.toBeInTheDocument();
    });
  });

  describe('detailed metrics display', () => {
    it('displays coverage metric when available', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={{
            ...defaultMetrics,
            coverage: 0.75,
          }}
          isLoading={false}
        />
      );

      expect(screen.getByText('75%')).toBeInTheDocument();
      expect(screen.getByText('Abdeckung')).toBeInTheDocument();
    });

    it('displays diversity metric when available', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={{
            ...defaultMetrics,
            diversity: 0.80,
          }}
          isLoading={false}
        />
      );

      expect(screen.getByText('80%')).toBeInTheDocument();
      expect(screen.getByText('Diversitaet')).toBeInTheDocument();
    });

    it('displays completeness metric when available', () => {
      render(
        <ResearchResponseDisplay
          synthesis="Test"
          sources={[]}
          researchPlan={[]}
          qualityMetrics={{
            ...defaultMetrics,
            completeness: 0.90,
          }}
          isLoading={false}
        />
      );

      expect(screen.getByText('90%')).toBeInTheDocument();
      expect(screen.getByText('Vollstaendigkeit')).toBeInTheDocument();
    });
  });
});
