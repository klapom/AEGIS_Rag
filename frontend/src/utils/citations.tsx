/**
 * Citation Parsing Utilities
 * Sprint 28 Feature 28.2: Parse and render inline citations
 * Sprint 32 Fix: Pre-process markdown to handle citations before react-markdown
 * Sprint 62 Feature 62.4: Section-aware citations with metadata extraction
 *
 * Converts [1], [2], etc. in markdown text to Citation components
 */

import { Fragment, type ReactNode } from 'react';
import { Citation } from '../components/chat/Citation';
import type { Source } from '../types/chat';
import {
  extractSectionMetadata,
  getDocumentType,
  type SectionMetadata,
  type DocumentType,
} from '../types/section';

// Special marker for citation placeholders that won't conflict with markdown
// Using CITE_MARK_X format to avoid markdown interpretation of underscores
const CITATION_MARKER_PREFIX = 'CITEMARK';
const CITATION_MARKER_SUFFIX = 'ENDCITE';

/**
 * Parse markdown text and replace citation markers [1], [2], etc.
 * with Citation components
 *
 * @param text - Markdown text with citation markers like [1]
 * @param sources - Array of sources to link citations to
 * @param onClickScrollTo - Callback when citation is clicked
 * @returns React nodes with Citation components embedded
 */
export function parseCitationsInText(
  text: string,
  sources: Source[],
  onClickScrollTo: (sourceId: string) => void
): ReactNode[] {
  if (!text || sources.length === 0) {
    return [text];
  }

  // Regex to match citation markers like [1], [2], [123]
  // Must be standalone (not part of markdown link syntax)
  const citationRegex = /\[(\d+)\]/g;

  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = citationRegex.exec(text)) !== null) {
    const fullMatch = match[0]; // e.g., "[1]"
    const citationNumber = parseInt(match[1], 10); // e.g., 1
    const matchIndex = match.index;

    // Check if this is part of a markdown link by looking for preceding ]( or )[
    const before = text.slice(Math.max(0, matchIndex - 2), matchIndex);
    const after = text.slice(matchIndex + fullMatch.length, matchIndex + fullMatch.length + 2);
    const isMarkdownLink = before === '](' || after === '](' || before === ')[';

    if (isMarkdownLink) {
      // Skip this match - it's part of markdown syntax
      continue;
    }

    // Add text before the citation
    if (matchIndex > lastIndex) {
      parts.push(
        <Fragment key={`text-${key++}`}>
          {text.slice(lastIndex, matchIndex)}
        </Fragment>
      );
    }

    // Check if citation index is valid (1-indexed)
    const sourceIndex = citationNumber - 1;
    if (sourceIndex >= 0 && sourceIndex < sources.length) {
      const source = sources[sourceIndex];
      parts.push(
        <Citation
          key={`citation-${key++}`}
          sourceIndex={citationNumber}
          source={source}
          onClickScrollTo={onClickScrollTo}
        />
      );
    } else {
      // Invalid citation number - render as plain text
      parts.push(
        <Fragment key={`text-${key++}`}>
          {fullMatch}
        </Fragment>
      );
    }

    lastIndex = matchIndex + fullMatch.length;
  }

  // Add remaining text after last citation
  if (lastIndex < text.length) {
    parts.push(
      <Fragment key={`text-${key++}`}>
        {text.slice(lastIndex)}
      </Fragment>
    );
  }

  return parts.length > 0 ? parts : [text];
}

/**
 * Custom text renderer for react-markdown that processes citations
 * Note: react-markdown's text component receives string children directly
 */
export function createCitationTextRenderer(
  sources: Source[],
  onClickScrollTo: (sourceId: string) => void
) {
  // React-markdown passes children as the string value directly
  return function renderTextWithCitations(children: string): ReactNode {
    if (typeof children !== 'string') {
      return children;
    }
    return <>{parseCitationsInText(children, sources, onClickScrollTo)}</>;
  };
}

/**
 * Pre-process markdown to replace [N] citations with special markers.
 * This ensures citations are preserved through react-markdown parsing.
 * Sprint 32 Fix: Pre-processing approach for react-markdown v10+
 *
 * @param markdown - The markdown text with [N] citation markers
 * @returns Modified markdown with citation markers replaced by placeholders
 */
