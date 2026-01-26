/**
 * ResearchProgressTracker Component
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 *
 * Displays real-time research progress with phase indicators,
 * iteration counts, and expandable details per phase.
 *
 * Features:
 * - Visual progress steps with icons
 * - Current phase highlighting
 * - Iteration count display
 * - Expandable details per phase
 * - Progress bar for overall completion
 * - Error state display
 */

import { useState, useMemo } from 'react';
import {
  Lightbulb,
  Search,
  CheckCircle2,
  FileText,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
  X,
} from 'lucide-react';
import type {
  ResearchProgressTrackerProps,
  ResearchPhase,
  ResearchProgress,
} from '../../types/research';
import { RESEARCH_PHASE_NAMES } from '../../types/research';

/**
 * Phase order for progress display
 */
const PHASE_ORDER: ResearchPhase[] = ['start', 'plan', 'search', 'evaluate', 'synthesize', 'complete'];

/**
 * Get icon for a research phase
 */
function getPhaseIcon(phase: ResearchPhase, status: 'pending' | 'current' | 'completed' | 'error') {
  const iconClass = 'w-5 h-5';

  if (status === 'error') {
    return <AlertCircle className={`${iconClass} text-red-500`} />;
  }

  if (status === 'current') {
    return <Loader2 className={`${iconClass} text-blue-500 animate-spin`} />;
  }

  const iconMap: Record<ResearchPhase, React.ReactNode> = {
    start: <Clock className={iconClass} />,
    plan: <Lightbulb className={iconClass} />,
    search: <Search className={iconClass} />,
    evaluate: <CheckCircle2 className={iconClass} />,
    synthesize: <FileText className={iconClass} />,
    complete: <CheckCircle2 className={iconClass} />,
  };

  return iconMap[phase] || <Clock className={iconClass} />;
}

/**
 * Get status color classes for a phase
 */
function getPhaseStatusClasses(status: 'pending' | 'current' | 'completed' | 'error'): string {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-700 border-green-300';
    case 'current':
      return 'bg-blue-100 text-blue-700 border-blue-300';
    case 'error':
      return 'bg-red-100 text-red-700 border-red-300';
    default:
      return 'bg-gray-100 text-gray-500 border-gray-200';
  }
}

/**
 * Individual phase progress item
 */
interface PhaseItemProps {
  phase: ResearchPhase;
  status: 'pending' | 'current' | 'completed' | 'error';
  progressData?: ResearchProgress;
  isExpanded: boolean;
  onToggle: () => void;
}

