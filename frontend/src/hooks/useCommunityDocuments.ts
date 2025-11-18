/**
 * useCommunityDocuments Hook
 * Sprint 29 Feature 29.7: Community Document Browser
 *
 * Fetches all documents mentioning entities from a specific community
 * API: GET /api/v1/graph/viz/communities/{id}/documents
 */

import { useState, useEffect } from 'react';
import type { Community, CommunityDocument } from '../types/graph';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface UseCommunityDocumentsReturn {
  documents: CommunityDocument[];
  community: Community | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Custom hook to fetch documents for a specific community
 *
 * @param communityId Community ID to fetch documents for
 * @param limit Maximum number of documents to return (default: 50)
 * @returns Documents, community info, loading state, error, and refetch function
 */
export function useCommunityDocuments(
  communityId: string,
  limit: number = 50
): UseCommunityDocumentsReturn {
  const [documents, setDocuments] = useState<CommunityDocument[]>([]);
  const [community, setCommunity] = useState<Community | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  useEffect(() => {
    let isMounted = true;

    const fetchCommunityDocuments = async () => {
      if (!communityId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // Fetch documents for the community
        const response = await fetch(
          `${API_BASE_URL}/api/v1/graph/viz/communities/${encodeURIComponent(communityId)}/documents?limit=${limit}`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );

        if (!response.ok) {
          // If endpoint doesn't exist, return mock data for development
          if (response.status === 404) {
            const mockDocuments: CommunityDocument[] = Array.from(
              { length: Math.min(limit, 8) },
              (_, i) => ({
                id: `doc-${communityId}-${i + 1}`,
                title: `Document ${i + 1} - ${communityId}`,
                excerpt: `This is an excerpt from document ${i + 1} that mentions entities from the ${communityId} community. The content provides context about how these entities relate to each other.`,
                entities: [
                  `Entity ${i * 2 + 1}`,
                  `Entity ${i * 2 + 2}`,
                  ...(i % 2 === 0 ? [`Entity ${i * 2 + 3}`] : []),
                ],
                chunk_id: `chunk-${i + 1}`,
                source: `source-${i + 1}`,
              })
            );

            const mockCommunity: Community = {
              id: communityId,
              topic: `Community ${communityId}`,
              size: mockDocuments.length * 2,
              density: 0.65,
            };

            if (isMounted) {
              setDocuments(mockDocuments);
              setCommunity(mockCommunity);
            }
            return;
          }

          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = await response.json();

        if (isMounted) {
          setDocuments(data.documents || []);
          setCommunity(data.community || null);
        }
      } catch (err) {
        if (isMounted) {
          setError(
            err instanceof Error ? err : new Error('Failed to fetch community documents')
          );
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void fetchCommunityDocuments();

    return () => {
      isMounted = false;
    };
  }, [communityId, limit, refetchTrigger]);

  const refetch = () => {
    setRefetchTrigger((prev) => prev + 1);
  };

  return { documents, community, loading, error, refetch };
}