export function preprocessMarkdownCitations(markdown: string): string {
  if (!markdown) return markdown;

  // Replace [N] patterns with special markers
  // Avoid replacing markdown link syntax like [text](url) or [text][ref]
  const result = markdown.replace(
    /\[(\d+)\](?!\(|\[)/g,
    (_match, num) => `${CITATION_MARKER_PREFIX}${num}${CITATION_MARKER_SUFFIX}`
  );

  // Log if any replacements were made
  if (result !== markdown) {
    console.log('[Preprocess] Replaced citations. Before:', markdown.substring(0, 100));
    console.log('[Preprocess] After:', result.substring(0, 100));
  }

  return result;
}

/**
 * Check if a string contains citation markers
 */
export function containsCitationMarkers(text: string): boolean {
  return text.includes(CITATION_MARKER_PREFIX);
}

/**
 * Replace citation markers with actual Citation components.
 * Use this to post-process react-markdown output.
 *
 * @param text - Text containing citation markers
 * @param sources - Array of sources for citations
 * @param onClickScrollTo - Callback when citation is clicked
 * @returns React nodes with Citation components
 */
export function replaceCitationMarkers(
  text: string,
  sources: Source[],
  onClickScrollTo: (sourceId: string) => void
): ReactNode[] {
  if (!text || sources.length === 0) {
    // If no sources, replace markers with original [N] format
    return [text.replace(
      new RegExp(`${CITATION_MARKER_PREFIX}(\\d+)${CITATION_MARKER_SUFFIX}`, 'g'),
      '[$1]'
    )];
  }

  const markerRegex = new RegExp(
    `${CITATION_MARKER_PREFIX}(\\d+)${CITATION_MARKER_SUFFIX}`,
    'g'
  );

  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = markerRegex.exec(text)) !== null) {
    const fullMatch = match[0];
    const citationNumber = parseInt(match[1], 10);
    const matchIndex = match.index;

    // Add text before the citation
    if (matchIndex > lastIndex) {
      parts.push(
        <Fragment key={`text-${key++}`}>
          {text.slice(lastIndex, matchIndex)}
        </Fragment>
      );
    }

    // Check if citation index is valid (1-indexed)
    const sourceIndex = citationNumber - 1;
    if (sourceIndex >= 0 && sourceIndex < sources.length) {
      const source = sources[sourceIndex];
      parts.push(
        <Citation
          key={`citation-${key++}`}
          sourceIndex={citationNumber}
          source={source}
          onClickScrollTo={onClickScrollTo}
        />
      );
    } else {
      // Invalid citation number - render as plain text
      parts.push(
        <Fragment key={`text-${key++}`}>
          [{citationNumber}]
        </Fragment>
      );
    }

    lastIndex = matchIndex + fullMatch.length;
  }

  // Add remaining text after last citation
  if (lastIndex < text.length) {
    parts.push(
      <Fragment key={`text-${key++}`}>
        {text.slice(lastIndex)}
      </Fragment>
    );
  }

  return parts.length > 0 ? parts : [text];
}

/**
 * Create a text renderer that handles citation markers from pre-processed markdown.
 * Sprint 32 Fix: Use this with react-markdown components prop.
 */
export function createMarkerTextRenderer(
  sources: Source[],
  onClickScrollTo: (sourceId: string) => void
) {
  return function renderMarkersAsComponents(text: string): ReactNode {
    if (typeof text !== 'string') {
      console.log('[TextRenderer] Not a string:', typeof text);
      return text;
    }
    if (!containsCitationMarkers(text)) {
      // Only log if text is non-trivial
      if (text.length > 20) {
        console.log('[TextRenderer] No markers in:', text.substring(0, 50));
      }
      return text;
    }
    console.log('[TextRenderer] Found markers in:', text.substring(0, 100));
    console.log('[TextRenderer] sources.length:', sources.length);
    return <>{replaceCitationMarkers(text, sources, onClickScrollTo)}</>;
  };
}

/**
 * Sprint 62.4: Extract section metadata from a source
 * Handles both direct section field and legacy metadata fields
 */
export function getSourceSectionMetadata(source: Source): SectionMetadata | null {
  return extractSectionMetadata(source);
}

/**
 * Sprint 62.4: Get document type from source
 */
export function getSourceDocumentType(source: Source): DocumentType {
  // Check direct document_type field first
  if (source.document_type) {
    return source.document_type;
  }
  return getDocumentType(source);
}

/**
 * Sprint 62.4: Check if source has section metadata
 */
export function hasSourceSectionMetadata(source: Source): boolean {
  const section = getSourceSectionMetadata(source);
  return section !== null && (
    !!section.section_id ||
    !!section.section_title ||
    !!section.section_number ||
    (section.section_level !== undefined && section.section_level > 0)
  );
}

/**
 * Sprint 62.4: Enrich sources with extracted section metadata
 * This normalizes section data from various backend formats
 */
export function enrichSourcesWithSectionMetadata(sources: Source[]): Source[] {
  return sources.map((source) => {
    const section = getSourceSectionMetadata(source);
    const documentType = getSourceDocumentType(source);

    // Return enriched source with normalized section data
    return {
      ...source,
      section: section || source.section,
      document_type: documentType,
    };
  });
}
