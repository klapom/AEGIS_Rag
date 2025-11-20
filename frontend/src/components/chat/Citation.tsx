/**
 * Citation Component
 * Sprint 28 Feature 28.2: Inline citations with hover previews
 *
 * Features:
 * - Superscript [1] styling with blue color
 * - Hover tooltip with source preview
 * - Click to scroll to source card
 */

import { useState } from 'react';
import type { Source } from '../../types/chat';

interface CitationProps {
  sourceIndex: number;
  source: Source;
  onClickScrollTo: (sourceId: string) => void;
}

export function Citation({ sourceIndex, source, onClickScrollTo }: CitationProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    // Use document_id or index as identifier
    const sourceId = source.document_id || `source-${sourceIndex}`;
    onClickScrollTo(sourceId);
  };

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

  const getPreviewText = () => {
    const text = source.context || source.text || '';
    return text.length > 100 ? text.slice(0, 100) + '...' : text;
  };

  return (
    <span className="inline-block relative">
      <button
        onClick={handleClick}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className="text-blue-600 hover:text-blue-800 cursor-pointer font-medium transition-colors"
        style={{ fontSize: '0.75em', verticalAlign: 'super' }}
        aria-label={`Quelle ${sourceIndex}: ${getDocumentName()}`}
        data-testid="citation"
        data-citation-number={sourceIndex}
      >
        [{sourceIndex}]
      </button>

      {/* Hover Tooltip */}
      {showTooltip && (
        <div
          className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50
                     w-80 p-3 bg-white border border-gray-200 rounded-lg shadow-xl
                     pointer-events-none"
          style={{ minWidth: '320px' }}
          data-testid="citation-tooltip"
        >
          {/* Arrow */}
          <div
            className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-px
                       w-0 h-0 border-l-8 border-r-8 border-t-8
                       border-l-transparent border-r-transparent border-t-white"
          />

          {/* Content */}
          <div className="space-y-2">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-6 h-6 bg-blue-100 rounded flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-bold text-blue-600">{sourceIndex}</span>
                </div>
                <div className="font-semibold text-gray-900 text-sm truncate">
                  {getDocumentName()}
                </div>
              </div>
            </div>

            {source.score !== undefined && (
              <div className="flex items-center space-x-2 text-xs">
                <span className="text-gray-500">Relevanz:</span>
                <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${Math.min(source.score * 100, 100)}%` }}
                  />
                </div>
                <span className="font-medium text-gray-700">
                  {(source.score * 100).toFixed(0)}%
                </span>
              </div>
            )}

            <p className="text-xs text-gray-700 leading-relaxed line-clamp-3">
              {getPreviewText()}
            </p>

            {source.retrieval_modes && source.retrieval_modes.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {source.retrieval_modes.map((mode) => (
                  <span
                    key={mode}
                    className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded capitalize"
                  >
                    {mode}
                  </span>
                ))}
              </div>
            )}

            <div className="text-xs text-gray-500 pt-1 border-t border-gray-100">
              Klicken zum Scrollen
            </div>
          </div>
        </div>
      )}
    </span>
  );
}
