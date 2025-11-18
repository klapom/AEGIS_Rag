/**
 * GraphModal Component
 * Sprint 29 Feature 29.2: Query Result Graph Visualization
 *
 * Features:
 * - Modal dialog with GraphViewer
 * - Displays subgraph for entities from query results
 * - Export functionality
 * - Responsive design
 */

import { useEffect } from 'react';
import { X, Download } from 'lucide-react';
import { GraphViewer } from './GraphViewer';
import { useGraphDataByEntities } from '../../hooks/useGraphDataByEntities';

interface GraphModalProps {
  /** List of entity names to visualize */
  entityNames: string[];
  /** Callback when modal is closed */
  onClose: () => void;
}

/**
 * Modal component for displaying query result graph
 * Shows entities and their relationships from query sources
 */
export function GraphModal({ entityNames, onClose }: GraphModalProps) {
  const { data, loading, error } = useGraphDataByEntities(entityNames);

  // Handle ESC key to close modal
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

  // Export graph data as JSON
  const handleExport = () => {
    if (!data) return;

    const dataStr = JSON.stringify(data, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `query-graph-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative bg-white rounded-xl shadow-2xl w-full max-w-6xl h-[80vh] mx-4 flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Knowledge Graph - Query Results
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {loading
                ? 'Loading graph...'
                : error
                ? 'Error loading graph'
                : `Showing relationships between ${entityNames.length} entities from your query`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
            aria-label="Close modal"
          >
            <X className="w-6 h-6 text-gray-600" />
          </button>
        </div>

        {/* Body - Graph Viewer */}
        <div className="flex-1 relative overflow-hidden">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-teal-600 mb-4"></div>
                <div className="text-gray-600">Loading knowledge graph...</div>
              </div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-white">
              <div className="text-center p-8">
                <div className="text-red-500 text-xl mb-2">Failed to load graph</div>
                <div className="text-gray-600 mb-4">{error.message}</div>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {!loading && !error && data && (
            <div className="w-full h-full">
              <GraphViewer
                maxNodes={100}
                entityTypes={undefined}
                highlightCommunities={undefined}
                onNodeClick={(node) => {
                  console.log('Node clicked:', node);
                }}
              />
            </div>
          )}

          {!loading && !error && (!data || data.nodes.length === 0) && (
            <div className="absolute inset-0 flex items-center justify-center bg-white">
              <div className="text-center p-8">
                <div className="text-gray-500 text-xl mb-2">No graph data found</div>
                <div className="text-gray-600 mb-4">
                  The entities from your query may not have relationships in the knowledge graph yet.
                </div>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="text-sm text-gray-600">
            {data && (
              <>
                {data.nodes.length} nodes, {data.links.length} relationships
              </>
            )}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleExport}
              disabled={!data || data.nodes.length === 0}
              className="flex items-center space-x-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>Export JSON</span>
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-900 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
