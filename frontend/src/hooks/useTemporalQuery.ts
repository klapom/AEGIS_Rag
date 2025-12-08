/**
 * useTemporalQuery Hook
 * Sprint 39 Feature 39.5: Time Travel Tab
 */

import { useState, useEffect } from 'react';
import type { TemporalQueryResponse } from '../types/graph';
import { fetchPointInTime } from '../api/graphViz';

interface UseTemporalQueryReturn {
  data: TemporalQueryResponse | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Custom hook to fetch graph state at a specific point in time
 *
 * @param timestamp Date to query (or null to skip query)
 * @param entityFilter Optional entity name filter
 * @param limit Maximum number of entities (default: 100)
 * @returns Temporal query data, loading state, error, and refetch function
 */
export function useTemporalQuery(
  timestamp: Date | null,
  entityFilter?: string,
  limit: number = 100
): UseTemporalQueryReturn {
  const [data, setData] = useState<TemporalQueryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  useEffect(() => {
    // Skip query if no timestamp
    if (!timestamp) {
      setData(null);
      setLoading(false);
      return;
    }

    let isMounted = true;

    const loadTemporalData = async () => {
      setLoading(true);
      setError(null);

      try {
        const temporalData = await fetchPointInTime(
          timestamp.toISOString(),
          entityFilter,
          limit
        );

        if (isMounted) {
          setData(temporalData);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Failed to fetch temporal data'));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadTemporalData();

    return () => {
      isMounted = false;
    };
  }, [timestamp, entityFilter, limit, refetchTrigger]);

  const refetch = () => {
    setRefetchTrigger((prev) => prev + 1);
  };

  return { data, loading, error, refetch };
}
