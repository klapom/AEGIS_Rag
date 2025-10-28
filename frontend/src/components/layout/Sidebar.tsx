/**
 * Sidebar Component
 * Sprint 15 Feature 15.2: Perplexity-style Sidebar (ADR-021)
 *
 * Vertical sidebar with logo, new chat button, history, and health status
 */

interface SidebarProps {
  isOpen: boolean;
  onToggle?: () => void;
}

export function Sidebar({ isOpen }: SidebarProps) {
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

        {/* New Chat Button */}
        <button
          className="w-full py-2 px-4 bg-primary text-white rounded-lg
                     hover:bg-primary-hover transition-colors mb-6
                     flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>Neuer Chat</span>
        </button>

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
