/**
 * SourceCardsScroll Component
 * Sprint 15 Feature 15.4: Horizontal scrolling source cards
 *
 * Displays retrieved sources in horizontal scroll container
 */

import type { Source } from '../../types/chat';
import { SourceCard } from './SourceCard';

interface SourceCardsScrollProps {
  sources: Source[];
}

export function SourceCardsScroll({ sources }: SourceCardsScrollProps) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700 flex items-center space-x-2">
        <span>📚</span>
        <span>Quellen ({sources.length})</span>
      </h3>
      <div className="flex space-x-4 overflow-x-auto pb-4 scrollbar-hide scroll-smooth">
        {sources.map((source, index) => (
          <SourceCard key={`${source.document_id}-${index}`} source={source} index={index + 1} />
        ))}
      </div>
    </div>
  );
}
