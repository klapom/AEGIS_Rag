import { useState, useCallback, useEffect } from 'react';

// Use same API base URL as other API calls (supports VITE_API_BASE_URL env var)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Document with sections
 */
export interface Document {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * Document section
 */
export interface DocumentSection {
  id: string;
  heading: string;
  level: number;
  entity_count?: number;
  chunk_count?: number;
}

/**
 * Hook to fetch all documents
 *
 * Returns a list of documents available for graph analysis.
 * Uses local state management (no react-query for simplicity).
 */
export function useDocuments() {
  const [data, setData] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/graph/documents`);

      if (!response.ok) {
        throw new Error(`Failed to fetch documents: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result.documents || []);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      setData([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Auto-fetch on mount
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchDocuments,
  };
}

/**
 * Hook to fetch sections for a specific document
 *
 * Automatically fetches when documentId changes.
 * Returns empty array if documentId is empty/null.
 */
export function useDocumentSections(documentId: string) {
  const [data, setData] = useState<DocumentSection[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchSections = useCallback(async (docId: string) => {
    if (!docId) {
      setData([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/graph/documents/${docId}/sections`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch sections: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result.sections || []);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      setData([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Auto-fetch when documentId changes
  useEffect(() => {
    fetchSections(documentId);
  }, [documentId, fetchSections]);

  return {
    data,
    isLoading,
    error,
    refetch: () => fetchSections(documentId),
  };
}
