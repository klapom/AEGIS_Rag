/**
 * useGraphCommunities Hook
 * Sprint 71 Feature 71.16: Graph Communities Integration
 *
 * Provides hooks for section-level community detection and comparison
 */

import { useState, useCallback } from 'react';
import type {
  SectionCommunityVisualizationResponse,
  CommunityComparisonOverview,
  SectionCommunitiesRequest,
  CommunityComparisonRequest,
} from '../types/graph';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Hook to fetch section communities with visualization data
 *
 * @returns Object with data, loading state, error, and fetch function
 */
export function useSectionCommunities() {
  const [data, setData] = useState<SectionCommunityVisualizationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchSectionCommunities = useCallback(
    async (request: SectionCommunitiesRequest): Promise<SectionCommunityVisualizationResponse> => {
      setIsLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        if (request.algorithm) params.append('algorithm', request.algorithm);
        if (request.resolution !== undefined) params.append('resolution', String(request.resolution));
        if (request.include_layout !== undefined) params.append('include_layout', String(request.include_layout));
        if (request.layout_algorithm) params.append('layout_algorithm', request.layout_algorithm);

        const url = `${API_BASE_URL}/api/v1/graph/communities/${request.document_id}/sections/${request.section_id}${
          params.toString() ? `?${params.toString()}` : ''
        }`;

        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result: SectionCommunityVisualizationResponse = await response.json();
        setData(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to fetch section communities');
        setError(error);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return {
    data,
    isLoading,
    error,
    fetchSectionCommunities,
  };
}

/**
 * Hook to compare communities across sections
 *
 * @returns Object with data, loading state, error, and compare function
 */
export function useCompareCommunities() {
  const [data, setData] = useState<CommunityComparisonOverview | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const compareCommunities = useCallback(
    async (request: CommunityComparisonRequest): Promise<CommunityComparisonOverview> => {
      setIsLoading(true);
      setError(null);

      try {
        const url = `${API_BASE_URL}/api/v1/graph/communities/compare`;

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result: CommunityComparisonOverview = await response.json();
        setData(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to compare communities');
        setError(error);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return {
    data,
    isLoading,
    error,
    compareCommunities,
  };
}
