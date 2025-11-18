/**
 * CommunityDocuments Component
 * Sprint 29 Feature 29.7: Community Document Browser
 *
 * Features:
 * - Modal dialog for viewing documents by community
 * - Grid layout (2 columns desktop, 1 column mobile)
 * - Document cards with entity mentions highlighted
 * - Header shows community topic + document count
 * - Click document to preview
 */

import { useEffect } from 'react';
import { X, FileText, User } from 'lucide-react';
import { useCommunityDocuments } from '../../hooks/useCommunityDocuments';
import type { CommunityDocument } from '../../types/graph';

interface CommunityDocumentsProps {
  communityId: string;
  onClose: () => void;
  onDocumentPreview?: (documentId: string) => void;
}

/**
 * Modal component for browsing documents that belong to a specific community
 *
 * @param communityId Community ID to fetch documents for
 * @param onClose Callback when modal is closed
 * @param onDocumentPreview Optional callback when a document is clicked
 */
export function CommunityDocuments({
  communityId,
  onClose,
  onDocumentPreview,
}: CommunityDocumentsProps) {
  const { documents, community, loading, error } = useCommunityDocuments(communityId);

  // Handle escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const handleDocumentClick = (doc: CommunityDocument) => {
    if (onDocumentPreview) {
      onDocumentPreview(doc.id);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div
          className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start justify-between px-6 py-5 border-b border-gray-200">
            <div className="flex-grow">
              <h2
                id="modal-title"
                className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2"
              >
                <FileText className="w-6 h-6 text-purple-600" />
                Documents - {community?.topic || 'Loading...'}
              </h2>
              <p className="text-sm text-gray-600">
                {loading
                  ? 'Loading documents...'
                  : error
                  ? 'Error loading documents'
                  : `${documents.length} document${documents.length !== 1 ? 's' : ''} mention${documents.length === 1 ? 's' : ''} entities from this community`}
              </p>
            </div>
            <button
              onClick={onClose}
              className="ml-4 text-gray-400 hover:text-gray-600 transition-colors p-1 rounded-md hover:bg-gray-100"
              aria-label="Close modal"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5">
            {loading ? (
              <LoadingSkeleton />
            ) : error ? (
              <ErrorMessage error={error} />
            ) : documents.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {documents.map((doc) => (
                  <DocumentCard
                    key={doc.id}
                    document={doc}
                    onClick={() => handleDocumentClick(doc)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end px-6 py-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border-2 border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-all"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/**
 * Document Card Component
 */
interface DocumentCardProps {
  document: CommunityDocument;
  onClick: () => void;
}

function DocumentCard({ document, onClick }: DocumentCardProps) {
  return (
    <div
      onClick={onClick}
      className="border-2 border-gray-200 rounded-lg p-4 hover:border-purple-400 hover:shadow-md transition-all cursor-pointer bg-white"
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      {/* Document Title */}
      <h3 className="font-semibold text-gray-900 mb-2 line-clamp-1 flex items-start gap-2">
        <FileText className="w-4 h-4 text-purple-600 flex-shrink-0 mt-0.5" />
        <span className="flex-1">{document.title}</span>
      </h3>

      {/* Document Excerpt */}
      <p className="text-sm text-gray-600 mb-3 line-clamp-2">{document.excerpt}</p>

      {/* Entity Mentions */}
      <div className="mt-3 pt-3 border-t border-gray-100">
        <div className="flex items-start gap-2">
          <User className="w-4 h-4 text-gray-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="text-xs font-medium text-gray-500 mb-1.5">Entity Mentions:</div>
            <div className="flex flex-wrap gap-1.5">
              {document.entities.slice(0, 5).map((entity, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-800 rounded-md"
                >
                  {entity}
                </span>
              ))}
              {document.entities.length > 5 && (
                <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded-md">
                  +{document.entities.length - 5} more
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Metadata Footer */}
      {(document.source || document.chunk_id) && (
        <div className="mt-3 pt-2 border-t border-gray-100 flex items-center gap-2 text-xs text-gray-500">
          {document.source && <span>{document.source}</span>}
          {document.source && document.chunk_id && <span>•</span>}
          {document.chunk_id && <span>{document.chunk_id}</span>}
        </div>
      )}
    </div>
  );
}

/**
 * Loading Skeleton
 */
function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="border-2 border-gray-200 rounded-lg p-4 animate-pulse">
          <div className="h-5 bg-gray-200 rounded w-3/4 mb-3" />
          <div className="h-4 bg-gray-200 rounded w-full mb-2" />
          <div className="h-4 bg-gray-200 rounded w-5/6 mb-3" />
          <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100">
            <div className="h-6 bg-gray-200 rounded w-20" />
            <div className="h-6 bg-gray-200 rounded w-24" />
            <div className="h-6 bg-gray-200 rounded w-16" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Error Message
 */
function ErrorMessage({ error }: { error: Error }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
        <X className="w-8 h-8 text-red-600" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Failed to load documents</h3>
      <p className="text-sm text-gray-600 max-w-md">{error.message}</p>
    </div>
  );
}

/**
 * Empty State
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
        <FileText className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">No documents found</h3>
      <p className="text-sm text-gray-600 max-w-md">
        No documents mention entities from this community yet.
      </p>
    </div>
  );
}

/**
 * Compact variant for use in dropdown/compact layouts
 */
interface CommunityDocumentsCompactProps {
  communityId: string;
  maxDocuments?: number;
  onDocumentClick?: (documentId: string) => void;
}

export function CommunityDocumentsCompact({
  communityId,
  maxDocuments = 5,
  onDocumentClick,
}: CommunityDocumentsCompactProps) {
  const { documents, loading, error } = useCommunityDocuments(communityId, maxDocuments);

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || documents.length === 0) {
    return (
      <div className="text-sm text-gray-500 text-center py-4">No documents available</div>
    );
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          onClick={() => onDocumentClick?.(doc.id)}
          className="p-3 border border-gray-200 rounded-lg hover:border-purple-400 hover:shadow-sm transition-all cursor-pointer"
        >
          <div className="font-medium text-sm text-gray-900 line-clamp-1 mb-1">{doc.title}</div>
          <div className="text-xs text-gray-600 line-clamp-1">{doc.excerpt}</div>
          <div className="flex gap-1 mt-2">
            {doc.entities.slice(0, 3).map((entity, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-1.5 py-0.5 text-xs bg-purple-100 text-purple-700 rounded"
              >
                {entity}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
