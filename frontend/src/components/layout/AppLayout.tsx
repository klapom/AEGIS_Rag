/**
 * AppLayout Component
 * Sprint 15 Feature 15.5: Layout with Session History Sidebar
 * Sprint 46 Feature 46.3: Removed duplicate sidebar - pages handle their own sidebars
 *
 * Main application layout wrapper. Note: SessionSidebar is now managed by individual
 * pages (e.g., HomePage) to avoid duplicate sidebars. This layout provides the overall
 * structure without the sidebar.
 */

import { type ReactNode } from 'react';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Main Content Area - Sidebar is managed by individual pages */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
