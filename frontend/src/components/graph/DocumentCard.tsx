/**
 * DocumentCard Component
 * Sprint 29 Feature 29.6: Embedding-based Document Search from Graph
 *
 * Displays a single related document with similarity score and metadata.
 */

import { FileText } from 'lucide-react';
import type { RelatedDocument } from '../../types/graph';

interface DocumentCardProps {
  document: RelatedDocument;
  onPreview: () => void;
}

/**
 * Card component for displaying a related document
 *
 * Features:
 * - Document title (truncated to 1 line)
 * - Excerpt (truncated to 2 lines)
 * - Similarity score as percentage
 * - Source file and chunk ID
 * - Hover effect
 * - Click to preview
 */
export function DocumentCard({ document, onPreview }: DocumentCardProps) {
  return (
    <div
      className="border border-gray-200 rounded-lg p-3 hover:border-teal-500 hover:shadow-md transition-all cursor-pointer"
      onClick={onPreview}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onPreview();
        }
      }}
    >
      {/* Title and Similarity Score */}
      <div className="flex items-start justify-between mb-2">
        <h5 className="font-medium text-sm line-clamp-1 flex-1 mr-2" title={document.title}>
          {document.title}
        </h5>
        <span className="text-xs font-semibold text-teal-600 ml-2 whitespace-nowrap">
          {(document.similarity * 100).toFixed(0)}%
        </span>
      </div>

      {/* Excerpt */}
      <p className="text-xs text-gray-600 line-clamp-2 mb-2" title={document.excerpt}>
        {document.excerpt}
      </p>

      {/* Metadata: Source and Chunk ID */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <FileText className="w-3 h-3 flex-shrink-0" />
        <span className="truncate" title={document.source}>
          {document.source}
        </span>
        <span className="flex-shrink-0">•</span>
        <span className="flex-shrink-0">{document.chunk_id}</span>
      </div>
    </div>
  );
}

/**
 * Skeleton loader for DocumentCard
 */
export function DocumentCardSkeleton() {
  return (
    <div className="border border-gray-200 rounded-lg p-3 animate-pulse">
      {/* Title skeleton */}
      <div className="flex items-start justify-between mb-2">
        <div className="h-4 bg-gray-200 rounded w-2/3"></div>
        <div className="h-4 bg-gray-200 rounded w-10"></div>
      </div>

      {/* Excerpt skeleton */}
      <div className="space-y-2 mb-2">
        <div className="h-3 bg-gray-200 rounded w-full"></div>
        <div className="h-3 bg-gray-200 rounded w-4/5"></div>
      </div>

      {/* Metadata skeleton */}
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 bg-gray-200 rounded"></div>
        <div className="h-3 bg-gray-200 rounded w-24"></div>
        <div className="h-3 bg-gray-200 rounded w-12"></div>
      </div>
    </div>
  );
}
