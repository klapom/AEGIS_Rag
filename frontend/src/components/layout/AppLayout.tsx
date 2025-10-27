/**
 * AppLayout Component
 * Sprint 15 Feature 15.2: Perplexity-style Layout (ADR-021)
 *
 * Main application layout with sidebar and content area
 */

import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
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
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onToggle={onToggleSidebar} />

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
