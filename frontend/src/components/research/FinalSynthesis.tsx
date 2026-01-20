/**
 * FinalSynthesis Component
 * Sprint 116.10: Deep Research Multi-Step (13 SP)
 *
 * Displays the final synthesized answer from deep research with
 * source citations and export functionality.
 *
 * Features:
 * - Formatted final answer display
 * - Source citations with expandable details
 * - Export to PDF/Markdown
 * - Timing information
 * - Copy to clipboard
 */

import { useState } from 'react';
import {
  FileText,
  Download,
  Copy,
  CheckCircle2,
  Clock,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import type { Source } from '../../types/research';

interface FinalSynthesisProps {
  /** Original research query */
  query: string;
  /** Final synthesized answer */
  finalAnswer: string;
  /** List of sources used */
  sources: Source[];
  /** Total execution time in milliseconds */
  totalTimeMs: number;
  /** Callback to export results */
  onExport?: (format: 'markdown' | 'pdf') => void;
}

/**
 * FinalSynthesis Component
 */
export function FinalSynthesis({
  query,
  finalAnswer,
  sources,
  totalTimeMs,
  onExport,
}: FinalSynthesisProps) {
  const [showSources, setShowSources] = useState(false);
  const [copied, setCopied] = useState(false);

  /**
   * Copy answer to clipboard
   */
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(finalAnswer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  /**
   * Format execution time
   */
  const formatTime = (ms: number): string => {
    if (ms < 1000) {
      return `${ms}ms`;
    } else if (ms < 60000) {
      return `${(ms / 1000).toFixed(1)}s`;
    } else {
      const minutes = Math.floor(ms / 60000);
      const seconds = ((ms % 60000) / 1000).toFixed(0);
      return `${minutes}m ${seconds}s`;
    }
  };

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
      data-testid="final-synthesis"
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-6 text-white">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-grow">
            <h2 className="text-xl font-semibold mb-2">Final Synthesis</h2>
            <p className="text-blue-100 text-sm">{query}</p>
          </div>
          <div className="flex items-center gap-2 text-sm bg-blue-400/30 px-3 py-1.5 rounded-full">
            <Clock className="w-4 h-4" />
            {formatTime(totalTimeMs)}
          </div>
        </div>
      </div>

      {/* Answer */}
      <div className="p-6">
        <div className="prose prose-sm max-w-none">
          <div className="whitespace-pre-wrap text-gray-900">{finalAnswer}</div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 mt-6 pt-6 border-t border-gray-200">
          <button
            onClick={copyToClipboard}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-2 text-sm text-gray-700"
            data-testid="copy-answer-button"
          >
            {copied ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy Answer
              </>
            )}
          </button>

          {onExport && (
            <>
              <button
                onClick={() => onExport('markdown')}
                className="px-4 py-2 bg-blue-100 hover:bg-blue-200 rounded-lg transition-colors flex items-center gap-2 text-sm text-blue-700"
                data-testid="export-markdown-button"
              >
                <Download className="w-4 h-4" />
                Export Markdown
              </button>

              <button
                onClick={() => onExport('pdf')}
                className="px-4 py-2 bg-green-100 hover:bg-green-200 rounded-lg transition-colors flex items-center gap-2 text-sm text-green-700"
                data-testid="export-pdf-button"
              >
                <FileText className="w-4 h-4" />
                Export PDF
              </button>
            </>
          )}

          <div className="flex-grow" />

          <button
            onClick={() => setShowSources(!showSources)}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-2 text-sm text-gray-700"
            data-testid="toggle-sources-button"
          >
            {showSources ? (
              <>
                <ChevronDown className="w-4 h-4" />
                Hide Sources ({sources.length})
              </>
            ) : (
              <>
                <ChevronRight className="w-4 h-4" />
                Show Sources ({sources.length})
              </>
            )}
          </button>
        </div>
      </div>

      {/* Sources */}
      {showSources && sources.length > 0 && (
        <div className="border-t border-gray-200 bg-gray-50 p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
            Sources ({sources.length})
          </h3>

          <div className="space-y-3">
            {sources.map((source, index) => (
              <div
                key={index}
                className="bg-white rounded-lg border border-gray-200 p-4"
                data-testid={`source-${index}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-500">
                      [{index + 1}]
                    </span>
                    <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                      {source.source_type}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">
                    Score: {source.score.toFixed(3)}
                  </span>
                </div>

                <p className="text-sm text-gray-700 mb-2">{source.text}</p>

                {/* Entities */}
                {source.entities && source.entities.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-100">
                    <div className="text-xs text-gray-500 mb-1">Entities:</div>
                    <div className="flex flex-wrap gap-1">
                      {source.entities.slice(0, 5).map((entity, idx) => (
                        <span
                          key={idx}
                          className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded"
                        >
                          {entity}
                        </span>
                      ))}
                      {source.entities.length > 5 && (
                        <span className="text-xs text-gray-400">
                          +{source.entities.length - 5} more
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Relationships */}
                {source.relationships && source.relationships.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-100">
                    <div className="text-xs text-gray-500 mb-1">Relationships:</div>
                    <div className="flex flex-wrap gap-1">
                      {source.relationships.slice(0, 3).map((rel, idx) => (
                        <span
                          key={idx}
                          className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded"
                        >
                          {rel}
                        </span>
                      ))}
                      {source.relationships.length > 3 && (
                        <span className="text-xs text-gray-400">
                          +{source.relationships.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
