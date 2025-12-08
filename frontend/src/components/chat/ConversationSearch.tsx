/**
 * ConversationSearch Component
 * Sprint 38 Feature 38.2: Conversation Search UI
 *
 * Features:
 * - Search input with search icon
 * - Debounced search (300ms)
 * - Dropdown results showing: title, snippet, date, relevance score
 * - Loading spinner while searching
 * - Click result to navigate to conversation
 * - Close dropdown on outside click
 * - Minimum 3 characters to trigger search
 */

import { useState, useEffect, useRef } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { useDebounce } from '../../hooks/useDebounce';
import { searchConversations } from '../../api/chat';
import type { ConversationSearchResult } from '../../api/chat';

interface ConversationSearchProps {
  onSelectResult: (sessionId: string) => void;
  placeholder?: string;
}

export function ConversationSearch({
  onSelectResult,
  placeholder = 'Search conversations...',
}: ConversationSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ConversationSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  // Debounce search query (300ms)
  const debouncedQuery = useDebounce(query, 300);

  // Search conversations when debounced query changes
  useEffect(() => {
    const performSearch = async () => {
      // Require minimum 3 characters
      if (debouncedQuery.length < 3) {
        setResults([]);
        setIsOpen(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await searchConversations(debouncedQuery, 10, 0.3);
        setResults(response.results);
        setIsOpen(response.results.length > 0);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Search failed');
        setResults([]);
        setIsOpen(false);
      } finally {
        setIsLoading(false);
      }
    };

    performSearch();
  }, [debouncedQuery]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  const handleResultClick = (sessionId: string) => {
    onSelectResult(sessionId);
    setQuery('');
    setResults([]);
    setIsOpen(false);
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return `${diffMins}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600 bg-green-50';
    if (score >= 0.6) return 'text-blue-600 bg-blue-50';
    return 'text-gray-600 bg-gray-50';
  };

  return (
    <div ref={searchRef} className="relative w-full" data-testid="conversation-search">
      {/* Search Input */}
      <div className="relative">
        <input
          type="search"
          value={query}
          onChange={handleInputChange}
          placeholder={placeholder}
          className="w-full px-4 py-2.5 pl-10 text-sm bg-gray-800 border border-gray-700 rounded-lg
                     focus:border-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600/20
                     placeholder-gray-500 text-white transition-all duration-200
                     hover:border-gray-600"
          aria-label="Search conversations"
          data-testid="conversation-search-input"
        />

        {/* Search Icon or Loading Spinner */}
        <div className="absolute left-3 top-1/2 -translate-y-1/2">
          {isLoading ? (
            <Loader2
              className="w-4 h-4 text-gray-400 animate-spin"
              data-testid="search-loading"
            />
          ) : (
            <Search className="w-4 h-4 text-gray-400" aria-hidden="true" />
          )}
        </div>
      </div>

      {/* Results Dropdown */}
      {isOpen && results.length > 0 && (
        <div
          className="absolute top-full mt-2 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto"
          role="listbox"
          aria-label="Search results"
          data-testid="search-results-dropdown"
        >
          {results.map((result) => (
            <button
              key={result.session_id}
              onClick={() => handleResultClick(result.session_id)}
              className="w-full px-4 py-3 text-left hover:bg-gray-700 active:bg-gray-600
                         flex flex-col gap-1.5 border-b border-gray-700 last:border-b-0
                         transition-colors duration-150"
              role="option"
              aria-selected="false"
              data-testid="search-result-item"
              data-session-id={result.session_id}
            >
              {/* Title and Score */}
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-white text-sm truncate flex-grow">
                  {result.title || 'Untitled Conversation'}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${getScoreColor(
                    result.score
                  )}`}
                  data-testid="result-score"
                >
                  {Math.round(result.score * 100)}%
                </span>
              </div>

              {/* Snippet */}
              {result.snippet && (
                <p
                  className="text-xs text-gray-400 line-clamp-2"
                  data-testid="result-snippet"
                >
                  {result.snippet}
                </p>
              )}

              {/* Date */}
              <span className="text-xs text-gray-500" data-testid="result-date">
                {formatDate(result.archived_at)}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* No Results Message */}
      {query.length >= 3 && !isLoading && results.length === 0 && !error && (
        <div
          className="absolute top-full mt-2 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50 px-4 py-6 text-center"
          data-testid="no-results-message"
        >
          <div className="text-sm text-gray-400">
            No conversations found matching "{query}"
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div
          className="absolute top-full mt-2 w-full bg-gray-800 border border-red-700 rounded-lg shadow-lg z-50 px-4 py-3"
          data-testid="search-error-message"
        >
          <div className="text-sm text-red-400">{error}</div>
        </div>
      )}

      {/* Minimum Characters Hint */}
      {query.length > 0 && query.length < 3 && (
        <div className="absolute top-full mt-2 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50 px-4 py-3">
          <div className="text-xs text-gray-500">
            Type at least 3 characters to search
          </div>
        </div>
      )}
    </div>
  );
}
