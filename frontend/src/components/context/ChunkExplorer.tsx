/**
 * ChunkExplorer Component
 * Sprint 111 Feature 111.1: Long Context UI
 *
 * Interactive chunk navigation component allowing users to:
 * - Browse through document chunks
 * - Preview chunk content
 * - View relevance scores per chunk
 * - Navigate using keyboard or scroll
 */

import { useState, useMemo } from 'react';
import { FileText, ChevronLeft, ChevronRight, Search, Hash } from 'lucide-react';

export interface DocumentChunk {
  id: string;
  content: string;
  relevanceScore: number;
  tokenCount: number;
  chunkIndex: number;
  metadata?: {
    source?: string;
    section?: string;
    pageNumber?: number;
  };
}

interface ChunkExplorerProps {
  chunks: DocumentChunk[];
  onChunkSelect?: (chunk: DocumentChunk) => void;
  selectedChunkId?: string;
  className?: string;
}

export function ChunkExplorer({
  chunks,
  onChunkSelect,
  selectedChunkId,
  className = '',
}: ChunkExplorerProps) {
  const [currentPage, setCurrentPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  const CHUNKS_PER_PAGE = 10;

  // Filter chunks by search query
  const filteredChunks = useMemo(() => {
    if (!searchQuery.trim()) return chunks;
    const query = searchQuery.toLowerCase();
    return chunks.filter(
      (chunk) =>
        chunk.content.toLowerCase().includes(query) ||
        chunk.metadata?.section?.toLowerCase().includes(query)
    );
  }, [chunks, searchQuery]);

  // Paginate chunks
  const paginatedChunks = useMemo(() => {
    const start = currentPage * CHUNKS_PER_PAGE;
    return filteredChunks.slice(start, start + CHUNKS_PER_PAGE);
  }, [filteredChunks, currentPage]);

  const totalPages = Math.ceil(filteredChunks.length / CHUNKS_PER_PAGE);

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30';
    if (score >= 0.5) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30';
    return 'text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-700';
  };

  const truncateContent = (content: string, maxLength: number = 150): string => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength).trim() + '...';
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 ${className}`} data-testid="chunk-explorer">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              Document Chunks
            </h3>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              ({filteredChunks.length} chunks)
            </span>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search chunks..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(0);
            }}
            className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-blue-500"
            data-testid="chunk-search-input"
          />
        </div>
      </div>

      {/* Chunk List */}
      <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-96 overflow-y-auto" data-testid="chunk-list">
        {paginatedChunks.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400" data-testid="empty-chunks">
            No chunks found
          </div>
        ) : (
          paginatedChunks.map((chunk) => (
            <div
              key={chunk.id}
              onClick={() => onChunkSelect?.(chunk)}
              className={`p-4 cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-700 ${
                selectedChunkId === chunk.id
                  ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500'
                  : ''
              }`}
              data-testid={`chunk-item-${chunk.id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  {/* Chunk header */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-400">
                      <Hash className="w-3 h-3" />
                      {chunk.chunkIndex + 1}
                    </span>
                    {chunk.metadata?.section && (
                      <span className="text-xs text-blue-600 dark:text-blue-400">
                        {chunk.metadata.section}
                      </span>
                    )}
                    <span className="text-xs text-gray-400">
                      {chunk.tokenCount} tokens
                    </span>
                  </div>

                  {/* Chunk content preview */}
                  <p className="text-sm text-gray-700 dark:text-gray-300" data-testid="chunk-content">
                    {truncateContent(chunk.content)}
                  </p>
                </div>

                {/* Relevance score */}
                <div
                  className={`px-2 py-1 rounded text-xs font-semibold ${getScoreColor(chunk.relevanceScore)}`}
                  data-testid={`chunk-score-${chunk.id}`}
                >
                  {(chunk.relevanceScore * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between" data-testid="chunk-pagination">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Page {currentPage + 1} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              disabled={currentPage === 0}
              className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="chunk-prev-page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={currentPage >= totalPages - 1}
              className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="chunk-next-page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
