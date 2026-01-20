/**
 * Unit tests for ExtractionSummary component
 * Sprint 117 Feature 117.10: Upload Dialog Classification Display
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ExtractionSummary } from './ExtractionSummary';

describe('ExtractionSummary', () => {
  it('renders all extraction statistics', () => {
    render(
      <ExtractionSummary
        entitiesCount={47}
        relationsCount={23}
        chunksCount={12}
        mentionedInCount={58}
      />
    );

    expect(screen.getByText('Extraction Summary')).toBeInTheDocument();
    expect(screen.getByText('47')).toBeInTheDocument(); // entities_count
    expect(screen.getByText('23')).toBeInTheDocument(); // relations_count
    expect(screen.getByText('12')).toBeInTheDocument(); // chunks_count
    expect(screen.getByText('58')).toBeInTheDocument(); // mentioned_in_count (different from entities)
    expect(screen.getByText('Entities')).toBeInTheDocument();
    expect(screen.getByText('Relations')).toBeInTheDocument();
    expect(screen.getByText('Chunks')).toBeInTheDocument();
    expect(screen.getByText('MENTIONED_IN')).toBeInTheDocument();
  });

  it('renders with zero counts', () => {
    render(
      <ExtractionSummary
        entitiesCount={0}
        relationsCount={0}
        chunksCount={0}
        mentionedInCount={0}
      />
    );

    // Should render four instances of "0"
    const zeroTexts = screen.getAllByText('0');
    expect(zeroTexts.length).toBeGreaterThanOrEqual(4);
  });

  it('renders with large counts', () => {
    render(
      <ExtractionSummary
        entitiesCount={10000}
        relationsCount={50000}
        chunksCount={1000}
        mentionedInCount={20000}
      />
    );

    expect(screen.getByText('10000')).toBeInTheDocument();
    expect(screen.getByText('50000')).toBeInTheDocument();
    expect(screen.getByText('1000')).toBeInTheDocument();
    expect(screen.getByText('20000')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <ExtractionSummary
        entitiesCount={5}
        relationsCount={10}
        chunksCount={3}
        mentionedInCount={5}
        className="custom-summary"
      />
    );

    const summary = container.querySelector('[data-testid="extraction-summary"]');
    expect(summary).toHaveClass('custom-summary');
  });

  it('displays all statistics in a row layout', () => {
    const { container } = render(
      <ExtractionSummary
        entitiesCount={100}
        relationsCount={200}
        chunksCount={50}
        mentionedInCount={100}
      />
    );

    const list = container.querySelector('ul');
    expect(list).toHaveClass('flex', 'flex-wrap', 'gap-4');
  });
});
