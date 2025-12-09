/**
 * GraphFilters Component
 * Sprint 29 Feature 29.5: Graph Explorer with Search
 * Sprint 34 Feature 34.6: Graph Edge Filter Controls
 *
 * Features:
 * - Multi-select for entity types
 * - Slider for minimum degree (1-20)
 * - Dropdown for max nodes (50/100/200/500)
 * - Edge type filters (RELATES_TO, MENTIONED_IN)
 * - Weight threshold slider for relationship strength
 * - onChange callback with updated filters
 */

import { useState, useEffect } from 'react';
import type { EdgeFilters } from '../../types/graph';

export interface GraphFilterValues {
  entityTypes: string[];
  minDegree: number;
  maxNodes: number;
}

interface GraphFiltersProps {
  entityTypes: string[]; // Available entity types
  value: GraphFilterValues;
  onChange: (filters: GraphFilterValues) => void;
  // Sprint 34 Feature 34.6: Edge filters
  edgeFilters?: EdgeFilters;
  onEdgeFilterChange?: (edgeFilters: EdgeFilters) => void;
}

const ENTITY_TYPE_OPTIONS = [
  { value: 'PERSON', label: 'Person', color: '#3b82f6' },
  { value: 'ORGANIZATION', label: 'Organization', color: '#10b981' },
  { value: 'LOCATION', label: 'Location', color: '#ef4444' },
  { value: 'EVENT', label: 'Event', color: '#f59e0b' },
  { value: 'DATE', label: 'Date', color: '#ec4899' },
  { value: 'PRODUCT', label: 'Product', color: '#8b5cf6' },
];

const MAX_NODES_OPTIONS = [50, 100, 200, 500];

/**
 * Filter controls for graph visualization
 *
 * @param entityTypes Available entity types in the graph
 * @param value Current filter values
 * @param onChange Callback when filters change
 * @param edgeFilters Edge filter values (Sprint 34 Feature 34.6)
 * @param onEdgeFilterChange Callback when edge filters change
 */
