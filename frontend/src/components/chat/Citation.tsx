/**
 * Citation Component
 * Sprint 28 Feature 28.2: Inline citations with hover previews
 * Sprint 62 Feature 62.4: Section-aware citations with section display
 *
 * Features:
 * - Superscript [1] styling with blue color
 * - Hover tooltip with source preview
 * - Click to scroll to source card
 * - Section information display (62.4)
 * - Document type badge (62.4)
 */

import { useState } from 'react';
import { FileText, File, FileCode, BookOpen, Hash } from 'lucide-react';
import type { Source } from '../../types/chat';
import {
  extractSectionMetadata,
  getDocumentType,
  formatSectionDisplay,
  formatSectionPath,
  type DocumentType,
} from '../../types/section';

/**
 * Extract clean text content from source text field.
 *
 * Sprint 32 Fix: Handle malformed Python object strings from legacy ingestion.
 * Some older data in Qdrant contains stringified Python objects like:
 * "chunk_id='abc' document_id='def' chunk_index=0 content='The actual text...' metadata={...}"
 *
 * This function extracts the actual content from such strings.
 */
function extractContextText(text: string | undefined): string {
  if (!text) return '';

  // Check if this looks like a Python object string (contains content='...')
  const contentMatch = text.match(/content='([^']*(?:''[^']*)*)'/);
  if (contentMatch) {
    // Extract content and unescape Python string escapes
    return contentMatch[1]
      .replace(/''/g, "'")  // Python escaped single quotes
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\r/g, '\r');
  }

  // Check for double-quoted content
  const contentMatchDouble = text.match(/content="([^"]*(?:""[^"]*)*)"/);
  if (contentMatchDouble) {
    return contentMatchDouble[1]
      .replace(/""/g, '"')
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\r/g, '\r');
  }

  // Not a Python object string, return as-is
  return text;
}

/**
 * Clean text for display by removing control characters.
 */
function cleanTextForDisplay(text: string): string {
  if (!text) return '';

  // Remove control characters but keep newlines, tabs, and spaces
  return text
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '') // Remove control chars except \t, \n, \r
    .trim();
}

interface CitationProps {
  sourceIndex: number;
  source: Source;
  onClickScrollTo: (sourceId: string) => void;
}

/**
 * Sprint 62.4: Get icon component for document type
 */
function getDocumentTypeIcon(docType: DocumentType): React.ReactNode {
  const iconClass = 'w-3 h-3';

  switch (docType) {
    case 'pdf':
      return <FileText className={iconClass} />;
    case 'docx':
      return <File className={iconClass} />;
    case 'md':
      return <BookOpen className={iconClass} />;
    case 'txt':
    case 'html':
      return <FileCode className={iconClass} />;
    default:
      return <File className={iconClass} />;
  }
}

/**
 * Sprint 62.4: Get color class for document type badge
 */
function getDocumentTypeColor(docType: DocumentType): string {
  switch (docType) {
    case 'pdf':
      return 'bg-red-100 text-red-700';
    case 'docx':
      return 'bg-blue-100 text-blue-700';
    case 'md':
      return 'bg-purple-100 text-purple-700';
    case 'txt':
      return 'bg-gray-100 text-gray-700';
    case 'html':
      return 'bg-orange-100 text-orange-700';
    default:
      return 'bg-gray-100 text-gray-600';
  }
}

/**
 * Sprint 62.4: Get display name for document type
 */
function getDocumentTypeName(docType: DocumentType): string {
  switch (docType) {
    case 'pdf':
      return 'PDF';
    case 'docx':
      return 'Word';
    case 'md':
      return 'Markdown';
    case 'txt':
      return 'Text';
    case 'html':
      return 'HTML';
    default:
      return 'Document';
  }
}

