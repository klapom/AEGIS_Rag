/**
 * ToolPermissionsManager Component
 * Sprint 116 Feature 116.5: MCP Tool Management UI
 *
 * Displays all MCP tools with enable/disable toggles and configuration buttons.
 * Provides centralized management of tool permissions.
 */

import { useState, useEffect } from 'react';
import {
  Shield,
  Settings,
  Search,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { getMCPTools, getToolPermissions, updateToolPermissions } from '../../api/admin';
import { ToolConfigModal } from './ToolConfigModal';
import type { MCPTool, MCPToolPermission } from '../../types/admin';

/**
 * Tool with permission status
 */
interface ToolWithPermission extends MCPTool {
  permission: MCPToolPermission | null;
  updating: boolean;
}

/**
 * ToolPermissionsManager - Tool list with permissions management
 *
 * Features:
 * - Display all MCP tools
 * - Enable/disable toggle for each tool
 * - Configuration button to open config modal
 * - Search/filter tools
 * - Permission status badges
 */
export function ToolPermissionsManager() {
  const [tools, setTools] = useState<ToolWithPermission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);
  const [configModalOpen, setConfigModalOpen] = useState(false);

  useEffect(() => {
    void loadTools();
  }, []);

  const loadTools = async () => {
    setLoading(true);
    setError(null);

    try {
      const toolsList = await getMCPTools();

      // Load permissions for each tool
      const toolsWithPermissions = await Promise.all(
        toolsList.map(async (tool) => {
          try {
            const permission = await getToolPermissions(tool.name);
            return {
              ...tool,
              permission,
              updating: false,
            };
          } catch {
            // If permission fetch fails, default to enabled
            return {
              ...tool,
              permission: null,
              updating: false,
            };
          }
        })
      );

      setTools(toolsWithPermissions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tools');
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePermission = async (toolName: string, currentEnabled: boolean) => {
    // Optimistically update UI
    setTools((prev) =>
      prev.map((t) =>
        t.name === toolName
          ? { ...t, updating: true }
          : t
      )
    );

    try {
      const updatedPermission = await updateToolPermissions(toolName, !currentEnabled);

      setTools((prev) =>
        prev.map((t) =>
          t.name === toolName
            ? { ...t, permission: updatedPermission, updating: false }
            : t
        )
      );
    } catch (err) {
      // Revert on error
      setTools((prev) =>
        prev.map((t) =>
          t.name === toolName
            ? { ...t, updating: false }
            : t
        )
      );
      alert(err instanceof Error ? err.message : 'Failed to update permission');
    }
  };

  const handleOpenConfig = (tool: MCPTool) => {
    setSelectedTool(tool);
    setConfigModalOpen(true);
  };

  const handleCloseConfig = () => {
    setSelectedTool(null);
    setConfigModalOpen(false);
  };

  const handleConfigSaved = () => {
    // Optionally refresh permissions after config save
    void loadTools();
  };

  // Filter tools by search query
  const filteredTools = tools.filter((tool) =>
    tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tool.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tool.server_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Count enabled/disabled tools
  const enabledCount = tools.filter((t) => t.permission?.enabled !== false).length;
  const disabledCount = tools.length - enabledCount;

  if (error && tools.length === 0) {
    return (
      <div
        className="bg-white dark:bg-gray-800 rounded-xl border-2 border-red-200 dark:border-red-800 p-8 text-center"
        data-testid="permissions-error"
      >
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Failed to Load Tools
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
        <button
          onClick={() => void loadTools()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="tool-permissions-manager">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/50 rounded-xl flex items-center justify-center">
            <Shield className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Tool Permissions
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Manage which tools are enabled for use ({enabledCount} enabled, {disabledCount} disabled)
            </p>
          </div>
        </div>
        <button
          onClick={() => void loadTools()}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
          data-testid="refresh-permissions"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search tools by name, description, or server..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 dark:bg-gray-700 dark:text-gray-100"
          data-testid="tool-search-input"
        />
      </div>

      {/* Loading State */}
      {loading && tools.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
          <span className="ml-3 text-gray-500">Loading tools...</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredTools.length === 0 && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-8 text-center">
          <Shield className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          {tools.length === 0 ? (
            <>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                No Tools Available
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Connect to MCP servers to see available tools.
              </p>
            </>
          ) : (
            <>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                No Matching Tools
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Try adjusting your search query.
              </p>
            </>
          )}
        </div>
      )}

      {/* Tools List */}
      <div className="space-y-3">
        {filteredTools.map((tool) => {
          const isEnabled = tool.permission?.enabled !== false;
          const isUpdating = tool.updating;

          return (
            <div
              key={tool.name}
              className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-4 hover:border-purple-300 dark:hover:border-purple-700 transition-colors"
              data-testid={`tool-card-${tool.name}`}
            >
              <div className="flex items-start justify-between gap-4">
                {/* Tool Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                      {tool.name}
                    </h3>
                    {isEnabled ? (
                      <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900/50 rounded-full">
                        <CheckCircle className="w-3 h-3" />
                        Enabled
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-900/50 rounded-full">
                        <XCircle className="w-3 h-3" />
                        Disabled
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {tool.description}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    Server: {tool.server_name}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-3">
                  {/* Config Button */}
                  <button
                    onClick={() => handleOpenConfig(tool)}
                    className="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                    aria-label="Configure tool"
                    data-testid={`config-button-${tool.name}`}
                  >
                    <Settings className="w-5 h-5" />
                  </button>

                  {/* Enable/Disable Toggle */}
                  <button
                    onClick={() => void handleTogglePermission(tool.name, isEnabled)}
                    disabled={isUpdating}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 ${
                      isEnabled
                        ? 'bg-green-500 dark:bg-green-600'
                        : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                    role="switch"
                    aria-checked={isEnabled}
                    aria-label={`Toggle ${tool.name}`}
                    data-testid={`toggle-${tool.name}`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        isEnabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Config Modal */}
      <ToolConfigModal
        tool={selectedTool}
        isOpen={configModalOpen}
        onClose={handleCloseConfig}
        onSave={handleConfigSaved}
      />
    </div>
  );
}

export default ToolPermissionsManager;
