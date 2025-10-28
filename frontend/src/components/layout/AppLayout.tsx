/**
 * AppLayout Component
 * Sprint 15 Feature 15.5: Layout with Session History Sidebar
 *
 * Main application layout with session history sidebar and content area
 */

import { type ReactNode } from 'react';
import { SessionSidebar } from '../history';
import { Header } from './Header';

interface AppLayoutProps {
  children: ReactNode;
  sidebarOpen?: boolean;
  onToggleSidebar?: () => void;
}

export function AppLayout({
  children,
  sidebarOpen = true,
  onToggleSidebar
}: AppLayoutProps) {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Session History Sidebar */}
      <SessionSidebar isOpen={sidebarOpen} onToggle={onToggleSidebar || (() => {})} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <Header onToggleSidebar={onToggleSidebar} />

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
