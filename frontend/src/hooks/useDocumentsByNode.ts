/**
 * useDocumentsByNode Hook
 * Sprint 29 Feature 29.6: Embedding-based Document Search from Graph
 *
 * Fetches related documents for a graph node using vector similarity search.
 */

import { useState, useEffect } from 'react';
import type { RelatedDocument } from '../types/graph';
import { fetchDocumentsByNode } from '../api/graphViz';

interface UseDocumentsByNodeReturn {
  documents: RelatedDocument[];
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Custom hook to fetch related documents for a graph entity
 *
 * @param entityName Entity name to search for (null if no node selected)
 * @param topK Number of documents to fetch (default: 10)
 * @returns Documents, loading state, error, and refetch function
 */
export function useDocumentsByNode(
  entityName: string | null,
  topK: number = 10
): UseDocumentsByNodeReturn {
  const [documents, setDocuments] = useState<RelatedDocument[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  useEffect(() => {
    // Skip fetch if no entity name provided
    if (!entityName) {
      setDocuments([]);
      setLoading(false);
      setError(null);
      return;
    }

    let isMounted = true;

    const loadDocuments = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetchDocumentsByNode(entityName, topK);

        if (isMounted) {
          setDocuments(response.documents);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Failed to fetch documents'));
          setDocuments([]);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadDocuments();

    return () => {
      isMounted = false;
    };
  }, [entityName, topK, refetchTrigger]);

  const refetch = () => {
    setRefetchTrigger((prev) => prev + 1);
  };

  return { documents, loading, error, refetch };
}
