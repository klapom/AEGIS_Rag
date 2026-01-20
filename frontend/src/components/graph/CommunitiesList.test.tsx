/**
 * CommunitiesList Component Tests
 * Sprint 116 Feature 116.7: Graph Communities UI
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { CommunitiesList } from './CommunitiesList';
import type { Community } from '../../types/graph';

// Mock CommunityCard and CommunityDetailsModal
vi.mock('./CommunityCard', () => ({
  CommunityCard: ({ community, onClick }: any) => (
    <div data-testid={`community-card-${community.id}`} onClick={onClick}>
      {community.topic}
    </div>
  ),
}));

vi.mock('./CommunityDetailsModal', () => ({
  CommunityDetailsModal: ({ communityId, onClose }: any) => (
    <div data-testid="community-details-modal">
      <button onClick={onClose}>Close</button>
      Modal for {communityId}
    </div>
  ),
}));

describe('CommunitiesList', () => {
  const mockCommunities: Community[] = [
    {
      id: 'comm-1',
      topic: 'Machine Learning',
      size: 25,
      density: 0.8,
      description: 'AI and ML research',
    },
    {
      id: 'comm-2',
      topic: 'Data Science',
      size: 15,
      density: 0.6,
      description: 'Data analysis and visualization',
    },
    {
      id: 'comm-3',
      topic: 'Software Engineering',
      size: 30,
      density: 0.7,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render communities list with all communities', () => {
      render(<CommunitiesList communities={mockCommunities} />);

      expect(screen.getByTestId('communities-list')).toBeInTheDocument();
      expect(screen.getByText(/3 of 3/)).toBeInTheDocument();
      expect(screen.getByTestId('community-card-comm-1')).toBeInTheDocument();
      expect(screen.getByTestId('community-card-comm-2')).toBeInTheDocument();
      expect(screen.getByTestId('community-card-comm-3')).toBeInTheDocument();
    });

    it('should render loading skeleton when loading', () => {
      render(<CommunitiesList communities={[]} loading={true} />);

      const skeletons = screen.getAllByTestId('skeleton-card');
      expect(skeletons).toHaveLength(6);
    });

    it('should render empty state when no communities', () => {
      render(<CommunitiesList communities={[]} />);

      expect(screen.getByText('No communities detected')).toBeInTheDocument();
      expect(
        screen.getByText(/Communities will appear here once entities are ingested/)
      ).toBeInTheDocument();
    });
  });

  describe('View Modes', () => {
    it('should default to grid view', () => {
      render(<CommunitiesList communities={mockCommunities} />);

      const container = screen.getByTestId('communities-container');
      expect(container).toHaveClass('grid');
    });

    it('should switch to list view when list button clicked', () => {
      render(<CommunitiesList communities={mockCommunities} />);

      const listButton = screen.getByTestId('view-mode-list');
      fireEvent.click(listButton);

      const container = screen.getByTestId('communities-container');
      expect(container).toHaveClass('space-y-3');
    });

    it('should toggle back to grid view', () => {
      render(<CommunitiesList communities={mockCommunities} />);

      const listButton = screen.getByTestId('view-mode-list');
      fireEvent.click(listButton);

      const gridButton = screen.getByTestId('view-mode-grid');
      fireEvent.click(gridButton);

      const container = screen.getByTestId('communities-container');
      expect(container).toHaveClass('grid');
    });
  });

  describe('Filtering and Sorting', () => {
    it('should toggle filter panel when filter button clicked', () => {
      render(<CommunitiesList communities={mockCommunities} showFilters={true} />);

      const filterButton = screen.getByTestId('toggle-filters');
      fireEvent.click(filterButton);

      expect(screen.getByTestId('search-input')).toBeInTheDocument();
      expect(screen.getByTestId('min-size-slider')).toBeInTheDocument();
      expect(screen.getByTestId('sort-field-select')).toBeInTheDocument();
    });

    it('should filter communities by search query', () => {
      render(<CommunitiesList communities={mockCommunities} showFilters={true} />);

      const filterButton = screen.getByTestId('toggle-filters');
      fireEvent.click(filterButton);

      const searchInput = screen.getByTestId('search-input');
      fireEvent.change(searchInput, { target: { value: 'Machine' } });

      // Should show only 1 community matching "Machine"
      expect(screen.getByText(/1 of 3/)).toBeInTheDocument();
      expect(screen.getByTestId('community-card-comm-1')).toBeInTheDocument();
      expect(screen.queryByTestId('community-card-comm-2')).not.toBeInTheDocument();
    });

    it('should filter by minimum size', () => {
      render(<CommunitiesList communities={mockCommunities} showFilters={true} />);

      const filterButton = screen.getByTestId('toggle-filters');
      fireEvent.click(filterButton);

      const sizeSlider = screen.getByTestId('min-size-slider');
      fireEvent.change(sizeSlider, { target: { value: '20' } });

      // Should show only communities with size >= 20
      expect(screen.getByText(/2 of 3/)).toBeInTheDocument();
    });

    it('should sort by size descending by default', () => {
      render(<CommunitiesList communities={mockCommunities} />);

      const cards = screen.getAllByTestId(/community-card-/);
      // Should be sorted by size desc: comm-3 (30), comm-1 (25), comm-2 (15)
      expect(cards[0]).toHaveAttribute('data-testid', 'community-card-comm-3');
      expect(cards[1]).toHaveAttribute('data-testid', 'community-card-comm-1');
      expect(cards[2]).toHaveAttribute('data-testid', 'community-card-comm-2');
    });

    it('should change sort field', () => {
      render(<CommunitiesList communities={mockCommunities} showFilters={true} />);

      const filterButton = screen.getByTestId('toggle-filters');
      fireEvent.click(filterButton);

      const sortFieldSelect = screen.getByTestId('sort-field-select');
      fireEvent.change(sortFieldSelect, { target: { value: 'topic' } });

      const cards = screen.getAllByTestId(/community-card-/);
      // Should be sorted alphabetically desc: Software, Machine, Data
      expect(cards[0]).toHaveAttribute('data-testid', 'community-card-comm-3');
    });

    it('should change sort order to ascending', () => {
      render(<CommunitiesList communities={mockCommunities} showFilters={true} />);

      const filterButton = screen.getByTestId('toggle-filters');
      fireEvent.click(filterButton);

      const sortOrderSelect = screen.getByTestId('sort-order-select');
      fireEvent.change(sortOrderSelect, { target: { value: 'asc' } });

      const cards = screen.getAllByTestId(/community-card-/);
      // Should be sorted by size asc: comm-2 (15), comm-1 (25), comm-3 (30)
      expect(cards[0]).toHaveAttribute('data-testid', 'community-card-comm-2');
      expect(cards[1]).toHaveAttribute('data-testid', 'community-card-comm-1');
      expect(cards[2]).toHaveAttribute('data-testid', 'community-card-comm-3');
    });

    it('should show no results message when filters exclude all', () => {
      render(<CommunitiesList communities={mockCommunities} showFilters={true} />);

      const filterButton = screen.getByTestId('toggle-filters');
      fireEvent.click(filterButton);

      const searchInput = screen.getByTestId('search-input');
      fireEvent.change(searchInput, { target: { value: 'NonExistent' } });

      expect(screen.getByText('No communities found')).toBeInTheDocument();
      expect(screen.getByText(/Try adjusting your filters/)).toBeInTheDocument();
    });
  });

  describe('Export Functionality', () => {
    it('should have export button', () => {
      render(<CommunitiesList communities={mockCommunities} />);

      expect(screen.getByTestId('export-communities')).toBeInTheDocument();
    });

    it('should export communities as JSON when clicked', () => {
      const createElementSpy = vi.spyOn(document, 'createElement');
      const createObjectURLSpy = vi.spyOn(URL, 'createObjectURL');

      render(<CommunitiesList communities={mockCommunities} />);

      const exportButton = screen.getByTestId('export-communities');
      fireEvent.click(exportButton);

      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(createObjectURLSpy).toHaveBeenCalled();
    });
  });

  describe('Community Selection', () => {
    it('should call onCommunitySelect when community clicked', () => {
      const onSelect = vi.fn();
      render(<CommunitiesList communities={mockCommunities} onCommunitySelect={onSelect} />);

      const card = screen.getByTestId('community-card-comm-1');
      fireEvent.click(card);

      expect(onSelect).toHaveBeenCalledWith('comm-1');
    });

    it('should open details modal when community clicked', () => {
      render(<CommunitiesList communities={mockCommunities} />);

      const card = screen.getByTestId('community-card-comm-1');
      fireEvent.click(card);

      expect(screen.getByTestId('community-details-modal')).toBeInTheDocument();
      expect(screen.getByText(/Modal for comm-1/)).toBeInTheDocument();
    });

    it('should close details modal when close button clicked', () => {
      render(<CommunitiesList communities={mockCommunities} />);

      // Open modal
      const card = screen.getByTestId('community-card-comm-1');
      fireEvent.click(card);

      // Close modal
      const closeButton = screen.getByText('Close');
      fireEvent.click(closeButton);

      expect(screen.queryByTestId('community-details-modal')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<CommunitiesList communities={mockCommunities} showFilters={true} />);

      const filterButton = screen.getByTestId('toggle-filters');
      fireEvent.click(filterButton);

      expect(screen.getByLabelText('Search')).toBeInTheDocument();
      expect(screen.getByLabelText(/Min Size:/)).toBeInTheDocument();
    });

    it('should support keyboard navigation in search', () => {
      render(<CommunitiesList communities={mockCommunities} showFilters={true} />);

      const filterButton = screen.getByTestId('toggle-filters');
      fireEvent.click(filterButton);

      const searchInput = screen.getByTestId('search-input');
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      // Should not crash and input should still be there
      expect(searchInput).toBeInTheDocument();
    });
  });
});
