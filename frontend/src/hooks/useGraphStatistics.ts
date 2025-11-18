/**
 * useGraphStatistics Hook
 * Sprint 29 Feature 29.4: Knowledge Graph Dashboard
 *
 * Fetches comprehensive graph statistics from the backend API
 */

import { useState, useEffect } from 'react';
import type { GraphStatistics } from '../types/graph';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface UseGraphStatisticsReturn {
  stats: GraphStatistics | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Custom hook to fetch and manage graph statistics
 *
 * @param autoRefreshInterval Optional interval in milliseconds for auto-refresh (default: disabled)
 * @returns Graph statistics, loading state, error, and refetch function
 */
export function useGraphStatistics(
  autoRefreshInterval?: number
): UseGraphStatisticsReturn {
  const [stats, setStats] = useState<GraphStatistics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  useEffect(() => {
    let isMounted = true;
    let intervalId: number | undefined;

    const fetchStatistics = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/graph/viz/statistics`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data: GraphStatistics = await response.json();

        if (isMounted) {
          setStats(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Failed to fetch graph statistics'));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    // Initial fetch
    void fetchStatistics();

    // Setup auto-refresh if interval is provided
    if (autoRefreshInterval && autoRefreshInterval > 0) {
      intervalId = window.setInterval(() => {
        void fetchStatistics();
      }, autoRefreshInterval);
    }

    return () => {
      isMounted = false;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [refetchTrigger, autoRefreshInterval]);

  const refetch = () => {
    setRefetchTrigger((prev) => prev + 1);
  };

  return { stats, loading, error, refetch };
}
