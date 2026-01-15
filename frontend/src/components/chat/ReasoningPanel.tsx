/**
 * ReasoningPanel Component
 * Sprint 46 Feature 46.2: Transparent Reasoning Panel
 * Sprint 51: Added phase events display to persist phases after answer
 * Sprint 63: Added tool execution visualization
 *
 * Expandable panel showing the retrieval chain, similar to ChatGPT's
 * chain-of-thought display. Collapsed by default, shows all retrieval
 * steps when expanded.
 *
 * Sections when expanded:
 * - Processing phases (Sprint 51)
 * - Intent classification (intent type + confidence score)
 * - Retrieval Chain with steps
 * - Tool Executions (Sprint 63)
 * - Tools Used section (if any)
 */

import { useState, useCallback } from 'react';
import { ChevronRight, ChevronDown, Brain, Wrench, CheckCircle, XCircle, SkipForward, Loader2, Terminal } from 'lucide-react';
import { RetrievalStep } from './RetrievalStep';
import { ToolExecutionDisplay } from './ToolExecutionDisplay';
import type {
  ReasoningData,
  IntentInfo,
  IntentType,
  PhaseEvent,
  FourWayResults,
  IntentWeights,
  ChannelSamples,
  ChannelSample,
  ToolExecutionStep,
} from '../../types/reasoning';
import { PHASE_NAMES } from '../../types/reasoning';

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
 * Sprint 51: Phases section showing completed processing phases
 */
