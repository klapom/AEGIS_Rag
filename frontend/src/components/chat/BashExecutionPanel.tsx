/**
 * BashExecutionPanel Component
 * Sprint 120 Feature 120.8: Bash Execution UI in Chat (8 SP)
 *
 * Integrated bash command execution panel for the chat interface.
 * Provides security-sandboxed bash command execution with:
 * - Command input with data-testid="bash-input"
 * - Execute button with data-testid="bash-execute-button"
 * - Output display with data-testid="bash-output"
 * - Approval dialog with data-testid="bash-approval-dialog"
 *
 * Security Features:
 * - Approval dialog before execution
 * - Sandboxed execution environment
 * - Timeout protection (30s default)
 * - Clear warning about command execution
 */

import { useState, useCallback } from 'react';
import { Terminal, Play, AlertCircle, CheckCircle, Clock, Shield } from 'lucide-react';

/**
 * Props for BashExecutionPanel
 */
export interface BashExecutionPanelProps {
  /** API base URL for bash execution */
  apiBaseUrl?: string;
  /** Optional auth token for API calls */
  authToken?: string;
  /** Callback when command is executed */
  onExecute?: (command: string, result: BashExecutionResult) => void;
}

/**
 * Bash execution result from API
 */
export interface BashExecutionResult {
  result?: {
    success: boolean;
    stdout?: string;
    stderr?: string;
    exit_code?: number;
  };
  execution_time_ms: number;
  status: 'success' | 'error' | 'timeout';
  error_message?: string;
}

/**
 * BashExecutionPanel component for chat interface
 */
export function BashExecutionPanel({
  apiBaseUrl = 'http://localhost:8000',
  authToken,
  onExecute,
}: BashExecutionPanelProps) {
  const [command, setCommand] = useState('');
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<BashExecutionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);

  /**
   * Show approval dialog when execute is clicked
   */
  const handleExecuteClick = useCallback(() => {
    if (!command.trim()) {
      setError('Command cannot be empty');
      return;
    }
    setShowApprovalDialog(true);
  }, [command]);

  /**
   * Cancel execution and close approval dialog
   */
  const handleCancelExecution = useCallback(() => {
    setShowApprovalDialog(false);
  }, []);

  /**
   * Execute bash command after approval
   */
  const handleApprovedExecution = useCallback(async () => {
    setShowApprovalDialog(false);
    setExecuting(true);
    setError(null);
    setResult(null);

    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const response = await fetch(`${apiBaseUrl}/api/v1/mcp/tools/bash/execute`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          parameters: { command: command.trim() },
          timeout: 30,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const executionResult: BashExecutionResult = await response.json();
      setResult(executionResult);
      onExecute?.(command.trim(), executionResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Command execution failed';
      setError(errorMessage);
    } finally {
      setExecuting(false);
    }
  }, [command, apiBaseUrl, authToken, onExecute]);

  return (
    <div
      className="bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
      data-testid="bash-execution-panel"
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <Terminal className="w-5 h-5 text-blue-600 dark:text-blue-400" />
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Bash Command Execution</h3>
      </div>

      {/* Security Warning */}
      <div className="px-4 py-3 bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-800">
        <div className="flex items-start gap-2 text-sm">
          <Shield className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="text-yellow-800 dark:text-yellow-300">
            Commands are executed in a sandboxed environment with a 30-second timeout.
            Always verify commands before execution.
          </div>
        </div>
      </div>

      {/* Command Input */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <label htmlFor="bash-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Command
        </label>
        <textarea
          id="bash-input"
          data-testid="bash-input"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder="echo 'Hello, World!'"
          rows={3}
          disabled={executing}
          className="w-full px-3 py-2 font-mono text-sm bg-gray-900 dark:bg-gray-950 text-gray-100 border border-gray-600 dark:border-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed resize-none"
        />
      </div>

      {/* Execute Button */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <button
          data-testid="bash-execute-button"
          onClick={handleExecuteClick}
          disabled={executing || !command.trim()}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          <Play className="w-4 h-4" />
          {executing ? 'Executing...' : 'Execute Command'}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="px-4 py-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-700 dark:text-red-400">Execution Error</p>
              <p className="text-sm text-red-600 dark:text-red-400 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Output Display */}
      {result && (
        <div
          data-testid="bash-output"
          className="px-4 py-3 bg-gray-50 dark:bg-gray-900/50"
        >
          {/* Status Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              {result.result?.exit_code === 0 ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-500" />
              )}
              <span
                className={`font-medium text-sm ${
                  result.result?.exit_code === 0
                    ? 'text-green-700 dark:text-green-400'
                    : 'text-red-700 dark:text-red-400'
                }`}
              >
                Exit Code: {result.result?.exit_code ?? 'N/A'}
              </span>
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {result.execution_time_ms}ms
            </span>
          </div>

          {/* stdout */}
          {result.result?.stdout && (
            <div className="mb-3">
              <div className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">stdout:</div>
              <pre className="p-3 bg-gray-900 dark:bg-black text-gray-100 text-xs font-mono rounded overflow-x-auto whitespace-pre-wrap break-all">
                {result.result.stdout}
              </pre>
            </div>
          )}

          {/* stderr */}
          {result.result?.stderr && (
            <div className="mb-3">
              <div className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">stderr:</div>
              <pre className="p-3 bg-red-950/50 text-red-300 text-xs font-mono rounded overflow-x-auto whitespace-pre-wrap break-all">
                {result.result.stderr}
              </pre>
            </div>
          )}

          {/* No output */}
          {!result.result?.stdout && !result.result?.stderr && (
            <p className="text-xs text-gray-400 dark:text-gray-500 italic">No output</p>
          )}
        </div>
      )}

      {/* Approval Dialog */}
      {showApprovalDialog && (
        <div
          data-testid="bash-approval-dialog"
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={handleCancelExecution}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Dialog Header */}
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Confirm Command Execution
                </h3>
              </div>
            </div>

            {/* Dialog Content */}
            <div className="px-6 py-4">
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
                You are about to execute the following bash command in a sandboxed environment:
              </p>
              <pre className="p-3 bg-gray-900 dark:bg-black text-gray-100 text-sm font-mono rounded overflow-x-auto mb-4">
                {command}
              </pre>
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded p-3">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-yellow-800 dark:text-yellow-300">
                    Please verify the command is safe before proceeding. Destructive operations may affect the system.
                  </p>
                </div>
              </div>
            </div>

            {/* Dialog Actions */}
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end gap-3">
              <button
                onClick={handleCancelExecution}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => void handleApprovedExecution()}
                className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
              >
                Execute Command
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default BashExecutionPanel;
