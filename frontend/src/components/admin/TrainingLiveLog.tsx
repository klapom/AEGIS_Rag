/**
 * TrainingLiveLog Component
 * Sprint 45 Feature 45.13: Real-time Training Progress with SSE
 *
 * Displays live SSE events during domain training.
 * Shows FULL content (prompts, responses, evaluations) - NOT truncated.
 */

import { useEffect, useRef, useState } from 'react';
import type { TrainingEvent, TrainingEventType } from '../../hooks/useDomainTraining';

interface TrainingLiveLogProps {
  events: TrainingEvent[];
  isConnected: boolean;
  latestEvent: TrainingEvent | null;
}

/**
 * Get icon and color for event type
 */
function getEventStyle(eventType: TrainingEventType): {
  icon: string;
  color: string;
  bgColor: string;
} {
  switch (eventType) {
    case 'started':
      return { icon: '🚀', color: 'text-blue-400', bgColor: 'bg-blue-900/30' };
    case 'phase_changed':
      return { icon: '📍', color: 'text-purple-400', bgColor: 'bg-purple-900/30' };
    case 'progress_update':
      return { icon: '📊', color: 'text-cyan-400', bgColor: 'bg-cyan-900/30' };
    case 'llm_request':
      return { icon: '📤', color: 'text-yellow-400', bgColor: 'bg-yellow-900/30' };
    case 'llm_response':
      return { icon: '📥', color: 'text-green-400', bgColor: 'bg-green-900/30' };
    case 'sample_processing':
      return { icon: '🔄', color: 'text-blue-300', bgColor: 'bg-blue-900/20' };
    case 'sample_result':
      return { icon: '📋', color: 'text-emerald-400', bgColor: 'bg-emerald-900/30' };
    case 'evaluation_start':
      return { icon: '🧪', color: 'text-amber-400', bgColor: 'bg-amber-900/30' };
    case 'evaluation_result':
      return { icon: '📈', color: 'text-lime-400', bgColor: 'bg-lime-900/30' };
    case 'bootstrap_iteration':
      return { icon: '🔁', color: 'text-indigo-400', bgColor: 'bg-indigo-900/30' };
    case 'demo_selected':
      return { icon: '✨', color: 'text-pink-400', bgColor: 'bg-pink-900/30' };
    case 'completed':
      return { icon: '✅', color: 'text-green-500', bgColor: 'bg-green-900/40' };
    case 'failed':
    case 'error':
      return { icon: '❌', color: 'text-red-500', bgColor: 'bg-red-900/40' };
    default:
      return { icon: '📝', color: 'text-gray-400', bgColor: 'bg-gray-800/30' };
  }
}

/**
 * Format timestamp for display
 */
function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3,
  });
}

/**
 * Render event data as expandable JSON
 */
