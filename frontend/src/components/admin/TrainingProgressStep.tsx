/**
 * TrainingProgressStep Component
 * Sprint 45 Feature 45.4, 45.13: Domain Training Admin UI with SSE Live Log
 *
 * Step 3 of domain wizard: Real-time training progress with SSE streaming
 * Shows FULL content (prompts, responses, evaluations) - NOT truncated.
 */

import { useState } from 'react';
import { useTrainingStatus, useTrainingStream } from '../../hooks/useDomainTraining';
import { TrainingLiveLog } from './TrainingLiveLog';

interface TrainingProgressStepProps {
  domainName: string;
  trainingRunId?: string | null;
  onComplete: () => void;
}

export function TrainingProgressStep({
  domainName,
  trainingRunId = null,
  onComplete,
}: TrainingProgressStepProps) {
  const { data: status, isLoading } = useTrainingStatus(domainName, true);
  const [showLiveLog, setShowLiveLog] = useState(true);

  // SSE stream for live events (Feature 45.13)
  // Connect as soon as we have a training_run_id (don't wait for status === 'training')
  const sseStream = useTrainingStream(
    domainName,
    trainingRunId,
    !!trainingRunId // Connect immediately when we have a run ID
  );

  // Use SSE progress if available, fallback to polling
  const sseProgress = sseStream.progress;
  const pollingProgress = status?.progress_percent || 0;
  const progress = sseProgress > 0 ? sseProgress : pollingProgress;

  // No auto-close - let user review results and click Done manually

  const isComplete = status?.status === 'ready' || sseStream.isComplete;
  const isFailed = status?.status === 'failed' || sseStream.isFailed;

  return (
    <div className="space-y-6" data-testid="training-progress-step">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Training in Progress</h2>
        <p className="text-gray-600">Step 3 of 3: Training domain model</p>
      </div>

      {/* Status */}
      <div className="p-6 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-center space-x-4">
          {!isComplete && !isFailed && (
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          )}
          {isComplete && (
            <svg
              className="w-8 h-8 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          )}
          {isFailed && (
            <svg
              className="w-8 h-8 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          )}
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900" data-testid="training-status">
              {isLoading && 'Initializing...'}
              {!isLoading && status?.status === 'pending' && 'Pending'}
              {!isLoading && status?.status === 'training' && 'Training...'}
              {!isLoading && status?.status === 'ready' && 'Training Complete!'}
              {!isLoading && status?.status === 'failed' && 'Training Failed'}
            </h3>
            <p className="text-sm text-gray-600">
              Domain: {domainName}
              {sseStream.phase && (
                <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                  {sseStream.phase.replace('_', ' ')}
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        {!isFailed && (
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Progress</span>
              <span className="font-semibold" data-testid="training-progress-percent">
                {progress.toFixed(0)}%
              </span>
            </div>
            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  isComplete ? 'bg-green-500' : 'bg-blue-600'
                }`}
                style={{ width: `${progress}%` }}
                data-testid="training-progress-bar"
              />
            </div>
          </div>
        )}

        {/* Error Message */}
        {isFailed && status?.error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800" data-testid="training-error">
              {status.error}
            </p>
          </div>
        )}
      </div>

      {/* Live Log Toggle */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowLiveLog(!showLiveLog)}
          className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          <span>{showLiveLog ? '▼' : '▶'}</span>
          {showLiveLog ? 'Hide' : 'Show'} Live Training Log
          {sseStream.events.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs">
              {sseStream.events.length}
            </span>
          )}
        </button>
        {sseStream.isConnected && (
          <span className="text-xs text-green-600 flex items-center gap-1">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            SSE Connected
          </span>
        )}
      </div>

      {/* SSE Live Log (Feature 45.13) */}
      {showLiveLog && (
        <TrainingLiveLog
          events={sseStream.events}
          isConnected={sseStream.isConnected}
          latestEvent={sseStream.latestEvent}
        />
      )}

      {/* Legacy Training Logs (fallback) */}
      {!showLiveLog && status?.logs && status.logs.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-700">Training Logs (Polling)</h3>
          <div
            className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs max-h-64 overflow-y-auto"
            data-testid="training-logs"
          >
            {status.logs.map((log, idx) => (
              <div key={idx} className="py-1">
                {log}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end pt-4 border-t">
        <button
          onClick={onComplete}
          disabled={!isComplete && !isFailed}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          data-testid="training-complete-button"
        >
          {isComplete ? 'Done' : isFailed ? 'Close' : 'Training...'}
        </button>
      </div>
    </div>
  );
}