export function GraphFilters({
  entityTypes,
  value,
  onChange,
  edgeFilters,
  onEdgeFilterChange
}: GraphFiltersProps) {
  const [localFilters, setLocalFilters] = useState(value);
  const [localEdgeFilters, setLocalEdgeFilters] = useState<EdgeFilters>(
    edgeFilters || { showRelatesTo: true, showCoOccurs: true, showMentionedIn: true, minWeight: 0 }
  );

  // Update local state when external value changes
  useEffect(() => {
    setLocalFilters(value);
  }, [value]);

  // Update local edge filters when external value changes
  useEffect(() => {
    if (edgeFilters) {
      setLocalEdgeFilters(edgeFilters);
    }
  }, [edgeFilters]);

  const handleEntityTypeToggle = (type: string) => {
    const newTypes = localFilters.entityTypes.includes(type)
      ? localFilters.entityTypes.filter((t) => t !== type)
      : [...localFilters.entityTypes, type];

    const updated = { ...localFilters, entityTypes: newTypes };
    setLocalFilters(updated);
    onChange(updated);
  };

  const handleMinDegreeChange = (degree: number) => {
    const updated = { ...localFilters, minDegree: degree };
    setLocalFilters(updated);
    onChange(updated);
  };

  const handleMaxNodesChange = (maxNodes: number) => {
    const updated = { ...localFilters, maxNodes };
    setLocalFilters(updated);
    onChange(updated);
  };

  // Sprint 34 Feature 34.6: Edge filter handlers
  const handleEdgeFilterChange = (updatedEdgeFilters: EdgeFilters) => {
    setLocalEdgeFilters(updatedEdgeFilters);
    if (onEdgeFilterChange) {
      onEdgeFilterChange(updatedEdgeFilters);
    }
  };

  // Filter options to only show available entity types
  const availableOptions = ENTITY_TYPE_OPTIONS.filter((option) =>
    entityTypes.includes(option.value)
  );

  return (
    <div className="space-y-6 p-4 bg-white rounded-lg border-2 border-gray-200">
      {/* Entity Types Filter */}
      <div>
        <label className="block text-sm font-semibold text-gray-900 mb-3">
          Entity Types
        </label>
        <div className="space-y-2">
          {availableOptions.map((option) => (
            <EntityTypeCheckbox
              key={option.value}
              label={option.label}
              color={option.color}
              checked={localFilters.entityTypes.includes(option.value)}
              onChange={() => handleEntityTypeToggle(option.value)}
            />
          ))}
        </div>
      </div>

      {/* Minimum Degree Filter */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label htmlFor="min-degree-slider" className="block text-sm font-semibold text-gray-900">
            Minimum Degree
          </label>
          <span className="text-sm text-gray-600 font-medium">
            {localFilters.minDegree} connections
          </span>
        </div>
        <input
          id="min-degree-slider"
          type="range"
          min={1}
          max={20}
          value={localFilters.minDegree}
          onChange={(e) => handleMinDegreeChange(parseInt(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer
                     focus:outline-none focus:ring-2 focus:ring-primary/20
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-4
                     [&::-webkit-slider-thumb]:h-4
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:bg-primary
                     [&::-webkit-slider-thumb]:cursor-pointer
                     [&::-webkit-slider-thumb]:hover:bg-primary-hover
                     [&::-moz-range-thumb]:w-4
                     [&::-moz-range-thumb]:h-4
                     [&::-moz-range-thumb]:rounded-full
                     [&::-moz-range-thumb]:bg-primary
                     [&::-moz-range-thumb]:cursor-pointer
                     [&::-moz-range-thumb]:border-0
                     [&::-moz-range-thumb]:hover:bg-primary-hover"
          aria-label="Minimum node degree"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>1</span>
          <span>20</span>
        </div>
      </div>

      {/* Max Nodes Filter */}
      <div>
        <label htmlFor="max-nodes-select" className="block text-sm font-semibold text-gray-900 mb-2">
          Maximum Nodes
        </label>
        <select
          id="max-nodes-select"
          value={localFilters.maxNodes}
          onChange={(e) => handleMaxNodesChange(parseInt(e.target.value))}
          className="w-full px-3 py-2 text-sm bg-white border-2 border-gray-300 rounded-lg
                     focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20
                     hover:border-gray-400 transition-all duration-200 cursor-pointer"
          aria-label="Maximum number of nodes"
        >
          {MAX_NODES_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option} nodes
            </option>
          ))}
        </select>
      </div>

      {/* Sprint 34 Feature 34.6: Edge Type Filters Section */}
      <div className="border-t border-gray-200 pt-4" data-testid="graph-edge-filter">
        <h4 className="text-sm font-semibold text-gray-900 mb-3">Relationship Types</h4>

        <div className="space-y-2" data-testid="edge-type-filter">
          <label className="flex items-center space-x-2 cursor-pointer group" data-testid="edge-filter-co-occurs">
            <input
              type="checkbox"
              checked={localEdgeFilters.showCoOccurs}
              onChange={(e) => handleEdgeFilterChange({
                ...localEdgeFilters,
                showCoOccurs: e.target.checked
              })}
              className="w-4 h-4 text-primary border-2 border-gray-300 rounded
                         focus:ring-2 focus:ring-primary/20 focus:ring-offset-0 cursor-pointer"
              aria-label="Show CO_OCCURS relationships"
              data-testid="edge-filter-co-occurs-checkbox"
            />
            <div className="w-4 h-0.5 bg-purple-500"></div>
            <span className="text-sm text-gray-700 group-hover:text-gray-900 font-medium">
              Co-Occurs
            </span>
          </label>

          <label className="flex items-center space-x-2 cursor-pointer group" data-testid="edge-filter-relates-to">
            <input
              type="checkbox"
              checked={localEdgeFilters.showRelatesTo}
              onChange={(e) => handleEdgeFilterChange({
                ...localEdgeFilters,
                showRelatesTo: e.target.checked
              })}
              className="w-4 h-4 text-primary border-2 border-gray-300 rounded
                         focus:ring-2 focus:ring-primary/20 focus:ring-offset-0 cursor-pointer"
              aria-label="Show RELATES_TO relationships"
              data-testid="edge-filter-relates-to-checkbox"
            />
            <div className="w-4 h-0.5 bg-blue-500"></div>
            <span className="text-sm text-gray-700 group-hover:text-gray-900 font-medium">
              Relates To
            </span>
          </label>

          <label className="flex items-center space-x-2 cursor-pointer group" data-testid="edge-filter-mentioned-in">
            <input
              type="checkbox"
              checked={localEdgeFilters.showMentionedIn}
              onChange={(e) => handleEdgeFilterChange({
                ...localEdgeFilters,
                showMentionedIn: e.target.checked
              })}
              className="w-4 h-4 text-primary border-2 border-gray-300 rounded
                         focus:ring-2 focus:ring-primary/20 focus:ring-offset-0 cursor-pointer"
              aria-label="Show MENTIONED_IN relationships"
              data-testid="edge-filter-mentioned-in-checkbox"
            />
            <div className="w-4 h-0.5 bg-gray-400"></div>
            <span className="text-sm text-gray-700 group-hover:text-gray-900 font-medium">
              Mentioned In
            </span>
          </label>
        </div>

        {/* Weight Threshold Slider */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="edge-weight-slider" className="block text-sm font-medium text-gray-700">
              Min Relationship Strength
            </label>
            <span className="text-sm text-gray-600 font-medium" data-testid="weight-threshold-value">
              {Math.round(localEdgeFilters.minWeight * 100)}%
            </span>
          </div>
          <input
            id="edge-weight-slider"
            type="range"
            min="0"
            max="100"
            value={localEdgeFilters.minWeight * 100}
            onChange={(e) => handleEdgeFilterChange({
              ...localEdgeFilters,
              minWeight: parseInt(e.target.value) / 100
            })}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer
                       focus:outline-none focus:ring-2 focus:ring-primary/20
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:h-4
                       [&::-webkit-slider-thumb]:rounded-full
                       [&::-webkit-slider-thumb]:bg-primary
                       [&::-webkit-slider-thumb]:cursor-pointer
                       [&::-webkit-slider-thumb]:hover:bg-primary-hover
                       [&::-moz-range-thumb]:w-4
                       [&::-moz-range-thumb]:h-4
                       [&::-moz-range-thumb]:rounded-full
                       [&::-moz-range-thumb]:bg-primary
                       [&::-moz-range-thumb]:cursor-pointer
                       [&::-moz-range-thumb]:border-0
                       [&::-moz-range-thumb]:hover:bg-primary-hover"
            aria-label="Minimum relationship strength"
            data-testid="weight-threshold-slider"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0%</span>
            <span>100%</span>
          </div>
        </div>
      </div>

      {/* Reset Filters Button */}
      <button
        onClick={() => {
          const defaultFilters: GraphFilterValues = {
            entityTypes: availableOptions.map((opt) => opt.value),
            minDegree: 1,
            maxNodes: 100,
          };
          const defaultEdgeFilters: EdgeFilters = {
            showRelatesTo: true,
            showCoOccurs: true,
            showMentionedIn: true,
            minWeight: 0,
          };
          setLocalFilters(defaultFilters);
          setLocalEdgeFilters(defaultEdgeFilters);
          onChange(defaultFilters);
          if (onEdgeFilterChange) {
            onEdgeFilterChange(defaultEdgeFilters);
          }
        }}
        className="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100
                   hover:bg-gray-200 active:bg-gray-300 rounded-lg
                   transition-colors duration-200"
        data-testid="reset-filters"
      >
        Reset Filters
      </button>
    </div>
  );
}

/**
 * Checkbox component for entity type selection
 */
interface EntityTypeCheckboxProps {
  label: string;
  color: string;
  checked: boolean;
  onChange: () => void;
}

function EntityTypeCheckbox({ label, color, checked, onChange }: EntityTypeCheckboxProps) {
  return (
    <label className="flex items-center space-x-3 cursor-pointer group">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="w-4 h-4 text-primary border-2 border-gray-300 rounded
                   focus:ring-2 focus:ring-primary/20 focus:ring-offset-0
                   cursor-pointer"
        aria-label={`Filter ${label}`}
      />
      <span
        className="w-3 h-3 rounded-full flex-shrink-0"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />
      <span className="text-sm text-gray-700 group-hover:text-gray-900 font-medium">
        {label}
      </span>
    </label>
  );
}
