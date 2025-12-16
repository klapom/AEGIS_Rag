/**
 * ReasoningPanel Component
 * Sprint 46 Feature 46.2: Transparent Reasoning Panel
 *
 * Expandable panel showing the retrieval chain, similar to ChatGPT's
 * chain-of-thought display. Collapsed by default, shows all retrieval
 * steps when expanded.
 *
 * Sections when expanded:
 * - Intent classification (intent type + confidence score)
 * - Retrieval Chain with steps
 * - Tools Used section (if any)
 */

import { useState, useCallback } from 'react';
import { ChevronRight, ChevronDown, Brain, Wrench } from 'lucide-react';
import { RetrievalStep } from './RetrievalStep';
import type {
  ReasoningData,
  IntentInfo,
  IntentType,
} from '../../types/reasoning';

interface ReasoningPanelProps {
  /** Reasoning data to display */
  data: ReasoningData | null;
  /** Whether the panel is initially expanded */
  defaultExpanded?: boolean;
  /** Callback when panel expansion state changes */
  onToggle?: (expanded: boolean) => void;
}

/**
 * Get human-readable name for intent types
 */
function getIntentName(intent: IntentType): string {
  switch (intent) {
    case 'factual':
      return 'Faktenbezogen';
    case 'keyword':
      return 'Stichwortsuche';
    case 'exploratory':
      return 'Explorativ';
    case 'summary':
      return 'Zusammenfassung';
    default:
      return intent;
  }
}

/**
 * Get color styling for intent types
 */
function getIntentColor(intent: IntentType): string {
  switch (intent) {
    case 'factual':
      return 'bg-blue-100 text-blue-800';
    case 'keyword':
      return 'bg-amber-100 text-amber-800';
    case 'exploratory':
      return 'bg-purple-100 text-purple-800';
    case 'summary':
      return 'bg-green-100 text-green-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

/**
 * Intent Classification section
 */
function IntentSection({ intent }: { intent: IntentInfo }) {
  const confidencePercent = Math.round(intent.confidence * 100);
  const intentColor = getIntentColor(intent.intent);

  return (
    <div className="mb-4" data-testid="intent-section">
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
        Intent-Klassifikation
      </h4>
      <div className="flex items-center gap-3">
        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${intentColor}`}>
          {getIntentName(intent.intent)}
        </span>
        <div className="flex items-center gap-2">
          <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${confidencePercent}%` }}
            />
          </div>
          <span className="text-xs text-gray-600 font-medium">
            {confidencePercent}%
          </span>
        </div>
      </div>
      {intent.reasoning && (
        <p className="mt-2 text-xs text-gray-500 italic">
          {intent.reasoning}
        </p>
      )}
    </div>
  );
}

/**
 * Tools Used section
 */
function ToolsSection({ tools }: { tools: string[] }) {
  if (tools.length === 0) return null;

  return (
    <div className="mt-4 pt-4 border-t border-gray-200" data-testid="tools-section">
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <Wrench className="w-3.5 h-3.5" />
        Verwendete Tools
      </h4>
      <div className="flex flex-wrap gap-2">
        {tools.map((tool, index) => (
          <span
            key={`${tool}-${index}`}
            className="px-2.5 py-1 bg-gray-100 text-gray-700 rounded-md text-xs font-medium"
          >
            {tool}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Main ReasoningPanel component
 */
export function ReasoningPanel({
  data,
  defaultExpanded = false,
  onToggle,
}: ReasoningPanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const handleToggle = useCallback(() => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    onToggle?.(newExpanded);
  }, [isExpanded, onToggle]);

  // Don't render if no data
  if (!data) {
    return null;
  }

  const { intent, retrieval_steps, tools_used, total_duration_ms } = data;

  return (
    <div
      className="mt-3 border border-gray-200 rounded-lg bg-gray-50/50"
      data-testid="reasoning-panel"
    >
      {/* Toggle Button */}
      <button
        onClick={handleToggle}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-100 transition-colors rounded-lg"
        aria-expanded={isExpanded}
        aria-controls="reasoning-content"
        data-testid="reasoning-toggle"
      >
        <div className="flex items-center gap-2 text-sm text-gray-700">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
          <Brain className="w-4 h-4 text-primary" />
          <span className="font-medium">
            {isExpanded ? 'Reasoning ausblenden' : 'Reasoning anzeigen'}
          </span>
        </div>
        {total_duration_ms !== undefined && (
          <span className="text-xs text-gray-500">
            {total_duration_ms < 1000
              ? `${Math.round(total_duration_ms)}ms`
              : `${(total_duration_ms / 1000).toFixed(2)}s`}
          </span>
        )}
      </button>

      {/* Expandable Content */}
      {isExpanded && (
        <div
          id="reasoning-content"
          className="px-4 pb-4 space-y-4"
          data-testid="reasoning-content"
        >
          {/* Divider */}
          <div className="border-t border-gray-200 -mx-4" />

          {/* Intent Classification */}
          <IntentSection intent={intent} />

          {/* Retrieval Chain */}
          {retrieval_steps.length > 0 && (
            <div data-testid="retrieval-chain">
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
                Retrieval Chain ({retrieval_steps.length} Schritte)
              </h4>
              <div className="space-y-1">
                {retrieval_steps.map((step, index) => (
                  <RetrievalStep
                    key={`${step.source}-${step.step}`}
                    step={step}
                    isLast={index === retrieval_steps.length - 1}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Tools Used */}
          <ToolsSection tools={tools_used} />
        </div>
      )}
    </div>
  );
}
