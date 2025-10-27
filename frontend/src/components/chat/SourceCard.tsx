/**
 * SourceCard Component
 * Sprint 15 Feature 15.4: Individual source card display
 *
 * Displays metadata and preview of a single source document
 */

import type { Source } from '../../types/chat';

interface SourceCardProps {
  source: Source;
  index: number;
}

export function SourceCard({ source, index }: SourceCardProps) {
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

  return (
    <div
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
            <div className="text-sm font-semibold text-gray-900 truncate">
              {source.document_id || 'Document'}
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
