/**
 * BashToolExecutor Component
 * Sprint 116 Feature 116.6: Bash Tool Execution UI (8 SP)
 *
 * Dedicated UI for bash command execution with:
 * - Command input with syntax highlighting
 * - Execute button with loading state
 * - Output display (stdout/stderr)
 * - Command history (last 10 commands)
 * - Exit code visualization
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Terminal,
  Play,
  Clock,
  History,
  Trash2,
  Copy,
  Check,
  AlertCircle,
  CheckCircle,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

/**
 * Props for BashToolExecutor
 */
export interface BashToolExecutorProps {
  /** API base URL for tool execution */
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
 * Command history entry
 */
interface CommandHistoryEntry {
  id: string;
  command: string;
  result: BashExecutionResult;
  timestamp: Date;
}

/**
 * Local storage key for command history
 */
const HISTORY_STORAGE_KEY = 'aegis_bash_command_history';
const MAX_HISTORY_SIZE = 10;

/**
 * Load command history from localStorage
 */
function loadHistoryFromStorage(): CommandHistoryEntry[] {
  try {
    const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    // Convert timestamp strings back to Date objects
    return parsed.map((entry: CommandHistoryEntry) => ({
      ...entry,
      timestamp: new Date(entry.timestamp),
    }));
  } catch {
    return [];
  }
}

/**
 * Save command history to localStorage
 */
function saveHistoryToStorage(history: CommandHistoryEntry[]): void {
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  } catch (error) {
    console.error('Failed to save command history:', error);
  }
}

/**
 * BashToolExecutor component
 */
