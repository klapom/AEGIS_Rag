/**
 * SearchResultsPage Component
 * Sprint 15 Feature 15.4: Display streaming search results
 * Sprint 17 Feature 17.2: Preserve session_id for follow-up questions
 * Sprint 19: Load conversation history when clicking history items
 *
 * Shows query, streaming answer, and sources
 */

import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { StreamingAnswer } from '../components/chat';
import { SearchInput, type SearchMode } from '../components/search';
import { getConversationHistory } from '../api/chat';
import type { ConversationMessage } from '../types/chat';

export function SearchResultsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const query = searchParams.get('q') || '';
  const mode = (searchParams.get('mode') || 'hybrid') as SearchMode;
  const initialSessionId = searchParams.get('session_id') || undefined;

  // Sprint 17 Feature 17.2: Track active session ID for follow-up questions
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(initialSessionId);

  // Sprint 19: Load conversation history when navigating from history sidebar
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Update activeSessionId when URL session_id changes
  useEffect(() => {
    if (initialSessionId) {
      setActiveSessionId(initialSessionId);
    }
  }, [initialSessionId]);

  // Sprint 19: Load conversation history if session_id provided but no query
  useEffect(() => {
    const loadHistory = async () => {
      if (initialSessionId && !query) {
        setIsLoadingHistory(true);
        try {
          const history = await getConversationHistory(initialSessionId);
          setConversationHistory(history.messages);
        } catch (err) {
          console.error('Failed to load conversation history:', err);
        } finally {
          setIsLoadingHistory(false);
        }
      }
    };
    loadHistory();
  }, [initialSessionId, query]);

  const handleNewSearch = (newQuery: string, newMode: SearchMode) => {
    // Sprint 17 Feature 17.2: Include session_id in URL to maintain conversation context
    const url = activeSessionId
      ? `/search?q=${encodeURIComponent(newQuery)}&mode=${newMode}&session_id=${activeSessionId}`
      : `/search?q=${encodeURIComponent(newQuery)}&mode=${newMode}`;
    navigate(url);
  };

  // Sprint 17 Feature 17.2: Callback to update session ID from metadata
  const handleSessionIdReceived = (sessionId: string) => {
    if (!activeSessionId && sessionId) {
      setActiveSessionId(sessionId);
    }
  };

  // Sprint 28 Feature 28.1: Handle follow-up question clicks
  const handleFollowUpQuestion = (question: string) => {
    handleNewSearch(question, mode);
  };

  // Sprint 19: Show conversation history if no query but has session_id
  if (!query && initialSessionId) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Top Search Bar */}
        <div className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
          <div className="max-w-5xl mx-auto py-4 px-6">
            <SearchInput
              onSubmit={handleNewSearch}
              placeholder="Neue Frage..."
              autoFocus={false}
            />
          </div>
        </div>

        {/* Conversation History */}
        <div className="max-w-5xl mx-auto py-8 px-6">
          {isLoadingHistory ? (
            <div className="text-center py-12">
              <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-gray-600">Lade Konversation...</p>
            </div>
          ) : conversationHistory.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>Keine Nachrichten in dieser Konversation</p>
            </div>
          ) : (
            <div className="space-y-6">
              {conversationHistory.map((message, index) => (
                <div
                  key={index}
                  className={`p-6 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-blue-50 border-2 border-blue-200'
                      : 'bg-white border-2 border-gray-200'
                  }`}
                >
                  <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
                    {message.role === 'user' ? 'Frage' : 'Antwort'}
                  </div>
                  <div className="text-gray-900 whitespace-pre-wrap">{message.content}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // TD-38: Handle empty or whitespace-only queries (when no session_id either)
  if (!query || !query.trim()) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <h2 className="text-2xl font-bold text-gray-900">Keine Suchanfrage</h2>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover transition"
          >
            Zur Startseite
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Search Bar */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto py-4 px-6">
          <SearchInput
            onSubmit={handleNewSearch}
            placeholder="Neue Suche..."
            autoFocus={false}
          />
        </div>
      </div>

      {/* Results */}
      <div className="py-8">
        <StreamingAnswer
          query={query}
          mode={mode}
          sessionId={activeSessionId}
          onSessionIdReceived={handleSessionIdReceived}
          onFollowUpQuestion={handleFollowUpQuestion}
        />
      </div>
    </div>
  );
}
