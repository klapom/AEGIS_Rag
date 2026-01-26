/**
 * MCP Server Browser Component
 * Sprint 107 Feature 107.3: Browse and search MCP servers from registry
 * Sprint 112: Added multi-registry support with dropdown selector
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Search, Star, Download, ExternalLink, Package, ChevronDown, Globe, RefreshCw } from 'lucide-react';
import type { MCPServerDefinition } from '../../types/mcp';

interface Registry {
  id: string;
  name: string;
  url: string;
  description: string;
  type: string;
}

interface MCPServerBrowserProps {
  registry?: string;
  onInstall?: (server: MCPServerDefinition) => void;
  onServerSelect?: (server: MCPServerDefinition) => void;
  showRegistrySelector?: boolean;
}

export const MCPServerBrowser: React.FC<MCPServerBrowserProps> = ({
  registry: initialRegistry,
  onInstall,
  onServerSelect,
  showRegistrySelector = true,
}) => {
  const [servers, setServers] = useState<MCPServerDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredServers, setFilteredServers] = useState<MCPServerDefinition[]>([]);

  // Sprint 112: Registry selection state
  const [registries, setRegistries] = useState<Registry[]>([]);
  const [selectedRegistry, setSelectedRegistry] = useState<string>(initialRegistry || 'official');
  const [registryDropdownOpen, setRegistryDropdownOpen] = useState(false);
  const [loadingRegistries, setLoadingRegistries] = useState(false);

  // Fetch available registries
  useEffect(() => {
    const fetchRegistries = async () => {
      if (!showRegistrySelector) return;

      setLoadingRegistries(true);
      try {
        const response = await fetch('/api/v1/mcp/registry/registries');
        if (response.ok) {
          const data = await response.json();
          setRegistries(data.registries || []);
        }
      } catch (err) {
        console.error('Failed to fetch registries:', err);
      } finally {
        setLoadingRegistries(false);
      }
    };

    fetchRegistries();
  }, [showRegistrySelector]);

  // Sprint 112: Track if current registry requires browsing (non-JSON)
  const [browseUrl, setBrowseUrl] = useState<string | null>(null);

  // Fetch servers from registry
  const fetchServers = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBrowseUrl(null);

    try {
      const token = localStorage.getItem('token');
      const registryParam = selectedRegistry || 'official';
      const url = `/api/v1/mcp/registry/servers?registry=${encodeURIComponent(registryParam)}`;

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        // Sprint 112: Handle non-JSON registries (400 with browse_url)
        if (response.status === 400) {
          try {
            const errorData = await response.json();
            // Check multiple possible error formats due to middleware wrapping
            // Format 1: errorData.detail.error (direct HTTPException)
            // Format 2: errorData.error.message contains stringified detail
            let browseUrlFound: string | null = null;

            if (errorData.detail?.error === 'registry_not_fetchable') {
              browseUrlFound = errorData.detail.browse_url;
            } else if (errorData.error?.message) {
              // The message might contain the dict as a string, try to extract browse_url
              const msg = errorData.error.message;
              if (msg.includes('registry_not_fetchable') && msg.includes('browse_url')) {
                // Extract URL from string like "'browse_url': 'https://...'"
                const urlMatch = msg.match(/'browse_url':\s*'([^']+)'/);
                if (urlMatch) {
                  browseUrlFound = urlMatch[1];
                }
              }
            }

            if (browseUrlFound) {
              setBrowseUrl(browseUrlFound);
              setServers([]);
              setFilteredServers([]);
              setLoading(false);
              return;
            }
          } catch {
            // If JSON parsing fails, fall through to generic error
          }
        }
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
  }, [selectedRegistry]);

  useEffect(() => {
    fetchServers();
  }, [fetchServers]);

  // Get current registry info
  const currentRegistry = registries.find(r => r.id === selectedRegistry) || {
    id: selectedRegistry,
    name: selectedRegistry,
    url: '',
    description: '',
    type: 'unknown',
  };

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
    <div className="space-y-4" data-testid="mcp-server-browser">
      {/* Sprint 112: Registry Selector */}
      {showRegistrySelector && (
        <div className="flex items-center gap-4 p-4 bg-white border border-gray-200 rounded-lg" data-testid="registry-selector">
          <div className="flex items-center gap-2 text-gray-700">
            <Globe className="h-5 w-5" />
            <span className="font-medium">Registry:</span>
          </div>

          {/* Registry Dropdown */}
          <div className="relative flex-1 max-w-md">
            <button
              onClick={() => setRegistryDropdownOpen(!registryDropdownOpen)}
              disabled={loadingRegistries}
              className="w-full flex items-center justify-between px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
              data-testid="registry-dropdown-button"
            >
              <div className="flex items-center gap-2">
                <span className="font-medium">{currentRegistry.name}</span>
                {currentRegistry.type && (
                  <span className={`px-2 py-0.5 text-xs rounded ${
                    currentRegistry.type === 'json' ? 'bg-green-100 text-green-800' :
                    currentRegistry.type === 'github' ? 'bg-gray-100 text-gray-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {currentRegistry.type}
                  </span>
                )}
              </div>
              <ChevronDown className={`h-4 w-4 transition-transform ${registryDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {registryDropdownOpen && (
              <div
                className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto"
                data-testid="registry-dropdown-menu"
              >
                {registries.map((reg) => (
                  <button
                    key={reg.id}
                    onClick={() => {
                      setSelectedRegistry(reg.id);
                      setRegistryDropdownOpen(false);
                    }}
                    className={`w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-0 ${
                      selectedRegistry === reg.id ? 'bg-blue-50' : ''
                    }`}
                    data-testid={`registry-option-${reg.id}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{reg.name}</span>
                      <span className={`px-2 py-0.5 text-xs rounded ${
                        reg.type === 'json' ? 'bg-green-100 text-green-800' :
                        reg.type === 'github' ? 'bg-gray-100 text-gray-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {reg.type}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{reg.description}</p>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Refresh Button */}
          <button
            onClick={fetchServers}
            disabled={loading}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh servers"
            data-testid="refresh-button"
          >
            <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      )}

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

      {/* Server Count — hidden for browse-only registries */}
      {!browseUrl && (
        <div className="text-sm text-gray-600" data-testid="server-count">
          {filteredServers.length} {filteredServers.length === 1 ? 'server' : 'servers'} found
          {currentRegistry.name && ` in ${currentRegistry.name}`}
        </div>
      )}

      {/* Sprint 112: Browse-only registry message */}
      {browseUrl && (
        <div className="p-6 bg-amber-50 border border-amber-200 rounded-lg text-center" data-testid="browse-registry-message">
          <Globe className="mx-auto h-12 w-12 text-amber-500 mb-4" />
          <h3 className="text-lg font-medium text-amber-900 mb-2">
            Browse This Registry Directly
          </h3>
          <p className="text-amber-700 mb-4">
            This registry ({currentRegistry.name}) is a {currentRegistry.type} directory and cannot be fetched programmatically.
            Please browse it directly to discover MCP servers.
          </p>
          <a
            href={browseUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
            Browse {currentRegistry.name}
          </a>
        </div>
      )}

      {/* Server Grid */}
      {!browseUrl && filteredServers.length === 0 ? (
        <div className="text-center py-12 text-gray-500" data-testid="empty-state">
          <Package className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p>No servers found matching your search.</p>
        </div>
      ) : !browseUrl && (
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
