/**
 * DeepResearchUI Component
 * Sprint 116.10: Deep Research Multi-Step (13 SP)
 *
 * Main component for deep research interface with multi-step workflow,
 * intermediate results display, and export functionality.
 *
 * Features:
 * - Query input with validation
 * - Start/Cancel controls
 * - Real-time progress tracking
 * - Intermediate results display
 * - Final synthesis with export
 * - Error handling
 */

import { useState, useEffect } from 'react';
import {
  Send,
  StopCircle,
  Loader2,
  Download,
  AlertCircle,
} from 'lucide-react';
import { ResearchProgressTracker } from './ResearchProgressTracker';
import { IntermediateResults } from './IntermediateResults';
import { FinalSynthesis } from './FinalSynthesis';
import type {
  DeepResearchResponse,
  DeepResearchStatus,
  ResearchPhase,
  ResearchProgress,
} from '../../types/research';

interface DeepResearchUIProps {
  /** Default namespace for research */
  defaultNamespace?: string;
  /** Callback when research completes */
  onComplete?: (result: DeepResearchResponse) => void;
  /** Callback when research errors */
  onError?: (error: string) => void;
}

/**
 * API base URL from environment
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * DeepResearchUI Component
 */
export function DeepResearchUI({
  defaultNamespace = 'default',
  onComplete,
  onError,
}: DeepResearchUIProps) {
  // Research state
  const [query, setQuery] = useState('');
  const [isResearching, setIsResearching] = useState(false);
  const [researchId, setResearchId] = useState<string | null>(null);
  const [status, setStatus] = useState<DeepResearchStatus | null>(null);
  const [result, setResult] = useState<DeepResearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Progress tracking
  const [progressHistory, setProgressHistory] = useState<ResearchProgress[]>([]);
  const [currentPhase, setCurrentPhase] = useState<ResearchPhase>('pending');

  // Poll interval for status updates
  const [pollInterval, setPollInterval] = useState<number | null>(null);

  /**
   * Start deep research
   */
  const startResearch = async () => {
    if (!query.trim()) {
      setError('Please enter a research question');
      return;
    }

    setIsResearching(true);
    setError(null);
    setProgressHistory([]);
    setCurrentPhase('pending');
    setResult(null);

    try {
      // Start research
      const response = await fetch(`${API_BASE_URL}/api/v1/research/deep`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          namespace: defaultNamespace,
          max_iterations: 3,
          timeout_seconds: 180,
          step_timeout_seconds: 60,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start research: ${response.statusText}`);
      }

      const data: DeepResearchResponse = await response.json();
      setResearchId(data.id);

      // Start polling for status
      const interval = window.setInterval(() => {
        pollStatus(data.id);
      }, 1000); // Poll every second

      setPollInterval(interval);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to start research';
      setError(errorMsg);
      setIsResearching(false);
      onError?.(errorMsg);
    }
  };

  /**
   * Poll research status
   */
  const pollStatus = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/research/deep/${id}/status`);

      if (!response.ok) {
        throw new Error(`Failed to get status: ${response.statusText}`);
      }

      const statusData: DeepResearchStatus = await response.json();
      setStatus(statusData);

      // Update current phase
      setCurrentPhase(mapStatusToPhase(statusData.status));

      // Add to progress history
      setProgressHistory((prev) => [
        ...prev,
        {
          phase: mapStatusToPhase(statusData.status),
          message: `${statusData.current_step} (${statusData.progress_percent}%)`,
          iteration: 0,
          metadata: {
            progress_percent: statusData.progress_percent,
            estimated_time_remaining_ms: statusData.estimated_time_remaining_ms,
          },
        },
      ]);

      // If complete, error, or cancelled, stop polling and get full result
      if (['complete', 'error', 'cancelled'].includes(statusData.status)) {
        if (pollInterval !== null) {
          clearInterval(pollInterval);
          setPollInterval(null);
        }
        setIsResearching(false);

        // Get full result
        await getFullResult(id);
      }
    } catch (err) {
      console.error('Failed to poll status:', err);
    }
  };

  /**
   * Get full research result
   */
  const getFullResult = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/research/deep/${id}`);

      if (!response.ok) {
        throw new Error(`Failed to get result: ${response.statusText}`);
      }

      const resultData: DeepResearchResponse = await response.json();
      setResult(resultData);

      if (resultData.error) {
        setError(resultData.error);
        onError?.(resultData.error);
      } else if (resultData.status === 'complete') {
        onComplete?.(resultData);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to get result';
      setError(errorMsg);
      onError?.(errorMsg);
    }
  };

  /**
   * Cancel research
   */
  const cancelResearch = async () => {
    if (!researchId) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/research/deep/${researchId}/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          reason: 'User cancelled',
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to cancel research: ${response.statusText}`);
      }

      // Stop polling
      if (pollInterval !== null) {
        clearInterval(pollInterval);
        setPollInterval(null);
      }

      setIsResearching(false);
      setError('Research cancelled by user');
    } catch (err) {
      console.error('Failed to cancel research:', err);
    }
  };

  /**
   * Export research results
   */
  const exportResults = async (format: 'markdown' | 'pdf') => {
    if (!researchId) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/research/deep/${researchId}/export?format=${format}&include_sources=true&include_intermediate=true`
      );

      if (!response.ok) {
        throw new Error(`Failed to export: ${response.statusText}`);
      }

      // Download file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `research_${researchId}.${format === 'pdf' ? 'pdf' : 'md'}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Failed to export:', err);
      setError(err instanceof Error ? err.message : 'Failed to export');
    }
  };

  /**
   * Map status to research phase
   */
  const mapStatusToPhase = (statusVal: string): ResearchPhase => {
    const phaseMap: Record<string, ResearchPhase> = {
      pending: 'start',
      decomposing: 'plan',
      retrieving: 'search',
      analyzing: 'evaluate',
      synthesizing: 'synthesize',
      complete: 'complete',
      error: 'complete',
      cancelled: 'complete',
    };

    return phaseMap[statusVal] || 'start';
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollInterval !== null) {
        clearInterval(pollInterval);
      }
    };
  }, [pollInterval]);

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6" data-testid="deep-research-ui">
      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Deep Research</h1>
        <p className="text-gray-600">
          Conduct comprehensive multi-step research with intermediate results and citations.
        </p>
      </div>

      {/* Query Input */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <label htmlFor="research-query" className="block text-sm font-medium text-gray-700 mb-2">
          Research Question
        </label>
        <div className="flex gap-3">
          <textarea
            id="research-query"
            data-testid="research-query-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isResearching}
            placeholder="Enter your research question (e.g., 'What are the latest advancements in quantum computing?')"
            className="flex-grow p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            rows={3}
          />
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between mt-4">
          <div className="text-sm text-gray-500">
            {isResearching ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Researching...
              </span>
            ) : (
              <span>Enter a question to start deep research</span>
            )}
          </div>

          <div className="flex gap-2">
            {isResearching ? (
              <button
                onClick={cancelResearch}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                data-testid="cancel-research-button"
              >
                <StopCircle className="w-4 h-4" />
                Cancel
              </button>
            ) : (
              <button
                onClick={startResearch}
                disabled={!query.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                data-testid="start-research-button"
              >
                <Send className="w-4 h-4" />
                Start Research
              </button>
            )}

            {result && result.status === 'complete' && (
              <button
                onClick={() => exportResults('markdown')}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                data-testid="export-markdown-button"
              >
                <Download className="w-4 h-4" />
                Export
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div
          className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3"
          role="alert"
          data-testid="research-error"
        >
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-grow">
            <h3 className="text-sm font-medium text-red-800">Error</h3>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Progress Tracker */}
      {(isResearching || progressHistory.length > 0) && (
        <ResearchProgressTracker
          progress={progressHistory}
          currentPhase={currentPhase}
          isResearching={isResearching}
          error={error || undefined}
        />
      )}

      {/* Intermediate Results */}
      {result && result.intermediate_answers && result.intermediate_answers.length > 0 && (
        <IntermediateResults intermediateAnswers={result.intermediate_answers} />
      )}

      {/* Final Synthesis */}
      {result && result.final_answer && (
        <FinalSynthesis
          query={result.query}
          finalAnswer={result.final_answer}
          sources={result.sources}
          totalTimeMs={result.total_time_ms}
          onExport={exportResults}
        />
      )}
    </div>
  );
}
