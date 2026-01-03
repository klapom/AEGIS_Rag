/**
 * MCPServerList Component
 * Sprint 72 Feature 72.1: MCP Tool Management UI
 *
 * List of MCP servers with status badges, connect/disconnect buttons,
 * and filter/search functionality.
 */

import { useState, useEffect, useCallback } from 'react';
import { Search, RefreshCw, Server, Filter, AlertCircle } from 'lucide-react';
import { MCPServerCard } from './MCPServerCard';
import { getMCPServers, connectMCPServer, disconnectMCPServer } from '../../api/admin';
import type { MCPServer, MCPServerStatus } from '../../types/admin';

/**
 * Props for MCPServerList
 */
interface MCPServerListProps {
  onSelectTool?: (toolName: string) => void;
}

/**
 * Filter options for server status
 */
type StatusFilter = 'all' | MCPServerStatus;

/**
 * MCPServerList - List of MCP servers with filtering and actions
 *
 * Features:
 * - Display all MCP servers with status
 * - Filter by status (all/connected/disconnected/error)
 * - Search by server name
 * - Connect/disconnect actions per server
 * - Refresh button
 */
export function MCPServerList({ onSelectTool }: MCPServerListProps) {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const fetchServers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMCPServers();
      setServers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch servers');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    void fetchServers();
  }, [fetchServers]);

  const handleConnect = async (serverName: string) => {
    // Optimistically update status to connecting
    setServers((prev) =>
      prev.map((s) =>
        s.name === serverName ? { ...s, status: 'connecting' as MCPServerStatus } : s
      )
    );

    try {
      const updatedServer = await connectMCPServer(serverName);
      setServers((prev) =>
        prev.map((s) => (s.name === serverName ? updatedServer : s))
      );
    } catch {
      // Revert on error
      setServers((prev) =>
        prev.map((s) =>
          s.name === serverName
            ? { ...s, status: 'error' as MCPServerStatus, error_message: 'Connection failed' }
            : s
        )
      );
      throw new Error('Connection failed');
    }
  };

  const handleDisconnect = async (serverName: string) => {
    try {
      const updatedServer = await disconnectMCPServer(serverName);
      setServers((prev) =>
        prev.map((s) => (s.name === serverName ? updatedServer : s))
      );
    } catch {
      throw new Error('Disconnection failed');
    }
  };

  // Filter and search servers
  const filteredServers = servers.filter((server) => {
    const matchesSearch = server.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === 'all' || server.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Count servers by status
  const statusCounts = servers.reduce(
    (acc, server) => {
      acc[server.status] = (acc[server.status] || 0) + 1;
      return acc;
    },
    {} as Record<MCPServerStatus, number>
  );

  if (error && !loading && servers.length === 0) {
    return (
      <div
        className="bg-white rounded-xl border-2 border-red-200 p-8 text-center"
        data-testid="mcp-server-list-error"
      >
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Failed to Load Servers
        </h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={() => void fetchServers()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="mcp-server-list">
      {/* Header with Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="relative flex-grow">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search servers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            data-testid="server-search-input"
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            data-testid="status-filter"
          >
            <option value="all">All ({servers.length})</option>
            <option value="connected">
              Connected ({statusCounts.connected || 0})
            </option>
            <option value="disconnected">
              Disconnected ({statusCounts.disconnected || 0})
            </option>
            <option value="error">Error ({statusCounts.error || 0})</option>
          </select>
        </div>

        {/* Refresh Button */}
        <button
          onClick={() => void fetchServers()}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          data-testid="refresh-servers"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Loading State */}
      {loading && servers.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
          <span className="ml-3 text-gray-500">Loading servers...</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredServers.length === 0 && (
        <div className="bg-gray-50 rounded-xl border-2 border-gray-200 p-8 text-center">
          <Server className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          {servers.length === 0 ? (
            <>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No MCP Servers Configured
              </h3>
              <p className="text-gray-600">
                Configure MCP servers in your backend to manage tools.
              </p>
            </>
          ) : (
            <>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No Matching Servers
              </h3>
              <p className="text-gray-600">
                Try adjusting your search or filter criteria.
              </p>
            </>
          )}
        </div>
      )}

      {/* Server Cards */}
      <div className="space-y-4">
        {filteredServers.map((server) => (
          <MCPServerCard
            key={server.name}
            server={server}
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
            onSelectTool={onSelectTool}
          />
        ))}
      </div>
    </div>
  );
}

export default MCPServerList;