function PhasesSection({ phases }: { phases: PhaseEvent[] }) {
  if (!phases || phases.length === 0) return null;

  /**
   * Get status icon for phase
   */
  const getStatusIcon = (status: PhaseEvent['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-3.5 h-3.5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-3.5 h-3.5 text-red-500" />;
      case 'skipped':
        return <SkipForward className="w-3.5 h-3.5 text-gray-400" />;
      case 'in_progress':
        return <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />;
      default:
        return <div className="w-3.5 h-3.5 rounded-full bg-gray-300" />;
    }
  };

  /**
   * Get duration in ms - use duration_ms field directly from backend
   * Sprint 52 Fix: Backend sends duration_ms, don't calculate from timestamps
   * (timestamps may have same value due to backend implementation)
   */
  const getDuration = (phase: PhaseEvent): number | null => {
    // Use the duration_ms field directly if available
    if (phase.duration_ms !== undefined && phase.duration_ms !== null) {
      return phase.duration_ms;
    }
    // Fallback to timestamp calculation if duration_ms not available
    if (!phase.end_time || !phase.start_time) return null;
    return new Date(phase.end_time).getTime() - new Date(phase.start_time).getTime();
  };

  /**
   * Format duration
   */
  const formatDuration = (ms: number | null): string => {
    if (ms === null) return '';
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div data-testid="phases-section">
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
        Verarbeitungsphasen ({phases.filter(p => p.status === 'completed').length}/{phases.length})
      </h4>
      <div className="space-y-1">
        {phases.map((phase) => {
          const duration = getDuration(phase);
          return (
            <div
              key={phase.phase_type}
              className="flex items-center justify-between py-1.5 px-2 rounded bg-white border border-gray-100"
            >
              <div className="flex items-center gap-2">
                {getStatusIcon(phase.status)}
                <span className="text-sm text-gray-700">
                  {PHASE_NAMES[phase.phase_type] || phase.phase_type}
                </span>
              </div>
              {duration !== null && (
                <span className="text-xs text-gray-500">
                  {formatDuration(duration)}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Sprint 52: Individual channel sample display
 * Enhanced to show keywords (Sparse) and entities (Graph)
 * Sprint 87: BM25 replaced with Sparse (BGE-M3 learned lexical weights)
 */
function ChannelSampleItem({ sample }: { sample: ChannelSample }) {
  const hasKeywords = sample.keywords && sample.keywords.length > 0;
  const hasEntities = sample.matched_entities && sample.matched_entities.length > 0;

  return (
    <div className="pl-6 py-1.5 text-xs text-gray-600 border-l-2 border-gray-200 ml-4">
      <div className="flex items-start gap-2">
        <span className="text-gray-400 shrink-0">•</span>
        <div className="flex-1 min-w-0">
          <p className="line-clamp-2 break-words">{sample.text}</p>
          {/* Keywords (Sparse channel - BGE-M3 learned lexical weights) */}
          {hasKeywords && (
            <div className="flex flex-wrap gap-1 mt-1">
              <span className="text-gray-400 text-[10px]">Keywords:</span>
              {sample.keywords!.slice(0, 5).map((kw, idx) => (
                <span
                  key={`kw-${idx}`}
                  className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-[10px] font-medium"
                >
                  {kw}
                </span>
              ))}
              {sample.keywords!.length > 5 && (
                <span className="text-gray-400 text-[10px]">+{sample.keywords!.length - 5}</span>
              )}
            </div>
          )}
          {/* Matched Entities (Graph channels) */}
          {hasEntities && (
            <div className="flex flex-wrap gap-1 mt-1">
              <span className="text-gray-400 text-[10px]">Entitäten:</span>
              {sample.matched_entities!.slice(0, 4).map((entity, idx) => (
                <span
                  key={`ent-${idx}`}
                  className="px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded text-[10px] font-medium"
                >
                  {entity}
                </span>
              ))}
              {sample.matched_entities!.length > 4 && (
                <span className="text-gray-400 text-[10px]">+{sample.matched_entities!.length - 4}</span>
              )}
            </div>
          )}
          {/* Community ID (Graph Global) */}
          {sample.community_id && (
            <span className="text-green-600 text-[10px] mt-1 inline-block">
              Community: {sample.community_id}
            </span>
          )}
          {sample.title && (
            <p className="text-gray-400 mt-0.5 truncate text-[10px]">
              {sample.title} {sample.score > 0 && `(${(sample.score * 100).toFixed(1)}%)`}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Sprint 63: Tool Executions section showing tool execution results
 */
function ToolExecutionsSection({ toolSteps }: { toolSteps: ToolExecutionStep[] }) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!toolSteps || toolSteps.length === 0) return null;

  return (
    <div data-testid="tool-executions-section">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-left mb-3"
        aria-expanded={isExpanded}
      >
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide flex items-center gap-1.5">
          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          <Terminal className="w-3.5 h-3.5" />
          Tool-Ausfuehrungen ({toolSteps.length})
        </h4>
      </button>
      {isExpanded && (
        <div className="space-y-3">
          {toolSteps.map((step, index) => (
            <ToolExecutionDisplay
              key={`${step.tool_name}-${step.timestamp}-${index}`}
              step={step}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Sprint 52: 4-Way Hybrid Search Results section
 */
function FourWaySection({
  results,
  weights,
  intentMethod,
  intentLatency,
  channelSamples,
}: {
  results?: FourWayResults;
  weights?: IntentWeights;
  intentMethod?: string;
  intentLatency?: number;
  channelSamples?: ChannelSamples;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  // Track which channels have their samples expanded
  const [expandedChannels, setExpandedChannels] = useState<Set<string>>(new Set());

  // Sprint 52 Debug: Log what we receive
  console.log('[FourWaySection] Received:', { results, weights, intentMethod, intentLatency, channelSamples });

  // Don't render if no data
  if (!results && !weights) {
    console.log('[FourWaySection] Returning null - no results and no weights');
    return null;
  }

  // Sprint 92: Support both new (dense/sparse) and legacy (vector/bm25) field names
  const denseCount = results?.dense_count ?? results?.vector_count ?? 0;
  const sparseCount = results?.sparse_count ?? results?.bm25_count ?? 0;
  const totalResults = results?.total_count ?? (results
    ? denseCount + sparseCount + (results.graph_local_count ?? 0) + (results.graph_global_count ?? 0)
    : 0);

  // Map channel keys to sample arrays
  // Sprint 92: Support dense/sparse (new), vector/bm25 (legacy) keys
  const channelSampleMap: Record<string, ChannelSample[]> = {
    'Dense (Semantisch)': channelSamples?.dense ?? channelSamples?.vector ?? [],
    'Sparse (Lexikalisch)': channelSamples?.sparse ?? channelSamples?.bm25 ?? [],
    'Graph Local': channelSamples?.graph_local ?? [],
    'Graph Global': channelSamples?.graph_global ?? [],
  };

  const channels = [
    { name: 'Dense (Semantisch)', count: denseCount, weight: weights?.dense ?? weights?.vector ?? 0, color: 'bg-blue-500', icon: '🔍' },
    { name: 'Sparse (Lexikalisch)', count: sparseCount, weight: weights?.sparse ?? weights?.bm25 ?? 0, color: 'bg-amber-500', icon: '📝' },
    { name: 'Graph Local', count: results?.graph_local_count ?? 0, weight: weights?.local ?? 0, color: 'bg-purple-500', icon: '🔗' },
    { name: 'Graph Global', count: results?.graph_global_count ?? 0, weight: weights?.global ?? 0, color: 'bg-green-500', icon: '🌐' },
  ];

  const toggleChannelSamples = (channelName: string) => {
    setExpandedChannels(prev => {
      const next = new Set(prev);
      if (next.has(channelName)) {
        next.delete(channelName);
      } else {
        next.add(channelName);
      }
      return next;
    });
  };

  return (
    <div data-testid="four-way-section" className="mb-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-left"
      >
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide flex items-center gap-2">
          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          4-Way Hybrid Search ({totalResults} Ergebnisse)
        </h4>
        {intentMethod && (
          <span className="text-xs text-gray-400">
            {intentMethod === 'llm' ? 'LLM' : 'Regel'}{intentLatency ? ` • ${Math.round(intentLatency)}ms` : ''}
          </span>
        )}
      </button>

      {isExpanded && (
        <div className="mt-3 space-y-1">
          {channels.map((channel) => {
            const samples = channelSampleMap[channel.name];
            const hasSamples = samples && samples.length > 0;
            const isChannelExpanded = expandedChannels.has(channel.name);

            return (
              <div key={channel.name}>
                <div
                  className={`flex items-center justify-between py-1.5 px-2 rounded bg-white border border-gray-100 ${hasSamples ? 'cursor-pointer hover:bg-gray-50' : ''}`}
                  onClick={hasSamples ? () => toggleChannelSamples(channel.name) : undefined}
                >
                  <div className="flex items-center gap-2 flex-1">
                    {hasSamples && (
                      isChannelExpanded
                        ? <ChevronDown className="w-3 h-3 text-gray-400" />
                        : <ChevronRight className="w-3 h-3 text-gray-400" />
                    )}
                    {!hasSamples && <span className="w-3" />}
                    <span className="text-sm">{channel.icon}</span>
                    <span className="text-sm text-gray-700">{channel.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {/* Weight bar */}
                    <div className="flex items-center gap-1.5">
                      <span className={`text-xs w-8 text-right ${channel.count === 0 ? 'text-gray-300' : 'text-gray-500'}`}>
                        {Math.round(channel.weight * 100)}%
                      </span>
                      <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${channel.count === 0 ? 'bg-gray-300' : channel.color} rounded-full transition-all`}
                          style={{ width: `${channel.weight * 100}%` }}
                        />
                      </div>
                    </div>
                    {/* Result count */}
                    <span className={`text-xs font-medium w-8 text-right ${channel.count === 0 ? 'text-gray-300' : 'text-gray-600'}`}>
                      {channel.count}
                    </span>
                  </div>
                </div>
                {/* Channel samples (expandable) */}
                {isChannelExpanded && hasSamples && (
                  <div className="mt-1 mb-2 space-y-0.5">
                    {samples.map((sample, idx) => (
                      <ChannelSampleItem key={`${channel.name}-${idx}`} sample={sample} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Main ReasoningPanel component
 */
export function ReasoningPanel({
  data,
  defaultExpanded = true, // Sprint 51: Default to expanded to show phases
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

  const { intent, retrieval_steps, tools_used, total_duration_ms, phase_events, four_way_results, intent_weights, intent_method, intent_latency_ms, channel_samples, tool_steps } = data;

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

          {/* Sprint 51: Processing Phases (shown first if available) */}
          {phase_events && phase_events.length > 0 && (
            <PhasesSection phases={phase_events} />
          )}

          {/* Intent Classification */}
          <IntentSection intent={intent} />

          {/* Sprint 52: 4-Way Hybrid Search Results */}
          <FourWaySection
            results={four_way_results}
            weights={intent_weights}
            intentMethod={intent_method}
            intentLatency={intent_latency_ms}
            channelSamples={channel_samples}
          />

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

          {/* Sprint 63: Tool Executions */}
          {tool_steps && tool_steps.length > 0 && (
            <ToolExecutionsSection toolSteps={tool_steps} />
          )}

          {/* Tools Used */}
          <ToolsSection tools={tools_used} />
        </div>
      )}
    </div>
  );
}
