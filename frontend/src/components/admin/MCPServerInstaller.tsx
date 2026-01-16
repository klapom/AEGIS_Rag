/**
 * MCP Server Installer Dialog
 * Sprint 107 Feature 107.3: Install servers from registry with progress
 */

import React, { useState } from 'react';
import { X, AlertCircle, CheckCircle, Loader, Package } from 'lucide-react';
import type { MCPServerDefinition } from '../../types/mcp';

interface MCPServerInstallerProps {
  server: MCPServerDefinition | null;
  isOpen: boolean;
  onClose: () => void;
  onInstallComplete?: (server: MCPServerDefinition) => void;
}

export const MCPServerInstaller: React.FC<MCPServerInstallerProps> = ({
  server,
  isOpen,
  onClose,
  onInstallComplete,
}) => {
  const [installing, setInstalling] = useState(false);
  const [autoConnect, setAutoConnect] = useState(true);
  const [installStatus, setInstallStatus] = useState<'idle' | 'installing' | 'success' | 'error'>(
    'idle'
  );
  const [errorMessage, setErrorMessage] = useState('');

  const handleInstall = async () => {
    if (!server) return;

    setInstalling(true);
    setInstallStatus('installing');
    setErrorMessage('');

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/mcp/registry/install', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          server_id: server.id,
          auto_connect: autoConnect,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Installation failed');
      }

      const result = await response.json();

      if (result.status === 'error') {
        throw new Error(result.message);
      }

      setInstallStatus('success');

      if (onInstallComplete) {
        onInstallComplete(server);
      }

      // Close dialog after 2 seconds
      setTimeout(() => {
        onClose();
        setInstallStatus('idle');
      }, 2000);
    } catch (err) {
      setInstallStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'Installation failed');
    } finally {
      setInstalling(false);
    }
  };

  if (!isOpen || !server) return null;

  const hasDependencies =
    server.dependencies &&
    (server.dependencies.npm?.length ||
      server.dependencies.pip?.length ||
      server.dependencies.env?.length);

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={onClose}
      data-testid="installer-overlay"
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        data-testid="installer-dialog"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold" data-testid="dialog-title">
            Install MCP Server
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            data-testid="close-button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Server Info */}
          <div className="flex items-start gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Package className="h-8 w-8 text-blue-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg" data-testid="server-name">
                {server.name}
              </h3>
              <p className="text-sm text-gray-500 mb-2" data-testid="server-id">
                {server.id}
              </p>
              <p className="text-sm text-gray-700" data-testid="server-description">
                {server.description}
              </p>
            </div>
          </div>

          {/* Dependencies */}
          {hasDependencies && (
            <div className="border border-gray-200 rounded-lg p-4" data-testid="dependencies-section">
              <h4 className="font-medium mb-3">Dependencies</h4>
              <div className="space-y-2 text-sm">
                {server.dependencies?.npm && server.dependencies.npm.length > 0 && (
                  <div data-testid="npm-dependencies">
                    <span className="font-medium">npm:</span>
                    <ul className="ml-4 mt-1 space-y-1">
                      {server.dependencies.npm.map((pkg) => (
                        <li key={pkg} className="text-gray-700">
                          • {pkg}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {server.dependencies?.pip && server.dependencies.pip.length > 0 && (
                  <div data-testid="pip-dependencies">
                    <span className="font-medium">pip:</span>
                    <ul className="ml-4 mt-1 space-y-1">
                      {server.dependencies.pip.map((pkg) => (
                        <li key={pkg} className="text-gray-700">
                          • {pkg}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {server.dependencies?.env && server.dependencies.env.length > 0 && (
                  <div data-testid="env-dependencies">
                    <span className="font-medium">Environment Variables Required:</span>
                    <ul className="ml-4 mt-1 space-y-1">
                      {server.dependencies.env.map((env) => (
                        <li key={env} className="text-gray-700">
                          • {env}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Auto-connect Option */}
          <div className="flex items-center gap-3" data-testid="auto-connect-option">
            <input
              type="checkbox"
              id="auto-connect"
              checked={autoConnect}
              onChange={(e) => setAutoConnect(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              disabled={installing}
            />
            <label htmlFor="auto-connect" className="text-sm text-gray-700">
              Auto-connect on startup (server will connect automatically and discover tools)
            </label>
          </div>

          {/* Status Messages */}
          {installStatus === 'installing' && (
            <div
              className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg"
              data-testid="installing-status"
            >
              <Loader className="h-5 w-5 text-blue-600 animate-spin" />
              <span className="text-blue-900">Installing server...</span>
            </div>
          )}

          {installStatus === 'success' && (
            <div
              className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg"
              data-testid="success-status"
            >
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-green-900 font-medium">Installation successful!</p>
                <p className="text-sm text-green-700 mt-1">
                  {autoConnect
                    ? 'Server will auto-connect on next startup. Tools will be available after connection.'
                    : 'Server added to configuration. Connect manually to use tools.'}
                </p>
              </div>
            </div>
          )}

          {installStatus === 'error' && (
            <div
              className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg"
              data-testid="error-status"
            >
              <AlertCircle className="h-5 w-5 text-red-600" />
              <div>
                <p className="text-red-900 font-medium">Installation failed</p>
                <p className="text-sm text-red-700 mt-1">{errorMessage}</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded transition-colors"
            disabled={installing}
            data-testid="cancel-button"
          >
            {installStatus === 'success' ? 'Close' : 'Cancel'}
          </button>
          {installStatus !== 'success' && (
            <button
              onClick={handleInstall}
              disabled={installing}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              data-testid="install-button"
            >
              {installing && <Loader className="h-4 w-4 animate-spin" />}
              {installing ? 'Installing...' : 'Install'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
