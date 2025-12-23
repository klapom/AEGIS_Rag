/**
 * Research API Client
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 *
 * API client for research endpoints with SSE streaming support.
 */

import type {
  ResearchQueryRequest,
  ResearchQueryResponse,
  ResearchProgress,
} from '../types/research';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * SSE chunk types from research stream
 */
export type ResearchChunkType = 'progress' | 'result' | 'error' | 'done';

/**
 * Parsed SSE chunk from research stream
 */
export interface ResearchChunk {
  type: ResearchChunkType;
  data?: ResearchProgress | ResearchQueryResponse;
  error?: string;
}

/**
 * Stream research query using Server-Sent Events (SSE)
 *
 * @param request Research query request
 * @param signal Optional AbortSignal to cancel the stream
 * @yields ResearchChunk objects (progress, result, error)
 */
export async function* streamResearch(
  request: ResearchQueryRequest,
  signal?: AbortSignal
): AsyncGenerator<ResearchChunk> {
  const requestBody = {
    query: request.query,
    namespace: request.namespace || 'default',
    max_iterations: request.max_iterations || 3,
    stream: true,
  };

  const response = await fetch(`${API_BASE_URL}/api/v1/research/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Split by newlines to get individual SSE messages
      const lines = buffer.split('\n');

      // Keep the last incomplete line in buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        // SSE messages start with "data: "
        if (line.startsWith('data: ')) {
          const data = line.slice(6); // Remove "data: " prefix

          // Check for completion signal
          if (data === '[DONE]') {
            yield { type: 'done' };
            return;
          }

          try {
            const parsed = JSON.parse(data);

            // Check if it's an error
            if (parsed.error) {
              yield { type: 'error', error: parsed.error };
              continue;
            }

            // Check if it's a final result (has synthesis field)
            if ('synthesis' in parsed) {
              yield { type: 'result', data: parsed as ResearchQueryResponse };
              continue;
            }

            // Otherwise it's a progress update
            yield { type: 'progress', data: parsed as ResearchProgress };
          } catch (e) {
            console.error('Failed to parse research SSE chunk:', e, 'Data:', data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Execute non-streaming research query
 *
 * @param request Research query request
 * @returns Complete research response
 */
export async function research(request: ResearchQueryRequest): Promise<ResearchQueryResponse> {
  const requestBody = {
    query: request.query,
    namespace: request.namespace || 'default',
    max_iterations: request.max_iterations || 3,
    stream: false,
  };

  const response = await fetch(`${API_BASE_URL}/api/v1/research/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  return response.json();
}

/**
 * Check research endpoint health
 *
 * @returns Health status
 */
export async function checkResearchHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/research/health`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Research health check failed: HTTP ${response.status}`);
  }

  return response.json();
}