export function BashToolExecutor({
  apiBaseUrl = 'http://localhost:8000',
  authToken,
  onExecute,
}: BashToolExecutorProps) {
  const [command, setCommand] = useState('');
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<BashExecutionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<CommandHistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(true);
  const [copiedCommand, setCopiedCommand] = useState(false);
  const [expandedOutput, setExpandedOutput] = useState<{
    stdout: boolean;
    stderr: boolean;
  }>({ stdout: true, stderr: true });

  // Load history from localStorage on mount
  useEffect(() => {
    setHistory(loadHistoryFromStorage());
  }, []);

  /**
   * Execute bash command via API
   */
  const handleExecute = useCallback(async () => {
    if (!command.trim()) {
      setError('Command cannot be empty');
      return;
    }

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

      // Add to history
      const historyEntry: CommandHistoryEntry = {
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        command: command.trim(),
        result: executionResult,
        timestamp: new Date(),
      };

      const newHistory = [historyEntry, ...history.slice(0, MAX_HISTORY_SIZE - 1)];
      setHistory(newHistory);
      saveHistoryToStorage(newHistory);

      // Callback
      onExecute?.(command.trim(), executionResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Command execution failed';
      setError(errorMessage);
    } finally {
      setExecuting(false);
    }
  }, [command, history, apiBaseUrl, authToken, onExecute]);

  /**
   * Clear command history
   */
  const handleClearHistory = useCallback(() => {
    setHistory([]);
    saveHistoryToStorage([]);
  }, []);

  /**
   * Load command from history
   */
  const handleLoadFromHistory = useCallback((entry: CommandHistoryEntry) => {
    setCommand(entry.command);
    setResult(null);
    setError(null);
  }, []);

  /**
   * Copy command to clipboard
   */
  const handleCopyCommand = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopiedCommand(true);
      setTimeout(() => setCopiedCommand(false), 2000);
    } catch {
      console.error('Failed to copy command');
    }
  }, [command]);

  /**
   * Handle Enter key to execute
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        void handleExecute();
      }
    },
    [handleExecute]
  );

  return (
    <div
      className="bg-white rounded-xl border-2 border-gray-200 overflow-hidden"
      data-testid="bash-tool-executor"
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-blue-600" />
          <h2 className="font-semibold text-gray-900">Bash Command Execution</h2>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Execute bash commands with real-time output (Ctrl+Enter to run)
        </p>
      </div>

      {/* Command Input */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700">Command</label>
          <button
            onClick={() => void handleCopyCommand()}
            disabled={!command.trim()}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="copy-command-button"
            aria-label="Copy command"
          >
            {copiedCommand ? (
              <>
                <Check className="w-3 h-3 text-green-500" />
                <span className="text-green-500">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                Copy
              </>
            )}
          </button>
        </div>

        <div className="relative rounded-lg overflow-hidden border border-gray-300 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500">
          <textarea
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="ls -la&#10;pwd&#10;echo 'Hello World'"
            rows={3}
            className="w-full px-3 py-2 font-mono text-sm bg-gray-900 text-gray-100 resize-none focus:outline-none"
            data-testid="bash-command-input"
          />
        </div>

        <p className="mt-2 text-xs text-gray-500">
          Press <kbd className="px-1.5 py-0.5 bg-gray-200 rounded text-xs">Ctrl+Enter</kbd> to
          execute
        </p>
      </div>

      {/* Execute Button */}
      <div className="p-4 border-b border-gray-100">
        <button
          onClick={() => void handleExecute()}
          disabled={executing || !command.trim()}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          data-testid="execute-bash-button"
        >
          <Play className="w-4 h-4" />
          {executing ? 'Executing...' : 'Execute Command'}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div
          className="p-4 bg-red-50 border-b border-red-100"
          data-testid="bash-execution-error"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-700">Execution Error</p>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div
          className="p-4 border-b border-gray-100"
          data-testid="bash-execution-result"
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
                className={`font-medium ${
                  result.result?.exit_code === 0 ? 'text-green-700' : 'text-red-700'
                }`}
              >
                Exit Code: {result.result?.exit_code ?? 'N/A'}
              </span>
            </div>
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {result.execution_time_ms}ms
            </span>
          </div>

          {/* stdout */}
          {result.result?.stdout && (
            <div className="mb-2">
              <button
                onClick={() =>
                  setExpandedOutput((prev) => ({ ...prev, stdout: !prev.stdout }))
                }
                className="w-full flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 text-gray-300 text-xs font-medium rounded-t-md hover:bg-gray-700 transition-colors"
                data-testid="toggle-stdout"
              >
                {expandedOutput.stdout ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
                stdout
              </button>
              {expandedOutput.stdout && (
                <div className="max-h-[200px] overflow-y-auto border border-gray-700 rounded-b-md">
                  <SyntaxHighlighter
                    language="bash"
                    style={oneDark}
                    customStyle={{
                      margin: 0,
                      padding: '12px',
                      fontSize: '12px',
                      borderRadius: '0 0 6px 6px',
                    }}
                    wrapLongLines
                  >
                    {result.result.stdout}
                  </SyntaxHighlighter>
                </div>
              )}
            </div>
          )}

          {/* stderr */}
          {result.result?.stderr && (
            <div>
              <button
                onClick={() =>
                  setExpandedOutput((prev) => ({ ...prev, stderr: !prev.stderr }))
                }
                className="w-full flex items-center gap-1.5 px-3 py-1.5 bg-red-900/50 text-red-300 text-xs font-medium rounded-t-md hover:bg-red-900/70 transition-colors"
                data-testid="toggle-stderr"
              >
                {expandedOutput.stderr ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
                stderr
              </button>
              {expandedOutput.stderr && (
                <div className="max-h-[200px] overflow-y-auto border border-red-800 rounded-b-md">
                  <pre className="p-3 text-xs font-mono text-red-300 bg-red-950/50 whitespace-pre-wrap break-all">
                    {result.result.stderr}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* No output */}
          {!result.result?.stdout && !result.result?.stderr && (
            <p className="text-xs text-gray-400 italic">No output</p>
          )}
        </div>
      )}

      {/* Command History */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
            data-testid="toggle-history"
          >
            <History className="w-4 h-4" />
            Command History ({history.length})
            {showHistory ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
          </button>
          {history.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-red-500 transition-colors"
              data-testid="clear-history"
            >
              <Trash2 className="w-3 h-3" />
              Clear
            </button>
          )}
        </div>

        {showHistory && history.length > 0 && (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {history.map((entry) => (
              <button
                key={entry.id}
                onClick={() => handleLoadFromHistory(entry)}
                className={`w-full p-3 rounded-lg border text-left transition-all hover:border-blue-300 hover:bg-blue-50 ${
                  entry.result.result?.exit_code === 0
                    ? 'bg-green-50 border-green-200'
                    : 'bg-red-50 border-red-200'
                }`}
                data-testid={`history-entry-${entry.id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <code className="text-xs font-mono text-gray-900 block truncate">
                      {entry.command}
                    </code>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-500">
                        {entry.timestamp.toLocaleTimeString()}
                      </span>
                      <span className="text-xs text-gray-400">•</span>
                      <span className="text-xs text-gray-500">
                        {entry.result.execution_time_ms}ms
                      </span>
                    </div>
                  </div>
                  <div>
                    {entry.result.result?.exit_code === 0 ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-red-500" />
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {showHistory && history.length === 0 && (
          <div className="text-center py-8">
            <History className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No command history yet</p>
            <p className="text-xs text-gray-400 mt-1">
              Execute a command to see it here
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default BashToolExecutor;
