/**
 * usePipelineProgress Hook
 * Sprint 37 Feature 37.4: Visual Pipeline Progress Component
 *
 * Custom hook to manage SSE connection for real-time pipeline progress updates
 */

import { useState, useEffect, useCallback } from 'react';
import type { PipelineProgressData } from '../types/admin';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface UsePipelineProgressReturn {
  progress: PipelineProgressData | null;
  isConnected: boolean;
  error: string | null;
  reconnect: () => void;
}

/**
 * Custom hook to subscribe to pipeline progress SSE stream
 *
 * @param jobId Unique job identifier for the indexing operation
 * @returns Progress data, connection status, error state, and reconnect function
 */
export function usePipelineProgress(jobId: string | null): UsePipelineProgressReturn {
  const [progress, setProgress] = useState<PipelineProgressData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectTrigger, setReconnectTrigger] = useState(0);

  useEffect(() => {
    if (!jobId) {
      setProgress(null);
      setIsConnected(false);
      setError(null);
      return;
    }

    let eventSource: EventSource | null = null;
    let isCleanedUp = false;

    const connectToSSE = () => {
      try {
        const url = `${API_BASE_URL}/api/v1/admin/indexing/progress/${jobId}`;
        eventSource = new EventSource(url);

        eventSource.onopen = () => {
          if (!isCleanedUp) {
            setIsConnected(true);
            setError(null);
          }
        };

        eventSource.onmessage = (event) => {
          if (isCleanedUp) return;

          try {
            const data = JSON.parse(event.data);

            // Check if this is a pipeline progress event
            if (data.type === 'pipeline_progress' && data.data) {
              setProgress(data.data);
            }
          } catch (err) {
            console.error('Failed to parse SSE event:', err);
            setError('Failed to parse progress data');
          }
        };

        eventSource.onerror = (err) => {
          if (isCleanedUp) return;

          console.error('SSE connection error:', err);
          setIsConnected(false);
          setError('Connection to progress stream lost');

          // Close the connection on error
          eventSource?.close();
        };
      } catch (err) {
        if (!isCleanedUp) {
          setError(err instanceof Error ? err.message : 'Failed to connect to progress stream');
          setIsConnected(false);
        }
      }
    };

    // Initial connection
    connectToSSE();

    // Cleanup function
    return () => {
      isCleanedUp = true;
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      setIsConnected(false);
    };
  }, [jobId, reconnectTrigger]);

  const reconnect = useCallback(() => {
    setReconnectTrigger((prev) => prev + 1);
  }, []);

  return {
    progress,
    isConnected,
    error,
    reconnect,
  };
}
