/**
 * useVersionDiff Hook
 * Sprint 39 Feature 39.7: Version Comparison View
 */

import { useState, useEffect } from 'react';
import type { VersionDiff, EntityVersion } from '../types/graph';
import { fetchVersionDiff, fetchEntityVersions } from '../api/graphViz';

interface UseVersionDiffReturn {
  data: VersionDiff | null;
  versions: EntityVersion[] | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Custom hook to fetch version diff and available versions for an entity
 *
 * @param entityId Entity ID to compare versions for
 * @param versionA First version number (or null to skip)
 * @param versionB Second version number (or null to skip)
 * @returns Version diff data, available versions, loading state, error, and refetch function
 */
export function useVersionDiff(
  entityId: string | null,
  versionA: number | null,
  versionB: number | null
): UseVersionDiffReturn {
  const [data, setData] = useState<VersionDiff | null>(null);
  const [versions, setVersions] = useState<EntityVersion[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  // Fetch available versions
  useEffect(() => {
    if (!entityId) {
      setVersions(null);
      return;
    }

    let isMounted = true;

    const loadVersions = async () => {
      try {
        const entityVersions = await fetchEntityVersions(entityId);
        if (isMounted) {
          setVersions(entityVersions);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Failed to fetch versions'));
        }
      }
    };

    void loadVersions();

    return () => {
      isMounted = false;
    };
  }, [entityId, refetchTrigger]);

  // Fetch version diff
  useEffect(() => {
    // Skip query if missing parameters
    if (!entityId || versionA === null || versionB === null) {
      setData(null);
      setLoading(false);
      return;
    }

    let isMounted = true;

    const loadDiff = async () => {
      setLoading(true);
      setError(null);

      try {
        const diff = await fetchVersionDiff(entityId, versionA, versionB);

        if (isMounted) {
          setData(diff);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Failed to fetch version diff'));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadDiff();

    return () => {
      isMounted = false;
    };
  }, [entityId, versionA, versionB, refetchTrigger]);

  const refetch = () => {
    setRefetchTrigger((prev) => prev + 1);
  };

  return { data, versions, loading, error, refetch };
}
