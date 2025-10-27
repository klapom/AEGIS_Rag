/**
 * StreamingAnswer Component
 * Sprint 15 Feature 15.4: Display streaming answer with source cards
 *
 * Features:
 * - Token-by-token streaming display
 * - Source cards (horizontal scroll)
 * - Markdown rendering
 * - Loading states
 * - Error handling
 */

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { streamChat, ChatChunk } from '../../api/chat';
import type { Source } from '../../types/chat';
import { SourceCardsScroll } from './SourceCardsScroll';

interface StreamingAnswerProps {
  query: string;
  mode: string;
  sessionId?: string;
}

export function StreamingAnswer({ query, mode, sessionId }: StreamingAnswerProps) {
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<Source[]>([]);
  const [metadata, setMetadata] = useState<any>(null);
  const [isStreaming, setIsStreaming] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [intent, setIntent] = useState<string>('');

  useEffect(() => {
    const fetchStream = async () => {
      setAnswer('');
      setSources([]);
      setMetadata(null);
      setIntent('');
      setError(null);
      setIsStreaming(true);

      try {
        for await (const chunk of streamChat({
          query,
          intent: mode,
          session_id: sessionId,
          include_sources: true
        })) {
          handleChunk(chunk);
        }
      } catch (err) {
        console.error('Streaming error:', err);
        setError(err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten');
        setIsStreaming(false);
      }
    };

    fetchStream();
  }, [query, mode, sessionId]);

  const handleChunk = (chunk: ChatChunk) => {
    switch (chunk.type) {
      case 'metadata':
        setMetadata(chunk);
        break;

      case 'intent':
        setIntent(chunk.intent);
        break;

      case 'source':
        setSources((prev) => [...prev, chunk.source]);
        break;

      case 'token':
        setAnswer((prev) => prev + chunk.content);
        break;

      case 'done':
        setMetadata(chunk.metadata);
        setIsStreaming(false);
        break;

      case 'error':
        setError(chunk.error);
        setIsStreaming(false);
        break;
    }
  };

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <ErrorDisplay error={error} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-6">
      {/* Query Title */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-gray-900">{query}</h1>
        {intent && (
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-md font-medium">
              {intent}
            </span>
            {isStreaming && (
              <span className="flex items-center space-x-1">
                <LoadingDots />
                <span>Suche läuft...</span>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex space-x-6 border-b border-gray-200">
        <Tab active icon="🤖" label="Antwort" />
        <Tab icon="🌐" label={`Quellen ${sources.length > 0 ? `(${sources.length})` : ''}`} />
      </div>

      {/* Source Cards */}
      {sources.length > 0 && (
        <SourceCardsScroll sources={sources} />
      )}

      {/* Answer Content */}
      <div className="prose prose-lg max-w-none">
        {answer ? (
          <>
            <ReactMarkdown>{answer}</ReactMarkdown>
            {isStreaming && <span className="animate-pulse text-primary">▊</span>}
          </>
        ) : (
          <div className="space-y-3">
            <SkeletonLine />
            <SkeletonLine />
            <SkeletonLine width="75%" />
          </div>
        )}
      </div>

      {/* Metadata */}
      {metadata && !isStreaming && (
        <div className="flex items-center space-x-6 text-sm text-gray-500 pt-4 border-t border-gray-200">
          {metadata.latency_seconds && (
            <span className="flex items-center space-x-1">
              <span>⚡</span>
              <span>{metadata.latency_seconds.toFixed(2)}s</span>
            </span>
          )}
          {metadata.agent_path && Array.isArray(metadata.agent_path) && (
            <span className="flex items-center space-x-1">
              <span>📊</span>
              <span>{metadata.agent_path.join(' → ')}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}

interface TabProps {
  active?: boolean;
  icon: string;
  label: string;
}

function Tab({ active = false, icon, label }: TabProps) {
  return (
    <button
      className={`
        flex items-center space-x-2 pb-3 px-1
        border-b-2 transition-colors
        ${active
          ? 'border-primary text-primary font-medium'
          : 'border-transparent text-gray-500 hover:text-gray-700'
        }
      `}
    >
      <span>{icon}</span>
      <span>{label}</span>
    </button>
  );
}

function LoadingDots() {
  return (
    <div className="flex space-x-1">
      <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
      <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
      <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  );
}

function SkeletonLine({ width = '100%' }: { width?: string }) {
  return (
    <div
      className="h-4 bg-gray-200 rounded animate-pulse"
      style={{ width }}
    />
  );
}

function ErrorDisplay({ error }: { error: string }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-6 space-y-3">
      <div className="flex items-center space-x-2 text-red-700">
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <h3 className="font-semibold">Fehler beim Laden der Antwort</h3>
      </div>
      <p className="text-red-600">{error}</p>
      <button
        onClick={() => window.location.reload()}
        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
      >
        Erneut versuchen
      </button>
    </div>
  );
}
