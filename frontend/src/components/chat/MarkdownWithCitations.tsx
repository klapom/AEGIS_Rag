/**
 * MarkdownWithCitations Component
 * Sprint 32 Fix: Reliable citation rendering with react-markdown v10+
 *
 * This component renders markdown content with inline citations.
 * It uses a two-pass approach:
 * 1. First, parse the text to find [N] citation patterns
 * 2. Then, render markdown segments with Citation components inserted
 */

import { Fragment } from 'react';
import ReactMarkdown from 'react-markdown';
import { Citation } from './Citation';
import type { Source } from '../../types/chat';

interface MarkdownWithCitationsProps {
  content: string;
  sources: Source[];
  onCitationClick: (sourceId: string) => void;
}

/**
 * Parse text to extract citation markers and split into segments
 * Returns array of { type: 'text' | 'citation', content: string | number }
 */
function parseTextWithCitations(text: string): Array<{ type: 'text' | 'citation'; content: string | number }> {
  const segments: Array<{ type: 'text' | 'citation'; content: string | number }> = [];
  const citationRegex = /\[(\d+)\](?!\()/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = citationRegex.exec(text)) !== null) {
    // Add text before the citation
    if (match.index > lastIndex) {
      segments.push({
        type: 'text',
        content: text.slice(lastIndex, match.index)
      });
    }

    // Add the citation
    segments.push({
      type: 'citation',
      content: parseInt(match[1], 10)
    });

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    segments.push({
      type: 'text',
      content: text.slice(lastIndex)
    });
  }

  return segments;
}

/**
 * Render markdown segments with citations inline
 */
export function MarkdownWithCitations({ content, sources, onCitationClick }: MarkdownWithCitationsProps) {
  // DEBUG: Log inputs to understand what we're receiving
  console.log('[MarkdownWithCitations] RENDER:', {
    contentLength: content?.length || 0,
    contentPreview: content?.substring(0, 200) || 'empty',
    sourcesCount: sources?.length || 0,
    sourcesPreview: sources?.slice(0, 2).map(s => ({
      text: s.text?.substring(0, 50),
      title: s.title,
      source: s.source,
      document_id: s.document_id
    }))
  });

  // If no content or no citations, render plain markdown
  if (!content) {
    console.log('[MarkdownWithCitations] Early return: no content');
    return null;
  }

  // Check if content has any citations
  const hasCitations = /\[\d+\](?!\()/.test(content);
  console.log('[MarkdownWithCitations] hasCitations:', hasCitations, 'sources.length:', sources?.length || 0);

  if (!hasCitations || sources.length === 0) {
    // No citations or no sources - render plain markdown
    console.log('[MarkdownWithCitations] Early return: hasCitations=', hasCitations, 'sources.length=', sources?.length || 0);
    return <ReactMarkdown>{content}</ReactMarkdown>;
  }

  // Parse content by paragraphs to maintain markdown structure
  const paragraphs = content.split(/\n\n+/);

  return (
    <>
      {paragraphs.map((paragraph, pIndex) => {
        const trimmed = paragraph.trim();
        if (!trimmed) return null;

        // Check if this paragraph has citations
        const paragraphHasCitations = /\[\d+\](?!\()/.test(trimmed);

        if (!paragraphHasCitations) {
          // No citations - render as plain markdown
          return (
            <ReactMarkdown key={`p-${pIndex}`}>
              {trimmed}
            </ReactMarkdown>
          );
        }

        // Parse the paragraph for citations
        const segments = parseTextWithCitations(trimmed);

        // Check if this looks like a list item
        const isListItem = /^[-*]\s/.test(trimmed) || /^\d+\.\s/.test(trimmed);

        // Render segments with citations inline
        const renderedContent = segments.map((segment, sIndex) => {
          if (segment.type === 'citation') {
            const citationNum = segment.content as number;
            const sourceIndex = citationNum - 1;

            if (sourceIndex >= 0 && sourceIndex < sources.length) {
              const source = sources[sourceIndex];
              return (
                <Citation
                  key={`citation-${pIndex}-${sIndex}`}
                  sourceIndex={citationNum}
                  source={source}
                  onClickScrollTo={onCitationClick}
                />
              );
            }
            // Invalid citation number - render as text
            return <Fragment key={`text-${pIndex}-${sIndex}`}>[{citationNum}]</Fragment>;
          }

          // Text segment - render inline markdown (bold, italic, etc.)
          // For simplicity, we strip list markers since we handle the whole paragraph
          let textContent = segment.content as string;
          if (sIndex === 0 && isListItem) {
            textContent = textContent.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '');
          }

          // Use ReactMarkdown for inline formatting only
          return (
            <ReactMarkdown
              key={`md-${pIndex}-${sIndex}`}
              components={{
                // Force inline rendering (no paragraph wrapping)
                p: ({ children }) => <>{children}</>,
              }}
            >
              {textContent}
            </ReactMarkdown>
          );
        });

        // Wrap in appropriate element
        if (isListItem) {
          return (
            <ul key={`list-${pIndex}`} className="list-disc list-inside">
              <li>{renderedContent}</li>
            </ul>
          );
        }

        return (
          <p key={`para-${pIndex}`}>
            {renderedContent}
          </p>
        );
      })}
    </>
  );
}

export default MarkdownWithCitations;
