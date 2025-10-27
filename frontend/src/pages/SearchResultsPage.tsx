/**
 * SearchResultsPage Component
 * Sprint 15 Feature 15.4: Display streaming search results
 *
 * Shows query, streaming answer, and sources
 */

import { useSearchParams, useNavigate } from 'react-router-dom';
import { StreamingAnswer } from '../components/chat';
import { SearchInput, SearchMode } from '../components/search';

export function SearchResultsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const query = searchParams.get('q') || '';
  const mode = (searchParams.get('mode') || 'hybrid') as SearchMode;
  const sessionId = searchParams.get('session_id') || undefined;

  const handleNewSearch = (newQuery: string, newMode: SearchMode) => {
    navigate(`/search?q=${encodeURIComponent(newQuery)}&mode=${newMode}`);
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
          sessionId={sessionId}
        />
      </div>
    </div>
  );
}
