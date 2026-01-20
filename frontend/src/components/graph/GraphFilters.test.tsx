/**
 * GraphFilters Component Tests
 * Sprint 116 Feature 116.8: Graph Edge Filters UI Tests
 *
 * Tests edge type filtering, weight threshold slider, and URL persistence.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { GraphFilters, type GraphFilterValues } from './GraphFilters';
import type { EdgeFilters } from '../../types/graph';

describe('GraphFilters - Edge Type Filtering', () => {
  const mockEntityTypes = ['PERSON', 'ORGANIZATION', 'LOCATION'];
  const mockFilters: GraphFilterValues = {
    entityTypes: mockEntityTypes,
    minDegree: 1,
    maxNodes: 100,
  };

  const mockEdgeFilters: EdgeFilters = {
    showRelatesTo: true,
    showCoOccurs: true,
    showMentionedIn: true,
    showHasSection: true,
    showDefines: true,
    showBelongsTo: true,
    showWorksFor: true,
    showLocatedIn: true,
    minWeight: 0,
  };

  const mockOnChange = vi.fn();
  const mockOnEdgeFilterChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders edge type filter section', () => {
    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={mockEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    expect(screen.getByText('Relationship Types')).toBeInTheDocument();
  });

  it('renders all default edge type checkboxes', () => {
    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={mockEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    // Check for default edge types
    expect(screen.getByTestId('edge-filter-co_occurs-checkbox')).toBeInTheDocument();
    expect(screen.getByTestId('edge-filter-relates_to-checkbox')).toBeInTheDocument();
    expect(screen.getByTestId('edge-filter-mentioned_in-checkbox')).toBeInTheDocument();
  });

  it('toggles edge type filter on checkbox click', () => {
    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={mockEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    const checkbox = screen.getByTestId('edge-filter-relates_to-checkbox');
    fireEvent.click(checkbox);

    expect(mockOnEdgeFilterChange).toHaveBeenCalledWith(
      expect.objectContaining({
        showRelatesTo: false,
        showCoOccurs: true,
        showMentionedIn: true,
      })
    );
  });

  it('renders weight threshold slider', () => {
    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={mockEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    const slider = screen.getByTestId('weight-threshold-slider');
    expect(slider).toBeInTheDocument();
    expect(slider).toHaveAttribute('type', 'range');
    expect(slider).toHaveAttribute('min', '0');
    expect(slider).toHaveAttribute('max', '100');
  });

  it('displays correct weight threshold value', () => {
    const edgeFiltersWithWeight: EdgeFilters = {
      ...mockEdgeFilters,
      minWeight: 0.45,
    };

    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={edgeFiltersWithWeight}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    expect(screen.getByTestId('weight-threshold-value')).toHaveTextContent('45%');
  });

  it('updates weight threshold on slider change', () => {
    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={mockEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    const slider = screen.getByTestId('weight-threshold-slider');
    fireEvent.change(slider, { target: { value: '75' } });

    expect(mockOnEdgeFilterChange).toHaveBeenCalledWith(
      expect.objectContaining({
        minWeight: 0.75,
      })
    );
  });

  it('renders extended edge types (HAS_SECTION, DEFINES, etc.)', () => {
    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={mockEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
        availableRelationshipTypes={['HAS_SECTION', 'DEFINES', 'BELONGS_TO']}
      />
    );

    // Extended edge types should be visible
    expect(screen.getByText('Has Section')).toBeInTheDocument();
    expect(screen.getByText('Defines')).toBeInTheDocument();
    expect(screen.getByText('Belongs To')).toBeInTheDocument();
  });

  it('filters relationship types by search input', () => {
    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={mockEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    const searchInput = screen.getByTestId('relationship-search-input');
    fireEvent.change(searchInput, { target: { value: 'Co-Occurs' } });

    // Should show Co-Occurs
    expect(screen.getByText('Co-Occurs')).toBeInTheDocument();

    // Should not show unrelated types
    expect(screen.queryByText('Relates To')).not.toBeInTheDocument();
  });

  it('selects all relationship types on "Select all" click', () => {
    const partialEdgeFilters: EdgeFilters = {
      ...mockEdgeFilters,
      showRelatesTo: false,
      showCoOccurs: false,
    };

    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={partialEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    // "Select all" is in the relationship types section, find all matching text
    const selectAllButtons = screen.getAllByText('Select all');
    // Second button is for relationship types (first is for entity types)
    fireEvent.click(selectAllButtons[1]);

    expect(mockOnEdgeFilterChange).toHaveBeenCalledWith(
      expect.objectContaining({
        showCoOccurs: true,
        showRelatesTo: true,
        showMentionedIn: true,
      })
    );
  });

  it('deselects all relationship types on "Deselect all" click', () => {
    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={mockEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    // "Deselect all" is in the relationship types section, find all matching text
    const deselectAllButtons = screen.getAllByText('Deselect all');
    // Second button is for relationship types (first is for entity types)
    fireEvent.click(deselectAllButtons[1]);

    expect(mockOnEdgeFilterChange).toHaveBeenCalledWith(
      expect.objectContaining({
        showCoOccurs: false,
        showRelatesTo: false,
        showMentionedIn: false,
      })
    );
  });

  it('resets edge filters on "Reset Filters" click', () => {
    const customEdgeFilters: EdgeFilters = {
      showRelatesTo: false,
      showCoOccurs: false,
      showMentionedIn: false,
      minWeight: 0.8,
    };

    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={customEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    const resetButton = screen.getByTestId('reset-filters');
    fireEvent.click(resetButton);

    expect(mockOnEdgeFilterChange).toHaveBeenCalledWith(
      expect.objectContaining({
        showRelatesTo: true,
        showCoOccurs: true,
        showMentionedIn: true,
        minWeight: 0,
      })
    );
  });

  it('handles multiple edge type toggles correctly', () => {
    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={mockEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    // Toggle RELATES_TO off
    fireEvent.click(screen.getByTestId('edge-filter-relates_to-checkbox'));
    expect(mockOnEdgeFilterChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ showRelatesTo: false })
    );

    // Toggle CO_OCCURS off
    fireEvent.click(screen.getByTestId('edge-filter-co_occurs-checkbox'));
    expect(mockOnEdgeFilterChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ showCoOccurs: false })
    );
  });

  it('renders with minimal edge filters (only required types)', () => {
    const minimalEdgeFilters: EdgeFilters = {
      showRelatesTo: true,
      showCoOccurs: true,
      showMentionedIn: true,
      minWeight: 0,
    };

    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={minimalEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
      />
    );

    // Should still render without optional edge types
    expect(screen.getByText('Relationship Types')).toBeInTheDocument();
  });

  it('handles edge filter changes with optional types', () => {
    const extendedEdgeFilters: EdgeFilters = {
      showRelatesTo: true,
      showCoOccurs: true,
      showMentionedIn: true,
      showHasSection: true,
      showDefines: false,
      minWeight: 0.3,
    };

    render(
      <GraphFilters
        entityTypes={mockEntityTypes}
        value={mockFilters}
        onChange={mockOnChange}
        edgeFilters={extendedEdgeFilters}
        onEdgeFilterChange={mockOnEdgeFilterChange}
        availableRelationshipTypes={['HAS_SECTION', 'DEFINES']}
      />
    );

    // HAS_SECTION should be checked
    const hasSectionCheckbox = screen.getByLabelText('Show HAS_SECTION relationships');
    expect(hasSectionCheckbox).toBeChecked();

    // DEFINES should not be checked
    const definesCheckbox = screen.getByLabelText('Show DEFINES relationships');
    expect(definesCheckbox).not.toBeChecked();
  });
});
