/**
 * useEntityChangelog Hook
 * Sprint 39 Feature 39.6: Entity Changelog Panel
 */

import { useState, useEffect, useCallback } from 'react';
import type { ChangelogResponse, ChangeEvent } from '../types/graph';
import { fetchEntityChangelog } from '../api/graphViz';

interface UseEntityChangelogReturn {
  data: ChangeEvent[] | null;
  loading: boolean;
  error: Error | null;
  hasMore: boolean;
  fetchMore: () => void;
  refetch: () => void;
}

/**
 * Custom hook to fetch and manage entity changelog with pagination
 *
 * @param entityId Entity ID to fetch changelog for
 * @param initialLimit Initial number of changes to load (default: 50)
 * @returns Changelog data, loading state, error, and pagination functions
 */
export function useEntityChangelog(
  entityId: string | null,
  initialLimit: number = 50
): UseEntityChangelogReturn {
  const [data, setData] = useState<ChangeEvent[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasMore, setHasMore] = useState<boolean>(true);
  const [currentLimit, setCurrentLimit] = useState<number>(initialLimit);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  useEffect(() => {
    // Skip query if no entityId
    if (!entityId) {
      setData(null);
      setLoading(false);
      return;
    }

    let isMounted = true;

    const loadChangelog = async () => {
      setLoading(true);
      setError(null);

      try {
        const response: ChangelogResponse = await fetchEntityChangelog(entityId, currentLimit);

        if (isMounted) {
          setData(response.changes);
          // Check if there are more changes available
          setHasMore(response.changes.length >= currentLimit && response.changes.length < response.total);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Failed to fetch changelog'));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadChangelog();

    return () => {
      isMounted = false;
    };
  }, [entityId, currentLimit, refetchTrigger]);

  const fetchMore = useCallback(() => {
    if (!loading && hasMore) {
      setCurrentLimit((prev) => prev + 50);
    }
  }, [loading, hasMore]);

  const refetch = useCallback(() => {
    setRefetchTrigger((prev) => prev + 1);
  }, []);

  return { data, loading, error, hasMore, fetchMore, refetch };
}
