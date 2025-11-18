/**
 * SourceCardsScroll Component
 * Sprint 15 Feature 15.4: Horizontal scrolling source cards
 * Sprint 28 Feature 28.2: Support scrolling to specific source by ID
 *
 * Displays retrieved sources in horizontal scroll container
 */

import { useRef, useImperativeHandle, forwardRef } from 'react';
import type { Source } from '../../types/chat';
import { SourceCard } from './SourceCard';

interface SourceCardsScrollProps {
  sources: Source[];
}

export interface SourceCardsScrollRef {
  scrollToSource: (sourceId: string) => void;
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

          // Add a highlight animation
          cardElement.classList.add('ring-2', 'ring-blue-500', 'ring-offset-2');
          setTimeout(() => {
            cardElement.classList.remove('ring-2', 'ring-blue-500', 'ring-offset-2');
          }, 2000);
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
          {sources.map((source, index) => {
            const sourceId = source.document_id || `source-${index + 1}`;
            return (
              <div
                key={`${source.document_id}-${index}`}
                ref={(el) => {
                  if (el) {
                    cardRefs.current.set(sourceId, el);
                  } else {
                    cardRefs.current.delete(sourceId);
                  }
                }}
                className="transition-all duration-300"
              >
                <SourceCard source={source} index={index + 1} />
              </div>
            );
          })}
        </div>
      </div>
    );
  }
);
