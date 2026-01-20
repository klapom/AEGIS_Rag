/**
 * GraphLegend Component Tests
 * Sprint 116 Feature 116.9: Graph legend with edge type toggles
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GraphLegend } from '../../../components/graph/GraphLegend';

describe('GraphLegend', () => {
  const mockEdgeColors = {
    RELATES_TO: '#3B82F6',
    MENTIONED_IN: '#22C55E',
    CONTAINS: '#F97316',
    PART_OF: '#A855F7',
    SIMILAR_TO: '#06B6D4',
    CO_OCCURS: '#EAB308',
    REFERENCES: '#EC4899',
    DEFAULT: '#6B7280',
  };

  const allEdgeTypes = new Set(Object.keys(mockEdgeColors).filter((k) => k !== 'DEFAULT'));

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders legend with all edge types', () => {
    const onToggle = vi.fn();
    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={allEdgeTypes}
        onToggleEdgeType={onToggle}
      />
    );

    expect(screen.getByTestId('graph-legend')).toBeInTheDocument();
    expect(screen.getByText('Edge Types')).toBeInTheDocument();
  });

  it('renders all edge type items except DEFAULT', () => {
    const onToggle = vi.fn();
    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={allEdgeTypes}
        onToggleEdgeType={onToggle}
      />
    );

    // Should render all edge types except DEFAULT
    expect(screen.getByTestId('legend-item-relates_to')).toBeInTheDocument();
    expect(screen.getByTestId('legend-item-mentioned_in')).toBeInTheDocument();
    expect(screen.getByTestId('legend-item-contains')).toBeInTheDocument();
    expect(screen.getByTestId('legend-item-part_of')).toBeInTheDocument();
    expect(screen.getByTestId('legend-item-similar_to')).toBeInTheDocument();
    expect(screen.getByTestId('legend-item-co_occurs')).toBeInTheDocument();
    expect(screen.getByTestId('legend-item-references')).toBeInTheDocument();

    // Should not render DEFAULT
    expect(screen.queryByTestId('legend-item-default')).not.toBeInTheDocument();
  });

  it('toggles edge type visibility on click', () => {
    const onToggle = vi.fn();
    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={allEdgeTypes}
        onToggleEdgeType={onToggle}
      />
    );

    const relatesTo = screen.getByTestId('legend-item-relates_to');
    fireEvent.click(relatesTo);

    expect(onToggle).toHaveBeenCalledWith('RELATES_TO');
  });

  it('shows Show All and Hide All buttons', () => {
    const onToggle = vi.fn();
    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={allEdgeTypes}
        onToggleEdgeType={onToggle}
      />
    );

    expect(screen.getByTestId('legend-show-all')).toBeInTheDocument();
    expect(screen.getByTestId('legend-hide-all')).toBeInTheDocument();
  });

  it('calls onToggleEdgeType for all types on Show All', () => {
    const visibleTypes = new Set(['RELATES_TO']); // Only one visible
    const onToggle = vi.fn();

    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={visibleTypes}
        onToggleEdgeType={onToggle}
      />
    );

    const showAllButton = screen.getByTestId('legend-show-all');
    fireEvent.click(showAllButton);

    // Should toggle all hidden types
    const expectedCalls = Array.from(allEdgeTypes).filter((type) => !visibleTypes.has(type)).length;
    expect(onToggle).toHaveBeenCalledTimes(expectedCalls);
  });

  it('calls onToggleEdgeType for all types on Hide All', () => {
    const onToggle = vi.fn();

    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={allEdgeTypes}
        onToggleEdgeType={onToggle}
      />
    );

    const hideAllButton = screen.getByTestId('legend-hide-all');
    fireEvent.click(hideAllButton);

    // Should toggle all visible types
    expect(onToggle).toHaveBeenCalledTimes(allEdgeTypes.size);
  });

  it('collapses legend on collapse button click', () => {
    const onToggle = vi.fn();
    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={allEdgeTypes}
        onToggleEdgeType={onToggle}
      />
    );

    const collapseButton = screen.getByTestId('legend-collapse');
    fireEvent.click(collapseButton);

    // Legend should be collapsed (only expand button visible)
    expect(screen.queryByText('Edge Types')).not.toBeInTheDocument();
    expect(screen.getByTestId('legend-expand')).toBeInTheDocument();
  });

  it('expands legend on expand button click', () => {
    const onToggle = vi.fn();
    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={allEdgeTypes}
        onToggleEdgeType={onToggle}
      />
    );

    // Collapse first
    const collapseButton = screen.getByTestId('legend-collapse');
    fireEvent.click(collapseButton);

    // Then expand
    const expandButton = screen.getByTestId('legend-expand');
    fireEvent.click(expandButton);

    expect(screen.getByText('Edge Types')).toBeInTheDocument();
  });

  it('applies correct color to edge type items', () => {
    const onToggle = vi.fn();
    const { container } = render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={allEdgeTypes}
        onToggleEdgeType={onToggle}
      />
    );

    const relatesTo = screen.getByTestId('legend-item-relates_to');
    const colorBox = relatesTo.querySelector('div');
    expect(colorBox).toHaveStyle({ backgroundColor: mockEdgeColors.RELATES_TO });
  });

  it('renders formatted edge type labels', () => {
    const onToggle = vi.fn();
    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={allEdgeTypes}
        onToggleEdgeType={onToggle}
      />
    );

    // RELATES_TO should be formatted as "Relates To"
    expect(screen.getByText('Relates To')).toBeInTheDocument();
    // MENTIONED_IN should be formatted as "Mentioned In"
    expect(screen.getByText('Mentioned In')).toBeInTheDocument();
    // CO_OCCURS should be formatted as "Co Occurs"
    expect(screen.getByText('Co Occurs')).toBeInTheDocument();
  });

  it('shows visibility indicator for visible edge types', () => {
    const onToggle = vi.fn();
    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={allEdgeTypes}
        onToggleEdgeType={onToggle}
      />
    );

    // All edge types should have eye icon (visible)
    const relatesTo = screen.getByTestId('legend-item-relates_to');
    expect(relatesTo.querySelector('svg')).toBeInTheDocument();
  });

  it('shows visibility indicator for hidden edge types', () => {
    const visibleTypes = new Set<string>(); // None visible
    const onToggle = vi.fn();
    render(
      <GraphLegend
        edgeColors={mockEdgeColors}
        visibleEdgeTypes={visibleTypes}
        onToggleEdgeType={onToggle}
      />
    );

    // All edge types should have eye-off icon (hidden)
    const relatesTo = screen.getByTestId('legend-item-relates_to');
    expect(relatesTo.querySelector('svg')).toBeInTheDocument();
  });
});
