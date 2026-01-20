/**
 * SourceCard Component
 * Sprint 15 Feature 15.4: Individual source card display
 * Sprint 19 Feature: Source click with chunk preview modal
 * Sprint 52 Feature: Replaced modal with inline expandable details
 * Sprint 62 Feature 62.4: Section-aware citations with section badges
 *
 * Displays metadata and preview of a single source document
 * Click expands to show full chunk context and search type
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, File, FileCode, BookOpen, Hash } from 'lucide-react';
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

interface SourceCardProps {
  source: Source;
  index: number;
}

/**
 * Get icon for search/retrieval type
 */
function getSearchTypeIcon(searchType: string): string {
  switch (searchType?.toLowerCase()) {
    case 'vector':
    case 'embedding':
      return '🔍';
    case 'bm25':
    case 'keyword':
      return '📝';
    case 'graph':
      return '🕸️';
    case 'memory':
      return '💭';
    default:
      return '📄';
  }
}

/**
 * Get display name for search type
 */
function getSearchTypeName(searchType: string): string {
  switch (searchType?.toLowerCase()) {
    case 'vector':
      return 'Vector/Embedding';
    case 'bm25':
      return 'BM25/Keyword';
    case 'graph':
      return 'Graph';
    case 'memory':
      return 'Memory';
    default:
      return searchType || 'Unbekannt';
  }
}

/**
 * Get color class for search type badge
 */
function getSearchTypeColor(searchType: string): string {
  switch (searchType?.toLowerCase()) {
    case 'vector':
    case 'embedding':
      return 'bg-blue-100 text-blue-700 border-blue-200';
    case 'bm25':
    case 'keyword':
      return 'bg-amber-100 text-amber-700 border-amber-200';
    case 'graph':
      return 'bg-purple-100 text-purple-700 border-purple-200';
    case 'memory':
      return 'bg-green-100 text-green-700 border-green-200';
    default:
      return 'bg-gray-100 text-gray-700 border-gray-200';
  }
}

/**
 * Sprint 62.4: Get icon component for document type
 */
function getDocumentTypeIcon(docType: DocumentType): React.ReactNode {
  const iconClass = 'w-3.5 h-3.5';

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
function getDocumentTypeBadgeColor(docType: DocumentType): string {
  switch (docType) {
    case 'pdf':
      return 'bg-red-100 text-red-700 border-red-200';
    case 'docx':
      return 'bg-blue-100 text-blue-700 border-blue-200';
    case 'md':
      return 'bg-purple-100 text-purple-700 border-purple-200';
    case 'txt':
      return 'bg-gray-100 text-gray-700 border-gray-200';
    case 'html':
      return 'bg-orange-100 text-orange-700 border-orange-200';
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200';
  }
}

/**
 * Sprint 62.4: Get display name for document type
 */
function getDocumentTypeDisplayName(docType: DocumentType): string {
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
      return 'Doc';
  }
}

