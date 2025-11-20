/**
 * StreamingAnswer Component
 * Sprint 15 Feature 15.4: Display streaming answer with source cards
 * Sprint 28 Feature 28.2: Inline citations with hover previews
 *
 * Features:
 * - Token-by-token streaming display
 * - Source cards (horizontal scroll)
 * - Markdown rendering with inline citations
 * - Loading states
 * - Error handling
 */

import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Network } from 'lucide-react';  // Sprint 29 Feature 29.2
import { streamChat, generateConversationTitle, type ChatChunk } from '../../api/chat';
import type { Source } from '../../types/chat';
import { SourceCardsScroll, type SourceCardsScrollRef } from './SourceCardsScroll';
import { CopyButton } from './CopyButton';  // Sprint 27 Feature 27.6
import { createCitationTextRenderer } from '../../utils/citations';  // Sprint 28 Feature 28.2
import { FollowUpQuestions } from './FollowUpQuestions';  // Sprint 28 Feature 28.1
import { GraphModal } from '../graph/GraphModal';  // Sprint 29 Feature 29.2
import { extractEntitiesFromSources } from '../../utils/entityExtractor';  // Sprint 29 Feature 29.2

interface StreamingAnswerProps {
  query: string;
  mode: string;
  sessionId?: string;
  onSessionIdReceived?: (sessionId: string) => void;
  onTitleGenerated?: (title: string) => void;  // Sprint 17 Feature 17.3
  onFollowUpQuestion?: (question: string) => void;  // Sprint 28 Feature 28.1
}

