/**
 * Admin API Client
 * Sprint 17 Feature 17.1: Admin UI for Directory Indexing
 */

import type { ReindexProgressChunk, ReindexRequest, SystemStats } from '../types/admin';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Stream re-indexing progress using Server-Sent Events (SSE)
 *
 * @param request Re-index request with directory, dry_run, and confirm flags
 * @param signal Optional AbortSignal to cancel the stream
 * @yields ReindexProgressChunk objects with progress updates
 */
export async function* streamReindex(
  request: ReindexRequest,
  signal?: AbortSignal
): AsyncGenerator<ReindexProgressChunk> {
  const params = new URLSearchParams();
  params.append('input_dir', request.input_dir);
  if (request.dry_run !== undefined) {
    params.append('dry_run', String(request.dry_run));
  }
  if (request.confirm !== undefined) {
    params.append('confirm', String(request.confirm));
  }

  const url = `${API_BASE_URL}/api/v1/admin/reindex?${params.toString()}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Accept': 'text/event-stream',
    },
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

          try {
            const chunk: ReindexProgressChunk = JSON.parse(data);
            yield chunk;
          } catch (e) {
            console.error('Failed to parse SSE chunk:', e, 'Data:', data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Get comprehensive system statistics for admin dashboard
 *
 * @returns SystemStats with Qdrant, Neo4j, BM25, and Redis statistics
 */
export async function getSystemStats(): Promise<SystemStats> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/stats`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}
