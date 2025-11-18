/**
 * DocumentPreviewModal Component
 * Sprint 29 Feature 29.6: Embedding-based Document Search from Graph
 *
 * Modal for previewing document details when clicked from NodeDetailsPanel.
 * For now, shows document metadata. Future: Full document viewer with highlighting.
 */

import { X, FileText, Hash, Percent, Info } from 'lucide-react';
import type { RelatedDocument } from '../../types/graph';

interface DocumentPreviewModalProps {
  document: RelatedDocument;
  onClose: () => void;
}

/**
 * Modal for previewing document details
 *
 * Current features:
 * - Document metadata display
 * - Similarity score
 * - Full excerpt
 *
 * Future enhancements:
 * - Full document text viewer
 * - Keyword highlighting
 * - Navigation between chunks
 */
export function DocumentPreviewModal({ document, onClose }: DocumentPreviewModalProps) {
  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      {/* Modal Content */}
      <div
        className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-4 flex items-start justify-between z-10">
          <div className="flex items-start gap-3 flex-1 mr-2">
            <FileText className="w-6 h-6 text-teal-600 flex-shrink-0 mt-1" />
            <div className="flex-1 min-w-0">
              <h3 className="font-bold text-lg text-gray-900" title={document.title}>
                {document.title}
              </h3>
              <p className="text-sm text-gray-500 mt-1">{document.source}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 p-1 hover:bg-gray-100 rounded-md transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Metadata */}
        <div className="p-6 bg-gray-50 border-b border-gray-200">
          <h4 className="font-semibold text-sm text-gray-700 mb-3 flex items-center gap-2">
            <Info className="w-4 h-4" />
            Document Metadata
          </h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-2">
              <Hash className="w-4 h-4 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">Chunk ID</p>
                <p className="text-sm font-medium text-gray-900">{document.chunk_id}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Percent className="w-4 h-4 text-teal-600" />
              <div>
                <p className="text-xs text-gray-500">Similarity</p>
                <p className="text-sm font-semibold text-teal-600">
                  {(document.similarity * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          </div>

          {/* Additional Metadata */}
          {document.metadata && Object.keys(document.metadata).length > 0 && (
            <div className="mt-4">
              <p className="text-xs text-gray-500 mb-2">Additional Metadata:</p>
              <div className="bg-white rounded-md p-3 text-xs font-mono">
                <pre className="whitespace-pre-wrap break-words">
                  {JSON.stringify(document.metadata, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Document Excerpt */}
        <div className="p-6">
          <h4 className="font-semibold text-sm text-gray-700 mb-3">Document Excerpt</h4>
          <div className="prose prose-sm max-w-none">
            <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
              {document.excerpt}
            </p>
          </div>

          {/* Future Enhancement Notice */}
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              <strong>Future Enhancement:</strong> Full document viewer with keyword highlighting
              and chunk navigation will be available in a future update.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors font-medium text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