export function StreamingAnswer({ query, mode, sessionId, onSessionIdReceived, onTitleGenerated, onFollowUpQuestion }: StreamingAnswerProps) {
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<Source[]>([]);
  const [metadata, setMetadata] = useState<any>(null);
  const [isStreaming, setIsStreaming] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [intent, setIntent] = useState<string>('');
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>(sessionId);
  const [showGraphModal, setShowGraphModal] = useState(false);  // Sprint 29 Feature 29.2
  const [citationMap, setCitationMap] = useState<Record<number, any> | null>(null);  // Sprint 27 Feature 27.10
  const sourceCardsRef = useRef<SourceCardsScrollRef>(null);  // Sprint 28 Feature 28.2

  useEffect(() => {
    // Sprint 17 Feature 17.5: Fix duplicate streaming caused by React StrictMode
    // AbortController cancels SSE connection on cleanup (e.g., during StrictMode unmount)
    const abortController = new AbortController();
    let isAborted = false;

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
        }, abortController.signal)) {  // Pass signal to streamChat
          // Stop processing if component unmounted
          if (isAborted) {
            break;
          }
          handleChunk(chunk);
        }
      } catch (err) {
        // Ignore AbortError (expected during cleanup)
        if (isAborted) {
          return;
        }

        // Check if error is an AbortError (DOMException or Error)
        const isAbortError =
          (err instanceof Error && err.name === 'AbortError') ||
          (err instanceof DOMException && err.name === 'AbortError');

        if (isAbortError) {
          return;
        }

        console.error('Streaming error:', err);
        setError(err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten');
        setIsStreaming(false);
      }
    };

    fetchStream();

    // Cleanup: Cancel SSE connection when component unmounts
    return () => {
      isAborted = true;
      abortController.abort();
    };
  }, [query, mode, sessionId]);

  // Sprint 28 Feature 28.2: Scroll to source card when citation is clicked
  const handleCitationClick = (sourceId: string) => {
    if (sourceCardsRef.current) {
      sourceCardsRef.current.scrollToSource(sourceId);
    }
  };

  // Sprint 17 Feature 17.3: Auto-trigger title generation after first answer
  useEffect(() => {
    const triggerTitleGeneration = async () => {
      // Only trigger if streaming is complete, we have an answer, and we have a session ID
      if (!isStreaming && answer && currentSessionId && onTitleGenerated) {
        try {
          // Check if this might be the first message (simple heuristic: answer length > 50 chars)
          if (answer.length > 50) {
            const response = await generateConversationTitle(currentSessionId);
            onTitleGenerated(response.title);
            console.log('Title auto-generated:', response.title);
          }
        } catch (err) {
          // Silently fail - title generation is non-critical
          console.warn('Failed to auto-generate title:', err);
        }
      }
    };

    triggerTitleGeneration();
  }, [isStreaming, answer, currentSessionId, onTitleGenerated]);

  const handleChunk = (chunk: ChatChunk) => {
    switch (chunk.type) {
      case 'metadata':
        setMetadata(chunk.data || chunk);
        if (chunk.data?.intent) {
          setIntent(chunk.data.intent);
        }
        // Sprint 17 Feature 17.2: Notify parent of session_id for follow-up questions
        if (chunk.data?.session_id) {
          setCurrentSessionId(chunk.data.session_id);
          if (onSessionIdReceived) {
            onSessionIdReceived(chunk.data.session_id);
          }
        }
        // Sprint 27 Feature 27.10: Store citation_map from backend
        if (chunk.data?.citation_map) {
          setCitationMap(chunk.data.citation_map);
          console.log('Citation map received:', chunk.data.citations_count, 'citations');
        }
        break;

      case 'source':
        if (chunk.source) {
          setSources((prev) => [...prev, chunk.source!]);
        }
        break;

      case 'token':
        if (chunk.content) {
          setAnswer((prev) => prev + chunk.content);
        }
        break;

      case 'complete':
        setMetadata(chunk.data);
        setIsStreaming(false);
        break;

      case 'error':
        setError(chunk.error || 'Unknown error');
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
        <SourceCardsScroll ref={sourceCardsRef} sources={sources} />
      )}

      {/* Answer Content with Citations - Sprint 28 Feature 28.2 */}
      <div className="prose prose-lg max-w-none">
        {answer ? (
          <>
            <ReactMarkdown
              components={{
                // Custom text renderer to process inline citations
                // react-markdown passes props object with children
                text: ({ children }) => {
                  if (typeof children === 'string') {
                    // Sprint 27 Feature 27.10: Prefer citationMap from backend over sources
                    // Convert citationMap (1-indexed Record) to 0-indexed array
                    const sourcesForCitations = citationMap
                      ? Object.entries(citationMap)
                          .sort(([a], [b]) => Number(a) - Number(b))  // Sort by citation number
                          .map(([_, metadata]) => metadata)  // Extract metadata, now 0-indexed
                      : sources;

                    const textRenderer = createCitationTextRenderer(sourcesForCitations, handleCitationClick);
                    return <>{textRenderer(children)}</>;
                  }
                  return <>{children}</>;
                }
              }}
            >
              {answer}
            </ReactMarkdown>
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

      {/* Action Toolbar - Sprint 27 Feature 27.6 */}
      {answer && !isStreaming && (
        <div className="flex items-center justify-end border-t border-gray-200 pt-3 mt-4">
          <CopyButton text={answer} format="markdown" />
        </div>
      )}

      {/* View Knowledge Graph Button - Sprint 29 Feature 29.2 */}
      {sources.length > 0 && !isStreaming && (
        <div className="mt-4">
          <button
            onClick={() => setShowGraphModal(true)}
            className="flex items-center gap-2 px-4 py-2 text-teal-600 hover:text-teal-700 hover:bg-teal-50 rounded-lg transition-colors"
          >
            <Network className="w-5 h-5" />
            <span className="font-medium">View Knowledge Graph</span>
          </button>
        </div>
      )}

      {/* Graph Modal - Sprint 29 Feature 29.2 */}
      {showGraphModal && (
        <GraphModal
          entityNames={extractEntitiesFromSources(sources)}
          onClose={() => setShowGraphModal(false)}
        />
      )}

      {/* Follow-up Questions - Sprint 28 Feature 28.1 */}
      {!isStreaming && currentSessionId && (
        <FollowUpQuestions
          sessionId={currentSessionId}
          onQuestionClick={(question) => {
            if (onFollowUpQuestion) {
              onFollowUpQuestion(question);
            }
          }}
        />
      )}

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