export function SourceCard({ source, index }: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Sprint 52: Get search type from metadata
  const searchType = source.metadata?.search_type as string | undefined;

  // Sprint 92: Get graph hops from metadata (if graph search was used)
  const graphHops = source.metadata?.graph_hops_used as number | undefined;

  // Sprint 62.4: Extract section metadata and document type
  const sectionMetadata = extractSectionMetadata(source);
  const docType = source.document_type || getDocumentType(source);
  const hasSection = sectionMetadata !== null && (
    sectionMetadata.section_title ||
    sectionMetadata.section_number ||
    sectionMetadata.section_id
  );
  const sectionDisplay = hasSection ? formatSectionDisplay(sectionMetadata!) : null;
  const sectionPath = hasSection ? formatSectionPath(sectionMetadata!) : null;
  const pageNumber = sectionMetadata?.page_number;

  // Sprint 19: Extract readable document name from metadata
  // Sprint 32 Fix: Check title/source from citation_map first
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
      const metadataSource = source.metadata.source as string;
      const filename = metadataSource.split(/[/\\]/).pop() || metadataSource;
      return filename.replace(/\.[^/.]+$/, '');
    }
    // Check document_id as fallback
    if (source.document_id && source.document_id !== 'Document') {
      return source.document_id;
    }
    return 'Unbekanntes Dokument';
  };

  // Get the full context text
  const fullText = cleanTextForDisplay(extractContextText(source.context || source.text)) || 'Kein Kontext verfügbar';

  // Get source file path
  const sourcePath = source.source || (source.metadata?.source as string | undefined) || source.title;

  return (
    <div
      className="bg-white border border-gray-200 rounded-lg overflow-hidden transition-all duration-200 hover:border-primary/50"
      data-source-id={source.document_id || `source-${index}`}
    >
      {/* Clickable Header */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        data-testid="source-card-header"
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Index Badge */}
          <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-sm font-bold text-primary">{index}</span>
          </div>

          {/* Document Name and Section Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <div className="text-sm font-semibold text-gray-900 truncate" title={getDocumentName()}>
                {getDocumentName()}
              </div>
              {/* Sprint 62.4: Document Type Badge */}
              {docType !== 'unknown' && (
                <span
                  className={`hidden sm:flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium rounded border flex-shrink-0 ${getDocumentTypeBadgeColor(docType)}`}
                  title={`Dokumenttyp: ${getDocumentTypeDisplayName(docType)}`}
                  data-testid="document-type-badge"
                >
                  {getDocumentTypeIcon(docType)}
                  <span className="hidden md:inline">{getDocumentTypeDisplayName(docType)}</span>
                </span>
              )}
            </div>
            {/* Sprint 62.4: Section Badge - Shown below document name on mobile, inline on desktop */}
            {hasSection && (
              <div
                className="flex items-center gap-1.5 mt-1 text-xs text-indigo-600"
                title={sectionPath || undefined}
                data-testid="section-badge"
              >
                <Hash className="w-3 h-3 text-indigo-500 flex-shrink-0" />
                <span className="truncate">{sectionDisplay}</span>
                {sectionMetadata?.section_level && (
                  <span className="text-indigo-400 flex-shrink-0">(L{sectionMetadata.section_level})</span>
                )}
              </div>
            )}
          </div>

          {/* Search Type Badge - Sprint 52 */}
          {searchType && (
            <span
              className={`px-2 py-1 text-xs font-medium rounded-md border flex items-center gap-1 flex-shrink-0 ${getSearchTypeColor(searchType)}`}
              title={`Suchmethode: ${getSearchTypeName(searchType)}`}
            >
              <span>{getSearchTypeIcon(searchType)}</span>
              <span className="hidden sm:inline">{getSearchTypeName(searchType)}</span>
            </span>
          )}

          {/* Graph Hops Badge - Sprint 92 */}
          {graphHops !== undefined && graphHops > 0 && searchType === 'graph' && (
            <span
              className="px-2 py-1 text-xs font-medium rounded-md border bg-indigo-100 text-indigo-700 border-indigo-200 flex items-center gap-1 flex-shrink-0"
              title={`Graph-Traversierung: ${graphHops} Hop${graphHops !== 1 ? 's' : ''}`}
              data-testid="graph-hops-badge"
            >
              <span>↔️</span>
              <span>{graphHops}-hop</span>
            </span>
          )}

          {/* Score Badge */}
          {source.score != null && source.score > 0 && (
            <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded-md flex-shrink-0">
              {(source.score * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {/* Expand/Collapse Icon */}
        <div className="ml-2 text-gray-400">
          {isExpanded ? (
            <ChevronDown className="w-5 h-5" />
          ) : (
            <ChevronRight className="w-5 h-5" />
          )}
        </div>
      </div>

      {/* Expandable Content - Sprint 52 */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          {/* Full Chunk Content */}
          <div className="mt-3">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Chunk-Inhalt
            </h4>
            <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-800 leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto">
              {fullText}
            </div>
          </div>

          {/* Metadata Section */}
          <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
            {/* Source Path */}
            {sourcePath && (
              <div className="col-span-2">
                <span className="text-gray-500">Quelle:</span>
                <span className="ml-2 text-gray-700 break-all">{sourcePath}</span>
              </div>
            )}

            {/* Sprint 62.4: Section Path (full hierarchy) */}
            {hasSection && sectionPath && (
              <div className="col-span-2" data-testid="section-path">
                <span className="text-gray-500">Abschnitt:</span>
                <span className="ml-2 text-indigo-600">{sectionPath}</span>
              </div>
            )}

            {/* Sprint 62.4: Document Type */}
            {docType !== 'unknown' && (
              <div data-testid="document-type-info">
                <span className="text-gray-500">Dokumenttyp:</span>
                <span className="ml-2 text-gray-700">{getDocumentTypeDisplayName(docType)}</span>
              </div>
            )}

            {/* Sprint 62.4: Page Number (for PDFs) */}
            {pageNumber && (
              <div>
                <span className="text-gray-500">Seite:</span>
                <span className="ml-2 text-gray-700">{pageNumber}</span>
              </div>
            )}

            {/* Search Type */}
            {searchType && (
              <div>
                <span className="text-gray-500">Suchmethode:</span>
                <span className="ml-2 text-gray-700">{getSearchTypeName(searchType)}</span>
              </div>
            )}

            {/* Graph Hops - Sprint 92 */}
            {graphHops !== undefined && graphHops > 0 && searchType === 'graph' && (
              <div data-testid="graph-hops-info">
                <span className="text-gray-500">Graph-Hops:</span>
                <span className="ml-2 text-indigo-600 font-medium">
                  {graphHops} Hop{graphHops !== 1 ? 's' : ''}
                </span>
              </div>
            )}

            {/* Rank */}
            {source.metadata?.rank != null && (
              <div>
                <span className="text-gray-500">Rang:</span>
                <span className="ml-2 text-gray-700">#{source.metadata.rank as number}</span>
              </div>
            )}

            {/* Document ID */}
            {source.document_id && (
              <div>
                <span className="text-gray-500">Doc-ID:</span>
                <span className="ml-2 text-gray-700 font-mono text-xs">{source.document_id}</span>
              </div>
            )}

            {/* Namespace */}
            {source.metadata?.namespace && (
              <div>
                <span className="text-gray-500">Namespace:</span>
                <span className="ml-2 text-gray-700">{source.metadata.namespace as string}</span>
              </div>
            )}

            {/* Chunk Index */}
            {source.chunk_index !== undefined && (
              <div>
                <span className="text-gray-500">Chunk:</span>
                <span className="ml-2 text-gray-700">
                  {source.chunk_index}
                  {source.total_chunks && ` / ${source.total_chunks}`}
                </span>
              </div>
            )}
          </div>

          {/* Entity Tags */}
          {source.entities && source.entities.length > 0 && (
            <div className="mt-3">
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Entitäten ({source.entities.length})
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {source.entities.map((entity, i) => (
                  <EntityTag key={i} entity={entity} />
                ))}
              </div>
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
