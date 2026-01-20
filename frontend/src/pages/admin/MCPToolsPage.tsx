/**
 * MCPToolsPage Component
 * Sprint 72 Feature 72.1: MCP Tool Management UI
 *
 * Main page for MCP Server Management with connect/disconnect functionality
 * and tool execution testing.
 *
 * Features:
 * - Real-time health monitoring
 * - Server list with status badges
 * - Connect/disconnect functionality
 * - Tool execution panel
 * - Responsive two-column layout
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Wrench, Server, Activity, Shield } from 'lucide-react';
import { MCPHealthMonitor } from '../../components/admin/MCPHealthMonitor';
import { MCPServerList } from '../../components/admin/MCPServerList';
import { MCPToolExecutionPanel } from '../../components/admin/MCPToolExecutionPanel';
import { ToolPermissionsManager } from '../../components/admin/ToolPermissionsManager';

/**
 * Tab view options
 * Sprint 116 Feature 116.5: Added permissions tab
 */
type TabView = 'servers' | 'tools' | 'permissions';

/**
 * MCPToolsPage - Main page for MCP tool management
 *
 * Layout:
 * - Header with back button and tabs
 * - Health monitor bar
 * - Two-column layout on desktop: Server list + Tool execution panel
 * - Single column on mobile with tab navigation
 */
export function MCPToolsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabView>('servers');
  const [selectedTool, setSelectedTool] = useState<string | null>(null);

  const handleSelectTool = (toolName: string) => {
    setSelectedTool(toolName);
    setActiveTab('tools');
  };

  const handleClearSelection = () => {
    setSelectedTool(null);
  };

  return (
    <div
      className="min-h-screen bg-gray-50 dark:bg-gray-900"
      data-testid="mcp-tools-page"
    >
      <div className="max-w-7xl mx-auto py-8 px-6 space-y-6">
        {/* Header */}
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/admin')}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200 transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              data-testid="back-to-admin-button"
              aria-label="Back to Admin Dashboard"
            >
              <ArrowLeft className="w-5 h-5" />
              <span>Back to Admin</span>
            </button>
          </div>

          {/* Mobile Tab Navigation */}
          <div className="flex sm:hidden bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('servers')}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'servers'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
              data-testid="tab-servers"
            >
              <Server className="w-4 h-4" />
              Servers
            </button>
            <button
              onClick={() => setActiveTab('tools')}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'tools'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
              data-testid="tab-tools"
            >
              <Wrench className="w-4 h-4" />
              Execute
            </button>
            <button
              onClick={() => setActiveTab('permissions')}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'permissions'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
              data-testid="tab-permissions"
            >
              <Shield className="w-4 h-4" />
              Permissions
            </button>
          </div>

          {/* Desktop Tab Navigation */}
          <div className="hidden sm:flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('servers')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'servers'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
              data-testid="tab-servers-desktop"
            >
              <Server className="w-4 h-4" />
              Servers
            </button>
            <button
              onClick={() => setActiveTab('tools')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'tools'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
              data-testid="tab-tools-desktop"
            >
              <Wrench className="w-4 h-4" />
              Tool Execution
            </button>
            <button
              onClick={() => setActiveTab('permissions')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'permissions'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
              data-testid="tab-permissions-desktop"
            >
              <Shield className="w-4 h-4" />
              Permissions
            </button>
          </div>
        </header>

        {/* Page Title and Description */}
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/50 rounded-xl flex items-center justify-center">
              <Wrench className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                MCP Tools
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Manage MCP servers and test tool execution
              </p>
            </div>
          </div>
        </div>

        {/* Health Monitor */}
        <MCPHealthMonitor />

        {/* Permissions Tab Content (Full Width) */}
        {activeTab === 'permissions' && (
          <div className="space-y-4">
            <ToolPermissionsManager />
          </div>
        )}

        {/* Main Content - Two Column Layout (Servers & Tools) */}
        {activeTab !== 'permissions' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Server List Column */}
            <div
              className={`space-y-4 ${
                activeTab === 'tools' ? 'hidden lg:block' : 'block'
              }`}
            >
              <div className="flex items-center gap-2 mb-4">
                <Server className="w-5 h-5 text-gray-500" />
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  MCP Servers
                </h2>
              </div>
              <MCPServerList onSelectTool={handleSelectTool} />
            </div>

            {/* Tool Execution Column */}
            <div
              className={`space-y-4 ${
                activeTab === 'servers' ? 'hidden lg:block' : 'block'
              }`}
            >
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-gray-500" />
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Tool Execution
                </h2>
              </div>
              <MCPToolExecutionPanel
                selectedToolName={selectedTool}
                onClearSelection={handleClearSelection}
              />
            </div>
          </div>
        )}

        {/* Info Section */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-xl p-6">
          <div className="flex gap-3">
            <div className="flex-shrink-0">
              <svg
                className="w-6 h-6 text-blue-600 dark:text-blue-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div>
              <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                About MCP Tools
              </h4>
              <p className="text-sm text-blue-800 dark:text-blue-200">
                The Model Context Protocol (MCP) allows you to extend the capabilities of your RAG system
                with external tools and services. Connect to MCP servers to access their tools, then
                test them using the execution panel. Tools can perform actions like web searches,
                file operations, API calls, and more.
              </p>
              <ul className="mt-3 space-y-1 text-sm text-blue-800 dark:text-blue-200">
                <li className="flex items-start gap-2">
                  <svg
                    className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>Connect/disconnect servers to manage tool availability</span>
                </li>
                <li className="flex items-start gap-2">
                  <svg
                    className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>Test tool execution with custom parameters</span>
                </li>
                <li className="flex items-start gap-2">
                  <svg
                    className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>Monitor health status with auto-refresh every 30 seconds</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MCPToolsPage;
