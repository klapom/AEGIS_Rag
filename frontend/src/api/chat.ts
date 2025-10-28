/**
 * Chat API Client
 * Sprint 15 Feature 15.1: SSE Streaming Client (ADR-020)
 */

import type { ChatRequest, ChatChunk, ChatResponse, SessionListResponse, ConversationHistoryResponse } from '../types/chat';

// Re-export types for easier imports
export type { ChatChunk, ChatRequest, ChatResponse, SessionListResponse, ConversationHistoryResponse };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Stream chat response using Server-Sent Events (SSE)
 *
 * @param request Chat request with query and optional session_id
 * @yields ChatChunk objects (metadata, tokens, sources, errors)
 */
export async function* streamChat(request: ChatRequest): AsyncGenerator<ChatChunk> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
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
          const data = line.slice(6);  // Remove "data: " prefix

          // Check for completion signal
          if (data === '[DONE]') {
            return;
          }

          try {
            const chunk: ChatChunk = JSON.parse(data);
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
 * Send non-streaming chat request
 *
 * @param request Chat request
 * @returns Chat response with complete answer
 */
export async function chat(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  return response.json();
}

/**
 * List all conversation sessions
 *
 * @returns List of sessions with metadata
 */
export async function listSessions(): Promise<SessionListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  return response.json();
}

/**
 * Get conversation history for a session
 *
 * @param sessionId Session ID
 * @returns Conversation history
 */
export async function getConversationHistory(sessionId: string): Promise<ConversationHistoryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/history/${sessionId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  return response.json();
}

/**
 * Delete conversation history for a session
 *
 * @param sessionId Session ID to delete
 */
export async function deleteConversationHistory(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/history/${sessionId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }
}

/**
 * Delete a session (alias for deleteConversationHistory)
 * Sprint 15 Feature 15.5
 */
export async function deleteSession(sessionId: string): Promise<void> {
  return deleteConversationHistory(sessionId);
}
