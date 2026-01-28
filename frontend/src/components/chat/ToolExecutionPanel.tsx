/**
 * ToolExecutionPanel Component
 * Sprint 119 Feature 119.1: Skills/Tools Chat Integration
 *
 * Panel showing tool execution in chat message flow.
 * Displays tool name, status, progress, and output.
 * Supports concurrent tool executions.
 */

import { useState, useCallback } from 'react';
import {
  Terminal,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Code,
  Search,
  Globe,
  Wrench,
  Copy,
  Check,
} from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { ToolExecutionState } from '../../types/skills-events';

interface ToolExecutionPanelProps {
  /** Tool execution state to display */
  execution: ToolExecutionState;
}

/**
 * Get status icon based on tool execution status
 */
function getStatusIcon(status: ToolExecutionState['status']) {
  switch (status) {
    case 'running':
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
    case 'success':
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    case 'error':
      return <XCircle className="w-4 h-4 text-red-500" />;
    case 'timeout':
      return <AlertTriangle className="w-4 h-4 text-amber-500" />;
  }
}

/**
 * Get status badge color classes
 */
function getStatusBadgeClass(status: ToolExecutionState['status']): string {
  switch (status) {
    case 'running':
      return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400';
    case 'success':
      return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400';
    case 'error':
      return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400';
    case 'timeout':
      return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400';
  }
}

/**
 * Format duration in milliseconds
 */
function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return '';
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Format tool input/output for display
 */
function formatData(data: unknown): string {
  if (typeof data === 'string') return data;
  if (data === null || data === undefined) return '';
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}

/**
 * Get syntax highlighting language based on tool name
 */
function getOutputLanguage(toolName: string): string {
  const name = toolName.toLowerCase();
  if (name === 'bash') return 'bash';
  if (name === 'python') return 'python';
  if (name.includes('search') || name.includes('fetch') || name.includes('api')) return 'json';
  return 'text';
}

/**
 * Get tool icon based on tool type
 */
function getToolIcon(toolName: string) {
  const name = toolName.toLowerCase();
  if (name === 'bash') return <Terminal className="w-4 h-4 text-gray-700 dark:text-gray-300" />;
  if (name === 'python') return <Code className="w-4 h-4 text-blue-600 dark:text-blue-400" />;
  if (name.includes('search')) return <Search className="w-4 h-4 text-green-600 dark:text-green-400" />;
  if (name.includes('browser') || name.includes('fetch')) return <Globe className="w-4 h-4 text-purple-600 dark:text-purple-400" />;
  return <Wrench className="w-4 h-4 text-gray-700 dark:text-gray-300" />;
}

/**
 * ToolExecutionPanel displays a single tool execution
 */
export function ToolExecutionPanel({ execution }: ToolExecutionPanelProps) {
  const [isInputExpanded, setIsInputExpanded] = useState(false);
  const [isOutputExpanded, setIsOutputExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  const statusIcon = getStatusIcon(execution.status);
  const statusBadgeClass = getStatusBadgeClass(execution.status);
  const toolIcon = getToolIcon(execution.tool);
  const outputLanguage = getOutputLanguage(execution.tool);

  const inputText = formatData(execution.input);
  const outputText = formatData(execution.output);
  const hasInput = inputText.trim().length > 0 && Object.keys(execution.input).length > 0;
  const hasOutput = outputText.trim().length > 0;

  /**
   * Copy text to clipboard
   */
  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.error('Failed to copy to clipboard');
    }
  }, []);

  return (
    <div
      className="my-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
      data-testid={`tool-${execution.tool}`}
      data-tool={execution.tool}
      data-status={execution.status}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded bg-gray-200 dark:bg-gray-700">
            {toolIcon}
          </div>
          <div>
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {execution.tool}
            </div>
            {execution.server && (
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {execution.server}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Duration */}
          {execution.duration_ms !== undefined && (
            <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              {formatDuration(execution.duration_ms)}
            </span>
          )}

          {/* Status Badge */}
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium ${statusBadgeClass}`}
            data-testid={`tool-status-${execution.status}`}
          >
            {statusIcon}
            {execution.status === 'running' ? 'Running' : execution.status === 'success' ? 'Success' : execution.status === 'error' ? 'Error' : 'Timeout'}
          </span>
        </div>
      </div>

      {/* Input Section (collapsible) */}
      {hasInput && (
        <div className="border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setIsInputExpanded(!isInputExpanded)}
            className="w-full flex items-center justify-between px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
            aria-expanded={isInputExpanded}
          >
            <span className="flex items-center gap-2 text-xs font-medium text-gray-600 dark:text-gray-400">
              {isInputExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              Input
            </span>
          </button>

          {isInputExpanded && (
            <div className="px-4 pb-3" data-testid="tool-input">
              <div className="max-h-[200px] overflow-y-auto rounded">
                <SyntaxHighlighter
                  language={outputLanguage}
                  style={oneDark}
                  customStyle={{
                    margin: 0,
                    padding: '12px',
                    fontSize: '12px',
                    borderRadius: '6px',
                  }}
                  wrapLongLines
                >
                  {inputText}
                </SyntaxHighlighter>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Progress Bar (for running state) */}
      {execution.status === 'running' && execution.progress !== undefined && (
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700" data-testid="tool-progress-indicator">
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${execution.progress}%` }}
                  data-testid="tool-progress-bar"
                />
              </div>
            </div>
            <span className="text-xs text-gray-600 dark:text-gray-400 font-medium">
              {Math.round(execution.progress)}%
            </span>
          </div>
          {execution.progressMessage && (
            <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
              {execution.progressMessage}
            </div>
          )}
        </div>
      )}

      {/* Output Section (for completed executions) */}
      {(execution.status === 'success' || execution.status === 'error') && (hasOutput || execution.error) && (
        <div className="border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setIsOutputExpanded(!isOutputExpanded)}
            className="w-full flex items-center justify-between px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
            aria-expanded={isOutputExpanded}
          >
            <span className="flex items-center gap-2 text-xs font-medium text-gray-600 dark:text-gray-400">
              {isOutputExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              {execution.status === 'error' ? 'Error Details' : 'Output'}
            </span>
            {/* Copy button (only shown for successful outputs) */}
            {execution.status === 'success' && hasOutput && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleCopy(outputText);
                }}
                className="flex items-center gap-1.5 px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
                title="Copy output"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            )}
          </button>

          {isOutputExpanded && (
            <div className="px-4 pb-3" data-testid="tool-result-output">
              {execution.error ? (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-700 dark:text-red-400">
                  {execution.error}
                </div>
              ) : hasOutput ? (
                <div className="max-h-[200px] overflow-y-auto rounded">
                  <SyntaxHighlighter
                    language={outputLanguage}
                    style={oneDark}
                    customStyle={{
                      margin: 0,
                      padding: '12px',
                      fontSize: '12px',
                      borderRadius: '6px',
                    }}
                    wrapLongLines
                  >
                    {outputText}
                  </SyntaxHighlighter>
                </div>
              ) : (
                <div className="text-xs text-gray-400 dark:text-gray-500 italic">
                  No output
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Timeout Message */}
      {execution.status === 'timeout' && (
        <div className="px-4 py-3" data-testid="tool-timeout-message">
          <div className="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-400">
            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <div>
              Tool execution timed out. The operation took too long to complete.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
