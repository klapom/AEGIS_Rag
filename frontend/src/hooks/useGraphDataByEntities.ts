/**
 * useGraphDataByEntities Hook
 * Sprint 29 Feature 29.2: Fetch subgraph by entity names
 */

import { useState, useEffect } from 'react';
import type { GraphData } from '../types/graph';
import { fetchQuerySubgraph } from '../api/graphViz';

interface UseGraphDataByEntitiesReturn {
  data: GraphData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Custom hook to fetch graph data for specific entities
 * Used for query result visualization (Feature 29.2)
 *
 * @param entityNames List of entity names to fetch
 * @returns Graph data, loading state, error, and refetch function
 */
export function useGraphDataByEntities(
  entityNames: string[]
): UseGraphDataByEntitiesReturn {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  useEffect(() => {
    let isMounted = true;

    const loadGraphData = async () => {
      // Don't fetch if no entities provided
      if (!entityNames || entityNames.length === 0) {
        setData(null);
        setLoading(false);
        setError(null);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const graphData = await fetchQuerySubgraph(entityNames);

        if (isMounted) {
          setData(graphData);
        }
      } catch (err) {
        if (isMounted) {
          setError(
            err instanceof Error ? err : new Error('Failed to fetch query subgraph')
          );
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
  }, [entityNames.join(','), refetchTrigger]); // Join entity names for dependency tracking

  const refetch = () => {
    setRefetchTrigger((prev) => prev + 1);
  };

  return { data, loading, error, refetch };
}
