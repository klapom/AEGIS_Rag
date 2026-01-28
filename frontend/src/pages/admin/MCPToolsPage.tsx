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
import { ArrowLeft, Wrench, Server, Activity, Shield, Terminal } from 'lucide-react';
import { MCPHealthMonitor } from '../../components/admin/MCPHealthMonitor';
import { MCPServerList } from '../../components/admin/MCPServerList';
import { MCPToolExecutionPanel } from '../../components/admin/MCPToolExecutionPanel';
import { ToolPermissionsManager } from '../../components/admin/ToolPermissionsManager';
import { BashExecutionPanel } from '../../components/chat/BashExecutionPanel';

/**
 * Tab view options
 * Sprint 116 Feature 116.5: Added permissions tab
 * Sprint 120 Feature 120.8: Added bash tab
 */
type TabView = 'servers' | 'tools' | 'permissions' | 'bash';

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
            <button
              onClick={() => setActiveTab('bash')}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'bash'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
              data-testid="tab-bash"
            >
              <Terminal className="w-4 h-4" />
              Bash
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
            <button
              onClick={() => setActiveTab('bash')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'bash'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
              data-testid="tab-bash-desktop"
            >
              <Terminal className="w-4 h-4" />
              Bash Execution
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
                Extend your RAG system with external tools via MCP servers. Connect servers, test tool execution, and monitor health.
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

        {/* Bash Tab Content (Full Width) - Sprint 120 Feature 120.8 */}
        {activeTab === 'bash' && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <Terminal className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Bash Command Execution
              </h2>
            </div>
            <BashExecutionPanel />
          </div>
        )}

        {/* Main Content - Two Column Layout (Servers & Tools) */}
        {activeTab !== 'permissions' && activeTab !== 'bash' && (
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

      </div>
    </div>
  );
}

export default MCPToolsPage;
