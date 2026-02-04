/**
 * SearchInput Component
 * Sprint 15 Feature 15.3: Large search input with mode selector (ADR-021)
 * Sprint 42: Added namespace/project selection for search filtering
 * Sprint 52: ChatGPT-style floating input with auto-grow textarea
 * Sprint 63 Feature 63.8: Added Research Mode toggle
 * Sprint 79 Feature 79.6: Added Graph Expansion Settings toggle
 *
 * ChatGPT-inspired search input with:
 * - Auto-growing textarea that expands with content
 * - Inline project selector chip
 * - Fixed Hybrid mode (mode selector removed)
 * - Clean, minimal design
 * - Research Mode toggle (Sprint 63)
 * - Graph Expansion settings (Sprint 79)
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { NamespaceSelector } from './NamespaceSelector';
import { ResearchModeToggleCompact } from '../research';
import {
  GraphExpansionSettingsCompact,
  loadGraphExpansionConfig,
} from '../settings';
import type { GraphExpansionConfig } from '../../types/settings';

export type SearchMode = 'hybrid' | 'vector' | 'graph' | 'memory' | 'sparse';

interface SearchInputProps {
  onSubmit: (query: string, mode: SearchMode, namespaces: string[], graphExpansionConfig?: GraphExpansionConfig) => void;
  placeholder?: string;
  autoFocus?: boolean;
  /** Sprint 63: Whether Research Mode is enabled */
  isResearchMode?: boolean;
  /** Sprint 63: Callback to toggle Research Mode */
  onResearchModeToggle?: () => void;
  /** Sprint 63: Whether Research Mode toggle should be shown */
  showResearchToggle?: boolean;
  /** Sprint 79: Whether Graph Expansion settings should be shown */
  showGraphExpansionToggle?: boolean;
  /** Sprint 123.11: Initial mode (from URL or parent) */
  initialMode?: SearchMode;
}

export function SearchInput({
  onSubmit,
  placeholder = "Fragen Sie alles über Ihre Dokumente...",
  autoFocus = true,
  isResearchMode = false,
  onResearchModeToggle,
  showResearchToggle = true,
  showGraphExpansionToggle = true,
  initialMode = 'hybrid',
}: SearchInputProps) {
  const [query, setQuery] = useState('');
  // Sprint 123.11: Mode selector support (replaces hardcoded 'hybrid')
  const [mode, setMode] = useState<SearchMode>(initialMode);
  const [selectedNamespaces, setSelectedNamespaces] = useState<string[]>([]);

  // Sprint 123.11: Sync mode state when initialMode prop changes (e.g., from URL navigation)
  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sprint 79 Feature 79.6: Graph expansion config state
  const [graphExpansionConfig, setGraphExpansionConfig] = useState<GraphExpansionConfig>(
    () => loadGraphExpansionConfig()
  );

  // Auto-resize textarea based on content
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto';
      // Set to scrollHeight but cap at max height (200px ~ 8 lines)
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
    }
  }, []);

  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  // Adjust height whenever query changes
  useEffect(() => {
    adjustTextareaHeight();
  }, [query, adjustTextareaHeight]);

  const handleSubmit = () => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      return;
    }
    // Sprint 79 Feature 79.6: Pass graph expansion config with submit
    onSubmit(trimmedQuery, mode, selectedNamespaces, graphExpansionConfig);
    setQuery('');
    // Reset textarea height after clearing
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full space-y-3 overflow-visible">
      {/* Sprint 123.11: Mode Selector */}
      <div className="flex items-center gap-2" data-testid="search-mode-selector">
        {(['vector', 'sparse', 'hybrid', 'graph', 'memory'] as const).map((modeOption) => (
          <button
            key={modeOption}
            type="button"
            onClick={() => setMode(modeOption)}
            data-testid={`mode-${modeOption}`}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-all duration-200 ${
              mode === modeOption
                ? 'bg-primary text-white shadow-sm'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {modeOption === 'vector' && '🔍 Vector'}
            {modeOption === 'sparse' && '📝 Sparse'}
            {modeOption === 'hybrid' && '⚡ Hybrid'}
            {modeOption === 'graph' && '🕸️ Graph'}
            {modeOption === 'memory' && '💭 Memory'}
          </button>
        ))}
      </div>

      {/* Main input container with rounded border */}
      <div className="relative bg-white border border-gray-300 rounded-2xl shadow-sm
                      focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20
                      transition-all duration-200 hover:border-gray-400">
        {/* Textarea - auto-grows with content */}
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          data-testid="message-input"
          className="w-full px-4 py-3 pr-14 text-base bg-transparent border-none
                     focus:outline-none focus:ring-0
                     placeholder-gray-400 resize-none
                     min-h-[48px] max-h-[200px] overflow-y-auto"
          style={{ height: 'auto' }}
        />

        {/* Submit Button - positioned at bottom right */}
        <button
          onClick={handleSubmit}
          disabled={!query.trim()}
          data-testid="send-button"
          aria-label="Suche starten"
          className="absolute right-2 bottom-2
                     w-9 h-9 flex items-center justify-center
                     bg-primary hover:bg-primary-hover
                     disabled:bg-gray-200 disabled:cursor-not-allowed
                     text-white rounded-lg transition-all duration-200
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

      {/* Bottom row: Project selector, Graph Expansion, and Research toggle - overflow-visible for dropdown */}
      <div className="flex items-center justify-between overflow-visible">
        {/* Left side: Project Selector, Graph Expansion, and Research Toggle */}
        <div className="flex items-center gap-2">
          {/* Compact Project Selector */}
          <NamespaceSelector
            selectedNamespaces={selectedNamespaces}
            onSelectionChange={setSelectedNamespaces}
            compact={true}
          />

          {/* Sprint 79 Feature 79.6: Graph Expansion Settings */}
          {showGraphExpansionToggle && (
            <GraphExpansionSettingsCompact
              config={graphExpansionConfig}
              onChange={setGraphExpansionConfig}
            />
          )}

          {/* Sprint 63: Research Mode Toggle */}
          {showResearchToggle && onResearchModeToggle && (
            <ResearchModeToggleCompact
              isEnabled={isResearchMode}
              onToggle={onResearchModeToggle}
            />
          )}
        </div>

        {/* Help Text - right aligned */}
        <div className="text-xs text-gray-400 hidden sm:block">
          <kbd className="px-1.5 py-0.5 text-xs bg-gray-100 border border-gray-200 rounded">
            Enter
          </kbd>
          {' '}senden
        </div>
      </div>
    </div>
  );
}
