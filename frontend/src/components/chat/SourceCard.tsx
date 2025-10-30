/**
 * SourceCard Component
 * Sprint 15 Feature 15.4: Individual source card display
 * Sprint 19 Feature: Source click with chunk preview modal
 *
 * Displays metadata and preview of a single source document
 * Click opens modal with full chunk context or graph visualization
 */

import { useState, useEffect } from 'react';
import type { Source } from '../../types/chat';

interface SourceCardProps {
  source: Source;
  index: number;
}

export function SourceCard({ source, index }: SourceCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const getRetrievalModeIcon = (mode: string) => {
    switch (mode) {
      case 'vector':
        return '🔍';
      case 'graph':
        return '🕸️';
      case 'memory':
        return '💭';
      case 'bm25':
        return '📝';
      default:
        return '📄';
    }
  };

  const isGraphSource = source.retrieval_modes?.includes('graph');

  // Sprint 19: Extract readable document name from metadata
  const getDocumentName = () => {
    // Try metadata.source first (actual filename)
    if (source.metadata?.source) {
      // Extract filename from path
      const filename = source.metadata.source.split(/[/\\]/).pop() || source.metadata.source;
      // Remove file extension for cleaner display
      return filename.replace(/\.[^/.]+$/, '');
    }
    // Fallback to document_id if available
    if (source.document_id && source.document_id !== 'Document') {
      return source.document_id;
    }
    // Last resort fallback
    return 'Unbekanntes Dokument';
  };

  return (
    <>
      <div
        onClick={() => setIsModalOpen(true)}
        className="flex-shrink-0 w-80 p-5 bg-white border-2 border-gray-200
                   rounded-xl hover:shadow-lg hover:border-primary/50
                   transition-all duration-200 cursor-pointer group"
      >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center
                          group-hover:bg-primary/20 transition-colors">
            <span className="text-lg font-bold text-primary">{index}</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-gray-900 truncate" title={getDocumentName()}>
              {getDocumentName()}
            </div>
            {source.chunk_index !== undefined && (
              <div className="text-xs text-gray-500">
                Chunk {source.chunk_index}
                {source.total_chunks && ` / ${source.total_chunks}`}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="space-y-2 mb-4">
        {/* Score */}
        {source.score !== undefined && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">Relevanz:</span>
            <div className="flex items-center space-x-2">
              <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all"
                  style={{ width: `${Math.min(source.score * 100, 100)}%` }}
                />
              </div>
              <span className="font-medium text-gray-900 text-xs">
                {(source.score * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}

        {/* Retrieval Modes */}
        {source.retrieval_modes && source.retrieval_modes.length > 0 && (
          <div className="flex items-center space-x-1">
            {source.retrieval_modes.map((mode) => (
              <span
                key={mode}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-md
                           flex items-center space-x-1"
                title={mode}
              >
                <span>{getRetrievalModeIcon(mode)}</span>
                <span className="capitalize">{mode}</span>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Content Preview */}
      <p className="text-sm text-gray-700 line-clamp-4 leading-relaxed">
        {source.context || 'Keine Vorschau verfügbar'}
      </p>

      {/* Entity Tags */}
      {source.entities && source.entities.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex flex-wrap gap-1.5">
            {source.entities.slice(0, 4).map((entity, i) => (
              <EntityTag key={i} entity={entity} />
            ))}
            {source.entities.length > 4 && (
              <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-md">
                +{source.entities.length - 4} mehr
              </span>
            )}
          </div>
        </div>
      )}

      {/* Metadata Footer */}
      {source.metadata && (
        <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500 space-y-1">
          {source.metadata.source && (
            <div className="truncate" title={source.metadata.source}>
              📎 {source.metadata.source}
            </div>
          )}
          {source.metadata.created_at && (
            <div>
              🕒 {new Date(source.metadata.created_at).toLocaleDateString('de-DE')}
            </div>
          )}
        </div>
      )}
    </div>

    {/* Source Detail Modal */}
    {isModalOpen && (
      <SourceDetailModal
        source={source}
        index={index}
        isGraphSource={isGraphSource}
        onClose={() => setIsModalOpen(false)}
      />
    )}
    </>
  );
}

interface EntityTagProps {
  entity: { name: string; type?: string };
}

function EntityTag({ entity }: EntityTagProps) {
  const getEntityTypeColor = (type?: string) => {
    switch (type?.toLowerCase()) {
      case 'person':
        return 'bg-blue-100 text-blue-700';
      case 'organization':
        return 'bg-purple-100 text-purple-700';
      case 'location':
        return 'bg-green-100 text-green-700';
      case 'date':
        return 'bg-orange-100 text-orange-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <span
      className={`px-2 py-1 text-xs rounded-md ${getEntityTypeColor(entity.type)}`}
      title={entity.type}
    >
      {entity.name}
    </span>
  );
}

// Source Detail Modal Component
interface SourceDetailModalProps {
  source: Source;
  index: number;
  isGraphSource: boolean;
  onClose: () => void;
}

function SourceDetailModal({ source, index, isGraphSource, onClose }: SourceDetailModalProps) {
  // Sprint 19: Extract readable document name
  const getDocumentName = () => {
    if (source.metadata?.source) {
      const filename = source.metadata.source.split(/[/\\]/).pop() || source.metadata.source;
      return filename.replace(/\.[^/.]+$/, '');
    }
    if (source.document_id && source.document_id !== 'Document') {
      return source.document_id;
    }
    return 'Unbekanntes Dokument';
  };

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      {/* Modal Content */}
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
              <span className="text-lg font-bold text-primary">{index}</span>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                {getDocumentName()}
              </h2>
              {source.chunk_index !== undefined && (
                <p className="text-sm text-gray-500">
                  Chunk {source.chunk_index}
                  {source.total_chunks && ` / ${source.total_chunks}`}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors"
            aria-label="Schließen"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {/* Graph Source Notice */}
          {isGraphSource && (
            <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
              <div className="flex items-start space-x-3">
                <span className="text-2xl">🕸️</span>
                <div>
                  <h3 className="font-semibold text-purple-900 mb-1">Graph-Quelle</h3>
                  <p className="text-sm text-purple-700">
                    Diese Quelle stammt aus dem Knowledge Graph. Eine grafische Visualisierung folgt in einem späteren Sprint.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            {source.score !== undefined && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500 mb-2">Relevanz-Score</div>
                <div className="flex items-center space-x-3">
                  <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${Math.min(source.score * 100, 100)}%` }}
                    />
                  </div>
                  <span className="font-bold text-lg text-gray-900">
                    {(source.score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            )}

            {source.retrieval_modes && source.retrieval_modes.length > 0 && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500 mb-2">Retrieval-Modi</div>
                <div className="flex flex-wrap gap-2">
                  {source.retrieval_modes.map((mode) => (
                    <span
                      key={mode}
                      className="px-3 py-1 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg capitalize"
                    >
                      {mode}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Full Context */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Kontext</h3>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                {source.context || 'Kein Kontext verfügbar'}
              </p>
            </div>
          </div>

          {/* Entities */}
          {source.entities && source.entities.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Entitäten ({source.entities.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {source.entities.map((entity, i) => (
                  <EntityTag key={i} entity={entity} />
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          {source.metadata && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Metadaten</h3>
              <div className="p-4 bg-gray-50 rounded-lg space-y-2 text-sm">
                {source.metadata.source && (
                  <div className="flex items-start">
                    <span className="text-gray-500 w-32 flex-shrink-0">Quelle:</span>
                    <span className="text-gray-900 break-all">{source.metadata.source}</span>
                  </div>
                )}
                {source.metadata.created_at && (
                  <div className="flex items-start">
                    <span className="text-gray-500 w-32 flex-shrink-0">Erstellt:</span>
                    <span className="text-gray-900">
                      {new Date(source.metadata.created_at).toLocaleString('de-DE')}
                    </span>
                  </div>
                )}
                {source.metadata.page && (
                  <div className="flex items-start">
                    <span className="text-gray-500 w-32 flex-shrink-0">Seite:</span>
                    <span className="text-gray-900">{source.metadata.page}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Klicken Sie außerhalb des Modals oder drücken Sie ESC zum Schließen
            </p>
            <button
              onClick={onClose}
              className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors"
            >
              Schließen
            </button>
          </div>
        </div>
      </div>

      {/* Backdrop Click Handler */}
      <div
        className="absolute inset-0 -z-10"
        onClick={onClose}
      />
    </div>
  );
}
