/**
 * MCPToolExecutionPanel Component
 * Sprint 72 Feature 72.1: MCP Tool Management UI
 *
 * Tool selection, parameter input form, execution, and result display.
 * Includes execution history log.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Wrench,
  Play,
  X,
  CheckCircle,
  XCircle,
  Clock,
  ChevronDown,
  Trash2,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { getMCPTools, getMCPTool, executeMCPTool } from '../../api/admin';
import type { MCPTool, MCPToolParameter, MCPExecutionResult } from '../../types/admin';

/**
 * Props for MCPToolExecutionPanel
 */
interface MCPToolExecutionPanelProps {
  selectedToolName?: string | null;
  onClearSelection?: () => void;
}

/**
 * Execution history entry
 */
interface ExecutionHistoryEntry extends MCPExecutionResult {
  id: string;
  parameters: Record<string, unknown>;
}

/**
 * MCPToolExecutionPanel - Tool execution with parameter form and history
 *
 * Features:
 * - Tool selection dropdown
 * - Dynamic parameter input form based on tool schema
 * - Execute button with loading state
 * - Result display (success/error)
 * - Execution history log (last 10 executions)
 */
export function MCPToolExecutionPanel({
  selectedToolName,
  onClearSelection,
}: MCPToolExecutionPanelProps) {
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parameters, setParameters] = useState<Record<string, unknown>>({});
  const [result, setResult] = useState<MCPExecutionResult | null>(null);
  const [history, setHistory] = useState<ExecutionHistoryEntry[]>([]);

  // Fetch all tools
  const fetchTools = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMCPTools();
      setTools(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tools');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchTools();
  }, [fetchTools]);

  // Handle external tool selection
  useEffect(() => {
    if (selectedToolName) {
      const tool = tools.find((t) => t.name === selectedToolName);
      if (tool) {
        setSelectedTool(tool);
        initializeParameters(tool);
      } else if (tools.length > 0) {
        // Fetch tool details if not in list
        void (async () => {
          try {
            const toolDetails = await getMCPTool(selectedToolName);
            setSelectedTool(toolDetails);
            initializeParameters(toolDetails);
          } catch {
            setError(`Tool "${selectedToolName}" not found`);
          }
        })();
      }
    }
  }, [selectedToolName, tools]);

  // Initialize parameters with default values
  const initializeParameters = (tool: MCPTool) => {
    const defaults: Record<string, unknown> = {};
    tool.parameters.forEach((param) => {
      if (param.default !== undefined) {
        defaults[param.name] = param.default;
      } else {
        switch (param.type) {
          case 'boolean':
            defaults[param.name] = false;
            break;
          case 'number':
            defaults[param.name] = 0;
            break;
          case 'array':
            defaults[param.name] = [];
            break;
          case 'object':
            defaults[param.name] = {};
            break;
          default:
            defaults[param.name] = '';
        }
      }
    });
    setParameters(defaults);
    setResult(null);
  };

  const handleToolSelect = (toolName: string) => {
    const tool = tools.find((t) => t.name === toolName);
    if (tool) {
      setSelectedTool(tool);
      initializeParameters(tool);
    }
  };

  const handleParameterChange = (name: string, value: unknown) => {
    setParameters((prev) => ({ ...prev, [name]: value }));
  };

  const handleExecute = async () => {
    if (!selectedTool) return;

    setExecuting(true);
    setError(null);
    setResult(null);

    try {
      const executionResult = await executeMCPTool(selectedTool.name, parameters);
      setResult(executionResult);

      // Add to history
      const historyEntry: ExecutionHistoryEntry = {
        ...executionResult,
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        parameters: { ...parameters },
      };
      setHistory((prev) => [historyEntry, ...prev.slice(0, 9)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Execution failed');
    } finally {
      setExecuting(false);
    }
  };

  const handleClearHistory = () => {
    setHistory([]);
  };

  const handleClearSelection = () => {
    setSelectedTool(null);
    setParameters({});
    setResult(null);
    onClearSelection?.();
  };

  // Render parameter input based on type
  const renderParameterInput = (param: MCPToolParameter) => {
    const value = parameters[param.name];

    switch (param.type) {
      case 'boolean':
        return (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={Boolean(value)}
              onChange={(e) => handleParameterChange(param.name, e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              data-testid={`param-${param.name}`}
            />
            <span className="text-sm text-gray-600">Enable</span>
          </label>
        );

      case 'number':
        return (
          <input
            type="number"
            value={value as number}
            onChange={(e) =>
              handleParameterChange(param.name, parseFloat(e.target.value) || 0)
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            data-testid={`param-${param.name}`}
          />
        );

      case 'array':
      case 'object':
        return (
          <textarea
            value={typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
            onChange={(e) => {
              try {
                handleParameterChange(param.name, JSON.parse(e.target.value));
              } catch {
                // Keep as string if invalid JSON
                handleParameterChange(param.name, e.target.value);
              }
            }}
            rows={4}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
            placeholder={param.type === 'array' ? '["item1", "item2"]' : '{"key": "value"}'}
            data-testid={`param-${param.name}`}
          />
        );

      default:
        // String with enum options
        if (param.enum && param.enum.length > 0) {
          return (
            <select
              value={value as string}
              onChange={(e) => handleParameterChange(param.name, e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
              data-testid={`param-${param.name}`}
            >
              <option value="">Select...</option>
              {param.enum.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          );
        }

        // Default string input
        return (
          <input
            type="text"
            value={value as string}
            onChange={(e) => handleParameterChange(param.name, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder={param.description}
            data-testid={`param-${param.name}`}
          />
        );
    }
  };

  // Check if all required parameters are filled
  const canExecute = useMemo(() => {
    if (!selectedTool) return false;
    return selectedTool.parameters
      .filter((p) => p.required)
      .every((p) => {
        const value = parameters[p.name];
        if (value === undefined || value === null) return false;
        if (typeof value === 'string' && value.trim() === '') return false;
        return true;
      });
  }, [selectedTool, parameters]);

  if (loading && tools.length === 0) {
    return (
      <div
        className="bg-white rounded-xl border-2 border-gray-200 p-8 text-center"
        data-testid="mcp-tool-panel-loading"
      >
        <RefreshCw className="w-8 h-8 text-gray-400 animate-spin mx-auto mb-4" />
        <p className="text-gray-500">Loading tools...</p>
      </div>
    );
  }

  return (
    <div
      className="bg-white rounded-xl border-2 border-gray-200 overflow-hidden"
      data-testid="mcp-tool-execution-panel"
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wrench className="w-5 h-5 text-blue-600" />
            <h2 className="font-semibold text-gray-900">Tool Execution</h2>
          </div>
          {selectedTool && (
            <button
              onClick={handleClearSelection}
              className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
              aria-label="Clear selection"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Tool Selection */}
      <div className="p-4 border-b border-gray-100">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Tool
        </label>
        <div className="relative">
          <select
            value={selectedTool?.name || ''}
            onChange={(e) => handleToolSelect(e.target.value)}
            className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white appearance-none"
            data-testid="tool-selector"
          >
            <option value="">Choose a tool...</option>
            {tools.map((tool) => (
              <option key={tool.name} value={tool.name}>
                {tool.name} ({tool.server_name})
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
        {selectedTool && (
          <p className="mt-2 text-sm text-gray-500">{selectedTool.description}</p>
        )}
      </div>

      {/* Parameter Form */}
      {selectedTool && selectedTool.parameters.length > 0 && (
        <div className="p-4 border-b border-gray-100 space-y-4">
          <h3 className="text-sm font-medium text-gray-700">Parameters</h3>
          {selectedTool.parameters.map((param) => (
            <div key={param.name}>
              <label className="block text-sm font-medium text-gray-600 mb-1">
                {param.name}
                {param.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              {renderParameterInput(param)}
              <p className="mt-1 text-xs text-gray-400">{param.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* Execute Button */}
      {selectedTool && (
        <div className="p-4 border-b border-gray-100">
          <button
            onClick={() => void handleExecute()}
            disabled={executing || !canExecute}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            data-testid="execute-tool-button"
          >
            {executing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Execute Tool
              </>
            )}
          </button>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border-b border-red-100" data-testid="tool-execution-error">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-700">Execution Error</p>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Loading Display */}
      {executing && !result && (
        <div
          className="p-4 bg-blue-50 border-b border-gray-100"
          data-testid="tool-execution-loading"
        >
          <div className="flex items-center gap-3">
            <RefreshCw className="w-5 h-5 text-blue-500 animate-spin flex-shrink-0" />
            <p className="text-sm text-blue-700">Executing tool...</p>
          </div>
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div
          className={`p-4 ${result.success ? 'bg-green-50' : 'bg-red-50'} border-b border-gray-100`}
          data-testid="tool-execution-result"
        >
          <div className="flex items-start gap-3">
            {result.success ? (
              <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-grow min-w-0">
              <div className="flex items-center justify-between mb-2">
                <p
                  className={`font-medium ${result.success ? 'text-green-700' : 'text-red-700'}`}
                >
                  {result.success ? 'Execution Successful' : 'Execution Failed'}
                </p>
                <span
                  className="text-xs text-gray-500 flex items-center gap-1"
                  data-testid="execution-time"
                >
                  <Clock className="w-3 h-3" />
                  {result.execution_time_ms}ms
                </span>
              </div>
              {result.result && (
                <pre
                  className="bg-white rounded-lg p-3 text-sm font-mono overflow-x-auto border border-gray-200 max-h-48"
                  data-testid="tool-result"
                >
                  {typeof result.result === 'string'
                    ? result.result
                    : JSON.stringify(result.result, null, 2)}
                </pre>
              )}
              {result.error && (
                <p className="text-sm text-red-600 mt-2">{result.error}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Execution History */}
      {history.length > 0 && (
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-700">
              Execution History ({history.length})
            </h3>
            <button
              onClick={handleClearHistory}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-red-500 transition-colors"
              data-testid="clear-history"
            >
              <Trash2 className="w-3 h-3" />
              Clear
            </button>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {history.map((entry) => (
              <div
                key={entry.id}
                className={`p-3 rounded-lg border ${
                  entry.success
                    ? 'bg-green-50 border-green-200'
                    : 'bg-red-50 border-red-200'
                }`}
                data-testid={`history-entry-${entry.id}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {entry.success ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span className="font-medium text-sm text-gray-900">
                      {entry.tool_name}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="mt-1 text-xs text-gray-500">
                  {entry.execution_time_ms}ms
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!selectedTool && tools.length > 0 && (
        <div className="p-8 text-center">
          <Wrench className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Select a Tool to Execute
          </h3>
          <p className="text-gray-500 text-sm">
            Choose a tool from the dropdown above or click a tool from the server list.
          </p>
        </div>
      )}
    </div>
  );
}

export default MCPToolExecutionPanel;
