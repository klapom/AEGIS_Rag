/**
 * RetrievalStep Component
 * Sprint 46 Feature 46.2: Transparent Reasoning Panel
 *
 * Displays an individual retrieval step in the reasoning chain.
 * Shows source icon, name, duration, result count, and source-specific details.
 */

import { Database, Search, GitBranch, Clock, Layers, Filter } from 'lucide-react';
import type { RetrievalStep as RetrievalStepType, RetrievalSource } from '../../types/reasoning';

interface RetrievalStepProps {
  /** The retrieval step data to display */
  step: RetrievalStepType;
  /** Whether this is the last step (for styling) */
  isLast?: boolean;
}

/**
 * Get the appropriate icon for each retrieval source
 */
function getSourceIcon(source: RetrievalSource): React.ReactNode {
  const iconClass = 'w-4 h-4';
  switch (source) {
    case 'qdrant':
      return <Database className={iconClass} />;
    case 'bm25':
      return <Search className={iconClass} />;
    case 'neo4j':
      return <GitBranch className={iconClass} />;
    case 'redis':
      return <Clock className={iconClass} />;
    case 'rrf_fusion':
      return <Layers className={iconClass} />;
    case 'reranker':
      return <Filter className={iconClass} />;
    default:
      return <Database className={iconClass} />;
  }
}

/**
 * Get human-readable name for each retrieval source
 */
function getSourceName(source: RetrievalSource): string {
  switch (source) {
    case 'qdrant':
      return 'Qdrant Vector Search';
    case 'bm25':
      return 'BM25 Keyword Search';
    case 'neo4j':
      return 'Neo4j Graph Query';
    case 'redis':
      return 'Redis Memory Check';
    case 'rrf_fusion':
      return 'RRF Fusion';
    case 'reranker':
      return 'Reranker';
    default:
      return source;
  }
}

/**
 * Get color styling for each retrieval source
 */
function getSourceColor(source: RetrievalSource): {
  bg: string;
  text: string;
  border: string;
} {
  switch (source) {
    case 'qdrant':
      return {
        bg: 'bg-blue-50',
        text: 'text-blue-700',
        border: 'border-blue-200',
      };
    case 'bm25':
      return {
        bg: 'bg-amber-50',
        text: 'text-amber-700',
        border: 'border-amber-200',
      };
    case 'neo4j':
      return {
        bg: 'bg-purple-50',
        text: 'text-purple-700',
        border: 'border-purple-200',
      };
    case 'redis':
      return {
        bg: 'bg-red-50',
        text: 'text-red-700',
        border: 'border-red-200',
      };
    case 'rrf_fusion':
      return {
        bg: 'bg-green-50',
        text: 'text-green-700',
        border: 'border-green-200',
      };
    case 'reranker':
      return {
        bg: 'bg-indigo-50',
        text: 'text-indigo-700',
        border: 'border-indigo-200',
      };
    default:
      return {
        bg: 'bg-gray-50',
        text: 'text-gray-700',
        border: 'border-gray-200',
      };
  }
}

/**
 * Format duration in milliseconds to a human-readable string
 */
function formatDuration(ms: number): string {
  if (ms < 1) {
    return '<1ms';
  }
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Render source-specific details
 */
function renderDetails(step: RetrievalStepType): React.ReactNode {
  const { source, details } = step;

  switch (source) {
    case 'qdrant':
      return (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
          <span>
            Ergebnisse: <span className="font-medium">{step.result_count}</span>
          </span>
          {details.top_score !== undefined && (
            <span>
              Top Score: <span className="font-medium">{(details.top_score * 100).toFixed(1)}%</span>
            </span>
          )}
        </div>
      );

    case 'bm25':
      return (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
          <span>
            Ergebnisse: <span className="font-medium">{step.result_count}</span>
          </span>
          {details.query_terms && details.query_terms.length > 0 && (
            <span>
              Begriffe: <span className="font-medium">{details.query_terms.join(', ')}</span>
            </span>
          )}
        </div>
      );

    case 'neo4j':
      return (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
          {details.entities !== undefined && (
            <span>
              Entitaeten: <span className="font-medium">{details.entities}</span>
            </span>
          )}
          {details.relations !== undefined && (
            <span>
              Relationen: <span className="font-medium">{details.relations}</span>
            </span>
          )}
        </div>
      );

    case 'redis':
      return (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
          <span>
            Status:{' '}
            <span className={`font-medium ${details.found ? 'text-green-600' : 'text-gray-500'}`}>
              {details.found ? 'Gefunden' : 'Nicht gefunden'}
            </span>
          </span>
          {details.session_id && (
            <span className="truncate max-w-[200px]" title={details.session_id}>
              Session: <span className="font-medium">{details.session_id.slice(0, 8)}...</span>
            </span>
          )}
        </div>
      );

    case 'rrf_fusion':
      return (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
          <span>
            Zusammengefuehrt: <span className="font-medium">{step.result_count}</span>
          </span>
          {details.merged_count !== undefined && (
            <span>
              Quellen: <span className="font-medium">{details.merged_count}</span>
            </span>
          )}
        </div>
      );

    case 'reranker':
      return (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
          <span>
            Ergebnisse: <span className="font-medium">{step.result_count}</span>
          </span>
          {details.model && (
            <span>
              Modell: <span className="font-medium">{details.model}</span>
            </span>
          )}
        </div>
      );

    default:
      return (
        <div className="text-xs text-gray-600">
          Ergebnisse: <span className="font-medium">{step.result_count}</span>
        </div>
      );
  }
}

export function RetrievalStep({ step, isLast = false }: RetrievalStepProps) {
  const colors = getSourceColor(step.source);

  return (
    <div
      className="relative"
      data-testid={`retrieval-step-${step.step}`}
      data-source={step.source}
    >
      {/* Connection line to next step */}
      {!isLast && (
        <div className="absolute left-[17px] top-[36px] w-0.5 h-[calc(100%-20px)] bg-gray-200" />
      )}

      <div className="flex items-start gap-3">
        {/* Step number and icon */}
        <div
          className={`flex-shrink-0 w-9 h-9 rounded-lg ${colors.bg} ${colors.text} flex items-center justify-center border ${colors.border}`}
        >
          {getSourceIcon(step.source)}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 pb-4">
          {/* Header row */}
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-500">
                {step.step}.
              </span>
              <span className="font-medium text-gray-900 text-sm">
                {getSourceName(step.source)}
              </span>
            </div>
            <span className="text-xs text-gray-500 flex-shrink-0 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatDuration(step.duration_ms)}
            </span>
          </div>

          {/* Details */}
          {renderDetails(step)}
        </div>
      </div>
    </div>
  );
}
