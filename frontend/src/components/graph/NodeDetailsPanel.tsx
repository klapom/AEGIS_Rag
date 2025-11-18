/**
 * NodeDetailsPanel Component
 * Sprint 29 Feature 29.6: Embedding-based Document Search from Graph
 *
 * Side panel that displays node details and related documents when a node is clicked.
 *
 * Features:
 * - Node information (name, type, connections, community)
 * - Related documents via vector similarity search
 * - Document preview on click
 * - Slide-in animation from right
 */

import { useState } from 'react';
import { X, FileText, AlertCircle } from 'lucide-react';
import type { GraphNode, RelatedDocument } from '../../types/graph';
import { useDocumentsByNode } from '../../hooks/useDocumentsByNode';
import { DocumentCard, DocumentCardSkeleton } from './DocumentCard';
import { DocumentPreviewModal } from './DocumentPreviewModal';

interface NodeDetailsPanelProps {
  node: GraphNode | null;
  onClose: () => void;
}

/**
 * Side panel that appears when a graph node is clicked
 *
 * Displays:
 * 1. Node details (name, type, connections, community)
 * 2. Related documents from vector search (top 10 by similarity)
 * 3. Document preview modal on click
 */
export function NodeDetailsPanel({ node, onClose }: NodeDetailsPanelProps) {
  const { documents, loading, error } = useDocumentsByNode(node?.label || null);
  const [previewDocument, setPreviewDocument] = useState<RelatedDocument | null>(null);

  // Don't render if no node selected
  if (!node) return null;

  return (
    <>
      {/* Side Panel */}
      <div className="absolute right-0 top-0 w-96 h-full bg-white border-l border-gray-200 shadow-lg overflow-y-auto z-20 animate-slide-in-right">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-4 flex items-start justify-between z-10">
          <div className="flex-1 mr-2">
            <h3 className="font-bold text-lg text-gray-900 line-clamp-2" title={node.label}>
              {node.label}
            </h3>
            <p className="text-sm text-gray-500 mt-1">{node.type}</p>
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 p-1 hover:bg-gray-100 rounded-md transition-colors"
            aria-label="Close panel"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Node Information */}
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <h4 className="font-semibold text-sm text-gray-700 mb-3">Node Information</h4>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Connections:</span>
              <span className="font-medium text-gray-900">{node.degree || 0}</span>
            </div>
            {node.community && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Community:</span>
                <span className="font-medium text-gray-900 text-right max-w-[200px] truncate" title={node.community}>
                  {node.community}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Related Documents Section */}
        <div className="p-4">
          <h4 className="font-semibold text-sm text-gray-700 mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-teal-600" />
            Related Documents
          </h4>

          {/* Loading State */}
          {loading && (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <DocumentCardSkeleton key={i} />
              ))}
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-800">Failed to load documents</p>
                <p className="text-xs text-red-600 mt-1">{error.message}</p>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && documents.length === 0 && (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">No related documents found</p>
              <p className="text-xs text-gray-400 mt-1">
                Try ingesting documents that mention "{node.label}"
              </p>
            </div>
          )}

          {/* Documents List */}
          {!loading && !error && documents.length > 0 && (
            <div className="space-y-3">
              {documents.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  document={doc}
                  onPreview={() => setPreviewDocument(doc)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Document Preview Modal */}
      {previewDocument && (
        <DocumentPreviewModal
          document={previewDocument}
          onClose={() => setPreviewDocument(null)}
        />
      )}
    </>
  );
}
