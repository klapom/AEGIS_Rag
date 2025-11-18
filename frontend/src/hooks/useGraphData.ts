/**
 * useGraphData Hook
 * Sprint 29 Feature 29.1: Graph Data Fetching Hook
 */

import { useState, useEffect } from 'react';
import type { GraphData, GraphFilters } from '../types/graph';
import { fetchGraphData } from '../api/graphViz';

interface UseGraphDataReturn {
  data: GraphData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Custom hook to fetch and manage graph data
 *
 * @param filters Graph filters (maxNodes, entityTypes, highlightCommunities)
 * @returns Graph data, loading state, error, and refetch function
 */
export function useGraphData(filters: GraphFilters = {}): UseGraphDataReturn {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  useEffect(() => {
    let isMounted = true;

    const loadGraphData = async () => {
      setLoading(true);
      setError(null);

      try {
        const graphData = await fetchGraphData({
          format: 'json',
          max_nodes: filters.maxNodes || 100,
          entity_types: filters.entityTypes,
          include_communities: true,
        });

        if (isMounted) {
          setData(graphData);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Failed to fetch graph data'));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadGraphData();

    return () => {
      isMounted = false;
    };
  }, [filters.maxNodes, filters.entityTypes, refetchTrigger]);

  const refetch = () => {
    setRefetchTrigger((prev) => prev + 1);
  };

  return { data, loading, error, refetch };
}