function EventData({ data, eventType }: { data: Record<string, unknown>; eventType: TrainingEventType }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // For LLM events, show some quick info inline
  const quickInfo = (() => {
    if (eventType === 'llm_request' && data.prompt) {
      const promptStr = String(data.prompt);
      return promptStr.length > 100 ? promptStr.slice(0, 100) + '...' : promptStr;
    }
    if (eventType === 'llm_response' && data.entities) {
      return `Entities: ${(data.entities as string[]).join(', ')}`;
    }
    if (eventType === 'llm_response' && data.relations) {
      return `Relations: ${(data.relations as unknown[]).length} extracted`;
    }
    if (eventType === 'sample_result') {
      return `F1: ${(data.f1 as number)?.toFixed(3) || 'N/A'}, Precision: ${(data.precision as number)?.toFixed(3) || 'N/A'}, Recall: ${(data.recall as number)?.toFixed(3) || 'N/A'}`;
    }
    if (eventType === 'evaluation_result' && data.metrics) {
      const metrics = data.metrics as Record<string, number>;
      return `F1: ${metrics.f1?.toFixed(3) || 'N/A'}`;
    }
    return null;
  })();

  if (!data || Object.keys(data).length === 0) {
    return null;
  }

  return (
    <div className="mt-1">
      {quickInfo && (
        <div className="text-xs text-gray-400 font-mono truncate">{quickInfo}</div>
      )}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="text-xs text-blue-400 hover:text-blue-300 mt-1"
      >
        {isExpanded ? '▼ Hide details' : '▶ Show full data (NOT truncated)'}
      </button>
      {isExpanded && (
        <pre className="mt-2 p-2 bg-gray-950 rounded text-xs text-gray-300 overflow-x-auto max-w-full whitespace-pre-wrap break-words">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

/**
 * Single event row
 */
function EventRow({ event }: { event: TrainingEvent }) {
  const { icon, color, bgColor } = getEventStyle(event.event_type);

  return (
    <div className={`p-2 rounded ${bgColor} border-l-2 border-current ${color}`}>
      <div className="flex items-start gap-2">
        <span className="text-sm">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500 font-mono">
              {formatTime(event.timestamp)}
            </span>
            <span className={`text-xs font-semibold uppercase ${color}`}>
              {event.event_type.replace('_', ' ')}
            </span>
            {event.phase && (
              <span className="text-xs text-gray-500 bg-gray-800 px-1 rounded">
                {event.phase}
              </span>
            )}
            {event.progress_percent > 0 && (
              <span className="text-xs text-gray-400">
                {event.progress_percent.toFixed(1)}%
              </span>
            )}
          </div>
          <p className="text-sm text-gray-200 mt-0.5">{event.message}</p>
          <EventData data={event.data} eventType={event.event_type} />
        </div>
      </div>
    </div>
  );
}

/**
 * Main TrainingLiveLog component
 */
export function TrainingLiveLog({ events, isConnected, latestEvent }: TrainingLiveLogProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState<'all' | 'llm' | 'progress'>('all');

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  // Detect manual scroll to disable auto-scroll
  const handleScroll = () => {
    if (!logContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  };

  // Filter events
  const filteredEvents = events.filter((event) => {
    if (filter === 'all') return true;
    if (filter === 'llm') {
      return ['llm_request', 'llm_response'].includes(event.event_type);
    }
    if (filter === 'progress') {
      return ['started', 'phase_changed', 'progress_update', 'completed', 'failed'].includes(
        event.event_type
      );
    }
    return true;
  });

  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          Live Training Log
          {isConnected && (
            <span className="inline-flex items-center gap-1 text-xs text-green-600">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              Connected
            </span>
          )}
          {!isConnected && events.length > 0 && (
            <span className="text-xs text-gray-500">Disconnected</span>
          )}
        </h3>
        <div className="flex items-center gap-2">
          {/* Filter buttons */}
          <div className="flex gap-1">
            {(['all', 'llm', 'progress'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-1 text-xs rounded ${
                  filter === f
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {f === 'all' ? 'All' : f === 'llm' ? 'LLM Only' : 'Progress'}
              </button>
            ))}
          </div>
          {/* Event count */}
          <span className="text-xs text-gray-500">{events.length} events</span>
        </div>
      </div>

      {/* Log container */}
      <div
        ref={logContainerRef}
        onScroll={handleScroll}
        className="bg-gray-900 rounded-lg p-2 max-h-96 overflow-y-auto space-y-1 font-mono"
        data-testid="training-live-log"
      >
        {filteredEvents.length === 0 && (
          <div className="text-center py-8 text-gray-500 text-sm">
            {events.length === 0
              ? 'Waiting for training events...'
              : 'No events match the current filter'}
          </div>
        )}
        {filteredEvents.map((event, idx) => (
          <EventRow key={`${event.timestamp}-${idx}`} event={event} />
        ))}
      </div>

      {/* Auto-scroll indicator */}
      {!autoScroll && events.length > 10 && (
        <button
          onClick={() => {
            setAutoScroll(true);
            if (logContainerRef.current) {
              logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
            }
          }}
          className="w-full py-1 text-xs text-center text-blue-600 bg-blue-50 rounded hover:bg-blue-100"
        >
          ↓ Scroll to latest events
        </button>
      )}

      {/* Latest event summary */}
      {latestEvent && (
        <div className="text-xs text-gray-600 flex items-center gap-2">
          <span className="font-semibold">Latest:</span>
          <span>{latestEvent.message}</span>
        </div>
      )}
    </div>
  );
}