function PhaseItem({ phase, status, progressData, isExpanded, onToggle }: PhaseItemProps) {
  const hasDetails = progressData && Object.keys(progressData.metadata).length > 0;

  return (
    <div
      className={`rounded-lg border transition-all duration-200 ${getPhaseStatusClasses(status)}`}
      data-testid={`phase-item-${phase}`}
    >
      <button
        onClick={onToggle}
        disabled={!hasDetails}
        className={`w-full flex items-center gap-3 p-3 text-left ${
          hasDetails ? 'cursor-pointer hover:bg-opacity-80' : 'cursor-default'
        }`}
        aria-expanded={isExpanded}
        aria-label={`${RESEARCH_PHASE_NAMES[phase]} - ${status}`}
      >
        {/* Icon */}
        <div className="flex-shrink-0">
          {getPhaseIcon(phase, status)}
        </div>

        {/* Phase name and description */}
        <div className="flex-grow min-w-0">
          <div className="font-medium text-sm">{RESEARCH_PHASE_NAMES[phase]}</div>
          {progressData?.message && status === 'current' && (
            <div className="text-xs opacity-75 truncate">{progressData.message}</div>
          )}
        </div>

        {/* Iteration badge (if applicable) */}
        {progressData && progressData.iteration > 0 && (
          <div className="flex-shrink-0 text-xs px-2 py-0.5 rounded-full bg-white/50">
            Iteration {progressData.iteration}
          </div>
        )}

        {/* Expand chevron */}
        {hasDetails && (
          <div className="flex-shrink-0">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </div>
        )}
      </button>

      {/* Expanded details */}
      {isExpanded && hasDetails && progressData && (
        <div className="px-3 pb-3 pt-0 border-t border-current/10">
          <div className="grid grid-cols-2 gap-2 text-xs mt-2">
            {progressData.metadata.num_queries && (
              <div>
                <span className="opacity-70">Abfragen:</span>{' '}
                <span className="font-medium">{progressData.metadata.num_queries}</span>
              </div>
            )}
            {progressData.metadata.sources_found && (
              <div>
                <span className="opacity-70">Quellen:</span>{' '}
                <span className="font-medium">{progressData.metadata.sources_found}</span>
              </div>
            )}
            {progressData.metadata.num_results && (
              <div>
                <span className="opacity-70">Ergebnisse:</span>{' '}
                <span className="font-medium">{progressData.metadata.num_results}</span>
              </div>
            )}
            {progressData.metadata.quality_score !== undefined && (
              <div>
                <span className="opacity-70">Qualitaet:</span>{' '}
                <span className="font-medium">
                  {(progressData.metadata.quality_score * 100).toFixed(0)}%
                </span>
              </div>
            )}
            {progressData.metadata.coverage !== undefined && (
              <div>
                <span className="opacity-70">Abdeckung:</span>{' '}
                <span className="font-medium">
                  {(progressData.metadata.coverage * 100).toFixed(0)}%
                </span>
              </div>
            )}
            {progressData.metadata.diversity !== undefined && (
              <div>
                <span className="opacity-70">Diversitaet:</span>{' '}
                <span className="font-medium">
                  {(progressData.metadata.diversity * 100).toFixed(0)}%
                </span>
              </div>
            )}
          </div>

          {/* Plan steps (if available) - Sprint 92: Enhanced sub-query display */}
          {progressData.metadata.plan_steps &&
            Array.isArray(progressData.metadata.plan_steps) &&
            progressData.metadata.plan_steps.length > 0 && (
              <div className="mt-2">
                <div className="opacity-70 mb-1">Generierte Such-Queries:</div>
                <ul className="list-decimal list-inside text-xs space-y-1">
                  {(progressData.metadata.plan_steps as string[]).map((step, idx) => (
                    <li key={idx} className="truncate" title={step}>
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
            )}

          {/* Sprint 92: Per-query chunk counts */}
          {progressData.metadata.contexts_per_query &&
            typeof progressData.metadata.contexts_per_query === 'object' && (
              <div className="mt-2">
                <div className="opacity-70 mb-1">Chunks pro Query:</div>
                <div className="text-xs space-y-0.5">
                  {Object.entries(progressData.metadata.contexts_per_query as Record<string, number>).map(
                    ([queryIdx, count]) => (
                      <div key={queryIdx} className="flex justify-between">
                        <span className="opacity-70">Query {queryIdx}:</span>
                        <span className="font-medium">{count} Chunks</span>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

          {/* Sprint 92: Quality label for evaluate phase */}
          {progressData.metadata.quality_label && (
            <div className="mt-2">
              <div className="flex items-center gap-2">
                <span className="opacity-70">Qualität:</span>
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    progressData.metadata.quality_label === 'excellent'
                      ? 'bg-green-100 text-green-700'
                      : progressData.metadata.quality_label === 'good'
                      ? 'bg-blue-100 text-blue-700'
                      : progressData.metadata.quality_label === 'fair'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}
                >
                  {progressData.metadata.quality_label === 'excellent'
                    ? 'Exzellent'
                    : progressData.metadata.quality_label === 'good'
                    ? 'Gut'
                    : progressData.metadata.quality_label === 'fair'
                    ? 'Ausreichend'
                    : 'Schwach'}
                </span>
                {progressData.metadata.avg_score !== undefined && (
                  <span className="text-xs opacity-60">
                    (Ø Score: {(progressData.metadata.avg_score as number).toFixed(2)})
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Sprint 92: Top sources used in synthesis */}
          {progressData.metadata.top_sources &&
            Array.isArray(progressData.metadata.top_sources) &&
            progressData.metadata.top_sources.length > 0 && (
              <div className="mt-2">
                <div className="opacity-70 mb-1">Verwendete Quellen:</div>
                <ul className="text-xs space-y-1 max-h-32 overflow-y-auto">
                  {(progressData.metadata.top_sources as string[]).map((source, idx) => (
                    <li key={idx} className="truncate text-gray-600" title={source}>
                      {source}
                    </li>
                  ))}
                </ul>
              </div>
            )}

          {/* Sprint 92: Better empty results feedback */}
          {progressData.metadata.num_contexts === 0 && phase === 'search' && (
            <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-amber-700 text-xs">
              <div className="font-medium">Keine Ergebnisse gefunden</div>
              <div className="mt-1 opacity-80">
                Die Suche hat keine passenden Dokumente gefunden.
                Mögliche Gründe:
                <ul className="list-disc list-inside mt-1">
                  <li>Zu spezifische Suchbegriffe</li>
                  <li>Dokumente nicht im gewählten Namespace</li>
                  <li>Noch keine Dokumente indiziert</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * ResearchProgressTracker Component
 */
export function ResearchProgressTracker({
  progress,
  currentPhase,
  isResearching,
  error,
  onPhaseClick,
  onDismiss,
}: ResearchProgressTrackerProps) {
  const [expandedPhases, setExpandedPhases] = useState<Set<ResearchPhase>>(new Set());

  // Calculate phase statuses based on progress
  const phaseStatuses = useMemo(() => {
    const statuses: Record<ResearchPhase, 'pending' | 'current' | 'completed' | 'error'> = {
      start: 'pending',
      plan: 'pending',
      search: 'pending',
      evaluate: 'pending',
      synthesize: 'pending',
      complete: 'pending',
    };

    // Get phases that have been seen in progress
    const seenPhases = new Set(progress.map((p) => p.phase));

    // Determine status for each phase
    for (const phase of PHASE_ORDER) {
      if (error && phase === currentPhase) {
        statuses[phase] = 'error';
      } else if (phase === currentPhase && isResearching) {
        statuses[phase] = 'current';
      } else if (seenPhases.has(phase)) {
        // Phase has been processed
        const phaseIndex = PHASE_ORDER.indexOf(phase);
        const currentIndex = currentPhase ? PHASE_ORDER.indexOf(currentPhase) : -1;

        if (currentIndex > phaseIndex || !isResearching) {
          statuses[phase] = 'completed';
        } else if (phase === currentPhase) {
          statuses[phase] = 'current';
        }
      }
    }

    return statuses;
  }, [progress, currentPhase, isResearching, error]);

  // Get latest progress data for each phase
  const latestProgressByPhase = useMemo(() => {
    const latest: Partial<Record<ResearchPhase, ResearchProgress>> = {};

    for (const p of progress) {
      latest[p.phase] = p;
    }

    return latest;
  }, [progress]);

  // Calculate overall progress percentage
  const progressPercentage = useMemo(() => {
    const completedCount = PHASE_ORDER.filter(
      (phase) => phaseStatuses[phase] === 'completed'
    ).length;

    // Add 0.5 for current phase
    const currentCount = currentPhase && isResearching ? 0.5 : 0;

    return Math.round(((completedCount + currentCount) / (PHASE_ORDER.length - 1)) * 100); // -1 because 'complete' is not a real phase
  }, [phaseStatuses, currentPhase, isResearching]);

  // Toggle phase expansion
  const togglePhase = (phase: ResearchPhase) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(phase)) {
        next.delete(phase);
      } else {
        next.add(phase);
      }
      return next;
    });

    onPhaseClick?.(phase);
  };

  // Filter out 'start' and 'complete' from display (they are implicit)
  const displayPhases = PHASE_ORDER.filter((p) => p !== 'start' && p !== 'complete');

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 shadow-sm p-4"
      data-testid="research-progress-tracker"
    >
      {/* Header with progress bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-700">Recherche-Fortschritt</h3>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">
              {isResearching ? `${progressPercentage}%` : 'Abgeschlossen'}
            </span>
            {/* Sprint 120 Bug 120.2: Dismiss button */}
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                aria-label="Schließen"
                data-testid="research-progress-dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              error ? 'bg-red-500' : isResearching ? 'bg-blue-500' : 'bg-green-500'
            }`}
            style={{ width: `${progressPercentage}%` }}
            role="progressbar"
            aria-valuenow={progressPercentage}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Research progress"
          />
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div
          className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm"
          role="alert"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Phase list */}
      <div className="space-y-2">
        {displayPhases.map((phase) => (
          <PhaseItem
            key={phase}
            phase={phase}
            status={phaseStatuses[phase]}
            progressData={latestProgressByPhase[phase]}
            isExpanded={expandedPhases.has(phase)}
            onToggle={() => togglePhase(phase)}
          />
        ))}
      </div>

      {/* Current iteration indicator */}
      {progress.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>Aktuelle Iteration</span>
            <span className="font-medium">
              {Math.max(...progress.map((p) => p.iteration), 0)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
