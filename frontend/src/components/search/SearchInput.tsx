/**
 * SearchInput Component
 * Sprint 15 Feature 15.3: Large search input with mode selector (ADR-021)
 *
 * Perplexity-inspired search input with:
 * - Large centered input field
 * - Mode selector chips (Hybrid, Vector, Graph, Memory)
 * - Input icons and submit button
 * - Keyboard shortcuts (Enter to submit)
 */

import { useState, useRef, useEffect } from 'react';

export type SearchMode = 'hybrid' | 'vector' | 'graph' | 'memory';

interface SearchInputProps {
  onSubmit: (query: string, mode: SearchMode) => void;
  placeholder?: string;
  autoFocus?: boolean;
}

export function SearchInput({
  onSubmit,
  placeholder = "Fragen Sie alles über Ihre Dokumente...",
  autoFocus = true
}: SearchInputProps) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<SearchMode>('hybrid');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  const handleSubmit = () => {
    const trimmedQuery = query.trim();
    if (trimmedQuery) {
      onSubmit(trimmedQuery, mode);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="max-w-3xl mx-auto w-full space-y-6">
      {/* Search Input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full h-16 px-6 pr-20 text-lg border-2 border-gray-300 rounded-2xl
                     focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20
                     placeholder-gray-400 transition-all duration-200
                     hover:border-gray-400"
        />

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={!query.trim()}
          data-testid="search-submit-button" // TD-38: Add testid for E2E tests
          aria-label="Suche starten"
          className="absolute right-3 top-1/2 -translate-y-1/2
                     w-10 h-10 flex items-center justify-center
                     bg-primary hover:bg-primary-hover
                     disabled:bg-gray-300 disabled:cursor-not-allowed
                     text-white rounded-xl transition-all duration-200
                     transform hover:scale-105 active:scale-95"
          title="Suche starten (Enter)"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 12h14M12 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>

      {/* Mode Selector Chips */}
      <div className="flex justify-center space-x-3">
        <ModeChip
          active={mode === 'hybrid'}
          onClick={() => setMode('hybrid')}
          icon="🔀"
          label="Hybrid"
          description="Vector + Graph + BM25"
        />
        <ModeChip
          active={mode === 'vector'}
          onClick={() => setMode('vector')}
          icon="🔍"
          label="Vector"
          description="Semantic similarity"
        />
        <ModeChip
          active={mode === 'graph'}
          onClick={() => setMode('graph')}
          icon="🕸️"
          label="Graph"
          description="Entity relationships"
        />
        <ModeChip
          active={mode === 'memory'}
          onClick={() => setMode('memory')}
          icon="💭"
          label="Memory"
          description="Conversation history"
        />
      </div>

      {/* Help Text */}
      <div className="text-center text-sm text-gray-500">
        <kbd className="px-2 py-1 text-xs bg-gray-100 border border-gray-300 rounded">
          Enter
        </kbd>
        {' '}zum Senden
      </div>
    </div>
  );
}

interface ModeChipProps {
  active: boolean;
  onClick: () => void;
  icon: string;
  label: string;
  description: string;
}

function ModeChip({ active, onClick, icon, label, description }: ModeChipProps) {
  return (
    <button
      onClick={onClick}
      title={description}
      data-testid={`mode-${label.toLowerCase()}-button`} // TD-38: Add testid for E2E tests
      aria-label={`${label} Mode`} // TD-38: Improved accessibility
      role="button"
      aria-pressed={active}
      className={`
        px-5 py-2.5 rounded-full border-2
        flex items-center space-x-2
        transition-all duration-200
        transform hover:scale-105 active:scale-95
        ${active
          ? 'bg-primary text-white border-primary shadow-md'
          : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400 hover:shadow-sm'
        }
      `}
    >
      <span className="text-lg" role="img" aria-label={label}>
        {icon}
      </span>
      <span className="font-medium text-sm">{label}</span>
    </button>
  );
}
