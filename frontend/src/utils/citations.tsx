/**
 * Citation Parsing Utilities
 * Sprint 28 Feature 28.2: Parse and render inline citations
 *
 * Converts [1], [2], etc. in markdown text to Citation components
 */

import { Fragment, type ReactNode } from 'react';
import { Citation } from '../components/chat/Citation';
import type { Source } from '../types/chat';

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
