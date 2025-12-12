/**
 * TrainingProgressStep Component
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 *
 * Step 3 of domain wizard: Real-time training progress with logs
 */

import { useEffect } from 'react';
import { useTrainingStatus } from '../../hooks/useDomainTraining';

interface TrainingProgressStepProps {
  domainName: string;
  onComplete: () => void;
}

export function TrainingProgressStep({ domainName, onComplete }: TrainingProgressStepProps) {
  const { data: status, isLoading } = useTrainingStatus(domainName, true);

  // Auto-close on completion
  useEffect(() => {
    if (status?.status === 'ready') {
      // Give user time to see success message
      const timer = setTimeout(() => {
        onComplete();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [status, onComplete]);

  const isComplete = status?.status === 'ready';
  const isFailed = status?.status === 'failed';
  const progress = status?.progress || 0;

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
            <p className="text-sm text-gray-600">Domain: {domainName}</p>
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
        {isFailed && status.error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800" data-testid="training-error">
              {status.error}
            </p>
          </div>
        )}
      </div>

      {/* Training Logs */}
      {status?.logs && status.logs.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-700">Training Logs</h3>
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