export function Citation({ sourceIndex, source, onClickScrollTo }: CitationProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  // Sprint 62.4: Extract section metadata and document type
  const sectionMetadata = extractSectionMetadata(source);
  const docType = source.document_type || getDocumentType(source);
  const hasSection = sectionMetadata !== null && (
    sectionMetadata.section_title ||
    sectionMetadata.section_number ||
    sectionMetadata.section_id
  );

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    // Use document_id or index as identifier
    const sourceId = source.document_id || `source-${sourceIndex}`;
    onClickScrollTo(sourceId);
  };

  const getDocumentName = () => {
    // Check title first (from citation_map, usually the best display name)
    if (source.title && source.title !== 'Unknown') {
      // If title is a file path, extract just the filename
      if (source.title.includes('/') || source.title.includes('\\')) {
        const filename = source.title.split(/[/\\]/).pop() || source.title;
        return filename.replace(/\.[^/.]+$/, '');
      }
      return source.title;
    }
    // Check direct source field (from citation_map - the document path)
    if (source.source && source.source !== 'Unknown') {
      const filename = source.source.split(/[/\\]/).pop() || source.source;
      return filename.replace(/\.[^/.]+$/, '');
    }
    // Check metadata.source (from SSE source events)
    if (source.metadata?.source) {
      const metaSource = source.metadata.source as string;
      const filename = metaSource.split(/[/\\]/).pop() || metaSource;
      return filename.replace(/\.[^/.]+$/, '');
    }
    // Check document_id as fallback
    if (source.document_id && source.document_id !== 'Document') {
      return source.document_id;
    }
    return 'Unbekanntes Dokument';
  };

  const getPreviewText = () => {
    // Sprint 32 Fix: Extract clean text from Python object strings + clean for display
    const rawText = source.context || source.text || '';
    const text = cleanTextForDisplay(extractContextText(rawText));
    return text.length > 100 ? text.slice(0, 100) + '...' : text;
  };

  // Sprint 62.4: Get section display text
  const getSectionDisplayText = () => {
    if (!sectionMetadata) return null;
    return formatSectionDisplay(sectionMetadata);
  };

  // Sprint 62.4: Get section path for tooltip
  const getSectionPathText = () => {
    if (!sectionMetadata) return null;
    return formatSectionPath(sectionMetadata);
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
            {/* Header with document name and badges */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center space-x-2 min-w-0 flex-1">
                <div className="w-6 h-6 bg-blue-100 rounded flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-bold text-blue-600">{sourceIndex}</span>
                </div>
                <div className="font-semibold text-gray-900 text-sm truncate">
                  {getDocumentName()}
                </div>
              </div>
              {/* Sprint 62.4: Document type badge */}
              {docType !== 'unknown' && (
                <span
                  className={`flex items-center gap-1 px-1.5 py-0.5 text-xs rounded flex-shrink-0 ${getDocumentTypeColor(docType)}`}
                  data-testid="document-type-badge"
                >
                  {getDocumentTypeIcon(docType)}
                  <span className="hidden sm:inline">{getDocumentTypeName(docType)}</span>
                </span>
              )}
            </div>

            {/* Sprint 62.4: Section information */}
            {hasSection && (
              <div
                className="flex items-center gap-2 px-2 py-1.5 bg-indigo-50 rounded-md border border-indigo-100"
                data-testid="section-info"
                title={getSectionPathText() || undefined}
              >
                <Hash className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0" />
                <span className="text-xs text-indigo-700 truncate">
                  {getSectionDisplayText()}
                </span>
                {sectionMetadata?.section_level && (
                  <span className="text-xs text-indigo-400 flex-shrink-0">
                    (L{sectionMetadata.section_level})
                  </span>
                )}
              </div>
            )}

            {/* Sprint 32 Fix: Check for both null and undefined */}
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-gray-500">Relevanz:</span>
              {source.score != null && source.score > 0 ? (
                <>
                  <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full"
                      style={{ width: `${Math.min(source.score * 100, 100)}%` }}
                    />
                  </div>
                  <span className="font-medium text-gray-700">
                    {(source.score * 100).toFixed(0)}%
                  </span>
                </>
              ) : (
                <span className="font-medium text-gray-400">N/A</span>
              )}
            </div>

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
