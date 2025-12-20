/**
 * Chat API Client
 * Sprint 15 Feature 15.1: SSE Streaming Client (ADR-020)
 */

import type { ChatRequest, ChatChunk, ChatResponse, SessionListResponse, ConversationHistoryResponse, SessionInfo } from '../types/chat';

// Re-export types for easier imports
export type { ChatChunk, ChatRequest, ChatResponse, SessionListResponse, ConversationHistoryResponse, SessionInfo };

/**
 * SessionSummary for SessionSidebar display
 * Sprint 35 Feature 35.5
 */
export type SessionSummary = {
  session_id: string;
  title: string | null;
  preview?: string;
  updated_at: string;
  message_count: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Stream chat response using Server-Sent Events (SSE)
 *
 * Sprint 17 Feature 17.5: Added AbortController support to prevent duplicate streams
 *
 * @param request Chat request with query and optional session_id
 * @param signal Optional AbortSignal to cancel the stream
 * @yields ChatChunk objects (metadata, tokens, sources, errors)
 */
export async function* streamChat(request: ChatRequest, signal?: AbortSignal): AsyncGenerator<ChatChunk> {
  // Sprint 53-58 Refactoring Fix: Ensure namespace is always sent
  const requestWithNamespace = {
    ...request,
    namespaces: request.namespaces || ['default'],
  };

  const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestWithNamespace),
    signal,  // Pass AbortSignal to fetch
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
            // Yield complete event to signal end of stream
            yield { type: 'complete', data: {} } as ChatChunk;
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
  // Sprint 53-58 Refactoring Fix: Ensure namespace is always sent
  const requestWithNamespace = {
    ...request,
    namespaces: request.namespaces || ['default'],
  };

  const response = await fetch(`${API_BASE_URL}/api/v1/chat/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestWithNamespace),
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

// Sprint 17 Feature 17.3: Auto-Generated Conversation Titles
// Sprint 35 Feature 35.4: Session Info Retrieval
// Note: SessionInfo is imported from ../types/chat and re-exported above

export interface TitleResponse {
  session_id: string;
  title: string;
  generated_at: string;
}

/**
 * Get session information including title
 * Sprint 35 Feature 35.4
 *
 * @param sessionId Session ID to get info for
 * @returns SessionInfo with title, message count, and timestamps
 */
export async function getSessionInfo(sessionId: string): Promise<SessionInfo> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}`, {
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
 * Generate conversation title automatically using LLM
 * Sprint 17 Feature 17.3
 *
 * @param sessionId Session ID to generate title for
 * @returns TitleResponse with generated title
 */
export async function generateConversationTitle(sessionId: string): Promise<TitleResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}/generate-title`, {
    method: 'POST',
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
 * Update conversation title manually
 * Sprint 17 Feature 17.3
 *
 * @param sessionId Session ID to update
 * @param title New title
 * @returns TitleResponse with updated title
 */
export async function updateConversationTitle(sessionId: string, title: string): Promise<TitleResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  return response.json();
}

// Sprint 28 Feature 28.1: Follow-up Questions

export interface FollowUpQuestionsResponse {
  followup_questions: string[];
}

/**
 * Get follow-up questions for a session
 * Sprint 28 Feature 28.1
 *
 * @param sessionId Session ID to get follow-up questions for
 * @returns Array of follow-up questions
 */
export async function getFollowUpQuestions(sessionId: string): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}/followup-questions`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  const data: FollowUpQuestionsResponse = await response.json();
  return data.followup_questions || [];
}

/**
 * Get full conversation for a session
 * Sprint 35 Feature 35.5: Session History Sidebar
 *
 * @param sessionId Session ID to get conversation for
 * @returns Conversation history with messages
 */
export async function getConversation(sessionId: string): Promise<ConversationHistoryResponse> {
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

// Sprint 38 Feature 38.2: Conversation Search

export interface ConversationSearchRequest {
  query: string;
  limit?: number;
  min_score?: number;
}

export interface ConversationSearchResult {
  session_id: string;
  title: string;
  snippet: string;
  archived_at: string;
  score: number;
}

export interface ConversationSearchResponse {
  results: ConversationSearchResult[];
  total: number;
}

/**
 * Search conversations by query
 * Sprint 38 Feature 38.2
 *
 * @param query Search query
 * @param limit Maximum number of results (default: 10)
 * @param minScore Minimum relevance score (default: 0.5)
 * @returns Search results with relevance scores
 */
export async function searchConversations(
  query: string,
  limit: number = 10,
  minScore: number = 0.5
): Promise<ConversationSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query, limit, min_score: minScore }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  return response.json();
}

export interface ArchiveConversationResponse {
  success: boolean;
  archived_at: string;
}

/**
 * Archive a conversation
 * Sprint 38 Feature 38.2
 *
 * @param sessionId Session ID to archive
 * @returns Archive response with timestamp
 */
export async function archiveConversation(sessionId: string): Promise<ArchiveConversationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}/archive`, {
    method: 'POST',
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

// Sprint 38 Feature 38.3: Share Conversation Links

export interface ShareLinkRequest {
  expiry_hours: number;
}

export interface ShareLinkResponse {
  share_url: string;
  share_token: string;
  expires_at: string;
  session_id: string;
}

export interface SharedConversationResponse {
  session_id: string;
  title: string | null;
  messages: Array<{
    role: string;
    content: string;
    timestamp: string;
    intent?: string;
    source_count?: number;
    sources?: any[];
  }>;
  message_count: number;
  created_at: string | null;
  shared_at: string;
  expires_at: string;
}

/**
 * Create a public share link for a conversation
 * Sprint 38 Feature 38.3
 *
 * @param sessionId Session ID to share
 * @param expiryHours Hours until link expires (1-168)
 * @returns Share link response with URL and token
 */
export async function createShareLink(
  sessionId: string,
  expiryHours: number = 24
): Promise<ShareLinkResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}/share`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ expiry_hours: expiryHours }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }

  return response.json();
}

/**
 * Get shared conversation by token (public, no auth required)
 * Sprint 38 Feature 38.3
 *
 * @param shareToken Share token from URL
 * @returns Shared conversation data
 */
export async function getSharedConversation(shareToken: string): Promise<SharedConversationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/share/${shareToken}`, {
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
