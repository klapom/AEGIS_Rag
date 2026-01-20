/**
 * SourceCardsScroll Component
 * Sprint 15 Feature 15.4: Horizontal scrolling source cards
 * Sprint 28 Feature 28.2: Support scrolling to specific source by ID
 * Sprint 51 Fix: Support explicit citation numbers for filtered sources
 *
 * Displays retrieved sources in horizontal scroll container
 */

import { useRef, useImperativeHandle, forwardRef } from 'react';
import type { Source } from '../../types/chat';
import { SourceCard } from './SourceCard';

/**
 * Source with optional explicit citation number.
 * Sprint 51 Fix: When sources are filtered to only cited ones,
 * we need to preserve the original citation numbers.
 */
interface SourceWithCitation {
  source: Source;
  citationNumber: number;
}

interface SourceCardsScrollProps {
  /** Sources to display - can be plain sources or sources with citation numbers */
  sources: Source[] | SourceWithCitation[];
}

export interface SourceCardsScrollRef {
  scrollToSource: (sourceId: string) => void;
}

/**
 * Type guard to check if sources are SourceWithCitation format.
 */
function isSourceWithCitation(item: Source | SourceWithCitation): item is SourceWithCitation {
  return 'source' in item && 'citationNumber' in item;
}

export const SourceCardsScroll = forwardRef<SourceCardsScrollRef, SourceCardsScrollProps>(
  ({ sources }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

    useImperativeHandle(ref, () => ({
      scrollToSource: (sourceId: string) => {
        const cardElement = cardRefs.current.get(sourceId);
        if (cardElement && containerRef.current) {
          // Scroll the card into view with smooth animation
          cardElement.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
            inline: 'center'
          });

          // Add a highlight pulse animation with glow effect
          // Sprint 116 Feature 116.4: Enhanced citation linking with pulse animation
          cardElement.classList.add('citation-highlight-pulse');

          // Remove highlight after 3 seconds
          setTimeout(() => {
            cardElement.classList.remove('citation-highlight-pulse');
          }, 3000);
        }
      }
    }));

    if (sources.length === 0) {
      return null;
    }

    return (
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center space-x-2">
          <span>📚</span>
          <span>Quellen ({sources.length})</span>
        </h3>
        <div
          ref={containerRef}
          className="flex space-x-4 overflow-x-auto pb-4 scrollbar-hide scroll-smooth"
        >
          {sources.map((item, index) => {
            // Sprint 51 Fix: Support both plain sources and sources with citation numbers
            const source = isSourceWithCitation(item) ? item.source : item;
            const citationNumber = isSourceWithCitation(item) ? item.citationNumber : index + 1;
            const sourceId = source.document_id || `source-${citationNumber}`;

            return (
              <div
                key={`${source.document_id}-${citationNumber}`}
                ref={(el) => {
                  if (el) {
                    cardRefs.current.set(sourceId, el);
                  } else {
                    cardRefs.current.delete(sourceId);
                  }
                }}
                className="transition-all duration-300"
              >
                <SourceCard source={source} index={citationNumber} />
              </div>
            );
          })}
        </div>
      </div>
    );
  }
);
