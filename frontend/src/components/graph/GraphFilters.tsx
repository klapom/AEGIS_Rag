/**
 * GraphFilters Component
 * Sprint 29 Feature 29.5: Graph Explorer with Search
 * Sprint 34 Feature 34.6: Graph Edge Filter Controls
 * Sprint 51: Added search for entity types and relationship types
 *
 * Features:
 * - Multi-select for entity types with search
 * - Slider for minimum degree (1-20)
 * - Dropdown for max nodes (50/100/200/500)
 * - Edge type filters (RELATES_TO, MENTIONED_IN) with search
 * - Weight threshold slider for relationship strength
 * - onChange callback with updated filters
 */

import { useState, useEffect, useMemo } from 'react';
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
  // Sprint 51: Available relationship types from graph
  availableRelationshipTypes?: string[];
}

const ENTITY_TYPE_OPTIONS = [
  { value: 'PERSON', label: 'Person', color: '#3b82f6' },
  { value: 'ORGANIZATION', label: 'Organization', color: '#10b981' },
  { value: 'LOCATION', label: 'Location', color: '#ef4444' },
  { value: 'EVENT', label: 'Event', color: '#f59e0b' },
  { value: 'DATE', label: 'Date', color: '#ec4899' },
  { value: 'PRODUCT', label: 'Product', color: '#8b5cf6' },
  { value: 'CONCEPT', label: 'Concept', color: '#06b6d4' },
  { value: 'DOCUMENT', label: 'Document', color: '#84cc16' },
  { value: 'TECHNOLOGY', label: 'Technology', color: '#f97316' },
];

