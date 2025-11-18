/**
 * Sidebar Component
 * Sprint 15 Feature 15.2: Perplexity-style Sidebar (ADR-021)
 * Sprint 27 Feature 27.9: Quick Actions Bar integration
 *
 * Vertical sidebar with logo, quick actions, history, and health status
 */

import { QuickActionsBar } from './QuickActionsBar';

interface SidebarProps {
  isOpen: boolean;
  onToggle?: () => void;
}

export function Sidebar({ isOpen }: SidebarProps) {
  const handleNewChat = () => {
    // Sprint 27 Feature 27.9: Navigate to new chat
    window.location.href = '/';
  };

  const handleClearHistory = () => {
    // Sprint 27 Feature 27.9: Clear conversation history
    localStorage.removeItem('aegis-chat-history');
    console.log('Chat history cleared');
  };

  const handleSettings = () => {
    // Sprint 27 Feature 27.9: Placeholder for settings
    console.log('Settings clicked (placeholder)');
  };
  return (
    <aside
      className={`
        ${isOpen ? 'w-64' : 'w-0'}
        bg-white border-r border-gray-200
        transition-all duration-300 ease-in-out
        overflow-hidden
        flex flex-col
      `}
    >
      {/* Sidebar Content */}
      <div className="flex flex-col h-full p-4">
        {/* Logo */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-white font-bold">A</span>
            </div>
            <span className="text-lg font-semibold text-gray-900">AegisRAG</span>
          </div>
        </div>

        {/* Quick Actions Bar - Sprint 27 Feature 27.9 */}
        <QuickActionsBar
          onNewChat={handleNewChat}
          onClearHistory={handleClearHistory}
          onSettings={handleSettings}
        />

        {/* History Section */}
        <div className="flex-1 overflow-y-auto">
          <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
            Verlauf
          </h3>
          {/* TODO: Add SessionList component */}
          <div className="text-sm text-gray-500">
            Keine Konversationen
          </div>
        </div>

        {/* Bottom Section: Health Status */}
        <div className="pt-4 border-t border-gray-200">
          <button className="w-full py-2 px-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span>System Status</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
