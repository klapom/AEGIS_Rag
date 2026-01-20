/**
 * GraphLegend Component
 * Sprint 116 Feature 116.9: Graph legend with edge type toggles
 *
 * Features:
 * - Show all edge types with color boxes
 * - Allow toggling edge type visibility
 * - Collapsible legend (can minimize)
 * - Color-coded edge types
 */

import { useState } from 'react';

interface GraphLegendProps {
  edgeColors: Record<string, string>;
  visibleEdgeTypes: Set<string>;
  onToggleEdgeType: (edgeType: string) => void;
}

export function GraphLegend({ edgeColors, visibleEdgeTypes, onToggleEdgeType }: GraphLegendProps) {
  const [collapsed, setCollapsed] = useState(false);

  // Filter out DEFAULT and sort alphabetically
  const edgeTypes = Object.keys(edgeColors)
    .filter((type) => type !== 'DEFAULT')
    .sort();

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-2 border border-gray-200 hover:bg-white transition-colors"
        data-testid="legend-expand"
        aria-label="Expand legend"
      >
        <svg className="w-5 h-5 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </button>
    );
  }

  return (
    <div
      className="bg-white/90 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200 max-w-xs"
      data-testid="graph-legend"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">Edge Types</h3>
        <button
          onClick={() => setCollapsed(true)}
          className="text-gray-500 hover:text-gray-700 transition-colors"
          data-testid="legend-collapse"
          aria-label="Collapse legend"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Legend Items */}
      <div className="p-3 space-y-2 max-h-80 overflow-y-auto">
        {edgeTypes.map((edgeType) => {
          const isVisible = visibleEdgeTypes.has(edgeType);
          const color = edgeColors[edgeType];
          const label = edgeType
            .split('_')
            .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
            .join(' ');

          return (
            <button
              key={edgeType}
              onClick={() => onToggleEdgeType(edgeType)}
              className={`flex items-center space-x-2 w-full px-2 py-1.5 rounded transition-colors ${
                isVisible
                  ? 'bg-gray-50 hover:bg-gray-100'
                  : 'bg-gray-100 hover:bg-gray-200 opacity-60'
              }`}
              data-testid={`legend-item-${edgeType.toLowerCase()}`}
            >
              {/* Color box */}
              <div
                className="w-4 h-4 rounded border-2 border-gray-300 flex-shrink-0"
                style={{ backgroundColor: isVisible ? color : '#d1d5db' }}
              />

              {/* Label */}
              <span className={`text-sm flex-grow text-left ${isVisible ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                {label}
              </span>

              {/* Visibility indicator */}
              <div className="flex-shrink-0">
                {isVisible ? (
                  <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Footer with toggle all */}
      <div className="flex gap-2 p-3 border-t border-gray-200 text-xs">
        <button
          onClick={() => edgeTypes.forEach((type) => !visibleEdgeTypes.has(type) && onToggleEdgeType(type))}
          className="flex-1 px-2 py-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
          data-testid="legend-show-all"
        >
          Show All
        </button>
        <button
          onClick={() => edgeTypes.forEach((type) => visibleEdgeTypes.has(type) && onToggleEdgeType(type))}
          className="flex-1 px-2 py-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
          data-testid="legend-hide-all"
        >
          Hide All
        </button>
      </div>
    </div>
  );
}
