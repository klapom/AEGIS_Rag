/**
 * useCommunities Hook
 * Sprint 29 Feature 29.3: Admin Graph Analytics View
 *
 * Fetches top N communities from the backend API
 */

import { useState, useEffect } from 'react';
import { fetchTopCommunities } from '../api/graphViz';
import type { Community } from '../types/graph';

interface UseCommunitiesReturn {
  communities: Community[];
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Custom hook to fetch and manage community data
 *
 * @param limit Maximum number of communities to fetch (default: 10)
 * @returns Communities, loading state, error, and refetch function
 */
export function useCommunities(limit: number = 10): UseCommunitiesReturn {
  const [communities, setCommunities] = useState<Community[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  useEffect(() => {
    let isMounted = true;

    const loadCommunities = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await fetchTopCommunities(limit);

        if (isMounted) {
          setCommunities(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Failed to fetch communities'));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadCommunities();

    return () => {
      isMounted = false;
    };
  }, [limit, refetchTrigger]);

  const refetch = () => {
    setRefetchTrigger((prev) => prev + 1);
  };

  return { communities, loading, error, refetch };
}
