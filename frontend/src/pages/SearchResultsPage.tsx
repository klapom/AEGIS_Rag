/**
 * SearchResultsPage Component
 * Sprint 15 Feature 15.4: Display streaming search results
 * Sprint 17 Feature 17.2: Preserve session_id for follow-up questions
 *
 * Shows query, streaming answer, and sources
 */

import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { StreamingAnswer } from '../components/chat';
import { SearchInput, type SearchMode } from '../components/search';

export function SearchResultsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const query = searchParams.get('q') || '';
  const mode = (searchParams.get('mode') || 'hybrid') as SearchMode;
  const initialSessionId = searchParams.get('session_id') || undefined;

  // Sprint 17 Feature 17.2: Track active session ID for follow-up questions
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(initialSessionId);

  // Update activeSessionId when URL session_id changes
  useEffect(() => {
    if (initialSessionId) {
      setActiveSessionId(initialSessionId);
    }
  }, [initialSessionId]);

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

  if (!query) {
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
        />
      </div>
    </div>
  );
}
