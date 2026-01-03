/**
 * MemorySearchPanel Component
 * Sprint 72 Feature 72.3: Memory Management UI
 *
 * Search form with filters for searching across memory layers.
 * Displays results with pagination and layer indicators.
 */

import { useState, useCallback } from 'react';
import { Search, Filter, ChevronLeft, ChevronRight, Download, Database, HardDrive, Network } from 'lucide-react';
import type { MemorySearchRequest, MemorySearchResult, MemorySearchResponse } from '../../types/admin';
import { searchMemory, exportMemory } from '../../api/admin';

/**
 * Props for MemorySearchPanel component
 */
interface MemorySearchPanelProps {
  /** Optional list of namespaces for filtering */
  namespaces?: string[];
}

/**
 * Layer badge component
 */
function LayerBadge({ layer }: { layer: 'redis' | 'qdrant' | 'graphiti' }) {
  const config = {
    redis: {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-700 dark:text-red-400',
      icon: Database,
      label: 'Redis',
    },
    qdrant: {
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      text: 'text-blue-700 dark:text-blue-400',
      icon: HardDrive,
      label: 'Qdrant',
    },
    graphiti: {
      bg: 'bg-purple-100 dark:bg-purple-900/30',
      text: 'text-purple-700 dark:text-purple-400',
      icon: Network,
      label: 'Graphiti',
    },
  };

  const { bg, text, icon: Icon, label } = config[layer];

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${bg} ${text}`}>
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}

/**
 * Relevance score indicator
 */
function RelevanceIndicator({ score }: { score: number }) {
  const percentage = Math.round(score * 100);
  const color =
    percentage >= 80
      ? 'text-green-600 dark:text-green-400'
      : percentage >= 50
      ? 'text-yellow-600 dark:text-yellow-400'
      : 'text-gray-600 dark:text-gray-400';

  return (
    <div className={`text-sm font-medium ${color}`}>
      {percentage}%
    </div>
  );
}

/**
 * Search result row component
 */
function SearchResultRow({ result }: { result: MemorySearchResult }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="border-b border-gray-200 dark:border-gray-700 last:border-b-0 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      data-testid="search-result-row"
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 pt-1">
          <LayerBadge layer={result.layer} />
        </div>
        <div className="flex-grow min-w-0">
          <div
            className={`text-sm text-gray-700 dark:text-gray-300 ${
              expanded ? '' : 'line-clamp-2'
            } cursor-pointer`}
            onClick={() => setExpanded(!expanded)}
          >
            {result.content}
          </div>
          {result.content.length > 150 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-1"
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
            <span>ID: {result.id.slice(0, 8)}...</span>
            <span>{new Date(result.timestamp).toLocaleString()}</span>
          </div>
        </div>
        <div className="flex-shrink-0 text-right">
          <RelevanceIndicator score={result.relevance_score} />
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">Relevance</div>
        </div>
      </div>
    </div>
  );
}

/**
 * MemorySearchPanel - Search form and results display
 */
export function MemorySearchPanel({ namespaces = [] }: MemorySearchPanelProps) {
  // Form state
  const [userId, setUserId] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [query, setQuery] = useState('');
  const [namespace, setNamespace] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Results state
  const [results, setResults] = useState<MemorySearchResult[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Pagination state
  const [page, setPage] = useState(1);
  const limit = 20;

  // Export state
  const [exporting, setExporting] = useState(false);

  const handleSearch = useCallback(async (newPage = 1) => {
    setLoading(true);
    setError(null);
    setHasSearched(true);
    setPage(newPage);

    const request: MemorySearchRequest = {
      limit,
      offset: (newPage - 1) * limit,
    };

    if (userId.trim()) request.user_id = userId.trim();
    if (sessionId.trim()) request.session_id = sessionId.trim();
    if (query.trim()) request.query = query.trim();
    if (namespace) request.namespace = namespace;

    try {
      const response: MemorySearchResponse = await searchMemory(request);
      setResults(response.results);
      setTotalCount(response.total_count);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Search failed'));
      setResults([]);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  }, [userId, sessionId, query, namespace]);

  const handleExport = useCallback(async () => {
    if (!sessionId.trim()) {
      setError(new Error('Session ID is required for export'));
      return;
    }

    setExporting(true);
    try {
      await exportMemory(sessionId.trim());
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Export failed'));
    } finally {
      setExporting(false);
    }
  }, [sessionId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      void handleSearch(1);
    }
  };

  const totalPages = Math.ceil(totalCount / limit);

  return (
    <div className="space-y-4" data-testid="memory-search-panel">
      {/* Search Form */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="flex-grow relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search memory content..."
              className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400"
              data-testid="search-query-input"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border transition-colors ${
              showFilters
                ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-400'
                : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'
            }`}
            data-testid="toggle-filters-button"
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <button
            onClick={() => void handleSearch(1)}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            data-testid="search-button"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            Search
          </button>
        </div>

        {/* Expandable Filters */}
        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                User ID
              </label>
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Filter by user ID"
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 dark:text-gray-100"
                data-testid="user-id-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Session ID
              </label>
              <input
                type="text"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Filter by session ID"
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 dark:text-gray-100"
                data-testid="session-id-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Namespace
              </label>
              <select
                value={namespace}
                onChange={(e) => setNamespace(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 dark:text-gray-100"
                data-testid="namespace-select"
              >
                <option value="">All namespaces</option>
                {namespaces.map((ns) => (
                  <option key={ns} value={ns}>
                    {ns}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-xl p-4">
          <p className="text-sm text-red-700 dark:text-red-400">{error.message}</p>
        </div>
      )}

      {/* Results */}
      {hasSearched && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700">
          {/* Results Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {loading ? (
                'Searching...'
              ) : (
                <>
                  Found <span className="font-semibold text-gray-900 dark:text-gray-100">{totalCount}</span> results
                </>
              )}
            </div>
            {sessionId.trim() && (
              <button
                onClick={() => void handleExport()}
                disabled={exporting}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
                data-testid="export-button"
              >
                <Download className="w-4 h-4" />
                {exporting ? 'Exporting...' : 'Export Session'}
              </button>
            )}
          </div>

          {/* Results List */}
          <div className="px-6 divide-y divide-gray-200 dark:divide-gray-700" data-testid="search-results">
            {loading ? (
              <div className="py-12 text-center">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400">Searching across memory layers...</p>
              </div>
            ) : results.length === 0 ? (
              <div className="py-12 text-center">
                <div className="text-4xl mb-4">?</div>
                <p className="text-gray-500 dark:text-gray-400">No results found. Try adjusting your search criteria.</p>
              </div>
            ) : (
              results.map((result) => <SearchResultRow key={result.id} result={result} />)
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => void handleSearch(page - 1)}
                disabled={page === 1 || loading}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => void handleSearch(page + 1)}
                disabled={page === totalPages || loading}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default MemorySearchPanel;
