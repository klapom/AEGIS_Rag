/**
 * MCPServerCard Component
 * Sprint 72 Feature 72.1: MCP Tool Management UI
 *
 * Individual server card with tools list, status indicator, and connect/disconnect actions.
 * Expand/collapse for tool details.
 */

import { useState } from 'react';
import {
  Server,
  Plug,
  Unplug,
  ChevronDown,
  ChevronRight,
  Wrench,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import type { MCPServer, MCPServerStatus } from '../../types/admin';

/**
 * Props for MCPServerCard
 */
interface MCPServerCardProps {
  server: MCPServer;
  onConnect: (serverName: string) => Promise<void>;
  onDisconnect: (serverName: string) => Promise<void>;
  onSelectTool?: (toolName: string) => void;
}

/**
 * Get status badge configuration
 */
function getStatusConfig(status: MCPServerStatus): {
  bg: string;
  text: string;
  icon: React.ReactNode;
  label: string;
} {
  switch (status) {
    case 'connected':
      return {
        bg: 'bg-green-100',
        text: 'text-green-700',
        icon: <CheckCircle className="w-3 h-3" />,
        label: 'Connected',
      };
    case 'disconnected':
      return {
        bg: 'bg-gray-100',
        text: 'text-gray-600',
        icon: <XCircle className="w-3 h-3" />,
        label: 'Disconnected',
      };
    case 'connecting':
      return {
        bg: 'bg-blue-100',
        text: 'text-blue-700',
        icon: <Loader2 className="w-3 h-3 animate-spin" />,
        label: 'Connecting...',
      };
    case 'error':
      return {
        bg: 'bg-red-100',
        text: 'text-red-700',
        icon: <AlertCircle className="w-3 h-3" />,
        label: 'Error',
      };
    default:
      return {
        bg: 'bg-gray-100',
        text: 'text-gray-600',
        icon: <XCircle className="w-3 h-3" />,
        label: 'Unknown',
      };
  }
}

/**
 * MCPServerCard - Individual server card with tools and actions
 *
 * Features:
 * - Status indicator (connected/disconnected/error/connecting)
 * - Connect/disconnect buttons
 * - Expandable tools list
 * - Tool selection for execution
 */
export function MCPServerCard({
  server,
  onConnect,
  onDisconnect,
  onSelectTool,
}: MCPServerCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const statusConfig = getStatusConfig(server.status);
  const isConnected = server.status === 'connected';
  const isConnecting = server.status === 'connecting';

  const handleConnect = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      await onConnect(server.name);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Connection failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      await onDisconnect(server.name);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Disconnection failed');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div
      className="bg-white rounded-xl border-2 border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
      data-testid={`mcp-server-${server.name}`}
      data-server-name={server.name}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <Server className="w-5 h-5 text-gray-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{server.name}</h3>
              {server.description && (
                <p className="text-sm text-gray-500">{server.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Status Badge */}
            <span
              className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.text}`}
              data-testid={`server-status-${server.name}`}
              data-status={server.status}
            >
              {statusConfig.icon}
              <span data-testid="server-status">{statusConfig.label}</span>
            </span>
          </div>
        </div>

        {/* Server URL */}
        {server.url && (
          <p className="mt-2 text-xs text-gray-400 font-mono">{server.url}</p>
        )}

        {/* Action Error */}
        {actionError && (
          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{actionError}</p>
          </div>
        )}

        {/* Error Message from server */}
        {server.error_message && (
          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{server.error_message}</p>
          </div>
        )}

        {/* Actions */}
        <div className="mt-3 flex items-center gap-2">
          {isConnected ? (
            <button
              onClick={() => void handleDisconnect()}
              disabled={actionLoading}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors disabled:opacity-50"
              data-testid={`disconnect-${server.name}`}
            >
              {actionLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Unplug className="w-4 h-4" />
              )}
              Disconnect
            </button>
          ) : (
            <button
              onClick={() => void handleConnect()}
              disabled={actionLoading || isConnecting}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-green-600 bg-green-50 hover:bg-green-100 rounded-lg transition-colors disabled:opacity-50"
              data-testid={`connect-${server.name}`}
            >
              {actionLoading || isConnecting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Plug className="w-4 h-4" />
              )}
              Connect
            </button>
          )}

          {/* Expand/Collapse Tools */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors ml-auto"
            aria-expanded={expanded}
            aria-controls={`tools-${server.name}`}
            data-testid={`toggle-tools-${server.name}`}
          >
            <Wrench className="w-4 h-4" />
            <span data-testid={`tools-count-${server.name}`}>
              {server.tool_count ?? server.tools?.length ?? 0} Tools
            </span>
            {expanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Tools List (Expanded) */}
      {expanded && (
        <div
          id={`tools-${server.name}`}
          className="p-4 bg-gray-50 space-y-2"
          data-testid={`tools-list-${server.name}`}
        >
          {(server.tools?.length ?? 0) === 0 ? (
            <p className="text-sm text-gray-500 text-center py-2">
              No tools available
            </p>
          ) : (
            (server.tools ?? []).map((tool) => (
              <div
                key={tool.name}
                className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer"
                onClick={() => onSelectTool?.(tool.name)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectTool?.(tool.name);
                  }
                }}
                data-testid={`tool-${tool.name}`}
              >
                <div className="flex items-center gap-3">
                  <Wrench className="w-4 h-4 text-blue-500" />
                  <div>
                    <p className="font-medium text-gray-900 text-sm">{tool.name}</p>
                    <p className="text-xs text-gray-500 line-clamp-1">
                      {tool.description}
                    </p>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default MCPServerCard;
