/**
 * ToolExecutionDisplay Component
 * Sprint 63 Feature 63.10: Tool Output Visualization in Chat UI
 *
 * Displays tool execution results (bash, python) with syntax highlighting,
 * stdout/stderr output, and exit code visualization.
 */

import { useState, useCallback } from 'react';
import { Terminal, Code, ChevronDown, ChevronRight, Copy, Check, Clock, Server, AlertCircle, CheckCircle } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { ToolExecutionStep, ToolExecutionDisplayProps } from '../../types/reasoning';

/**
 * Get the appropriate icon for tool type
 */
function getToolIcon(toolName: string): React.ReactNode {
  const iconClass = 'w-4 h-4';
  switch (toolName.toLowerCase()) {
    case 'bash':
      return <Terminal className={iconClass} />;
    case 'python':
      return <Code className={iconClass} />;
    default:
      return <Terminal className={iconClass} />;
  }
}

/**
 * Get syntax highlighter language from tool name
 */
function getLanguage(toolName: string): string {
  switch (toolName.toLowerCase()) {
    case 'bash':
      return 'bash';
    case 'python':
      return 'python';
    default:
      return 'text';
  }
}

/**
 * Get the command or code from tool input
 */
function getInputCode(step: ToolExecutionStep): string {
  if (step.input.command) {
    return step.input.command;
  }
  if (step.input.code) {
    return step.input.code;
  }
  if (step.input.arguments) {
    return JSON.stringify(step.input.arguments, null, 2);
  }
  return '';
}

/**
 * Format duration in milliseconds to human-readable string
 */
function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return '';
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Collapsible output section component
 */
function OutputSection({
  title,
  content,
  isError = false,
  defaultExpanded = true,
}: {
  title: string;
  content: string;
  isError?: boolean;
  defaultExpanded?: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.error('Failed to copy to clipboard');
    }
  }, [content]);

  if (!content || content.trim() === '') return null;

  const bgColor = isError ? 'bg-red-950/50' : 'bg-gray-900/50';
  const borderColor = isError ? 'border-red-800/50' : 'border-gray-700/50';
  const textColor = isError ? 'text-red-300' : 'text-gray-300';
  const headerBg = isError ? 'bg-red-900/30' : 'bg-gray-800/50';

  return (
    <div
      className={`rounded-md border ${borderColor} overflow-hidden mt-2`}
      data-testid={`output-section-${isError ? 'stderr' : 'stdout'}`}
    >
      <div
        className={`w-full flex items-center justify-between px-3 py-1.5 ${headerBg} text-xs font-medium ${textColor}`}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        onClick={() => setIsExpanded(!isExpanded)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }
        }}
      >
        <span className="flex items-center gap-1.5 cursor-pointer">
          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          {title}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleCopy();
          }}
          className="p-1 hover:bg-white/10 rounded transition-colors"
          title="Copy output"
          aria-label="Copy output"
          data-testid="copy-output-button"
        >
          {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
        </button>
      </div>
      {isExpanded && (
        <div className={`${bgColor} max-h-[200px] overflow-y-auto`}>
          <pre className={`p-3 text-xs font-mono ${textColor} whitespace-pre-wrap break-all`}>
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}

/**
 * Exit code badge component
 */
function ExitCodeBadge({ exitCode }: { exitCode?: number }) {
  if (exitCode === undefined || exitCode === null) return null;

  const isSuccess = exitCode === 0;
  const bgColor = isSuccess ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30';
  const textColor = isSuccess ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400';
  const icon = isSuccess
    ? <CheckCircle className="w-3 h-3" />
    : <AlertCircle className="w-3 h-3" />;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${bgColor} ${textColor}`}
      data-testid="exit-code-badge"
    >
      {icon}
      Exit: {exitCode}
    </span>
  );
}

/**
 * ToolExecutionDisplay component
 * Displays a single tool execution step with syntax highlighting and output
 */
export function ToolExecutionDisplay({ step }: ToolExecutionDisplayProps) {
  const [isCommandExpanded, setIsCommandExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  const inputCode = getInputCode(step);
  const language = getLanguage(step.tool_name);

  const handleCopyCommand = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(inputCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.error('Failed to copy command');
    }
  }, [inputCode]);

  return (
    <div
      className="bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
      data-testid="tool-execution-display"
      data-tool={step.tool_name}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-6 h-6 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
            {getToolIcon(step.tool_name)}
          </span>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {step.tool_name}
          </span>
          <span
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded text-xs"
            data-testid="server-badge"
          >
            <Server className="w-3 h-3" />
            {step.server}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {step.duration_ms !== undefined && (
            <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400" data-testid="duration-display">
              <Clock className="w-3 h-3" />
              {formatDuration(step.duration_ms)}
            </span>
          )}
          <ExitCodeBadge exitCode={step.output.exit_code} />
        </div>
      </div>

      {/* Command/Code Section */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <div
          className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
          role="button"
          tabIndex={0}
          aria-expanded={isCommandExpanded}
          data-testid="command-toggle"
          onClick={() => setIsCommandExpanded(!isCommandExpanded)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setIsCommandExpanded(!isCommandExpanded);
            }
          }}
        >
          <span className="flex items-center gap-1.5 text-xs font-medium text-gray-600 dark:text-gray-400">
            {isCommandExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            {step.tool_name === 'bash' ? 'Command' : step.tool_name === 'python' ? 'Code' : 'Input'}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleCopyCommand();
            }}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
            title="Copy command"
            aria-label="Copy command"
            data-testid="copy-command-button"
          >
            {copied ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3 text-gray-500" />}
          </button>
        </div>
        {isCommandExpanded && inputCode && (
          <div className="max-h-[150px] overflow-y-auto" data-testid="command-content">
            <SyntaxHighlighter
              language={language}
              style={oneDark}
              customStyle={{
                margin: 0,
                padding: '12px',
                fontSize: '12px',
                borderRadius: 0,
                background: '#1e1e1e',
              }}
              wrapLongLines
            >
              {inputCode}
            </SyntaxHighlighter>
          </div>
        )}
      </div>

      {/* Output Section */}
      <div className="px-3 py-2 space-y-1">
        {/* Standard Output */}
        <OutputSection
          title="stdout"
          content={step.output.stdout || ''}
          isError={false}
        />

        {/* Standard Error */}
        <OutputSection
          title="stderr"
          content={step.output.stderr || ''}
          isError={true}
        />

        {/* Error Message */}
        {step.output.error && (
          <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-xs text-red-700 dark:text-red-400" data-testid="error-message">
            <span className="font-medium">Error:</span> {step.output.error}
          </div>
        )}

        {/* Empty output indicator */}
        {!step.output.stdout && !step.output.stderr && !step.output.error && (
          <div className="text-xs text-gray-400 dark:text-gray-500 italic" data-testid="no-output">
            No output
          </div>
        )}
      </div>
    </div>
  );
}
