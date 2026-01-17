/**
 * MCP Server Browser Component
 * Sprint 107 Feature 107.3: Browse and search MCP servers from registry
 */

import React, { useState, useEffect } from 'react';
import { Search, Star, Download, ExternalLink, Package } from 'lucide-react';
import type { MCPServerDefinition } from '../../types/mcp';

interface MCPServerBrowserProps {
  registry?: string;
  onInstall?: (server: MCPServerDefinition) => void;
  onServerSelect?: (server: MCPServerDefinition) => void;
}

export const MCPServerBrowser: React.FC<MCPServerBrowserProps> = ({
  registry,
  onInstall,
  onServerSelect,
}) => {
  const [servers, setServers] = useState<MCPServerDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredServers, setFilteredServers] = useState<MCPServerDefinition[]>([]);

  // Fetch servers from registry
  useEffect(() => {
    const fetchServers = async () => {
      setLoading(true);
      setError(null);

      try {
        const token = localStorage.getItem('token');
        const url = registry
          ? `/api/v1/mcp/registry/servers?registry=${encodeURIComponent(registry)}`
          : '/api/v1/mcp/registry/servers';

        const response = await fetch(url, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch servers: ${response.statusText}`);
        }

        const data = await response.json();
        setServers(data.servers || []);
        setFilteredServers(data.servers || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch servers');
      } finally {
        setLoading(false);
      }
    };

    fetchServers();
  }, [registry]);

  // Filter servers based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredServers(servers);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = servers.filter(
      (server) =>
        server.name.toLowerCase().includes(query) ||
        server.description.toLowerCase().includes(query) ||
        server.id.toLowerCase().includes(query) ||
        server.tags.some((tag) => tag.toLowerCase().includes(query))
    );

    setFilteredServers(filtered);
  }, [searchQuery, servers]);

  const handleInstall = (server: MCPServerDefinition) => {
    if (onInstall) {
      onInstall(server);
    }
  };

  const handleServerClick = (server: MCPServerDefinition) => {
    if (onServerSelect) {
      onServerSelect(server);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12" data-testid="loading-state">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg" data-testid="error-state">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="mcp-server-browser-container">
      {/* Search Bar */}
      <div className="relative">
        <input
          type="text"
          placeholder="Search servers by name, description, or tags..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          data-testid="search-input"
        />
        <Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
      </div>

      {/* Server Count */}
      <div className="text-sm text-gray-600" data-testid="server-count">
        {filteredServers.length} {filteredServers.length === 1 ? 'server' : 'servers'} found
      </div>

      {/* Server Grid */}
      {filteredServers.length === 0 ? (
        <div className="text-center py-12 text-gray-500" data-testid="empty-state">
          <Package className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p>No servers found matching your search.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredServers.map((server) => (
            <div
              key={server.id}
              className="border border-gray-200 rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => handleServerClick(server)}
              data-testid={`server-card-${server.id}`}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900" data-testid="server-name">
                    {server.name}
                  </h3>
                  <p className="text-xs text-gray-500" data-testid="server-id">
                    {server.id}
                  </p>
                </div>
                <span
                  className={`px-2 py-1 text-xs rounded ${
                    server.transport === 'stdio'
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-green-100 text-green-800'
                  }`}
                  data-testid="server-transport"
                >
                  {server.transport}
                </span>
              </div>

              {/* Description */}
              <p className="text-sm text-gray-600 mb-3 line-clamp-2" data-testid="server-description">
                {server.description}
              </p>

              {/* Stats */}
              <div className="flex items-center gap-4 mb-3 text-sm text-gray-500">
                <div className="flex items-center gap-1" data-testid="server-stars">
                  <Star className="h-4 w-4" />
                  {server.stars.toLocaleString()}
                </div>
                <div className="flex items-center gap-1" data-testid="server-downloads">
                  <Download className="h-4 w-4" />
                  {server.downloads.toLocaleString()}
                </div>
                <span className="text-xs" data-testid="server-version">
                  v{server.version}
                </span>
              </div>

              {/* Tags */}
              {server.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3" data-testid="server-tags">
                  {server.tags.slice(0, 3).map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded"
                    >
                      {tag}
                    </span>
                  ))}
                  {server.tags.length > 3 && (
                    <span className="px-2 py-0.5 text-gray-500 text-xs">
                      +{server.tags.length - 3}
                    </span>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleInstall(server);
                  }}
                  className="flex-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                  data-testid="install-button"
                >
                  Install
                </button>
                {server.repository && (
                  <a
                    href={server.repository}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="p-1.5 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                    title="View repository"
                    data-testid="repository-link"
                  >
                    <ExternalLink className="h-4 w-4 text-gray-600" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
