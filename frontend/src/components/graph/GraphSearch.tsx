/**
 * GraphSearch Component
 * Sprint 29 Feature 29.5: Graph Explorer with Search
 *
 * Features:
 * - Real-time node search as user types (>2 chars)
 * - Dropdown results (max 10 nodes)
 * - Color dot by entity type
 * - Click result -> onNodeSelect callback
 */

import { useState, useEffect, useRef } from 'react';
import type { GraphData } from '../../types/graph';
import { useGraphSearch } from '../../hooks/useGraphSearch';

interface GraphSearchProps {
  data: GraphData;
  onNodeSelect: (nodeId: string) => void;
  placeholder?: string;
}

/**
 * Search component for finding nodes in the graph
 *
 * @param data Graph data to search through
 * @param onNodeSelect Callback when a node is selected
 * @param placeholder Optional placeholder text
 */
export function GraphSearch({
  data,
  onNodeSelect,
  placeholder = 'Search entities...',
}: GraphSearchProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const results = useGraphSearch(data, query);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Show dropdown when results are available
  useEffect(() => {
    setIsOpen(results.length > 0);
  }, [results]);

  const handleNodeClick = (nodeId: string) => {
    onNodeSelect(nodeId);
    setQuery('');
    setIsOpen(false);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  return (
    <div ref={searchRef} className="relative w-full">
      {/* Search Input */}
      <div className="relative">
        <input
          type="search"
          value={query}
          onChange={handleInputChange}
          placeholder={placeholder}
          className="w-full px-4 py-2.5 pl-10 text-sm bg-white border-2 border-gray-300 rounded-lg
                     focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20
                     placeholder-gray-400 transition-all duration-200
                     hover:border-gray-400"
          aria-label="Search graph nodes"
        />

        {/* Search Icon */}
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>

      {/* Results Dropdown */}
      {isOpen && results.length > 0 && (
        <div
          className="absolute top-full mt-1 w-full bg-white border-2 border-gray-200 rounded-lg shadow-lg z-20 max-h-80 overflow-y-auto"
          role="listbox"
          aria-label="Search results"
        >
          {results.map((node) => (
            <button
              key={node.id}
              onClick={() => handleNodeClick(node.id)}
              className="w-full px-4 py-3 text-left hover:bg-gray-50 active:bg-gray-100
                         flex items-center gap-3 border-b border-gray-100 last:border-b-0
                         transition-colors duration-150"
              role="option"
              aria-selected="false"
            >
              {/* Entity Type Color Dot */}
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: getColorByType(node.type) }}
                aria-hidden="true"
              />

              {/* Node Label */}
              <span className="font-medium text-gray-900 flex-grow truncate">
                {node.label}
              </span>

              {/* Entity Type Badge */}
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full flex-shrink-0">
                {node.type}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* No Results Message */}
      {query.length >= 2 && results.length === 0 && (
        <div className="absolute top-full mt-1 w-full bg-white border-2 border-gray-200 rounded-lg shadow-lg z-20 px-4 py-6 text-center">
          <div className="text-sm text-gray-500">
            No entities found matching "{query}"
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Get color for entity type
 * Matches the color scheme in GraphViewer.tsx
 */
function getColorByType(type: string): string {
  const normalizedType = type.toUpperCase();
  switch (normalizedType) {
    case 'PERSON':
      return '#3b82f6'; // Blue
    case 'ORGANIZATION':
      return '#10b981'; // Green
    case 'LOCATION':
      return '#ef4444'; // Red
    case 'EVENT':
      return '#f59e0b'; // Amber
    case 'DATE':
      return '#ec4899'; // Pink
    case 'PRODUCT':
      return '#8b5cf6'; // Purple
    default:
      return '#6b7280'; // Gray
  }
}
