/**
 * CommunitiesList Component
 * Sprint 116 Feature 116.7: Graph Communities UI
 *
 * Features:
 * - Display all detected communities in grid layout
 * - Sort by size, topic, or cohesion score
 * - Filter by minimum size
 * - Search communities by topic/description
 * - Click to view details modal
 * - Export community data
 */

import { useState, useMemo } from 'react';
import { Search, SlidersHorizontal, Download, LayoutGrid, List } from 'lucide-react';
import { CommunityCard } from './CommunityCard';
import { CommunityDetailsModal } from './CommunityDetailsModal';
import type { Community } from '../../types/graph';

export type SortField = 'size' | 'topic' | 'density';
export type SortOrder = 'asc' | 'desc';
export type ViewMode = 'grid' | 'list';

interface CommunitiesListProps {
  communities: Community[];
  loading?: boolean;
  onCommunitySelect?: (communityId: string) => void;
  showFilters?: boolean;
  defaultViewMode?: ViewMode;
}

/**
 * Main communities list component with filtering, sorting, and view modes
 *
 * @param communities List of communities to display
 * @param loading Loading state
 * @param onCommunitySelect Callback when community is selected
 * @param showFilters Whether to show filter controls
 * @param defaultViewMode Default view mode (grid or list)
 */
export function CommunitiesList({
  communities,
  loading = false,
  onCommunitySelect,
  showFilters = true,
  defaultViewMode = 'grid',
}: CommunitiesListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [minSize, setMinSize] = useState(1);
  const [sortField, setSortField] = useState<SortField>('size');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [viewMode, setViewMode] = useState<ViewMode>(defaultViewMode);
  const [selectedCommunityId, setSelectedCommunityId] = useState<string | null>(null);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  // Filter and sort communities
  const filteredCommunities = useMemo(() => {
    let filtered = [...communities];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.topic.toLowerCase().includes(query) ||
          c.description?.toLowerCase().includes(query)
      );
    }

    // Size filter
    filtered = filtered.filter((c) => c.size >= minSize);

    // Sort
    filtered.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'size':
          comparison = a.size - b.size;
          break;
        case 'topic':
          comparison = a.topic.localeCompare(b.topic);
          break;
        case 'density':
          comparison = (a.density || 0) - (b.density || 0);
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [communities, searchQuery, minSize, sortField, sortOrder]);

  // Handle community click
  const handleCommunityClick = (communityId: string) => {
    setSelectedCommunityId(communityId);
    onCommunitySelect?.(communityId);
  };

  // Handle export
  const handleExport = () => {
    const data = JSON.stringify(filteredCommunities, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `communities_${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <LoadingSkeleton viewMode={viewMode} />;
  }

  if (communities.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="space-y-4" data-testid="communities-list">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            Communities
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({filteredCommunities.length} of {communities.length})
            </span>
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Detected entity clusters in the knowledge graph
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded transition-colors ${
                viewMode === 'grid'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
              aria-label="Grid view"
              data-testid="view-mode-grid"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded transition-colors ${
                viewMode === 'list'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
              aria-label="List view"
              data-testid="view-mode-list"
            >
              <List className="w-4 h-4" />
            </button>
          </div>

          {/* Filter Toggle */}
          {showFilters && (
            <button
              onClick={() => setShowFilterPanel(!showFilterPanel)}
              className={`p-2 rounded-lg border transition-colors ${
                showFilterPanel
                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400'
              }`}
              aria-label="Toggle filters"
              data-testid="toggle-filters"
            >
              <SlidersHorizontal className="w-4 h-4" />
            </button>
          )}

          {/* Export Button */}
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            data-testid="export-communities"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && showFilterPanel && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-4">
          {/* Search */}
          <div>
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
              Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                id="search"
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by topic or description..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="search-input"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Min Size Filter */}
            <div>
              <label htmlFor="min-size" className="block text-sm font-medium text-gray-700 mb-1">
                Min Size: {minSize}
              </label>
              <input
                id="min-size"
                type="range"
                min="1"
                max="100"
                value={minSize}
                onChange={(e) => setMinSize(Number(e.target.value))}
                className="w-full"
                data-testid="min-size-slider"
              />
            </div>

            {/* Sort Field */}
            <div>
              <label htmlFor="sort-field" className="block text-sm font-medium text-gray-700 mb-1">
                Sort By
              </label>
              <select
                id="sort-field"
                value={sortField}
                onChange={(e) => setSortField(e.target.value as SortField)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                data-testid="sort-field-select"
              >
                <option value="size">Size</option>
                <option value="topic">Topic</option>
                <option value="density">Density</option>
              </select>
            </div>

            {/* Sort Order */}
            <div>
              <label htmlFor="sort-order" className="block text-sm font-medium text-gray-700 mb-1">
                Order
              </label>
              <select
                id="sort-order"
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as SortOrder)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                data-testid="sort-order-select"
              >
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Communities Grid/List */}
      {filteredCommunities.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
          <Search className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-900 mb-1">No communities found</h3>
          <p className="text-sm text-gray-600">Try adjusting your filters or search query</p>
        </div>
      ) : (
        <div
          className={
            viewMode === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
              : 'space-y-3'
          }
          data-testid="communities-container"
        >
          {filteredCommunities.map((community) => (
            <CommunityCard
              key={community.id}
              community={community}
              onClick={() => handleCommunityClick(community.id)}
              compact={viewMode === 'list'}
            />
          ))}
        </div>
      )}

      {/* Details Modal */}
      {selectedCommunityId && (
        <CommunityDetailsModal
          communityId={selectedCommunityId}
          onClose={() => setSelectedCommunityId(null)}
        />
      )}
    </div>
  );
}

/**
 * Loading Skeleton
 */
function LoadingSkeleton({ viewMode }: { viewMode: ViewMode }) {
  return (
    <div className="space-y-4">
      {/* Header Skeleton */}
      <div className="flex items-center justify-between">
        <div>
          <div className="h-6 bg-gray-200 rounded w-48 animate-pulse mb-2" />
          <div className="h-4 bg-gray-200 rounded w-64 animate-pulse" />
        </div>
        <div className="flex gap-2">
          <div className="h-10 w-24 bg-gray-200 rounded animate-pulse" />
          <div className="h-10 w-10 bg-gray-200 rounded animate-pulse" />
        </div>
      </div>

      {/* Cards Skeleton */}
      <div
        className={
          viewMode === 'grid'
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
            : 'space-y-3'
        }
      >
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="border border-gray-200 rounded-lg p-4 animate-pulse"
            data-testid="skeleton-card"
          >
            <div className="h-5 bg-gray-200 rounded w-3/4 mb-3" />
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2" />
            <div className="h-4 bg-gray-200 rounded w-full mb-2" />
            <div className="h-4 bg-gray-200 rounded w-5/6" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Empty State
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center bg-gray-50 rounded-lg border border-gray-200">
      <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-4">
        <LayoutGrid className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">No communities detected</h3>
      <p className="text-sm text-gray-600 max-w-md">
        Communities will appear here once entities are ingested and community detection runs.
        Upload documents to start building your knowledge graph.
      </p>
    </div>
  );
}