// Default relationship types
const DEFAULT_RELATIONSHIP_TYPES = [
  { value: 'CO_OCCURS', label: 'Co-Occurs', color: '#8b5cf6' },
  { value: 'RELATES_TO', label: 'Relates To', color: '#3b82f6' },
  { value: 'MENTIONED_IN', label: 'Mentioned In', color: '#6b7280' },
  { value: 'BELONGS_TO', label: 'Belongs To', color: '#10b981' },
  { value: 'WORKS_FOR', label: 'Works For', color: '#f59e0b' },
  { value: 'LOCATED_IN', label: 'Located In', color: '#ef4444' },
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
 * @param availableRelationshipTypes Available relationship types (Sprint 51)
 */
export function GraphFilters({
  entityTypes,
  value,
  onChange,
  edgeFilters,
  onEdgeFilterChange,
  availableRelationshipTypes,
}: GraphFiltersProps) {
  const [localFilters, setLocalFilters] = useState(value);
  const [localEdgeFilters, setLocalEdgeFilters] = useState<EdgeFilters>(
    edgeFilters || { showRelatesTo: true, showCoOccurs: true, showMentionedIn: true, minWeight: 0 }
  );
  // Sprint 51: Search states
  const [entitySearch, setEntitySearch] = useState('');
  const [relationshipSearch, setRelationshipSearch] = useState('');
  const [selectedRelTypes, setSelectedRelTypes] = useState<string[]>([
    'CO_OCCURS', 'RELATES_TO', 'MENTIONED_IN'
  ]);

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

  // Sprint 51: Handle relationship type toggle
  const handleRelTypeToggle = (relType: string) => {
    const newTypes = selectedRelTypes.includes(relType)
      ? selectedRelTypes.filter((t) => t !== relType)
      : [...selectedRelTypes, relType];
    setSelectedRelTypes(newTypes);

    // Update edge filters based on selected relationship types
    const updatedEdgeFilters: EdgeFilters = {
      ...localEdgeFilters,
      showCoOccurs: newTypes.includes('CO_OCCURS'),
      showRelatesTo: newTypes.includes('RELATES_TO'),
      showMentionedIn: newTypes.includes('MENTIONED_IN'),
    };
    handleEdgeFilterChange(updatedEdgeFilters);
  };

  // Filter options to only show available entity types
  const availableOptions = ENTITY_TYPE_OPTIONS.filter((option) =>
    entityTypes.includes(option.value)
  );

  // Sprint 51: Filter entity types by search
  const filteredEntityOptions = useMemo(() => {
    if (!entitySearch.trim()) return availableOptions;
    const search = entitySearch.toLowerCase();
    return availableOptions.filter(
      (opt) =>
        opt.label.toLowerCase().includes(search) ||
        opt.value.toLowerCase().includes(search)
    );
  }, [availableOptions, entitySearch]);

  // Sprint 51: Build relationship type options
  const relationshipTypeOptions = useMemo(() => {
    const options = [...DEFAULT_RELATIONSHIP_TYPES];
    // Add any extra types from the API
    if (availableRelationshipTypes) {
      availableRelationshipTypes.forEach((type) => {
        if (!options.some((opt) => opt.value === type)) {
          options.push({
            value: type,
            label: type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
            color: '#6b7280',
          });
        }
      });
    }
    return options;
  }, [availableRelationshipTypes]);

  // Sprint 51: Filter relationship types by search
  const filteredRelTypeOptions = useMemo(() => {
    if (!relationshipSearch.trim()) return relationshipTypeOptions;
    const search = relationshipSearch.toLowerCase();
    return relationshipTypeOptions.filter(
      (opt) =>
        opt.label.toLowerCase().includes(search) ||
        opt.value.toLowerCase().includes(search)
    );
  }, [relationshipTypeOptions, relationshipSearch]);

  return (
    <div className="space-y-6 p-4 bg-white rounded-lg border-2 border-gray-200">
      {/* Entity Types Filter */}
      <div>
        <label className="block text-sm font-semibold text-gray-900 mb-2">
          Entity Types
        </label>
        {/* Sprint 51: Entity search input */}
        <div className="mb-3">
          <div className="relative">
            <input
              type="text"
              value={entitySearch}
              onChange={(e) => setEntitySearch(e.target.value)}
              placeholder="Search entities..."
              className="w-full px-3 py-1.5 pl-8 text-sm border-2 border-gray-200 rounded-md
                         focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/20"
              data-testid="entity-search-input"
            />
            <svg
              className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            {entitySearch && (
              <button
                onClick={() => setEntitySearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {filteredEntityOptions.length > 0 ? (
            filteredEntityOptions.map((option) => (
              <EntityTypeCheckbox
                key={option.value}
                label={option.label}
                color={option.color}
                checked={localFilters.entityTypes.includes(option.value)}
                onChange={() => handleEntityTypeToggle(option.value)}
              />
            ))
          ) : (
            <p className="text-xs text-gray-500 py-2">No matching entity types</p>
          )}
        </div>
        {/* Quick select/deselect all */}
        <div className="flex gap-2 mt-2 pt-2 border-t border-gray-100">
          <button
            onClick={() => {
              const allTypes = availableOptions.map((opt) => opt.value);
              const updated = { ...localFilters, entityTypes: allTypes };
              setLocalFilters(updated);
              onChange(updated);
            }}
            className="text-xs text-blue-600 hover:text-blue-700"
          >
            Select all
          </button>
          <span className="text-gray-300">|</span>
          <button
            onClick={() => {
              const updated = { ...localFilters, entityTypes: [] };
              setLocalFilters(updated);
              onChange(updated);
            }}
            className="text-xs text-blue-600 hover:text-blue-700"
          >
            Deselect all
          </button>
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
      {/* Sprint 51: Enhanced with search and multiselect */}
      <div className="border-t border-gray-200 pt-4" data-testid="graph-edge-filter">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">Relationship Types</h4>

        {/* Sprint 51: Relationship search input */}
        <div className="mb-3">
          <div className="relative">
            <input
              type="text"
              value={relationshipSearch}
              onChange={(e) => setRelationshipSearch(e.target.value)}
              placeholder="Search relationships..."
              className="w-full px-3 py-1.5 pl-8 text-sm border-2 border-gray-200 rounded-md
                         focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/20"
              data-testid="relationship-search-input"
            />
            <svg
              className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            {relationshipSearch && (
              <button
                onClick={() => setRelationshipSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        <div className="space-y-2 max-h-40 overflow-y-auto" data-testid="edge-type-filter">
          {filteredRelTypeOptions.length > 0 ? (
            filteredRelTypeOptions.map((option) => (
              <label
                key={option.value}
                className="flex items-center space-x-2 cursor-pointer group"
                data-testid={`edge-filter-${option.value.toLowerCase()}`}
              >
                <input
                  type="checkbox"
                  checked={selectedRelTypes.includes(option.value)}
                  onChange={() => handleRelTypeToggle(option.value)}
                  className="w-4 h-4 text-primary border-2 border-gray-300 rounded
                             focus:ring-2 focus:ring-primary/20 focus:ring-offset-0 cursor-pointer"
                  aria-label={`Show ${option.value} relationships`}
                  data-testid={`edge-filter-${option.value.toLowerCase()}-checkbox`}
                />
                <div
                  className="w-4 h-0.5"
                  style={{ backgroundColor: option.color }}
                />
                <span className="text-sm text-gray-700 group-hover:text-gray-900 font-medium">
                  {option.label}
                </span>
              </label>
            ))
          ) : (
            <p className="text-xs text-gray-500 py-2">No matching relationship types</p>
          )}
        </div>

        {/* Quick select/deselect all relationships */}
        <div className="flex gap-2 mt-2 pt-2 border-t border-gray-100">
          <button
            onClick={() => {
              const allTypes = relationshipTypeOptions.map((opt) => opt.value);
              setSelectedRelTypes(allTypes);
              handleEdgeFilterChange({
                ...localEdgeFilters,
                showCoOccurs: true,
                showRelatesTo: true,
                showMentionedIn: true,
              });
            }}
            className="text-xs text-blue-600 hover:text-blue-700"
          >
            Select all
          </button>
          <span className="text-gray-300">|</span>
          <button
            onClick={() => {
              setSelectedRelTypes([]);
              handleEdgeFilterChange({
                ...localEdgeFilters,
                showCoOccurs: false,
                showRelatesTo: false,
                showMentionedIn: false,
              });
            }}
            className="text-xs text-blue-600 hover:text-blue-700"
          >
            Deselect all
          </button>
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
