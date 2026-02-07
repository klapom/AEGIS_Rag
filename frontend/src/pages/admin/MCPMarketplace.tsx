/**
 * MCP Marketplace Page
 * Sprint 107 Feature 107.3: Browse, search, and install MCP servers
 * Sprint 112: Added AdminNavigationBar for navigation back to admin pages
 */

import React, { useState } from 'react';
import { Store, RefreshCw } from 'lucide-react';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';
import { MCPServerBrowser } from '../../components/admin/MCPServerBrowser';
import { MCPServerInstaller } from '../../components/admin/MCPServerInstaller';
import { MCPCustomServerForm } from '../../components/admin/MCPCustomServerForm';
import type { MCPServerDefinition } from '../../types/mcp';

export const MCPMarketplace: React.FC = () => {
  const [selectedServer, setSelectedServer] = useState<MCPServerDefinition | null>(null);
  const [isInstallerOpen, setIsInstallerOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [reloadingConfig, setReloadingConfig] = useState(false);

  const handleInstall = (server: MCPServerDefinition) => {
    setSelectedServer(server);
    setIsInstallerOpen(true);
  };

  const handleInstallComplete = async (server: MCPServerDefinition) => {
    console.log('Server installed:', server);
    // Trigger refresh of browser
    setRefreshKey((prev) => prev + 1);
  };

  const handleReloadConfig = async () => {
    setReloadingConfig(true);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/mcp/reload-config?reconnect=true', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to reload config');
      }

      const result = await response.json();
      console.log('Config reloaded:', result);

      // Show success message
      alert(
        `Configuration reloaded! ${result.connected || 0} servers connected. Tools are now available.`
      );
    } catch (err) {
      console.error('Failed to reload config:', err);
      alert('Failed to reload configuration. Please try again.');
    } finally {
      setReloadingConfig(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6" data-testid="mcp-marketplace-page">
      {/* Sprint 112: Admin Navigation Bar */}
      <div className="max-w-7xl mx-auto mb-4">
        <AdminNavigationBar />
      </div>

      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Store className="h-8 w-8 text-blue-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900" data-testid="page-title">
                MCP Server Marketplace
              </h1>
              <p className="text-gray-600 mt-1" data-testid="page-subtitle">
                Browse and install MCP servers from multiple registries
              </p>
            </div>
          </div>

          {/* Reload Config Button */}
          <button
            onClick={handleReloadConfig}
            disabled={reloadingConfig}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="reload-config-button"
            title="Reload configuration and connect to newly installed servers"
          >
            <RefreshCw className={`h-4 w-4 ${reloadingConfig ? 'animate-spin' : ''}`} />
            {reloadingConfig ? 'Reloading...' : 'Connect Servers'}
          </button>
        </div>

        {/* Info Banner */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg" data-testid="info-banner">
          <h3 className="font-medium text-blue-900 mb-2">How it works:</h3>
          <ol className="list-decimal list-inside space-y-1 text-sm text-blue-800">
            <li>Browse or search for MCP servers in the registry</li>
            <li>Click "Install" to add a server to your configuration</li>
            <li>
              Enable "Auto-connect" to automatically connect on startup, or click "Connect Servers"
              to connect immediately
            </li>
            <li>
              After connection, all server tools are automatically discovered and available for use
            </li>
          </ol>
        </div>
      </div>

      {/* Custom Server Form */}
      <div className="max-w-7xl mx-auto mb-6">
        <MCPCustomServerForm
          onServerAdded={() => {
            setRefreshKey((prev) => prev + 1);
          }}
        />
      </div>

      {/* Browser */}
      <div className="max-w-7xl mx-auto">
        <MCPServerBrowser
          key={refreshKey}
          onInstall={handleInstall}
          onServerSelect={(server) => {
            setSelectedServer(server);
            setIsInstallerOpen(true);
          }}
        />
      </div>

      {/* Installer Dialog */}
      <MCPServerInstaller
        server={selectedServer}
        isOpen={isInstallerOpen}
        onClose={() => {
          setIsInstallerOpen(false);
          setSelectedServer(null);
        }}
        onInstallComplete={handleInstallComplete}
      />
    </div>
  );
};

export default MCPMarketplace;
