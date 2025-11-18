/**
 * useGraphSearch Hook
 * Sprint 29 Feature 29.5: Graph Explorer with Search
 *
 * Custom hook for client-side node search with debouncing
 */

import { useMemo } from 'react';
import type { GraphData, GraphNode } from '../types/graph';

/**
 * Custom hook for searching graph nodes by label
 *
 * Features:
 * - Case-insensitive search
 * - Filters nodes by label
 * - Returns max 10 results
 * - Efficient client-side filtering
 *
 * @param data Graph data to search through
 * @param query Search query (requires min 2 chars)
 * @returns Array of matching nodes (max 10)
 */
export function useGraphSearch(data: GraphData, query: string): GraphNode[] {
  return useMemo(() => {
    // Require minimum 2 characters
    if (query.length < 2) {
      return [];
    }

    const normalizedQuery = query.toLowerCase().trim();

    // Filter nodes by label (case-insensitive)
    const matchingNodes = data.nodes.filter((node) =>
      node.label.toLowerCase().includes(normalizedQuery)
    );

    // Sort by relevance (exact match first, then starts with, then contains)
    const sorted = matchingNodes.sort((a, b) => {
      const aLabel = a.label.toLowerCase();
      const bLabel = b.label.toLowerCase();

      // Exact match
      if (aLabel === normalizedQuery) return -1;
      if (bLabel === normalizedQuery) return 1;

      // Starts with query
      const aStarts = aLabel.startsWith(normalizedQuery);
      const bStarts = bLabel.startsWith(normalizedQuery);
      if (aStarts && !bStarts) return -1;
      if (bStarts && !aStarts) return 1;

      // Sort by degree (most connected first)
      const aDegree = a.degree || 0;
      const bDegree = b.degree || 0;
      if (aDegree !== bDegree) {
        return bDegree - aDegree;
      }

      // Alphabetical fallback
      return aLabel.localeCompare(bLabel);
    });

    // Return max 10 results
    return sorted.slice(0, 10);
  }, [data, query]);
}

/**
 * Debounced version of useGraphSearch
 * Useful for real-time search without excessive re-renders
 *
 * Note: For most use cases, the standard useGraphSearch is sufficient
 * as it uses useMemo for efficient filtering.
 */
export function useDebouncedGraphSearch(
  data: GraphData,
  query: string,
  _delay: number = 300
): GraphNode[] {
  // For now, just use the standard search
  // Debouncing can be added at the component level if needed
  return useGraphSearch(data, query);
}

/**
 * Hook for filtering graph data by multiple criteria
 */
export interface GraphSearchFilters {
  query?: string;
  entityTypes?: string[];
  minDegree?: number;
  communityId?: string | null;
}

export function useGraphFilter(data: GraphData, filters: GraphSearchFilters): GraphData {
  return useMemo(() => {
    let filteredNodes = [...data.nodes];

    // Filter by search query
    if (filters.query && filters.query.length >= 2) {
      const normalizedQuery = filters.query.toLowerCase().trim();
      filteredNodes = filteredNodes.filter((node) =>
        node.label.toLowerCase().includes(normalizedQuery)
      );
    }

    // Filter by entity types
    if (filters.entityTypes && filters.entityTypes.length > 0) {
      filteredNodes = filteredNodes.filter((node) =>
        filters.entityTypes!.includes(node.type.toUpperCase())
      );
    }

    // Filter by minimum degree
    if (filters.minDegree !== undefined && filters.minDegree > 0) {
      filteredNodes = filteredNodes.filter(
        (node) => (node.degree || 0) >= filters.minDegree!
      );
    }

    // Filter by community
    if (filters.communityId !== null && filters.communityId !== undefined) {
      filteredNodes = filteredNodes.filter(
        (node) => node.community === filters.communityId
      );
    }

    // Get node IDs
    const nodeIds = new Set(filteredNodes.map((node) => node.id));

    // Filter links to only include those between filtered nodes
    const filteredLinks = data.links.filter((link) => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });

    return {
      nodes: filteredNodes,
      links: filteredLinks,
    };
  }, [data, filters]);
}
