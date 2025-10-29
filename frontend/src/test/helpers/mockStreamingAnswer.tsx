/**
 * Mock StreamingAnswer Component
 * Sprint 18 TD-38 Phase 2: Mock helpers for StreamingAnswer component testing
 *
 * Problem:
 * - SearchResultsPage tests fail because StreamingAnswer requires real SSE streams
 * - Query text not displayed because streaming fails in test environment
 *
 * Solution:
 * - Provide simplified mock component that renders query immediately
 * - No SSE/fetch required - just displays props for testing
 *
 * Usage:
 * ```typescript
 * vi.mock('../../components/chat/StreamingAnswer', () => ({
 *   StreamingAnswer: MockStreamingAnswer
 * }));
 * ```
 */

import type { SearchMode } from '../../components/search';

export interface MockStreamingAnswerProps {
  query: string;
  mode: SearchMode;
  sessionId?: string;
  onSessionIdReceived?: (sessionId: string) => void;
}

/**
 * Simplified mock of StreamingAnswer for page-level tests.
 *
 * Displays query as h1 (matching real component) without SSE complexity.
 */
export function MockStreamingAnswer({
  query,
  mode,
  sessionId,
}: MockStreamingAnswerProps) {
  return (
    <div data-testid="streaming-answer" className="max-w-4xl mx-auto px-6 py-8">
      {/* Query heading - matches real component */}
      <h1 className="text-3xl font-bold text-gray-900 mb-6">{query}</h1>

      {/* Mode indicator for test validation */}
      <div data-testid="streaming-mode" className="text-sm text-gray-600 mb-4">
        Mode: {mode}
      </div>

      {/* Session ID indicator (if present) */}
      {sessionId && (
        <div data-testid="streaming-session" className="text-xs text-gray-500">
          Session: {sessionId}
        </div>
      )}

      {/* Mock answer content */}
      <div data-testid="streaming-content" className="prose max-w-none">
        <p>Mock answer for: {query}</p>
      </div>
    </div>
  );
}

/**
 * Create a mock StreamingAnswer component with custom behavior.
 *
 * Useful for testing edge cases (loading states, errors, etc.)
 */
export function createMockStreamingAnswer(overrides?: {
  loading?: boolean;
  error?: string;
  customRender?: (props: MockStreamingAnswerProps) => JSX.Element;
}) {
  return function CustomMockStreamingAnswer(props: MockStreamingAnswerProps) {
    if (overrides?.customRender) {
      return overrides.customRender(props);
    }

    if (overrides?.loading) {
      return (
        <div data-testid="streaming-answer" className="text-center py-8">
          <div className="text-gray-600">Suche läuft...</div>
        </div>
      );
    }

    if (overrides?.error) {
      return (
        <div data-testid="streaming-answer" className="text-center py-8">
          <div className="text-red-600">Fehler: {overrides.error}</div>
        </div>
      );
    }

    return <MockStreamingAnswer {...props} />;
  };
}

/**
 * Mock implementation that simulates the full component lifecycle.
 *
 * Use for integration tests that need to verify session ID callbacks, etc.
 */
export function MockStreamingAnswerWithCallbacks({
  query,
  mode,
  sessionId,
  onSessionIdReceived,
}: MockStreamingAnswerProps) {
  // Simulate session ID callback on mount
  React.useEffect(() => {
    if (!sessionId && onSessionIdReceived) {
      // Simulate receiving session ID from metadata
      onSessionIdReceived('mock-session-123');
    }
  }, [sessionId, onSessionIdReceived]);

  return <MockStreamingAnswer query={query} mode={mode} sessionId={sessionId} />;
}

// React import for useEffect
import React from 'react';
